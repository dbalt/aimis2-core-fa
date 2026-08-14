## 1. Модуль enum_mapper (БАЗОВЫЙ БЛОК — блокирует все остальные фазы)

- [ ] 1.1 Создать `libfa2/sreda_models/enum_mapper.py`
- [ ] 1.2 Реализовать `map_metric_type(v: Any) → Optional[MetricType]`
  - `"SUM"` / `"sum"` → `MetricType.SUM`
  - `"MULTI"` / `"multi"` → `MetricType.MULTI`
  - `"RATIO"` / `"ratio"` → `MetricType.RATIO`
  - `"1"` → `None` (не маппится)
  - `None` → `None`
- [ ] 1.3 Реализовать `map_multi_part_type(v: Any) → Optional[ComponentMultiPartType]`
  - `"RATE"` → `ComponentMultiPartType.RATE`
  - `"BASE"` → `ComponentMultiPartType.BASE`
  - `None` → `None`
- [ ] 1.4 Реализовать `map_ratio_part_type(v: Any) → Optional[ComponentRatioPartType]`
  - `"NUMERATOR"` → `ComponentRatioPartType.NUMERATOR`
  - `"DENOMINATOR"` → `ComponentRatioPartType.DENOMINATOR`
  - `None` → `None`
- [ ] 1.5 Реализовать `map_mp_decomposition_type(v: Any) → Optional[MultipartDecompositionType]`
  - `"Integral"` → `MultipartDecompositionType.INTEGRAL`
  - `"DirectBase"` → `MultipartDecompositionType.DIRECT_BASE`
  - `"DirectRate"` → `MultipartDecompositionType.DIRECT_RATE`
  - `"AverageWeighted"` → `MultipartDecompositionType.AVERAGE_WEIGHTED`
  - `"1"` → `MultipartDecompositionType.INTEGRAL` (баг сервера)
  - `None` → `None`
- [ ] 1.6 Тесты: `map_metric_type("SUM")` → SUM, `"sum"` → SUM, `"1"` → None, None → None
- [ ] 1.7 Тесты: `map_mp_decomposition_type("1")` → INTEGRAL, `"Integral"` → INTEGRAL

## 2. Пакет sreda_api/ (HTTP-клиент)

- [ ] 2.1 Создать пакет `libfa2/sreda_api/` с `__init__.py`
- [ ] 2.2 Создать `libfa2/sreda_api/exceptions.py` — классы `SredaAPIError`, `SredaHTTPError`
- [ ] 2.3 Создать `libfa2/sreda_api/client.py` — dataclass `SredaClientConfig`
  - [ ] 2.3.1 Поля: `host`, `cert_dir`, `cookies`
  - [ ] 2.3.2 `__post_init__` — валидация `cert_dir.exists()`
  - [ ] 2.3.3 GUID передаются как параметры методов, не как поля конфигурации
- [ ] 2.4 Реализовать `SredaAPIClient.__init__()` — SSL context, mTLS, cookie
  - [ ] 2.4.1 `_build_ssl_context()` — чтение cert.pem, chain.pem, private.key
  - [ ] 2.4.2 `_get_session()` — lazy init httpx.Client
  - [ ] 2.4.3 `close()` / `__enter__` / `__exit__` — контекстный менеджер
- [ ] 2.5 Реализовать `SredaAPIClient.fetch_guide(guide_id, where=None, limit=200, with_tabular_parts=True) → dict`
  - [ ] 2.5.1 Формирование options JSON: limit, offset, withOutCount, withTabularParts, metaAccessWhere, order
  - [ ] 2.5.2 Добавление `where` в options если передан
  - [ ] 2.5.3 Возврат `response.json()`
  - [ ] 2.5.4 Бросок `SredaHTTPError` при status != 200
- [ ] 2.6 Реализовать `SredaAPIClient.fetch_children(parent_id, guide_id, max_depth=5) → list[dict]`
  - [ ] 2.6.1 Рекурсивный обход с `_depth` и `_children`
  - [ ] 2.6.2 Остановка на `max_depth`
- [ ] 2.7 Реализовать `SredaAPIClient.fetch_query_filters(query_uuid, query_guide_id) → list[dict]`
  - [ ] 2.7.1 Запрос с `where: {id: query_uuid}`
  - [ ] 2.7.2 Extract `TabularParts.t_aimis_fa__query_filters__details`
- [ ] 2.8 Реализовать `SredaAPIClient.fetch_step_algorithm(step_uuid, step_guide_id) → list[dict]`
  - [ ] 2.8.1 Поиск записи по `id == step_uuid`
  - [ ] 2.8.2 Extract `TabularParts.t_aimis_fa__analyt_drill_steps__components`
- [ ] 2.9 Реализовать `SredaAPIClient.build_full_tree(metric_guide_id, query_guide_id, step_guide_id) → dict`
  - [ ] 2.9.1 Загрузка корневых сценариев
  - [ ] 2.9.2 Для каждого сценария: query_filters, drill_steps, children
  - [ ] 2.9.3 Возврат `{scenarios: [record, query_filters, drill_steps, children, ...]}`

## 3. Пакет sreda_models/ (dataclass-модели)

- [ ] 3.1 Создать пакет `libfa2/sreda_models/` с `__init__.py`
- [ ] 3.2 Создать `libfa2/sreda_models/analyt_step.py` — dataclass `AnalytStep`
  - [ ] 3.2.1 Поля: `id: str`, `code: int`, `owner: str`, `rank: int`, `step: str`
  - [ ] 3.2.2 Методы: `to_dict()`, `from_dict()`, `from_api_record()`
- [ ] 3.3 Создать `libfa2/sreda_models/drill_step_component.py` — dataclass `DrillStepComponent`
  - [ ] 3.3.1 Поля: `id: str`, `code: int`, `owner: str`, `rank: int`, `col_name: str`, `col_descr: str`
  - [ ] 3.3.2 Методы: `to_dict()`, `from_dict()`, `from_api_record()`
  - [ ] 3.3.3 Функция `build_drill_order(components) → list[list[str]]` — сортировка по rank
  - [ ] 3.3.4 Функция `build_dimensions(components) → dict[str, Dimension]` — col_name → Dimension
- [ ] 3.4 Создать `libfa2/sreda_models/query_filter.py` — dataclass `QueryFilterDetail`
  - [ ] 3.4.1 Поля: `id: str`, `code: int`, `owner: str`, `rank: int`, `col_name: str`, `value: Any`
  - [ ] 3.4.2 Методы: `to_dict()`, `from_dict()`, `from_api_record()`
  - [ ] 3.4.3 Функция `build_filter_dict(details) → dict[str, Any]` — парсинг int и JSON-массивов

## 4. Пакет sreda_transform/ (конвертер)

- [ ] 4.1 Создать пакет `libfa2/sreda_transform/` с `__init__.py`
- [ ] 4.2 Создать `libfa2/sreda_transform/to_metadata.py`
- [ ] 4.3 Реализовать `SredaToDeviationCalcConverter.__init__()`
  - [ ] 4.3.1 Поля: `metrics_source`, `rep_dt_column`, `plan_column`, `fact_column`, `sign_negative_impact`
- [ ] 4.4 Реализовать `transform(sreda_tree, code=None, aliases=None) → Res[DeviationCalcMetadata]`
  - [ ] 4.4.1 Итерация по `sreda_tree.scenarios`
  - [ ] 4.4.2 Для каждого: `_build_hierarchy()` → Hierarchy
  - [ ] 4.4.3 Валидация `hierarchy.is_valid()`, warning при ошибках
  - [ ] 4.4.4 Создание `DeviationCalcMetadata` с `SourceParameters` и `SearchDevParameters`
  - [ ] 4.4.5 Возврат `Res.mk_result(dcm)` или `Res.mk_error()`
- [ ] 4.5 Реализовать `_api_record_to_node(api_record, filters, drill_steps, parent_id) → MetricNode`
  - [ ] 4.5.1 `id = int(api_record.id, 16) % (2**31)`
  - [ ] 4.5.2 `code = _name_to_system_code(api_record.name)`
  - [ ] 4.5.3 `name = api_record.pres_name or api_record.name`
  - [ ] 4.5.4 `type = map_metric_type(api_record.node_type)` (через enum_mapper)
  - [ ] 4.5.5 `componentMultiPartType = map_multi_part_type(api_record.multi_part_type)`
  - [ ] 4.5.6 `componentRatioPartType = map_ratio_part_type(api_record.ratio_part_type)`
  - [ ] 4.5.7 `mp_decomp_tp = map_mp_decomposition_type(api_record.mp_decomp_type)`
  - [ ] 4.5.8 `api_uuid = api_record.id` (строка)
  - [ ] 4.5.9 `analyt_steps = [AnalytStep.from_api_record(s) for s in drill_steps]`
  - [ ] 4.5.10 `query = _build_query(filters)`
  - [ ] 4.5.11 `analyt_metadata = _build_analyt_metadata(drill_steps)`
- [ ] 4.6 Реализовать `_build_query(filters) → Query | None`
  - [ ] 4.6.1 `QueryFilterDetail.from_api_record()` для каждого фильтра
  - [ ] 4.6.2 `build_filter_dict()` для сборки params
- [ ] 4.7 Реализовать `_build_analyt_metadata(drill_steps) → AnalyticalStructureMetadata | None`
  - [ ] 4.7.1 Извлечение `_components` из каждого drill_step
  - [ ] 4.7.2 `DrillStepComponent.from_api_record()` для каждого компонента
  - [ ] 4.7.3 Сбор `drill_order = [[c.col_name] for c in sorted(components, key=lambda x: x.rank)]`
  - [ ] 4.7.4 Сбор `dimensions = {c.col_name: Dimension(...)} `
  - [ ] 4.7.5 `Algorithm(id=1, drill_order=drill_order)`
- [ ] 4.8 Реализовать `_attach_children(hierarchy, parent_id, children) → None`
  - [ ] 4.8.1 Для каждого child: `child_filters = self._client.fetch_query_filters(child_query_ref, query_guide_id)`
  - [ ] 4.8.2 `_api_record_to_node(child, child_filters, child_steps, parent_id)`
  - [ ] 4.8.3 `hierarchy.add_node(child_node)`
  - [ ] 4.8.4 Рекурсия: `_attach_children(hierarchy, child["id"], child["_children"])`
- [ ] 4.9 Реализовать `_name_to_system_code(name) → str`
  - [ ] 4.9.1 Split по `:` и взять часть после
  - [ ] 4.9.2 `rstrip()` + `replace(" ", "_")`

## 5. Модификация hier_metadata/metric_node.py

- [ ] 5.1 Добавить поле `analyt_steps: List["AnalytStep"] = field(default_factory=list)` в `MetricNode`
- [ ] 5.2 Добавить поле `api_uuid: Optional[str] = None` в `MetricNode`
- [ ] 5.3 Добавить импорт TYPE_CHECKING для `libfa2.sreda_models.AnalytStep`
- [ ] 5.4 Обновить `to_dict()` — добавить `analyt_steps: [step.to_dict() for step in self.analyt_steps]`
- [ ] 5.5 Обновить `to_dict()` — добавить `api_uuid: self.api_uuid`
- [ ] 5.6 Обновить `from_dict()` — парсинг `analyt_steps` из списка dict в `AnalytStep`
- [ ] 5.7 Обновить `from_dict()` — парсинг `api_uuid: data.get("api_uuid")`

## 6. Интеграционное тестирование

- [ ] 6.1 Адхок-скрипт для полного пайплайна
  - [ ] 6.1.1 Создать `SredaAPIClient` с GUID из конфига
  - [ ] 6.1.2 Вызвать `build_full_tree(metric_q, query_q, step_q)`
  - [ ] 6.1.3 Создать `SredaToDeviationCalcConverter`
  - [ ] 6.1.4 Вызвать `converter.transform(tree)`
  - [ ] 6.1.5 Валидация: количество иерархий >= 1, валидность Hierarchy
  - [ ] 6.1.6 Проверить: все узлы имеют `api_uuid` (не None)
  - [ ] 6.1.7 Проверить: узлы с `node_type="SUM"` имеют `type=MetricType.SUM`
  - [ ] 6.1.8 Проверить: leaf-узлы (node_type=null) имеют `type=None`
- [ ] 6.2 Тест на `build_filter_dict` — int значения, JSON-массив, пустой список
- [ ] 6.3 Тест на `build_drill_order` — 1 компонент, 3 компонента, пустой список
- [ ] 6.4 Тест на `build_dimensions` — 1 компонент, 2 компонента
