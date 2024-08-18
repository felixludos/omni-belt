from .imports import *
from .environment import where_am_i

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
		super().__init__(src, lazy=lazy)


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
		roots, counts, branches = zip(*[self.analyze(branch, includeupper=includeupper) for branch in src])
		root = min(roots, key=lambda r: len(str(r)))
		return root, sum(counts), list(branches)
        


