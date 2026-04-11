# Summary: Реализация модели метаданных иерархии показателей

**Задача:** Реализовать классы для работы с метаинформацией иерархии показателей факторного анализа

**Статус:** ✅ Завершено

---

## Реализованные компоненты

### 1. Enum классы для строковых констант (`src/libfa2/hier_metadata/enums.py`)

```python
MetricType      # SUM, MULTI - типы составных показателей
DriverType     # RATE, BASE - типы драйверов
ValidationErrorType  # 12 типов ошибок валидации
```

### 2. Класс Query для параметров БД (`src/libfa2/hier_metadata/query.py`)

```python
Query:
  - params: dict[str, Any] | None
  - is_empty: bool
  - to_dict() -> dict | None
  - from_dict(dict) -> Query
```

### 3. Класс MetricNode для узла иерархии (`src/libfa2/hier_metadata/metric_node.py`)

```python
@dataclass MetricNode:
  - id: int                    # уникальный идентификатор
  - code: str                  # мнемонический код для API/UI
  - name: str                  # отображаемое имя
  - parent: int | None          # ID родительского узла
  - type: MetricType | None    # тип составного показателя
  - query: Query | None         # параметры запроса к БД
  - driver_type: DriverType | None  # тип драйвера

  Свойства:
    - is_leaf: bool
    - is_root: bool
    - is_sum_type: bool
    - is_multi_type: bool
    - is_rate_driver: bool
    - is_base_driver: bool
    - requires_db_query: bool

  Методы:
    - to_dict() -> dict    # опускает пустые поля
    - from_dict(dict) -> MetricNode
```

### 4. Класс Hierarchy для управления деревом (`src/libfa2/hier_metadata/hierarchy.py`)

```python
@dataclass Hierarchy:
  - nodes: dict[int, MetricNode]

  Свойства:
    - root: MetricNode | None
    - node_ids: set[int]
    - codes: set[str]

  CRUD операции:
    - add_node(MetricNode) -> None
    - add_nodes(Iterable[MetricNode]) -> None
    - remove_node(int) -> None
    - get_node(int) -> MetricNode | None
    - get_node_by_code(str) -> MetricNode | None

  Навигация:
    - get_children(int) -> list[MetricNode]
    - get_parent(int) -> MetricNode | None
    - get_ancestors(int) -> list[MetricNode]
    - get_descendants(int) -> list[MetricNode]

  Проверки:
    - is_leaf(int) -> bool
    - is_root(int) -> bool
    - find_roots() -> list[MetricNode]
    - find_leaves() -> list[MetricNode]

  Обходы:
    - traverse(order="preorder"|"postorder"|"bfs") -> list[MetricNode]
    - build_tree_dict() -> dict | None

  Сериализация:
    - to_json(indent) -> str
    - from_json(str) -> Hierarchy
    - from_nodes(Iterable[MetricNode]) -> Hierarchy

  Валидация:
    - validate() -> ValidationReport
```

### 5. Классы для валидации (`src/libfa2/hier_metadata/hierarchy.py`)

```python
@dataclass ValidationError:
  - type: ValidationErrorType
  - message: str
  - node_id: int | None
  - details: dict[str, Any] | None

@dataclass ValidationReport:
  - is_valid: bool
  - errors: list[ValidationError]

  Factory методы:
    - success() -> ValidationReport
    - failure(list[ValidationError]) -> ValidationReport
```

---

## Правила валидации

Метод `Hierarchy.validate()` проверяет:

1. **Дубликаты ID** - несколько узлов с одинаковым `id`
2. **Дубликаты кодов** - несколько узлов с одинаковым `code`
3. **Отсутствие корня** - нет узла с `parent: null`
4. **Несколько корней** - более одного узла с `parent: null`
5. **Неверная ссылка на родителя** - `parent` указывает на несуществующий ID
6. **Циклы** - обнаружение циклических ссылок
7. **Отсутствие типа у нелиста** - нелистовой узел без поля `type`
8. **Отсутствие query у multi** - multi-показатель без обязательного поля `query`
9. **Отсутствие driver_type** - потомок multi без типа драйвера
10. **Неверный driver_type** - значение не rate или base
11. **Query у rate драйвера** - rate driver рассчитывается, не должен иметь query

---

## JSON сериализация

### Особенности:
- Пустые поля (None, пустой query) опускаются из JSON
- Типы enum сериализуются как строки
- Поддерживается формат плоского списка и вложенного дерева

### Пример:

```json
[
  {
    "id": 1,
    "code": "FP",
    "name": "Финансовый результат",
    "type": "sum"
  },
  {
    "id": 101,
    "code": "INT_INC",
    "name": "Процентный доход",
    "parent": 1,
    "type": "multi",
    "query": {"metric": "interest_income"}
  }
]
```

---

## Тестирование

**Файл:** `tests/libfa2/hier_metadata/test_hierarchy_metadata.py`

**84 теста:**
- Query: 13 тестов
- MetricNode: 22 теста
- Hierarchy: 24 теста
- Validation: 12 тестов
- Full example: 3 интеграционных теста

**Все тесты проходят успешно.**

Интеграционные тесты используют полный пример иерархии из документации
и проверяют:
- Сериализацию/десериализацию
- Валидацию структуры
- Навигацию по дереву

---

## Использование

```python
from libfa2.hier_metadata import (
    Hierarchy,
    MetricNode,
    Query,
    MetricType,
    DriverType,
)

# Создание иерархии
hierarchy = Hierarchy()
root = MetricNode(id=1, code="ROOT", name="Root", type=MetricType.SUM)
child = MetricNode(id=2, code="CHILD", name="Child", parent=1)
hierarchy.add_nodes([root, child])

# Сериализация в JSON
json_str = hierarchy.to_json()

# Десериализация из JSON
restored = Hierarchy.from_json(json_str)

# Валидация
report = restored.validate()
if report.is_valid:
    print("Иерархия валидна")
else:
    for error in report.errors:
        print(f"Ошибка: {error.message}")
```

---

## Структура директории

```
src/libfa2/hier_metadata/
  ├── __init__.py       # Экспорт публичного API
  ├── enums.py           # Enum классы
  ├── query.py           # Query для параметров БД
  ├── metric_node.py     # Класс узла иерархии
  └── hierarchy.py        # Управление деревом и валидация

tests/libfa2/hier_metadata/
  └── test_hierarchy_metadata.py  # Все юнит-тесты
```

---

**Дата завершения:** 2026-04-11
