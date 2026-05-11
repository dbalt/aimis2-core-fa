"""Data access layer for FA module."""
try:
    from .aggr import DataAccess, DataAccessDataGate, DataAccessDbWrapper
    from .data_mgmt import DataMgmt, DataMgmtDataGate, DataMgmtDbWrapper
    __all__ = [
        'DataAccess', 'DataAccessDataGate', 'DataAccessDbWrapper',
        'DataMgmt', 'DataMgmtDataGate', 'DataMgmtDbWrapper',
    ]
except ImportError:
    # SDK may not be available in all environments (e.g., during testing)
    __all__ = []
