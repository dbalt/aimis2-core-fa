## Why

FaServerImpl в aimis2-core-fa не реализует сквозную передачу `client_session_id` от точки входа до всех исходящих вызовов. При запросе от navi_signal через FaClient guard `_check_csid` в DataGateClient и GigaChatClient выбрасывает `RuntimeError`: "client_session_id не передан".

Конкретно:
1. `FaServerImpl.m__process_request` не имеет параметра `client_session_id`
2. `DataMgmtDataGate._exec/_query` не передаёт csid в `GeneralSQLDataGateClientPart.get_data`
3. `_base_llm_processing_function` не передаёт csid в `GigaChatClientPartV2.ask_giga`

## What Changes

- `FaServerImpl.m__process_request`: добавить параметр `client_session_id`, передавать в обработчики
- `DataMgmtDataGate`: принимать и передавать `client_session_id` в `dgc.get_data`
- `_base_llm_processing_function`: принимать и передавать `client_session_id` в `llm_client.ask_giga`
- `calculate_and_summarize_deviation` / `summarize`: передать csid в `_base_llm_processing_function`

## Capabilities

### Modified Capabilities
- `csid-transport`: требование к fa2026 серверу корректно передавать `client_session_id` во все исходящие вызовы (DataGate, GigaChat)

### New Capabilities
<!-- Нет новых capabilities — только исправление существующего транспорта csid -->

## Impact

| Файл | Действие |
|------|----------|
| `src/libfa2/fa_server.py` | Изменение — `FaServerImpl.m__process_request` принимает csid |
| `src/libfa2/data_access/data_mgmt.py` | Изменение — `DataMgmtDataGate` принимает и передаёт csid |
| `src/libfa2/fa_impl/summarize.py` | Изменение — `_base_llm_processing_function` принимает csid |
| `src/libfa2/fa_impl/all_together.py` | Изменение — передача csid в summarize |

**Незатрагиваемые зоны:**
- Вычисления отклонений (calc.py) — не делают исходящих вызовов SDK
- Metadata (hier_metadata) — локальная бизнес-логика
- DataAccess (aggr.py, conditions.py) — внутренние вычисления
- API Gateway и маршрутизация
