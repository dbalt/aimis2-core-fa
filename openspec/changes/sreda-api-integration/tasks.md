## 1. Модуль enum_mapper (БАЗОВЫЙ БЛОК — блокирует все остальные фазы)

- [x] 1.1 Создать `libfa2/sreda_models/enum_mapper.py`
- [x] 1.2 Реализовать `map_metric_type(v: Any) → Optional[MetricType]`
  - `"SUM"` / `"sum"` → `MetricType.SUM`
  - `"MULTI"` / `"multi"` → `MetricType.MULTI`
  - `"RATIO"` / `"ratio"` → `MetricType.RATIO`
  - `"1"` → `None` (не маппится)
  - `None` → `None`
- [x] 1.3 Реализовать `map_multi_part_type(v: Any) → Optional[ComponentMultiPartType]`
  - `"RATE"` → `ComponentMultiPartType.RATE`
  - `"BASE"` → `ComponentMultiPartType.BASE`
  - `None` → `None`
- [x] 1.4 Реализовать `map_ratio_part_type(v: Any) → Optional[ComponentRatioPartType]`
  - `"NUMERATOR"` → `ComponentRatioPartType.NUMERATOR`
  - `"DENOMINATOR"` → `ComponentRatioPartType.DENOMINATOR`
  - `None` → `None`
- [x] 1.5 Реализовать `map_mp_decomposition_type(v: Any) → Optional[MultipartDecompositionType]`
  - `"Integral"` → `MultipartDecompositionType.INTEGRAL`
  - `"DirectBase"` → `MultipartDecompositionType.DIRECT_BASE`
  - `"DirectRate"` → `MultipartDecompositionType.DIRECT_RATE`
  - `"AverageWeighted"` → `MultipartDecompositionType.AVERAGE_WEIGHTED`
  - `"1"` → `MultipartDecompositionType.INTEGRAL` (баг сервера)
  - `None` → `None`
- [x] 1.6 Тесты: `map_metric_type("SUM")` → SUM, `"sum"` → SUM, `"1"` → None, None → None
- [x] 1.7 Тесты: `map_mp_decomposition_type("1")` → INTEGRAL, `"Integral"` → INTEGRAL

## 2. Пакет sreda_api/ (HTTP-клиент)

- [x] 2.1 Создать пакет `libfa2/sreda_api/` с `__init__.py`
- [x] 2.2 Создать `libfa2/sreda_api/exceptions.py` — классы `SredaAPIError`, `SredaHTTPError`
- [x] 2.3 Создать `libfa2/sreda_api/client.py` — dataclass `SredaClientConfig`
  - [x] 2.3.1 Поля: `host`, `cert_dir`, `cookies`, `login`, `password`, `origin`, `auto_login`
  - [x] 2.3.2 `__post_init__` — валидация `cert_dir.exists()`
  - [x] 2.3.3 GUID справочников не хардкодятся — определяются через `discover_guides()`
- [x] 2.4 Реализовать `SredaAPIClient.__init__()` — SSL context, mTLS
  - [x] 2.4.1 `_build_ssl_context()` — чтение cert.pem, chain.pem, private.key
  - [x] 2.4.2 `_get_session()` — lazy init httpx.Client (+ авто-логин)
  - [x] 2.4.3 `close()` / `__enter__` / `__exit__` — контекстный менеджер
- [x] 2.5 Реализовать `SredaAPIClient.fetch_guide(guide_id, where=None, limit=200, with_tabular_parts=True) → dict`
  - [x] 2.5.1 Формирование options JSON: limit, offset, withOutCount, withTabularParts, metaAccessWhere, order
  - [x] 2.5.2 Добавление `where` в options если передан
  - [x] 2.5.3 Возврат `response.json()`
  - [x] 2.5.4 Бросок `SredaHTTPError` при status != 200
- [x] 2.6 Реализовать `SredaAPIClient.fetch_children(parent_id, guide_id, max_depth=5) → list[dict]`
  - [x] 2.6.1 Рекурсивный обход с `_depth` и `_children`
  - [x] 2.6.2 Остановка на `max_depth`
- [x] 2.7 Реализовать `SredaAPIClient.fetch_query_filters(query_uuid, query_guide_id) → list[dict]`
  - [x] 2.7.1 Запрос с `where: {id: query_uuid}`
  - [x] 2.7.2 Extract `TabularParts.t_aimis_fa__query_filters__details`
- [x] 2.8 Реализовать `SredaAPIClient.fetch_step_algorithm(step_uuid, step_guide_id) → list[dict]`
  - [x] 2.8.1 Поиск записи по `id == step_uuid`
  - [x] 2.8.2 Extract `TabularParts.t_aimis_fa__analyt_drill_steps__components`
- [x] 2.9 Реализовать `SredaAPIClient.build_full_tree(...) → dict`
  - [x] 2.9.1 Загрузка корневых сценариев
  - [x] 2.9.2 Для каждого сценария: query_filters, drill_steps, children, scenario, source_params
  - [x] 2.9.3 Возврат `{scenarios: [...], guides: {...}}`
- [x] 2.10 Реализовать `login()` — `POST /api/auth/login`, fallback 501→Origin, cookie в сессию
- [x] 2.11 Реализовать `discover_guides()` — авто-поиск 5 справочников через `/api/metadata/v3/tree`
- [x] 2.12 Реализовать `_resolve_scenario(state, hier_id, scenario_guide)` —
      связка сценарий по GUID → source_params из ФАПараметрыИсточников

## 3. Пакет sreda_models/ (dataclass-модели)

- [x] 3.1 Создать пакет `libfa2/sreda_models/` с `__init__.py`
- [x] 3.2 Создать `libfa2/sreda_models/analyt_step.py` — dataclass `AnalytStep`
  - [x] 3.2.1 Поля: `id: str`, `code: int`, `owner: str`, `rank: int`, `step: str`
  - [x] 3.2.2 Методы: `to_dict()`, `from_dict()`, `from_api_record()`
- [x] 3.3 Создать `libfa2/sreda_models/drill_step_component.py` — dataclass `DrillStepComponent`
  - [x] 3.3.1 Поля: `id: str`, `code: int`, `owner: str`, `rank: int`, `col_name: str`, `col_descr: str`
  - [x] 3.3.2 Методы: `to_dict()`, `from_dict()`, `from_api_record()`
  - [x] 3.3.3 Функция `build_drill_order(components) → list[list[str]]` — сортировка по rank
  - [x] 3.3.4 Функция `build_dimensions(components) → dict[str, Dimension]` — col_name → Dimension
- [x] 3.4 Создать `libfa2/sreda_models/query_filter.py` — dataclass `QueryFilterDetail`
  - [x] 3.4.1 Поля: `id: str`, `code: int`, `owner: str`, `rank: int`, `col_name: str`, `value: Any`
  - [x] 3.4.2 Методы: `to_dict()`, `from_dict()`, `from_api_record()`
  - [x] 3.4.3 Функция `build_filter_dict(details) → dict[str, Any]` — парсинг int, JSON-массивов
        и Python-литералов (`.literal_eval` для `node_code` в одинарных кавычках)

## 4. Пакет sreda_transform/ (конвертер)

- [x] 4.1 Создать пакет `libfa2/sreda_transform/` с `__init__.py`
- [x] 4.2 Создать `libfa2/sreda_transform/to_metadata.py`
- [x] 4.3 Реализовать `SredaToDeviationCalcConverter.__init__()`
  - [x] 4.3.1 Поля: `metrics_source`, `rep_dt_column`, `plan_column`, `fact_column`, `sign_negative_impact`
  - [x] 4.3.2 guide_id optional: `metric_guide_id`, `query_guide_id`, `step_guide_id` (авто-поиск при None)
- [x] 4.4 Реализовать `transform(sreda_tree, code=None, aliases=None) → Res[DeviationCalcMetadata]`
  - [x] 4.4.1 Итерация по `sreda_tree.scenarios`
  - [x] 4.4.2 Для каждого: `_build_hierarchy()` → Hierarchy
  - [x] 4.4.3 Валидация `hierarchy.is_valid()`, warning при ошибках
  - [x] 4.4.4 Создание `DeviationCalcMetadata` с `SourceParameters` и `SearchDevParameters`
  - [x] 4.4.5 Возврат `Res.mk_result(dcm)` или `Res.mk_error()`
- [x] 4.5 Реализовать `_api_record_to_node(api_record, filters, drill_steps, parent_id) → MetricNode`
  - [x] 4.5.1 `id = int(api_record.id, 16) % (2**31)`
  - [x] 4.5.2 `code = _name_to_system_code(api_record.name)`
  - [x] 4.5.3 `name = api_record.pres_name or api_record.name`
  - [x] 4.5.4 `type = map_metric_type(api_record.node_type)` (через enum_mapper)
  - [x] 4.5.5 `componentMultiPartType = map_multi_part_type(api_record.multi_part_type)`
  - [x] 4.5.6 `componentRatioPartType = map_ratio_part_type(api_record.ratio_part_type)`
  - [x] 4.5.7 `mp_decomp_tp = map_mp_decomposition_type(api_record.mp_decomp_type)`
  - [x] 4.5.8 `api_uuid = api_record.id` (строка)
  - [x] 4.5.9 `analyt_steps = [AnalytStep.from_api_record(s) for s in drill_steps]`
  - [x] 4.5.10 `query = _build_query(filters)`
  - [x] 4.5.11 `analyt_metadata = _build_analyt_metadata(drill_steps)`
- [x] 4.6 Реализовать `_build_query(filters) → Query | None`
  - [x] 4.6.1 `QueryFilterDetail.from_api_record()` для каждого фильтра
  - [x] 4.6.2 `build_filter_dict()` для сборки params
- [x] 4.7 Реализовать `_build_analyt_metadata(drill_steps) → AnalyticalStructureMetadata | None`
  - [x] 4.7.1 Извлечение `_components` из каждого drill_step
  - [x] 4.7.2 `DrillStepComponent.from_api_record()` для каждого компонента
  - [x] 4.7.3 Сбор `drill_order = [[c.col_name] for c in sorted(components, key=lambda x: x.rank)]`
  - [x] 4.7.4 Сбор `dimensions = {c.col_name: Dimension(...)}`
  - [x] 4.7.5 `Algorithm(id=1, drill_order=drill_order)`
- [x] 4.8 Реализовать `_attach_children(hierarchy, parent_id, children) → None`
  - [x] 4.8.1 Для каждого child: `child_filters = self._client.fetch_query_filters(child_query_ref, query_guide_id)`
  - [x] 4.8.2 `_api_record_to_node(child, child_filters, child_steps, parent_id)`
  - [x] 4.8.3 `hierarchy.add_node(child_node)`
  - [x] 4.8.4 Рекурсия: `_attach_children(hierarchy, child["id"], child["_children"])`
- [x] 4.9 Реализовать `_name_to_system_code(name) → str`
  - [x] 4.9.1 Split по `:` и взять часть после
  - [x] 4.9.2 `rstrip()` + `replace(" ", "_")`
- [x] 4.10 Заполнять `SourceParameters`/`SearchDevParameters`/`aliases` из API
      (`source_params` + `scenario` первого сценария), fallback на дефолты конвертера
- [x] `_resolve_guide_ids(ctx)` — взять найденные guide_id из `tree["guides"]` при повторном вызове

## 5. Модификация hier_metadata/metric_node.py

- [x] 5.1 Добавить поле `analyt_steps: List["AnalytStep"] = field(default_factory=list)` в `MetricNode`
- [x] 5.2 Добавить поле `api_uuid: Optional[str] = None` в `MetricNode`
- [x] 5.3 Добавить импорт TYPE_CHECKING для `libfa2.sreda_models.AnalytStep`
- [x] 5.4 Обновить `to_dict()` — добавить `analyt_steps: [step.to_dict() for step in self.analyt_steps]`
- [x] 5.5 Обновить `to_dict()` — добавить `api_uuid: self.api_uuid`
- [x] 5.6 Обновить `from_dict()` — парсинг `analyt_steps` из списка dict в `AnalytStep`
- [x] 5.7 Обновить `from_dict()` — парсинг `api_uuid: data.get("api_uuid")`

## 6. Интеграционное тестирование

- [x] 6.1 Адхок-скрипт для полного пайплайна
  - [x] 6.1.1 Создать `SredaAPIClient` (mTLS + `login()` из env `SREDA_LOGIN`/`SREDA_PASSWORD`)
  - [x] 6.1.2 Вызвать `build_full_tree()` (все guide_id найдены `discover_guides()`, без хардкода)
  - [x] 6.1.3 Создать `SredaToDeviationCalcConverter`
  - [x] 6.1.4 Вызвать `converter.transform(tree)`
  - [x] 6.1.5 Валидация: количество иерархий >= 1, валидность Hierarchy
  - [x] 6.1.6 Проверить: все узлы имеют `api_uuid` (не None)
  - [x] 6.1.7 Проверить: узлы с `node_type="SUM"` имеют `type=MetricType.SUM`
  - [x] 6.1.8 Проверить: leaf-узлы (node_type=null) имеют `type=None`
  - [x] 6.1.9 Проверить: `source_params`/`aliases` заполнены из API (`missa_bidr...`, план/факт)
  - [x] 6.1.10 Перегенерировать `tests/sreda_api_output.json` без подстановки GUID
- [x] 6.2 Тесты на `build_filter_dict` — int значения, JSON-массив, Python-литерал `node_code`, пустой список
- [x] 6.3 Тест на `build_drill_order` — 1 компонент, 3 компонента, пустой список
- [x] 6.4 Тест на `build_dimensions` — 1 компонент, 2 компонента
- [x] 6.5 Тесты авторизации (`tests/test_sreda_login.py`, мок сессии)
- [x] 6.6 Тесты discovery (`tests/test_sreda_discover.py`, 5 справочников)
- [x] 6.7 Тесты связки сценарий → источник (`tests/test_sreda_scenario.py`, мок `fetch_guide`)
