
from .flow import safe_self_execute, multi_index
from .logging import get_printer, get_global_setting, get_global_settings, set_global_setting, set_printer_setting
from .typing import primitives, unspecified_argument, join_classes, replace_class, \
	duplicate_class, duplicate_func, duplicate_instance, wrap_class, mix_into, \
	conditional_method, lambda_conditional_method, agnosticmethod, agnostic, agnosticproperty
from .filesystem import create_dir, crawl, spawn_path_options, load_yaml, save_yaml, \
	load_csv, load_tsv, load_json, save_json, monkey_patch, load_txt, save_txt, Persistent, HierarchyPersistent, \
	load_pickle, save_pickle
from .timing import get_now, recover_date
from .patterns import Singleton, InitWall
from .containers import deep_get, Simple_Child, Proper_Child, AttrDict, AttrOrdDict, Value, LoadedValue, Named
from .registries import Registry, Entry_Registry, Named_Registry, Class_Registry, Path_Registry, Function_Registry
from .logic import sort_by, resolve_order, toposort
from .hashing import Hashable, md5
from .utils import sign, split_dict
from .ordered_set import OrderedSet
from .farming import WorkerPool
# from .exporting import export, load_export, Exportable
from .exporting import export, load_export, set_export_manager, ExportManager, Exporter, Exportable
from .tricks import self_aware, clsdec, innerchild, method_wrapper, ClassDescriptable, classdescriptor, \
	extract_function_signature, capturable_super, captured_super, auto_init, dynamic_capture, \
	smartproperty, autoproperty, referenceproperty, defaultproperty, TrackSmart, Tracer, \
	Modifiable, inject_modifiers

from .packing import Packable, primitive, Primitive, SERIALIZABLE, JSONABLE, pack, unpack
from .packing import save_pack, load_pack, json_pack, json_unpack
# from .pure_packing import pack, unpack, json_unpack, json_pack

from .transactions import Transactionable, AbortTransaction
from .wrappers import ObjectWrapper
from .nodes import OmniNode, OmniStructure, TreeNode, LocalNode
from .viz import printc, bcolors, colorize

# from .wrappers import ObjectWrapper, Array # causes an error if required libs aren't already installed
# try:
# 	import numpy
# except ImportError:
# 	pass
# else: # Register additional common packable types
# 	from . import common

from .basic_containers import adict, tdict, tlist, tset, tstack, tdeque, theap
from .basic_containers import containerify

from .structured import TreeSpace, Table, Key_Table

import os
__info__ = {'__file__':os.path.join(os.path.abspath(os.path.dirname(__file__)), '_info.py')}
with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), '_info.py'), 'r') as f:
	exec(f.read(), __info__)
del os
del __info__['__file__']
__author__ = __info__['author']
__version__ = __info__['version']

