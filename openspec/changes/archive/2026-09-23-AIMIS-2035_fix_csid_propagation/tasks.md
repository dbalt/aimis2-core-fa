## 1. Обновить FaServerImpl.m__process_request

- [x] 1.1 Добавить параметр `client_session_id: str = '-1'` в `m__process_request`
- [x] 1.2 Передать `client_session_id` во все `_handle_*` методы (GET_DEVIATION_SUMMARY, DELETE_METADATA, SAVE_METADATA, GET_METADATA, DELETE_RESULTS, DELETE_RESULTS_FOR_DT)

## 2. Обновить DataMgmtDataGate

- [x] 2.1 Добавить `client_session_id: str = '-1'` в абстрактные `_exec` и `_query` в `DataMgmt`
- [x] 2.2 Передать `client_session_id` в `GeneralSQLDataGateClientPart.get_data` из `DataMgmtDataGate._exec`
- [x] 2.3 Передать `client_session_id` в `GeneralSQLDataGateClientPart.get_data` из `DataMgmtDataGate._query`
- [x] 2.4 Обновить `DataMgmtDbWrapper._exec` и `_query` (принять, но не использовать csid)

## 3. Обновить GigaChat вызовы

- [x] 3.1 Добавить `client_session_id: str = '-1'` в `_base_llm_processing_function`
- [x] 3.2 Передать `client_session_id` в `llm_client.ask_giga` из `_base_llm_processing_function`
- [x] 3.3 Добавить `client_session_id: str = '-1'` в функцию `summarize`
- [x] 3.4 Передать `client_session_id` в `_base_llm_processing_function` из `summarize`

## 4. Обновить calculate_and_summarize_deviation

- [x] 4.1 Добавить `client_session_id: str = '-1'` в `calculate_and_summarize_deviation`
- [x] 4.2 Передать `client_session_id` в `summarize` из `calculate_and_summarize_deviation`

## 5. Валидация

- [x] 5.1 Запустить `openspec validate AIMIS-2035_fix_csid_propagation --type change`
- [x] 5.2 Проверить что все вызовы DataGate и GigaChat в fa2026 имеют csid

## 6. Тесты

- [x] 6.1 Написать тесты для FaServerImpl (test_fa_server_csid.py)
- [x] 6.2 Написать тесты для DataMgmtDataGate (test_data_mgmt_csid.py)
- [x] 6.3 Написать тесты для summarize (test_summarize_csid.py)
- [x] 6.4 Написать тесты для calculate_and_summarize_deviation (test_calculate_deviation_csid.py)
