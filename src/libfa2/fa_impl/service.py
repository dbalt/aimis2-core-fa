import asyncio
from .units import DrillComponent, Drill, DeviationAmts, DeviationDetailAmts, SearchDevParameters
from ..hier_metadata import Hierarchy
from ..analyt_struct_metadata import AnalyticalStructureMetadata
from datetime import date

async def calculate_deviations(
        rep_dt:date,
        hieararchy:Hierarchy,
        analytical_structure:AnalyticalStructureMetadata,
        params: SearchDevParameters
    ) -> DrillComponent:

    hier_root = hieararchy.get_root()

    for desc_node in hieararchy.get_children(hier_root.id):
        pass



    pass