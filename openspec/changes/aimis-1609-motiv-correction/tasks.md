# Tasks: Мотивационная корректировка

## Группа 1: Создание MotivCorrectionMetadata и get_motiv_correction_data()

- [x] 1.1 Создать файл `src/libfa2/fa_impl/motiv_correction.py`
- [x] 1.2 Определить `MotivCorrectionMetadata` dataclass с полем `query: Query`
- [x] 1.3 Реализовать `to_dict()`, `to_json()`, `to_json_str()`
- [x] 1.4 Реализовать `from_dict()`, `from_json()`, `from_json_str()`
- [x] 1.5 Создать функцию `get_motiv_correction_data(metadata, rep_dt, data_access, fallback_source_params, fallback_search_dev_params) -> Res[DataRow | None]`
- [x] 1.6 В `get_motiv_correction_data()`: проверка `metadata is None` → возврат `Res.mk_result(None)`
- [x] 1.7 В `get_motiv_correction_data()`: определение `source_params` и `search_dev_params` (fallback логика)
- [x] 1.8 В `get_motiv_correction_data()`: формирование `ConditionSet.from_dict(metadata.query.to_dict())`
- [x] 1.9 В `get_motiv_correction_data()`: добавление `ConditionSet({rep_dt_column: rep_dt})` через `ConditionAnd`
- [x] 1.10 В `get_motiv_correction_data()`: вызов `data_access.get_aggr_data(source, grp_by_columns=None, aggr_columns=[plan, fact], conditions)`
- [x] 1.11 В `get_motiv_correction_data()`: возврат `DataRow.from_dict(result[0], search_dev_params)` или `Res.mk_result(None)` при пустом результате

## Группа 2: Интеграция в DeviationCalcMetadata

- [x] 2.1 Добавить поле `motiv_correction: MotivCorrectionMetadata | None = None` в `DeviationCalcMetadata`
- [x] 2.2 Обновить `to_dict()` — включать `"motiv_correction": metadata.motiv_correction.to_dict()` когда не `None`
- [x] 2.3 Обновить `to_json()` — включать ключ при наличии данных
- [x] 2.4 Обновить `from_dict()` — читать `data.get("motiv_correction")` и вызывать `MotivCorrectionMetadata.from_dict()`
- [x] 2.5 Убедиться, что `from_json` / `from_json_str` работают через `from_dict`

## Группа 3: Модификация collect_for_summary

- [x] 3.1 Добавить параметр `motiv_correction_row: DataRow | None = None` в `collect_for_summary`
- [x] 3.2 В `_process_drill_component`: проверка `motiv_correction_row is not None` и `(row.plan != 0 or row.fact != 0)`
- [x] 3.3 При выполнении условия: прибавить `motiv_correction` к `dc.amts.plan`, `dc.amts.fact`, `dc.amts.deviation`, пересчитать `dc.amts.impact`
- [x] 3.4 При выполнении условия: вставить `data["motiv_correction"] = {"plan": ..., "fact": ..., "deviation": ..., "label": "мотивационной корректировки"}`
- [x] 3.5 При невыполнении условия (None или 0/0): не вставлять ключ, не менять amounts
- [x] 3.6 Убедиться, что `_has_negative_in_tree` не затронут (дочерние impact без изменений)

## Группа 4: Модификация calculate_and_summarize_deviation

- [x] 4.1 Импортировать `get_motiv_correction_data` из `motiv_correction`
- [x] 4.2 Добавить в `asyncio.TaskGroup` вызов `get_motiv_correction_data()` параллельно с `calculate_deviations`
- [x] 4.3 Распаковать результаты: `drills = [t.result() for t in tsk_lst[:-1]]`, `motiv_res = tsk_lst[-1].result()`
- [x] 4.4 Обработать `motiv_res`: если `motiv_res.ok`, взять `motiv_row = motiv_res.data`, иначе `motiv_row = None`
- [x] 4.5 Логгировать предупреждение при ошибке: `lgr.warning(f'Failed to load motiv correction: {motiv_res.err}')`
- [x] 4.6 Перед `collect_for_summary` проверить тип `motiv_correction` из `deviation_calc_metadata` — импортировать `MotivCorrectionMetadata`
- [x] 4.7 Передавать `motiv_correction_row` во все вызовы `collect_for_summary(x, motiv_correction_row=motiv_row)`

## Группа 5: Модификация summarize.py — build_branch_report

- [x] 5.1 В `build_branch_report()`: после сборки `short_summary`, `key_factors`, `table` — проверить `data.get("motiv_correction")`
- [x] 5.2 Если ключ есть и (`motiv["plan"] != 0` или `motiv["fact"] != 0`):
  - [x] 5.2.1 Вычислить `plan_before = amounts.plan - motiv.plan`
  - [x] 5.2.2 Вычислить `fact_before = amounts.fact - motiv.fact`
  - [x] 5.2.3 Сформировать `motiv_text` с блоком ⚠️
- [x] 5.3 Вставить `motiv_text` в конец `final_report`
- [x] 5.4 При отсутствии ключа или нулевых значениях — блок не добавлять

## Группа 6: Тесты

- [x] 6.1 Тест: `MotivCorrectionMetadata.to_dict()` / `from_dict()` сериализация/десериализация
- [x] 6.2 Тест: `MotivCorrectionMetadata.to_json()` / `from_json()` — без пустых полей
- [x] 6.3 Тест: `DeviationCalcMetadata` с `motiv_correction` → `to_dict()` включает ключ
- [x] 6.4 Тест: `DeviationCalcMetadata` без `motiv_correction` → `to_dict()` не включает ключ
- [x] 6.5 Тест: `get_motiv_correction_data(None, ...)` → `Res.mk_result(None)`
- [x] 6.6 Тест: `get_motiv_correction_data()` с моком `data_access` — успешная загрузка
- [x] 6.7 Тест: `get_motiv_correction_data()` — пустой результат БД → `None`
- [x] 6.8 Тест: `collect_for_summary()` с ненулевой корректировкой → amounts скорректированы, ключ в JSON
- [x] 6.9 Тест: `collect_for_summary()` с нулевой корректировкой → amounts без изменений, ключ отсутствует
- [x] 6.10 Тест: `collect_for_summary()` — impact дочерних узлов не меняется
- [x] 6.11 Тест: `build_branch_report()` с мотив. корректировкой → текст содержит блок ⚠️
- [x] 6.12 Тест: `build_branch_report()` без мотив. корректировки → текст без блока
- [x] 6.13 Тест: end-to-end — полный конвейер с `motiv_correction` заданным и данными в БД
- [x] 6.14 Тест: end-to-end — полный конвейер без `motiv_correction` (обратная совместимость)
