"""
Data management layer for FA metadata and results tables.

Provides CRUD operations for t_aimis__fa__metadata and t_aimis__fa__results
via two implementations: DataMgmtDataGate (KeyDB/DataGate) and DataMgmtDbWrapper (direct DB).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Tuple, Callable, Awaitable, Dict, Any, List

from coredis import Redis as KeyDbClient

from sdk.datagate.dg_client import GeneralSQLDataGateClientPart
from sdk.core.monadic import Res
from sdk.core.logging import get_logger

from .dbwrapper import DbWrapper


class DataMgmt(ABC):
    """Abstract base class for data management operations."""

    def __init__(
        self,
        metadata_table: str,
        results_table: str,
    ):
        self._metadata_table = metadata_table
        self._results_table = results_table

    @abstractmethod
    async def _exec(self, sql: str, params: Dict[str, Any] | None = None) -> Res[None]:
        """Execute a non-SELECT SQL statement (INSERT/DELETE)."""
        ...

    @abstractmethod
    async def _query(self, sql: str, params: Dict[str, Any] | None = None) -> Res[List[Dict[str, Any]]]:
        """Execute a SELECT SQL query and return rows."""
        ...

    async def delete_metadata(self, code: str) -> Res[None]:
        """Delete metadata row by code."""
        lgr = get_logger()
        lgr.info(f'delete_metadata: code={code}')

        sql = f"delete from {self._metadata_table} where code = %(code)s"
        lgr.debug(f'SQL: {sql}, params: code={code}')

        res = await self._exec(sql, {'code': code})
        if not res.ok:
            lgr.exception(f'delete_metadata failed: {res.err}')
        else:
            lgr.info(f'delete_metadata completed: code={code}')
        return res

    async def save_metadata(self, code: str, data: str) -> Res[None]:
        """Upsert metadata: delete existing row then insert new one."""
        lgr = get_logger()
        lgr.info(f'save_metadata: code={code}')
        lgr.debug(f'save_metadata data length={len(data)}')

        del_res = await self.delete_metadata(code)
        if not del_res.ok:
            lgr.warning(f'save_metadata: delete failed but continuing: {del_res.err}')

        sql = f"insert into {self._metadata_table} (code, metadata) values (%(code)s, %(metadata)s)"
        lgr.debug(f'SQL: {sql}')

        res = await self._exec(sql, {'code': code, 'metadata': data})
        if not res.ok:
            lgr.exception(f'save_metadata failed: {res.err}')
        else:
            lgr.info(f'save_metadata completed: code={code}')
        return res

    async def get_metadata(self, code: str) -> Res[str]:
        """Retrieve metadata string by code."""
        lgr = get_logger()
        lgr.info(f'get_metadata: code={code}')

        sql = f"select metadata from {self._metadata_table} where code = %(code)s"
        lgr.debug(f'SQL: {sql}')

        res = await self._query(sql, {'code': code})
        if not res.ok:
            lgr.exception(f'get_metadata query failed: {res.err}')
            return Res.error(res.err)

        rows = res.data
        if not rows:
            lgr.warning(f'get_metadata: no row found for code={code}')
            return Res.error(f'No metadata found for code={code}')

        lgr.info(f'get_metadata completed: code={code}, data_len={len(rows[0]["metadata"])}')
        lgr.debug(f'get_metadata result: {rows[0]["metadata"]}')
        return Res.result(rows[0]['metadata'])

    async def delete_results(self, code: str, dt: date) -> Res[None]:
        """Delete results row by code and date."""
        lgr = get_logger()
        lgr.info(f'delete_results: code={code}, dt={dt}')

        sql = f"delete from {self._results_table} where code = %(code)s and dt = %(dt)s"
        lgr.debug(f'SQL: {sql}, params: code={code}, dt={dt}')

        res = await self._exec(sql, {'code': code, 'dt': dt})
        if not res.ok:
            lgr.exception(f'delete_results failed: {res.err}')
        else:
            lgr.info(f'delete_results completed: code={code}, dt={dt}')
        return res

    async def delete_results_for_dt(self, dt: date) -> Res[None]:
        """Delete all results for a given date."""
        lgr = get_logger()
        lgr.info(f'delete_results_for_dt: dt={dt}')

        sql = f"delete from {self._results_table} where dt = %(dt)s"
        lgr.debug(f'SQL: {sql}, params: dt={dt}')

        res = await self._exec(sql, {'dt': dt})
        if not res.ok:
            lgr.exception(f'delete_results_for_dt failed: {res.err}')
        else:
            lgr.info(f'delete_results_for_dt completed: dt={dt}')
        return res

    async def save_results(self, code: str, dt: date, data: str, summary: str) -> Res[None]:
        """Insert results row."""
        lgr = get_logger()
        lgr.info(f'save_results: code={code}, dt={dt}')
        lgr.debug(f'save_results data_len={len(data)}, summary_len={len(summary)}')

        sql = (
            f"insert into {self._results_table} (code, dt, data, summary) "
            f"values (%(code)s, %(dt)s, %(data)s, %(summary)s)"
        )
        lgr.debug(f'SQL: {sql}')

        res = await self._exec(sql, {'code': code, 'dt': dt, 'data': data, 'summary': summary})
        if not res.ok:
            lgr.exception(f'save_results failed: {res.err}')
        else:
            lgr.info(f'save_results completed: code={code}, dt={dt}')
        return res

    async def get_results(self, code: str, dt: date) -> Res[Tuple[str, str]]:
        """Retrieve results (data, summary) by code and date."""
        lgr = get_logger()
        lgr.info(f'get_results: code={code}, dt={dt}')

        sql = f"select data, summary from {self._results_table} where code = %(code)s and dt = %(dt)s"
        lgr.debug(f'SQL: {sql}')

        res = await self._query(sql, {'code': code, 'dt': dt})
        if not res.ok:
            lgr.exception(f'get_results query failed: {res.err}')
            return Res.error(res.err)

        rows = res.data
        if not rows:
            lgr.warning(f'get_results: no row found for code={code}, dt={dt}')
            return Res.error(f'No results found for code={code}, dt={dt}')

        row = rows[0]
        lgr.info(f'get_results completed: code={code}, dt={dt}')
        lgr.debug(f'get_results data_len={len(row["data"])}, summary_len={len(row["summary"])}')
        return Res.result((row['data'], row['summary']))


class DataMgmtDataGate(DataMgmt):
    """Data management via GeneralSQLDataGateClientPart (KeyDB/DataGate)."""

    def __init__(
        self,
        keydb_client: KeyDbClient,
        metadata_table: str,
        results_table: str,
    ):
        super().__init__(metadata_table, results_table)
        lgr = get_logger()
        lgr.debug('DataMgmtDataGate.__init__')
        self._keydb_client = keydb_client
        lgr.info('DataMgmtDataGate initialized')

    async def _exec(self, sql: str, params: Dict[str, Any] | None = None) -> Res[None]:
        lgr = get_logger()
        dgc = GeneralSQLDataGateClientPart(self._keydb_client)
        res = await dgc.get_data(sql=sql, params=params)
        if not res.ok:
            return Res.error(res.err)
        return Res.result(None)

    async def _query(self, sql: str, params: Dict[str, Any] | None = None) -> Res[List[Dict[str, Any]]]:
        dgc = GeneralSQLDataGateClientPart(self._keydb_client)
        return await dgc.get_data(sql=sql, params=params)


class DataMgmtDbWrapper(DataMgmt):
    """Data management via DbWrapper (direct DB connection)."""

    def __init__(
        self,
        db_wrapper_gen: Callable[[], Awaitable[DbWrapper]],
        metadata_table: str,
        results_table: str,
    ):
        super().__init__(metadata_table, results_table)
        lgr = get_logger()
        lgr.debug('DataMgmtDbWrapper.__init__')
        self._db_gen = db_wrapper_gen
        lgr.info('DataMgmtDbWrapper initialized')

    async def _exec(self, sql: str, params: Dict[str, Any] | None = None) -> Res[None]:
        try:
            dbw = await self._db_gen()
            await dbw.exec(sql, params)
            return Res.result(None)
        except Exception as e:
            return Res.error(str(e))

    async def _query(self, sql: str, params: Dict[str, Any] | None = None) -> Res[List[Dict[str, Any]]]:
        try:
            rows = []
            dbw = await self._db_gen()
            async for row in dbw.query(sql, params):
                rows.append(row)
            return Res.result(rows)
        except Exception as e:
            return Res.error(str(e))
