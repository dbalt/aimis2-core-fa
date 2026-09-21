"""
Query — параметры запроса к БД для узла иерархии.

Ре-экспорт из sdk.fa2026.metadata.hier_metadata.query —
единый источник истины (модели использует экшен sync_sreda_metadata в SDK).
"""

from sdk.fa2026.metadata.hier_metadata.query import Query

__all__ = ["Query"]
