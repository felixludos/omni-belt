
# from omnibelt import safe_self_execute
import re
import builtins
import ast
from typing import Iterator, Hashable, Any, Dict, List, Tuple
import sys
from collections import OrderedDict
from string import Formatter
import textwrap
from humanize import naturalsize
from tqdm import tqdm
from tqdm.notebook import tqdm as tqdm_notebook



def wrap_text(data: str, width: int = 80) -> str:
	"""
	Format data for display.
	"""
	return '\n'.join(textwrap.wrap(str(data), width=width))




def is_pycharm_debugger_running():
	return 'pydevd' in sys.modules


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



def human_size(size: int):
	return naturalsize(size, gnu=True, format='%.0f').replace('G', 'M').replace('T', 'B')



def fixed_width_format_positive(val: float, width: int) -> str:
	return fixed_width_format_value(val, width, force_positive=True)



def fixed_width_format_value(val: float, width: int, force_positive: bool = False) -> str:
	# https://chatgpt.com/c/6721c2ed-98ec-8005-b967-9b81f6b8d5f1

	if force_positive:
		s = fixed_width_format_value(val, width+1, force_positive=False)
		if s[0] == ' ':
			return s[1:]
		return s

	import math

	if width < 1:
		raise ValueError("Width must be at least 1.")

	# Determine the sign and adjust width accordingly
	sign = '-' if val < 0 else ' '
	number_width = width - 1  # Account for the sign character

	abs_val = abs(val)

	# Try fixed-point notation
	integer_part = int(abs_val)
	integer_part_str = str(integer_part)
	integer_part_length = len(integer_part_str)

	if integer_part_length <= number_width:
		# Calculate available space for decimal places
		decimal_places = number_width - integer_part_length - (1 if integer_part_length < number_width else 0)
		format_str = f"{{:0{number_width}.{decimal_places}f}}"
		formatted_number = format_str.format(abs_val)
		if len(formatted_number) <= number_width:
			formatted = sign + formatted_number
			if len(formatted) == width:
				return formatted
	# Scientific notation
	if abs_val == 0:
		exponent = 0
	else:
		exponent = int(math.floor(math.log10(abs_val)))
	mantissa = abs_val / (10 ** exponent)

	# Available space for mantissa and exponent
	exponent_str = f"e{exponent}" if exponent >= 0 else f"e-{abs(exponent)}"
	exponent_length = len(exponent_str)
	mantissa_width = number_width - exponent_length
	if mantissa_width < 1:
		raise ValueError(f"Cannot format value {val} in width {width}")

	for decimal_places in range(mantissa_width, -1, -1):
		mantissa_rounded = round(mantissa, decimal_places)
		# Adjust mantissa and exponent if mantissa_rounded >= 10
		if mantissa_rounded >= 10:
			mantissa_rounded /= 10
			exponent += 1
			exponent_str = f"e{exponent}" if exponent >= 0 else f"e-{abs(exponent)}"
			exponent_length = len(exponent_str)
			mantissa_width = number_width - exponent_length
			if mantissa_width < 1:
				continue  # Not enough width, try next decimal_places

		if decimal_places > 0:
			mantissa_format = f"{{:.{decimal_places}f}}"
			mantissa_str = mantissa_format.format(mantissa_rounded)
		else:
			mantissa_rounded_int = int(round(mantissa_rounded))
			mantissa_str = f"{mantissa_rounded_int}"
			if mantissa_width >= len(mantissa_str) + 1:
				mantissa_str += '.'
		mantissa_str_length = len(mantissa_str)
		if mantissa_str_length <= mantissa_width:
			formatted = sign + mantissa_str + exponent_str
			if len(formatted) == width:
				return formatted
	raise ValueError(f"Cannot format value {val} in width {width}")



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


_builtin_vars = dir(builtins)

class PowerFormatter(Formatter):
	@staticmethod
	def _ignore_variable(var: str):
		return var in _builtin_vars


	def parse(self, s):
		nodes = self.parse_bracket_tree(s)

		idx = 0
		for start, end, children in nodes:
			if children is None:
				if end > idx:
					literal = s[idx:end]
					yield literal, None, '', None
					idx = end + 1
			else:
				content, spec, conv = self.parse_field(s[start + 1:end])
				yield s[idx:start], content, spec, conv
				idx = end + 1

		if idx < len(s):
			yield s[idx:], None, '', None

	@staticmethod
	def parse_bracket_tree(s):
		'''
		Parses a string with bracket escapes into a tree of bracketed fields

		Output: [(start, end, children), ...]
		where start and end are the indices of the brackets, and children is a list of children nodes
		if children is None, then it's an escaped bracket
		'''
		stack = []
		extra_closes = []
		pairs = []
		for i, c in enumerate(s):
			if c == '{':
				stack.append(i)
			elif c == '}':
				if len(stack):
					start = stack.pop()
					pairs.append((start, i))
				else:
					extra_closes.append(i)

		# remove unpaired double bracket escapes
		assert all(i + 1 in stack or i - 1 in stack for i in
				   stack), f'Unbalanced opening brackets in {s!r} (remember to use double brackets to escape)'
		assert all(i + 1 in extra_closes or i - 1 in extra_closes for i in
				   extra_closes), f'Unbalanced closing brackets in {s!r} (remember to use double brackets to escape)'

		escaped_nodes = ([(i, i + 1, None) for i in stack if i + 1 in stack]  # escaped opening brackets
						 + [(i, i + 1, None) for i in extra_closes if
							i + 1 in extra_closes])  # escaped closing brackets
		escaped_pairs = [(start, end) for start, end in pairs if (start - 1, end + 1) in pairs]
		for start, end in escaped_pairs:
			pairs.remove((start - 1, end + 1))
			pairs.remove((start, end))
			escaped_nodes.append((start - 1, start, None))
			escaped_nodes.append((end, end + 1, None))

		if not len(pairs):
			return sorted(escaped_nodes)

		def build_interval_tree(remaining, lim=None):
			nodes = []
			while remaining and (lim is None or remaining[-1][0] < lim):
				start, end = remaining.pop()
				nodes.append((start, end, build_interval_tree(remaining, end)))
			return nodes

		tree = build_interval_tree(sorted(pairs, reverse=True))
		return sorted(escaped_nodes + tree)

	_spec_pattern = r'[<>=^]?[+\- ]?\d*(?:\.\d+)?[bcdeEfFgGnosxX%]?'
	def parse_field(self, field):
		content = field
		terms = field.split(':')
		spec = ''
		if len(terms) > 1:
			spec = terms[-1]
			match = re.match(self._spec_pattern, spec)
			if match is not None and match.group() == spec:
				content = ':'.join(terms[:-1])
			else:
				spec = ''
		conv = None
		if content.endswith('!r') or content.endswith('!s') or content.endswith('!a'):
			conv = content[-1]
			content = content[:-2]
		# ic(content, spec, conv)
		return content, spec, conv

	# def format(self, s, *args, **kwargs):
	# 	return self.vformat(s, args, kwargs)
	# def format_field(self, value, format_spec):
	# 	return super().format_field(value, format_spec)
	# def convert_field(self, value, conversion):
	# 	return super().convert_field(value, conversion)

	def variable_scope(self, expr, args, kwargs):
		vars = self._expression_variables(expr)
		scope = {}
		for key in vars:
			for src in [*args, kwargs]:
				try:
					scope[key] = src[key]
				except KeyError:
					pass
				else:
					break
			if key not in scope:
				if key in __builtins__:
					scope[key] = __builtins__[key]
				else:
					raise KeyError(f'Variable {key!r} not found in provided args or kwargs')
		return scope

	def get_field(self, field_name, args, kwargs):
		try:
			scope = self.variable_scope(field_name, args, kwargs)
			out = eval(field_name, scope)
		except SyntaxError:
			out = self.vformat(field_name, args, kwargs)
		return out, field_name

	def _expression_variables(self, expr):
		tree = ast.parse(expr, mode='eval')

		class VariableVisitor(ast.NodeVisitor):
			def __init__(self):
				self.variables = []

			def visit_Name(self, node):
				if node.id not in self.variables:
					self.variables.append(node.id)

		visitor = VariableVisitor()
		visitor.visit(tree)
		return list(visitor.variables)

	def variables(self, s: str, /, allow_repeats=False):
		nodes = self.parse_bracket_tree(s)
		past = set()
		for start, end, children in nodes:
			if children is None:
				continue
			elif len(children):
				for var in self.variables(s[start + 1:end], allow_repeats=allow_repeats):
					if var not in past and not self._ignore_variable(var):
						if not allow_repeats:
							past.add(var)
						yield var
			else:
				content, spec, conv = self.parse_field(s[start + 1:end])
				try:
					vars = self._expression_variables(content)
				except SyntaxError:
					continue
				for var in vars:
					if var not in past and not self._ignore_variable(var):
						if not allow_repeats:
							past.add(var)
						yield var



# test_cases = {
# 	'var!r': ('var', '', 'r'),
# 	'var2:5.2g': ('var2', '5.2g', None),
# 	'{1:0}!r': ('{1:0}', '', 'r'),
# 	'{1:0.5}[1]:.2f': ('{1:0.5}[1]', '.2f', None),
# 	'num:>10': ('num', '>10', None),
# 	'num!r:.2f': ('num', '.2f', 'r'),
# 	'{something_nice:.0f}_{num:>10}': ('{something_nice:.0f}_{num:>10}', '', None),
# 	'{something_nice:.0f}_{num:>10}:>10': ('{something_nice:.0f}_{num:>10}', '>10', None),
# }



def pformat(s: str, /, *srcs: Dict[str, Any], **manual: Any):
	"""
	Evaluates the keys in the given string as expressions using the given variables (recursively)

	The inside of brackets is evaluated as an expression using the variables in srcs and manual.
	Note that each of the `srcs` should behave like a dictionary implementing __getitem__ and __contains__.
	If a necessary variable is not found in any of the `srcs`, it will be looked up in `manual`.
	Also, all `srcs` and `manual` are checked each time a variable is looked up, so they can be updated.

	Also, for convenience, you can also treat the content inside the brackets as a format string. This just means,
	if you want something like this: `'{f"{x} and then {y}"}'`, you can just write `'{{x} and then {y}}'` instead.
	Note however, that this will only work if the content inside the brackets is not a valid expression.
	"""
	fmt = PowerFormatter()
	return fmt.vformat(s, srcs, manual)



def pformat_vars(s: str, /, allow_repeats=False):
	"""
	Returns the variables in the given string as expressions (recursively)

	See `pformat` doc for more details.
	"""
	fmt = PowerFormatter()
	yield from fmt.variables(s, allow_repeats=allow_repeats)



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







