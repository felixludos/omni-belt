from typing import List, Dict, Tuple, Optional, Union, Any, Hashable, Sequence, Callable, Generator, Type, Iterable, \
	Iterator, IO
from pathlib import Path
from . import Exporter, load_txt, save_txt, Packable, save_pack, load_pack, save_json, save_yaml, load_yaml, load_json
from .exporting import ExportManager, Exporter, SelectiveExporter, CollectiveExporter
import dill
import toml


class PickleExport(CollectiveExporter, extensions='.pk'):
	@staticmethod
	def validate_export_obj(obj: Any, **kwargs) -> bool:
		return dill.pickles(obj, **kwargs)

	@staticmethod
	def _load_export(path: Union[Path, str], src: Type[ExportManager], **kwargs) -> Any:
		return dill.load(path, **kwargs)

	@staticmethod
	def _export_payload(payload: Any, path: Union[Path, str], src: Type[ExportManager], **kwargs) -> Path:
		dill.dump(payload, path, **kwargs)
		return path


class PackedExport(CollectiveExporter, extensions='.pkd'):
	@staticmethod
	def _load_export(path: Union[Path, str], src: Type[ExportManager], **kwargs) -> Any:
		return load_pack(path, **kwargs)

	@staticmethod
	def _export_payload(payload: Any, path: Union[Path, str],
	                    src: Type[ExportManager], **kwargs) -> Optional[Path]:
		save_pack(payload, path, **kwargs)
		return path



class JsonExport(CollectiveExporter, extensions='.json'):
	@staticmethod
	def _load_export(path: Union[Path, str], src: Type[ExportManager], **kwargs) -> Any:
		return load_json(path, **kwargs)

	@staticmethod
	def _export_payload(payload: Any, path: Union[Path, str],
	                    src: Type[ExportManager], **kwargs) -> Optional[Path]:
		save_json(payload, path, **kwargs)
		return path


class YamlExport(CollectiveExporter, extensions=['.yaml', '.yml']):
	@staticmethod
	def _load_export(path: Union[Path, str], src: Type[ExportManager], **kwargs) -> Any:
		return load_yaml(path, **kwargs)

	@staticmethod
	def _export_payload(payload: Any, path: Union[Path, str],
	                    src: Type[ExportManager], **kwargs) -> Optional[Path]:
		save_yaml(payload, path, **kwargs)
		return path


class TomlExport(CollectiveExporter, extensions=['.toml', '.tml']):
	@staticmethod
	def _load_export(path: Union[Path, str], src: Type[ExportManager], **kwargs) -> Any:
		return toml.load(path, **kwargs)

	@staticmethod
	def _export_payload(payload: Any, path: Union[Path, str],
	                    src: Type[ExportManager], **kwargs) -> Optional[Path]:
		toml.dump(payload, path.open('w'), **kwargs)
		return path



class StrExport(SelectiveExporter, types=str, extensions='.txt'):
	@staticmethod
	def _load_export(path: Union[Path, str], src: Type[ExportManager]) -> str:
		return load_txt(path)

	@staticmethod
	def _export_payload(payload: Any, path: Union[Path, str],
	                    src: Type[ExportManager], **kwargs) -> Optional[Path]:
		save_txt(payload, path)
		return path


class IntExport(SelectiveExporter, types=int, extensions='.int'):
	@staticmethod
	def _load_export(path: Union[Path, str], src: Type[ExportManager]) -> int:
		return int(load_txt(path))

	@staticmethod
	def _export_payload(payload: Any, path: Union[Path, str],
	                    src: Type[ExportManager], **kwargs) -> Optional[Path]:
		return save_txt(str(payload), path)


class FloatExport(SelectiveExporter, types=float, extensions='.float'):
	@staticmethod
	def _load_export(path: Union[Path, str], src: Type[ExportManager]) -> float:
		return float(load_txt(path))

	@staticmethod
	def _export_payload(payload: Any, path: Union[Path, str],
	                    src: Type[ExportManager], **kwargs) -> Optional[Path]:
		return save_txt(str(payload), path)




