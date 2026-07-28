## ADDED Requirements

### Requirement: SUM-ветка дриллит все факторы при all-positive

При разложении по иерархии (SUM-тип узла) если все факторы, прошедшие Pareto-отбор, положительные, каждый из них должен быть дриллен дальше (и иерархия, и аналитика).

#### Scenario: все факторы положительные — дриллим всех
- **WHEN** `get_factors(data_set, params, flg_all=False, flg_positive=True)` возвращает факторы `[f1, f2, f3]` и `all(f.deviation > 0 for f in factors)` → True
- **THEN** для каждого `f` создаётся `DrillComponent` и планируется задача через `task_group.create_task(make_next_drill(...))`

#### Scenario: есть негативные факторы — дриллим только негатив
- **WHEN** `get_factors(data_set, params, flg_all=False, flg_positive=True)` возвращает факторы `[f1(+), f2(-), f3(+) ]` и `all_positive` → False
- **THEN** дриллятся только те `f`, для которых `is_negative(f.deviation)` → True
- **THEN** позитивные факторы (f1, f3) не дриллятся

#### Scenario: force_drill принудительно дриллит узел
- **WHEN** у `DrillComponent.hier_ref.force_drill` → True
- **THEN** узел дриллится независимо от знака impact

### Requirement: ANALYT-ветка дриллит все факторы при all-positive

При аналитическом разложении `get_factors` вызывается с `flg_positive=True`, чтобы позитивные факторы попадали в результат. Логика `all_positive` применяется так же, как для SUM-ветки.

#### Scenario: все факторы положительные — дриллим всех
- **WHEN** `get_factors(data_set, params, flg_all=False, flg_positive=True)` возвращает факторы `[f1, f2, f3]` и `all_positive` → True
- **THEN** для каждого `f` создаётся `DrillComponent` и планируется задача (`_process_algorithm_step` или `make_next_drill`)

#### Scenario: есть негативные факторы — дриллим только негатив
- **WHEN** `get_factors` возвращает микс и `all_positive` → False
- **THEN** дриллятся только факторы с `is_negative(f.deviation)` → True

#### Scenario: get_factors в ANALYT вызывается с flg_positive=True
- **WHEN** аналитический шаг выполняется
- **THEN** вызов `get_factors(data_set, params, flg_all=False, flg_positive=True)` — позитивные факторы попадают в результат

### Requirement: collect_for_summary отсекает ветки без негатива

В итоговую AI-фактуру включаются только те ветки дерева drill-down, в которых хотя бы один фактор на каком-то уровне имеет отрицательное влияние (impact < 0).

#### Scenario: ветка с негативом — полная детализация
- **WHEN** `_has_negative_in_tree(dc)` → True (на каком-то уровне impact < 0)
- **THEN** `collect_for_summary` включает поле `details` с полной рекурсией дочерних компонентов

#### Scenario: ветка без негатива — без деталей
- **WHEN** `_has_negative_in_tree(dc)` → False (все факторы positive на всех уровнях)
- **THEN** `collect_for_summary` включает данные текущего уровня, но **не включает** поле `details`

#### Scenario: негатив на глубине 3
- **WHEN** на уровне 0 и 1 — факторы положительные, на уровне 2 — негатив
- **THEN** все три уровня включены в результат с полной детализацией

#### Scenario: вложенные ветки (негатив в одной, позитив в другой)
- **WHEN** sibling A имеет негатив в поддереве, sibling B — все позитивные
- **THEN** sibling A включён с полной детализацией, sibling B — только текущий уровень без details

### Requirement: _has_negative_in_tree — рекурсивная проверка

Рекурсивная функция проверяет, есть ли хотя бы один `DrillComponent` с `impact < 0` в дереве.

#### Scenario: корень имеет негатив
- **WHEN** `dc.amts.impact < 0`
- **THEN** функция возвращает True (без рекурсии)

#### Scenario: негатив на глубине
- **WHEN** `dc.amts.impact > 0`, но один из дочерних компонентов имеет `impact < 0`
- **THEN** функция обходит все `drill.components` рекурсивно, возвращает True

#### Scenario: пустое дерево
- **WHEN** `dc.amts.impact > 0` и `dc.drills` пуст или все компоненты positive
- **THEN** функция возвращает False

### Requirement: знак определяется через impact < 0

Функция `_has_negative_in_tree` использует эвристику `impact < 0` для определения негатива, предполагая `sign_negative_impact == -1`.

#### Scenario: sign_negative_impact = -1
- **WHEN** `dc.amts.impact < 0`
- **THEN** считаем негативным влиянием

#### Scenario: sign_negative_impact != -1 (не используется)
- **WHEN** в системе установлен `sign_negative_impact = 1` (не встречается в проде)
- **THEN** эвристика может не соответствовать — известный ограни
