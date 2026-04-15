Проект по имплементации факторного анализа отклонений факта от плана

тех стек: python 3.12+

Это часть большой микросервисной системы

Клиенты для доступа к другим микросервисам описаны в проекте aimis-sdk, который находится в /Users/baltakov-df/source/repos/aimis-sdk (этот путь доступен как еще один path для импорта модулей)

Общее описание бизнес требований в @agent_stuff/docs/factor_analysis__general_description.md

Для запуска юнит тестов и отладки можно использовать venv по пути /Users/baltakov-df/venv/foo

Для запуска тестов использовать команду:
```bash
source /Users/baltakov-df/venv/foo/bin/activate && PYTHONPATH=/Users/baltakov-df/source/repos/aimis2-core-fa-refac/src python -m pytest <test_file> -v
```

## Модули проекта

### libfa2.hier_metadata
Модуль для управления иерархией метрик факторного анализа.
- [`hierarchy.py`](src/libfa2/hier_metadata/hierarchy.py) — класс Hierarchy для управления деревом метрик
- [`metric_node.py`](src/libfa2/hier_metadata/metric_node.py) — класс MetricNode для узлов иерархии
- [`query.py`](src/libfa2/hier_metadata/query.py) — класс Query для параметров запросов к БД
- [`enums.py`](src/libfa2/hier_metadata/enums.py) — Enum классы для строковых констант

### libfa2.analyt_struct_metadata
Модуль для управления метаданными алгоритмов разложения по аналитическим разрезам.
- [`metadata.py`](src/libfa2/analyt_struct_metadata/metadata.py) — класс AnalyticalStructureMetadata для контейнера метаданных
- [`algorithm.py`](src/libfa2/analyt_struct_metadata/algorithm.py) — класс Algorithm для алгоритмов разложения
- [`dimension.py`](src/libfa2/analyt_struct_metadata/dimension.py) — класс Dimension для аналитических разрезов
- [`enums.py`](src/libfa2/analyt_struct_metadata/enums.py) — Enum классы для строковых констант
