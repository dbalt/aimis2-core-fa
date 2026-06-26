# ===========================================================================
#     Д Е Т Е Р М И Н И Р О В А Н Н Ы Й   Р Е Н Д Е Р   Т А Б Л И Ц Ы  (без LLM)
# ===========================================================================
# Воспроизводит формат, который раньше формировал TABLE_PROMPT: один заголовок
# `###`, одна сплошная таблица из 5 колонок, обход в глубину, строки-разделители
# `*↳ по …*`, отступы &emsp;, подавление дубля имени показателя, жирный новый
# разрез, маркеры 🔴/🟢 в колонке «Влияние», динамические числа.
import re
from typing import Optional, Dict, List


NULL_SLICE_LABEL = "без распределения"   # как показывать значение разреза = null
SEP_COMPONENTS = "*↳ по компонентам иерархии*"   # ярлык разделителя для компонент


def _clean_name(s) -> str:
    if not s:
        return "" if s is None else str(s)
    return re.sub(r"\s*(?:ур\.?|уровень|лвл|lvl)\s*\d+\b", "", str(s), flags=re.IGNORECASE).strip()


def _impact(node: Dict) -> float:
    return float(node.get("amounts", {}).get("impact_to_top_lvl", 0.0) or 0.0)


def _t_amount(v) -> str:
    """План/Факт в млн (минус — обычный дефис; ставки |v|<1 → проценты)."""
    if v is None:
        return ""
    if 0 < abs(v) < 1:                                   # ставка/доля
        return f"{v * 100:.3f}".replace(".", ",") + "%"
    n = abs(v) / 1e6
    s = f"{n:,.1f}".replace(",", " ").replace(".", ",")
    return ("-" if v < 0 else "") + s


def _t_impact(v: float) -> str:
    """Влияние в млн со знаком: + / − (длинное тире) / 0,0; ставки → проценты."""
    if not v:
        return "0,0"
    if 0 < abs(v) < 1:
        return ("−" if v < 0 else "+") + f"{abs(v) * 100:.3f}".replace(".", ",") + "%"
    n = abs(v) / 1e6
    s = f"{n:,.1f}".replace(",", " ").replace(".", ",")
    return ("−" if v < 0 else "+") + s


def _impact_cell(v: float, bold: bool) -> str:
    txt = _t_impact(v)
    if bold:
        txt = f"**{txt}**"
    marker = "🔴 " if v < 0 else ("🟢 " if v > 0 else "")
    return marker + txt


def _sep_label(dtype: str) -> str:
    if "компонент" in dtype:
        return SEP_COMPONENTS
    m = re.search(r"\[(.+?)\]", dtype)
    if m:
        return f"*↳ по {_clean_name(m.group(1))}*"
    return SEP_COMPONENTS


def _path_cell(node: Dict, depth: int, parent: Optional[Dict]) -> str:
    indent = "&emsp;" * depth
    name = _clean_name(node.get("hieararchy_node", ""))

    # Часть 1 — название показателя
    if depth == 0:
        part1 = f"**{name}**"                            # корень — жирным
    else:
        part1 = name
        ptype = ((parent.get("details") or {}).get("type") or "") if parent else ""
        if ptype.startswith("Детализация по:") and \
                _clean_name(parent.get("hieararchy_node", "")) == name:
            part1 = ""                                   # подавление дубля имени

    # Часть 2 — значения аналитических разрезов
    parent_keys = set((parent.get("analytic_slice") or {}).keys()) if parent else set()
    parts2 = []
    for k, v in (node.get("analytic_slice") or {}).items():
        val = _clean_name(v) if v is not None else NULL_SLICE_LABEL
        parts2.append(f"**{val}**" if k not in parent_keys else val)   # новый разрез — жирным

    segs = ([part1] if part1 else []) + parts2
    if not segs:
        segs = [name]
    return indent + " \\| ".join(segs)


async def render_factor_table(data: Dict) -> str:
    """JSON → markdown-таблица детализации (тот же формат, что давал TABLE_PROMPT)."""
    trees = data.get("data") or []
    if not trees:
        return ""

    counter = [0]
    rows: List[str] = []

    def walk(node: Dict, depth: int, parent: Optional[Dict], is_single: bool) -> None:
        children = (node.get("details") or {}).get("top_factors") or []
        has_children = len(children) > 0
        am = node.get("amounts") or {}
        base_val = am.get("plan")
        if base_val is None:
            for f in ("prognoz", "benchmark", "fact_appg"):
                if am.get(f) is not None:
                    base_val = am[f]
                    break
        num = " " if depth == 0 else str(counter.__setitem__(0, counter[0] + 1) or counter[0])
        bold_infl = has_children or is_single or depth == 0
        rows.append(
            f"| {num} | {_path_cell(node, depth, parent)} "
            f"| {_t_amount(base_val)} | {_t_amount(am.get('fact'))} "
            f"| {_impact_cell(_impact(node), bold_infl)} |"
        )
        if has_children:
            dtype = (node.get("details") or {}).get("type") or ""
            rows.append(f"|   | {'&emsp;' * depth}{_sep_label(dtype)} | | | |")
            for c in children:
                walk(c, depth + 1, node, len(children) == 1)

    for ti, tree in enumerate(trees):
        if ti > 0:
            rows.append("|   | | | | |")          # разделитель между деревьями
        walk(tree, 0, None, False)

    head = (f"### Детализация факторного анализа отклонений: "
            f"{_clean_name(trees[0].get('hieararchy_node', ''))}\n\n"
            f"| # | Путь разложения | План, млн | Факт, млн | Влияние, млн |\n"
            f"|---|----------------|----------:|----------:|----------------:|\n")
    return head + "\n".join(rows)


async def render_factor_table_wrapper(data):
    try:
        table_res = await render_factor_table(data)
        return {"table":table_res,"ex": None}
    except Exception as e:
        return {"table":None,"ex":str(e)}