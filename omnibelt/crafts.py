from typing import Tuple, List, Dict, Optional, Union, Any, Callable, Sequence, Iterator, Iterable, Type, Set


# from .abstract import


class AbstractCrafty:
	@classmethod
	def _emit_my_crafts(cls, instance: 'AbstractCrafty'): # N-O
		for key, val in reversed(cls.__dict__.items()): # N-O
			if isinstance(val, AbstractCraft):
				yield from val.emit_craft_items(instance) # N-O



class InheritableCrafty(AbstractCrafty):
	@classmethod
	def _emit_all_crafts(cls, instance: 'AbstractCrafty', *,
	                           remaining: Iterator[Type['InheritableCrafty']] = None): # N-O
		if remaining is None:
			remaining = iter(cls.mro()) # N-O

		for current in remaining: # N-O
			if issubclass(current, AbstractCrafty):
				yield from current._emit_my_crafts(instance)
			if issubclass(current, InheritableCrafty):
				yield from current._emit_all_crafts(instance, remaining=remaining)



class AbstractCraft:
	def emit_craft_items(self, instance: AbstractCrafty):
		yield self # stateless



class OperationalCraft(AbstractCraft):
	class Operator:
		def __init__(self, base: AbstractCraft, instance: AbstractCrafty, **kwargs):
			super().__init__(**kwargs)
			self._base = base
			self._instance = instance


	def emit_craft_items(self, instance: AbstractCrafty):
		yield self.Operator(self, instance) # stateful



class NestableCraft(AbstractCraft):
	def emit_craft_items(self, instance: AbstractCrafty): # parsing order (N-O)
		yield from super().emit_craft_items(instance)
		if isinstance(self.wrapped, AbstractCraft):
			yield self.wrapped.emit_craft_items(instance)


	@property
	def content(self): # wrapped method
		if isinstance(self.wrapped, NestableCraft):
			return self.wrapped.content


	@property
	def wrapped(self): # wrapped method
		raise NotImplementedError



########################################################################################################################


class ProcessedCrafty(InheritableCrafty):
	def __init__(self, *args, process_crafts=True, **kwargs):
		super().__init__(*args, **kwargs)
		if process_crafts:
			self._process_all_crafts()


	def _process_all_crafts(self):
		pass



class ProcessedIndividualCrafty(ProcessedCrafty):
	def _process_all_crafts(self):
		for craft in self._emit_all_crafts():
			self._process_craft(craft)


	def _process_craft(self, craft: AbstractCraft):
		pass


########################################################################################################################





















