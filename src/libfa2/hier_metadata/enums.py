"""
Enum classes for hierarchy metadata string constants.

This module contains all enum classes that define string constants used
throughout the hierarchy metadata system. Using enum classes ensures
type safety and self-documenting code.
"""

from enum import Enum


class MetricType(Enum):
    """
    Типы составных показателей.

    Определяет способ агрегации дочерних элементов для составного показателя.
    """

    SUM = "sum"
    """Суммируемый показатель - равен сумме дочерних элементов."""

    MULTI = "multi"
    """
    Мультипликативный показатель - равен произведению драйверов.
    Используется для показателей, которые рассчитываются как произведение
    коэффициента (rate) на базу (base).
    """


class DriverType(Enum):
    """
    Типы драйверов для мультипликативных показателей.

    Драйверы используются в показателях типа `multi` для разложения
    показателя на коэффициент и базу.
    """

    RATE = "rate"
    """
    Коэффициент, ставка, процент.

    Нормированный показатель, который рассчитывается обратным счетом:
    rate = multi_показатель / base.

    Примеры: ставка по кредитам, процентная маржа.
    """

    BASE = "base"
    """
    Объемный показатель, абсолютное значение.

    Абсолютный показатель, на который умножается коэффициент.

    Примеры: объем выданных кредитов, количество клиентов.
    """


class ValidationErrorType(Enum):
    """
    Типы ошибок валидации метаданных иерархии.

    Используется для классификации ошибок, обнаруженных при проверке
    корректности структуры метаданных.
    """

    DUPLICATE_ID = "duplicate_id"
    """Несколько узлов имеют одинаковый идентификатор."""

    DUPLICATE_CODE = "duplicate_code"
    """Несколько узлов имеют одинаковый код."""

    MISSING_ROOT = "missing_root"
    """Отсутствует корневой узел (узел с parent=null)."""

    MULTIPLE_ROOTS = "multiple_roots"
    """Найдено несколько корневых узлов (должен быть один)."""

    INVALID_PARENT_REFERENCE = "invalid_parent_reference"
    """Узел ссылается на несуществующий родительский идентификатор."""

    CYCLE_DETECTED = "cycle_detected"
    """В иерархии обнаружен циклический узор (узел ссылается сам на себя косвенно)."""

    MISSING_TYPE_FOR_NON_LEAF = "missing_type_for_non_leaf"
    """У нелистового узла отсутствует поле type."""

    MISSING_QUERY_FOR_MULTI = "missing_query_for_multi"
    """У показателя типа multi отсутствует обязательное поле query."""

    MISSING_DRIVER_TYPE = "missing_driver_type"
    """
    У дочернего элемента multi-показателя отсутствует поле driverType.
    """

    INVALID_DRIVER_TYPE = "invalid_driver_type"
    """Значение driverType не является допустимым (не rate или base)."""

    INVALID_METRIC_TYPE = "invalid_metric_type"
    """Значение type не является допустимым (не sum или multi)."""

    INVALID_RATE_DRIVER_WITH_QUERY = "invalid_rate_driver_with_query"
    """
    Драйвер типа rate не должен иметь поле query, так как рассчитывается
    обратным счетом: rate = multi_показатель / base.
    """
