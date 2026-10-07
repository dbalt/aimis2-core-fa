"""Unit-тесты summary_validator (оракул A/B-харнесса, AIMIS-2173).

Проверяют:
1. Чистый отчёт (собранный из display-строк) — 0 ошибок (нет ложных срабатываний)
2. Паттерны 5 прод-инцидентов (t_aimis__fa__results) классифицируются нужными классами:
   - 3ba67ea…: выдуманные драйверы (резервы/ЧПД/комиссии/персонал) + «1 105 млн»
   - 611483b…: выдуманная вложенность налога (−3850,2 / +153,9)
   - 252fe9f…: «рост страховых выплат −6190,72» (динамика + выдумка)
   - 75a21db…: нарративная выдумка про точки клиента
   - 797d34c…: REPACKED_PLAN_FACT (plan/fact узла выдан за драйвер)
3. Маркеры: 🟢 запрещён, знак ↔ маркер
"""

from __future__ import annotations

import sys
import os

from src.libfa2.fa_impl.value_formatter import enrich_display
from src.adhoc.summary_validator import (
    DYNAMICS_LANGUAGE,
    INVENTED_DRIVER,
    INVENTED_NUMBER,
    REPACKED_PLAN_FACT,
    UNALLOWED_NAME,
    WRONG_MARKER,
    WRONG_SCALE,
    validate_report,
    validate_report_json,
)

sys.path.insert(0, os.path.dirname(__file__))

from tests.test_value_formatter import _non_ratio_data  # noqa: E402


def _enriched() -> dict:
    return enrich_display(_non_ratio_data())


class TestCleanReport:

    def test_clean_report_zero_errors(self):
        data = _enriched()
        report = (
            "## Краткое саммари\n"
            "Показатель «ОД до резервов» выполнил план: факт 29,3 млрд, "
            "план 29,2 млрд, отклонение +91,4 млн. Вклад канала УС -535,5 млн, "
            "компенсировано вкладом МБ +125,1 млн.\n"
            "\n"
            "## Ключевые факторы\n"
            "- 🔴 **ОД до резервов (УС)** — вклад -535,5 млн\n"
            "- ❇️ **Прочие чистые операционные доходы (МБ)** — вклад +125,1 млн\n"
            "- 🔴 **Расчёты за устройства самообслуживания (УС)** — вклад -660,6 млн\n"
        )
        res = validate_report(report, data)
        assert res.ok, [e.to_dict() for e in res.errors]

    def test_json_wrapper(self):
        data = _enriched()
        import json
        res = validate_report_json("факт 29,3 млрд", json.dumps(data, ensure_ascii=False))
        assert res.ok


class TestProdPattern1InventedDrivers:
    """3ba67ea…: Чистая прибыль — выдуманные драйверы, «1 105 млн»."""

    REPORT = (
        "## Ключевые факторы\n"
        "- 🔴 **Чистая прибыль** — вклад -1 105 млн\n"
        "  - Главный драйвер — расходы по кредитным картам (-986,74 млн руб.)\n"
    )

    def test_invented_driver(self):
        res = validate_report(self.REPORT, _enriched())
        classes = {e.error_class for e in res.errors}
        assert INVENTED_DRIVER in classes

    def test_digit_loss_number(self):
        res = validate_report(self.REPORT, _enriched())
        classes = {e.error_class for e in res.errors}
        assert INVENTED_NUMBER in classes or WRONG_SCALE in classes


class TestProdPattern2InventedNesting:
    """611483b…: выдуманная вложенность налога −3850,2 / +153,9."""

    def test_invented_numbers(self):
        report = (
            "- 🔴 **ОД до резервов (УС)** — вклад -535,5 млн\n"
            "  - в том числе налог на прибыль -3 850,2 млн\n"
            "  - в том числе компенсация +153,9 млн\n"
        )
        res = validate_report(report, _enriched())
        classes = {e.error_class for e in res.errors}
        assert INVENTED_NUMBER in classes


class TestProdPattern3Dynamics:
    """252fe9f…: «рост страховых выплат −6190,72» у ОД после резервов."""

    def test_dynamics_and_invented(self):
        report = (
            "- 🔴 **рост страховых выплат** (−6190,72)\n"
        )
        res = validate_report(report, _enriched())
        classes = {e.error_class for e in res.errors}
        assert DYNAMICS_LANGUAGE in classes
        assert INVENTED_NUMBER in classes
        assert UNALLOWED_NAME in classes


class TestProdPattern4Narrative:
    """75a21db…: нарративная выдумка (Инкассация, «точки клиента»)."""

    def test_narrative_dynamics_and_number(self):
        report = (
            "## Краткое саммари\n"
            "Показатель «ОД до резервов»: факт 29,3 млрд, план 29,2 млрд. "
            "Вклад клиентов в отделениях вырос на 42,7 млн.\n"
        )
        res = validate_report(report, _enriched())
        classes = {e.error_class for e in res.errors}
        assert DYNAMICS_LANGUAGE in classes
        assert INVENTED_NUMBER in classes


class TestProdPattern5RepackedPlanFact:
    """797d34c…: план/факт узла выдан за драйвер («−12163 при плане −20,6»)."""

    def test_repacked_plan_fact(self):
        data = _enriched()
        # display.plan листового узла «Прочие чистые операционные доходы (МБ)» = "1 млн"
        report = (
            "- 🔴 **Прочие чистые операционные доходы (МБ)** — Главный драйвер — "
            "Прочие чистые операционные доходы (1 млн)\n"
        )
        res = validate_report(report, data)
        classes = {e.error_class for e in res.errors}
        assert REPACKED_PLAN_FACT in classes


class TestMarkers:

    def test_green_emoji_forbidden(self):
        report = "- 🟢 **ОД до резервов (УС)** — вклад -535,5 млн\n"
        res = validate_report(report, _enriched())
        classes = {e.error_class for e in res.errors}
        assert WRONG_MARKER in classes

    def test_marker_sign_mismatch(self):
        report = "- 🔴 **ОД до резервов (УС)** — вклад +535,5 млн\n"
        res = validate_report(report, _enriched())
        classes = {e.error_class for e in res.errors}
        assert WRONG_MARKER in classes


class TestWrongScale:

    def test_digit_loss_same_digits(self):
        """Прод-кейс: 29 213,6 млрд напечатано как «29213 млн»."""
        data = _enriched()
        report = "факт 29213 млн, план 29,2 млрд"
        res = validate_report(report, data)
        classes = {e.error_class for e in res.errors}
        assert WRONG_SCALE in classes


def _hyphen_data() -> dict:
    """Фикстура с дефисным именем и парой чисел ×10 (для FP-тестов)."""
    return {
        "data": [{
            "hieararchy_node": "Итог",
            "metric_type": "sum",
            "amounts": {"plan": 2e9, "fact": 1.7e9, "deviation": -3e8, "impact_to_top_lvl": -3e8},
            "details": {"type": "Детализация по компонентам иерархии", "top_factors": [
                {"hieararchy_node": "Инвестиционно-накопительное страхование",
                 "amounts": {"plan": 1e9, "fact": 0.8e9, "deviation": -2e8, "impact_to_top_lvl": -2e8}},
                {"hieararchy_node": "Брокерский бизнес",
                 "amounts": {"plan": 1e9, "fact": 1.1e9, "deviation": 1e8, "impact_to_top_lvl": 1e8}},
            ]},
        }],
        "plan_alias": "План", "fact_alias": "Факт", "sign_negative_impact": -1,
    }


class TestFalsePositiveFixes:
    """Регрессии ложных срабатываний, найденных на smoke A/B (прогон 2026-10-02)."""

    def test_typographic_minus_is_exact_quote(self):
        """«−200 млн» (U+2212) — та же цитата, что display «-200 млн».

        Соседний display ×10 («+100 млн») не должен затенять точное совпадение.
        """
        data = enrich_display(_hyphen_data())
        report = "Вклад −200 млн, компенсация +100 млн."
        res = validate_report(report, data)
        assert res.ok, [e.to_dict() for e in res.errors]

    def test_hyphen_name_not_split(self):
        """Дефис внутри имени («Инвестиционно-накопительное») — не разделитель."""
        data = enrich_display(_hyphen_data())
        report = (
            "*   🔴 **Инвестиционно-накопительное страхование** — вклад -200 млн\n"
            "*   ❇️ **брокерским бизнесом** — вклад +100 млн\n"
        )
        res = validate_report(report, data)
        assert res.ok, [e.to_dict() for e in res.errors]

    def test_inflected_name_allowed(self):
        """Падежная форма допустимого имени («брокерским бизнесом») — не выдумка."""
        data = enrich_display(_hyphen_data())
        report = "❇️ **брокерским бизнесом** — вклад +100 млн"
        res = validate_report(report, data)
        assert res.ok, [e.to_dict() for e in res.errors]

    def test_greedy_prefix_with_quoted_name(self):
        """Маркер внутри текста «(🔴). …по направлению «Имя»» — имя допустимо."""
        data = enrich_display(_hyphen_data())
        report = "Давление (🔴). Основное давление оказали результаты по направлению «Инвестиционно-накопительное страхование» (-200 млн)"
        res = validate_report(report, data)
        assert res.ok, [e.to_dict() for e in res.errors]

    def test_invented_name_still_caught(self):
        """Морфология не должна маскировать настоящие выдумки."""
        data = enrich_display(_hyphen_data())
        report = "🔴 **Страхование жизни и здоровья заёмщиков** — вклад -100 млн"
        res = validate_report(report, data)
        classes = {e.error_class for e in res.errors}
        assert UNALLOWED_NAME in classes
