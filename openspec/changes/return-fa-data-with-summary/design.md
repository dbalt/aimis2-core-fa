## Context

Изменение затрагивает 3 репозитория: `aimis2-core-fa` (FaServer), `aimis-sdk` (FaClient), `aimis-backend` (копия FaClient).

Текущий поток: Navi Signal → FaClient → aimis2-core-fa возвращает только `summary`. Диалоговый сервис `aimis2-fa-dlg` требует `data` для инициализации LLM-диалога.

`aimis-backend` не использует `aimis-sdk` как внешний пакет — у него собственная копия `FaClient` в `src/mbi/fa2026/client.py`. Изменения нужно вносить в оба места.

## Goals / Non-Goals

**Goals:**
- FaServer возвращает `data` вместе с `summary` — additive к существующему ответу.
- Новый метод `FaClient.get_summary_with_data()` отдаёт `Res[dict]` с доступом по ключам.
- `FaClient.get_summary()` остаётся `Res[str]` — ни один существующий потребитель не требует правок.

**Non-Goals:**
- Не меняем логику расчёта ФА.
- Не меняем кэширование в БД.
- Не унифицируем `get_summary()` под новый формат ценой breaking change.

## Decisions

### Decision 1: FaServer отдаёт data без трансформации (additive)

`_handle_get_deviation_summary()` уже имеет `data` (dict из `calculate_and_summarize_deviation()`). Изменение: добавить `'data': data` в возвращаемый dict. `data` уже JSON-сериализуем (сохраняется в БД через `json.dumps()`).

Существующий ключ `summary` не трогается, поэтому ответ остаётся совместимым: потребитель, читающий только `summary`, продолжает работать без изменений.

### Decision 2: `get_summary()` не меняется, `data` отдаётся новым методом

Вместо смены возвращаемого типа `get_summary()` с `Res[str]` на `Res[dict]` (это ломало бы всех потребителей) вводится отдельный метод:

- `get_summary(code, dt) -> Res[str]` — как раньше: `Res.mk_result(data_res.data['summary'])`.
- `get_summary_with_data(code, dt) -> Res[dict]` — `Res.mk_result(data_res.data)`, т.е. весь ответ FA-сервиса без трансформации.

Оба метода отправляют одно и то же действие `GET_DEVIATION_SUMMARY` и различаются только извлечением значения из ответа.

**Альтернатива A (отклонена): менять `get_summary()` на `Res[dict]`.** Требует синхронной правки всех потребителей в трёх репозиториях и согласованного релиза `aimis-sdk` / `aimis-backend` / `aimis2-core-fa`; рассинхрон версий ломает прод. Отклонено.

**Альтернатива B (отклонена): DTO-класс.** Лишняя сущность, dict с ключами достаточен и совместим с форматом ответа.

**Альтернатива C (отклонена): флаг `with_data: bool = False` у `get_summary()`.** Тип возврата становится `Res[Union[str, dict]]`, что непредсказуемо для вызывающего кода и всё равно требует правок типов.

### Decision 3: Изменение вносится в aimis-sdk и aimis-backend параллельно

`aimis-sdk` не имеет openspec. Изменение в `sdk/fa2026/client.py` вносится вручную: `get_summary()` с контрактом `Res[str]` и новый `get_summary_with_data()`. `aimis-backend` имеет openspec — отдельный change `add-fadlg-routing-and-dialog-client`, где копия клиента правится идентично.

### Decision 4: Из потребителей переходит только Navi Signal

Единственному потребителю, которому нужен `data`, — `aimis-backend/src/mbi/navi_signal/server.py` (передача в `fa_init` диалогового сервиса) — достаточно вызвать `get_summary_with_data()` и взять `res.data['data']`.

`aimis2-core-fa/src/aivisor/server.py` и adhoc-скрипты остаются на `get_summary()`, где `res.data` — строка; обращения по ключу `res.data['summary']` из них убираются (первоначальный вид — `git show af7324e^:<файл>`).

## Risks / Trade-offs

- **Дублирование запроса в двух методах клиента** → вынести общую отправку в приватный хелпер, возвращающий сырой `Res[dict]`; публичные методы лишь извлекают нужное. Публичный контракт важнее DRY.
- **Разъезд двух копий клиента** (`aimis-sdk` и `aimis-backend`) → держим сигнатуры идентичными, покрываем тестами контракта в каждом репозитории.
- **Лишний метод в API** (`get_summary` + `get_summary_with_data`) → принято осознанно: обратная совместимость дешевле одного метода.
- **Additive-ключ `data` в ответе FA-сервиса** → безопасен: потребителей со строгой валидацией схемы ответа нет, а `get_summary()` лишние ключи игнорирует.
- **Размер ответа** → `data` (дерево drill) заметно больше `summary`; payload передаётся через KeyDB. Рост трафика принимается, при необходимости — отдельная оптимизация (вне рамок изменения).
