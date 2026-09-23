## Context

`FaServerImpl` в `aimis2-core-fa` не принимает `client_session_id` от `BaseAppServerPart`, хотя тот вызывает `m__process_request(payload, client_session_id=mu.client_session_id)`. Из-за этого DataGate и GigaChat не получают csid, что приводит к `RuntimeError('client_session_id не передан')` на мягких стендах (ift/dev/vm_dev).

Изменения в других сервисах (aimis-backend, aimis2-fa-dlg) показали паттерн: `BaseAppServerPart.m__do_work` уже передаёт `mu.client_session_id` в `m__process_request`.

## Goals / Non-Goals

**Goals:**
- `FaServerImpl.m__process_request` принимает `client_session_id` и пробрасывает в обработчики
- `DataMgmtDataGate._exec/_query` передаёт csid в `GeneralSQLDataGateClientPart.get_data`
- `_base_llm_processing_function` передаёт csid в `GigaChatClientPartV2.ask_giga`
- Полная цепочка: BaseAppServerPart → FaServerImpl → DataMgmtDataGate → GeneralSQLDataGateClientPart
- Полная цепочка: BaseAppServerPart → FaServerImpl → calculate_and_summarize_deviation → summarize → _base_llm_processing_function → GigaChatClientPartV2

**Non-Goals:**
- Изменение сигнатур методов `DataMgmt` (базовый класс ABC) — передаём csid как параметр
- Модификация `BaseAppServerPart` и `DServerBase`
- Изменение логики вычислений (calc.py, aggr.py)

## Decisions

### Decision 1: Проброс csid через все обработчики FaServerImpl
**Выбор:** Добавить `client_session_id: str = '-1'` в `FaServerImpl.m__process_request`, передать в `_handle_*` методы.

**Альтернативы:**
1. Извлечь csid из `request_payload` — ❌ не работает, если csid не в payload (BaseAppServerPart передаёт отдельным параметром)
2. Добавить csid в payload в FaServerImpl — ❌ избыточно, payload не содержит metadata

**Решение:** Принимаем параметр как в SpSQLNaviServer (см. aimis-backend), используем как есть.

### Decision 2: DataMgmtDataGate принимает csid
**Выбор:** Добавить `client_session_id: str = '-1'` в `_exec` и `_query`, передать в `dgc.get_data`.

**Альтернативы:**
1. Сохранить csid в self — ❌ не thread-safe, воркеры разделяют экземпляр DataMgmt
2. Передавать через params — ❌ params — это SQL-параметры

**Решение:** Отдельный параметр, совместимо с существующими вызовами в FaServerImpl.

### Decision 3: GigaChat получает csid
**Выбор:** Добавить `client_session_id: str = '-1'` в `_base_llm_processing_function` и `summarize`, передать в `llm_client.ask_giga`.

**Решение:** Паттерн идентичен FaClient и DialogClient из aimis-backend.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Нарушение обратной совместимости из-за новых сигнатур | Дефолт `'-1'` сохраняет совместимость с существующими вызовами внутри сервиса |
| Утечка csid в логи | Логируем только первый символ csid, не полный ID |
| Пропуск csid в новом обработчике | Добавить pytest-тесты для каждого обработчика |

## Migration Plan

1. Deploy aimis2-core-fa с новыми сигнатурами
2. Запустить fa2026 на стенде ift/dev
3. Проверить что FaClient.get_summary_with_data(code, dt, csid) работает без ошибки csid
4. Мониторить логи на наличие `client_session_id не передан`

## Open Questions

Нет.
