import sys, os
import json
import yaml

from collections import OrderedDict

def monkey_patch(cls, module=None, include_mp=True):
	if module is None:
		import __main__
		module = __main__
		
		# try:
		# 	import __mp_main__
		# except ImportError:
		# 	pass
		# else:
		# 	monkey_patch(cls, module=__mp_main__)
	
	setattr(module, cls.__name__, cls)
	cls.__module__ = module.__name__

def ordered_load(stream, Loader=yaml.Loader, object_pairs_hook=OrderedDict):
	class OrderedLoader(Loader):
		pass
	def construct_mapping(loader, node):
		loader.flatten_mapping(node)
		return object_pairs_hook(loader.construct_pairs(node))
	OrderedLoader.add_constructor(
		yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
		construct_mapping)
	return yaml.load(stream, OrderedLoader)

# usage example:
# ordered_load(stream, yaml.SafeLoader)

def ordered_dump(data, stream=None, Dumper=yaml.Dumper, **kwds):
	class OrderedDumper(Dumper):
		pass
	def _dict_representer(dumper, data):
		return dumper.represent_mapping(
			yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
			data.items())
	OrderedDumper.add_representer(OrderedDict, _dict_representer)
	return yaml.dump(data, stream, OrderedDumper, **kwds)

# usage:
# ordered_dump(data, Dumper=yaml.SafeDumper)

def load_yaml(path, ordered=False):
	path = str(path)
	with open(path, 'r') as f:
		if ordered:
			return ordered_load(f, yaml.SafeLoader)
		return yaml.safe_load(f)

		# return yaml.load(f)

def save_yaml(data, path, ordered=False, default_flow_style=None, **kwargs):
	path = str(path)
	with open(path, 'w') as f:
		if ordered:
			return ordered_dump(data, stream=f, Dumper=yaml.SafeDumper,
			                    default_flow_style=default_flow_style, **kwargs)
		return yaml.safe_dump(data, f, default_flow_style=default_flow_style, **kwargs)


def load_json(path):
	path = str(path)
	with open(path, 'r') as f:
		return json.load(f)

def save_json(data, path):
	path = str(path)
	with open(path, 'w') as f:
		return json.dump(data, f)



def create_dir(directory):
	if not os.path.exists(directory):
		os.makedirs(directory)

def crawl(d, cond):
	if os.path.isdir(d):
		options = []
		for f in os.listdir(d):
			path = os.path.join(d, f)
			options.extend(crawl(path, cond))
		return options
	if cond(d):
		return [d]
	return []

def load_csv(path, sep=',', head=0, tail=0, row_sep='\n', as_gen=False):
	'''
	
	:param path:
	:param sep:
	:param head: number of lines to skip at the beginning of the file
	:param tail: number of lines to skip at the end of the file
	:return:
	'''

	with open(path, 'r') as f:
		raw = f.read()

	lines = raw.split(row_sep)
	if head > 0:
		lines = lines[min(head, len(lines)):]
	if tail > 0:
		lines = lines[:-min(tail, len(lines))]
		
	rows = (line.split(sep) for line in lines)
	
	if as_gen:
		return rows
	return list(rows)

def load_tsv(path, **kwargs):
	kwargs['sep'] = '\t'
	return load_csv(path, **kwargs)

def spawn_path_options(path):
	options = set()
	
	if os.path.isfile(path):
		options.add(path)
		path = os.path.dirname(path)
	
	if os.path.isdir(path):
		options.add(path)
	
	# TODO: include FIG_PATH_ROOT
	
	return options

