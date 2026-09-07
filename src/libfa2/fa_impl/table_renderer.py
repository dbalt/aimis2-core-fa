# ===========================================================================
#     Д Е Т Е Р М И Н И Р О В А Н Н Ы Й   Р Е Н Д Е Р   Т АБЛИЦЫ  (без LLM)
# ===========================================================================
# Воспроизводит формат, который раньше формировал TABLE_PROMPT: один заголовок
# `###`, одна сплошная таблица из 5 колонок, обход в глубину, строки-разделители
# `*↳ по …*`, обдеты &emsp;, подавление дубля имени показателя, жирный новый
# разрез, маркеры 🔴/🟢 в колонке «Влияние», динамические числа.
import re
from typing import Optional, Dict, List, Tuple


NULL_SLICE_LABEL = "без распределения"   # как показывать значение разреза = null
SEP_COMPONENTS = "*↳ по компонентам иерархии*"   # ярлык разделителя для компонент


def _group_thousands(num_str: str) -> str:
    """Группирует цифры целого числа по тройки, разделяя пробелами."""
    num_str = num_str.lstrip('-')
    rev = num_str[::-1]
    chunks = [rev[i:i+3] for i in range(0, len(rev), 3)]
    return ' '.join(chunks)[::-1]


def _clean_name(s) -> str:
    if not s:
        return "" if s is None else str(s)
    return re.sub(r"\s*(?:ур\.?|уровень|лвл|lvl)\s*\d+\b", "", str(s), flags=re.IGNORECASE).strip()


def _impact(node: Dict) -> float:
    return float(node.get("amounts", {}).get("impact_to_top_lvl", 0.0) or 0.0)


def _infer_scale(values: List[float]) -> Tuple[float, str, str]:
    """
    Определяет оптимальный масштаб для всей таблицы на основе распределения значений.

    УСТАРЕЛО: теперь всегда используется миллионный масштаб.
    Оставлен для обратной совместимости, но всегда возвращает млн.
    """
    return 1_000_000, "млн", "млн руб."


def _format_number(
    v: float,
    scale: float,
    component_type: Optional[str] = None,
    as_percentage: bool = False,
    node_type: Optional[str] = None,
) -> str:
    """
    Форматирует число с динамическим suffix.

    Базовая шкала — млн. В ячейках suffix меняется для малых значений:
      - |v| >= 1 млн → без suffix (контекст из шапки)
      - |v| < 1 млн → "тыс." с достаточной точностью (никогда не обнуляем)

    Для rate/ratio — всегда проценты.
    Для ratio-узлов проценты форматируются как п.п. (процентные пункты).
    Никогда не округляет ненулевое число до нуля.
    """
    if v is None:
        return ""

    # --- Проценты (rate, ratio) ---
    if as_percentage:
        pct_suffix = "п.п." if node_type == "ratio" else "%"
        s = f"{abs(v) * 100:.3f}".replace(".", ",")
        sign = "-" if v < 0 else ""
        return sign + s.rstrip('0').rstrip(',') + " " + pct_suffix

    if 0 < abs(v) < 1 and not as_percentage:
        pct_suffix = "п.п." if node_type == "ratio" else "%"
        s = f"{abs(v) * 100:.3f}".replace(".", ",")
        sign = "-" if v < 0 else ""
        return sign + s.rstrip('0').rstrip(',') + " " + pct_suffix

    # --- Ноль ---
    if abs(v) < 1e-10:
        return "0,0"

    # --- Определяем suffix и точность по абсолютному значению ---
    abs_v = abs(v)

    if abs_v >= 1_000_000:
        decimals = 1
        suffix = "млн"  # Рекомендую добавить "млн" для ясности, вместо пустой строки ""
        scale_factor = 1_000_000

    elif abs_v >= 1_000:
        # Числа от 1 000 до 999 999 — форматируем в тысячах, округление до 1 знака
        suffix = "тыс."
        scale_factor = 1_000
        decimals = 1

    else:
        # Все числа < 1 000 — форматируем как есть (в рублях)
        suffix = "руб."
        scale_factor = 1
        decimals = 1  # Можно поставить 0, если копейки для целых рублей не нужны

    # if abs_v >= 1_000_000:
    #     decimals = 1
    #     suffix = ""
    #     scale_factor = 1_000_000
    # else:
    #     # Все числа < 1 млн — форматируем в тысячах, округление до 1 знака
    #     suffix = "тыс."
    #     scale_factor = 1_000
    #     decimals = 1

    scaled = v / scale_factor

    # --- Форматируем число ---
    raw = f"{abs(scaled):.{decimals}f}"
    if '.' in raw:
        int_part, dec_part = raw.split('.')
        dec_part = dec_part.rstrip('0')
        if dec_part:
            formatted = _group_thousands(int_part) + ',' + dec_part
        else:
            formatted = _group_thousands(int_part)
    else:
        formatted = _group_thousands(raw)

    # --- Собираем ---
    if suffix:
        result = f"{formatted} {suffix}"
    else:
        result = formatted

    sign = "-" if v < 0 else ""
    return sign + result


def _t_amount(
    v: float,
    scale: float,
    flg_rate_type: Optional[bool] = None,
    node_type: Optional[str] = None,
) -> str:
    """План/Факт с динамическим масштабированием. Для rate/ratio показываем как проценты."""
    as_percentage = flg_rate_type is True
    return _format_number(v, scale, None, as_percentage=as_percentage, node_type=node_type)


def _t_impact(
    v: float,
    scale: float,
    flg_rate_type: Optional[bool] = None,
    node_type: Optional[str] = None,
) -> str:
    """Влияние с динамическим масштабом и знаком: + / − / 0,0."""
    if not v:
        return "0,0"
    as_percentage = flg_rate_type is True
    return _format_number(v, scale, None, as_percentage=as_percentage, node_type=node_type)

def _impact_cell(
    v: float,
    bold: bool,
    scale: float,
    flg_rate_type: Optional[bool] = None,
    node_type: Optional[str] = None,
    sign_negative_impact: int = -1,
) -> str:
    txt = _t_impact(v, scale, flg_rate_type, node_type=node_type)
    if bold:
        txt = f"**{txt}**"
    # Определяем негативность с учётом sign_negative_impact
    is_neg = (v > 0) if sign_negative_impact == -1 else (v < 0)
    marker = "🔴 " if is_neg else ("🟢 " if v != 0 else "")
    return marker + txt


def _format_pp(v: float, bold: bool, sign_negative_impact: int = -1) -> str:
    """Форматирует уже вычисленное влияние в п.п. (deviation/parent_deviation * parent_impact_pp)."""
    if abs(v) < 1e-10:
        txt = "0,0"
    else:
        sign = "-" if v < 0 else "+"
        txt = sign + f"{abs(v):.3f}".replace(".", ",") + " п.п."
    if bold:
        txt = f"**{txt}**"
    is_neg = (v > 0) if sign_negative_impact == -1 else (v < 0)
    marker = "🔴 " if is_neg else ("🟢 " if v != 0 else "")
    return marker + txt


def _sep_label(dtype: str) -> str:
    if "компонент" in dtype:
        return SEP_COMPONENTS
    m = re.search(r"\[(.+?)\]", dtype)
    if m:
        return f"*↳ по {_clean_name(m.group(1))}*"
    return SEP_COMPONENTS


def _path_cell(node: Dict, depth: int, parent: Optional[Dict]) -> str:
    indent = ".&emsp;" * depth
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

    # Базовый масштаб — всегда миллион
    scale_factor = 1_000_000

    # Получаем sign_negative_impact (по умолчанию -1)
    sign_negative_impact = data.get("sign_negative_impact", -1)

    # Определяем тип метрики корня (для всех деревьев одинаковый)
    root_metric_type = trees[0].get("metric_type")

    counter = [0]
    rows: List[str] = []

    def walk(
        node: Dict,
        depth: int,
        parent: Optional[Dict],
        is_single: bool,
        _inherit_type: Optional[str] = None,
        _parent_impact_pp: Optional[float] = None,
        _parent_deviation: Optional[float] = None,
    ) -> None:
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

        flg_rate_type = node.get("flg_rate_type")
        # Если узел не определяет свой metric_type — наследуем от родителя/корня
        metric_type = node.get("metric_type") or _inherit_type

        # Для ratio-метрик глубины >= 2: weight = deviation / parent_deviation
        # impact_pp = weight * parent_impact_pp
        node_impact = _impact(node)
        formatted_impact_txt: str

        if metric_type == "ratio" and depth >= 2 and _parent_impact_pp is not None and _parent_deviation is not None and _parent_deviation != 0:
            deviation = float(am.get("deviation") or 0)
            weight = deviation / _parent_deviation
            impact_pp = weight * _parent_impact_pp
            formatted_impact_txt = _format_pp(impact_pp, bold_infl, sign_negative_impact)
        else:
            formatted_impact_txt = _impact_cell(node_impact, bold_infl, scale_factor, flg_rate_type, metric_type, sign_negative_impact)

        rows.append(
            f"| {num} | {_path_cell(node, depth, parent)} "
            f"| {_t_amount(base_val, scale_factor, flg_rate_type)} | "
            f"{_t_amount(am.get('fact'), scale_factor, flg_rate_type)} "
            f"| {formatted_impact_txt} |"
        )
        if has_children:
            dtype = (node.get("details") or {}).get("type") or ""
            rows.append(f"|   | {'.&emsp;' * depth}{_sep_label(dtype)} | | | |")
            # Передаём parent_deviation и parent_impact_pp потомкам
            parent_deviation = float(am.get("deviation") or 0)
            for c in children:
                walk(c, depth + 1, node, len(children) == 1,
                     _inherit_type=metric_type,
                     _parent_impact_pp=node_impact * 100 if metric_type == "ratio" else None,
                     _parent_deviation=parent_deviation)

    for ti, tree in enumerate(trees):
        if ti > 0:
            rows.append("|   | | | | |")          # разделитель между деревьями
        walk(tree, 0, None, False, _inherit_type=root_metric_type)

    plan_label = data.get("plan_alias") or trees[0].get("plan_alias") or "План"
    fact_label = data.get("fact_alias") or trees[0].get("fact_alias") or "Факт"

    # Суффикс единиц — только для ratio его нет (там проценты/п.п.)
    unit = ", млн руб." if root_metric_type != "ratio" else ""
    head = (f"### Детализация факторного анализа отклонений: "
            f"{_clean_name(trees[0].get('hieararchy_node', ''))}\n\n"
            f"| # | Структура факторов | {plan_label}{unit} | {fact_label}{unit} | Влияние{unit} |\n"
            f"|---|----------------|----------:|----------:|----------------:|\n")
    return head + "\n".join(rows)


async def render_factor_table_wrapper(data):
    try:
        table_res = await render_factor_table(data)
        return {"table":table_res,"ex": None}
    except Exception as e:
        return {"table":None,"ex":str(e)}


def _get_scale_info(data: Dict) -> Dict:
    """
    Возвращает информацию о масштабе для промптов.
    Всегда: миллионный масштаб.
    """
    return {
        "scale": "млн",
        "scale_full": "млн руб.",
        "scale_factor": 1_000_000
    }
