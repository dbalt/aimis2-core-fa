# -*- coding: utf-8 -*-
"""
summarize_prompts.py — промпты саммаризации ФА (уровень A, AIMIS-2173)
=======================================================================

Числа в отчёте пишет КОД: каждый узел входных данных содержит объект
`display` с готовыми строками (план/факт/отклонение/вклад, маркер,
флаг значимости, пара «п.п. + рубли» для ratio). LLM ТОЛЬКО цитирует
готовые строки — вычисления, смены масштаба и перегруппировки разрядов
запрещены (см. правило QUOTING в общих секциях).
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from types import SimpleNamespace

from .precompute_config import MODE_CODE, pct_str, validate_precompute_cfg
from . import summarize_prompts_legacy as _legacy_prompts


# ===========================================================================
#                    О Б Щ И Е   ПРАВИЛА   (для всех разделов)
# ===========================================================================
_COMMON_FACTORS = """
## DATA STRUCTURE

Input format:
{
    "data": [ tree1, tree2, ... ],  // ОДНО отклонение, разложенное по разным осям
    "scale_info": {
        "scale": "млрд",        // справочно; строки чисел уже готовы в display
        "scale_full": "млрд руб.",
        "scale_factor": 1000000000
    }
}

Each tree has:
- hieararchy_node: название показателя
- analytic_slice: { "Разрез": "значение" } — аналитический разрез
- amounts: { plan, fact, deviation, impact_to_top_lvl } — СЫРЫЕ числа (НЕ для текста!)
{{display_structure}}
- details: { type, deviation_amounts, top_factors[] } — дочерние узлы
{{names_field}}

## CORE RULES

{{numbers_rule}}

{{names_rule}}
{{children_rule}}

{{marker_rule}}

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
Нет: "сценарий", "разрез", "срез", "алгоритм", "drill-down", "top_factors", "impact_to_top_lvl", "display", "marker", "significant".
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
{{numbers_formatting}}

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
⚠️ ПОСЛЕ списка факторов — НИЧЕГО не писать. Никаких заключительных предложений,
«хвостов», резюме, объяснений. Список факторов = КОНЕЦ ответа.

Ветка 2 (корень +, нет 🔴):
## Краткое саммари
2-4 предложения про ❇️ перевыполнение.

## Ключевые факторы
❇️-факторы (до 6).
⚠️ ПОСЛЕ списка факторов — НИЧЕГО не писать. Никаких заключительных предложений,
«хвостов», резюме, объяснений. Список факторов = КОНЕЦ ответа.

Ветка 3 (корень −):
## Краткое саммари
2-4 предложения про 🔴 отклонение.

## Ключевые факторы
🔴-факторы (только значимые).

---

## FINAL CHECKLIST (обязательно перед отправкой)

{{factors_common_checklist}}
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
- amounts: { plan, fact, deviation, impact_to_top_lvl } — СЫРЫЕ числа (НЕ для текста!)
{{display_structure}}
- details: { type, deviation_amounts, top_factors[] } — дочерние узлы
{{names_field}}

## CORE RULES

- ALL 🔴/❇️ FACTORS ARE TAKEN ONLY FROM impact_to_top_lvl
- ВСЕ числа — только цитаты display-строк (см. правило 1 QUOTING)

{{numbers_rule}}

{{names_rule}}
{{children_rule}}

{{marker_rule}}

### 3. NO TIME DYNAMICS (запрещено)
НИКОГДА не пиши: "снижение", "снизился", "падение", "упал", "рост", "вырос", "увеличение", "прирост", "снижением", "ростом", "рост прибыли", "рост дохода", "снижение расходов".
Используй маркеры: 🔴 "прочие доходы (−0,84 млн)" или ❇️ "процентный доход (+200 млн)".
❌ «Ключевыми драйверами роста прибыли стали операционный доход и экономия на расходах»
❌ «снижением операционных расходов»
✅ «Операционные расходы — +5,7 млрд» (поскольку вклад положительный)

### 4. ONLY DIRECT CHILDREN (обязательно)
В "Ключевых факторах" — ТОЛЬКО прямые потомки корня (первый уровень top_factors).
НЕ включай внуков, правнуков и т.д. в основной список.

### 5. ONE TREE, ONE OUTPUT
Если data = [tree1, tree2, ...] — это ОДНО отклонение, разложенное по разным осям.
Выводи каждый tree в отдельной секции, НЕ дублируя корневой показатель.

### 6. NO TECHNICAL TERMS
Нет: "сценарий", "разрез", "срез", "алгоритм", "drill-down", "top_factors", "impact_to_top_lvl", "display", "marker", "significant".
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
{{numbers_formatting}}

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
⚠️ ПОСЛЕ списка факторов — НИЧЕГО не писать. Никаких заключительных предложений,
«хвостов», резюме, объяснений. Список факторов = КОНЕЦ ответа.

Ветка 2 (корень +, нет 🔴):
## Краткое саммари
2-4 предложения про ❇️ перевыполнение.

## Ключевые факторы
❇️-факторы (до 6).
⚠️ ПОСЛЕ списка факторов — НИЧЕГО не писать. Никаких заключительных предложений,
«хвостов», резюме, объяснений. Список факторов = КОНЕЦ ответа.

Ветка 3 (корень −):
## Краткое саммари
2-4 предложения про 🔴 отклонение.

## Ключевые факторы
🔴-факторы (только значимые).

---

## FINAL CHECKLIST (обязательно перед отправкой)

{{summary_common_checklist}}

{{summary_final_instruction}}
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
- ❌ НЕ ПИШИ после ## Краткое саммари никаких заключительных абзацев.
  Саммари = 2-4 предложения. После них — КОНЕЦ. Никаких «ключевыми драйверами роста прибыли стали...» и прочего.

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
- **SOURCE OF TRUTH for all impact values: display.impact** (он уже посчитан из impact_to_top_lvl).
- Секции по осям: каждое дерево данных = одна секция. Секция выводится, если
  у дерева есть дети или значимое отклонение. Дерево БЕЗ детей и без значимого
  отклонения секции НЕ порождает — и это НЕ нарушение полноты вывода.
  Не выдумывай факторы, чтобы «заполнить» ось.
{{selection_rule}}
- If N-th factor and (N+1)-th differ < {{similarity_pct}}% → include both (up to 6 total per axis)
- If only 1 significant child → output 1 bullet (not a problem)
- Get to the root of negative impacts ONLY via existing child nodes in the JSON.
  If a factor has no children — stop at its display.impact quote; do NOT invent
  causes or sub-factors.
- ALL 🔴/❇️ FACTORS ARE TAKEN ONLY FROM display (impact/marker)

{{leaf_rule}}

### CRITICAL RULE: PRESERVE ALL ANALYTICAL DIMENSIONS
- **NEVER skip any analytical slice** even if its impact is small relative to Pareto threshold
- **NEVER skip entire analytical dimensions** represented as separate trees in data array
  (пустые деревья — см. Selection rules: секция не выводится, факторы НЕ выдумываются)
- **Pareto 80% rule does NOT apply to slices from same analytical dimension**: all slices from one dimension must be reported together as a group
- Exception: only if factor is absolutely trivial (|impact| < 0.01% of root deviation AND |impact| < 1 млн)

### CRITICAL RULE: TRUNCATION WITH PRIORITY
- If inclusion of ALL slices exceeds 10 items:
  - First, keep ALL slices from dimensions that represent major business axes (such as business blocks, channels, territories)
  - Then, keep ALL slices from core component breakdowns
  - Finally, truncate least significant factors (starting from deepest nesting level)
  - **Priority order**: Major business axes > Core components > Product/feature breakdowns

### Structure
- Top level: {marker} **Measure name** — <цитата display.impact>
- Nested 2nd level: driver (components or algorithm 7.2)
- Nested 3rd level: slice breakdown (if present)

### Nested levels
1. Component driver: "Главный драйвер — {marker} <имя дочернего узла из JSON> (<цитата его display.impact>)"
   - Применимо ТОЛЬКО к узлам с детьми (см. LEAF EDGE CASE).
   - Apply algorithm 7.2: ratio = |child.impact_to_top_lvl| / |parent.impact_to_top_lvl|
   - Single child ratio >= 0.90 → compress into parent
   - Multiple siblings ratio < 2 → output 2-3 separate bullets
2. Slice breakdown: "в том числе:" with 2-3 slice values (цитаты display-строк)

### For branch 3 (only 🔴):
- All nested levels show only 🔴 components
- No ❇️ components in nesting

---

## FINAL CHECKLIST

{{factors_base_checklist}}

{{factors_final_instruction}}
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

Example (числа в примере ИЛЛЮСТРАТИВНЫЕ — в реальном тексте только цитаты display):
Корневой показатель перевыполнил **{{plan_alias}}** на <цитата display.deviation корня> (факт — <цитата display.fact>, **{{plan_alias}}** — <цитата display.plan>). Основной вклад внесли ❇️ Чистый процентный доход (<цитата display.impact>) и ❇️ Прочие чистые операционные доходы (<цитата display.impact>).
"""

_SHORT_SUMMARY_BRANCH_3 = _BASE_SUMMARY + """
## TASK (BRANCH 3)

Root ОТКЛОНЯЕТСЯ от плана (negative impact).
Only 🔴-факторы, ❇️-факторы НЕ показывать.

Output: 2-4 sentences
1. Root measure + actual value + **{{plan_alias}}** + total 🔴 deviation
2. List 1-2 largest 🔴-factors (direct children)
3. Never mention compensation or ❇️ factors

Example (числа в примере ИЛЛЮСТРАТИВНЫЕ — в реальном тексте только цитаты display):
Корневой показатель отклонился от **{{plan_alias}}** на <цитата display.deviation корня> (факт — <цитата display.fact>, **{{plan_alias}}** — <цитата display.plan>). Отклонение обусловлено 🔴 Прочими чистыми операционными доходами (<цитата display.impact>) и 🔴 ОД до резервов (<цитата display.impact>).
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
   - If N-th and (N+1)-th differ < {{similarity_pct}}% → include both
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
- {display.marker} **Measure** — отклонение от **{{plan_alias}}** на <цитата display.impact>
- {display.marker} **Measure** — перевыполнил **{{plan_alias}}**, вклад <цитата display.impact>
"""

_KEY_FACTORS_BRANCH_2 = _BASE_FACTORS + """
## TASK (BRANCH 2)

Root выполняет/перевыполняет план (positive impact), 🔴-факторов НЕТ.

Output: section `## Ключевые факторы`

Structure:
- If multiple trees: separate sections for each with header
- If one tree: flat list without subheaders

Contents:
- Up to 6 ❇️-factors (direct children, by |impact| desc)
- If significant < 6, output actual count (no fillers)

Format: ❇️ **Measure** — impact <цитата display.impact>. Optional driver sentence (только для узлов с детьми, см. LEAF EDGE CASE).
Nested: slice breakdown if present (цитаты display-строк).

Format example:
- ❇️ **Measure** — перевыполнил **{{plan_alias}}**, вклад <цитата display.impact>
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
   - Add "в том числе:" with 2-3 largest 🔴 slice values (цитаты display.impact)

Format:
- Top level: 🔴 **Measure** — отклонение от **{{plan_alias}}** на <цитата display.impact>
- Nested: 🔴 <component> (<цитата display.impact>) or 🔴 <slice> (<цитата display.impact>)
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
 - amounts: { plan, fact, deviation, impact_to_top_lvl } — СЫРЫЕ числа (НЕ для текста!)
 - display: { plan, fact, deviation, impact, marker, significant, margin_impact, margin_rub }
   — ГОТОВЫЕ СТРОКИ. ЕДИНСТВЕННЫЙ источник чисел для текста.
 - details: { type, top_factors[] }
 - analytic_slice: { "Разрез": "значение" }

Твоя задача написать краткое саммари по этому дереву.
Взять значение из корня дерева (display корня: план/факт/отклонение — уже в % и п.п.),
это значение самое важное, его всегда надо писать.
Написать в саммари его потомков, т.е. объяснить как получается это значение.
Объясни почему оно отклоняется от факта, напиши влияние потомков.
Не используй сложно подчененных предложений, в каждом предложении пиши не больше 10 слов в предложении. (критично)

### QUOTING (КРИТИЧНО — единственный способ писать числа)
Каждое число в тексте — ПОСИМВОЛЬНАЯ КОПИЯ строки из display соответствующего узла:
- план/факт/отклонение корня = display.plan / display.fact / display.deviation (уже % и п.п.);
- вклад потомка = display.impact (уже п.п. для корня и прямых потомков);
- рублёвый эквивалент вклада = display.margin_rub (только у прямых потомков корня).
ЗАПРЕЩЕНО: умножать на 100, делить, выбирать масштаб, менять разряды
(млн ↔ млрд ↔ тыс.), менять запятую/пробелы, менять знак.
Сырые числа из amounts НЕ использовать.

### QUOTING NAMES (КРИТИЧНО — второй источник выдумок)
В данных есть массив "allowed_names" — ЕДИНСТВЕННЫЙ список разрешённых имён
(все узлы JSON). Пиши имена ТОЛЬКО из него, в любом падеже.
Имени нет в allowed_names → фактор НЕ упоминается вовсе.
Если у фактора нет детей в JSON — НЕ строй его декомпозицию и НЕ объясняй
причины: достаточно «{marker} **Имя** — <цитата display.impact>».

### ШАБЛОН ВКЛАДА ПОТОМКА КОРНЯ (обязателен для каждого прямого потомка)
«отклонение маржи составило <цитата display.margin_impact>, что оказало влияние
на верхнеуровневый показатель в <цитата display.margin_rub>»
Пример: «отклонение маржи составило -26,4 п.п., что оказало влияние на
верхнеуровневый показатель в +300 тыс.» (строки взяты из display узла).

### Листовые узлы (нет details.top_factors): НЕ выдумывай драйверы и причины —
только {marker} **Имя** + цитата display.impact.

### Маркеры (обязательно)
Маркер берётся из display.marker — САМ не вычисляй.
🔴 = отрицательный вклад (факт хуже плана)
❇️ = положительный вклад (факт лучше плана)
Знак числа из display уже согласован с маркером.
Нет других эмодзи (🟢 ЗАПРЕЩЁН).
Положительный вклад никогда не называй отклонением.

### 2. Масштаб (обязательно)
- Игнорируй всё, что написано в scale_info (критично) — все строки уже в display.

### 3. NO DYNAMICS: НИКОГДА не пиши "рост", "снижение", "падение", "прирост", "увеличение". Используй маркеры и статичные формулировки.

### 4. ALIASES: Используй plan_alias / fact_alias. Если пустые — "План"/"Факт".

### 5. TECHNICAL TERMS: Нет "разрез", "drill-down", "top_factors", "детализация по компонентам", "display", "marker", "significant".

### 6. DETAILS FIELD: В этом разделе поле details.type = "Детализация по:" ИГНОРИРУЙ. Выводи его ТОЛЬКО в разделе "## Ключевые факторы".


 ## OUTPUT FORMAT (СТРОГО СЛЕДУЙ)

 Выведи ТОЛЬКО заголовок `## Краткое саммари` и сразу за ним один абзац текста.

 ЗАПРЕЩЕНО:
 - Подзаголовки (`###`, `## Ключевые факторы`, `### Детализация`)
 - Маркированные/нумерованные списки (`-`, `*`, `1.`)
 - План/факт для дочерних узлов
 - Вложенные структуры, таблицы, списки компонентов
 - Дублирование разметки второго раздела
 - Числа, не являющиеся посимвольными цитатами display-строк

 Текст: 2-3 предложения сплошным абзацем:
 1. Root: название + план + факт + отклонение в п.п. (цитаты display корня)
 2. Ключевые драйверы отклонения (🔴 и ❇️ по display, с шаблоном маржи)
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
- amounts: { plan, fact, deviation, impact_to_top_lvl } — СЫРЫЕ числа (НЕ для текста!)
- display: { plan, fact, deviation, impact, marker, significant, margin_impact, margin_rub }
  — ГОТОВЫЕ СТРОКИ. ЕДИНСТВЕННЫЙ источник чисел для текста.
  У корня и прямых потомков корня: impact — в п.п., margin_rub — рублёвый эквивалент.
  У вложенных узлов и срезов: все строки — абсолютные (млрд/млн/тыс./руб.).
- details: { type, top_factors[] }
- analytic_slice: { "Разрез": "значение" }
- flg_rate_type: true/false

---

## CORE RULES

### 1. QUOTING NUMBERS (КРИТИЧНО — единственный способ писать числа)
Каждое число в тексте — ПОСИМВОЛЬНАЯ КОПИЯ строки из display соответствующего узла.
- НЕ УМНОЖАЙ НИЧЕГО НА 100 — проценты/п.п. уже посчитаны кодом и лежат в display.
- НЕ выбирай масштаб и НЕ меняй разряды — млн/млрд/тыс. уже выбраны кодом.
- НЕ меняй запятую, пробелы, знак, суффиксы.
- Сырые числа из amounts НЕ использовать.
Пример правильного подхода:
  display: { plan: "200 %", fact: "178 %", deviation: "-21,7 п.п.", impact: "-26,4 п.п.", margin_rub: "+300 тыс." }
  → в тексте РОВНО эти строки.

### 1b. QUOTING NAMES (КРИТИЧНО — второй источник выдумок)
Каждое имя фактора — из JSON (hieararchy_node), в любом падеже.
ЗАПРЕЩЕНО упоминать факторы, которых НЕТ в JSON, даже типичные для банка.
Если у фактора нет детей в JSON — НЕ строй его декомпозицию и НЕ объясняй
причины: достаточно «{marker} **Имя** — <цитата display.impact>».

### ШАБЛОН ВКЛАДА ПРЯМОГО ПОТОМКА КОРНЯ (обязателен)
Для каждого прямого потомка корня указывай вклад шаблоном:
«отклонение маржи составило <цитата display.margin_impact>, что оказало влияние
на верхнеуровневый показатель в <цитата display.margin_rub>»

### 2. МАСШТАБ
Игнорируй scale_info — все строки уже в display.

### 3. МАРКЕРЫ
Маркер берётся из display.marker — САМ не вычисляй.
🔴 = отрицательный вклад (факт хуже плана)
❇️ = положительный вклад (факт лучше плана)
Знак числа из display уже согласован с маркером.
Нет других эмодзи (🟢 ЗАПРЕЩЁН).

### 4. LEAF EDGE CASE (КРИТИЧНО)
У узла нет детей (details.top_factors пуст) → НЕ выдумывай драйверы, причины
и состав: только {marker} **Имя** + цитата display.impact.
НЕ переупаковывай plan/fact узла в «драйвер» его отклонения.

### 5. NO DYNAMICS (запрещено)
НИКОГДА не пиши: "рост", "снижение", "падение", "прирост", "увеличение", "увеличилось", "увеличился", "вырос", "упал".
Используй статичные формулировки:
- "🔴 кредитный портфель (<цитата display.impact>)"
- "❇️ расходы на резервы (<цитата display.impact>)"

### 6. ALIASES
Используй plan_alias / fact_alias. Если пустые — "План"/"Факт".

### 7. TECHNICAL TERMS (запрещено)
Нет: "разрез", "drill-down", "top_factors", "детализация по компонентам", "display", "marker", "significant".
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
- Числа, не являющиеся посимвольными цитатами display-строк

---

## OUTPUT STRUCTURE

### Если несколько деревьев → секция для каждого с ## заголовком
- tree 1: `## Ключевые факторы`
- tree 2+: `## Ключевые факторы (по [analytic_slice])`

### Если одно дерево → плоский список без подзаголовков

### Contents (по display, |impact| desc):

1. **Корневой показатель** (первое дерево)
   - Указать план %, факт %, отклонение п.п. — цитаты display корня.
   - Пример: "**Стоимость риска (COR)**: план <display.plan>, факт <display.fact>, отклонение <display.deviation>"

2. **Прямые потомки корня** (первый уровень top_factors)
   - Вклад — цитата display.impact (уже в п.п.), ОБЯЗАТЕЛЬНО шаблон маржи
     («отклонение маржи составило <display.margin_impact>, что оказало влияние
     на верхнеуровневый показатель в <display.margin_rub>»).

3. **Детализация по разрезам** (если details.type содержит срезы)
   - Цитаты display-строк (абсолютные величины — уже готовы).
   - Формат:
     - в том числе:
       - 🔴 **Розничный сегмент** (<цитата display.impact>)
       - ❇️ **Корпоративный сегмент** (<цитата display.impact>)

### Формат bullets:

**Процентные факторы** (root + прямые потомки):
- {display.marker} **Название** — отклонение от **{{plan_alias}}**, <цитата display>
- {display.marker} **Название** — перевыполнил **{{plan_alias}}**, вклад <цитата display>

**Абсолютные факторы** (вложенные узлы, analytic_slice):
- {display.marker} **Название** — отклонение, <цитата display>
- {display.marker} **Название** — вклад, <цитата display>

---

## RATIO-SPECIFIC NOTES

- Root → цитаты display (уже % / п.п.)
- Прямые потомки → цитата display.impact (уже п.п.) + шаблон маржи с display.margin_rub
- Вложенные узлы → цитаты display (уже абсолютные)
- analytic_slice → цитаты display (уже абсолютные)
- Если children нет → не выводи секцию (Tree != Root), факторы НЕ выдумывать

---

## COMMON FORMATTING

- Запятая и группировка разрядов уже внутри display-строк — цитируй посимвольно.
- Жирный: **названия показателей** (не числа)
- Маркеры: 🔴 ❇️ (только из display.marker)

### Пример формата (строки ИЛЛЮСТРАТИВНЫЕ — в реальном тексте цитаты display):
## Ключевые факторы

- 🔴 **Стоимость риска (COR)** — отклонение от **Прогноз**, <display.deviation корня>
  - в том числе:
    - 🔴 **Кредитный портфель** — отклонение маржи составило <display.margin_impact>, что оказало влияние на верхнеуровневый показатель в <display.margin_rub>
      - в том числе:
        - 🔴 **Розничный сегмент** (<display.impact>)
        - ❇️ **Корпоративный сегмент** (<display.impact>)
"""


# ===========================================================================
#   Ф Р А Г М Е Н Т Ы   П Р А В И Л   П О Д   К О Н Ф И Г   П Р Е Д В Ы Ч И С Л Е Н И Й
# ===========================================================================
# Слоты {{...}} в константах выше заполняются по конфигу предвычислений
# (precompute_config.py): mode="code" — актуальные правила (числа/маркеры/
# отбор готовит код, LLM цитирует), mode="llm" — правила legacy-промптов
# (LLM считает сама). Фрагменты code-режима ниже — дословный текст, вырезанный
# на места слотов: дефолтный конфиг (всё code) даёт тексты, бит-в-бит равные
# исходным промптам (эталон — tests/golden_prompts_precompute.json).

# --- code-фрагменты (вырезаны с мест слотов дословно) ---

_RULE_NUMBERS_CODE = """### 1. QUOTING NUMBERS (КРИТИЧНО — главный источник ошибок)
Каждое число в тексте — ПОСИМВОЛЬНАЯ КОПИЯ строки из display узла:
- вклад = display.impact; отклонение = display.deviation;
  план = display.plan; факт = display.fact.
- ЗАПРЕЩЕНО: считать, делить, умножать, выбирать масштаб, менять разряды
  (млн ↔ млрд ↔ тыс.), менять запятую/пробелы/суффиксы, менять знак.
- НЕ используй сырые числа из amounts — только строки из display.
- Пример: display.impact = "-535,5 млн" → в тексте РОВНО "-535,5 млн"."""

_RULE_NAMES_CODE = """### 1b. QUOTING NAMES (КРИТИЧНО — второй источник выдумок)
В данных есть массив "allowed_names" — ЕДИНСТВЕННЫЙ список разрешённых имён
(все узлы и аналитические срезы JSON). Пиши имена ТОЛЬКО из него, в любом падеже.
Имени нет в allowed_names → фактор НЕ упоминается вовсе. Запрещено достраивать
типовую структуру банка («чистый процентный доход», «расходы на персонал»,
«страховые выплаты» и т.п.) — если её нет в allowed_names, её нет в отчёте."""

_RULE_CHILDREN_CODE = """Если у фактора нет детей в JSON — НЕ строй его декомпозицию («в том числе: …»,
«Главный драйвер: …»): достаточно «{marker} **Имя** — <цитата display.impact>».
Не знаешь причину по данным — не пиши её: знания о типичной структуре банка ≠ данные."""

_RULE_MARKER_CODE = """### 2. MARKERS (обязательно)
Маркер каждого фактора берётся из display.marker — САМ не вычисляй.
🔴 = отрицательный вклад (факт хуже плана)
❇️ = положительный вклад (факт лучше плана)
Знак числа из display уже согласован с маркером.
Нет других эмодзи (🟢 ЗАПРЕЩЁН)."""

_NUMBERS_FORMATTING_CODE = """- ВСЕ числа в тексте — посимвольные цитаты display-строк (правило 1 QUOTING).
- Своё форматирование запрещено: масштаб, запятая, группировка уже в display.
- `flg_rate_type: true` → display уже содержит % / п.п. — цитируй как есть."""

_SELECTION_RULE_CODE = """- Включай факторы ТОЛЬКО с display.significant = true (порог значимости
  уже посчитан кодом; НЕ пересчитывай и не «добавляй по собственному суждению»)."""

_LEAF_RULE_CODE = """### LEAF EDGE CASE (КРИТИЧНО — источник выдуманных драйверов)
«Главный драйвер — ...» разрешён ТОЛЬКО если у фактора ЕСТЬ дети в JSON
(details.top_factors не пуст), а источник драйвера — имя СУЩЕСТВУЮЩЕГО
дочернего узла. Если у фактора нет детей (лист):
- НЕ пиши «Главный драйвер», не указывай вложенные причины и состав,
- НЕ используй обороты «за счёт», «вследствие», «благодаря» с именами,
  которых нет в JSON (даже «правдоподобные»: резервы, комиссии, персонал),
- НЕ переупаковывай значения plan/fact узла в «драйвер» его отклонения,
- просто: {marker} **Имя** — <цитата display.impact>. Этого достаточно."""

_DISPLAY_STRUCTURE_CODE = """- display: { plan, fact, deviation, impact, marker, significant } — ГОТОВЫЕ СТРОКИ
  чисел, маркер (🔴/❇️/"") и флаг значимости. ЕДИНСТВЕННЫЙ источник чисел для текста.
  У узлов с детьми есть ещё display.children_names — имена ЕГО прямых детей."""

_NAMES_FIELD_CODE = "- allowed_names: [ ... ] — ЕДИНСТВЕННЫЙ список имён, которые можно писать в тексте"

_FACTORS_COMMON_CHECKLIST_CODE = """1. ✅ Маркеры взяты из display.marker и совпадают со знаками чисел
2. ✅ В "Ключевых факторах" только прямые потомки корня
3. ✅ Нет слов динамики ("снижение", "падение", "рост" и т.д.)
4. ✅ КАЖДОЕ число — посимвольная цитата display-строки (ничего не пересчитано)
5. ✅ В ветке 3 нет ❇️-факторов, в ветке 2 нет 🔴-факторов
6. ✅ Нет дублирующихся узлов (родитель + доминирующий потомок)
7. ✅ Транзитные цепочки сжаты (алгоритм 7.2)
8. ✅ «Главный драйвер» только у узлов с детьми; имя драйвера есть в JSON
9. ✅ Все имена факторов — из JSON; ни одного придуманного имени/подфактора"""

_SUMMARY_COMMON_CHECKLIST_CODE = """1. ✅ Маркеры взяты из display.marker и совпадают со знаками чисел
2. ✅ В "Ключевых факторах" только прямые потомки корня
3. ✅ Нет слов динамики ("снижение", "падение", "рост" и т.д.)
4. ✅ КАЖДОЕ число — посимвольная цитата display-строки (ничего не пересчитано)
5. ✅ В ветке 3 нет ❇️-факторов, в ветке 2 нет 🔴-факторов
6. ✅ Нет дублирующихся узлов (родитель + доминирующий потомок)
7. ✅ Транзитные цепочки сжаты (алгоритм 7.2)"""

_FACTORS_BASE_CHECKLIST_CODE = """1. ✅ Only direct children in main list (no grandchildren)
2. ✅ Each factor has marker from display.marker with matching sign
3. ✅ No duplicates (parent + dominant child)
4. ✅ Transit chains compressed (algorithm 7.2)
5. ✅ Top 6 limit respected (but not a quota)
6. ✅ КАЖДОЕ число — посимвольная цитата display-строки (ничего не пересчитано)
7. ✅ «Главный драйвер» только у узлов с детьми; имена драйверов есть в JSON"""

# --- хвост «ПОСЛЕДНЯЯ ИНСТРУКЦИЯ» — собирается из под-блоков по режимам ---

_TAIL_HEAD = """## ⚠️ ПОСЛЕДНЯЯ ИНСТРУКЦИЯ (перечитай ПЕРЕД ответом)
JSON в следующем сообщении — ЕДИНСТВЕННЫЙ источник имён и чисел."""
_TAIL_NAMES = "Разрешённые имена — ТОЛЬКО из массива \"allowed_names\" в данных."
_TAIL_CHILDREN = """У узла нет children (details.top_factors пуст) → вся строка фактора:
«{marker} **Имя** — <цитата display.impact>». Без «в том числе», без драйверов,
без причин. Любое имя или число не из JSON — грубая ошибка.
❌ «Главный драйвер — страховые выплаты (−6,1 млрд)» (страховые выплаты нет в JSON)
✅ «🔴 Корпоративное страхование — -6,2 млрд»"""
_TAIL_SIGN = """ЗНАК ОБЯЗАТЕЛЕН при цитировании plan/fact: расходные статьи в JSON отрицательны,
цитируй РОВНО как в display: «факт -15,7 млрд против плана -14,4 млрд».
❌ «(факт 15,7 млрд против плана 14,4 млрд)» — потерян минус
✅ «(факт -15,7 млрд против плана -14,4 млрд)»"""
_TAIL_DRIVER = """«Главный драйвер» — только «Главный драйвер — {marker} <имя из display.children_names
ЭТОГО узла> (<цитата его display.impact>)». Нет display.children_names у узла →
никаких драйверов, «в том числе», подпунктов и причин — только
«{marker} **Имя** — <цитата display.impact>». Имя ребёнка ДРУГОГО узла драйвером
быть не может (даже если оно есть в allowed_names).
❌ «Главный драйвер — страховые выплаты (−6,1 млрд)» (страховые выплаты нет в JSON)
❌ «Главный драйвер: рост выплат (−6,2 млрд)» (даже если "Корп. страхование" имеет
   children_names=["Прочие"], драйвер — ИМЕННО имя из children_names, а не описание)
✅ «🔴 Корпоративное страхование — -6,2 млрд» (у него нет display.children_names)"""
_TAIL_DYNAMICS = """Запрещены слова динамики: рост, вырос, снижение, снизился, увеличение, увеличился,
падение, прирост — вклады описывай ТОЛЬКО маркером и числом.
❌ «Ключевой вклад обеспечил рост операционного дохода»
❌ «Ключевым драйвером перевыполнения стал рост операционного дохода»
✅ «❇️ Операционный доход до резервов — +11,7 млрд»"""
_TAIL_ALLOWED = "Разрешённые имена (allowed_names): {{allowed_names}}"

# --- llm-фрагменты (источник: summarize_prompts_legacy.py — промпты до
# AIMIS-2173; legacy-модуль более НЕ удаляется: он baseline A/B-харнесса
# и источник правил llm-режима) ---

_RULE_NUMBERS_LLM = """### 1. SCALING (обязательно — числа форматируй САМИ по сырым amounts)
Базовая шкала: млн руб. При форматировании чисел из JSON:
- |v| >= 1 млн → X,XX млн (1 знак): 26,5
- |v| < 1 млн → X тыс. с достаточной точностью:
  - |v| >= 1 тыс. → 2 знака (500 тыс., 1,5 тыс.)
  - |v| < 1 тыс. → больше знаков, чтобы не округлить до 0 (5 руб. = 0,005 тыс.)
Действие: определи |v| из impact/plan/fact, выбери масштаб,
примени деление и suffix. Разделитель дробной части — запятая.
НИКОГДА не округляй ненулевое число до нуля."""

# names llm / children llm: ограничения не действуют (поведение legacy)
_RULE_NAMES_LLM = ""
_RULE_CHILDREN_LLM = ""

_RULE_MARKER_LLM = """### 2. MARKERS (обязательно)
🔴 = отрицательный вклад (факт хуже плана)
❇️ = положительный вклад (факт лучше плана)
Знак числа + или − должен совпадать с маркером.
Нет других эмодзи (🟢 ЗАПРЕЩЁН)."""

_NUMBERS_FORMATTING_LLM = """- Числа форматируй САМИ по правилу SCALING (правило 1): масштаб млн/тыс.,
  десятичный разделитель — запятая, группировка тысяч — пробел.
- `flg_rate_type: true` → план/факт = проценты (xxx.xxx%); 0 < |v| < 1 и
  процентный контекст → xxx.xxx% или x.xxx п.п. (×100 — самостоятельно)."""

_SELECTION_RULE_LLM = """- Включай факторы с |вкладом| >= {{threshold_pct}}% от максимального |вклада|
  среди соседних узлов (первый уровень top_factors); сверх этого правила
  факторы по собственному суждению НЕ добавляй."""


# ===========================================================================
#   С Б О Р К А   П Р О М П Т О В   П О   К О Н Ф И Г У
# ===========================================================================

_RAW_SHORT_PROMPTS: Dict[int, str] = {
    1: _SHORT_SUMMARY_BRANCH_1,
    2: _SHORT_SUMMARY_BRANCH_2,
    3: _SHORT_SUMMARY_BRANCH_3,
    4: _SHORT_SUMMARY_BRANCH_4,
}

_RAW_KEY_PROMPTS: Dict[int, str] = {
    1: _KEY_FACTORS_BRANCH_1,
    2: _KEY_FACTORS_BRANCH_2,
    3: _KEY_FACTORS_BRANCH_3,
    4: _KEY_FACTORS_BRANCH_4,
}


def _apply(text: str, pairs) -> str:
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def _compose_display_structure(cfg: Dict) -> str:
    """DATA STRUCTURE-бюллетень display: перечень полей по code-ручкам."""
    numbers_code = cfg["numbers"]["mode"] == MODE_CODE
    markers_code = cfg["markers"]["mode"] == MODE_CODE
    selection_code = cfg["selection"]["mode"] == MODE_CODE
    children_code = cfg["names"]["children"] == MODE_CODE
    if not numbers_code:
        # numbers=llm: display в данных нет вовсе
        return ""
    if markers_code and selection_code and children_code:
        return _DISPLAY_STRUCTURE_CODE  # golden-фрагмент дословно
    fields = ["plan", "fact", "deviation", "impact"]
    if markers_code:
        fields.append("marker")
    if selection_code:
        fields.append("significant")
    if markers_code and selection_code:
        detail = ", маркер (🔴/❇️/\"\") и флаг значимости."
    elif markers_code:
        detail = " и маркер (🔴/❇️/\"\")."
    elif selection_code:
        detail = " и флаг значимости."
    else:
        detail = "."
    lines = [
        "- display: { " + ", ".join(fields) + " } — ГОТОВЫЕ СТРОКИ",
        "  чисел" + detail + " ЕДИНСТВЕННЫЙ источник чисел для текста.",
    ]
    if children_code:
        lines.append(
            "  У узлов с детьми есть ещё display.children_names — имена ЕГО прямых детей."
        )
    return "\n".join(lines)


def _compose_final_instruction(cfg: Dict) -> str:
    """Хвост «ПОСЛЕДНЯЯ ИНСТРУКЦИЯ»: под-блоки по code-ручкам."""
    names_code = cfg["names"]["allowed"] == MODE_CODE
    children_code = cfg["names"]["children"] == MODE_CODE
    numbers_code = cfg["numbers"]["mode"] == MODE_CODE
    head = _TAIL_HEAD
    if names_code:
        head += "\n" + _TAIL_NAMES
    if children_code:
        head += "\n" + _TAIL_CHILDREN
    blocks = [head]
    if numbers_code:
        blocks.append(_TAIL_SIGN)
    if children_code:
        blocks.append(_TAIL_DRIVER)
    blocks.append(_TAIL_DYNAMICS)
    if names_code:
        blocks.append(_TAIL_ALLOWED)
    return "\n\n".join(blocks)


def _fill_slots(text: str, cfg: Dict) -> str:
    """Заполняет слоты {{...}} фрагментами по режимам конфига."""
    markers_code = cfg["markers"]["mode"] == MODE_CODE
    selection_code = cfg["selection"]["mode"] == MODE_CODE
    children_code = cfg["names"]["children"] == MODE_CODE
    names_code = cfg["names"]["allowed"] == MODE_CODE
    numbers_code = cfg["numbers"]["mode"] == MODE_CODE

    thr_pct = pct_str(cfg["selection"]["threshold"])
    sim_pct = pct_str(cfg["selection"]["similarity"])

    numbers_rule = _RULE_NUMBERS_CODE if numbers_code else _RULE_NUMBERS_LLM
    names_rule = _RULE_NAMES_CODE if names_code else _RULE_NAMES_LLM
    children_rule = _RULE_CHILDREN_CODE if children_code else _RULE_CHILDREN_LLM
    marker_rule = _RULE_MARKER_CODE if markers_code else _RULE_MARKER_LLM
    numbers_fmt = _NUMBERS_FORMATTING_CODE if numbers_code else _NUMBERS_FORMATTING_LLM
    selection_rule = _SELECTION_RULE_CODE if selection_code else \
        _SELECTION_RULE_LLM.replace("{{threshold_pct}}", thr_pct)
    leaf_rule = _LEAF_RULE_CODE if children_code else ""
    display_structure = _compose_display_structure(cfg)
    names_field = _NAMES_FIELD_CODE if names_code else ""

    marker_item = "1. ✅ Маркеры взяты из display.marker и совпадают со знаками чисел" \
        if markers_code else "1. ✅ Маркеры совпадают со знаками чисел"
    marker_item_en = "2. ✅ Each factor has marker from display.marker with matching sign" \
        if markers_code else "2. ✅ Each factor has marker with matching sign"
    numbers_item = "4. ✅ КАЖДОЕ число — посимвольная цитата display-строки (ничего не пересчитано)" \
        if numbers_code else "4. ✅ Все числа отформатированы по правилу SCALING (млн/тыс.)"
    numbers_item_en = "6. ✅ КАЖДОЕ число — посимвольная цитата display-строки (ничего не пересчитано)" \
        if numbers_code else "6. ✅ Все числа отформатированы по правилу SCALING (млн/тыс.)"
    driver_item = "8. ✅ «Главный драйвер» только у узлов с детьми; имя драйвера есть в JSON" \
        if children_code else "8. ✅ Драйверы — только имена существующих узлов JSON"
    driver_item_en = "7. ✅ «Главный драйвер» только у узлов с детьми; имена драйверов есть в JSON" \
        if children_code else "7. ✅ Драйверы — только имена существующих узлов JSON"

    factors_common_checklist = "\n".join([
        marker_item,
        "2. ✅ В \"Ключевых факторах\" только прямые потомки корня",
        "3. ✅ Нет слов динамики (\"снижение\", \"падение\", \"рост\" и т.д.)",
        numbers_item,
        "5. ✅ В ветке 3 нет ❇️-факторов, в ветке 2 нет 🔴-факторов",
        "6. ✅ Нет дублирующихся узлов (родитель + доминирующий потомок)",
        "7. ✅ Транзитные цепочки сжаты (алгоритм 7.2)",
        driver_item,
        "9. ✅ Все имена факторов — из JSON; ни одного придуманного имени/подфактора",
    ]) if names_code else "\n".join([
        marker_item,
        "2. ✅ В \"Ключевых факторах\" только прямые потомки корня",
        "3. ✅ Нет слов динамики (\"снижение\", \"падение\", \"рост\" и т.д.)",
        numbers_item,
        "5. ✅ В ветке 3 нет ❇️-факторов, в ветке 2 нет 🔴-факторов",
        "6. ✅ Нет дублирующихся узлов (родитель + доминирующий потомок)",
        "7. ✅ Транзитные цепочки сжаты (алгоритм 7.2)",
        driver_item,
    ])

    summary_common_checklist = "\n".join([
        marker_item,
        "2. ✅ В \"Ключевых факторах\" только прямые потомки корня",
        "3. ✅ Нет слов динамики (\"снижение\", \"падение\", \"рост\" и т.д.)",
        numbers_item,
        "5. ✅ В ветке 3 нет ❇️-факторов, в ветке 2 нет 🔴-факторов",
        "6. ✅ Нет дублирующихся узлов (родитель + доминирующий потомок)",
        "7. ✅ Транзитные цепочки сжаты (алгоритм 7.2)",
    ])

    factors_base_checklist = "\n".join([
        "1. ✅ Only direct children in main list (no grandchildren)",
        marker_item_en,
        "3. ✅ No duplicates (parent + dominant child)",
        "4. ✅ Transit chains compressed (algorithm 7.2)",
        "5. ✅ Top 6 limit respected (but not a quota)",
        numbers_item_en,
        driver_item_en,
    ])

    return _apply(text, [
        ("{{numbers_rule}}", numbers_rule),
        ("{{names_rule}}", names_rule),
        ("{{children_rule}}", children_rule),
        ("{{marker_rule}}", marker_rule),
        ("{{numbers_formatting}}", numbers_fmt),
        ("{{display_structure}}", display_structure),
        ("{{names_field}}", names_field),
        ("{{selection_rule}}", selection_rule),
        ("{{leaf_rule}}", leaf_rule),
        ("{{factors_common_checklist}}", factors_common_checklist),
        ("{{summary_common_checklist}}", summary_common_checklist),
        ("{{factors_base_checklist}}", factors_base_checklist),
        ("{{summary_final_instruction}}", _compose_final_instruction(cfg)),
        ("{{factors_final_instruction}}", _compose_final_instruction(cfg)),
        ("{{similarity_pct}}", sim_pct),
    ])


# Точечные замены для llm-ручек в смешанных режимах (numbers=code):
# ссылки на display-поля, которых при llm-режиме в данных нет.
_MIXED_PAIRS = {
    "markers": [
        ("- ALL 🔴/❇️ FACTORS ARE TAKEN ONLY FROM display (impact/marker)",
         "- ALL 🔴/❇️ FACTORS ARE TAKEN ONLY FROM display (impact); маркер вычисляй по знаку вклада"),
        ("Маркер берётся из display.marker — САМ не вычисляй.\n", ""),
        ("Знак числа из display уже согласован с маркером.",
         "Знак числа + или − должен совпадать с маркером."),
        ("(только из display.marker)", "(по знаку вклада)"),
        ("{display.marker} **Measure**", "{marker} **Measure**"),
        ("{display.marker} **Название**", "{marker} **Название**"),
    ],
    "selection": [
        ("If only 1 significant child → output 1 bullet (not a problem)",
         "If only 1 factor qualifies → output 1 bullet (not a problem)"),
        ("If only 1 significant child → output exactly 1 top-level bullet",
         "If only 1 factor qualifies → output exactly 1 top-level bullet"),
        ("If significant < 6, output actual count (no fillers)",
         "If fewer than 6 qualify, output actual count (no fillers)"),
    ],
    "children": [
        ("Get to the root of negative impacts ONLY via existing child nodes in the JSON.\n"
         "  If a factor has no children — stop at its display.impact quote; do NOT invent\n"
         "  causes or sub-factors.\n", ""),
        ("- Применимо ТОЛЬКО к узлам с детьми (см. LEAF EDGE CASE).",
         "- Применимо ТОЛЬКО к узлам с детьми."),
        ("(только для узлов с детьми, см. LEAF EDGE CASE)",
         "(только для узлов с детьми)"),
        ("Если у фактора нет детей в JSON — НЕ строй его декомпозицию и НЕ объясняй\n"
         "причины: достаточно «{marker} **Имя** — <цитата display.impact>».\n", ""),
        ("### Листовые узлы (нет details.top_factors): НЕ выдумывай драйверы и причины —\n"
         "только {marker} **Имя** + цитата display.impact.\n", ""),
        ("### 4. LEAF EDGE CASE (КРИТИЧНО)\n"
         "У узла нет детей (details.top_factors пуст) → НЕ выдумывай драйверы, причины\n"
         "и состав: только {marker} **Имя** + цитата display.impact.\n"
         "НЕ переупаковывай plan/fact узла в «драйвер» его отклонения.\n", ""),
    ],
    "names": [
        ("### QUOTING NAMES (КРИТИЧНО — второй источник выдумок)\n"
         "В данных есть массив \"allowed_names\" — ЕДИНСТВЕННЫЙ список разрешённых имён\n"
         "(все узлы JSON). Пиши имена ТОЛЬКО из него, в любом падеже.\n"
         "Имени нет в allowed_names → фактор НЕ упоминается вовсе.\n", ""),
        ("### 1b. QUOTING NAMES (КРИТИЧНО — второй источник выдумок)\n"
         "Каждое имя фактора — из JSON (hieararchy_node), в любом падеже.\n"
         "ЗАПРЕЩЕНО упоминать факторы, которых НЕТ в JSON, даже типичные для банка.\n", ""),
    ],
}

# Замены ветки 4 (ratio) для all-llm (numbers=llm): display нет — LLM считает сама.
_B4_NUMBERS_LLM_PAIRS = [
    ("- amounts: { plan, fact, deviation, impact_to_top_lvl } — СЫРЫЕ числа (НЕ для текста!)",
     "- amounts: { plan, fact, deviation, impact_to_top_lvl }"),
    ("- display: { plan, fact, deviation, impact, marker, significant, margin_impact, margin_rub }\n"
     "  — ГОТОВЫЕ СТРОКИ. ЕДИНСТВЕННЫЙ источник чисел для текста.\n", ""),
    ("  У корня и прямых потомков корня: impact — в п.п., margin_rub — рублёвый эквивалент.\n"
     "  У вложенных узлов и срезов: все строки — абсолютные (млрд/млн/тыс./руб.).\n", ""),
    ("Взять значение из корня дерева (display корня: план/факт/отклонение — уже в % и п.п.),",
     "Взять значение из корня дерева (план/факт/отклонение; flg_rate_type=true → умножай на 100: % и п.п.),"),
    ("### QUOTING (КРИТИЧНО — единственный способ писать числа)\n"
     "Каждое число в тексте — ПОСИМВОЛЬНАЯ КОПИЯ строки из display соответствующего узла:\n"
     "- план/факт/отклонение корня = display.plan / display.fact / display.deviation (уже % и п.п.);\n"
     "- вклад потомка = display.impact (уже п.п. для корня и прямых потомков);\n"
     "- рублёвый эквивалент вклада = display.margin_rub (только у прямых потомков корня).\n"
     "ЗАПРЕЩЕНО: умножать на 100, делить, выбирать масштаб, менять разряды\n"
     "(млн ↔ млрд ↔ тыс.), менять запятую/пробелы, менять знак.\n"
     "Сырые числа из amounts НЕ использовать.",
     "### SCALING (КРИТИЧНО — числа форматируй САМИ по сырым amounts)\n"
     "Форматируй числа по правилу SCALING: масштаб млн/тыс., десятичный разделитель —\n"
     "запятая, группировка тысяч — пробел, ненулевое НИКОГДА не округляй до нуля.\n"
     "- flg_rate_type=true: план/факт ×100 → %; отклонение корня ×100 → п.п.;\n"
     "- вклад прямого потомка корня = impact_to_top_lvl × 100 → п.п.;\n"
     "- рублёвый эквивалент вклада = deviation потомка (формат SCALING)."),
    ("### 1. QUOTING NUMBERS (КРИТИЧНО — единственный способ писать числа)\n"
     "Каждое число в тексте — ПОСИМВОЛЬНАЯ КОПИЯ строки из display соответствующего узла.\n"
     "- НЕ УМНОЖАЙ НИЧЕГО НА 100 — проценты/п.п. уже посчитаны кодом и лежат в display.\n"
     "- НЕ выбирай масштаб и НЕ меняй разряды — млн/млрд/тыс. уже выбраны кодом.\n"
     "- НЕ меняй запятую, пробелы, знак, суффиксы.\n"
     "- Сырые числа из amounts НЕ использовать.\n"
     "Пример правильного подхода:\n"
     "  display: { plan: \"200 %\", fact: \"178 %\", deviation: \"-21,7 п.п.\", impact: \"-26,4 п.п.\", margin_rub: \"+300 тыс.\" }\n"
     "  → в тексте РОВНО эти строки.",
     "### 1. SCALING (КРИТИЧНО — числа форматируй САМИ по сырым amounts)\n"
     "- flg_rate_type=true: план/факт ×100 → %, отклонение/вклад корня и прямых\n"
     "  потомков ×100 → п.п. (умножай сам).\n"
     "- рублёвый эквивалент вклада прямого потомка корня = его deviation (формат SCALING).\n"
     "- Масштаб млн/тыс. выбирай сам; десятичный разделитель — запятая,\n"
     "  группировка тысяч — пробел; ненулевое НИКОГДА не округляй до нуля."),
    ("«отклонение маржи составило <цитата display.margin_impact>, что оказало влияние\n"
     "на верхнеуровневый показатель в <цитата display.margin_rub>»",
     "«отклонение маржи составило <вклад потомка × 100, в п.п.>, что оказало влияние\n"
     "на верхнеуровневый показатель в <отклонение потомка, формат SCALING>»"),
    ("Пример: «отклонение маржи составило -26,4 п.п., что оказало влияние на\n"
     "верхнеуровневый показатель в +300 тыс.» (строки взяты из display узла).\n", ""),
    ("<display.margin_impact>", "<вклад потомка × 100, п.п.>"),
    ("<display.margin_rub>", "<отклонение потомка, формат SCALING>"),
    ("Игнорируй scale_info — все строки уже в display.",
     "Масштаб (млн/тыс./млрд) выбирай сам по правилу SCALING."),
    ("- Игнорируй всё, что написано в scale_info (критично) — все строки уже в display.",
     "- Используй scale_info как справочник единиц (масштаб выбирай сам)."),
    ("- Числа, не являющиеся посимвольными цитатами display-строк",
     "- Числа, не отформатированные по правилу SCALING"),
    ("- Указать план %, факт %, отклонение п.п. — цитаты display корня.",
     "- Указать план %, факт %, отклонение п.п. (умножай сам)."),
    ("- Пример: \"**Стоимость риска (COR)**: план <display.plan>, факт <display.fact>, отклонение <display.deviation>\"",
     "- Пример: \"**Стоимость риска (COR)**: план <план %>, факт <факт %>, отклонение <п.п.>\""),
    ("- Вклад — цитата display.impact (уже в п.п.), ОБЯЗАТЕЛЬНО шаблон маржи",
     "- Вклад = impact_to_top_lvl × 100 (п.п.), ОБЯЗАТЕЛЬНО шаблон маржи"),
    ("- Цитаты display-строк (абсолютные величины — уже готовы).",
     "- Числа — абсолютные величины (формат SCALING)."),
    ("### Contents (по display, |impact| desc):", "### Contents (|impact| desc):"),
    ("- Root → цитаты display (уже % / п.п.)",
     "- Root → план/факт/отклонение корня (×100 для % и п.п.)"),
    ("- Прямые потомки → цитата display.impact (уже п.п.) + шаблон маржи с display.margin_rub",
     "- Прямые потомки → вклад = impact_to_top_lvl × 100 (п.п.) + шаблон маржи"),
    ("- Вложенные узлы → цитаты display (уже абсолютные)",
     "- Вложенные узлы → абсолютные величины (формат SCALING)"),
    ("- analytic_slice → цитаты display (уже абсолютные)",
     "- analytic_slice → абсолютные величины (формат SCALING)"),
    ("- Запятая и группировка разрядов уже внутри display-строк — цитируй посимвольно.",
     "- Десятичный разделитель — запятая; группировка тысяч — пробел."),
    ("### Пример формата (строки ИЛЛЮСТРАТИВНЫЕ — в реальном тексте цитаты display):",
     "### Пример формата (строки ИЛЛЮСТРАТИВНЫЕ — числа по правилу SCALING):"),
    ("(<display.impact>)", "(<вклад, формат SCALING>)"),
    ("(<цитата display.impact>)", "(<вклад, формат SCALING>)"),
    ("<display.deviation корня>", "<отклонение корня, п.п.>"),
    (" Пример: \"**Стоимость риска (COR)**: план <display.plan>",
     " Пример: \"**Стоимость риска (COR)**: план <план %>"),
]


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
- Если в данных есть объект `display` — КАЖДОЕ число в тексте это ПОСИМВОЛЬНАЯ
  КОПИЯ строки из display: display.plan_before, display.fact_before,
  display.plan, display.fact. Вычислять, менять масштаб/разряды/знак ЗАПРЕЩЕНО.
- Если display отсутствует, форматируй числа с умным сокращением:
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

BRANCH_TITLE = {
    1: "Ветка 1 — выполняет план, есть негатив (фокус на 🔴 + компенсация)",
    2: "Ветка 2 — выполняет план, негатива нет (только ❇️)",
    3: "Ветка 3 — отклоняется (только значимые 🔴)",
}


def resolve_prompt_texts(cfg: Optional[Dict] = None) -> Tuple[Dict[int, str], Dict[int, str], str]:
    """Конфиг предвычислений → (short_prompts, key_prompts, motiv_prompt).

    numbers=code (дефолт) — актуальные промпты, слоты заполняются code- и
    llm-фрагментами по ручкам markers/selection/names. numbers=llm (мастер-
    режим, форсирует всё в llm) — ветки 1-3 берутся из legacy-промптов
    (поведение до AIMIS-2173, пороги подставляются из конфига), ветка 4
    (ratio) — из актуальных текстов заменами на SCALING-правила.
    Алиасы {{plan_alias}}/{{fact_alias}}/{{allowed_names}} здесь НЕ подставляются.
    """
    cfg = validate_precompute_cfg(cfg)
    numbers_code = cfg["numbers"]["mode"] == MODE_CODE
    thr_pct = pct_str(cfg["selection"]["threshold"])
    sim_pct = pct_str(cfg["selection"]["similarity"])

    if not numbers_code:
        short: Dict[int, str] = {}
        key: Dict[int, str] = {}
        for b in (1, 2, 3):
            s, k = _legacy_prompts.SUMMARY_PROMPT_PAIRS[b]
            sub = [
                (">= 30% of largest", f">= {thr_pct}% of largest"),
                ("differ < 15%", f"differ < {sim_pct}%"),
            ]
            short[b] = _apply(s, sub)
            key[b] = _apply(k, sub)
        # Ветка 4 (ratio): legacy-промптов нет — актуальные тексты, слоты с
        # llm-фрагментами + все замены llm-ручек + SCALING-замены чисел.
        b4_pairs = (_MIXED_PAIRS["markers"] + _MIXED_PAIRS["selection"]
                    + _MIXED_PAIRS["children"] + _MIXED_PAIRS["names"]
                    + _B4_NUMBERS_LLM_PAIRS)
        short[4] = _apply(_fill_slots(_RAW_SHORT_PROMPTS[4], cfg), b4_pairs)
        key[4] = _apply(_fill_slots(_RAW_KEY_PROMPTS[4], cfg), b4_pairs)
        return short, key, MOTIV_PROMPT

    mixed_pairs: list = []
    if cfg["markers"]["mode"] != MODE_CODE:
        mixed_pairs += _MIXED_PAIRS["markers"]
    if cfg["selection"]["mode"] != MODE_CODE:
        mixed_pairs += _MIXED_PAIRS["selection"]
    if cfg["names"]["children"] != MODE_CODE:
        mixed_pairs += _MIXED_PAIRS["children"]
    if cfg["names"]["allowed"] != MODE_CODE:
        mixed_pairs += _MIXED_PAIRS["names"]

    short = {b: _apply(_fill_slots(t, cfg), mixed_pairs)
             for b, t in _RAW_SHORT_PROMPTS.items()}
    key = {b: _apply(_fill_slots(t, cfg), mixed_pairs)
           for b, t in _RAW_KEY_PROMPTS.items()}
    return short, key, MOTIV_PROMPT


def make_prompt_provider(
        precompute_cfg: Optional[Dict] = None,
        plan_alias: str = "План",
        fact_alias: str = "Факт",
        allowed_names: Optional[List[str]] = None,
) -> SimpleNamespace:
    """Собирает провайдер промптов по конфигу предвычислений.

    Возвращает объект с интерфейсом SummarizerPrompt (SHORT_SUMMARY_PROMPTS,
    KEY_FACTORS_PROMPTS, SUMMARY_PROMPT_PAIRS, BRANCH_TITLE, MOTIV_PROMPT) с
    уже подставленными алиасами и белым списком имён. Используется
    build_branch_report; прямой вызов summarize без cfg деградирует к дефолту
    (всё code) — совместимость с A/B-харнессом сохранена.
    """
    cfg = validate_precompute_cfg(precompute_cfg)
    short, key, motiv = resolve_prompt_texts(cfg)
    names_str = ", ".join(allowed_names or [])

    def _sub(t: str) -> str:
        return (t
                .replace("{{plan_alias}}", plan_alias)
                .replace("{{fact_alias}}", fact_alias)
                .replace("{{allowed_names}}", names_str))

    short = {b: _sub(t) for b, t in short.items()}
    key = {b: _sub(t) for b, t in key.items()}
    return SimpleNamespace(
        SHORT_SUMMARY_PROMPTS=short,
        KEY_FACTORS_PROMPTS=key,
        SUMMARY_PROMPT_PAIRS={b: (short[b], key[b]) for b in (1, 2, 3)},
        BRANCH_TITLE=dict(BRANCH_TITLE),
        MOTIV_PROMPT=_sub(motiv),
    )


# Golden-тексты: дефолтный конфиг (всё code) — бит-в-бит исходные промпты.
_GOLDEN_SHORT, _GOLDEN_KEY, _GOLDEN_MOTIV = resolve_prompt_texts(None)

SHORT_SUMMARY_PROMPTS: Dict[int, str] = _GOLDEN_SHORT
KEY_FACTORS_PROMPTS: Dict[int, str] = _GOLDEN_KEY

SUMMARY_PROMPT_PAIRS: Dict[int, Tuple[str, str]] = {
    1: (_GOLDEN_SHORT[1], _GOLDEN_KEY[1]),
    2: (_GOLDEN_SHORT[2], _GOLDEN_KEY[2]),
    3: (_GOLDEN_SHORT[3], _GOLDEN_KEY[3]),
}


class SummarizerPrompt:
    """Backward-compatible interface (golden: дефолтный конфиг, всё code)."""
    SHORT_SUMMARY_PROMPTS = SHORT_SUMMARY_PROMPTS
    KEY_FACTORS_PROMPTS = KEY_FACTORS_PROMPTS
    SUMMARY_PROMPT_PAIRS = SUMMARY_PROMPT_PAIRS
    BRANCH_TITLE = BRANCH_TITLE
    MOTIV_PROMPT = MOTIV_PROMPT
