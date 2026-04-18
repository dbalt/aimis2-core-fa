import asyncio
from .units import DrillComponent, Drill, DeviationAmts, DeviationDetailAmts, SearchDevParameters
from ..hier_metadata import Hierarchy
from ..analyt_struct_metadata import AnalyticalStructureMetadata
from datetime import date
from ..data_access import DataAccess

async def calculate_deviations(
        rep_dt:date,
        source:str, # argument for data access (if direct access then just table name)
        hierarchy:Hierarchy,
        params: SearchDevParameters,
        data_access: DataAccess
    ) -> DrillComponent:


    hier_root = hierarchy.get_root()



    # Сначала нужно собрать сумму отклонений на топ уровне

    top_lvl_res = await data_access.get_aggr_data(
        source = source,
        grp_by_columns = [],
        aggr_columns = [params.fact_column, params.plan_column],
        conditions = {

        }
    )




    for desc_node in hierarchy.get_children(hier_root.id):
        pass



    pass