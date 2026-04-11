"""
Hierarchy metadata module for factor analysis.

This module provides classes for managing hierarchical metadata of financial
metrics used in factor analysis. It supports:

- Metric hierarchy with sum and multi (driver-based) aggregation
- JSON serialization/deserialization
- Validation of structure and logical constraints
- Tree navigation and traversal

Example usage:
    >>> from libfa2.hier_metadata import (
    ...     Hierarchy,
    ...     MetricNode,
    ...     Query,
    ...     MetricType,
    ...     DriverType,
    ... )
    >>>
    >>> # Create a simple hierarchy
    >>> hierarchy = Hierarchy()
    >>> root = MetricNode(id=1, code="ROOT", name="Root", type=MetricType.SUM)
    >>> child = MetricNode(id=2, code="CHILD", name="Child", parent=1)
    >>> hierarchy.add_nodes([root, child])
    >>>
    >>> # Serialize to JSON
    >>> json_str = hierarchy.to_json()
    >>>
    >>> # Deserialize from JSON
    >>> restored = Hierarchy.from_json(json_str)
    >>>
    >>> # Validate
    >>> report = restored.validate()
    >>> report.is_valid
    True
"""

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

__all__ = [
    # Enums
    "DriverType",
    "MetricType",
    "ValidationErrorType",
    # Classes
    "Hierarchy",
    "MetricNode",
    "Query",
    "ValidationError",
    "ValidationReport",
]
