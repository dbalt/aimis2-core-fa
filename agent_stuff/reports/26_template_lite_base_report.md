# Отчёт по задаче 26: Классы для упрощённого шаблона сценария обхода (template_lite)

## Суть задачи

В папке `src/tmp/template_lite` лежат JSON-файлы, заполненные утилитой по
составлению сценария обхода данных для факторного анализа. Требовалось:

1. Изучить структуру JSON и спроектировать классы для представления данных.
2. Поля с 2–5 значениями упаковать в `enum`-классы.
3. Написать функцию десериализации `get_from_template_lite_json()`.
4. Разместить классы и функции в модуле `libfa2.adhoc.template_lite`.
5. Тесты — в `libfa2.adhoc.template_lite.tests`.
6. Сохранить подробный отчёт.

## Структура исходных данных

Анализ обоих JSON-файлов (`чкд+_тб_business_lite.json`,
`операционный_доход_до_резервов_тб_business_lite.json`) показал единый формат:

```jsonc
{
  "metricName": "ЧКД+ ТБ",        // str — имя показателя сценария
  "nodes": [                       // list — узлы дерева сценария
    {
      "id": 1,                     // int — уникальный id узла
      "name": "ЧКД+ ТБ",           // str — отображаемое имя
      "role": "podstatya",         // str — роль узла (enum)
      "parent": null               // int | null — id родителя
    },
    ...
  ]
}
```

**Анализ полей на пригодность для enum (2–5 значений):**

| Поле         | Тип          | Кол-во значений | В enum? | Обоснование |
|--------------|--------------|-----------------|---------|-------------|
| `role`       | str          | 4               | ✅ Да   | Конечное множество ролей: `podstatya`, `razrez`, `tarif`, `baza` |
| `metricName` | str          | 2 (по файлам)   | ❌ Нет  | Произвольное отображаемое имя показателя, а не enum-домен |
| `id`         | int          | много           | ❌ Нет  | Произвольные числовые идентификаторы |
| `name`       | str          | много           | ❌ Нет  | Произвольные имена статей |
| `parent`     | int \| null  | много           | ❌ Нет  | Ссылки на id |

Единственное поле с доменом из 2–5 значений — `role` (ровно 4). Для него
создан один enum-класс `NodeRole`. Остальные поля представлены примитивными
типами.

## Семантика ролей и связь с предметной областью

| Роль JSON   | Enum-член          | Смысл в сценарии                                     | Аналог в полной иерархии |
|-------------|--------------------|------------------------------------------------------|--------------------------|
| `podstatya` | `NodeRole.PODSTATYA` | Подстатья — суммируемый компонент показателя       | суммируемый компонент (`SUM`) |
| `razrez`    | `NodeRole.RAZREZ`  | Аналитический разрез/срез (напр. «ТБ/ГОСБ»)          | аналитический dimension |
| `tarif`     | `NodeRole.TARIF`   | Тариф — компонент-множитель (ставка), лист в паре с базой | `ComponentMultiPartType.RATE` |
| `baza`      | `NodeRole.BAZA`    | База — объёмный показатель, лист в паре с тарифом    | `ComponentMultiPartType.BASE` |

`tarif`/`baza` всегда идут парами под одной подстатьей, образуя
мультипликативную статью (`ставка × объём`). Это отражено методом
`TemplateLite.get_multiplier_nodes()`.

## Спроектированные классы

Архитектура модуля повторяет устоявшийся паттерн проекта
`libfa2.hier_metadata` (dataclass + контейнер-дерево + enum + сериализация):

```
src/libfa2/adhoc/
├── __init__.py
└── template_lite/
    ├── __init__.py          # публичные экспорты
    ├── enums.py             # NodeRole (str, Enum)
    ├── node.py              # TemplateLiteNode (dataclass)
    ├── template.py          # TemplateLite (контейнер дерева)
    ├── deserializer.py      # get_from_template_lite_json()
    └── tests/
        ├── __init__.py
        ├── conftest.py
        ├── test_enums.py
        ├── test_node.py
        ├── test_template.py
        ├── test_deserializer.py
        └── test_real_files.py
```

### `NodeRole` (`enums.py`)
`(str, Enum)` со значениями `PODSTATYA`, `RAZREZ`, `TARIF`, `BAZA`.
Наследование от `str` даёт сравнение со строкой и прямую JSON-сериализацию
через `.value`, в духе `MetricType` из `hier_metadata.enums`.

### `TemplateLiteNode` (`node.py`)
`@dataclass` с полями `id: int`, `name: str`, `role: NodeRole`,
`parent: Optional[int] = None`.
Методы:
- классификаторы роли: `is_root`, `is_podstatya`, `is_razrez`, `is_tarif`, `is_baza`;
- сериализация: `to_dict`, `from_dict` (с валидацией типов);
- валидация: `validate`, `is_valid`;
- `__repr__`.

### `TemplateLite` (`template.py`)
`@dataclass`-контейнер: `metric_name: str`, `nodes: Dict[int, TemplateLiteNode]`.
Возможности:
- управление узлами: `add_node`/`remove_node`/`get_node`/`has_node`;
- навигация по дереву: `get_root`, `get_roots`, `get_children` (упорядочены по
  `id`), `get_parent`, `get_descendants`, `get_ancestors`, `get_path`;
- фильтры по ролям: `get_podstatya`, `get_razrez`, `get_tarif`, `get_baza`,
  `get_multiplier_nodes` (подстатьи с парой тариф+база);
- сериализация: `to_dict`, `to_json`, `to_json_string`,
  `from_dict`, `from_json_string`;
- валидация структуры: `validate` (непустое имя, ровно один корень, корень —
  `podstatya`, все `parent` существуют, отсутствие циклов),
  `_find_cycle`, `is_valid`;
- dunder-методы: `__len__`, `__contains__`, `__iter__`, `__repr__`, `__eq__`.

### `get_from_template_lite_json(source)` (`deserializer.py`)
Главная точка входа для разбора «lite»-сценариев. Принимает `source`
одного из трёх видов:
1. **путь к файлу** (`str` / `Path`) — основной сценарий («из этого json файла»);
2. **JSON-строка** (начинается с `{`/`[`);
3. **уже разобранный `dict`**.

Возвращает `TemplateLite`.

## Найденный и исправленный баг при разработке

Первоначально различение «файл vs JSON-строка» делалось через
`Path(text).is_file()`. Тест `test_from_json_string` (длинная JSON-строка)
вскрыл дефект: `is_file()` на слишком длинном имени выбрасывает
`OSError: [Errno 63] File name too long`, а не возвращает `False`.
Исправление: детерминированная эвристика по первому непробельному символу
(`{`/`[` → JSON-контент, иначе путь). Это быстрее (без обращения к ФС) и не
зависит от ограничений ОС на длину имени. Поведение отражено в тестах
(`test_nonexistent_path_raises`, `test_malformed_json_content_raises`).

## Тесты

Запуск: `PYTHONPATH=src python -m pytest src/libfa2/adhoc/template_lite/tests/ -v`
**Результат: 98 passed.**

Покрытие:
- `test_enums.py` — 4 значения, соответствие строкам JSON, наследование `str`, отказ от неизвестной роли;
- `test_node.py` — создание, классификаторы ролей, round-trip сериализации, валидация (пустое имя, нулевой/отрицательный id, self-parent), ошибки `from_dict`, `repr`;
- `test_template.py` — управление узлами, навигация (дети/предки/путь), фильтры по ролям, `get_multiplier_nodes`, round-trip сериализации, все правила `validate`, dunder-методы;
- `test_deserializer.py` — чтение из dict / JSON-строки / файла (`str` и `Path`, кириллические имена), обработка ошибок;
- `test_real_files.py` — end-to-end разбор обоих реальных файлов, round-trip `to_dict()` == исходный JSON, валидность структуры, парность тариф/база, проверки конкретных фактов.

## Результаты разбора реальных файлов

| Файл | metricName | Узлов | podstatya | razrez | tarif | baza | мультиплик. статей | Валиден |
|------|------------|-------|-----------|--------|-------|------|--------------------|---------|
| `операционный_доход_до_резервов_тб_business_lite.json` | Операционный доход до резервов ТБ | 72 | 53 | 3 | 8 | 8 | 7 | ✅ |
| `чкд+_тб_business_lite.json` | ЧКД+ ТБ | 33 | 31 | 2 | 0 | 0 | 0 | ✅ |

Оба файла десериализуются без ошибок, проходят `validate()` и round-trip
сериализацию, парность «тариф↔база» соблюдена.

## Использование

```python
from libfa2.adhoc.template_lite import get_from_template_lite_json, NodeRole

tpl = get_from_template_lite_json("src/tmp/template_lite/чкд+_тб_business_lite.json")
print(tpl.metric_name)              # 'ЧКД+ ТБ'
print(tpl.count_nodes())            # 33
print(len(tpl.get_razrez()))        # 2 — аналитических разреза
print(len(tpl.get_multiplier_nodes()))  # 0 — нет пар тариф/база
print(tpl.is_valid())               # True
```

## Принятые проектные решения

1. **Один enum `NodeRole`.** По данным только `role` имеет домен 2–5 значений
   (4). Альтернатива — разнести роли на два enum («структурные» и «части
   множителя») — отвергнута: в исходном JSON это единое поле `role`, и
   дублирование вводило бы неоднозначность десериализации.
2. **Контейнер хранит узлы в `dict` по `id`**, как и `Hierarchy`. Это даёт O(1)
   доступ и автоматически гарантирует уникальность `id`.
3. **Детерминированный порядок** вывода (сортировка по `id`) в `to_dict`,
   `get_children`, `__iter__` — для воспроизводимого round-trip и тестов.
4. **Сигнатура `get_from_template_lite_json(source)`.** В задаче функция
   показана без аргументов (`def get_from_template_lite_json()`), но
   десериализация без источника лишена смысла. Принят обязательный
   параметр `source` (путь/JSON/dict); такая сигнатура практична и единообразна
   с `Hierarchy.from_json_string`.
5. **Валидация корня = `podstatya`.** Сценарий описывает показатель, поэтому
   корневой узел обязан быть подстатьей (а не разрезом/тарифом/базой).
6. **Соответствие стилю кодовой базы:** docstrings на русском, dataclass,
   `Optional`/`List` из `typing` в сигнатурах навигации, `str, Enum` для
   констант — как в `hier_metadata`.
