# Отчет: JSON сериализация/десериализация DeviationCalcParams

## Задача
Добавить методы JSON сериализации и десериализации в `DeviationCalcParams` и все используемые им классы.

## Анализ зависимостей

Граф зависимостей `DeviationCalcParams`:
```
DeviationCalcParams
├── date (datetime) — встроенный тип, сериализуется как ISO-строка
├── SourceParameters — нужны методы ✅ добавлены
├── SearchDevParameters — нужны методы ✅ добавлены
└── Hierarchy — уже имеет to_json/from_json ✅ без изменений
    └── MetricNode — уже имеет to_dict/to_json/from_dict/from_json ✅ без изменений
        ├── Query — уже имеет to_dict/to_json/from_dict/from_json ✅ без изменений
        ├── enums (MetricType, ComponentMultiPartType, ...) — str Enum ✅ без изменений
        └── AnalyticalStructureMetadata — уже имеет to_json/from_json ✅ без изменений
            ├── Algorithm — уже имеет to_dict/from_dict ✅ без изменений
            └── Dimension — уже имеет to_dict/from_dict ✅ без изменений
```

Классы `Hierarchy`, `MetricNode`, `Query`, `AnalyticalStructureMetadata`, `Algorithm`, `Dimension` уже имели нужные методы сериализации — изменения потребовались только в `SourceParameters`, `SearchDevParameters` и `DeviationCalcParams`.

## Внесенные изменения

### 1. `src/libfa2/fa_impl/units.py`

Добавлен `import json`. Добавлены методы в `SourceParameters` и `SearchDevParameters`:

| Метод | Описание |
|-------|----------|
| `to_dict()` | Полный словарь (включая пустые значения) |
| `to_json()` | Словарь без пустых значений (None, "", []) |
| `to_json_str()` | `json.dumps(to_json(), ensure_ascii=False)` |
| `from_dict(data)` | Создание из словаря |
| `from_json(data)` | Синоним `from_dict` |
| `from_json_str(s)` | Десериализация из JSON-строки |

### 2. `src/libfa2/fa_impl/deviation_calc_params.py`

Добавлен `import json`. Добавлены 6 методов в `DeviationCalcParams`:

| Метод | Описание |
|-------|----------|
| `to_dict()` | Полный словарь; `rep_dt` → ISO-строка; `hier` через `to_json(include_empty_fields=True)` |
| `to_json()` | Без пустых значений; делегирует вложенным объектам |
| `to_json_str()` | `json.dumps(to_json(), ensure_ascii=False)` |
| `from_dict(data)` | Создание из словаря; поддерживает `rep_dt` как строку и как `date` |
| `from_json(data)` | Синоним `from_dict` |
| `from_json_str(s)` | Десериализация из JSON-строки |

### 3. Тесты: `tests/libfa2/test_deviation_calc_params_serde.py`

38 тестов в 3 классах:
- **TestSourceParametersSerde** (12 тестов) — все 6 методов + roundtrip + edge cases
- **TestSearchDevParametersSerde** (12 тестов) — все 6 методов + roundtrip + валидация обязательных полей
- **TestDeviationCalcParamsSerde** (14 тестов) — все 6 методов + roundtrip через все форматы + иерархия с аналитикой + MULTI-узлы

Все 38 тестов проходят.
