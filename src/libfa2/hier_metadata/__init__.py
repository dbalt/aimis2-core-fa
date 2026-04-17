"""
Модуль hier_metadata для управления иерархией метрик факторного анализа.

Этот модуль предоставляет классы для работы с метаданными иерархии финансовых показателей,
используемых при выполнении факторного анализа отклонений факта от плана.

Основные классы:
- Hierarchy: Контейнер для управления деревом метрик
- MetricNode: Узел в иерархии показателей
- Query: Параметры запроса к БД

Enum классы для строковых констант:
- MetricType: Тип показателя (sum, multi, ratio)
- ComponentMultiPartType: Тип компонента-множителя (rate, base)
- ComponentRatioPartType: Тип компонента-отношения (numerator, denominator)

Пример использования:
    >>> from libfa2.hier_metadata import Hierarchy, MetricNode, MetricType, Query
    >>>
    >>> hierarchy = Hierarchy()
    >>>
    >>> # Создаем корневой узел
    >>> root = MetricNode(
    ...     id=100,
    ...     code="NII",
    ...     name="Чистый процентный доход",
    ...     type=MetricType.SUM
    ... )
    >>> hierarchy.add_node(root)
    >>>
    >>> # Создаем дочерний узел с query
    >>> child = MetricNode(
    ...     id=101,
    ...     code="INT_INC",
    ...     name="Процентный доход",
    ...     type=MetricType.MULTI,
    ...     parent=100,
    ...     query=Query({"metricType": "interest_income"})
    ... )
    >>> hierarchy.add_node(child)
    >>>
    >>> # Сериализация
    >>> json_str = hierarchy.to_json_string()
    >>>
    >>> # Десериализация
    >>> restored = Hierarchy.from_json_string(json_str)
"""

from .hierarchy import Hierarchy
from .metric_node import MetricNode
from .query import Query
from .enums import MetricType, ComponentMultiPartType, ComponentRatioPartType

__all__ = [
    "Hierarchy",
    "MetricNode",
    "Query",
    "MetricType",
    "ComponentMultiPartType",
    "ComponentRatioPartType",
]

__version__ = "1.0.0"
