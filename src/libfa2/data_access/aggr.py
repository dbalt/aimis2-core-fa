"""
Data access layer for aggregated SQL queries.

This module provides a high-level interface for constructing and executing
aggregated SQL queries using the GeneralSQLDataGateClientPart from aimis-sdk.
"""

from typing import List, Dict, Any

from coredis import Redis as KeyDbClient

from sdk.datagate.dg_client import GeneralSQLDataGateClientPart
from sdk.core.monadic import Res


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
        self._dg_client = GeneralSQLDataGateClientPart(keydb_client)

    async def get_aggr_data(
        self,
        source: str,
        grp_by_columns: List[str],
        aggr_columns: List[str],
        conditions: Dict[str, Any | List[Any]]
    ) -> Res[List[Dict[str, Any]]]:
        """
        Execute an aggregated SQL query with grouping and summation.

        Args:
            source: Table name in schema.table format (e.g., 'missa_bidr.t_aimis_fa__metrics_bsp')
            grp_by_columns: List of column names to group by
            aggr_columns: List of column names to aggregate with SUM()
            conditions: Dictionary of WHERE clause conditions.
                        If value is a list, uses IN operator.
                        If value is a single value, uses = operator.

        Returns:
            Res[List[Dict[str, Any]]]: Result containing list of dictionaries with aggregated data,
                                      or an error if query fails.

        Example:
            >>> await get_aggr_data(
            ...     'missa_bidr.t_aimis_fa__metrics_bsp',
            ...     ['gosb_name'],
            ...     ['plan', 'fact'],
            ...     {
            ...         'rep_dt': datetime.date(2026, 2, 28),
            ...         'kpi_name': 'Чистая прибыль',
            ...         'tb_name': ['Уральский банк', 'Байкальский банк']
            ...     }
            ... )
        """
        sql, params = self._build_query(
            source=source,
            grp_by_columns=grp_by_columns,
            aggr_columns=aggr_columns,
            conditions=conditions
        )

        return await self._dg_client.get_data(sql=sql, params=params)

    def _build_query(
        self,
        source: str,
        grp_by_columns: List[str],
        aggr_columns: List[str],
        conditions: Dict[str, Any | List[Any]]
    ) -> tuple[str, Dict[str, Any]]:
        """
        Build SQL query and parameters dictionary.

        Args:
            source: Table name
            grp_by_columns: Columns to group by
            aggr_columns: Columns to aggregate
            conditions: WHERE conditions

        Returns:
            Tuple of (sql_query_string, parameters_dict)
        """
        # Build SELECT clause
        select_parts = []
        for col in grp_by_columns:
            select_parts.append(f"t.{col}")
        for col in aggr_columns:
            select_parts.append(f"sum(t.{col}) as {col}")

        select_clause = ",\n    ".join(select_parts)

        # Build WHERE clause
        where_conditions = []
        params: Dict[str, Any] = {}

        for key, value in conditions.items():
            if isinstance(value, list):
                # Use IN operator for lists
                where_conditions.append(f"t.{key} in %({key})s")
                params[key] = tuple(value)
            else:
                # Use = operator for single values
                where_conditions.append(f"t.{key} = %({key})s")
                params[key] = value

        where_clause = ""
        if where_conditions:
            where_conditions_str = "\n    and ".join(where_conditions)
            where_clause = f"\nwhere 1=1\n    and {where_conditions_str}"

        # Build GROUP BY clause
        group_by_parts = [f"t.{col}" for col in grp_by_columns]
        group_by_clause = ",\n    ".join(group_by_parts)

        # Construct full query
        sql = f"""select
    {select_clause}
from {source} t{where_clause}
group by
    {group_by_clause}
"""

        return sql, params
