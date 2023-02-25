from typing import Tuple, List, Dict, Optional, Union, Any, Callable, Sequence, Iterator, Iterable, Type, Set


# from .abstract import


class AbstractCrafty:
	@classmethod
	def _emit_my_craft_items(cls) -> Iterator[Tuple[str, 'AbstractCraft']]: # N-O
		for key, val in reversed(cls.__dict__.items()): # N-O
			if isinstance(val, AbstractCraft):
				for craft in val.emit_craft_items(): # N-O
					yield key, craft


class AbstractSkill:
	def as_skill(self, owner: AbstractCrafty):
		return self



class AbstractCraft(AbstractSkill):
	def emit_craft_items(self):
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
	def emit_craft_items(self): # parsing order (N-O)
		yield from super().emit_craft_items()
		if isinstance(self.wrapped, AbstractCraft):
			yield self.wrapped.emit_craft_items()


	@property
	def content(self): # wrapped method
		if isinstance(self.wrapped, NestableCraft):
			return self.wrapped.content


	@property
	def wrapped(self): # wrapped method
		raise NotImplementedError



########################################################################################################################


class InheritableCrafty(AbstractCrafty):
	@classmethod
	def _emit_all_craft_items(cls, *, remaining: Iterator[Type['InheritableCrafty']] = None,
	                          ) -> Iterator[Tuple[Type[AbstractCrafty], str, AbstractCraft]]: # N-O
		if remaining is None:
			remaining = iter(cls.mro()) # N-O

		for current in remaining: # N-O
			if issubclass(current, AbstractCrafty):
				for key, craft in current._emit_my_craft_items():
					yield current, key, craft
			if issubclass(current, InheritableCrafty):
				yield from current._emit_all_craft_items(remaining=remaining)



class ProcessedCrafty(InheritableCrafty):
	def _process_crafts(self):
		pass



class IndividualCrafty(ProcessedCrafty):
	def _process_crafts(self):
		for owner, key, craft in self._emit_all_craft_items():
			self._process_skill(craft.as_skill(self))


	def _process_skill(self, skill: AbstractSkill):
		pass


########################################################################################################################





















