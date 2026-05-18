import json
from dataclasses import dataclass, field
from ..hier_metadata import MetricNode
from typing import List, Dict


class EnumDrillType:
    HIER:str = 'h'
    ANALYTICAL:str = 'a'


@dataclass
class SourceParameters:
    source_name:str = ''
    rep_dt_column:str = 'rep_dt'

    def to_dict(self) -> dict:
        return {
            "source_name": self.source_name,
            "rep_dt_column": self.rep_dt_column,
        }

    def to_json(self) -> dict:
        result = {}
        if self.source_name:
            result["source_name"] = self.source_name
        if self.rep_dt_column:
            result["rep_dt_column"] = self.rep_dt_column
        return result

    def to_json_str(self) -> str:
        return json.dumps(self.to_json(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict) -> "SourceParameters":
        return cls(
            source_name=data.get("source_name", ""),
            rep_dt_column=data.get("rep_dt_column", "rep_dt"),
        )

    @classmethod
    def from_json(cls, data: dict) -> "SourceParameters":
        return cls.from_dict(data)

    @classmethod
    def from_json_str(cls, json_str: str) -> "SourceParameters":
        return cls.from_json(json.loads(json_str))


@dataclass
class SearchDevParameters:
    plan_column:str
    fact_column:str
    sign_negative_impact:int = -1
    # TODO: parameters to filter, if need

    def to_dict(self) -> dict:
        return {
            "plan_column": self.plan_column,
            "fact_column": self.fact_column,
            "sign_negative_impact": self.sign_negative_impact,
        }

    def to_json(self) -> dict:
        result = {}
        if self.plan_column:
            result["plan_column"] = self.plan_column
        if self.fact_column:
            result["fact_column"] = self.fact_column
        if self.sign_negative_impact is not None:
            result["sign_negative_impact"] = self.sign_negative_impact
        return result

    def to_json_str(self) -> str:
        return json.dumps(self.to_json(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict) -> "SearchDevParameters":
        return cls(
            plan_column=data["plan_column"],
            fact_column=data["fact_column"],
            sign_negative_impact=data.get("sign_negative_impact", -1),
        )

    @classmethod
    def from_json(cls, data: dict) -> "SearchDevParameters":
        return cls.from_dict(data)

    @classmethod
    def from_json_str(cls, json_str: str) -> "SearchDevParameters":
        return cls.from_json(json.loads(json_str))


def _rnd(x: float) -> float:
    if abs(x) < 1:
        return round(x, 8)
    return round(x, 2)


@dataclass
class DeviationAmts:
    plan:float = 0
    fact:float = 0
    deviation:float = 0
    impact:float = 0

    @classmethod
    def mk(cls, plan:float, fact:float, impact_ratio:float = 1)-> 'DeviationAmts':
        res = DeviationAmts(
            plan,
            fact,
            fact - plan,
            (fact - plan) * impact_ratio
        )
        return res

    @classmethod
    def mk_with_custom_impact(cls, plan:float, fact:float, custom_impact:float)->'DeviationAmts':
        res = DeviationAmts(
            plan,
            fact,
            fact - plan,
            custom_impact
        )
        return res

    def as_dict_for_summary(self)->Dict[str,float]:
        d = {
            'plan':_rnd(self.plan),
            'fact':_rnd(self.fact),
            'deviation':_rnd(self.deviation),
            'impact_to_top_lvl': _rnd(self.impact),
        }
        return d

@dataclass
class DeviationDetailAmts:
    positive_contrib:float = 0
    negative_contrib:float = 0

    @property
    def total(self)->float:
        return self.positive_contrib + self.negative_contrib

    def as_dict_for_summary(self)->Dict[str,float]:
        d = {
            'positive_contrib': _rnd(self.positive_contrib),
            'negative_contrib': _rnd(self.negative_contrib),
            'total': _rnd(self.total),
        }
        return d


@dataclass
class Drill:
    drill_type: str = ''

    detail_amts:DeviationDetailAmts = field(default_factory=DeviationDetailAmts)

    analyt_slice: List[str] = field(default_factory=list)

    components:List['DrillComponent'] = field(default_factory=list)



@dataclass
class DrillComponent:

    hier_ref: MetricNode

    analyt_struct: Dict[str,str] = field(default_factory=dict)
    """ Описывается комбинация {измерение:значение}. 
        Например:
        {
            "Террбанк": "ЦА",
            "Сегмент": "Крупный бизнес",
        }
    """

    parent: Drill = None

    amts:DeviationAmts = field(default_factory=DeviationAmts)

    drills:List[Drill] = field(default_factory=list)




