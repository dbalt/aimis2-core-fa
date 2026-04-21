from dataclasses import dataclass
from datetime import date
from .units import SearchDevParameters, SourceParameters
from ..hier_metadata import Hierarchy
from ..analyt_struct_metadata import AnalyticalStructureMetadata


@dataclass
class DeviationCalcParams:
    rep_dt:date
    source_params:SourceParameters
    search_dev_params:SearchDevParameters
    hier:Hierarchy

