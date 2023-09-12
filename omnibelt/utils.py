
# from omnibelt import safe_self_execute

from typing import Iterator, Hashable

from collections import OrderedDict
from string import Formatter
from tqdm import tqdm
from tqdm.notebook import tqdm as tqdm_notebook


def format_readable_number(n, sig_figs):
	format_str = "{:." + str(sig_figs) + "g}"
	val = format_str.format(n)
	# remove trailing 0s
	if '.' in val:
		val = val.rstrip("0")
	# remove trailing .
	val = val.rstrip(".")
	return val


def human_readable_number(num, significant_figures=3, *, gap='', units=None):
	# Default units if not provided

	if num is None:
		return num

	if units is None:
		units = {
			"Q": 1_000_000_000_000_000,
			"T": 1_000_000_000_000,
			"B": 1_000_000_000,
			"M": 1_000_000,
			"K": 1_000,
			# "": 1
		}

	# Sort units from largest to smallest
	sorted_units = sorted(units.items(), key=lambda x: x[1], reverse=True)

	for unit, threshold in sorted_units:
		if abs(num) >= threshold:
			return format_readable_number(num / threshold, significant_figures) + gap + unit

	return format_readable_number(num, significant_figures)



def tqdmd(itr, key=None, **kwargs):
	pbar = tqdm(itr, **kwargs)
	for v in pbar:
		if key is not None:
			pbar.set_description(v if isinstance(key, bool) else key(v))
		yield v


def tqdmd_notebook(itr, key=None, **kwargs):
	pbar = tqdm_notebook(itr, **kwargs)
	for v in pbar:
		if key is not None:
			pbar.set_description(v if isinstance(key, bool) else key(v))
		yield v



def sign(x):
	return 0 if x == 0 else (1 if x > 0 else -1)


def expression_format(s, **vars):
	"""
	Evaluates the keys in the given string as expressions using the given variables
	"""
	fmt = Formatter()
	vals = {key:eval(key, vars) for _, key, _, _ in fmt.parse(s)}
	return s.format(**vals)



class PowerFormatter(Formatter):
	# TODO: partial formatting - only format fields that are specified, and leave others as is
	def get_field(self, field_name, args, kwargs):
		try:
			return super().get_field(field_name, args, kwargs)
		except: # TODO: find the right exception
			return eval(self.vformat(field_name, args, kwargs), kwargs), field_name
			# return f'{{{field_name}}}', field_name


	def parse(self, s):
		start_idx = -1
		escaped = ''
		pre_idx = 0
		counter = 0
		idx = 0

		while idx < len(s):
			open_idx = s.find("{", idx)
			close_idx = s.find("}", idx)

			if open_idx == -1 and close_idx == -1:
				if counter == 0:
					# raise StopIteration
					# print(f'ending with: {escaped + s[idx:]!r}')
					yield escaped + s[idx:], None, '', None
				else:
					raise ValueError("Mismatched '{' at index {}".format(start_idx))
				break

			if open_idx != -1 and (open_idx < close_idx or close_idx == -1):
				if counter == 0:
					# yield (s[idx:open_idx], None)
					start_idx = open_idx
					pre_idx = idx
				idx = open_idx + 1
				counter += 1

			if close_idx != -1 and (close_idx < open_idx or open_idx == -1):
				if counter == 0:
					raise ValueError("Mismatched '}' at index {}".format(close_idx))
				counter -= 1
				if counter == 0:
					pre = s[pre_idx:start_idx]
					field = s[start_idx + 1:close_idx]
					if field.startswith("{") and field.endswith("}"):
						escaped = pre + '{'

						for lit, field, spec, conv in self.parse(field[1:-1]):
							if escaped is not None:
								lit = escaped + lit
								escaped = None
							yield lit, field, spec, conv

						escaped = '}'

					else:
						# spec = None
						lim = field.rfind('}')
						conv_idx = field[lim+1:].find('!')
						if conv_idx != -1:
							conv = field[lim+2+conv_idx:]
							field = field[:lim+1+conv_idx]
						else:
							conv = None

						if conv is None:
							lim = field.rfind(']')
							spec_idx = field[lim+1:].find(':')
							if spec_idx != -1:
								spec = field[lim+2+spec_idx:]
								field = field[:lim+1+spec_idx]
							else:
								spec = ''
						else:
							spec_idx = conv.find(':')
							if spec_idx != -1:
								spec = conv[spec_idx+1:]
								conv = conv[:spec_idx]
							else:
								spec = ''

						# print(f'yielding: {escaped + pre!r}, {field!r}, {spec!r}, {conv!r}')
						# field = eval(self._format(field), self._world)
						yield escaped + pre, field, spec, conv
						escaped = ''
					start_idx = -1
				idx = close_idx + 1



def pformat(s, **vars):
	"""
	Evaluates the keys in the given string as expressions using the given variables (recursively)
	"""
	fmt = PowerFormatter()
	return fmt.format(s, **vars)




def safe_self_execute(obj, fn, default='<<short circuit>>',
				 flag='safe execute flag'):
	
	if flag in obj.__dict__:
		return default  # short circuit
	obj.__dict__[flag] = True
	
	try:
		out = fn()
	finally:
		del obj.__dict__['self printed flag']
	
	return out



def split_dict(items, keys):
	good, bad = OrderedDict(), OrderedDict()
	for k in items:
		if k in keys:
			good[k] = items[k]
		else:
			bad[k] = items[k]
	return good, bad



def filter_duplicates(*iterators: Iterator[Hashable]):
	seen = set()
	for itr in iterators:
		for x in itr:
			if x not in seen:
				seen.add(x)
				yield x







