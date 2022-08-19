import inspect


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



class method_wrapper:
	def __init__(self, fn=None):
		self.fn = fn


	def __call__(self, fn):
		self.fn = fn
		return self


	def __get__(self, obj, cls=None):
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
	
	
	
def extract_function_signature(fn, args, kwargs, default_fn):
	params = inspect.signature(fn).parameters
	
	arg_idx = 0
	fixed_args = []
	fixed_kwargs = {}
	
	for n, p in params.items():
		if p.kind == p.POSITIONAL_ONLY:
			if arg_idx < len(args):
				fixed_args.append(args[arg_idx])
				arg_idx += 1
			else:
				try:
					val = default_fn(n)
				except KeyError:
					pass
				else:
					fixed_args.append(val)
		elif p.kind == p.VAR_POSITIONAL:
			try:
				val = default_fn(n)
			except KeyError:
				fixed_args.extend(args[arg_idx:])
				arg_idx = len(args)
			else:
				fixed_args.extend(val)
		elif p.kind == p.VAR_KEYWORD:
			try:
				val = default_fn(n)
			except KeyError:
				fixed_kwargs.update(kwargs)
			else:
				fixed_kwargs.update(val)

		elif p.kind == p.KEYWORD_ONLY:
			if n in kwargs:
				fixed_kwargs[n] = kwargs[n]
			else:
				try:
					val = default_fn(n)
				except KeyError:
					pass
				else:
					fixed_kwargs[n] = val

		else:
			if n in kwargs:
				fixed_kwargs[n] = kwargs[n]
			elif arg_idx < len(args):
				fixed_args.append(args[arg_idx])
				arg_idx += 1
			else:
				try:
					val = default_fn(n)
				except KeyError:
					pass
				else:
					fixed_kwargs[n] = val
	return fixed_args, fixed_kwargs



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




