from typing import List, Dict, Tuple, Optional, Union, Any, Hashable, Sequence, Callable, Generator, Type, Iterable, \
	Iterator, IO
from pathlib import Path
from . import load_txt, save_txt, Packable, save_pack, load_pack, save_json, save_yaml, load_yaml, load_json
from .exporting import SimpleExporterBase
import dill
import toml


class UniversalExporter(SimpleExporterBase):
	@staticmethod
	def affinity_from_payload(payload: Any, **kwargs) -> bool:
		return True



class PickleExport(UniversalExporter, extensions='.pk'):
	@staticmethod
	def affinity_from_payload(payload: Any, **kwargs) -> bool:
		return dill.pickles(payload, **kwargs)

	@staticmethod
	def _load_payload(path: Path, **kwargs) -> Any:
		return dill.load(path, **kwargs)

	@staticmethod
	def _export_payload(payload: Any, path: Path, **kwargs) -> None:
		dill.dump(payload, path, **kwargs)



class PackedExport(UniversalExporter, extensions='.pkd'):
	@staticmethod
	def _load_payload(path: Path, **kwargs) -> Any:
		return load_pack(path, **kwargs)

	@staticmethod
	def _export_payload(payload: Any, path: Path, **kwargs) -> None:
		save_pack(payload, path, **kwargs)



class YamlExport(UniversalExporter, extensions=['.yml', '.yaml']):
	@staticmethod
	def _load_payload(path: Path, **kwargs) -> Any:
		return load_yaml(path, **kwargs)

	@staticmethod
	def _export_payload(payload: Any, path: Path, **kwargs) -> None:
		save_yaml(payload, path, **kwargs)



class TomlExport(UniversalExporter, extensions=['.toml', '.tml']):
	@staticmethod
	def _load_payload(path: Path, **kwargs) -> Any:
		return toml.load(path, **kwargs)

	@staticmethod
	def _export_payload(payload: Any, path: Path, **kwargs) -> None:
		toml.dump(payload, path.open('w'), **kwargs)



class JsonExport(SimpleExporterBase, types=[dict, list, str, int, float, bool, type(None)], extensions='.json'):
	@staticmethod
	def _load_payload(path: Path, **kwargs) -> Any:
		return load_json(path, **kwargs)

	@staticmethod
	def _export_payload(payload: Any, path: Path, **kwargs) -> None:
		save_json(payload, path, **kwargs)



class TextExport(SimpleExporterBase, types=str, extensions=['.txt', '.str']):
	@staticmethod
	def _load_payload(path: Path, **kwargs) -> Any:
		return load_txt(path)

	@staticmethod
	def _export_payload(payload: Any, path: Path, **kwargs) -> None:
		save_txt(payload, path)



class IntExport(SimpleExporterBase, types=int, extensions='.int'):
	@staticmethod
	def _load_payload(path: Path, **kwargs) -> Any:
		return int(load_txt(path))

	@staticmethod
	def _export_payload(payload: Any, path: Path, **kwargs) -> None:
		save_txt(str(payload), path)



class FloatExport(SimpleExporterBase, types=float, extensions='.float'):
	@staticmethod
	def _load_payload(path: Path, **kwargs) -> Any:
		return float(load_txt(path))

	@staticmethod
	def _export_payload(payload: Any, path: Path, **kwargs) -> None:
		save_txt(str(payload), path)




