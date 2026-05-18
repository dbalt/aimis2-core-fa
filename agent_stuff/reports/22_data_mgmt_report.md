# Report: data_mgmt module implementation (task 22)

## Summary

Implemented the `data_mgmt` module for CRUD operations on `t_aimis__fa__metadata` and `t_aimis__fa__results` tables, following the existing class hierarchy pattern from `libfa2.data_access.aggr`.

## Files created

### `src/libfa2/data_access/data_mgmt.py`

Main module with class hierarchy:

- **`DataMgmt`** (ABC) — abstract base class with 6 public methods:
  - `delete_metadata(code)` — deletes row from metadata table by code
  - `save_metadata(code, data)` — upsert: delete existing + insert new row
  - `get_metadata(code)` — returns metadata string by code
  - `delete_results(code, dt)` — deletes row from results table by code and date
  - `save_results(code, dt, data, summary)` — inserts results row
  - `get_results(code, dt)` — returns (data, summary) tuple

  Delegates SQL execution to abstract methods `_exec` and `_query`.

- **`DataMgmtDataGate`** — implementation via `GeneralSQLDataGateClientPart` (KeyDB/DataGate). Creates a new `GeneralSQLDataGateClientPart` instance for each SQL call.

- **`DataMgmtDbWrapper`** — implementation via `DbWrapper` (direct DB connection). Uses a generator function passed in constructor to create new `DbWrapper` instances.

Constructor parameters for both implementations:
- `metadata_table: str` — fully qualified metadata table name
- `results_table: str` — fully qualified results table name
- `keydb_client` (DataGate) or `db_wrapper_gen` (DbWrapper) — client factory

### `tests/libfa2/test_data_mgmt.py`

16 unit tests covering:
- All 6 methods (happy path + error cases) via `DataMgmtDataGate` with mocked `GeneralSQLDataGateClientPart`
- Custom table names validation
- `DataMgmtDbWrapper` implementation (exec, query error, get_results success)

All tests pass (16/16).

### Updated `src/libfa2/data_access/__init__.py`

Added exports for `DataMgmt`, `DataMgmtDataGate`, `DataMgmtDbWrapper`.

## Design decisions

1. **Separate `_exec` / `_query` abstract methods** instead of one generic `_execute`. This mirrors the distinction between SELECT (returns rows) and INSERT/DELETE (no rows) in the underlying clients (`get_data` vs `exec`).

2. **`save_metadata` does delete+insert** (not UPDATE) as specified in the task. Delete failure is logged as warning but does not block the insert.

3. **`Res` monad** used consistently for return types, matching the project convention.

4. **Logging** via `get_logger()` at the start of each method with appropriate levels:
   - `debug` — SQL text, params, variable values
   - `info` — method entry/completion, key decisions
   - `warning` — missing data, non-critical failures
   - `exception` — error cases on failed DB operations
