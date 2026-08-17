## ADDED Requirements

### Requirement: SredaToDeviationCalcConverter MUST трансформировать API-данные в DeviationCalcMetadata

Конвертер **MUST** принимать дерево `sreda_tree` (результат `SredaAPIClient.build_full_tree()`),
создавать `MetricNode` из каждой записи, строить `Hierarchy`, `Query`,
`AnalyticalStructureMetadata` и возвращать `Res[DeviationCalcMetadata]`.

GUID guide могут быть переданы как параметры конвертера либо найдены автоматически
через `SredaAPIClient.discover_guides()` (ручка `/api/metadata/v3/tree`), без хардкода.

#### Scenario: Успешная трансформация полного дерева

- **WHEN** вызывается `converter.transform({"scenarios": [...]})`
- **WHEN** в `sreda_tree` есть `scenarios` с полями `record`, `query_filters`, `drill_steps`, `children`
- **THEN** для каждой записи `record` создаётся `MetricNode` с `id`, `code`, `name`, `type` (через `enum_mapper`), `parent`, `query`, `analyt_metadata`, `analyt_steps`, `api_uuid`
- **THEN** из `MetricNode` собирается `Hierarchy` через `add_node()`
- **THEN** создаются `SourceParameters` и `SearchDevParameters` из параметров конвертера
- **THEN** возвращается `Res.mk_result(DeviationCalcMetadata(code, source_params, search_dev_params, hier_lst))`

#### Scenario: Transform с пустым деревом

- **WHEN** вызывается `converter.transform({"scenarios": []})`
- **THEN** возвращается `Res.mk_error("sreda_tree.scenarios is empty")`

#### Scenario: Transform с невалидной иерархией

- **WHEN** вызывается `converter.transform({"scenarios": [...]})`
- **WHEN** `hierarchy.validate()` возвращает ошибки валидации
- **THEN** логируется `logger.warning("Hierarchy validation errors: ...")`
- **THEN** иерархия пропускается (не добавляется в `hier_lst`)

#### Scenario: Transform без query для узла

- **WHEN** `record` не содержит `query` или `query_filters = []`
- **THEN** `MetricNode.query = None`

#### Scenario: Transform без drill-steps для узла

- **WHEN** `drill_steps = []` или отсутствует `TabularParts.t_aimis_fa__metric_hier__analyt_steps`
- **THEN** `MetricNode.analyt_steps = []`
- **THEN** `MetricNode.analyt_metadata = None`

### Requirement: SredaToDeviationCalcConverter MUST корректно строить Query из фильтров

Конвертер **MUST** преобразовывать `query_filters` из API-записи в объект `Query`.

#### Scenario: Построение Query из нескольких фильтров

- **WHEN** `query_filters = [{"col_name": "ind_id", "value": "49", "rank": 1}, {"col_name": "total_type", "value": "3", "rank": 2}]`
- **THEN** создаётся `Query({"ind_id": 49, "total_type": 3})`
- **THEN** значения парсятся: строки `"49"` → `int 49`, `"3"` → `int 3`

#### Scenario: Построение Query с JSON-массивом

- **WHEN** `query_filters = [{"col_name": "node_code", "value": '["PL_01_03_01", "PL_14_45_08"]', "rank": 1}]`
- **THEN** создаётся `Query({"node_code": ["PL_01_03_01", "PL_14_45_08"]})`
- **THEN** строка `'["PL_01_03_01", "PL_14_45_08"]'` парсится через `json.loads()`

#### Scenario: Построение Query при отсутствии фильтров

- **WHEN** `query_filters = []`
- **THEN** `Query` не создаётся, возвращается `None`

### Requirement: SredaToDeviationCalcConverter MUST корректно строить AnalyticalStructureMetadata из drill-шагов

Конвертер **MUST** преобразовывать drill-шаги (analyt_steps) в `AnalyticalStructureMetadata`
с `Algorithm.drill_order` и `Dimension[]`.

#### Scenario: Построение analyt_metadata из одного drill-шага

- **WHEN** `drill_steps = [{"step": "c74fe30d-...", "_components": [{"col_name": "tb", "col_descr": "ТБ", "rank": 1}]}]`
- **THEN** создаётся `Algorithm(id=1, drill_order=[["tb"]])`
- **THEN** создаётся `Dimension(code="tb", name="ТБ", column="tb")`
- **THEN** `AnalyticalStructureMetadata.add_algorithm(algo)`
- **THEN** `AnalyticalStructureMetadata.add_dimension(dim)`

#### Scenario: Построение analyt_metadata из нескольких drill-шагов

- **WHEN** `drill_steps = [
    {"step": "c74fe30d-...", "_components": [{"col_name": "tb", "col_descr": "ТБ", "rank": 1}]},
    {"step": "569a7af7-...", "_components": [{"col_name": "biz_block", "col_descr": "Бизнес-блок", "rank": 1}]}
  ]`
- **THEN** создаётся `Algorithm(id=1, drill_order=[["tb"], ["biz_block"]])`
- **THEN** создаются оба `Dimension`

#### Scenario: Построение analyt_metadata при отсутствии компонентов

- **WHEN** `drill_steps = [{"step": "c74fe30d-...", "_components": []}]`
- **THEN** `analyt_metadata = None`

#### Scenario: Построение analyt_metadata при отсутствии drill_steps

- **WHEN** `drill_steps = []`
- **THEN** `analyt_metadata = None`

### Requirement: SredaToDeviationCalcConverter MUST собирать детей в Hierarchy

Конвертер **MUST** рекурсивно добавлять `children` в `Hierarchy` с правильным `parent_id`.

#### Scenario: Добавление детей первого уровня

- **WHEN** `children = [{"id": "e7e53f8d-...", "name": "...", "query": "5d463b5b-..."}]`
- **WHEN** `parent_id = "b0220ce2-..."`
- **THEN** для каждого child вызывается `_api_record_to_node` с `parent_id`
- **THEN** каждый child добавляется в `Hierarchy` через `add_node()`
- **THEN** `MetricNode.parent` вычисляется как `int(parent_id, 16) % (2**31)`

#### Scenario: Рекурсивное добавление вложенных детей

- **WHEN** child содержит `_children: [{"id": "0f5d59fa-...", ...}]`
- **WHEN** parent_id для grandchildren = `child.id`
- **THEN** grandchildren рекурсивно добавляются в `Hierarchy`
- **THEN** глубина не ограничена (рекурсия продолжается пока есть `_children`)

### Requirement: SredaToDeviationCalcConverter MUST преобразовывать name в system_code

Статический метод `_name_to_system_code` **MUST** преобразовывать human-readable name
в machine-readable code.

#### Scenario: Преобразование имени с двоеточием

- **WHEN** `_name_to_system_code("ТБГОСБ: Кредиты юридическим лицам")`
- **THEN** возвращается `"Кредиты_юридическим_лицам"` (берётся часть после `:`, пробелы → `_`)

#### Scenario: Преобразование имени без двоеточия

- **WHEN** `_name_to_system_code("Чистый процентный доход от активов")`
- **THEN** возвращается `"Чистый_процентный_доход_от_активов"`

#### Scenario: Преобразование имени с пробелами в конце

- **WHEN** `_name_to_system_code("ТБГОСБ: ТБ ")`
- **THEN** возвращается `"ТБ"` (trim + split + replace)

### Requirement: MetricNode MUST поддерживать поля analyt_steps и api_uuid

После модификации `hier_metadata/metric_node.py` каждый `MetricNode` **MUST**
поддерживать новые поля для интеграции с API Среды.

#### Scenario: Создание MetricNode с analyt_steps и api_uuid

- **WHEN** создаётся `MetricNode(id=1, code="test", name="Тест", api_uuid="abc-123", analyt_steps=[...])`
- **THEN** поля `api_uuid` и `analyt_steps` корректно инициализируются

#### Scenario: Сериализация в dict

- **WHEN** вызывается `node.to_dict()` на узле с `analyt_steps` и `api_uuid`
- **THEN** возвращаемый `dict` включает ключи `analyt_steps` (список dict) и `api_uuid` (строка или null)

#### Scenario: Десериализация из dict

- **WHEN** вызывается `MetricNode.from_dict({"analyt_steps": [...], "api_uuid": "abc-123", ...})`
- **THEN** создаётся `MetricNode` с корректно десериализованными `analyt_steps` и `api_uuid`

---

## POTENTIAL (не реализовано)

> Открытый вопрос для согласования. Сейчас `transform()` разворачивает **все** корневые
> сценарии (`scenarios`) в `hier_lst`. Возможная альтернатива — разворачивать **только один**
> конкретный сценарий, выбранный по приходящему извне GUID сценария (`record.id`)
> или по коду (`record.name`).

### Требование (candidate): выбор одного сценария по GUID

- **WHEN** в `transform(..., scenario_guid="...")` передан GUID конкретного сценария
- **THEN** в `hier_lst` попадает **только** `Hierarchy`, построенная из записи с `record.id == scenario_guid`
- **THEN** остальные корневые записи пропускаются (в `hier_lst` не попадают)

#### Scenario: передан GUID существующего сценария

- **WHEN** `scenarios` содержит запись с `record.id == scenario_guid`
- **THEN** строится одна `Hierarchy` для этого сценария
- **THEN** `hier_lst` содержит ровно одну иерархию

#### Scenario: GUID не найден

- **WHEN** в `scenarios` нет записи с `record.id == scenario_guid`
- **THEN** возвращается `Res.mk_error(...)` (либо пропуск с `logger.warning` — уточнить)

#### Scenario: GUID не передан

- **WHEN** `scenario_guid` отсутствует / `None`
- **THEN** поведение остаётся текущим — разворачиваются все `scenarios`
