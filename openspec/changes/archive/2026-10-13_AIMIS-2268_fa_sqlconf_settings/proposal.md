## Why

Конфиг предвычислений саммаризации (`configs.fa2026.summarize.precompute`) сейчас читается из локального файла `configs/fa2026.json` — правка значения требует перевыкладки конфиг-пакета сервиса. Нужно управлять настройкой через общую таблицу конфигураций `missa_aimis.t_config` (ClickHouse), ключ `core_fa_settings`: значения записываются в таблицу вручную (эксплуатацией), приложение только читает.

## What Changes

- `src/run__fa_server.py`: чтение precompute-конфига переносится с файлового ключа `configs.fa2026.summarize.precompute` на SQL-конфиг `#sqlconf.core_fa_settings.summarize.precompute` (готовый механизм SDK — `sdk/tools/sqlconf.py`: `SELECT val FROM missa_aimis.t_config FINAL WHERE key = 'core_fa_settings'` через DataGate, JSON из `val`, путь `summarize.precompute` внутри него).
- `configs.fa2026.json`: блок `summarize` удаляется — файл больше не является источником этого параметра.
- Эффективный (провалидированный) precompute-конфиг логируется на старте (info).
- При недоступности таблицы / отсутствии строки / битовом JSON — деградация к дефолту (все ручки `code`) + warning в логе от `sdk.tools.sqlconf`.
- Валидация `validate_precompute_cfg()` и плумбинг (`FaServerImpl → all_together → summarize`) не меняются — меняется только источник значения.

## Capabilities

### New Capabilities

- `fa-sqlconf-settings`: настройки сервиса факторного анализа (начиная с precompute-конфига саммаризации) читаются из общей таблицы `t_config` (ключ `core_fa_settings`, в `val` — один JSON с вложенным `summarize`) через SQL-конфиг SDK; файловые конфиги источником этих настроек больше не являются.

### Modified Capabilities

(нет — спецификация `summarize-precompute-config` не изменяется: её требования к структуре и валидации precompute-конфига остаются в силе, меняется только источник значения)

## Non-goals

- Hot-reload конфига: чтение выполняется один раз на старте сервиса, обновление значений требует рестарта.
- Любая запись в `t_config` из кода приложения (в том числе при старте) — значения вносятся вручную.
- Перенос остальных настроек (`models`, `tables`, `gigachat_cert_source` и пр.) на SQL-конфиг.
- Изменение структуры и валидации precompute-конфига (см. `summarize-precompute-config`).

## Impact

- **Код**: `src/run__fa_server.py` (замена ключа `get_conf` + info-лог эффективного конфига), `configs.fa2026.json` (удаление блока `summarize`).
- **SDK**: используется готовый механизм `#sqlconf.` (`sdk/tools/sqlconf.py`) — правки SDK не требуются.
- **Инфраструктура**: в `missa_aimis.t_config` вручную должна существовать запись `key='core_fa_settings'` с JSON в `val` — до выкатки сервиса (иначе сервис стартует с дефолтом «всё code»).
- **Тесты**: проверка, что файловый блок `summarize` удалён и чтение идёт по sqlconf-пути.
- **Затронутые репозитории**: только `aimis2-core-fa`.
