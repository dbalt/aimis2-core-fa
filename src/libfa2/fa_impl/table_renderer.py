# ===========================================================================
#     Д Е Т Е Р М И Н И Р О В А Н Н Ы Й   Р Е Н Д Е Р   Т А Б Л И Ц Ы  (без LLM)
# ===========================================================================
# Воспроизводит формат, который раньше формировал TABLE_PROMPT: один заголовок
# `###`, одна сплошная таблица из 5 колонок, обход в глубину, строки-разделители
# `*↳ по …*`, отступы &emsp;, подавление дубля имени показателя, жирный новый
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


def _format_number(v: float, scale: float, component_type: Optional[str] = None, as_percentage: bool = False) -> str:
    """
    Форматирует число с динамическим suffix.

    Базовая шкала — млн. В ячейках suffix меняется для малых значений:
      - |v| >= 1 млн → без suffix (контекст из шапки)
      - |v| < 1 млн → "тыс." с достаточной точностью (никогда не обнуляем)

    Для rate/ratio — всегда проценты.
    Никогда не округляет ненулевое число до нуля.
    """
    if v is None:
        return ""

    # --- Проценты (rate, ratio) ---
    if as_percentage:
        s = f"{abs(v) * 100:.3f}".replace(".", ",")
        sign = "-" if v < 0 else ""
        return sign + s.rstrip('0').rstrip(',') + "%"

    if 0 < abs(v) < 1 and not as_percentage:
        s = f"{abs(v) * 100:.3f}".replace(".", ",")
        sign = "-" if v < 0 else ""
        return sign + s.rstrip('0').rstrip(',') + "%"

    # --- Ноль ---
    if abs(v) < 1e-10:
        return "0,0"

    # --- Определяем suffix и точность по абсолютному значению ---
    abs_v = abs(v)

    if abs_v >= 1_000_000:
        decimals = 1
        suffix = ""
        scale_factor = 1_000_000
    else:
        # Все числа < 1 млн — форматируем в тысячах с достаточной точностью
        # Чтобы не терять мелкие числа: 1 руб. = 0.001 тыс., 500 руб. = 0.5 тыс.
        suffix = "тыс."
        scale_factor = 1_000
        # Считаем сколько знаков нужно:
        # Если scaled < 0.01 → 4 знака, < 0.1 → 3 знака, < 1 → 2 знака
        raw_scaled = abs(v) / scale_factor
        if raw_scaled < 0.01:
            decimals = 4
        elif raw_scaled < 0.1:
            decimals = 3
        elif raw_scaled < 1:
            decimals = 2
        else:
            decimals = 2

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


def _t_amount(v: float, scale: float, flg_rate_type: Optional[bool] = None) -> str:
    """План/Факт с динамическим масштабированием. Для rate/ratio показываем как проценты."""
    # Для rate/ratio показываем как проценты, иначе используем автоматическое определение
    as_percentage = flg_rate_type is True
    return _format_number(v, scale, None, as_percentage=as_percentage)


def _t_impact(v: float, scale: float) -> str:
    """Влияние с динамическим масштабом и знаком: + / − / 0,0."""
    if not v:
        return "0,0"
    return _format_number(v, scale, None, as_percentage=False)


def _impact_cell(v: float, bold: bool, scale: float, flg_rate_type: Optional[bool] = None) -> str:
    txt = _t_impact(v, scale)
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

    # Базовый масштаб — всегда миллион (используется в _format_number как аргумент scale,
    # но _format_number сам определяет реальный масштаб по abs(v))
    scale_factor = 1_000_000

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

        # flg_rate_type берётся с текущего узла
        flg_rate_type = node.get("flg_rate_type")

        rows.append(
            f"| {num} | {_path_cell(node, depth, parent)} "
            f"| {_t_amount(base_val, scale_factor, flg_rate_type)} | {_t_amount(am.get('fact'), scale_factor, flg_rate_type)} "
            f"| {_impact_cell(_impact(node), bold_infl, scale_factor)} |"
        )
        if has_children:
            dtype = (node.get("details") or {}).get("type") or ""
            rows.append(f"|   | {'.&emsp;' * depth}{_sep_label(dtype)} | | | |")
            for c in children:
                walk(c, depth + 1, node, len(children) == 1)

    for ti, tree in enumerate(trees):
        if ti > 0:
            rows.append("|   | | | | |")          # разделитель между деревьями
        walk(tree, 0, None, False)

    plan_label = data.get("plan_alias") or trees[0].get("plan_alias") or "План"
    fact_label = data.get("fact_alias") or trees[0].get("fact_alias") or "Факт"

    # Фиксированный заголовок — всегда "млн руб."
    head = (f"### Детализация факторного анализа отклонений: "
            f"{_clean_name(trees[0].get('hieararchy_node', ''))}\n\n"
            f"| # | Путь разложения | {plan_label}, млн руб. | {fact_label}, млн руб. | Влияние, млн руб. |\n"
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