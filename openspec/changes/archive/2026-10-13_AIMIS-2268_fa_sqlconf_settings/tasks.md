## 1. aimis2-core-fa — перенос источника конфига

- [x] 1.1 `src/run__fa_server.py`: `get_conf('configs.fa2026.summarize.precompute', None)` → `get_conf('#sqlconf.core_fa_settings.summarize.precompute', None)`; вызов `validate_precompute_cfg()` остаётся без изменений.
- [x] 1.2 `src/run__fa_server.py`: после валидации — info-лог эффективного конфига (`lgr.info(f'precompute_cfg: {precompute_cfg}')`); `lgr` в `run()` уже создан.
- [x] 1.3 `configs.fa2026.json`: удалить блок `summarize` (файл больше не источник этого параметра).
- [x] 1.4 Проверить грепом: в `src/` не осталось чтений файлового ключа `configs.fa2026.summarize.precompute`.

## 2. Тесты

- [x] 2.1 Тест: `configs.fa2026.json` не содержит ключа `summarize` (источник перенесён, деградация к дефолту при отсутствии sqlconf-строки покрыта `validate_precompute_cfg(None)` в `tests/test_precompute_config.py`).
- [x] 2.2 Проверить: `tests/test_precompute_config.py` остаётся зелёным (валидатор не менялся).
- [x] 2.3 `PYTHONPATH=src python -m pytest tests/ -v` — все зелёные.

## 3. Спецификация и эксплуатация

- [x] 3.1 Синхронизировать дельту: `openspec/changes/AIMIS-2268_fa_sqlconf_settings/specs/fa-sqlconf-settings/spec.md` → `openspec/specs/fa-sqlconf-settings/spec.md` (новая capability; старая спека `summarize-precompute-config` не трогается).
- [x] 3.2 Ручной шаг (эксплуатация/DBA, вне кода, ДО выкатки сервиса): `INSERT INTO missa_aimis.t_config (key, val) VALUES ('core_fa_settings', '{"summarize":{"precompute":{"selection":{"mode":"llm"}}}}');`

## 4. Проверка на стенде

- [x] 4.1 Старт сервиса при наличии строки в `t_config`: в логе info с эффективным конфигом (`selection.mode=llm`).
- [x] 4.2 Старт сервиса при отсутствии строки: в логе warning от sqlconf + info с дефолтным конфигом (всё `code`), сервис стартует.
