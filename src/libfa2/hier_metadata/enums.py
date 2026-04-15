"""
Enum classes for hierarchy metadata string constants.

This module contains all enum classes that define string constants used
throughout the hierarchy metadata system. Using enum classes ensures
type safety and self-documenting code.
"""

from enum import Enum


class MetricType(Enum):
    """
    Types of metrics in the hierarchy.

    Defines the calculation method for composite metrics.
    """

    SUM = "sum"
    """Sum of child components (summing components)."""

    MULTI = "multi"
    """Product of multiplier and base components (multiplier components)."""

    RATIO = "ratio"
    """Ratio of two components (numerator / denominator)."""


class MultiplierType(Enum):
    """
    Types of multiplier components.

    Used for child nodes of metrics with type 'multi'.
    """

    RATE = "rate"
    """
    Multiplier - normalized indicator (rate, percentage, etc.).
    Calculated by reverse calculation: rate = parent_multi / base.
    """

    BASE = "base"
    """
    Base - volumetric indicator, absolute value.
    Fetched directly from the database.
    """


class ValidationErrorType(Enum):
    """
    Types of validation errors for hierarchy metadata.

    Used for classifying errors discovered during validation of
    the correctness of metadata structure.
    """

    DUPLICATE_METRIC_ID = "duplicate_metric_id"
    """Multiple metrics have the same ID."""

    DUPLICATE_METRIC_CODE = "duplicate_metric_code"
    """Multiple metrics have the same code."""

    MISSING_PARENT_REFERENCE = "missing_parent_reference"
    """A metric references a parent ID that doesn't exist."""

    MISSING_NUMERATOR_REFERENCE = "missing_numerator_reference"
    """A ratio metric references a numerator ID that doesn't exist."""

    MISSING_DENOMINATOR_REFERENCE = "missing_denominator_reference"
    """A ratio metric references a denominator ID that doesn't exist."""

    INVALID_METRIC_ID = "invalid_metric_id"
    """Metric ID is not a positive integer."""

    INVALID_METRIC_CODE = "invalid_metric_code"
    """Metric code is empty or invalid."""

    INVALID_METRIC_NAME = "invalid_metric_name"
    """Metric name is empty."""

    INVALID_METRIC_TYPE = "invalid_metric_type"
    """Metric type is not one of the allowed values."""

    INVALID_MULTIPLIER_TYPE = "invalid_multiplier_type"
    """Multiplier type is not one of the allowed values."""

    INVALID_MULTIPLIER_FOR_NON_MULTI = "invalid_multiplier_for_non_multi"
    """Multiplier type specified for a node whose parent is not type 'multi'."""

    MISSING_QUERY_FOR_MULTI = "missing_query_for_multi"
    """A metric of type 'multi' is missing the required 'query' field."""

    MISSING_NUMERATOR_FOR_RATIO = "missing_numerator_for_ratio"
    """A metric of type 'ratio' is missing the required 'numerator' field."""

    MISSING_DENOMINATOR_FOR_RATIO = "missing_denominator_for_ratio"
    """A metric of type 'ratio' is missing the required 'denominator' field."""

    RATIO_NOT_AT_ROOT = "ratio_not_at_root"
    """A metric of type 'ratio' is not at the root level (has a parent)."""

    RATIO_HAS_CHILDREN = "ratio_has_children"
    """A metric of type 'ratio' has children (should be leaf)."""

    INVALID_QUERY_FIELDS = "invalid_query_fields"
    """Query field contains invalid data."""

    EMPTY_METRICS = "empty_metrics"
    """Metrics list is empty."""

    CYCLIC_REFERENCE = "cyclic_reference"
    """A cyclic reference detected in the hierarchy."""

    MULTIPLE_ROOTS = "multiple_roots"
    """Multiple root nodes found (should have exactly one)."""

    NO_ROOT = "no_root"
    """No root node found (at least one metric should have parent: null)."""

    INCOMPLETE_MULTI_CHILDREN = "incomplete_multi_children"
    """A 'multi' node has children but missing rate or base component."""

    DISCONNECTED_SUBTREE = "disconnected_subtree"
    """A subtree exists that is not connected to the root."""
