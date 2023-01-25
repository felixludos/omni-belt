from typing import Tuple, List, Dict, Optional, Union, Any, Callable, Sequence, Iterator, Iterable, Type, Set
from functools import cached_property

from .abstract import AbstractCrafty, AbstractCrafts, AbstractRawCraft, AbstractCraft
from .crafty import BasicCrafty
from .craft import AwareCraft



class ProcessedCrafts(AbstractCrafts): # container for crafts
	CraftLike = AbstractRawCraft

	@classmethod
	def process_crafts(cls, owner: Type[AbstractCrafty]) -> 'ProcessedCrafts':
		return cls(owner)


	def _extract_craft_items(self, owner: Type[AbstractCrafty]) -> Iterator[AbstractCraft]:
		for key, val in owner.__dict__.items(): # O-N
			if isinstance(val, self.CraftLike):
				yield from self._process_craft_item(owner, key, val) # parsing order


	def _process_craft_item(self, owner: Type[AbstractCrafty], key: str,
	                        raw: AbstractRawCraft) -> Iterator[AbstractCraft]:
		for craft in [raw, *raw.nested_craft_items()]: # parsing order
			# IMPORTANT: call nested_craft_items before any package_craft_items
			yield craft.package_craft_item(self, owner, key)


	def __init__(self, owner: Type[AbstractCrafty] = None, *, crafts: Iterable[AbstractCraft] = None, **kwargs):
		if crafts is None:
			crafts = list(self._extract_craft_items(owner))
		super().__init__(**kwargs)
		self._crafts = crafts


	def crafts(self) -> Iterator[AbstractCraft]:
		yield from self._crafts


	class Operator(AbstractCrafts.Operator):
		def __init__(self, base: 'ProcessedCrafts', instance: Any, *, crafts: List[AbstractCraft] = None, **kwargs):
			if crafts is None:
				crafts = []
			super().__init__(base, instance, **kwargs)
			self._crafts = crafts


		def crafts(self) -> Iterator[AbstractCraft]:
			yield from self._crafts


	def _create_operator(self, instance, owner, *, crafts=None, **kwargs):
		if crafts is None:
			crafts = [craft.crafting(instance) for craft in self.crafts()]
		return super()._create_operator(instance, owner, crafts=crafts, **kwargs)



class SeamlessCrafts(ProcessedCrafts):
	def _extract_craft_items(self, owner: Type[AbstractCrafty]) -> Iterator[AbstractCraft]:
		fixes = {}
		for key, val in owner.__dict__.items(): # O-N
			if isinstance(val, self.CraftLike):
				items = self._process_craft_item(owner, key, val) # parsing order
				first = next(items)
				if isinstance(first, AwareCraft):
					content = first.static_content
					if content is None:
						fixes[key] = first
					else:
						first.add_top_level_key(key)
						fixes[key] = content

				yield first
				yield from items

		for key, val in fixes.items():
			setattr(owner, key, val)



class ItemCrafts(ProcessedCrafts):
	CraftItem: AbstractCraft = None

	def _process_craft_item(self, owner: Type[AbstractCrafty], key: str, raw: AbstractRawCraft) -> AbstractCraft:
		if self.CraftItem is None:
			yield from super()._process_craft_item(owner, key, raw)
		else:
			for craft in [raw, *raw.nested_craft_items()]:  # parsing order
				# IMPORTANT: call nested_craft_items before any package_craft_items
				yield self.CraftItem.package(self, owner, key, craft)



class InheritableCrafts(ProcessedCrafts):
	def __init__(self, owner: Type[BasicCrafty] = None, raw: Iterator[AbstractRawCraft] = None, *,
	             crafts: Iterable[AbstractCraft] = None, **kwargs):
		super().__init__(owner, raw, crafts=crafts, **kwargs)
		if owner is not None:
			self._inherit_crafts(owner)


	def _inherit_crafts(self, owner: Type[BasicCrafty]) -> 'InheritableCrafts':
		bases = [getattr(base, '_processed_crafts', None) for base in owner.__bases__] # N-O
		bases = [base for base in bases if base is not None]
		if bases:
			self.update(*bases) # N-O


	def update(self, *others: AbstractCrafts) -> 'InheritableCrafts': # O-N(O-N)
		raise NotImplementedError



class SeamlessInheritableCrafts(InheritableCrafts, SeamlessCrafts):
	def _inherit_crafts(self, owner: Type[BasicCrafty]) -> 'InheritableCrafts':
		super()._inherit_crafts(owner)
		self._inherit_top_level_crafts(owner)


	def _inherit_top_level_crafts(self, owner: Type[BasicCrafty]) -> None:
		for craft in self.crafts():
			if isinstance(craft, AwareCraft):
				for key in craft.top_level_keys():
					if key is not None:
						if getattr(owner, key, None) is not craft:
							setattr(owner, key, craft) # replace old craft with current one




########################################################################################################################





# class SignatureCrafts(InheritableCrafts):
# 	def __init__(self, owner: Type[AbstractCrafty], crafts: List[AbstractRawCraft] = None, **kwargs):
# 		super().__init__(**kwargs)
# 		self._owner = owner
# 		self._gizmos = {} if crafts is None else self._extract_gizmos(crafts)
#
#
# 	def gizmos(self) -> Iterator[str]:
# 		yield from self._gizmos.keys()
#
#
# 	def _package_raw_crafts(self, crafts: Iterable[AbstractRawCraft]) -> Iterator[Dict[str, Any]]:
# 		for base in crafts:
# 			yield {'args': base._args, 'kwargs': base._kwargs, 'name': base._method_name, 'type': type(base).__name__,
# 			       'fn': base._name if base._fn is not None else None, }
#
#
# 	def _extract_gizmos(self, crafts: List[AbstractRawCraft]):
# 		gizmos = {}
#
# 		for info in self._package_raw_crafts(crafts):
# 			name = info.get('name')
# 			targets = info['args']
# 			targets = tuple(tuple(target) if isiterable(target) else (target,) for target in targets)
#
# 			context = info.copy()
# 			if len(targets) > 1:
# 				context['signature'] = targets
#
# 			for target in targets:
# 				spec = context.copy()
# 				if len(target) > 1:
# 					spec['aliases'] = target
#
# 				for gizmo in target:
# 					gizmos.setdefault(gizmo, {})[name] = spec.copy()
#
# 		return gizmos
#
#
# 	def gizmo_info(self, gizmo: str, default: Optional[Any] = None):
# 		return self._gizmos.get(gizmo, default)
#
#
# 	def _merge_gizmo(self, current, old):
# 		current.update(old)
# 		return current
#
#
# 	def merge_crafts(self, *others: 'SignatureCrafts') -> 'SignatureCrafts':
# 		gizmos = self._gizmos
#
# 		for other in others:
# 			for gizmo in other.gizmos():
# 				if gizmo in gizmos:
# 					gizmos[gizmo] = self._merge_gizmo(gizmos[gizmo], other.gizmo_info(gizmo))
#
# 		return self


########################################################################################################################


# class SimpleCrafts(AbstractCrafts):
# 	Tool = CraftOperator
#
# 	def crafting(self, instance: AbstractCrafty):
# 		return self.Tool(instance, self)
#
#
#
# class CustomCrafts(SimpleCrafts): # TODO: add support for custom craft initialization
# 	pass


########################################################################################################################



# class SeamlessCrafts(BasicCrafts):  # can be updated with craft items or other crafts
# 	@classmethod
# 	def process_raw_crafts(cls, owner: Type[AbstractCrafty]) -> AbstractCrafts:
# 		crafts = super().process_raw_crafts(owner)
# 		crafts._cleanup_owner(owner)
# 		return crafts
#
#
# 	def _cleanup_owner(self, owner: Type[AbstractCrafty]):
# 		for key, val in owner.__dict__.items():
# 			if isinstance(val, self.CraftTrigger) and val._fn is not None:
# 				setattr(owner, key, val._fn)


# class WrappingCraft(BasicCrafts):
# 	@classmethod
# 	def _process_craft_fn(cls, owner: Type[AbstractCrafty], craft: AbstractRawCraft) -> Callable:
# 		fn = super()._process_craft_item(owner, craft)
# 		if fn is not None:
# 			return cls._wrap_craft_fn(craft, fn)
#
#
# 	@classmethod
# 	def _wrap_craft_fn(cls, craft: AbstractRawCraft, fn: Callable) -> Callable:
# 		wrappers = cls._get_craft_wrappers()
# 		if craft._method_name in wrappers:
# 			return wrappers[craft._method_name](fn)
# 		return fn
#
#
# 	@staticmethod
# 	def _get_craft_wrappers():
# 		return {}



# class PropertyCraft(WrappingCraft):
# 	_craft_property_type = cached_property
#
#
# 	@staticmethod
# 	def _get_craft_properties() -> Set[str]:
# 		return set()
#
#
# 	@classmethod
# 	def _get_craft_wrappers(cls):
# 		wrappers = super()._get_craft_wrappers()
# 		wrappers.update({k: cls._craft_property_type for k in cls._get_craft_properties()})
# 		return wrappers
#
#
#
# class SpacedCraft(PropertyCraft):
# 	@staticmethod
# 	def _get_craft_properties() -> Set[str]:
# 		return {'space', *super()._get_craft_properties()}





