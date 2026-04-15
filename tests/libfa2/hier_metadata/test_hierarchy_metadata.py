"""
Comprehensive unit tests for hierarchy metadata module.

Tests cover:
- Query class
- MetricNode class
- Hierarchy class
- JSON serialization/deserialization
- Validation
- Full example from documentation
"""

from __future__ import annotations

import json

import pytest

from libfa2.hier_metadata import (
    Hierarchy,
    MetricNode,
    MetricType,
    MultiplierType,
    Query,
    ValidationError,
    ValidationErrorType,
    ValidationReport,
)


# =============================================================================
# Query Class Tests
# =============================================================================

class TestQuery:
    """Test cases for the Query class."""

    def test_init_empty(self) -> None:
        """Test Query initialization with no fields."""
        query = Query()
        assert query.is_empty()
        assert query.fields is None

    def test_init_with_fields(self) -> None:
        """Test Query initialization with fields."""
        query = Query(fields={"segment": "corporate"})
        assert query.get_field("segment") == "corporate"
        assert not query.is_empty()

    def test_init_with_list_field(self) -> None:
        """Test Query initialization with list field."""
        query = Query(fields={"segment": ["corporate", "sme"]})
        assert query.get_field("segment") == ["corporate", "sme"]

    def test_init_invalid_field_name(self) -> None:
        """Test that empty field name raises ValueError."""
        with pytest.raises(ValueError, match="field name must be a non-empty string"):
            Query(fields={"": "value"})

    def test_init_invalid_field_value(self) -> None:
        """Test that empty string field value raises ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            Query(fields={"segment": ""})

    def test_init_invalid_list_field(self) -> None:
        """Test that empty list raises ValueError."""
        with pytest.raises(ValueError, match="list must not be empty"):
            Query(fields={"segment": []})

    def test_init_invalid_list_item(self) -> None:
        """Test that empty string in list raises ValueError."""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            Query(fields={"segment": ["a", "", "b"]})

    def test_get_field_exists(self) -> None:
        """Test get_field with existing field."""
        query = Query(fields={"segment": "corporate"})
        assert query.get_field("segment") == "corporate"

    def test_get_field_not_exists(self) -> None:
        """Test get_field with non-existing field."""
        query = Query(fields={"segment": "corporate"})
        assert query.get_field("not_found") is None

    def test_get_field_as_list_string(self) -> None:
        """Test get_field_as_list with string value."""
        query = Query(fields={"segment": "corporate"})
        assert query.get_field_as_list("segment") == ["corporate"]

    def test_get_field_as_list_list(self) -> None:
        """Test get_field_as_list with list value."""
        query = Query(fields={"segment": ["a", "b"]})
        assert query.get_field_as_list("segment") == ["a", "b"]

    def test_get_field_as_list_not_exists(self) -> None:
        """Test get_field_as_list with non-existing field."""
        query = Query(fields={"segment": "corporate"})
        assert query.get_field_as_list("not_found") == []

    def test_is_empty_true(self) -> None:
        """Test is_empty with empty query."""
        assert Query().is_empty()
        assert Query(fields=None).is_empty()

    def test_is_empty_false(self) -> None:
        """Test is_empty with non-empty query."""
        assert not Query(fields={"a": "b"}).is_empty()

    def test_to_dict_with_fields(self) -> None:
        """Test converting Query with fields to dictionary."""
        query = Query(fields={"segment": "corporate"})
        result = query.to_dict()
        assert result == {"segment": "corporate"}

    def test_to_dict_empty(self) -> None:
        """Test converting empty Query to dictionary returns None."""
        assert Query().to_dict() is None

    def test_from_dict_valid(self) -> None:
        """Test creating Query from dictionary."""
        data = {"segment": "corporate", "metric": "interest_income"}
        query = Query.from_dict(data)
        assert query.get_field("segment") == "corporate"
        assert query.get_field("metric") == "interest_income"

    def test_from_dict_none(self) -> None:
        """Test creating Query from None returns empty query."""
        query = Query.from_dict(None)
        assert query.is_empty()

    def test_from_dict_with_list(self) -> None:
        """Test creating Query with list field."""
        data = {"segment": ["corporate", "sme"]}
        query = Query.from_dict(data)
        assert query.get_field("segment") == ["corporate", "sme"]

    def test_from_dict_numeric_value(self) -> None:
        """Test that numeric values are converted to strings."""
        data = {"amount": 100, "ratio": 0.05}
        query = Query.from_dict(data)
        assert query.get_field("amount") == "100"
        assert query.get_field("ratio") == "0.05"

    def test_from_dict_boolean_value(self) -> None:
        """Test that boolean values are converted to strings."""
        data = {"active": True, "deleted": False}
        query = Query.from_dict(data)
        assert query.get_field("active") == "True"
        assert query.get_field("deleted") == "False"

    def test_from_dict_empty_dict(self) -> None:
        """Test creating Query from empty dict returns empty query."""
        query = Query.from_dict({})
        assert query.is_empty()

    def test_from_dict_skip_none_in_list(self) -> None:
        """Test that None values in list are skipped."""
        data = {"segment": ["a", None, "b", None]}
        query = Query.from_dict(data)
        assert query.get_field("segment") == ["a", "b"]

    def test_from_dict_all_none_in_list(self) -> None:
        """Test that list with only None values is skipped."""
        data = {"segment": [None, None]}
        query = Query.from_dict(data)
        assert query.get_field("segment") is None

    def test_equality(self) -> None:
        """Test Query equality."""
        q1 = Query(fields={"a": "b"})
        q2 = Query(fields={"a": "b"})
        q3 = Query(fields={"a": "c"})
        assert q1 == q2
        assert q1 != q3
        assert q1 != "not a query"

    def test_hash(self) -> None:
        """Test Query hash for set membership."""
        q1 = Query(fields={"a": "b"})
        q2 = Query(fields={"a": "b"})
        queries = {q1}
        assert q2 in queries


# =============================================================================
# MetricNode Class Tests
# =============================================================================

class TestMetricNode:
    """Test cases for the MetricNode class."""

    def test_init_minimal(self) -> None:
        """Test MetricNode initialization with minimal fields."""
        node = MetricNode(
            id=1,
            code="A",
            name="A Metric"
        )
        assert node.id == 1
        assert node.code == "A"
        assert node.name == "A Metric"
        assert node.parent is None
        assert node.type is None
        assert node.query is None
        assert node.multiplier_type is None

    def test_init_full(self) -> None:
        """Test MetricNode initialization with all fields."""
        node = MetricNode(
            id=1,
            code="A",
            name="A Metric",
            parent=0,
            type=MetricType.SUM,
            query=Query(fields={"segment": "corporate"}),
            multiplier_type=MultiplierType.RATE,
        )
        assert node.type == MetricType.SUM
        assert node.multiplier_type == MultiplierType.RATE

    def test_init_invalid_id(self) -> None:
        """Test that invalid ID raises ValueError."""
        with pytest.raises(ValueError, match="ID must be a positive integer"):
            MetricNode(id=0, code="A", name="A")
        with pytest.raises(ValueError, match="ID must be a positive integer"):
            MetricNode(id=-1, code="A", name="A")

    def test_init_empty_code(self) -> None:
        """Test that empty code raises ValueError."""
        with pytest.raises(ValueError, match="code must be a non-empty string"):
            MetricNode(id=1, code="", name="A")

    def test_init_empty_name(self) -> None:
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="name must be a non-empty string"):
            MetricNode(id=1, code="A", name="")

    def test_init_multi_without_query(self) -> None:
        """Test that multi type without query raises ValueError."""
        with pytest.raises(ValueError, match="type 'multi' must have a query"):
            MetricNode(
                id=1,
                code="A",
                name="A",
                type=MetricType.MULTI,
                query=None
            )

    def test_init_multi_with_numerator_denominator(self) -> None:
        """Test that multi type with numerator/denominator raises ValueError."""
        with pytest.raises(ValueError, match="cannot have numerator/denominator"):
            MetricNode(
                id=1,
                code="A",
                name="A",
                type=MetricType.MULTI,
                query=Query(),
                numerator=2,
                denominator=3
            )

    def test_init_ratio_without_numerator(self) -> None:
        """Test that ratio type without numerator raises ValueError."""
        with pytest.raises(ValueError, match="must have numerator"):
            MetricNode(
                id=1,
                code="A",
                name="A",
                type=MetricType.RATIO,
                numerator=None,
                denominator=2
            )

    def test_init_ratio_without_denominator(self) -> None:
        """Test that ratio type without denominator raises ValueError."""
        with pytest.raises(ValueError, match="must have denominator"):
            MetricNode(
                id=1,
                code="A",
                name="A",
                type=MetricType.RATIO,
                numerator=1,
                denominator=None
            )

    def test_init_ratio_with_multiplier_type(self) -> None:
        """Test that ratio type with multiplier_type raises ValueError."""
        with pytest.raises(ValueError, match="cannot have multiplier_type"):
            MetricNode(
                id=1,
                code="A",
                name="A",
                type=MetricType.RATIO,
                numerator=1,
                denominator=2,
                multiplier_type=MultiplierType.RATE
            )

    def test_is_leaf_true(self) -> None:
        """Test is_leaf returns True for nodes without type."""
        node = MetricNode(id=1, code="A", name="A")
        assert node.is_leaf

    def test_is_leaf_false(self) -> None:
        """Test is_leaf returns False for nodes with type."""
        node = MetricNode(id=1, code="A", name="A", type=MetricType.SUM)
        assert not node.is_leaf

    def test_is_root_true(self) -> None:
        """Test is_root returns True for nodes with no parent."""
        node = MetricNode(id=1, code="A", name="A", parent=None)
        assert node.is_root

    def test_is_root_false(self) -> None:
        """Test is_root returns False for nodes with parent."""
        node = MetricNode(id=1, code="A", name="A", parent=0)
        assert not node.is_root

    def test_is_composite_true(self) -> None:
        """Test is_composite returns True for nodes with type."""
        node = MetricNode(id=1, code="A", name="A", type=MetricType.SUM)
        assert node.is_composite

    def test_is_composite_false(self) -> None:
        """Test is_composite returns False for nodes without type."""
        node = MetricNode(id=1, code="A", name="A")
        assert not node.is_composite

    def test_is_multi_child_true(self) -> None:
        """Test is_multi_child returns True for nodes with multiplier_type."""
        node = MetricNode(
            id=1, code="A", name="A",
            multiplier_type=MultiplierType.RATE
        )
        assert node.is_multi_child

    def test_is_multi_child_false(self) -> None:
        """Test is_multi_child returns False for nodes without multiplier_type."""
        node = MetricNode(id=1, code="A", name="A")
        assert not node.is_multi_child

    def test_is_ratio_root_true(self) -> None:
        """Test is_ratio_root returns True for ratio root nodes."""
        node = MetricNode(
            id=1,
            code="COR",
            name="Cost of Risk",
            parent=None,
            type=MetricType.RATIO,
            numerator=2,
            denominator=3
        )
        assert node.is_ratio_root

    def test_is_ratio_root_false(self) -> None:
        """Test is_ratio_root returns False for non-ratio nodes."""
        node = MetricNode(
            id=1,
            code="A",
            name="A",
            parent=None,
            type=MetricType.SUM
        )
        assert not node.is_ratio_root

    def test_is_rate_multiplier_true(self) -> None:
        """Test is_rate_multiplier returns True for rate multipliers."""
        node = MetricNode(
            id=1, code="A", name="A",
            multiplier_type=MultiplierType.RATE
        )
        assert node.is_rate_multiplier

    def test_is_base_multiplier_true(self) -> None:
        """Test is_base_multiplier returns True for base multipliers."""
        node = MetricNode(
            id=1, code="A", name="A",
            multiplier_type=MultiplierType.BASE
        )
        assert node.is_base_multiplier

    def test_to_dict_minimal(self) -> None:
        """Test converting MetricNode with minimal fields to dict."""
        node = MetricNode(id=1, code="A", name="A")
        result = node.to_dict()
        assert result == {"id": 1, "code": "A", "name": "A"}

    def test_to_dict_with_all_fields(self) -> None:
        """Test converting MetricNode with all fields to dict."""
        node = MetricNode(
            id=1,
            code="A",
            name="A",
            parent=0,
            type=MetricType.SUM,
            query=Query(fields={"segment": "corporate"}),
            multiplier_type=MultiplierType.RATE,
            numerator=2,
            denominator=3
        )
        result = node.to_dict()
        assert result["id"] == 1
        assert result["code"] == "A"
        assert result["parent"] == 0
        assert result["type"] == "sum"
        assert result["query"] == {"segment": "corporate"}
        assert result["multiplierType"] == "rate"
        assert result["numerator"] == 2
        assert result["denominator"] == 3

    def test_to_dict_omits_empty_query(self) -> None:
        """Test that empty query is omitted from dict."""
        node = MetricNode(
            id=1,
            code="A",
            name="A",
            query=Query()  # Empty query
        )
        result = node.to_dict()
        assert "query" not in result

    def test_to_dict_omits_none_parent(self) -> None:
        """Test that None parent is omitted from dict."""
        node = MetricNode(id=1, code="A", name="A", parent=None)
        result = node.to_dict()
        assert "parent" not in result

    def test_from_dict_minimal(self) -> None:
        """Test creating MetricNode from minimal dict."""
        data = {"id": 1, "code": "A", "name": "A"}
        node = MetricNode.from_dict(data)
        assert node.id == 1
        assert node.code == "A"
        assert node.name == "A"

    def test_from_dict_full(self) -> None:
        """Test creating MetricNode from full dict."""
        data = {
            "id": 1,
            "code": "A",
            "name": "A Metric",
            "parent": 0,
            "type": "sum",
            "query": {"segment": "corporate"},
            "multiplierType": "rate",
            "numerator": 2,
            "denominator": 3
        }
        node = MetricNode.from_dict(data)
        assert node.id == 1
        assert node.code == "A"
        assert node.name == "A Metric"
        assert node.parent == 0
        assert node.type == MetricType.SUM
        assert node.multiplier_type == MultiplierType.RATE
        assert node.numerator == 2
        assert node.denominator == 3

    def test_from_dict_missing_id(self) -> None:
        """Test from_dict with missing id raises KeyError."""
        data = {"code": "A", "name": "A"}
        with pytest.raises(KeyError, match="'id'"):
            MetricNode.from_dict(data)

    def test_from_dict_missing_code(self) -> None:
        """Test from_dict with missing code raises KeyError."""
        data = {"id": 1, "name": "A"}
        with pytest.raises(KeyError, match="'code'"):
            MetricNode.from_dict(data)

    def test_from_dict_missing_name(self) -> None:
        """Test from_dict with missing name raises KeyError."""
        data = {"id": 1, "code": "A"}
        with pytest.raises(KeyError, match="'name'"):
            MetricNode.from_dict(data)

    def test_from_dict_invalid_type(self) -> None:
        """Test from_dict with invalid type raises ValueError."""
        data = {"id": 1, "code": "A", "name": "A", "type": "invalid"}
        with pytest.raises(ValueError, match="Invalid metric type"):
            MetricNode.from_dict(data)

    def test_from_dict_invalid_multiplier_type(self) -> None:
        """Test from_dict with invalid multiplier_type raises ValueError."""
        data = {"id": 1, "code": "A", "name": "A", "multiplierType": "invalid"}
        with pytest.raises(ValueError, match="Invalid multiplier type"):
            MetricNode.from_dict(data)

    def test_from_dict_empty_query(self) -> None:
        """Test that empty query dict results in None query."""
        data = {"id": 1, "code": "A", "name": "A", "query": {}}
        node = MetricNode.from_dict(data)
        assert node.query is None

    def test_from_dict_with_parent_null(self) -> None:
        """Test that parent: null results in None."""
        data = {"id": 1, "code": "A", "name": "A", "parent": None}
        node = MetricNode.from_dict(data)
        assert node.parent is None

    def test_equality(self) -> None:
        """Test MetricNode equality."""
        n1 = MetricNode(id=1, code="A", name="A")
        n2 = MetricNode(id=1, code="A", name="A")
        n3 = MetricNode(id=2, code="A", name="A")
        assert n1 == n2
        assert n1 != n3
        assert n1 != "not a metric"

    def test_hash(self) -> None:
        """Test MetricNode hash for set membership."""
        n1 = MetricNode(id=1, code="A", name="A")
        n2 = MetricNode(id=1, code="A", name="A")
        metrics = {n1}
        assert n2 in metrics


# =============================================================================
# Hierarchy Class Tests
# =============================================================================

class TestHierarchy:
    """Test cases for the Hierarchy class."""

    def test_init_empty(self) -> None:
        """Test Hierarchy initialization."""
        h = Hierarchy()
        assert len(h.metrics) == 0

    def test_add_metric(self) -> None:
        """Test adding a metric to hierarchy."""
        h = Hierarchy()
        node = MetricNode(id=1, code="A", name="A")
        h.add_metric(node)
        assert 1 in h.metrics
        assert "A" in h.metric_codes

    def test_add_duplicate_id(self) -> None:
        """Test that adding duplicate ID raises ValueError."""
        h = Hierarchy()
        node1 = MetricNode(id=1, code="A", name="A")
        node2 = MetricNode(id=1, code="B", name="B")
        h.add_metric(node1)
        with pytest.raises(ValueError, match="already exists"):
            h.add_metric(node2)

    def test_add_duplicate_code(self) -> None:
        """Test that adding duplicate code raises ValueError."""
        h = Hierarchy()
        node1 = MetricNode(id=1, code="A", name="A")
        node2 = MetricNode(id=2, code="A", name="B")
        h.add_metric(node1)
        with pytest.raises(ValueError, match="already exists"):
            h.add_metric(node2)

    def test_remove_metric(self) -> None:
        """Test removing a metric from hierarchy."""
        h = Hierarchy()
        node = MetricNode(id=1, code="A", name="A")
        h.add_metric(node)
        h.remove_metric(1)
        assert 1 not in h.metrics

    def test_remove_nonexistent(self) -> None:
        """Test removing non-existent metric raises KeyError."""
        h = Hierarchy()
        with pytest.raises(KeyError, match="not found"):
            h.remove_metric(999)

    def test_add_metrics(self) -> None:
        """Test adding multiple metrics."""
        h = Hierarchy()
        metrics = [
            MetricNode(id=1, code="A", name="A"),
            MetricNode(id=2, code="B", name="B")
        ]
        h.add_metrics(metrics)
        assert len(h.metrics) == 2

    def test_get_metric(self) -> None:
        """Test getting a metric by ID."""
        h = Hierarchy()
        node = MetricNode(id=1, code="A", name="A")
        h.add_metric(node)
        result = h.get_metric(1)
        assert result is not None
        assert result.code == "A"

    def test_get_metric_not_found(self) -> None:
        """Test getting non-existent metric returns None."""
        h = Hierarchy()
        assert h.get_metric(999) is None

    def test_get_metric_by_code(self) -> None:
        """Test getting a metric by code."""
        h = Hierarchy()
        node = MetricNode(id=1, code="A", name="A")
        h.add_metric(node)
        result = h.get_metric_by_code("A")
        assert result is not None
        assert result.id == 1

    def test_get_metric_by_code_not_found(self) -> None:
        """Test getting non-existent metric by code returns None."""
        h = Hierarchy()
        assert h.get_metric_by_code("not_found") is None

    def test_get_children(self) -> None:
        """Test getting children of a metric."""
        h = Hierarchy()
        h.add_metric(MetricNode(id=1, code="A", name="A"))
        h.add_metric(MetricNode(id=2, code="B", name="B", parent=1))
        h.add_metric(MetricNode(id=3, code="C", name="C", parent=1))
        children = h.get_children(1)
        assert len(children) == 2
        codes = {c.code for c in children}
        assert codes == {"B", "C"}

    def test_get_children_leaf(self) -> None:
        """Test getting children of a leaf returns empty list."""
        h = Hierarchy()
        h.add_metric(MetricNode(id=1, code="A", name="A"))
        assert len(h.get_children(1)) == 0

    def test_get_parent(self) -> None:
        """Test getting parent of a metric."""
        h = Hierarchy()
        h.add_metric(MetricNode(id=1, code="A", name="A"))
        h.add_metric(MetricNode(id=2, code="B", name="B", parent=1))
        parent = h.get_parent(2)
        assert parent is not None
        assert parent.code == "A"

    def test_get_parent_root(self) -> None:
        """Test getting parent of root returns None."""
        h = Hierarchy()
        h.add_metric(MetricNode(id=1, code="A", name="A", parent=None))
        assert h.get_parent(1) is None

    def test_get_ancestors(self) -> None:
        """Test getting ancestors of a metric."""
        h = Hierarchy()
        h.add_metric(MetricNode(id=1, code="A", name="A"))
        h.add_metric(MetricNode(id=2, code="B", name="B", parent=1))
        h.add_metric(MetricNode(id=3, code="C", name="C", parent=2))
        ancestors = h.get_ancestors(3)
        codes = [a.code for a in ancestors]
        assert codes == ["B", "A"]

    def test_get_ancestors_root(self) -> None:
        """Test getting ancestors of root returns empty list."""
        h = Hierarchy()
        h.add_metric(MetricNode(id=1, code="A", name="A", parent=None))
        assert len(h.get_ancestors(1)) == 0

    def test_get_descendants(self) -> None:
        """Test getting descendants of a metric."""
        h = Hierarchy()
        h.add_metric(MetricNode(id=1, code="A", name="A"))
        h.add_metric(MetricNode(id=2, code="B", name="B", parent=1))
        h.add_metric(MetricNode(id=3, code="C", name="C", parent=2))
        descendants = h.get_descendants(1)
        codes = {d.code for d in descendants}
        assert codes == {"B", "C"}

    def test_get_descendants_leaf(self) -> None:
        """Test getting descendants of a leaf returns empty list."""
        h = Hierarchy()
        h.add_metric(MetricNode(id=1, code="A", name="A"))
        assert len(h.get_descendants(1)) == 0

    def test_get_path_to_root(self) -> None:
        """Test getting path from metric to root."""
        h = Hierarchy()
        h.add_metric(MetricNode(id=1, code="A", name="A"))
        h.add_metric(MetricNode(id=2, code="B", name="B", parent=1))
        path = h.get_path_to_root(2)
        codes = [m.code for m in path]
        assert codes == ["B", "A"]

    def test_get_depth(self) -> None:
        """Test getting depth of a metric."""
        h = Hierarchy()
        h.add_metric(MetricNode(id=1, code="A", name="A"))
        h.add_metric(MetricNode(id=2, code="B", name="B", parent=1))
        h.add_metric(MetricNode(id=3, code="C", name="C", parent=2))
        assert h.get_depth(1) == 0
        assert h.get_depth(2) == 1
        assert h.get_depth(3) == 2

    def test_get_max_depth(self) -> None:
        """Test getting max depth of hierarchy."""
        h = Hierarchy()
        h.add_metric(MetricNode(id=1, code="A", name="A"))
        h.add_metric(MetricNode(id=2, code="B", name="B", parent=1))
        h.add_metric(MetricNode(id=3, code="C", name="C", parent=2))
        assert h.get_max_depth() == 2

    def test_is_ancestor_of(self) -> None:
        """Test checking if one metric is ancestor of another."""
        h = Hierarchy()
        h.add_metric(MetricNode(id=1, code="A", name="A"))
        h.add_metric(MetricNode(id=2, code="B", name="B", parent=1))
        h.add_metric(MetricNode(id=3, code="C", name="C", parent=2))
        assert h.is_ancestor_of(1, 3)
        assert not h.is_ancestor_of(3, 1)
        assert not h.is_ancestor_of(1, 1)

    def test_roots_property(self) -> None:
        """Test roots property returns root nodes."""
        h = Hierarchy()
        h.add_metric(MetricNode(id=1, code="A", name="A", parent=None))
        h.add_metric(MetricNode(id=2, code="B", name="B", parent=1))
        assert len(h.roots) == 1
        assert h.roots[0].code == "A"

    def test_leaves_property(self) -> None:
        """Test leaves property returns leaf nodes."""
        h = Hierarchy()
        h.add_metric(MetricNode(id=1, code="A", name="A"))
        h.add_metric(MetricNode(id=2, code="B", name="B", parent=1))
        assert len(h.leaves) == 1
        assert h.leaves[0].code == "B"

    def test_to_json(self) -> None:
        """Test serializing hierarchy to JSON."""
        h = Hierarchy()
        h.add_metric(MetricNode(id=1, code="A", name="A"))
        json_str = h.to_json()
        data = json.loads(json_str)
        assert "metrics" in data
        assert len(data["metrics"]) == 1

    def test_from_json(self) -> None:
        """Test deserializing hierarchy from JSON."""
        json_str = '{"metrics": []}'
        h = Hierarchy.from_json(json_str)
        assert len(h.metrics) == 0

    def test_from_json_with_data(self) -> None:
        """Test deserializing hierarchy with data."""
        json_str = '''{
            "metrics": [
                {"id": 1, "code": "A", "name": "A"},
                {"id": 2, "code": "B", "name": "B", "parent": 1}
            ]
        }'''
        h = Hierarchy.from_json(json_str)
        assert len(h.metrics) == 2

    def test_json_roundtrip(self) -> None:
        """Test JSON serialization roundtrip preserves data."""
        h = Hierarchy()
        h.add_metric(MetricNode(id=1, code="A", name="A", type=MetricType.SUM))
        h.add_metric(MetricNode(id=2, code="B", name="B", parent=1))

        json_str = h.to_json()
        result = Hierarchy.from_json(json_str)

        assert len(result.metrics) == len(h.metrics)
        assert result.get_metric(1).code == "A"
        assert result.get_metric(2).parent == 1

    def test_contains_with_int(self) -> None:
        """Test 'in' operator with metric ID."""
        h = Hierarchy()
        h.add_metric(MetricNode(id=1, code="A", name="A"))
        assert 1 in h
        assert 2 not in h

    def test_contains_with_str(self) -> None:
        """Test 'in' operator with metric code."""
        h = Hierarchy()
        h.add_metric(MetricNode(id=1, code="A", name="A"))
        assert "A" in h
        assert "B" not in h

    def test_len(self) -> None:
        """Test Hierarchy length."""
        h = Hierarchy()
        assert len(h) == 0
        h.add_metric(MetricNode(id=1, code="A", name="A"))
        h.add_metric(MetricNode(id=2, code="B", name="B"))
        assert len(h) == 2

    def test_equality(self) -> None:
        """Test Hierarchy equality."""
        h1 = Hierarchy()
        h2 = Hierarchy()
        node = MetricNode(id=1, code="A", name="A")
        h1.add_metric(node)
        h2.add_metric(node)
        assert h1 == h2


# =============================================================================
# Validation Tests
# =============================================================================

class TestValidation:
    """Test cases for hierarchy metadata validation."""

    def test_valid_hierarchy(self) -> None:
        """Test validation of valid hierarchy."""
        h = Hierarchy()
        h.add_metric(MetricNode(
            id=1, code="A", name="A", parent=None, type=MetricType.SUM
        ))
        h.add_metric(MetricNode(id=2, code="B", name="B", parent=1))

        report = h.validate()
        assert report.is_valid
        assert len(report.errors) == 0

    def test_empty_metrics(self) -> None:
        """Test detection of empty metrics."""
        h = Hierarchy()

        report = h.validate()
        assert not report.is_valid
        error_types = {e.type for e in report.errors}
        assert ValidationErrorType.EMPTY_METRICS in error_types

    def test_no_root(self) -> None:
        """Test detection of no root node."""
        h = Hierarchy()
        h.add_metric(MetricNode(id=1, code="A", name="A", parent=2))
        h.add_metric(MetricNode(id=2, code="B", name="B", parent=1))

        report = h.validate()
        assert not report.is_valid
        error_types = {e.type for e in report.errors}
        assert ValidationErrorType.NO_ROOT in error_types

    def test_multiple_roots(self) -> None:
        """Test detection of multiple roots."""
        h = Hierarchy()
        h.add_metric(MetricNode(id=1, code="A", name="A", parent=None))
        h.add_metric(MetricNode(id=2, code="B", name="B", parent=None))

        report = h.validate()
        assert not report.is_valid
        error_types = {e.type for e in report.errors}
        assert ValidationErrorType.MULTIPLE_ROOTS in error_types

    def test_missing_parent_reference(self) -> None:
        """Test detection of missing parent reference."""
        h = Hierarchy()
        h.add_metric(MetricNode(id=1, code="A", name="A", parent=None))
        h.add_metric(MetricNode(id=2, code="B", name="B", parent=999))

        report = h.validate()
        assert not report.is_valid
        error_types = {e.type for e in report.errors}
        assert ValidationErrorType.MISSING_PARENT_REFERENCE in error_types

    def test_multi_without_query(self) -> None:
        """Test detection of multi without query."""
        h = Hierarchy()
        node = MetricNode(id=1, code="A", name="A", type=MetricType.MULTI, query=Query())
        # Bypass validation to create invalid state
        object.__setattr__(node, "query", None)
        h.metrics[1] = node

        report = h.validate()
        assert not report.is_valid
        error_types = {e.type for e in report.errors}
        assert ValidationErrorType.MISSING_QUERY_FOR_MULTI in error_types

    def test_ratio_not_at_root(self) -> None:
        """Test detection of ratio not at root."""
        h = Hierarchy()
        h.add_metric(MetricNode(id=1, code="A", name="A", parent=None))
        h.add_metric(MetricNode(
            id=2, code="B", name="B", parent=1,
            type=MetricType.RATIO, numerator=3, denominator=4
        ))
        h.add_metric(MetricNode(id=3, code="C", name="C"))
        h.add_metric(MetricNode(id=4, code="D", name="D"))

        report = h.validate()
        assert not report.is_valid
        error_types = {e.type for e in report.errors}
        assert ValidationErrorType.RATIO_NOT_AT_ROOT in error_types

    def test_ratio_has_children(self) -> None:
        """Test detection of ratio with children."""
        h = Hierarchy()
        h.add_metric(MetricNode(
            id=1, code="COR", name="COR", parent=None,
            type=MetricType.RATIO, numerator=2, denominator=3
        ))
        h.add_metric(MetricNode(id=2, code="A", name="A"))
        h.add_metric(MetricNode(id=3, code="B", name="B"))
        h.add_metric(MetricNode(id=4, code="C", name="C", parent=1))

        report = h.validate()
        assert not report.is_valid
        error_types = {e.type for e in report.errors}
        assert ValidationErrorType.RATIO_HAS_CHILDREN in error_types

    def test_missing_numerator_reference(self) -> None:
        """Test detection of missing numerator reference."""
        h = Hierarchy()
        h.add_metric(MetricNode(
            id=1, code="COR", name="COR", parent=None,
            type=MetricType.RATIO, numerator=999, denominator=2
        ))
        h.add_metric(MetricNode(id=2, code="A", name="A"))

        report = h.validate()
        assert not report.is_valid
        error_types = {e.type for e in report.errors}
        assert ValidationErrorType.MISSING_NUMERATOR_REFERENCE in error_types

    def test_missing_denominator_reference(self) -> None:
        """Test detection of missing denominator reference."""
        h = Hierarchy()
        h.add_metric(MetricNode(
            id=1, code="COR", name="COR", parent=None,
            type=MetricType.RATIO, numerator=2, denominator=999
        ))
        h.add_metric(MetricNode(id=2, code="A", name="A"))

        report = h.validate()
        assert not report.is_valid
        error_types = {e.type for e in report.errors}
        assert ValidationErrorType.MISSING_DENOMINATOR_REFERENCE in error_types

    def test_multiplier_on_non_multi_child(self) -> None:
        """Test detection of multiplier type on non-multi child."""
        h = Hierarchy()
        h.add_metric(MetricNode(id=1, code="A", name="A", parent=None, type=MetricType.SUM))
        h.add_metric(MetricNode(
            id=2, code="B", name="B", parent=1,
            multiplier_type=MultiplierType.RATE
        ))

        report = h.validate()
        assert not report.is_valid
        error_types = {e.type for e in report.errors}
        assert ValidationErrorType.INVALID_MULTIPLIER_FOR_NON_MULTI in error_types

    def test_incomplete_multi_children_no_rate(self) -> None:
        """Test detection of multi children missing rate."""
        h = Hierarchy()
        h.add_metric(MetricNode(
            id=1, code="A", name="A", parent=None,
            type=MetricType.MULTI, query=Query()
        ))
        h.add_metric(MetricNode(
            id=2, code="B", name="B", parent=1,
            multiplier_type=MultiplierType.BASE
        ))

        report = h.validate()
        assert not report.is_valid
        error_types = {e.type for e in report.errors}
        assert ValidationErrorType.INCOMPLETE_MULTI_CHILDREN in error_types

    def test_incomplete_multi_children_no_base(self) -> None:
        """Test detection of multi children missing base."""
        h = Hierarchy()
        h.add_metric(MetricNode(
            id=1, code="A", name="A", parent=None,
            type=MetricType.MULTI, query=Query()
        ))
        h.add_metric(MetricNode(
            id=2, code="B", name="B", parent=1,
            multiplier_type=MultiplierType.RATE
        ))

        report = h.validate()
        assert not report.is_valid
        error_types = {e.type for e in report.errors}
        assert ValidationErrorType.INCOMPLETE_MULTI_CHILDREN in error_types

    def test_disconnected_subtree(self) -> None:
        """Test detection of disconnected subtree within a single-root hierarchy."""
        # Create a hierarchy with a root, a connected subtree, and a disconnected node
        h = Hierarchy()
        h.add_metric(MetricNode(id=1, code="A", name="A", parent=None, type=MetricType.SUM))
        h.add_metric(MetricNode(id=2, code="B", name="B", parent=1))
        h.add_metric(MetricNode(id=3, code="C", name="C", parent=2))
        # Add a disconnected node by setting its parent to a non-existent node
        node = MetricNode(id=4, code="D", name="D", parent=999)
        h.metrics[4] = node

        report = h.validate()
        assert not report.is_valid
        error_types = {e.type for e in report.errors}
        assert ValidationErrorType.MISSING_PARENT_REFERENCE in error_types

    def test_cyclic_reference(self) -> None:
        """Test detection of cyclic reference."""
        h = Hierarchy()
        h.add_metric(MetricNode(id=1, code="A", name="A", parent=2))
        h.add_metric(MetricNode(id=2, code="B", name="B", parent=1))

        report = h.validate()
        assert not report.is_valid
        error_types = {e.type for e in report.errors}
        assert ValidationErrorType.CYCLIC_REFERENCE in error_types

    def test_validation_report_success(self) -> None:
        """Test ValidationReport.success factory method."""
        report = ValidationReport.success()
        assert report.is_valid
        assert len(report.errors) == 0

    def test_validation_report_failure(self) -> None:
        """Test ValidationReport.failure factory method."""
        errors = [
            ValidationError(type=ValidationErrorType.EMPTY_METRICS, message="Error 1"),
            ValidationError(type=ValidationErrorType.NO_ROOT, message="Error 2"),
        ]
        report = ValidationReport.failure(errors)
        assert not report.is_valid
        assert len(report.errors) == 2


# =============================================================================
# Full Example Tests (from documentation)
# =============================================================================

class TestFullExample:
    """Integration tests with full example from documentation."""

    def test_full_example_serialization_deserialization(self) -> None:
        """
        Test serialization and deserialization of full example from
        documentation.
        """
        h = self._create_full_example_hierarchy()

        # Serialize to JSON
        json_str = h.to_json()

        # Verify JSON is valid
        data = json.loads(json_str)
        assert "metrics" in data
        assert len(data["metrics"]) == 16

        # Deserialize from JSON
        deserialized = Hierarchy.from_json(json_str)

        # Verify deserialized hierarchy matches the original
        assert len(deserialized.metrics) == len(h.metrics)

        # Verify root
        root = deserialized.get_metric(1)
        assert root is not None
        assert root.code == "FP"

        # Verify deep node
        deep = deserialized.get_metric(1001)
        assert deep is not None
        assert deep.code == "INT_RATE"
        assert deep.multiplier_type == MultiplierType.RATE

    def test_full_example_validation(self) -> None:
        """Test that full example passes validation."""
        h = self._create_full_example_hierarchy()
        report = h.validate()
        assert report.is_valid
        assert len(report.errors) == 0

    def test_full_example_hierarchy_structure(self) -> None:
        """Test hierarchy structure properties on full example."""
        h = self._create_full_example_hierarchy()

        # Test root
        assert len(h.roots) == 1
        assert h.roots[0].code == "FP"

        # Test children of root
        fp_children = h.get_children(1)
        codes = {c.code for c in fp_children}
        assert codes == {"NII", "COMM_INC", "NON_INT_INC"}

        # Test max depth
        assert h.get_max_depth() == 3

        # Test leaves
        leaves = {l.code for l in h.leaves}
        assert "INT_RATE" in leaves
        assert "DEBT_ASSETS" in leaves

    def test_full_example_navigation(self) -> None:
        """Test navigation methods on full example."""
        h = self._create_full_example_hierarchy()

        # Test get_path_to_root
        path = h.get_path_to_root(1001)
        codes = [m.code for m in path]
        assert codes == ["INT_RATE", "INT_INC", "NII", "FP"]

        # Test is_ancestor_of
        assert h.is_ancestor_of(1, 1001)  # FP is ancestor of INT_RATE
        assert not h.is_ancestor_of(1001, 1)  # INT_RATE is not ancestor of FP

    def test_full_example_multi_node_structure(self) -> None:
        """Test multi node structure in full example."""
        h = self._create_full_example_hierarchy()

        # Test INT_INC multi node
        int_inc = h.get_metric(101)
        assert int_inc is not None
        assert int_inc.type == MetricType.MULTI
        assert int_inc.query is not None

        # Test children of INT_INC
        children = h.get_children(101)
        assert len(children) == 2
        codes = {c.code for c in children}
        assert codes == {"INT_RATE", "DEBT_ASSETS"}

        # Verify one is rate and one is base
        rate_child = next(c for c in children if c.multiplier_type == MultiplierType.RATE)
        base_child = next(c for c in children if c.multiplier_type == MultiplierType.BASE)
        assert rate_child.code == "INT_RATE"
        assert base_child.code == "DEBT_ASSETS"

    def test_full_example_sum_node_with_query(self) -> None:
        """Test sum node with query (subtotal stored in DB)."""
        h = self._create_full_example_hierarchy()

        comm_inc = h.get_metric(20)
        assert comm_inc is not None
        assert comm_inc.type == MetricType.SUM
        assert comm_inc.query is not None
        assert comm_inc.query.get_field("metric") == "commission_income_total"

    def _create_full_example_hierarchy(self) -> Hierarchy:
        """
        Create a full example hierarchy from the documentation.

        This creates a complete hierarchy matching the example in
        factor_analysis__hieararchy_drill_metadata.md.
        """
        h = Hierarchy()

        # Level 0: Root
        h.add_metric(MetricNode(
            id=1,
            code="FP",
            name="Финансовый результат",
            parent=None,
            type=MetricType.SUM
        ))

        # Level 1: Main components
        h.add_metric(MetricNode(
            id=10,
            code="NII",
            name="Чистый процентный доход",
            parent=1,
            type=MetricType.SUM
        ))

        h.add_metric(MetricNode(
            id=20,
            code="COMM_INC",
            name="Комиссионный доход",
            parent=1,
            type=MetricType.SUM,
            query=Query(fields={"metric": "commission_income_total"})
        ))

        h.add_metric(MetricNode(
            id=30,
            code="NON_INT_INC",
            name="Непроцентные доходы",
            parent=1,
            type=MetricType.SUM
        ))

        # Level 2: NII components (sum and multi)
        h.add_metric(MetricNode(
            id=101,
            code="INT_INC",
            name="Процентный доход",
            parent=10,
            type=MetricType.MULTI,
            query=Query(fields={"metric": "interest_income"})
        ))

        h.add_metric(MetricNode(
            id=102,
            code="INT_EXP",
            name="Процентный расход",
            parent=10,
            type=MetricType.MULTI,
            query=Query(fields={"metric": "interest_expense"})
        ))

        h.add_metric(MetricNode(
            id=103,
            code="OTHER_NII",
            name="Прочие компоненты, включенные в ЧПД",
            parent=10,
            query=Query(fields={"metric_type": "other_nii"})
        ))

        # Level 2: Commission income leaves
        h.add_metric(MetricNode(
            id=201,
            code="COMM_INC_CORP",
            name="Комиссионный доход от юр. лиц",
            parent=20,
            query=Query(fields={"segment": ["corporate", "sme"]})
        ))

        h.add_metric(MetricNode(
            id=202,
            code="COMM_INC_RET",
            name="Комиссионный доход от физ. лиц",
            parent=20,
            query=Query(fields={"segment": ["retail", "vip"]})
        ))

        h.add_metric(MetricNode(
            id=203,
            code="COMM_INC_OTHER",
            name="Прочий комиссионный доход",
            parent=20,
            query=Query(fields={"segment": ["other"]})
        ))

        # Level 2: Non-interest income leaves
        h.add_metric(MetricNode(
            id=301,
            code="TRADING_INC",
            name="Доходы от торговых операций",
            parent=30,
            query=Query(fields={"metric_type": "trading_pnl"})
        ))

        h.add_metric(MetricNode(
            id=302,
            code="OTHER_INC",
            name="Прочие доходы",
            parent=30,
            query=Query(fields={"metric_type": "other_income"})
        ))

        # Level 3: INT_INC multipliers
        h.add_metric(MetricNode(
            id=1001,
            code="INT_RATE",
            name="Ставка процентного дохода",
            parent=101,
            multiplier_type=MultiplierType.RATE
        ))

        h.add_metric(MetricNode(
            id=1002,
            code="DEBT_ASSETS",
            name="Объем требований по долговым фин. инструментам",
            parent=101,
            multiplier_type=MultiplierType.BASE,
            query=Query(fields={"metric": "debt_assets_volume"})
        ))

        # Level 3: INT_EXP multipliers
        h.add_metric(MetricNode(
            id=1003,
            code="EXP_RATE",
            name="Ставка процентного расхода",
            parent=102,
            multiplier_type=MultiplierType.RATE
        ))

        h.add_metric(MetricNode(
            id=1004,
            code="DEBT_LIAB",
            name="Объем обязательств по долговым фин. инструментам",
            parent=102,
            multiplier_type=MultiplierType.BASE,
            query=Query(fields={"metric": "debt_liabilities_volume"})
        ))

        return h


# =============================================================================
# Ratio Example Tests (COR)
# =============================================================================

class TestRatioExample:
    """Test cases for ratio-type metrics (COR example)."""

    def test_ratio_root_creation(self) -> None:
        """Test creating a ratio root node."""
        h = Hierarchy()
        h.add_metric(MetricNode(
            id=5,
            code="COR",
            name="Cost of Risk",
            parent=None,
            type=MetricType.RATIO,
            numerator=501,
            denominator=502
        ))

        cor = h.get_metric(5)
        assert cor is not None
        assert cor.is_ratio_root
        assert cor.numerator == 501
        assert cor.denominator == 502

    def test_ratio_with_full_hierarchy(self) -> None:
        """Test ratio metric with full numerator/denominator hierarchies."""
        h = self._create_cor_example()

        # Verify ratio root
        cor = h.get_metric(5)
        assert cor is not None
        assert cor.type == MetricType.RATIO
        assert cor.is_root

        # Verify numerator hierarchy
        numerator = h.get_metric(501)
        assert numerator is not None
        assert numerator.type == MetricType.SUM
        assert len(h.get_children(501)) == 4  # Reserves by type

        # Verify denominator hierarchy
        denominator = h.get_metric(502)
        assert denominator is not None
        assert denominator.type == MetricType.SUM
        assert len(h.get_children(502)) == 2  # Assets by type

    def test_ratio_example_validation(self) -> None:
        """Test that COR example passes validation."""
        h = self._create_cor_example()
        report = h.validate()
        assert report.is_valid

    def test_ratio_example_serialization(self) -> None:
        """Test serialization of ratio example."""
        h = self._create_cor_example()

        json_str = h.to_json()
        data = json.loads(json_str)

        # Find the COR metric
        cor_metric = next(m for m in data["metrics"] if m["code"] == "COR")
        assert cor_metric["type"] == "ratio"
        assert cor_metric["numerator"] == 501
        assert cor_metric["denominator"] == 502
        assert "parent" not in cor_metric

        # Deserialize and verify
        deserialized = Hierarchy.from_json(json_str)
        assert len(deserialized.metrics) == len(h.metrics)

    def _create_cor_example(self) -> Hierarchy:
        """
        Create a COR (Cost of Risk) example hierarchy.

        This creates a complete hierarchy matching the COR example in
        factor_analysis__general_description.md.
        """
        h = Hierarchy()

        # COR ratio root
        h.add_metric(MetricNode(
            id=5,
            code="COR",
            name="Cost of Risk",
            parent=None,
            type=MetricType.RATIO,
            numerator=501,
            denominator=502
        ))

        # Numerator: Расходы на резервы
        h.add_metric(MetricNode(
            id=501,
            code="RESERVE_EXP",
            name="Расходы на резервы",
            type=MetricType.SUM
        ))

        # Numerator children: Reserve by credit type
        h.add_metric(MetricNode(
            id=511,
            code="RESERVE_CORP",
            name="Резервы по корпоративным кредитам",
            parent=501,
            query=Query(fields={"credit_type": "corporate"})
        ))

        h.add_metric(MetricNode(
            id=512,
            code="RESERVE_RETAIL",
            name="Резервы по розничным кредитам",
            parent=501,
            query=Query(fields={"credit_type": "retail"})
        ))

        h.add_metric(MetricNode(
            id=513,
            code="RESERVE_SME",
            name="Резервы по кредитам МСБ",
            parent=501,
            query=Query(fields={"credit_type": "sme"})
        ))

        # Numerator child: Reserves on other assets
        h.add_metric(MetricNode(
            id=521,
            code="RESERVE_OTHER",
            name="Резервы по прочим активам",
            parent=501,
            query=Query(fields={"reserve_type": "other_assets"})
        ))

        # Denominator: Среднехронологические работающие активы
        h.add_metric(MetricNode(
            id=502,
            code="AVG_WORK_ASSETS",
            name="Среднехронологические работающие активы",
            type=MetricType.SUM
        ))

        # Denominator children: Assets by type
        h.add_metric(MetricNode(
            id=531,
            code="LOAN_PORTFOLIO",
            name="Кредитный портфель",
            parent=502,
            query=Query(fields={"asset_type": "loans"})
        ))

        h.add_metric(MetricNode(
            id=532,
            code="OTHER_WORK_ASSETS",
            name="Прочие работающие активы",
            parent=502,
            query=Query(fields={"asset_type": "other_working"})
        ))

        return h


# =============================================================================
# JSON Edge Cases Tests
# =============================================================================

class TestJsonEdgeCases:
    """Tests for JSON serialization/deserialization edge cases."""

    def test_empty_hierarchy_json(self) -> None:
        """Test deserializing empty hierarchy."""
        json_str = '{"metrics": []}'
        h = Hierarchy.from_json(json_str)
        assert len(h.metrics) == 0

    def test_json_compact_format(self) -> None:
        """Test compact JSON without indentation."""
        h = Hierarchy()
        h.add_metric(MetricNode(id=1, code="A", name="A"))
        json_str = h.to_json(indent=None)
        assert json_str.count("\n") == 0

    def test_json_unicode_handling(self) -> None:
        """Test that JSON handles Unicode characters correctly."""
        h = Hierarchy()
        h.add_metric(MetricNode(
            id=1,
            code="COR",
            name="Стоимость риска"
        ))
        json_str = h.to_json()
        assert "Стоимость риска" in json_str
        # Verify it's not escaped
        assert "\\u" not in json_str

    def test_json_with_all_field_types(self) -> None:
        """Test JSON with all field types present."""
        h = Hierarchy()
        h.add_metric(MetricNode(
            id=1,
            code="A",
            name="A",
            parent=None,
            type=MetricType.SUM,
            query=Query(fields={"a": "b", "c": ["d", "e"]}),
            numerator=2,
            denominator=3
        ))

        json_str = h.to_json()
        data = json.loads(json_str)

        assert data["metrics"][0]["id"] == 1
        assert data["metrics"][0]["type"] == "sum"
        assert data["metrics"][0]["query"] == {"a": "b", "c": ["d", "e"]}

    def test_json_dict_immutable(self) -> None:
        """Test that to_dict returns independent copies."""
        h = Hierarchy()
        node = MetricNode(id=1, code="A", name="A")
        h.add_metric(node)
        json_str = h.to_json()
        data = json.loads(json_str)

        # Modify dict
        data["metrics"][0]["name"] = "Changed"

        # Original should be unchanged
        assert h.get_metric(1).name == "A"
