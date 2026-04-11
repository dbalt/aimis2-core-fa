"""
Analytical structure metadata module for factor analysis.

This module contains classes for managing metadata about analytical
dimension drill-down algorithms used in factor analysis.

Modules:
    enums: Enum classes for string constants
    dimension: Dimension class for analytical dimensions
    algorithm: Algorithm class for drill-down algorithms
    metadata: AnalyticalStructureMetadata container class
"""

from libfa2.analyt_struct_metadata.algorithm import Algorithm
from libfa2.analyt_struct_metadata.dimension import Dimension
from libfa2.analyt_struct_metadata.enums import ValidationErrorType
from libfa2.analyt_struct_metadata.metadata import (
    AnalyticalStructureMetadata,
    ValidationError,
    ValidationReport,
)

__all__ = [
    "Algorithm",
    "Dimension",
    "ValidationErrorType",
    "AnalyticalStructureMetadata",
    "ValidationError",
    "ValidationReport",
]
