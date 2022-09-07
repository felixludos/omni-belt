from typing import List, Dict, Tuple, Optional, Union, Any, Hashable, Sequence, Callable, Generator, Type, Iterable, Iterator
import types
import inspect
from .typing import unspecified_argument



# class _customizable_super_parent: pass # hidden parent class to hold the delegators
# class customizable_super(_customizable_super_parent):
# 	def captured_super(self, src, name, args, kwargs):
# 		'''
# 		Called when methods decorated with @capture_super call super() (without parameters).
#
# 		:param src: the class from which the method was called
# 		:param name: of the method being called
# 		:param args: positional arguments passed to the method
# 		:param kwargs: keyword arguments passed to the method
# 		:return: output of the desired effect of super().[name](*args, **kwargs)
# 		'''
# 		return getattr(super(src, self), name)(*args, **kwargs)
#
#
#
# class capture_super:
# 	_child_capturer = customizable_super # gets set as the __class__ of methods decoared with @capture_super
# 	_parent_capturer = _customizable_super_parent # contains the corresponding delegator to execute capture
#
# 	def __init__(self, fn=None, ):#use_method_maker=True):
# 		self.fn = fn
# 		self._is_setup = False
# 		# self.use_method_maker = use_method_maker
#
# 	def __call__(self, fn):
# 		self.fn = fn
# 		return self
#
# 	def setup(self, name, owner):
# 		self._is_setup = True
# 		self.name = name
# 		self.owner = owner
#
# 		if self.fn is not None:
# 			setattr(self._parent_capturer, self.name, self.run_delegator(self.name))
# 		return self
#
# 	def __set_name__(self, owner, name):
# 		setattr(owner, name, self.setup(name, owner))
#
# 	def __get__(self, instance, owner):
# 		if not self._is_setup:
# 			raise RuntimeError(f'{self.__class__.__name__} not setup properly '
# 			                   f'(call setup(name, owner) or use as decorator)')
# 		if self.fn is not None and self.fn.__closure__ is not None:
# 			self.fn.__closure__[0].cell_contents = self._child_capturer
#
# 		if instance is None:
# 			# if not self.use_method_maker:
# 			# 	return self.fn
# 			return self.method_delay(self.fn, self.owner,
# 			                         self.run_delegator.single_run.instance_trigger.format(name=self.name))
#
# 		setattr(instance, self.run_delegator.single_run.instance_trigger.format(name=self.name), self.owner)
# 		return types.MethodType(self.fn, instance)
#
# 		# if instance is not None:
# 		# 	setattr(instance, self.run_delegator.single_run.instance_trigger.format(name=self.name), self.owner)
# 		#
# 		# return self.fn if instance is None else types.MethodType(self.fn, instance)
#
#
# 	class method_delay:
# 		def __init__(self, fn, owner, flag):
# 			self.fn = fn
# 			self.owner = owner
# 			self.flag = flag
#
# 		def __call__(self, instance, *args, **kwargs):
# 			setattr(instance, self.flag, self.owner)
# 			return self.fn(instance, *args, **kwargs)
#
#
# 	class run_delegator: # located in _parent_capturer and checks if instance can trigger a capture of a method
# 		def __init__(self, name):
# 			self.name = name
#
# 		def __get__(self, instance, owner):
# 			if instance is None:
# 				raise AttributeError(self.name)
#
# 			true_owner = getattr(instance, self.single_run.instance_trigger.format(name=self.name), None)
# 			if true_owner is None:
# 				# return getattr(instance, self.name)
# 				return getattr(super(owner, instance), self.name)
# 				# raise AttributeError(self.name)
#
# 			return self.single_run(instance, true_owner, self.name)
#
#
# 		class single_run: # created by delegator for a single run with a specific instance and method
# 			instance_trigger = '_invisible_super_trigger_for_{name}'
#
# 			def __init__(self, obj, cls, name):
# 				self.obj = obj
# 				self.cls = cls
# 				self.name = name
#
# 			def clean_up(self):
# 				key = self.instance_trigger.format(name=self.name)
# 				if hasattr(self, key):
# 					delattr(self.obj, key)
#
# 			def __call__(self, *args, **kwargs):
# 				out = self.run(self.cls, self.obj, self.name, args, kwargs)
# 				self.clean_up()
# 				return out
#
# 			@staticmethod
# 			def run(cls, obj, name, args, kwargs):
# 				return obj.captured_super(cls, name, args, kwargs)




# Example usage:
# class A(customizable_super):
#     def captured_super(self, src, name, args, kwargs):
#         print('!! captured', self, src, name, args, kwargs)
#         return super().captured_super(src, name, args, kwargs)
#
#     def f(self, a=1):
#         print('A.f', self, a)
#         # print(super().f())
#
# class B(A):
#     x = -10
#
#     def f(self, a=2):
#         print('B.f', self, a)
#         super().f()
#
# # @enable_hijacks
# class C(B):
#     x = 0
#     @capture_super
#     def f(self, a=3):
#         print('C.f', self, a)
#         super().f()
#
# class D(C):
#     def f(self, a=4):
#         print('D.f', self, a)
#         super().f()
#
# class E(D):
#     @capture_super
#     def f(self, a=5):
#         print('E.f', self, a)
#         super().f()
#
# class F(E):
#     def f(self, a=6):
#         print('F.f', self, a)
#         super().f()

# A().f()
# print()
# B().f()
# print()
# C().f()
# print()
# D().f()
# print()
# E().f()
# print()
# F().f()

###################################################

class ClassDescriptable(type):
	def __setattr__(self, key, val):
		existing = inspect.getattr_static(self, key, None)
		if isinstance(existing, classdescriptor):
			existing.__set__(self, val)
		else:
			super().__setattr__(key, val)


	def __delattr__(self, item):
		existing = inspect.getattr_static(self, item, None)
		if isinstance(existing, classdescriptor):
			existing.__delete__(self)
		else:
			super().__delattr__(item)



class classdescriptor:
	def __set__(self, obj, value):
		raise NotImplementedError


	def __delete__(self, obj):
		raise NotImplementedError



class MRONamespace(dict):
	def __init__(self, bases):
		if any(isinstance(base, MROMeta) for base in bases):
			class Scoped(*bases, use_mro_namespace=False): pass
		else:
			class Scoped(*bases): pass
		self.pseudo = Scoped

	def __getitem__(self, index):
		if index in self:
			return super().__getitem__(index)

		if hasattr(self.pseudo, index):
			return getattr(self.pseudo, index)

		raise IndexError()


class MROMeta(type):
	def __new__(metacls, name, bases, namespace, **kwargs):
		return super().__new__(metacls, name, bases, namespace)

	@classmethod
	def __prepare__(cls, name, bases, use_mro_namespace=True, **kwargs):
		if use_mro_namespace:
			return MRONamespace(bases)
		return dict()



class Scope(metaclass=MROMeta):
	pass



class method_decorator:
	def __init__(self, fn=None, *, enforce_setup=True):
		self.fn = fn
		self._enforce_setup = enforce_setup
		self._is_setup = False

	def __call__(self, fn):
		self.fn = fn
		return self


	def setup(self, owner, name=None):
		self._is_setup = True
		if name is None:
			name = self.fn.__name__
		self._setup(owner, name)
		return self


	def _setup(self, owner: Type, name: str):
		pass


	def __set_name__(self, owner, name):
		setattr(owner, name, self.setup(owner, name))


	def __get__(self, instance, owner):
		if self._enforce_setup and not self._is_setup:
			raise RuntimeError(f'{self.__class__.__name__} not setup properly '
			                   f'(call .setup(name, owner) or use as decorator)')
		return self.package(instance, owner)


	def package(self, instance, owner):
		return self.fn if instance is None else types.MethodType(self.fn, instance)



class method_locator(method_decorator):
	def _setup(self, owner, name):
		self.location = owner
		return super()._setup(owner, name)



class method_binder(method_decorator):
	class future_method:
		def __init__(self, fn, owner, instance=None):
			self.fn = fn
			self.instance = instance
			self.owner = owner

		def __repr__(self):
			return f'<future_method {self.fn.__name__} of {self.owner.__name__}>' if self.instance is None \
				else f'<future_method {self.fn.__name__} of {self.owner.__name__} bound to {self.instance}>'

		def __call__(self, *args, **kwargs):
			if self.instance is None:
				assert len(args), 'no instance to call method on'
				self.instance = args[0]
				args = args[1:]
			return self.fn_call(self.fn, self.instance, *args, **kwargs)

		@staticmethod
		def fn_call(fn, instance, *args, **kwargs):
			return fn(instance, *args, **kwargs)


	def package(self, instance, owner):
		return self.future_method(self.fn, owner, instance)



class capturable_method:
	def captured_method_call(self, src, fn, args, kwargs):
		return fn(self, *args, **kwargs)


class captured_method(method_locator, method_binder):
	_capturer_type = None

	class future_method(method_binder.future_method):
		def fn_call(self, fn, instance, *args, **kwargs):
			return instance.captured_method_call(self.owner, fn, args, kwargs)


	def package(self, instance, owner):
		return self.future_method(self.fn, self.location, instance)




class _capturable_super_parent: pass # hidden parent class to hold the delegators
class capturable_super(_capturable_super_parent):
	def captured_super_call(self, src, name, args, kwargs):
		'''
		Called when methods decorated with @capture_super call super() (without parameters).

		:param src: the class from which the method was called
		:param name: of the method being called
		:param args: positional arguments passed to the method
		:param kwargs: keyword arguments passed to the method
		:return: output of the desired effect of super().[name](*args, **kwargs)
		'''
		return getattr(super(src, self), name)(*args, **kwargs)



class captured_super(method_locator, method_binder):
	_child_capturer = capturable_super # gets set as the __class__ of methods decoared with @capture_super
	_parent_capturer = _capturable_super_parent # contains the corresponding delegator to execute capture


	def _setup(self, owner, name):
		self.name = name
		if self.fn is not None:
			setattr(self._parent_capturer, self.name, self.run_delegator(self.name))

		# if self.fn is not None and self.fn.__closure__ is not None:
		# 	self.fn.__closure__[0].cell_contents = self._child_capturer
		return super()._setup(owner, name)


	def package(self, instance, owner):
		if self.fn is not None and self.fn.__closure__ is not None:
			self.fn.__closure__[0].cell_contents = self._child_capturer
		return self.future_method(self.fn, self.location, instance,
			self.run_delegator.single_run.instance_trigger.format(name=self.name))


	class future_method(method_binder.future_method):
		def __init__(self, fn, owner, instance=None, flag=None):
			super().__init__(fn, owner, instance)
			self.flag = flag

		def fn_call(self, fn, instance, *args, **kwargs):
			setattr(instance, self.flag, self.owner)
			return super().fn_call(fn, instance, *args, **kwargs)


	class run_delegator: # located in _parent_capturer and checks if instance can trigger a capture of a method
		def __init__(self, name):
			self.name = name

		def __get__(self, instance, owner):
			if instance is None:
				raise AttributeError(self.name)

			true_owner = getattr(instance, self.single_run.instance_trigger.format(name=self.name), None)
			if true_owner is None:
				# return getattr(instance, self.name)
				return getattr(super(owner, instance), self.name)
				# raise AttributeError(self.name)

			return self.single_run(instance, true_owner, self.name)


		class single_run: # created by delegator for a single run with a specific instance and method
			instance_trigger = '_invisible_super_trigger_for_{name}'

			def __init__(self, obj, cls, name):
				self.obj = obj
				self.cls = cls
				self.name = name

			def clean_up(self):
				key = self.instance_trigger.format(name=self.name)
				if hasattr(self, key):
					delattr(self.obj, key)

			def __call__(self, *args, **kwargs):
				out = self.run(self.cls, self.obj, self.name, args, kwargs)
				self.clean_up()
				return out

			@staticmethod
			def run(cls, obj, name, args, kwargs):
				return obj.captured_super_call(cls, name, args, kwargs)



class Capturable(capturable_method, capturable_super):
	pass


class captured(captured_super, captured_method):
	class future_method(captured_super.future_method, captured_method.future_method): pass






class method_wrapper(method_decorator):
	def package(self, obj, cls=None):
		self.obj, self.cls = obj, cls
		return self.apply_fn


	def process_args(self, args, kwargs):
		args = (self.obj, *args)
		return args, kwargs


	@staticmethod
	def process_out(out):
		return out


	def apply_fn(self, *args, **kwargs):
		args, kwargs = self.process_args(args, kwargs)
		out = self.fn(*args, **kwargs)
		out = self.process_out(out)
		return out



class self_aware:
	def __init__(self, cls):
		self.cls = cls

	def __set_name__(self, owner, name):
		self.cls.owner = owner
		setattr(owner, name, self.cls)



class _meta_clsdec(type):
	def __getattr__(self, key):
		self.key = key
		return self



class clsdec(metaclass=_meta_clsdec):
	def __init__(self, *args, **kwargs):
		self.args, self.kwargs = args, kwargs


	def __call__(self, fn):
		self.fn = fn
		return self


	def __set_name__(self, obj, name):
		setattr(obj, name, getattr(obj, self.key)(*self.args, **self.kwargs)(self.fn))



class innerchild:
	def __init__(self, cls):
		self.cls = cls


	class MissingParent(Exception):
		def __init__(self, base, name):
			super().__init__(f'{base.__name__} has not inner class {name}')


	def __set_name__(self, owner, name):
		cls_name = self.cls.__name__
		parent = getattr(super(owner, owner), cls_name, None)
		if parent is None:
			raise self.MissingParent(owner, cls_name)
		child = type(cls_name, (self.cls, parent), {})
		setattr(owner, name, child)


from inspect import Parameter

def deep_method_finder(typ: type, method: str, *, break_fn: Callable[[type],bool] = None) -> Iterator[Callable]:
	on_parents = False
	for cls in typ.mro():
		fn = cls.__dict__.get(method, None)
		if fn is not None:
			if on_parents and break_fn is not None and break_fn(fn):
				break
			on_parents = True
			yield fn

def collect_fn_kwargs(*fns: Callable, default: Any = Parameter.empty, ignore_positional_only=False):
	kwargs = {}

	for fn in fns:
		params = inspect.signature(fn).parameters
		for param in params.values():
			if param.kind == param.POSITIONAL_ONLY and not ignore_positional_only:
				raise TypeError(f'Positional only arguments are not supported: {param.name}')
			elif param.kind in {param.POSITIONAL_OR_KEYWORD, param.KEYWORD_ONLY} and param.name not in kwargs:
				kwargs[param.name] = default if param.default is param.empty else param.default

	return kwargs

def collect_init_kwargs(typ: type, default: Any = Parameter.empty, *, end_type: Union[Sequence[Type], Type] = None,
						ignore_positional_only=False, break_fn=None):
	if break_fn is None:
		if end_type is not None and isinstance(end_type, type):
			end_type = {end_type,}
		break_fn = (lambda cls: True) if end_type is None else (lambda cls: cls in end_type)
	return collect_fn_kwargs(*deep_method_finder(typ, method='__init__', break_fn=break_fn),
							 default=default, ignore_positional_only=ignore_positional_only)

	
def extract_function_signature(fn, args=(), kwargs={}, *, default_fn=None, allow_positional=True):
	params = inspect.signature(fn).parameters
	
	arg_idx = 0
	fixed_args = []
	fixed_kwargs = {}
	
	for n, p in params.items():
		if p.kind == p.POSITIONAL_ONLY:
			if not allow_positional:
				raise TypeError(f'Function {fn.__name__} has a positional only argument ({n})')
			if arg_idx < len(args):
				fixed_args.append(args[arg_idx])
				arg_idx += 1
			else:
				try:
					if default_fn is None:
						raise KeyError
					val = default_fn(n)
				except KeyError:
					pass
				else:
					fixed_args.append(val)
		elif p.kind == p.VAR_POSITIONAL:
			if not allow_positional:
				raise TypeError(f'Function {fn.__name__} has variable positional arguments ({n})')
			try:
				if default_fn is None:
					raise KeyError
				val = default_fn(n)
			except KeyError:
				fixed_args.extend(args[arg_idx:])
				arg_idx = len(args)
			else:
				fixed_args.extend(val)
		elif p.kind == p.VAR_KEYWORD:
			try:
				if default_fn is None:
					raise KeyError
				val = default_fn(n)
			except KeyError:
				fixed_kwargs.update(kwargs)
			else:
				fixed_kwargs.update(val)

		else:
			if n in kwargs:
				fixed_kwargs[n] = kwargs[n]
			elif p.kind != p.KEYWORD_ONLY and arg_idx < len(args):
				if allow_positional:
					fixed_args.append(args[arg_idx])
				else:
					fixed_kwargs[n] = args[arg_idx]
				arg_idx += 1
			else:
				try:
					if default_fn is None:
						raise KeyError
					val = default_fn(n)
				except KeyError:
					pass
				else:
					fixed_kwargs[n] = val
	if allow_positional:
		return fixed_args, fixed_kwargs
	assert len(fixed_args) == 0, f'fixed_args: {fixed_args}'
	return fixed_kwargs



# class Property(object):
#     "Emulate PyProperty_Type() in Objects/descrobject.c"
#
#     def __init__(self, fget=None, fset=None, fdel=None, doc=None):
#         self.fget = fget
#         self.fset = fset
#         self.fdel = fdel
#         if doc is None and fget is not None:
#             doc = fget.__doc__
#         self.__doc__ = doc
#
#     def __get__(self, obj, objtype=None):
#         if obj is None:
#             return self
#         if self.fget is None:
#             raise AttributeError("unreadable attribute")
#         return self.fget(obj)
#
#     def __set__(self, obj, value):
#         if self.fset is None:
#             raise AttributeError("can't set attribute")
#         self.fset(obj, value)
#
#     def __delete__(self, obj):
#         if self.fdel is None:
#             raise AttributeError("can't delete attribute")
#         self.fdel(obj)
#
#     def getter(self, fget):
#         return type(self)(fget, self.fset, self.fdel, self.__doc__)
#
#     def setter(self, fset):
#         return type(self)(self.fget, fset, self.fdel, self.__doc__)
#
#     def deleter(self, fdel):
#         return type(self)(self.fget, self.fset, fdel, self.__doc__)





# class Grandparent:
# 	print('setting up Grandparent')
# 	class mydec:
# 		def __init__(self, *args, **kwargs):
# 			print('Grandparent.mydec.__init__')
#
# 		def __call__(self, fn):
# 			print('Grandparent.mydec.__call__')
# 			return fn
#
#
# class Uncle(Grandparent):
# 	print('setting up Uncle')
# 	@clsdec.mydec('dec_arg_uncle', dec_kwarg=2)
# 	def do_something(self, x=1, y=2):
# 		print('Uncle.do_something')
#
#
# class Parent(Grandparent):
# 	print('setting up Parent')
# 	@innerchild
# 	class mydec:
# 		def __init__(self, *args, **kwargs):
# 			print('Parent.mydec.__init__')
# 		def __call__(self, fn):
# 			print('Parent.mydec.__call__')
# 			return super().__call__(fn)
#
#
# class Child(Parent):
# 	print('setting up Child')
# 	@clsdec.mydec('dec_arg_child', dec_kwarg=1)
# 	def do_something(self, x=3, y=4):
# 		print('Child.do_something')




