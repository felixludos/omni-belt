
# from omnibelt import safe_self_execute

from collections import OrderedDict

def sign(x):
	return 0 if x == 0 else (1 if x > 0 else -1)


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








