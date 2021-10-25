import sys, os
import json
import yaml
import pickle

from . import unspecified_argument
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



def load_txt(path):
	path = str(path)
	with open(path, 'r') as f:
		return f.read()

def save_txt(data, path):
	path = str(path)
	with open(path, 'w') as f:
		return f.write(data)


def save_pickle(data, path):
	with open(str(path), 'w') as f:
		pickle.dump(data, f)


def load_pickle(path):
	with open(str(path), 'r') as f:
		return pickle.load(f)


def create_dir(directory):
	directory = str(directory)
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



class Persistent:
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._datafiles = {}


	def _get_datafile_path(self, path=None, name=None, ext=None):
		if path is None:
			raise NotImplementedError
		if name is None:
			return path
		if ext is not None:
			name = f'{name}.{ext}'
		path.mkdir(exist_ok=True)
		return path / name


	def _save_datafile(self, data, path=None, name=None, ext='pk', overwrite=False):
		path = self._get_datafile_path(path=path, name=name, ext=ext)
		if not path.exists() or overwrite:
			save_pickle(data, path)
			return path


	def _load_datafile(self, path=None, name=None, ext='pk', **kwargs):
		path = self._get_datafile_path(path=path, name=name, ext=ext)
		return load_pickle(path)


	def has_datafile(self, ident, path=None, ext=None, persistent=False):
		fixed = ident.split('.')[0] if ext is not None else ident
		if fixed in self._datafiles and not persistent:
			return True

		return self._get_datafile_path(path=path, name=fixed, ext=ext).exists()


	def update_datafile(self, ident, data, path=None, overwrite=False, ext=None, **kwargs):
		fixed = ident.split('.')[0] if ext is not None else ident

		self._datafiles[fixed] = data
		return self._save_datafile(data, name=fixed, path=path, overwrite=overwrite, **kwargs)


	def get_datafile(self, ident, path=None, ext=None, force_load=False, skip_cache=False,
	                 default=unspecified_argument, **kwargs):
		if not force_load:
			if ident in self._datafiles:
				return self._datafiles[ident]

			fixed = ident.split('.')[0] if ext is not None else ident
			if fixed in self._datafiles:
				return self._datafiles[fixed]

		try:
			self._datafiles[fixed] = self._load_datafile(name=fixed, path=path, **kwargs)
		except FileNotFoundError:
			if default is unspecified_argument:
				raise
			self.update_datafile(fixed, default, path)
		out = self._datafiles[fixed]
		if skip_cache:
			del self._datafiles[fixed]
		return out


	def store_datafiles(self, datafiles=None, path=None, overwrite=False, ext=None, **kwargs):
		if datafiles is None:
			datafiles = self._datafiles
		return {name: self.update_datafile(name, value, path=path, overwrite=overwrite, ext=ext, **kwargs)
		        for name, value in datafiles.items()}



class HierarchyPersistent(Persistent):

	def _save_datafile(self, data, path=None, name=None, ext='pk', overwrite=False,
	                  separate_dict=True, recursive=False):
		top = None if separate_dict and isinstance(data, dict) else ext
		path = self._get_results_path(path=path, name=name, ext=top)

		if top is None:
			path.mkdir(exist_ok=True)
			for key, value in data.items():
				self._save_datafile(value, path=path, name=key, overwrite=overwrite, ext=ext,
				                   separate_dict=separate_dict and recursive, recursive=recursive)
			return path
		return super()._save_datafile(data, path=path, name=name, ext=ext, overwrite=overwrite)


	def _load_datafile(self, path=None, name=None, ext=None, delimiter='/', **kwargs):
		assert path is not None or name is not None, 'no info'

		if isinstance(name, str):
			name = name.split(delimiter)
		if name is not None:
			name = Path(*name)

		path = self._get_results_path(path=path, name=name, ext=ext)
		if path.is_dir():
			return {p.stem.split('.')[0]: self._load_results(path=p, delimiter=delimiter, **kwargs)
			        for p in path.glob('*')}
		elif not path.is_file():
			fix = list(path.parents[0].glob(f'{path.name}*'))
			if len(fix) == 0:
				raise FileNotFoundError(str(path))
			path = fix[0]

		return super()._load_datafile(path=path, ext=ext, **kwargs)










