"""
Data access layer for aggregated SQL queries.

This module provides an abstract base class DataAccess with two implementations:
- DataAccessDataGate: uses GeneralSQLDataGateClientPart from aimis-sdk (via KeyDB/Redis)
- DataAccessDbWrapper: uses DbWrapper for direct database connections
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from coredis import Redis as KeyDbClient

from sdk.datagate.dg_client import GeneralSQLDataGateClientPart
from sdk.core.monadic import Res

from .conditions import ConditionBase, get_where_clause_part, reduce_condition
from .dbwrapper import DbWrapper
from dataclasses import dataclass, field

from ..fa_impl.units import SearchDevParameters

from sdk.core.logging import get_logger


@dataclass
class DataRow:
    dims:Dict[str,Any] = field(default_factory=dict)
    plan:float = 0
    fact:float = 0

    @property
    def deviation(self)->float:
        if self.fact is None: return 0
        if self.plan is None: return 0
        return self.fact - self.plan

    @classmethod
    def from_dict(cls, row:Dict[str,Any],params:'SearchDevParameters')->'DataRow':
        plan_val = row[params.plan_column] or 0
        fact_val = row[params.fact_column] or 0
        dims = {k:v for (k,v) in row.items() if k != params.plan_column and k != params.fact_column}
        it = DataRow(dims, plan_val, fact_val)
        return it


class DataAccess(ABC):
    """
    Abstract base class for data access layer.

    Provides shared logic for building aggregated SQL queries and delegates
    the actual data fetching to subclasses via the _get_data method.
    """

    @abstractmethod
    async def _get_data(
        self,
        sql: str,
        params: Dict[str, Any]
    ) -> Res[List[Dict[str, Any]]]:
        """
        Execute a SQL query and return the result.

        Args:
            sql: SQL query string
            params: Query parameters dictionary

        Returns:
            Res[List[Dict[str, Any]]]: Result containing list of row dicts, or an error.
        """
        ...

    async def get_aggr_data(
        self,
        source: str,
        grp_by_columns: Optional[List[str]],
        aggr_columns: List[str],
        conditions: ConditionBase
    ) -> Res[List[Dict[str, Any]]]:
        """
        Execute an aggregated SQL query with optional grouping and summation.

        Args:
            source: Table name in schema.table format (e.g., 'missa_bidr.t_aimis_fa__metrics_bsp')
            grp_by_columns: List of column names to group by. Empty list or None for aggregation
                           without grouping (single row result with summed values).
            aggr_columns: List of column names to aggregate with SUM()
            conditions: ConditionBase object representing WHERE clause conditions.
                        Can be ConditionSet for simple filters or ConditionOr/ConditionAnd
                        for complex combined conditions.

        Returns:
            Res[List[Dict[str, Any]]]: Result containing list of dictionaries with aggregated data,
                                      or an error if query fails.

        Example:
            >>> from libfa2.data_access.conditions import ConditionSet
            >>> await get_aggr_data(
            ...     'missa_bidr.t_aimis_fa__metrics_bsp',
            ...     ['gosb_name'],
            ...     ['plan', 'fact'],
            ...     ConditionSet({
            ...         'rep_dt': datetime.date(2026, 2, 28),
            ...         'kpi_name': 'Чистая прибыль',
            ...         'tb_name': ['Уральский банк', 'Байкальский банк']
            ...     })
            ... )
        """
        lgr = get_logger()
        lgr.info(f'get_aggr_data started: source={source}, grp_by={grp_by_columns}, aggr={aggr_columns}')

        sql, params = self._build_query(
            source=source,
            grp_by_columns=grp_by_columns,
            aggr_columns=aggr_columns,
            conditions=conditions
        )

        lgr.debug(f'Executing SQL query: {sql.strip()}, params={params}')

        res: Res[List[Dict[str, Any]]] = await self._get_data(sql=sql, params=params)

        if not res.ok:
            lgr.error(f'get_aggr_data query failed: {res.err}')
        else:
            lgr.info(f'get_aggr_data completed: {len(res.data)} row(s) returned')
            lgr.debug(f'get_aggr_data result: {res.data}')

        return res

    def _build_query(
        self,
        source: str,
        grp_by_columns: Optional[List[str]],
        aggr_columns: List[str],
        conditions: ConditionBase
    ) -> tuple[str, Dict[str, Any]]:
        """
        Build SQL query and parameters dictionary.

        Args:
            source: Table name
            grp_by_columns: Columns to group by (empty list or None for aggregation without grouping)
            aggr_columns: Columns to aggregate
            conditions: WHERE conditions as ConditionBase

        Returns:
            Tuple of (sql_query_string, parameters_dict)
        """
        lgr = get_logger()
        lgr.debug(f'_build_query started: source={source}, grp_by={grp_by_columns}, aggr={aggr_columns}')

        # Handle None for grp_by_columns
        if grp_by_columns is None:
            grp_by_columns = []

        # Build SELECT clause
        select_parts = []
        for col in grp_by_columns:
            select_parts.append(f"t.{col}")
        for col in aggr_columns:
            select_parts.append(f"sum(t.{col}) as {col}")

        select_clause = ",\n    ".join(select_parts)

        lgr.debug(f'SELECT clause built: {select_clause}')

        # Reduce and build WHERE clause
        reduced_condition = reduce_condition(conditions)
        where_sql, params = get_where_clause_part(reduced_condition)

        where_clause = ""
        if where_sql:
            where_clause = f"\nwhere 1=1\n    and {where_sql}"

        lgr.debug(f'WHERE clause built: {where_sql}, params={params}')

        # Build GROUP BY clause (only if there are group by columns)
        group_by_clause = ""
        if grp_by_columns:
            group_by_parts = [f"t.{col}" for col in grp_by_columns]
            group_by_clause = ",\n    ".join(group_by_parts)

        # Construct full query
        if group_by_clause:
            sql = f"""select
    {select_clause}
from {source} t{where_clause}
group by
    {group_by_clause}
"""
        else:
            # No GROUP BY clause when grp_by_columns is empty
            sql = f"""select
    {select_clause}
from {source} t{where_clause}
"""

        lgr.debug(f'Built SQL:\n{sql}')
        return sql, params


class DataAccessDataGate(DataAccess):
    """
    Data access implementation using GeneralSQLDataGateClientPart.

    Communicates with the data gate service via KeyDB/Redis pub/sub.
    """

    def __init__(self, keydb_client: KeyDbClient):
        """
        Initialize DataAccessDataGate with a Redis client.

        Args:
            keydb_client: Redis client for communication with data gate service
        """
        lgr = get_logger()
        lgr.debug('DataAccessDataGate.__init__ started')
        self._keydb_client = keydb_client
        lgr.info('DataAccessDataGate initialized')

    async def _get_data(
        self,
        sql: str,
        params: Dict[str, Any]
    ) -> Res[List[Dict[str, Any]]]:
        dgc = GeneralSQLDataGateClientPart(self._keydb_client)
        return await dgc.get_data(sql=sql, params=params)


class DataAccessDbWrapper(DataAccess):
    """
    Data access implementation using DbWrapper for direct database connections.

    Collects results from DbWrapper's async iterator into a list.
    """

    def __init__(self, db_wrapper_gen):
        """
        Initialize DataAccessDbWrapper with a DbWrapper generator.

        Args:
            db_wrapper: DbWrapper generator instance with an active database connection
        """
        lgr = get_logger()
        lgr.debug('DataAccessDbWrapper.__init__ started')
        self._db_gen = db_wrapper_gen
        lgr.info('DataAccessDbWrapper initialized')

    async def _get_data(
        self,
        sql: str,
        params: Dict[str, Any]
    ) -> Res[List[Dict[str, Any]]]:
        try:
            rows = []
            dbw:DbWrapper = await self._db_gen()
            async for row in dbw.query(sql, params):
                rows.append(row)
            return Res.result(rows)
        except Exception as e:
            return Res.error(str(e))
        finally:
            await dbw.release()