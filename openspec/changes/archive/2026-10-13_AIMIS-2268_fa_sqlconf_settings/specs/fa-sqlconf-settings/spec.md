## Purpose

Чтение настроек сервиса факторного анализа (начиная с precompute-конфига саммаризации) из общей таблицы конфигураций `missa_aimis.t_config` (ClickHouse) через SQL-конфиг SDK, чтобы управлять значениями вручную, без перевыкладки конфиг-пакета сервиса. Переносит источник precompute-конфига (см. `summarize-precompute-config`) с файлового конфига на `t_config`; требования к структуре и валидации precompute-конфига остаются в силе.

## ADDED Requirements

### Requirement: precompute-конфиг читается из t_config

Сервис факторного анализа SHALL читать precompute-конфиг саммаризации по пути `#sqlconf.core_fa_settings.summarize.precompute` (SDK sqlconf: `SELECT val FROM missa_aimis.t_config FINAL WHERE key = 'core_fa_settings'`, JSON из `val`, путь `summarize.precompute` внутри него). Файловый ключ `configs.fa2026.summarize.precompute` источником больше не является. Результат SHALL проходить `validate_precompute_cfg()` без изменений валидации.

#### Scenario: строка в t_config задана

- **WHEN** в `t_config` есть строка `key='core_fa_settings'`, `val` — корректный JSON с путём `summarize.precompute`
- **THEN** сервис стартует с `precompute_cfg = validate_precompute_cfg(<значение по пути>)`

#### Scenario: строка отсутствует, JSON битый или таблица недоступна

- **WHEN** чтение не удалось (нет строки, битый JSON, ошибка DataGate)
- **THEN** `get_conf` возвращает `None`, в лог пишется warning (от `sdk.tools.sqlconf`), сервис стартует с дефолтом (все ручки `code`)

### Requirement: val — один JSON с вложенным summarize

`val` для ключа `core_fa_settings` SHALL быть одним JSON-документом, содержащим вложенный объект `summarize` (внутри — `precompute`). Последующие настройки core-fa SHALL добавляться секциями в тот же JSON, а не новыми строками таблицы.

#### Scenario: текущее рабочее значение

- **WHEN** `val = {"summarize":{"precompute":{"selection":{"mode":"llm"}}}}`
- **THEN** `selection.mode = llm`, остальные ручки — дефолт (`code`)

### Requirement: приложение read-only по t_config

Приложение SHALL только читать `t_config`. Запись значений (INSERT/UPDATE) SHALL выполняться вручную (эксплуатация/DBA) — из кода приложения и при старте записи быть не должно.

#### Scenario: старт приложения не пишет в t_config

- **WHEN** сервис стартует
- **THEN** ни один компонент не выполняет запись в `t_config`

### Requirement: эффективный конфиг логируется на старте

Сервис SHALL логировать (info) эффективный precompute-конфиг после валидации, чтобы по логу можно было проверить, что реально подействовало (в т.ч. сработала ли деградация к дефолту).

#### Scenario: лог при старте

- **WHEN** `run()` прочитала и провалидировала конфиг
- **THEN** в лог пишется info-сообщение с сериализованным эффективным конфигом

### Requirement: чтение однократное, на старте

Конфиг SHALL читаться один раз при старте сервиса (в `run__fa_server.run()`); hot-reload не требуется — обновление значения требует рестарта пода.

#### Scenario: правка в t_config без рестарта

- **WHEN** значение в `t_config` изменено после старта
- **THEN** сервис продолжает работать с конфигом, прочитанным на старте
