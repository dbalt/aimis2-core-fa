# Отчет по реализации модуля метаданных аналитической структуры

## Обзор

Разработан модуль `libfa2.analyt_struct_metadata` для работы с метаинформацией алгоритмов разложения по аналитическим разрезам в системе факторного анализа отклонений факта от плана.

## Структура модуля

### Файлы модуля

```
src/libfa2/analyt_struct_metadata/
├── __init__.py           # Экспорт основных классов
├── enums.py              # Enum классы для строковых констант
├── dimension.py          # Класс Dimension
├── algorithm.py          # Класс Algorithm
└── metadata.py           # Класс AnalyticalStructureMetadata
```

### Файлы тестов

```
tests/libfa2/analyt_struct_metadata/
├── __init__.py
└── test_analyt_struct_metadata.py  # Комплексные unit tests
```

## Реализованные классы

### 1. ValidationErrorType (Enum)

**Файл:** [enums.py](src/libfa2/analyt_struct_metadata/enums.py)

Определяет типы ошибок валидации:

- `DUPLICATE_ALGORITHM_ID` — дублирующиеся ID алгоритмов
- `DUPLICATE_DIMENSION_CODE` — дублирующиеся коды разрезов
- `MISSING_DIMENSION_REFERENCE` — ссылка на несуществующий разрез
- `INVALID_ALGORITHM_ID` — некорректный ID алгоритма
- `INVALID_DIMENSION_CODE` — некорректный код разреза
- `INVALID_DRILL_ORDER` — некорректная структура drill_order
- `EMPTY_ALGORITHMS` — пустой список алгоритмов
- `EMPTY_DIMENSIONS` — пустой список разрезов
- `INVALID_DRILL_STEP` — некорректный шаг разложения
- `INVALID_DIMENSION_NAME` — пустое имя разреза
- `INVALID_DIMENSION_COLUMN` — пустое имя столбца

### 2. Dimension (dataclass)

**Файл:** [dimension.py](src/libfa2/analyt_struct_metadata/dimension.py)

Представляет аналитический разрез для детализации данных.

**Атрибуты:**
- `code: str` — уникальный код для ссылок из drill_order
- `name: str` — отображаемое имя разреза
- `column: str` — имя столбца в БД

**Методы:**
- `to_dict()` — сериализация в словарь
- `from_dict()` — десериализация из словаря
- Валидация в `__post_init__`
- Реализованы `__eq__`, `__hash__`, `__repr__`

### 3. Algorithm (dataclass)

**Файл:** [algorithm.py](src/libfa2/analyt_struct_metadata/algorithm.py)

Представляет алгоритм разложения по аналитическим разрезам.

**Атрибуты:**
- `id: int` — уникальный числовой идентификатор
- `drill_order: list[list[str]]` — порядок разложения (массив шагов)

**Свойства:**
- `step_count` — количество шагов разложения
- `dimension_codes` — множество всех используемых кодов разрезов

**Методы:**
- `get_step(step_index)` — получение конкретного шага
- `to_dict()` — сериализация в словарь
- `from_dict()` — десериализация из словаря
- `from_dict_strict()` — десериализация с дополнительной валидацией кодов разрезов
- Валидация в `__post_init__`
- Реализованы `__eq__`, `__hash__`, `__repr__`

### 4. ValidationError (dataclass)

**Файл:** [metadata.py](src/libfa2/analyt_struct_metadata/metadata.py)

Представляет ошибку валидации.

**Атрибуты:**
- `type: ValidationErrorType` — тип ошибки
- `message: str` — описание ошибки
- `algorithm_id: int | None` — ID алгоритма с ошибкой
- `dimension_code: str | None` — код разреза с ошибкой
- `details: dict | None` — дополнительная информация

### 5. ValidationReport (dataclass)

**Файл:** [metadata.py](src/libfa2/analyt_struct_metadata/metadata.py)

Отчет о валидации.

**Атрибуты:**
- `is_valid: bool` — признак успешной валидации
- `errors: list[ValidationError]` — список ошибок

**Методы:**
- `success()` — фабричный метод для успешного отчета
- `failure(errors)` — фабричный метод для отчета с ошибками

### 6. AnalyticalStructureMetadata (dataclass)

**Файл:** [metadata.py](src/libfa2/analyt_struct_metadata/metadata.py)

Контейнер для коллекции алгоритмов и разрезов.

**Атрибуты:**
- `algorithms: dict[int, Algorithm]` — словарь алгоритмов
- `dimensions: dict[str, Dimension]` — словарь разрезов

**Свойства:**
- `algorithm_ids` — множество ID алгоритмов
- `dimension_codes` — множество кодов разрезов

**Методы:**
- `add_algorithm()` / `add_algorithms()` — добавление алгоритмов
- `remove_algorithm()` — удаление алгоритма
- `add_dimension()` / `add_dimensions()` — добавление разрезов
- `remove_dimension()` — удаление разреза
- `get_algorithm()` — получение алгоритма по ID
- `get_dimension()` — получение разреза по коду
- `to_json()` — сериализация в JSON
- `from_json()` — десериализация из JSON
- `validate()` — комплексная валидация структуры
- Реализованы `__eq__`, `__len__`, `__contains__`, `__repr__`

## Сериализация/десериализация JSON

### Формат JSON

```json
{
  "algorithms": [
    {
      "id": 1,
      "drill_order": [
        ["segment"],
        ["geo_structure"],
        ["product"]
      ]
    }
  ],
  "dimensions": [
    {
      "code": "segment",
      "name": "Сегмент",
      "column": "segment_id"
    }
  ]
}
```

### Особенности

1. **Опциональные поля:** При сериализации отсутствующие поля опускаются (в данном модуле все поля обязательные, так как они необходимы для корректной работы).

2. **Копирование данных:** Методы `to_dict()` возвращают независимые копии структур данных для предотвращения случайных изменений.

3. **Поддержка Unicode:** JSON сериализуется с поддержкой Unicode символов (кириллица и т.д.) без эскейпинга.

## Валидация

### Проверки, выполняемые методом `validate()`

1. **Проверка на пустоту:**
   - `EMPTY_ALGORITHMS` — список алгоритмов пуст
   - `EMPTY_DIMENSIONS` — список разрезов пуст

2. **Проверка дубликатов:**
   - `DUPLICATE_ALGORITHM_ID` — дублирующиеся ID алгоритмов
   - `DUPLICATE_DIMENSION_CODE` — дублирующиеся коды разрезов

3. **Проверка ссылок:**
   - `MISSING_DIMENSION_REFERENCE` — drill_order ссылается на несуществующий код разреза

4. **Проверка структуры алгоритмов:**
   - `INVALID_ALGORITHM_ID` — ID не является положительным целым числом
   - `INVALID_DRILL_ORDER` — drill_order не является списком или пуст
   - `INVALID_DRILL_STEP` — шаг разложения некорректен

5. **Проверка структуры разрезов:**
   - `INVALID_DIMENSION_CODE` — код разреза пуст
   - `INVALID_DIMENSION_NAME` — имя разреза пусто
   - `INVALID_DIMENSION_COLUMN` — имя столбца пусто

## Тестирование

### Статистика

- **Всего тестов:** 82
- **Пройдено:** 82
- **Провалено:** 0

### Классы тестов

1. **TestDimension** (13 тестов) — тесты класса Dimension
2. **TestAlgorithm** (21 тест) — тесты класса Algorithm
3. **TestAnalyticalStructureMetadata** (19 тестов) — тесты контейнера
4. **TestValidation** (8 тестов) — тесты валидации
5. **TestFullExample** (4 теста) — интеграционные тесты с полным примером
6. **TestJsonStructure** (6 тестов) — тесты JSON сериализации

### Пример теста с полным примером

Тест `TestFullExample.test_full_example_serialization_deserialization` проверяет:
- Создание полной структуры метаданных (5 алгоритмов, 6 разрезов)
- Сериализацию в JSON
- Десериализацию из JSON
- Проверку соответствия оригинала и десериализованных данных

## Пример использования

### Создание метаданных

```python
from libfa2.analyt_struct_metadata import (
    AnalyticalStructureMetadata,
    Algorithm,
    Dimension,
)

metadata = AnalyticalStructureMetadata()

# Добавляем разрезы
metadata.add_dimensions([
    Dimension(code="segment", name="Сегмент", column="segment_id"),
    Dimension(code="geo_structure", name="Геоструктура", column="geo_structure_id"),
    Dimension(code="product", name="Продукт", column="product_id"),
])

# Добавляем алгоритмы
metadata.add_algorithms([
    Algorithm(
        id=1,
        drill_order=[
            ["segment"],
            ["geo_structure"],
            ["product"]
        ]
    ),
    Algorithm(
        id=2,
        drill_order=[
            ["segment"],
            ["geo_structure", "product"],  # Пересечение разрезов
        ]
    ),
])

# Валидация
report = metadata.validate()
if report.is_valid:
    print("Метаданные валидны")
else:
    for error in report.errors:
        print(f"Ошибка: {error.message}")
```

### Сериализация/десериализация

```python
# Сериализация
json_str = metadata.to_json(indent=2)
with open("metadata.json", "w") as f:
    f.write(json_str)

# Десериализация
with open("metadata.json") as f:
    metadata = AnalyticalStructureMetadata.from_json(f.read())
```

### Работа с алгоритмами

```python
# Получить алгоритм по ID
algo = metadata.get_algorithm(1)
if algo:
    print(f"Шагов разложения: {algo.step_count}")
    print(f"Используемые разрезы: {algo.dimension_codes}")

# Получить конкретный шаг
step_0 = algo.get_step(0)  # Первый шаг
step_1 = algo.get_step(1)  # Второй шаг
```

## Сравнение с существующими модулями

Модуль `analyt_struct_metadata` разработан в соответствии с паттернами, используемыми в существующем модуле `hier_metadata`:

| Аспект | hier_metadata | analyt_struct_metadata |
|--------|--------------|------------------------|
| Enum классы | ✓ | ✓ |
| Dataclass для сущностей | ✓ | ✓ |
| Методы to_dict/from_dict | ✓ | ✓ |
| Валидация | ✓ | ✓ |
| JSON сериализация | ✓ | ✓ |
| Unit tests | ✓ | ✓ |

## Вывод

Модуль `libfa2.analyt_struct_metadata` полностью реализован и протестирован. Он предоставляет:

1. ✅ Классы для работы с метаинформацией аналитической структуры
2. ✅ Функции сериализации/десериализации в/из JSON
3. ✅ Комплексную валидацию корректности структуры
4. ✅ Строковые константы в виде Enum классов
5. ✅ Лаконичную документацию (docstrings)
6. ✅ 82 unit теста, включая проверку на полноценном примере

Код размещен в директории [`src/libfa2/analyt_struct_metadata/`](src/libfa2/analyt_struct_metadata/).
