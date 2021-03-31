

def multi_index(obj, *inds):
	if len(inds):
		idx, *inds = inds
		return multi_index(obj[idx], *inds)
	return obj

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
