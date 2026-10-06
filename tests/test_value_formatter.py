"""Unit-тесты value_formatter — детерминированное форматирование display-строк.

Проверяют:
1. Правила масштабирования (млрд/млн/тыс./руб.), группировку, запятую, знаки
2. Red-кейсы прод-инцидентов (потеря разряда «29213 млн», «1 105 млн»)
3. Проценты/п.п. для flg_rate_type и ratio-деревьев (по глубине)
4. Маркеры и флаг значимости
5. Детерминированность enrich_display и отсутствие мутации входа
"""

from __future__ import annotations

import copy

from src.libfa2.fa_impl.value_formatter import enrich_display, format_abs, format_percent, collect_allowed_names


class TestFormatAbs:

    def test_billion_scale(self):
        """|v| >= 1 млрд → млрд, 1 знак, без потери разряда."""
        assert format_abs(11047180942.92) == "11 млрд"

    def test_red_case_29213_billion(self):
        """Прод-инцидент: 29 213 553 млн → «29 213,6 млрд», а НЕ «29213 млн»."""
        assert format_abs(29213553000000.0) == "29 213,6 млрд"

    def test_million_scale(self):
        assert format_abs(535475430.4) == "535,5 млн"
        assert format_abs(1500000.0) == "1,5 млн"

    def test_thousand_scale(self):
        assert format_abs(500000.0) == "500 тыс."

    def test_rubles_small_never_round_to_zero(self):
        assert format_abs(5.0) == "5 руб."
        assert format_abs(0.005) == "0,01 руб."
        assert format_abs(0.001) == "0,001 руб."

    def test_zero_and_none(self):
        assert format_abs(0.0) == "0 руб."
        assert format_abs(None) == ""

    def test_signs(self):
        assert format_abs(-535475430.4) == "-535,5 млн"
        assert format_abs(300000.0, signed=True) == "+300 тыс."
        assert format_abs(-300000.0, signed=True) == "-300 тыс."


class TestFormatPercent:

    def test_percent(self):
        assert format_percent(2.0) == "200 %"
        assert format_percent(1.78) == "178 %"
        assert format_percent(-0.00121) == "-0,121 %"
        assert format_percent(-0.0078) == "-0,78 %"

    def test_pp_signed(self):
        assert format_percent(-0.217, pp=True, signed=True) == "-21,7 п.п."
        assert format_percent(0.00123, pp=True, signed=True) == "+0,123 п.п."

    def test_zero(self):
        assert format_percent(0.0, pp=True, signed=True) == "0 п.п."
        assert format_percent(None) == ""


def _non_ratio_data() -> dict:
    """Фрагмент bsp-примера: ОД до резервов по каналу УС (не ratio)."""
    return {
        "data": [
            {
                "hieararchy_node": "ОД до резервов",
                "metric_type": "base",
                "amounts": {
                    "plan": 29246651050.66,
                    "fact": 29338006012.54,
                    "deviation": 91354961.89,
                    "impact_to_top_lvl": 91354961.89,
                },
                "details": {
                    "type": "Детализация по: [Канал]",
                    "top_factors": [
                        {
                            "hieararchy_node": "ОД до резервов",
                            "analytic_slice": {"Канал": "УС"},
                            "amounts": {
                                "plan": 10075473914.48,
                                "fact": 9539998484.09,
                                "deviation": -535475430.4,
                                "impact_to_top_lvl": -535475430.4,
                            },
                            "details": {"top_factors": []},
                        },
                        {
                            "hieararchy_node": "Прочие чистые операционные доходы",
                            "analytic_slice": {"Канал": "МБ"},
                            "amounts": {
                                "plan": 1000000.0,
                                "fact": 1125146170.15,
                                "deviation": 125146170.15,
                                "impact_to_top_lvl": 125146170.15,
                            },
                            "details": {"top_factors": []},
                        },
                        {
                            "hieararchy_node": "Расчёты за устройства самообслуживания",
                            "analytic_slice": {"Канал": "УС"},
                            "amounts": {
                                "plan": 900000.0,
                                "fact": 160621600.55,
                                "deviation": -660621600.55,
                                "impact_to_top_lvl": -660621600.55,
                            },
                            "details": {"top_factors": []},
                        },
                    ],
                },
            }
        ]
    }


def _ratio_data() -> dict:
    """Ratio-дерево (COR): flg_rate_type у корня, абсолютные суммы у потомка."""
    return {
        "data": [
            {
                "hieararchy_node": "Стоимость риска (COR)",
                "metric_type": "ratio",
                "flg_rate_type": True,
                "amounts": {
                    "plan": 2.0,
                    "fact": 1.78,
                    "deviation": -0.217,
                    "impact_to_top_lvl": -0.217,
                },
                "details": {
                    "top_factors": [
                        {
                            "hieararchy_node": "Кредитный портфель",
                            "amounts": {
                                "plan": 2000000.0,
                                "fact": 2300000.0,
                                "deviation": 300000.0,
                                "impact_to_top_lvl": -0.26413043,
                            },
                            "details": {
                                "top_factors": [
                                    {
                                        "hieararchy_node": "Розничный сегмент",
                                        "analytic_slice": {"Сегмент": "Розница"},
                                        "amounts": {
                                            "plan": 100000.0,
                                            "fact": -150000.0,
                                            "deviation": -250000.0,
                                            "impact_to_top_lvl": -0.1,
                                        },
                                        "details": {"top_factors": []},
                                    }
                                ]
                            },
                        }
                    ]
                },
            }
        ]
    }


class TestEnrichDisplayNonRatio:

    def setup_method(self):
        self.out = enrich_display(_non_ratio_data())
        self.root = self.out["data"][0]
        self.children = self.root["details"]["top_factors"]

    def test_root_display(self):
        d = self.root["display"]
        assert d["plan"] == "29,2 млрд"
        assert d["fact"] == "29,3 млрд"
        assert d["deviation"] == "+91,4 млн"
        assert d["impact"] == "+91,4 млн"
        assert d["marker"] == "❇️"
        assert d["significant"] is True

    def test_markers_match_sign(self):
        assert self.children[0]["display"]["marker"] == "🔴"
        assert self.children[1]["display"]["marker"] == "❇️"
        assert self.children[2]["display"]["marker"] == "🔴"

    def test_significance_threshold_30_percent(self):
        """|impact| >= 30% максимума среди соседей → значимый."""
        sig = [c["display"]["significant"] for c in self.children]
        # |−535,5| и |−660,6| >= 30% от 660,6; |125,1| — нет
        assert sig == [True, False, True]

    def test_impact_strings_are_quotes(self):
        assert self.children[0]["display"]["impact"] == "-535,5 млн"
        assert self.children[1]["display"]["impact"] == "+125,1 млн"
        assert self.children[2]["display"]["impact"] == "-660,6 млн"


class TestEnrichDisplayRatio:

    def setup_method(self):
        self.out = enrich_display(_ratio_data())
        self.root = self.out["data"][0]
        self.child = self.root["details"]["top_factors"][0]
        self.grandchild = self.child["details"]["top_factors"][0]

    def test_root_rate_percent_and_pp(self):
        d = self.root["display"]
        assert d["plan"] == "200 %"
        assert d["fact"] == "178 %"
        assert d["deviation"] == "-21,7 п.п."
        assert d["impact"] == "-21,7 п.п."

    def test_direct_child_impact_in_pp(self):
        """Прямой потомок корня ratio: impact ×100 → п.п., суммы абсолютные."""
        d = self.child["display"]
        assert d["impact"] == "-26,413 п.п."
        assert d["plan"] == "2 млн"
        assert d["fact"] == "2,3 млн"
        assert d["deviation"] == "+300 тыс."

    def test_margin_pair_for_direct_child(self):
        """Пара для формулировки маржи: п.п. + рублёвый эквивалент."""
        d = self.child["display"]
        assert d["margin_impact"] == "-26,413 п.п."
        assert d["margin_rub"] == "+300 тыс."

    def test_deep_node_weighted_pp_like_table(self):
        """Глубина >= 2: весовой пересчёт п.п. как в таблице.

        weight = -250000 / 300000; impact_pp = weight * (-26,413) → +22,011 п.п.
        """
        assert self.grandchild["display"]["impact"] == "+22,011 п.п."


class TestDeterminism:

    def test_repeated_calls_identical(self):
        data = _non_ratio_data()
        assert enrich_display(data) == enrich_display(data)

    def test_input_not_mutated(self):
        data = _ratio_data()
        snapshot = copy.deepcopy(data)
        enrich_display(data)
        assert data == snapshot


class TestCollectAllowedNames:
    """Белый список имён для промпта (allowed_names, AIMIS-2173)."""

    def test_collects_all_nodes_and_slices_dedup(self):
        data = {
            "data": [{
                "hieararchy_node": "Корень",
                "details": {"top_factors": [
                    {"hieararchy_node": "Инвестиционно-накопительное страхование",
                     "analytic_slice": {"Сегмент": "Крупный бизнес"}},
                    {"hieararchy_node": "Корень"},  # дубль
                ]},
            }],
        }
        names = collect_allowed_names(data)
        assert names == ["Корень", "Инвестиционно-накопительное страхование", "Крупный бизнес"]

    def test_empty_data(self):
        assert collect_allowed_names({"data": []}) == []


class TestChildrenNames:
    """display.children_names — белый список детей для правила «Главный драйвер»."""

    def test_children_names_present_for_parent(self):
        data = _non_ratio_data()
        out = enrich_display(data)
        root = out["data"][0]
        assert root["display"]["children_names"] == [
            "ОД до резервов", "Прочие чистые операционные доходы",
            "Расчёты за устройства самообслуживания",
        ]

    def test_children_names_absent_for_leaf(self):
        data = _non_ratio_data()
        out = enrich_display(data)
        leaf = out["data"][0]["details"]["top_factors"][0]
        assert "children_names" not in leaf["display"]
