# Data Access Layer - Implementation Report

## Overview
Implemented a data access layer module that provides a high-level interface for executing aggregated SQL queries using `GeneralSQLDataGateClientPart` from aimis-sdk.

## Module Structure

### Location
`src/libfa2/data_access/`

### Files Created

1. **`__init__.py`** - Module entry point
   - Exports `DataAccess` class

2. **`aggr.py`** - Core implementation
   - Contains `DataAccess` class
   - Implements `get_aggr_data()` method with dynamic SQL generation

## Implementation Details

### `DataAccess` Class

#### Constructor
```python
def __init__(self, keydb_client: KeyDbClient)
```
- Initializes with a Redis client for data gate communication
- Creates internal `GeneralSQLDataGateClientPart` instance

#### `get_aggr_data()` Method
```python
async def get_aggr_data(
    source: str,
    grp_by_columns: List[str],
    aggr_columns: List[str],
    conditions: Dict[str, Any | List[Any]]
) -> Res[List[Dict[str, Any]]]
```

**Features:**
- Generates SQL queries with SELECT, FROM, WHERE, and GROUP BY clauses
- Supports both single values (uses `=`) and lists (uses `IN`) in conditions
- Applies `SUM()` aggregation to specified columns
- Uses parameterized queries for security and type safety

#### Private `_build_query()` Method
- Separates SQL generation logic from execution
- Returns tuple of (sql_query, params_dict)
- Handles different value types in conditions dict

## SQL Generation Example

For input:
```python
await get_aggr_data(
    'missa_bidr.t_aimis_fa__metrics_bsp',
    ['gosb_name'],
    ['plan', 'fact'],
    {
        'rep_dt': datetime.date(2026, 2, 28),
        'kpi_name': 'Чистая прибыль',
        'tb_name': ['Уральский банк', 'Байкальский банк']
    }
)
```

Generated SQL:
```sql
select
    t.gosb_name,
    sum(t.fact) as fact,
    sum(t.plan) as plan
from missa_bidr.t_aimis_fa__metrics_bsp t
where 1=1
    and t.rep_dt = %(rep_dt)s
    and t.kpi_name = %(kpi_name)s
    and t.tb_name in %(tb_name)s
group by
    t.gosb_name
```

## Dependencies
- `aimis_sdk.sdk.datagate.dg_client.GeneralSQLDataGateClientPart`
- `aimis_sdk.sdk.core.monadic.Res`
- `coredis.Redis` (KeyDbClient)
- `typing` (List, Dict, Any)

## Usage Pattern
```python
from coredis import Redis
from libfa2.data_access import DataAccess

redis = Redis()
data_access = DataAccess(redis)

result = await data_access.get_aggr_data(
    source='missa_bidr.t_aimis_fa__metrics_bsp',
    grp_by_columns=['gosb_name'],
    aggr_columns=['plan', 'fact'],
    conditions={'rep_dt': datetime.date(2026, 2, 28)}
)

if result.ok:
    data = result.data
else:
    error = result.err
```

## Future Considerations
- Could extend to support other aggregate functions (AVG, COUNT, MIN, MAX)
- Could add support for HAVING clauses
- Could add query result caching if performance requires it
