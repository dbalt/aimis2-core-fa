"""
Data access layer for aggregated SQL queries.

This module provides a high-level interface for constructing and executing
aggregated SQL queries using the GeneralSQLDataGateClientPart from aimis-sdk.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional

from coredis import Redis as KeyDbClient

from sdk.datagate.dg_client import GeneralSQLDataGateClientPart
from sdk.core.monadic import Res

from .conditions import ConditionBase, get_where_clause_part, reduce_condition
from dataclasses import dataclass, field

from ..fa_impl.units import SearchDevParameters

from sdk.core.logging import get_logger


@dataclass
class DataRow:
    dims:Dict[str,Any] = field(default_factory=Dict)
    plan:float = 0
    fact:float = 0

    @property
    def deviation(self)->float:
        return self.fact - self.plan

    @classmethod
    def from_dict(cls, row:Dict[str,Any],params:'SearchDevParameters')->'DataRow':
        plan_val = row[params.plan_column]
        fact_val = row[params.fact_column]
        dims = {k:v for (k,v) in row.items() if k != params.plan_column and k != params.fact_column}
        it = DataRow(dims, plan_val, fact_val)
        return it



class DataAccess:
    """
    Data access layer for executing aggregated SQL queries.

    This class wraps GeneralSQLDataGateClientPart and provides a convenient
    interface for constructing SELECT queries with GROUP BY and SUM aggregation.
    """

    def __init__(self, keydb_client: KeyDbClient):
        """
        Initialize DataAccess with a Redis client.

        Args:
            keydb_client: Redis client for communication with data gate service
        """
        lgr = get_logger()
        lgr.debug('DataAccess.__init__ started')
        self._dg_client = GeneralSQLDataGateClientPart(keydb_client)
        lgr.info('DataAccess initialized')

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

        res:Res[List[Dict[str,Any]]] = await self._dg_client.get_data(sql=sql, params=params)

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
