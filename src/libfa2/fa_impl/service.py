import asyncio
from asyncio import TaskGroup

from pygments.style import ansicolors

from .units import DrillComponent, Drill, DeviationAmts, DeviationDetailAmts, SearchDevParameters, SourceParameters, EnumDrillType

from ..hier_metadata import Hierarchy, MetricNode, MetricType, ComponentMultiPartType, ComponentRatioPartType

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
from sdk.core.tools import search_first_in_lst_or








# def _get_conditions_for_hier_node(hier: Hierarchy, node: MetricNode, source_params:SourceParameters, rep_dt:date):
def _get_query_select_conditions_for_hierarchy_node(cp:DeviationCalcParams, node:MetricNode):
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




async def _query_data_from_data_access_layer(
        cp:DeviationCalcParams,
        data_access:DataAccess,
        node:MetricNode,
        current_analyt:ConditionBase = None,
        next_analyt:List[str] = None
) -> Res[List[DataRow]]:

    _conditions = _get_query_select_conditions_for_hierarchy_node(cp, node)
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






async def make_hier_drill(current_drill_component:DrillComponent, deviation_calc_params:DeviationCalcParams, data_access_client:DataAccess, task_group:TaskGroup):
    node = current_drill_component.hier_ref

    node_analyt_condition_set = None
    if current_drill_component.analyt_struct is not None and len(current_drill_component.analyt_struct.keys()) > 0:
        node_analyt_condition_set = ConditionSet(current_drill_component.analyt_struct)

    components: List[DataRow] = []
    factors:List[DataRow] = []
    deviation_detail_amts = DeviationDetailAmts()

    if node.type is None:
        return

    async def _get_data_for_node(node:MetricNode)->DataRow:
        val_res = await _query_data_from_data_access_layer(deviation_calc_params, data_access_client, node, node_analyt_condition_set)
        if not val_res.ok:
            raise Exception(f'Could not retrieve data for node:{node}, err:{val_res.err}')
        val_row = val_res.data[0]
        val_row.dims['node'] = chld
        return val_row


    _pos = lambda x: x if x > 0 else 0
    _neg = lambda x: x if x < 0 else 0

    if node.type == MetricType.SUM:
        # Собираем как сумму потомков
        for chld in deviation_calc_params.hier.get_children(node.id):
            val_row = await _get_data_for_node(chld)
            components.append(val_row)

        (factors, deviation_detail_amts) = get_factors(components, deviation_calc_params.search_dev_params)

        drill = Drill(
            drill_type=EnumDrillType.HIER,
            detail_amts=deviation_detail_amts
        )

        current_drill_component.drills.append(drill)

        for f in factors:
            chld_dc = DrillComponent(
                hier_ref=f.dims['chld'],
                analyt_struct=current_drill_component.analyt_struct,
                parent=drill,
                amts=DeviationAmts.mk(f.plan, f.fact)
            )

            drill.components.append(chld_dc)

            task_group.create_task(make_next_drill(chld_dc, deviation_calc_params, data_access_client, task_group))

        return






    if node.type == MetricType.MULTI:

        children = deviation_calc_params.hier.get_children(node.id)
        cmp_ratio = search_first_in_lst_or(children, lambda x:x.componentMultiPartType.RATE)
        cmp_base = search_first_in_lst_or(children, lambda x:x.componentMultiPartType.BASE)

        base_data = await _get_data_for_node(cmp_base)
        ratio_data = DataRow(
            dims = {'node':cmp_base},
            plan =current_drill_component.amts.plan / base_data.plan,
            fact =current_drill_component.amts.fact / base_data.fact
        )

        # Считаем влияение
        rat_direct_impact = ratio_data.fact * base_data.plan - ratio_data.plan * base_data.plan
        base_direct_impact = ratio_data.plan * base_data.fact - ratio_data.plan * base_data.plan
        total_impact = current_drill_component.amts.impact

        ratio_weighted_impact = (rat_direct_impact / (rat_direct_impact + base_direct_impact)) * total_impact
        base_weighted_impact = (base_direct_impact / (rat_direct_impact + base_direct_impact)) * total_impact

        ratio_dev_amts = DeviationAmts.mk_with_custom_impact(ratio_data.plan, ratio_data.fact, ratio_weighted_impact)
        base_dev_amts = DeviationAmts.mk_with_custom_impact(base_data.plan, base_data.plan, base_weighted_impact)

        deviation_detail_amts = DeviationDetailAmts(
            positive_contrib=_pos(ratio_weighted_impact) + _pos(base_weighted_impact),
            negative_contrib=_neg(ratio_weighted_impact) + _neg(base_weighted_impact)
        )

        drill = Drill(
            drill_type=EnumDrillType.HIER,
            detail_amts=deviation_detail_amts
        )

        current_drill_component.drills.append(drill)

        ratio_dc = DrillComponent(
            hier_ref=cmp_ratio,
            analyt_struct=current_drill_component.analyt_struct,
            parent=drill,
            amts = ratio_dev_amts
        )
        drill.components.append(ratio_dc)
        task_group.create_task(make_next_drill(ratio_dc, deviation_calc_params, data_access_client, task_group))


        base_dc = DrillComponent(
            hier_ref=cmp_base,
            analyt_struct=current_drill_component.analyt_struct,
            parent=drill,
            amts=base_dev_amts
        )
        drill.components.append(base_dc)
        task_group.create_task(make_next_drill(base_dc, deviation_calc_params, data_access_client, task_group))

        return




    if node.type == MetricType.RATIO:

        # Тут сильно под вопросом как вообще это считается. Это может быть только на верхнем уровне, тут надо думать что да как

        children = deviation_calc_params.hier.get_children(node.id)

        node_num:MetricNode = search_first_in_lst_or(children, lambda x:x.componentRatioPartType == ComponentRatioPartType.NUMERATOR)
        if node_num is None:
            raise Exception(f'Possible corrupted metadata. Cant find numerator part of ratio indicator')

        node_denom:MetricNode = search_first_in_lst_or(children, lambda x: x.componentRatioPartType == ComponentRatioPartType.DENOMINATOR)
        if node_denom is None:
            raise Exception(f'Possible corrupted metadata. Cant find denominator part of ratio indicator')

        num_data = await _get_data_for_node(node_num)
        denom_data = await _get_data_for_node(node_denom)

        if denom_data.plan == 0 or denom_data.fact == 0:
            # TODO: some kind of default behavior
            pass
        else:
            total_dev = abs(num_data.fact/denom_data.fact) - abs(num_data.plan/denom_data.plan)
            num_impact_direct_calc = abs(num_data.fact/denom_data.plan) - abs(num_data.plan/denom_data.plan)
            denom_impact_direct_calc = abs(num_data.plan/denom_data.fact) - abs(num_data.plan/denom_data.plan)

            num_impact_weighted = num_impact_direct_calc * total_dev /(num_impact_direct_calc + denom_impact_direct_calc)
            denom_impact_weighted = denom_impact_direct_calc * total_dev /(num_impact_direct_calc + denom_impact_direct_calc)

            factors = [num_data, denom_data]

            deviation_detail_amts = DeviationDetailAmts(
                positive_contrib= _pos(num_impact_weighted) + _pos(denom_impact_weighted),
                negative_contrib=_neg(num_impact_weighted) + _neg(denom_impact_weighted)
            )

            pass








async def make_analyt_drill(dc:DrillComponent, cp:DeviationCalcParams, da:DataAccess, tg:TaskGroup):
    """
    Эта ветка должна отрабатывать целиком до конца аналитическую нарезку
    Предварительно посчитать, нет ли уже чего нарезанного
    """



    async def _process_algorithm_step(_dc:DrillComponent, steps:List[List[str]]):
        current_step, *next_steps = steps

        _as = _dc.analyt_struct

        cond_set = None if len(_as.keys()) == 0 else ConditionSet(_as)

        data_res = await _query_data_from_data_access_layer(
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
        return await _query_data_from_data_access_layer(
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