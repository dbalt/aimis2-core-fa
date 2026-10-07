"""Unit-тесты сборки промптов по конфигу предвычислений (aimis-2173-precompute-config).

Проверяют:
1. Golden: дефолтный конфиг (всё code) → тексты бит-в-бит равны снапшоту
   исходных промптов (tests/golden_prompts_precompute.json)
2. Отсутствие незаполненных слотов {{...}} вresolved-промптах
3. selection llm → правило «>= N% максимума», без ссылки на флаг значимости
4. numbers llm → SCALING-правило, нет ссылок на display-поля
5. markers/names llm → соответствующие ограничения сняты
6. Подстановка similarity в обоих режимах, алиасов и allowed_names
7. Интеграцию build_branch_report: cfg влияет на промпт и данные
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from sdk.giga.iface import AssistantMsg
from src.libfa2.fa_impl import summarize_prompts_legacy
from src.libfa2.fa_impl.summarize import build_branch_report
from src.libfa2.fa_impl.summarize_prompts import (
    KEY_FACTORS_PROMPTS,
    SHORT_SUMMARY_PROMPTS,
    SummarizerPrompt,
    make_prompt_provider,
    resolve_prompt_texts,
)

pytestmark = pytest.mark.asyncio

_GOLDEN_PATH = Path(__file__).parent / "golden_prompts_precompute.json"

_SLOTS = [
    "{{numbers_rule}}", "{{names_rule}}", "{{children_rule}}", "{{marker_rule}}",
    "{{numbers_formatting}}", "{{display_structure}}", "{{names_field}}",
    "{{selection_rule}}", "{{leaf_rule}}", "{{factors_common_checklist}}",
    "{{summary_common_checklist}}", "{{factors_base_checklist}}",
    "{{summary_final_instruction}}", "{{factors_final_instruction}}",
    "{{similarity_pct}}", "{{threshold_pct}}",
]


def _all_prompts(short, key):
    for prompts in (short, key):
        for text in prompts.values():
            yield text


class TestGoldenDefault:

    def test_short_prompts_match_snapshot(self):
        snap = json.loads(_GOLDEN_PATH.read_text(encoding="utf-8"))
        for b in (1, 2, 3, 4):
            assert SHORT_SUMMARY_PROMPTS[b] == snap["short"][str(b)]

    def test_key_prompts_match_snapshot(self):
        snap = json.loads(_GOLDEN_PATH.read_text(encoding="utf-8"))
        for b in (1, 2, 3, 4):
            assert KEY_FACTORS_PROMPTS[b] == snap["key"][str(b)]

    def test_motiv_matches_snapshot(self):
        snap = json.loads(_GOLDEN_PATH.read_text(encoding="utf-8"))
        assert SummarizerPrompt.MOTIV_PROMPT == snap["motiv"]

    def test_no_unresolved_slots_in_golden(self):
        for text in _all_prompts(SHORT_SUMMARY_PROMPTS, KEY_FACTORS_PROMPTS):
            for slot in _SLOTS:
                assert slot not in text

    def test_golden_has_code_rules(self):
        text = KEY_FACTORS_PROMPTS[1]
        assert "QUOTING NUMBERS" in text
        assert "display.significant = true" in text
        assert "берётся из display.marker" in text
        assert "allowed_names" in text
        assert "differ < 15%" in text


class TestSelectionLlm:

    def test_rule_without_flag_reference(self):
        short, key, _ = resolve_prompt_texts({"selection": {"mode": "llm", "threshold": 0.5}})
        for text in _all_prompts(short, key):
            if "## TASK" in text or "## FORMAT" in text or "Selection rules" in text:
                assert "display.significant" not in text

    def test_threshold_substituted(self):
        short, key, _ = resolve_prompt_texts({"selection": {"mode": "llm", "threshold": 0.5}})
        assert ">= 50% от максимального |вклада|" in key[1]

    def test_custom_threshold_substituted(self):
        _, key, _ = resolve_prompt_texts({"selection": {"mode": "llm", "threshold": 0.42}})
        assert ">= 42%" in key[3]

    def test_significant_child_wording_neutralized(self):
        _, key, _ = resolve_prompt_texts({"selection": {"mode": "llm"}})
        assert "If only 1 significant child" not in key[1]
        assert "If only 1 factor qualifies" in key[1]

    def test_code_mode_keeps_flag_rule(self):
        short, key, _ = resolve_prompt_texts(None)
        assert "display.significant = true" in key[1]
        assert ">= 30% от максимального" not in key[1]


class TestNumbersLlm:

    def test_branches_123_use_legacy_scaling(self):
        short, key, _ = resolve_prompt_texts({"numbers": {"mode": "llm"}})
        for b in (1, 2, 3):
            assert "SCALING" in short[b]
            assert "SCALING" in key[b]
            # legacy-промпты не знают про display
            assert "display." not in short[b]
            assert "display." not in key[b]

    def test_branch4_scaling(self):
        short, key, _ = resolve_prompt_texts({"numbers": {"mode": "llm"}})
        assert "SCALING" in short[4]
        assert "SCALING" in key[4]
        assert "display." not in short[4]
        assert "display." not in key[4]
        assert "impact_to_top_lvl × 100" in short[4]

    def test_threshold_in_legacy_selection(self):
        _, key, _ = resolve_prompt_texts({
            "numbers": {"mode": "llm"},
            "selection": {"mode": "llm", "threshold": 0.4},
        })
        assert ">= 40% of largest" in key[3]

    def test_motiv_unchanged_dual_mode(self):
        snap = json.loads(_GOLDEN_PATH.read_text(encoding="utf-8"))
        _, _, motiv = resolve_prompt_texts({"numbers": {"mode": "llm"}})
        assert motiv == snap["motiv"]  # дуальный промпт: сам работает без display


class TestMarkersLlm:

    def test_marker_rule_replaced(self):
        short, key, _ = resolve_prompt_texts({"markers": {"mode": "llm"}})
        for text in _all_prompts(short, key):
            assert "берётся из display.marker" not in text
            assert "{display.marker}" not in text

    def test_marker_legend_present(self):
        _, key, _ = resolve_prompt_texts({"markers": {"mode": "llm"}})
        assert "Знак числа + или − должен совпадать с маркером." in key[1]


class TestNamesLlm:

    def test_allowed_names_constraint_removed(self):
        short, key, _ = resolve_prompt_texts({"names": {"allowed": "llm"}})
        for text in _all_prompts(short, key):
            # правило белого списка снято; упоминание в скобках параграфа
            # про драйверы (источник ограничения — имена из JSON) остаётся
            assert "ЕДИНСТВЕННЫЙ список разрешённых имён" not in text
            assert "Пиши имена ТОЛЬКО из него" not in text
            assert "Разрешённые имена — ТОЛЬКО из массива" not in text

    def test_children_llm_removes_leaf_case(self):
        short, key, _ = resolve_prompt_texts({"names": {"children": "llm"}})
        for text in _all_prompts(short, key):
            assert "children_names" not in text
            assert "LEAF EDGE CASE" not in text

    def test_children_code_keeps_leaf_case(self):
        _, key, _ = resolve_prompt_texts(None)
        assert "LEAF EDGE CASE" in key[1]
        assert "display.children_names" in key[1]


class TestSimilarity:

    def test_custom_similarity_mixed(self):
        _, key, _ = resolve_prompt_texts({"selection": {"similarity": 0.2}})
        assert "differ < 20%" in key[1]

    def test_custom_similarity_all_llm(self):
        _, key, _ = resolve_prompt_texts({
            "numbers": {"mode": "llm"},
            "selection": {"mode": "llm", "similarity": 0.25},
        })
        assert "differ < 25%" in key[3]


class TestMakePromptProvider:

    def test_substitutes_aliases_and_names(self):
        p = make_prompt_provider(None, "Прогноз", "Факт по ЧПД", ["Корень", "Канал УС"])
        text = p.KEY_FACTORS_PROMPTS[1]
        assert "{{plan_alias}}" not in text
        assert "Прогноз" in text
        assert "Корень, Канал УС" in text
        # {{fact_alias}} в key-промптах ветки 1 нет — проверяем на мотив-промпте
        assert "Факт по ЧПД" in p.MOTIV_PROMPT

    def test_provider_interface(self):
        p = make_prompt_provider(None, "{{plan_alias}}", "{{fact_alias}}", [])
        assert set(p.SHORT_SUMMARY_PROMPTS) == {1, 2, 3, 4}
        assert set(p.KEY_FACTORS_PROMPTS) == {1, 2, 3, 4}
        assert set(p.SUMMARY_PROMPT_PAIRS) == {1, 2, 3}
        assert p.BRANCH_TITLE == SummarizerPrompt.BRANCH_TITLE
        # мотив с identity-алиасами == golden; в дефолтных алиасах токенов нет
        assert p.MOTIV_PROMPT == SummarizerPrompt.MOTIV_PROMPT
        q = make_prompt_provider(None)
        assert "{{plan_alias}}" not in q.MOTIV_PROMPT
        assert "План" in q.MOTIV_PROMPT

    def test_default_provider_equals_golden(self):
        p = make_prompt_provider(None, "{{plan_alias}}", "{{fact_alias}}", ["{{allowed_names}}"])
        assert p.SHORT_SUMMARY_PROMPTS == SHORT_SUMMARY_PROMPTS
        assert p.KEY_FACTORS_PROMPTS == KEY_FACTORS_PROMPTS

    def test_llm_cfg_provider(self):
        p = make_prompt_provider({"numbers": {"mode": "llm"}})
        assert "SCALING" in p.SHORT_SUMMARY_PROMPTS[1]
        assert "display." not in p.SHORT_SUMMARY_PROMPTS[1]


class TestBuildBranchReportWithCfg:
    """Интеграция: cfg доходит до промпта и данных LLM-вызова."""

    def _mock_llm(self):
        mock_llm_client = MagicMock()
        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.data = AssistantMsg("## Краткое саммари\nтест")
        mock_llm_client.ask_giga = AsyncMock(return_value=mock_response)
        return mock_llm_client

    def _data(self):
        return {
            "data": [{
                "hieararchy_node": "ОД",
                "amounts": {"plan": 100.0, "fact": 80.0,
                            "deviation": -20.0, "impact_to_top_lvl": -20.0},
                "details": {"top_factors": [{
                    "hieararchy_node": "Резервы",
                    "amounts": {"plan": 100.0, "fact": 80.0,
                                "deviation": -20.0, "impact_to_top_lvl": -20.0},
                    "details": {"top_factors": []},
                }]},
            }],
        }

    async def test_default_cfg_keeps_code_prompt(self):
        client = self._mock_llm()
        res = await build_branch_report(
            self._data(), 3, AsyncMock(return_value=client),
            precompute_cfg=None,
        )
        assert res.ok
        first_prompt = client.ask_giga.call_args_list[0][1]["msgs"][0].prompt
        assert "QUOTING NUMBERS" in first_prompt

    async def test_numbers_llm_prompt_and_data(self):
        client = self._mock_llm()
        res = await build_branch_report(
            self._data(), 3, AsyncMock(return_value=client),
            precompute_cfg={"numbers": {"mode": "llm"}},
        )
        assert res.ok
        call = client.ask_giga.call_args_list[0]
        prompt = call[1]["msgs"][0].prompt
        sent_data = json.loads(call[1]["msgs"][1].message.removeprefix("data:"))
        assert "SCALING" in prompt
        assert "display." not in prompt
        # в данных нет display и allowed_names (форс всех ручек в llm)
        assert "display" not in sent_data["data"][0]
        assert "allowed_names" not in sent_data

    async def test_names_llm_removes_allowed_names(self):
        client = self._mock_llm()
        res = await build_branch_report(
            self._data(), 3, AsyncMock(return_value=client),
            precompute_cfg={"names": {"allowed": "llm"}},
        )
        assert res.ok
        prompt = client.ask_giga.call_args_list[0][1]["msgs"][0].prompt
        assert "Разрешённые имена" not in prompt

    async def test_legacy_provider_priority(self):
        """Явный legacy-провайдер (A/B-харнесс) приоритетнее cfg-сборки."""
        client = self._mock_llm()
        legacy_provider = summarize_prompts_legacy.SummarizerPrompt
        res = await build_branch_report(
            self._data(), 3, AsyncMock(return_value=client),
            prompt_provider=legacy_provider,
            precompute_cfg={"markers": {"mode": "llm"}},
        )
        assert res.ok
        prompt = client.ask_giga.call_args_list[0][1]["msgs"][0].prompt
        assert "QUOTING NUMBERS" not in prompt  # legacy-текст без правила AIMIS-2173

    async def test_no_cfg_direct_call_works(self):
        """Прямой вызов без cfg (совместимость харнесса) не падает."""
        client = self._mock_llm()
        res = await build_branch_report(self._data(), 3, AsyncMock(return_value=client))
        assert res.ok
