import sys, os
import yaml

def load_yaml(path):
	with open(path, 'r') as f:
		return yaml.safe_load(f)

def save_yaml(data, path):
	with open(path, 'w') as f:
		return yaml.safe_dump(data, f)

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

