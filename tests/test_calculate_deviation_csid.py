"""Unit-тесты calculate_and_summarize_deviation — проверка проброса client_session_id.

Проверяют что:
1. calculate_and_summarize_deviation принимает и передаёт csid в summarize
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date

import pytest
from sdk.core.monadic import Res

from src.libfa2.fa_impl.all_together import calculate_and_summarize_deviation
from src.libfa2.fa_impl.deviation_calc_metadata import DeviationCalcMetadata
from src.libfa2.fa_impl.units import SourceParameters, SearchDevParameters


pytestmark = pytest.mark.asyncio


def _make_metadata() -> DeviationCalcMetadata:
    """Минимальные валидные метаданные: пустой список иерархий, без мотив. коррекции."""
    return DeviationCalcMetadata(
        code='test_code',
        source_params=SourceParameters(),
        search_dev_params=SearchDevParameters(plan_column='plan', fact_column='fact'),
        hier_lst=[],
        aliases={},
    )


class TestCalculateAndSummarizeDeviationCsId:

    async def test_passes_csid_to_summarize(self):
        """calculate_and_summarize_deviation передаёт client_session_id в summarize."""
        mock_data_access = MagicMock()
        mock_llm_client = AsyncMock()
        mock_llm_client.ask_giga = AsyncMock(return_value=Res.mk_result(
            type('obj', (object,), {
                'ok': True,
                'data': type('obj', (object,), {'role': 'assistant', 'message': 'test'})()
            })()
        ))

        metadata = _make_metadata()

        with patch('src.libfa2.fa_impl.all_together.summarize', new_callable=AsyncMock, return_value=Res.mk_result('test summary')) as mock_summarize:
            result = await calculate_and_summarize_deviation(
                'test_code',
                date(2026, 1, 1),
                metadata,
                mock_data_access,
                lambda: mock_llm_client,
                'GigaChat-3-Ultra',
                'GigaChat-2-Max',
                client_session_id='csid-all-123'
            )

            assert result.ok
            mock_summarize.assert_called_once()
            call_kwargs = mock_summarize.call_args[1]
            assert call_kwargs['client_session_id'] == 'csid-all-123'

    async def test_default_csid_in_calculate_and_summarize_deviation(self):
        """Если csid не передан, calculate_and_summarize_deviation передаёт '-1' в summarize."""
        mock_data_access = MagicMock()
        mock_llm_client = AsyncMock()
        mock_llm_client.ask_giga = AsyncMock(return_value=Res.mk_result(
            type('obj', (object,), {
                'ok': True,
                'data': type('obj', (object,), {'role': 'assistant', 'message': 'test'})()
            })()
        ))

        metadata = _make_metadata()

        with patch('src.libfa2.fa_impl.all_together.summarize', new_callable=AsyncMock, return_value=Res.mk_result('test summary')) as mock_summarize:
            result = await calculate_and_summarize_deviation(
                'test_code',
                date(2026, 1, 1),
                metadata,
                mock_data_access,
                lambda: mock_llm_client,
            )

            assert result.ok
            mock_summarize.assert_called_once()
            call_kwargs = mock_summarize.call_args[1]
            assert call_kwargs['client_session_id'] == '-1'
