from .imports import *
import json, yaml
import pandas as pd
from .environment import where_am_i
from .progress_bar import HierarchicalProgressBar, ProgressBarIterator, CustomProgressBarIterator

# import h5py as hdf
# try:
#     from datasets import load_dataset
# except ImportError:
#     load_dataset = None


class FileJester:
	def __init__(self, src: Union[Path, str], *, lazy: bool = False):
		if lazy:
			raise NotImplementedError("Lazy loading is not yet implemented")
		if isinstance(src, str):
			src = Path(src)
		self.src = src
		self._root = None
		self._count = None
		self._files = None

	def __repr__(self):
		self.prepare()
		return f'[{self.remaining}/{len(self)} paths in {self._root}]'

	def _extract_root(self, path: Path):
		path = path.expanduser().resolve()
		return path if path.exists() else self._extract_root(path.parent)

	def analyze(self, src: Path) -> Tuple[Path, int, Union[Path, List[Path]]]:
		if src.exists():
			if src.is_dir():
				raise ValueError("The 'src' parameter must be a file or pattern, not a directory")
			else:
				return src.parent, 1, src

		root = self._extract_root(src)
		pattern = src.relative_to(root)
		children = list(root.glob(str(pattern)))

		if len(children) == 0:
			raise FileNotFoundError(f"'{pattern}' in {root}")
		if len(children) == 1:
			return root, 1, children
		return root, len(children), children

	def prepare(self):
		if self._count is None:
			self._root, self._count, self._files = self.analyze(self.src)
			self._index = 0

	def __next__(self):
		if self._index < self._count:
			self._index += 1
			return self._files[self._index - 1]
		raise StopIteration

	def __iter__(self):
		self.prepare()
		return self

	def peek(self):
		self.prepare()
		return self._files[self._index]

	def __len__(self):
		self.prepare()
		return self._count

	@property
	def root(self):
		self.prepare()
		return self._root

	@property
	def remaining(self):
		self.prepare()
		return self._count - self._index



class AutoFileJester(FileJester):
	def __init__(self, src: Union[Path, str], ext: str = None,
				 *, recursive: bool = True, lazy: bool = False, **kwargs):
		super().__init__(src, lazy=lazy, **kwargs)
		self.ext = ext
		self.recursive = recursive

	def prepare(self):
		if self._count is None:
			self._root, self._count, self._files = self.analyze(self.src, ext=self.ext, recursive=self.recursive)
			self._index = 0

	def analyze(self, src: Path, ext: Optional[str] = None, *,
				recursive: bool = True) -> Tuple[Path, int, Union[Path, List[Path]]]:
		if src.is_dir():
			if ext is None:
				raise ValueError("The 'ext' parameter must be provided when the source is a directory")
			src = src / f'{"**/" if recursive else ""}*.{ext}'
		return super().analyze(src)



class MultiFileJester(FileJester):
	def __init__(self, src: Union[Path, str, Iterable[Union[Path, str]]], *, lazy: bool = False, **kwargs):
		if isinstance(src, (Path, str)):
			src = [src]
		if not isinstance(src, Path):
			src = [Path(s) for s in src]
		super().__init__(src, lazy=lazy, **kwargs)


	def include(self, src: Union[Path, str, Iterable[Union[Path, str]]]):
		if isinstance(src, str):
			src = Path(src)
		if not isinstance(src, Path):
			src = [Path(s) for s in src]
		self.src.extend(src)


	def analyze(self, src: Union[Path, Iterable[Path]]) -> Tuple[Path, int, Union[Path, List[Path]]]:
		if isinstance(src, Path):
			return super().analyze(src)

		assert isinstance(src, Iterable), "The 'src' parameter must be a Path, str, or Iterable of Paths or strings"
		roots, counts, branches = zip(*[self.analyze(branch) for branch in src])
		root = min(roots, key=lambda r: len(str(r)))
		return root, sum(counts), [item for branch in branches for item in branch]
        


class Jester(MultiFileJester):
	_ProgressBar = HierarchicalProgressBar

	class _FileLevel(ProgressBarIterator):
		def __init__(self, paths: Iterable[Path], root: Path, loader: Callable, **kwargs):
			super().__init__(paths, **kwargs)
			self._root = root
			self._loader = loader

		def get_start_msg(self):
			return f'Loading {self._total} in {self._root}'
		def get_finished_msg(self, msg: str = None):
			return f"Done with {self._total} files in {self._root}"

		def branch(self, item: Path):
			return self._loader(item)

		def record(self, item: Path):
			desc = item.relative_to(self._root)
			self._pbar.set_description(str(desc), refresh=False)
			self.update()

	class _ItemLevel(CustomProgressBarIterator):
		def __init__(self, items: Iterable, leave: bool = False, **kwargs):
			super().__init__(items, leave=leave, **kwargs)

	def __init__(self, src: Union[Path, str, Iterable[Union[Path, str]]], *,
				 log_file: 'TextIO' = None, file_print_msgs: int = None, item_print_msgs: int = 10,
				 no_display: bool = None, force_display: bool = None, **kwargs):
		super().__init__(src, **kwargs)
		self.pbar = self._ProgressBar()
		self._log_file = log_file
		self._no_display = no_display
		self._force_display = force_display
		self._file_print_msgs = file_print_msgs
		self._item_print_msgs = item_print_msgs

	@staticmethod
	def load(path: Path):
		if path.suffix == '.json':
			return json.load(path.open('r'))
		if path.suffix == '.jsonl':
			return [json.loads(line) for line in path.open('r') if len(line)]

		if path.suffix == '.yaml':
			return yaml.load(path.open(), Loader=yaml.FullLoader)
		if path.suffix == '.yamll':
			return [yaml.load(line, Loader=yaml.FullLoader) for line in path.open('r') if len(line)]

		if path.suffix == '.csv':
			df = pd.read_csv(path)
			return [{k: (None if v != v else v) for k, v in row.items()}
					for _, row in df.iterrows()]
		if path.suffix == '.tsv':
			df = pd.read_csv(path, sep='\t')
			return [{k: (None if v != v else v) for k, v in row.items()}
					for _, row in df.iterrows()]

		raise ValueError(f'{path}')

	def _load_branch(self, path: Path):
		items = self.load(path)
		return self._ItemLevel(items, log_file=self._log_file, no_display=self._no_display,
							   force_display=self._force_display, print_msgs=self._item_print_msgs)

	def __iter__(self):
		self.prepare()
		return self.pbar.push(self._FileLevel(
			self._files, root=self._root, loader=self._load_branch, total=self._count,
			log_file=self._log_file, no_display=self._no_display, force_display=self._force_display,
			print_msgs=self._file_print_msgs))


