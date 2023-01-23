from typing import Any, Iterator, List, Optional, Tuple, Union, Callable

from . import unspecified_argument


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



	# class NoOperationFound(AttributeError):
	# 	pass


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



class UniversalOperator(AbstractOperator):
	def _default_operation(self, item):
		return getattr(self._base, item)


	def __getattribute__(self, item):
		try:
			return super().__getattribute__(item)
		except AttributeError:
			return self._default_operation(item)



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



class Operator(OptionOperator):
	def __init__(self, base, instance, *, aliases=None, **kwargs):
		if aliases is None:
			aliases = {}
		super().__init__(base, instance, **kwargs)
		self._ops = {**{op: op for op in self._ops}, **aliases}


	def _find_operation_target(self, item):
		return getattr(self._base, self._ops[item])



class Operational(AbstractOperational):
	Operator = Operator


	def operations(self) -> Iterator[str]:
		raise NotImplementedError


	def _create_operator(self, instance, owner, operations=None):
		if operations is None:
			operations = set(self.operations())
		return self.Operator(self, instance, ops=operations)



