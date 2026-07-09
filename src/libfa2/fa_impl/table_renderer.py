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


def _clean_name(s) -> str:
    if not s:
        return "" if s is None else str(s)
    return re.sub(r"\s*(?:ур\.?|уровень|лвл|lvl)\s*\d+\b", "", str(s), flags=re.IGNORECASE).strip()


def _impact(node: Dict) -> float:
    return float(node.get("amounts", {}).get("impact_to_top_lvl", 0.0) or 0.0)


def _infer_scale(values: List[float]) -> Tuple[float, str, str]:
    """
    Определяет оптимальный масштаб для всей таблицы на основе распределения значений.
    
    Использует медиану и процент значений в каждом диапазоне для выбора масштаба:
    - Если большинство значений (>= 60%) < 1 млн, выбираем млн
    - Если большинство значений < 1 тыс., выбираем тыс.
    - Иначе выбираем млрд
    
    Возвращает:
        (scale_factor, suffix_short, suffix_full)
        например: (1_000_000_000, "млрд", "млрд руб.")
    """
    # Фильтруем ненулевые значения
    non_zero_values = [abs(v) for v in values if v]
    if not non_zero_values:
        return 1_000_000, "млн", "млн руб."
    
    n = len(non_zero_values)
    
    # Считаем, сколько значений в каждом диапазоне
    count_rub = sum(1 for v in non_zero_values if v < 1_000)
    count_thou = sum(1 for v in non_zero_values if 1_000 <= v < 1_000_000)
    count_mln = sum(1 for v in non_zero_values if 1_000_000 <= v < 1_000_000_000)
    count_mld = sum(1 for v in non_zero_values if v >= 1_000_000_000)
    
    # Логика выбора масштаба:
    # 1. Если >= 60% значений < 1 тыс. → используем тыс. или руб.
    # 2. Если >= 60% значений < 1 млн → используем млн
    # 3. Если >= 60% значений < 1 млрд → используем млрд
    # 4. Иначе (много очень больших значений) → используем млрд
    
    threshold = n * 0.6  # 60% значений
    
    if count_rub >= threshold:
        # Большинство < 1 тыс.
        if count_mln + count_mld > 0:
            return 1_000, "тыс.", "тыс. руб."
        else:
            return 1.0, "руб.", "руб."
    elif count_thou >= threshold:
        # Большинство в диапазоне тыс.
        return 1_000, "тыс.", "тыс. руб."
    elif count_mln >= threshold:
        # Большинство < 1 млн
        return 1_000_000, "млн", "млн руб."
    elif count_mld >= threshold:
        # Большинство >= 1 млрд
        return 1_000_000_000, "млрд", "млрд руб."
    else:
        # Смешанное распределение — используем медиану для определения
        sorted_vals = sorted(non_zero_values)
        median = sorted_vals[n // 2]
        
        if median >= 1_000_000_000:
            return 1_000_000_000, "млрд", "млрд руб."
        elif median >= 1_000_000:
            return 1_000_000, "млн", "млн руб."
        elif median >= 1_000:
            return 1_000, "тыс.", "тыс. руб."
        else:
            return 1.0, "руб.", "руб."


def _format_number(v: float, scale: float, component_type: Optional[str] = None, as_percentage: bool = False) -> str:
    """
    Форматирует число с учётом масштаба и точности.

    Параметры:
        v: значение для форматирования
        scale: масштаб для деления (если 0, не делить)
        component_type: тип компонента ('rate', 'base', 'ratio_num', 'ratio_den')
        as_percentage: если True, всегда форматировать как проценты (для rate/ratio_num/ratio_den)
                       если False, использовать масштаб (для impact)

    Правила:
        - Если as_percentage=True и component_type в ('rate', 'ratio_num', 'ratio_den') → проценты
        - Если 0 < abs(v) < 1 и as_percentage не задан → автоматически проценты
        - Иначе → с масштабированием
    """
    if v is None:
        return ""

    # Если явно указано как проценты (для rate/ratio_num/ratio_den)
    if as_percentage and component_type in ('rate', 'ratio_num', 'ratio_den'):
        s = f"{abs(v) * 100:.3f}".replace(".", ",")
        sign = "-" if v < 0 else ""
        return sign + s.rstrip('0').rstrip(',') + "%"

    # Ставки/доли показываем в процентах (без учёта масштаба)
    if 0 < abs(v) < 1 and not as_percentage:
        s = f"{abs(v) * 100:.3f}".replace(".", ",")
        sign = "-" if v < 0 else ""
        return sign + s.rstrip('0').rstrip(',') + "%"

    # Если масштаб не задан (scale=0), используем 1
    if scale == 0:
        scale = 1

    scaled = v / scale

    # Для нулевых значений — показываем 0,0 (учитываем float-артефакты)
    if abs(scaled) < 1e-10:
        return "0,0"

    # Для очень маленьких чисел (меньше 1% от масштаба) — больше знаков после запятой
    if 0 < abs(scaled) < 0.01:
        s = f"{abs(scaled):.4f}".replace(".", ",")
        # Убираем лишние нули в конце
        s = s.rstrip('0').rstrip(',')
        return ("-" if v < 0 else "") + s

    # Обычный формат с 1 знаком после запятой
    s = f"{abs(scaled):,.1f}".replace(",", " ").replace(".", ",")
    # Убираем лишние нули и точки
    s = s.rstrip('0').rstrip(',')
    return ("-" if v < 0 else "") + s


def _t_amount(v: float, scale: float, component_type: Optional[str] = None) -> str:
    """План/Факт с динамическим масштабированием. Для rate/ratio показываем как проценты."""
    # Для rate/ratio_num/ratio_den используем проценты, иначе используем автоматическое определение
    as_percentage = component_type in ('rate', 'ratio_num', 'ratio_den')
    return _format_number(v, scale, component_type, as_percentage=as_percentage)


def _t_impact(v: float, scale: float, component_type: Optional[str] = None) -> str:
    """Влияние с динамическим масштабом и знаком: + / − / 0,0. Для всех типов - как рубли."""
    if not v:
        return "0,0"
    return _format_number(v, scale, component_type, as_percentage=False)


def _impact_cell(v: float, bold: bool, scale: float, component_type: Optional[str] = None) -> str:
    txt = _t_impact(v, scale, component_type)
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

    # Фильтрация деревьев: оставляем только те, у которых есть дети
    filtered_trees = []
    for tree in trees:
        children = (tree.get("details") or {}).get("top_factors") or []
        if len(children) > 0:
            filtered_trees.append(tree)

    if not filtered_trees:
        return ""

    # Сбор всех значений для определения оптимального масштаба
    all_values: List[float] = []

    def collect_values(node: Dict) -> None:
        am = node.get("amounts") or {}
        for key in ("plan", "fact", "deviation", "impact_to_top_lvl"):
            val = am.get(key)
            if val is not None:
                all_values.append(float(val))
        children = (node.get("details") or {}).get("top_factors") or []
        for c in children:
            collect_values(c)

    for tree in filtered_trees:
        collect_values(tree)

    # Определение оптимального масштаба
    scale_factor, scale_suffix, scale_full = _infer_scale(all_values)

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
        
        # Получаем тип компонента из node для корректного форматирования
        component_type = node.get("amount_type")
        
        rows.append(
            f"| {num} | {_path_cell(node, depth, parent)} "
            f"| {_t_amount(base_val, scale_factor, component_type)} | {_t_amount(am.get('fact'), scale_factor, component_type)} "
            f"| {_impact_cell(_impact(node), bold_infl, scale_factor, component_type)} |"
        )
        if has_children:
            dtype = (node.get("details") or {}).get("type") or ""
            rows.append(f"|   | {'&emsp;' * depth}{_sep_label(dtype)} | | | |")
            for c in children:
                walk(c, depth + 1, node, len(children) == 1)

    for ti, tree in enumerate(filtered_trees):
        if ti > 0:
            rows.append("|   | | | | |")          # разделитель между деревьями
        walk(tree, 0, None, False)

    head = (f"### Детализация факторного анализа отклонений: "
            f"{_clean_name(filtered_trees[0].get('hieararchy_node', ''))}\n\n"
            f"| # | Путь разложения | План, {scale_suffix} | Факт, {scale_suffix} | Влияние, {scale_suffix} |\n"
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
    Аналогична логике _infer_scale, но без форматирования чисел.
    """
    trees = data.get("data") or []
    all_values: List[float] = []
    
    def collect_values(node: Dict) -> None:
        am = node.get("amounts") or {}
        for key in ("plan", "fact", "deviation", "impact_to_top_lvl"):
            val = am.get(key)
            if val is not None:
                all_values.append(float(val))
        children = (node.get("details") or {}).get("top_factors") or []
        for c in children:
            collect_values(c)
    
    for tree in trees:
        collect_values(tree)

    scale_factor, scale_suffix, scale_full = _infer_scale(all_values)
    
    return {
        "scale": scale_suffix,
        "scale_full": scale_full,
        "scale_factor": scale_factor
    }