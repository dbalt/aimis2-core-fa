## Why

Диалоговый сервис `aimis2-fa-dlg` требует структурированный отчёт факторного анализа (`data`) для инициализации LLM-диалога. Сейчас `FaServer` возвращает только текстовое `summary`, а `data` сохраняется в БД, но не отдаётся наружу. Navi Signal (aimis-backend) не может передать `data` в диалоговый сервис, т.к. не получает его от `FaClient`.

## What Changes

- `FaServerImpl._handle_get_deviation_summary()`: возврат `{'summary': summary, 'data': data}` вместо `{'summary': summary}`.
- `FaClient.get_summary()` (в `aimis-sdk` и копия в `aimis-backend`): возврат `Res[dict]` с ключами `{'summary': str, 'data': dict}` вместо `Res[str]`. Потребители берут значения по ключам — `result.data['summary'], result.data['data']`.

## Capabilities

### New Capabilities

- `fa-summary-with-data`: Возврат структурированного отчёта (`data`) вместе с текстовым саммари (`summary`) из сервиса факторного анализа, чтобы downstream-потребители (Navi Signal, диалоговый сервис) могли использовать `data` как FA-контекст для LLM.

### Modified Capabilities

(нет)

## Non-goals

- Не меняем логику расчёта ФА (`calculate_and_summarize_deviation()`, `collect_for_summary()`).
- Не меняем кэширование в БД (`save_results()` уже сохраняет `data`).
- Не меняем другие методы `FaClient` (`save_metadata`, `get_metadata`, `delete_metadata`).

## Impact

- **FaServer**: `_handle_get_deviation_summary()` — добавляется ключ `data` в возвращаемый dict.
- **FaClient.get_summary()**: возвращаемый тип меняется с `Res[str]` на `Res[dict]` — **BREAKING** для потребителей. Потребители берут значения по ключам: `result.data['summary'], result.data['data']`.
- **aimis-sdk** (`sdk/fa2026/client.py`): не имеет openspec, изменение вносится вручную.
- **aimis-backend** (`src/mbi/fa2026/client.py`): копия `FaClient`, отдельный openspec change.
- **Потребители `get_summary()` (все исправлены — переход на `result.data['summary']`):**
  - Production: `aimis2-core-fa/src/aivisor/server.py`, `aimis-backend/src/mbi/navi_signal/server.py`
  - Adhoc: `adhoc_opextb_summaries.py`, `adhoc_rozn_summaries.py`, `adhoc_test_fa_client.py`, `run_export_all_mds.py`, `run_template_lite_transforms.py`
- **Затронутые репозитории**: `aimis2-core-fa`, `aimis-sdk`, `aimis-backend`.
