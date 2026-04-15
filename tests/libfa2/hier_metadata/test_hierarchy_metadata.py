"""
Comprehensive unit tests for hierarchy metadata module.

Tests cover:
- Query class
- MetricNode class
- Hierarchy class
- JSON serialization/deserialization
- Validation
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from libfa2.hier_metadata.enums import (
    DriverType,
    MetricType,
    ValidationErrorType,
)
from libfa2.hier_metadata.hierarchy import (
    Hierarchy,
    ValidationError,
    ValidationReport,
)
from libfa2.hier_metadata.metric_node import MetricNode
from libfa2.hier_metadata.query import Query


# =============================================================================
# Query Class Tests
# =============================================================================

class TestQuery:
    """Test cases for the Query class."""

    def test_init_with_params(self) -> None:
        """Test Query initialization with parameters."""
        params = {"segment": "corporate", "product": "loans"}
        query = Query(params)
        assert query.params == params

    def test_init_without_params(self) -> None:
        """Test Query initialization without parameters."""
        query = Query()
        assert query.params is None

    def test_init_with_empty_dict(self) -> None:
        """Test Query initialization with empty dictionary."""
        query = Query({})
        assert query.params is None

    def test_is_empty_with_params(self) -> None:
        """Test is_empty property with parameters."""
        query = Query({"segment": "corporate"})
        assert not query.is_empty

    def test_is_empty_without_params(self) -> None:
        """Test is_empty property without parameters."""
        query = Query()
        assert query.is_empty

    def test_to_dict(self) -> None:
        """Test converting Query to dictionary."""
        params = {"metric": "interest_income"}
        query = Query(params)
        assert query.to_dict() == params

    def test_to_dict_empty(self) -> None:
        """Test converting empty Query to dictionary."""
        query = Query()
        assert query.to_dict() is None

    def test_from_dict(self) -> None:
        """Test creating Query from dictionary."""
        params = {"segment": "corporate", "product": "loans"}
        query = Query.from_dict(params)
        assert query.params == params

    def test_from_dict_none(self) -> None:
        """Test creating Query from None."""
        query = Query.from_dict(None)
        assert query.params is None

    def test_equality(self) -> None:
        """Test Query equality."""
        q1 = Query({"segment": "corporate"})
        q2 = Query({"segment": "corporate"})
        q3 = Query({"segment": "retail"})
        assert q1 == q2
        assert q1 != q3
        assert q1 != "not a query"

    def test_hash(self) -> None:
        """Test Query hash for set membership."""
        q1 = Query({"segment": "corporate"})
        q2 = Query({"segment": "corporate"})
        queries = {q1}
        assert q2 in queries

    def test_repr(self) -> None:
        """Test Query string representation."""
        query = Query({"segment": "corporate"})
        assert "Query(params=" in repr(query)

    def test_with_list_values(self) -> None:
        """Test Query with list values."""
        query = Query({"segment": ["corporate", "sme"]})
        assert query.params["segment"] == ["corporate", "sme"]


# =============================================================================
# MetricNode Class Tests
# =============================================================================

class TestMetricNode:
    """Test cases for the MetricNode class."""

    def test_init_minimal(self) -> None:
        """Test MetricNode with minimal fields."""
        node = MetricNode(id=1, code="CODE", name="Name")
        assert node.id == 1
        assert node.code == "CODE"
        assert node.name == "Name"
        assert node.parent is None
        assert node.type is None
        assert node.query is None
        assert node.driver_type is None

    def test_init_full(self) -> None:
        """Test MetricNode with all fields."""
        node = MetricNode(
            id=1001,
            code="INT_INC",
            name="Процентный доход",
            parent=900,
            type=MetricType.MULTI,
            query=Query({"metric": "interest_income"}),
            driver_type=DriverType.RATE,
        )
        assert node.id == 1001
        assert node.code == "INT_INC"
        assert node.parent == 900
        assert node.type == MetricType.MULTI
        assert node.driver_type == DriverType.RATE

    def test_init_with_dict_query(self) -> None:
        """Test MetricNode with dictionary query converts to Query."""
        node = MetricNode(
            id=1,
            code="CODE",
            name="Name",
            query={"segment": "corporate"},
        )
        assert isinstance(node.query, Query)
        assert node.query.params == {"segment": "corporate"}

    def test_is_leaf_true(self) -> None:
        """Test is_leaf for leaf nodes."""
        node = MetricNode(id=1, code="LEAF", name="Leaf")
        assert node.is_leaf

    def test_is_leaf_false(self) -> None:
        """Test is_leaf for composite nodes."""
        node = MetricNode(id=1, code="SUM", name="Sum", type=MetricType.SUM)
        assert not node.is_leaf

    def test_is_leaf_with_driver_type(self) -> None:
        """Test is_leaf for driver nodes."""
        node = MetricNode(id=1, code="RATE", name="Rate", driver_type=DriverType.RATE)
        assert node.is_leaf

    def test_is_root_true(self) -> None:
        """Test is_root for root nodes."""
        node = MetricNode(id=1, code="ROOT", name="Root")
        assert node.is_root

    def test_is_root_false(self) -> None:
        """Test is_root for child nodes."""
        node = MetricNode(id=2, code="CHILD", name="Child", parent=1)
        assert not node.is_root

    def test_is_sum_type(self) -> None:
        """Test is_sum_type property."""
        node = MetricNode(id=1, code="SUM", name="Sum", type=MetricType.SUM)
        assert node.is_sum_type
        assert not node.is_multi_type

    def test_is_multi_type(self) -> None:
        """Test is_multi_type property."""
        node = MetricNode(id=1, code="MULTI", name="Multi", type=MetricType.MULTI)
        assert node.is_multi_type
        assert not node.is_sum_type

    def test_is_rate_driver(self) -> None:
        """Test is_rate_driver property."""
        node = MetricNode(id=1, code="RATE", name="Rate", driver_type=DriverType.RATE)
        assert node.is_rate_driver
        assert not node.is_base_driver

    def test_is_base_driver(self) -> None:
        """Test is_base_driver property."""
        node = MetricNode(id=1, code="BASE", name="Base", driver_type=DriverType.BASE)
        assert node.is_base_driver
        assert not node.is_rate_driver

    def test_requires_db_query(self) -> None:
        """Test requires_db_query property."""
        node = MetricNode(
            id=1,
            code="CODE",
            name="Name",
            query=Query({"segment": "corporate"}),
        )
        assert node.requires_db_query

    def test_to_dict_minimal(self) -> None:
        """Test to_dict for minimal node."""
        node = MetricNode(id=1, code="CODE", name="Name")
        result = node.to_dict()
        assert result == {"id": 1, "code": "CODE", "name": "Name"}

    def test_to_dict_full(self) -> None:
        """Test to_dict for node with all fields."""
        node = MetricNode(
            id=1001,
            code="INT_INC",
            name="Процентный доход",
            parent=900,
            type=MetricType.MULTI,
            query=Query({"metric": "interest_income"}),
            driver_type=DriverType.RATE,
        )
        result = node.to_dict()
        assert result["id"] == 1001
        assert result["code"] == "INT_INC"
        assert result["parent"] == 900
        assert result["type"] == "multi"
        assert result["query"] == {"metric": "interest_income"}
        assert result["driverType"] == "rate"

    def test_to_dict_omits_empty_fields(self) -> None:
        """Test that to_dict omits None and empty query fields."""
        node = MetricNode(
            id=1,
            code="CODE",
            name="Name",
            parent=None,
            type=None,
            query=None,
            driver_type=None,
        )
        result = node.to_dict()
        assert "parent" not in result
        assert "type" not in result
        assert "query" not in result
        assert "driverType" not in result

    def test_from_dict_minimal(self) -> None:
        """Test from_dict for minimal data."""
        data = {"id": 1, "code": "CODE", "name": "Name"}
        node = MetricNode.from_dict(data)
        assert node.id == 1
        assert node.code == "CODE"
        assert node.name == "Name"
        assert node.parent is None

    def test_from_dict_full(self) -> None:
        """Test from_dict for full data."""
        data = {
            "id": 1001,
            "code": "INT_INC",
            "name": "Процентный доход",
            "parent": 900,
            "type": "multi",
            "query": {"metric": "interest_income"},
            "driverType": "rate",
        }
        node = MetricNode.from_dict(data)
        assert node.id == 1001
        assert node.code == "INT_INC"
        assert node.parent == 900
        assert node.type == MetricType.MULTI
        assert node.query.params == {"metric": "interest_income"}
        assert node.driver_type == DriverType.RATE

    def test_from_dict_invalid_type(self) -> None:
        """Test from_dict with invalid type value."""
        data = {"id": 1, "code": "CODE", "name": "Name", "type": "invalid"}
        with pytest.raises(ValueError, match="Invalid metric type"):
            MetricNode.from_dict(data)

    def test_from_dict_invalid_driver_type(self) -> None:
        """Test from_dict with invalid driverType value."""
        data = {"id": 1, "code": "CODE", "name": "Name", "driverType": "invalid"}
        with pytest.raises(ValueError, match="Invalid driver type"):
            MetricNode.from_dict(data)

    def test_from_dict_missing_required_fields(self) -> None:
        """Test from_dict with missing required fields."""
        with pytest.raises(KeyError):
            MetricNode.from_dict({"id": 1, "code": "CODE"})  # Missing 'name'

    def test_equality(self) -> None:
        """Test MetricNode equality."""
        n1 = MetricNode(id=1, code="CODE", name="Name")
        n2 = MetricNode(id=1, code="CODE", name="Name")
        n3 = MetricNode(id=2, code="CODE", name="Name")
        assert n1 == n2
        assert n1 != n3
        assert n1 != "not a node"

    def test_hash(self) -> None:
        """Test MetricNode hash for set membership."""
        n1 = MetricNode(id=1, code="CODE", name="Name")
        n2 = MetricNode(id=1, code="CODE", name="Name")
        nodes = {n1}
        assert n2 in nodes

    def test_repr(self) -> None:
        """Test MetricNode string representation."""
        node = MetricNode(id=1, code="CODE", name="Name")
        assert "MetricNode" in repr(node)
        assert "id=1" in repr(node)


# =============================================================================
# Hierarchy Class Tests
# =============================================================================

class TestHierarchy:
    """Test cases for the Hierarchy class."""

    def test_init_empty(self) -> None:
        """Test Hierarchy initialization."""
        hierarchy = Hierarchy()
        assert len(hierarchy) == 0
        assert hierarchy.root is None

    def test_add_node(self) -> None:
        """Test adding a node to hierarchy."""
        hierarchy = Hierarchy()
        node = MetricNode(id=1, code="CODE", name="Name")
        hierarchy.add_node(node)
        assert 1 in hierarchy.nodes

    def test_add_duplicate_id(self) -> None:
        """Test that adding duplicate ID raises ValueError."""
        hierarchy = Hierarchy()
        node1 = MetricNode(id=1, code="CODE1", name="Name1")
        node2 = MetricNode(id=1, code="CODE2", name="Name2")
        hierarchy.add_node(node1)
        with pytest.raises(ValueError, match="already exists"):
            hierarchy.add_node(node2)

    def test_remove_node(self) -> None:
        """Test removing a node from hierarchy."""
        hierarchy = Hierarchy()
        node = MetricNode(id=1, code="CODE", name="Name")
        hierarchy.add_node(node)
        hierarchy.remove_node(1)
        assert 1 not in hierarchy.nodes

    def test_remove_nonexistent(self) -> None:
        """Test removing non-existent node raises KeyError."""
        hierarchy = Hierarchy()
        with pytest.raises(KeyError, match="not found"):
            hierarchy.remove_node(999)

    def test_get_node(self) -> None:
        """Test getting a node by ID."""
        hierarchy = Hierarchy()
        node = MetricNode(id=1, code="CODE", name="Name")
        hierarchy.add_node(node)
        result = hierarchy.get_node(1)
        assert result is not None
        assert result.code == "CODE"

    def test_get_node_not_found(self) -> None:
        """Test getting non-existent node returns None."""
        hierarchy = Hierarchy()
        assert hierarchy.get_node(999) is None

    def test_get_node_by_code(self) -> None:
        """Test getting a node by code."""
        hierarchy = Hierarchy()
        node = MetricNode(id=1, code="INT_INC", name="Name")
        hierarchy.add_node(node)
        result = hierarchy.get_node_by_code("INT_INC")
        assert result is not None
        assert result.id == 1

    def test_get_node_by_code_not_found(self) -> None:
        """Test getting non-existent node by code returns None."""
        hierarchy = Hierarchy()
        assert hierarchy.get_node_by_code("NOT_FOUND") is None

    def test_get_children(self) -> None:
        """Test getting children of a node."""
        hierarchy = Hierarchy()
        parent = MetricNode(id=1, code="PARENT", name="Parent", type=MetricType.SUM)
        child1 = MetricNode(id=2, code="C1", name="Child1", parent=1)
        child2 = MetricNode(id=3, code="C2", name="Child2", parent=1)
        hierarchy.add_node(parent)
        hierarchy.add_node(child1)
        hierarchy.add_node(child2)

        children = hierarchy.get_children(1)
        assert len(children) == 2
        child_ids = {c.id for c in children}
        assert child_ids == {2, 3}

    def test_get_children_empty(self) -> None:
        """Test getting children of leaf node."""
        hierarchy = Hierarchy()
        node = MetricNode(id=1, code="LEAF", name="Leaf")
        hierarchy.add_node(node)
        assert hierarchy.get_children(1) == []

    def test_get_parent(self) -> None:
        """Test getting parent of a node."""
        hierarchy = Hierarchy()
        parent = MetricNode(id=1, code="PARENT", name="Parent")
        child = MetricNode(id=2, code="CHILD", name="Child", parent=1)
        hierarchy.add_node(parent)
        hierarchy.add_node(child)

        result = hierarchy.get_parent(2)
        assert result is not None
        assert result.id == 1

    def test_get_parent_of_root(self) -> None:
        """Test getting parent of root returns None."""
        hierarchy = Hierarchy()
        root = MetricNode(id=1, code="ROOT", name="Root")
        hierarchy.add_node(root)
        assert hierarchy.get_parent(1) is None

    def test_get_ancestors(self) -> None:
        """Test getting ancestors of a node."""
        hierarchy = Hierarchy()
        root = MetricNode(id=1, code="ROOT", name="Root", type=MetricType.SUM)
        child = MetricNode(id=2, code="CHILD", name="Child", parent=1, type=MetricType.SUM)
        grandchild = MetricNode(id=3, code="GC", name="Grandchild", parent=2)
        hierarchy.add_nodes([root, child, grandchild])

        ancestors = hierarchy.get_ancestors(3)
        ancestor_ids = {a.id for a in ancestors}
        assert ancestor_ids == {1, 2}

    def test_get_descendants(self) -> None:
        """Test getting descendants of a node."""
        hierarchy = Hierarchy()
        root = MetricNode(id=1, code="ROOT", name="Root", type=MetricType.SUM)
        child = MetricNode(id=2, code="CHILD", name="Child", parent=1, type=MetricType.SUM)
        grandchild = MetricNode(id=3, code="GC", name="Grandchild", parent=2)
        hierarchy.add_nodes([root, child, grandchild])

        descendants = hierarchy.get_descendants(1)
        descendant_ids = {d.id for d in descendants}
        assert descendant_ids == {2, 3}

    def test_is_leaf(self) -> None:
        """Test is_leaf check."""
        hierarchy = Hierarchy()
        parent = MetricNode(id=1, code="PARENT", name="Parent", type=MetricType.SUM)
        child = MetricNode(id=2, code="CHILD", name="Child", parent=1)
        hierarchy.add_nodes([parent, child])

        assert not hierarchy.is_leaf(1)
        assert hierarchy.is_leaf(2)

    def test_is_root(self) -> None:
        """Test is_root check."""
        hierarchy = Hierarchy()
        root = MetricNode(id=1, code="ROOT", name="Root")
        child = MetricNode(id=2, code="CHILD", name="Child", parent=1)
        hierarchy.add_nodes([root, child])

        assert hierarchy.is_root(1)
        assert not hierarchy.is_root(2)

    def test_find_roots(self) -> None:
        """Test finding all root nodes."""
        hierarchy = Hierarchy()
        root1 = MetricNode(id=1, code="ROOT1", name="Root1")
        root2 = MetricNode(id=2, code="ROOT2", name="Root2")
        child = MetricNode(id=3, code="CHILD", name="Child", parent=1)
        hierarchy.add_nodes([root1, root2, child])

        roots = hierarchy.find_roots()
        root_ids = {r.id for r in roots}
        assert root_ids == {1, 2}

    def test_find_leaves(self) -> None:
        """Test finding all leaf nodes."""
        hierarchy = Hierarchy()
        root = MetricNode(id=1, code="ROOT", name="Root", type=MetricType.SUM)
        child = MetricNode(id=2, code="CHILD", name="Child", parent=1)
        hierarchy.add_nodes([root, child])

        leaves = hierarchy.find_leaves()
        leaf_ids = {l.id for l in leaves}
        assert leaf_ids == {2}

    def test_traverse_preorder(self) -> None:
        """Test preorder traversal."""
        hierarchy = Hierarchy()
        root = MetricNode(id=1, code="ROOT", name="Root", type=MetricType.SUM)
        child1 = MetricNode(id=2, code="C1", name="C1", parent=1)
        child2 = MetricNode(id=3, code="C2", name="C2", parent=1)
        hierarchy.add_nodes([root, child1, child2])

        result = hierarchy.traverse(order="preorder")
        assert [n.id for n in result] == [1, 2, 3]

    def test_traverse_postorder(self) -> None:
        """Test postorder traversal."""
        hierarchy = Hierarchy()
        root = MetricNode(id=1, code="ROOT", name="Root", type=MetricType.SUM)
        child = MetricNode(id=2, code="CHILD", name="Child", parent=1)
        hierarchy.add_nodes([root, child])

        result = hierarchy.traverse(order="postorder")
        assert [n.id for n in result] == [2, 1]

    def test_traverse_bfs(self) -> None:
        """Test BFS traversal."""
        hierarchy = Hierarchy()
        root = MetricNode(id=1, code="ROOT", name="Root", type=MetricType.SUM)
        child1 = MetricNode(id=2, code="C1", name="C1", parent=1, type=MetricType.SUM)
        child2 = MetricNode(id=3, code="C2", name="C2", parent=1)
        grandchild = MetricNode(id=4, code="GC", name="GC", parent=2)
        hierarchy.add_nodes([root, child1, child2, grandchild])

        result = hierarchy.traverse(order="bfs")
        assert [n.id for n in result] == [1, 2, 3, 4]

    def test_traverse_invalid_order(self) -> None:
        """Test traversal with invalid order raises ValueError."""
        hierarchy = Hierarchy()
        root = MetricNode(id=1, code="ROOT", name="Root")
        hierarchy.add_node(root)
        with pytest.raises(ValueError, match="Invalid order"):
            hierarchy.traverse(order="invalid")

    def test_build_tree_dict(self) -> None:
        """Test building tree dictionary."""
        hierarchy = Hierarchy()
        root = MetricNode(id=1, code="ROOT", name="Root", type=MetricType.SUM)
        child = MetricNode(id=2, code="CHILD", name="Child", parent=1)
        hierarchy.add_nodes([root, child])

        tree = hierarchy.build_tree_dict()
        assert tree is not None
        assert tree["id"] == 1
        assert "children" in tree
        assert tree["children"][0]["id"] == 2

    def test_to_json(self) -> None:
        """Test serializing hierarchy to JSON."""
        hierarchy = Hierarchy()
        root = MetricNode(id=1, code="ROOT", name="Root")
        hierarchy.add_node(root)

        json_str = hierarchy.to_json()
        data = json.loads(json_str)
        assert len(data) == 1
        assert data[0]["id"] == 1

    def test_from_json(self) -> None:
        """Test deserializing hierarchy from JSON."""
        json_str = '[{"id": 1, "code": "ROOT", "name": "Root"}]'
        hierarchy = Hierarchy.from_json(json_str)
        assert hierarchy.get_node(1) is not None
        assert hierarchy.get_node(1).code == "ROOT"

    def test_from_json_multiple_nodes(self) -> None:
        """Test deserializing hierarchy with multiple nodes."""
        json_str = '''[
            {"id": 1, "code": "ROOT", "name": "Root", "parent": null, "type": "sum"},
            {"id": 2, "code": "CHILD", "name": "Child", "parent": 1}
        ]'''
        hierarchy = Hierarchy.from_json(json_str)
        assert len(hierarchy) == 2
        assert hierarchy.get_node(1) is not None
        assert hierarchy.get_node(2) is not None
        assert hierarchy.get_node(2).parent == 1

    def test_json_roundtrip(self) -> None:
        """Test JSON serialization roundtrip preserves data."""
        hierarchy = Hierarchy()
        root = MetricNode(
            id=1,
            code="ROOT",
            name="Root",
            type=MetricType.SUM,
        )
        child = MetricNode(
            id=2,
            code="CHILD",
            name="Child",
            parent=1,
            query=Query({"segment": "corporate"}),
        )
        hierarchy.add_nodes([root, child])

        json_str = hierarchy.to_json()
        result = Hierarchy.from_json(json_str)

        assert len(result) == len(hierarchy)
        assert result.get_node(1).type == MetricType.SUM
        assert result.get_node(2).query.params == {"segment": "corporate"}

    def test_from_nodes(self) -> None:
        """Test creating hierarchy from iterable of nodes."""
        nodes = [
            MetricNode(id=1, code="ROOT", name="Root"),
            MetricNode(id=2, code="CHILD", name="Child", parent=1),
        ]
        hierarchy = Hierarchy.from_nodes(nodes)
        assert len(hierarchy) == 2
        assert hierarchy.get_node(1) is not None

    def test_add_nodes(self) -> None:
        """Test adding multiple nodes at once."""
        hierarchy = Hierarchy()
        nodes = [
            MetricNode(id=1, code="N1", name="N1"),
            MetricNode(id=2, code="N2", name="N2"),
            MetricNode(id=3, code="N3", name="N3"),
        ]
        hierarchy.add_nodes(nodes)
        assert len(hierarchy) == 3

    def test_equality(self) -> None:
        """Test Hierarchy equality."""
        h1 = Hierarchy()
        h2 = Hierarchy()
        node = MetricNode(id=1, code="CODE", name="Name")
        h1.add_node(node)
        h2.add_node(node)
        assert h1 == h2

    def test_len(self) -> None:
        """Test Hierarchy length."""
        hierarchy = Hierarchy()
        assert len(hierarchy) == 0
        hierarchy.add_node(MetricNode(id=1, code="CODE", name="Name"))
        assert len(hierarchy) == 1

    def test_contains(self) -> None:
        """Test 'in' operator for hierarchy."""
        hierarchy = Hierarchy()
        hierarchy.add_node(MetricNode(id=1, code="CODE", name="Name"))
        assert 1 in hierarchy
        assert 999 not in hierarchy


# =============================================================================
# Validation Tests
# =============================================================================

class TestValidation:
    """Test cases for hierarchy validation."""

    def test_valid_hierarchy(self) -> None:
        """Test validation of a valid hierarchy."""
        hierarchy = Hierarchy()
        root = MetricNode(id=1, code="ROOT", name="Root", type=MetricType.SUM)
        child = MetricNode(id=2, code="CHILD", name="Child", parent=1)
        hierarchy.add_nodes([root, child])

        report = hierarchy.validate()
        assert report.is_valid
        assert len(report.errors) == 0

    def test_duplicate_code(self) -> None:
        """Test detection of duplicate codes."""
        hierarchy = Hierarchy()
        hierarchy.add_node(MetricNode(id=1, code="CODE", name="Name1"))
        hierarchy.add_node(MetricNode(id=2, code="CODE", name="Name2"))

        report = hierarchy.validate()
        assert not report.is_valid
        error_types = {e.type for e in report.errors}
        assert ValidationErrorType.DUPLICATE_CODE in error_types

    def test_missing_root(self) -> None:
        """Test detection of missing root."""
        hierarchy = Hierarchy()
        hierarchy.add_node(MetricNode(id=1, code="N1", name="N1", parent=999))

        report = hierarchy.validate()
        assert not report.is_valid
        error_types = {e.type for e in report.errors}
        assert ValidationErrorType.MISSING_ROOT in error_types

    def test_multiple_roots(self) -> None:
        """Test detection of multiple roots."""
        hierarchy = Hierarchy()
        hierarchy.add_node(MetricNode(id=1, code="ROOT1", name="R1"))
        hierarchy.add_node(MetricNode(id=2, code="ROOT2", name="R2"))

        report = hierarchy.validate()
        assert not report.is_valid
        error_types = {e.type for e in report.errors}
        assert ValidationErrorType.MULTIPLE_ROOTS in error_types

    def test_invalid_parent_reference(self) -> None:
        """Test detection of invalid parent reference."""
        hierarchy = Hierarchy()
        root = MetricNode(id=1, code="ROOT", name="Root", type=MetricType.SUM)
        child = MetricNode(id=2, code="CHILD", name="Child", parent=999)
        hierarchy.add_nodes([root, child])

        report = hierarchy.validate()
        assert not report.is_valid
        error_types = {e.type for e in report.errors}
        assert ValidationErrorType.INVALID_PARENT_REFERENCE in error_types

    def test_missing_type_for_non_leaf(self) -> None:
        """Test detection of missing type for non-leaf nodes."""
        hierarchy = Hierarchy()
        root = MetricNode(id=1, code="ROOT", name="Root")  # No type, but has child
        child = MetricNode(id=2, code="CHILD", name="Child", parent=1)
        hierarchy.add_nodes([root, child])

        report = hierarchy.validate()
        assert not report.is_valid
        error_types = {e.type for e in report.errors}
        assert ValidationErrorType.MISSING_TYPE_FOR_NON_LEAF in error_types

    def test_missing_query_for_multi(self) -> None:
        """Test detection of missing query for multi-type nodes."""
        hierarchy = Hierarchy()
        root = MetricNode(
            id=1,
            code="ROOT",
            name="Root",
            type=MetricType.MULTI,
        )  # Multi without query
        child = MetricNode(id=2, code="RATE", name="Rate", parent=1, driver_type=DriverType.RATE)
        hierarchy.add_nodes([root, child])

        report = hierarchy.validate()
        assert not report.is_valid
        error_types = {e.type for e in report.errors}
        assert ValidationErrorType.MISSING_QUERY_FOR_MULTI in error_types

    def test_missing_driver_type_for_multi_child(self) -> None:
        """Test detection of missing driver_type for multi node children."""
        hierarchy = Hierarchy()
        root = MetricNode(
            id=1,
            code="ROOT",
            name="Root",
            type=MetricType.MULTI,
            query=Query({"metric": "value"}),
        )
        child = MetricNode(
            id=2,
            code="CHILD",
            name="Child",
            parent=1,
        )  # No driver_type
        hierarchy.add_nodes([root, child])

        report = hierarchy.validate()
        assert not report.is_valid
        error_types = {e.type for e in report.errors}
        assert ValidationErrorType.MISSING_DRIVER_TYPE in error_types

    def test_rate_driver_with_query(self) -> None:
        """Test detection of query on rate driver (should be calculated)."""
        hierarchy = Hierarchy()
        root = MetricNode(
            id=1,
            code="ROOT",
            name="Root",
            type=MetricType.MULTI,
            query=Query({"metric": "value"}),
        )
        child = MetricNode(
            id=2,
            code="RATE",
            name="Rate",
            parent=1,
            driver_type=DriverType.RATE,
            query=Query({"metric": "rate"}),  # Rate shouldn't have query
        )
        hierarchy.add_nodes([root, child])

        report = hierarchy.validate()
        assert not report.is_valid
        error_types = {e.type for e in report.errors}
        assert ValidationErrorType.INVALID_RATE_DRIVER_WITH_QUERY in error_types

    def test_validation_report_success(self) -> None:
        """Test ValidationReport.success factory method."""
        report = ValidationReport.success()
        assert report.is_valid
        assert len(report.errors) == 0

    def test_validation_report_failure(self) -> None:
        """Test ValidationReport.failure factory method."""
        errors = [
            ValidationError(type=ValidationErrorType.DUPLICATE_ID, message="Error 1"),
            ValidationError(type=ValidationErrorType.DUPLICATE_CODE, message="Error 2"),
        ]
        report = ValidationReport.failure(errors)
        assert not report.is_valid
        assert len(report.errors) == 2


# =============================================================================
# Integration Tests with Full Example
# =============================================================================

class TestFullExample:
    """Integration tests with the full example from the documentation."""

    def test_full_example_serialization_deserialization(self) -> None:
        """
        Test serialization and deserialization of the full example from
        the documentation.
        """
        # Create the full hierarchy example
        hierarchy = self._create_full_example_hierarchy()

        # Serialize to JSON
        json_str = hierarchy.to_json()

        # Verify JSON is valid
        data = json.loads(json_str)
        assert isinstance(data, list)
        assert len(data) == 16  # Total number of nodes in the example

        # Deserialize from JSON
        deserialized = Hierarchy.from_json(json_str)

        # Verify the deserialized hierarchy matches the original
        assert len(deserialized) == len(hierarchy)

        # Verify key nodes
        root = deserialized.get_node(1)
        assert root is not None
        assert root.code == "FP"

        nii = deserialized.get_node(10)
        assert nii is not None
        assert nii.code == "NII"
        assert nii.type == MetricType.SUM

        int_inc = deserialized.get_node(101)
        assert int_inc is not None
        assert int_inc.code == "INT_INC"
        assert int_inc.type == MetricType.MULTI

        # Verify hierarchy structure
        children_of_nii = deserialized.get_children(10)
        child_ids = {c.id for c in children_of_nii}
        assert child_ids == {101, 102, 103}

        children_of_int_inc = deserialized.get_children(101)
        assert len(children_of_int_inc) == 2

        # Verify driver types
        rate_driver = deserialized.get_node(1001)
        assert rate_driver is not None
        assert rate_driver.driver_type == DriverType.RATE

        base_driver = deserialized.get_node(1002)
        assert base_driver is not None
        assert base_driver.driver_type == DriverType.BASE

    def test_full_example_validation(self) -> None:
        """Test that the full example passes validation."""
        hierarchy = self._create_full_example_hierarchy()
        report = hierarchy.validate()
        assert report.is_valid
        assert len(report.errors) == 0

    def test_full_example_navigation(self) -> None:
        """Test navigation through the full example hierarchy."""
        hierarchy = self._create_full_example_hierarchy()

        # Find root
        root = hierarchy.root
        assert root is not None
        assert root.id == 1

        # Navigate to leaf
        leaf = hierarchy.get_node(1001)  # INT_RATE
        assert leaf is not None

        # Get ancestors
        ancestors = hierarchy.get_ancestors(1001)
        ancestor_ids = {a.id for a in ancestors}
        assert ancestor_ids == {101, 10, 1}

        # Get descendants of root
        descendants = hierarchy.get_descendants(1)
        assert len(descendants) == 15  # All other nodes

        # Build tree dict
        tree_dict = hierarchy.build_tree_dict()
        assert tree_dict is not None
        assert tree_dict["id"] == 1
        assert "children" in tree_dict

    def _create_full_example_hierarchy(self) -> Hierarchy:
        """
        Create the full example hierarchy from the documentation.

        This creates a complete hierarchy matching the example in
        factor_analysis__hieararchy_drill_metadata.md.
        """
        nodes = [
            # LEVEL 0: Root
            MetricNode(
                id=1,
                code="FP",
                name="Финансовый результат",
                parent=None,
                type=MetricType.SUM,
            ),

            # LEVEL 1: Main components
            MetricNode(
                id=10,
                code="NII",
                name="Чистый процентный доход",
                parent=1,
                type=MetricType.SUM,
            ),
            MetricNode(
                id=20,
                code="COMM_INC",
                name="Комиссионный доход",
                parent=1,
                type=MetricType.SUM,
                query=Query({"metric": "commission_income_total"}),
            ),
            MetricNode(
                id=30,
                code="NON_INT_INC",
                name="Непроцентные доходы",
                parent=1,
                type=MetricType.SUM,
            ),

            # LEVEL 2: NII components
            MetricNode(
                id=101,
                code="INT_INC",
                name="Процентный доход",
                parent=10,
                type=MetricType.MULTI,
                query=Query({"metric": "interest_income"}),
            ),
            MetricNode(
                id=102,
                code="INT_EXP",
                name="Процентный расход",
                parent=10,
                type=MetricType.MULTI,
                query=Query({"metric": "interest_expense"}),
            ),
            MetricNode(
                id=103,
                code="OTHER_NII",
                name="Прочие компоненты, включенные в ЧПД",
                parent=10,
                query=Query({"metric_type": "other_nii"}),
            ),

            # LEVEL 2: Commission income leaves
            MetricNode(
                id=201,
                code="COMM_INC_CORP",
                name="Комиссионный доход от юр. лиц",
                parent=20,
                query=Query({"segment": ["corporate", "sme"]}),
            ),
            MetricNode(
                id=202,
                code="COMM_INC_RET",
                name="Комиссионный доход от физ. лиц",
                parent=20,
                query=Query({"segment": ["retail", "vip"]}),
            ),
            MetricNode(
                id=203,
                code="COMM_INC_OTHER",
                name="Прочий комиссионный доход",
                parent=20,
                query=Query({"segment": ["other"]}),
            ),

            # LEVEL 2: Non-interest income leaves
            MetricNode(
                id=301,
                code="TRADING_INC",
                name="Доходы от торговых операций",
                parent=30,
                query=Query({"metric_type": "trading_pnl"}),
            ),
            MetricNode(
                id=302,
                code="OTHER_INC",
                name="Прочие доходы",
                parent=30,
                query=Query({"metric_type": "other_income"}),
            ),

            # LEVEL 3: Interest income drivers
            MetricNode(
                id=1001,
                code="INT_RATE",
                name="Ставка процентного дохода",
                parent=101,
                driver_type=DriverType.RATE,
            ),
            MetricNode(
                id=1002,
                code="DEBT_ASSETS",
                name="Объем требований по долговым фин. инструментам",
                parent=101,
                driver_type=DriverType.BASE,
                query=Query({"metric": "debt_assets_volume"}),
            ),

            # LEVEL 3: Interest expense drivers
            MetricNode(
                id=1003,
                code="EXP_RATE",
                name="Ставка процентного расхода",
                parent=102,
                driver_type=DriverType.RATE,
            ),
            MetricNode(
                id=1004,
                code="DEBT_LIAB",
                name="Объем обязательств по долговым фин. инструментам",
                parent=102,
                driver_type=DriverType.BASE,
                query=Query({"metric": "debt_liabilities_volume"}),
            ),
        ]

        return Hierarchy.from_nodes(nodes)
