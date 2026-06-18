# Отчёт по задаче 28: Логирование в adhoc-рутинах трансформации template_lite

**Дата:** 2026-06-18
**Задача:** [28_improve_adhoc_transform_routines.md](../tasks/28_improve_adhoc_transform_routines.md)
**Статус:** ✅ Выполнено

---

## 1. Суть задачи

Добавить логирование в функцию `main` модуля
[`adhoc.run_template_lite_transforms`](../../src/adhoc/run_template_lite_transforms.py)
и во все транзитивно вызываемые функции, расположенные в модуле `adhoc` и его
подмодулях.

Объект логгера получается вызовом `get_logger()` из
`sdk.core.logging` **в начале каждой функции** (функция анализирует точку вызова
через `sys._getframe().f_back.f_code.co_qualname` и именует логгер по
квалифицированному имени вызвавшей функции, поэтому вызов обязан стоять первой
исполняемой строкой функции — после docstring).

Распределение по уровням согласно постановке:

| Уровень | Назначение |
|---------|-----------|
| `debug` | трейс значений переменных, почти повсеместно |
| `info` | развилки и переходы между блоками логики (что именно происходит) |
| `warning` | пойманное и «проглоченное» исключение с возвратом к нормальному выполнению; существенное предположение; отказ от обработки ошибок/проверки входных данных |
| `exception` | логирование исключений |

---

## 2. Граф вызовов из `main()` (область покрытия)

В покрытие включены **только** функции модуля `adhoc` (вызовы в `libfa2.*`
и `sdk.*` логированию не подвергались — они вне области задачи).

```
main()                                          run_template_lite_transforms.py
├─ get_from_template_lite_json()                deserializer.py
│  └─ TemplateLite.from_dict()                  template.py
│     ├─ TemplateLiteNode.from_dict()           node.py
│     └─ TemplateLite.add_node()                template.py
├─ transform_template_lite_to_hierarchy()       transform.py
│  ├─ _nearest_metric_ancestor()  (вложенная)   transform.py
│  ├─ _build_analyt_metadata()                  transform.py
│  │  └─ _unique_dimension_code()               transform.py
│  └─ Hierarchy.add_node()                      libfa2 (вне области)
└─ transform_next_step()                        transform_queries.py
   └─ process_node()  (вложенная)               transform_queries.py
      ├─ calculate_and_set_query_prop()         transform_queries.py
      │  ├─ find_parts_by_name()                grp_map.py
      │  ├─ split_custom_name()                 grp_map.py
      │  ├─ find_node_address_by_fin_code()     pl_map_setup.py
      │  └─ find_node_address_by_name()         pl_map_setup.py
      └─ Hierarchy.get_children()               libfa2 (вне области)
```

---

## 3. Изменённые файлы

| Файл | Изменённые функции |
|------|-------------------|
| [src/adhoc/run_template_lite_transforms.py](../../src/adhoc/run_template_lite_transforms.py) | `main` |
| [src/adhoc/template_lite/deserializer.py](../../src/adhoc/template_lite/deserializer.py) | `get_from_template_lite_json` |
| [src/adhoc/template_lite/template.py](../../src/adhoc/template_lite/template.py) | `TemplateLite.from_dict`, `TemplateLite.add_node` |
| [src/adhoc/template_lite/node.py](../../src/adhoc/template_lite/node.py) | `TemplateLiteNode.from_dict` |
| [src/adhoc/template_lite/transform.py](../../src/adhoc/template_lite/transform.py) | `transform_template_lite_to_hierarchy`, `_nearest_metric_ancestor`, `_build_analyt_metadata`, `_unique_dimension_code` |
| [src/adhoc/template_lite/transform_queries.py](../../src/adhoc/template_lite/transform_queries.py) | `transform_next_step`, `process_node`, `calculate_and_set_query_prop` (доработано) |
| [src/adhoc/template_lite/grp_map.py](../../src/adhoc/template_lite/grp_map.py) | `split_custom_name`, `find_parts_by_name` |
| [src/adhoc/template_lite/pl_map_setup.py](../../src/adhoc/template_lite/pl_map_setup.py) | `find_node_address_by_name`, `find_node_address_by_fin_code` |

Логика ни одной функции не изменена — добавлены **только** вызовы логирования
(и импорт `from sdk.core.logging import get_logger` в файлах, где его ещё не было).

---

## 4. Детализация по модулям

### 4.1. `run_template_lite_transforms.py` — `main`

- `info` — запуск с путём к файлу-источнику; завершение каждого из трёх шагов
  (с ключевыми размерностями: `metric_name`, число узлов); итоговое завершение.
- `debug` — начало каждого шага.
- Оркестрация обёрнута в `try/except`: при любом исключении логируется через
  `lgr.exception(...)` (с трейсбэком) и исключение пробрасывается дальше (`raise`)
  — поведение (код возврата) не меняется, добавляется лишь структурированный лог.

### 4.2. `deserializer.py` — `get_from_template_lite_json`

- `debug` — тип источника.
- `info` — выбранная ветвь разбора: `dict` напрямую / JSON-строка / путь к файлу
  (развилка, определяющая дальнейший поток).
- `warning` — если по пути файл не существует (`path.is_file()` ложно) —
  предупреждение до попытки открытия, т.к. дальше последует `FileNotFoundError`.

### 4.3. `template.py` — `from_dict`, `add_node`

- `from_dict`: `debug` старт/финал сборки; `info` — имя показателя и число узлов в
  JSON, итоговое число добавленных узлов (переход между блоками разбора).
- `add_node`: `debug` — добавляемый узел; `error` + `raise ValueError` при дубле `id`
  (это именно ошибка состояния, а не «мягкая» деградация — поэтому `error`,
  затем корректный проброс исключения).
- `except ValueError` в `from_dict` при ошибке десериализации узла логируется через
  `lgr.exception(...)` перед перевызовом с расширенным сообщением.

### 4.4. `node.py` — `from_dict`

- `debug` — входной dict и итоговый созданный узел.

### 4.5. `transform.py` — ядро преобразования

- `transform_template_lite_to_hierarchy`: `info` — старт (имя, число узлов,
  `mp_decomp_tp`), статистика по метрикам/разрезам, старт сборки, итоговая сводка.
  `debug` — определённый `metric_type` для каждого узла.
- `_nearest_metric_ancestor` (вложенная): `debug` трейс поиска; `warning` —
  аномалии структуры (узел/предок не найдены) — это «существенное предположение»
  о целостности входных данных, после которого функция возвращает `None` и работа
  продолжается.
- `_build_analyt_metadata`: `debug` старт/финал; `debug` (не `warning`) — пустой
  список разрезов (это нормальная ситуация, не деградация).
- `_unique_dimension_code`: `warning` — коллизия кода измерения и переход на суффикс
  (`_2`, `_3`, …) — это **существенное предположение** об уникальности, которое
  могло бы замаскировать дубликат разреза.

### 4.6. `transform_queries.py` — расчёт `query`

- `transform_next_step`: `info` старт (корень) и завершение.
- `process_node` (вложенная): `debug` — обход узла; какие узлы идут в расчёт
  (`MULTI` / листовой).
- `calculate_and_set_query_prop` (уже содержал `get_logger()` — **доработан**):
  - `info` — главная развилка: прямое имя vs. имя с `(***)` (поиск по grp-карте).
  - `debug` — разбор каждой части, результат разности списков.
  - `warning` — точки деградации, где выставляется `query = {'BAD_FIELD': ''}`
    (составные части не найдены / адрес по `fin_code` или имени не найден /
    элемент `exclude` отсутствует в `include`). Именно здесь отказ от обработки
    и «мягкое» продолжение.
  - **Исправлено:** исходный `print(f'ERROR: elem {x} not in include_lst')` заменён
    на `lgr.warning(...)` — ранее это было «немое» сообщение на stdout, не
    попадавшее в лог-инфраструктуру.

### 4.7. `grp_map.py`, `pl_map_setup.py` — lookup-помощники

- `debug` — вход в поиск и его результат (найдено/не найдено, число элементов).
- В «ненайденных» ветках использован именно `debug`, **а не `warning`**: промах
  lookup-функции — её нормальное возвращаемое значение (`None`), а решение о
  деградации (`BAD_FIELD`) принимает вызывающий `calculate_and_set_query_prop` —
  там и стоит `warning`. Это удерживает WARNING-поток сфокусированным на реальных
  точках отказа (см. п. 6.2).

---

## 5. Корректность `get_logger()`

`sdk.core.logging.get_logger()` берёт квалифицированное имя **вызывающей** функции.
Поэтому:

1. `lgr = get_logger()` — первая исполняемая строка каждой функции (после docstring).
2. Для вложенных функций (`_nearest_metric_ancestor`, `process_node`) имя логгера
   корректно отражает вложенность, напр. `transform_next_step.<locals>.process_node`
   (подтверждено прогоном — см. §7).

---

## 6. Замечания и наблюдения

### 6.1. ⚠️ Подозрительный баг в `pl_map_setup.py` (НЕ исправлялся — вне рамок задачи)

В функциях `find_node_address_by_name` и `find_node_address_by_fin_code` оператор
`return None` расположен **внутри** цикла `for` (на уровне тела цикла), а не после
него:

```python
def find_node_address_by_name(name: str) -> List | None:
    for (...) in PL_MAP_SRC:
        if name == pl_name:
            ...
            return lst
        return None   # <-- прерывает поиск после ПЕРВОЙ же записи!
```

Из-за этого поиск завершается после первой записи `PL_MAP_SRC`, и для подавляющего
большинства входов функции возвращают `None` (→ `query = BAD_FIELD`). Поведение
**сохранено намеренно**: задача 28 — про логирование, а не про правку логики.
Правда, теперь благодаря `warning` в `calculate_and_set_query_prop` этот массовый
выход в `BAD_FIELD` стал **виден в логах** (раньше он был полностью silent).
Правильный отступ `return None` — кандидат на отдельную задачу. Места помечены
комментарием `# NOTE: ... (см. отчёт по задаче 28)`.

### 6.2. Уровни логирования для lookup-промахов

Изначально «не найдено в pl-карте» логировалось как `warning` внутри lookup-функций.
После анализа понижено до `debug`: промах — нормальный результат функции, а
единственная точка реального отказа (`BAD_FIELD`) — в `calculate_and_set_query_prop`,
там `warning` и оставлен. Иначе WARN-поток захлёбывался бы сообщениями из
вспомогательных поисков (особенно на фоне бага 6.1).

### 6.3. Зависимость от `sdk` стала нагрузкой для всего пакета

Раньше `sdk` импортировал только `transform_queries.py`; `node.py`/`template.py`/
`deserializer.py`/`transform.py` его не требовали, поэтому юнит-тесты запускались
без `aimis-sdk` в `PYTHONPATH`. После добавления `get_logger()` весь пакет
`adhoc.template_lite` теперь зависит от `sdk`. Это **соответствует реальному
рантайму**: скрипт-раннер `run_template_lite_transforms.py` и так импортирует
`sdk.tools.settings.FileTools` и `sdk.core.logging`. Следствие — команда запуска
тестов должна включать путь к `aimis-sdk` (см. §7).

---

## 7. Проверка

### 7.1. Юнит-тесты

Полный набор `src/adhoc/template_lite/tests/` — **121 passed, 2 skipped**, 0 failed.
Логирование не сломало ни одного теста.

```bash
source /Users/baltakov-df/venv/foo/bin/activate && \
PYTHONPATH=src:/Users/baltakov-df/source/repos/aimis-sdk \
python -m pytest src/adhoc/template_lite/tests/ -q
```

> Примечание: к `PYTHONPATH` добавлен путь к `aimis-sdk` (см. §6.3). Базовая команда
> из `CLAUDE.md` (только `src`) для этих тестов теперь недостаточна.

### 7.2. End-to-end прогон `main()`

Скрипт отработал на реальном файле `od_bef_rez_tb.json` без ошибок. На уровне INFO
виден весь поток преобразования (сокращённо):

```
[INFO] main: Запуск преобразования template_lite. Файл-источник: .../od_bef_rez_tb.json
[INFO] get_from_template_lite_json: Источник распознан как путь к файлу: ...
[INFO] TemplateLite.from_dict: metricName='Операционный доход до резервов ТБ', узлов в JSON: 72
[INFO] main: Шаг 1/3 завершён: получен TemplateLite (узлов=72)
[INFO] transform_template_lite_to_hierarchy: Старт преобразования: узлов=72, mp_decomp_tp=...DIRECT_BASE
[INFO] transform_template_lite_to_hierarchy: Узлов-метрик: 69, узлов-разрезов (схлопываются): 3
[INFO] transform_template_lite_to_hierarchy: Преобразование завершено: MetricNode построено=69
[INFO] main: Шаг 2/3 завершён: построена Hierarchy (узлов=69)
[INFO] transform_next_step: Старт transform_next_step: корень id=1 name='Операционный доход до резервов'
[INFO] calculate_and_set_query_prop: Прямое имя: ищем адрес по pl-карте ('...')
[WARNING] calculate_and_set_query_prop: Адрес узла по имени '...' не найден в pl-карте — query=BAD_FIELD
...
[INFO] transform_next_step: transform_next_step завершён
[INFO] main: Преобразование template_lite успешно завершено
```

Результат: `nodes=69` (72 узла сценария − 3 разреза = 69 `MetricNode`) — совпадает
с эталоном задачи 27. `get_logger()` корректно разрешает имя вложенной функции
(`transform_next_step.<locals>.process_node`).

### 7.3. Команда для просмотра логов в консоли

`sdk.core.logging` по умолчанию настраивает асинхронные файловые/консольные
хендлеры только через `get_logger_elk()`/`setup_async_logging()`. Для отладки в
консоли достаточно добавить собственный хендлер на корневой логгер:

```python
import logging
h = logging.StreamHandler()
h.setLevel(logging.DEBUG)
h.setFormatter(logging.Formatter('[%(levelname)s] %(name)s: %(message)s'))
logging.getLogger().addHandler(h)
logging.getLogger().setLevel(logging.DEBUG)
```

---

## 8. Итог

Логирование добавлено во все функции графа вызовов `main()` в пределах модуля
`adhoc` (8 файлов, 14 функций, включая 2 вложенные). Поведение кода не изменено —
внесены только лог-вызовы и импорт `get_logger`. Тесты зелёные (121/121), полный
рантайм-прогон `main()` успешен. Параллельно обнаружен и задокументирован (но не
тронут) подозрительный баг отступа в `pl_map_setup.py` — теперь он виден в логах.
