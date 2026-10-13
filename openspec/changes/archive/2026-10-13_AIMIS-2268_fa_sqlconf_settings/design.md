## Context

precompute-конфиг саммаризации (capability `summarize-precompute-config`) сейчас читается из файла: `run__fa_server.py` → `get_conf('configs.fa2026.summarize.precompute', None)` → `validate_precompute_cfg()`. Файловый `get_conf` кэширует результат навсегда (`functools.cache`), но вызывается один раз на старте — правки значения требуют перевыкладки конфиг-пакета.

В SDK уже есть готовый механизм SQL-конфига: `get_conf('#sqlconf.<код>.<путь>')` (`sdk/tools/sqlconf.py`) — `SELECT val FROM missa_aimis.t_config FINAL WHERE key = <код>` через DataGate, парсинг JSON из `val`, кэш 30 с, ошибки чтения не поднимаются (возвращается default). Схема таблицы: `key String, val String (JSON), updated_at DateTime`, `ReplacingMergeTree(updated_at) ORDER BY key`. Пока ни один сервис механизм не использует — наш будет первым.

## Goals / Non-Goals

**Goals:**
- precompute-конфиг читается из `t_config` (ключ `core_fa_settings`) — правка значения вручную, без перевыкладки сервиса.
- Логирование эффективного конфига на старте (info) + warning при недоступности (даёт SDK).
- Деградация к дефолту (всё `code`) при ошибке чтения.

**Non-Goals:**
- Hot-reload — чтение однократное, на старте.
- Запись в `t_config` из кода (в т.ч. на старте) — только ручные операции эксплуатации.
- Перенос остальных настроек сервиса.
- Изменение структуры/валидации precompute-конфига.

## Decisions

### Decision 1: `val` — один JSON с вложенным `summarize`; читаем путь внутри JSON

`t_config`: `key='core_fa_settings'`, `val` — один JSON-документ; путь чтения `#sqlconf.core_fa_settings.summarize.precompute`. Ключ множественного числа (`core_fa_settings`) рассчитан на будущие секции — новые настройки core-fa дописываются секциями в тот же `val` без создания новых строк таблицы (по образцу SDK-примера `fa_sched_settings`).

**Альтернатива B (отклонена): `val` = ровно словарь precompute.** Для каждой новой настройки потребовалась бы отдельная строка в `t_config` и свой ключ — против духа имени `core_fa_settings`.

### Decision 2: точка чтения не меняется — `run__fa_server.py`, один раз на старте

Меняется только префикс ключа в существующем вызове `get_conf`. TTL кэша sqlconf (30 с) в этой схеме не задействован: чтение однократное. Валидация `validate_precompute_cfg()` остаётся без изменений (fail-fast на старте при невалидной структуре JSON).

**Альтернатива (отклонена): чтение в `summarize()` на каждый вызов.** Дало бы hot-reload (TTL 30 с), но усложняет плумбинг и противоречит согласованному решению — hot-reload не требуется.

### Decision 3: деградация к дефолту + логирование

`sqlconf` при ошибке чтения / отсутствии строки / битовом JSON возвращает `None` → `validate_precompute_cfg(None)` → `DEFAULT_PRECOMPUTE` (всё `code`). SDK уже пишет warning (`[sqlconf] read failed ...` / `no row for key ...`). Дополнительно в `run__fa_server.py` — info-лог эффективного (провалидированного) конфига.

### Decision 4: запись значений — ручная операция вне кода

Приложение read-only по `t_config`: никаких INSERT/UPDATE из кода и при старте. Ручной шаг эксплуатации (до выкатки сервиса):

```sql
INSERT INTO missa_aimis.t_config (key, val) VALUES
('core_fa_settings', '{"summarize":{"precompute":{"selection":{"mode":"llm"}}}}');
```

## Risks / Trade-offs

- **Строка в `t_config` не создана / таблица недоступна при старте** → сервис стартует с дефолтом (всё `code`) молча для пользователя — смягчается warning-логом SDK и info-логом эффективного конфига; операционная проверка — grep по логу при старте.
- **Битый JSON в `val`** → sqlconf глотает ошибку → дефолт; структурная валидация `validate_precompute_cfg` остаётся (fail-fast на старте при валидном JSON, но неверной структуре).
- **Поведенческое отличие после выкатки**: файл давал `selection.mode=llm`; если INSERT не выполнен, сервис станет считать selection кодом. Митигируется порядком: ручной INSERT до выкатки (см. tasks, п. 3.2).
