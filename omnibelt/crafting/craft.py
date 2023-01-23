from typing import Tuple, List, Dict, Optional, Union, Any, Callable, Sequence, Iterator, Iterable, Type, Set
from functools import cached_property
from .. import method_propagator, method_decorator, OrderedSet, isiterable

from .abstract import AbstractCrafty, AbstractCraft, AbstractCrafts, AbstractRawCraft, AbstractCraftOperator



class BasicRawCraft(AbstractRawCraft): # decorator
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._filter_callable_arg()


	_common_content_types = (method_propagator, cached_property, method_decorator, property, staticmethod, classmethod)

	def _filter_callable_arg(self):
		args = self._args
		if len(args):
			first = args[0]
			if callable(first) or isinstance(first, self._common_content_types):
				self._args = args[1:]
				self._fn = first


	_CraftItem: AbstractCraft = None # must not be a subclass of SelfCrafting!

	def package_craft_item(self, manager: 'AbstractCrafts', owner: Type[AbstractCrafty], key: str):
		return self._CraftItem._package_payload(manager, owner, key, self)


	def nested_craft_items(self) -> Iterator['AbstractRawCraft']:
		if isinstance(self._fn, AbstractRawCraft):
			yield self._fn
			yield from self._fn.nested_craft_items()
			self._fn = self._fn._fn  # IMPORTANT: unnest content!


class SignatureRawCraft(AbstractRawCraft): # the only part of the decorator that matters is the signature
	def extract_craft_data(self):
		return {'name': self._name, 'fn': self._fn, 'type': type(self).__name__,
		        'method': self._method_name, 'args': self._args, 'kwargs': self._kwargs}



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



class SignatureCraft(BasicCraft):
	def __init__(self, manager: 'AbstractCrafts', owner: Type[AbstractCrafty], key: str,
	             raw: SignatureRawCraft, **kwargs):
		super().__init__(manager, owner, key, raw, **kwargs)
		self._data = raw.extract_craft_data()



class AwareCraft(BasicCraft): # (making RawCraft master) - not used -> Craft is master, not RawCraft
	@property
	def static_content(self) -> Optional[Callable]:
		return getattr(self._raw, '_fn', None)



class WrappedCraft(AwareCraft):
	def __init__(self, manager: 'AbstractCrafts', owner: Type[AbstractCrafty], key: str,
	             raw: AbstractRawCraft, **kwargs):
		setattr(raw, '_fn', self._wrap_craft_fn(owner, raw, getattr(raw, '_fn', None)))
		super().__init__(manager, owner, key, raw, **kwargs)


	@staticmethod
	def _wrap_craft_fn(owner: Type[AbstractCrafty], raw: AbstractRawCraft, fn: Optional[Callable] = None) -> Callable:
		return fn



class PropertyCraft(WrappedCraft):
	_property_type = cached_property

	@classmethod
	def _wrap_craft_fn(cls, owner: Type[AbstractCrafty], raw: AbstractRawCraft,
	                   fn: Optional[Callable] = None) -> Callable:
		fn = super()._wrap_craft_fn(owner, raw, fn)
		if fn is not None:
			return cls._property_type(fn)



########################################################################################################################



# class CraftOperator(AbstractCraftOperator): # when instantiating a "Crafty", Crafts are instantiated as CraftSources
# 	def __init__(self, base: AbstractCraft, instance: 'AbstractCrafty', **kwargs):
# 		super().__init__(**kwargs)


