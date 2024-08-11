from .imports import *

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


	def _extract_root(self, path: Path):
		path = path.expanduser().resolve()
		return path if path.exists() else self._extract_root(path.parent)


	def analyze(self, src: Path, *, includeupper: bool = True) -> Tuple[Path, int, Union[Path, List[Path]]]:
		if src.exists():
			if src.is_dir():
				raise ValueError("The 'src' parameter must be a file or pattern, not a directory")
			else:
				return src.parent, 1, src

		root = self._extract_root(src)
		pattern = src.relative_to(root)
		children = list(root.glob(str(pattern)))
		if includeupper:
			base = pattern.parent / pattern.stem
			ext = pattern.suffix
			children.extend(root.glob(base.with_suffix(ext.upper())))
			children = sorted(children)

		if len(children) == 0:
			raise FileNotFoundError(f"'{pattern}' in {root}")
		if len(children) == 1:
			return root, 1, children[0]
		return root, len(children), children


	def peek(self):
		raise NotImplemented


	def __iter__(self):
		return self.flow()


	def __len__(self):
		raise NotImplemented


	def flow(self):
		raise NotImplemented



class AutoFileJester(FileJester):
	def __init__(self, src: Union[Path, str], ext: str = None,
				 *, recursive: bool = True, lazy: bool = False, **kwargs):
		super().__init__(src, lazy=lazy, **kwargs)
		self.ext = ext
		self.recursive = recursive


	def analyze(self, src: Path, ext: Optional[str] = None, *,
				recursive: bool = True, includeupper: bool = True) -> Tuple[Path, int, Union[Path, List[Path]]]:
		if src.is_dir():
			if ext is None:
				raise ValueError("The 'ext' parameter must be provided when the source is a directory")
			src = src / f'{"**/" if recursive else ""}*.{ext}'
		return super().analyze(src, includeupper=includeupper)



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


	def analyze(self, src: Union[Path, Iterable[Path]], *,
				includeupper: bool = True) -> Tuple[Path, int, Union[Path, List[Path]]]:
		if isinstance(src, Path):
			return super().analyze(src, includeupper=includeupper)

		assert isinstance(src, Iterable), "The 'src' parameter must be a Path, str, or Iterable of Paths or strings"
		roots, counts, branches = zip(*[self.analyze(branch, includeupper=includeupper) for branch in src])
		root = min(roots, key=lambda r: len(str(r)))
		return root, sum(counts), list(branches)
        


