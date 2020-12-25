
from collections import OrderedDict
from wrapt import ObjectProxy

class AttrDict(dict):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.__dict__ = self

class AttrOrdDict(OrderedDict):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.__dict__ = self


class Value(ObjectProxy):
	def __init__(self, val):
		self.set(val)
	
	def get(self):
		return self.__wrapped__
	
	def set(self, val):
		self.__wrapped__ = val


def deep_get(tree, keys):
	if isinstance(keys, (tuple, list)):
		if len(keys) == 1:
			return tree[keys[0]]
	return deep_get(tree[keys[0]], keys[1:])



class Simple_Child(object):
	'''a simple wrapper that delegates __getattribute__ to some parent object if it fails'''

	def __init__(self, *args, _parent=None, **kwargs):
		super().__init__(*args, **kwargs)
		self._parent = _parent

	def __getattribute__(self, item):

		try:
			return super().__getattribute__(item)
		except AttributeError as e:
			try: # check the parent first
				parent = super().__getattribute__('_parent')
				return parent.__getattribute__(item)
			except AttributeError:
				raise e






class Proper_Child(object):
	'''a simple wrapper that delegates __getattribute__ to some parent object if it fails'''

	def __init__(self, *args, _parent=None, **kwargs):
		super().__init__(*args, **kwargs)
		self._parent = _parent

	def __getattribute__(self, item):

		try:
			return super().__getattribute__(item)
		except AttributeError as e:
			try:  # check the parent first
				parent = super().__getattribute__('_parent')

				out = parent.__getattribute__(item)

				if hasattr(out, '__self__'):
					# return out.__func__

				# return out

				# cls = parent.__class__

					fn = out.__func__ #cls.__getattribute__(parent, item)

					def _call_ghost(*args, **kwargs):
						return fn(self, *args, **kwargs)

					return _call_ghost
				return out
			except AttributeError:
				try:
					return parent.__getattribute__(item)
				except AttributeError:
					raise e
