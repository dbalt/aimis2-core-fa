## Context

Микросервис факторного анализа `aimis2-core-fa` раскладывает финансовые отклонения факта от плана по двум осям: иерархия показателей (SUM/MULTI/RATIO) и аналитические разрезы. Drill-down движок рекурсивно спускается по дереву, загружая данные из ClickHouse на каждом уровне.

**Текущее поведение:**
- `get_factors()` с `flg_positive=True` (SUM) делает Pareto-отбор по обоим знакам
- `get_factors()` без `flg_positive=True` (ANALYT) — только негативные
- Дриллятся только факторы, прошедшие `is_negative()` или `force_drill`
- `collect_for_summary` включает все ветки с полной детализацией

**Проблема:** позитивные ветки раздувают дерево, создают бесполезные запросы к ClickHouse, не неся негативных инсайтов.

## Goals / Non-Goals

**Goals:**
- Если на уровне все факторы положительные — дриллить каждый (до листьев)
- Если есть отрицательные — дриллить только их (как сейчас)
- В итоговую AI-фактуру включать только ветки с хотя бы одним негативным impact
- Уменьшить количество DAL-запросов и объём итогового JSON

**Non-Goals:**
- Изменение бизнес-логики расчёта отклонений (SUM/MULTI/RATIO формулы)
- Изменение Pareto-алгоритма отбора факторов
- Изменение `sign_negative_impact` — параметр оставляем, но логика `impact < 0` считается стандартной
- Ограничение максимальной глубины дриллинга (решено оставить без `max_drill_depth` — до листьев иерархии)

## Decisions

### Decision 1: `all_positive` проверяет Pareto-топ, а не полный dataset

```
factors = get_factors(..., flg_positive=True)  → Pareto-топ по обоим знакам
all_positive = all(f.deviation > 0 for f in factors)
```

**Почему так:** `get_factors` — единственная точка отбора факторов. Если добавить `get_factors(flg_all=True)` — двойной вызов, двойной DAL-запрос.

**Альтернатива:** Использовать `data_set` (полный лист) для проверки `all_positive`. Но `data_set` не доступен в SUM-ветке (локальная переменная `_get_data_for_node` внутри цикла).

**Риск:** факторы, не прошедшие Pareto (малый вклад), не учитываются. Приемлемо — они слишком малы для отдельного анализа.

### Decision 2: ANALYT-ветка — включить `flg_positive=True`

```python
# Было:
(factors, _) = get_factors(data_set, params)

# Стало:
(factors, _) = get_factors(data_set, params, flg_all=False, flg_positive=True)
```

**Почему:** без `flg_positive=True` позитивные факторы вообще не попадают в `factors`, логика `all_positive` не применима. Если внутри позитивного фактора есть негатив на глубине — он теряется.

**Риск:** +DAL-запросы для позитивных факторов. Митигация: `collect_for_summary` отсекает позитивные ветки в финальном результате.

### Decision 3: `_has_negative_in_tree` — эвристика `impact < 0`

```python
def _has_negative_in_tree(dc: DrillComponent) -> bool:
    if dc.amts.impact < 0:
        return True
    for drill in dc.drills:
        for component in drill.components:
            if _has_negative_in_tree(component):
                return True
    return False
```

**Почему:** `SearchDevParameters` недоступен в `collect.py` (он в `DeviationCalcParams`, который не передаётся). `sign_negative_impact` всегда `-1` — эвристика корректна.

**Альтернатива:** передать `params` через контекст. Но усложнение ради `sign_negative_impact == 1`, который никогда не используется — избыточно.

### Decision 4: `map` в `collect_for_summary` — known issue

Текущая реализация мутатирует общий `map` при рекурсии. На практике не влияет, т.к. `analyt_metadata` заполнен только для корневых узлов.

**Решение:** документировать, не чинить в этом change.

## Risks / Trade-offs

| Риск | Уровень | Митигация |
|------|---------|-----------|
| `all_positive` не видит Pareto-отсечённые факторы | Средний | Принято — малый вклад |
| Explosion DAL-запросов при all-positive ветках без листьев | Высокий | В проде иерархия не глубже 3-4 уровня, ветвление 3-5. Если нужно — добавить `max_drill_depth` в следующем change |
| `impact < 0` без учёта `sign_negative_impact` | Низкий | Всегда `-1` в проде |
| `map` перезаписывается на глубоких уровнях | Низкий | Known issue, не влияет |
| ANALYT: +DAL-запросы для позитивных факторов | Средний | `collect_for_summary` отсекает в финале |
