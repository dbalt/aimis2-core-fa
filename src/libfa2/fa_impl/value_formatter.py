"""
value_formatter.py — детерминированное форматирование чисел ФА в display-строки
================================================================================

Уровень A (AIMIS-2173): числа в отчёте пишет код, LLM только цитирует готовые
строки. Чистая функция `enrich_display` обходит деревья входных данных и
добавляет в каждый узел объект `display` с готовыми строками:

    display = {
        "plan": ..., "fact": ..., "deviation": ..., "impact": ...,   # строки
        "marker": "🔴" | "❇️" | "",
        "significant": true | false,
        "margin_impact": ..., "margin_rub": ...,   # только ratio, depth <= 1
    }

Конфиг предвычислений (precompute_cfg, см. precompute_config.py) выбирает
для каждого поля режим code|llm: llm-ручка своё поле не генерирует
(numbers=llm — display не строится вовсе), threshold задаёт порог значимости.
По умолчанию всё считается кодом (текущее поведение).

Правила (единая семантика с table_renderer.py):
  - абсолютные величины: млрд (|v| >= 1 млрд) / млн / тыс. / руб. по |v|,
    группировка тысяч пробелом, десятичная запятая, суффикс всегда;
  - flg_rate_type=true: план/факт ×100 → %, отклонение ×100 → п.п.;
  - ratio-деревья: impact корня и прямых потомков ×100 → п.п.; глубже —
    вес impact_pp = (deviation / parent_deviation) * parent_impact_pp → п.п.,
    ровно как в детерминированной таблице; analytic_slice — абсолютные;
  - ненулевое значение НИКОГДА не округляется до нуля;
  - знак: обычный дефис "-", явный "+" у deviation/impact;
  - маркер по знаку impact с учётом sign_negative_impact;
  - значимость: |impact| >= threshold × максимума среди соседних узлов
    (threshold по умолчанию 0.30).
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

from .precompute_config import MODE_CODE, validate_precompute_cfg
from .table_renderer import _group_thousands


_MARKER_POS = "❇️"
_MARKER_NEG = "🔴"

_EPS = 1e-10


class _DisplayFlags(NamedTuple):
    """Какие поля display кладёт код (llm-ручки поля не генерируют)."""

    numbers: bool
    markers: bool
    selection: bool
    children: bool


def _fmt_decimal(av: float, decimals: int) -> str:
    """abs-число → строка с группировкой тысяч и десятичной запятой."""
    raw = f"{av:.{decimals}f}"
    if "." in raw:
        int_part, dec_part = raw.split(".")
        dec_part = dec_part.rstrip("0")
        if dec_part:
            return _group_thousands(int_part) + "," + dec_part
        return _group_thousands(int_part)
    return _group_thousands(raw)


def format_abs(v: Optional[float], signed: bool = False) -> str:
    """Абсолютная величина в руб.: млрд/млн/тыс./руб. по |v|.

    signed=True → явный знак +/- (для deviation/impact),
    signed=False → "-" только у отрицательных (для plan/fact).
    """
    if v is None:
        return ""
    if abs(v) < _EPS:
        return "0 руб."
    av = abs(v)
    if av >= 1e9:
        s = _fmt_decimal(av / 1e9, 1) + " млрд"
    elif av >= 1e6:
        s = _fmt_decimal(av / 1e6, 1) + " млн"
    elif av >= 1e3:
        s = _fmt_decimal(av / 1e3, 1) + " тыс."
    else:
        # < 1 тыс. — полностью в руб., с достаточной точностью
        s = "0"
        for d in (2, 3, 4, 5, 6, 7, 8):
            s = _fmt_decimal(av, d)
            if s != "0":
                break
        s = s + " руб."
    if v < 0:
        return "-" + s
    return ("+" + s) if signed else s


def format_percent(v: Optional[float], pp: bool = False, signed: bool = False) -> str:
    """×100 → проценты ("%") или процентные пункты ("п.п.").

    Точность — 3 знака с обрезкой нулей (как в таблице).
    signed=True → явный знак +/-; иначе "-" только у отрицательных.
    """
    if v is None:
        return ""
    suffix = " п.п." if pp else " %"
    if abs(v) < _EPS:
        return "0" + suffix
    s = _fmt_decimal(abs(v) * 100, 3)
    if v < 0:
        return "-" + s + suffix
    return ("+" + s + suffix) if signed else (s + suffix)


def _marker(impact: float, sign_negative_impact: int) -> str:
    """Маркер по знаку вклада с учётом инверсии негатива."""
    is_neg = (impact < 0) if sign_negative_impact == -1 else (impact > 0)
    if abs(impact) < _EPS:
        return ""
    return _MARKER_NEG if is_neg else _MARKER_POS


def _is_significant(impact_abs: float, sibling_impacts: List[float], threshold: float) -> bool:
    """|impact| >= threshold × максимум среди соседних узлов (одного родителя)."""
    m = max((abs(x) for x in sibling_impacts), default=0.0)
    if m < _EPS:
        return False
    return impact_abs >= threshold * m


def _impact_display(
        node: Dict,
        depth: int,
        ratio: bool,
        parent_ctx: Optional[Dict[str, float]],
) -> Tuple[str, float]:
    """Строка вклада + его числовая величина для сравнения значимости.

    Возвращает (display-строка, magnitude): для п.п. — значение в п.п.,
    для абсолютных — значение в руб. Соседи узла живут в тех же единицах,
    поэтому magnitude сравнима внутри уровня.
    """
    impact = float((node.get("amounts") or {}).get("impact_to_top_lvl", 0.0) or 0.0)
    if not ratio:
        return format_abs(impact, signed=True), impact
    if depth <= 1:
        # корень и прямые потомки: impact задан в долях → п.п.
        return format_percent(impact, pp=True, signed=True), impact * 100.0
    # глубже первого уровня: весовой пересчёт, как в таблице
    if parent_ctx and parent_ctx.get("deviation") and parent_ctx.get("impact_pp") is not None:
        deviation = float((node.get("amounts") or {}).get("deviation", 0.0) or 0.0)
        weight = deviation / parent_ctx["deviation"]
        impact_pp = weight * parent_ctx["impact_pp"]
        # impact_pp уже в п.п. — форматируем без повторного ×100
        if abs(impact_pp) < _EPS:
            return "0 п.п.", 0.0
        s = _fmt_decimal(abs(impact_pp), 3)
        sign = "-" if impact_pp < 0 else "+"
        return sign + s + " п.п.", impact_pp
    return format_abs(impact, signed=True), impact


def _display_for_node(
        node: Dict,
        depth: int,
        ratio: bool,
        sign_negative_impact: int,
        sibling_impacts: List[float],
        parent_ctx: Optional[Dict[str, float]],
        flags: _DisplayFlags,
        threshold: float,
) -> Tuple[Dict[str, Any], float]:
    """Собирает display-объект узла; возвращает его и magnitude вклада."""
    am = node.get("amounts") or {}
    rate = node.get("flg_rate_type") is True

    plan = am.get("plan")
    fact = am.get("fact")
    deviation = am.get("deviation")
    impact = am.get("impact_to_top_lvl")

    if rate:
        plan_s = format_percent(plan, pp=False, signed=False)
        fact_s = format_percent(fact, pp=False, signed=False)
        dev_s = format_percent(deviation, pp=True, signed=True)
    else:
        plan_s = format_abs(plan)
        fact_s = format_abs(fact)
        dev_s = format_abs(deviation, signed=True)

    impact_s, impact_magnitude = _impact_display(node, depth, ratio, parent_ctx)
    impact_val = float(impact or 0.0)

    display: Dict[str, Any] = {
        "plan": plan_s,
        "fact": fact_s,
        "deviation": dev_s,
        "impact": impact_s,
    }
    if flags.markers:
        display["marker"] = _marker(impact_val, sign_negative_impact)
    if flags.selection:
        display["significant"] = (
            True if depth == 0
            else _is_significant(abs(impact_magnitude), sibling_impacts, threshold)
        )
    if ratio and depth <= 1:
        display["margin_impact"] = impact_s
        display["margin_rub"] = dev_s
    return display, impact_magnitude


def _walk(
        node: Dict,
        depth: int,
        ratio: bool,
        sign_negative_impact: int,
        parent_ctx: Optional[Dict[str, float]],
        sibling_impacts: List[float],
        flags: _DisplayFlags,
        threshold: float,
) -> None:
    """Обход в глубину: display для узла и всех потомков (in-place).

    sibling_impacts — impacts узлов того же уровня (соседей данного узла).
    numbers=llm (мастер-режим) — display не строится вовсе.
    """
    display: Optional[Dict[str, Any]] = None
    impact_magnitude = 0.0
    if flags.numbers:
        display, impact_magnitude = _display_for_node(
            node, depth, ratio, sign_negative_impact, sibling_impacts,
            parent_ctx, flags, threshold,
        )
        node["display"] = display

    children: List[Dict] = (node.get("details") or {}).get("top_factors") or []
    if display is not None and flags.children:
        # белый список детей узла: «Главный драйвер» — только из этих имён
        child_names = [
            (c.get("hieararchy_node") or "").strip() for c in children
            if (c.get("hieararchy_node") or "").strip()
        ]
        if child_names:
            display["children_names"] = child_names
    child_impacts = [
        float((c.get("amounts") or {}).get("impact_to_top_lvl", 0.0) or 0.0)
        for c in children
    ]

    ctx: Optional[Dict[str, float]] = None
    if flags.numbers and ratio and depth >= 1:
        # для детей глубины >= 2: impact_pp родителя (в п.п.) и его deviation
        deviation = float((node.get("amounts") or {}).get("deviation", 0.0) or 0.0)
        if depth == 1:
            parent_pp = impact_magnitude
        else:
            parent_pp = impact_magnitude if display["impact"].endswith("п.п.") else None
        if parent_pp is not None:
            ctx = {"deviation": deviation, "impact_pp": parent_pp}

    for c in children:
        _walk(c, depth + 1, ratio, sign_negative_impact, ctx, child_impacts,
              flags, threshold)


def enrich_display(data: Dict, precompute_cfg: Optional[Dict[str, Any]] = None) -> Dict:
    """Чистая функция: data → data_display (deep copy + display-объекты).

    data — словарь вида {"data": [tree, ...], ...} (как в summarize()).
    precompute_cfg — конфиг предвычислений (None → дефолт: всё кодом).
    Возвращает копию, где каждый узел каждого дерева дополнен `display`;
    llm-ручки конфига исключают свои поля из display (numbers=llm — весь
    display, markers — marker, selection — significant, names.children —
    children_names).
    """
    cfg = validate_precompute_cfg(precompute_cfg)
    flags = _DisplayFlags(
        numbers=cfg["numbers"]["mode"] == MODE_CODE,
        markers=cfg["markers"]["mode"] == MODE_CODE,
        selection=cfg["selection"]["mode"] == MODE_CODE,
        children=cfg["names"]["children"] == MODE_CODE,
    )
    threshold = float(cfg["selection"]["threshold"])
    out = copy.deepcopy(data)
    trees: List[Dict] = out.get("data") or []
    metric_type = trees[0].get("metric_type") if trees else None
    ratio = metric_type == "ratio"
    sign_negative_impact = out.get("sign_negative_impact", -1)
    for tree in trees:
        tree_impact = float((tree.get("amounts") or {}).get("impact_to_top_lvl", 0.0) or 0.0)
        _walk(tree, 0, ratio, sign_negative_impact, None, [tree_impact],
              flags, threshold)
    return out


def collect_allowed_names(data: Dict) -> List[str]:
    """Белый список имён для промпта (AIMIS-2173, итерация «allowed_names»).

    Все hieararchy_node + значения analytic_slice в порядке обхода, без дублей.
    LLM разрешается упоминать ТОЛЬКО эти имена — источник «выдуманных
    подфакторов» (типовая структура P&L банка) отсекается по данным.
    """
    seen: set = set()
    out: List[str] = []

    def _walk_names(nodes: List[Dict]) -> None:
        for n in nodes:
            name = (n.get("hieararchy_node") or "").strip()
            if name and name not in seen:
                seen.add(name)
                out.append(name)
            for v in (n.get("analytic_slice") or {}).values():
                s = str(v).strip()
                if s and s not in seen:
                    seen.add(s)
                    out.append(s)
            _walk_names((n.get("details") or {}).get("top_factors") or [])

    _walk_names(data.get("data") or [])
    return out
