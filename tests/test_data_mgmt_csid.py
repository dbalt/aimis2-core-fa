"""Unit-тесты DataMgmtDataGate — проверка проброса client_session_id.

Проверяют что:
1. DataMgmtDataGate._exec и _query передают csid в GeneralSQLDataGateClientPart
2. Публичные методы (get_metadata, save_metadata, etc.) передают csid
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import date

import pytest
from sdk.core.monadic import Res

from src.libfa2.data_access.data_mgmt import DataMgmtDataGate


pytestmark = pytest.mark.asyncio


class TestDataMgmtDataGateCsId:

    async def test_exec_passes_csid_to_datagate(self):
        """DataMgmtDataGate._exec передаёт client_session_id в GeneralSQLDataGateClientPart.get_data."""
        mock_kc = MagicMock()

        with patch('src.libfa2.data_access.data_mgmt.GeneralSQLDataGateClientPart') as MockDGC:
            mock_dgc_instance = MagicMock()
            mock_dgc_instance.get_data = AsyncMock(return_value=Res.result(None))
            MockDGC.return_value = mock_dgc_instance

            mgmt = DataMgmtDataGate(mock_kc, 'metadata', 'results')
            await mgmt._exec('INSERT INTO test VALUES (1)', {'param': 'value'}, client_session_id='csid-test-123')

            mock_dgc_instance.get_data.assert_called_once_with(
                sql='INSERT INTO test VALUES (1)',
                params={'param': 'value'},
                client_session_id='csid-test-123'
            )

    async def test_query_passes_csid_to_datagate(self):
        """DataMgmtDataGate._query передаёт client_session_id в GeneralSQLDataGateClientPart.get_data."""
        mock_kc = MagicMock()
        expected_rows = [{'metadata': '{"key": "value"}'}]

        with patch('src.libfa2.data_access.data_mgmt.GeneralSQLDataGateClientPart') as MockDGC:
            mock_dgc_instance = MagicMock()
            mock_dgc_instance.get_data = AsyncMock(return_value=Res.result(expected_rows))
            MockDGC.return_value = mock_dgc_instance

            mgmt = DataMgmtDataGate(mock_kc, 'metadata', 'results')
            result = await mgmt._query('SELECT * FROM test', {'code': 'abc'}, client_session_id='csid-query-456')

            mock_dgc_instance.get_data.assert_called_once_with(
                sql='SELECT * FROM test',
                params={'code': 'abc'},
                client_session_id='csid-query-456'
            )
            assert result.ok

    async def test_get_metadata_passes_csid(self):
        """DataMgmtDataGate.get_metadata передаёт csid в _query."""
        mock_kc = MagicMock()
        expected_rows = [{'metadata': '{"code": "test", "calc_params_lst": []}'}]

        with patch('src.libfa2.data_access.data_mgmt.GeneralSQLDataGateClientPart') as MockDGC:
            mock_dgc_instance = MagicMock()
            mock_dgc_instance.get_data = AsyncMock(return_value=Res.result(expected_rows))
            MockDGC.return_value = mock_dgc_instance

            mgmt = DataMgmtDataGate(mock_kc, 'metadata', 'results')
            result = await mgmt.get_metadata('test_code', client_session_id='csid-meta-789')

            assert result.ok
            mock_dgc_instance.get_data.assert_called_once_with(
                sql='select metadata from metadata where code = %(code)s',
                params={'code': 'test_code'},
                client_session_id='csid-meta-789'
            )

    async def test_save_metadata_passes_csid(self):
        """DataMgmtDataGate.save_metadata передаёт csid в _exec (delete + insert)."""
        mock_kc = MagicMock()

        with patch('src.libfa2.data_access.data_mgmt.GeneralSQLDataGateClientPart') as MockDGC:
            mock_dgc_instance = MagicMock()
            mock_dgc_instance.get_data = AsyncMock(return_value=Res.result(None))
            MockDGC.return_value = mock_dgc_instance

            mgmt = DataMgmtDataGate(mock_kc, 'metadata', 'results')
            await mgmt.save_metadata('test_code', {'key': 'value'}, client_session_id='csid-save-012')

            # save_metadata вызывает delete_metadata (1 вызов) + insert (1 вызов) = 2 вызова
            assert mock_dgc_instance.get_data.call_count == 2
            for call_args in mock_dgc_instance.get_data.call_args_list:
                assert call_args[1]['client_session_id'] == 'csid-save-012'

    async def test_get_results_passes_csid(self):
        """DataMgmtDataGate.get_results передаёт csid в _query."""
        mock_kc = MagicMock()
        expected_rows = [{'data': '{}', 'summary': 'test summary'}]

        with patch('src.libfa2.data_access.data_mgmt.GeneralSQLDataGateClientPart') as MockDGC:
            mock_dgc_instance = MagicMock()
            mock_dgc_instance.get_data = AsyncMock(return_value=Res.result(expected_rows))
            MockDGC.return_value = mock_dgc_instance

            mgmt = DataMgmtDataGate(mock_kc, 'metadata', 'results')
            result = await mgmt.get_results('test_code', date(2026, 1, 1), client_session_id='csid-res-345')

            assert result.ok
            mock_dgc_instance.get_data.assert_called_once_with(
                sql='select data, summary from results where code = %(code)s and dt = %(dt)s',
                params={'code': 'test_code', 'dt': date(2026, 1, 1)},
                client_session_id='csid-res-345'
            )

    async def test_delete_results_passes_csid(self):
        """DataMgmtDataGate.delete_results передаёт csid в _exec."""
        mock_kc = MagicMock()

        with patch('src.libfa2.data_access.data_mgmt.GeneralSQLDataGateClientPart') as MockDGC:
            mock_dgc_instance = MagicMock()
            mock_dgc_instance.get_data = AsyncMock(return_value=Res.result(None))
            MockDGC.return_value = mock_dgc_instance

            mgmt = DataMgmtDataGate(mock_kc, 'metadata', 'results')
            await mgmt.delete_results('test_code', date(2026, 1, 1), client_session_id='csid-del-678')

            mock_dgc_instance.get_data.assert_called_once_with(
                sql='delete from results where code = %(code)s and dt = %(dt)s',
                params={'code': 'test_code', 'dt': date(2026, 1, 1)},
                client_session_id='csid-del-678'
            )

    async def test_delete_results_for_dt_passes_csid(self):
        """DataMgmtDataGate.delete_results_for_dt передаёт csid в _exec."""
        mock_kc = MagicMock()

        with patch('src.libfa2.data_access.data_mgmt.GeneralSQLDataGateClientPart') as MockDGC:
            mock_dgc_instance = MagicMock()
            mock_dgc_instance.get_data = AsyncMock(return_value=Res.result(None))
            MockDGC.return_value = mock_dgc_instance

            mgmt = DataMgmtDataGate(mock_kc, 'metadata', 'results')
            await mgmt.delete_results_for_dt(date(2026, 1, 1), client_session_id='csid-del-dt-901')

            mock_dgc_instance.get_data.assert_called_once_with(
                sql='delete from results where dt = %(dt)s',
                params={'dt': date(2026, 1, 1)},
                client_session_id='csid-del-dt-901'
            )

    async def test_save_results_passes_csid(self):
        """DataMgmtDataGate.save_results передаёт csid в _exec (delete + insert)."""
        mock_kc = MagicMock()

        with patch('src.libfa2.data_access.data_mgmt.GeneralSQLDataGateClientPart') as MockDGC:
            mock_dgc_instance = MagicMock()
            mock_dgc_instance.get_data = AsyncMock(return_value=Res.result(None))
            MockDGC.return_value = mock_dgc_instance

            mgmt = DataMgmtDataGate(mock_kc, 'metadata', 'results')
            await mgmt.save_results('test_code', date(2026, 1, 1), {'data': 'test'}, 'summary', client_session_id='csid-sr-234')

            # save_results вызывает delete_results (1 вызов) + insert (1 вызов) = 2 вызова
            assert mock_dgc_instance.get_data.call_count == 2
            for call_args in mock_dgc_instance.get_data.call_args_list:
                assert call_args[1]['client_session_id'] == 'csid-sr-234'

    async def test_default_csid_is_dash1(self):
        """Если csid не передан, используется дефолт '-1'."""
        mock_kc = MagicMock()

        with patch('src.libfa2.data_access.data_mgmt.GeneralSQLDataGateClientPart') as MockDGC:
            mock_dgc_instance = MagicMock()
            mock_dgc_instance.get_data = AsyncMock(return_value=Res.result(None))
            MockDGC.return_value = mock_dgc_instance

            mgmt = DataMgmtDataGate(mock_kc, 'metadata', 'results')
            await mgmt._exec('DELETE FROM test', {'code': 'abc'})

            mock_dgc_instance.get_data.assert_called_once_with(
                sql='DELETE FROM test',
                params={'code': 'abc'},
                client_session_id='-1'
            )
