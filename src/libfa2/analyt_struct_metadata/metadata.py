"""
AnalyticalStructureMetadata — контейнер аналитической структуры.

Ре-экспорт из sdk.fa2026.metadata.analyt_struct_metadata.metadata —
единый источник истины (модели использует экшен sync_sreda_metadata в SDK).
"""

from sdk.fa2026.metadata.analyt_struct_metadata.metadata import (
    AnalyticalStructureMetadata,
    ValidationError,
    ValidationReport,
)

__all__ = [
    "AnalyticalStructureMetadata",
    "ValidationError",
    "ValidationReport",
]
