"""
Unit tests for libfa2.data_access.data_mgmt module.

Uses a mock of GeneralSQLDataGateClientPart to test business logic
without a real KeyDB/DataGate connection.
"""

import pytest
import asyncio
from datetime import date
from unittest.mock import MagicMock, patch

from sdk.core.monadic import Res


# --- Mock infrastructure ---

class MockDGClient:
    """Mock for GeneralSQLDataGateClientPart that records calls and returns configurable results."""

    def __init__(self):
        self.calls = []
        self._response = Res.result([])
        self._side_effect = None

    def set_response(self, response: Res):
        self._response = response

    def set_side_effect(self, fn):
        self._side_effect = fn

    async def get_data(self, sql: str, params: dict = None):
        self.calls.append({'sql': sql, 'params': params})
        if self._side_effect:
            return await self._side_effect(sql, params)
        return self._response


def _patch_dg(mock_dg):
    return patch('libfa2.data_access.data_mgmt.GeneralSQLDataGateClientPart', return_value=mock_dg)


def _make_dm(mock_dg):
    from libfa2.data_access.data_mgmt import DataMgmtDataGate
    mock_keydb = MagicMock()
    return DataMgmtDataGate(
        keydb_client=mock_keydb,
        metadata_table='missa_aimis.t_aimis__fa__metadata',
        results_table='missa_aimis.t_aimis__fa__results',
    )


# Helper to run async tests synchronously via anyio/asyncio
def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# --- Tests: metadata operations ---

class TestDeleteMetadata:

    def test_delete_metadata_sends_correct_sql(self):
        mock_dg = MockDGClient()
        mock_dg.set_response(Res.result([]))
        dm = _make_dm(mock_dg)

        with _patch_dg(mock_dg):
            res = run_async(dm.delete_metadata('TEST_CODE'))

        assert res.ok
        assert len(mock_dg.calls) == 1
        assert 'delete from' in mock_dg.calls[0]['sql'].lower()
        assert 'missa_aimis.t_aimis__fa__metadata' in mock_dg.calls[0]['sql']
        assert mock_dg.calls[0]['params'] == {'code': 'TEST_CODE'}

    def test_delete_metadata_error(self):
        mock_dg = MockDGClient()
        mock_dg.set_response(Res.error('connection failed'))
        dm = _make_dm(mock_dg)

        with _patch_dg(mock_dg):
            res = run_async(dm.delete_metadata('TEST_CODE'))

        assert not res.ok
        assert 'connection failed' in res.err


class TestSaveMetadata:

    def test_save_metadata_deletes_then_inserts(self):
        mock_dg = MockDGClient()
        mock_dg.set_response(Res.result([]))
        dm = _make_dm(mock_dg)

        with _patch_dg(mock_dg):
            res = run_async(dm.save_metadata('TEST_CODE', '{"key": "value"}'))

        assert res.ok
        assert len(mock_dg.calls) == 2

        # First call: DELETE
        assert 'delete from' in mock_dg.calls[0]['sql'].lower()
        assert mock_dg.calls[0]['params'] == {'code': 'TEST_CODE'}

        # Second call: INSERT
        assert 'insert into' in mock_dg.calls[1]['sql'].lower()
        assert mock_dg.calls[1]['params'] == {'code': 'TEST_CODE', 'metadata': '{"key": "value"}'}

    def test_save_metadata_insert_error(self):
        mock_dg = MockDGClient()
        call_count = 0

        async def side_effect(sql, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return Res.result([])
            return Res.error('insert failed')

        mock_dg.set_side_effect(side_effect)
        dm = _make_dm(mock_dg)

        with _patch_dg(mock_dg):
            res = run_async(dm.save_metadata('TEST_CODE', 'data'))

        assert not res.ok
        assert 'insert failed' in res.err


class TestGetMetadata:

    def test_get_metadata_found(self):
        mock_dg = MockDGClient()
        mock_dg.set_response(Res.result([{'metadata': '{"key": "val"}'}]))
        dm = _make_dm(mock_dg)

        with _patch_dg(mock_dg):
            res = run_async(dm.get_metadata('TEST_CODE'))

        assert res.ok
        assert res.data == '{"key": "val"}'
        assert 'select' in mock_dg.calls[0]['sql'].lower()
        assert mock_dg.calls[0]['params'] == {'code': 'TEST_CODE'}

    def test_get_metadata_not_found(self):
        mock_dg = MockDGClient()
        mock_dg.set_response(Res.result([]))
        dm = _make_dm(mock_dg)

        with _patch_dg(mock_dg):
            res = run_async(dm.get_metadata('MISSING_CODE'))

        assert not res.ok
        assert 'MISSING_CODE' in res.err

    def test_get_metadata_query_error(self):
        mock_dg = MockDGClient()
        mock_dg.set_response(Res.error('db error'))
        dm = _make_dm(mock_dg)

        with _patch_dg(mock_dg):
            res = run_async(dm.get_metadata('TEST_CODE'))

        assert not res.ok
        assert 'db error' in res.err


# --- Tests: results operations ---

class TestDeleteResults:

    def test_delete_results_sends_correct_sql(self):
        mock_dg = MockDGClient()
        mock_dg.set_response(Res.result([]))
        dm = _make_dm(mock_dg)
        dt = date(2026, 5, 11)

        with _patch_dg(mock_dg):
            res = run_async(dm.delete_results('CODE1', dt))

        assert res.ok
        assert 'delete from' in mock_dg.calls[0]['sql'].lower()
        assert 'missa_aimis.t_aimis__fa__results' in mock_dg.calls[0]['sql']
        assert mock_dg.calls[0]['params'] == {'code': 'CODE1', 'dt': dt}


class TestDeleteResultsForDt:

    def test_delete_results_for_dt_sends_correct_sql(self):
        mock_dg = MockDGClient()
        mock_dg.set_response(Res.result([]))
        dm = _make_dm(mock_dg)
        dt = date(2026, 5, 11)

        with _patch_dg(mock_dg):
            res = run_async(dm.delete_results_for_dt(dt))

        assert res.ok
        assert 'delete from' in mock_dg.calls[0]['sql'].lower()
        assert 'missa_aimis.t_aimis__fa__results' in mock_dg.calls[0]['sql']
        assert 'code' not in mock_dg.calls[0]['sql'].lower().split('where')[1]
        assert mock_dg.calls[0]['params'] == {'dt': dt}

    def test_delete_results_for_dt_error(self):
        mock_dg = MockDGClient()
        mock_dg.set_response(Res.error('connection failed'))
        dm = _make_dm(mock_dg)

        with _patch_dg(mock_dg):
            res = run_async(dm.delete_results_for_dt(date(2026, 5, 11)))

        assert not res.ok
        assert 'connection failed' in res.err


class TestSaveResults:

    def test_save_results_inserts_row(self):
        mock_dg = MockDGClient()
        mock_dg.set_response(Res.result([]))
        dm = _make_dm(mock_dg)
        dt = date(2026, 5, 11)

        with _patch_dg(mock_dg):
            res = run_async(dm.save_results('CODE1', dt, '{"result": 42}', 'summary text'))

        assert res.ok
        assert len(mock_dg.calls) == 1
        assert 'insert into' in mock_dg.calls[0]['sql'].lower()
        assert mock_dg.calls[0]['params'] == {
            'code': 'CODE1', 'dt': dt,
            'data': '{"result": 42}', 'summary': 'summary text',
        }


class TestGetResults:

    def test_get_results_found(self):
        mock_dg = MockDGClient()
        dt = date(2026, 5, 11)
        mock_dg.set_response(Res.result([{'data': '{"x":1}', 'summary': 'sum'}]))
        dm = _make_dm(mock_dg)

        with _patch_dg(mock_dg):
            res = run_async(dm.get_results('CODE1', dt))

        assert res.ok
        assert res.data == ('{"x":1}', 'sum')

    def test_get_results_not_found(self):
        mock_dg = MockDGClient()
        dt = date(2026, 5, 11)
        mock_dg.set_response(Res.result([]))
        dm = _make_dm(mock_dg)

        with _patch_dg(mock_dg):
            res = run_async(dm.get_results('MISSING', dt))

        assert not res.ok

    def test_get_results_query_error(self):
        mock_dg = MockDGClient()
        dt = date(2026, 5, 11)
        mock_dg.set_response(Res.error('timeout'))
        dm = _make_dm(mock_dg)

        with _patch_dg(mock_dg):
            res = run_async(dm.get_results('CODE1', dt))

        assert not res.ok
        assert 'timeout' in res.err


# --- Tests: custom table names ---

class TestCustomTableNames:

    def test_custom_table_names_in_sql(self):
        mock_dg = MockDGClient()
        mock_dg.set_response(Res.result([]))
        mock_keydb = MagicMock()

        with _patch_dg(mock_dg):
            from libfa2.data_access.data_mgmt import DataMgmtDataGate
            dm = DataMgmtDataGate(
                keydb_client=mock_keydb,
                metadata_table='custom_schema.tbl_meta',
                results_table='custom_schema.tbl_results',
            )
            run_async(dm.delete_metadata('X'))

        assert 'custom_schema.tbl_meta' in mock_dg.calls[0]['sql']


# --- Tests: DbWrapper implementation ---

class TestDbWrapperImplementation:

    def test_dbw_exec_and_query(self):
        from libfa2.data_access.data_mgmt import DataMgmtDbWrapper

        mock_dbw = MagicMock()

        async def mock_exec(sql, params=None):
            pass

        mock_dbw.exec = mock_exec

        async def db_gen():
            return mock_dbw

        dm = DataMgmtDbWrapper(
            db_wrapper_gen=db_gen,
            metadata_table='test.meta',
            results_table='test.results',
        )

        res = run_async(dm.delete_metadata('CODE'))
        assert res.ok

    def test_dbw_query_error(self):
        from libfa2.data_access.data_mgmt import DataMgmtDbWrapper

        mock_dbw = MagicMock()

        async def mock_query(sql, params=None):
            raise Exception('db down')
            yield  # noqa: unreachable — makes this an async generator

        mock_dbw.query = mock_query

        async def db_gen():
            return mock_dbw

        dm = DataMgmtDbWrapper(
            db_wrapper_gen=db_gen,
            metadata_table='test.meta',
            results_table='test.results',
        )

        res = run_async(dm.get_metadata('CODE'))
        assert not res.ok
        assert 'db down' in res.err

    def test_dbw_get_results_success(self):
        from libfa2.data_access.data_mgmt import DataMgmtDbWrapper

        mock_dbw = MagicMock()
        dt = date(2026, 5, 11)

        async def mock_query(sql, params=None):
            yield {'data': '{"res":1}', 'summary': 'test_summary'}

        mock_dbw.query = mock_query

        async def db_gen():
            return mock_dbw

        dm = DataMgmtDbWrapper(
            db_wrapper_gen=db_gen,
            metadata_table='test.meta',
            results_table='test.results',
        )

        res = run_async(dm.get_results('CODE', dt))
        assert res.ok
        assert res.data == ('{"res":1}', 'test_summary')
