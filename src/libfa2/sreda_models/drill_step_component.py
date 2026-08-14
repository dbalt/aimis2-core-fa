"""
DrillStepComponent — данные из табличной части
t_aimis_fa__analyt_drill_steps__components (step_guide).
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from ..analyt_struct_metadata.dimension import Dimension


@dataclass
class DrillStepComponent:
    """
    Компонент шага аналитического разложения.

    Содержит измерительные колонки для drill-down.
    """

    id: str
    code: int
    owner: str
    rank: int
    col_name: str
    col_descr: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DrillStepComponent":
        return cls(
            id=data["id"],
            code=data["code"],
            owner=data["owner"],
            rank=data["rank"],
            col_name=data["col_name"],
            col_descr=data["col_descr"],
        )

    @classmethod
    def from_api_record(cls, api_record: dict) -> "DrillStepComponent":
        return cls(
            id=api_record["id"],
            code=api_record["code"],
            owner=api_record["owner"],
            rank=api_record["rank"],
            col_name=api_record["col_name"],
            col_descr=api_record["col_descr"],
        )


def build_drill_order(
    components: list[DrillStepComponent],
) -> list[list[str]]:
    """
    Собрать DrillStepComponent[] в drill_order для Algorithm.

    Сортирует по rank и возвращает [[col_name], ...].

    Пример:
        [DrillStepComponent(col_name="biz_block", rank=1)]
        → [["biz_block"]]
    """
    return [[c.col_name] for c in sorted(components, key=lambda x: x.rank)]


def build_dimensions(
    components: list[DrillStepComponent],
) -> dict[str, Any]:
    """
    Собрать DrillStepComponent[] в словарь col_name → Dimension.

    Пример:
        {"biz_block": Dimension(code="biz_block", name="Бизнес-блок", column="biz_block")}
    """
    from analyt_struct_metadata.dimension import Dimension

    return {
        c.col_name: Dimension(
            code=c.col_name, name=c.col_descr, column=c.col_name
        )
        for c in components
    }
