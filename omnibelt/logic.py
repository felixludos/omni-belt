# from c3linearize import linearize
from collections import deque


# courtesy of chat-gpt (with modifications)

def linearize(graph):
	'''
	C3 linearization of a DAG of hashable nodes (using python type system directly)

	:param graph: dict of {node: [parents]}

	:return: dict of {node: [parents]}

	:raises CycleDetectedError: if a cycle is detected
	'''
	toname = {node: f'_n{i}' for i, node in enumerate(graph)}
	totyp = {}
	tonode = {}

	for node in toposort(graph):
		typ = type(toname[node], tuple(totyp[e] for e in graph[node]), {})
		totyp[node] = typ
		tonode[typ] = node

	return {node: [tonode[t] for t in  typ.mro()[:-1]] for node, typ in totyp.items()}



class CycleDetectedError(ValueError):
	def __init__(self, remaining):
		super().__init__(f'Cycle detected near: {remaining}')
		self.remaining = remaining



def toposort(graph):
	'''
	Topological sort of a DAG of hashable nodes (using python type system directly)

	:param graph: dict of {node: [parents]}

	:return: dict of {node: [parents]}

	:raises CycleDetectedError: if a cycle is detected
	'''
	# Create a dictionary mapping each class to its ancestors
	ancestors = {}
	for node, parents in graph.items():
		ancestors[node] = set(parents)

	# Perform the topological sort
	toporder = []
	while len(ancestors) > 0:
		# Find a class with no ancestors
		for node in ancestors:
			if len(ancestors[node]) == 0:
				break
		else:
			raise CycleDetectedError(ancestors)
		# Remove this class from the ancestor dictionary and add it to the output list
		toporder.append(node)
		del ancestors[node]
		# Decrement the ancestor count for each of this class's descendants
		for descendant, parents in ancestors.items():
			ancestors[descendant].discard(node)
	return toporder

#
# def linearize(classes):
#     # Sort the list of classes in topological order
#     classes = topological_sort(classes)
#     linearization = []
#     for cls in classes:
#         # Check for an explicit linearization of this class
#         if hasattr(cls, '__linearization__'):
#             linearization.extend(cls.__linearization__)
#         else:
#             linearization.append(cls)
#     return linearization
#
# def topological_sort(classes):
#     """
#     Perform a topological sort on the given list of classes.
#     """
#     # Create a dictionary mapping each class to the set of its ancestors
#     ancestors = {}
#     for cls in classes:
#         ancestors[cls] = set(cls.__bases__)
#
#     # Perform the topological sort
#     sorted_classes = []
#     while len(ancestors) > 0:
#         # Find a class with no ancestors
#         for cls in ancestors:
#             if len(ancestors[cls]) == 0:
#                 break
#         else:
#             raise ValueError("Inheritance graph contains a cycle")
#         # Remove this class from the ancestor dictionary and add it to the output list
#         sorted_classes.append(cls)
#         del ancestors[cls]
#         # Decrement the ancestor count for each of this class's descendants
#         for descendant in ancestors:
#             ancestors[descendant].discard(cls)
#     return sorted_classes







def sort_by(seq, vals, reverse=False):
	return [x[0] for x in sorted(zip(seq, vals), key=lambda x: x[1], reverse=reverse)]



def resolve_order(key, *srcs, valid=None):
	'''
	All sources must either be callable or a dict-like (implementing .get())
	If no ``valid`` is provided, only outputs that are ``None`` is treated as invalid.
	
	:param key: key to be found
	:param srcs: ordered sources that may contain key
	:param valid: callable returns a bool whether or not the source output should be accepted
	:return: output corresponding to key of the first source that produced a valid output
	'''
	for src in srcs:
		val = src(key) if callable(src) else src.get(key, None)
		if (valid is None and val is not None) or (valid is not None and valid(val)):
			return val



# class CycleDetectedError(Exception):
# 	def __init__(self, node):
# 		super().__init__('Cycle detected near: {}'.format(node))


# graph = {0:[1,2], 1:[3,4], 2:[4,6], 3:[7], 4:[5], 5:[], 6:[], 7:[]}
# util.toposort(0,lambda x: graph[x], depth_first=True)
# produces: [0, 1, 3, 7, 2, 4, 6, 5]
# but should be: [0, 1, 3, 7, 2, 4, 5, 6]

# def graph_conv(x, g, d=None):
# 	if d is None:
# 		d = {}
# 	if x not in d:
# 		e = g(x)
# 		if x not in d:
# 			d[x] = e
# 		for v in e:
# 			graph_conv(v, g, d)
# 	return d
#
#
# # def toposort(root, src):
# # 	return linearize(src, heads=[root], order=True)[root]
#
# def toposort(root, get_edges, ordered=True): # TODO: this is super messy and must be cleaned up
# 	src = graph_conv(root, get_edges)
#
# 	return linearize(src, heads=[root], order=ordered)[root]
#
#
# def _toposort_bad(root, get_edges, depth_first=False):
# 	if depth_first:
# 		raise NotImplementedError  # not working atm
#
# 	order = [root]
# 	done = set(order)
# 	options = deque(get_edges(root))
#
# 	while len(options):
#
# 		next = None
# 		for node in options:
# 			success = True
# 			for check in options:
# 				if node in get_edges(check):
# 					success = False
# 					break
# 			if success:
# 				next = node
# 				break
# 		if next is None:
# 			raise CycleDetectedError(node)
# 		else:
# 			options.remove(next)
# 			if next not in done:
# 				order.append(next)
# 				done.add(next)
# 				if depth_first:
# 					options.extendleft(reversed(get_edges(next)))
# 				else:
# 					options.extend(get_edges(next))
#
# 	return order


