from typing import Tuple, List, Dict, Optional, Union, Any, Callable, Sequence, Iterator, Iterable, Type, Set
from ..propagators import method_propagator
from ..operators import AbstractOperational, AbstractOperator



class AbstractCrafty: # owner of crafts
	def __init_subclass__(cls, **kwargs):
		super().__init_subclass__(**kwargs)
		cls._process_raw_crafts()


	@classmethod
	def _process_raw_crafts(cls):
		pass



class AbstractRawCraft(method_propagator): # decorator wrapping a property/method - aka craft-item
	def package_craft_item(self, manager: 'AbstractCrafts', owner: Type[AbstractCrafty], key: str) -> 'AbstractCraft':
		raise NotImplementedError


	def nested_craft_items(self) -> Iterator['AbstractRawCraft']:
		raise NotImplementedError



class AbstractCraft(AbstractOperational):
	@classmethod
	def package(cls, manager: 'AbstractCrafts', owner: Type[AbstractCrafty], key: str,
	            raw: AbstractRawCraft) -> 'AbstractCraft':
		raise NotImplementedError


	def merge(self, gizmo: str, others: Iterable['AbstractCraft']) -> 'AbstractCraft':
		raise NotImplementedError



class AbstractCrafts(AbstractOperational):
	def crafts(self) -> Iterator[AbstractCraft]:
		raise NotImplementedError


	def crafting(self, instance: 'AbstractCrafty') -> Iterator['AbstractCraftOperator']:
		raise NotImplementedError


	@classmethod
	def process_raw_crafts(cls, owner: Type['AbstractCrafty']) -> 'AbstractCrafts': # custom constructor
		raise NotImplementedError



class AbstractCraftsOperator(AbstractOperator):
	pass



class AbstractCraftOperator(AbstractOperator):
	pass












