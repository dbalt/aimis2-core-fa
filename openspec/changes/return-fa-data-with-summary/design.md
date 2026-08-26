## Context

Изменение затрагивает 3 репозитория: `aimis2-core-fa` (FaServer), `aimis-sdk` (FaClient), `aimis-backend` (копия FaClient).

Текущий поток: Navi Signal → FaClient → aimis2-core-fa возвращает только `summary`. Диалоговый сервис `aimis2-fa-dlg` требует `data` для инициализации LLM-диалога.

`aimis-backend` не использует `aimis-sdk` как внешний пакет — у него собственная копия `FaClient` в `src/mbi/fa2026/client.py`. Изменения нужно вносить в оба места.

## Goals / Non-Goals

**Goals:**
- FaServer возвращает `data` вместе с `summary`.
- FaClient.get_summary() возвращает `Res[dict]` с доступом по ключам.

**Non-Goals:**
- Не меняем логику расчёта ФА.
- Не меняем кэширование в БД.

## Decisions

### Decision 1: FaServer отдаёт data без трансформации

`_handle_get_deviation_summary()` уже имеет `data` (dict из `calculate_and_summarize_deviation()`). Изменение: добавить `'data': data` в возвращаемый dict. `data` уже JSON-сериализуем (сохраняется в БД через `json.dumps()`).

### Decision 2: FaClient отдаёт Res.result(data_res.data) без трансформации

Вместо `Res.mk_result(data_res.data['summary'])` — `Res.mk_result(data_res.data)`. Формат ответа FA-сервиса (`{'summary': ..., 'data': ...}`) и формат `Res.data` совпадают. Потребители берут значения по ключам: `result.data['summary'], result.data['data']`.

**Альтернатива:** Ввести отдельный DTO-класс. Отклонено — лишняя сущность, dict с ключами достаточен и обеспечивает совместимость.

### Decision 3: Изменение вносится в aimis-sdk и aimis-backend параллельно

`aimis-sdk` не имеет openspec. Изменение в `sdk/fa2026/client.py` вносится вручную. `aimis-backend` имеет openspec — отдельный change `add-fadlg-routing-and-dialog-client`.

## Risks / Trade-offs

- **[BREAKING] FaClient.get_summary() меняет возвращаемый тип** → потребители, использующие `result.data` как строку, сломаются. Смягчение: все потребители обновлены одновременно — переход на доступ по ключам `result.data['summary']`.
- **Production-потребители (исправлены):**
  - `aimis2-core-fa/src/aivisor/server.py` — `return summary_res.data['summary']`
  - `aimis-backend/src/mbi/navi_signal/server.py` — `'message': summary_res.data['summary']`
- **Adhoc-скрипты (исправлены):**
  - `aimis2-core-fa/src/adhoc/adhoc_opextb_summaries.py`
  - `aimis2-core-fa/src/adhoc/adhoc_rozn_summaries.py`
  - `aimis2-core-fa/src/adhoc/adhoc_test_fa_client.py`
  - `aimis2-core-fa/src/adhoc/run_export_all_mds.py`
  - `aimis2-core-fa/src/adhoc/run_template_lite_transforms.py`
