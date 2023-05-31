from typing import Tuple, List, Dict, Optional, Union, Any, Callable, Sequence, Iterator, Iterable, Type, Set


# from .abstract import
from .typing import agnostic


class AbstractCrafty:
	@classmethod
	def _emit_my_craft_items(cls, owner=None) -> Iterator[Tuple[str, 'AbstractCraft']]: # N-O
		if owner is None:
			owner = cls
		for key, val in reversed(cls.__dict__.items()): # N-O
			if isinstance(val, AbstractCraft):
				for craft in val.emit_craft_items(owner): # N-O
					yield key, craft



class AbstractSkill:
	def as_skill(self, owner: AbstractCrafty):
		return self



class AbstractCraft(AbstractSkill):
	def emit_craft_items(self, owner=None):
		yield self # stateless



class SkilledCraft(AbstractCraft):
	class Skill(AbstractSkill):
		def __init__(self, base: AbstractCraft, instance: AbstractCrafty, **kwargs):
			super().__init__(**kwargs)
			self._base = base
			self._instance = instance


	def as_skill(self, owner: AbstractCrafty):
		return self.Skill(self, owner) # stateful



class NestableCraft(AbstractCraft):
	def emit_craft_items(self, owner=None): # parsing order (N-O)
		yield from super().emit_craft_items(owner)
		content = self._wrapped_content()
		if isinstance(content, AbstractCraft):
			yield from content.emit_craft_items(owner)


	def _wrapped_content_leaf(self): # wrapped method
		wrapped = self._wrapped_content()
		return wrapped._wrapped_content_leaf() if isinstance(wrapped, NestableCraft) else wrapped


	def _wrapped_content(self): # wrapped method
		raise NotImplementedError



########################################################################################################################


class InheritableCrafty(AbstractCrafty):
	@agnostic
	def _emit_all_craft_items(self, *, remaining: Iterator[Type['InheritableCrafty']] = None,
	                          start : Type['InheritableCrafty'] = None, owner : Type['InheritableCrafty'] = None,
	                          **kwargs) -> Iterator[Tuple[Type[AbstractCrafty], str, AbstractCraft]]: # N-O
		cls = self if isinstance(self, type) else type(self)
		if remaining is None:
			remaining = iter(cls.mro()) # N-O
		if start is None:
			start = cls
		if owner is None:
			owner = self

		for current in remaining: # N-O
			if issubclass(current, AbstractCrafty):
				for key, craft in current._emit_my_craft_items(owner):
					yield current, key, craft
			if issubclass(current, InheritableCrafty):
				yield from current._emit_all_craft_items(remaining=remaining, start=start, owner=owner, **kwargs)



class ProcessedCrafty(InheritableCrafty):
	def _process_crafts(self):
		pass



class IndividualCrafty(ProcessedCrafty):
	def _process_crafts(self):
		for owner, key, craft in self._emit_all_craft_items():
			self._process_skill(owner, key, craft, craft.as_skill(self))


	def _process_skill(self, src: Type[AbstractCrafty], key: str, craft: AbstractCraft, skill: AbstractSkill):
		pass



class HiddenCrafty(AbstractCrafty):
	_hidden_crafts = None
	def __init_subclass__(cls, **kwargs):
		super().__init_subclass__(**kwargs)
		cls._hidden_crafts = []


	@classmethod
	def _emit_my_craft_items(cls, owner=None) -> Iterator[Tuple[str, 'AbstractCraft']]: # N-O
		yield from super()._emit_my_craft_items(owner)
		if cls._hidden_crafts is not None:
			yield from cls._hidden_crafts




########################################################################################################################





















