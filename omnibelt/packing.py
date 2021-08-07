
from typing import Any, Union, Dict, List, Set, Tuple, NoReturn, ClassVar, TextIO, Callable, NewType
import json
from pathlib import Path
from collections import namedtuple, OrderedDict
import time

import copy

from .registries import Entry_Double_Registry
# from .errors import SavableClassCollisionError, ObjectIDReadOnlyError, UnregisteredClassError
from .logging import get_printer

prt = get_printer(__file__)

primitive = (str, int, float, bool, type(None)) # all json readable and no sub elements
# py_types = (bytes, complex, range, tuple)
# py_containers = (dict, list, set)


class MissingEntryError(TypeError):
	def __init__(self, name=None, cls=None, ancestors=None):
		msg = []
		if name is not None:
			msg.append(f'name={name}')
		if cls is not None:
			msg.append(f'cls={cls}')
		if ancestors is not None:
			msg.append(f'ancestors={ancestors}')
		msg = ', '.join(msg)
		super().__init__(msg)



class Packable_Registry(Entry_Double_Registry, primary_component='name', sister_component='cls',
                        components=['pack_fn', 'create_fn', 'unpack_fn', 'ancestors']):
	
	_pack_fn_name = '__pack__'
	_unpack_fn_name = '__unpack__'
	_create_fn_name = '__create__'
	
	
	def new(self, cls, name=None, pack_fn=None, create_fn=None, unpack_fn=None, ancestors=None):
		''' TODO: update
		Register a type to be packable. Requires a pack_fn, create_fn, and unpack_fn to store and restore object state.

		:param cls: type to be registered
		:param pack_fn: callable input is an instance of the type, and packs all data necessary to recover the state
		:param create_fn: callable input is the expected type and the packed data, creates a new instance of the type,
		without unpacking any packed data (to avoid reference loops)
		:param unpack_fn: callable input is the instance of packed data and then restores that instance to the original
		state using the packed data by unpacking any values therein.
		:param name: (optional) name of the class used for storing
		:return: A `SavableClassCollisionError` if the name is already registered
		'''
		
		if name is None:
			name = self.full_name(cls)
			
		if pack_fn is None:
			pack_fn = getattr(cls, self._pack_fn_name, None)
		
		if create_fn is None:
			create_fn = getattr(cls, self._create_fn_name, None)
			if create_fn is not None:
				create_fn = create_fn.__func__
		
		if unpack_fn is None:
			unpack_fn = getattr(cls, self._unpack_fn_name, None)
		
		if ancestors is None:
			ancestors = self._find_ancestors(cls)
		ancestors = [(parent if parent in self else self.backward()[parent].name)
		             for parent in ancestors if self.is_known(parent)]
		
		return super().new(name=name, cls=cls, ancestors=ancestors,
		                   pack_fn=pack_fn, create_fn=create_fn, unpack_fn=unpack_fn)
	
	
	def find_nearest(self, name=None, cls=None, ancestors=None):
		if name is not None and name in self:
			return self[name]
		if cls is not None and cls in self.backward():
			return self.backward()[cls]
		
		if ancestors is not None:
			for ancestor in ancestors:
				if ancestor in self:
					return self[ancestor]
		
		raise MissingEntryError(name=name, cls=cls, ancestors=ancestors)
	
	
	def _find_ancestors(self, cls):
		return cls.__mro__[1:]
	
	
	@staticmethod
	def full_name(cls: ClassVar) -> str:
		'''
		Find the full, unique name of a class by connecting it to the module where is is declared.

		:param cls: type
		:return: unique name of the class
		'''
		name = str(cls.__name__)
		module = str(cls.__module__)
		if module is None:
			return name
		return '.'.join([module, name])



registry = Packable_Registry()
register_packable = registry.new

def as_packable(name=None, ancestors=None, pack_fn=None, create_fn=None, unpack_fn=None):
	def _reg_pack(cls):
		register_packable(name=name, cls=cls, ancestors=ancestors,
                pack_fn=pack_fn, create_fn=create_fn, unpack_fn=unpack_fn)
		return cls
	return _reg_pack


for _primitive in primitive:
	register_packable(_primitive, create_fn=lambda _, d, __, ___: d)


# region Mutable

def _pack_dict(d, pack_member):
	return {pack_member(k,force_str=True):pack_member(v) for k,v in d.items()}
def _unpack_dict(d, x, o, unpack_member):
	d.update({unpack_member(k):unpack_member(v) for k, v in x.items()})
register_packable(dict, ancestors=[],
             pack_fn=_pack_dict,
             unpack_fn=_unpack_dict,
)
register_packable(OrderedDict,
             pack_fn=_pack_dict,
             unpack_fn=_unpack_dict,
)

def _pack_list(xs, pack_member):
	return [pack_member(x) for x in xs]
def _unpack_list(ls, xs, o, unpack_member):
	ls.extend(unpack_member(x) for x in xs)
register_packable(list, ancestors=[],
             pack_fn=_pack_list,
             unpack_fn=_unpack_list,
)
register_packable(set, ancestors=[list],
             pack_fn=_pack_list,
             unpack_fn=lambda s, xs, _, unpack_member: s.update(unpack_member(x) for x in xs),
)

# endregion

# region Immutable

register_packable(type, name='class', ancestors=[],
             pack_fn=lambda t, _: registry.backward()[t].name if t in registry.backward() else registry.full_name(t),
             create_fn=lambda _, d, __, ___: registry[d].cls if d in registry else locals().get(d),
                  # TODO check ancestry for nearest
)
register_packable(tuple, ancestors=[list],
             pack_fn=_pack_list,
             create_fn=lambda _, xs, __, unpack_member: tuple(unpack_member(x) for x in xs),
)
register_packable(complex, ancestors=[dict],
             pack_fn=lambda c, pack_member: [pack_member(c.real), pack_member(c.imag)],
             create_fn=lambda _, data, __, unpack_member: complex(unpack_member(data[0]), unpack_member(data[1])),
)
register_packable(range, ancestors=[dict],
             pack_fn=lambda r, pack_member: {'start':pack_member(r.start),
                                             'stop':pack_member(r.stop),
                                             'step':pack_member(r.step)},
             create_fn=lambda _, data, __, unpack_member: range(unpack_member(data['start']),
                                                                unpack_member(data['stop']),
                                                                unpack_member(data['step'])),
)
register_packable(bytes, ancestors=[str],
             pack_fn=lambda b, _: b.decode('8859'),
             create_fn=lambda _, s, __, ___: s.encode('8859'),
)

# endregion


class Packable(object):
	'''
	Any subclass of this mixin can be serialized using `pack`
	
	All subclasses must implement __create__, __pack__, and __unpack__ to register the type. By passing a type to
	`use_cls` the type for which these methods are used can be overridden from the subclass.
	'''
	def __init_subclass__(cls, use_cls: ClassVar = None, name: str = None) -> NoReturn:
		'''
		This method automatically registers any subclass that is declared.
		
		:param use_cls: The class to register (if it is different than `cls`)
		:return: None
		'''
		super().__init_subclass__() # TODO: remove
		
		if use_cls is None:
			use_cls = cls
		
		register_packable(use_cls, name=name)


	def __deepcopy__(self, memodict: Dict[Any,Any] = None) -> Any:
		'''
		Produces a deep copy of the data by packing and repacking.
		
		:param memodict: Unused
		:return: A deep copy of self
		'''
		return unpack(pack(self))
	
	
	@classmethod
	def __create__(cls, data: Dict[str, 'PACKED'], original: str, unpack_member: Callable) -> 'Packable':
		'''
		Create the object without loading the state from data. You can use the data to inform how
		to initialize the object, however no stored objects should be unpacked (to avoid reference loops)
		
		:param data: packed data to restore object state, should NOT be unpacked here
		:return: A fresh instance of the class registered with this create_fn
		'''
		return cls.__new__(cls)
	
	
	def __pack__(self, pack_member: Callable) -> Dict[str,'PACKED']:
		'''
		Collect all data in self necessary to store the state.
		
		.. warning:: All data must be "packed" storing it. This is done by passing the data into
		`Packable._pack_obj` and using what is returned.
		
		:return: A dict of packed data necessary to recover the state of self
		'''
		return {pack_member(k, force_str=True): pack_member(v) for k,v in self.__dict__.items()}
	
	
	def __unpack__(self, data: Dict[str, 'PACKED'], original: str, unpack_member: Callable) -> NoReturn:
		'''
		Using `data`, recover the packed state.
		Must be overridden by all subclasses.
		
		.. warning:: All data must be "unpacked" before using it. This is done by passing the data into
		`Packable._unpack_obj` and using what is returned.
		
		:param data: The information that is returned by `__pack__`.
		:return: Nothing. Once returned, the object should be in the same state as when it was packed
		'''
		self.__dict__.update({unpack_member(k): unpack_member(v) for k, v in data.items()})



PRIMITIVE = Union[primitive]
'''Valid primitives'''
#
# SERIALIZABLE = Union[Packable, PRIMITIVE, Dict['SERIALIZABLE', 'SERIALIZABLE'],
#                      List['SERIALIZABLE'], Set['SERIALIZABLE'], Tuple['SERIALIZABLE']]
# '''Types that can be serialized using `pack`'''
#
# JSONABLE = Union[Dict[str,'JSONABLE'], List['JSONABLE'], PRIMITIVE]
# '''Any object that is valid in json (eg. using `json.dumps`)'''
#
# PACKED = Union[PRIMITIVE, List['PACKED'], Dict['PACKED', 'PACKED']]
# '''Any information that is valid json and can be unpacked to recover the state of `Packable` subclasses.'''



SERIALIZABLE = NewType('SERIALIZABLE', object)
JSONABLE = NewType('JSONABLE', object)
PACKED = NewType('PACKED', object)



class Packer:
	def __init__(self, key_prefix='!', ref_prefix='$'):
		self.key_prefix = key_prefix
		self.ref_prefix = ref_prefix
		self.reset()
		
		
	def reset(self):
		self.ref_table = {}
		self.obj_table = {}
		self.ancestry = {}
		self.corrections = []
	
	
	def make_obj_ref(self, obj: SERIALIZABLE) -> str:
		'''
		Compute the object ID for packing objects, which must be unique and use the reference prefix

		:param obj: object to get the reference for
		:return: unique ID associated with `obj` for packing
		'''
		return f'{self.ref_prefix}{hex(id(obj))[2:]}'
	
	
	def find_nearest(self, name=None, cls=None, ancestors=None):
		return registry.find_nearest(name=name, cls=cls, ancestors=ancestors)
		
	
	def pack_member(self, obj: SERIALIZABLE, force_str: bool = False) -> PACKED:
		'''
		Store the object state by packing it, possibly returning a reference.
		
		This function should be called inside implemented __pack__ on all data in an object necessary to restore
		the object state.
		
		Note: this function should not be called on the top level (use `pack` instead).
		
		:param obj: serializable data that should be packed
		:param force_str: if the data is a key for a dict, set this to true to ensure the key is a str
		:return: packed data
		'''
		if isinstance(obj, primitive):
			if (isinstance(obj, str) and obj.startswith(self.ref_prefix)) or (not isinstance(obj, str) and force_str):
				ref = self.make_obj_ref(obj)
				self.ref_table[ref] = {f'{self.key_prefix}type': self.find_nearest(cls=type(obj)).name,
				                       f'{self.key_prefix}data': obj}
			else:
				return obj
		else:
			ref = self.make_obj_ref(obj)
			typ = type(obj)
	
			if ref in self.ref_table:
				return ref
			data = {}
			self.ref_table[ref] = data  # create entry in refs to stop reference loops
			
			info = self.find_nearest(cls=typ)
			self.ancestry[info.name] = info.ancestors
			data[f'{self.key_prefix}type'] = info.name
			data[f'{self.key_prefix}data'] = self._dispatch_pack(info, obj)
		
		return ref
	
	
	def unpack_member(self, data: PACKED) -> SERIALIZABLE:
		'''
		Restore the object data by unpacking it.
		
		This function should be called inside implemented __unpack__ on all data in an object necessary to restore
		the object state from the packed data.
		
		Note: this function should not be called on the top level (use `unpack` instead).
		
		:param data: packed data that should be unpacked
		:return: unpacked data to restore the state
		'''
	
		if isinstance(data, str) and data.startswith(self.ref_prefix):  # reference or class
			if data in self.obj_table: # known reference
				return self.obj_table[data]
	
			ref = data
			typname = self.ref_table[ref][f'{self.key_prefix}type']
			data = self.ref_table[ref][f'{self.key_prefix}data']
			
			info = self.find_nearest(name=typname, ancestors=self.ancestry.get(typname, None))
			
			obj = self._dispatch_create(info, data, typname)
			
			del self.ref_table[ref]
			self.obj_table[ref] = obj
			
			self._dispatch_unpack(info, obj, data, typname)
			
			if self.corrections is not None and info.name != typname:
				self.corrections.append({'expected': typname, 'used': info.name, 'obj': obj})
			
		else:
			info = self.find_nearest(cls=type(data))
			
			obj = self._dispatch_create(info, data)
			self._dispatch_unpack(info, obj, data)
			
		
		return obj


	def _dispatch_pack(self, entry, obj):
		return obj if entry.pack_fn is None else entry.pack_fn(obj, self.pack_member)
	
	
	def _dispatch_create(self, entry, data, original=None):
		if entry.create_fn is None and entry.unpack_fn is None:
			return entry.cls(data)
		elif entry.create_fn is None:
			return entry.cls()
		return entry.create_fn(entry.cls, data, original, self.unpack_member)
	
	
	def _dispatch_unpack(self, entry, obj, data, original=None):
		if entry.unpack_fn is not None:
			return entry.unpack_fn(obj, data, original, self.unpack_member)

	
	def pack(self, obj: SERIALIZABLE, meta: Dict[str, PACKED] = None, include_timestamp: bool = False) -> JSONABLE:
		'''
		Serializes any object, returning a json object that can be converted to a json string.
		
		:param obj: Object to be serialized
		:param meta: Meta information, must be jsonable
		:param include_timestamp: include a timestamp in the meta information
		:return: packed data, which can be converted to a json string using json.dumps
		'''
		self.reset()
	
		try:
			out = self.pack_member(obj)
	
			# additional meta info
			if meta is None:
				meta = {}
			if include_timestamp:
				meta['timestamp'] = time.strftime('%Y-%m-%d_%H%M%S')
	
			data = {
				'table': self.ref_table,
				'ancestry': self.ancestry,
				'meta': meta,
				'head': out, # save parent object separately
			}
	
		except Exception as e:
			raise e

		return data
	
	
	def unpack(self, data: PACKED, return_meta: bool = False, return_corrections: bool = False,
	           allow_ancestors: bool = True) -> SERIALIZABLE:
		'''
		Deserialize a packed object to recover the original state.
		
		:param data: serialized (packed) state of an object
		:param return_meta: return any meta information from the serialized data
		:return: the unpacked (restored) object
		'''
		self.reset()
		self.ref_table = data.get('table', {})
		self.ancestry = data.get('ancestry', {}) if allow_ancestors else {}
	
		try:
			obj = self.unpack_member(data['head'])
		except Exception as e:
			raise e
	
		out = [obj]
		
		if allow_ancestors and return_corrections:
			out.append(self.corrections)
		if return_meta:
			out.append(data.get('meta', None))
	
		if len(out) > 1:
			return out
		return out[0]



def pack(obj: SERIALIZABLE, meta: Dict[str, PACKED] = None, include_timestamp: bool = False,
         packer: Union[Packer, None] = None) -> JSONABLE:
	if packer is None:
		packer = Packer()
	return packer.pack(obj, meta=meta, include_timestamp=include_timestamp)
	
	
	
def unpack(data: PACKED, return_meta: bool = False, return_corrections: bool = False,
           allow_ancestors: bool = True, packer: Union[Packer, None] = None,
           skip_deepcopy: bool = False) -> SERIALIZABLE:
	if packer is None:
		packer = Packer()
	if not skip_deepcopy:
		data = json.loads(json.dumps(data))
	return packer.unpack(data, return_meta=return_meta, return_corrections=return_corrections)



def save_pack(obj: SERIALIZABLE, fp: Union[TextIO, str, Path], meta: Dict[str, JSONABLE] = None,
              include_timestamp: bool = False) -> NoReturn:
	'''
	Pack (serialize) the object and store it as a json file
	
	:param obj: object to be packed
	:param fp: writable file-like object where the packed object is stored
	:param include_timestamp: include timestamp in meta information
	:return: None
	'''
	if isinstance(fp, (str, Path)):
		fp = open(str(fp), 'w')
	return json.dump(pack(obj, meta=meta, include_timestamp=include_timestamp), fp)



def load_pack(fp: Union[TextIO, str, Path], return_meta: bool = False, return_corrections: bool = False,
                allow_ancestors: bool = True) -> SERIALIZABLE:
	'''
	Loads json file of packed object and unpacks the object
	
	:param fp: writable file-like object
	:param return_meta: return the meta information stored
	:return: unpacked object from json file
	'''
	if isinstance(fp, (str, Path)):
		fp = open(str(fp), 'r')
	return unpack(json.load(fp), return_meta=return_meta, return_corrections=return_corrections,
	              allow_ancestors=allow_ancestors)



def json_pack(obj: SERIALIZABLE, meta: Dict[str, JSONABLE] = None, include_timestamp:bool = False) -> str:
	'''
	Pack object and return a json string of the serialized object
	
	:param obj: to be packed
	:param meta: any meta information to include
	:param include_timestamp: include timestamp in meta information
	:return: json string of the serialized data
	'''
	return json.dumps(pack(obj, meta=meta, include_timestamp=include_timestamp))



def json_unpack(data: str, return_meta: bool = False, return_corrections: bool = False,
                allow_ancestors: bool = True) -> SERIALIZABLE:
	'''
	Unpack json string of a packed object.
	
	:param data: json string of a packed object
	:param return_meta: return meta information
	:return: unpacked object
	'''
	return unpack(json.loads(data), return_meta=return_meta, return_corrections=return_corrections,
	              allow_ancestors=allow_ancestors)



