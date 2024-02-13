
import sys, os
import importlib
from pathlib import Path

from .logging import get_printer

from collections import OrderedDict

prt = get_printer(__name__)

def multi_index(obj, *inds):
	if len(inds):
		idx, *inds = inds
		return multi_index(obj[idx], *inds)
	return obj

def safe_self_execute(obj, fn, default='<<short circuit>>',
					  flag='safe execute flag'):
	if flag in obj.__dict__:
		return default  # short circuit
	obj.__dict__[flag] = True
	
	try:
		out = fn()
	finally:
		del obj.__dict__['self printed flag']
	
	return out



class cwd:
	def __init__(self, path, prepend=True):
		self.path = None
		if path is not None:
			path = Path(path)
			path = path.absolute()
			if path.is_dir():
				self.path = path

		# assert os.path.isdir(self.path), 'invalid path: {}'.format(self.path)
		self.prepend = prepend
		self.old = None

	def __enter__(self):
		if self.path is not None:
			self.old = os.getcwd()
			os.chdir(self.path)
			if self.prepend:
				sys.path.insert(0, str(self.path))

	def __exit__(self, exc_type, exc_val, exc_tb):
		if self.path is not None:
			os.chdir(self.old)
			if self.prepend:
				del sys.path[0]



def filter_local_modules(path, modules):
	if path is not None:# and isinstance(path, Path):
		for name, module in modules.items():
			loc = getattr(module, '__file__', None)
			if loc is not None and loc.startswith(str(path.absolute())):
				yield name, module
				# loc = Path(loc)
				# if loc.name == '__init__.py':
				# 	loc = loc.parent
				# loc = loc.parent
				# if loc.absolute() == path.absolute():
				# 	yield name, module



def find_submodules(module):
	"""Identify submodules of a given module."""
	submodules = []
	base_path = Path(module.__file__).parent
	for attribute_name in dir(module):
		attribute = getattr(module, attribute_name)
		if hasattr(attribute, '__file__'):
			attribute_path = Path(attribute.__file__).parent
			if base_path == attribute_path or base_path in attribute_path.parents:
				submodules.append(attribute)
	return submodules


def reload_module_recursively(module):
	"""Reload a module and all its submodules."""
	importlib.reload(module)
	for submodule in find_submodules(module):
		reload_module_recursively(submodule)


def include_modules(*modules: str, root=None, allow_local=False, package_name=None):
	'''
	Imports modules based on their names/paths

	Args:
		modules: list of modules (names or paths) to be imported
		root: root directory containing the modules (inserted at the beginning of sys.path)
		allow_local: if True, will leave any local modules in sys.modules

	Returns:
		:code:`None`

	'''
	loaded = OrderedDict()

	world = set(sys.modules.keys())
	all_new = dict()

	package_name = None

	with cwd(root):
		for mod in modules:
			path = mod.parent if isinstance(mod, Path) else None
			name = mod.stem if isinstance(mod, Path) else mod
			with cwd(path):
				if name not in sys.modules:
					prt.debug(f'Importing {name}')
					out = importlib.import_module(name, package_name)
				else:
					existing_module = sys.modules[name]
					if Path(existing_module.__file__).parent.parent.absolute() == Path().absolute():
						# Reload the existing module and its submodules
						prt.debug(f'Reloading {name}')
						reload_module_recursively(existing_module)
					else:
						# Replace the module and reload it along with its submodules
						prt.debug(f'Replacing {name} (previously {sys.modules[name].__file__!r})')
						del sys.modules[name]
						new_module = importlib.import_module(name, package_name)
						reload_module_recursively(new_module)
				# elif Path(sys.modules[name].__file__).parent.parent.absolute() == Path().absolute():
				# 	prt.debug(f'Reloading {name}')
				# 	out = importlib.reload(sys.modules[name])
				# else:
				# 	prt.debug(f'Replacing {name} (previously {sys.modules[name].__file__!r})')
				# 	del sys.modules[name]
				# 	out = importlib.import_module(name, package_name)
				new = {k: v for k, v in sys.modules.items() if k not in world}
				loaded[mod] = (out, new.copy())
				all_new.update(new)
				world.update(new.keys())

	# TODO: removed to enable multiprocessing - was it necessary in the first place?
	# if not allow_local and root is not None:
	# 	for n, m in filter_local_modules(root, all_new):
	# 		del sys.modules[n]

	return loaded



class lengen:
	class _lengen: # TODO: wrap generator functions
		def __init__(self, gen, n):
			self.gen = gen
			self.n = n
			
		def __iter__(self):
			return self
		
		def __next__(self):
			return next(self.gen)
		
		def __len__(self):
			return self.n
	
	def __init__(self, generator_fn):
		self.generator_fn = generator_fn
		
	def __repr__(self):
		return f'<lengen {self.generator_fn.__name__}>'
	
	def __call__(self, *args, **kwargs):
		gen = self.generator_fn(*args, **kwargs)
		return self._lengen(gen, next(gen))




