from typing import Any, Iterator, List, Optional, Tuple, Union, Callable, Type, Dict
import inspect

from .typing import unspecified_argument
from .tricks import method_decorator
from .propagators import universal_propagator


class AbstractOperational:
	def __get__(self, instance, owner):
		if instance is None:
			return self
		return self._create_operator(instance, owner)


	def _create_operator(self, instance, owner):
		raise NotImplementedError



class AbstractOperator:
	def __init__(self, base: AbstractOperational, instance: Any, **kwargs):
		super().__init__(**kwargs)


	def _send_operation(self, item):
		raise NotImplementedError



class SimpleOperator(AbstractOperator):
	def __init__(self, base, instance, **kwargs):
		super().__init__(base, instance, **kwargs)
		self._base = base
		self._instance = instance

	class _operation_caller:
		def __init__(self, fn, instance, **kwargs):
			super().__init__(**kwargs)
			self.fn = fn
			self.instance = instance

		def __call__(self, *args, **kwargs):
			return self.fn(self.instance, *args, **kwargs)

	def _send_operation(self, fn: Callable, **kwargs):
		return self._operation_caller(fn, self._instance, **kwargs)



class AutoOperator(SimpleOperator):
	def _find_operation_target(self, item):
		return getattr(self._base, item)


	def _send_operation(self, item: str, **kwargs):
		return super()._send_operation(self._find_operation_target(item), **kwargs)



class FormatOperator(AutoOperator):
	def __init__(self, base, instance, formatter: str, **kwargs):
		super().__init__(base, instance, **kwargs)
		self._formatter = formatter


	def _find_operation_target(self, item):
		return getattr(self._base, self._formatter.format(item))



class PrefixOperator(AutoOperator):
	def __init__(self, base, instance, prefix: str, formatter: str = None, **kwargs):
		if formatter is None:
			formatter = f'{prefix}{"{}"}'
		super().__init__(base, instance, formatter=formatter, **kwargs)
		self._prefix = prefix



class KeyedOperator(AutoOperator):
	class _operation_caller(SimpleOperator._operation_caller):
		def __init__(self, fn, instance, *, key=None, **kwargs):
			super().__init__(fn, instance, **kwargs)
			self.key = key

		def __call__(self, *args, **kwargs):
			if self.key is not None:
				args = (self.key, *args)
			return super().__call__(*args, **kwargs)


	def _send_operation(self, item, *, key=unspecified_argument, **kwargs):
		if key is unspecified_argument:
			key = item
		return self._operation_caller(item, self._instance, key=key, **kwargs)



class HubOperator(KeyedOperator):
	def __init__(self, base, instance, *, hub_fn=None, **kwargs):
		if isinstance(hub_fn, str):
			hub_fn = getattr(base, hub_fn)
		super().__init__(base, instance, **kwargs)
		self._hub_fn = hub_fn


	def _find_operation_target(self, item):
		if self._hub_fn is None:
			return super()._find_operation_target(item)
		return self._hub_fn



class UniversalOperator(SimpleOperator):
	def _default_operation(self, item):
		return getattr(self._base, item)


	def __getattribute__(self, item):
		try:
			return super().__getattribute__(item)
		except AttributeError:
			return self._default_operation(item)



class MappedOperator(UniversalOperator):
	def __init__(self, base, instance, *, ops: Dict[str, Callable] = None, **kwargs):
		super().__init__(base, instance, **kwargs)
		self._ops = ops


	def _default_operation(self, item):
		if self._ops is None:
			return super()._default_operation(item)
		return self._send_operation(item)


	def _send_operation(self, fn: Union[Callable, str], **kwargs):
		if isinstance(fn, str):
			fn = self._ops[fn]
		return super()._send_operation(fn, **kwargs)


class ConditionalOperator(AutoOperator, UniversalOperator):
	def _check_if_operation(self, item):
		raise NotImplementedError


	def _default_operation(self, item):
		if self._check_if_operation(item):
			return self._send_operation(item)
		return super()._default_operation(item)



class OptionOperator(ConditionalOperator):
	def __init__(self, base, instance, *, ops=None, **kwargs):
		if ops is None:
			ops = set()
		super().__init__(base, instance, **kwargs)
		self._ops = ops


	def _check_if_operation(self, item):
		return item in self._ops



class AliasOperator(OptionOperator):
	def __init__(self, base, instance, *, aliases=None, **kwargs):
		if aliases is None:
			aliases = {}
		super().__init__(base, instance, **kwargs)
		self._ops = {**{op: op for op in self._ops}, **aliases}


	def _find_operation_target(self, item):
		return getattr(self._base, self._ops[item])



class _operation_base(method_decorator):
	def __init__(self, fn: Callable = None, **kwargs):
		super().__init__(fn, **kwargs)
		self._attr_name = None


	def _setup_decorator(self, owner: Type, name: str) -> 'method_decorator':
		self._attr_name = name
		return super()._setup_decorator(owner, name)


	@property
	def op_name(self):
		raise NotImplementedError


	@property
	def attr_name(self):
		return self._attr_name


	@property
	def original_function(self):
		return self._fn



class operation_base(_operation_base):
	# first argument of wrapped functions should always be the instance
	def __init__(self, fn: Union[str, Callable], **kwargs):
		if isinstance(fn, str):
			fn, name = None, fn
		else:
			name = None
		super().__init__(fn, **kwargs)
		self._op_name = name


	@property
	def op_name(self):
		if self._op_name is None:
			return self._attr_name
		return self._op_name



class auto_operation(_operation_base, universal_propagator):
	# first argument of wrapped functions should always be the instance
	def __call__(self, fn):
		raise ValueError('operation decorator does not take arguments')


	@property
	def op_name(self):
		if self._method_name is None:
			return self._attr_name
		return self._method_name



class SimpleOperational(AbstractOperational):
	Operator = AbstractOperator


	def _create_operator(self, instance, owner, **kwargs):
		return self.Operator(self, instance, **kwargs)



class OptionOperational(SimpleOperational):
	Operator = OptionOperator


	def operations(self) -> Iterator[str]:
		raise NotImplementedError


	def _create_operator(self, instance, owner, *, ops=None, **kwargs):
		if ops is None:
			ops = set(self.operations())
		return super()._create_operator(instance, owner, ops=ops, **kwargs)



class Operationalized(AbstractOperational):
	def as_operator(self, instance):
		return self._create_operator(instance, type(instance))



class DecoratedOperational(OptionOperational):
	Operator = MappedOperator

	_known_operations = None
	def __init_subclass__(cls, skip_inherit_operations=False, **kwargs):
		super().__init_subclass__(**kwargs)
		if '_known_operations' not in cls.__dict__:
			ops = {}
			if not skip_inherit_operations:
				for base in reversed(cls.__bases__):  # O-N
					new = getattr(base, '_known_operations', {})
					if new:
						ops.update(new)
			for name, attr in cls.__dict__.items(): # O-N
				if isinstance(attr, _operation_base):
					ops[attr.op_name] = attr
					setattr(cls, name, attr.original_function)
			cls._known_operations = ops # O-N

	def _process_operation(self, ops, name, attr):
		return op


	def operations(self) -> Iterator[str]:
		yield from self._known_operations.keys()


	def _create_operator(self, instance, owner, *, ops=None, **kwargs):
		if ops is None:
			ops = {name: getattr(self, op.attr_name)
			       for name, op in self._known_operations.items()}
		return super()._create_operator(instance, owner, ops=ops, **kwargs)




