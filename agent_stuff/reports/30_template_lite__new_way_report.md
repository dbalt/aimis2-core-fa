# Отчёт по задаче 30: Поле `codes` (node_code из `upr_cube_codes`) в `adhoc.template_lite`

## 0. TL;DR

В «lite»-сценариях появилось новое поле `upr_cube_codes` — список объектов с
тремя ключами `type_code`, `fin_code`, `node_code`. Реализована поддержка этого
поля:

1. В `TemplateLiteNode` добавлено поле **`codes: List[str]`** (значения
   `node_code`).
2. Десериализация (`get_from_template_lite_json` → `TemplateLite.from_dict` →
   `TemplateLiteNode.from_dict`) заполняет `codes` из `upr_cube_codes`.
3. `transform_template_lite_to_hierarchy` для узлов с непустым `codes` строит
   `query` вида **`Query({'node_code': <codes>})`** (вместо прежнего
   `{'pl_code': <name>}`).

---

## 1. Контекст

Модуль `adhoc.template_lite` построен в задачах 26–29:

- @agent_stuff/tasks/26_template_light_base.md — классы + десериализация JSON;
- @agent_stuff/tasks/27_transform_logic.md — `transform_template_lite_to_hierarchy`;
- @agent_stuff/tasks/28_improve_adhoc_transform_routines.md — логирование;
- @agent_stuff/tasks/29_template_lite__refac_x1.md — один `Algorithm` на все разрезы.

Новое требование (@agent_stuff/tasks/30_temlate_lite__new_way.md): у элементов
базового JSON появилось поле `upr_cube_codes` — список «привязок» узла сценария
к узлам управляющего куба. Из каждого такого элемента нужен `node_code`, чтобы
использовать его как точный ключ запроса к данным в `MetricNode.query`.

Пример элемента JSON (файл `od_tbgosb/…/2 ветка ОД (от блока).json`):

```json
{
  "id": 5,
  "name": "Кредиты банкам",
  "role": "podstatya",
  "parent": 4,
  "upr_cube_codes": [
    { "type_code": "PL", "fin_code": "A.01.02", "node_code": "R_01_02" }
  ]
}
```

> Поля `type_code` и `fin_code` в рамках данной задачи **не используются** —
> `codes` хранит только `node_code` (тип `List[str]`, как и требует задача).

---

## 2. Что менялось

### [src/adhoc/template_lite/node.py](src/adhoc/template_lite/node.py)

1. **Новое поле dataclass:**

   ```python
   codes: List[str] = field(default_factory=list)
   ```

   Идёт после `parent` (имеет значение по умолчанию), поэтому совместимо со
   всеми существующими конструкторами `TemplateLiteNode(id, name, role[, parent])`
   — `codes` по умолчанию пуст.

2. **Модульные константы** (рядом с импортами):

   ```python
   UPR_CUBE_CODES_KEY = "upr_cube_codes"
   NODE_CODE_KEY = "node_code"
   ```

   `NODE_CODE_KEY` реэкспортируется и используется в `transform.py`.

3. **`from_dict`** — разбор `upr_cube_codes → codes`:
   - поле опционально (отсутствует → `codes = []`);
   - из каждого элемента-объекта берётся только `node_code`;
   - элементы без `node_code` пропускаются с `lgr.warning` (разбор не рвётся);
   - если `upr_cube_codes` есть, но не список — `ValueError`;
   - в логе отладки — сколько `node_code` извлечено.

4. **`to_dict`** — `upr_cube_codes` включается **только при непустом `codes`** и
   реконструируется из него:

   ```python
   if self.codes:
       result[UPR_CUBE_CODES_KEY] = [{NODE_CODE_KEY: code} for code in self.codes]
   ```

   См. обоснование в разделе «Решения по дизайну».

5. Обновлены docstring: `Attributes` (описание `codes`), `from_dict`
   (упоминание `upr_cube_codes`), `to_dict` (поведение сериализации).

### Десериализация: где живёт логика

Цепочка вызовов:

```
get_from_template_lite_json(source)   # deserializer.py
  → TemplateLite.from_dict(data)      # template.py
      → TemplateLiteNode.from_dict(raw_node)   # node.py  ← разбор upr_cube_codes
```

Логика заполнения `codes` размещена в `TemplateLiteNode.from_dict` (где и так
разбираются все поля узла). Тем самым требование «модифицировать
`get_from_template_lite_json`» выполняется автоматически — после вызова
десериализатора узлы уже несут заполненный `codes`. Отдельный пост-проход по
дереву в `get_from_template_lite_json` не потребовался (это был бы обход
архитектуры).

### [src/adhoc/template_lite/transform.py](src/adhoc/template_lite/transform.py)

1. **Импорт константы:** `from .node import NODE_CODE_KEY`.

2. **Логика `query`** в цикле сборки `MetricNode` — добавлена приоритетная
   ветка для `codes`:

   ```python
   if node.codes:
       query: Optional[Query] = Query({NODE_CODE_KEY: node.codes})
   elif metric_type == MetricType.MULTI or metric_type is None:
       query = Query({PL_CODE_KEY: node.name})   # прежнее поведение
   else:
       query = None
   ```

   То есть: **есть `codes` → `{'node_code': codes}`**, иначе — прежнее
   `{'pl_code': name}` для листьев и `MULTI`. SUM-узлы без собственных данных
   по-прежнему не получают `query`.

3. Обновлён модульный docstring (правило 3) и добавлен `lgr.debug` о построении
   `query` по `codes`.

> Конвенция `Query({'node_code': <list>})` уже используется в модуле
> [transform_queries.py](src/adhoc/template_lite/transform_queries.py)
> (строки 67, 79) — новый код с ней полностью согласован.

---

## 3. Решения по дизайну

### 3.1. `query` по `codes` замещает `pl_code`, а не дополняет

Задача явно описывает значение: `Query({'node_code': <codes>})`. Поэтому при
непустом `codes` `query` содержит **только** `node_code`; `pl_code` (имя) в этом
случае не добавляется. `node_code` — точный идентификатор узла куба, тогда как
`pl_code` был лишь приближением; смешивать их не нужно.

### 3.2. Применимость правила «codes → query»

Реализовано как «любой узел с непустым `codes` получает `node_code`-query»,
а не только листья/MULTI. Это буквально соответствует формулировке задачи
(«при преобразовании тех элементов, у которых непустой `codes`»). На реальных
данных `codes` встречаются только у листьев (`podstatya`) и баз (`baza`),
поэтому на практике поведение совпадает с «листья + MULTI». Преимущество:
симметрично и не теряет данные, если позже `codes` появятся у промежуточных
узлов; `MetricNode.validate` разрешает `query` у SUM-узлов.

### 3.3. `to_dict` реконструирует `upr_cube_codes` из `codes`

Поскольку `codes` хранит только `node_code` (тип задан задачей как `List[str]`),
значения `type_code`/`fin_code` намеренно не сохраняются. Чтобы `to_dict` ↔
`from_dict` оставались согласованными (round-trip не терял `codes`), `to_dict`
при непустом `codes` эмитит:

```json
"upr_cube_codes": [{"node_code": "R_01_02"}, {"node_code": "R_01_99"}]
```

Это точное отражение того, что реально хранится в памяти. Для узлов без `codes`
ключ `upr_cube_codes` в `to_dict` отсутствует — поэтому существующие
round-trip-тесты на верхних файлах (`chkd.json`, `od_bef_rez_tb.json`,
`opextb.json`, где поля нет) проходят без изменений.

> Примечание: round-trip **сырого** JSON с полными объектами `upr_cube_codes`
> (трёх ключей) теряет `type_code`/`fin_code` — это следствие выбора `List[str]`
> в задаче. Если эти поля потребуются позже, тип `codes` нужно будет расширить
> (например, до списка датаклассов).

---

## 4. Тесты

Запуск: `source /Users/baltakov-df/venv/foo/bin/activate && PYTHONPATH=src:/Users/baltakov-df/source/repos/aimis-sdk python -m pytest src/adhoc/template_lite/tests/ -q`
**Результат: 144 passed, 2 skipped** (2 skip-а —pre-existing: `test_operacionnyj_dohod_specifics`,
`test_chkd_specifics` пропускаются из-за транслитерированных имён файлов, не
связаны с задачей 30).

### [src/adhoc/template_lite/tests/test_node.py](src/adhoc/template_lite/tests/test_node.py)

Новый класс `TestNodeCodes` (12 тестов): значение по умолчанию, явное задание,
извлечение `node_code` из `upr_cube_codes`, отсутствие поля, пустой список,
одиночный элемент, пропуск элементов без `node_code`, `ValueError` на не-списке,
поведение `to_dict` (с/без `upr_cube_codes`), round-trip `codes`.

### [src/adhoc/template_lite/tests/test_transform.py](src/adhoc/template_lite/tests/test_transform.py)

7 новых тестов: лист с `codes` → `{'node_code': codes}`; приоритет `node_code`
над `pl_code`; одиночный код; база с `codes`; MULTI с `codes`; лист без `codes`
→ прежний `pl_code`; смешанное дерево (часть с `codes`, часть без).

### [src/adhoc/template_lite/tests/test_real_files.py](src/adhoc/template_lite/tests/test_real_files.py)

3 end-to-end теста на реальных файлах `od_tbgosb/**` (содержат `upr_cube_codes`):

- `test_upr_cube_codes_parsed_into_codes` — `codes` заполняются и это списки строк;
- `test_upr_cube_codes_flow_into_node_code_query` — после трансформации каждый узел
  с `codes` получает `query == {'node_code': codes}`, иерархия валидна;
- `test_specific_od_tbgosb_file_codes` — «Кредиты банкам» → `["R_01_02"]`.

Все три выполняются (не пропускаются) и проходят.

---

## 5. Критерии приёмки

- [x] Поле `codes: List[str]` добавлено в `TemplateLiteNode`.
- [x] `get_from_template_lite_json` (через `TemplateLiteNode.from_dict`)
      заполняет `codes` значениями `node_code` из `upr_cube_codes`.
- [x] `transform_template_lite_to_hierarchy` для узлов с непустым `codes`
      заполняет `MetricNode.query = Query({'node_code': <codes>})`.
- [x] Логирование (задача 28) учтено: `debug`/`warning` в местах разбора и
      построения `query`.
- [x] Тесты добавлены и проходят (144 passed, 2 pre-existing skipped).
- [x] Существующие тесты не сломаны (поведение без `codes` не изменилось).

---

## 6. Smoke-проверка

```
codes n2 = ['R_01_02', 'R_01_99']                 # извлечение node_code
codes n3 = []                                       # нет upr_cube_codes → пусто
to_dict n2 = {..., 'upr_cube_codes': [{'node_code': 'R_01_02'}, {'node_code': 'R_01_99'}]}
query n2 = {'node_code': ['R_01_02', 'R_01_99']}   # codes → node_code query
query n3 = {'pl_code': 'Без кодов'}                 # без codes → прежний pl_code
valid: True []
```

---

## 7. Связанные материалы

- @agent_stuff/tasks/30_temlate_lite__new_way.md
- @agent_stuff/tasks/26_template_light_base.md
- @agent_stuff/tasks/27_transform_logic.md
- [src/adhoc/template_lite/node.py](src/adhoc/template_lite/node.py)
- [src/adhoc/template_lite/transform.py](src/adhoc/template_lite/transform.py)
- [src/adhoc/template_lite/deserializer.py](src/adhoc/template_lite/deserializer.py)
- Реальные данные: [src/tmp/template_lite/od_tbgosb/](src/tmp/template_lite/od_tbgosb/)
