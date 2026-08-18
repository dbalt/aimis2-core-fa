## Context

Микросервис `aimis2-core-fa` раскладывает финансовые отклонения факта от плана
по иерархии показателей SUM/MULTI/RATIO. Методанные ранее загружались напрямую из БД,
но в новой конфигурации платформы «Среда» (IFT) все метаданные экспонируются через
REST API:

- `/api/metadata/guide/{guide_id}` — справочники иерархии (metric_hier), фильтры (query_guide),
  алгоритмы аналитического разложения (drill_steps), сценарии (ФАСценарии),
  параметры источников (ФАПараметрыИсточников).
- mTLS-аутентификация (cert.pem + chain.pem + private.key) + cookie SID.
  SID получается программно через `POST /api/auth/login` (с fallback на Origin).
- Автопоиск справочников через `/api/metadata/v3/tree` — без хардкода GUID.

Проведено полное исследование API (см. `src/sreda_api_research.md`):
- 5 работающих справочников: `ФАИерархииПоказателей`, `ФАФильтрыЗапроса`,
  `ФАШагАлгоритмаАналитическогоРазложения`, `ФАСценарии`, `ФАПараметрыИсточников`.
- Enum-значения API возвращаются как строки: `"SUM"`, `"RATE"`, `"DENOMINATOR"`, `"1"`.
- Числовые значения (`node_type=2`) — временный баг API, игнорируются.
- 2 корневых сценария, 11 query-фильтров, 5 drill-step алгоритмов.
- Дерево иерархии: 2 уровня глубины, 14 узлов.
- Связка «сценарий ↔ источник» по GUID: `metric_hier[id] ⇔ scenario__hiers.hier
  ⇔ ФАСценарии.source ⇔ ФАПараметрыИсточников[id]`.

## Goals / Non-Goals

**Goals:**
1. Создать HTTP-клиент `SredaAPIClient` для работы с API платформы «Среда».
2. Реализовать dataclass-модели (`AnalytStep`, `DrillStepComponent`, `QueryFilterDetail`)
   с сериализацией/десериализацией.
3. Реализовать модуль `enum_mapper.py` для маппинга строковых значений API → enum-классы проекта.
4. Реализовать конвертер `SredaToDeviationCalcConverter` для трансформации API → DeviationCalcMetadata.
5. Поддержать drill-down через табличную часть `t_aimis_fa__analyt_drill_steps__components`.
6. Сохранить `api_uuid` в каждом `MetricNode` для отслеживания происхождения узла.
7. Обеспечить обратную совместимость — при отсутствии данных поведение не меняется.

**Non-Goals:**
- Загрузка метрик из БД — остаётся в `data_access`.
- Параллельная загрузка из API — один синхронный запрос к guide.
- Кэширование результатов — каждый вызов делает свежий запрос.
- Обратная конвертация (`reverse()`) — DeviationCalcMetadata → API JSON.
- Вынесение GUID в env-переменные — справочники находятся автоматически (`discover_guides()`).
- `raw_api_tree` в DeviationCalcMetadata — без модификации ядра.
- README и внешняя документация — в следующей итерации.

## Decisions

### 1. Три отдельных пакета вместо одного

**Decision:** `sreda_api/`, `sreda_models/`, `sreda_transform/` — три пакета.

**Rationale:** Разделение ответственности (SRP):
- `sreda_api` — сетевой уровень (mTLS, HTTP, retry).
- `sreda_models` — модель данных (dataclass, JSON, enum-маппинг).
- `sreda_transform` — бизнес-логика трансформации.

**Alternative:** Один пакет `sreda/`. Не подходит — нарушает SRP, затрудняет тестирование.

### 2. UUID как str, parent как int (hex→int % 2^31)

**Decision:** `MetricNode.id` остаётся `int`, parent — `int`. UUID из API (str) конвертируется
через `int(uuid, 16) % (2**31)`.

**Rationale:** Обратная совместимость — все существующие dataclass (`MetricNode`, `Hierarchy`,
`DeviationCalcMetadata`) работают с `int`. Изменение на `str` сломает сериализацию/десериализацию.

**Alternative:** Изменить `MetricNode.id` на `str`. Не подходит — сломает все существующие вызовы.

### 3. Enum-маппинг через отдельный модуль, не через модификацию enums.py

**Decision:** Создать `sreda_models/enum_mapper.py` с 4 статическими функциями:
`map_metric_type()`, `map_multi_part_type()`, `map_ratio_part_type()`, `map_mp_decomposition_type()`.

Исходные `hier_metadata/enums.py` остаются без изменений.

**Rationale:** 
- `hier_metadata/enums.py` — чистые enum-классы, без привязки к API.
- API возвращает строковые значения (`"SUM"`, `"1"`) — маппинг в lowercase ключи.
- Баг сервера: `mp_decomp_type="1"` маппится на `INTEGRAL`.
- Маппинг в одном месте — легко расширять и тестировать.

**Alternative:** Добавить `from_api_value()` в каждый enum-класс. Не подходит — нарушает чистоту enum-модуля.

### 4. DrillStepComponent → Algorithm.drill_order напрямую

**Decision:** `DrillStepComponent[]` → `[[col_name]]` → `Algorithm.drill_order`.

**Rationale:** Tabular part `t_aimis_fa__analyt_drill_steps__components` содержит
измерительные колонки (`col_name`, `col_descr`). Каждая колонка — это отдельный
элемент `drill_order`. `col_descr` маппится в `Dimension.name`.

**Alternative:** Создать отдельный `Algorithm` для каждого `step`. Не нужно —
все шаги одного сценария объединяются в один `Algorithm` с расширенным `drill_order`.

### 5. Автопоиск справочников по имени (discover_guides), без хардкода GUID

**Decision:** `SredaAPIClient` определяет guide_id справочников автоматически через
`discover_guides()`: корень схемы (`/api/metadata/v3/tree`) → класс `Guide` →
по именам ищет 5 справочников. GUID можно передать явно как fallback, но по умолчанию
не обязательны.

**Rationale:** GUID различаются между окружениями и вручную менять каждый вызов — ошибкоопасно.
Имена справочников уникальны (префикс «ФА»), поэтому идентификация по имени надёжна.

**Alternative:** Вынести GUID в env-переменные (`SREDA_METRIC_GUID`). Не нужно —
автопоиск убирает потребность в env-параметрах.

### 5a. Программная авторизация через POST /api/auth/login

**Decision:** `SredaAPIClient` получает cookie SID через `POST /api/auth/login`
(поля `login`/`password` в `SredaClientConfig`), авто-логин при первом использовании
сессии. При ответе 501 повторяет запрос с заголовком `Origin`.

**Rationale:** Ручное таскание SID в конфиге — не обслуживаемо. Креды тестовые
(`testfa`/`123`), в коде берутся из env с fallback, в репозиторий не коммитятся.

### 5b. Расчётный контур (source/plan/fact/aliases) — из API

**Decision:** `SourceParameters`, `SearchDevParameters` и `aliases` заполняются из API:
`ФАСценарии` → `ФАПараметрыИсточников` через связку по GUID (`_resolve_scenario`).
Дефолты конвертера остаются как fallback при отсутствии данных.

**Rationale:** Это закрывает требование «всё должно приходить из апи»: имя источника,
колонки периода/плана/факта и их подписи (`col_*`) действительно экспонируются
платформой. Раньше эти значения брались из дефолтов конвертера.

### 6. `api_uuid` в MetricNode вместо `raw_api_tree` в DCM

**Decision:** Каждый `MetricNode` получает поле `api_uuid: str | None` — UUID узла
из Среды. Без добавления `raw_api_tree` в `DeviationCalcMetadata`.

**Rationale:**
- `MetricNode.api_uuid` позволяет отслеживать происхождение узла и выполнять
  точечные обновления без модификации ядра.
- `raw_api_tree` в DCM — это изменение существующего класса, которое лучше
  вынести в отдельное изменение.
- Обратная конвертация (DCM → API JSON) отложена на следующую итерацию.

**Alternative:** Сохранить `raw_api_tree` в DCM. Не подходит — требует модификации ядра.

## Risks / Trade-offs

| Риск | Уровень | Митигация |
|------|---------|-----------|
| Сервер Среды недоступен | Средний | Fallback на старый путь загрузки из БД (в следующей итерации) |
| Изменения структуры API | Средний | Unit-тесты на существующих JSON-ответах (`sreda_responses/`) |
| Производительность рекурсивного обхода | Низкий | `max_depth=5`, кэш в следующей итерации |
| Числовые enum-значения (`node_type=2`) | Низкий | Игнорировать — временный баг API, маппер поддерживает только строки |
| Enum-маппинг не покрывает все значения | Низкий | `from_api_value()` → `None` для неизвестных значений |

## Migration Plan

### Фаза 1: Enum-маппер
1. Создать `sreda_models/enum_mapper.py` с 4 функциями.
2. Написать тесты на маппинг (строки, `None`, `"1"`).

### Фаза 2: sreda_api (HTTP-клиент)
1. Создать `sreda_api/exceptions.py` и `client.py`.
2. Реализовать `SredaAPIClient`: mTLS, `login()` (POST /api/auth/login), `fetch_guide`,
   `fetch_children`, `discover_guides()`, `build_full_tree`, `_resolve_scenario()`.
3. Тесты на модули пакетов (без сетевых вызовов, с моком fetch/session).

### Фаза 3: sreda_models (dataclass-модели)
1. Создать `sreda_models/` — `AnalytStep`, `DrillStepComponent`, `QueryFilterDetail`.
2. Реализовать методы сериализации/десериализации.
3. Реализовать `build_drill_order()`, `build_dimensions()`, `build_filter_dict()`.

### Фаза 4: sreda_transform (конвертер) + интеграция
1. Создать `sreda_transform/to_metadata.py` — `SredaToDeviationCalcConverter`.
2. Модифицировать `hier_metadata/metric_node.py` — добавить `analyt_steps` + `api_uuid`.
3. Integration-тест на полный пайплайн: API → DCM → валидация.

### Обратная совместимость
- При `query_filters = []` — `MetricNode.query = None` (поведение не меняется).
- При `drill_steps = []` — `MetricNode.analyt_metadata = None` (поведение не меняется).
- `api_uuid = None` по умолчанию — существующий код не ломается.
