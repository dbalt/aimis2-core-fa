# Отчёт по задаче 27: Трансформация `TemplateLite` → `Hierarchy`

**Дата:** 2026-06-15
**Задача:** [27_transform_logic.md](../tasks/27_transform_logic.md)
**Статус:** ✅ Выполнено

---

## 1. Суть задачи

Реализовать функцию `transform_template_lite_to_hierarchy` в модуле
[`adhoc.template_lite`](../../src/adhoc/template_lite/), которая разворачивает
«lite»-сценарий обхода данных (`TemplateLite`, результат задачи 26) в полноценную
иерархию показателей (`Hierarchy` из [`libfa2.hier_metadata`](../../src/libfa2/hier_metadata/))
с метаданными аналитических разрезов (`AnalyticalStructureMetadata` из
[`libfa2.analyt_struct_metadata`](../../src/libfa2/analyt_struct_metadata/)).

Функция реализует три правила отображения ролей узла (`NodeRole`) на поля
`MetricNode`, заданные в постановке задачи.

---

## 2. Файлы

| Файл | Назначение |
|------|-----------|
| [src/adhoc/template_lite/transform.py](../../src/adhoc/template_lite/transform.py) | Реализация `transform_template_lite_to_hierarchy` и вспомогательных функций |
| [src/adhoc/template_lite/tests/test_transform.py](../../src/adhoc/template_lite/tests/test_transform.py) | 25 юнит/интеграционных тестов |
| [src/adhoc/template_lite/__init__.py](../../src/adhoc/template_lite/__init__.py) | Публичный экспорт функции |
| [src/adhoc/run_template_lite_transforms.py](../../src/adhoc/run_template_lite_transforms.py) | Скрипт-раннер для ручного запуска |

Функция доступна как `from adhoc.template_lite import transform_template_lite_to_hierarchy`.

---

## 3. Правила отображения и их реализация

### Правило 1. `RAZREZ` → `AnalyticalStructureMetadata` на родителе

> Узел с `role == NodeRole.RAZREZ` — это описание аналитического разреза. Он **не**
> становится отдельным `MetricNode`: в его родительский `MetricNode` добавляется
> `AnalyticalStructureMetadata` с **одним алгоритмом и одним измерением**; все
> наименования берутся из поля `name`.

**Реализация:**

1. Разрез **исключается** из множества узлов, становящихся `MetricNode`
   (`metric_ids` = все узлы, у которых `role != NodeRole.RAZREZ`).
2. Разрез привязывается к **ближайшему неразрезному предку**
   (`_nearest_metric_ancestor`) — это целевой `MetricNode`, куда попадут его
   `analyt_metadata`.
3. Все разрезы, относящиеся к одному `MetricNode`, группируются
   (`razrez_by_target`), и для узла строится единый `AnalyticalStructureMetadata`,
   где **каждый разрез даёт ровно одно измерение (`Dimension`) и один алгоритм
   (`Algorithm`)** с `drill_order=[[<code>]]`.
4. `code`, `name`, `column` измерения берутся из `name` разреза (по постановке
   «все наименования берутся из `name` поля»).

**Подъём поддерева (lifting).** В исходных сценариях разрез нередко имеет
собственное поддерево статей (например, под разрезом «Продукт ЕК» лежит пара
тариф/база). Чтобы не оставить в итоговом дереве «висящие» ссылки на удалённый
узел-разрез, поддерево разреза **подтягивается на уровень ближайшего неразрезного
предка**: эффективным родителем (`parent`) каждого неразрезного узла становится
его ближайший неразрезный предок, а не непосредственный родитель-разрез.

**Дедупликация кодов.** Если у одного `MetricNode` оказалось несколько разрезов с
одинаковым `name`, второму и последующим измерениям к `code`/`column` добавляется
числовой суффикс (`_2`, `_3`, …), т.к. `Dimension.code` должен быть уникален в
пределах контейнера (см. `AnalyticalStructureMetadata.add_dimension`).

### Правило 2. Роли потомков → `type` родителя; `componentMultiPartType`

> `role == NodeRole.PODSTATYA` у потомка → `type=MetricType.SUM` у родителя.
> `role` в `{TARIF, BAZA}` → `type=MetricType.MULTI` у родителя, а сам узел
> получает `componentMultiPartType` (`RATE` для тарифа, `BASE` для базы).

**Реализация:**

- Тип родителя выводится по **ролям эффективных (неразрезных) потомков**
  (`eff_children_roles`):
  - есть `TARIF`/`BAZA` → `MULTI` (приоритетнее, т.к. мультипликативная статья
    не может одновременно быть суммируемой);
  - иначе есть `PODSTATYA` → `SUM`;
  - иначе (потомков нет) → `None` (листовой элемент).
- `componentMultiPartType` выставляется **самому** узлу-тарифу/базе:
  - `NodeRole.TARIF` → `ComponentMultiPartType.RATE`;
  - `NodeRole.BAZA` → `ComponentMultiPartType.BASE`.

### Правило 3. `query` для листьев и `MULTI`

> Листовые `MetricNode` (кроме ratio-частей) и `MULTI`-узлы получают `query`
> вида `{'pl_code': <name>}`.

**Реализация:**

```python
if metric_type == MetricType.MULTI or metric_type is None:
    query = Query({PL_CODE_KEY: node.name})   # PL_CODE_KEY == "pl_code"
else:
    query = None
```

- `type is None` (листья, в т.ч. тариф/база) → `query` заполняется;
- `type == MULTI` → `query` заполняется (требуется валидатором `MetricNode`:
  MULTI обязан иметь `query`);
- `SUM`/`RATIO` без собственных данных → `query = None`.

> **Примечание к формулировке правила.** В постановке исключение сформулировано
> как «кроме тех, у которых `componentMultiPartType === ratio`». Буквально
> `componentMultiPartType` принимает значения `rate`/`base`, а не `ratio`
> (`ratio` относится к `componentRatioPartType`: `numerator`/`denominator`).
> В «lite»-сценариях показатели типа ratio **отсутствуют** (нет роли для них), поэтому
> исключение неприменимо и ни одного листа не затрагивает — все листья получают
> `query`.

---

## 4. Дополнительные проектные решения

### 4.1. `mp_decomp_tp` для `MULTI` (обязателен в текущей модели)

В актуальной модели `MetricNode` ([metric_node.py:86-87](../../src/libfa2/hier_metadata/metric_node.py#L86-L87))
появилось поле `mp_decomp_tp: Optional[MultipartDecompositionType]`, причём
валидатор узла ([metric_node.py:372-374](../../src/libfa2/hier_metadata/metric_node.py#L372-L374))
**требует** его заполнения для `type=MULTI`. Поэтому функция принимает
keyword-параметр:

```python
def transform_template_lite_to_hierarchy(
    template_lite: TemplateLite,
    *,
    mp_decomp_tp: MultipartDecompositionType = DEFAULT_MULTI_DECOMP_TP,  # DIRECT_BASE
) -> Hierarchy:
```

По умолчанию используется `MultipartDecompositionType.DIRECT_BASE` (метод цепных
подстановок с прямым счётом влияния базы, см.
[algo__chain_substs_method.md](../docs/algo__chain_substs_method.md)). Значение
можно переопределить, передав `mp_decomp_tp=...`.

### 4.2. Поле `code`

`MetricNode.code` обязательно, но в «lite»-сценарии отдельного кода статьи нет
(есть только отображаемое `name`). Поэтому `code = node.name` — то же значение,
что и `name`. Это позволяет сохранить идентичность статьи и не вводить
искусственный код.

### 4.3. `parent` через эффективного предка

`parent` итогового `MetricNode` — это ближайший неразрезный предок в исходном
сценарии (см. lifting в п. 3.1), что гарантирует отсутствие ссылок на
«схлопнутые» узлы-разрезы и корректность `Hierarchy.validate()`.

### 4.4. Проверка типа аргумента

На входе проверяется `isinstance(template_lite, TemplateLite)`; при нарушении
выбрасывается `TypeError`.

---

## 5. Алгоритм сборки (последовательность шагов в `transform.py`)

1. `_nearest_metric_ancestor(node_id)` — для каждого узла ищет ближайшего
   неразрезного предка (используется и как целевой `MetricNode` для разрезов, и
   как эффективный `parent` для неразрезных узлов).
2. `metric_ids` — список id узлов, становящихся `MetricNode` (все, кроме разрезов).
3. `eff_children_roles[parent_id]` — роли неразрезных потомков по их целевому
   родителю (для вывода `type`).
4. `razrez_by_target[parent_id]` — сгруппированные по целевому узлу имена разрезов.
5. Для каждого узла из `metric_ids` собирается `MetricNode` с рассчитанными
   `type`, `componentMultiPartType`, `query`, `analyt_metadata`, `mp_decomp_tp`,
   `parent` и добавляется в `Hierarchy`.

Все шаги линейны по числу узлов (O(N) на навигацию по предкам в худшем случае).

---

## 6. Наглядный пример

**Сценарий** (корень → разрез → подстатья → тариф/база; плюс лист-подстатья):

```
ЧКД+ ТБ (podstatya, корень)
└── ТБ/ГОСБ (razrez)
    └── Процентный доход (podstatya)
        ├── Маржа (tarif)
        └── СДО (baza)
Прочие доходы (podstatya, под корнем)
```

**Результат трансформации** (`Hierarchy.visualize()`):

```
ЧКД+ ТБ (id: 1, type: sum)
├── Процентный доход (id: 3, type: multi)
│   ├── Маржа (id: 4, rate)
│   └── СДО (id: 5, base)
└── Прочие доходы (id: 6)            ← лист, type=None, есть query
```

Что произошло:
- разрез «ТБ/ГОСБ» **схлопнут** — узел id=2 не попал в иерархию;
- «Процентный доход» **поднят** под корень (id=1) и стал `MULTI` (пара тариф/база);
- корень получил `analyt_metadata` с измерением и алгоритмом «ТБ/ГОСБ».

**JSON корня** (поле `analyt_metadata`):

```json
{
  "id": 1, "code": "ЧКД+ ТБ", "name": "ЧКД+ ТБ", "type": "sum",
  "analyt_metadata": {
    "algorithms":   [{"id": 1, "drill_order": [["ТБ/ГОСБ"]]}],
    "dimensions":   [{"code": "ТБ/ГОСБ", "name": "ТБ/ГОСБ", "column": "ТБ/ГОСБ"}]
  }
}
```

---

## 7. Тесты

**Файл:** [src/adhoc/template_lite/tests/test_transform.py](../../src/adhoc/template_lite/tests/test_transform.py)
**Запуск:**

```bash
source /Users/baltakov-df/venv/foo/bin/activate && \
PYTHONPATH=src python -m pytest src/adhoc/template_lite/tests/test_transform.py -v
```

**Результат: 25 passed.**

Группы тестов:

| Группа | Что проверяет |
|--------|--------------|
| Тип результата | возвращает `Hierarchy`; не-`TemplateLite` → `TypeError` |
| Правило 1 (RAZREZ) | разрез не создаёт узел; 1 алгоритм + 1 измерение из `name`; подъём вложенного разреза; объединение нескольких разрезов; суффиксы при дубликате имён |
| Правило 2 (типы) | подстатья-потомок → `SUM`; пара тариф/база → `MULTI`; тариф → `RATE`, база → `BASE`; лист без типа; MULTI валиден (1 rate + 1 base) |
| Lifting | поддерево разреза подтягивается к неразрезному предку; подстатья с разрезом-единственным потомком становится `MULTI` |
| Правило 3 (query) | листья и MULTI получают `{'pl_code': <name>}`; тариф/база — тоже; `SUM` без данных — без `query` |
| `mp_decomp_tp` | значение по умолчанию `DIRECT_BASE`; переопределение параметром; отсутствие у не-MULTI |
| Валидность/сериализация | построенная иерархия проходит `is_valid()`; round-trip `to_json_string → from_json_string` сохраняет структуру и `analyt_metadata` |
| End-to-end | оба реальных файла → валидные иерархии; конкретные факты по «операционному доходу» |

Весь модуль `adhoc.template_lite` целиком: **122 passed, 1 skipped**.

---

## 8. Результаты на реальных файлах

Прогон на файлах из [src/tmp/template_lite/](../../src/tmp/template_lite/):

| Файл | metricName | Узлов сценария | razrez | Узлов иерархии | `is_valid` |
|------|-----------|----------------|--------|----------------|------------|
| `od_bef_rez_tb.json` | Операционный доход до резервов ТБ | 72 | 3 | 69 | ✅ |
| `чкд+_тб_business_lite.json` | ЧКД+ ТБ | 33 | 2 | 31 | ✅ |

**`od_bef_rez_tb.json`** (подробнее):
- распределение по типам: **SUM — 13, MULTI — 8, листовых — 48**;
- корень — `SUM` с двумя разрезами: «ТБ/ГОСБ», «Блок/Подблок(Сегмент КИБ)»;
- `analyt_metadata` есть у 2 узлов (корень + вложенная мультипликативная статья,
  чьи тариф/база лежали под разрезом «Продукт ЕК»);
- `query` заполнен у 56 узлов (все листья + все MULTI).

**`чкд+_тб_business_lite.json`** (подробнее):
- распределение по типам: **SUM — 7, листовых — 24** (мультипликативных статей нет);
- `query` заполнен у 24 узлов (все листья);
- оба разреза привязаны к корню → `analyt_metadata` у 1 узла (корня).

Количество узлов иерархии = количество узлов сценария − количество разрезов
(разрезы схлопываются, поддеревья подтягиваются без потери узлов).

---

## 9. Соответствие требованиям

| Требование задачи 27 | Статус | Реализация |
|----------------------|--------|-----------|
| `RAZREZ` → `AnalyticalStructureMetadata` на родителе (1 алгоритм + 1 измерение, имена из `name`) | ✅ | `_build_analyt_metadata` + группировка по `_nearest_metric_ancestor` |
| `role != RAZREZ` → `MetricNode` | ✅ | `metric_ids` |
| `PODSTATYA`-потомок → `type=SUM` у родителя | ✅ | вывод `type` по `eff_children_roles` |
| `TARIF`/`BAZA` → `type=MULTI` у родителя + `componentMultiPartType` у узла | ✅ | `RATE`/`BASE` |
| Листья (кроме ratio) + `MULTI` получают `query` `{'pl_code': <name>}` | ✅ | правило 3 |
| Имя функции `transform_template_lite_to_hierarchy` | ✅ | — |
| Модуль `adhoc.template_lite` | ✅ | `src/adhoc/template_lite/transform.py` |
| Подробный отчёт | ✅ | этот файл |

---

## 10. Принятые проектные решения (сводка)

1. **Разрез «схлопывается» в `analyt_metadata`** ближайшего неразрезного предка, а
   не становится узлом. Это единственный способ одновременно выполнить правило 1 и
   получить валидное дерево `Hierarchy` (без ссылок на несуществующий родитель).
2. **Подъём поддерева разреза (lifting)** к неразрезному предку — следствие п. 1.
3. **Один алгоритм + одно измерение на разрез.** Несколько разрезов одного узла
   дают несколько измерений и несколько алгоритмов (по постановке «в нём один
   алгоритм и одно измерение» — на каждый разрез).
4. **`mp_decomp_tp` обязателен для MULTI** (требование актуальной модели
   `MetricNode`), значение по умолчанию `DIRECT_BASE`, переопределяемо параметром.
5. **`code = name`** — в lite-сценарии отдельного кода нет.
6. **Суффиксы кодов** при совпадении имён разрезов — ради уникальности `Dimension.code`.
7. **Стиль кода** — docstrings на русском, type hints, соответствие существующим
   модулям `libfa2.*`.
