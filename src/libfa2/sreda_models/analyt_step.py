"""
AnalytStep — шаг аналитического разложения из табличной части
t_aimis_fa__metric_hier__analyt_steps (metric_hier guide).
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class AnalytStep:
    """Шаг аналитического разложения (t_aimis_fa__metric_hier__analyt_steps)."""

    id: str
    code: int
    owner: str
    rank: int
    step: str  # UUID алгоритма → GUID step_guide

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnalytStep":
        return cls(
            id=data["id"],
            code=data["code"],
            owner=data["owner"],
            rank=data["rank"],
            step=data["step"],
        )

    @classmethod
    def from_api_record(cls, api_record: dict) -> "AnalytStep":
        return cls(
            id=api_record["id"],
            code=api_record["code"],
            owner=api_record["owner"],
            rank=api_record["rank"],
            step=api_record["step"],
        )
