from typing import Tuple, List, Dict, Optional, Union, Any, Callable, Sequence, Iterator, Iterable, Type, Set

# from .abstract import


class AbstractCrafty:
	pass



class AbstractCraft:
	def emit_craft_items(self, obj: AbstractCrafty):
		yield self


########################################################################################################################


class CraftyBase(AbstractCrafty):
	def __init__(self, owner: Type[AbstractCrafty] = None, *, crafts: Iterable[AbstractCraft] = None, **kwargs):
		if crafts is None:
			crafts = list(self._extract_craft_items(owner))
		super().__init__(**kwargs)
		self._crafts = crafts

	
	pass


########################################################################################################################


class CraftBase(AbstractCraft):
	pass
	

























