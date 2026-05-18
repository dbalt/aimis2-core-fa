# Отчет: Реализация функции get_factors

## Задача
Разработать функцию `get_factors` для разбиения итогового отклонения на позитивную/негативную составляющие и отбора наиболее существенных факторов негативного влияния по принципу Парето.

## Реализация

### Файл: `src/libfa2/fa_impl/search_factors.py`

Функция `get_factors(data_set, params) -> Tuple[List[DataRow], DeviationDetailAmts]`:

1. **Разбиение отклонений**: Обходит `data_set` и для каждого `DataRow` вычисляет отклонение (`fact - plan`). На основе `params.sign_negative_impact` определяет, является ли отклонение негативным:
   - `sign_negative_impact = -1`: негативные отклонения < 0
   - `sign_negative_impact = 1`: негативные отклонения > 0

2. **DeviationDetailAmts**: Формирует структуру с двумя полями:
   - `positive_contrib` — сумма всех позитивных отклонений
   - `negative_contrib` — сумма всех негативных отклонений
   - `total` — сумма positive + negative (property)

3. **Отбор по Парето**: Из негативных строк отбирает наиболее существенные, сортируя по `|deviation|` по убыванию и накапливая сумму, пока кумулятивный вклад не достигнет 80% от совокупного негатива.

### Исправленные баги

При работе были обнаружены и исправлены ошибки в существующих модулях:

1. **`aggr.py`**: Добавлен `from __future__ import annotations` для устранения `NameError: 'SearchDevParameters' is not defined` при импорте `DataRow`.

2. **`units.py`**: Класс `DeviationDetailAmts` был декорирован `@classmethod` вместо `@dataclass` — исправлено на `@dataclass`.

### Тесты

Файл `tests/libfa2/test_search_factors.py` — 12 тестов, разбитых на 4 группы:

| Группа | Кол-во | Покрытие |
|--------|--------|----------|
| TestDeviationDetailAmts | 4 | Разбиение positive/negative, пустой набор, все позитивные, все негативные |
| TestPositiveSignNegativeImpact | 2 | sign_negative_impact=1: инверсия знака, Парето по позитивным отклонениям |
| TestParetoSelection | 5 | Один большой фактор, два фактора для 80%, все строки, нулевое отклонение, сохранение dims |
| TestUnorderedInput | 1 | Сортировка по убыванию \|deviation\| |

Все 12 тестов проходят.
