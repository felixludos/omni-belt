

try:
	import uuid
	from IPython.display import display_javascript, display_html
	import json
except ImportError:
	pass


class bcolors:
	BLUE = '\033[94m'
	CYAN = '\033[96m'
	GREEN = '\033[92m'
	YELLOW = '\033[93m'
	RED = '\033[91m'

	HEADER = '\033[95m'
	WARNING = '\033[93m'
	FAIL = '\033[91m'

	ENDC = '\033[0m'

	BOLD = '\033[1m'
	UNDERLINE = '\033[4m'

	color_table = {
		'blue': '\033[94m',
		'cyan': '\033[96m',
		'green': '\033[92m',
		'magenta': '\033[95m',
		'yellow': '\033[93m',
		'red': '\033[91m',

		'header': '\033[95m', # magenta
		'warning': '\033[93m', # yellow
		'fail': '\033[91m', # red
	}
	fmt_table = {
		'bold': '\033[1m',
		'underline': '\033[4m',
	}

def colorize(text, color=None, fmt=None):
	if color is None and fmt is None:
		return text
	else:
		fmt = bcolors.fmt_table.get(fmt.lower(), fmt) if isinstance(fmt, str) else ''
		color = bcolors.color_table.get(color.lower(), color) if isinstance(color, str) else ''
		return f'{color}{fmt}{text}{bcolors.ENDC}'

def printc(*args, color=None, fmt=None, sep=' ', **kwargs):
	print(colorize(sep.join(map(str, args)), color=color, fmt=fmt), **kwargs)


class render_dict(object):
	def __init__(self, json_data):
		if isinstance(json_data, dict):
			self.json_str = json.dumps(json_data)
		else:
			self.json_str = json_data
		self.uuid = str(uuid.uuid4())

	def _ipython_display_(self):
		display_html('<div id="{}" style="height: 100px; width:100%;"></div>'.format(self.uuid), raw=True)
		display_javascript("""
		require(["https://rawgit.com/caldwell/renderjson/master/renderjson.js"], function() {
		document.getElementById('%s').appendChild(renderjson(%s))
		});
		""" % (self.uuid, self.json_str), raw=True)
