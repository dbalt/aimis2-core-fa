# Design: Мотивационная корректировка

## Context

Микросервис `aimis2-core-fa` раскладывает финансовые отклонения факта от плана по иерархии
показателей (SUM/MULTI/RATIO) и аналитическим разрезам. Главный оркестратор —
`calculate_and_summarize_deviation()` — выполняет расчёт отклонений по всем иерархиям,
собирает результат в JSON через `collect_for_summary()`, затем вызывает LLM-суммаризацию.

Мотивационная корректировка — внешний аддитивный фактор, который не входит в иерархию
показателей. Он загружается отдельным запросом, прибавляется только к корневому узлу
и не участвует в факторной декомпозиции.

Текущая архитектура:

```
DeviationCalcMetadata
        │
        ▼
calculate_and_summarize_deviation()
        │
        ├──▶ calculate_deviations() → DrillComponent[]     (TaskGroup, параллельно)
        ├──▶ collect_for_summary() → Dict[]
        ├──▶ summarize() → classify() → branch 1/2/3
        │         │
        │         ├──▶ LLM short_summary
        │         ├──▶ LLM key_factors
        │         └──▶ render_factor_table
        │
        └──▶ Res[(data_dict, summary_text)]
```

## Goals

1. Поддержать мотивационную корректировку как опциональный блок данных в `DeviationCalcMetadata`.
2. Загружать данные корректировки параллельно с расчётом отклонений (единый `TaskGroup`).
3. Корректировать `amounts` корневого узла без изменения impact-ов дочерних узлов.
4. Отражать корректировку в JSON-результате (`"motiv_correction"` ключ).
5. Добавлять детерминированный поясняющий блок в текстовое LLM-саммари.
6. Сохранить обратную совместимость: при `motiv_correction=None` поведение не меняется.

## Non-Goals

- Изменение бизнес-логики расчёта отклонений по иерархии.
- Мотивационная корректировка для отдельных дочерних узлов (только корень).
- Параметризация формата текстового пояснения — жёстко задан в `build_branch_report()`.
- Поддержка множественных мотивационных корректировок.

## Key Design Decisions

### 1. Параллельная загрузка через единый TaskGroup

Мотив. корректировка загружается **параллельно** с расчётом отклонений по иерархиям в рамках единого `asyncio.TaskGroup`:

```python
async with asyncio.TaskGroup() as tg:
    tsk_lst = [tg.create_task(calculate_deviations(x, data_access))
                for x in calc_params_lst]
    tsk_lst.append(tg.create_task(get_motiv_correction_data(...)))

drills = [t.result() for t in tsk_lst[:-1]]
motiv_res = tsk_lst[-1].result()
```

**Почему параллельно:** мотив. корректировка — лёгкий запрос (~200ms), параллельная загрузка экономит время и увеличивает throughput.

**Риск:** увеличенное количество соединений к БД. **Митигация:** один лёгкий запрос, не конкурирует с тяжёлыми запросами к ClickHouse.

### 2. Корректировка только корневого узла

Мотивационная корректировка прибавляется **только** к `amounts` корневого `DrillComponent`:

```
amounts.plan  += motiv.plan
amounts.fact  += motiv.fact
amounts.deviation += motiv.deviation
amounts.impact  = amounts.deviation  # impact_to_top_lvl = deviation
```

Impact-ы всех дочерних узлов остаются без изменений. Корректировка — внешняя добавка к верху, не участвующая в декомпозиции.

### 3. classify() может сменить ветку из-за корректировки

Поскольку `classify()` в `summarize.py` определяет ветку (1/2/3) на основе `impact` корневого узла,
корректировка может изменить ветку саммаризации:

```
До корректировки: root.impact = -500K  →  branch 3 (негатив)
С корректировкой: root.impact = +200K  →  branch 2 (позитив)
```

Это **корректное и ожидаемое поведение** — корректировка меняет реальную картину отклонений. Задокументировано как факт, не как баг.

### 4. DataRow.from_dict() требует SearchDevParameters

Метод `DataRow.from_dict(row, params)` использует `plan_column` и `fact_column` из `SearchDevParameters`.
Параметры берутся из `metadata` если заданы, иначе — `fallback` от `DeviationCalcMetadata`.

```python
source_params = metadata.query.source_params if ... else fallback_source_params
search_dev_params = ... if ... else fallback_search_dev_params
```

### 5. Возврат `None` при пустых данных

`get_motiv_correction_data()` возвращает `Res.mk_result(None)` в случаях:
- `metadata is None`
- Результат запроса пустой (`[]`)
- Данные из БД пришли, но `DataRow` имеет `plan=0` и `fact=0` (проверка на этапе использования)

**Примечание:** проверка на `plan=0` и `fact=0` происходит не в `get_motiv_correction_data()`, а в `collect_for_summary()` и `build_branch_report()` — так `get_motiv_correction_data()` остаётся простой и возвращает сырые данные.

### 6. Одна корректировка на все иерархии

`MotivCorrectionMetadata` — одно поле в `DeviationCalcMetadata`, не зависит от конкретной иерархии.
Если `hier_lst = [hier_1, hier_2]`, то одна и та же корректировка применяется к корню каждой иерархии:

```
collect_for_summary(drill_1, motiv_correction_row) → root_1.amts += motiv
collect_for_summary(drill_2, motiv_correction_row) → root_2.amts += motiv
```

## Risks

| Риск | Уровень | Митигация |
|------|---------|-----------|
| `classify()` сменит ветку из-за корректировки | Низкий | Корректное поведение, задокументировано |
| Параллельные запросы к БД | Низкий | Один лёгкий запрос, не конкурирует с ClickHouse |
| `DataRow.from_dict()` без проверки `plan`/`fact` на `None` | Низкий | `from_dict` уже обрабатывает `None` (приводит к `0`) |
| Пустая корректировка (0/0) добавляет лишний ключ | Средний | Проверка в `collect_for_summary()` и `build_branch_report()` — ключ не вставляется при 0/0 |
| Сериализация/десериализация `MotivCorrectionMetadata` ломает обратную совместимость | Низкий | Поле опциональное, `from_json`/`from_dict` игнорируют отсутствующее поле |
