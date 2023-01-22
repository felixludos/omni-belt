from typing import Type, Optional, Union, Any, Callable, Sequence, Iterable, Iterator, Tuple, List, Dict, NamedTuple
from collections import OrderedDict
from functools import cached_property

from .tricks import method_decorator, nested_method_decorator
from .typing import agnostic



class method_propagator(nested_method_decorator):
	def __init__(self, *args, **kwargs):
		super().__init__()
		self._method_name = None
		self._args = args
		self._kwargs = kwargs


	def _setup(self, owner: Type, name: str) -> None:
		super()._setup(owner, name)
		self._name = name


	def _make_propagator(self, name, **kwargs):
		return self._propagator_reference(self, name, **kwargs)


	_propagation_type = None
	class _propagator_reference:
		def __init__(self, originator, name, *, propagation_type=None, **kwargs):
			if propagation_type is None:
				propagation_type = originator._propagation_type
			super().__init__(**kwargs)
			self.name = name
			self._propagator_type = propagation_type


		def __call__(self, *args, **kwargs):
			sub = self._propagator_type(*args, **kwargs)
			sub._method_name = self.name
			return sub



class propagated_method_propagator(method_propagator):
	pass
method_propagator._propagation_type = propagated_method_propagator



class universal_propagator(method_propagator):
	def __getattribute__(self, item):
		try:
			return super().__getattribute__(item)
		except AttributeError:
			return self._make_propagator(item)



class AbstractCollectorTrigger:
	@classmethod
	def process_collectors(cls, owner: Type['Collectable']):
		for key, val in owner.__dict__.items():
			if isinstance(val, method_propagator):
				setattr(owner, key, cls(owner, val))


	def __init__(self, owner: Type['Collectable'], base: method_propagator, **kwargs):
		super().__init__(**kwargs)



# class Collectable:
# 	def __init_subclass__(cls, collector_trigger: Optional[AbstractCollectorTrigger] = None, **kwargs):
# 		super().__init_subclass__(**kwargs)
# 		if collector_trigger is not None:
# 			collector_trigger.process_collectors(cls)
#
# 	def __init__(self, *args, collector_type=None, **kwargs):
# 		if collector_type is not None:
# 			collector_type.process_collectors(self)
# 		super().__init__(*args, **kwargs)



class AbstractCollector:
	@classmethod
	def process_triggers(cls, source: Any, *,
	                     triggers: Optional[Iterator[Tuple[str, AbstractCollectorTrigger]]] = None):
		if triggers is None:
			triggers = ((name, trigger) for name, trigger in type(source).__dict__.items()
			            if isinstance(trigger, AbstractCollectorTrigger))
		for name, trigger in triggers:
			if isinstance(trigger, AbstractCollectorTrigger):
				setattr(source, name, cls(source, trigger))


	def __init__(self, source: Any, base: AbstractCollectorTrigger, **kwargs):
		super().__init__(**kwargs)















