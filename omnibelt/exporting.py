from typing import List, Dict, Tuple, Optional, Union, Any, Hashable, Sequence, Callable, Generator, Type, Iterable, \
	Iterator, IO
from pathlib import Path
from itertools import chain
from collections import OrderedDict

from .typing import unspecified_argument
# from .registries import Class_Registry
from .logging import get_printer
prt = get_printer(__name__)



########################################################################################################################



class UnknownExportData(Exception):
	def __init__(self, obj):
		super().__init__(f'{obj}')
		self.obj = obj


class UnknownExportPath(Exception):
	def __init__(self, path):
		super().__init__(f'{str(path)}')
		self.path = path


class ExportFailedError(ValueError):
	def __init__(self, obj, fmts):
		super().__init__(f'{obj} failed using: {", ".join(fmts)}')
		self.fmts = fmts
		self.obj = obj


class LoadFailedError(Exception):
	def __init__(self, path, fmts):
		super().__init__(f'{path} failed using: {", ".join(fmts)}')
		self.path = path
		self.fmts = fmts


class AmbiguousLoadPathError(FileNotFoundError):
	def __init__(self, options):
		super().__init__(f'{options}')
		self.options = options



########################################################################################################################



class AbstractExportManager:
	def exporters(self) -> Iterator['AbstractExporter']: # N-O
		raise NotImplementedError


	def loaders(self) -> Iterator['AbstractLoader']:
		raise NotImplementedError


	def export(self, payload: Any, path: Union[str, Path], fmt: Union[str, 'AbstractExporter', None] = None, *,
			   root: Union[str, Path, None] = None, **kwargs) -> Path:
		raise NotImplementedError


	def load_export(self, path: Union[str, Path], fmt: Optional[Union[str, 'AbstractLoader']] = None, *,
	                root: Optional[Union[str, Path]] = None, **kwargs) -> Any:
		raise NotImplementedError



class AbstractLoader:
	def affinity_from_format(self, fmt: str) -> int:
		'''
		Returns a value representing whether this exporter should be used for the given format.
		Non-positive values mean this exporter should not be used for this format.
		The higher the value, the higher the priority for this exporter to be used.
		'''
		raise NotImplementedError


	def affinity_from_path(self, path: Path) -> int:
		'''
		Returns a value representing whether this exporter should be used for the given path.
		Non-positive values mean this exporter should not be used for this path.
		The higher the value, the higher the priority for this exporter to be used.
		'''
		return self.affinity_from_format(''.join(path.suffixes))


	@staticmethod
	def load_payload(src: AbstractExportManager, path: Path, *, fmt: Optional[str] = None, **kwargs) -> Any:
		raise NotImplementedError


	@classmethod
	def load_export(self, name: Optional[str] = None, root: Optional[Union[Path, str]] = None, *,
					path: Optional[Union[str, Path]] = None, manager: Optional['ExportManager'] = None,
					fmt: Optional[Union[str, Type['ExporterBase']]] = unspecified_argument) -> Any:
		if manager is None:
			manager = getattr(self, '_my_export_manager', _current_export_manager)
		if fmt is unspecified_argument:
			fmt = self
		return manager.load_export(name=name, root=root, path=path, fmt=fmt)



class AbstractExporter:
	def affinity_from_format(self, fmt: str) -> int:
		'''
		Returns a value representing whether this exporter should be used for the given format.
		Non-positive values mean this exporter should not be used for this format.
		The higher the value, the higher the priority for this exporter to be used.
		'''
		raise NotImplementedError


	def affinity_from_path(self, path: Path) -> int:
		'''
		Returns a value representing whether this exporter should be used for the given path.
		Non-positive values mean this exporter should not be used for this path.
		The higher the value, the higher the priority for this exporter to be used.
		'''
		return self.affinity_from_format(''.join(path.suffixes))


	def affinity_from_payload(self, payload: Any) -> int:
		'''
		Returns a value representing whether this exporter should be used for the given payload.
		Non-positive values mean this exporter should not be used for this payload.
		The higher the value, the higher the priority for this exporter to be used.
		'''
		raise NotImplementedError


	# top level

	@classmethod
	def export(cls, payload, name: Optional[str] = None, root: Optional[Union[str, Path]] = None, *,
			   path: Optional[Union[str, Path]] = None, manager: Optional['ExportManager'] = None,
			   fmt: Optional[Union[str, Type['ExporterBase']]] = unspecified_argument) -> Optional[Path]:
		if manager is None:
			manager = getattr(cls, '_my_export_manager', _current_export_manager)
		if fmt is unspecified_argument:
			fmt = cls
		return manager.export(payload, name=name, root=root, path=path, fmt=fmt)

	_LoadFailedError = LoadFailedError
	_ExportFailedError = ExportFailedError

	# custom workers

	@staticmethod
	def export_payload(src: AbstractExportManager, payload: Any, path: Path, *,
					   fmt: Optional[str] = None, **kwargs) -> Path:
		raise NotImplementedError



########################################################################################################################



class ExportManager(AbstractExportManager):
	def __init__(self, *, exporters: Optional[Iterable[AbstractExporter]] = None,
	             loaders: Optional[Iterable[AbstractLoader]] = None):
		self._exporters = list(exporters) if exporters is not None else []
		self._loaders = list(loaders) if loaders is not None else []


	def register(self, *exporters: Union[AbstractExporter, AbstractLoader,
										 Type[AbstractExporter], Type[AbstractLoader]]):
		for exporter in exporters:
			if (isinstance(exporter, type)
					and (issubclass(exporter, AbstractExporter) or issubclass(exporter, AbstractLoader))):
				exporter = exporter()
			if isinstance(exporter, AbstractExporter):
				self._exporters.append(exporter)
			elif isinstance(exporter, AbstractLoader):
				self._loaders.append(exporter)
			else:
				raise TypeError(f'Cannot register {exporter} as an exporter or loader')


	def exporters(self) -> Iterator[AbstractExporter]: # N-O
		yield from reversed(self._exporters)


	def _matching_exporters(self, fmt: Optional[str] = None, path: Optional[Path] = None,
							payload: Optional[Any] = unspecified_argument) -> Iterator[AbstractExporter]:
		assert fmt is not None or path is not None or payload is not unspecified_argument, \
			f'Must provide either a format, a path, or a payload: {fmt}, {path}, {payload}'
		options = list((None if payload is unspecified_argument else exporter.affinity_from_payload(payload),
					None if fmt is None else exporter.affinity_from_format(fmt),
					None if path is None else exporter.affinity_from_path(path),
					exporter) for exporter in self.exporters())

		for payload_affinity, fmt_affinity, path_affinity, exporter in sorted(options, reverse=True,
																			  key=lambda info: tuple(info[:-1])):
			if (payload_affinity is None or payload_affinity <= 0) \
				and (fmt_affinity is None or fmt_affinity <= 0) \
				and (path_affinity is None or path_affinity <= 0):
				break
			yield exporter


	def loaders(self) -> Iterator[AbstractExporter]: # N-O
		yield from reversed(self._loaders)


	def _matching_loaders(self, path: Path, fmt: Optional[str] = None) -> Iterator[AbstractLoader]:
		options = list((None if fmt is None else exporter.affinity_from_format(fmt),
					None if path is None else exporter.affinity_from_path(path),
					exporter) for exporter in self.exporters())

		for fmt_affinity, path_affinity, loader in sorted(options, reverse=True, key=lambda info: tuple(info[:-1])):
			if (fmt_affinity is None or fmt_affinity <= 0) and (path_affinity is None or path_affinity <= 0):
				break
			yield loader


	_UnknownExportData = UnknownExportData
	_ExportFailedError = ExportFailedError


	def export(self, payload: Any, path: Union[str, Path], *, fmt: Union[str, AbstractExporter, None] = None,
			   root: Union[str, Path, None] = None, **kwargs) -> Path:
		path = Path(path)
		if root is not None:
			path = Path(root) / path

		if isinstance(fmt, AbstractExporter):
			return fmt.export_payload(payload, path, src=self, **kwargs)

		errors = OrderedDict()
		for exporter in self._matching_exporters(payload=payload, fmt=fmt, path=path):
			try:
				return exporter.export_payload(self, payload=payload, path=path, fmt=fmt, **kwargs)
			except ExportFailedError as e:
				errors[exporter] = e

		if not errors:
			raise self._UnknownExportData(payload)
		raise self._ExportFailedError(errors)


	_UnknownLoadPath = UnknownExportPath
	_LoadFailedError = LoadFailedError


	def load_export(self, path: Union[str, Path], *, fmt: Optional[Union[str, AbstractLoader]] = None,
	                root: Optional[Union[str, Path]] = None, **kwargs) -> Any:
		path = Path(path)
		if root is not None:
			path = Path(root) / path

		if not path.exists(): # infer suffix only
			fallback = [p for p in path.parent.glob(f'{path.name}*') if p.stem == path.stem]
			if len(fallback) == 0:
				raise FileNotFoundError(path)
			elif len(fallback) > 1:
				raise AmbiguousLoadPathError(fallback)
			else:
				path = fallback[0]

		if isinstance(fmt, AbstractLoader):
			return fmt.load_payload(self, path, **kwargs)

		errors = OrderedDict()
		for loader in self._matching_loaders(path, fmt=fmt):
			try:
				return loader.load_payload(self, path=path, fmt=fmt, **kwargs)
			except LoadFailedError as e:
				errors[loader] = e

		if not errors:
			raise self._UnknownLoadPath(path)
		raise self._LoadFailedError(path, errors)



_current_export_manager = ExportManager()
def set_export_manager(manager: AbstractExportManager) -> AbstractExportManager:
	global _current_export_manager
	old = _current_export_manager
	_current_export_manager = manager
	return old



def export(obj: Any, path: Union[str, Path], *, fmt: Union[str, AbstractExporter, None] = None,
		   root: Union[str, Path, None] = None, manager: Optional[AbstractExportManager] = None,
		   **kwargs):
	if manager is None:
		manager = _current_export_manager
	return manager.export(obj, path=path, fmt=fmt, root=root, **kwargs)


def load_export(path: Union[str, Path], *, fmt: Union[str, AbstractLoader, None] = None,
				root: Union[str, Path, None] = None, manager: Optional[AbstractExportManager] = None,
				**kwargs):
	if manager is None:
		manager = _current_export_manager
	return manager.load_export(path=path, fmt=fmt, root=root, **kwargs)



class ExporterBase(AbstractExporter, AbstractLoader):
	_my_suffixes = None
	_my_payload_types = None
	def __init_subclass__(cls, extensions: Union[None, str, Sequence[str]] = None,
						  types: Union[None, Type, Sequence[Type]] = None, register: bool = None, **kwargs):
		super().__init_subclass__(**kwargs)
		if extensions is not None:
			extensions = extensions if isinstance(extensions, Sequence) else [extensions]
			extensions = [cls._parse_extension(ext) for ext in extensions]
			cls._my_suffixes = extensions

		if types is not None:
			types = types if isinstance(types, Sequence) else [types]
			cls._my_payload_types = tuple(types)

		if register is None:
			register = cls._my_suffixes is not None or cls._my_payload_types is not None
		if register:
			_current_export_manager.register(cls)


	@staticmethod
	def _parse_extension(ext):
		ext = ext.lower()
		if len(ext) and not ext.startswith('.'):
			ext = f'.{ext}'
		return ext


	def affinity_from_format(self, fmt: str) -> int:
		'''
		Returns a value representing whether this exporter should be used for the given format.
		Non-positive values mean this exporter should not be used for this format.
		The higher the value, the higher the priority for this exporter to be used.
		'''
		return self._my_suffixes is not None and self._parse_extension(fmt) in self._my_suffixes


	def affinity_from_path(self, path: Path) -> int:
		'''
		Returns a value representing whether this exporter should be used for the given path.
		Non-positive values mean this exporter should not be used for this path.
		The higher the value, the higher the priority for this exporter to be used.
		'''
		return self.affinity_from_format(''.join(path.suffixes))


	def affinity_from_payload(self, payload: Any) -> int:
		'''
		Returns a value representing whether this exporter should be used for the given payload.
		Non-positive values mean this exporter should not be used for this payload.
		The higher the value, the higher the priority for this exporter to be used.
		'''
		if self._my_payload_types is None or not isinstance(payload, self._my_payload_types):
			return False
		product = type(payload)
		history = product.mro()
		return len(history) - min(history.index(typ) for typ in self._my_payload_types if issubclass(product, typ))



class SimpleExporterBase(ExporterBase):
	def fix_path(self, path: Path) -> Path:
		if self._my_suffixes is not None and ''.join(path.suffixes) not in self._my_suffixes:
			path = path.with_suffix(self._my_suffixes[0])
		return path


	def export_payload(self, src: AbstractExportManager, payload: Any, path: Path, *,
					   fmt: Optional[str] = None, **kwargs) -> Path:
		if not len(path.suffix) and (fmt is None or self.affinity_from_format(fmt) > 0):
			# if no manual fmt was provided, or manually specified self
			path = self.fix_path(path.resolve())
		self._export_payload(payload, path, **kwargs)
		return path


	@staticmethod
	def _export_payload(payload: Any, path: Path, **kwargs) -> None:
		raise NotImplementedError


	def load_payload(self, src: AbstractExportManager, path: Path, *, fmt: Optional[str] = None, **kwargs) -> Any:
		if fmt is None or self.affinity_from_format(fmt) > 0:
			# if no manual fmt was provided, or manually specified self
			path = self.fix_path(path.resolve())
		if not path.exists():
			raise FileNotFoundError(path)
		return self._load_payload(path, **kwargs)


	@staticmethod
	def _load_payload(path: Path, **kwargs) -> Any:
		raise NotImplementedError





########################################################################################################################


#
#
# class OldExportManager:
#
# 	_export_fmts_head = []
# 	_export_fmts_tail = []
# 	_export_fmt_types: Dict[Type, List[Type[AbstractExporter]]] = OrderedDict()
# 	_export_fmt_exts: Dict[str, List[Type[AbstractExporter]]] = OrderedDict()
#
# 	# def __init_subclass__(cls, inherit_exporters=True, set_as_current=False, **kwargs):
# 	# 	super().__init_subclass__(**kwargs)
# 	#
# 	# 	head, tail = [], []
# 	# 	typs, exts = OrderedDict(), OrderedDict()
# 	#
# 	# 	if inherit_exporters:
# 	# 		for base in cls.__bases__:
# 	# 			if issubclass(base, ExportManager):
# 	# 				head.extend(base._export_fmts_head)
# 	# 				tail.extend(base._export_fmts_tail)
# 	# 				for k, v in base._export_fmt_types.items():
# 	# 					typs.setdefault(k, []).extend(v)
# 	# 				for k, v in base._export_fmt_exts.items():
# 	# 					exts.setdefault(k, []).extend(v)
# 	#
# 	# 	cls._export_fmts_head = head
# 	# 	cls._export_fmts_tail = tail
# 	# 	cls._export_fmt_types = typs
# 	# 	cls._export_fmt_exts = exts
# 	#
# 	# 	if set_as_current:
# 	# 		set_export_manager(cls)
#
# 	_UnknownExportData = UnknownExportData
# 	_UnknownExportPath = UnknownExportPath
# 	_UnknownExportFormat = UnknownExportFormat
#
# 	@classmethod
# 	def _related_fmts_by_type(cls, typ):
# 		options = [base for base in reversed(cls._export_fmt_types) if issubclass(typ, base)]
# 		history = list(typ.mro())
# 		for typ in sorted(options, key=lambda t: history.index(t)):
# 			yield from cls._export_fmt_types[typ]
#
# 	@classmethod
# 	def _related_fmts_by_path(cls, path):
# 		suffixes = path.suffixes
# 		if len(suffixes) == 0:
# 			suffixes = ['']
# 		for i in range(len(suffixes)):
# 			suffix = ''.join(suffixes[i:])
# 			if suffix in cls._export_fmt_exts:
# 				yield from cls._export_fmt_exts[suffix]
#
# 	@classmethod
# 	def resolve_fmt_from_obj(cls, obj: Any) -> Iterator[Type[AbstractExporter]]:
# 		missing = True
# 		for fmt in chain(reversed(cls._export_fmts_head),
# 		                 cls._related_fmts_by_type(type(obj)),
# 		                 cls._export_fmts_tail):
# 			if fmt.validate_export_obj(obj):
# 				missing = False
# 				yield fmt
#
# 		if missing:
# 			raise cls._UnknownExportData(obj)
#
# 	@classmethod
# 	def resolve_fmt_from_path(cls, path: Path) -> Iterator[Type[AbstractExporter]]:
# 		missing = True
# 		for fmt in chain(reversed(cls._export_fmts_head),
# 		                 cls._related_fmts_by_path(path), # TODO: maybe check for multi suffixes
# 		                 cls._export_fmts_tail):
# 			if fmt.validate_export_path(path):
# 				missing = False
# 				yield fmt
#
# 		if missing:
# 			raise cls._UnknownExportPath(path)
#
# 	@classmethod
# 	def resolve_fmt(cls, fmt: Union[str, Type, Type[AbstractExporter]]) -> Iterator[Type[AbstractExporter]]:
# 		if isinstance(fmt, type):
# 			if issubclass(fmt, Exporter):
# 				yield fmt
# 			else:
# 				yield from cls._related_fmts_by_type(fmt)
# 		else:
# 			assert isinstance(fmt, str), f'{fmt!r}'
# 			try:
# 				yield from cls.resolve_fmt_from_path(Path(f'null.{fmt}' if len(fmt) else 'null'))
# 			except cls._UnknownExportPath:
# 				raise cls._UnknownExportFormat(fmt)
#
# 	@classmethod
# 	def create_export_path(cls, name: str, *, root: Optional[Union[str, Path]] = None,
# 	                       fmt: Optional[str] = None) -> Path:
# 		if root is None:
# 			root = Path()
# 		root = Path(root)
#
# 		if fmt is None:
# 			return root / name
#
# 		for fmt in cls.resolve_fmt(fmt):
# 			return fmt._create_export_path(name, root, src=cls)
#
#
# 	@classmethod
# 	def create_load_path(cls, name: str, root: Optional[Union[str, Path]] = None):
# 		if root is None:
# 			root = Path()
# 		root = Path(root)
#
# 		if not root.exists():
# 			raise FileNotFoundError(root)
# 		options = list(root.glob(f'{name}*'))
# 		if not len(options):
# 			raise FileNotFoundError(root / name)
# 		if len(options) > 1:
# 			raise cls.AmbiguousLoadPathError(options)
# 		return options[0]
#
# 	@classmethod
# 	def _export_fmt(cls, fmt: Type['Exporter'], payload: Any, path: Path, **kwargs: Any) -> Path:
# 		return fmt._export_payload(payload, path=path, src=cls, **kwargs)
#
# 	@classmethod
# 	def _load_export_fmt(cls, fmt: Type['Exporter'], path: Path, **kwargs: Any) -> Path:
# 		return fmt._load_export(path, src=cls, **kwargs)
#
# 	@classmethod
# 	def export(cls, payload: Any, name: Optional[str] = None, root: Optional[Union[str, Path]] = None,
# 	           fmt: Optional[Union[str, Type, Type['Exporter']]] = None, path: Optional[Union[str, Path]] = None,
# 	           **kwargs) -> Path:
# 		assert path is not None or name is not None, f'Must provide either a path or a name to export: {payload}'
# 		if root is None and path is None and isinstance(name, Path):
# 			path = name
# 			name = None
# 		if root is not None:
# 			root = Path(root)
#
# 		if fmt is not None:
# 			fmts = cls.resolve_fmt(fmt)
# 		elif path is not None: # TODO: payload exporter has to figure out what to do if the extension is different
# 			fmts = cls.resolve_fmt_from_path(Path(path))
# 		else:
# 			fmts = cls.resolve_fmt_from_obj(payload)
#
# 		for fmt in fmts:
# 			dest = fmt.create_export_path(name=name, root=root, payload=payload) if path is None else Path(path)
# 			try:
# 				return cls._export_fmt(fmt, payload, dest, **kwargs)
# 			except ExportFailedError:
# 				pass
#
# 		raise cls.ExportFailedError(payload, fmts)
#
# 	@classmethod
# 	def load_export(cls, name: Optional[str] = None, root: Optional[Union[str, Path]] = None, *,
# 	                fmt: Optional[Union[str, Type['Exporter']]] = None, path: Optional[Union[str, Path]] = None,
# 	                **kwargs) -> Any:
# 		if root is None and path is None and isinstance(name, Path):
# 			path = name
# 			name = None
# 		if root is not None:
# 			root = Path(root)
#
# 		if fmt is not None:
# 			fmts = cls.resolve_fmt(fmt)
# 		elif path is not None:
# 			fmts = cls.resolve_fmt_from_path(path)
# 		else:
# 			path = cls.create_load_path(name=name, root=root)
# 			fmts = cls.resolve_fmt_from_path(path)
#
# 		for fmt in fmts:
# 			dest = fmt.create_export_path(name=name, root=root) if path is None else Path(path)
# 			try:
# 				return cls._load_export_fmt(fmt, dest, **kwargs)
# 			except fmt._LoadFailedError:
# 				pass
#
# 		raise cls.LoadFailedError(path, fmts)
#
# 	@classmethod
# 	def register(cls, exporter: Type['Exporter'], extensions: Optional[Union[str, Sequence[str]]] = None,
# 	             types: Optional[Union[Type, Sequence[Type]]] = None,
# 	             head: Optional[bool] = None, tail: Optional[bool] = None):
#
# 		if head is None and tail is None:
# 			head, tail = types is None, False
# 		if head:
# 			cls._export_fmts_head.append(exporter)
# 		if tail:
# 			cls._export_fmts_tail.append(exporter)
#
# 		if extensions is not None:
# 			if isinstance(extensions, str):
# 				extensions = (extensions,)
# 			else:
# 				extensions = tuple(extensions)
# 			for ext in extensions:
# 				if ext not in cls._export_fmt_exts:
# 					cls._export_fmt_exts[ext] = []
# 				cls._export_fmt_exts[ext].append(exporter)
#
# 		if types is not None:
# 			if isinstance(types, type):
# 				types = (types,)
# 			else:
# 				types = tuple(types)
# 			for typ in types:
# 				if typ not in cls._export_fmt_types:
# 					cls._export_fmt_types[typ] = []
# 				cls._export_fmt_types[typ].append(exporter)
#
# 		if extensions is None and types is None and not head and not tail:
# 			prt.warning(f'Exporter {exporter} is not registered to any extensions or types')
#


# class LoadFailedError(ValueError): pass
# class ExportFailedError(ValueError): pass


# class Exporter:
# 	@classmethod
# 	def validate_export_obj(cls, obj: Any) -> bool:
# 		options = getattr(cls, '_my_export_types', None)
# 		return options is not None and isinstance(obj, options)
#
# 	@classmethod
# 	def validate_export_path(cls, path: Path) -> bool:
# 		suffix = ''.join(path.suffixes)
# 		options = getattr(cls, '_my_export_extensions', None)
# 		return options is not None and len(suffix) and (suffix in options
# 		                                                or (suffix.startswith('.') and suffix[1:] in options))
#
#
# 	def __init_subclass__(cls, extensions: Optional[Union[str, Sequence[str]]] = None,
# 	                      types: Optional[Union[Type, Sequence[Type]]] = None,
# 			              head: Optional[bool] = None, tail: Optional[bool] = None,
# 	                      manager: Optional[ExportManager] = None, **kwargs):
# 		if extensions is not None:
# 			extensions = (extensions,) if isinstance(extensions, str) else tuple(extensions)
# 			extensions = tuple(ext if ext.startswith('.') else f'.{ext}' for ext in extensions)
# 		if types is not None:
# 			types = (types,) if isinstance(types, type) else tuple(types)
#
# 		_auto_manager = False
# 		if manager is None:
# 			_auto_manager = True
# 			manager = _current_export_manager
#
# 		super().__init_subclass__(**kwargs)
# 		manager.register(cls, extensions=extensions, types=types, head=head, tail=tail)
#
# 		if extensions is not None:
# 			cls._my_export_extensions = extensions
# 		if types is not None:
# 			cls._my_export_types = types
# 		if manager is not None and not _auto_manager:
# 			cls._my_export_manager = manager
#
#
# 	@classmethod
# 	def load_export(cls, name: Optional[str] = None, root: Optional[Union[Path, str]] = None, *,
# 	                path: Optional[Union[str, Path]] = None, manager: Optional['ExportManager'] = None,
# 	                fmt: Optional[Union[str, Type['Exporter']]] = unspecified_argument) -> Any:
# 		if manager is None:
# 			manager = getattr(cls, '_my_export_manager', _current_export_manager)
# 		if fmt is unspecified_argument:
# 			fmt = cls
# 		return manager.load_export(name=name, root=root, path=path, fmt=fmt)
#
# 	@classmethod
# 	def export(cls, payload, name: Optional[str] = None, root: Optional[Union[str, Path]] = None, *,
# 	           path: Optional[Union[str, Path]] = None, manager: Optional['ExportManager'] = None,
# 	           fmt: Optional[Union[str, Type['Exporter']]] = unspecified_argument) -> Optional[Path]:
# 		if manager is None:
# 			manager = getattr(cls, '_my_export_manager', _current_export_manager)
# 		if fmt is unspecified_argument:
# 			fmt = cls
# 		return manager.export(payload, name=name, root=root, path=path, fmt=fmt)
#
#
# 	@classmethod
# 	def create_export_path(cls, name: str, root: Optional[Union[Path, str]], *,
# 	                       payload: Optional[Any] = unspecified_argument) -> Path:
# 		if root is None:
# 			root = Path()
# 		root = Path(root)
# 		options = getattr(cls, '_my_export_extensions', None)
# 		if options is not None and len(options) and not name.endswith(options[0]):
# 			name = f'{name}{options[0]}'
# 		return root / name
#
# 	_LoadFailedError = LoadFailedError
# 	_ExportFailedError = ExportFailedError
#
# 	@staticmethod
# 	def _load_export(path: Path, src: Type['ExportManager']) -> Any:
# 		raise NotImplementedError
#
# 	@staticmethod
# 	def _export_payload(payload: Any, path: Path, src: Type['ExportManager']) -> Optional[Path]:
# 		raise NotImplementedError


#
# class CollectiveExporter(Exporter):
# 	'''Usually braod exporters that can export multiple types of objects (eg. pickle, json, etc.)'''
# 	def __init_subclass__(cls, extensions=None, head=None, tail=None, **kwargs):
# 		super().__init_subclass__(extensions=extensions, head=head, tail=tail, **kwargs)
#
#
# class SelectiveExporter(Exporter):
# 	'''Usually specific exporters where the produced file is specific to the object type (eg. .png, .jpg, etc.)'''
# 	def __init_subclass__(cls, extensions=None, types=None, **kwargs):
# 		super().__init_subclass__(extensions=extensions, types=types, **kwargs)
#
#
# class Exportable(SelectiveExporter):
# 	'''Mixin for objects that can be exported with a custom export function :func:`_export_payload()`'''
# 	def __init_subclass__(cls, extensions=None, types=None, **kwargs):
# 		if types is None:
# 			types = cls
# 		super().__init_subclass__(extensions=extensions, types=types, **kwargs)
#
# 	def export(self, name: Optional[str] = None, root: Optional[Union[str, Path]] = None,
# 	           manager: Optional['ExportManager'] = None) -> Optional[Path]:
# 		return super().export(self, name=name, root=root, manager=manager)







