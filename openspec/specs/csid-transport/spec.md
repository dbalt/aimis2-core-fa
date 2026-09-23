# csid-transport Specification

## Purpose
Определяет требование к серверу fa2026 (aimis2-core-fa) корректно передавать `client_session_id` от точки входа через все обработчики до DataGate и GigaChat.
## Requirements
### Requirement: FaServerImpl SHALL передавать client_session_id в обработчики
Сервер `FaServerImpl.m__process_request` SHALL принимать `client_session_id` от `BaseAppServerPart` и передавать его во все обработчики (GET_DEVIATION_SUMMARY, DELETE_METADATA, SAVE_METADATA, GET_METADATA, DELETE_RESULTS, DELETE_RESULTS_FOR_DT).

#### Scenario: GET_DEVIATION_SUMMARY получает csid
- **WHEN** входящий запрос от FaClient с `client_session_id='abc-123'`
- **THEN** `FaServerImpl.m__process_request` передаёт csid в `_handle_get_deviation_summary`
- **THEN** csid доходит до `calculate_and_summarize_deviation`

#### Scenario: SAVE_METADATA получает csid
- **WHEN** входящий запрос от FaClient с `client_session_id='abc-123'`
- **THEN** `FaServerImpl.m__process_request` передаёт csid в `_handle_save_metadata`
- **THEN** csid доходит до `DataMgmt.save_metadata`

### Requirement: DataMgmtDataGate SHALL пробрасывать csid в DataGate
Все методы `DataMgmtDataGate` (`_exec`, `_query`) SHALL передавать `client_session_id` в `GeneralSQLDataGateClientPart.get_data`.

#### Scenario: _exec передаёт csid в DataGate
- **WHEN** вызван `DataMgmtDataGate._exec(sql, params)` с `client_session_id='abc-123'`
- **THEN** вызывается `dgc.get_data(sql=sql, params=params, client_session_id='abc-123')`
- **THEN** сформированный MsgUnit содержит `client_session_id='abc-123'`

#### Scenario: _query передаёт csid в DataGate
- **WHEN** вызван `DataMgmtDataGate._query(sql, params)` с `client_session_id='abc-123'`
- **THEN** вызывается `dgc.get_data(sql=sql, params=params, client_session_id='abc-123')`
- **THEN** сформированный MsgUnit содержит `client_session_id='abc-123'`

### Requirement: GigaChat SHALL получать csid для саммаризации
Функции `_base_llm_processing_function` и `summarize` SHALL передавать `client_session_id` в `GigaChatClientPartV2.ask_giga`.

#### Scenario: _base_llm_processing_function передаёт csid
- **WHEN** вызван `_base_llm_processing_function(system_prompt, data, llm_client, llm_model)` с `client_session_id='abc-123'`
- **THEN** вызывается `llm_client.ask_giga(msgs, model=llm_model, client_session_id='abc-123')`
- **THEN** сформированный MsgUnit содержит `client_session_id='abc-123'`

#### Scenario: summarize передаёт csid в _base_llm_processing_function
- **WHEN** вызван `summarize(data, fn_get_llm_client, model_summary, model_details, client_session_id='abc-123')`
- **THEN** вызывается `_base_llm_processing_function` с `client_session_id='abc-123'`
- **THEN** GigaChat получает csid

### Requirement: Сервис fa2026 должен передавать client_session_id во все исходящие вызовы
Сервис fa2026 MUST передавать `client_session_id` от точки входа (BaseAppServerPart) до всех исходящих вызовов SDK (DataGate, GigaChat). Если csid не задан, используется дефолт '-1'. На мягких стендах (ift, dev, vm_dev) csid обязательно должен быть передан.

#### Scenario: Все вызовы DataGate получают csid
- **WHEN** входящий запрос от FaClient с `client_session_id='abc-123'`
- **THEN** `DataMgmtDataGate._exec` вызывает `dgc.get_data(client_session_id='abc-123')`
- **THEN** `DataMgmtDataGate._query` вызывает `dgc.get_data(client_session_id='abc-123')`

#### Scenario: Все вызовы GigaChat получают csid
- **WHEN** запрос требует саммаризации через GigaChat с `client_session_id='abc-123'`
- **THEN** `_base_llm_processing_function` вызывает `llm_client.ask_giga(client_session_id='abc-123')`

#### Scenario: Сервис работает на мягких стендах без ошибок
- **WHEN** стенд в `_CSID_SOFT_STANDS` ('ift', 'dev', 'vm_dev')
- **THEN** все вызовы DataGate и GigaChat содержат `client_session_id`
- **THEN** guard `_check_csid` НЕ выбрасывает `RuntimeError`

