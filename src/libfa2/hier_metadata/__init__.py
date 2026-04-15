"""
Hierarchy metadata module for factor analysis.

This module contains classes for managing metadata about the hierarchical
structure of financial metrics used in factor analysis.

Modules:
    enums: Enum classes for string constants
    query: Query class for database query parameters
    metric_node: MetricNode class for hierarchy nodes
    hierarchy: Hierarchy class for managing the metric tree
"""

from libfa2.hier_metadata.enums import (
    MetricType,
    MultiplierType,
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
    "MetricType",
    "MultiplierType",
    "ValidationErrorType",
    "Hierarchy",
    "ValidationError",
    "ValidationReport",
    "MetricNode",
    "Query",
]
