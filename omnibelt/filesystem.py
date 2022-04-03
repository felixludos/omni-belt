import sys, os
from pathlib import Path
import json
import yaml
import pickle

from . import unspecified_argument, agnosticmethod
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


def load_json(path, **kwargs):
	path = str(path)
	with open(path, 'r') as f:
		return json.load(f, **kwargs)

def save_json(data, path, **kwargs):
	path = str(path)
	with open(path, 'w') as f:
		return json.dump(data, f, **kwargs)



def load_txt(path):
	path = str(path)
	with open(path, 'r') as f:
		return f.read()

def save_txt(data, path):
	path = str(path)
	with open(path, 'w') as f:
		return f.write(data)


def save_pickle(data, path):
	with open(str(path), 'wb') as f:
		pickle.dump(data, f)


def load_pickle(path):
	with open(str(path), 'rb') as f:
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


	def _get_datafile_path(self, path, ext=unspecified_argument, quiet=False):
		'''if no name is provided, the head of path is used. if no ext is provided, it will try to be inferred
		by path contents, but no ext is used if it is ambiguous'''
		path = Path(path)
		root, name = path.parents[0], path.name #path.stem, path.suffix
		if ext is unspecified_argument and root.exists():
			options = list(root.glob(f'{name}*'))
			if len(options) == 1:
				name = options[0].name
		elif ext is not unspecified_argument and ext is not None:
			name = f'{name}.{ext}'
		if not quiet:
			create_dir(root)
			# root.mkdir(exist_ok=True)
		return root / name


	def _save_datafile(self, data, path, ext=unspecified_argument, overwrite=False, _save_fn=None):
		if ext is unspecified_argument:
			ext = 'pk'
		path = self._get_datafile_path(path, ext=ext)
		if _save_fn is None:
			_save_fn = save_pickle
		if not path.exists() or overwrite:
			_save_fn(data, str(path))
			return path


	def _load_datafile(self, path=None, name=None, ext=unspecified_argument, _load_fn=None):
		if ext is unspecified_argument:
			ext = 'pk'
		path = self._get_datafile_path(path=path, ext=ext)
		if _load_fn is None:
			_load_fn = load_pickle
		return _load_fn(str(path))


	def has_datafile(self, ident, root=None, ext=unspecified_argument, persistent=False):
		fixed, *suffix = ident.split('.')
		if ext is unspecified_argument and len(suffix):
			ext = '.'.join(suffix)
		if (ident in self._datafiles or fixed in self._datafiles) and not persistent:
			return True

		path = self._get_datafile_path(fixed if root is None else Path(root, fixed), ext=ext)
		return path.exists()


	def update_datafile(self, ident, data, root=None, overwrite=True, skip_save=False,
	                    ext=unspecified_argument, **kwargs):
		fixed, *suffix = ident.split('.')
		if ext is None and len(suffix):
			ext = '.'.join(suffix)
		path = fixed if root is None else Path(root, fixed)

		self._datafiles[fixed] = data
		if not skip_save:
			return self._save_datafile(data, path=path, ext=ext, overwrite=overwrite, **kwargs)


	def get_datafile(self, ident, root=None, ext=unspecified_argument, force_load=False, skip_cache=False,
	                 default=unspecified_argument, **kwargs):
		fixed, *suffix = ident.split('.')
		if ext is None and len(suffix):
			ext = '.'.join(suffix)
		path = fixed if root is None else Path(root, fixed)

		if not force_load:
			if ident in self._datafiles:
				return self._datafiles[ident]

			if fixed in self._datafiles:
				return self._datafiles[fixed]

		try:
			self._datafiles[fixed] = self._load_datafile(path, ext=ext, **kwargs)
		except FileNotFoundError:
			if default is unspecified_argument:
				raise
			self.update_datafile(fixed, default, root=root, ext=ext)
		out = self._datafiles[fixed]
		if skip_cache:
			del self._datafiles[fixed]
		return out


	def store_datafiles(self, datafiles=None, root=None, overwrite=False, ext=unspecified_argument, **kwargs):
		if datafiles is None:
			datafiles = self._datafiles
		return {name: self.update_datafile(name, value, root=root, overwrite=overwrite, ext=ext, **kwargs)
		        for name, value in datafiles.items()}



class HierarchyPersistent(Persistent):


	def _save_datafile(self, data, path, ext=unspecified_argument, overwrite=False,
	                  separate_dict=True, recursive=False, **kwargs):
		top = None if separate_dict and isinstance(data, dict) else ext
		path = self._get_datafile_path(path, ext=top)

		if top is None:
			path.mkdir(exist_ok=True)
			for key, value in data.items():
				self._save_datafile(value, path=path / key, overwrite=overwrite,
				                   separate_dict=separate_dict and recursive, recursive=recursive, **kwargs)
			return path
		return super()._save_datafile(data, path=path, ext=None, overwrite=overwrite, **kwargs)


	def _load_datafile(self, path, ext=unspecified_argument, delimiter='/', **kwargs):
		if isinstance(path, str) and delimiter is not None:
			path = Path(*path.split(delimiter))

		path = self._get_datafile_path(path=path, ext=ext)
		if path.is_dir():
			return {p.stem.split('.')[0]: self._load_datafile(path=p, delimiter=delimiter, **kwargs)
			        for p in path.glob('*')}
		return super()._load_datafile(path=path, ext=None, **kwargs)










