import json
from collections import OrderedDict, namedtuple


primitive = (str, int, float, bool, type(None))



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




class Registry(OrderedDict):
	
	_pack_fn_name = '__pack__'
	_unpack_fn_name = '__unpack__'
	_create_fn_name = '__create__'
	
	def __init__(self, primary_component='name', sister_component='cls',
	             components=['pack_fn', 'create_fn', 'unpack_fn', 'ancestors'],
	             sister_registry_object=None, sister_registry_cls=None):
		if sister_registry_cls is None:
			sister_registry_cls = self.__class__
		if sister_registry_object is None:
			sister_registry_object = sister_registry_cls(sister_registry_object=self,
			                                             primary_component=sister_component,
			                                             sister_component=primary_component,
			                                             components=components)
		
		super().__init__()
		self._sister_registry_object = sister_registry_object
		
		self._key_name = primary_component
		self._sister_key_name = sister_component
		self._entry_cls = namedtuple(f'{self.__class__.__name__}_Entry',
		                             [primary_component, sister_component] + components)
		
		self._init_sister_registry()
	
	
	def is_known(self, x):
		return x in self or x in self.backward()
	
	
	def backward(self):
		return self._sister_registry_object
	
	
	def _init_sister_registry(self):
		for k, v in self.items():
			self._sister_registry_object.__setitem__(self._get_sister_entry_key(k, v), v, sync=False)
	
	
	def _get_sister_entry_key(self, key, value):
		assert isinstance(value, self._entry_cls)
		if key == getattr(value, self._key_name):
			return getattr(value, self._sister_key_name)
		return getattr(value, self._key_name)
	
	
	def update(self, other, sync=True):
		if sync:
			self._sister_registry_object.update({self._get_sister_entry_key(k, v): v
			                                     for k, v in other.items()}, sync=False)
		return super().update(other)


	def __setitem__(self, key, value, sync=True):
		if sync:
			self._sister_registry_object.__setitem__(self._get_sister_entry_key(key, value), value, sync=False)
		return super().__setitem__(key, value)
	
	
	def __delitem__(self, key, sync=True):
		if sync:
			self._sister_registry_object.__delitem__(self._get_sister_entry_key(key, self[key]), sync=False)
		return super().__delitem__(key)
		
		
	def _old_new(self, name, obj):  # register a new entry
		self[name] = obj
		return obj


	def _old_new2(self, *args, **info):  # register a new entry
		if self._key_name not in info:
			assert len(args) == 1
			info[self._key_name] = args[0]
		assert self._key_name in info, f'Missing key: {self._key_name}'
		return self._old_new(info[self._key_name], self._entry_cls(**info))
	
	
	def is_registered(self, obj):
		for opt in self.values():
			if obj == opt:
				return True
		return False
	
	
	def new(self, cls, name=None, pack_fn=None, create_fn=None, unpack_fn=None, ancestors=None):
		
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
		
		return self._old_new2(name=name, cls=cls, ancestors=ancestors,
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
	def full_name(cls):
		name = str(cls.__name__)
		module = str(cls.__module__)
		if module is None:
			return name
		return '.'.join([module, name])



registry = Registry()
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
             unpack_fn=lambda s, xs, o, unpack_member: s.update(unpack_member(x) for x in xs),
)

# endregion

# region Immutable

class TypeStr(str):
	pass

register_packable(type, name='class', ancestors=[],
             pack_fn=lambda t, _: registry.backward()[t].name if t in registry.backward() else registry.full_name(t),
             create_fn=lambda _, d, __, ___: registry[d].cls if d in registry else TypeStr(d),
                  # TODO check ancestry for nearest
)
register_packable(tuple, ancestors=[list],
             pack_fn=_pack_list,
             create_fn=lambda _, xs, __, ___: tuple(unpack_member(x) for x in xs),
)
register_packable(complex, ancestors=[dict],
             pack_fn=lambda c, _: [pack_member(c.real), pack_member(c.imag)],
             create_fn=lambda _, data, __, ___: complex(unpack_member(data[0]), unpack_member(data[1])),
)
register_packable(range, ancestors=[dict],
             pack_fn=lambda r, _: {'start':pack_member(r.start), 'stop':pack_member(r.stop), 'step':pack_member(r.step)},
             create_fn=lambda _, data, __, ___: range(start=unpack_member(data['start']), stop=unpack_member(data['stop']),
                                          step=unpack_member(data['step'])),
)
register_packable(bytes, ancestors=[str],
             pack_fn=lambda b, _: b.decode(),
             create_fn=lambda _, s, __, ___: s.encode('latin1'),
)

# endregion


class Packable(object):
	
	def __init_subclass__(cls, use_cls = None, name = None):
		super().__init_subclass__()  # TODO: remove
		
		if use_cls is None:
			use_cls = cls
		
		register_packable(use_cls, name=name)
	
	def __deepcopy__(self, memodict = None):
		return unpack(pack(self))
	
	
	@classmethod
	def __create__(cls, data, original, unpack_member):
		return cls.__new__(cls)
	
	
	def __pack__(self, pack_member):
		return {pack_member(k, force_str=True): pack_member(v) for k, v in self.__dict__.items()}
	
	
	def __unpack__(self, data, original, unpack_member):
		self.__dict__.update({unpack_member(k): unpack_member(v) for k, v in data.items()})


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
	
	def make_obj_ref(self, obj):
		return f'{self.ref_prefix}{hex(id(obj))[2:]}'
	
	def find_nearest(self, name=None, cls=None, ancestors=None):
		return registry.find_nearest(name=name, cls=cls, ancestors=ancestors)
	
	def pack_member(self, obj, force_str = False):
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
	
	def unpack_member(self, data):
		
		if isinstance(data, str) and data.startswith(self.ref_prefix):  # reference or class
			if data in self.obj_table:  # known reference
				return self.obj_table[data]
			
			ref = data
			typname = self.ref_table[ref][f'{self.key_prefix}type']
			data = self.ref_table[ref][f'{self.key_prefix}data']
			
			info = self.find_nearest(name=typname, ancestors=self.ancestry.get(typname, None))
			
			obj = self._dispatch_create(info, data)
			
			del self.ref_table[ref]
			self.obj_table[ref] = obj
			
			self._dispatch_unpack(info, obj, data)
			
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
	
	def pack(self, obj, meta = None, include_timestamp = False):
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
				'head': out,  # save parent object separately
			}
		
		except Exception as e:
			raise e
		
		return data
	
	def unpack(self, data, return_meta = False, return_corrections = False, allow_ancestors = True):
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



def pack(obj, meta=None, include_timestamp=False, packer=None):
	if packer is None:
		packer = Packer()
	return packer.pack(obj, meta=meta, include_timestamp=include_timestamp)



def unpack(data, return_meta=False, return_corrections=False,
           allow_ancestors=True, packer=None, skip_deepcopy=False):
	if packer is None:
		packer = Packer()
	if not skip_deepcopy:
		data = json.loads(json.dumps(data))
	return packer.unpack(data, return_meta=return_meta, return_corrections=return_corrections)


def json_pack(obj, meta=None, include_timestamp=False):
	return json.dumps(pack(obj, meta=meta, include_timestamp=include_timestamp))


def json_unpack(data, return_meta=False, return_corrections=False, allow_ancestors=True):
	return unpack(json.loads(data), return_meta=return_meta, return_corrections=return_corrections,
	              allow_ancestors=allow_ancestors)



	
