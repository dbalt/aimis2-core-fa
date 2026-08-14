"""
QueryFilterDetail — фильтр запроса из табличной части
t_aimis_fa__query_filters__details (query_guide).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class QueryFilterDetail:
    """Деталь фильтра запроса (t_aimis_fa__query_filters__details)."""

    id: str
    code: int
    owner: str
    rank: int
    col_name: str
    value: Any

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QueryFilterDetail":
        return cls(
            id=data["id"],
            code=data["code"],
            owner=data["owner"],
            rank=data["rank"],
            col_name=data["col_name"],
            value=data["value"],
        )

    @classmethod
    def from_api_record(cls, api_record: dict) -> "QueryFilterDetail":
        return cls(
            id=api_record["id"],
            code=api_record["code"],
            owner=api_record["owner"],
            rank=api_record["rank"],
            col_name=api_record["col_name"],
            value=api_record["value"],
        )


def build_filter_dict(details: list[QueryFilterDetail]) -> dict[str, Any]:
    """
    Собрать QueryFilterDetail[] в {col_name: value}.

    Сортирует по rank, парсит JSON-массивы и числа.

    Пример:
        [QueryFilterDetail(col_name="ind_id", value="49", rank=1)]
        → {"ind_id": 49}
    """
    result: dict[str, Any] = {}

    for d in sorted(details, key=lambda x: x.rank):
        val = d.value

        # JSON-массив
        if isinstance(val, str) and val.startswith("["):
            try:
                val = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                pass
        # Число
        else:
            try:
                val = int(val)
            except (ValueError, TypeError):
                pass

        result[d.col_name] = val

    return result
