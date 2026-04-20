"""Data access layer for FA module."""
try:
    from .aggr import DataAccess
    __all__ = ['DataAccess']
except ImportError:
    # SDK may not be available in all environments (e.g., during testing)
    __all__ = []
