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


@dataclass
class SearchDevParameters:
    plan_column:str
    fact_column:str
    sign_negative_impact:int = -1
    # TODO: parameters to filter, if need






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

@dataclass
class DeviationDetailAmts:
    positive_contrib:float = 0
    negative_contrib:float = 0

    @property
    def total(self)->float:
        return self.positive_contrib + self.negative_contrib


@dataclass
class Drill:
    drill_type: str = ''

    detail_amts:DeviationDetailAmts = field(default_factory=DeviationDetailAmts)

    analyt_slice: List[str] = field(default_factory=List)

    components:List['DrillComponent'] = field(default_factory=List)



@dataclass
class DrillComponent:

    hier_ref: MetricNode

    analyt_struct: Dict[str,str] = field(default_factory=Dict)
    """ Описывается комбинация {измерение:значение}. 
        Например:
        {
            "Террбанк": "ЦА",
            "Сегмент": "Крупный бизнес",
        }
    """

    parent: Drill = None

    amts:DeviationAmts = field(default_factory=DeviationAmts)

    drills:List[Drill] = field(default_factory=List)




