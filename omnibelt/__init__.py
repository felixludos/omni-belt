
from .flow import safe_self_execute
from .logging import get_printer, get_global_setting, get_global_settings, set_global_setting
from .filesystem import create_dir, crawl, spawn_path_options, load_yaml, save_yaml
from .typing import primitives
from .timing import get_now
from .containers import deep_get, Simple_Child, Proper_Child
from .logic import sort_by, resolve_order, toposort

import os
__info__ = load_yaml(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.fig.yaml'))
__author__ = __info__['author']
__version__ = __info__['version']

