## ADDED Requirements

### Requirement: SredaAPIClient MUST поддерживать программную авторизацию (POST /api/auth/login)

Клиент MUST уметь получать cookie SID автоматически через `POST /api/auth/login`
вместо ручного таскания SID в конфигурации. Креды задаются в `SredaClientConfig`
поля `login`, `password`; при ответе 501 запрос повторяется с заголовком `Origin`
(из `config.origin`).

#### Scenario: Авторизация с кредами возвращает cookie

- **WHEN** в `SredaClientConfig` заданы `login` и `password`
- **THEN** `SredaAPIClient.login()` вызывает `POST /api/auth/login` с телом `{"login","password"}`
- **THEN** при ответе 200 cookie SID сохраняются в сессию (доступны для последующих запросов)

#### Scenario: Авторизация при ответе 501 с fallback на Origin

- **WHEN** первый `POST /api/auth/login` возвращает 501 и задан `origin`
- **THEN** клиент повторяет запрос с заголовком `Origin: <origin>`
- **THEN** если второй ответ 200 — cookie сохраняются в сессию

#### Scenario: Авто-логин при первом использовании сессии

- **WHEN** в конфиге заданы креды, `auto_login=True` и нет готовых `cookies`
- **THEN** при первом вызове `_get_session()` выполняется `login()`
- **THEN** если в конфиге переданы готовые `cookies` — они приоритетнее, авто-логин не выполняется

#### Scenario: Ошибка авторизации

- **WHEN** креды не заданы или сервер возвращает статус != 200
- **THEN** бросается `SredaAPIError` с описанием

### Requirement: SredaAPIClient MUST поддерживать mTLS-аутентификацию и GET-запросы к API Среды

Средне-клиент MUST подключаться к API платформы «Среда» с использованием mTLS (cert.pem + chain.pem + private.key)
и cookie SID, выполнять GET-запросы к `/api/metadata/guide/{guide_id}` с JSON-опциями
и возвращать разобранный ответ в виде `dict`.

#### Scenario: Создание клиента с конфигурацией

- **WHEN** создаётся `SredaAPIClient(config=SredaClientConfig(cert_dir=..., cookies={"SID": "..."}))`
- **THEN** клиент инициализирует SSL context и httpx session

#### Scenario: Создание клиента с отсутствующими сертификатами

- **WHEN** `cert_dir` не существует
- **THEN** `SredaClientConfig.__post_init__` бросает `FileNotFoundError`

#### Scenario: Запрос guide данных с настройками по умолчанию

- **WHEN** вызывается `fetch_guide("fde17d36-...")`
- **THEN** отправляется `GET /api/metadata/guide/fde17d36-...?options={limit:200, withTabularParts:true, order:[["code","ASC"]]}`
- **THEN** возвращается `dict` с полями `rows` и `cols`

#### Scenario: Запрос guide с WHERE-фильтром

- **WHEN** вызывается `fetch_guide("fde17d36-...", where={"parent": "b0220ce2-..."})`
- **THEN** отправляется запрос с `options.where={"parent": "b0220ce2-..."}`
- **THEN** в `rows` возвращаются только дочерние записи корневого узла `b0220ce2`

#### Scenario: Запрос guide без TabularParts

- **WHEN** вызывается `fetch_guide("fde17d36-...", with_tabular_parts=False)`
- **THEN** отправляется запрос с `options.withTabularParts=false`
- **THEN** в `rows` отсутствуют поля `TabularParts`

#### Scenario: Ошибка HTTP (status != 200)

- **WHEN** сервер возвращает статус 500
- **THEN** бросается `SredaHTTPError` с `guide_id`, `status_code` и `body`

### Requirement: SredaAPIClient MUST поддерживать рекурсивный обход иерархии

Клиент MUST рекурсивно обходить дерево метрик по GUID guide_id, получая children
для каждого узла до заданной глубины, с пометкой `_depth` и `_children` в каждом элементе.

#### Scenario: Обход иерархии глубиной 2

- **WHEN** вызывается `fetch_children("b0220ce2-...", "fde17d36-...", max_depth=2)`
- **THEN** для каждого child рекурсивно запрашиваются grandchildren
- **THEN** в результате child содержит поле `_children: [...]` с массивом grandchildren
- **THEN** каждый child содержит поле `_depth: 1`, grandchildren содержат `_depth: 2`

#### Scenario: Остановка обхода на максимальной глубине

- **WHEN** вызывается `fetch_children("b0220ce2-...", "fde17d36-...", max_depth=1)`
- **THEN** возвращаются только дети root-узла
- **THEN** у каждого child `_children` пустой `[]`

#### Scenario: Обход с пустым результатом

- **WHEN** вызывается `fetch_children("9e11f0c7-...", "fde17d36-...")`
- **THEN** возвращается пустой список `[]` (у этого узла нет детей)

### Requirement: SredaAPIClient MUST поддерживать получение query-фильтров

Клиент MUST находить запись по `query_uuid` в guide query_guide и извлекать
табличную часть `t_aimis_fa__query_filters__details`.

#### Scenario: Получение фильтров для query

- **WHEN** вызывается `fetch_query_filters("5d463b5b-d231-4c60-b7b0-4e33575ac565", "b3c03b04-...")`
- **THEN** отправляется запрос к `/api/metadata/guide/b3c03b04-...?options.where={id:"5d463b5b-..."}`
- **THEN** из `TabularParts.t_aimis_fa__query_filters__details` извлекаются записи фильтров
- **THEN** возвращается `list[dict]` с полями `id`, `code`, `owner`, `rank`, `col_name`, `value`

#### Scenario: Запрос фильтров для query без записей

- **WHEN** вызывается `fetch_query_filters("nonexistent-uuid", "b3c03b04-...")`
- **THEN** возвращается пустой список `[]`

### Requirement: SredaAPIClient MUST поддерживать получение drill-step алгоритмов

Клиент MUST находить шаг алгоритма разложения по `step_uuid` в step_guide
и извлекать табличную часть `t_aimis_fa__analyt_drill_steps__components`.

#### Scenario: Получение drill-компонентов для шага

- **WHEN** вызывается `fetch_step_algorithm("c74fe30d-62b1-4b1d-900f-80f91ca465b0", "3f3292e9-...")`
- **THEN** отправляется запрос к `/api/metadata/guide/3f3292e9-...`
- **THEN** среди `rows` находится запись с `id == step_uuid`
- **THEN** из `TabularParts.t_aimis_fa__analyt_drill_steps__components` извлекаются компоненты
- **THEN** возвращается `list[dict]` с полями `id`, `code`, `owner`, `rank`, `col_name`, `col_descr`

#### Scenario: Запрос несуществующего step

- **WHEN** вызывается `fetch_step_algorithm("nonexistent-uuid", "3f3292e9-...")`
- **THEN** возвращается пустой список `[]`

### Requirement: SredaAPIClient MUST поддерживать авто-поиск справочников (discover_guides)

Клиент MUST находить guide_id справочников ФА автоматически, без хардкода GUID,
проходя дерево схемы метаданных через `GET /api/metadata/v3/tree`.

#### Scenario: Авто-поиск всех пяти справочников ФА

- **WHEN** вызывается `discover_guides()`
- **THEN** от корня схемы (`SREDA_METADATA_ROOT_ID`) ищется класс `Guide`
- **THEN** в списке справочников по имени находятся:
  - `ФАИерархииПоказателей` → `metric_guide`
  - `ФАФильтрыЗапроса` → `query_guide`
  - `ФАШагАлгоритмаАналитическогоРазложения` → `step_guide`
  - `ФАСценарии` → `scenario_guide`
  - `ФАПараметрыИсточников` → `src_params_guide`
- **THEN** возвращается `dict` с этими пятью ключами

#### Scenario: Класс Guide не найден

- **WHEN** в корне схемы нет узла класса `Guide`
- **THEN** бросается `SredaAPIError`

#### Scenario: Справочник отсутствует в схеме

- **WHEN** в списке справочников нет одного из ФА-гайдов
- **THEN** бросается `SredaAPIError` с перечислением пропущенных справочников

### Requirement: SredaAPIClient MUST поддерживать сбор полного дерева

GUID можно передать явно либо опустить — тогда они находятся автоматически через
`discover_guides()`, без хардкода.

Клиент MUST собрать полный сценарий: метрику, query-фильтры, drill-шаги, детей,
а также метаданные сценария из `ФАСценарии` и параметры его источника из
`ФАПараметрыИсточников`.

#### Scenario: Сбор полного дерева

- **WHEN** вызывается `build_full_tree()`
- **THEN** для каждой записи в `rows` метрики:
  - Загружаются query-фильтры (если `query` не null)
  - Загружаются drill-шаги из `t_aimis_fa__metric_hier__analyt_steps`
  - Для каждого шага загружаются компоненты из step_guide
  - Загружаются дети через `fetch_children`
- **THEN** через `_resolve_scenario` по GUID (`scenario__hiers.hier == record.id`)
  находится сценарий в `ФАСценарии`
- **THEN** по `scenario.source` (GUID) из `ФАПараметрыИсточников` берутся параметры источника
- **THEN** каждый сценарий содержит `record`, `query_filters`, `drill_steps`, `children`
- **THEN** при наличии связки — также `scenario` и `source_params`
- **THEN** возвращается `dict` с ключами `scenarios` и `guides` (все 5 найденных id)

#### Scenario: Сбор дерева для сценария без query и drill

- **WHEN** `build_full_tree()` для узла с `query=null`
- **THEN** `query_filters = []`
- **THEN** `drill_steps = []`

#### Scenario: Связка сценария по GUID (`_resolve_scenario`)

- **WHEN** иерархия `record.id` совпадает с `hier` в `t_aimis_fa__scenario__hiers`
- **THEN** возвращается `{'scenario': {...}, 'source_params': {...}}`
- **THEN** `source_params` берётся из `ФАПараметрыИсточников` по `scenario.source`
- **WHEN** сценарий не найден
- **THEN** возвращается `None`
