## Purpose

Возврат структурированного отчёта (`data`) вместе с текстовым саммари (`summary`) из сервиса факторного анализа `aimis2-core-fa`, чтобы downstream-потребители (Navi Signal → диалоговый сервис aimis2-fa-dlg) могли использовать `data` как FA-контекст для инициализации LLM-диалога.

## ADDED Requirements

### Requirement: FaServer возвращает summary и data

Сервис факторного анализа SHALL возвращать в ответе на `GET_DEVIATION_SUMMARY` оба поля: `summary` (текстовое саммари) и `data` (структурированный отчёт — дерево DrillComponent с план/факт/отклонениями/top_factors).

#### Scenario: Ответ содержит оба поля

- **WHEN** `FaServerImpl._handle_get_deviation_summary()` успешно завершает расчёт
- **THEN** возвращается `{'summary': <str>, 'data': <dict>}` где `data` — JSON-сериализуемый dict

#### Scenario: Ответ из кэша содержит оба поля

- **WHEN** результаты найдены в кэше (`DataMgmt.get_results()`)
- **THEN** возвращается `{'summary': <str>, 'data': <dict>}` где `data` восстанавливается из кэша БД

### Requirement: FaClient.get_summary возвращает Res[dict] с доступом по ключам

`FaClient.get_summary()` SHALL возвращать `Res[dict]` где `Res.data` — это dict с ключами `{'summary': str, 'data': dict}`. Потребители SHALL обращаться к значениям по ключам: `result.data['summary'], result.data['data']`. Формат `Res.data` совпадает с форматом ответа FA-сервиса — `FaClient` отдаёт `Res.result(data_res.data)` без трансформации.

#### Scenario: Успешный вызов get_summary

- **WHEN** `FaClient.get_summary(code, dt)` получает успешный ответ от FA-сервиса
- **THEN** возвращается `Res.result({'summary': <str>, 'data': <dict>})`

#### Scenario: Ошибка от FA-сервиса

- **WHEN** FA-сервис возвращает ошибку
- **THEN** возвращается `Res.error(<сообщение об ошибке>)`

#### Scenario: Потребитель берёт summary по ключу

- **WHEN** потребитель вызывает `result = await fa_client.get_summary(code, dt)` и обращается к `result.data['summary']`
- **THEN** возвращается строка с текстовым саммари

#### Scenario: Потребитель берёт data по ключу

- **WHEN** потребитель вызывает `result = await fa_client.get_summary(code, dt)` и обращается к `result.data['data']`
- **THEN** возвращается dict со структурированным отчётом

### Requirement: data — JSON-сериализуемый dict

Поле `data` SHALL быть JSON-сериализуемым dict, содержащим результаты `collect_for_summary()` — дерево факторов с план/факт/отклонениями, готовое для передачи в системный промпт диалогового сервиса.

#### Scenario: data сериализуется в JSON

- **WHEN** `data` возвращается из `calculate_and_summarize_deviation()`
- **THEN** `json.dumps(data, ensure_ascii=False)` выполняется без ошибок и содержит ключи `"data"` (список результатов) и опционально `"motiv_correction"`, `"plan_alias"`, `"fact_alias"`
