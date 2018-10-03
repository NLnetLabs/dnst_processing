#!/usr/bin/env python

from datetime import *
import matplotlib
import sys
matplotlib.use('Agg')
import matplotlib.pyplot as pp
import matplotlib.patches as mpatches
import matplotlib.dates as mpd
import pandas as pd

def darken(color):
	return '#%.2X%.2X%.2X' % ( int(color[1:3], 16) / 1.25
	                         , int(color[3:5], 16) / 1.25
	                         , int(color[5:7], 16) / 1.25
	                         )

class Index(object):
	def __init__(self, path, title):
		self.path  = path
		self.title = title
		self.plots = []

	def add_plots(self, title, anchor, plots, refs = None):
		self.plots.append((title, anchor, plots))

	def save(self):
		with file(self.path + '/index.html', 'w') as f:
			f.write('<html><head><title>%s</title></head><body>\n'
			       % self.title)
			first = True
			for title, anchor, plots in self.plots:
				if first:
					first = False
				else:
					f.write('<hr />\n')
				f.write( '<a name="%s"></a><h1>%s</h1>\n%s\n'
				       % (anchor, title, plots))

class Prop(object):
	def __init__(self, title, col_name, lab_name, size = 3):
		self.title    = title
		self.col_name = col_name
		self.lab_name = lab_name
		self.size     = size
		self.plot_fns = []

	def cols(self):
		return [p + '_' + self.col_name for p, l in self.prop][:self.size]
	def labs(self):
		return [l + ' ' + self.lab_name for p, l in self.prop][:self.size]
	def colors(self):
		return ['#7DB874', '#E39C37', '#D92120'][:self.size]
	
	def register_plot(self, fn):
		self.plot_fns.append(fn)
	
	def register_with_index(self, ind):
		ind.add_plots( self.title
		             , self.col_name
		             , ''.join([ '<img src="%s" />' % fn.split('/')[-1]
		                         for fn in self.plot_fns ]))
	
	def plot_more(self, ax):
		pass;

	def do_plot(self, dt_ts, data_ts, fn, data_ts_prbs = None):
		fig, ax = pp.subplots(figsize=(8, 4.5))

		if len(dt_ts) > 270:
			ticks = []
			prev_month = dt_ts[0].month
			for day in dt_ts:
				if day.month != prev_month:
					ticks.append(day)
				prev_month = day.month

			ax.xaxis.set_ticks(ticks)
			ax.xaxis.set_major_formatter(mpd.DateFormatter('%Y-%m-%d'))
		else:
			ax.xaxis.set_major_formatter(mpd.DateFormatter('%Y-%m-%d'))

		ax.stackplot(dt_ts, data_ts, colors = self.colors())
		ax.set_xlim(dt_ts[0], dt_ts[-1])

		self.dt_ts = dt_ts
		self.plot_more(ax)
		
		colors = [ mpatches.Patch(color = c) for c in self.colors()]
		labels = self.labs()
		if data_ts_prbs:
			i = 0
			for col_prbs in data_ts_prbs:
				color = darken(self.colors()[i])
				colors.append(mpatches.Patch(color = color))
				label = 'probes that ' + labels[i]
				labels.append(label)
				ax.plot(dt_ts, col_prbs, color = color)
				i += 1
		ax.legend( colors[::-1]
			 , labels[::-1]
			 , ncol=1, loc='upper left')
		ax.set_ylabel('Probe/resolver pairs')
		
		fig.autofmt_xdate(rotation=45)
		pp.savefig(fn)
		pp.close()
		self.register_plot(fn)

	def plot(self, dt_ts, csv, ind):
		data_ts = [csv[col].values for col in self.cols()]
		for offset in range(len(dt_ts)):
			if sum([ts[offset] for ts in data_ts]) > 0:
				break;
		data_ts_prbs = [csv[col + '_prbs'].values[offset:] for col in self.cols()]

		self.csv    = csv
		self.do_plot( dt_ts[offset:]
		            , [ts[offset:] for ts in data_ts]
			    , ind.path + '/' + self.col_name + '.svg'
		            , data_ts_prbs )
		self.register_with_index(ind)

class DoesProp(Prop):
	prop = [('does', 'do'), ('doesnt', 'do not do')]

class HasProp(Prop):
	prop = [('has', 'have'), ('hasnt', 'do not have ')]
	def colors(self):
		return ['#7DB874', '#D92120'][:self.size]

class CanProp(Prop):
	prop = [('can', 'can do'), ('cannot', 'cannot do'), ('broken', 'broken')]

class DNSSECProp(CanProp):
	prop = [('can', 'can do'), ('cannot', 'cannot do'), ('broken', 'has broken')]
	def labs(self):
		return [ self.lab_name + ' secure', self.lab_name + ' insecure'
		       , self.lab_name + ' failing' ]

class DNSKEYProp(DNSSECProp):
	def __init__(self, col_name, lab_name):
		super(DNSKEYProp, self).__init__(
		    'DNSKEY Algorithm %s support' % lab_name, col_name, lab_name)

class DSProp(DNSSECProp):
	def __init__(self, col_name, lab_name):
		super(DSProp, self).__init__(
		    'DS Algorithm %s support' % lab_name, col_name, lab_name)

class IntProp(Prop):
	def __init__(self):
		super(IntProp, self).__init__(
		    'Internal, Forwarding & External',
		    'int_fwd_ext', 'Internal/Forwarding/External')
	def cols(self):
		return ['is_internal', 'is_forwarding', 'is_external']
	def labs(self):
		return ['internal', 'forwarding', 'external']
	def colors(self):
		return ['#993399', '#339999', '#999933']

class TopASNs(Prop):
	def __init__(self, asn_type):
		self.asn_type = asn_type
		self.labels = None
		super(TopASNs, self).__init__(
		    ( 'Top %d %sASNs'
		    % ( len(self.colors()) - 1
		      , 'Probe ' if asn_type == 'probe' else
		        'Resolver ' if asn_type == 'resolver' else
		        'Authoritative ' if asn_type == 'auth' else '' )),
		    'top_%s_asns' % asn_type, 'Top ASNs')

	def labs(self):
		return self.labels
	def colors(self):
		return [ '#CC9966', '#CC6699', '#99CC66', '#9966CC', '#66CC99', '#6699CC'
		       , '#33CC99', '#3399CC', '#CC3399', '#CC9933'#, '#9933CC', '#99CC33'
		       , '#999999'][:(len(self.labels)
		                       if self.labels is not None else 999999)]
	def plot(self, dt_ts, csv, ind):
		offset = -1
		n_resolvers = csv['# resolvers'].values
		for i in range(len(n_resolvers)):
			if n_resolvers[i] != 0:
				offset = i
				break
		if offset < 0:
			return '';

		asn_totals = dict()
		bands = [ zip( csv['%s #%d total' % (self.asn_type, band)].values[offset:]
		             , csv['%s #%d ASNs' % (self.asn_type, band)].values[offset:])
		          for band in range(1,100) ]
		rem   = csv['Remaining %s ASNs count' % self.asn_type].values[offset:]
		bands += [zip(rem, ['rem'] * len(rem))]
		for band in bands:
			i = 0
			for total, ASNs in band:
				if n_resolvers[offset + i] == 0:
					i += 1
					continue
				if type(ASNs) is not str or not ASNs.startswith('AS'):
					i ++ 1
					continue
				ASNs = ASNs.split(',')
				for asn in ASNs:
					if asn not in asn_totals:
						asn_totals[asn] = 0
					asn_totals[asn] += total / len(ASNs)
				i += 1

		top = sorted( [(tot, asn) for asn, tot in asn_totals.items()]
		            , reverse = True)

		size = len(self.colors())
		self.labels = [asn for tot, asn in top][:size-1]
		self.labels += ['Remaining']
		data_ts = list()
		i = 0
		for row in zip(*bands):
			if n_resolvers[offset + i] == 0:
				i += 1
				data_ts.append([0] * size)
				continue
			asn_dict = {}
			top_row = list()
			rem = 0
			for total, ASNs in row:
				if type(ASNs) is not str:
					continue
				if not ASNs.startswith('AS'):
					rem += total
					continue
				ASNs = ASNs.split(',')
				for asn in ASNs:
					asn_dict[asn] = total / len(ASNs)
			for j in range(len(self.labels)-1):
				asn = self.labels[j]
				top_row.append(asn_dict.get(asn, 0))
				asn_dict[asn] = 0
			top_row.append(sum(asn_dict.values()) + rem)
			data_ts.append(top_row)
			i += 1

		data_ts = [list(ts) for ts in zip(*data_ts)]
		self.do_plot( dt_ts[offset:], data_ts
			    , ind.path + '/' + self.col_name + '.svg' )
		self.register_with_index(ind)

class TopECSMasks(Prop):
	def __init__(self):
		self.labels = None
		super(TopECSMasks, self).__init__(
		    'Top EDNS Client Subnet masks', 'ecs_masks', 'ECS Masks')

	def labs(self):
		return self.labels
	def colors(self):
		return [ '#CC9966', '#CC6699', '#99CC66', '#9966CC', '#66CC99', '#6699CC'
		       , '#33CC99'#, '#3399CC', '#CC3399', '#CC9933', '#9933CC', '#99CC33'
		       , '#999999'][:(len(self.labels)
		                       if self.labels is not None else 999999)]
	def plot(self, dt_ts, csv, ind):
		offset = -1
		n_resolvers = csv['# resolvers'].values
		for i in range(len(n_resolvers)):
			if n_resolvers[i] != 0:
				offset = i
				break
		if offset < 0:
			return '';

		ecs_totals = dict()
		masks = [ zip( csv['ECS mask #%d'       % mask].values[offset:]
		             , csv['ECS mask #%d count' % mask].values[offset:])
		          for mask in range(1,10) ]
		rem   = csv['Remaining ECS mask count'].values[offset:]
		masks+= [zip([-1] * len(rem), rem)]
		for mask_counts in masks:
			i = 0
			for mask, count in mask_counts:
				if n_resolvers[offset + i] == 0:
					i += 1
					continue
				if mask not in ecs_totals:
					ecs_totals[mask] = 0
				ecs_totals[mask] += count
				i += 1

		top = sorted( [ (tot, ecs) for ecs, tot in ecs_totals.items()]
		            , reverse = True)
		size = len(self.colors())
		self.labels = [ecs for tot, ecs in top][:size-1]
		self.labels += ['Remaining']
		data_ts = list()
		i = 0
		for row in zip(*masks):
			if n_resolvers[offset + i] == 0:
				i += 1
				data_ts.append([0] * size)
				continue
			ecs_dict = dict(row)
			top_row = list()
			rem = 0
			for j in range(len(self.labels)-1):
				mask = self.labels[j]
				top_row.append(ecs_dict.get(mask, 0))
				ecs_dict[mask] = 0
			top_row.append(sum(ecs_dict.values()) + rem)
			data_ts.append(top_row)
			i += 1

		data_ts = [list(ts) for ts in zip(*data_ts)]
		self.labels = [ '/' + str(l) if type(l) is not str else l
		                for l in self.labels]
		self.do_plot( dt_ts[offset:], data_ts
			    , ind.path + '/' + self.col_name + '.svg' )
		self.register_with_index(ind)

class TAProp(HasProp):
	def __init__(self):
		return super(TAProp, self).__init__(
		    'Root Key Trust Anchor Sentinel for DNSSEC',
		    'ta_20326' , '. KSK 20326')
	
	def colors(self):
		return super(TAProp, self).colors() + ['#000000']
	def labs(self):
		return super(TAProp, self).labs() + ['has . KSK 19036']
	def plot_more(self, ax):
		has_19036 = self.csv['has_ta_19036'].values
		if len(has_19036) > len(self.dt_ts):
			has_19036 = has_19036[(len(has_19036) - len(self.dt_ts)):]
		ax.plot(self.dt_ts, has_19036, color = '#000000')

def create_plots(fn):
	props = [ CanProp   ('IPv6', 'ipv6'     , 'IPv6'       , 1)
		, CanProp   ('TCP' , 'tcp'      , 'TCP'        , 1)
		, CanProp   ('TCP6', 'tcp6'     , 'TCP6'       , 1)
		, DoesProp  ('Non existant domain hijacking', 'nxdomain' , 'NX hijacking', 2)
		, DoesProp  ('Qname Minimization', 'qnamemin' , 'qnamemin'   , 2)
		, DoesProp  ('ENDS Client Subnet', 'ecs'      , 'EDNS Client Subnet', 1)
		, TopECSMasks()
                , IntProp()
		, TopASNs   ('auth')
		, TopASNs   ('resolver')
		, TopASNs   ('probe')
	        , TAProp()
		, DNSKEYProp('ed448'    , 'ED448')
		, DNSKEYProp('ed25519'  , 'ED25519')
		, DNSKEYProp('ecdsa384' , 'ECDSA-P384-SHA384')
		, DNSKEYProp('ecdsa256' , 'ECDSA-P256-SHA256')
		, DNSKEYProp('eccgost'  , 'ECC-GOST')
		, DNSKEYProp('rsasha512', 'RSA-SHA512')
		, DNSKEYProp('rsasha256', 'RSA-SHA256')
		, DNSKEYProp('rsansec3' , 'RSA-SHA1-NSEC3')
		, DNSKEYProp('dsansec3' , 'DSA-NSEC3')
		, DNSKEYProp('rsasha1'  , 'RSA-SHA1')
		, DNSKEYProp('dsa'      , 'DSA')
		, DNSKEYProp('rsamd5'   , 'RSA-MD5')
		, DSProp    ('gost'     , 'GOST DS')
		, DSProp    ('sha384'   , 'SHA-384 DS')
		]

	report_csv  = pd.read_csv(fn)

	ts_series   = [ datetime.strptime(iso_dt, '%Y-%m-%dT%H:%M:%SZ')
		        for iso_dt in report_csv['datetime'].values ]

	path = '/'.join(fn.split('/')[:-1])
	path = path if path else '.'
	page = Index(path, 'DNSThought')
	for prop in props:
		prop.plot(ts_series, report_csv, page)
	page.save()

if __name__ == '__main__':
	if len(sys.argv) != 2:
		print('usage: %s <report.csv>' % sys.argv[0])
		sys.exit(1)
	
	create_plots(sys.argv[1])
