
import sys, os
import importlib
from pathlib import Path

from collections import OrderedDict

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



def _filter_local(path, modules):
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



def include_modules(*modules: str, root=None, allow_local=False):
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

	with cwd(root):
		for mod in modules:
			path = mod.parent if isinstance(mod, Path) else None
			name = mod.stem if isinstance(mod, Path) else mod
			with cwd(path):
				if name not in sys.modules:
					# prt.debug(f'Importing {name}')
					out = importlib.import_module(name)
				else:
					# prt.debug(f'Reloading {name}')
					out = importlib.reload(sys.modules[name])
				new = {k: v for k, v in sys.modules.items() if k not in world}
				loaded[mod] = (out, new.copy())
				all_new.update(new)
				world.update(new.keys())

	if not allow_local and root is not None:
		for n, m in _filter_local(root, all_new):
			del sys.modules[n]

	return loaded

