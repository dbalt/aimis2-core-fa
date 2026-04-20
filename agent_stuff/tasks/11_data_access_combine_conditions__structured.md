# Задача: Реализация модуля условий для доступа к данным (libfa2.data_access)

**Модуль:** `@src/libfa2/data_access/`

## Обзор

Реализовать иерархическую систему классов для представления SQL-условий фильтрации (`WHERE`-clause) с возможностью их комбинирования и оптимизации (редукции).

---

## Часть 1. ConditionSet

### Описание
Типизированный контейнер для фильтрации по столбцам таблицы. По смыслу — `Dict[str, Any|List[Any]]`, где:
- **ключ** — имя столбца
- **значение** — одно значение или список значений для фильтрации

### SQL-семантика
Для словаря:
```python
{
    "name": ["foo", "bar"],
    "part_id": 1
}
```
Генерируется SQL:
```sql
WHERE 1=1
    AND name IN ('foo', 'bar')
    AND part_id = 1
```

### Обязательные методы

```python
class ConditionSet:
    @property
    def columns(self) -> List[str]:
        """Возвращает список имён столбцов в ConditionSet."""

    def get_filter_for_column(self, column_name: str) -> Any | List[Any]:
        """Возвращает значение(я) фильтрации для указанного столбца."""

    def to_dict(self) -> Dict[str, Any | List[Any]]:
        """Сериализует в словарь."""

    @classmethod
    def from_dict(cls, data: Dict[str, Any | List[Any]]) -> "ConditionSet":
        """Фабричный метод создания из словаря."""
```

### Дополнительные методы (по вашему усмотрению)
- CRUD-операции для модификации содержимого
- Методы проверки валидности
- Методы объединения/пересечения с другими ConditionSet

---

## Часть 2. ConditionOr

### Описание
Контейнер для условий, объединённых оператором `OR` (логическое ИЛИ).

### SQL-семантика
Для двух ConditionSet:
```python
ConditionOr([
    ConditionSet({"name": ["foo", "bar"], "part_id": 1}),
    ConditionSet({"name": "baz", "part_id": [1, 2, 3]})
])
```
Генерируется SQL:
```sql
WHERE 1=1
    AND (
        name IN ('foo', 'bar') AND part_id = 1
        OR
        name = 'baz' AND part_id IN (1, 2, 3)
    )
```

### Требования
- Хранит список объектов типа `ConditionBase`
- Реализует CRUD-операции для управления условиями
- Стандартный набор методов (как у ConditionSet)

---

## Часть 3. ConditionAnd

### Описание
Контейнер для условий, объединённых оператором `AND` (логическое И).

### SQL-семантика
Аналогична `ConditionOr`, но с оператором `AND` между условиями:
```sql
WHERE 1=1
    AND (
        условие_1 AND условие_2 AND условие_3
    )
```

---

## Часть 4. Иерархия классов

```
ConditionBase (абстрактный базовый класс)
    ├── ConditionSet
    ├── ConditionOr
    └── ConditionAnd
```

- `ConditionOr` и `ConditionAnd` — контейнеры для элементов типа `ConditionBase`
- Поддерживаются вложенные конструкции любой глубины

---

## Часть 5. Функция `reduce_condition`

### Сигнатура
```python
def reduce_condition(condition: ConditionBase) -> ConditionBase:
    """
    Оптимизирует (редуцирует) структуру условий.
    Возвращает условие в максимально упрощённой форме.
    """
```

### Логика редукции

#### 5.1. Базовые правила

| Исходное условие | Результат | Описание |
|-----------------|-----------|----------|
| `ConditionSet` | `ConditionSet` (as is) | Один ConditionSet не редуцируется |

#### 5.2. ConditionAnd редукция

**Правило:** `ConditionAnd(ConditionSet1, ConditionSet2)` → `ConditionSet`

Логика:
1. Все столбцы из `ConditionSet2` добавляются в `ConditionSet1`
2. При пересечении имён столбцов — берётся **пересечение** значений фильтров
3. Если общих значений нет → **ошибка**

##### Пример 1: Успешная редукция ConditionAnd

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

##### Пример 2: Ошибка при редукции ConditionAnd

**Вход:**
```python
ConditionAnd([
    ConditionSet({"name": ["foo", "bar"]}),
    ConditionSet({"name": ["baz", "qux"]})
])
```

**Процесс:**
- `name`: пересечение `["foo", "bar"]` ∩ `["baz", "qux"]` → `[]` (пусто)

**Результат:** `ValueError` (нет общих значений)

---

#### 5.3. ConditionOr редукция

**Правило:** `ConditionOr(ConditionSet1, ConditionSet2)` → `ConditionSet` (если возможно)

Условие для редукции:
- Оба ConditionSet имеют **одинаковый набор столбцов**

Логика:
- Для каждого столбца берётся **объединение** значений

##### Пример 3: Успешная редукция ConditionOr

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

##### Пример 4: Неуспешная редукция ConditionOr

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

#### 5.4. Редукция вложенных структур

Вложенные структуры могут быть редуцированы рекурсивно — сначала редуцируются внутренние контейнеры, затем внешние.

##### Пример 5: Успешная редукция вложенной структуры

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

**Шаг 1: Редукция вложенного ConditionOr**
- Столбцы совпадают (`["status"]`) → редуцируется
- Результат: `ConditionSet({"status": ["active", "pending"]})`

**Промежуточное состояние:**
```python
ConditionAnd([
    ConditionSet({"name": "foo"}),
    ConditionSet({"status": ["active", "pending"]})
])
```

**Шаг 2: Редукция ConditionAnd**
- Объединяем столбцы из обоих ConditionSet

**Результат:**
```python
ConditionSet({
    "name": "foo",
    "status": ["active", "pending"]
})
```

**SQL до редукции:**
```sql
WHERE 1=1
    AND (name = 'foo' AND (status = 'active' OR status = 'pending'))
```

**SQL после редукции:**
```sql
WHERE 1=1
    AND name = 'foo'
    AND status IN ('active', 'pending')
```

---

#### 5.5. Множественные элементы (итеративная редукция)

**Правило:** Если в ConditionOr или ConditionAnd больше 2 элементов:
1. Пытаться редуцировать **каждый с каждым** (порядок пар не важен)
2. После каждой успешной редукции — начинать процесс сначала
3. Остановиться, когда попытались каждый с каждым и редукций не было

##### Пример 6: Итеративная редукция ConditionAnd

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

##### Пример 7: Итеративная редукция ConditionOr

**Вход:**
```python
ConditionOr([
    ConditionSet({"name": ["foo"], "status": "active"}),
    ConditionSet({"name": ["bar"], "status": "active"}),
    ConditionSet({"name": ["baz"], "status": "active"})
])
```

**Итерация 1:**
- Пара 1-2: столбцы совпадают, редуцируется → `ConditionSet({"name": ["foo", "bar"], "status": "active"})`

```python
ConditionOr([
    ConditionSet({"name": ["foo", "bar"], "status": "active"}),
    ConditionSet({"name": ["baz"], "status": "active"})
])
```

**Итерация 2:**
- Пара 1-2: столбцы совпадают, редуцируется → `ConditionSet({"name": ["foo", "bar", "baz"], "status": "active"})`
- Один элемент → возврат как есть

**Результат:**
```python
ConditionSet({
    "name": ["foo", "bar", "baz"],
    "status": "active"
})
```

##### Пример 8: Частичная редукция с остановкой

**Вход:**
```python
ConditionOr([
    ConditionSet({"name": ["foo"], "status": "active"}),
    ConditionSet({"name": ["bar"], "status": "active"}),
    ConditionSet({"name": ["baz"], "part_id": 1})  # Другие столбцы!
])
```

**Итерация 1:**
- Пара 1-2: редуцируется → `ConditionSet({"name": ["foo", "bar"], "status": "active"})`
- Пары с 3-м элементом: не редуцируются (разные столбцы)

```python
ConditionOr([
    ConditionSet({"name": ["foo", "bar"], "status": "active"}),
    ConditionSet({"name": ["baz"], "part_id": 1})
])
```

**Итерация 2:**
- Пара 1-2: разные столбцы → не редуцируется

**Результат:** остановка, возврат как есть

---

#### 5.6. Рекурсивная редукция (снизу вверх)

**Правило:** Редукция начинается с листьев дерева.

##### Пример 9: Рекурсивная редукция

**Вход:**
```python
ConditionAnd([
    ConditionOr([
        ConditionSet({"name": ["foo"], "status": "active"}),
        ConditionSet({"name": ["bar"], "status": "active"})
    ]),
    ConditionOr([
        ConditionSet({"name": ["baz"], "part_id": 1}),
        ConditionSet({"name": ["qux"], "part_id": 1})
    ]),
    ConditionSet({"region": "Moscow"})
])
```

**Шаг 1: Редукция первого ConditionOr**
- Столбцы совпадают → редуцируется
- Результат: `ConditionSet({"name": ["foo", "bar"], "status": "active"})`

**Шаг 2: Редукция второго ConditionOr**
- Столбцы совпадают → редуцируется
- Результат: `ConditionSet({"name": ["baz", "qux"], "part_id": 1})`

**Промежуточное состояние:**
```python
ConditionAnd([
    ConditionSet({"name": ["foo", "bar"], "status": "active"}),
    ConditionSet({"name": ["baz", "qux"], "part_id": 1}),
    ConditionSet({"region": "Moscow"})
])
```

**Шаг 3: Попытка редукции ConditionAnd**
- Пара 1-2: `name` → пересечение `["foo", "bar"]` ∩ `["baz", "qux"]` → пусто → **ошибка!**

**Результат:** `ValueError` — противоречивые условия

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

## Требования к реализации

### Модули
1. **Основной модуль:** `src/libfa2/data_access/conditions.py`
   - Классы `ConditionBase`, `ConditionSet`, `ConditionOr`, `ConditionAnd`
   - Функция `reduce_condition`

2. **Тесты:** `src/libfa2/data_access/tests/test_conditions.py`
   - Юнит-тесты для всех классов
   - Тесты для `reduce_condition` с покрытием всех описанных кейсов

### Требования к коду
- Лаконичные и понятные комментарии
- Соблюдение PEP 8
- Типизация (type hints)
- Обработка ошибок (особенно для конфликтующих условий в ConditionAnd)

### Отчёт
Сохранить отчёт о проделанной работе в:
`@agent_stuff/reports/condition_logic_impl_glm_report.md`
