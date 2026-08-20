"""
QueryFilterDetail — фильтр запроса из табличной части
t_aimis_fa__query_filters__details (query_guide).
"""

from __future__ import annotations

import ast
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


def _parse_list_value(val: str) -> Any:
    """
    Попытаться распарсить строку как список (JSON или Python-style literal).

    API Среды возвращает массивы в двух форматах:
      - JSON:          '["code1", "code2"]'
      - Python literal: "['code1', 'code2']"  (node_code и т.п.)

    Если строка не распознаётся как список, возвращается исходное значение.
    """
    # 1) JSON-массив
    try:
        parsed = json.loads(val)
        if isinstance(parsed, list):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass

    # 2) Python-style literal: "['code1', 'code2']"
    try:
        parsed = ast.literal_eval(val)
        if isinstance(parsed, list):
            return parsed
    except (ValueError, TypeError, SyntaxError):
        pass

    # Не удалось распарсить — возвращаем строку как есть
    return val


def build_filter_dict(details: list[QueryFilterDetail]) -> dict[str, Any]:
    """
    Собрать QueryFilterDetail[] в {col_name: value}.

    Сортирует по rank, парсит JSON-массивы, Python-list строки и числа.

    Пример:
        [QueryFilterDetail(col_name="ind_id", value="49", rank=1)]
        → {"ind_id": 49}
        [QueryFilterDetail(col_name="node_code", value="['c1', 'c2']", rank=1)]
        → {"node_code": ["c1", "c2"]}
    """
    result: dict[str, Any] = {}

    for d in sorted(details, key=lambda x: x.rank):
        val = d.value

        # JSON-массив или Python-style список-строка
        if isinstance(val, str) and val.startswith("["):
            val = _parse_list_value(val)
        # Число
        else:
            try:
                val = int(val)
            except (ValueError, TypeError):
                pass

        result[d.col_name] = val

    return result
