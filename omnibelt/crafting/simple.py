from typing import Tuple, List, Dict, Optional, Union, Any, Callable, Sequence, Iterator, Iterable, Type, Set
import inspect
from functools import cached_property

import torch

from omnibelt import method_decorator, agnostic

# from .abstract import


class AbstractCrafty:
	@classmethod
	def _emit_my_crafts(cls, instance: 'AbstractCrafty'): # N-O
		for key, val in reversed(cls.__dict__.items()): # N-O
			if isinstance(val, AbstractCraft):
				yield from val.emit_craft_items(instance) # N-O



class InheritableCrafty(AbstractCrafty):
	def _emit_all_crafts(self): # N-O
		for owner in type(self).mro(): # N-O
			if isinstance(owner, AbstractCrafty):
				yield from owner._emit_my_crafts(self) # N-O



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


class LabelCraft(AbstractCraft):
	def __init__(self, label: str, **kwargs):
		super().__init__(**kwargs)
		self._label = label


	@property
	def label(self):
		return self._label



class ToolCraft(LabelCraft, NestableCraft, OperationalCraft):
	class Operator(OperationalCraft.Operator):
		def get_from(self, ctx, gizmo: str):
			return self._base.get_from(self._instance, ctx, gizmo)


	def get_from(self, instance: AbstractCrafty, ctx, gizmo: str):
		raise NotImplementedError



class FunctionToolCraft(ToolCraft, method_decorator):
	def __init__(self, label: str, *, fn=None, **kwargs):
		super().__init__(label=label, fn=fn, **kwargs)


	_name = None
	def _setup_decorator(self, owner: Type, name: str) -> 'method_decorator':
		self._name = name
		return super()._setup_decorator(owner, name)


	def get_from(self, instance: AbstractCrafty, ctx, gizmo: str):
		if self._name is None:
			raise TypeError('no name')
		if self._label != gizmo:
			raise ValueError(f'gizmo mismatch: {self._label} != {gizmo}')
		return self._get_from_fn(getattr(instance, self._name), ctx, gizmo)


	def _get_from_fn(self, fn, ctx, gizmo):
		return fn(ctx)



class MachineCraft(FunctionToolCraft):
	@staticmethod
	def _parse_context_args(fn: Callable, ctx):
		# TODO: allow for default values -> use omnibelt extract_signature

		args = {}
		params = inspect.signature(fn).parameters
		for name, param in params[1:].items():
			if name in ctx:
				args[name] = ctx[name]

		return args


	def _get_from_fn(self, fn, ctx, gizmo):
		return fn(**self._parse_context_args(fn, ctx))



class BatchCraft(FunctionToolCraft):
	def _get_from_fn(self, fn, ctx, gizmo):
		return fn(getattr(ctx, 'batch', ctx))



class SizeCraft(FunctionToolCraft):
	def _get_from_fn(self, fn, ctx, gizmo):
		return fn(getattr(ctx, 'size', ctx))



class IndexCraft(FunctionToolCraft):
	def _get_from_fn(self, fn, ctx, gizmo):
		return fn(getattr(ctx, 'indices', ctx))



class SampleCraft(FunctionToolCraft):
	def _get_from_fn(self, fn, ctx, gizmo):
		size = getattr(ctx, 'size', None)
		if size is None:
			return fn()
		return torch.stack([fn() for _ in range(size)])



class IndexSampleCraft(IndexCraft, SampleCraft):
	def _get_from_fn(self, fn, ctx, gizmo):
		indices = getattr(ctx, 'indices', None)
		if indices is None:
			return fn(getattr(ctx, 'index', ctx))
		return torch.stack([fn(i) for i in indices])



class SpaceCraft(LabelCraft, cached_property):
	def __init__(self, gizmo: str, *, func=None, **kwargs):
		super().__init__(gizmo=gizmo, func=func, **kwargs)


	def __call__(self, func: Callable):
		self.func = func
		return self



class OptionalCraft(MachineCraft):
	pass



class DefaultCraft(MachineCraft):
	pass



########################################################################################################################



class machine(MachineCraft):
	@staticmethod
	def optional(*args, **kwargs):
		return OptionalCraft(*args, **kwargs)


	@staticmethod
	def default(*args, **kwargs):
		return DefaultCraft(*args, **kwargs)


	@agnostic
	def space(self, *args, **kwargs):
		if not isinstance(self, type):
			return SpaceCraft(self.label)(*args, **kwargs)
		return SpaceCraft(*args, **kwargs)
























