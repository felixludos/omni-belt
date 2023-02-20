from typing import Tuple, List, Dict, Optional, Union, Any, Callable, Sequence, Iterator, Iterable, Type, Set
from functools import cached_property
import inspect
from omnibelt import method_propagator, OrderedSet, isiterable

from .abstract import AbstractCrafty, AbstractCrafts



class BasicCrafty(AbstractCrafty): # contains crafts (and craft sources when instantiated)
	_Crafts = None # router for crafts
	_processed_crafts = None

	@classmethod
	def _process_raw_crafts(cls):
		if '_processed_crafts' not in cls.__dict__:
			cls._processed_crafts = None if cls._Crafts is None else cls._Crafts.process_crafts(cls)



class InitializationCrafty(BasicCrafty): # Not needed because of "Operational"
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._initialize_crafts()


	def _initialize_crafts(self):
		crafts = inspect.getattr_static(self, '_processed_crafts', None)
		if crafts is not None and isinstance(crafts, AbstractCrafts):
			self._processed_crafts = crafts.crafting(self)



# TODO: crafty where crafts can be added after declaration/inheritance -> LiveCrafty


# class LiveCrafty(Crafty): # also cosolidates at instantiation (in case some crafts are added after class creation)
# 	def _process_known_crafts(self, craft_items: Optional[List['Crafts']] = None): # full consolidation
# 		if craft_items is None:
# 			craft_items = self._known_crafts
#
# 		tools = []
#
# 		while craft_items:
# 			craft = craft_items.pop()
#
# 			if isinstance(craft, ConsolidationCrafts):
# 				related = []
# 				remaining = []
# 				for item in craft_items:
# 					if craft.consolidate(item):
# 						related.append(item)
# 					else:
# 						remaining.append(item)
#
#
# 			if isinstance(craft, ConsolidationCrafts):
# 				craft_items.extend(craft.consolidate_craft_items(self, tools, craft_items))
# 			tools, craft_items = craft.consolidate_craft_items(self, tools, craft_items)
#
# 		return list(reversed(tools))



