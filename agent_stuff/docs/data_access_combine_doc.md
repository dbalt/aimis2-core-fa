# Документация модуля `libfa2.data_access.conditions`

## Оглавление
1. [Обзор](#обзор)
2. [Типы данных](#типы-данных)
3. [Иерархия классов](#иерархия-классов)
4. [Классы и их методы](#классы-и-их-методы)
   - [ConditionBase](#conditionbase)
   - [ConditionSet](#conditionset)
   - [ConditionOr](#conditionor)
   - [ConditionAnd](#conditionand)
5. [Алгоритм редукции](#алгоритм-редукции)
   - [Общие принципы](#общие-принципы)
   - [Правила редукции ConditionAnd](#правила-редукции-conditionand)
   - [Правила редукции ConditionOr](#правила-редукции-conditionor)
   - [Рекурсивная и итеративная редукция](#рекурсивная-и-итеративная-редукция)
6. [Вспомогательные функции](#вспомогательные-функции)
7. [Примеры использования](#примеры-использования)

---

## Обзор

Модуль `libfa2.data_access.conditions` предоставляет иерархическую систему классов для представления SQL-условий фильтрации (`WHERE`-clause) с возможностью их комбинирования и оптимизации (редукции).

### Ключевые возможности:
- **Типизированное представление условий**: через `ConditionSet` для простых фильтров
- **Логические операторы**: `ConditionOr` (ИЛИ) и `ConditionAnd` (И) для комбинирования условий
- **Оптимизация структуры**: функция `reduce_condition` для упрощения сложных выражений
- **Вложенные конструкции**: поддержка рекурсивного комбинирования условий любой глубины

### Путь к модулю
```
src/libfa2/data_access/conditions.py
```

---

## Типы данных

### `FilterValue`

Тип для значений фильтрации, который может быть:
- Любое одиночное значение (`Any`)
- Список значений (`List[Any]`)

```python
FilterValue = Union[Any, List[Any]]
```

**Примеры:**
```python
"foo"                    # одиночное значение
1                       # одиночное значение
["foo", "bar", "baz"]   # список значений
```

---

## Иерархия классов

```
ConditionBase (абстрактный базовый класс)
    ├── ConditionSet
    ├── _ConditionContainer (базовый класс для контейнеров)
    │   ├── ConditionOr
    │   └── ConditionAnd
```

### Описание иерархии:
- **`ConditionBase`**: Абстрактный базовый класс, определяющий общий интерфейс для всех условий
- **`ConditionSet`**: Типизированный контейнер для простых фильтров (аналог `Dict[str, FilterValue]`)
- **`_ConditionContainer`**: Базовый класс для контейнеров (`ConditionOr` / `ConditionAnd`), хранит список условий
- **`ConditionOr`**: Контейнер для условий, объединённых оператором OR (логическое ИЛИ)
- **`ConditionAnd`**: Контейнер для условий, объединённых оператором AND (логическое И)

---

## Классы и их методы

### ConditionBase

Абстрактный базовый класс для всех типов условий.

#### Абстрактные методы

##### `to_dict() -> Dict[str, FilterValue]`
Сериализует условие в словарь.

##### `columns: List[str]` (property)
Возвращает список имён столбцов, используемых в условии.

##### `get_filter_for_column(column_name: str) -> FilterValue`
Возвращает значение(я) фильтрации для указанного столбца.

**Параметры:**
- `column_name`: Имя столбца

**Возвращает:**
- Значение или список значений для фильтрации

**Исключения:**
- `KeyError`: Если столбец не найден в условии

---

### ConditionSet

Типизированный контейнер для фильтрации по столбцам таблицы.

#### SQL-семантика
```python
ConditionSet({"name": ["foo", "bar"], "part_id": 1})
# Эквивалентно SQL:
# WHERE 1=1 AND name IN ('foo', 'bar') AND part_id = 1
```

#### Методы

##### `__init__(data: Dict[str, FilterValue] | None = None)`
Инициализирует `ConditionSet`.

**Параметры:**
- `data`: Словарь условий `{имя_столбца: значение/список_значений}` (опционально)

##### `columns: List[str]` (property)
Возвращает список имён столбцов в `ConditionSet`.

**Пример:**
```python
cs = ConditionSet({"name": "foo", "part_id": 1})
print(cs.columns)  # ["name", "part_id"]
```

##### `get_filter_for_column(column_name: str) -> FilterValue`
Возвращает значение(я) фильтрации для указанного столбца.

**Параметры:**
- `column_name`: Имя столбца

**Возвращает:**
- Значение или список значений для фильтрации

**Исключения:**
- `KeyError`: Если столбец не найден в `ConditionSet`

**Пример:**
```python
cs = ConditionSet({"name": ["foo", "bar"], "part_id": 1})
cs.get_filter_for_column("name")  # ["foo", "bar"]
cs.get_filter_for_column("part_id")  # 1
```

##### `set_filter(column_name: str, value: FilterValue) -> None`
Устанавливает фильтр для указанного столбца.

**Параметры:**
- `column_name`: Имя столбца
- `value`: Значение или список значений для фильтрации

**Пример:**
```python
cs = ConditionSet()
cs.set_filter("name", "foo")
cs.set_filter("part_id", [1, 2, 3])
```

##### `remove_filter(column_name: str) -> bool`
Удаляет фильтр для указанного столбца.

**Параметры:**
- `column_name`: Имя столбца

**Возвращает:**
- `True` если фильтр был удалён, `False` если столбец не найден

**Пример:**
```python
cs = ConditionSet({"name": "foo", "part_id": 1})
cs.remove_filter("name")  # True
cs.remove_filter("status")  # False
```

##### `has_column(column_name: str) -> bool`
Проверяет наличие столбца в `ConditionSet`.

**Параметры:**
- `column_name`: Имя столбца

**Возвращает:**
- `True` если столбец присутствует, иначе `False`

**Пример:**
```python
cs = ConditionSet({"name": "foo"})
cs.has_column("name")  # True
cs.has_column("status")  # False
```

##### `to_dict() -> Dict[str, FilterValue]`
Сериализует в словарь (возвращает копию данных).

**Пример:**
```python
cs = ConditionSet({"name": "foo", "part_id": 1})
data = cs.to_dict()  # {"name": "foo", "part_id": 1}
```

##### `from_dict(cls, data: Dict[str, FilterValue]) -> ConditionSet` (classmethod)
Фабричный метод создания из словаря.

**Параметры:**
- `data`: Словарь условий

**Возвращает:**
- Экземпляр `ConditionSet`

**Пример:**
```python
data = {"name": "foo", "part_id": 1}
cs = ConditionSet.from_dict(data)
```

##### `copy() -> ConditionSet`
Возвращает копию `ConditionSet`.

**Пример:**
```python
cs1 = ConditionSet({"name": "foo"})
cs2 = cs1.copy()
cs2.set_filter("name", "bar")
# cs1.get_filter_for_column("name") == "foo"
# cs2.get_filter_for_column("name") == "bar"
```

##### `__repr__() -> str`
Строковое представление для отладки.

**Пример:**
```python
cs = ConditionSet({"name": "foo"})
repr(cs)  # "ConditionSet({'name': 'foo'})"
```

##### `__eq__(other: object) -> bool`
Сравнение на равенство.

**Пример:**
```python
cs1 = ConditionSet({"name": "foo"})
cs2 = ConditionSet({"name": "foo"})
cs1 == cs2  # True
```

---

### ConditionOr

Контейнер для условий, объединённых оператором `OR` (логическое ИЛИ).

#### SQL-семантика
```python
ConditionOr([
    ConditionSet({"name": ["foo", "bar"], "part_id": 1}),
    ConditionSet({"name": "baz", "part_id": [1, 2, 3]})
])
# Эквивалентно SQL:
# WHERE 1=1 AND (
#     name IN ('foo', 'bar') AND part_id = 1
#     OR
#     name = 'baz' AND part_id IN (1, 2, 3)
# )
```

#### Методы (наследуются от `_ConditionContainer`)

##### `__init__(conditions: List[ConditionBase] | None = None)`
Инициализирует контейнер условий.

**Параметры:**
- `conditions`: Список условий `ConditionBase` (опционально)

##### `add(condition: ConditionBase) -> None`
Добавляет условие в контейнер.

**Параметры:**
- `condition`: Условие для добавления

##### `remove(index: int) -> ConditionBase`
Удаляет условие по индексу.

**Параметры:**
- `index`: Индекс условия

**Возвращает:**
- Удалённое условие

**Исключения:**
- `IndexError`: Если индекс вне диапазона

##### `get(index: int) -> ConditionBase`
Возвращает условие по индексу.

**Параметры:**
- `index`: Индекс условия

**Возвращает:**
- Условие `ConditionBase`

**Исключения:**
- `IndexError`: Если индекс вне диапазона

##### `conditions: List[ConditionBase]` (property)
Возвращает список условий (копию).

##### `count: int` (property)
Возвращает количество условий.

##### `columns: List[str]` (property)
Возвращает список всех уникальных столбцов из всех вложенных условий.

##### `get_filter_for_column(column_name: str) -> FilterValue`
Возвращает значение(я) фильтрации для указанного столбца из первого условия, содержащего этот столбец.

**Исключения:**
- `KeyError`: Если столбец не найден ни в одном условии

##### `copy() -> ConditionOr`
Возвращает копию контейнера.

---

### ConditionAnd

Контейнер для условий, объединённых оператором `AND` (логическое И).

#### SQL-семантика
```python
ConditionAnd([
    ConditionSet({"name": "foo"}),
    ConditionSet({"part_id": 1})
])
# Эквивалентно SQL:
# WHERE 1=1 AND (name = 'foo' AND part_id = 1)
```

#### Методы
Все методы идентичны `ConditionOr`, так как оба класса наследуются от `_ConditionContainer`.

---

## Алгоритм редукции

Функция `reduce_condition` оптимизирует (редуцирует) структуру условий, возвращая условие в максимально упрощённой форме.

### Общие принципы

1. **Редукция снизу вверх**: Сначала редуцируются вложенные контейнеры, затем внешние
2. **Итеративный подход**: При наличии более 2 элементов контейнер редуцируется парно
3. **Сохранение семантики**: Редукция не должна изменять логическое значение условия
4. **Обработка конфликтов**: При противоречивых условиях в `ConditionAnd` генерируется ошибка

### Правила редукции ConditionAnd

#### Базовое правило
```
ConditionAnd(ConditionSet1, ConditionSet2) → ConditionSet
```

**Логика:**
1. Все столбцы из `ConditionSet2` добавляются в `ConditionSet1`
2. При пересечении имён столбцов — берётся **пересечение** значений фильтров
3. Если общих значений нет → `ValueError`

#### Пример успешной редукции

**Вход:**
```python
ConditionAnd([
    ConditionSet({"name": ["foo", "bar", "baz"], "part_id": 1}),
    ConditionSet({"name": ["bar", "baz"], "status": "active"})
])
```

**Процесс:**
- `name`: пересечение `["foo", "bar", "baz"]` ∩ `["bar", "baz"]` → `["bar", "baz"]`
- `part_id`: берём из первого → `1`
- `status`: берём из второго → `"active"`

**Результат:**
```python
ConditionSet({
    "name": ["bar", "baz"],
    "part_id": 1,
    "status": "active"
})
```

**SQL до редукции:**
```sql
WHERE 1=1
    AND (name IN ('foo', 'bar', 'baz') AND part_id = 1
         AND name IN ('bar', 'baz') AND status = 'active')
```

**SQL после редукции:**
```sql
WHERE 1=1
    AND name IN ('bar', 'baz')
    AND part_id = 1
    AND status = 'active'
```

#### Пример ошибки при редукции

**Вход:**
```python
ConditionAnd([
    ConditionSet({"name": ["foo", "bar"]}),
    ConditionSet({"name": ["baz", "qux"]})
])
```

**Процесс:**
- `name`: пересечение `["foo", "bar"]` ∩ `["baz", "qux"]` → `[]` (пусто)

**Результат:** `ValueError: Conflicting conditions for column 'name': no common values in ['foo', 'bar'] and ['baz', 'qux']`

---

### Правила редукции ConditionOr

#### Базовое правило
```
ConditionOr(ConditionSet1, ConditionSet2) → ConditionSet
```

**Условие для редукции:**
- Оба `ConditionSet` имеют **одинаковый набор столбцов**

**Логика:**
- Для каждого столбца берётся **объединение** значений

#### Пример успешной редукции

**Вход:**
```python
ConditionOr([
    ConditionSet({"name": ["foo", "bar"], "part_id": 1}),
    ConditionSet({"name": ["baz"], "part_id": 1})
])
```

**Анализ:**
- Столбцы первого: `["name", "part_id"]`
- Столбцы второго: `["name", "part_id"]`
- Совпадают ✓ → редукция возможна

**Процесс:**
- `name`: объединение `["foo", "bar"]` ∪ `["baz"]` → `["foo", "bar", "baz"]`
- `part_id`: объединение `[1]` ∪ `[1]` → `[1]` → упрощается до `1`

**Результат:**
```python
ConditionSet({
    "name": ["foo", "bar", "baz"],
    "part_id": 1
})
```

**SQL до редукции:**
```sql
WHERE 1=1
    AND (name IN ('foo', 'bar') AND part_id = 1
         OR name = 'baz' AND part_id = 1)
```

**SQL после редукции:**
```sql
WHERE 1=1
    AND name IN ('foo', 'bar', 'baz')
    AND part_id = 1
```

#### Пример неуспешной редукции

**Вход:**
```python
ConditionOr([
    ConditionSet({"name": ["foo", "bar"], "part_id": 1}),
    ConditionSet({"name": ["baz"], "status": "active"})
])
```

**Анализ:**
- Столбцы первого: `["name", "part_id"]`
- Столбцы второго: `["name", "status"]`
- Не совпадают ✗ → редукция невозможна

**Результат:** `ConditionOr(...)` возвращается без изменений

---

### Рекурсивная и итеративная редукция

#### Редукция вложенных структур

Вложенные структуры редуцируются рекурсивно — сначала внутренние контейнеры, затем внешние.

**Пример:**

**Вход:**
```python
ConditionAnd([
    ConditionSet({"name": "foo"}),
    ConditionOr([
        ConditionSet({"status": "active"}),
        ConditionSet({"status": "pending"})
    ])
])
```

**Шаг 1: Редукция вложенного `ConditionOr`**
- Столбцы совпадают (`["status"]`) → редуцируется
- Результат: `ConditionSet({"status": ["active", "pending"]})`

**Шаг 2: Редукция `ConditionAnd`**
```python
ConditionAnd([
    ConditionSet({"name": "foo"}),
    ConditionSet({"status": ["active", "pending"]})
])
```
→ Редуцируется в:
```python
ConditionSet({
    "name": "foo",
    "status": ["active", "pending"]
})
```

#### Итеративная редукция для >2 элементов

Если в `ConditionOr` или `ConditionAnd` больше 2 элементов:
1. Пытаться редуцировать **каждый с каждым** (порядок пар не важен)
2. После каждой успешной редукции — начинать процесс сначала
3. Остановиться, когда попытались каждый с каждым и редукций не было

**Пример итеративной редукции `ConditionAnd`:**

**Вход:**
```python
ConditionAnd([
    ConditionSet({"name": ["foo", "bar", "baz"]}),
    ConditionSet({"name": ["bar", "baz"]}),
    ConditionSet({"part_id": 1})
])
```

**Итерация 1:**
- Пара 1-2: редуцируется → `ConditionSet({"name": ["bar", "baz"]})`
- Заменяем пару на результат:
```python
ConditionAnd([
    ConditionSet({"name": ["bar", "baz"]}),
    ConditionSet({"part_id": 1})
])
```

**Итерация 2:**
- Пара 1-2: редуцируется → `ConditionSet({"name": ["bar", "baz"], "part_id": 1})`
- Один элемент → возврат как есть

**Результат:**
```python
ConditionSet({
    "name": ["bar", "baz"],
    "part_id": 1
})
```

---

### Функция `reduce_condition`

```python
def reduce_condition(condition: ConditionBase) -> ConditionBase:
    """
    Оптимизирует (редуцирует) структуру условий.

    Возвращает условие в максимально упрощённой форме.
    Редукция происходит рекурсивно снизу вверх.

    Args:
        condition: Исходное условие

    Returns:
        Редуцированное условие

    Raises:
        ValueError: При конфликте условий в ConditionAnd
    """
```

**Пример использования:**
```python
from libfa2.data_access.conditions import ConditionSet, ConditionOr, ConditionAnd, reduce_condition

# Сложное вложенное условие
condition = ConditionAnd([
    ConditionSet({"name": "foo"}),
    ConditionOr([
        ConditionSet({"status": "active"}),
        ConditionSet({"status": "pending"})
    ])
])

# Редуцируем
reduced = reduce_condition(condition)
# reduced == ConditionSet({"name": "foo", "status": ["active", "pending"]})
```

---

## Вспомогательные функции

### `_normalize_value(value: FilterValue) -> List[Any]`
Нормализует значение фильтра к списку.

**Примеры:**
```python
_normalize_value("foo")    # ["foo"]
_normalize_value([1, 2])  # [1, 2]
```

### `_denormalize_value(values: List[Any]) -> FilterValue`
Денормализует список значений в оптимальное представление.

Если список состоит из одного элемента, возвращает этот элемент. Иначе возвращает список.

**Примеры:**
```python
_denormalize_value(["foo"])    # "foo"
_denormalize_value([1, 2, 3])  # [1, 2, 3]
```

### `_intersect_values(value1: FilterValue, value2: FilterValue, column_name: str) -> FilterValue`
Вычисляет пересечение значений двух фильтров.

**Параметры:**
- `value1`: Первое значение или список значений
- `value2`: Второе значение или список значений
- `column_name`: Имя столбца (для сообщения об ошибке)

**Возвращает:**
- Пересечение значений

**Исключения:**
- `ValueError`: Если пересечение пусто

### `_union_values(value1: FilterValue, value2: FilterValue) -> FilterValue`
Вычисляет объединение значений двух фильтров с сохранением уникальности.

### `_has_same_columns(set1: ConditionSet, set2: ConditionSet) -> bool`
Проверяет, имеют ли два `ConditionSet` одинаковый набор столбцов.

---

## Примеры использования

### Пример 1: Создание простых условий

```python
from libfa2.data_access.conditions import ConditionSet

# Фильтр по одному столбцу с одиночным значением
cs1 = ConditionSet({"name": "foo"})

# Фильтр по нескольким столбцам
cs2 = ConditionSet({
    "name": ["foo", "bar", "baz"],
    "part_id": 1,
    "status": "active"
})

# Модификация фильтра
cs2.set_filter("name", "qux")  # Заменить значение
cs2.remove_filter("part_id")  # Удалить столбец

# Проверка наличия столбца
if cs2.has_column("status"):
    value = cs2.get_filter_for_column("status")
```

### Пример 2: Комбинирование условий с OR

```python
from libfa2.data_access.conditions import ConditionSet, ConditionOr, reduce_condition

# Создание условий с OR
or_condition = ConditionOr([
    ConditionSet({"name": ["foo", "bar"], "status": "active"}),
    ConditionSet({"name": "baz", "status": "active"}),
    ConditionSet({"name": ["qux"], "part_id": 1})
])

# Редукция (первые два условия объединятся)
reduced = reduce_condition(or_condition)
# reduced == ConditionOr([
#     ConditionSet({"name": ["foo", "bar", "baz"], "status": "active"}),
#     ConditionSet({"name": ["qux"], "part_id": 1})
# ])
```

### Пример 3: Комбинирование условий с AND

```python
from libfa2.data_access.conditions import ConditionSet, ConditionAnd, reduce_condition

# Создание условий с AND
and_condition = ConditionAnd([
    ConditionSet({"name": ["foo", "bar", "baz"]}),
    ConditionSet({"name": ["bar", "baz"]}),
    ConditionSet({"part_id": 1})
])

# Редукция (все три условия объединятся)
reduced = reduce_condition(and_condition)
# reduced == ConditionSet({
#     "name": ["bar", "baz"],
#     "part_id": 1
# })
```

### Пример 4: Вложенные структуры

```python
from libfa2.data_access.conditions import ConditionSet, ConditionOr, ConditionAnd, reduce_condition

# Сложная вложенная структура
complex_condition = ConditionAnd([
    ConditionOr([
        ConditionSet({"name": ["foo"], "status": "active"}),
        ConditionSet({"name": ["bar"], "status": "active"})
    ]),
    ConditionOr([
        ConditionSet({"name": ["foo"], "part_id": 1}),
        ConditionSet({"name": ["bar"], "part_id": 2})
    ]),
    ConditionSet({"region": "Moscow"})
])

# Редукция
reduced = reduce_condition(complex_condition)
# Результат: ConditionSet({
#     "name": ["foo", "bar"],
#     "status": "active",
#     "part_id": [1, 2],
#     "region": "Moscow"
# })
```

### Пример 5: Обработка конфликтов

```python
from libfa2.data_access.conditions import ConditionSet, ConditionAnd, reduce_condition

# Конфликтующие условия
conflict_condition = ConditionAnd([
    ConditionSet({"name": ["foo", "bar"]}),
    ConditionSet({"name": ["baz", "qux"]})
])

try:
    reduced = reduce_condition(conflict_condition)
except ValueError as e:
    print(f"Ошибка: {e}")
    # Ошибка: Conflicting conditions for column 'name': no common values in ['foo', 'bar'] and ['baz', 'qux']
```

### Пример 6: Сериализация и десериализация

```python
from libfa2.data_access.conditions import ConditionSet

# Создание из словаря
data = {"name": ["foo", "bar"], "part_id": 1}
cs = ConditionSet.from_dict(data)

# Сериализация в словарь
serialized = cs.to_dict()
# serialized == {"name": ["foo", "bar"], "part_id": 1}

# Проверка (возвращается копия)
serialized["new_col"] = "value"
print(cs.to_dict())  # {"name": ["foo", "bar"], "part_id": 1} - без new_col
```

---

## Сводная таблица правил редукции

| Шаблон | Редуцируется? | Результат | Условие |
|--------|---------------|-----------|---------|
| `ConditionSet` | ❌ | сам себя | — |
| `ConditionAnd(ConditionSet1, ConditionSet2)` | ✅ | `ConditionSet` | При непустом пересечении |
| `ConditionOr(ConditionSet1, ConditionSet2)` | ✅ | `ConditionSet` | При одинаковых столбцах |
| `ConditionAnd(ConditionOr(...), ...)` | ✅ | возможно | Рекурсивно (сначала вложенные) |
| `ConditionOr(ConditionOr(...), ...)` | ✅ | возможно | Рекурсивно (сначала вложенные) |
| `ConditionAnd([...])` (>2 элементов) | ⚠️ | итеративно | Пара за парой |
| `ConditionOr([...])` (>2 элементов) | ⚠️ | итеративно | Пара за парой |
| Смешанные структуры | ⚠️ | зависит от содержимого | Рекурсивно |

---

*Документация создана для модуля `libfa2.data_access.conditions`*
