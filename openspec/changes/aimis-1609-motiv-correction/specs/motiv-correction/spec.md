# Spec: Мотивационная корректировка

## Requirement 1: Метаданные мотивационной корректировки

Система должна поддерживать опциональное поле `motiv_correction` в `DeviationCalcMetadata`
и новый dataclass `MotivCorrectionMetadata` с методами сериализации.

### Scenario 1.1: Создание MotivCorrectionMetadata

**Дано:** `Query` с параметрами WHERE-фильтрации.
**Когда:** Создаётся `MotivCorrectionMetadata(query=...)`.
**То:** Объект содержит `query` и поддерживает `to_dict()`, `to_json()`, `to_json_str()`.

### Scenario 1.2: Десериализация MotivCorrectionMetadata

**Дано:** Словарь `{"query": {"metricType": "motiv_correction"}}`.
**Когда:** Вызывается `MotivCorrectionMetadata.from_dict(data)`.
**То:** Создаётся объект с `query=Query({"metricType": "motiv_correction"})`.

### Scenario 1.3: DeviationCalcMetadata с motiv_correction

**Дано:** `DeviationCalcMetadata` с не-`None` `motiv_correction`.
**Когда:** Вызывается `to_dict()`.
**То:** В словаре присутствует ключ `"motiv_correction"` с сериализованным объектом.

### Scenario 1.4: DeviationCalcMetadata без motiv_correction

**Дано:** `DeviationCalcMetadata` с `motiv_correction=None`.
**Когда:** Вызывается `to_dict()`.
**То:** В словаре отсутствует ключ `"motiv_correction"`.

---

## Requirement 2: Загрузка данных мотивационной корректировки

Система должна загружать один ряд данных мотивационной корректировки из БД параллельно с расчётом отклонений.

### Scenario 2.1: metadata is None

**Дано:** `metadata=None`, `data_access` подключён к БД.
**Когда:** Вызывается `get_motiv_correction_data(None, rep_dt, data_access, ...)`.
**То:** Возвращается `Res.mk_result(None)`.

### Scenario 2.2: Успешная загрузка данных

**Дано:** `metadata` задан, `query.to_dict()` возвращает `{"metricType": "motiv_correction"}`, в БД есть строка с `rep_dt=2026-08-03`, `plan=1000000`, `fact=1500000`.
**Когда:** Вызывается `get_motiv_correction_data(metadata, rep_dt, data_access, source_params, search_dev_params)`.
**То:** Возвращается `Res.mk_result(DataRow(plan=1000000, fact=1500000, dims={}))`.

### Scenario 2.3: Данные из БД отсутствуют (пустой результат)

**Дано:** `metadata` задан, в БД нет строки с заданным `rep_dt`.
**Когда:** Вызывается `get_motiv_correction_data(metadata, rep_dt, data_access, ...)`.
**То:** Возвращается `Res.mk_result(None)`.

### Scenario 2.4: Fallback source_params / search_dev_params

**Дано:** `metadata.source_params` пустой, `metadata.query` содержит только WHERE-фильтры.
**Когда:** Вызывается `get_motiv_correction_data(...)`.
**То:** Используются `fallback_source_params` и `fallback_search_dev_params` для определения `source_name`, `rep_dt_column`, `plan_column`, `fact_column`.

### Scenario 2.5: Загрузка с rep_dt фильтром

**Дано:** `metadata.query` задаёт `{"metricType": "motiv_correction"}`, `rep_dt=2026-08-03`.
**Когда:** Вызывается `get_motiv_correction_data(...)`.
**То:** Формируется `ConditionAnd([ConditionSet({"metricType": "motiv_correction"}), ConditionSet({"rep_dt": 2026-08-03})])`.

---

## Requirement 3: Корректировка amounts корневого узла и JSON

Система должна прибавлять значения мотивационной корректировки к `amounts` корневого `DrillComponent` и включать ключ в JSON.

### Scenario 3.1: Ненулевая корректировка

**Дано:** `motiv_correction_row` с `plan=1000000`, `fact=1500000`, корневой `DrillComponent` с `amounts.plan=5000000`, `amounts.fact=6000000`.
**Когда:** Вызывается `collect_for_summary(root_dc, motiv_correction_row)`.
**То:**
- `amounts.plan = 6000000` (5000000 + 1000000)
- `amounts.fact = 7500000` (6000000 + 1500000)
- `amounts.deviation = 1500000` (7500000 - 6000000)
- `amounts.impact = 1500000` (равно deviation)
- Возвращаемый `Dict` содержит `"motiv_correction": {"plan": 1000000, "fact": 1500000, "deviation": 500000, "label": "мотивационной корректировки"}`

### Scenario 3.2: Нулевая корректировка (plan=0, fact=0)

**Дано:** `motiv_correction_row` с `plan=0`, `fact=0`.
**Когда:** Вызывается `collect_for_summary(root_dc, motiv_correction_row)`.
**То:**
- `amounts` корневого узла **не** изменяются
- Возвращаемый `Dict` **не** содержит ключ `"motiv_correction"`

### Scenario 3.3: Только plan ≠ 0

**Дано:** `motiv_correction_row` с `plan=500000`, `fact=0`.
**Когда:** Вызывается `collect_for_summary(root_dc, motiv_correction_row)`.
**То:**
- `amounts.plan += 500000`
- `amounts.fact` без изменений
- `amounts.deviation` пересчитан
- `motiv_correction` ключ присутствует в JSON

### Scenario 3.4: Только fact ≠ 0

**Дано:** `motiv_correction_row` с `plan=0`, `fact=300000`.
**Когда:** Вызывается `collect_for_summary(root_dc, motiv_correction_row)`.
**То:**
- `amounts.fact += 300000`
- `amounts.plan` без изменений
- `amounts.deviation` пересчитан
- `motiv_correction` ключ присутствует в JSON

### Scenario 3.5: Impact дочерних узлов не меняется

**Дано:** Корневой `DrillComponent` с `impact=1000000` и дочерним узлом с `impact=300000`. `motiv_correction_row` с `plan=500000`, `fact=700000` (deviation=200000).
**Когда:** Вызывается `collect_for_summary(root_dc, motiv_correction_row)`.
**То:**
- Корневой `impact = 1200000` (был 1000000 + 200000)
- Дочерний `impact = 300000` (без изменений)

---

## Requirement 4: Параллельная загрузка в оркестраторе

Система должна запускать `get_motiv_correction_data()` параллельно с `calculate_deviations()` через единый `asyncio.TaskGroup`.

### Scenario 4.1: Корректное распаковывание результатов

**Дано:** `hier_lst = [hier_1, hier_2]`, `motiv_correction` задан.
**Когда:** Вызывается `calculate_and_summarize_deviation(code, dt, metadata, data_access, ...)`.
**То:**
- `calculate_deviations` для каждой иерархии запускается в `TaskGroup`.
- `get_motiv_correction_data` запускается в том же `TaskGroup`.
- `drills` получает результаты только `calculate_deviations` (без последнего элемента).
- `motiv_row` получает результат `get_motiv_correction_data` (последний элемент).

### Scenario 4.2: Поведение при ошибке загрузки корректировки

**Дано:** `get_motiv_correction_data` возвращает `Res.mk_error("DB connection failed")`.
**Когда:** Вызывается `calculate_and_summarize_deviation(...)`.
**То:**
- Логгируется `lgr.warning("Failed to load motiv correction: ...")`.
- `motiv_row = None`.
- Система продолжает работу как при `motiv_correction=None`.

### Scenario 4.3: Поведение при отсутствии motiv_correction

**Дано:** `metadata.motiv_correction = None`.
**Когда:** Вызывается `calculate_and_summarize_deviation(...)`.
**То:**
- `get_motiv_correction_data` возвращает `Res.mk_result(None)`.
- `motiv_row = None`.
- Поведение идентично до внедрения мотивационной корректировки.

---

## Requirement 5: Детерминированный блок в текстовом саммари

Система должна добавлять поясняющий блок о мотивационной корректировке в текстовый отчёт при ненулевой корректировке.

### Scenario 5.1: Корректировка присутствует и ненулевая

**Дано:** `data["motiv_correction"] = {"plan": 1000000, "fact": 1500000, "deviation": 500000}`, корневой `amounts = {"plan": 6000000, "fact": 7500000}`.
**Когда:** Вызывается `build_branch_report(data, ...)`.
**То:** В финальный отчёт добавляется:
```

⚠️ Итоговые значения плана и факта указаны с учётом мотивационной корректировки.
Данные до корректировки: план 5000000, факт 6000000.
Мотивационная корректировка: план 1000000, факт 1500000.
```

### Scenario 5.2: Корректировка отсутствует в data

**Дано:** `data` не содержит ключ `"motiv_correction"`.
**Когда:** Вызывается `build_branch_report(data, ...)`.
**То:** Поясняющий блок **не** добавляется, отчёт без изменений.

### Scenario 5.3: Корректировка нулевая (plan=0, fact=0)

**Дано:** `data["motiv_correction"] = {"plan": 0, "fact": 0}`.
**Когда:** Вызывается `build_branch_report(data, ...)`.
**То:** Поясняющий блок **не** добавляется.

---

## Requirement 6: Обратная совместимость

Система должна вести себя идентично текущему поведению при отсутствии `motiv_correction`.

### Scenario 6.1: No regressions when motiv_correction is absent

**Дано:** `DeviationCalcMetadata` без `motiv_correction` (или `None`).
**Когда:** Вызывается полный конвейер `calculate_and_summarize_deviation()` → `summarize()`.
**То:**
- JSON-результат **не** содержит ключ `"motiv_correction"`.
- Текстовый саммари **не** содержит блок о мотивационной корректировке.
- `amounts` всех узлов без изменений.
- `classify()` определяет ту же ветку, что и до внедрения.
