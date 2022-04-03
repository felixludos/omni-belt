
from . import Exportable, load_txt, save_txt, Packable, save_pack, load_pack, save_json, save_yaml, load_yaml, load_json
import dill



class PickleExport(Exportable, extensions='.pk'):
	@staticmethod
	def validate_export_obj(obj, **kwargs):
		return dill.pickles(obj, **kwargs)
	@staticmethod
	def _load_export(path, src=None, **kwargs):
		return dill.load(path, **kwargs)
	@staticmethod
	def _export_self(self, path, src=None, **kwargs):
		return dill.dump(self, path, **kwargs)



class PackedExport(Exportable, extensions='.pkd'):
	@staticmethod
	def _load_export(path, src=None, **kwargs):
		return load_pack(path, **kwargs)
	@staticmethod
	def _export_self(self, path, src=None, **kwargs):
		return save_pack(self, path, **kwargs)



class JsonExport(Exportable, extensions='.json'):
	@staticmethod
	def _load_export(path, src=None, **kwargs):
		return load_json(path, **kwargs)
	@staticmethod
	def _export_self(self, path, src=None, **kwargs):
		return save_json(self, path, **kwargs)



class YamlExport(Exportable, extensions='.yaml'):
	@staticmethod
	def _load_export(path, src=None, **kwargs):
		return load_yaml(path, **kwargs)
	@staticmethod
	def _export_self(self, path, src=None, **kwargs):
		return save_yaml(self, path, **kwargs)



class StrExport(Exportable, types=str, extensions='.txt'):
	@staticmethod
	def _load_export(path, src=None):
		return load_txt(path)
	@staticmethod
	def _export_self(self, path, src=None):
		return save_txt(self, path)



class IntExport(Exportable, types=int, extensions='.int'):
	@staticmethod
	def _load_export(path, src=None):
		return int(load_txt(path))
	@staticmethod
	def _export_self(self, path, src=None):
		return save_txt(str(self), path)



class FloatExport(Exportable, types=float, extensions='.float'):
	@staticmethod
	def _load_export(path, src=None):
		return float(load_txt(path))
	@staticmethod
	def _export_self(self, path, src=None):
		return save_txt(str(self), path)




