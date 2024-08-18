from .imports import *
from .environment import where_am_i
import tqdm



class ProgressBar:
	class Container:
		def __init__(self, **kwargs):
			self.__dict__.update(kwargs)

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self._env = where_am_i()
		self._hierarchy = []

	@property
	def current(self):
		if len(self._hierarchy):
			return self._hierarchy[-1]

	@property
	def leaf(self):
		current = self.current
		if current is not None:
			return getattr(current, 'value', None)

	def step(self, n: int = 1):
		if self.current is not None:
			self.current.update(n)
		return self

	def push(self, itr: Container | Iterable | Iterator | int, *, total: int = None,
			 scribe: Callable[[Any], str] = None, seeder: Callable[[Any], Optional[Iterable]] = None, **kwargs):
		if not isinstance(itr, self.Container):
			pbar_cls = tqdm.notebook.tqdm if self._env == 'jupyter' else tqdm.tqdm
			if isinstance(itr, int):
				itr = range(itr)
			pbar = pbar_cls(itr, total=total, leave=False, desc=scribe if isinstance(scribe, str) else None, **kwargs)
			if isinstance(scribe, str):
				scribe = None
			item = self.Container(itr=iter(pbar), pbar=pbar, src=itr, seeder=seeder, scribe=scribe)
		self._hierarchy.append(item)
		return self

	def pop(self):
		if len(self._hierarchy):
			self._hierarchy[-1].itr.close()
			self._hierarchy.pop()
		return self

	def clear(self):
		for item in self._hierarchy:
			item.itr.close()
		self._hierarchy.clear()
		return self

	def __iter__(self):
		return self

	def __next__(self):
		if self.current is None:
			raise StopIteration
		try:
			item = next(self.current.itr)
			# cache value
			self.current.value = item
			# update description
			if self.current.scribe is not None:
				self.current.itr.set_description(self.current.scribe(item))
			# check if this item has children
			if self.current.seeder is not None:
				child = self.current.seeder(item)
				if child is not None:
					self.push(child)
					return self.__next__()
			return item
		except StopIteration:
			self.pop()
			return self.__next__()











