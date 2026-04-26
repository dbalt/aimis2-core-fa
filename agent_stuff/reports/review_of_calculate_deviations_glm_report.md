# Code Review: calculate_deviations и сопутствующие модули

**Файл:** `src/libfa2/fa_impl/service.py`
**Дата:** 2026-04-25

---

## Сводка

Проведен детальный code review функции `calculate_deviations` и всех её вспомогательных функций: `make_hier_drill`, `make_analyt_drill`, `make_next_drill`, `_query_data_from_data_access_layer`, `_get_query_select_conditions_for_hierarchy_node`.

Обнаружено **6 критических багов** (runtime crash), **3 логических ошибки** (неверный результат без краша), **3 риска деления на ноль** и ряд замечаний по качеству кода.

---

## 1. КРИТИЧЕСКИЕ БАГИ (Runtime Crash)

### 1.1. `aggr.py:103` — `NameError: cp` не в области видимости

```python
# DataAccess.get_aggr_data (aggr.py:103)
res.transform_data(lambda d: [DataRow.from_dict(x, cp.search_dev_params) for x in d])
```

Переменная `cp` не определена внутри метода `get_aggr_data`. Параметры метода — `source`, `grp_by_columns`, `aggr_columns`, `conditions`. Ни один из них не является `cp`.

**Следствие:** `NameError` при любом обращении к `DataAccess.get_aggr_data`, т.е. **весь пайплайн расчёта отклонений неработоспособен**.

**Исправление:** Убрать `transform_data` из `DataAccess` (он не должен знать о `SearchDevParameters`) и перенести трансформацию в вызывающий код.

---

### 1.2. `service.py:88` — `TypeError: DataRow.from_dict()` вызывается с одним аргументом вместо двух

```python
# _query_data_from_data_access_layer (service.py:88)
res.transform_data(lambda l: [DataRow.from_dict(x) for x in l])
```

`DataRow.from_dict` объявлен как `def from_dict(cls, row, params) -> DataRow` — требует два позиционных аргумента. Вызов с одним аргументом вызывает `TypeError`.

Даже если исправить на `DataRow.from_dict(x, cp.search_dev_params)` — данные уже были бы трансформированы в `DataRow` в `DataAccess.get_aggr_data` (если бы баг 1.1 был исправлен), что привело бы к передаче `DataRow` вместо `dict` в `from_dict`.

**Исправление:** После исправления 1.1 (убрать transform из DataAccess), заменить строку 88 на:
```python
res.transform_data(lambda l: [DataRow.from_dict(x, cp.search_dev_params) for x in l])
```

---

### 1.3. `sdk/core/monadic.py:71` — `AttributeError: can't set attribute` в `Res.transform_data`

```python
# Res.transform_data (monadic.py:70-72)
def transform_data(self, fn_transform):
    if self.ok:
        self.data = fn_transform(self.data)  # BUG
```

Свойство `data` объявлено через `@property` без `@data.setter`. Присваивание `self.data = ...` внутри метода вызовет `AttributeError: can't set attribute`.

Это означает, что **метод `transform_data` в `Res` никогда не может быть выполнен успешно**.

**Исправление:** Заменить `self.data = ...` на `self._data = ...`:
```python
def transform_data(self, fn_transform):
    if self.ok:
        self._data = fn_transform(self._data)
```

> **Примечание:** Этот баг находится в SDK (`aimis-sdk`), а не в текущем проекте. Но он блокирует всю работу `calculate_deviations`.

---

### 1.4. `service.py:120` — `NameError: chld` в `_get_data_for_node` для MULTI и RATIO веток

```python
# _get_data_for_node внутри make_hier_drill (service.py:115-121)
async def _get_data_for_node(node:MetricNode)->DataRow:
    val_res = await _query_data_from_data_access_layer(...)
    if not val_res.ok:
        raise Exception(...)
    val_row = val_res.data[0]
    val_row.dims['node'] = chld   # <-- BUG: 'chld' не определена в MULTI/RATIO ветках
    return val_row
```

Переменная `chld` — это переменная цикла `for chld in ...` из блока `SUM` (строка 129). Она **не определена** при входе в блоки `MULTI` (строка 166) или `RATIO` (строки 238-239), т.к. эти блоки выполняются через `if ... return` и `chld` никогда не получает значения.

**Следствие:** `NameError: name 'chld' is not defined` при обработке узлов типа `MULTI` или `RATIO`.

**Исправление:** Заменить `val_row.dims['node'] = chld` на `val_row.dims['node'] = node` (использовать параметр функции).

---

### 1.5. `service.py:163-164` — Некорректные предикаты для `search_first_in_lst_or` (MULTI)

```python
# make_hier_drill, блок MULTI (service.py:163-164)
node_ratio = search_first_in_lst_or(children, lambda x:x.componentMultiPartType.RATE)
node_base = search_first_in_lst_or(children, lambda x:x.componentMultiPartType.BASE)
```

`ComponentMultiPartType` — это `str, Enum`. Доступ к атрибуту `.RATE` на любом элементе enum возвращает элемент enum (truthy), а не `bool`. Таким образом:
- `ComponentMultiPartType.RATE.RATE` → `ComponentMultiPartType.RATE` (truthy)
- `ComponentMultiPartType.BASE.RATE` → `ComponentMultiPartType.RATE` (truthy)

Оба предиката **всегда truthy**, и `search_first_in_lst_or` всегда возвращает **первый элемент списка**. В итоге `node_ratio` и `node_base` будут указывать на **один и тот же узел**.

**Следствие:** Расчёт для MULTI узлов использует один и тот же узел вместо разных (rate и base). Результат будет полностью некорректным.

**Исправление:**
```python
node_ratio = search_first_in_lst_or(children, lambda x: x.componentMultiPartType == ComponentMultiPartType.RATE)
node_base = search_first_in_lst_or(children, lambda x: x.componentMultiPartType == ComponentMultiPartType.BASE)
```

---

### 1.6. `service.py:230,234` — Та же проблема с предикатами для RATIO

```python
node_numerator = search_first_in_lst_or(children, lambda x:x.componentRatioPartType == ComponentRatioPartType.NUMERATOR)
node_denominator = search_first_in_lst_or(children, lambda x: x.componentRatioPartType == ComponentRatioPartType.DENOMINATOR)
```

В блоке RATIO предикаты написаны корректно (с `==`), в отличие от блока MULTI. Но стоит отметить, что проверка на `None` результат отсутствует — если метаданные повреждены, `node_numerator` или `node_denominator` будут `None`, и дальнейший код крашнется с непонятной ошибкой при `_get_data_for_node(None)`.

---

## 2. ЛОГИЧЕСКИЕ ОШИБКИ

### 2.1. `service.py:182` — `plan` вместо `fact` для base в MULTI-блоке

```python
base_deviation_amounts = DeviationAmts.mk_with_custom_impact(
    base_data_row.plan,
    base_data_row.plan,    # <-- ОШИБКА: должен быть base_data_row.fact ?
    base_weighted_impact
)
```

Для `ratio_drill_component` (строка 181) используется `ratio_data_row.plan` и `ratio_data_row.fact`. А для `base_drill_component` используются `base_data_row.plan` и `base_data_row.plan` — оба значения `plan`.

**Следствие:** `DeviationAmts.deviation` для base компонента всегда будет 0 (plan - plan = 0). Это нарушает инвариант `deviation = fact - plan`.

**Вероятное исправление:** `base_data_row.plan, base_data_row.fact`.

---

### 2.2. `service.py:250-251` — Использование `abs()` в расчёте влияния для RATIO

```python
numerator_impact_direct_calc = abs(numerator_data_row.fact/denominator_data_row.plan) - abs(numerator_data_row.plan/denominator_data_row.plan)
denominator_impact_direct_calc = abs(numerator_data_row.plan/denominator_data_row.fact) - abs(numerator_data_row.plan/denominator_data_row.plan)
```

Метод цепных подстановок для ratio:
- Влияние числителя: `(num_fact/den_plan) - (num_plan/den_plan)`
- Влияние знаменателя: `(num_plan/den_fact) - (num_plan/den_plan)`

Использование `abs()` **теряет знак** отклонения. Если числитель отрицательный (расходы), `abs()` превратит его в положительный, и направление влияния будет определено неверно.

Кроме того, сам автор пометил этот блок комментарием: *"Тут сильно под вопросом как вообще это считается"*. Это подтверждает, что логика не проверена.

**Рекомендация:** Убрать `abs()` и использовать стандартный метод цепных подстановок без модуля.

---

### 2.3. `service.py:337-338` — Загрязнение `analyt_struct` ключом `'node'`

```python
# make_analyt_drill (service.py:337-338)
new_analyt_struct = current_drill_component.analyt_struct.copy()
new_analyt_struct.update(f.dims)
```

В `_get_data_for_node` (если исправить баг 1.4) устанавливается `val_row.dims['node'] = node`. Если `get_factors` возвращает эти строки с ключом `'node'` в `dims`, и они затем используются в контексте аналитического разложения, ключ `'node'` (ссылка на MetricNode) попадёт в `analyt_struct`, что не является аналитическим разрезом.

> Для `make_analyt_drill` данные приходят напрямую из `_query_data_from_data_access_layer`, а не через `_get_data_for_node`, поэтому в текущей реализации проблема возникает только в `make_hier_drill`.

---

## 3. РИСКИ ДЕЛЕНИЯ НА НОЛЬ

### 3.1. `service.py:178-179` — Сумма direct impacts = 0 в MULTI

```python
ratio_weighted_impact = (ratio_impact_direct_calc / (ratio_impact_direct_calc + base_impact_direct_calc)) * total_impact
```

Если `ratio_impact_direct_calc + base_impact_direct_calc == 0` (например, оба impacts равны по модулю и противоположны по знаку), произойдёт `ZeroDivisionError`.

**Когда это возможно:** Если ставка выросла ровно настолько, насколько упала база (влияния компенсируют друг друга).

### 3.2. `service.py:169-170` — Деление plan/fact базового узла

```python
plan = current_drill_component.amts.plan / base_data_row.plan,
fact = current_drill_component.amts.fact / base_data_row.fact
```

Если `base_data_row.plan == 0` или `base_data_row.fact == 0`, `ZeroDivisionError`. Нет проверки.

### 3.3. `service.py:253-254` — Сумма impacts = 0 в RATIO

```python
numerator_impact_weighted = numerator_impact_direct_calc * current_drill_component.amts.impact / (numerator_impact_direct_calc + denominator_impact_direct_calc)
```

Аналогично 3.1 — если сумма равна нулю.

---

## 4. ЗАМЕЧАНИЯ ПО КАЧЕСТВУ КОДА

### 4.1. Неиспользуемый импорт

```python
# service.py:4
from pygments.style import ansicolors  # Никогда не используется
```

### 4.2. `service.py:119` — Нет проверки на пустой результат

```python
val_row = val_res.data[0]  # IndexError если data пустой
```

Нет проверки `len(val_res.data) > 0`.

### 4.3. `service.py:437` — Аналогично в `calculate_deviations`

```python
top_lvl_data:DataRow = top_lvl_res.data[0]  # IndexError если data пустой
```

### 4.4. Использование `Exception` вместо специализированных типов

Все ошибки в модуле выбрасываются как `raise Exception(...)`. Рекомендуется ввести иерархию исключений (например, `FactorAnalysisError`, `DataRetrievalError`, `MetadataError`) для более гранулярной обработки.

### 4.5. `_get_data_for_node` — замыкание с побочным эффектом

Функция `_get_data_for_node` определена как вложенная функция и модифицирует данные (`val_row.dims['node'] = ...`). Это побочный эффект, который неочевиден при чтении кода. Лучше вынести установку `dims['node']` за пределы функции.

### 4.6. `units.py:72-73` — Использование `List` и `Dict` как default_factory

```python
analyt_slice: List[str] = field(default_factory=List)
components: List['DrillComponent'] = field(default_factory=List)
```

`List` и `Dict` из `typing` используются как фабрики. Хотя это работает (`List()` → `[]`, `Dict()` → `{}`), более идиоматичный Python способ — `field(default_factory=list)` / `field(default_factory=dict)`.

---

## 5. АРХИТЕКТУРНЫЕ ЗАМЕЧАНИЯ

### 5.1. Дублирование структуры в `make_hier_drill`

Блоки `SUM`, `MULTI` и `RATIO` в `make_hier_drill` содержат много повторяющегося кода по созданию `Drill` и `DrillComponent`. Общую логику можно вынести в helper-функции.

### 5.2. Разделение ответственности DataAccess

`DataAccess.get_aggr_data` в `aggr.py` выполняет и SQL-запрос, и трансформацию в `DataRow`. Трансформация требует знания о `SearchDevParameters`, что нарушает SRP. Рекомендуется разделить: `DataAccess` возвращает сырые `dict`, а вызывающий код выполняет трансформацию.

---

## 6. СВОДНАЯ ТАБЛИЦА

| # | Серьёзность | Файл | Строка | Описание |
|---|-------------|------|--------|----------|
| 1.1 | **CRITICAL** | aggr.py | 103 | `NameError: cp` не в scope |
| 1.2 | **CRITICAL** | service.py | 88 | `TypeError: from_dict()` — не хватает аргумента |
| 1.3 | **CRITICAL** | monadic.py | 71 | `AttributeError: can't set attribute` в `transform_data` |
| 1.4 | **CRITICAL** | service.py | 120 | `NameError: chld` в MULTI/RATIO ветках |
| 1.5 | **CRITICAL** | service.py | 163-164 | Предикаты для MULTI всегда truthy → node_ratio == node_base |
| 2.1 | **HIGH** | service.py | 182 | `plan` вместо `fact` для base |
| 2.2 | **HIGH** | service.py | 250-251 | `abs()` ломает знак в цепных подстановках RATIO |
| 3.1 | **MEDIUM** | service.py | 178 | Деление на ноль при компенсации impacts |
| 3.2 | **MEDIUM** | service.py | 169-170 | Деление на ноль при нулевом plan/fact базы |
| 3.3 | **MEDIUM** | service.py | 253-254 | Деление на ноль в RATIO при нулевой сумме impacts |
| 2.3 | **MEDIUM** | service.py | 337 | Загрязнение analyt_struct ключом 'node' |
| 4.1 | **LOW** | service.py | 4 | Неиспользуемый импорт `ansicolors` |
| 4.2 | **LOW** | service.py | 119, 437 | Нет проверки на пустой результат |
| 4.4 | **LOW** | service.py | везде | Грубый `Exception` вместо специализированных |
| 4.6 | **LOW** | units.py | 72-73 | `List`/`Dict` из typing как default_factory |

---

## 7. ПРИОРИТЕТ ИСПРАВЛЕНИЙ

**Первый приоритет (блокеры — код не может выполняться):**
1. Исправить `Res.transform_data` в SDK: `self._data = ...` вместо `self.data = ...`
2. Убрать `transform_data` из `DataAccess.get_aggr_data` (aggr.py:103)
3. Исправить трансформацию в `_query_data_from_data_access_layer` (service.py:88)
4. Исправить `val_row.dims['node'] = chld` → `val_row.dims['node'] = node` (service.py:120)

**Второй приоритет (логические ошибки — код работает, но результат неверный):**
5. Исправить предикаты для MULTI: `lambda x: x.componentMultiPartType == ComponentMultiPartType.RATE` (service.py:163-164)
6. Исправить `base_data_row.plan` → `base_data_row.fact` в base_deviation_amounts (service.py:182)
7. Убрать `abs()` из расчёта цепных подстановок для RATIO (service.py:250-251)

**Третий приоритет (защитное программирование):**
8. Добавить проверки деления на ноль
9. Добавить проверки на пустые результаты данных
10. Убрать неиспользуемый импорт
