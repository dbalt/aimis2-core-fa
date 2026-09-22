"""
Analytical structure metadata module for factor analysis.

Ре-экспорт из sdk.fa2026.metadata.analyt_struct_metadata —
единый источник истины (модели использует экшен sync_sreda_metadata в SDK).
"""

from sdk.fa2026.metadata.analyt_struct_metadata import (
    Algorithm,
    AnalyticalStructureMetadata,
    Dimension,
    ValidationError,
    ValidationErrorType,
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
