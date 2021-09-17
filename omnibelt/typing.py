import types


primitives = (str, int, float, bool)



class unspecified_argument:
	@staticmethod
	def __repr__():
		return '[unspecified]'



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

	return new



def duplicate_class(cls, name=None, chain=False):
	if name is None:
		name = cls.__name__

	if chain:
		parents = (cls,)
		data = {}
	else:
		parents = cls.__bases__
		data = dict(cls.__dict__)

	new = type(name, parents, data)
	for attr in new.__dict__:
		if isinstance(getattr(new, attr), types.FunctionType):
			setattr(new, attr, duplicate_func(getattr(new, attr), cls=new))

	return new



# class Template:
# 	def __activate__(self, *args, **kwargs):
# 		pass
# class Template:
# 	def __init_subclass__(cls, **kwargs):
# 		super().__init_subclass__(**kwargs)
# 		cls.__sub_count = 0
#
#
# 	@classmethod
# 	def _gen_sub_template_name(cls):
# 		cls.__sub_count += 1
# 		return f'{cls.__name__}{cls.__sub_count}'
#
#
# 	@classmethod
# 	def _gen_sub_template(cls):
# 		return duplicate_class(cls, cls._gen_sub_template_name())
#
#
# 	def __activate__(self, *args, **kwargs):
# 		pass
#
#
#
# class Wrapper(Template):
# 	@classmethod
# 	def wrap_instance(cls, obj, *args, **kwargs):
# 		new = cls.wrap_class(obj.__class__)
# 		obj.__class__ = new
# 		obj.__activate__(*args, **kwargs)
# 		return obj
#
#
# 	@classmethod
# 	def wrap_class(cls, other):
# 		return cls._gen_sub_template()



_class_subs = {}
def _gen_sub_template_name(cls):
	if cls not in _class_subs:
		_class_subs[cls] = 0
	_class_subs[cls] += 1
	return f'{cls.__name__}{_class_subs[cls]}'



def wrap_class(wrapper, cls, name=None, chain=False):
	if name is None:
		name = wrapper._gen_sub_template_name()
	sub = duplicate_class(wrapper, name, chain=chain)
	return type(f'{sub.__name__}_{obj.__class__.__name__}', (sub, obj.__class__), {})



def wrap_instance(wrapper, obj, chain=False):
	obj.__class__ = wrap_class(wrapper, obj.__class__, chain=chain)
	return obj







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

