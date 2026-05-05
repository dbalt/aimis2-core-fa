"""Data access layer for FA module."""
try:
    from .aggr import DataAccess, DataAccessDataGate, DataAccessDbWrapper
    __all__ = ['DataAccess', 'DataAccessDataGate', 'DataAccessDbWrapper']
except ImportError:
    # SDK may not be available in all environments (e.g., during testing)
    __all__ = []
