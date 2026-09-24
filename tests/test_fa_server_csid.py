"""Unit-тесты FaServerImpl — проверка проброса client_session_id.

Проверяют что:
1. FaServerImpl.m__process_request принимает client_session_id
2. client_session_id передаётся во все _handle_* методы
3. _handle_get_deviation_summary передаёт csid в DataMgmt и calculate_and_summarize_deviation
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date

import pytest
from sdk.core.monadic import Res

from src.libfa2.fa_server import FaServerImpl
from src.libfa2.data_access.data_mgmt import DataMgmt


pytestmark = pytest.mark.asyncio


class MockDataMgmt(DataMgmt):
    """Заглушка DataMgmt для тестирования."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._calls = []

    async def _exec(self, sql: str, params: dict | None = None, client_session_id: str = '-1'):
        self._calls.append({'type': 'exec', 'sql': sql, 'client_session_id': client_session_id})
        return Res.result(None)

    async def _query(self, sql: str, params: dict | None = None, client_session_id: str = '-1'):
        self._calls.append({'type': 'query', 'sql': sql, 'client_session_id': client_session_id})
        return Res.result([])

    async def get_results(self, code: str, dt: date, client_session_id: str = '-1'):
        self._calls.append({'type': 'get_results', 'code': code, 'client_session_id': client_session_id})
        return Res.error('No results found')

    async def get_metadata(self, code: str, client_session_id: str = '-1'):
        self._calls.append({'type': 'get_metadata', 'code': code, 'client_session_id': client_session_id})
        # имитируем реальный DataMgmt: чтение идёт через _query (csid должен дойти до него)
        await self._query(
            'select metadata from metadata where code = %(code)s',
            {'code': code},
            client_session_id=client_session_id,
        )
        return Res.result({
            'code': code,
            'source_params': {'source_name': '', 'rep_dt_column': 'rep_dt'},
            'search_dev_params': {'plan_column': 'plan', 'fact_column': 'fact'},
            'hier_lst': [],
        })

    async def save_results(self, code: str, dt: date, data: dict, summary: str, client_session_id: str = '-1'):
        self._calls.append({'type': 'save_results', 'code': code, 'client_session_id': client_session_id})
        return Res.result(None)


class TestFaServerImplCsId:

    async def test_m__process_request_accepts_and_passes_csid(self):
        """m__process_request принимает client_session_id и передаёт в обработчик."""
        mock_kc = MagicMock()
        data_mgmt = MockDataMgmt('metadata', 'results')
        data_access = MagicMock()

        server = FaServerImpl(
            keydb_client=mock_kc,
            data_mgmt=data_mgmt,
            data_access=data_access,
            llm_client_gen_fn=lambda: AsyncMock(),
        )

        # Mock calculate_and_summarize_deviation
        with patch('src.libfa2.fa_server.calculate_and_summarize_deviation', new_callable=AsyncMock, return_value=Res.mk_result(({}, ''))):
            payload = {
                'action': 'get_deviation_summary',
                'payload': {'code': 'test_code', 'dt': '2026-01-01'}
            }
            async for result in server.m__process_request(payload, client_session_id='csid-test-123'):
                pass

        # Проверяем что csid был передан в get_metadata и save_results
        get_metadata_call = [c for c in data_mgmt._calls if c['type'] == 'get_metadata']
        save_results_call = [c for c in data_mgmt._calls if c['type'] == 'save_results']

        assert len(get_metadata_call) == 1
        assert get_metadata_call[0]['client_session_id'] == 'csid-test-123'

        assert len(save_results_call) == 1
        assert save_results_call[0]['client_session_id'] == 'csid-test-123'

    async def test_handle_delete_metadata_passes_csid(self):
        """_handle_delete_metadata передаёт client_session_id в _exec."""
        mock_kc = MagicMock()
        data_mgmt = MockDataMgmt('metadata', 'results')
        data_access = MagicMock()

        server = FaServerImpl(
            keydb_client=mock_kc,
            data_mgmt=data_mgmt,
            data_access=data_access,
            llm_client_gen_fn=lambda: AsyncMock(),
        )

        payload = {
            'action': 'delete_metadata',
            'payload': {'code': 'test_code'}
        }

        async for _ in server.m__process_request(payload, client_session_id='csid-del-456'):
            pass

        exec_call = [c for c in data_mgmt._calls if c['type'] == 'exec']
        assert len(exec_call) == 1
        assert exec_call[0]['client_session_id'] == 'csid-del-456'

    async def test_handle_save_metadata_passes_csid(self):
        """_handle_save_metadata передаёт client_session_id в _exec."""
        mock_kc = MagicMock()
        data_mgmt = MockDataMgmt('metadata', 'results')
        data_access = MagicMock()

        server = FaServerImpl(
            keydb_client=mock_kc,
            data_mgmt=data_mgmt,
            data_access=data_access,
            llm_client_gen_fn=lambda: AsyncMock(),
        )

        payload = {
            'action': 'save_metadata',
            'payload': {'code': 'test_code', 'data': {'key': 'value'}}
        }

        async for _ in server.m__process_request(payload, client_session_id='csid-save-789'):
            pass

        exec_calls = [c for c in data_mgmt._calls if c['type'] == 'exec']
        # save_metadata вызывает delete_metadata + insert
        assert len(exec_calls) == 2
        assert all(c['client_session_id'] == 'csid-save-789' for c in exec_calls)

    async def test_handle_get_metadata_passes_csid(self):
        """_handle_get_metadata передаёт client_session_id в _query."""
        mock_kc = MagicMock()
        data_mgmt = MockDataMgmt('metadata', 'results')
        data_access = MagicMock()

        server = FaServerImpl(
            keydb_client=mock_kc,
            data_mgmt=data_mgmt,
            data_access=data_access,
            llm_client_gen_fn=lambda: AsyncMock(),
        )

        payload = {
            'action': 'get_metadata',
            'payload': {'code': 'test_code'}
        }

        async for _ in server.m__process_request(payload, client_session_id='csid-get-012'):
            pass

        query_call = [c for c in data_mgmt._calls if c['type'] == 'query']
        assert len(query_call) == 1
        assert query_call[0]['client_session_id'] == 'csid-get-012'

    async def test_handle_delete_results_passes_csid(self):
        """_handle_delete_results передаёт client_session_id в _exec."""
        mock_kc = MagicMock()
        data_mgmt = MockDataMgmt('metadata', 'results')
        data_access = MagicMock()

        server = FaServerImpl(
            keydb_client=mock_kc,
            data_mgmt=data_mgmt,
            data_access=data_access,
            llm_client_gen_fn=lambda: AsyncMock(),
        )

        payload = {
            'action': 'delete_results',
            'payload': {'code': 'test_code', 'dt': '2026-01-01'}
        }

        async for _ in server.m__process_request(payload, client_session_id='csid-dr-345'):
            pass

        exec_call = [c for c in data_mgmt._calls if c['type'] == 'exec']
        assert len(exec_call) == 1
        assert exec_call[0]['client_session_id'] == 'csid-dr-345'

    async def test_handle_delete_results_for_dt_passes_csid(self):
        """_handle_delete_results_for_dt передаёт client_session_id в _exec."""
        mock_kc = MagicMock()
        data_mgmt = MockDataMgmt('metadata', 'results')
        data_access = MagicMock()

        server = FaServerImpl(
            keydb_client=mock_kc,
            data_mgmt=data_mgmt,
            data_access=data_access,
            llm_client_gen_fn=lambda: AsyncMock(),
        )

        payload = {
            'action': 'delete_results_for_dt',
            'payload': {'dt': '2026-01-01'}
        }

        async for _ in server.m__process_request(payload, client_session_id='csid-drfd-678'):
            pass

        exec_call = [c for c in data_mgmt._calls if c['type'] == 'exec']
        assert len(exec_call) == 1
        assert exec_call[0]['client_session_id'] == 'csid-drfd-678'

    async def test_process_request_uses_default_csid(self):
        """m__process_request без csid использует дефолт '-1'."""
        mock_kc = MagicMock()
        data_mgmt = MockDataMgmt('metadata', 'results')
        data_access = MagicMock()

        server = FaServerImpl(
            keydb_client=mock_kc,
            data_mgmt=data_mgmt,
            data_access=data_access,
            llm_client_gen_fn=lambda: AsyncMock(),
        )

        payload = {
            'action': 'get_metadata',
            'payload': {'code': 'test_code'}
        }

        async for _ in server.m__process_request(payload):
            pass

        query_call = [c for c in data_mgmt._calls if c['type'] == 'query']
        assert len(query_call) == 1
        assert query_call[0]['client_session_id'] == '-1'
