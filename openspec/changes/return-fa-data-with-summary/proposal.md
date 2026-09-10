## Why

Диалоговый сервис `aimis2-fa-dlg` требует структурированный отчёт факторного анализа (`data`) для инициализации LLM-диалога. Сейчас `FaServer` возвращает только текстовое `summary`, а `data` сохраняется в БД, но не отдаётся наружу. Navi Signal (aimis-backend) не может передать `data` в диалоговый сервис, т.к. не получает его от `FaClient`.

## What Changes

**Принцип: никаких ломающих изменений контрактов.** Существующие методы и типы не меняются, `data` отдаётся новым методом.

- `FaServerImpl._handle_get_deviation_summary()`: возврат `{'summary': summary, 'data': data}` вместо `{'summary': summary}` — **additive** (существующий ключ `summary` не меняется, добавляется новый).
- `FaClient.get_summary()` (в `aimis-sdk` и копия в `aimis-backend`): **контракт не меняется** — остаётся `Res[str]` с текстовым саммари (`Res.mk_result(data_res.data['summary'])`). Кто получал `summary`, получает его как раньше.
- **Новый метод** `FaClient.get_summary_with_data()` (в `aimis-sdk` и копия в `aimis-backend`): `Res[dict]` с ключами `{'summary': str, 'data': dict}` — для потребителей, которым нужен структурированный `data`.
- Потребитель, которому нужен `data` (`aimis-backend`: Navi Signal → aimis2-fa-dlg), переходит на `get_summary_with_data()`. Остальные потребители остаются на `get_summary()` **без правок**.

## Capabilities

### New Capabilities

- `fa-summary-with-data`: Возврат структурированного отчёта (`data`) вместе с текстовым саммари (`summary`) из сервиса факторного анализа через отдельный метод `get_summary_with_data()`, чтобы downstream-потребители (Navi Signal, диалоговый сервис) могли использовать `data` как FA-контекст для LLM, не затрагивая существующий `get_summary()`.

### Modified Capabilities

(нет)

## Non-goals

- Не меняем логику расчёта ФА (`calculate_and_summarize_deviation()`, `collect_for_summary()`).
- Не меняем кэширование в БД (`save_results()` уже сохраняет `data`).
- Не меняем другие методы `FaClient` (`save_metadata`, `get_metadata`, `delete_metadata`).
- **Не меняем сигнатуру и возвращаемый тип `get_summary()`** — обратная совместимость приоритетнее единообразия.

## Impact

- **FaServer**: `_handle_get_deviation_summary()` — добавляется ключ `data` в возвращаемый dict (additive; потребители, читающие `summary`, не затрагиваются).
- **FaClient.get_summary()**: без изменений — `Res[str]`.
- **FaClient.get_summary_with_data()**: новый метод, `Res[dict]` с ключами `summary` / `data`.
- **aimis-sdk** (`sdk/fa2026/client.py`): не имеет openspec, изменение вносится вручную — `get_summary()` с контрактом `Res[str]` + новый `get_summary_with_data()` (как было до промежуточной правки — `git show 09bda56^:sdk/fa2026/client.py`).
- **aimis-backend** (`src/mbi/fa2026/client.py`): копия `FaClient`, те же правки; свой openspec change `add-fadlg-routing-and-dialog-client`.
- **Потребители**:
  - `aimis2-core-fa/src/aivisor/server.py` — остаётся на `get_summary()`, возврат `summary_res.data` (строка).
  - `aimis2-core-fa/src/adhoc/*` (`adhoc_opextb_summaries.py`, `adhoc_rozn_summaries.py`, `adhoc_test_fa_client.py`, `run_export_all_mds.py`, `run_template_lite_transforms.py`) — остаются на `get_summary()`, `res.data` (строка).
  - `aimis-backend/src/mbi/navi_signal/server.py` — **единственный**, кто переходит на `get_summary_with_data()` (ему нужен `data` для `fa_init`).
- **Затронутые репозитории**: `aimis2-core-fa`, `aimis-sdk`, `aimis-backend`.
