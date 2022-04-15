

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




