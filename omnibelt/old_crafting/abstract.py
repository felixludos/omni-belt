from typing import Tuple, List, Dict, Optional, Union, Any, Callable, Sequence, Iterator, Iterable, Type, Set
from ..propagators import method_propagator
from ..operators import AbstractOperational, AbstractOperator, SimpleOperational



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



class AbstractCraftOperator(AbstractOperator):
	pass



class AbstractCraft(SimpleOperational):
	Operator = AbstractCraftOperator

	@classmethod
	def package(cls, manager: 'AbstractCrafts', owner: Type[AbstractCrafty], key: str,
	            raw: AbstractRawCraft) -> 'AbstractCraft':
		raise NotImplementedError


	def crafting(self, instance: 'AbstractCrafty') -> 'AbstractCraftOperator':
		return self._create_operator(instance, type(instance))


	def merge(self, others: Iterable['AbstractCraft']) -> 'AbstractCraft':
		raise NotImplementedError



class AbstractCraftsOperator(AbstractOperator):
	def crafts(self) -> Iterator[AbstractCraftOperator]:
		raise NotImplementedError



class AbstractCrafts(SimpleOperational):
	Operator = AbstractCraftsOperator

	def crafts(self) -> Iterator[AbstractCraft]:
		raise NotImplementedError


	def crafting(self, instance: 'AbstractCrafty') -> 'AbstractCraftsOperator':
		return self._create_operator(instance, type(instance))


	@classmethod
	def process_raw_crafts(cls, owner: Type['AbstractCrafty']) -> 'AbstractCrafts': # custom constructor
		raise NotImplementedError















