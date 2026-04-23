import asyncio
from asyncio import TaskGroup

from pygments.style import ansicolors

from .units import DrillComponent, Drill, DeviationAmts, DeviationDetailAmts, SearchDevParameters, SourceParameters, EnumDrillType

from ..hier_metadata import Hierarchy, MetricNode, MetricType

from ..analyt_struct_metadata import AnalyticalStructureMetadata, Algorithm, Dimension

from datetime import date
from ..data_access import DataAccess
from ..data_access.aggr import DataRow
from ..data_access.conditions import ConditionBase, ConditionSet, ConditionOr, reduce_condition, ConditionAnd
from sdk.core.monadic import Res
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, field
from .deviation_calc_params import DeviationCalcParams
from .search_factors import get_factors








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
) -> Res[List[DataRow]]:

    _conditions = _get_conditions_for_hier_node(cp, node)
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


async def make_hier_drill(dc:DrillComponent, cp:DeviationCalcParams, da:DataAccess, tg:TaskGroup):
    node = dc.hier_ref

    node_analyt_condition_set = None
    if dc.analyt_struct is not None and len(dc.analyt_struct.keys()) > 0:
        node_analyt_condition_set = ConditionSet(dc.analyt_struct)

    components: List[DataRow] = []
    factors:List[DataRow] = []
    deviation_detail_amts = DeviationDetailAmts()

    if node.type == MetricType.SUM:
        # Собираем как сумму потомков

        for chld in cp.hier.get_children(node.id):
            val_res = await _get_data(cp, da, chld, node_analyt_condition_set)
            if not val_res.ok: continue
            val_row = val_res.data[0]
            val_row.dims['node'] = chld
            components.append(val_row)

        (factors, deviation_detail_amts) = get_factors(components, cp.search_dev_params)

    drill = Drill(
        drill_type=EnumDrillType.HIER,
        detail_amts=deviation_detail_amts
    )

    dc.drills.append(drill)

    for f in factors:
        chld_dc = DrillComponent(
            hier_ref=f.dims['chld'],
            analyt_struct=dc.analyt_struct,
            parent=drill,
            amts=DeviationAmts.mk(f.plan, f.fact)
        )

        tg.create_task(make_next_drill(chld_dc, cp, da, tg))

        drill.components.append(
            chld_dc
        )


async def make_analyt_drill(dc:DrillComponent, cp:DeviationCalcParams, da:DataAccess, tg:TaskGroup):
    """
    Эта ветка должна отрабатывать целиком до конца аналитическую нарезку
    Предварительно посчитать, нет ли уже чего нарезанного
    """



    async def _process_algorithm_step(_dc:DrillComponent, steps:List[List[str]]):
        current_step, *next_steps = steps

        _as = _dc.analyt_struct

        cond_set = None if len(_as.keys()) == 0 else ConditionSet(_as)

        data_res = await _get_data(
            cp, da, _dc.hier_ref, cond_set, current_step
        )

        if not data_res.ok:
            raise Exception(data_res.err)

        data_set = data_res.data





    async def _process_algorithm(_dc:DrillComponent, alg:Algorithm):
        # Вычисляем шаги, с учетом что у нас уже может быть как то порезано по аналит разрезам
        current_analytical_slices = _dc.analyt_struct.keys()
        steps = []
        for step in alg.drill_order:
            new_step = [x for x in step if x not in current_analytical_slices]
            if len(new_step) == 0: continue
            steps.append(new_step)

        tg.create_task(_process_algorithm_step(_dc, steps))



    for a in dc.hier_ref.analyt_metadata.algorithms.values():
        tg.create_task(_process_algorithm(a))

    # node = dc.hier_ref
    # current_analytical_slices:List[str] = dc.analyt_struct.keys()
    # for a in node.analyt_metadata.algorithms.values(): # Algorithm
    #     a.drill_order





async def make_next_drill(dc:DrillComponent, cp:DeviationCalcParams, da:DataAccess, tg:TaskGroup):
    """
    Пока что действуем в такой парадигме:
    - Если есть метаданные аналитического разложения - идем в них
    - Иначе идем в иерархию

    Тем самым у нас в итоге только одна ветка сценариев
    """
    node = dc.hier_ref
    if node.analyt_metadata:
        tg.create_task(make_analyt_drill(dc, cp, da, tg))
    else:
        tg.create_task(make_hier_drill(dc, cp, da, tg))
















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


    '''
        Результат верхнего уровня
    '''
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