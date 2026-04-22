import asyncio
from asyncio import TaskGroup

from .units import DrillComponent, Drill, DeviationAmts, DeviationDetailAmts, SearchDevParameters, SourceParameters
from ..hier_metadata import Hierarchy, MetricNode
from ..analyt_struct_metadata import AnalyticalStructureMetadata
from datetime import date
from ..data_access import DataAccess
from ..data_access.aggr import DataRow
from ..data_access.conditions import ConditionBase, ConditionSet, ConditionOr, reduce_condition, ConditionAnd
from sdk.core.monadic import Res
from typing import List, Dict, Any
from dataclasses import dataclass, field
from .deviation_calc_params import DeviationCalcParams








# def _get_conditions_for_hier_node(hier: Hierarchy, node: MetricNode, source_params:SourceParameters, rep_dt:date):
def _get_conditions_for_hier_node(cp:DeviationCalcParams, node:MetricNode):
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

        children = cp.hier.get_children(_node.id)

        if len(children) == 0:
            raise Exception(f'node {_node} has neither query property nor siblings')

        children_conds = [__traverse_hierarchy_for_query(x) for x in children]

        cond_or = ConditionOr(children_conds)

        return cond_or

    res = __traverse_hierarchy_for_query(node)
    res = ConditionAnd([res, ConditionSet.from_dict({cp.source_params.rep_dt_column: cp.rep_dt})])
    res = reduce_condition(res)
    return res




async def _get_data(
        cp:DeviationCalcParams,
        data_access:DataAccess,
        node:MetricNode,
        current_analyt:ConditionBase = None,
        next_analyt:List[str] = None
) -> Res[Dict[str,Any]]:

    _conditions = _get_conditions_for_hier_node(cp.hier, node, cp.source_params, cp.rep_dt)
    if current_analyt:
        _conditions = ConditionAnd([_conditions, current_analyt])
        _conditions = reduce_condition(_conditions)

    _grp_by_columns = []
    if next_analyt and len(next_analyt) > 0:
        _grp_by_columns = next_analyt


    res = await data_access.get_aggr_data(
        source=cp.source_params.source_name,
        grp_by_columns=_grp_by_columns,
        aggr_columns=[cp.search_dev_params.fact_column, cp.search_dev_params.plan_column],
        conditions=_conditions
    )



    return res





# class Driller(object):
#     def __init__(
#             self,
#             rep_dt:date,
#             hier:Hierarchy,
#             search_dev_params:SearchDevParameters,
#             source_params:SourceParameters,
#             data_access:DataAccess,
#             tsk_grp:TaskGroup
#         ):
#         self.rep_dt = rep_dt
#         self.hier = hier
#         self.search_dev_params = search_dev_params
#         self.source_params = source_params
#         self.data_access = data_access
#         self.tsk_grp = tsk_grp
#
#
#     async def build_drills(self, root_drill_component:DrillComponent)->Drill:
#         # 1. Если есть аналитическая структура - должны разложить по ней все
#
#         # 2. Иначе идем строить иерархический спуск
#         pass
#
#
# async def _build_drills(
#         rep_dt:date,
#         drill_component:DrillComponent,
#         hier:Hierarchy,
#         search_dev_params:SearchDevParameters,
#         source_params: SourceParameters,
#         data_access:DataAccess,
#         tg:TaskGroup
# ):
#
#     '''
#
#     :param rep_dt: Отчетная дата
#     :param drill_component: текущий компонент
#     :param hier: Иерархия показателей
#     :param search_dev_params:
#     :param source_params:
#     :param data_access:
#     :param tg:
#     :return:
#     '''
#
#
#     node = drill_component.hier_ref
#
#     if not node.is_leaf():
#         # Нужно дриллить по иерархии
#         pass
#
#
#     am = node.analyt_metadata
#     if am is not None:
#         cur_analyt_columns = drill_component.analyt_struct.keys()
#
#
#         # Возможно надо дрилллить по аналитике
#         pass



def get_factors(dataset: List[DataRow], params:SearchDevParameters)->List[DataRow]:

    # 1. sort list
    dataset.sort(key=lambda x:x.deviation, reverse= (params.sign_negative_impact != 1))

    # 2. calc sums
    _total_neg_fact = 0
    _total_neg_plan = 0
    _total_neg_deviation = 0
    for x in dataset:
        if not (x.deviation * params.sign_negative_impact > 0): continue

        _total_neg_plan = _total_neg_plan + x.plan
        _total_neg_fact = _total_neg_fact + x.fact
        _total_neg_deviation = _total_neg_deviation + x.deviation









async def calculate_deviations(
        cp:DeviationCalcParams,
        data_access: DataAccess
    ) -> DrillComponent:

    hier_root = cp.hier.get_root()

    async def __get_data_shortcut(
            _node:MetricNode,
            current_analyt_conditions: ConditionSet = None,
            next_analyt_slices:List[str] = None
    ):
        return await _get_data(
            cp,
            data_access,
            _node,
            current_analyt_conditions,
            next_analyt_slices
        )


    '''Результат верхнего уровня'''
    top_lvl_res = await __get_data_shortcut(hier_root)

    if not top_lvl_res.ok:
        raise Exception(top_lvl_res.err)

    top_lvl_data:DataRow = top_lvl_res.data[0]

    top_lvl_component = DrillComponent(
        hier_ref = hier_root,
        amts = DeviationAmts.mk(plan=top_lvl_data.plan, fact=top_lvl_data.fact)
    )





    async with asyncio.TaskGroup() as tg:
        tg.create_task(
            _build_drills(
                rep_dt,
                top_lvl_component,
                hierarchy,
                params,
                source_params,
                data_access,
                tg
            )
        )

    return top_lvl_component


    # Теперь мы должны рекурсивно наполнять эту историю

    # async def __mk_hier_drill(hier:Hierarchy, node:MetricNode, current_analyt_conditions:ConditionSet = None) -> Drill:
    #     from ..hier_metadata.enums import MetricType
    #     # Поскольку это спуск по иерархии - то мы тупо спускаемся вниз,
    #
    #     if node.type == MetricType.SUM:
    #         # Это самый обычный подход, суммируем по очереди тупо
    #
    #         drill_components = []
    #
    #         async def __collect_and_set(_node:MetricNode):
    #
    #             data_res = await __get_data_shortcut(hier, _node, current_analyt_conditions)
    #
    #             if not data_res.ok:
    #                 return
    #
    #             data_row:DataRow = data_res.data[0]
    #
    #             drill_component = DrillComponent(
    #                 hier_ref = _node,
    #                 analyt_struct=current_analyt_conditions.to_dict() if current_analyt_conditions is not None else dict(),
    #                 parent = node,
    #                 amts = DeviationAmts.mk(plan=data_row.plan, fact=data_row.fact)
    #             )
    #
    #             drill_components.append(drill_component)
    #
    #             return
    #
    #
    #         async with asyncio.TaskGroup() as tg:
    #             for x in hier.get_children(node.id):
    #                 tg.create_task(__collect_and_set(x))
















    for desc_node in hierarchy.get_children(hier_root.id):
        pass



    pass