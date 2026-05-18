"""
Enum classes for analytical structure metadata string constants.

This module contains all enum classes that define string constants used
throughout the analytical structure metadata system. Using enum classes
ensures type safety and self-documenting code.
"""

from enum import Enum


class ValidationErrorType(Enum):
    """
    Types of validation errors for analytical structure metadata.

    Used for classifying errors discovered during validation of
    the correctness of metadata structure.
    """

    DUPLICATE_ALGORITHM_ID = "duplicate_algorithm_id"
    """Multiple fa_impl have the same ID."""

    DUPLICATE_DIMENSION_CODE = "duplicate_dimension_code"
    """Multiple dimensions have the same code."""

    MISSING_DIMENSION_REFERENCE = "missing_dimension_reference"
    """Algorithm drill_order references a dimension code that doesn't exist."""

    INVALID_ALGORITHM_ID = "invalid_algorithm_id"
    """Algorithm ID is not a positive integer."""

    INVALID_DIMENSION_CODE = "invalid_dimension_code"
    """Dimension code is empty or contains invalid characters."""

    INVALID_DRILL_ORDER = "invalid_drill_order"
    """Drill_order is empty or contains invalid data."""

    EMPTY_ALGORITHMS = "empty_algorithms"
    """Algorithms list is empty."""

    EMPTY_DIMENSIONS = "empty_dimensions"
    """Dimensions list is empty."""

    INVALID_DRILL_STEP = "invalid_drill_step"
    """A drill step is empty or not a list of strings."""

    INVALID_DIMENSION_NAME = "invalid_dimension_name"
    """Dimension name is empty."""

    INVALID_DIMENSION_COLUMN = "invalid_dimension_column"
    """Dimension column is empty."""
