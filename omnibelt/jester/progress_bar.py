from .imports import *
from .environment import where_am_i
import io
import tqdm


class AbstractIterator:
	pass


class SimpleIterator(AbstractIterator):
	_no_value = object()
	def __init__(self, source: Iterable | Iterator | int, **kwargs):
		if isinstance(source, int):
			source = range(source)
		super().__init__(**kwargs)
		self.src = source
		self._itr = None
		self._n_gen = 0
		self._cached_value = self._no_value

	def __iter__(self):
		self.prepare()
		return self

	def __next__(self):
		return self.next()

	@property
	def value(self):
		if self._cached_value is self._no_value:
			raise ValueError("No value cached")
		return self._cached_value

	def reset(self):
		self._itr = None
		self._cached_value = self._no_value
		return self

	def prepare(self, parent: AbstractIterator = None):
		if self._itr is None:
			self._prepare()
		return self

	def _prepare(self, parent: AbstractIterator = None):
		self._itr = iter(self.src)
		self._parent = parent

	def next(self):
		if self._itr is None:
			self.prepare()
		if self._n_gen == 0:
			self.start()
		try:
			item = self._next()
		except StopIteration:
			self.finished()
			raise
		self._n_gen += 1
		self._cached_value = item # cache value
		self.record(item) # update description
		return item

	def _next(self):
		return next(self._itr)

	def record(self, item: Any):
		self._cached_value = item
		return item

	def start(self):
		pass

	def finished(self):
		pass

	def branch(self, item: Any) -> Optional[Union[Iterable, AbstractIterator]]:
		pass

	def skip(self, n: int = 1):
		raise NotImplementedError


class EagerIterator(SimpleIterator):
	def __init__(self, source: Iterable | Iterator | int, total: int = None, **kwargs):
		super().__init__(source=source, **kwargs)
		if total is None:
			try:
				total = len(self.src)
			except TypeError:
				self.src = list(self.src)
				total = len(self.src)
		self._total = total

	def __len__(self):
		return self._total



# class logtqdm(tqdm):
# 	def __init__(self, *args, no_pbar: bool = False, log_file: io.StringIO = None, target_log_count: int = 100,
# 				 log_fmt=None, file: io.StringIO = None, **kwargs):
# 		if no_pbar:
# 			assert log_file is not None
# 			file = io.StringIO()
# 		super().__init__(*args, file=file, **kwargs)
# 		self.no_pbar = no_pbar
# 		self.log_file = log_file
# 		self.log_fmt = log_fmt
# 		self.target_log_count = target_log_count
# 		self.prev_log = None
# 		self.log_progress_threshold = None if target_log_count is None else 100. / target_log_count
#
# 	def log(self):
# 		if self.log_fmt is None:
# 			status = self.format_meter(bar_format='{l_bar}{r_bar}', **self.format_dict)
# 		else:
# 			status = self.log_fmt.format(**self.format_dict)
#
# 		self.log_file.write(status + '\n')
# 		self.log_file.flush()
# 		return status
#
# 	def refresh(self, nolock=False, lock_args=None):
# 		# super().refresh(nolock, lock_args)
# 		if (self.log_progress_threshold is None or self.prev_log is None
# 				or self.n / self.total - self.prev_log >= self.log_progress_threshold):
# 			self.log()
# 			self.prev_log = self.n / self.total
# 		if not self.no_pbar:
# 			super().refresh(nolock, lock_args)

class cb_tqdm(tqdm.tqdm):
	def __init__(self, *args, hide: bool = False, file: io.StringIO = None,
				 callback: Callable[['cb_tqdm'], bool] = None, **kwargs):
		if hide:
			assert file is None, f'Cannot hide progress bar and write to file: {file}'
			old_display = self.display
			self.display = lambda *args, **kwargs: 0 # nullop
			file = io.StringIO()
		super().__init__(*args, file=file, **kwargs)
		self._callback = callback

	def refresh(self, nolock=False, lock_args=None):
		if self._callback is None or self._callback(self):
			self.force_refresh(nolock, lock_args)

	def force_refresh(self, nolock=False, lock_args=None):
		super().refresh(nolock, lock_args)


class cb_nbtqdm(cb_tqdm, tqdm.notebook.tqdm):
	pass



class ProgressBarIterator(EagerIterator):
	_envs_no_pbar = {'cluster', 'pytest'}
	_envs_notebook_pbar = {'jupyter', 'colab'}
	_std_tqdm = cb_tqdm
	_nb_tqdm = cb_nbtqdm

	def __init__(self, source: Iterable | Iterator | int, total: int = None, *,
				 desc: Optional[str] = None, leave: Optional[bool] = True,
				 log_file: Optional[Union[str, io.TextIOBase]] = None,
				 no_display: bool = False, force_display: bool = False,
				 print_msgs: int = 100, **kwargs):
		super().__init__(source, total=total, **kwargs)
		assert not (no_display and force_display), "Cannot have both 'no_display' and 'force_display' set to True"
		self._env = where_am_i()
		self._pbar = None
		self._leave = leave
		self._desc = desc
		self._log_progress_threshold = None if print_msgs is None else 1. / print_msgs
		self.log_file = log_file
		self._no_display = no_display
		self._force_display = force_display

	@property
	def is_logging(self):
		return self.log_file is not None

	@property
	def is_displaying(self):
		return not self._no_display and (self._force_display or self._env not in self._envs_no_pbar)

	def reset(self):
		if self._pbar is not None:
			self._pbar.close()
		super().reset()
		return self

	def _prepare(self, parent: AbstractIterator = None):
		self._parent = parent
		pbar_cls = self._nb_tqdm if self._env in self._envs_notebook_pbar else self._std_tqdm
		self._pbar = pbar_cls(self.src, hide=not self.is_displaying, callback=lambda pbar: False,
							 leave=self._leave, desc=self._desc)
		self._itr = iter(self._pbar)
		self._prev_log = None
		return self

	def update(self, force: bool = False):
		pbar = self._pbar
		pbar.force_refresh()
		if force or self.log_file is not None and (self._log_progress_threshold is None or self._prev_log is None
				or pbar.n / pbar.total - self._prev_log >= self._log_progress_threshold):
			info = pbar.format_dict
			info['bar_format'] = '{l_bar}{r_bar}'
			status = pbar.format_meter(**info).replace('||', ' |')
			# status = self.log_fmt.format(**self.format_dict)
			self.log_file.write(status + '\n')
			self.log_file.flush()
			self._prev_log = pbar.n / pbar.total

	def get_start_msg(self):
		if self._desc is not None:
			return f"Starting {self._desc}"

	def get_finished_msg(self):
		pass

	def start(self):
		msg = self.get_start_msg()
		if self.log_file is not None and msg is not None:
			self.log_file.write(msg + '\n')
			self._prev_log = 0

	def finished(self):
		msg = self.get_finished_msg()
		if self.log_file is not None and msg is not None:
			self.log_file.write(msg + '\n')
		else:
			self.update(force=True)
		self._pbar.close()

	def record(self, item: Any):
		self.update()


class CustomProgressBarIterator(ProgressBarIterator):
	def __init__(self, source: Iterable | Iterator | int, *, total: int = None,
				 reporter: Callable[[Any], str] = None, brancher: Callable[[Any], Optional[Iterable]] = None,
				 **kwargs):
		super().__init__(source=source, total=total, **kwargs)
		self._reporter = reporter
		self._brancher = brancher

	def record(self, item: Any):
		pbar = self._pbar
		if self._reporter is not None:
			desc = self._reporter(item, pbar)
			if desc is not None:
				pbar.set_description(str(desc), refresh=False)
		return super().record(pbar)

	def finished(self, msg: str = 'Done'):
		self._pbar.set_description(msg, refresh=False)
		super().finished()

	def branch(self, item: Any) -> Optional[Union[Iterable, AbstractIterator]]:
		if self._brancher is not None:
			child = self._brancher(item)
			return child



class HierarchicalProgressBar:
	class Level(CustomProgressBarIterator):
		@property
		def level(self):
			return self._level
		@level.setter
		def level(self, value):
			self._level = value

		def get_start_msg(self):
			if self.level == 1:
				return super().get_start_msg()
		def get_finished_msg(self, msg: str = None):
			return f"Level {self.level} Done"

	def __init__(self, *, leave_top: bool = True, no_display: bool = False, force_display: bool = False,
				 print_msgs: int = 100, **kwargs):
		super().__init__(**kwargs)
		assert not (no_display and force_display), "Cannot have both 'no_display' and 'force_display' set to True"
		self._hierarchy = []
		self._leave_top = leave_top
		self._no_display = no_display
		self._force_display = force_display
		self._print_msgs = print_msgs

	@property
	def is_displaying(self):
		return any(level.is_displaying for level in self._hierarchy) \
			if len(self._hierarchy) else self._create_level([]).is_displaying

	@property
	def current(self):
		if len(self._hierarchy):
			return self._hierarchy[-1]

	@property
	def leaf(self):
		current = self.current
		if current is not None:
			return getattr(current, 'value', None)

	def _create_level(self, source: Iterable | Iterator | int, leave: bool = None, **kwargs):
		if leave is None:
			leave = self._leave_top and len(self._hierarchy) == 0
		return self.Level(source, no_display=self._no_display, force_display=self._force_display,
						  print_msgs=self._print_msgs, leave=leave, **kwargs)

	def push(self, source: AbstractIterator | Iterable | Iterator | int, *, total: int = None,
			 reporter: Callable[[Any], Optional[str]] = None, brancher: Callable[[Any], Optional[Iterable]] = None,
			 **kwargs):
		item = source if isinstance(source, self.Level) \
			else self._create_level(source, total=total, reporter=reporter, brancher=brancher, **kwargs)
		item.level = len(self._hierarchy) + 1
		self._hierarchy.append(item)
		return self

	def pop(self):
		if len(self._hierarchy):
			self._hierarchy[-1].reset()
			self._hierarchy.pop()
		return self

	def clear(self):
		for item in self._hierarchy:
			item.reset()
		self._hierarchy.clear()
		return self

	def __iter__(self):
		return self

	def __next__(self):
		if self.current is None:
			raise StopIteration
		try:
			item = self.current.next()
		except StopIteration:
			self.pop()
		else:
			branch = self.current.branch(item)
			if branch is None:
				return item
			self.push(branch)
		return self.__next__()






