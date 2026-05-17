import json
from dataclasses import dataclass
from datetime import date
from typing import List

from sdk.core.logging import get_logger

from .deviation_calc_params import DeviationCalcParams
from .units import SearchDevParameters, SourceParameters
from ..hier_metadata import Hierarchy


@dataclass
class DeviationCalcMetadata:
    """Метаданные для расчета отклонений по нескольким иерархиям."""

    code: str | None
    source_params: SourceParameters
    search_dev_params: SearchDevParameters
    hier_lst: List[Hierarchy]

    # ---- serialization: dict ----

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "source_params": self.source_params.to_dict(),
            "search_dev_params": self.search_dev_params.to_dict(),
            "hier_lst": [h.to_json(include_empty_fields=True) for h in self.hier_lst],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DeviationCalcMetadata":
        lgr = get_logger()
        lgr.info("Deserializing DeviationCalcMetadata from dict")
        hier_lst = [Hierarchy.from_json(h) for h in data["hier_lst"]]
        lgr.debug("Restored %d hierarchies", len(hier_lst))
        return cls(
            code=data.get("code"),
            source_params=SourceParameters.from_dict(data["source_params"]),
            search_dev_params=SearchDevParameters.from_dict(data["search_dev_params"]),
            hier_lst=hier_lst,
        )

    # ---- serialization: json dict ----

    def to_json(self) -> dict:
        result = {}
        if self.code is not None:
            result["code"] = self.code
        result["source_params"] = self.source_params.to_json()
        result["search_dev_params"] = self.search_dev_params.to_json()
        result["hier_lst"] = [h.to_json() for h in self.hier_lst]
        return result

    @classmethod
    def from_json(cls, data: dict) -> "DeviationCalcMetadata":
        return cls.from_dict(data)

    # ---- serialization: json string ----

    def to_json_str(self) -> str:
        return json.dumps(self.to_json(), ensure_ascii=False)

    @classmethod
    def from_json_str(cls, json_str: str) -> "DeviationCalcMetadata":
        lgr = get_logger()
        lgr.debug("Parsing DeviationCalcMetadata from json string")
        return cls.from_json(json.loads(json_str))

    # ---- business logic ----

    def calc_params_lst(self, rep_dt: date) -> List[DeviationCalcParams]:
        """Генерация списка DeviationCalcParams для каждой иерархии на заданную дату."""
        lgr = get_logger()
        lgr.info(
            "Generating DeviationCalcParams list: rep_dt=%s, hier_count=%d",
            rep_dt.isoformat(), len(self.hier_lst),
        )
        result = [
            DeviationCalcParams(
                code=self.code,
                rep_dt=rep_dt,
                source_params=self.source_params,
                search_dev_params=self.search_dev_params,
                hier=hier,
            )
            for hier in self.hier_lst
        ]
        lgr.debug("Generated %d DeviationCalcParams instances", len(result))
        return result
