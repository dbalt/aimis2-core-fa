## 1. aimis2-core-fa — FaServer

- [x] 1.1 В `src/libfa2/fa_server.py`, метод `_handle_get_deviation_summary()`: изменить возврат с `{'summary': summary}` на `{'summary': summary, 'data': data}`. Проверить: `data` — dict из `calculate_and_summarize_deviation()`, уже сохраняется в БД через `save_results(code, dt, data, summary)`.
- [x] 1.2 Проверить ветку кэша: при `results_res.ok` возвращать `{'summary': summary, 'data': data}` где `data` берётся из `results_res.data` (кортеж `(data, summary)`).
- [x] 1.3 Добавить unit-тест: `_handle_get_deviation_summary()` возвращает dict с ключами `summary` и `data`.
- [x] 1.4 Добавить unit-тест: `data` в ответе JSON-сериализуем (`json.dumps(data, ensure_ascii=False)` не выбрасывает).
- [x] 1.5 Запустить тесты: `PYTHONPATH=src python -m pytest tests/ -v`.

## 2. aimis-sdk — FaClient.get_summary()

- [x] 2.1 В `sdk/fa2026/client.py`, метод `get_summary()`: изменить `return Res.mk_result(data_res.data['summary'])` на `return Res.mk_result(data_res.data)` — отдаёт весь dict без трансформации.
- [x] 2.2 Обновить return-тип в аннотации: `Res[str]` → `Res[dict]`.

## 3. aimis-backend — копия FaClient

- [x] 3.1 В `src/mbi/fa2026/client.py`, метод `get_summary()`: аналогичное изменение — `return Res.mk_result(data_res.data)` вместо `return Res.mk_result(data_res.data['summary'])`.
- [x] 3.2 Обновить return-тип в аннотации: `Res[str]` → `Res[dict]`.
- [x] 3.3 Добавить unit-тест: `get_summary()` возвращает `Res[dict]` с ключами `summary` и `data`.
- [x] 3.4 Добавить unit-тест: `result.data['summary']` возвращает строку, `result.data['data']` возвращает dict.
- [x] 3.5 Запустить тесты aimis-backend.

## 4. Фикс потребителей — переход на доступ по ключам

- [x] 4.1 `aimis2-core-fa/src/aivisor/server.py:121`: `return summary_res.data` → `return summary_res.data['summary']`.
- [x] 4.2 `aimis-backend/src/mbi/navi_signal/server.py:605`: `'message': summary_res.data` → `'message': summary_res.data['summary']`.
- [x] 4.3 `aimis2-core-fa/src/adhoc/adhoc_opextb_summaries.py:32`: `summary = res.data` → `summary = res.data['summary']`.
- [x] 4.4 `aimis2-core-fa/src/adhoc/adhoc_rozn_summaries.py:32`: `summary = res.data` → `summary = res.data['summary']`.
- [x] 4.5 `aimis2-core-fa/src/adhoc/adhoc_test_fa_client.py:46`: `print(summ)` → `print(summ.data['summary'])`.
- [x] 4.6 `aimis2-core-fa/src/adhoc/run_export_all_mds.py:26`: `content.data` → `content.data['summary']`.
- [x] 4.7 `aimis2-core-fa/src/adhoc/run_template_lite_transforms.py:506`: `return res.data` → `return res.data['summary']`.
