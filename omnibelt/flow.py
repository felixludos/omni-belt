
import sys, os
import importlib
from pathlib import Path

from .loggers import get_printer

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



def include_module(module: str, root=None, allow_local=False):
	'''
	Imports modules based on their names/paths

	Args:
		modules: list of modules (names or paths) to be imported
		root: root directory containing the modules (inserted at the beginning of sys.path)
		allow_local: if True, will leave any local modules in sys.modules

	Returns:
		:code:`None`

	'''
	world = set(sys.modules.keys())
	all_new = dict()

	with cwd(root):
		path = module.parent if isinstance(module, Path) else None
		name = module.stem if isinstance(module, Path) else module
		with cwd(path):
			if name in sys.modules:
				prt.debug(f'Reloading {name}')
				out = importlib.reload(sys.modules[name])
			else:
				prt.debug(f'Importing {name}')
				out = importlib.import_module(name)

	# TODO: removed to enable multiprocessing - was it necessary in the first place?
	# if not allow_local and root is not None:
	# 	for n, m in filter_local_modules(root, all_new):
	# 		del sys.modules[n]

	new = {k: v for k, v in sys.modules.items() if k not in world}
	return out, new



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


try:
	import cloudpickle
except ImportError:
	prt.warning('cloudpickle not found, some functionality may be limited.')
	cloudpickle = None

from typing import Iterator, Tuple, Callable, TypeVar, Any, Union, Iterable
import multiprocessing as mp



class pickle_rick:
	def __init__(self, fn: Callable, *, num_workers: int = None, pickle_args: bool = False, star: bool = None):
		if num_workers is None:
			num_workers = mp.cpu_count()
		num_args = fn.__code__.co_argcount
		if star is None:
			star = num_args > 1
		self._pool = None
		self._fn = fn
		self._num_workers = num_workers
		self._pickle_args = pickle_args
		self._star_args = star

	def __enter__(self):
		if self._num_workers > 0:
			pfn = cloudpickle.dumps(self._fn)
			self._pool = mp.Pool(self._num_workers, initializer=self._worker_init,
								 initargs=(pfn, self._pickle_args, self._star_args))
		return self

	def __exit__(self, exc_type, exc_val, exc_tb):
		if self._pool is not None:
			self._pool.close()
			self._pool.join()

	def start(self):
		self.__enter__()

	def close(self):
		self.__exit__(None, None, None)

	def __del__(self):
		self.close()

	# is set by the worker
	_child_worker_unpickle_args = None
	_child_worker_star_args = None
	_child_worker_fn = None

	@classmethod
	def _worker_init(cls, pfn: bytes, pickle_args: bool, star_args: bool):
		cls._child_worker_unpickle_args = pickle_args
		cls._child_worker_star_args = star_args
		cls._child_worker_fn = cloudpickle.loads(pfn)

	@classmethod
	def _worker_fn(cls, info):
		if cls._child_worker_unpickle_args:
			info = cloudpickle.loads(info)
		if cls._child_worker_star_args:
			return cls._child_worker_fn(*info)
		return cls._child_worker_fn(info)

	def _local_worker_fn(self, info):
		if self._pickle_args:
			info = cloudpickle.dumps(info)
		if self._star_args:
			return self._fn(*info)
		return self._fn(info)

	def _dispatch(self, dispatcher_name: str, src: Union[Iterator, Iterable]):
		if self._num_workers == 0:
			return (self._local_worker_fn(info) for info in src)
		if self._pool is None:
			with self:
				return self._dispatch(dispatcher_name, src)
		return getattr(self._pool, dispatcher_name)(self._worker_fn, src)

	def map(self, src: Union[Iterator, Iterable]) -> Iterable[Any]: # blocking
		out = self._dispatch('map', src)
		return tuple(out) if self._num_workers == 0 else out

	def imap(self, src: Union[Iterator, Iterable]) -> Iterator[Any]:
		yield from self._dispatch('imap', src)

	def imap_unordered(self, src: Union[Iterator, Iterable]) -> Iterator[Any]:
		yield from self._dispatch('imap_unordered', src)



def test_pickle_rick():
	y = 10
	def f(x):
		return x - y

	with pickle_rick(f, num_workers=0) as pool:
		assert pool.map([10, 20]) == (0, 10)

	with pickle_rick(f, num_workers=1) as pool:
		assert tuple(pool.imap([10, 20])) == (0, 10)




# def pickle_rick(info):
# 	'''just pickle run it, f*ck'''
# 	import cloudpickle
#
# 	pfn, args = info
#
# 	fn = cloudpickle.loads(pfn)
#
# 	return fn(*args)
#
#
#
# _pickle_rick_state = None
# def pickle_rick_init(info):
# 	'''just pickle run it, f*ck'''
# 	import cloudpickle
#
# 	pfn, args = info
#
# 	fn = cloudpickle.loads(pfn)
#
# 	global __pickle_rick_state
# 	if __pickle_rick_state is None:
# 		__pickle_rick_state = fn(*args)
# 		return __pickle_rick_state
# 	else:
# 		return fn(__pickle_rick_state, *args)
#
#
# def pickle_rick_me(fn, src, num_workers=None):
#
# 	import cloudpickle
# 	import multiprocessing as mp
#
# 	if num_workers is None:
# 		num_workers = mp.cpu_count()
#
# 	if num_workers == 0:
# 		yield from map(fn, src)
#
# 	else:
# 		pfn = cloudpickle.dumps(fn)
# 		with mp.Pool(num_workers) as pool:
# 			for out in pool.imap_unordered(fn, src):
# 				yield out
#
#
# 	pass



