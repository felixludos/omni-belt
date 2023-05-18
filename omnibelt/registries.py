from typing import NamedTuple, Dict, Any, Union, Optional, List, Tuple, Callable, Type, Sequence, Iterable, Iterator
from pathlib import Path
from collections import OrderedDict, namedtuple

from .typing import unspecified_argument
from .logging import get_printer

prt = get_printer(__name__)

class Registry(OrderedDict):
	def new(self, name, obj): # register a new entry
		# if name in self:
		# 	prt.warning(f'Register {self.__class__.__name__} already contains {name}, now overwriting')
		# else:
		# 	prt.debug(f'Registering {name} in {self.__class__.__name__}')
		
		self[name] = obj
		return obj

	class NotFoundError(KeyError): pass


	def find(self, x, default=unspecified_argument):
		if x in self:
			return self[x]
		if default is not unspecified_argument:
			return default
		raise self.NotFoundError(x)


	def is_registered(self, obj):
		for opt in self.values():
			if obj == opt:
				return True
		return False


class Named_Registry(Registry):


	def find_name(self, obj):
		return obj.get_name()


	def is_registered(self, obj):
		name = self.find_name(obj)
		return name in self


# class _Entry:
# 	def __init__(self, **kwargs):
# 		self.__dict__.update(kwargs)


class Entry_Registry(Registry):
	'''
	Automatically wraps data into an "entry" object (namedtuple) which is stored in the registry
	'''
	entry_cls: namedtuple = None
	def __init_subclass__(cls, key_name='name', components=[], required=[]):
		super().__init_subclass__()
		entry_keys = [key_name, *components]
		# cls._entry_keys = entry_keys
		cls.entry_cls: namedtuple = namedtuple(f'{cls.__name__}_Entry', entry_keys)
		cls._required_keys = [key_name, *required]
		cls._key_name = key_name


	def new(self, *args, **kwargs):  # register a new entry
		args = dict(zip(self.entry_cls._fields, args))

		overlap = ', '.join(set(args).intersection(kwargs.keys()))
		if len(overlap):
			raise TypeError(f'{self.__class__.__name__} got multiple values for arguments: {overlap}')

		info = {**args, **kwargs}

		missing = ', '.join(key for key in self._required_keys if key not in info)
		if len(missing):
			raise TypeError(f'{self.__class__.__name__} missing {len(missing)} required keys for entry: {missing}')

		return super().new(info[self._key_name], self.entry_cls(**info))



class InvalidDoubleRegistryError(Exception):
	pass



class Double_Registry(Registry):
	def __init__(self, *args, _sister_registry_object=None, _sister_registry_cls=None, **kwargs):
		if _sister_registry_cls is None:
			_sister_registry_cls = self.__class__
		if _sister_registry_object is None:
			_sister_registry_object = _sister_registry_cls(_sister_registry_object=self)
		
		super().__init__(*args, **kwargs)
		self._sister_registry_object = _sister_registry_object
		
		self._init_sister_registry()


	def _init_sister_registry(self):
		for k, v in self.items():
			self._sister_registry_object.__setitem__(v, k, sync=False)


	def is_known(self, x):
		return x in self or x in self.backward()


	def find(self, x, default=unspecified_argument):
		if x in self:
			return self[x]
		if x in self.backward():
			return self.backward()[x]
		if default is not unspecified_argument:
			return default
		raise self.NotFoundError(x)


	def backward(self):
		return self._sister_registry_object


	def update(self, other, sync=True):
		if sync:
			self._sister_registry_object.update({v:k for k,v in other.items()}, sync=False)
		return super().update(other)


	def __setitem__(self, key, value, sync=True):
		if sync:
			self._sister_registry_object.__setitem__(value, key, sync=False)
		return super().__setitem__(key, value)


	def __delitem__(self, key, sync=True):
		if sync:
			self._sister_registry_object.__delitem__(self[key], sync=False)
		return super().__delitem__(key)



class Entry_Double_Registry(Double_Registry, Entry_Registry):
	
	def __init_subclass__(cls, primary_component='name', sister_component='value', components=[], required=[]):
		super().__init_subclass__(key_name=primary_component, components=[sister_component, *components],
		                          required=[sister_component, *required])
		cls._sister_key_name = sister_component


	def _init_sister_registry(self):
		for k, v in self.items():
			self._sister_registry_object.__setitem__(self._get_sister_entry_key(k, v), v, sync=False)


	@classmethod
	def _get_sister_entry_key(cls, key, value):
		assert isinstance(value, cls.entry_cls)
		if key == getattr(value, cls._key_name):
			return getattr(value, cls._sister_key_name)
		return getattr(value, cls._key_name)


	def get_value(self, key, default=unspecified_argument):
		if default is unspecified_argument:
			return getattr(self.find(key), self._sister_key_name)
		return getattr(self.find(key), self._sister_key_name, default)


	def update(self, other, sync=True):
		if sync:
			self._sister_registry_object.update({self._get_sister_entry_key(k, v): v
			                                     for k, v in other.items()}, sync=False)
		return super().update(other, sync=False)


	def __setitem__(self, key, value, sync=True):
		if sync:
			self._sister_registry_object.__setitem__(self._get_sister_entry_key(key, value), value, sync=False)
		return super().__setitem__(key, value, sync=False)


	def __delitem__(self, key, sync=True):
		if sync:
			self._sister_registry_object.__delitem__(self._get_sister_entry_key(key, self[key]), sync=False)
		return super().__delitem__(key, sync=False)


	def get_decorator(self, name: Optional[str] = None, defaults: Dict[str, Any] = None) -> Type['DecoratorBase']:
		if defaults is None:
			defaults = {}
		return type(f'{self.__class__.__name__}_Decorator' if name is None else name,
		            (self.DecoratorBase,), {'_registry': self, '_defaults': defaults})


	class DecoratorBase:
		_registry = None
		_defaults = None
		def __init__(self, *args, **kwargs):

			registry = self._registry

			arg_keys = list(registry.entry_cls._fields)
			# del arg_keys[1]
			args = dict(zip(arg_keys, args))

			overlap = ', '.join({registry._sister_key_name, *args.keys()}.intersection(kwargs))
			if len(overlap):
				raise TypeError(f'{self.__class__.__name__} got multiple values for arguments: {overlap}')

			self.params = {**args, **kwargs}


		# @classmethod
		# def _get_registry(cls):
		# 	return cls._registry


		def _register(self, val, **params):
			registry = self._registry
			key = registry._sister_key_name
			if key not in params:
				params[key] = val
			full = self._defaults.copy()
			full.update(params)
			return registry.new(**params)


		def __call__(self, sister_value):
			self._register(sister_value, **self.params)
			return sister_value


class Path_Registry(Entry_Double_Registry, sister_component='path'):
	def __init_subclass__(cls, sister_component='path', components=[], required=[]):
		super().__init_subclass__(primary_component='name', sister_component=sister_component,
		                          components=components, required=required)

	def new(self, name, path, *args, **kwargs):
		if isinstance(path, str):
			path = Path(path)
		return super().new(name, path, *args, **kwargs)

	def get_path(self, key):
		return self.get_value(key)


class Function_Registry(Entry_Double_Registry, sister_component='fn'):
	def __init_subclass__(cls, sister_component='fn', components=[], required=[]):
		super().__init_subclass__(primary_component='name', sister_component=sister_component,
		                          components=components, required=required)

	def get_function(self, key):
		return self.get_value(key)


class Class_Registry(Entry_Double_Registry, sister_component='cls'):

	def __init_subclass__(cls, sister_component='cls', components=[], required=[]):
		super().__init_subclass__(primary_component='name', sister_component=sister_component,
		                          components=components, required=required)

	def get_class(self, key, default=unspecified_argument):
		return self.get_value(key, default=default)

	class DecoratorBase(Entry_Double_Registry.DecoratorBase):
		def _register(self, val, name=None, **params):
			if name is None:
				name = val.__name__
			return super()._register(val, name=name, **params)




