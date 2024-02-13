from typing import List, Dict, Tuple, Optional, Union, Any, Hashable, Sequence, Callable, Generator, Type, \
	Iterable, Iterator, TypeVar, Type
import types
import inspect
from collections import OrderedDict

from .typing import unspecified_argument


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



class method_decorator: # always replaces the function
	def __init__(self, fn: Callable = None, **kwargs):
		super().__init__(**kwargs)
		self._fn = fn


	def __call__(self, fn: Callable) -> 'method_decorator':
		self._fn = fn
		return self


	def __set_name__(self, owner: Type, name: str) -> None:
		setattr(owner, name, self._setup_decorator(owner, name))


	def __get__(self, instance: Any, owner: Type) -> Any:
		return self._package_payload(self._fn, instance, owner)


	def _setup_decorator(self, owner: Type, name: str) -> 'method_decorator':
		return self


	@staticmethod
	def _package_payload(fn: Callable, instance: Any, owner: Type) -> Callable:
		getter = getattr(fn, '__get__', None)
		if getter is not None and instance is not None:
			return getter(instance, owner)
		return fn



class setup_method_decorator(method_decorator):
	def __init__(self, fn: Callable = None, *, enforce_setup: bool = True, **kwargs):
		super().__init__(fn, **kwargs)
		self._enforce_setup = enforce_setup
		self._is_setup = False


	def _setup_decorator(self, owner: Type, name: str) -> 'method_decorator':
		self._is_setup = True
		return super()._setup_decorator(owner, name)


	def _package_payload(self, fn: Callable, instance: Any, owner: Type) -> Callable:
		if self._enforce_setup and not self._is_setup:
			raise RuntimeError(f'{self.__class__.__name__} not setup properly '
							   f'(call .setup(name, owner) or use as decorator)')
		return super()._package_payload(fn, instance, owner)



class manual_method_decorator(method_decorator):
	def setup(self, owner: Type, name: Optional[str] = None) -> 'method_decorator':
		if name is None:
			name = self._fn.__name__
		return self._setup_decorator(owner, name)




# class nested_method_decorator(method_decorator):
# 	def _setup(self, owner: Type, name: str) -> None:
# 		set_name = getattr(self._fn, '__set_name__', None)
# 		if set_name is not None:
# 			set_name(owner, name)
# 		return super()._setup(owner, name)
#
# 	def __get__(self, instance: Any, owner: Type) -> Any:
# 		if self._enforce_setup and not self._is_setup:
# 			raise RuntimeError(f'{self.__class__.__name__} not setup properly '
# 							   f'(call .setup(name, owner) or use as decorator)')
# 		fn = self._fn
# 		getter = getattr(fn, '__get__', None)
# 		if getter is not None:
# 			fn = getter(instance, owner)
# 		return self.package(fn, instance, owner)


class method_binder(method_decorator):
	class future_method:
		def __init__(self, src: Type, fn: Callable, owner: Type, instance: Any = None, *,
		             is_static: Optional[bool] = None, **kwargs):
			'''
			
			Args:
				src: Class where the method is defined
				fn: Method to call
				owner: Class where the method is called
				instance: Instance where the method is called
				is_static: Whether the method is a staticmethod or classmethod
			'''
			# if is_static is None:
			# 	is_static = fn in {staticmethod, classmethod}
			self.fn = fn
			self.instance = instance
			self.src = src
			self.owner = owner
			# self.is_static = is_static
			

		def __repr__(self):
			return f'<future_method {self.fn.__name__} of {self.owner.__name__}>' if self.instance is None \
				else f'<future_method {self.fn.__name__} of {self.owner.__name__} bound to {self.instance}>'

		# def __get__(self, instance, owner):
		# 	# if instance is None:
		# 	# 	return self
		# 	return self.fn.__get__(instance, owner)

		def __call__(self, *args: Any, **kwargs: Any) -> Any:
			# if not self.is_static and self.instance is None:
			# 	assert len(args), 'no instance to call method on'
			# 	self.instance = args[0]
			# 	args = args[1:]
			return self.fn_call(self.fn,
			                    # None if self.is_static else
			                    self.instance,
			                    *args, **kwargs)

		@staticmethod
		def fn_call(fn: Callable, instance: Any, *args, **kwargs) -> Any:
			return fn(*args, **kwargs)


	def _setup_decorator(self, owner: Type, name: str) -> None:
		self.src = owner
		return super()._setup_decorator(owner, name)


	def _package_payload(self, fn: Callable, instance: Any, owner: Type) -> future_method:
		return self.future_method(self.src, fn, owner, instance)
		                          # is_static=isinstance(self.fn, (staticmethod, classmethod)))



class capturable_method:
	@classmethod
	def captured_method_call(cls, self: Optional['capturable_method'], src: Type, fn: Callable,
	                         args: Tuple, kwargs: Dict[str, Any]) -> Any:
		return fn(*args, **kwargs)


class captured_method(method_binder):
	_capturer_type = None

	class future_method(method_binder.future_method):
		def fn_call(self, fn: Callable, instance: Any, *args: Any, **kwargs: Any) -> Any:
			return self.owner.captured_method_call(instance, self.src, fn, args, kwargs)


	# def package(self, instance: Any, owner: Type) -> future_method:
	# 	return self.future_method(self.fn, self.location, instance)




class _capturable_super_parent: pass # hidden parent class to hold the delegators
class capturable_super(_capturable_super_parent):
	@classmethod
	def captured_super_call(cls, self, src: Type, name: str, args: Tuple, kwargs: Dict[str, Any]) -> Any:
		'''
		Called when methods decorated with @capture_super call super() (without parameters).

		:param src: the class from which the method was called
		:param name: of the method being called
		:param args: positional arguments passed to the method
		:param kwargs: keyword arguments passed to the method
		:return: output of the desired effect of super().[name](*args, **kwargs)
		'''
		return getattr(super(src, self), name)(*args, **kwargs)



class captured_super(method_binder):
	_child_capturer = capturable_super # gets set as the __class__ of methods decoared with @capture_super
	_parent_capturer = _capturable_super_parent # contains the corresponding delegator to execute capture


	def _setup(self, owner: Type, name: str) -> None:
		self.name = name
		if self._fn is not None:
			setattr(self._parent_capturer, self.name, self.run_delegator(self.name))

		# if self.fn is not None and self.fn.__closure__ is not None:
		# 	self.fn.__closure__[0].cell_contents = self._child_capturer
		return super()._setup(owner, name)


	class future_method(method_binder.future_method):
		def __init__(self, src, fn, owner, instance=None, flag=None):
			super().__init__(src, fn, owner, instance)
			self.flag = flag

		def fn_call(self, fn, instance, *args, **kwargs):
			if instance is None:
				raise NotImplementedError('capturing super() for classmethods or staticmethods '
				                          'is currently not supported.')
				
			setattr(instance, self.flag, self.owner)
			return super().fn_call(fn, instance, *args, **kwargs)


	def package(self, fn: Callable, instance: Any, owner: Type) -> future_method:
		if fn is not None and fn.__closure__ is not None:
			fn.__closure__[0].cell_contents = self._child_capturer
		return self.future_method(self.src, fn, owner, instance,
			self.run_delegator.single_run.instance_trigger.format(name=self.name))


	class run_delegator: # located in _parent_capturer and checks if instance can trigger a capture of a method
		def __init__(self, name: str):
			self.name = name

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

		def __get__(self, instance: Any, owner: Type) -> Union[single_run, Callable]:
			if instance is None:
				raise AttributeError(self.name)

			true_owner = getattr(instance, self.single_run.instance_trigger.format(name=self.name), None)
			if true_owner is None:
				# return getattr(instance, self.name)
				return getattr(super(owner, instance), self.name)
				# raise AttributeError(self.name)

			return self.single_run(instance, true_owner, self.name)




class Capturable(capturable_method, capturable_super):
	pass



class captured(captured_super, captured_method):
	class future_method(captured_super.future_method, captured_method.future_method): pass



class method_wrapper(method_decorator):
	def _package_payload(self, fn: Callable, instance: Any, owner: Type = None) -> Callable:
		return self.method_application(self, fn, instance, owner)
	
	@staticmethod
	def process_args(args, kwargs, owner, instance, fn):
		return args, kwargs

	@staticmethod
	def process_out(out: Any, owner, instance, fn) -> Any:
		return out

	class method_application:
		def __init__(self, wrapper: 'method_wrapper', fn: Callable, instance: Any, owner: Type = None):
			self.wrapper, self.fn, self.instance, self.owner = wrapper, fn, instance, owner

		def __call__(self, *args, **kwargs):
			args, kwargs = self.wrapper.process_args(args, kwargs, self.owner, self.instance, self.fn)
			out = self.fn(*args, **kwargs)
			return self.wrapper.process_out(out, self.owner, self.instance, self.fn)



class auto_methods(capturable_method):
	class _method_capturer(captured_method, manual_method_decorator):
		pass
	_auto_wrap_mro_until = None
	def __init_subclass__(cls, auto_methods: Optional[Union[str, Sequence[str]]] = (), wrap_existing: bool = False,
	                      inheritable_auto_methods: Optional[Union[str, Sequence[str]]] = (),
	                      wrap_mro_until=None, **kwargs):
		super().__init_subclass__(**kwargs)

		existing = [method for method, inherit in getattr(cls, '_auto_methods', {}).items() if inherit]
		if isinstance(inheritable_auto_methods, str):
			inheritable_auto_methods = (inheritable_auto_methods,)
		if isinstance(auto_methods, str):
			auto_methods = (auto_methods,)
		cls._auto_methods = OrderedDict((method, True) for method in existing + list(inheritable_auto_methods))
		cls._auto_methods.update((method, False) for method in auto_methods)

		for method in cls._auto_methods:
			if wrap_existing or method in cls.__dict__:
				fn = inspect.getattr_static(cls, method)
				if not isinstance(fn, cls._method_capturer):
					setattr(cls, method, cls._method_capturer(fn).setup(cls, method))
		if wrap_mro_until is not None:
			if wrap_mro_until is True:
				wrap_mro_until = cls
			cls._auto_wrap_mro_until = wrap_mro_until
		if cls._auto_wrap_mro_until is not None and issubclass(cls, cls._auto_wrap_mro_until):
			for parent in cls.mro():
				if parent is cls._auto_wrap_mro_until:
					break
				if parent is not cls:
					for method in cls._auto_methods:
						fn = parent.__dict__.get(method, None)
						if fn is not None and not isinstance(fn, cls._method_capturer):
							setattr(parent, method, cls._method_capturer(fn).setup(parent, method))

	@classmethod
	def _auto_method_call(cls, self, src: Type, method: Callable, args: Tuple, kwargs: Dict[str, Any]) -> None:
		raise NotImplementedError

	@classmethod
	def captured_method_call(cls, self, src: Type['auto_methods'], fn: Callable,
	                         args: Tuple, kwargs: Dict[str, Any]) -> Any:
		if getattr(cls, '_auto_methods', None) is not None and getattr(fn, '__name__', None) in cls._auto_methods:
			return cls._auto_method_call(self, src, fn, args, kwargs)
		return super().captured_method_call(self, src, fn, args, kwargs)


class auto_fix_args(auto_methods):
	class _auto_method_arg_fixer:
		def __init__(self, method: Callable, src: Type, owner: Type, obj: 'auto_methods', **kwargs):
			super().__init__(**kwargs)
			self.method = method
			self.src = src
			self.owner = owner
			self.obj = obj

		def __call__(self, key: str, default: Optional[Any] = inspect.Parameter.empty) -> Any:
			raise KeyError(key)

	class MissingArgumentsError(TypeError):
		def __init__(self, src, method, missing, *, msg=None):
			if msg is None:
				msg = f'{src.__name__}.{method.__name__}() missing {len(missing)} ' \
				      f'required arguments: {", ".join(missing)}'
			super().__init__(msg)
			self.missing = missing
			self.src = src
			self.method = method

	@classmethod
	def _auto_method_call(cls, self, src: Type, method: Callable, args: Tuple, kwargs: Dict[str, Any]) -> None:
		fixed_args, fixed_kwargs, missing = extract_function_signature(method, args, kwargs,
												default_fn=cls._auto_method_arg_fixer(method, src, cls, self),
											                  include_missing=True)
		if len(missing):
			raise cls.MissingArgumentsError(src, method, missing)
		return method(*fixed_args, **fixed_kwargs)


class auto_init(auto_methods, inheritable_auto_methods='__init__'):
	pass


T = TypeVar('T')

class dynamic_capture:
	def __init__(self, srcs: Sequence[Type[T]],
	             fn: Callable[[Type, Callable, T, Tuple, Dict[str, Any]], Any],
	             *method_names: str):

		self.srcs = srcs
		self.fn = fn
		self.method_names = method_names

		self.original_methods = None

		# if not isinstance(owner, type):
		# 	owner = type(owner)


	class capture_context:
		def __init__(self, owner, method_fn, fn):
			self.owner = owner # current class
			self.instance = None # instance of owner
			self.method_fn = method_fn # original method of src that was now replaced with self
			self.fn = fn

		def __get__(self, instance, owner):
			self.instance = instance
			return self
			# return self.fn(instance, self.src, self.original)

		def __call__(self, *args, **kwargs):
			# assert self.instance is not None, 'cannot call a captured method without an instance'
			return self.fn(self.owner, self.method_fn, self.instance, args, kwargs)


	def activate(self):
		original_methods = {}
		for cls in self.srcs:
			if cls is not object:
				for name in self.method_names:
					if name in cls.__dict__:
						original_methods[cls, name] = getattr(cls, name)
						setattr(cls, name, self.capture_context(cls, original_methods[cls, name], self.fn))
		self.original_methods = original_methods
		return self

	class NotActivatedError(ValueError): pass

	def deactivate(self):
		if self.original_methods is None:
			raise self.NotActivatedError('cannot deactivate a dynamic capture that has not been activated')
		for (cls, name), original in self.original_methods.items():
			setattr(cls, name, original)

	def __enter__(self):
		return self.activate()

	def __exit__(self, exc_type, exc_val, exc_tb):
		self.deactivate()
		# return exc_type, exc_val, exc_tb


class simple_dynamic_capture(dynamic_capture):
	def __init__(self, target: Type[T], fn: Callable[[Type, Callable, T, Tuple, Dict[str, Any]], Any],
	             *method_names: str, full_bases: Optional[bool] = False, full_mro: Optional[bool] = False):
		super().__init__(target.mro() if full_mro else target.__bases__ if full_bases else (target,),
		                 fn, *method_names)



class ClassHierarchy:
	_class_hierarchy_root = None
	_class_hierarchy_parent_ref = None
	_class_hierarchy_parent = None
	_class_hierarchy_address = ()
	_class_hierarchy_children = None

	def __init_subclass__(cls, ident=None, as_branch=False, new_hierarchy=None, **kwargs):
		super().__init_subclass__(**kwargs)
		if new_hierarchy is None:
			new_hierarchy = cls._class_hierarchy_parent_ref is None
		if new_hierarchy:
			cls._class_hierarchy_root = cls
			cls._class_hierarchy_parent = None
			cls._class_hierarchy_parent_ref = cls
			cls._class_hierarchy_children = OrderedDict()
		else:
			cls._class_hierarchy_parent = cls._class_hierarchy_parent_ref
			if ident is not None:
				cls._class_hierarchy_children[ident] = cls
			if as_branch:
				cls._class_hierarchy_parent_ref = cls
				cls._class_hierarchy_children = OrderedDict()
			cls._class_hierarchy_address = (*cls._class_hierarchy_address, as_branch)



class smartproperty:
	unknown = object()

	def __init__(self, *, name=None, src=None, cache=False, fget=None, fset=None, fdel=None, doc=None):
		# super().__init__(fget=fget, **kwargs)
		self.name = name
		self.src = src

		self.cache = cache
		self.cached_value = self.unknown # only for the class property

		self.fget = fget
		self.fset = fset
		self.fdel = fdel
		self.doc = doc

		self._during_getter = False
		self._during_setter = False
		self._during_deleter = False

	def copy(self, src=unspecified_argument, name=unspecified_argument,
	         default=unspecified_argument, cache=unspecified_argument,
	         fget=unspecified_argument, fset=unspecified_argument, fdel=unspecified_argument, doc=unspecified_argument,
	         **kwargs):
		if src is unspecified_argument:
			src = self.src
		if name is unspecified_argument:
			name = self.name
		if default is unspecified_argument:
			default = self.default
		if cache is unspecified_argument:
			cache = self.cache
		if fget is unspecified_argument:
			fget = self.fget
		if fset is unspecified_argument:
			fset = self.fset
		if fdel is unspecified_argument:
			fdel = self.fdel
		if doc is unspecified_argument:
			doc = self.__doc__
		return type(self)(name=name, src=src, default=default, cache=cache,
		                  fget=fget, fset=fset, fdel=fdel, doc=doc, **kwargs)

	def __set_name__(self, owner, name):
		if self.src is not None and owner is not self.src:
			setattr(owner, name, self.copy(src=owner, name=name))
		else:
			if self.name is None: # TODO: test with using subsequent .setter as with properties
				self.name = name
			self.src = owner
			setattr(owner, name, self)

	def __call__(self, fget: Callable[[], Any]) -> 'smartproperty':
		return self.getter(fget)

	def getter(self, fget: Callable[[], Any]) -> 'smartproperty':
		self.fget = fget
		return self

	def setter(self, fset: Callable[[Any], None]) -> 'smartproperty':
		self.fset = fset
		return self

	def deleter(self, fdel: Callable[[], None]) -> 'smartproperty':
		self.fdel = fdel
		return self

	def __get__(self, instance, owner=None):
		return self.get_value(instance, owner)

	def __set__(self, instance, value) -> None:
		self.update_value(instance, value)

	def __delete__(self, instance):  # TODO: test this
		self.reset(instance)

	class MissingValueError(AttributeError):
		def __init__(self, base, name, *, msg=None):
			basename = base.__name__ if isinstance(base, type) else base.__class__.__name__
			super().__init__(f'{basename}.{name} has no value' if msg is None else msg)

	class GetterFailedError(MissingValueError):
		def __init__(self, base, name=None, *, msg=None):
			basename = base.__name__ if isinstance(base, type) else base.__class__.__name__
			super().__init__(f'{basename}{"" if name is None else "."+name}' if msg is None else msg)

	# class SetterFailedError(TypeError):
	# 	def __init__(self, base, name=None, value=None, *, msg=None):
	# 		basename = base.__name__ if isinstance(base, type) else base.__class__.__name__
	# 		super().__init__(f'{basename}{"" if name is None else "."+name} setter failed' if msg is None else msg)
	#
	# class DeleterFailedError(TypeError):
	# 	def __init__(self, base, name=None, *, msg=None):
	# 		basename = base.__name__ if isinstance(base, type) else base.__class__.__name__
	# 		super().__init__(f'{basename}{"" if name is None else "."+name} deleter failed' if msg is None else msg)

	@staticmethod
	def _call_descriptor(fn, instance, owner, *args, **kwargs):
		getter = getattr(fn, '__get__', None)
		if getter is not None:
			fn = getter(instance, owner)
		return fn(*args, **kwargs)

	def create_value(self, base, owner=None):
		if self.fget is None:
			raise self.MissingValueError(base, self.name)
		try:
			return self._call_descriptor(self.fget, base, owner)
		except self.GetterFailedError:
			raise self.MissingValueError(base, self.name) from None

	def _set_cached_value(self, base, value):
		if base is self.src:
			self.cached_value = value
			return
		elif isinstance(base, type):
			raise NotImplementedError

		setter = getattr(base, '__setattr__', None)
		if setter is not None and not self._during_setter:
			self._during_setter = True
			setter(self.name, value)
			self._during_setter = False
		else:
			# raise AttributeError(f'cannot cache attribute {self.name} of {base}')
			# raise NotImplementedError
			cache = getattr(base, '__dict__', None)
			if cache is None or self.name is None:
				raise AttributeError(f'cannot cache attribute {self.name} of {base}')
			if cache is not None:
				cache[self.name] = value

	def is_cached(self, base):
		return self._get_cached_value(base) is not self.unknown

	def _get_cached_value(self, base):
		if base is self.src:
			return self.cached_value
		elif isinstance(base, type):
			raise NotImplementedError

		getter = getattr(base, '__getattr__', None)
		if getter is not None and not self._during_getter:
			self._during_getter = True
			try:
				value = getter(self.name)
			except AttributeError:
				pass
			else:
				return value
			finally:
				self._during_getter = False

		cache = getattr(base, '__dict__', None)
		if cache is None:
			return self.unknown
		return cache.get(self.name, self.unknown)

	def _clear_cache(self, base):
		if base is self.src:
			self.cached_value = self.unknown
			return
		elif isinstance(base, type):
			raise NotImplementedError

		deleter = getattr(base, '__delattr__', None)
		if deleter is not None and not self._during_deleter:
			self._during_deleter = True
			deleter(self.name)
			self._during_deleter = False
			return
		else:
			# raise AttributeError(f'cannot reset attribute {self.name} of {base}')
			# raise NotImplementedError
			cache = getattr(base, '__dict__', None)
			if cache is None or self.name is None:
				raise AttributeError(f'cannot reset attribute {self.name} of {base}')
			if cache is not None:
				cache.pop(self.name, None)

	def get_value(self, base, owner=None): # TODO: maybe make thread-safe by using a lock
		'''
		Check cache of base first, if that fails, then try getter function

		Args:
			base: instance or type to get value from
			owner: type of instance if it is provided

		Returns:
			value of property

		'''
		value = self._get_cached_value(base)
		if value is self.unknown:
			value = self.create_value(base, owner)
			if self.cache:
				self._set_cached_value(base, value)
		return value
		
	def update_value(self, base, value):
		'''Try manually specified setter function, if that fails, then try to set value in cache'''
		if self.fset is None:
			self._set_cached_value(base, value)
		else:
			return self._call_descriptor(self.fset, base, None, value)

	def reset(self, base):
		if self.fdel is None:
			self._clear_cache(base)
		else:
			return self._call_descriptor(self.fdel, base, None)



# class cachedproperty(smartproperty):
# 	def __init__(self, fget: Callable[[], Any] = None, *, cache=False, **kwargs):
# 		super().__init__(fget=fget, **kwargs)
# 		self.cache = cache
# 		self.cached_value = self.unknown
#
# 	def _get_cached_value(self, base):
# 		if base is self.src:
# 			return self.cached_value
# 		return super()._get_cached_value(base)
#
# 	def _set_cached_value(self, base, value):
# 		if base is self.src:
# 			self.cached_value = value
# 		else:
# 			super()._set_cached_value(base, value)
#
# 	def _clear_cache(self, base):
# 		if base is self.src:
# 			self.cached_value = self.unknown
# 		else:
# 			super()._clear_cache(base)
#
# 	def get_value(self, base, owner=None):
# 		value = self._get_cached_value(base)
# 		if value is self.unknown:
# 			value = self.create_value(base, owner)
# 			if self.cache:
# 				self._set_cached_value(base, value)
# 		return value


class autoproperty(smartproperty): # agnostic to whether it is a class or instance attribute
	def _get_base(self, instance, owner=None):
		return owner if instance is None else instance

	def __get__(self, instance, owner=None):
		return self.get_value(self._get_base(instance, owner), owner)

	def __set__(self, instance, value) -> None:
		self.update_value(self._get_base(instance), value)

	def __delete__(self, instance):  # TODO: test this
		self.reset(self._get_base(instance))
	
	
class _referenceproperty_target:
	def __init__(self, prop, base):
		self.prop = prop
		self.base = base

	def _get_reference(self):
		ref = getattr(self.base, self.prop.ref_name, None)
		# if ref is None:
		# 	raise self.prop.MissingReferenceError(f'{self.base} has no reference to {self.prop.ref_name}')
		return ref

	@staticmethod
	def target_call(ref, *args, **kwargs):
		raise NotImplementedError

	def __call__(self, *args, **kwargs):
		return self.target_call(self._get_reference(), *args, **kwargs)


class referenceproperty(smartproperty):

	class MissingReferenceError(AttributeError):
		pass
	
	class _reference_getter(_referenceproperty_target):
		def target_call(self, ref):
			if ref is None:
				raise self.prop.GetterFailedError(self.base, self.prop.name)
			return getattr(ref, self.prop.name)
	
	class _reference_setter(_referenceproperty_target):
		def target_call(self, ref, value):
			setattr(ref, self.prop.name, value)
	
	class _reference_deleter(_referenceproperty_target):
		def target_call(self, ref):
			delattr(ref, self.prop.name)
	
	class _reference_descriptor:
		def __init__(self, prop, target):
			self.prop = prop
			self.target = target

		def __get__(self, instance, owner=None):
			return self.target(self.prop, instance)

	def __init__(self, ref_key: str, *, use_getter=True, use_setter=False, use_deleter=False, **kwargs):
		super().__init__(**kwargs)
		self.ref_key = ref_key
		self.use_getter = use_getter
		self.use_setter = use_setter
		self.use_deleter = use_deleter
		
	@property
	def fget(self):
		if self._fget is None and self.use_getter:
			return self._reference_descriptor(self, self._reference_getter)
		return self._fget
	@fget.setter
	def fget(self, value):
		self._fget = value
	
	@property
	def fset(self):
		if self._fset is None and self.use_setter:
			return self._reference_descriptor(self, self._reference_setter)
		return self._fset
	@fset.setter
	def fset(self, value):
		self._fset = value
	
	@property
	def fdel(self):
		if self._fdel is None and self.use_deleter:
			return self._reference_descriptor(self, self._reference_deleter)
		return self._fdel
	@fdel.setter
	def fdel(self, value):
		self._fdel = value
	


class defaultproperty(smartproperty):
	def __init__(self, default=unspecified_argument, *, fget=unspecified_argument, **kwargs):
		if default is unspecified_argument:
			default = self.unknown
		fget, default = self._check_fget(fget, default)
		super().__init__(fget=fget, **kwargs)
		self.default = default

	def _check_fget(self, fget=unspecified_argument, default=unspecified_argument):
		if fget is unspecified_argument:
			if callable(default) and not isinstance(default, type) and default.__qualname__ != default.__name__:
				return default, unspecified_argument  # decorator has no other args
			return None, default  # no fget provided (optionally can be added with __call__)
		return fget, default  # fget was specified as keyword argument


	def get_value(self, base, owner=None): # TODO: maybe make thread-safe by using a lock
		try:
			return super().get_value(base, owner)
		except self.MissingValueError:
			if self.default is self.unknown:
				raise
			return self.default

	# def create_value(self, base, owner=None): # TODO: maybe make thread-safe by using a lock
	# 	try:
	# 		return super().create_value(base, owner)
	# 	except self.MissingValueError:
	# 		if self.default is self.unknown:
	# 			raise
	# 		return self.default


from .utils import split_dict


class TrackSmart:
	def _extract_smart_properties(self, kwargs, *, src=None):
		if src is None:
			src = dict(self._my_smart_properties())
		found, remaining = split_dict(kwargs, src)
		for key, val in found.items():
			setattr(self, key, val)
		return remaining

	def _get_property(self, name, default=unspecified_argument):
		try:
			return inspect.getattr_static(self, name)
		except AttributeError:
			if default is unspecified_argument:
				raise
			return default

	# def _fill_smart_properties(self, kwargs, *, src=None):
	# 	if src is None:
	# 		src = dict(self._my_smart_properties())
	# 	for key, val in src.items():
	# 		if key not in kwargs:
	# 			kwargs[key] = val

	@classmethod
	def _my_smart_properties(cls):
		for name, value in cls.__dict__.items():
			if isinstance(value, smartproperty):
				yield name, value

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **self._extract_smart_properties(kwargs))


class Tracer(tuple):
	def append(self, term):
		return self.__class__((self, term))

	def extend(self, terms):
		for term in terms:
			self = self.append(term)
		return self

	def back(self, n=1, strict=True):
		if n == 0:
			return self
		if n < 0:
			raise ValueError('n must be >= 0')
		if not self:
			if strict:
				raise IndexError('cannot go back from empty tracer')
			return self
		return self[0].back(n - 1)

	@property
	def path(self):
		if len(self):
			return self[0].path + (self[1],)
		return ()



def inject_modifiers(base, *mods, name=None):
	'''
	Mods should be types that are used to modify the cls. The order of the mods corresponds to the order
	in which the cls is "modified", so for example:

	```python

	class A(Modifiable): pass
	class B: pass
	class C: pass

	out = A.inject_mods(B, C)
	assert out.mro() == [out, C, B, A, Modifiable, object]
	assert out.__name__ == 'C_B_A' # default name
	```
	'''
	if len(mods):
		bases = (*reversed(mods), base)
		if name is None:
			name = '_'.join(base.__name__ for base in bases)
		return type(name, bases, {})
	return base


class Modifiable:
	@classmethod
	def inject_mods(cls, *mods, name=None):
		'''
		Mods should be types that are used to modify the cls. The order of the mods corresponds to the order
		in which the cls is "modified", so for example:

		```python

		class A(Modifiable): pass
		class B: pass
		class C: pass

		out = A.inject_mods(B, C)
		assert out.mro() == [out, C, B, A, Modifiable, object]
		assert out.__name__ == 'C_B_A' # default name
		```
		'''
		return inject_modifiers(cls, *mods, name=name)

	# @classmethod
	# def __new_mod__(cls, mods, *args, **kwargs):
	# 	if isinstance(mods, str):
	# 		mods = (mods,)
	# 	return cls.inject_mods(*mods)(*args, **kwargs)


# class old_auto_init(capturable_method):
# 	def __init_subclass__(cls, **kwargs):
# 		super().__init_subclass__(**kwargs)
# 		if '__init__' in cls.__dict__:
# 			cls.__init__ = captured_method(cls.__init__).setup(cls)
#
#
# 	class _init_arg_fixer:
# 		def __init__(self, src: Type, obj: 'old_auto_init', **kwargs):
# 			super().__init__(**kwargs)
# 			self.src = src
# 			self.obj = obj
#
# 		def __call__(self, key: str, default: Optional[Any] = inspect.Parameter.empty) -> Any:
# 			raise KeyError(key)
#
#
# 	def _auto_init(self, src: Type, init_fn: Callable, args: Tuple, kwargs: Dict[str, Any]) -> None:
# 		fixed_args, fixed_kwargs = extract_function_signature(init_fn, (self, *args), kwargs,
# 															  default_fn=self._init_arg_fixer(src, self))
# 		return init_fn(*fixed_args, **fixed_kwargs)
#
#
# 	def captured_method_call(self, src: Type, fn: Callable, args: Tuple, kwargs: Dict[str, Any]) -> Any:
# 		if fn.__name__ == '__init__':
# 			return self._auto_init(src, fn, args, kwargs)
# 		return super().captured_method_call(src, fn, args, kwargs)




# Example usage:

# class A(Capturable):
#     def captured_super_call(self, src, name, args, kwargs):
#         print('!! captured super', self, src, name, args, kwargs)
#         return super().captured_super_call(src, name, args, kwargs)
#
#     def captured_method_call(self, src, fn, args, kwargs):
#         print('!! captured method', self, src, fn, args, kwargs)
#         return super().captured_method_call(src, fn, args, kwargs)
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
# class C(B):
#     @captured
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
#     @captured
#     def f(self, a=5):
#         print('E.f', self, a)
#         super().f()
#
# class F(E):
#     def f(self, a=6):
#         print('F.f', self, a)
#         super().f()
#
# class G(F):
#     pass
#
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
# print()
# G().f()

###################################################




class self_aware:
	def __init__(self, cls: Type) -> None:
		self.cls = cls

	def __set_name__(self, owner: Type, name: str) -> None:
		self.cls.owner = owner
		setattr(owner, name, self.cls)



class _meta_clsdec(type):
	def __getattr__(self, key: str) -> '_meta_clsdec':
		self.key = key
		return self



class clsdec(metaclass=_meta_clsdec):
	def __init__(self, *args: Any, **kwargs: Any) -> None:
		self.args, self.kwargs = args, kwargs


	def __call__(self, fn: Callable) -> 'clsdec':
		self.fn = fn
		return self


	def __set_name__(self, obj: Any, name: str) -> None:
		setattr(obj, name, getattr(obj, self.key)(*self.args, **self.kwargs)(self.fn))



class innerchild:
	def __init__(self, cls: Type) -> None:
		self.cls = cls


	class MissingParent(Exception):
		def __init__(self, base: Type, name: str) -> None:
			super().__init__(f'{base.__name__} has not inner class {name}')


	def __set_name__(self, owner: Type, name: str) -> None:
		cls_name = self.cls.__name__
		parent = getattr(super(owner, owner), cls_name, None)
		if parent is None:
			raise self.MissingParent(owner, cls_name)
		child = type(cls_name, (self.cls, parent), {})
		setattr(owner, name, child)


from inspect import Parameter

def deep_method_finder(typ: Type, method: str, *, break_fn: Callable[[Type],bool] = None) -> Iterator[Callable]:
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

def collect_init_kwargs(typ: Type, default: Any = Parameter.empty, *, end_type: Union[Sequence[Type], Type] = None,
						ignore_positional_only=False, break_fn=None):
	if break_fn is None:
		if end_type is not None and isinstance(end_type, type):
			end_type = {end_type,}
		break_fn = (lambda cls: True) if end_type is None else (lambda cls: cls in end_type)
	return collect_fn_kwargs(*deep_method_finder(typ, method='__init__', break_fn=break_fn),
							 default=default, ignore_positional_only=ignore_positional_only)



def args2kwargs(fn: Callable, args: Tuple = None, kwargs: Dict[str, Any] = None, *,
                ignore_positional_only: bool = False, include_missing: bool = False) -> Dict[str, Any]:
	return extract_function_signature(fn, args, kwargs, allow_positional=False, include_missing=include_missing,
	                                  force_no_positional=not ignore_positional_only)


	
def extract_function_signature(fn: Union[Callable, Type],
                               args: Optional[Tuple] = None, kwargs: Optional[Dict[str, Any]] = None, *,
                               default_fn: Callable[[str, Any], Any] = None, include_missing: bool = False,
							   allow_rest: bool = True,
                               allow_positional: bool = True, force_no_positional: bool = False, skip_first=None) \
		-> Union[Tuple[List[Any], Dict[str, Any], List[inspect.Parameter]],
		         Tuple[List[Any], Dict[str, Any]],
		         Dict[str, Any]]:
	if args is None:
		args = ()
	if kwargs is None:
		kwargs = {}

	if isinstance(fn, type):
		fn = fn.__init__
		skip_first = skip_first is not False

	params = inspect.signature(fn).parameters
	if skip_first:
		params = list(params.values())[1:]
		params = {param.name: param for param in params}

	arg_idx = 0
	fixed_args = []
	fixed_kwargs = {}

	collect_rest = False

	missing = []

	for n, p in params.items():
		if p.kind == p.POSITIONAL_ONLY:
			if not allow_positional or force_no_positional:
				raise TypeError(f'Function {fn.__name__} has a positional only argument ({n})')
			if arg_idx < len(args):
				fixed_args.append(args[arg_idx])
				arg_idx += 1
			else:
				if default_fn is None:
					if p.default is p.empty:
						missing.append(p)
					else:
						fixed_args.append(p.default)
				else:
					val = default_fn(n, p.default)
					if val is p.empty:
						missing.append(p)
					else:
						fixed_args.append(val)

		elif p.kind == p.VAR_POSITIONAL:
			if force_no_positional:
				raise TypeError(f'Function {fn.__name__} has variable positional arguments ({n})')
				# continue
			if default_fn is None:
				fixed_args.extend(args[arg_idx:])
				arg_idx = len(args)
			else:
				val = default_fn(n, [])
				fixed_args.extend(val)

		elif p.kind == p.VAR_KEYWORD:
			collect_rest = True
			if default_fn is None:
				fixed_kwargs.update(kwargs)
			else:
				val = default_fn(n, {})
				fixed_kwargs.update(val)

		else:
			if n in kwargs:
				fixed_kwargs[n] = kwargs[n]
			elif p.kind != p.KEYWORD_ONLY and arg_idx < len(args):
				# if allow_positional: # Note: removing this to prefer keyword arguments over positional arguments
				# 	fixed_args.append(args[arg_idx])
				# else:
				fixed_kwargs[n] = args[arg_idx]
				arg_idx += 1
			else:
				if default_fn is None:
					if p.default is p.empty:
						missing.append(p)
					else:
						fixed_kwargs[n] = p.default
				else:
					val = default_fn(n, p.default)
					if val is p.empty:
						missing.append(p)
					else:
						fixed_kwargs[n] = val

	if collect_rest and allow_rest:
		fixed_kwargs.update(kwargs)

	if include_missing:
		return fixed_args, fixed_kwargs, missing
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




