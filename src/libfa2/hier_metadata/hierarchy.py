"""
Hierarchy module for managing the metric tree structure.

This module defines the Hierarchy class which manages a tree structure
of MetricNode instances and provides methods for navigation, validation,
and serialization.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from libfa2.hier_metadata.enums import (
    DriverType,
    MetricType,
    ValidationErrorType,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from libfa2.hier_metadata.metric_node import MetricNode


@dataclass
class ValidationError:
    """
    Represents a validation error for hierarchy metadata.

    Attributes:
        type: The type of validation error.
        message: Human-readable description of the error.
        node_id: ID of the node where the error occurred, if applicable.
        details: Additional context about the error.
    """

    type: ValidationErrorType
    """The type of validation error."""

    message: str
    """Human-readable description of the error."""

    node_id: int | None = None
    """ID of the node where the error occurred, if applicable."""

    details: dict[str, Any] | None = None
    """Additional context about the error."""

    def __repr__(self) -> str:
        """Return a string representation of the ValidationError."""
        node_info = f", node_id={self.node_id}" if self.node_id else ""
        return f"ValidationError(type={self.type}, message={self.message!r}{node_info})"


@dataclass
class ValidationReport:
    """
    Report containing the results of hierarchy validation.

    Attributes:
        is_valid: True if no errors were found, False otherwise.
        errors: List of validation errors found.
    """

    is_valid: bool
    """True if no errors were found, False otherwise."""

    errors: list[ValidationError] = field(default_factory=list)
    """List of validation errors found."""

    @classmethod
    def success(cls) -> ValidationReport:
        """Create a success report with no errors."""
        return cls(is_valid=True, errors=[])

    @classmethod
    def failure(cls, errors: list[ValidationError]) -> ValidationReport:
        """Create a failure report with the given errors."""
        return cls(is_valid=False, errors=errors)


@dataclass
class Hierarchy:
    """
    Manages a tree structure of MetricNode instances.

    The Hierarchy class provides methods for:
    - Building a tree from a flat list of nodes
    - Navigating the tree (finding children, parents, ancestors, descendants)
    - Serializing to/from JSON
    - Validating the structure

    Attributes:
        nodes: Dictionary mapping node IDs to MetricNode instances.
    """

    nodes: dict[int, MetricNode] = field(default_factory=dict)
    """Dictionary mapping node IDs to MetricNode instances."""

    @property
    def root(self) -> MetricNode | None:
        """
        Get the root node of the hierarchy.

        Returns:
            The root MetricNode if found, None otherwise.

        Examples:
            >>> hierarchy = Hierarchy()
            >>> hierarchy.add_node(MetricNode(id=1, code="ROOT", name="Root"))
            >>> hierarchy.root is not None
            True
            >>> hierarchy.root.id
            1
        """
        for node in self.nodes.values():
            if node.parent is None:
                return node
        return None

    @property
    def node_ids(self) -> set[int]:
        """
        Get the set of all node IDs in the hierarchy.

        Returns:
            Set of all node IDs.

        Examples:
            >>> hierarchy = Hierarchy()
            >>> hierarchy.add_node(MetricNode(id=1, code="A", name="A"))
            >>> hierarchy.add_node(MetricNode(id=2, code="B", name="B"))
            >>> hierarchy.node_ids
            {1, 2}
        """
        return set(self.nodes.keys())

    @property
    def codes(self) -> set[str]:
        """
        Get the set of all metric codes in the hierarchy.

        Returns:
            Set of all metric codes.

        Examples:
            >>> hierarchy = Hierarchy()
            >>> hierarchy.add_node(MetricNode(id=1, code="A", name="A"))
            >>> hierarchy.add_node(MetricNode(id=2, code="B", name="B"))
            >>> hierarchy.codes
            {'A', 'B'}
        """
        return {node.code for node in self.nodes.values()}

    def add_node(self, node: MetricNode) -> None:
        """
        Add a node to the hierarchy.

        Args:
            node: The MetricNode to add.

        Raises:
            ValueError: If a node with the same ID already exists.

        Examples:
            >>> hierarchy = Hierarchy()
            >>> node = MetricNode(id=1, code="A", name="A")
            >>> hierarchy.add_node(node)
            >>> 1 in hierarchy.nodes
            True
        """
        if node.id in self.nodes:
            raise ValueError(f"Node with id={node.id} already exists")
        self.nodes[node.id] = node

    def add_nodes(self, nodes: Iterable[MetricNode]) -> None:
        """
        Add multiple nodes to the hierarchy.

        Args:
            nodes: Iterable of MetricNode instances to add.

        Raises:
            ValueError: If any node with the same ID already exists.

        Examples:
            >>> hierarchy = Hierarchy()
            >>> nodes = [
            ...     MetricNode(id=1, code="A", name="A"),
            ...     MetricNode(id=2, code="B", name="B")
            ... ]
            >>> hierarchy.add_nodes(nodes)
            >>> len(hierarchy)
            2
        """
        for node in nodes:
            if node.id in self.nodes:
                raise ValueError(f"Node with id={node.id} already exists")
        for node in nodes:
            self.nodes[node.id] = node

    def remove_node(self, node_id: int) -> None:
        """
        Remove a node from the hierarchy.

        Args:
            node_id: ID of the node to remove.

        Raises:
            KeyError: If no node with the given ID exists.

        Examples:
            >>> hierarchy = Hierarchy()
            >>> node = MetricNode(id=1, code="A", name="A")
            >>> hierarchy.add_node(node)
            >>> hierarchy.remove_node(1)
            >>> 1 in hierarchy.nodes
            False
        """
        if node_id not in self.nodes:
            raise KeyError(f"Node with id={node_id} not found")
        del self.nodes[node_id]

    def get_node(self, node_id: int) -> MetricNode | None:
        """
        Get a node by its ID.

        Args:
            node_id: ID of the node to retrieve.

        Returns:
            The MetricNode if found, None otherwise.

        Examples:
            >>> hierarchy = Hierarchy()
            >>> node = MetricNode(id=1, code="A", name="A")
            >>> hierarchy.add_node(node)
            >>> hierarchy.get_node(1).id
            1
            >>> hierarchy.get_node(999) is None
            True
        """
        return self.nodes.get(node_id)

    def get_node_by_code(self, code: str) -> MetricNode | None:
        """
        Get a node by its code.

        Args:
            code: Code of the node to retrieve.

        Returns:
            The MetricNode if found, None otherwise.

        Examples:
            >>> hierarchy = Hierarchy()
            >>> node = MetricNode(id=1, code="INT_INC", name="Interest Income")
            >>> hierarchy.add_node(node)
            >>> hierarchy.get_node_by_code("INT_INC").id
            1
            >>> hierarchy.get_node_by_code("NOT_FOUND") is None
            True
        """
        for node in self.nodes.values():
            if node.code == code:
                return node
        return None

    def get_children(self, node_id: int) -> list[MetricNode]:
        """
        Get all children of a node.

        Args:
            node_id: ID of the parent node.

        Returns:
            List of child nodes. Empty list if node has no children.

        Examples:
            >>> hierarchy = Hierarchy()
            >>> parent = MetricNode(id=1, code="PARENT", name="Parent")
            >>> child = MetricNode(id=2, code="CHILD", name="Child", parent=1)
            >>> hierarchy.add_node(parent)
            >>> hierarchy.add_node(child)
            >>> [c.id for c in hierarchy.get_children(1)]
            [2]
        """
        return [node for node in self.nodes.values() if node.parent == node_id]

    def get_parent(self, node_id: int) -> MetricNode | None:
        """
        Get the parent of a node.

        Args:
            node_id: ID of the child node.

        Returns:
            The parent MetricNode if found, None otherwise.

        Examples:
            >>> hierarchy = Hierarchy()
            >>> parent = MetricNode(id=1, code="PARENT", name="Parent")
            >>> child = MetricNode(id=2, code="CHILD", name="Child", parent=1)
            >>> hierarchy.add_node(parent)
            >>> hierarchy.add_node(child)
            >>> hierarchy.get_parent(2).id
            1
        """
        node = self.get_node(node_id)
        if node is None or node.parent is None:
            return None
        return self.get_node(node.parent)

    def get_ancestors(self, node_id: int) -> list[MetricNode]:
        """
        Get all ancestors of a node, from parent up to root.

        Args:
            node_id: ID of the starting node.

        Returns:
            List of ancestor nodes. Empty list if node has no parent.

        Examples:
            >>> hierarchy = Hierarchy()
            >>> root = MetricNode(id=1, code="ROOT", name="Root")
            >>> child = MetricNode(id=2, code="CHILD", name="Child", parent=1)
            >>> grandchild = MetricNode(id=3, code="GC", name="Grandchild", parent=2)
            >>> hierarchy.add_node(root)
            >>> hierarchy.add_node(child)
            >>> hierarchy.add_node(grandchild)
            >>> [n.id for n in hierarchy.get_ancestors(3)]
            [2, 1]
        """
        ancestors: list[MetricNode] = []
        current = self.get_parent(node_id)
        while current is not None:
            ancestors.append(current)
            current = self.get_parent(current.id)
        return ancestors

    def get_descendants(self, node_id: int) -> list[MetricNode]:
        """
        Get all descendants of a node (all levels deep).

        Args:
            node_id: ID of the starting node.

        Returns:
            List of all descendant nodes. Empty list if node has no children.

        Examples:
            >>> hierarchy = Hierarchy()
            >>> root = MetricNode(id=1, code="ROOT", name="Root")
            >>> child = MetricNode(id=2, code="CHILD", name="Child", parent=1)
            >>> grandchild = MetricNode(id=3, code="GC", name="Grandchild", parent=2)
            >>> hierarchy.add_node(root)
            >>> hierarchy.add_node(child)
            >>> hierarchy.add_node(grandchild)
            >>> [n.id for n in hierarchy.get_descendants(1)]
            [2, 3]
        """
        descendants: list[MetricNode] = []
        children = self.get_children(node_id)
        for child in children:
            descendants.append(child)
            descendants.extend(self.get_descendants(child.id))
        return descendants

    def is_leaf(self, node_id: int) -> bool:
        """
        Check if a node is a leaf (has no children).

        Args:
            node_id: ID of the node to check.

        Returns:
            True if the node has no children, False otherwise.

        Examples:
            >>> hierarchy = Hierarchy()
            >>> parent = MetricNode(id=1, code="PARENT", name="Parent")
            >>> child = MetricNode(id=2, code="CHILD", name="Child", parent=1)
            >>> hierarchy.add_node(parent)
            >>> hierarchy.add_node(child)
            >>> hierarchy.is_leaf(1)
            False
            >>> hierarchy.is_leaf(2)
            True
        """
        return len(self.get_children(node_id)) == 0

    def is_root(self, node_id: int) -> bool:
        """
        Check if a node is the root (has no parent).

        Args:
            node_id: ID of the node to check.

        Returns:
            True if the node has no parent, False otherwise.

        Examples:
            >>> hierarchy = Hierarchy()
            >>> root = MetricNode(id=1, code="ROOT", name="Root")
            >>> child = MetricNode(id=2, code="CHILD", name="Child", parent=1)
            >>> hierarchy.add_node(root)
            >>> hierarchy.add_node(child)
            >>> hierarchy.is_root(1)
            True
            >>> hierarchy.is_root(2)
            False
        """
        node = self.get_node(node_id)
        return node is not None and node.parent is None

    def find_roots(self) -> list[MetricNode]:
        """
        Find all root nodes (nodes with no parent).

        Returns:
            List of root nodes.

        Examples:
            >>> hierarchy = Hierarchy()
            >>> root1 = MetricNode(id=1, code="ROOT1", name="Root1")
            >>> root2 = MetricNode(id=2, code="ROOT2", name="Root2")
            >>> hierarchy.add_node(root1)
            >>> hierarchy.add_node(root2)
            >>> [n.id for n in hierarchy.find_roots()]
            [1, 2]
        """
        return [node for node in self.nodes.values() if node.parent is None]

    def find_leaves(self) -> list[MetricNode]:
        """
        Find all leaf nodes (nodes with no children).

        Returns:
            List of leaf nodes.

        Examples:
            >>> hierarchy = Hierarchy()
            >>> parent = MetricNode(id=1, code="PARENT", name="Parent")
            >>> child = MetricNode(id=2, code="CHILD", name="Child", parent=1)
            >>> hierarchy.add_node(parent)
            >>> hierarchy.add_node(child)
            >>> [n.id for n in hierarchy.find_leaves()]
            [2]
        """
        return [self.get_node(node_id) for node_id in self.node_ids if self.is_leaf(node_id) and self.get_node(node_id) is not None]

    def traverse(
        self,
        start_node_id: int | None = None,
        order: str = "preorder",
        visit_func: Callable[[MetricNode], None] | None = None,
    ) -> list[MetricNode]:
        """
        Traverse the hierarchy tree.

        Args:
            start_node_id: ID of the starting node. If None, starts from root.
            order: Traversal order: 'preorder', 'postorder', or 'bfs'.
            visit_func: Optional function to call for each visited node.

        Returns:
            List of nodes in traversal order.

        Raises:
            ValueError: If order is not 'preorder', 'postorder', or 'bfs'.

        Examples:
            >>> hierarchy = Hierarchy()
            >>> root = MetricNode(id=1, code="ROOT", name="Root")
            >>> child1 = MetricNode(id=2, code="C1", name="Child1", parent=1)
            >>> child2 = MetricNode(id=3, code="C2", name="Child2", parent=1)
            >>> hierarchy.add_node(root)
            >>> hierarchy.add_node(child1)
            >>> hierarchy.add_node(child2)
            >>> [n.id for n in hierarchy.traverse(order="preorder")]
            [1, 2, 3]
        """
        if order not in ("preorder", "postorder", "bfs"):
            raise ValueError(f"Invalid order: {order}")

        if start_node_id is None:
            roots = self.find_roots()
            result: list[MetricNode] = []
            for root in roots:
                result.extend(self.traverse(root.id, order, visit_func))
            return result

        start_node = self.get_node(start_node_id)
        if start_node is None:
            return []

        nodes: list[MetricNode] = []

        if order == "preorder":
            def _preorder(node: MetricNode) -> None:
                nodes.append(node)
                if visit_func is not None:
                    visit_func(node)
                for child in self.get_children(node.id):
                    _preorder(child)
            _preorder(start_node)

        elif order == "postorder":
            def _postorder(node: MetricNode) -> None:
                for child in self.get_children(node.id):
                    _postorder(child)
                nodes.append(node)
                if visit_func is not None:
                    visit_func(node)
            _postorder(start_node)

        elif order == "bfs":
            from collections import deque
            queue = deque([start_node])
            while queue:
                node = queue.popleft()
                nodes.append(node)
                if visit_func is not None:
                    visit_func(node)
                queue.extend(self.get_children(node.id))

        return nodes

    def build_tree_dict(self, node_id: int | None = None) -> dict[str, Any] | None:
        """
        Build a nested dictionary representation of the tree.

        Args:
            node_id: ID of the starting node. If None, starts from root.

        Returns:
            Nested dictionary representation of the tree.

        Examples:
            >>> hierarchy = Hierarchy()
            >>> root = MetricNode(id=1, code="ROOT", name="Root")
            >>> child = MetricNode(id=2, code="CHILD", name="Child", parent=1)
            >>> hierarchy.add_node(root)
            >>> hierarchy.add_node(child)
            >>> tree = hierarchy.build_tree_dict()
            >>> tree["id"]
            1
            >>> tree["children"][0]["id"]
            2
        """
        if node_id is None:
            roots = self.find_roots()
            if not roots:
                return None
            if len(roots) == 1:
                return self.build_tree_dict(roots[0].id)
            # Multiple roots - return as a forest
            return {
                "forest": [self.build_tree_dict(r.id) for r in roots]
            }

        node = self.get_node(node_id)
        if node is None:
            return None

        result = node.to_dict()
        children = self.get_children(node_id)
        if children:
            result["children"] = [self.build_tree_dict(c.id) for c in children]

        return result

    def to_json(self, indent: int | None = 2) -> str:
        """
        Serialize the hierarchy to a JSON string.

        Args:
            indent: Number of spaces for indentation. None for compact JSON.

        Returns:
            JSON string representation of the hierarchy.

        Examples:
            >>> hierarchy = Hierarchy()
            >>> root = MetricNode(id=1, code="ROOT", name="Root")
            >>> hierarchy.add_node(root)
            >>> json_str = hierarchy.to_json()
            >>> '"id": 1' in json_str
            True
        """
        nodes_list = [node.to_dict() for node in self.nodes.values()]
        return json.dumps(nodes_list, indent=indent, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> Hierarchy:
        """
        Deserialize a hierarchy from a JSON string.

        Args:
            json_str: JSON string containing the hierarchy data.

        Returns:
            A new Hierarchy instance populated from the JSON.

        Raises:
            json.JSONDecodeError: If the JSON is invalid.
            ValueError: If the data is invalid.

        Examples:
            >>> json_str = '[{"id": 1, "code": "ROOT", "name": "Root"}]'
            >>> hierarchy = Hierarchy.from_json(json_str)
            >>> hierarchy.get_node(1).code
            'ROOT'
        """
        from libfa2.hier_metadata.metric_node import MetricNode

        data = json.loads(json_str)

        if isinstance(data, dict):
            # Handle forest format
            if "forest" in data:
                nodes_list: list[dict[str, object]] = []
                for tree in data["forest"]:
                    nodes_list.extend(cls._extract_nodes_from_tree(tree))
            else:
                raise ValueError("Invalid JSON format")
        else:
            nodes_list = data

        hierarchy = cls()
        for node_data in nodes_list:
            if not isinstance(node_data, dict):
                raise ValueError("Each node must be a dictionary")
            node = MetricNode.from_dict(node_data)
            hierarchy.add_node(node)

        return hierarchy

    @staticmethod
    def _extract_nodes_from_tree(tree: dict[str, object]) -> list[dict[str, object]]:
        """Extract all nodes from a nested tree structure."""
        nodes: list[dict[str, object]] = [tree]
        if "children" in tree and isinstance(tree["children"], list):
            for child in tree["children"]:
                if isinstance(child, dict):
                    nodes.extend(Hierarchy._extract_nodes_from_tree(child))
        return nodes

    @classmethod
    def from_nodes(cls, nodes: Iterable[MetricNode]) -> Hierarchy:
        """
        Create a Hierarchy instance from an iterable of MetricNode instances.

        Args:
            nodes: Iterable of MetricNode instances.

        Returns:
            A new Hierarchy instance containing all nodes.

        Examples:
            >>> nodes = [
            ...     MetricNode(id=1, code="ROOT", name="Root"),
            ...     MetricNode(id=2, code="CHILD", name="Child", parent=1)
            ... ]
            >>> hierarchy = Hierarchy.from_nodes(nodes)
            >>> hierarchy.get_node(1).code
            'ROOT'
        """
        hierarchy = cls()
        for node in nodes:
            hierarchy.add_node(node)
        return hierarchy

    def validate(self) -> ValidationReport:
        """
        Validate the hierarchy structure.

        Checks for:
        - Duplicate IDs
        - Duplicate codes
        - Missing root
        - Multiple roots
        - Invalid parent references
        - Cycles
        - Missing type for non-leaf nodes
        - Missing query for multi-type nodes
        - Missing/invalid driver_type for multi children
        - Rate drivers with query

        Returns:
            ValidationReport with results.

        Examples:
            >>> hierarchy = Hierarchy()
            >>> root = MetricNode(id=1, code="ROOT", name="Root", type=MetricType.SUM)
            >>> hierarchy.add_node(root)
            >>> report = hierarchy.validate()
            >>> report.is_valid
            True
        """
        errors: list[ValidationError] = []

        # Check for duplicate IDs
        id_counts: dict[int, int] = {}
        for node_id in self.node_ids:
            id_counts[node_id] = id_counts.get(node_id, 0) + 1
        for node_id, count in id_counts.items():
            if count > 1:
                errors.append(ValidationError(
                    type=ValidationErrorType.DUPLICATE_ID,
                    message=f"Duplicate ID found: {node_id} ({count} occurrences)",
                    node_id=node_id,
                ))

        # Check for duplicate codes
        code_counts: dict[str, int] = {}
        for node in self.nodes.values():
            code_counts[node.code] = code_counts.get(node.code, 0) + 1
        for code, count in code_counts.items():
            if count > 1:
                errors.append(ValidationError(
                    type=ValidationErrorType.DUPLICATE_CODE,
                    message=f"Duplicate code found: {code} ({count} occurrences)",
                ))

        # Check for root(s)
        roots = self.find_roots()
        if not roots:
            errors.append(ValidationError(
                type=ValidationErrorType.MISSING_ROOT,
                message="No root node found (no node with parent=None)",
            ))
        elif len(roots) > 1:
            root_ids = [r.id for r in roots]
            errors.append(ValidationError(
                type=ValidationErrorType.MULTIPLE_ROOTS,
                message=f"Multiple root nodes found: {root_ids}",
                details={"root_ids": root_ids},
            ))

        # Check for invalid parent references
        for node in self.nodes.values():
            if node.parent is not None:
                if node.parent not in self.node_ids:
                    errors.append(ValidationError(
                        type=ValidationErrorType.INVALID_PARENT_REFERENCE,
                        message=f"Invalid parent reference: node {node.id} references parent {node.parent} which does not exist",
                        node_id=node.id,
                        details={"parent_id": node.parent},
                    ))

        # Check for cycles using DFS
        visited: set[int] = set()
        rec_stack: set[int] = set()

        def _has_cycle(node_id: int) -> bool:
            """Check if there's a cycle starting from the given node."""
            visited.add(node_id)
            rec_stack.add(node_id)

            for child in self.get_children(node_id):
                if child.id not in visited:
                    if _has_cycle(child.id):
                        return True
                elif child.id in rec_stack:
                    return True

            rec_stack.remove(node_id)
            return False

        for node_id in self.node_ids:
            if node_id not in visited:
                if _has_cycle(node_id):
                    errors.append(ValidationError(
                        type=ValidationErrorType.CYCLE_DETECTED,
                        message=f"Cycle detected in hierarchy starting from node {node_id}",
                        node_id=node_id,
                    ))
                    break

        # Check for missing type in non-leaf nodes
        for node_id in self.node_ids:
            if not self.is_leaf(node_id):
                node = self.get_node(node_id)
                if node and node.type is None:
                    errors.append(ValidationError(
                        type=ValidationErrorType.MISSING_TYPE_FOR_NON_LEAF,
                        message=f"Non-leaf node {node_id} is missing type field",
                        node_id=node_id,
                    ))

        # Check for missing query in multi-type nodes
        for node in self.nodes.values():
            if node.type == MetricType.MULTI and node.query is None:
                errors.append(ValidationError(
                    type=ValidationErrorType.MISSING_QUERY_FOR_MULTI,
                    message=f"Multi-type node {node.id} is missing required query field",
                    node_id=node.id,
                ))

        # Check driver_type constraints for multi-type node children
        for node in self.nodes.values():
            if node.type == MetricType.MULTI:
                children = self.get_children(node.id)
                for child in children:
                    if child.driver_type is None:
                        errors.append(ValidationError(
                            type=ValidationErrorType.MISSING_DRIVER_TYPE,
                            message=f"Child {child.id} of multi-type node {node.id} is missing driverType",
                            node_id=child.id,
                            details={"parent_id": node.id},
                        ))
                    elif child.driver_type not in (DriverType.RATE, DriverType.BASE):
                        errors.append(ValidationError(
                            type=ValidationErrorType.INVALID_DRIVER_TYPE,
                            message=f"Invalid driver type '{child.driver_type}' for node {child.id}",
                            node_id=child.id,
                        ))

                    # Check rate driver doesn't have query
                    if child.driver_type == DriverType.RATE and child.query is not None:
                        errors.append(ValidationError(
                            type=ValidationErrorType.INVALID_RATE_DRIVER_WITH_QUERY,
                            message=f"Rate driver node {child.id} should not have a query field",
                            node_id=child.id,
                        ))

        return ValidationReport(is_valid=len(errors) == 0, errors=errors)

    def __eq__(self, other: object) -> bool:
        """
        Check equality with another Hierarchy instance.

        Args:
            other: Another object to compare with.

        Returns:
            True if other is a Hierarchy with the same nodes, False otherwise.
        """
        if not isinstance(other, Hierarchy):
            return False
        return self.nodes == other.nodes

    def __len__(self) -> int:
        """Return the number of nodes in the hierarchy."""
        return len(self.nodes)

    def __contains__(self, node_id: int) -> bool:
        """Check if a node ID exists in the hierarchy."""
        return node_id in self.nodes

    def __repr__(self) -> str:
        """Return a string representation of the Hierarchy."""
        return f"Hierarchy(nodes={len(self.nodes)}, root_id={self.root.id if self.root else None})"
