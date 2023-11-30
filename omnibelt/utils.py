
# from omnibelt import safe_self_execute
import re
import ast
from typing import Iterator, Hashable, Any
import sys
from collections import OrderedDict
from string import Formatter
from tqdm import tqdm
from tqdm.notebook import tqdm as tqdm_notebook



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
					if var not in past:
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
					if var not in past:
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



def pformat(s: str, /, *srcs: dict[str, Any], **manual: Any):
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







