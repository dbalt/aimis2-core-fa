## ADDED Requirements

### Requirement: Модуль enum_mapper.py MUST маппить строковые значения API → enum-классы проекта

Модуль `sreda_models/enum_mapper.py` **MUST** содержать 4 функции для маппинга строковых значений
из API Среды в enum-классы `hier_metadata.enums`.

Исходные `hier_metadata/enums.py` не модифицируются.

#### Scenario: map_metric_type с "SUM"

- **WHEN** `map_metric_type("SUM")`
- **THEN** возвращается `MetricType.SUM`

#### Scenario: map_metric_type с "sum" (нижний регистр)

- **WHEN** `map_metric_type("sum")`
- **THEN** возвращается `MetricType.SUM`

#### Scenario: map_metric_type с "MULTI"

- **WHEN** `map_metric_type("MULTI")`
- **THEN** возвращается `MetricType.MULTI`

#### Scenario: map_metric_type с "RATIO"

- **WHEN** `map_metric_type("RATIO")`
- **THEN** возвращается `MetricType.RATIO`

#### Scenario: map_metric_type с "1" (баг сервера)

- **WHEN** `map_metric_type("1")`
- **THEN** возвращается `None` (значение не маппится, т.к. "1" не соответствует ни одному типу)

#### Scenario: map_metric_type с None

- **WHEN** `map_metric_type(None)`
- **THEN** возвращается `None`

### Requirement: map_multi_part_type MUST маппить "RATE" и "BASE"

Функция `map_multi_part_type` **MUST** преобразовывать строковые значения из API в `ComponentMultiPartType`.

- **WHEN** `map_multi_part_type("RATE")`
- **THEN** возвращается `ComponentMultiPartType.RATE`

#### Scenario: map_multi_part_type с "base"

- **WHEN** `map_multi_part_type("base")`
- **THEN** возвращается `ComponentMultiPartType.BASE`

#### Scenario: map_multi_part_type с None

- **WHEN** `map_multi_part_type(None)`
- **THEN** возвращается `None`

### Requirement: map_ratio_part_type MUST маппить "NUMERATOR" и "DENOMINATOR"

Функция `map_ratio_part_type` **MUST** преобразовывать строковые значения из API в `ComponentRatioPartType`.

#### Scenario: map_ratio_part_type с "DENOMINATOR"

- **WHEN** `map_ratio_part_type("DENOMINATOR")`
- **THEN** возвращается `ComponentRatioPartType.DENOMINATOR`

#### Scenario: map_ratio_part_type с "NUMERATOR"

- **WHEN** `map_ratio_part_type("NUMERATOR")`
- **THEN** возвращается `ComponentRatioPartType.NUMERATOR`

#### Scenario: map_ratio_part_type с None

- **WHEN** `map_ratio_part_type(None)`
- **THEN** возвращается `None`

### Requirement: map_mp_decomposition_type MUST маппить "Integral", "DirectBase" и "1"

Функция `map_mp_decomposition_type` **MUST** преобразовывать строковые значения из API в `MultipartDecompositionType`.

#### Scenario: map_mp_decomposition_type с "Integral"

- **WHEN** `map_mp_decomposition_type("Integral")`
- **THEN** возвращается `MultipartDecompositionType.INTEGRAL`

#### Scenario: map_mp_decomposition_type с "DirectBase"

- **WHEN** `map_mp_decomposition_type("DirectBase")`
- **THEN** возвращается `MultipartDecompositionType.DIRECT_BASE`

#### Scenario: map_mp_decomposition_type с "DirectRate"

- **WHEN** `map_mp_decomposition_type("DirectRate")`
- **THEN** возвращается `MultipartDecompositionType.DIRECT_RATE`

#### Scenario: map_mp_decomposition_type с "AverageWeighted"

- **WHEN** `map_mp_decomposition_type("AverageWeighted")`
- **THEN** возвращается `MultipartDecompositionType.AVERAGE_WEIGHTED`

#### Scenario: map_mp_decomposition_type с "1" (баг сервера)

- **WHEN** `map_mp_decomposition_type("1")`
- **THEN** возвращается `MultipartDecompositionType.INTEGRAL`

#### Scenario: map_mp_decomposition_type с None

- **WHEN** `map_mp_decomposition_type(None)`
- **THEN** возвращается `None`

### Requirement: AnalytStep MUST поддерживать сериализацию и десериализацию

Dataclass `AnalytStep` **MUST** описывать шаг аналитического разложения из табличной части
`t_aimis_fa__metric_hier__analyt_steps` и поддерживать методы `to_dict()`, `from_dict()`,
`from_api_record()`.

#### Scenario: Создание AnalytStep

- **WHEN** создаётся `AnalytStep(id="abc", code=1, owner="def", rank=1, step="c74fe30d...")`
- **THEN** объект содержит все 5 обязательных полей

#### Scenario: Сериализация в dict

- **WHEN** вызывается `step.to_dict()`
- **THEN** возвращается `dict` с ключами `id`, `code`, `owner`, `rank`, `step`

#### Scenario: Десериализация из dict

- **WHEN** вызывается `AnalytStep.from_dict({"id": "abc", "code": 1, "owner": "def", "rank": 1, "step": "c74fe30d..."})`
- **THEN** создаётся объект с полями, идентичными входному `dict`

#### Scenario: Создание из API-записи

- **WHEN** вызывается `AnalytStep.from_api_record({"id": "abc", "code": 1, "owner": "def", "rank": 1, "step": "c74fe30d..."})`
- **THEN** создаётся объект с полями, скопированными из ключей API-записи

### Requirement: DrillStepComponent MUST поддерживать сериализацию и десериализацию

Dataclass `DrillStepComponent` **MUST** описывать компонент шага из табличной части
`t_aimis_fa__analyt_drill_steps__components` и поддерживать методы `to_dict()`,
`from_dict()`, `from_api_record()`.

#### Scenario: Создание DrillStepComponent

- **WHEN** создаётся `DrillStepComponent(id="abc", code=4, owner="c74fe30d...", rank=1, col_name="tb", col_descr="ТБ")`
- **THEN** объект содержит все 6 обязательных полей

#### Scenario: Сериализация в dict

- **WHEN** вызывается `comp.to_dict()`
- **THEN** возвращается `dict` с ключами `id`, `code`, `owner`, `rank`, `col_name`, `col_descr`

#### Scenario: Десериализация из dict

- **WHEN** вызывается `DrillStepComponent.from_dict({"id": "abc", "code": 4, "owner": "c74fe30d...", "rank": 1, "col_name": "tb", "col_descr": "ТБ"})`
- **THEN** создаётся объект с полями, идентичными входному `dict`

### Requirement: build_drill_order MUST собирать DrillStepComponent[] в drill_order

Функция `build_drill_order(components)` **MUST** сортировать компоненты по `rank`
и возвращать список списков `[col_name]` для каждого компонента.

#### Scenario: Сбор drill_order из одного компонента

- **WHEN** `components = [DrillStepComponent(col_name="tb", rank=1)]`
- **THEN** `build_drill_order(components)` возвращает `[["tb"]]`

#### Scenario: Сбор drill_order из нескольких компонентов

- **WHEN** `components = [DrillStepComponent(col_name="prod_l1", rank=3), DrillStepComponent(col_name="tb", rank=1), DrillStepComponent(col_name="prod_l2", rank=2)]`
- **THEN** `build_drill_order(components)` возвращает `[["tb"], ["prod_l2"], ["prod_l1"]]`

#### Scenario: Сбор drill_order из пустого списка

- **WHEN** `components = []`
- **THEN** `build_drill_order(components)` возвращает `[]`

### Requirement: build_dimensions MUST собирать DrillStepComponent[] в словарь Dimension

Функция `build_dimensions(components)` **MUST** создавать словарь `col_name → Dimension`
для каждого компонента.

#### Scenario: Сбор измерений из одного компонента

- **WHEN** `components = [DrillStepComponent(col_name="biz_block", col_descr="Бизнес-блок", rank=1)]`
- **THEN** `build_dimensions(components)` возвращает `{"biz_block": Dimension(code="biz_block", name="Бизнес-блок", column="biz_block")}`

#### Scenario: Сбор измерений из нескольких компонентов

- **WHEN** `components = [DrillStepComponent(col_name="tb", col_descr="ТБ", rank=1), DrillStepComponent(col_name="prod_l1", col_descr="Продукт ЕК ур.1", rank=2)]`
- **THEN** `build_dimensions(components)` возвращает словарь с двумя элементами по `col_name`

### Requirement: QueryFilterDetail MUST поддерживать сериализацию и десериализацию

Dataclass `QueryFilterDetail` **MUST** описывать фильтр запроса из табличной части
`t_aimis_fa__query_filters__details` и поддерживать методы `to_dict()`, `from_dict()`,
`from_api_record()`.

#### Scenario: Создание QueryFilterDetail

- **WHEN** создаётся `QueryFilterDetail(id="abc", code=1, owner="def", rank=1, col_name="ind_id", value="49")`
- **THEN** объект содержит все 6 полей

#### Scenario: Сериализация в dict

- **WHEN** вызывается `detail.to_dict()`
- **THEN** возвращается `dict` с ключами `id`, `code`, `owner`, `rank`, `col_name`, `value`

#### Scenario: Десериализация из dict

- **WHEN** вызывается `QueryFilterDetail.from_dict({"id": "abc", "code": 1, "owner": "def", "rank": 1, "col_name": "ind_id", "value": "49"})`
- **THEN** создаётся объект с полями, идентичными входному `dict`

### Requirement: build_filter_dict MUST собирать QueryFilterDetail[] в {col_name: value}

Функция `build_filter_dict(details)` **MUST** сортировать детали по `rank`, парсить
JSON-строки и числа, и возвращать словарь `{col_name: value}`.

#### Scenario: Сбор filter_dict из одного компонента

- **WHEN** `details = [QueryFilterDetail(col_name="ind_id", value="49", rank=1)]`
- **THEN** `build_filter_dict(details)` возвращает `{"ind_id": 49}`

#### Scenario: Сбор filter_dict из JSON-массива

- **WHEN** `details = [QueryFilterDetail(col_name="node_code", value='["PL_01_03_01", "PL_14_45_08"]', rank=3)]`
- **THEN** `build_filter_dict(details)` возвращает `{"node_code": ["PL_01_03_01", "PL_14_45_08"]}`

#### Scenario: Сбор filter_dict из нескольких компонентов

- **WHEN** `details = [QueryFilterDetail(col_name="total_type", value="3", rank=2), QueryFilterDetail(col_name="ind_id", value="49", rank=1)]`
- **THEN** `build_filter_dict(details)` возвращает `{"ind_id": 49, "total_type": 3}`

#### Scenario: Сбор filter_dict из пустого списка

- **WHEN** `details = []`
- **THEN** `build_filter_dict(details)` возвращает `{}`
