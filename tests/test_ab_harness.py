"""Smoke-тесты A/B-харнесса adhoc__ab_prompt_runs (AIMIS-2173).

Прогоняют оркестрацию харнесса с ФЕЙКОВЫМ LLM-клиентом (без KeyDB/прокси):
- разрезка отчёта (LLM-часть vs детерминированная таблица);
- агрегация ошибок по классам;
- end-to-end run_variant: 10 последовательных прогонов, валидация, файлы.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from sdk.core.monadic import Res
from sdk.giga.iface import AssistantMsg

import src.adhoc.adhoc__ab_prompt_runs as harness
from src.libfa2.fa_impl.value_formatter import enrich_display

from tests.test_value_formatter import _non_ratio_data


# Чистый отчёт из display-строк фикстуры _non_ratio_data (оракул: 0 ошибок)
_CLEAN_REPORT = (
    "## Краткое саммари\n"
    "Показатель «ОД до резервов» выполнил план: факт 29,3 млрд, "
    "план 29,2 млрд, отклонение +91,4 млн.\n"
    "\n"
    "## Ключевые факторы\n"
    "- 🔴 **ОД до резервов (УС)** — вклад -535,5 млн\n"
    "- ❇️ **Прочие чистые операционные доходы (МБ)** — вклад +125,1 млн\n"
)


class TestHelpers:

    def test_llm_part_splits_table(self):
        report = _CLEAN_REPORT + "\n\n\n" + harness.TABLE_HEADER_MARKER + " отклонений...\n| 1 | ..."
        part = harness._llm_part_of_report(report)
        assert harness.TABLE_HEADER_MARKER not in part
        assert "Ключевые факторы" in part

    def test_llm_part_no_table(self):
        assert harness._llm_part_of_report(_CLEAN_REPORT) == _CLEAN_REPORT

    def test_aggregate_counts_classes(self):
        logs = [
            {"ok": True, "validation": {"errors": [
                {"error_class": "INVENTED_NUMBER", "fragment": "x", "detail": ""},
                {"error_class": "INVENTED_NUMBER", "fragment": "y", "detail": ""},
            ]}},
            {"ok": True, "validation": {"errors": []}},
            {"ok": False, "error": "429"},
        ]
        totals = harness._aggregate(logs)
        assert totals["ok_runs"] == 2
        assert totals["failed_runs"] == 1
        assert totals["total_errors"] == 2
        assert totals["by_class"]["INVENTED_NUMBER"] == 2


class TestRunVariantE2E:

    pytestmark = pytest.mark.asyncio

    async def test_ten_sequential_runs_with_fake_llm(self, tmp_path, monkeypatch):
        """10 прогонов → 10 файлов, валидация чистого отчёта — 0 ошибок."""
        fake_client = MagicMock()
        fake_response = MagicMock()
        fake_response.ok = True
        fake_response.data = AssistantMsg(_CLEAN_REPORT)
        fake_client.ask_giga = AsyncMock(return_value=fake_response)

        async def fake_client_fn():
            return fake_client

        monkeypatch.setattr(harness, "get_llm_client_cached", fake_client_fn)
        monkeypatch.setattr(harness, "PAUSE_BETWEEN_RUNS_SEC", 0)

        data = _non_ratio_data()
        logs = await harness.run_variant(
            "fixture_x", data, "new", harness.VARIANTS["new"],
            harness.AB_MODEL, str(tmp_path),
        )

        assert len(logs) == harness.RUNS_PER_VARIANT == 10
        assert all(e["ok"] for e in logs)
        assert all(e["validation"]["ok"] for e in logs)
        # прогоны независимы: каждый дошёл до LLM
        assert fake_client.ask_giga.await_count >= 20  # саммари + факторы на прогон
        # файлы отчётов записаны (fixture__variant__model__runN.md)
        files = sorted(tmp_path.glob(f"fixture_x__new__{harness.AB_MODEL}__run*.md"))
        assert len(files) == 10

    async def test_validation_catches_bad_llm(self, tmp_path, monkeypatch):
        """Фейковый LLM возвращает число не из display → оракул ловит."""
        bad_report = (
            "## Краткое саммари\n"
            "Показатель выполнил план: отклонение 1 105 млн.\n"
        )
        fake_client = MagicMock()
        fake_response = MagicMock()
        fake_response.ok = True
        fake_response.data = AssistantMsg(bad_report)
        fake_client.ask_giga = AsyncMock(return_value=fake_response)

        async def fake_client_fn():
            return fake_client

        monkeypatch.setattr(harness, "get_llm_client_cached", fake_client_fn)
        monkeypatch.setattr(harness, "PAUSE_BETWEEN_RUNS_SEC", 0)

        logs = await harness.run_variant(
            "fixture_y", _non_ratio_data(), "legacy", harness.VARIANTS["legacy"],
            harness.AB_MODEL, str(tmp_path),
        )
        totals = harness._aggregate(logs)
        assert totals["total_errors"] > 0
        assert totals["by_class"]["WRONG_SCALE"] + totals["by_class"]["INVENTED_NUMBER"] > 0
