import types
from typing import Callable, Any
import inspect


primitives = (str, int, float, bool, type(None))

# unspecified_argument = inspect._empty
class unspecified_argument:
	@staticmethod
	def __repr__():
		return '<unspecified>'


class agnostic:
	def __init__(self, fn=None, **kwargs):
		super().__init__(**kwargs)
		self.fn = fn

	def __get__(self, instance, owner=None):
		assert owner is not None, f'owner is missing: {self.fn} ({instance})'
		if instance is None:
			instance = owner
		return self.fn.__get__(instance, owner)


class agnosticproperty(property):
	def __get__(self, instance, owner=None):
		assert owner is not None, f'owner is missing: {self.fget} ({instance})'
		if instance is None:
			instance = owner
		return super().__get__(instance, owner)

	def getter(self, fget: Callable[[Any], Any]) -> 'agnosticproperty':
		return type(self)(fget, self.fset, self.fdel, self.__doc__)

	def setter(self, fset: Callable[[Any, Any], None]) -> 'agnosticproperty':
		return type(self)(self.fget, fset, self.fdel, self.__doc__)
	
	def deleter(self, fdel: Callable[[Any], None]) -> 'agnosticproperty':
		return type(self)(self.fget, self.fset, fdel, self.__doc__)


agnosticmethod = agnostic


def isiterable(obj):
	try:
		iter(obj)
		return True
	except TypeError:
		return False





# class agnosticmethod:
# 	def __init__(self, fn):
# 		self.fn = fn
#
#
# 	def __get__(self, obj, cls):
# 		# if inspect.isgeneratorfunction(self.fn):
# 		# 	return types.GeneratorType(self.fn, obj)
# 		return types.MethodType(self.fn, cls if obj is None else obj)


# class agnosticproperty:
#     def __init__(self, fget, fset=None):
#         self.fget = fget
#         self.fset = fset
#
#     def __get__(self, obj, klass=None):
#         if klass is None:
#             klass = type(obj)
#         return self.fget.__get__(obj, klass)()
#
#     def __set__(self, obj, value):
#         if not self.fset:
#             raise AttributeError("can't set attribute")
#         type_ = type(obj)
#         return self.fset.__get__(obj, type_)(value)
#
#     def setter(self, func):
#         if not isinstance(func, agnosticmethod):
#             func = agnosticmethod(func)
#         self.fset = func
#         return self



def duplicate_func(f, cls=None, name=None):
	'''
	Adapted from Aaron Hall's post here:
	https://stackoverflow.com/questions/6527633
	'''

	closure = []
	if f.__closure__ is not None:
		closure = list(f.__closure__)

		if cls is not None:
			cls_cell_idx = f.__code__.co_freevars.index("__class__")
			closure[cls_cell_idx] = types.CellType(cls)

	if name is None:
		name = f.__name__

	new = types.FunctionType(
		f.__code__,
		f.__globals__,
		name,
		f.__defaults__,
		tuple(closure)
	)

	new.__qualname__ = f"{cls.__name__}.{new.__name__}"
	new.__dict__.update(f.__dict__)

	return new



def join_classes(*bases, name=None, data=None):
	if data is None:
		data = {}
	if name is None:
		name = '_'.join(cls.__name__ for cls in bases)
	return type(name, bases, data)


class ClassAttr:
	def duplicate(self):
		clone = _Blank()
		clone.__class__ = self.__class__
		clone.__dict__.update(self.__dict__)
		return clone



def duplicate_class(cls, name=None, chain=False, data=None):
	if name is None:
		name = cls.__name__

	if chain:
		parents = (cls,)
		data = {}
	else:
		parents = cls.__bases__
		data = dict(cls.__dict__)

	new = join_classes(*parents, name=name, data=data)
	for key, attr in new.__dict__.items():
		if isinstance(attr, ClassAttr):
			setattr(new, key, attr.duplicate())
		elif isinstance(attr, types.FunctionType):
			setattr(new, key, duplicate_func(attr, cls=new))

	return new



class _Blank: pass
def duplicate_instance(obj):
	# slots = getattr(obj.__class__, '__slots__', None)
	# if slots is None:
	# 	class _Blank():
	# 		pass
	# else:
	# 	class _Blank():
	# 		__slots__ = slots
	new = _Blank()
	new.__dict__.update(obj.__dict__)
	new.__class__ = obj.__class__
	return new



class conditional_method(ClassAttr):
	def __init__(self, fn=None):
		self.fn = fn

	def condition(self, instance):
		raise NotImplementedError

	def set_owner(self, owner):
		self.owner = owner

	def set_base(self, base):
		self.base = base

	def _build_method(self, fn, instance, owner):
		return types.MethodType(duplicate_func(fn, cls=owner), instance)

	def __get__(self, instance, owner):
		# print(f"returned from descriptor object {instance} {owner}")

		if instance is None:
			return self

		if not self.condition(instance):
			raise AttributeError(f'Condition of wrapped method failed: {self.fn.__name__}')
		meth = self._build_method(self.fn, instance, getattr(self, 'base', owner))
		return meth


	def __set__(self, instance, value):
		print(f"set in descriptor object {instance} {value}")
		self.fn = value


	def __call__(self, fn):
		self.fn = fn
		return self



class lambda_conditional_method(conditional_method):
	def __init__(self, condition):
		self._condition = condition


	def condition(self, instance):
		return self._condition(instance)



_class_subs = {}
def _gen_sub_template_name(cls):
	if cls not in _class_subs:
		_class_subs[cls] = 0
	_class_subs[cls] += 1
	return f'{cls.__name__}{_class_subs[cls]}'



def wrap_class(wrapper, cls, name=None, chain=False, data=None):
	if name is None:
		name = _gen_sub_template_name(wrapper)

	sub = duplicate_class(wrapper, name, chain=chain, data=data)
	for attr in sub.__dict__.values():
		if isinstance(attr, conditional_method):
			attr.set_owner(sub)
			attr.set_base(cls)
	return join_classes(sub, cls)



def replace_class(obj, cls, check_conditions=True):
	obj.__class__ = cls
	return obj



def mix_into(wrapper, obj, new_instance=False, chain=False, cls_data=None):
	cls = wrap_class(wrapper, obj.__class__, chain=chain, data=cls_data)
	if new_instance:
		obj = duplicate_instance(obj)
	return replace_class(obj, cls)




# def make_multiplier_of(n):
#     def multiplier(x):
#         print(n)
#         return x * n
#     return multiplier
# f = make_multiplier_of(2)
# c = f.__code__
# c2 = c.replace(co_freevars=('_test', *f.__code__.co_freevars))
# closure = [ types.CellType('!')]
# if f.__closure__ is not None:
#     closure.extend(f.__closure__)
# f2 = types.FunctionType(
#     c2,
#     f.__globals__,
#     'f2',
#     f.__defaults__,
#     tuple(closure)
# )

