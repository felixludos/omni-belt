import sys, os
import yaml

from collections import OrderedDict


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
	with open(path, 'r') as f:
		if ordered:
			return ordered_load(f, yaml.SafeLoader)
		return yaml.safe_load(f)

def save_yaml(data, path, ordered=False, default_flow_style=None, **kwargs):
	with open(path, 'w') as f:
		if ordered:
			return ordered_dump(data, stream=f, Dumper=yaml.SafeDumper,
			                    default_flow_style=default_flow_style, **kwargs)
		return yaml.safe_dump(data, f, default_flow_style=default_flow_style, **kwargs)


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


def spawn_path_options(path):
	options = set()
	
	if os.path.isfile(path):
		options.add(path)
		path = os.path.dirname(path)
	
	if os.path.isdir(path):
		options.add(path)
	
	# TODO: include FIG_PATH_ROOT
	
	return options

