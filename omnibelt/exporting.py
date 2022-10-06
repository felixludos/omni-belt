from typing import List, Dict, Tuple, Optional, Union, Any, Hashable, Sequence, Callable, Generator, Type, Iterable, \
	Iterator, IO
from pathlib import Path
from itertools import chain
from collections import OrderedDict

from .typing import unspecified_argument
from .logging import get_printer
prt = get_printer(__name__)



class ExportManager:
	_export_fmts_head = []
	_export_fmts_tail = []
	_export_fmt_types: Dict[Type, List[Type['Exporter']]] = OrderedDict()
	_export_fmt_exts: Dict[str, List[Type['Exporter']]] = OrderedDict()

	class UnknownExportData(Exception):
		def __init__(self, obj):
			super().__init__(f'{obj}')
			self.obj = obj

	class UnknownExportPath(Exception):
		def __init__(self, path):
			super().__init__(f'{str(path)}')
			self.path = path

	class UnknownExportFormat(Exception):
		def __init__(self, fmt):
			super().__init__(f'{fmt}')
			self.fmt = fmt

	class ExportFailedError(ValueError):
		def __init__(self, obj, fmts):
			super().__init__(f'{type(obj).__name__} failed using: {", ".join(fmts)}')
			self.obj = obj
			self.fmts = fmts

	class LoadFailedError(Exception):
		def __init__(self, path, fmts):
			super().__init__(f'{path} failed using: {", ".join(fmts)}')
			self.path = path
			self.fmts = fmts

	class AmbiguousLoadPathError(FileNotFoundError):
		def __init__(self, options):
			super().__init__(f'{options}')
			self.options = options

	class ExportManagerInitError(Exception):
		pass

	def __init_subclass__(cls, inherit_exporters=True, set_as_current=False, **kwargs):
		super().__init_subclass__(**kwargs)

		head, tail = [], []
		typs, exts = OrderedDict(), OrderedDict()

		if inherit_exporters:
			for base in cls.__bases__:
				if issubclass(base, ExportManager):
					head.extend(base._export_fmts_head)
					tail.extend(base._export_fmts_tail)
					for k, v in base._export_fmt_types.items():
						typs.setdefault(k, []).extend(v)
					for k, v in base._export_fmt_exts.items():
						exts.setdefault(k, []).extend(v)

		cls._export_fmts_head = head
		cls._export_fmts_tail = tail
		cls._export_fmt_types = typs
		cls._export_fmt_exts = exts

		if set_as_current:
			set_export_manager(cls)


	def __init__(self, *args, **kwargs):
		raise self.ExportManagerInitError('ExportManager should not be instantiated')


	@classmethod
	def resolve_fmt_from_obj(cls, obj: Any) -> Iterator[Type['Exporter']]:
		missing = True
		for fmt in chain(reversed(cls._export_fmt_types.get(type(obj), [])),
		                 reversed(cls._export_fmts_head),
		                 cls._export_fmts_tail):
			if fmt.validate_export_obj(obj):
				missing = False
				yield fmt
		if missing:
			raise cls.UnknownExportData(obj)

	@classmethod
	def resolve_fmt_from_path(cls, path: Path) -> Iterator[Type['Exporter']]:
		missing = True
		for fmt in chain(reversed(cls._export_fmt_exts.get(path.suffix, [])),
		                 reversed(cls._export_fmts_head),
		                 cls._export_fmts_tail):
			if fmt.validate_export_path(path):
				missing = False
				yield fmt

		if missing:
			raise cls.UnknownExportPath(path)

	@classmethod
	def resolve_fmt(cls, fmt: Union[str, Type['Exporter']]) -> Iterator[Type['Exporter']]:
		if issubclass(fmt, Exporter):
			yield fmt
		else:
			try:
				yield from cls.resolve_fmt_from_path(Path(f'null.{fmt}' if len(fmt) else 'null'))
			except cls.UnknownExportPath:
				raise cls.UnknownExportFormat(fmt)

	@classmethod
	def create_export_path(cls, name: str, *, root: Optional[Union[str, Path]] = None,
	                       fmt: Optional[str] = None) -> Path:
		if root is None:
			root = Path()
		root = Path(root)

		if fmt is None:
			return root / name

		for fmt in cls.resolve_fmt(fmt):
			return fmt._create_export_path(name, root, src=cls)


	@classmethod
	def create_load_path(cls, name: str, root: Optional[Union[str, Path]] = None):
		if root is None:
			root = Path()
		root = Path(root)

		if not root.exists():
			raise FileNotFoundError(root)
		options = list(root.glob(f'{name}*'))
		if not len(options):
			raise FileNotFoundError(root / name)
		if len(options) > 1:
			raise cls.AmbiguousLoadPathError(options)
		return options[0]

	@classmethod
	def _export_fmt(cls, fmt: Type['Exporter'], payload: Any, path: Path, **kwargs: Any) -> Path:
		return fmt._export_payload(payload, path=path, src=cls, **kwargs)

	@classmethod
	def _load_export_fmt(cls, fmt: Type['Exporter'], path: Path, **kwargs: Any) -> Path:
		return fmt._load_export(path, src=cls, **kwargs)

	@classmethod
	def export(cls, payload: Any, name: Optional[str] = None, root: Optional[Union[str, Path]] = None,
	           fmt: Optional[Union[str, Type['Exporter']]] = None, path: Optional[Union[str, Path]] = None,
	           **kwargs) -> Path:
		assert path is not None or name is not None, f'Must provide either a path or a name to export: {payload}'
		if root is not None:
			root = Path(root)

		fmts = cls.resolve_fmt_from_obj(payload) if fmt is None else cls.resolve_fmt(fmt)
		for fmt in fmts:
			dest = fmt.create_export_path(name=name, root=root, payload=payload) if path is None else Path(path)
			try:
				return cls._export_fmt(fmt, payload, dest, **kwargs)
			except fmt.ExportFailedError:
				pass

		raise cls.ExportFailedError(payload, fmts)

	@classmethod
	def load_export(cls, name: Optional[str] = None, root: Optional[Union[str, Path]] = None, *,
	                fmt: Optional[Union[str, Type['Exporter']]] = None, path: Optional[Union[str, Path]] = None,
	                **kwargs) -> Any:
		if root is not None:
			root = Path(root)

		if fmt is not None:
			fmts = cls.resolve_fmt(fmt)
		elif path is not None:
			fmts = cls.resolve_fmt_from_path(path)
		else:
			path = cls.create_load_path(name=name, root=root)
			fmts = cls.resolve_fmt_from_path(path)

		for fmt in fmts:
			dest = fmt.create_export_path(name=name, root=root) if path is None else Path(path)
			try:
				return cls._load_export_fmt(fmt, dest, **kwargs)
			except fmt.LoadFailedError:
				pass

		raise cls.LoadFailedError(path, fmts)

	@classmethod
	def register(cls, exporter: Type['Exporter'], extensions: Optional[Union[str, Sequence[str]]] = None,
	             types: Optional[Union[Type, Sequence[Type]]] = None,
	             head: Optional[bool] = None, tail: Optional[bool] = None):

		if head is None and tail is None:
			head, tail = types is None, False
		if head:
			cls._export_fmts_head.append(exporter)
		if tail:
			cls._export_fmts_tail.append(exporter)

		if extensions is not None:
			if isinstance(extensions, str):
				extensions = (extensions,)
			else:
				extensions = tuple(extensions)
			for ext in extensions:
				if ext not in cls._export_fmt_exts:
					cls._export_fmt_exts[ext] = []
				cls._export_fmt_exts[ext].append(exporter)

		if types is not None:
			if isinstance(types, type):
				types = (types,)
			else:
				types = tuple(types)
			for typ in types:
				if typ not in cls._export_fmt_types:
					cls._export_fmt_types[typ] = []
				cls._export_fmt_types[typ].append(exporter)

		if extensions is None and types is None and not head and not tail:
			prt.warning(f'Exporter {exporter} is not registered to any extensions or types')



_current_export_manager = ExportManager
def set_export_manager(manager: Type[ExportManager]) -> Type[ExportManager]:
	global _current_export_manager
	old = _current_export_manager
	_current_export_manager = manager
	return old


def export(obj, name=None, root=None, *, fmt=None, path=None, manager=None, **kwargs):
	if manager is None:
		manager = _current_export_manager
	return manager.export(obj, name=name, root=root, fmt=fmt, path=path, **kwargs)


def load_export(name=None, root=None, *, fmt=None, path=None, manager=None, **kwargs):
	if manager is None:
		manager = _current_export_manager
	return manager.load_export(name=name, root=root, fmt=fmt, path=path, **kwargs)



class Exporter:
	@classmethod
	def validate_export_obj(cls, obj: Any) -> bool:
		options = getattr(cls, '_my_export_types', None)
		return options is not None and isinstance(obj, options)

	@classmethod
	def validate_export_path(cls, path: Path) -> bool:
		suffix = path.suffix
		options = getattr(cls, '_my_export_extensions', None)
		return options is not None and len(suffix) and suffix[1:] in options

	
	def __init_subclass__(cls, extensions: Optional[Union[str, Sequence[str]]] = None,
	                      types: Optional[Union[Type, Sequence[Type]]] = None,
			              head: Optional[bool] = None, tail: Optional[bool] = None,
	                      manager: Optional[ExportManager] = None, **kwargs):
		if extensions is not None:
			extensions = (extensions,) if isinstance(extensions, str) else tuple(extensions)
			extensions = tuple(ext if ext.startswith('.') else f'.{ext}' for ext in extensions)
		if types is not None:
			types = (types,) if isinstance(types, type) else tuple(types)

		_auto_manager = False
		if manager is None:
			_auto_manager = True
			manager = _current_export_manager

		super().__init_subclass__(**kwargs)
		manager.register(cls, extensions=extensions, types=types, head=head, tail=tail)

		if extensions is not None:
			cls._my_export_extensions = extensions
		if types is not None:
			cls._my_export_types = types
		if manager is not None and not _auto_manager:
			cls._my_export_manager = manager


	@classmethod
	def load_export(cls, name: Optional[str] = None, root: Optional[Union[Path, str]] = None, *,
	                path: Optional[Union[str, Path]] = None, manager: Optional['ExportManager'] = None) -> Any:
		if manager is None:
			manager = getattr(cls, '_my_export_manager', _current_export_manager)
		return manager.load_export(name=name, root=root, path=path, fmt=cls)

	@classmethod
	def export(cls, payload, name: Optional[str] = None, root: Optional[Union[str, Path]] = None, *,
	           path: Optional[Union[str, Path]] = None, manager: Optional['ExportManager'] = None) -> Optional[Path]:
		if manager is None:
			manager = getattr(cls, '_my_export_manager', _current_export_manager)
		return manager.export(payload, name=name, root=root, path=path, fmt=cls)

	@classmethod
	def create_export_path(cls, name: str, root: Optional[Union[Path, str]], *,
	                       payload: Optional[Any] = unspecified_argument) -> Path:
		if root is None:
			root = Path()
		root = Path(root)
		options = getattr(cls, '_my_export_extensions', None)
		return root / f'{name}{"" if options is None else options[0]}'


	class LoadFailedError(ValueError): pass
	class ExportFailedError(ValueError): pass

	@staticmethod
	def _load_export(path: Union[Path, str], src: Type['ExportManager']) -> Any:
		raise NotImplementedError

	@staticmethod
	def _export_payload(payload: Any, path: Union[Path, str], src: Type['ExportManager']) -> Optional[Path]:
		raise NotImplementedError



class CollectiveExporter(Exporter):
	'''Usually braod exporters that can export multiple types of objects (eg. pickle, json, etc.)'''
	def __init_subclass__(cls, extensions=None, head=None, tail=None, **kwargs):
		super().__init_subclass__(extensions=extensions, head=head, tail=tail, **kwargs)


class SelectiveExporter(Exporter):
	'''Usually specific exporters where the produced file is specific to the object type (eg. .png, .jpg, etc.)'''
	def __init_subclass__(cls, extensions=None, types=None, **kwargs):
		super().__init_subclass__(extensions=extensions, types=types, **kwargs)


class Exportable(SelectiveExporter):
	'''Mixin for objects that can be exported with a custom export function :func:`_export_payload()`'''
	def __init_subclass__(cls, extensions=None, types=None, **kwargs):
		if types is None:
			types = cls
		super().__init_subclass__(extensions=extensions, types=types, **kwargs)

	def export(self, name: Optional[str] = None, root: Optional[Union[str, Path]] = None,
	           manager: Optional['ExportManager'] = None) -> Optional[Path]:
		return super().export(self, name=name, root=root, manager=manager)







