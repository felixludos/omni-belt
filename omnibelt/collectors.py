from typing import Type, Optional, Union, Any, Callable, Sequence, Iterable, Iterator, Tuple, List, Dict, NamedTuple
from collections import OrderedDict
from .tricks import nested_method_decorator



class method_collector(nested_method_decorator):
	_method_table_type = list

	def __init__(self, *keys, replaces=None, **info):
		fn = None
		if len(keys) and callable(keys[0]): # if callable, assume it is the init function
			fn, keys = keys

		super().__init__(fn=fn)

		self._keys = keys
		self._replaces = replaces
		self._info = info
		self._methods = self._method_table_type()


	def _setup(self, owner: Type, name: str) -> None:
		super()._setup(owner, name)
		self._name = name


	def _make_collector(self, *args, **kwargs):
		collector = self._collector(*args, **kwargs)
		self._methods.append(collector)
		return collector


	class _collector:
		class _collect_fn:
			def __init__(self, owner):
				self.owner = owner
			def __call__(self, fn):
				self.owner.fn = fn
				return fn

		def __init__(self, *args, **kwargs):
			super().__init__(*args, **kwargs)
			self.args = None
			self.kwargs = None
			self.fn = None

		def __call__(self, *args, **kwargs):
			self.args = args
			self.kwargs = kwargs
			return self._collect_fn(self)



class universal_collector(method_collector):
	def __getattribute__(self, item):
		try:
			return super().__getattribute__(item)
		except AttributeError:
			return self._make_collector(item)



class AbstractCollectorTrigger:
	@classmethod
	def process_collectors(cls, owner: Type['Collectable']):
		for key, val in owner.__dict__.items():
			if isinstance(val, method_collector):
				setattr(owner, key, cls(owner, val))


	def __init__(self, owner: Type['Collectable'], base: method_collector, **kwargs):
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















