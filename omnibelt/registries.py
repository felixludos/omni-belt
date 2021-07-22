
from collections import OrderedDict, namedtuple

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
	def __init_subclass__(cls, key_name='name', components=[]):
		super().__init_subclass__()
		cls.entry_cls = namedtuple(f'{cls.__name__}_Entry', [key_name] + components)
		cls._key_name = key_name
	
	def new(self, *args, **info):  # register a new entry
		if self._key_name not in info:
			assert len(args) == 1
			info[self._key_name] = args[0]
		assert self._key_name in info, f'Missing key: {self._key_name}'
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
	
	def __init_subclass__(cls, primary_component='name', sister_component='cls', components=[]):
		super().__init_subclass__(key_name=primary_component, components=[sister_component] + components)
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



