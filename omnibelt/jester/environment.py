from typing import Union, Iterable, Tuple, Optional, List
import sys, os


def where_am_i():
	'''
	Returns a string indicating the current environment, allowing to differentiate among, for example:
	- 'jupyter': Jupyter notebook or JupyterLab
	- 'colab': Google Colab
	- 'cluster': Running on a cluster (defined by the presence of the 'JOB_ID' environment variable)
	- 'ci': Continuous integration environment
	- 'repl': Python REPL
	- 'pycharm': PyCharm IDE
	- 'vscode': Visual Studio Code
	- 'script': Running as a script
	'''
	loc = os.environ.get('WHEREAMI', None)
	if loc is not None:
		return loc

	try:
		from IPython import get_ipython
		if 'IPKernelApp' in get_ipython().config:
			return 'jupyter'
	except:
		pass

	if os.environ.get('JOB_ID', None) is not None:
		return 'cluster'
	elif 'COLAB_GPU' in os.environ:
		return "colab"
	elif any(ci in os.environ for ci in ['JENKINS_HOME', 'GITHUB_ACTIONS', 'GITLAB_CI', 'TRAVIS']):
		return "ci"
	# elif 'LAMBDA_RUNTIME_DIR' in os.environ:
	#     return "aws_lambda"
	# elif 'SPYDER' in sys.modules:
	#     return "spyder"
	# elif 'jupyterlab' in sys.modules:
	#     return "jupyterLab"
	elif hasattr(sys, 'ps1'):
		return 'repl'
	elif 'pydevd' in sys.modules:
		return 'pycharm'
	elif 'ptvsd' in sys.modules or 'debugpy' in sys.modules:
		return "vscode"

	return 'script'


def where_could_i_be():
	'''
	Returns a list of possible environments where the code could be running, allowing to differentiate among, for example:
	'''
	return ['jupyter', 'colab', 'cluster', 'ci',
			# 'aws_lambda', 'spyder', 'jupyterLab',
			'repl', 'pycharm', 'vscode', 'script']

