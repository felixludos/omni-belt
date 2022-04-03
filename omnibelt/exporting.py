from pathlib import Path
from itertools import chain
from collections import OrderedDict



class Exportable:
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
	
	
	class ExportFailedError(Exception):
		def __init__(self, obj):
			super().__init__(f'{type(obj).__name__}')
	
	
	class LoadFailedError(Exception):
		def __init__(self, path):
			super().__init__(f'{str(path)}')
	
	
	@classmethod
	def _find_parent_class_with_table(cls):
		ID = id(cls._export_fmts_head)
		for parent in cls.mro():
			tbl = getattr(parent, '_export_table', None)
			if isinstance(parent, Exportable) and tbl is not None and ID != id(tbl):
				return parent
	
	
	_export_fmts_head = []
	_export_fmts_tail = []
	_export_fmt_types = OrderedDict()
	_export_fmt_exts = OrderedDict()
	
	
	def __init_subclass__(cls, extensions=None, types=None, create_table=False, head=None, tail=None, **kwargs):
		super().__init_subclass__(**kwargs)
		
		if create_table:
			cls._export_fmt_exts = {}
			cls._export_fmt_types = {}
			cls._export_fmts_head = []
			cls._export_fmts_tail = []
		
		if head is None and tail is None:
			head, tail = False, True
		if head:
			cls._export_fmts_head.append(cls)
		if tail:
			cls._export_fmts_tail.append(cls)
		
		if extensions is not None:
			if isinstance(extensions, (list, tuple)):
				extensions = tuple(extensions)
			else:
				extensions = (extensions,)
			cls._my_export_extensions = extensions
			for ext in extensions:
				cls._export_fmt_exts[ext] = cls
		
		if types is not None:
			if isinstance(types, (list, tuple)):
				types = tuple(types)
			else:
				types = (types,)
			cls._my_export_types = types
			for typ in types:
				cls._export_fmt_types[typ] = cls
		cls._export_fmt_types[cls] = cls
	
	
	@classmethod
	def _resolve_obj_failed(cls, obj):
		parent = cls._find_parent_class_with_table()
		if parent is not None:
			return parent.resolve_fmt_from_obj(obj)
		raise cls.UnknownExportData(obj)
	
	
	@classmethod
	def resolve_fmt_from_obj(cls, obj):
		typ = type(obj)
		if typ not in cls._export_fmt_types:
			for fmt in chain(cls._export_fmts_head, reversed(cls._export_fmts_tail)):
				if fmt.validate_export_obj(obj):
					break
			else:
				return cls._resolve_obj_failed(obj)
			return fmt
		return cls._export_fmt_types[typ]
	
	
	@classmethod
	def _resolve_path_failed(cls, path):
		parent = cls._find_parent_class_with_table()
		if parent is not None:
			return parent.resolve_fmt_from_path(path)
		raise cls.UnknownExportPath(path)
	
	
	@classmethod
	def resolve_fmt_from_path(cls, path):
		ext = path.suffix if isinstance(path, Path) else path
		if ext in cls._export_fmt_exts:
			return cls._export_fmt_exts[ext]
		return cls._resolve_path_failed(path)
	
	
	@classmethod
	def validate_export_obj(cls, obj):
		options = getattr(cls, '_my_export_types', None)
		return options is not None and isinstance(obj, options)
	
	
	@classmethod
	def resolve_fmt(cls, fmt):
		if isinstance(fmt, Exportable):
			return fmt
		if not isinstance(fmt, str):
			raise cls.UnknownExportFormat(fmt)
		if not fmt.startswith('.') and len(fmt):
			fmt = f'.{fmt}'
		return cls.resolve_fmt_from_path(Path(f'null{fmt}'))
		
	
	
	@classmethod
	def create_export_path(cls, name, root=None, ext=None):
		if root is None:
			raise cls.ExportFailedError(f'Missing a root for {name} in {cls.__name__}')
		root = Path(root)
		
		if ext is None:
			options = getattr(cls, '_my_export_extensions', None)
			ext = '' if options is None else (options[0] if isinstance(options, (list, tuple)) else options)
		
		if ext is not None:
			name = f'{name}{ext}'
		return root / name
	
	
	@classmethod
	def create_load_path(cls, name, root=None):
		if root is None:
			raise cls.LoadFailedError(f'Missing a root for {name} in {cls.__name__}')
		root = Path(root)
		
		if not root.exists():
			raise FileNotFoundError(str(root))
		options = list(root.glob(f'{name}*'))
		if not len(options):
			raise FileNotFoundError(str(root / name))
		return options[0]
	
	
	@classmethod
	def export(cls, obj, name=None, root=None, fmt=None, path=None, **kwargs):
		assert path is not None or name is not None, f'Must provide either a path or a name to export: {obj}'
		if fmt is None:
			fmt = cls.resolve_fmt_from_obj(obj)
		else:
			fmt = cls.resolve_fmt(fmt)
		if path is None:
			path = fmt.create_export_path(name=name, root=root)
		else:
			path = Path(path)
		return fmt._export_self(obj, path, src=cls, **kwargs)
	
	
	@classmethod
	def load_export(cls, name=None, root=None, fmt=None, path=None, **kwargs):
		if path is None:
			path = cls.create_load_path(name=name, root=root)
		else:
			path = Path(path)
		if fmt is None:
			fmt = cls.resolve_fmt_from_path(path)
		else:
			fmt = cls.resolve_fmt(fmt)
		return fmt._load_export(path, src=cls, **kwargs)

	
	@staticmethod
	def _load_export(path, src=None):
		raise NotImplementedError

	
	@staticmethod
	def _export_self(self, path, src=None):
		raise NotImplementedError(self)



def export(obj, name=None, root=None, fmt=None, path=None, **kwargs):
	return Exportable.export(obj, name=name, root=root, fmt=fmt, path=path, **kwargs)



def load_export(name=None, root=None, fmt=None, path=None, **kwargs):
	return Exportable.load_export(name=name, root=root, fmt=fmt, path=path, **kwargs)



