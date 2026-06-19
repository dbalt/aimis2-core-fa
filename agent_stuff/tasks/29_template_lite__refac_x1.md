# Задача 29: Рефакторинг формирования аналитической структуры (модуль `adhoc.template_lite`)

## 0. TL;DR

Нужно изменить способ, которым функция `transform_template_lite_to_hierarchy` строит
`AnalyticalStructureMetadata` для узлов-разрезов (`NodeRole.RAZREZ`).

- **Сейчас:** каждый разрез превращается в **отдельный `Algorithm`** (по алгоритму на разрез).
- **Должно стать:** все разрезы попадают в **один `Algorithm`**, образуя цепочку шагов в его `drill_order`.

---

## 1. Контекст

Ранее был разработан модуль `adhoc.template_lite` (`src/adhoc/template_lite`) на основе требований:

- @agent_stuff/tasks/26_template_light_base.md — базовые классы, десериализация JSON-сценария;
- @agent_stuff/tasks/27_transform_logic.md — функция `transform_template_lite_to_hierarchy`
  (преобразование `TemplateLite` → `Hierarchy`);
- @agent_stuff/tasks/28_improve_adhoc_transform_routines.md — добавление логирования.

В этой задаче дорабатывается именно функция `transform_template_lite_to_hierarchy`
(и её вспомогательные функции), которая находится в
[src/adhoc/template_lite/transform.py](src/adhoc/template_lite/transform.py).

---

## 2. Суть изменения

В исходном «lite»-сценарии узел с `role == NodeRole.RAZREZ` — это описание аналитического
разреза. По правилам из задачи 27 такой узел **не** становится отдельным `MetricNode`, а
«схлопывается»: для его ближайшего неразрезного предка (целевого `MetricNode`) строится
объект `AnalyticalStructureMetadata` с набором измерений (`Dimension`) и алгоритмов (`Algorithm`).

Проблема в том, **как именно** сейчас группируются несколько разрезов, относящихся к одному
`MetricNode`: каждый разрез сейчас даёт **свой собственный `Algorithm`**. Это неверно по
семантике предметной области: несколько разрезов одного показателя — это **одна
последовательность детализации** (один алгоритм), а не несколько независимых.

> См. общий принцип в @agent_stuff/docs/factor_analysis__general_description.md,
> раздел «Разложение по аналитическим разрезам» — «Порядок разложения» (один порядок = одна
> цепочка измерений = один `Algorithm`).

---

## 3. Текущее поведение (as-is)

Реализовано в функции [`_build_analyt_metadata`](src/adhoc/template_lite/transform.py)
(вызывается из основного цикла сборки `MetricNode`). Цикл создаёт **по одному `Algorithm`
на каждый разрез**, каждый — с одношаговым `drill_order`:

```python
metadata = AnalyticalStructureMetadata()
for index, name in enumerate(razrez_names, start=1):
    code = _unique_dimension_code(metadata, name)
    metadata.add_dimension(Dimension(code=code, name=name, column=name))
    metadata.add_algorithm(Algorithm(id=index, drill_order=[[code]]))   # ← отдельный алгоритм
```

**Пример.** Допустим, у `MetricNode` «Комиссионный доход» два разреза: «Сегмент» и
«Геоструктура». Сейчас получается **2 алгоритма**:

```python
# измерения
Dimension(code="Сегмент",      name="Сегмент",      column="Сегмент")
Dimension(code="Геоструктура", name="Геоструктура", column="Геоструктура")
# алгоритмы (ПО ОДНОМУ НА РАЗРЕЗ):
Algorithm(id=1, drill_order=[["Сегмент"]])
Algorithm(id=2, drill_order=[["Геоструктура"]])
# итого: 2 алгоритма, у каждого drill_order из одного шага
```

---

## 4. Требуемое поведение (to-be)

Все разрезы одного `MetricNode` должны попадать в **один-единственный `Algorithm`**, где они
образуют цепочку шагов в свойстве `drill_order`.

### Структура `drill_order` (важно!)

Тип `drill_order` — `list[list[str]]`:

- **внешний список** — последовательность шагов детализации (от общего к частному);
- **каждый шаг** — список кодов измерений, разворачиваемых одновременно на этом шаге.

«Два элемента в свойстве `drill_order`» означает **два элемента во внешнем списке** (два шага),
каждый из которых содержит код одного разреза.

### Тот же пример после доработки

```python
# измерения — без изменений
Dimension(code="Сегмент",      name="Сегмент",      column="Сегмент")
Dimension(code="Геоструктура", name="Геоструктура", column="Геоструктура")
# ОДИН алгоритм со ВСЕМИ разрезами в цепочке drill_order:
Algorithm(id=1, drill_order=[["Сегмент"], ["Геоструктура"]])
# итого: 1 алгоритм, drill_order из двух шагов
```

### Обобщение на N разрезов

| Кол-во разрезов у `MetricNode` | Измерений (`Dimension`) | Алгоритмов (`Algorithm`) | `drill_order` |
|---|---|---|---|
| 0 | 0 | — (`AnalyticalStructureMetadata` не строится, `None`) | — |
| 1 | 1 | 1 | `[[code]]` |
| 2 | 2 | 1 | `[[code1], [code2]]` |
| N | N | 1 | `[[code1], [code2], …, [codeN]]` |

Порядок шагов в `drill_order` должен соответствовать порядку разрезов в исходном сценарии
(т.е. порядку обхода узлов — он уже детерминирован по `id` узла в текущей группировке
`razrez_by_target`).

### Частные случаи, которые должны сохраниться

- **Разрезов нет** (`razrez_names` пустой/`None`) → возвращается `None`, метаданные не строятся
  (как сейчас).
- **Один разрез** → 1 алгоритм с одним шагом `[[code]]`.
- **Коллизия имён разрезов** → прежняя логика `_unique_dimension_code` (суффиксы `_2`, `_3`, …)
  сохраняется; уникальные `code` должны корректно попасть в `drill_order`.

---

## 5. Где и что менять

Основные правки — внутри [`_build_analyt_metadata`](src/adhoc/template_lite/transform.py):

1. По-прежнему добавить все `Dimension` (по одному на разрез, с прежней обработкой коллизий
   через `_unique_dimension_code`).
2. Вместо создания `Algorithm` внутри цикла — собрать список кодов (в порядке разрезов) и
   создать **один** `Algorithm(id=1, drill_order=[[code] for code in codes])`.

При необходимости — уточнить/обновить docstring `_build_analyt_metadata` и модуля
(`transform.py`), чтобы они описывали новое поведение. Также проверить комментарии в
`transform_template_lite_to_hierarchy` вокруг вызова `_build_analyt_metadata`.

### Тесты

Поправить/дополнить тесты в `src/adhoc/template_lite/tests/test_transform.py` так, чтобы они
фиксировали новое поведение (количество алгоритмов = 1 для нескольких разрезов; правильная
цепочка в `drill_order`; неизменность поведения для 0 и 1 разрезов).

---

## 6. Требования к логированию

Учесть рекомендации из @agent_stuff/tasks/28_improve_adhoc_transform_routines.md:

- логгер получать через `get_logger()` (из `sdk.core.logging`) **в начале каждого метода**;
- `lgr.debug(...)` — для трейса значений переменных (например, список разрезов, построенные
  коды, итоговый `drill_order`);
- `lgr.info(...)` — на ключевых развилках/переходах логики (например, сколько разрезов
  сгруппировано, строится один алгоритм);
- `lgr.warning(...)` — в местах существенных предположений/обходов ошибок (например, при
  коллизии кодов измерений — см. уже существующее предупреждение в `_unique_dimension_code`);
- `lgr.exception(...)` — для логирования исключений.

Существующие вызовы логирования в `transform.py` сохраняются и при необходимости адаптируются
под новое поведение.

---

## 7. Критерии приёмки

- [ ] Для `MetricNode` с N разрезами (N ≥ 2) строится **ровно один** `Algorithm`.
- [ ] `drill_order` этого алгоритма содержит **N шагов**, по одному коду измерения в каждом,
      в порядке разрезов исходного сценария.
- [ ] Все `Dimension` по-прежнему создаются (N штук) с прежней обработкой коллизий имён.
- [ ] Поведение для 0 и 1 разрезов не сломано (`None` и `[[code]]` соответственно).
- [ ] Добавлено/обновлено логирование согласно разделу 6.
- [ ] Тесты (`test_transform.py`) обновлены и проходят.

---

## 8. Отчёт

Подробный отчёт о проделанной работе сохранить в
@agent_stuff/reports/29_template_lite__refac_x1___report.md.

---

## 9. Связанные материалы

- @agent_stuff/tasks/26_template_light_base.md
- @agent_stuff/tasks/27_transform_logic.md
- @agent_stuff/tasks/28_improve_adhoc_transform_routines.md
- @agent_stuff/docs/factor_analysis__general_description.md (раздел «Разложение по аналитическим разрезам»)
- [src/adhoc/template_lite/transform.py](src/adhoc/template_lite/transform.py)
- Модель данных: [src/libfa2/analyt_struct_metadata/](src/libfa2/analyt_struct_metadata/)
  (`AnalyticalStructureMetadata`, `Algorithm`, `Dimension`)
