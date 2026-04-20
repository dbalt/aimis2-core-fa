import asyncio
from .units import DrillComponent, Drill, DeviationAmts, DeviationDetailAmts, SearchDevParameters, SourceParameters
from ..hier_metadata import Hierarchy, MetricNode
from ..analyt_struct_metadata import AnalyticalStructureMetadata
from datetime import date
from ..data_access import DataAccess
from ..data_access.conditions import ConditionBase, ConditionSet, ConditionOr, reduce_condition, ConditionAnd









async def calculate_deviations(
        rep_dt:date,
        source_params:SourceParameters,
        hierarchy:Hierarchy,
        params: SearchDevParameters,
        data_access: DataAccess
    ) -> DrillComponent:



    def __get_conditions_for_hier_node(hier: Hierarchy, node: MetricNode):
        """
        Собираем условия для отбора данных соответствующим узлу иерархии
        (без учета аналитического разложения и отчетной даты)
        :param hier: Иерархия разложения отклонения
        :param node: Текущий уровень иерархии для которого собираем условия
        :return:
        """

        def __traverse_hierarchy_for_query(_node: MetricNode) -> ConditionBase:
            if _node.has_query():
                return ConditionSet.from_dict(_node.query.to_dict())

            children = hier.get_children(_node.id)

            if len(children) == 0:
                raise Exception(f'node {_node} has neither query property nor siblings')

            children_conds = [__traverse_hierarchy_for_query(x) for x in children]

            cond_or = ConditionOr(children_conds)

            return cond_or

        res = __traverse_hierarchy_for_query(node)
        res = ConditionAnd([res, ConditionSet.from_dict({source_params.rep_dt_column: rep_dt})])
        res = reduce_condition(res)
        return res

    hier_root = hierarchy.get_root()

    # Сначала нужно собрать сумму отклонений на топ уровне
    _conditions = __get_conditions_for_hier_node(hierarchy, hier_root)

    top_lvl_res = await data_access.get_aggr_data(
        source = source_params.source_name,
        grp_by_columns = [],
        aggr_columns = [params.fact_column, params.plan_column],
        conditions = _conditions
    )

    if not top_lvl_res.ok:
        raise Exception(top_lvl_res.err)

    top_lvl_data = top_lvl_res.data[0]

    top_lvl_component = DrillComponent(
        hier_ref = hier_root,
        amts = DeviationAmts.mk(plan=top_lvl_data['plan'], fact=top_lvl_data['fact'])
    )




    for desc_node in hierarchy.get_children(hier_root.id):
        pass



    pass