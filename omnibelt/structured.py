from typing import Union, List, Dict, Any, Callable, Iterable

PRIMITIVES = (str, int, float, bool, type(None))
JSONPRIMITIVE = Union[*PRIMITIVES, None]
JSONDATA = Union[JSONPRIMITIVE, List['JSONDATA'], Dict[str, 'JSONDATA']]
JSONOBJ = Dict[str, JSONDATA]
JSONFLAT = Dict[str, JSONPRIMITIVE]



class Jsonable:
	def json(self) -> 'JSONLIKEOBJ':
		"""
		Return a JSON serializable representation of the object.
		"""
		raise NotImplementedError("Subclasses must implement json() method")
JSONLIKE = Union[None, *PRIMITIVES, Jsonable, List['JSONLIKE'], Dict[str, 'JSONLIKE']]
JSONLIKEOBJ = Dict[str, JSONLIKE]



def flatten(data: JSONOBJ, parent_key: str = '', sep: str = '.') -> JSONFLAT:
	items = {}
	for key, value in data.items() if isinstance(data, dict) else enumerate(data):
		new_key = f"{parent_key}{sep}{key}" if parent_key else key
		if isinstance(value, (dict, list)) and not isinstance(value, str):
			items.update(flatten(value, new_key, sep=sep))
		else:
			items[new_key] = value
	return items



def unflatten(data: JSONFLAT, sep: str = '.') -> JSONOBJ:
	items = {}
	for key, value in data.items():
		keys = key.split(sep)
		d = items
		for k in keys[:-1]:
			if k not in d:
				d[k] = {} if keys[-1].isdigit() else []
			d = d[k]
		if keys[-1].isdigit():
			d.append(value)
		else:
			d[keys[-1]] = value
	return items



_empty_json = object()
def deep_get(data: JSONDATA, target: Union[str, Iterable[str]], default: Any = _empty_json, *, sep: str = '.') -> Any:
	if isinstance(target, str):
		target = target.split(sep)
	if not target:
		if default is _empty_json:
			raise ValueError(f"Cannot get empty value for target '{target}'")
		return default
	key, *rest = target
	if isinstance(data, dict):
		if key in data:
			value = data[key]
		elif any(k.startswith(key) for k in data):
			value = {k[len(key) + len(sep):]: v for k, v in data.items() if k.startswith(key + sep)}
		else:
			raise KeyError(f"Key '{key}' not found in data for target '{target}'")
		if rest:
			return deep_get(value, sep.join(rest), default, sep=sep)
		return value
	elif isinstance(data, list) and key.isdigit() and 0 <= int(key) < len(data):
		value = data[int(key)]
		if rest:
			return deep_get(value, sep.join(rest), default, sep=sep)
		return value
	elif default is not _empty_json:
		return default
	else:
		raise KeyError(f"Key '{key}' not found in data for target '{target}'")



def deep_extract(data: JSONDATA, target: Union[str, Iterable[str]], *, sep: str = '.') -> Any:
	if isinstance(target, str):
		target = target.split(sep)
	if not len(target):
		return data

	key, *rest = target

	if key.isdigit():
		if not isinstance(data, list):
			raise TypeError(f"Cannot access index '{key}' in non-list type {type(data).__name__}")
		key = int(key)
		if key >= len(data) or key < -len(data):
			raise IndexError(f"Index '{key}' out of range for list of length {len(data)}")
		out = [None] * (key + int(key >= 0))
	else:
		if not isinstance(data, dict):
			raise TypeError(f"Cannot access key '{key}' in non-dict type {type(data).__name__}")
		if key not in data:
			raise KeyError(f"Key '{key}' not found in data")
		out = {}

	out[key] = deep_extract(data[key], rest, sep=sep)
	return out


def deep_remove(data: JSONDATA, target: Union[str, Iterable[str]], *, sep: str = '.') -> Any:
	if isinstance(target, str):
		target = target.split(sep)
	if not target:
		raise ValueError(f"Cannot remove empty value for target '{target}'")
	key, *rest = target
	if isinstance(data, dict):
		if key in data:
			return deep_remove(data[key], sep.join(rest), sep=sep) if rest else data.pop(key, None)
		to_remove = [k for k in data if k.startswith(key + sep)]
		if any(k.startswith(key) for k in data):
			# Remove all keys that start with the target key

			for k in to_remove:
				del data[k]
			return None
	elif isinstance(data, list) and key.isdigit() and 0 <= int(key) < len(data):
		key = int(key)
		if rest:
			return deep_remove(data[key], sep.join(rest), sep=sep)
		value = data[key]
		data[key] = None
		return value
	else:
		raise KeyError(f"Key '{key}' not found in data for target '{target}'")



def jsonify(obj: JSONLIKE, *, encoder: Callable[[Any], JSONDATA] = str) -> JSONOBJ:
	"""
	Convert an object to a JSON serializable format.
	"""
	if isinstance(obj, Jsonable):
		raw = obj.json()
		return {k: jsonify(v, encoder=encoder) for k, v in raw.items()}
	elif isinstance(obj, PRIMITIVES):
		return obj
	elif isinstance(obj, (tuple, set, list)):
		return [jsonify(item, encoder=encoder) for item in obj]
	elif isinstance(obj, dict):
		return {k: jsonify(v, encoder=encoder) for k, v in obj.items()}
	elif encoder is not None:
		return encoder(obj)
	raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


