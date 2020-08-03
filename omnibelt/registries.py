
from collections import OrderedDict, namedtuple

from .logging import get_printer

prt = get_printer(__name__)

class Registry(OrderedDict):
	
	def new(self, name, obj): # register a new entry
		if name in self:
			prt.warning(f'Register {self.__class__.__name__} already contains {name}, now overwriting')
		# else:
		# 	prt.debug(f'Registering {name} in {self.__class__.__name__}')
		
		self[name] = obj
	
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

class Entry_Registry(Registry):
	'''
	Automatically wraps data into an "entry" object (namedtuple) which is stored in the registry
	'''
	def __init_subclass__(cls, components=[]):
		super().__init_subclass__()
		cls._entry = namedtuple(f'{cls.__name__}_Entry', ['name' ] +components)
	
	def new(self, name, **info):  # register a new entry
		super().new(name, self._entry(name=name, **info))



