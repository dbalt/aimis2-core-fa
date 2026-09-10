## 1. aimis2-core-fa — FaServer (уже сделано, additive — остаётся в силе)

- [x] 1.1 В `src/libfa2/fa_server.py`, метод `_handle_get_deviation_summary()`: возвращать `{'summary': summary, 'data': data}`. Ключ `summary` не трогается — изменение additive. Проверить: `data` — dict из `calculate_and_summarize_deviation()`, уже сохраняется в БД через `save_results(code, dt, data, summary)`.
- [x] 1.2 Проверить ветку кэша: при `results_res.ok` возвращать `{'summary': summary, 'data': data}` где `data` берётся из `results_res.data` (кортеж `(data, summary)`).
- [x] 1.3 Добавить unit-тест: `_handle_get_deviation_summary()` возвращает dict с ключами `summary` и `data`.
- [x] 1.4 Добавить unit-тест: `data` в ответе JSON-сериализуем (`json.dumps(data, ensure_ascii=False)` не выбрасывает).
- [x] 1.5 Запустить тесты: `PYTHONPATH=src python -m pytest tests/ -v`.

## 2. aimis-sdk — контракты клиента без breaking changes

Изменение в `sdk/fa2026/client.py`, чтобы существующие потребители `get_summary()` не ломались:

- [x] 2.1 `get_summary()` возвращает `Res.mk_result(data_res.data['summary'])` — только текстовое саммари.
- [x] 2.2 Аннотация возвращаемого типа `get_summary()`: `Res[str]`.
- [x] 2.3 Добавить `get_summary_with_data(self, code: str, dt: date) -> Res[dict]`: то же действие `GET_DEVIATION_SUMMARY`, `return Res.mk_result(data_res.data)` — весь ответ FA-сервиса без трансформации.
- [x] 2.4 (Опционально) Вынести общую отправку запроса в приватный хелпер, возвращающий сырой `Res[dict]`, чтобы оба метода не дублировали payload.

## 3. aimis-backend — НЕ здесь

Копия `FaClient` (`src/mbi/fa2026/client.py`) и переход Navi Signal на `get_summary_with_data()` оформлены в openspec самого `aimis-backend` — change `add-fadlg-routing-and-dialog-client` (его задачи 1.x и 3.x). Здесь только контроль: после выкатки backend его задачи должны быть закрыты.

## 4. aimis2-core-fa — привести потребителей к `get_summary() -> Res[str]`

Потребители остаются на `get_summary()`, где `res.data` — строка. Как было до правок потребителей — в истории git: `git show af7324e^:<файл>`.

- [x] 4.1 `src/aivisor/server.py:121`: `return summary_res.data['summary']` → `return summary_res.data`.
- [x] 4.2 `src/adhoc/adhoc_opextb_summaries.py:32`: `summary = res.data['summary']` → `summary = res.data`.
- [x] 4.3 `src/adhoc/adhoc_rozn_summaries.py:32`: `summary = res.data['summary']` → `summary = res.data`.
- [x] 4.4 `src/adhoc/adhoc_test_fa_client.py:46`: `print(summ.data['summary'])` → `print(summ.data)`.
- [x] 4.5 `src/adhoc/run_export_all_mds.py:26`: `content.data['summary']` → `content.data`.
- [x] 4.6 `src/adhoc/run_template_lite_transforms.py:506`: `return res.data['summary']` → `return res.data`.

## 5. Проверка обратной совместимости

- [x] 5.1 Проверить грепом по `aimis2-core-fa`: ни один потребитель `get_summary()` не обращается к `res.data['...']`.
- [x] 5.2 `PYTHONPATH=src python -m pytest tests/ tests_dfb/ -v` (тесты `_handle_get_deviation_summary` из п. 1.3–1.4 остаются зелёными).
- [x] 5.3 Убедиться в независимости релизов: FA-сервис с полем `data` совместим со старым `FaClient`; новый `FaClient` с `get_summary_with_data()` требует FA-сервиса с полем `data`.
