"""
Маппинг значений из API Среды → enum-классы проекта.

API платформы «Среда» возвращает enum-значения как строки:
  node_type:            "SUM", "MULTI", "RATIO"
  multi_part_type:      "RATE", "BASE"
  ratio_part_type:      "NUMERATOR", "DENOMINATOR"
  mp_decomp_type:       "Integral", "DirectBase", "1"(баг), ...

Наши enum-классы ожидают lowercase-строки:
  MetricType.SUM = "sum"
  ComponentMultiPartType.RATE = "rate"
  и т.д.

Мапперы нормализуют входное значение к lowercase и ищут в маппинге.
Все мапперы case-insensitive: "SUM" и "sum" → MetricType.SUM.
"""

from __future__ import annotations

from typing import Any, Optional

from ..hier_metadata.enums import (
    ComponentMultiPartType,
    ComponentRatioPartType,
    MetricType,
    MultipartDecompositionType,
)


def map_metric_type(v: Any) -> Optional[MetricType]:
    """
    Маппинг node_type из API → MetricType.

    Поддерживаемые значения:
        "SUM" / "sum"       → MetricType.SUM
        "MULTI" / "multi"   → MetricType.MULTI
        "RATIO" / "ratio"   → MetricType.RATIO
        "1"                 → None (не маппится — числовой баг API)
        None                → None
    """
    if v is None:
        return None
    mapping = {
        "sum": MetricType.SUM,
        "multi": MetricType.MULTI,
        "ratio": MetricType.RATIO,
    }
    return mapping.get(str(v).strip().lower())


def map_multi_part_type(v: Any) -> Optional[ComponentMultiPartType]:
    """
    Маппинг multi_part_type из API → ComponentMultiPartType.

    Поддерживаемые значения:
        "RATE"  → ComponentMultiPartType.RATE
        "BASE"  → ComponentMultiPartType.BASE
        None    → None
    """
    if v is None:
        return None
    mapping = {
        "rate": ComponentMultiPartType.RATE,
        "base": ComponentMultiPartType.BASE,
    }
    return mapping.get(str(v).strip().lower())


def map_ratio_part_type(v: Any) -> Optional[ComponentRatioPartType]:
    """
    Маппинг ratio_part_type из API → ComponentRatioPartType.

    Поддерживаемые значения:
        "NUMERATOR"     → ComponentRatioPartType.NUMERATOR
        "DENOMINATOR"   → ComponentRatioPartType.DENOMINATOR
        None            → None
    """
    if v is None:
        return None
    mapping = {
        "numerator": ComponentRatioPartType.NUMERATOR,
        "denominator": ComponentRatioPartType.DENOMINATOR,
    }
    return mapping.get(str(v).strip().lower())


def map_mp_decomposition_type(v: Any) -> Optional[MultipartDecompositionType]:
    """
    Маппинг mp_decomp_type из API → MultipartDecompositionType.

    Поддерживаемые значения:
        "Integral"        → MultipartDecompositionType.INTEGRAL
        "DirectBase"      → MultipartDecompositionType.DIRECT_BASE
        "DirectRate"      → MultipartDecompositionType.DIRECT_RATE
        "AverageWeighted" → MultipartDecompositionType.AVERAGE_WEIGHTED
        "1"               → MultipartDecompositionType.INTEGRAL (баг сервера)
        None              → None
    """
    if v is None:
        return None
    mapping = {
        "integral": MultipartDecompositionType.INTEGRAL,
        "1": MultipartDecompositionType.INTEGRAL,  # баг сервера: возвращает "1" вместо "Integral"
        "averageweight": MultipartDecompositionType.AVERAGE_WEIGHTED,
        "averageweighted": MultipartDecompositionType.AVERAGE_WEIGHTED,
        "directbase": MultipartDecompositionType.DIRECT_BASE,
        "directrate": MultipartDecompositionType.DIRECT_RATE,
    }
    return mapping.get(str(v).strip().lower())
