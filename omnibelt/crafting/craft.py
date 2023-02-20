from typing import Tuple, List, Dict, Optional, Union, Any, Callable, Sequence, Iterator, Iterable, Type, Set
from functools import cached_property
from .. import method_propagator, method_decorator, OrderedSet, isiterable
import inspect


from .abstract import AbstractCrafty, AbstractCraft, AbstractCrafts, AbstractRawCraft, AbstractCraftOperator



class BasicRawCraft(AbstractRawCraft): # decorator
	_CraftItem: AbstractCraft = None # must not be a subclass of SelfCrafting!

	def package_craft_item(self, manager: 'AbstractCrafts', owner: Type[AbstractCrafty], key: str):
		return self._CraftItem.package(manager, owner, key, self)


	def nested_craft_items(self) -> Iterator['AbstractRawCraft']:
		if isinstance(self._fn, AbstractRawCraft):
			yield self._fn
			yield from self._fn.nested_craft_items()
			self._fn = self._fn._fn  # IMPORTANT: unnest content!



class SignatureRawCraft(AbstractRawCraft): # the only part of the decorator that matters is the signature
	def extract_craft_data(self):
		return {'name': self._name, 'fn': self._fn, 'type': type(self),
		        'method': self._method_name, 'args': self._args, 'kwargs': self._kwargs}



class RawCraftItem(SignatureRawCraft, BasicRawCraft): # decorator
	pass


########################################################################################################################

# generally these are descriptors -> e.g. Operators


class BasicCraft(AbstractCraft): # Craft is master
	@classmethod
	def package(cls, manager: 'AbstractCrafts', owner: Type[AbstractCrafty], key: str, raw: AbstractRawCraft):
		return cls(manager, owner, key, raw)


	def __init__(self, manager: 'AbstractCrafts', owner: Type[AbstractCrafty], key: str,
	             raw: AbstractRawCraft, **kwargs):
		super().__init__(**kwargs)
		self._raw = raw



class SignatureCraft(BasicCraft): # the only part of the decorator that matters is the signature
	def __init__(self, manager: 'AbstractCrafts', owner: Type[AbstractCrafty], key: str,
	             raw: SignatureRawCraft, data=None, **kwargs):
		if data is None:
			data = raw.extract_craft_data()
		super().__init__(manager, owner, key, raw, **kwargs)
		self._data = data



class AwareCraft(BasicCraft): # (making RawCraft master) - not used -> Craft is master, not RawCraft
	def __init__(self, manager: 'AbstractCrafts', owner: Type[AbstractCrafty], key: str,
	             raw: AbstractRawCraft, *, top_keys=None, **kwargs):
		if top_keys is None:
			top_keys = OrderedSet()
		super().__init__(manager, owner, key, raw, **kwargs)
		self._top_keys = top_keys


	def remove_seams(self, owner: Type[AbstractCrafty], key: str):
		content = getattr(self._raw, '_fn', None)
		if content is None:
			self.add_top_level_key(key)
			setattr(owner, key, self)
		else:
			setattr(owner, key, content)


	def top_level_keys(self):
		yield from self._top_keys
	def add_top_level_key(self, key):
		self._top_keys.add(key)
	def update_top_level_keys(self, keys):
		self._top_keys.update(keys)


	# @property
	# def static_content(self) -> Optional[Callable]:
	# 	return getattr(self._raw, '_fn', None)


	def crafting(self, instance: 'AbstractCrafty') -> 'AbstractCraftOperator':
		obj = None
		for key in self.top_level_keys():
			value = inspect.getattr_static(instance, key, None)
			if isinstance(value, self.Operator):
				obj = value
				break
		if obj is None:
			obj = super().crafting(instance)
		for key in self.top_level_keys():
			setattr(instance, key, obj) # maybe check that important stuff isnt getting replaced here
		return obj



class WrappedCraft(AwareCraft): # NOTE: only the top of nested decorations is wrapped
	def remove_seams(self, owner: Type[AbstractCrafty], key: str):
		setattr(self._raw, '_fn', self._wrap_craft_fn(owner, self._raw, getattr(self._raw, '_fn', None)))
		super().remove_seams(owner, key)


	@staticmethod
	def _wrap_craft_fn(owner: Type[AbstractCrafty], raw: AbstractRawCraft, fn: Optional[Callable] = None) -> Callable:
		return fn



class PropertyCraft(WrappedCraft):
	_property_type = property

	def _wrap_craft_fn(self, owner: Type[AbstractCrafty], raw: AbstractRawCraft,
	                   fn: Optional[Callable] = None) -> Callable:
		if fn is not None and not isinstance(fn, (property, cached_property)):
			return self._property_type(super()._wrap_craft_fn(owner, raw, fn=fn))




########################################################################################################################

# class PropertyCraft(WrappedCraft):
# 	_property_type = None # cached_property
#
# 	@classmethod
# 	def _wrap_craft_fn(cls, owner: Type[AbstractCrafty], raw: AbstractRawCraft,
# 	                   fn: Optional[Callable] = None) -> Callable:
# 		fn = super()._wrap_craft_fn(owner, raw, fn)
# 		if fn is not None:
# 			return cls._property_type(fn)




# class CraftOperator(AbstractCraftOperator): # when instantiating a "Crafty", Crafts are instantiated as CraftSources
# 	def __init__(self, base: AbstractCraft, instance: 'AbstractCrafty', **kwargs):
# 		super().__init__(**kwargs)

