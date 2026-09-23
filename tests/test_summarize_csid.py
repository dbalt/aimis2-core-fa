"""Unit-тесты summarize — проверка проброса client_session_id в GigaChat.

Проверяют что:
1. _base_llm_processing_function передаёт csid в llm_client.ask_giga
2. build_branch_report передаёт csid в _base_llm_processing_function
3. summarize передаёт csid в build_branch_report
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sdk.core.monadic import Res
from sdk.giga.iface import MsgBase, AssistantMsg

from src.libfa2.fa_impl.summarize import _base_llm_processing_function, summarize, build_branch_report


pytestmark = pytest.mark.asyncio


class TestBaseLlmProcessingFunctionCsId:

    async def test_passes_csid_to_ask_giga(self):
        """_base_llm_processing_function передаёт client_session_id в llm_client.ask_giga."""
        mock_llm_client = MagicMock()
        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.data = AssistantMsg(message='test response', role='assistant')
        mock_llm_client.ask_giga = AsyncMock(return_value=mock_response)

        system_prompt = 'System prompt'
        data = {'key': 'value'}

        result = await _base_llm_processing_function(
            system_prompt, data, mock_llm_client, 'GigaChat-3-Ultra', client_session_id='csid-giga-123'
        )

        assert result.ok
        mock_llm_client.ask_giga.assert_called_once()
        call_kwargs = mock_llm_client.ask_giga.call_args[1]
        assert call_kwargs['client_session_id'] == 'csid-giga-123'

    async def test_default_csid_is_dash1(self):
        """Если csid не передан, используется дефолт '-1'."""
        mock_llm_client = MagicMock()
        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.data = AssistantMsg(message='test response', role='assistant')
        mock_llm_client.ask_giga = AsyncMock(return_value=mock_response)

        system_prompt = 'System prompt'
        data = {'key': 'value'}

        await _base_llm_processing_function(system_prompt, data, mock_llm_client, 'GigaChat-3-Ultra')

        call_kwargs = mock_llm_client.ask_giga.call_args[1]
        assert call_kwargs['client_session_id'] == '-1'


class TestBuildBranchReportCsId:

    async def test_passes_csid_to_llm_processing(self):
        """build_branch_report передаёт client_session_id в _base_llm_processing_function."""
        mock_llm_client = MagicMock()
        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.data = AssistantMsg(message='test response', role='assistant')
        mock_llm_client.ask_giga = AsyncMock(return_value=mock_response)

        data = {'data': [{'hieararchy_node': 'test', 'amounts': {'plan': 100, 'fact': 80, 'deviation': -20, 'impact_to_top_lvl': -20}, 'details': [], 'top_factors': []}]}
        branch = 1

        result = await build_branch_report(
            data, branch, lambda: mock_llm_client, 'GigaChat-3-Ultra', 'GigaChat-2-Max', client_session_id='csid-branch-456'
        )

        assert result.ok
        # build_branch_report вызывает _base_llm_processing_function минимум 2 раза (short_summary + key_factors)
        assert mock_llm_client.ask_giga.call_count >= 2
        for call_args in mock_llm_client.ask_giga.call_args_list:
            assert call_args[1]['client_session_id'] == 'csid-branch-456'


class TestSummarizeCsId:

    async def test_passes_csid_to_build_branch_report(self):
        """summarize передаёт client_session_id в build_branch_report."""
        mock_llm_client = MagicMock()
        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.data = AssistantMsg(message='test response', role='assistant')
        mock_llm_client.ask_giga = AsyncMock(return_value=mock_response)

        data = {
            'data': [{'hieararchy_node': 'test', 'amounts': {'plan': 100, 'fact': 80, 'deviation': -20, 'impact_to_top_lvl': -20}, 'details': [], 'top_factors': []}],
            'metric_type': 'absolute'
        }

        result = await summarize(
            data, lambda: mock_llm_client, 'GigaChat-3-Ultra', 'GigaChat-2-Max', client_session_id='csid-sum-789'
        )

        assert result.ok
        # summarize вызывает build_branch_report, который вызывает _base_llm_processing_function
        assert mock_llm_client.ask_giga.call_count >= 2
        for call_args in mock_llm_client.ask_giga.call_args_list:
            assert call_args[1]['client_session_id'] == 'csid-sum-789'

    async def test_default_csid_in_summarize(self):
        """Если csid не передан, summarize передаёт '-1' в build_branch_report."""
        mock_llm_client = MagicMock()
        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.data = AssistantMsg(message='test response', role='assistant')
        mock_llm_client.ask_giga = AsyncMock(return_value=mock_response)

        data = {
            'data': [{'hieararchy_node': 'test', 'amounts': {'plan': 100, 'fact': 80, 'deviation': -20, 'impact_to_top_lvl': -20}, 'details': [], 'top_factors': []}],
            'metric_type': 'absolute'
        }

        result = await summarize(data, lambda: mock_llm_client)

        assert result.ok
        assert mock_llm_client.ask_giga.call_count >= 2
        for call_args in mock_llm_client.ask_giga.call_args_list:
            assert call_args[1]['client_session_id'] == '-1'
