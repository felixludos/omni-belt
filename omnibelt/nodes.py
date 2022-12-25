
from typing import List, Dict, Tuple, Optional, Union, Any, Hashable, Sequence, Callable, Type, Iterator, Iterable
from datetime import datetime, timezone
from collections import OrderedDict, UserList, UserDict
from .ordered_set import OrderedSet
from .typing import agnosticmethod, unspecified_argument


class OmniStructure:
	pass



class OmniNode:
	def __copy__(self, **kwargs):
		return self.__class__(**kwargs)



class IntrinsicStructure(OmniStructure):
	'''The structure is fully defined by the collection of nodes (eg. linked list)'''
	def register(self, node: OmniNode) -> OmniStructure:
		raise NotImplementedError
	
	
	def deregister(self, node: OmniNode) -> OmniNode:
		raise NotImplementedError



class ExtrinsicStructure(OmniStructure):
	'''The structure includes auxillary information beyond the nodes (eg. dict)'''
	def register(self, addr: Hashable, node: OmniNode) -> OmniStructure:
		raise NotImplementedError
	
	
	def deregister(self, addr: Hashable) -> OmniNode:
		raise NotImplementedError



class ContextStructure(OmniStructure): # abstract
	_structure_instance_for_context = None
	def __new__(cls, *args, **kwargs):
		if cls._structure_instance_for_context is None:
			return super().__new__(cls, *args, **kwargs)
		return cls._structure_instance_for_context
	
	
	def __enter__(self):
		self.__class__._structure_instance_for_context = self
	
	
	def __exit__(self, exc_type, exc_val, exc_tb):
		del self.__class__._structure_instance_for_context



class PayloadNode(OmniNode):
	@property
	def payload(self) -> Any:
		raise NotImplementedError



class StructureNode(OmniNode):
	def __init__(self, structure: OmniStructure = None, **kwargs):
		super().__init__(**kwargs)
		self._structure = None
		self._structure = self._create_structure(structure)


	@property
	def structure(self) -> OmniStructure:
		return self._structure
	
	
	Structure = None
	def _create_structure(self, structure: OmniStructure = None, **kwargs) -> OmniStructure:
		if structure is None:
			structure = self.Structure(**kwargs)
		return structure.register(self)


	def _deregister(self):
		raise NotImplementedError

	
	def __copy__(self, structure: Optional[OmniStructure] = unspecified_argument, **kwargs):
		if structure is unspecified_argument:
			structure = self._structure
		return super().__copy__(structure=structure, **kwargs)
		
	
	def isolated_copy(self, structure=None, **kwargs):
		return self.__copy__(structure=None, **kwargs)
	


class AssertiveIntrinsicStructure(IntrinsicStructure):
	def register(self, node: StructureNode) -> OmniStructure:
		if node.structure is not self:
			node._structure = self
		return super().register(node)
		


class IdentNode(OmniNode):
	@property
	def identifier(self) -> Hashable:
		return hex(id(self))[2:]
	
	
	def __str__(self):
		return self.identifier
	
	
	def __repr__(self):
		return f'{self.__class__.__name__}:{self.identifier}'
	
	
	def __eq__(self, other):
		return self.identifier == other.identifier
	
	
	def __hash__(self):
		return hash(self.identifier)



class ExtrinsicToIntrinsicStructure(ExtrinsicStructure, IntrinsicStructure):
	def register(self, node: IdentNode) -> OmniStructure:
		return super().register(node.identifier, node)


	def deregister(self, node: IdentNode) -> OmniNode:
		return super().deregister(node.identifier)



class SequenceStructure(IntrinsicStructure, OrderedSet):
	def register(self, node: OmniNode) -> 'SequenceStructure':
		self.add(node)
		return self
	
	
	def deregister(self, node: OmniNode) -> 'SequenceStructure':
		self.remove(node)
		return self



class TableStructure(ExtrinsicStructure, OrderedDict):
	def register(self, addr: Hashable, node: OmniNode) -> 'TableStructure':
		self[addr] = node
		return self
	
	
	def deregister(self, addr: Hashable) -> OmniNode:
		node = self[addr]
		del self[addr]
		return node
	
	
	
class BaseStructure(OmniStructure):
	def __init__(self, base: OmniNode, structure: OmniStructure = None):
		super().__init__()
		self.base = base
		self.structure = structure
	
	
	def deregister_base(self):
		pass



class NodeEdgeStructure(IntrinsicStructure, OrderedDict):
	class NodeEdges(BaseStructure):
		pass


	def register(self, node: IdentNode, **kwargs) -> NodeEdges:
		ID = node.identifier
		if ID in self:
			return self[ID]
		edges = self.NodeEdges(node, self, **kwargs)
		self[ID] = edges
		return edges


	def deregister(self, node: IdentNode) -> IdentNode:
		ID = node.identifier
		self[ID].deregister_base()
		del self[ID]
		return node



class AbstractParentNode(OmniNode):
	@property
	def parent(self) -> OmniNode:
		raise NotImplementedError


	@property
	def children(self) -> OmniStructure:
		raise NotImplementedError



class ParentNode(AbstractParentNode): # single parent, many children
	def __init__(self,
	             parent: Optional[AbstractParentNode] = None,
	             children: Optional[Sequence[AbstractParentNode]] = None,
	             **kwargs):
		super().__init__(**kwargs)
		self._parent: Union[ParentNode, None] = None
		self.parent = parent
		if children is not None:
			self.add_children(*children)
	
	
	@property
	def parent(self) -> 'ParentNode':
		return self._parent
	@parent.setter
	def parent(self, parent: 'ParentNode'):
		if self._parent is not None:
			self.parent.children.deregister(self)
		if parent is not None:
			parent.children.register(self)
		self._parent = parent


	@property
	def children(self) -> IntrinsicStructure:
		raise NotImplementedError
	
	
	def add_children(self, *children: OmniNode) -> 'ParentNode':
		registry = self.children
		for child in children:
			registry.register(child)
		return self



class AbstractMultiParentNode(OmniNode):
	@property
	def parents(self) -> OmniStructure:
		raise NotImplementedError


	@property
	def children(self) -> OmniStructure:
		raise NotImplementedError



class MultiParentNode(AbstractMultiParentNode):  # single parent, many children
	def __init__(self,
	             parents: Optional[Sequence[AbstractMultiParentNode]] = None,
	             children: Optional[Sequence[AbstractMultiParentNode]] = None,
	             **kwargs):
		super().__init__(**kwargs)
		if parents is not None:
			self.add_parents(*parents)
		if children is not None:
			self.add_children(*children)
	

	def add_parents(self, *parents: 'MultiParentNode') -> 'MultiParentNode':
		registry = self.parents
		for parent in parents:
			registry.register(parent)
			# parent.children.register(self)
		return self
	
	
	def add_children(self, *children: 'MultiParentNode') -> 'MultiParentNode':
		registry = self.children
		for child in children:
			registry.register(child)
			# child.parents.register(self)
		return self



class GraphNode(StructureNode):
	class Structure(NodeEdgeStructure):
		class NodeEdges(NodeEdgeStructure.NodeEdges, SequenceStructure):
			def register(self, node: StructureNode) -> 'NodeEdges':
				node.structure.add(self.base)
				return super().register(node)
			
			
			def deregister(self, node: StructureNode) -> ParentNode:
				node = super().deregister(node)
				node.structure.remove(self.base)
				return node
			
			
			def deregister_base(self):
				for node in self:
					node.structure.remove(self.base)
				return super().deregister_base()



class GlobalTreeNode(ParentNode, StructureNode):
	@property
	def children(self) -> OmniStructure:
		return self.structure
	
	
	class Structure(NodeEdgeStructure):
		class NodeEdges(NodeEdgeStructure.NodeEdges):
			def register(self, node: ParentNode) -> 'NodeEdges':
				node._parent = self.base
				return super().register(node)
			
			
			def deregister(self, node: ParentNode) -> ParentNode:
				node = super().deregister(node)
				node._parent = None
				return node
			
			
			def deregister_base(self):
				for node in self:
					node._parent = None


class TableTreeNode(StructureNode): # Table Tree Node (tree where children have an address)
	class Structure(NodeEdgeStructure):
		class NodeEdges(NodeEdgeStructure.NodeEdges, TableStructure):
			def register(self, addr: Hashable, node: ParentNode) -> 'NodeEdges':
				node._parent = self.base
				return super().register(addr, node)

			def deregister(self, addr: Hashable) -> ParentNode:
				node = super().deregister(addr)
				node._parent = None
				return node

			def deregister_base(self):
				for node in self:
					node._parent = None



class DiGraphNode(MultiParentNode, StructureNode):
	class Structure(NodeEdgeStructure):
		class Parents(BaseStructure, SequenceStructure):
			def register(self, node: 'DiGraphNode') -> 'NodeEdges':
				node.children.add(self.base)
				return super().register(node)
			
			def deregister(self, node: 'DiGraphNode') -> 'DiGraphNode':
				node = super().deregister(node)
				node.children.remove(self.base)
				return node
			
			def deregister_base(self):
				for node in self:
					node.children.remove(self.base)
				return super().deregister_base()
		
		
		class Children(BaseStructure, SequenceStructure):
			def register(self, node: 'DiGraphNode') -> 'NodeEdges':
				node.parents.add(self.base)
				return super().register(node)
			
			def deregister(self, node: 'DiGraphNode') -> 'DiGraphNode':
				node = super().deregister(node)
				node.parents.remove(self.base)
				return node
			
			def deregister_base(self):
				for node in self:
					node.parents.remove(self.base)
				return super().deregister_base()
		
		
		class NodeEdges(NodeEdgeStructure.NodeEdges):
			def __init__(self, base: OmniNode, structure: OmniStructure,
			             parents: 'Parents', children: 'Children'):
				super().__init__(base, structure)
				self._parents = parents
				self._children = children
			
			
			@property
			def parents(self) -> 'Parents':
				return self._parents
			
			
			@property
			def children(self) -> 'Children':
				return self._children


			def deregister_base(self):
				for parent in self.parents:
					parent.children.deregister(self.base)
				for child in self.children:
					child.parents.deregister(self.base)
		
		
		def register(self, node: IdentNode, parents=unspecified_argument, children=unspecified_argument,
		             **kwargs) -> NodeEdges:
			if parents is unspecified_argument:
				parents = self.Parents(node, self)
			if children is unspecified_argument:
				children = self.Children(node, self)
			return super().register(node, parents=parents, children=children, **kwargs)

	
	@property
	def parents(self) -> 'Structure.Parents':
		return self.structure.parents

	
	@property
	def children(self) -> 'Structure.Children':
		return self.structure.children



class StampedNode(OmniNode):
	def __init__(self, timestamp=unspecified_argument, **kwargs):
		super().__init__(**kwargs)
		self._timestamp = datetime.now(tz=timezone.utc) if timestamp is unspecified_argument else timestamp
	
	
	def copy(self, timestamp=unspecified_argument, **kwargs):
		if timestamp is unspecified_argument:
			timestamp = self.timestamp
		return self.__copy__(timestamp=timestamp, **kwargs)
	
	
	@property
	def timestamp(self):
		return self._timestamp
	
	
	# def __hash__(self):
	# 	return hash(self.timestamp)
	#
	# def __eq__(self, other):
	# 	return self.timestamp == other.timestamp
	
	
	def __lt__(self, other):
		return self.timestamp < other.timestamp
	
	
	def __le__(self, other):
		return self.timestamp <= other.timestamp
	
	
	def __gt__(self, other):
		return self.timestamp > other.timestamp
	
	
	def __ge__(self, other):
		return self.timestamp >= other.timestamp



####################################################################################################

# if you need global structure in one object see TreeNode and TableTreeNode above (children, but not parent).
# if not, use LocalNode (parent and children only stored locally)


class LocalNode(PayloadNode):
	# DefaultNode = None
	ChildrenStructure = None

	class empty_value: pass
	empty_value.payload = empty_value

	class _MissingKey(KeyError): pass

	@classmethod
	def from_raw(cls, raw: Any, *, parent: Optional['LocalNode'] = unspecified_argument,
	             parent_key: Optional[str] = None, **kwargs) \
			-> Union['LocalNode', empty_value]:
		if isinstance(raw, LocalNode):
			raw.parent = parent
			raw._parent_key = parent_key
			return raw
		if raw is cls.empty_value or isinstance(raw, cls.empty_value):
			return raw
		return cls(payload=raw, parent=parent, **kwargs)

	def my_address(self):
		parent = self.parent
		return () if parent is None else parent.my_address() + (self.parent_key,)

	def __init__(self, payload=unspecified_argument, *, parent: Optional['LocalNode'] = unspecified_argument,
	             children: Optional[ChildrenStructure] = unspecified_argument,
	             parent_key: Optional[str] = None, **kwargs):
		super().__init__(**kwargs)
		self._payload = payload
		self._parent = parent
		if children is unspecified_argument:
			children = self.ChildrenStructure()
		self._children = children
		self._parent_key = parent_key


	@property
	def root(self) -> 'LocalNode':
		parent = self.parent
		if parent is None:
			return self
		return parent.root
	
	@property
	def parent(self):
		if self.has_parent:
			return self._parent
	@parent.setter
	def parent(self, value):
		self._parent = value
	@property
	def has_parent(self):
		return self._parent is not unspecified_argument
	@property
	def parent_key(self):
		return self._parent_key

	
	@property
	def payload(self):
		if self.has_payload:
			return self._payload
		return self._default_payload()
	@payload.setter
	def payload(self, value):
		self._payload = value
	@property
	def has_payload(self):
		return self._payload is not unspecified_argument


	@property
	def is_leaf(self):
		for _ in self.children(skip_empty=True):
			return False
		return True

	def __len__(self):
		return self._num_children()

	def __contains__(self, addr: Hashable):
		return self.has(addr)

	def __getitem__(self, addr: Hashable):
		return self.get(addr)

	def __setitem__(self, addr: Hashable, node: 'LocalNode'):
		return self.set(addr, node)

	def __delitem__(self, addr: Hashable):
		return self.remove(addr)

	def __iter__(self):
		return self.children()


	def _num_children(self):
		raise NotImplementedError


	def _get(self, addr: Hashable):
		raise NotImplementedError


	def _set(self, addr: Hashable, node: 'LocalNode'):
		raise NotImplementedError


	def _remove(self, key):
		raise NotImplementedError


	def _has(self, addr: Hashable):
		raise NotImplementedError


	def _iterate_children(self):
		raise NotImplementedError


	def _default_payload(self):
		return self.to_python()


	def to_python(self):
		if not self.has_payload:
			raise ValueError('no payload')
		return self.payload


	def named_children(self, skip_empty=True):
		for key, child in self._iterate_children():
			if skip_empty and child.is_leaf and not child.has_payload:
				continue
			yield key, child

	def children(self, skip_empty=True):
		for key, child in self.named_children(skip_empty=skip_empty):
			yield child

	def add_all(self, children: Iterable[Tuple[Hashable, 'LocalNode']], **kwargs) -> None:
		for addr, node in children:
			self.set(addr, node, **kwargs)


	def get(self, addr: Hashable, default: Any = unspecified_argument) -> 'LocalNode':
		try:
			return self._get(addr)
		except self._MissingKey:
			if default is unspecified_argument:
				raise
			return default


	def set(self, addr: Hashable, value: Any, **kwargs) -> 'LocalNode':
		node = self.from_raw(value, parent=self, parent_key=addr, **kwargs)
		self._set(addr, node)
		return node


	def has(self, addr: Hashable) -> bool:
		return self._has(addr)


	def remove(self, addr: Hashable) -> None:
		return self._remove(addr)



class SparseNode(LocalNode):
	ChildrenStructure = OrderedDict
	_python_structure = OrderedDict

	def _get(self, addr: Hashable) -> LocalNode:
		try:
			return self._children[addr]
		except KeyError:
			raise self._MissingKey(addr)

	def _set(self, addr: Hashable, node: LocalNode):
		self._children[addr] = node

	def _remove(self, addr: Hashable):
		del self._children[addr]

	def _has(self, addr: Hashable):
		return addr in self._children

	def _num_children(self):
		return len(self._children)

	def _iterate_children(self):
		return self._children.items()

	def to_python(self):
		return self._python_structure([(key, value.payload) for key, value in self._children.items()])



class DenseNode(LocalNode):
	ChildrenStructure = list
	_python_structure = list

	def _parse_index(self, addr: Hashable, strict: bool = False) -> int:
		if isinstance(addr, str):
			# if addr == '_':
			# 	addr = len(self)
			# else:
			addr = int(addr)
		if not isinstance(addr, int):
			raise ValueError(addr)
		if strict and not (-len(self._children) <= addr < len(self._children)):
			raise IndexError(addr)
		return addr

	def _get(self, addr: Hashable) -> LocalNode:
		try:
			return self._children[self._parse_index(addr, strict=True)]
		except (IndexError, ValueError):
			raise self._MissingKey(addr)

	def _set(self, addr: Hashable, node: LocalNode):
		idx = self._parse_index(addr, strict=False)
		if idx == len(self._children):
			self._children.append(node)
		elif -len(self._children) <= idx < len(self._children):
			self._children[idx] = node
		else:
			raise IndexError(addr)

	def _remove(self, addr: Hashable):
		del self._children[self._parse_index(addr, strict=True)]

	def _has(self, addr: Hashable):
		try:
			idx = self._parse_index(addr, strict=False)
		except IndexError:
			return False
		except ValueError:
			return False
		return -len(self._children) <= idx < len(self._children)

	def _num_children(self):
		return len(self._children)

	def _iterate_children(self):
		for i, x in enumerate(self._children):
			yield str(i), x

	def to_python(self):
		return self._python_structure(value.payload for value in self._children)

	def prepend(self, val: Any):
		self._children.insert(0, self.from_raw(val))

	def append(self, val: Any):
		self._children.append(self.from_raw(val))

	def insert(self, idx: int, val: Any):
		self._children.insert(idx, self.from_raw(val))

	def extend(self, vals: Iterable[Any]):
		self._children.extend(self.from_raw(val) for val in vals)


from indexed import IndexedOrderedDict

class IndexedSparseNode(LocalNode):
	ChildrenStructure = IndexedOrderedDict
	_python_structure = OrderedDict

	def _get(self, addr: Hashable) -> LocalNode:
		if isinstance(addr, int):
			return self._children.values()[addr]
		try:
			return self._children[addr]
		except KeyError:
			raise self._MissingKey(addr)

	def _set(self, addr: Hashable, node: LocalNode):
		if isinstance(addr, int):
			assert -len(self._children) <= addr < len(self._children), f'Index {addr} out of range'
			addr = self._children.keys()[addr]
		self._children[addr] = node

	def _remove(self, addr: Hashable):
		if isinstance(addr, int):
			assert -len(self._children) <= addr < len(self._children), f'Index {addr} out of range'
			addr = self._children.keys()[addr]
		del self._children[addr]

	def _has(self, addr: Hashable):
		if isinstance(addr, int):
			return -len(self._children) <= addr < len(self._children)
		return addr in self._children

	def _num_children(self):
		return len(self._children)

	def _iterate_children(self):
		yield from self._children.items()

	def to_python(self):
		return self._python_structure((key, value.payload) for key, value in self._children.items())

	def _default_payload(self):
		return self.to_python()


class TreeNode(LocalNode):
	DefaultNode: Type['TreeNode'] = SparseNode
	DenseNode: Type['TreeNode'] = None
	SparseNode: Type['TreeNode'] = None


	# def __new__(cls, raw: Any = unspecified_argument, **kwargs):
	# 	return cls.from_raw(raw)

	
	@classmethod
	def from_raw(cls, raw: Any, *, parent: Optional['LocalNode'] = unspecified_argument,
	             parent_key: Optional[str] = None, **kwargs) -> 'LocalNode':
		if isinstance(raw, LocalNode):
			raw.parent = parent
			raw._parent_key = parent_key
			return raw
		if isinstance(raw, dict):
			node = cls.SparseNode(parent=parent, parent_key=parent_key, **kwargs)
			for key, value in raw.items():
				node.set(key, cls.from_raw(value, parent=node, **kwargs), **kwargs)
		elif isinstance(raw, (tuple, list)):
			node = cls.DenseNode(parent=parent, parent_key=parent_key, **kwargs)
			for idx, value in enumerate(raw):
				idx = str(idx)
				node.set(idx, cls.from_raw(value, parent=node, **kwargs), **kwargs)
		else:
			node = cls.DefaultNode(payload=raw, parent=parent, **kwargs)
		return node


	@classmethod
	def from_dict(cls, raw: Dict[str, Any], *, parent: Optional['LocalNode'] = unspecified_argument,
	              **kwargs) -> 'LocalNode':
		return cls.from_raw(raw, parent=parent, **kwargs)



class TreeSparseNode(SparseNode, TreeNode): pass
class TreeDenseNode(DenseNode, TreeNode): pass

TreeNode.DefaultNode = TreeSparseNode
TreeNode.SparseNode = TreeSparseNode
TreeNode.DenseNode = TreeDenseNode



class ConvertableNode(TreeNode):
	def _convert_child(self, addr: Hashable, new_type: Type[LocalNode]) -> LocalNode:
		old = self.get(addr)
		new = new_type(parent=self)
		for key, value in old.children():
			new.set(key, value)
		self.set(addr, new)
		return new
	
	
	def convert_to_sparse(self, addr: Hashable) -> LocalNode:
		return self._convert_child(addr, self.SparseNode)


	def convert_to_dense(self, addr: Hashable) -> LocalNode:
		return self._convert_child(addr, self.DenseNode)



class AddressNode(LocalNode):
	_address_delimiter = '.'
	
	
	class _ConnectorError(LocalNode._MissingKey):
		def __init__(self, node, current, rest):
			super().__init__(current)
			self.node = node
			self.current = current
			self.rest = rest
	
	
	def _evaluate_address(self, addr: str) -> Tuple['AddressNode', str]:
		current, *rest = str(addr).split(self._address_delimiter)
		if len(rest):
			try:
				node = self[current] if len(current) else self.parent
			except KeyError:
				node = None
			if not isinstance(node, AddressNode):
				raise self._ConnectorError(self, current, rest)
			return node._evaluate_address(self._address_delimiter.join(rest))
		return self, current


	def flatten(self, include_connector_payloads=True, skip_empty=True) -> Iterator[Tuple[str, 'LocalNode']]:
		for key, value in self.children(skip_empty=skip_empty):
			assert isinstance(value, AddressNode), f'Unexpected node type: {type(value)}'
			if (include_connector_payloads and value.has_payload) or value.is_leaf:
				yield key, value.payload
			for subkey, subvalue in value.flatten(include_connector_payloads=include_connector_payloads,
			                                      skip_empty=skip_empty):
				yield f'{key}{self._address_delimiter}{subkey}', subvalue

	def get(self, addr: str, default: Any = unspecified_argument) -> 'LocalNode':
		node, key = self._evaluate_address(addr)
		return super(AddressNode, node).get(key, default)
		

	def set(self, addr: str, value: Any, **kwargs) -> 'LocalNode':
		node, key = self._evaluate_address(addr)
		return super(AddressNode, node).set(key, value, **kwargs)


	def has(self, addr: str) -> bool:
		try:
			node, key = self._evaluate_address(addr)
		except self._ConnectorError:
			return False
		return super(AddressNode, node).has(key)


	def remove(self, addr: str) -> None:
		node, key = self._evaluate_address(addr)
		return super(AddressNode, node).remove(key)



class AutoAddressNode(AddressNode):
	def _auto_create_child(self, key):
		return self.set(key, self.__class__(parent=self))

	def _evaluate_address(self, addr: str, auto_create: bool = False) -> Tuple['AddressNode', str]:
		try:
			return super()._evaluate_address(addr)
		except self._ConnectorError as e:
			if not auto_create:
				raise
			e.node._auto_create_child(e.current)
			return e.node._evaluate_address(self._address_delimiter.join((e.current, *e.rest)),
			                                auto_create=auto_create)

	def set(self, addr: str, value: Any, **kwargs):
		node, key = self._evaluate_address(addr, auto_create=True)
		return super(AddressNode, node).set(key, value, **kwargs)



class AutoTreeNode(AutoAddressNode, ConvertableNode, TreeNode):
	def _auto_create_child(self, key):
		node = self.DenseNode(parent=self) if key.isdigit() else self.SparseNode(parent=self)
		self.set(key, node)
class AutoTreeSparseNode(SparseNode, AutoTreeNode): pass
class AutoTreeDenseNode(DenseNode, AutoTreeNode):
	def _has(self, addr: Hashable):
		try:
			idx = self._parse_index(addr, strict=False)
		except IndexError:
			pass
		except TypeError:
			pass
		else:
			if -len(self._children) <= idx < len(self._children):
				return self._children[idx] is not self.empty_value
		return False

	def _set(self, addr: Hashable, node: LocalNode):
		idx = self._parse_index(addr, strict=False)
		if idx == len(self._children):
			self._children.append(node)
		elif -len(self._children) <= idx < len(self._children):
			self._children[idx] = node
		elif idx > 0:
			self._children.extend([self.empty_value] * (idx - len(self._children)))
			self._children.append(node)
		else:
			raise IndexError(idx)

AutoAddressNode.DefaultNode = AutoTreeSparseNode
AutoTreeNode.SparseNode = AutoTreeSparseNode
AutoTreeNode.DenseNode = AutoTreeDenseNode


####################################################################################################


class LeafNode(PayloadNode):
	def __init__(self, payload=unspecified_argument, **kwargs):
		super().__init__(**kwargs)
		self._payload = payload

	
	@property
	def payload(self):
		return self._payload



class TimelineNode(StructureNode):
	Structure = SequenceStructure
	# class Structure(SequenceStructure):
	# 	@property
	# 	def origin(self) -> StructureNode:
	# 		return self[0]
	
	
	@property
	def origin(self) -> StructureNode:
		return self.structure[0]
	
	
	def trajectory(self):
		idx = self.structure.index(self)
		for i in range(0, idx):
			yield self.structure[i]
	
	
	def past(self):
		idx = self.structure.index(self)
		for i in range(idx-1, -1, -1):
			yield self.structure[i]
	
	
	def future(self):
		idx = self.structure.index(self)
		for i in range(idx + 1, len(self.structure)):
			yield self.structure[i]
	



# class ConfigNode(Node):
# 	AntiNode = AntiNode
# 	ReferenceNode = ReferenceNode


#
# class SpaceTimeNode:
# 	def past(self, addr=None):
# 		raise NotImplementedError
#
# 	def future(self, addr=None):
# 		raise NotImplementedError
#
# 	def super(self, addr=None):
# 		raise NotImplementedError
#
# 	def sub(self, addr=None):
# 		raise NotImplementedError
	


# class AddressNode(SpaceTimeNode):
# 	def __init__(self, **kwargs):
# 		super().__init__(**kwargs)
# 		self._past_nodes = self.AddressBook()
# 		self._future_nodes = self.AddressBook()
# 		self._sub_nodes = self.AddressBook()
# 		self._super_nodes = self.AddressBook()
#
#
# 	class AddressBook:
# 		def __init__(self, **kwargs):
# 			super().__init__(**kwargs)
# 			self._addresses = []
# 			self._address_index = {}
#
# 		def cut(self, addr):
# 			if addr in self._address_index:
# 				index = self._address_index[addr]
# 				del self._addresses[index]
# 				del self._address_index[addr]
#
# 		def push(self, addr):
# 			if addr not in self._address_index:
# 				self._addresses.append(addr)
# 				self._address_index[addr] = len(self._addresses) - 1
#
#
# 		def recover(self, addr):
# 			if addr in self._address_index:
# 				return self._addresses[self._address_index[addr]]
#
#
# 		def next(self, addr=None):
# 			if addr is None and len(self._addresses) > 0:
# 				return self._addresses[0]
# 			if addr not in self._address_index or self._address_index[addr] == len(self._addresses) - 1:
# 				return None
# 			return self._addresses[self._address_index[addr] + 1]
#
#
# 		def search(self, addr=None):
# 			current = 0 if addr is None or addr not in self._address_index else self._address_index[addr]+1
# 			while current < len(self._addresses):
# 				yield self._addresses[current]
# 				current += 1
#
#
# 		def __len__(self):
# 			return len(self._addresses)
#
#
# 		def __contains__(self, item):
# 			return item in self._address_index
#
#
# 	def past(self, addr=None):
# 		return self._past_nodes.next(addr)
#
#
# 	def future(self, addr=None):
# 		return self._future_nodes.next(addr)
#
#
# 	def sub(self, addr=None):
# 		return self._sub_nodes.next(addr)
#
#
# 	def super(self, addr=None):
# 		return self._super_nodes.next(addr)
#
#
#
# class DataNode(SpaceTimeNode):
# 	def __init__(self, payload=None, **kwargs):
# 		super().__init__(**kwargs)
# 		self.data = payload
#
#
#
# class ReferenceNode(AddressNode, DataNode):
# 	pass
#
#
#
# class LeafNode(AddressNode, DataNode):
# 	pass
#
#
# class Structure:
# 	def update(self, addr=None, **kwargs):
# 		raise NotImplementedError
#
# 	def attach(self, addr=None, **kwargs):
# 		raise NotImplementedError
#
#
# 	def assemble(self, base=None, **kwargs):
# 		raise NotImplementedError
#
# 	def forecast(self, base=None, **kwargs):
# 		raise NotImplementedError
#
# 	def external(self, addr=None, **kwargs):
# 		raise NotImplementedError
#
# 	def internal(self, addr=None, **kwargs):
# 		raise NotImplementedError
#
# 	def owners(self, base=None, **kwargs):
# 		raise NotImplementedError
#
# 	def followers(self, base=None, **kwargs):
# 		raise NotImplementedError
#
#
#
#
# class BranchNode(AddressNode, DataNode):
#
# 	class _missing_value:
# 		pass
#
#
# 	class PullError(KeyError):
# 		def __init__(self, addr):
# 			super().__init__(str(addr))
# 			self.addr = addr
#
#
# 	def attach(self, node):
# 		self._sub_nodes.push(node)
# 		node._super_nodes.push(self)
#
#
# 	def update(self, node):
# 		self._future_nodes.push(node)
# 		node._past_nodes.push(self)
#
#
# 	def nodify(self, obj):
# 		'''Returns a node from the given object.'''
# 		raise NotImplementedError
#
#
# 	def pull(self, *addrs, default=unspecified_argument, **construct_args):
# 		trace = self._trace_pull(*addrs, default=default)
# 		return self.construct(trace, **construct_args)
#
#
# 	def pull_node(self, *addrs, default=unspecified_argument):
# 		trace = self._trace_pull(*addrs, default=default)
# 		return trace[-1]
# 		raise NotImplementedError
#
#
# 	class AddressTrace:
# 		def __init__(self, addrs=None, default=None, **kwargs):
# 			super().__init__(**kwargs)
# 			self.addrs = addrs
# 			self.default = default
# 			self.records = None
#
#
# 		class TracedRecord:
# 			__slots__ = ('trace', 'predecessor', 'record')
# 			def __init__(self, trace, predecessor=None, **kwargs):
# 				super().__init__(**kwargs)
# 				self.trace = trace
# 				self.predecessor = predecessor
# 				self.record = None
#
# 			def collect(self):
# 				records = [self.record]
# 				record = self
# 				while record.predecessor is not None:
# 					records.append(record.record)
# 					record = record.predecessor
# 				self.trace.records = records[::-1]
#
# 			def append(self, *args, **kwargs):
# 				self.record = args, kwargs
# 				return self.trace.create_record(predecessor=self, **kwargs)
#
#
# 		def create_record(self, predecessor=None, trace=None, **kwargs):
# 			if trace is None:
# 				trace = self
# 			return self.TracedRecord(trace=trace, predecessor=predecessor, **kwargs)
#
#
# 		def append(self, *args, **kwargs):
# 			return self.create_record(predecessor=self).append(*args, **kwargs)
#
#
# 		@classmethod
# 		def _flatten_trace(cls, path, node):
# 			'''Flattens the given trace.'''
# 			trace = [node]
# 			while len(path) > 1:
# 				trace.append(path[-1])
# 				path = path[0]
# 			trace.append(path[0])
# 			return trace[::-1]
#
#
# 	def _trace_pull(self, *addrs, default=unspecified_argument, trace=None):
# 		if default is not unspecified_argument:
# 			default = self.nodify(default)
# 		if trace is None:
# 			trace = self.AddressTrace(addrs=addrs, default=default)
# 		for addr in addrs:
# 			try:
# 				result = self._pull_remote(addr, trace=trace.append(addr=addr, node=self))
# 			except self.PullError:
# 				pass
# 			else:
# 				return result.collect()
# 		if default is not unspecified_argument:
# 			return trace
# 		raise self.PullError(addrs)
#
#
#
# 	def _pull_remote(self, addr, trace=None):
# 		try:
# 			return self._pull_local(addr, trace=trace)
# 		except self.PullError:
# 			# for past in self._past_nodes.search():
# 			# 	try:
# 			# 		return past._pull_remote(addr, trace=None if trace is None else trace.append(up=past))
# 			# 	except self.PullError:
# 			# 		pass
# 			for sup in self._super_nodes.search():
# 				try:
# 					return sup._pull_remote(addr, trace=None if trace is None else trace.append(left=sup))
# 				except self.PullError:
# 					pass
# 		raise self.PullError(addr)
#
#
# 	@staticmethod
# 	def _parse_addr(addr):
# 		if addr is None:
# 			return None
# 		if isinstance(addr, tuple):
# 			return addr
# 		if isinstance(addr, list):
# 			return tuple(addr)
# 		if isinstance(addr, str):
# 			if len(addr) == 0:
# 				return None
# 			return tuple(addr.split('.'))
# 		return (addr,)
#
#
# 	def _pull_local(self, addr, trace=None):
#
# 		terms = self._parse_addr(addr)
# 		if trace is not None and terms != addr:
# 			trace = trace.append(terms=terms, addr=addr)
# 		try:
# 			if terms is None or len(terms) == 0:
# 				return trace.append(terms=terms)
#
# 			if terms[0] == '':
# 				if len(terms) > 1:
# 					return self.super()._pull_local(terms[1:], trace=None if trace is None else trace.append(left=sup))
# 				return
# 			sub = self._sub_nodes.recover(terms[0])
# 			trace = (_trace, sub)
# 			if len(terms) > 1:
# 				return sub._pull_local(terms[1:], _trace=trace)
# 			return trace
# 		except self.PullError:
# 			for past in self._past_nodes.search():
# 				try:
# 					return past._pull_local(addr, _trace=trace)
# 				except self.PullError:
# 					pass
# 		raise self.PullError(addr)
#
#
# 	def push(self, addr, val):
# 		raise NotImplementedError
#
#
# 	def construct(self, trace, **kwargs):
# 		'''Processes and returns the payload of the node.'''
# 		return self.data
#
# 	pass
#
#
# class Integral:
# 	def touch(self, node):
# 		pass
#
# 	def mark(self, node):
# 		pass
#
# 	def untouched(self, nodes):
# 		pass
#
#
# class Trajectory:
# 	def step(self, current, target):
# 		pass
#
#
#
#
# class Node:
# 	def __init__(self, *args, **kwargs):
# 		super().__init__(*args, **kwargs)
# 		self._up = {}
# 		self._down = {}
# 		self._left = {}
# 		self._right = {}
#
#
# 	def _move_along_edge(self, direction, edges, key):
# 		if edges is None:
# 			return None
# 		return edges.get(key)
#
#
# 	def _set_single_edge(self, direction, edges, key, val=None):
# 		edges[key] = val
# 		return edges
#
#
# 	def up(self, key=None):
# 		return self._move_along_edge('up', edges=self._up, key=key)
#
#
# 	def down(self, key=None):
# 		return self._move_along_edge('down', edges=self._down, key=key)
#
#
# 	def left(self, key=None):
# 		return self._move_along_edge('left', edges=self._left, key=key)
#
#
# 	def right(self, key=None):
# 		return self._move_along_edge('right', edges=self._right, key=key)
#
#
# 	def set_up(self, key, val=None):
# 		self._set_single_edge('up', edges=self._up, key=key, val=val)
#
#
# 	def set_down(self, key, val=None):
# 		self._set_single_edge('down', edges=self._down, key=key, val=val)
#
#
# 	def set_left(self, key, val=None):
# 		self._set_single_edge('left', edges=self._left, key=key, val=val)
#
#
# 	def set_right(self, key, val=None):
# 		self._set_single_edge('right', edges=self._right, key=key, val=val)
#
#
#
# class DataNode(Node):
# 	def __init__(self, payload=None, **kwargs):
# 		super().__init__(**kwargs)
# 		self._payload = payload
#
#
# 	@property
# 	def payload(self):
# 		return self._payload










