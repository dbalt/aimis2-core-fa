"""
Unit tests for FaServerImpl._handle_get_deviation_summary().

Verifies that the response dict contains both 'summary' and 'data' keys,
and that 'data' is JSON-serializable.
"""

import json
import asyncio
from datetime import date
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from sdk.core.monadic import Res


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _make_fa_server(data_mgmt=None, data_access=None):
    from libfa2.fa_server import FaServerImpl
    mock_keydb = MagicMock()
    return FaServerImpl(
        keydb_client=mock_keydb,
        data_mgmt=data_mgmt or MagicMock(),
        data_access=data_access or MagicMock(),
        llm_client_gen_fn=MagicMock(),
    )


# ── Cache branch: response contains 'summary' and 'data' ───────────────


class TestCachedResponseHasSummaryAndData:
    """1.3 + 1.2: cached branch returns dict with 'summary' and 'data'."""

    def test_cached_response_has_both_keys(self):
        cached_data = {"data": [{"plan": 100, "fact": 120}]}
        cached_summary = "Тестовое саммари"

        mock_dm = MagicMock()
        mock_dm.get_results = AsyncMock(return_value=Res.result((cached_data, cached_summary)))

        server = _make_fa_server(data_mgmt=mock_dm)
        payload = {'code': 'TEST_CODE', 'dt': '2026-05-11'}

        result = run_async(server._handle_get_deviation_summary(payload))

        assert 'summary' in result
        assert 'data' in result
        assert result['summary'] == cached_summary
        assert result['data'] == cached_data


# ── Fresh calculation branch: response contains 'summary' and 'data' ────


class TestFreshCalcResponseHasSummaryAndData:
    """1.3 + 1.1: fresh calculation branch returns dict with 'summary' and 'data'."""

    def test_fresh_response_has_both_keys(self):
        fresh_data = {"data": [{"plan": 200, "fact": 150}]}
        fresh_summary = "Свежее саммари"

        mock_dm = MagicMock()
        mock_dm.get_results = AsyncMock(return_value=Res.error('not found'))
        mock_dm.get_metadata = AsyncMock(return_value=Res.result({'some': 'metadata'}))
        mock_dm.save_results = AsyncMock(return_value=Res.result(None))

        server = _make_fa_server(data_mgmt=mock_dm)

        with patch('libfa2.fa_server.DeviationCalcMetadata.from_dict', return_value=MagicMock()), \
             patch('libfa2.fa_server.calculate_and_summarize_deviation',
                   new=AsyncMock(return_value=Res.result((fresh_data, fresh_summary)))):
            payload = {'code': 'TEST_CODE', 'dt': '2026-05-11'}
            result = run_async(server._handle_get_deviation_summary(payload))

        assert 'summary' in result
        assert 'data' in result
        assert result['summary'] == fresh_summary
        assert result['data'] == fresh_data


# ── 1.4: data is JSON-serializable ─────────────────────────────────────


class TestDataJsonSerializable:
    """1.4: data in the response is JSON-serializable."""

    def test_cached_data_json_serializable(self):
        cached_data = {
            "data": [
                {"plan": 100.0, "fact": 120.0, "deviation": 20.0},
                {"plan": 50.0, "fact": 30.0, "deviation": -20.0},
            ],
            "motiv_correction": {
                "plan": 10.0, "fact": 15.0, "deviation": 5.0,
                "label": "мотивационной корректировки",
                "has_plan": True, "has_fact": True,
            },
            "plan_alias": "План",
            "fact_alias": "Факт",
        }
        cached_summary = "Саммари"

        mock_dm = MagicMock()
        mock_dm.get_results = AsyncMock(return_value=Res.result((cached_data, cached_summary)))

        server = _make_fa_server(data_mgmt=mock_dm)
        payload = {'code': 'TEST_CODE', 'dt': '2026-05-11'}

        result = run_async(server._handle_get_deviation_summary(payload))

        # Must not raise
        json_str = json.dumps(result['data'], ensure_ascii=False)
        assert isinstance(json_str, str)
        # Round-trip
        parsed = json.loads(json_str)
        assert parsed == cached_data

    def test_fresh_data_json_serializable(self):
        fresh_data = {
            "data": [{"plan": 1.0, "fact": 2.0}],
        }
        fresh_summary = "Саммари 2"

        mock_dm = MagicMock()
        mock_dm.get_results = AsyncMock(return_value=Res.error('not found'))
        mock_dm.get_metadata = AsyncMock(return_value=Res.result({'some': 'metadata'}))
        mock_dm.save_results = AsyncMock(return_value=Res.result(None))

        server = _make_fa_server(data_mgmt=mock_dm)

        with patch('libfa2.fa_server.DeviationCalcMetadata.from_dict', return_value=MagicMock()), \
             patch('libfa2.fa_server.calculate_and_summarize_deviation',
                   new=AsyncMock(return_value=Res.result((fresh_data, fresh_summary)))):
            payload = {'code': 'TEST_CODE', 'dt': '2026-05-11'}
            result = run_async(server._handle_get_deviation_summary(payload))

        json_str = json.dumps(result['data'], ensure_ascii=False)
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed == fresh_data
