import json
from dataclasses import dataclass
from datetime import date
from .units import SearchDevParameters, SourceParameters
from ..hier_metadata import Hierarchy
from ..analyt_struct_metadata import AnalyticalStructureMetadata


@dataclass
class DeviationCalcParams:
    code:str|None
    rep_dt:date|None
    source_params:SourceParameters
    search_dev_params:SearchDevParameters
    hier:Hierarchy

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "rep_dt": self.rep_dt.isoformat() if self.rep_dt else None,
            "source_params": self.source_params.to_dict(),
            "search_dev_params": self.search_dev_params.to_dict(),
            "hier": self.hier.to_json(include_empty_fields=True),
        }

    def to_json(self) -> dict:
        result = {}
        if self.code is not None:
            result["code"] = self.code
        if self.rep_dt is not None:
            result["rep_dt"] = self.rep_dt.isoformat()
        result["source_params"] = self.source_params.to_json()
        result["search_dev_params"] = self.search_dev_params.to_json()
        result["hier"] = self.hier.to_json()
        return result

    def to_json_str(self) -> str:
        return json.dumps(self.to_json(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict) -> "DeviationCalcParams":
        return cls(
            code = data.get('code'),
            rep_dt=date.fromisoformat(data["rep_dt"]) if isinstance(data["rep_dt"], str) else data["rep_dt"],
            source_params=SourceParameters.from_dict(data["source_params"]),
            search_dev_params=SearchDevParameters.from_dict(data["search_dev_params"]),
            hier=Hierarchy.from_json(data["hier"]),
        )

    @classmethod
    def from_json(cls, data: dict) -> "DeviationCalcParams":
        return cls.from_dict(data)

    @classmethod
    def from_json_str(cls, json_str: str) -> "DeviationCalcParams":
        return cls.from_json(json.loads(json_str))

