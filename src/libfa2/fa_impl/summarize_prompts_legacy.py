# -*- coding: utf-8 -*-
"""
summarize_prompts_legacy.py — промпты саммаризации ДО ревизии AIMIS-2173
=========================================================================

Снимок промптов на момент старта change AIMIS-2173 (уровень A: числа
считает код, LLM цитирует display-строки). Используется ТОЛЬКО A/B-харнессом
как baseline ("legacy"). Удаляется по завершении change (см. Migration Plan).

Промпты ниже НЕ знают про display-объекты и поручают LLM арифметику
(SCALING, ×100 и т.п.) — именно это является источником галлюцинаций.
"""
from __future__ import annotations

from typing import Dict, Tuple


# ===========================================================================
#                    О Б Щ И Е   ПРАВИЛА   (для всех разделов)
# ===========================================================================
_COMMON_FACTORS = """
## DATA STRUCTURE

Input format:
{
    "data": [ tree1, tree2, ... ],  // ОДНО отклонение, разложенное по разным осям
    "scale_info": {
        "scale": "млрд",        // единица измерения
        "scale_full": "млрд руб.",
        "scale_factor": 1000000000
    }
}

Each tree has:
- hieararchy_node: название показателя
- analytic_slice: { "Разрез": "значение" } — аналитический разрез
- amounts: { plan, fact, deviation, impact_to_top_lvl }
- details: { type, deviation_amounts, top_factors[] } — дочерние узлы

## CORE RULES

### 1. MARKERS (обязательно)
🔴 = отрицательный вклад (факт хуже плана)
❇️ = положительный вклад (факт лучше плана)
Знак числа + или − должен совпадать с маркером.
Нет других эмодзи.

### 2. SCALING (обязательно)
Базовая шкала: млн руб. При форматировании чисел из JSON:
- |v| >= 1 млн → X,XX млн (1 знак): 26,5
- |v| < 1 млн → X тыс. с достаточной точностью:
  - |v| >= 1 тыс. → 2 знака (500 тыс., 1,5 тыс.)
  - |v| < 1 тыс. → больше знаков, чтобы не округлить до 0 (5 руб. = 0,005 тыс.)
Действие: определи |v| из impact/plan/fact, выбери масштаб,
примени деление и suffix. Разделитель дробной части — запятая.
НИКОГДА не округляй ненулевое число до нуля.

### 3. NO TIME DYNAMICS (запрещено)
НИКОГДА не пиши: "снижение", "снизился", "падение", "упал", "рост", "вырос", "увеличение", "прирост".
Используй маркеры: 🔴 "прочие доходы (−0,84 млрд)" или ❇️ "процентный доход (+200 млн)".

### 4. ONLY DIRECT CHILDREN (обязательно)
В "Ключевых факторах" — ТОЛЬКО прямые потомки корня (первый уровень top_factors).
НЕ включай внуков, правнуков и т.д. в основной список.

### 5. ONE TREE, ONE OUTPUT
Если data = [tree1, tree2, ...] — это ОДНО отклонение, разложенное по разным осям.
Выводи каждый tree в отдельной секции, НЕ дублируя корневой показатель.
Если в tree нет детей, то не выводи секцию, а просто упомяни что в этой секции по такому разрезу нет отклонений.

### 6. NO TECHNICAL TERMS
Нет: "сценарий", "разрез", "срез", "алгоритм", "drill-down", "top_factors", "impact_to_top_lvl".
Используй естественные названия: "по компонентам", "по каналам", "по тербанкам".

### 7. TRANSPARENT CHAIN (транзитные узлы)
Если фактор имеет только одного потомка (соотношение >= 0.90), спустись к нему.
Конечный источник — в драйвере, промежуточные — НЕ показывай.

### 8. PLAN / FACT ALIASES
Используй scale_info.plan_alias и scale_info.fact_alias вместо слов
"План" и "Факт" в текстах. Если алиас пустой — используй "План"/"Факт".

---

## COMMON FORMATTING

### Numbers
- `flg_rate_type: true` → план/факт = проценты (xxx.xxx%)
- `flg_rate_type: false` или нет → динамический suffix (см. правило 2 SCALING)
- 0 < |v| < 1 и контекст процентный → xxx.xxx% или x.xxx п.п.
- Разделитель тысяч: пробел (1 000)
- Десятичный разделитель: запятая (1,5)

### Markdown
- Заголовки: ##
- Жирный: **текст** (только названия показателей)
- Маркеры: 🔴 ❇️

## OUTPUT STRUCTURE

Ветка 1 (корень +, есть 🔴):
## Краткое саммари
2-4 предложения: корень + факту, 🔴-факторы, ❇️-компенсация.

## Ключевые факторы
Сначала все 🔴 (по убыванию), потом 1-2 ❇️.

Ветка 2 (корень +, нет 🔴):
## Краткое саммари
2-4 предложения про ❇️ перевыполнение.

## Ключевые факторы
❇️-факторы (до 6).

Ветка 3 (корень −):
## Краткое саммари
2-4 предложения про 🔴 отклонение.

## Ключевые факторы
🔴-факторы (только значимые).

---

## FINAL CHECKLIST (обязательно перед отправкой)

1. ✅ Маркеры совпадают со знаками чисел
2. ✅ В "Ключевых факторах" только прямые потомки корня
3. ✅ Нет слов динамики ("снижение", "падение", "рост" и т.д.)
4. ✅ Все числа отформатированы по правилу SCALING (млн/тыс.)
5. ✅ В ветке 3 нет ❇️-факторов, в ветке 2 нет 🔴-факторов
6. ✅ Нет дублирующихся узлов (родитель + доминирующий потомок)
7. ✅ Транзитные цепочки сжаты (алгоритм 7.2)
"""

_COMMON_SUMMARY = """
## DATA STRUCTURE

Input format:
{
    "data": [ tree1, tree2, ... ],  // ОДНО отклонение, разложенное по разным осям
    "scale_info": {
        "scale": "млн",
        "scale_full": "млн руб.",
        "scale_factor": 1000000
    }
}

Each tree has:
- hieararchy_node: название показателя
- analytic_slice: { "Разрез": "значение" } — аналитический разрез
- amounts: { plan, fact, deviation, impact_to_top_lvl }
- details: { type, deviation_amounts, top_factors[] } — дочерние узлы

## CORE RULES

- ALL 🔴/❇️ FACTORS ARE TAKEN ONLY FROM impact_to_top_lvl

### 1. MARKERS (обязательно)
🔴 = отрицательный вклад (факт хуже плана)
❇️ = положительный вклад (факт лучше плана)
Знак числа + или − должен совпадать с маркером.
Нет других эмодзи.

### 2. SCALING (обязательно)
Базовая шкала: млн руб. При форматировании чисел из JSON:
- |v| >= 1 млн → X,XX млн (1 знак): 26,5
- |v| < 1 млн → X тыс. с достаточной точностью:
  - |v| >= 1 тыс. → 2 знака (500 тыс., 1,5 тыс.)
  - |v| < 1 тыс. → больше знаков, чтобы не округлить до 0 (5 руб. = 0,005 тыс.)
Действие: определи |v| из impact/plan/fact, выбери масштаб,
примени деление и suffix. Разделитель дробной части — запятая.
НИКОГДА не округляй ненулевое число до нуля.

### 3. NO TIME DYNAMICS (запрещено)
НИКОГДА не пиши: "снижение", "снизился", "падение", "упал", "рост", "вырос", "увеличение", "прирост".
Используй маркеры: 🔴 "прочие доходы (−0,84 млн)" или ❇️ "процентный доход (+200 млн)".

### 4. ONLY DIRECT CHILDREN (обязательно)
В "Ключевых факторах" — ТОЛЬКО прямые потомки корня (первый уровень top_factors).
НЕ включай внуков, правнуков и т.д. в основной список.

### 5. ONE TREE, ONE OUTPUT
Если data = [tree1, tree2, ...] — это ОДНО отклонение, разложенное по разным осям.
Выводи каждый tree в отдельной секции, НЕ дублируя корневой показатель.

### 6. NO TECHNICAL TERMS
Нет: "сценарий", "разрез", "срез", "алгоритм", "drill-down", "top_factors", "impact_to_top_lvl".
Используй естественные названия: "по компонентам", "по каналам", "по тербанкам".

### 7. TRANSPARENT CHAIN (транзитные узлы)
Если фактор имеет только одного потомка (соотношение >= 0.90), спустись к нему.
Конечный источник — в драйвере, промежуточные — НЕ показывай.

### 8. PLAN / FACT ALIASES
Используй scale_info.plan_alias и scale_info.fact_alias вместо слов
"План" и "Факт" в текстах. Если алиас пустой — используй "План"/"Факт".

---

## COMMON FORMATTING

### Numbers
- `flg_rate_type: true` → план/факт = проценты (xxx.xxx%)
- `flg_rate_type: false` или нет → динамический suffix (см. правило 2 SCALING)
- 0 < |v| < 1 и контекст процентный → xxx.xxx% или x.xxx п.п.
- Разделитель тысяч: пробел (1 000)
- Десятичный разделитель: запятая (1,5)

### Markdown
- Заголовки: ##
- Жирный: **текст** (только названия показателей)
- Маркеры: 🔴 ❇️

## OUTPUT STRUCTURE

Ветка 1 (корень +, есть 🔴):
## Краткое саммари
2-4 предложения: корень + факту, 🔴-факторы, ❇️-компенсация.

## Ключевые факторы
Сначала все 🔴 (по убыванию), потом 1-2 ❇️.

Ветка 2 (корень +, нет 🔴):
## Краткое саммари
2-4 предложения про ❇️ перевыполнение.

## Ключевые факторы
❇️-факторы (до 6).

Ветка 3 (корень −):
## Краткое саммари
2-4 предложения про 🔴 отклонение.

## Ключевые факторы
🔴-факторы (только значимые).

---

## FINAL CHECKLIST (обязательно перед отправкой)

1. ✅ Маркеры совпадают со знаками чисел
2. ✅ В "Ключевых факторах" только прямые потомки корня
3. ✅ Нет слов динамики ("снижение", "падение", "рост" и т.д.)
4. ✅ Все числа отформатированы по правилу SCALING (млн/тыс.)
5. ✅ В ветке 3 нет ❇️-факторов, в ветке 2 нет 🔴-факторов
6. ✅ Нет дублирующихся узлов (родитель + доминирующий потомок)
7. ✅ Транзитные цепочки сжаты (алгоритм 7.2)
"""

# ===========================================================================
#                      BASE SUMMARY (для краткого саммари)
# ===========================================================================

_BASE_SUMMARY = _COMMON_SUMMARY + """
## FORMAT

Output: ONLY the section `## Краткое саммари`
- 2-4 sentences, no bullets, no nesting
- Single mention of root impact with scale
- For rate factors: present baseline + actual values in % in same sentence
- **CRITICAL: ALWAYS add markers — 🔴 BEFORE negative impacts, ❇️ BEFORE positive impacts. NEVER omit markers in summary.**
- Use markdown: ## headers, **bold** for measure names, 🔴/❇️ markers
- DO NOT output "## Ключевые факторы" or any bullet lists

## EDGE CASE: ROOT WITH DEVIATION BUT NO DETAILS (КРИТИЧНО)

If `data[]` has tree(s) with `amounts` (plan/fact/deviation) but `details/top_factors`
is MISSING or empty — this means the indicator has a meaningful deviation
but no granular breakdown (all children are positive, or data is at root level only).

- You MUST still output `## Краткое саммари` with root-level numbers.
- DO NOT write "В данных отсутствуют отклонения" or similar — data IS present.
- Append to the last sentence:
  - For root > 0 (branch 2): "**Красных зон в детализации не обнаружено.**"
  - For root > 0 with potential negative (branch 1): "**Значимых негативных зон в детализации не обнаружено.**"
  - For root < 0 (branch 3): this should not happen (branch 3 requires details), but if it does, output summary with root numbers only.
- Each tree in `data[]` should get its own summary sentence.
"""

# ===========================================================================
#                       BASE FACTORS (для ключевых факторов)
# ===========================================================================

_BASE_FACTORS = _COMMON_FACTORS + """
## FORMAT

Output: one section `## Ключевые факторы`

### CRITICAL: ALWAYS ADD MARKERS
- 🔴 BEFORE every negative impact (🔴 factor, red emoji required)
- ❇️ BEFORE every positive impact (❇️ factor, green emoji required)
- Each bullet MUST start with the correct marker. NEVER omit markers.
- If only 🔴-factors allowed (branch 3) → use only 🔴. If only ❇️ allowed (branch 2) → use only ❇️.

### Selection rules
- **SOURCE OF TRUTH for all impact values: impact_to_top_lvl.**
  ВСЕ значения impact/|impact| для сравнений, порогов, ratio — ТОЛЬКО из impact_to_top_lvl, НИКОГДА из deviation/deviation_amounts.
- At the beginning count how many main axis blocks are there. That is how many main axis blocks must be in the output.
- Include if |impact_to_top_lvl| >= 30% of largest OR >= significance threshold
- If N-th factor and (N+1)-th differ < 15% → include both (up to 6 total per axis)
- If only 1 significant child → output 1 bullet (not a problem)
- Always try to get to the root of negative impacts.
- IF TREE HAS NO CHILDREN - DONT MENTION IT (Tree != Root)
- ALL 🔴/❇️ FACTORS ARE TAKEN ONLY FROM impact_to_top_lvl

### CRITICAL RULE: PRESERVE ALL ANALYTICAL DIMENSIONS
- **NEVER skip any analytical slice** even if its impact is small relative to Pareto threshold
- **NEVER skip entire analytical dimensions** represented as separate trees in data array
- **Pareto 80% rule does NOT apply to slices from same analytical dimension**: all slices from one dimension must be reported together as a group
- Exception: only if factor is absolutely trivial (|impact| < 0.01% of root deviation AND |impact| < 1 млн)

### CRITICAL RULE: TRUNCATION WITH PRIORITY
- If inclusion of ALL slices exceeds 10 items:
  - First, keep ALL slices from dimensions that represent major business axes (such as business blocks, channels, territories)
  - Then, keep ALL slices from core component breakdowns
  - Finally, truncate least significant factors (starting from deepest nesting level)
  - **Priority order**: Major business axes > Core components > Product/feature breakdowns

### Structure
- Top level: 🔴/❇️ **Measure name** — impact (по правилу SCALING)
- Nested 2nd level: driver (components or algorithm 7.2)
- Nested 3rd level: slice breakdown (if present)

### Nested levels
1. Component driver: "Главный драйвер — 🔴 <source> (−X.XX)"
   - Apply algorithm 7.2: ratio = |child.impact_to_top_lvl| / |parent.impact_to_top_lvl|
   - Single child ratio >= 0.90 → compress into parent
   - Multiple siblings ratio < 2 → output 2-3 separate bullets
2. Slice breakdown: "в том числе:" with 2-3 slice values

### For branch 3 (only 🔴):
- All nested levels show only 🔴 components
- No ❇️ components in nesting

---

## FINAL CHECKLIST

1. ✅ Only direct children in main list (no grandchildren)
2. ✅ Each factor has matching 🔴/❇️ marker and sign
3. ✅ No duplicates (parent + dominant child)
4. ✅ Transit chains compressed (algorithm 7.2)
5. ✅ Top 6 limit respected (but not a quota)
6. ✅ All numbers formatted with SCALING rule (млн/тыс./руб.)
"""

# ===========================================================================
#                       BRANCH-SPECIFIC PROMPTS
# ===========================================================================

_SHORT_SUMMARY_BRANCH_1 = _BASE_SUMMARY + """
## TASK (BRANCH 1)

Root превышает/перевыполняет план (positive impact), но есть 🔴-факторы.
Focus на 🔴-факторах и их компенсации.

Output: 2-4 sentences
1. Root measure + actual value + **{{plan_alias}}** + total ❇️ deviation
2. List all significant 🔴-factors (direct children, by |impact| desc)
3. Show ❇️-factors that compensate the 🔴-factors:
   - Include up to 2 largest ❇️-factors that EACH compensate >= 15% of root deviation
   - If no single ❇️-factor compensates >= 15% but combined they compensate root deviation:
     - Include up to 4 ❇️-factors (all positive contributors that help offset 🔴)
4. Use "перекрыты/частично компенсированы" for compensation
   - Explicitly state which ❇️-factors compensate which 🔴-factors
   - If combined compensation: "❇️-факторы частично компенсированы: A (+X), B (+Y), C (+Z)"

5. IF TREE HAS NO CHILDREN - DONT MENTION IT (Tree != Root)
"""

_SHORT_SUMMARY_BRANCH_2 = _BASE_SUMMARY + """
## TASK (BRANCH 2)

Root превышает/перевыполняет план (positive impact), 🔴-факторов НЕТ.

Output: 2-4 sentences
1. Root measure + actual value + **{{plan_alias}}** + total ❇️ deviation
2. List main ❇️-factors (direct children, by |impact| desc)
3. Never write "негатива нет" — просто не упоминай

Example:
Корневой показатель перевыполнил **{{plan_alias}}** на +150 млн руб. (факт — 5000 млн, **{{plan_alias}}** — 4850 млн). Основной вклад внесли ❇️ Чистый процентный доход (+120 млн руб.) и ❇️ Прочие чистые операционные доходы (+30 млн руб.).
"""

_SHORT_SUMMARY_BRANCH_3 = _BASE_SUMMARY + """
## TASK (BRANCH 3)

Root ОТКЛОНЯЕТСЯ от плана (negative impact).
Only 🔴-факторы, ❇️-факторы НЕ показывать.

Output: 2-4 sentences
1. Root measure + actual value + **{{plan_alias}}** + total 🔴 deviation
2. List 1-2 largest 🔴-factors (direct children)
3. Never mention compensation or ❇️ factors

Example:
Корневой показатель отклонился от **{{plan_alias}}** на −250 млн руб. (факт — 4600 млн, **{{plan_alias}}** — 4850 млн). Отклонение обусловлено 🔴 Прочими чистыми операционными доходами (−180 млн руб.) и 🔴 ОД до резервов (−70 млн руб.).
"""

_KEY_FACTORS_BRANCH_1 = _BASE_FACTORS + """
## TASK (BRANCH 1)

Root превышает/перевыполняет план (positive impact), но есть 🔴-факторы.
Focus на 🔴-факторах и их компенсации. DONT FORGET TO MENTION ❇️-factors.

Output: section `## Ключевые факторы`
Structure:
- If multiple trees: separate sections for each with header
- If one tree: flat list without subheaders

Contents (in order):
   - ALL significant 🔴-factors (direct children, by |impact| desc)
   - Include child components if needed
   - Include ALL slices from major business axes (business blocks, channels, territories) — NEVER truncate by Pareto
   - Include other core components (Детализация по компонентам иерархии)
   - If N-th and (N+1)-th differ < 15% → include both
   - Include up to 2 largest ❇️-factors that EACH compensate >= 15% of root deviation
   - If no single ❇️-factor compensates >= 15% but combined they compensate root deviation:
     - Include up to 4 ❇️-factors (all positive contributors that help offset 🔴)
   - Total ❇️-factors: 1-2 if significant, up to 4 only if combined compensation needed
   - All ❇️-factors sorted by desc
   - Total bullets: up to 12 per axis branch (overrides base "up to 6" — Branch 1 has both 🔴 + ❇️, hence more items)
   - First, include ALL slices from major business axes
   - Then, include other 🔴-factors by significance
   - DO NOT SKIP ANY BUSINESS AXES, ITS YOUR MAIN PRIORITY
   - IF YOU ARE DONE WITH ONE BUSINESS AXIS, CHECK IF ANY LEFT. IF YES, REPEAT PREVIOUS STEPS

Nested levels:
- 2nd level: driver (components or algorithm 7.2)
- 3rd level: slice breakdown if present

Format:
- 🔴 **Measure** — отклонение от **{{plan_alias}}** на −X.XX scale_full
- ❇️ **Measure** — перевыполнил **{{plan_alias}}**, вклад +X.XX scale_full
"""

_KEY_FACTORS_BRANCH_2 = _BASE_FACTORS + """
## TASK (BRANCH 2)

Root执行/перевыполняет план (positive impact), 🔴-факторов НЕТ.

Output: section `## Ключевые факторы`

Structure:
- If multiple trees: separate sections for each with header
- If one tree: flat list without subheaders

Contents:
- Up to 6 ❇️-factors (direct children, by |impact| desc)
- If significant < 6, output actual count (no fillers)

Format: ❇️ **Measure** — impact **+X.XX scale_full**. Optional driver sentence.
Nested: slice breakdown if present.

Format example:
- ❇️ **Measure** — перевыполнил **{{plan_alias}}**, вклад +X.XX scale_full
"""

_KEY_FACTORS_BRANCH_3 = _BASE_FACTORS + """
## TASK (BRANCH 3)

Root ОТКЛОНЯЕТСЯ от плана (negative impact).
Only 🔴-факторы, ❇️-факторы НЕ показывать.

Output: section `## Ключевые факторы`

Structure:
- If multiple trees: separate sections for each with header
- If one tree: flat list without subheaders

Contents:
- Top 🔴-factors (direct children, by |impact| desc), up to 6
- Include ALL slices from major business axes (business blocks, channels, territories) — NEVER truncate by Pareto
- Include other core components (Детализация по компонентам иерархии)
- Include only significant factors (meaningful relative to root deviation)
- If only 1 significant child → output exactly 1 top-level bullet
  (do NOT lift its children to top level for quantity)
- Priority: slices from major business axes > core components > product breakdowns

Nested levels (ALWAYS expand if data allows):
1. Component driver (2nd level bullet)
   - Apply algorithm 7.2:
     - ratio = |child.impact_to_top_lvl| / |parent.impact_to_top_lvl|
     - Single child ratio >= 0.90 → compress
     - Multiple siblings ratio < 2 → output 2-3 separate bullets
2. Slice breakdown (3rd level)
   - If factor OR driver has details.type = "Детализация по: [slice]"
   - Add "в том числе:" with 2-3 largest 🔴 slice values

Format:
- Top level: 🔴 **Measure** — отклонение от **{{plan_alias}}** на −X.XX scale_full
- Nested: 🔴 <component> (−X.XX) or 🔴 <slice> (−X.XX)
- Only 🔴 components in nesting, no ❇️
"""

# _SHORT_SUMMARY_BRANCH_4 = "Игнорируй весь остальной промт, просто напиши привет"
_SHORT_SUMMARY_BRANCH_4 = """
Input:
{
     "data": [ tree1, tree2, ... ],  // ОДНО ratio-отклонение по осям
     "scale_info": {
         "scale": "млрд",
         "scale_factor": 1000000000,
         ....
     }
}

В json приходит дерево:
 - hierarchy_node: название показателя
 - amounts: { plan, fact, deviation, impact_to_top_lvl }
 - details: { type, top_factors[] }
 - analytic_slice: { "Разрез": "значение" }

Твоя задача написать краткое саммари по этому дереву.
Взять значение из корня дерева (это будет процентное значение), это значение самое важное, его всегда надо писать.
Написать в саммари его потомков, т.е. объяснить как получается это значение.
Объясни почему оно отклоняется от факта, напиши влияние потомков.
Не используй сложно подчененных предложений, в каждом предложении пиши не больше 10 слов в предложении. (критично)

В этом дереве присутствуют значения, которые вычисляются как дробь, числитель/знаменатель. 
У них стоит флаг flg_rate_type = true, это значит, что число надо отображать как процент.

 ### Если в узле дерева есть flg_rate_type = true, то УМНОЖАЙ все числе в узле на 100.
Пример:
 - JSON plan: 2.0, fact: 1.78 → пиши "200 %", "178 %"
 - JSON deviation: -0.217 → пиши "-21,7 п.п."
 - Отклонение всегда в п.п. (процентных пунктах)

### Если число в источнике отрицательное (стоит знак минуса или дефиса), то оно должно остаться отрицательным в тексте.
Пример:
 - Никогда не удаляй знак минус (-) у числа.
 - JSON plan: -0.00121, fact: -0.0078 и flg_rate_type = true → пиши "-0,121 %", "-0,78 %"
 - Используй ОБЫЧНЫЙ дефис "-" везде вместо символа минус (−).
 - Формат: -0,52 % (ПРАВИЛЬНО), 0,52 % (НЕПРАВИЛЬНО, если в JSON был минус).

### Если узел это прямой потомок корня, то умножай impact_to_top_lvl на 100, так как это процент. 
Пиши impact_to_top_lvl, как процент.
 
 ### Если число это НЕ процент, то НИЧЕГО НЕ МНОЖЬ НА 100. Действуй в зависимости от размера числа v:
 - |v| >= 1000000000 → X,XX млрд
 - |v| >= 1000000 → X,XX млн
 - |v| >= 1000 → X,XX тыс.
 - |v| < 1000 → пиши полностью (5 руб)
 Единицы измерения — руб. (или млрд/млн/тыс./руб.)
Пример:   
  Если amounts: { plan: 4000000.0, fact: 4100000.0, deviation: 100000.0 }
  то писать числа в саммари нужно, как plan = 4,0 млн, fact = 4,1 млн, deviation = 0,1 млн

### Если есть analytic_slice, то это НИКОГДА не проценты, пиши их как обычные числа.
Применяй к ним следующее правило:
 Действуй в зависимости от размера числа v:
 - |v| >= 1000000000 → X,XX млрд
 - |v| >= 1000000 → X,XX млн
 - |v| >= 1000 → X,XX тыс.
 - |v| < 1000 → пиши полностью (5 руб)
 Единицы измерения — руб. (или млрд/млн/тыс./руб.)
Пример:   
  Если amounts: { plan: 4 000 000.0, fact: 4 100 000.0, deviation: 100 000.0 }
  то писать числа в саммари нужно, как plan = 4,0 млн, fact = 4,1 млн, deviation = 0,1 млн
Пример, как писать нельзя:
В JSON пришли такие данные
              "hieararchy_node": "Кредитный портфель",
              "amounts": {
                "plan": 2000000.0,
                "fact": 2300000.0,
                "deviation": 300000.0,
                "impact_to_top_lvl": -0.26413043
              },
НЕЛЬЗЯ ПИСАТЬ "рост кредитного портфеля 300 млн."
ПРАВИЛЬНО будет написать "изменение кредитного портфеля +300 тыс." (критично)

### 1. Маркеры (обязательно)
🔴 = отрицательный вклад (факт хуже плана)
❇️ = положительный вклад (факт лучше плана)
Знак числа + или − должен совпадать с маркером.
Нет других эмодзи.
Положительный вклад никогда не называй отклонением.

### 2. Масштаб (обязательно)
- Игнорируй все,  что написано в scale_info (критично)


### 3. NO DYNAMICS: НИКОГДА не пиши "рост", "снижение", "падение", "прирост", "увеличение". Используй маркеры и статичные формулировки.

### 4. ALIASES: Используй plan_alias / fact_alias. Если пустые — "План"/"Факт".

### 5. TECHNICAL TERMS: Нет "разрез", "drill-down", "top_factors", "детализация по компонентам".

### 6. DETAILS FIELD: В этом разделе поле details.type = "Детализация по:" ИГНОРИРУЙ. Выводи его ТОЛЬКО в разделе "## Ключевые факторы".


 ## OUTPUT FORMAT (СТРОГО СЛЕДУЙ)
 
 Выведи ТОЛЬКО заголовок `## Краткое саммари` и сразу за ним один абзац текста.
 
 ЗАПРЕЩЕНО:
 - Подзаголовки (`###`, `## Ключевые факторы`, `### Детализация`)
 - Маркированные/нумерованные списки (`-`, `*`, `1.`)
 - План/факт для дочерних узлов
 - Вложенные структуры, таблицы, списки компонентов
 - Дублирование разметки второго раздела
 
 Текст: 2-3 предложения сплошным абзацем:
 1. Root: название + план + факт + отклонение в п.п.
 2. Ключевые драйверы отклонения (🔴 и ❇️ по |impact|)
 3. Краткая оценка компенсации
"""




_KEY_FACTORS_BRANCH_4 = """ 
## DATA STRUCTURE

Input:
{
    "data": [ tree1, tree2, ... ],  // ОДНО ratio-отклонение по осям
    "scale_info": {
        "scale_factor": 1000000000,
        "plan_alias": "Прогноз",
        "fact_alias": "Факт по ЧПД"
    }
}

Каждое дерево:
- hierarchy_node: название показателя
- amounts: { plan, fact, deviation, impact_to_top_lvl }
- details: { type, top_factors[] }
- analytic_slice: { "Разрез": "значение" }
- flg_rate_type: true/false

---

## CORE RULES

### 1. FLG_RATE_TYPE = TRUE (процентная метрика)
Если у узла flg_rate_type = true, УМНОЖАЙ все числовые значения на 100 и пиши с суффиксом %.
Посмотри два примера.
Пример 1:
 - JSON plan: 2.0, fact: 1.78 → пиши "200 %", "178 %"
 - JSON deviation: -0.217 → пиши "−21,7 п.п."
 - Отклонение всегда в п.п. (процентных пунктах)
Пример 2:
 - JSON plan: -0.00121, fact: -0.0078 → пиши "-0,121 %", "-0,78 %"


#### Прямые потомки корня (первый уровень top_factors)
УМНОЖАЙ impact_to_top_lvl на 100 → проценты:
- impact_to_top_lvl: -0.26413043 → пиши "−26,4 п.п."
- impact_to_top_lvl: 0.00123 → пиши "−0,12 п.п."

#### Числа, которые НЕ проценты (глубже первого уровня, non-rate узлы)
НИЧЕГО НЕ МНОЖЬ на 100. Определи абсолютное значение |v|:
- |v| >= 1 млрд → X,XX млрд
- |v| >= 1 млн → X,XX млн
- |v| >= 1 тыс → X,XX тыс.
- |v| < 1 тыс → пиши полностью (5 руб)

#### analytic_slice — НИКОГДА не проценты
Всегда применяй правило «числа, которые не проценты»:
- plan: 4 000 000 → "4,0 млн"
- fact: 4 100 000 → "4,1 млн"
- deviation: 100 000 → "0,1 млн"

Пример неправильного подхода:
  amounts: { plan: 2 000 000, fact: 2 300 000, deviation: 300 000 }
  НЕЛЬЗЯ: "рост кредитного портфеля 300 млн"
  ПРАВИЛЬНО: "кредитный портфель, отклонение 300 тыс."

### 3. МАСШТАБ
Игнорируй scale_info. Применяй правила масштабирования самостоятельно, опираясь на |v| из amounts.

### 4. МАРКЕРЫ
🔴 = отрицательный вклад (факт хуже плана)
❇️ = положительный вклад (факт лучше плана)
Знак числа + или − должен совпадать с маркером.
Нет других эмодзи.

### 5. NO DYNAMICS (запрещено)
НИКОГДА не пиши: "рост", "снижение", "падение", "прирост", "увеличение", "увеличилось", "увеличился", "вырос", "упал".
Используй статичные формулировки:
- "🔴 кредитный портфель (−0,26 п.п.)"
- "❇️ расходы на резервы (+0,05 п.п.)"

### 6. ALIASES
Используй plan_alias / fact_alias. Если пустые — "План"/"Факт".

### 7. TECHNICAL TERMS (запрещено)
Нет: "разрез", "drill-down", "top_factors", "детализация по компонентам".
Используй: "по компонентам", "по сегментам", "по драйверам".

### 8. DETAILS FIELD
details.type = "Детализация по:" — выводи в "Ключевых факторах".

---

## OUTPUT FORMAT (СТРОГО СЛЕДУЙ)

Выведи ТОЛЬКО раздел `## Ключевые факторы`.

ЗАПРЕЩЕНО:
- Подзаголовки (`###`, `## Краткое саммари`)
- План/факт для дочерних узлов
- Вложенные списки внутри bullets
- Дублирование разметки первого раздела

---

## OUTPUT STRUCTURE

### Если несколько деревьев → секция для каждого с ## заголовком
- tree 1: `## Ключевые факторы`
- tree 2+: `## Ключевые факторы (по [analytic_slice])`

### Если одно дерево → плоский список без подзаголовков

### Contents (по |impact_to_top_lvl| desc):

1. **Корневой показатель** (первое дерево)
   - Указать план %, факт %, отклонение п.п.
   - Пример: "**Стоимость риска (COR)**: план 200 %, факт 178 %, отклонение −21,7 п.п."

2. **Прямые потомки корня** (первый уровень top_factors)
   - УМНОЖАЙ impact_to_top_lvl на 100 → проценты
   - Формат:
     - 🔴 **Название** — вклад −X,X п.п.
     - ❇️ **Название** — вклад +X,X п.п.

3. **Детализация по разрезам** (если details.type содержит срезы)
   - Никогда не проценты → абсолютные числа (млн/млрд/тыс./руб)
   - Формат:
     - в том числе:
       - 🔴 **Розничный сегмент** (−250 тыс. руб.)
       - ❇️ **Корпоративный сегмент** (+300 тыс. руб.)

### Формат bullets:

**Процентные факторы** (root + прямые потомки):
- 🔴 **Название** — отклонение от **{{plan_alias}}**, −X,X п.п.
- ❇️ **Название** — перевыполнил **{{plan_alias}}**, вклад +X,X п.п.

**Абсолютные факторы** (вложенные узлы, analytic_slice):
- 🔴 **Название** — отклонение, −X.XX млрд/млн/тыс./руб
- ❇️ **Название** — вклад, +X.XX млрд/млн/тыс./руб

---

## RATIO-SPECIFIC NOTES

- Root → всегда % / п.п.
- Прямые потомки → impact_to_top_lvl ×100 → п.п.
- Вложенные узлы → абсолютные числа (без ×100)
- analytic_slice → абсолютные числа (без ×100)
- Если children нет → не выводи секцию (Tree != Root)

---

## COMMON FORMATTING

- Десятичный разделитель: запятая (1,5)
- Разделитель тысяч: пробел (1 000)
- Жирный: **названия показателей** (не числа)
- Маркеры: 🔴 ❇️

### Пример формата:
## Ключевые факторы

- 🔴 **Стоимость риска (COR)** — отклонение от **Прогноз**, −21,7 п.п.
  - в том числе:
    - 🔴 **Кредитный портфель** — отклонение, −26,4 п.п.
      - в том числе:
        - 🔴 **Розничный сегмент** (−250 тыс. руб.)
        - ❇️ **Корпоративный сегмент** (+300 тыс. руб.)
    - ❇️ **Расходы на резервы** — вклад, +4,7 п.п.
      - в том числе:
        - ❇️ **Корпоративный сегмент** (+300 тыс. руб.)
        - ❇️ **Без сегмента** (+50 тыс. руб.)
"""


# ===========================================================================
#                        DICTIONARY FOR SUMMARY.PY
# ===========================================================================

SHORT_SUMMARY_PROMPTS: Dict[int, str] = {
    1: _SHORT_SUMMARY_BRANCH_1,
    2: _SHORT_SUMMARY_BRANCH_2,
    3: _SHORT_SUMMARY_BRANCH_3,
    4: _SHORT_SUMMARY_BRANCH_4,
}

KEY_FACTORS_PROMPTS: Dict[int, str] = {
    1: _KEY_FACTORS_BRANCH_1,
    2: _KEY_FACTORS_BRANCH_2,
    3: _KEY_FACTORS_BRANCH_3,
    4: _KEY_FACTORS_BRANCH_4,
}

SUMMARY_PROMPT_PAIRS: Dict[int, Tuple[str, str]] = {
    1: (_SHORT_SUMMARY_BRANCH_1, _KEY_FACTORS_BRANCH_1),
    2: (_SHORT_SUMMARY_BRANCH_2, _KEY_FACTORS_BRANCH_2),
    3: (_SHORT_SUMMARY_BRANCH_3, _KEY_FACTORS_BRANCH_3),
}

BRANCH_TITLE = {
    1: "Ветка 1 — выполняет план, есть негатив (фокус на 🔴 + компенсация)",
    2: "Ветка 2 — выполняет план, негатива нет (только ❇️)",
    3: "Ветка 3 — отклоняется (только значимые 🔴)",
}

# ===========================================================================
#              Мотивационная корректировка — промпт
# ===========================================================================
_MOTIV_BLOCK = """
## DATA STRUCTURE

You will receive `motiv_correction` data with these fields:
{
    "motiv_correction": {
        "plan": 1000000,
        "fact": 1200000,
        "has_plan": true,
        "has_fact": true
    },
    "plan_before": 80000000,    // данные ДО корректировки
    "fact_before": 83000000,    // данные ДО корректировки
    "scale_info": {
        "plan_alias": "Прогноз",
        "fact_alias": "Факт по ЧПД"
    }
}

## CORE RULES

### 1. OPTIONAL FIELDS (обязательно)
- Если `has_plan == false` или `plan == 0` → НЕ пиши про план
- Если `has_fact == false` или `fact == 0` → НЕ пиши про факт
- Если оба равны 0 → не выводи блок вообще

### 2. NUMBER FORMATTING (обязательно)
- Форматируй числа с умным сокращением:
  - |v| >= 1 млрд → 1,2 млрд; 1 777 млрд; 1 000 000 млрд
  - |v| >= 1 млн → 26,5 млн; 1 500 млн
  - |v| >= 1 тыс → 500 тыс; 1 250 тыс
  - |v| < 1 тыс → пиши полностью: 50 руб
- Десятичный разделитель — запятая
- Любые тысячные доли ОБЯЗАТЕЛЬНО группируй пробелами: 1 000, 1 000 000, 1 777 000
- Никаких пробелов между числом и суффиксом: "1 млрд", "1 777 млрд", "500 тыс"
- Никогда не пиши "1000000" или "1000000 млрд" — всегда сокращай и группируй
- Примеры:
  - ПРАВИЛЬНО: "1 777 млрд", "1 000 000 млн", "1 250 тыс"
  - НЕПРАВИЛЬНО: "1777 млрд", "1000000 млн", "1250 тыс"

### 3. ALIASES (КРИТИЧНО)
- Используй {{plan_alias}} и {{fact_alias}} КАК ЕСТЬ — БЕЗ СКЛОНЕНИЯ
- Если {{plan_alias}} = "Прогноз" → пиши "Прогноз", НЕ "Прогноза", НЕ "Прогнозу"
- Если {{fact_alias}} = "Факт по ЧПД" → пиши "Факт по ЧПД", НЕ "Факта по ЧПД"
- Используй эти алиасы в контексте: "Итоговые значения {alias1} и {alias2} указаны..."

### 4. NO "РУБ." (КРИТИЧНО)
- НИКОГДА не пиши "руб." после чисел
- "млн" и "тыс." — достаточные суффиксы
- Пример: "{plan_alias} 80 млн" — ПРАВИЛЬНО
- Пример: "{plan_alias} 80 млн руб." — НЕПРАВИЛЬНО

### 5. STRUCTURE
Текст должен содержать:
1. Уведомление что данные скорректированы
2. Данные ДО корректировки (только что есть)
3. Саму корректировку (только что есть)

ПРАВИЛЬНЫЙ пример (plan + fact):
⚠️ Итоговые значения {plan_alias} и {fact_alias} указаны с учётом мотивационной корректировки.
Данные до корректировки: {plan_alias} 81,5 млрд, {fact_alias} 84,5 млрд.
Мотивационная корректировка: {plan_alias} 1 млн, {fact_alias} 15 млрд.

ПРАВИЛЬНЫЙ пример (большие числа — группируй пробелами):
⚠️ Итоговые значения {plan_alias} и {fact_alias} указаны с учётом мотивационной корректировки.
Данные до корректировки: {plan_alias} 1 777 млрд, {fact_alias} 2 345 млрд.
Мотивационная корректировка: {plan_alias} 1 500 млн, {fact_alias} 25 000 тыс.

ПРАВИЛЬНЫЙ пример (только plan):
⚠️ Итоговое значение {plan_alias} указано с учётом мотивационной корректировки.
Данные до корректировки: {plan_alias} 80 млрд.
Мотивационная корректировка: {plan_alias} 10 млрд.

ПРАВИЛЬНЫЙ пример (только fact):
⚠️ Итоговое значение {fact_alias} указано с учётом мотивационной корректировки.
Данные до корректировки: {fact_alias} 83 млрд.
Мотивационная корректировка: {fact_alias} 10 млрд.

### 6. SINGULAR/PLURAL
- Один алиас → "Итоговое значение" (единственное)
- Два алиаса → "Итоговые значения" (множественное)

### 7. OUTPUT
Output: ONLY the motiv block text (no headers, no bullets)
Start with "⚠️"
"""

MOTIV_PROMPT = _MOTIV_BLOCK


class SummarizerPrompt:
    """Backward-compatible interface."""
    SHORT_SUMMARY_PROMPTS = SHORT_SUMMARY_PROMPTS
    KEY_FACTORS_PROMPTS = KEY_FACTORS_PROMPTS
    SUMMARY_PROMPT_PAIRS = SUMMARY_PROMPT_PAIRS
    BRANCH_TITLE = BRANCH_TITLE
    MOTIV_PROMPT = MOTIV_PROMPT
