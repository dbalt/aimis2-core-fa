# Отчёт: Реализация модуля условий для доступа к данным (libfa2.data_access)

**Дата:** 2026-04-19
**Задача:** Реализация иерархической системы классов для SQL-условий фильтрации с возможностью комбинирования и редукции

---

## Обзор

Реализован модуль `src/libfa2/data_access/conditions.py` с полной функциональностью согласно задаче. Модуль предоставляет иерархическую систему классов для представления SQL-условий фильтрации (WHERE-clause) с поддержкой комбинирования операторами AND/OR и оптимизации структуры через редукцию.

---

## Реализованные компоненты

### 1. ConditionSet

**Файл:** `src/libfa2/data_access/conditions.py`

**Описание:** Типизированный контейнер для фильтрации по столбцам таблицы. По смыслу — `Dict[str, Any|List[Any]]`, где ключ — имя столбца, значение — одно значение или список значений.

**Реализованные методы:**

| Метод | Описание |
|--------|----------|
| `__init__(data=None)` | Инициализация с данными или пустой ConditionSet |
| `columns` (property) | Возвращает список имён столбцов |
| `get_filter_for_column(column_name)` | Возвращает значение(я) фильтрации для столбца |
| `set_filter(column_name, value)` | Устанавливает фильтр для столбца |
| `remove_filter(column_name)` | Удаляет фильтр для столбца |
| `has_column(column_name)` | Проверяет наличие столбца |
| `to_dict()` | Сериализует в словарь |
| `from_dict(data)` (classmethod) | Фабричный метод создания из словаря |
| `copy()` | Возвращает копию ConditionSet |

**SQL-семантика:**
```python
ConditionSet({"name": ["foo", "bar"], "part_id": 1})
# → WHERE 1=1 AND name IN ('foo', 'bar') AND part_id = 1
```

---

### 2. ConditionOr

**Описание:** Контейнер для условий, объединённых оператором OR (логическое ИЛИ).

**Реализованные методы:**

| Метод | Описание |
|--------|----------|
| `__init__(conditions=None)` | Инициализация со списком условий |
| `add(condition)` | Добавляет условие |
| `remove(index)` | Удаляет условие по индексу |
| `get(index)` | Возвращает условие по индексу |
| `conditions` (property) | Возвращает копию списка условий |
| `count` (property) | Возвращает количество условий |
| `columns` (property) | Возвращает все уникальные столбцы из вложенных условий |
| `get_filter_for_column(column_name)` | Возвращает фильтр из первого условия с данным столбцом |
| `copy()` | Возвращает копию контейнера |

**SQL-семантика:**
```python
ConditionOr([
    ConditionSet({"name": "foo", "part_id": 1}),
    ConditionSet({"name": "bar", "status": "active"})
])
# → WHERE 1=1 AND (name = 'foo' AND part_id = 1
#                  OR name = 'bar' AND status = 'active')
```

---

### 3. ConditionAnd

**Описание:** Контейнер для условий, объединённых оператором AND (логическое И).

**Реализованные методы:** То же, что и у ConditionOr.

**SQL-семантика:**
```python
ConditionAnd([
    ConditionSet({"name": "foo"}),
    ConditionSet({"part_id": 1})
])
# → WHERE 1=1 AND (name = 'foo' AND part_id = 1)
```

---

### 4. Иерархия классов

```
ConditionBase (абстрактный базовый класс)
    ├── ConditionSet
    ├── ConditionOr (наследует _ConditionContainer)
    └── ConditionAnd (наследует _ConditionContainer)
```

**ConditionBase (абстрактный):**
- `to_dict() -> Dict[str, FilterValue]`
- `columns -> List[str]` (property)
- `get_filter_for_column(column_name: str) -> FilterValue`

---

### 5. Функция reduce_condition

**Сигнатура:**
```python
def reduce_condition(condition: ConditionBase) -> ConditionBase
```

**Описание:** Оптимизирует структуру условий рекурсивно снизу вверх.

---

## Логика редукции

### 5.1. Базовые правила

| Исходное условие | Результат | Описание |
|-----------------|-----------|----------|
| `ConditionSet` | `ConditionSet` (as is) | Один ConditionSet не редуцируется |

### 5.2. ConditionAnd редукция

**Правило:** `ConditionAnd(ConditionSet1, ConditionSet2)` → `ConditionSet`

**Логика:**
1. Все столбцы из `ConditionSet2` добавляются в `ConditionSet1`
2. При пересечении имён столбцов — берётся **пересечение** значений
3. Если общих значений нет → **ValueError**

**Пример успешной редукции:**
```python
# Вход:
ConditionAnd([
    ConditionSet({"name": ["foo", "bar", "baz"], "part_id": 1}),
    ConditionSet({"name": ["bar", "baz"], "status": "active"})
])

# Результат:
ConditionSet({
    "name": ["bar", "baz"],  # пересечение
    "part_id": 1,
    "status": "active"
})
```

### 5.3. ConditionOr редукция

**Правило:** `ConditionOr(ConditionSet1, ConditionSet2)` → `ConditionSet` (если возможно)

**Условие:** Оба ConditionSet имеют одинаковый набор столбцов

**Логика:** Для каждого столбца берётся **объединение** значений

**Пример успешной редукции:**
```python
# Вход:
ConditionOr([
    ConditionSet({"name": ["foo", "bar"], "part_id": 1}),
    ConditionSet({"name": ["baz"], "part_id": 1})
])

# Результат:
ConditionSet({
    "name": ["foo", "bar", "baz"],  # объединение
    "part_id": 1
})
```

### 5.4. Рекурсивная редукция

Редукция начинается с листьев дерева и движется снизу вверх.

**Пример:**
```python
# Вход:
ConditionAnd([
    ConditionSet({"name": "foo"}),
    ConditionOr([
        ConditionSet({"status": "active"}),
        ConditionSet({"status": "pending"})
    ])
])

# Шаг 1: редуцируем вложенный ConditionOr
# → ConditionSet({"status": ["active", "pending"]})

# Шаг 2: редуцируем ConditionAnd
# → ConditionSet({"name": "foo", "status": ["active", "pending"]})
```

### 5.5. Итеративная редукция для >2 элементов

**Правило:** Пытаться редуцировать каждую с каждым парой. После успешной редукции — начинать процесс сначала.

---

## Тестирование

**Файл:** `src/libfa2/data_access/tests/test_conditions.py`

**Всего тестов:** 52

**Покрытие:**

| Категория | Количество тестов |
|-----------|-----------------|
| ConditionSet | 17 |
| ConditionOr | 13 |
| ConditionAnd | 5 |
| reduce_condition | 17 |

**Результат:** Все 52 теста проходят успешно.

**Тесты для `reduce_condition`:**
- ✅ Базовая редукция (ConditionSet — без изменений)
- ✅ ConditionAnd с двумя ConditionSet (успешная редукция)
- ✅ ConditionAnd с двумя ConditionSet (ошибка при пустом пересечении)
- ✅ ConditionAnd с одиночными значениями
- ✅ ConditionOr с двумя ConditionSet (успешная редукция)
- ✅ ConditionOr с двумя ConditionSet (неудачная редукция)
- ✅ Вложенная структура ConditionAnd(ConditionOr(...))
- ✅ ConditionAnd с тремя элементами (итеративная редукция)
- ✅ ConditionOr с тремя элементами (итеративная редукция)
- ✅ ConditionOr с частичной редукцией
- ✅ Рекурсивная редукция сложной структуры (ValueError)
- ✅ Успешная редукция вложенной структуры
- ✅ Глубоко вложенная структура
- ✅ Контейнеры с одним элементом
- ✅ Сохранение исходного условия (immutability)
- ✅ Объединение одиночных значений в список
- ✅ Редукция списка из одного элемента в одиночное значение
- ✅ Сложное дерево условий

---

## Вспомогательные функции (внутренние)

| Функция | Описание |
|---------|----------|
| `_normalize_value(value)` | Нормализует значение к списку |
| `_denormalize_value(values)` | Денормализует список к оптимальному представлению |
| `_intersect_values(v1, v2, col)` | Вычисляет пересечение значений |
| `_union_values(v1, v2)` | Вычисляет объединение значений |
| `_has_same_columns(set1, set2)` | Проверяет совпадение наборов столбцов |
| `_reduce_condition_and_condition_set()` | Редукция ConditionAnd → ConditionSet |
| `_reduce_condition_or_condition_set()` | Редукция ConditionOr → ConditionSet |
| `_iterative_reduce(container)` | Итеративная редукция контейнера |
| `_reduce_recursively(condition)` | Рекурсивная редукция снизу вверх |

---

## Изменения в существующих файлах

**`src/libfa2/data_access/__init__.py`:**
- Добавлен try/except для обработки отсутствия SDK в тестовой среде

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

## Структура файлов

```
src/libfa2/data_access/
├── __init__.py              # (модифицирован для тестовой среды)
├── aggr.py                  # (существующий)
├── conditions.py            # (новый) основной модуль
└── tests/
    ├── __init__.py          # (новый)
    └── test_conditions.py   # (новый) тесты

agent_stuff/reports/
└── condition_logic_impl_glm_report.md  # этот файл
```

---

## Заключение

Задача успешно выполнена. Реализована полная функциональность согласно ТЗ:

1. ✅ Класс `ConditionSet` с полным набором методов
2. ✅ Класс `ConditionOr` для условий с OR
3. ✅ Класс `ConditionAnd` для условий с AND
4. ✅ Иерархия наследования от `ConditionBase`
5. ✅ Функция `reduce_condition` с рекурсивной и итеративной редукцией
6. ✅ Обработка ошибок при конфликте условий
7. ✅ Полное покрытие тестами (52 теста, все проходят)

Модуль готов к использованию в системе факторного анализа для построения сложных SQL-условий фильтрации данных.
