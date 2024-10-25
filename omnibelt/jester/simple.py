from .imports import *
from .environment import where_am_i
import io
import time
import tqdm


class Jester:
	_empty = object()
	_envs_no_pbar = {'cluster', 'pytest'}
	_envs_notebook_pbar = {'jupyter', 'colab'}
	_std_tqdm = tqdm.tqdm
	_nb_tqdm = tqdm.notebook.tqdm

	def __init__(self, src: Iterable[Any] | Path, *, log: Optional[io.StringIO] = None, pbar: bool = True,
				 brancher: Optional[Callable[[Any], Optional[Iterable[Any]]]] = None,
				 reporter: Optional[Callable[[Any], Optional[str]]] = None, count_level: int = 0,
				 sig_sec: float = 0.1, lazy: bool = False,
				 top_only: bool = False, bottom_only: bool = False, no_cache: bool = False, **kwargs):
		super().__init__(**kwargs)
		self._src = src
		self._log_file = log
		self._brancher = brancher
		self._reporter = reporter
		self._count_level = count_level
		self._no_cache = no_cache
		self._top_only = top_only # pbar
		self._bottom_only = bottom_only # pbar
		self._lazy = lazy

		if self._brancher is None:
			self._brancher = ()
		elif callable(self._brancher):
			self._brancher = (self._brancher,)
		elif isinstance(self._brancher, tuple):
			pass
		elif isinstance(self._brancher, Iterable):
			self._brancher = tuple(self._brancher)

		if lazy:
			raise NotImplementedError("Lazy mode is not yet implemented")

		self._env = where_am_i()
		self._ready = False
		self._total = None
		self._total_count = 0
		self._pbar = [] if pbar else None
		self._work = None
		self._skipped = None
		self._waiting = self._empty
		self._sig_sec_threshold = sig_sec
		self._stack = []
		self._cache = []
		self._count = []
		self._sig_n = []
		self._sig_t = []

	def __iter__(self):
		self._prepare()
		return self

	def __next__(self):
		return self._next()

	@property
	def use_pbar(self):
		return self._pbar is not None

	@property
	def live(self):
		return len(self._stack) > 0

	@property
	def remaining_top(self):
		if self.live:
			return self._total - self._count[0]

	@property
	def remaining(self):
		if self.live:
			return self._ - self._count[-1]

	def reset(self):
		self._ready = False
		self._total_count = 0
		self._work = None
		self._skipped = None
		self._stack.clear()
		self._cache.clear()
		self._count.clear()
		if self.use_pbar:
			self._pbar.clear()
		self._waiting = self._empty
		return self

	def __repr__(self):
		if self.live:
			return f'[ {self.remaining}/{len(self)} in {self._src} ]'
		try:
			num = len(self)
		except TypeError:
			return f'[ {self._src} ]'
		else:
			return f'[{num} in {self._src}]'

	class _Branch(tuple):
		pass

	def _analyze(self, src: Iterable[Any], branchers: List[Callable[[Any], Optional[Iterable[Any]]]]):
		if isinstance(src, str):
			src = Path(src)
		if isinstance(src, Path):
			if src.is_file():
				src = [src]
			elif src.is_dir():
				src = src.glob('*')
			elif src.parent.is_dir():
				src = src.parent.glob(src.name)
			elif src.parent.parent.is_dir():
				src = src.parent.parent.glob(f'{src.parent.name}/{src.name}')
			else:
				raise FileNotFoundError(src)
		if branchers:
			brancher = branchers.pop()
			total = 0
			payload = []
			skipped = []
			for item in src:
				branch = brancher(item)
				if branch:
					num, work, notwork = self._analyze(branch, branchers)
					payload.append(self._Branch(num, item, work, notwork))
					total += num
				else:
					skipped.append(item)
			return total, payload, skipped
		try:
			len(src)
		except TypeError:
			items = list(src)
		return len(items), items, None

	def _prepare(self):
		if self._ready: return
		self.reset()

		if self._lazy:
			self._stack.append(iter(self._src))
		else:
			branchers = list(reversed(self._brancher[:self._count_level]))
			self._total, self._work, self._skipped = self._analyze(self._src, branchers)
			self._push_frame(self._work)

		self._ready = True
		self._start(0)

	def _create_pbar(self, **kwargs):
		pbar_cls = self._std_tqdm if self._env in self._envs_no_pbar else self._nb_tqdm
		return pbar_cls(**kwargs)

	def _start(self, level: int):
		if self._log_file is not None:
			msg = self._start_msg(level)
			if msg:
				self._log_file.write(msg + '\n')

		# self._push_frame(self._work, total=self._total)

	def _start_msg(self, level: int = 0):
		pass

	def _log_level(self, level: int, total: int, work: Iterable[Any], skipped: List[Any]):
		pass

	def _finish(self, level: int):
		if self._log_file is not None:
			msg = self._finish_msg()
			if msg:
				self._log_file.write(msg + '\n')

		if self.use_pbar:
			self._pbar[level].close()
			if len(self._pbar)-1 == level:
				self._pbar.pop()

	def _finish_msg(self):
		pass

	def peek(self):
		raise NotImplementedError("Peeking is not yet implemented")
		if not self._ready:
			self._prepare()
		if self._waiting is self._empty:
			self._waiting = self._next()
		return self._waiting

	def _status_signal(self, level: int, item: Any):
		now = time.time()
		if self._sig_t[level] is not None and now - self._sig_t[level] < self._sig_sec_threshold:
			return
		self._sig_t[level] = now
		dt = self._count[level] - self._sig_n[level]
		self._sig_n[level] = self._count[level]
		self._pbar[level].update(dt)
		if self._log_file is not None:
			msg = f'{self._count[level]}: {item}'
			if msg:
				self._log_file.write(msg + '\n')

	def _push_frame(self, src, total: int = None):
		if total is None:
			try:
				total = len(src)
			except TypeError:
				src = list(src)
				total = len(src)
		self._stack.append(iter(src))
		self._count.append(0)
		self._sig_n.append(0)
		self._sig_t.append(None)
		if self.use_pbar:
			self._pbar.append(self._create_pbar(total=total))

	def _pop_frame(self):
		self._cache.pop()
		self._stack.pop()
		self._count.pop()
		self._sig_n.pop()
		self._sig_t.pop()
		if self.use_pbar and len(self._pbar):
			self._pbar[-1].close()
			self._pbar.pop()

	def _next(self):
		if not self.live:
			self._prepare()
		if self._waiting is self._empty:
			level = len(self._stack) - 1
			try:
				item = next(self._stack[level])
			except StopIteration:
				self._finish(level)
				self._pop_frame()
				if self.live:
					return self._next()
				raise
			else:
				self._count[level] += 1
				if len(self._cache):
					self._cache.pop() # remove the last item
				if isinstance(item, self._Branch):
					num, item, work, notwork = item
					self._cache.append(item)
					self._push_frame(work)
					self._start(len(self._stack))
					return self._next()

				if len(self._brancher) > level:
					brancher = self._brancher[level]
					branch = brancher(item)
					if branch:
						self._cache.append(item)
						self._push_frame(branch)
						self._start(len(self._stack))
					return self._next() # either skipped or branched

				self._status_signal(level, item)
				self._cache.append(item)
				self._total_count += 1
				return item
		else:
			raise NotImplementedError("Peeking is not yet implemented")
			out = self._waiting
			self._waiting = self._empty
			return out


	class _Reporter:
		def start(self, level: int, total: Optional[int] = None,
				  work: Optional[Iterable[Any]] = None, skipped: Optional[List[Any]] = None) -> Optional[str]:
			pass

		def finish(self, level: int, total: Optional[int] = None,
				  work: Optional[Iterable[Any]] = None, skipped: Optional[List[Any]] = None) -> Optional[str]:
			pass

		def status(self, item: Any, index: int, total: Optional[int] = None) -> Optional[str]:
			pass















