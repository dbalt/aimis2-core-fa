"""
Модуль service.py — ядро факторного анализа отклонений.

Содержит главную точку входа calculate_deviations() и рекурсивный движок
пошагового погружения (drill-down) по двум осям:
  1. Иерархия показателей (make_hier_drill) — SUM / MULTI / RATIO
  2. Аналитические разрезы (make_analyt_drill) — сегмент, гео и т.д.

Движок работает через asyncio.TaskGroup: каждый дочерний DrillComponent
планируется как отдельная задача, что обеспечивает параллельную загрузку данных.

Архитектура вложенных функций:
  - Вложенные async-def (например _get_data_for_node) замыкают параметры
    внешней функции (cp, data_access, ...) и используются как «локальные хелперы».
    НЕ вызывать извне — они существуют только в рамках вызова родительской функции.
  - Вложенные функции с двумя подчёркиваниями (__func_name) — приватные
    рекурсивные обходчики, не предполагающие прямого вызова.

Рекомендации по расширению:
  - Добавлять новый тип разложения по иерархии — в make_hier_drill, новый if-блок.
  - Добавлять новый drill-type — новая async-функция + вызов из make_next_drill.
  - При добавлении новых вложенных функций следовать паттерну: замыкание параметров
    через внешнюю область видимости, без мутации захваченных переменных.
"""

import asyncio
from asyncio import TaskGroup

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

from sdk.core.logging import get_logger




# ---------------------------------------------------------------------------
# Вспомогательные функции для построения запросов к слою данных
# ---------------------------------------------------------------------------

def _get_query_select_conditions_for_hierarchy_node(cp:DeviationCalcParams, node:MetricNode):
    """
    Собирает условия выборки (WHERE) для узла иерархии.

    Рекурсивно обходит поддерево node: листья с query → ConditionSet,
    промежуточные узлы → ConditionOr по всем потомкам. Затем добавляет
    фильтр по отчётной дате (rep_dt) и упрощает дерево условий через reduce_condition.

    Используется на каждом уровне drill-down для формирования запроса к DAL.

    Вложенная функция __traverse_hierarchy_for_query:
      - Рекурсивный обход поддерева от _node до листьев.
      - Замыкает cp для доступа к иерархии.
      - Не вызывать напрямую — только через обёртку выше.
    """

    def __traverse_hierarchy_for_query(_node: MetricNode) -> ConditionBase:
        # Лист: берём готовые условия из query-параметров узла
        if _node.has_query():
            return ConditionSet.from_dict(_node.query.to_dict())

        # Промежуточный узел: объединяем условия потомков через OR
        children = cp.hier.get_children(_node.id)

        if len(children) == 0:
            raise Exception(f'node {_node} has neither query property nor siblings')

        children_conds = [__traverse_hierarchy_for_query(x) for x in children]
        cond_or = ConditionOr(children_conds)
        return cond_or

    lgr = get_logger()
    lgr.debug(f'Building query conditions for node id={node.id}, name={node.name}')

    res = __traverse_hierarchy_for_query(node)
    # Добавляем фильтр по отчётной дате
    res = ConditionAnd([res, ConditionSet.from_dict({cp.source_params.rep_dt_column: cp.rep_dt})])
    res = reduce_condition(res)

    lgr.debug(f'Query conditions for node id={node.id} built: {res}')
    return res


async def _query_data_from_data_access_layer(
        cp:DeviationCalcParams,
        data_access:DataAccess,
        node:MetricNode,
        current_analyt:ConditionBase = None,
        next_analyt:List[str] = None
) -> Res[List[DataRow]]:
    """
    Единая точка запроса агрегированных данных из DAL.

    - Строит условия выборки по узлу иерархии (_get_query_select_conditions_for_hierarchy_node).
    - Если задан current_analyt — добавляет фильтр по аналитическому разрезу (AND).
    - Если задан next_analyt — данные группируются по этим колонкам (для следующего шага нарезки).
    - Результат оборачивается в DataRow через transform_data.

    Возвращает Res[List[DataRow]] — монаду с результатом или ошибкой.
    """

    lgr = get_logger()
    lgr.debug(f'Querying DAL for node id={node.id}, name={node.name}, '
              f'has_analyt={current_analyt is not None}, grp_columns={next_analyt}')

    _conditions = _get_query_select_conditions_for_hierarchy_node(cp, node)
    if current_analyt:
        _conditions = ConditionAnd([_conditions, current_analyt])
        _conditions = reduce_condition(_conditions)

    # Группировка по аналитическим колонкам (пусто → итоговая строка без группировки)
    _grp_by_columns = []
    if next_analyt and len(next_analyt) > 0:
        _grp_by_columns = next_analyt

    lgr.debug(f'DAL request: source={cp.source_params.source_name}, '
              f'grp_by={_grp_by_columns}, conditions={_conditions}')

    res = await data_access.get_aggr_data(
        source=cp.source_params.source_name,
        grp_by_columns=_grp_by_columns,
        aggr_columns=[cp.search_dev_params.fact_column, cp.search_dev_params.plan_column],
        conditions=_conditions
    )

    if not res.ok:
        lgr.error(f'DAL query failed for node id={node.id}: {res.err}')
    else:
        lgr.debug(f'DAL query returned {len(res.data)} row(s) for node id={node.id}')

    # Преобразуем сырые словари в типизированные DataRow
    resx = res.transform_data(lambda l: [DataRow.from_dict(x, cp.search_dev_params) for x in l])

    return resx


# ---------------------------------------------------------------------------
# Drill-down по иерархии показателей
# ---------------------------------------------------------------------------

async def make_hier_drill(current_drill_component:DrillComponent, deviation_calc_params:DeviationCalcParams, data_access_client:DataAccess, task_group:TaskGroup):
    """
    Разложение текущего показателя по компонентам иерархии.

    В зависимости от типа узла (MetricType) выбирает стратегию расчёта:
      - SUM:    сумма потомков → простое отклонение каждого
      - MULTI:  множитель × база → метод цепных подстановок
      - RATIO:  числитель / знаменатель → взвешенное влияние

    Каждый дочерний DrillComponent планируется в task_group для параллельного
    продолжения погружения через make_next_drill.

    Вложенные функции и замыкания:
      - _get_data_for_node(node) — локальный async-хелпер для загрузки данных
        одного узла. Замыкает deviation_calc_params, data_access_client,
        current_node_analytical_condition_set. Не использовать вне этого вызова.
      - _pos / _neg — лямбды для выделения положительной/отрицательной части
        вклада. Используются при подсчёте DeviationDetailAmts.
    """

    lgr = get_logger()
    current_node = current_drill_component.hier_ref

    lgr.info(f'make_hier_drill started for node id={current_node.id}, name={current_node.name}, type={current_node.type}')

    # Нет типа → нет погружения (лист без потомков)
    if current_node.type is None:
        lgr.debug(f'Node id={current_node.id} has no type — skipping drill-down')
        return

    # Если уже есть аналитическая нарезка — формируем из неё ConditionSet
    current_node_analytical_condition_set = None
    if current_drill_component.analyt_struct is not None and len(current_drill_component.analyt_struct.keys()) > 0:
        current_node_analytical_condition_set = ConditionSet(current_drill_component.analyt_struct)

    components: List[DataRow] = []
    factors:List[DataRow] = []
    deviation_detail_amts = DeviationDetailAmts()

    # --- Локальный хелпер: загрузка данных для одного узла ---
    async def _get_data_for_node(node:MetricNode)->DataRow:
        """Загружает агрегированные данные для node с учётом текущих аналитических условий.
        Замыкает: deviation_calc_params, data_access_client, current_node_analytical_condition_set.
        Добавляет ссылку на узел в dims['node'] для последующего извлечения."""
        lgr_node = get_logger()
        lgr_node.debug(f'Loading data for node id={node.id}, name={node.name}')
        val_res = await _query_data_from_data_access_layer(deviation_calc_params, data_access_client, node, current_node_analytical_condition_set)
        if not val_res.ok:
            lgr_node.error(f'Failed to retrieve data for node id={node.id}, name={node.name}: {val_res.err}')
            raise Exception(f'Could not retrieve data for node:{node}, err:{val_res.err}')
        val_row = val_res.data[0]
        val_row.dims['node'] = node
        lgr_node.debug(f'Data loaded for node id={node.id}: plan={val_row.plan}, fact={val_row.fact}')
        return val_row

    # Лямбды для выделения положительной / отрицательной составляющих вклада
    _pos = lambda x: x if x > 0 else 0
    _neg = lambda x: x if x < 0 else 0

    # ----- SUM: суммируемые компоненты -----
    if current_node.type == MetricType.SUM:
        lgr.info(f'Processing SUM decomposition for node id={current_node.id}, name={current_node.name}')
        # Загружаем данные по каждому прямому потомку
        for chld in deviation_calc_params.hier.get_children(current_node.id):
            val_row = await _get_data_for_node(chld)
            components.append(val_row)

        # Рассчитываем факторы (влияние каждого потомка на отклонение)
        (factors, deviation_detail_amts) = get_factors(components, deviation_calc_params.search_dev_params)

        lgr.debug(f'SUM factors calculated for node id={current_node.id}: {len(factors)} factors, '
                  f'positive_contrib={deviation_detail_amts.positive_contrib}, negative_contrib={deviation_detail_amts.negative_contrib}')

        drill = Drill(
            drill_type=EnumDrillType.HIER,
            detail_amts=deviation_detail_amts
        )

        current_drill_component.drills.append(drill)

        lgr.info(f'SUM drill created for node id={current_node.id}, scheduling {len(factors)} child tasks')

        # Создаём DrillComponent для каждого значимого фактора и планируем дальнейшее погружение
        for f in factors:
            chld_dc = DrillComponent(
                hier_ref=f.dims['node'],
                analyt_struct=current_drill_component.analyt_struct,
                parent=drill,
                amts=DeviationAmts.mk(f.plan, f.fact)
            )

            drill.components.append(chld_dc)
            task_group.create_task(make_next_drill(chld_dc, deviation_calc_params, data_access_client, task_group))

        return


    # ----- MULTI: компоненты-множители (метод цепных подстановок) -----
    if current_node.type == MetricType.MULTI:
        lgr.info(f'Processing MULTI decomposition for node id={current_node.id}, name={current_node.name}')
        # Показатель = RATE × BASE. Находим пару потомков по типу компонента.
        children = deviation_calc_params.hier.get_children(current_node.id)
        node_ratio = search_first_in_lst_or(children, lambda x:x.componentMultiPartType == ComponentMultiPartType.RATE)
        node_base = search_first_in_lst_or(children, lambda x:x.componentMultiPartType == ComponentMultiPartType.BASE)

        lgr.debug(f'MULTI children: ratio_node_id={node_ratio.id}, base_node_id={node_base.id}')

        # Данные по базе — загружаем из DAL
        base_data_row = await _get_data_for_node(node_base)

        # Значения множителя (ставки) вычисляем как частное: показатель / база
        ratio_data_row = DataRow(
            dims = {'node':node_base},
            plan =current_drill_component.amts.plan / base_data_row.plan,
            fact =current_drill_component.amts.fact / base_data_row.fact
        )

        lgr.debug(f'MULTI rate calculated: plan={ratio_data_row.plan:.6f}, fact={ratio_data_row.fact:.6f}; '
                  f'base: plan={base_data_row.plan}, fact={base_data_row.fact}')

        # Метод цепных подстановок: прямое влияние каждого фактора
        #   ratio_impact = (fact_rate × plan_base) - (plan_rate × plan_base)
        #   base_impact  = (plan_rate × fact_base) - (plan_rate × plan_base)
        ratio_impact_direct_calc = ratio_data_row.fact * base_data_row.plan - ratio_data_row.plan * base_data_row.plan
        base_impact_direct_calc = ratio_data_row.plan * base_data_row.fact - ratio_data_row.plan * base_data_row.plan
        total_impact = current_drill_component.amts.impact

        lgr.debug(f'MULTI direct impacts: ratio={ratio_impact_direct_calc}, base={base_impact_direct_calc}, total={total_impact}')

        # Пропорциональное распределение фактического отклонения между факторами
        ratio_weighted_impact = (ratio_impact_direct_calc / (ratio_impact_direct_calc + base_impact_direct_calc)) * total_impact
        base_weighted_impact = (base_impact_direct_calc / (ratio_impact_direct_calc + base_impact_direct_calc)) * total_impact

        lgr.debug(f'MULTI weighted impacts: ratio={ratio_weighted_impact}, base={base_weighted_impact}')

        ratio_deviation_amounts = DeviationAmts.mk_with_custom_impact(ratio_data_row.plan, ratio_data_row.fact, ratio_weighted_impact)
        base_deviation_amounts = DeviationAmts.mk_with_custom_impact(base_data_row.plan, base_data_row.fact, base_weighted_impact)

        deviation_detail_amts = DeviationDetailAmts(
            positive_contrib=_pos(ratio_weighted_impact) + _pos(base_weighted_impact),
            negative_contrib=_neg(ratio_weighted_impact) + _neg(base_weighted_impact)
        )

        drill = Drill(
            drill_type=EnumDrillType.HIER,
            detail_amts=deviation_detail_amts
        )

        current_drill_component.drills.append(drill)

        lgr.info(f'MULTI drill created for node id={current_node.id}, scheduling 2 child tasks (ratio + base)')

        # DrillComponent для множителя (ставки)
        ratio_drill_component = DrillComponent(
            hier_ref=node_ratio,
            analyt_struct=current_drill_component.analyt_struct,
            parent=drill,
            amts = ratio_deviation_amounts
        )
        drill.components.append(ratio_drill_component)
        task_group.create_task(make_next_drill(ratio_drill_component, deviation_calc_params, data_access_client, task_group))

        # DrillComponent для базы
        base_drill_component = DrillComponent(
            hier_ref=node_base,
            analyt_struct=current_drill_component.analyt_struct,
            parent=drill,
            amts=base_deviation_amounts
        )
        drill.components.append(base_drill_component)
        task_group.create_task(make_next_drill(base_drill_component, deviation_calc_params, data_access_client, task_group))

        return


    # ----- RATIO: показатель-отношение (числитель / знаменатель) -----
    # Может встречаться только на верхнем уровне иерархии.
    if current_node.type == MetricType.RATIO:
        lgr.info(f'Processing RATIO decomposition for node id={current_node.id}, name={current_node.name}')

        children = deviation_calc_params.hier.get_children(current_node.id)

        # Находим пару: числитель и знаменатель
        node_numerator:MetricNode = search_first_in_lst_or(children, lambda x:x.componentRatioPartType == ComponentRatioPartType.NUMERATOR)
        if node_numerator is None:
            lgr.error(f'Cannot find numerator for RATIO node id={current_node.id}')
            raise Exception(f'Possible corrupted metadata. Cant find numerator part of ratio indicator')

        node_denominator:MetricNode = search_first_in_lst_or(children, lambda x: x.componentRatioPartType == ComponentRatioPartType.DENOMINATOR)
        if node_denominator is None:
            lgr.error(f'Cannot find denominator for RATIO node id={current_node.id}')
            raise Exception(f'Possible corrupted metadata. Cant find denominator part of ratio indicator')

        lgr.debug(f'RATIO children: numerator_id={node_numerator.id}, denominator_id={node_denominator.id}')

        numerator_data_row = await _get_data_for_node(node_numerator)
        denominator_data_row = await _get_data_for_node(node_denominator)

        if denominator_data_row.plan == 0 or denominator_data_row.fact == 0:
            lgr.warning(f'Potential division by zero for RATIO node id={current_node.id}: '
                        f'denominator plan={denominator_data_row.plan}, fact={denominator_data_row.fact}')
            # TODO: обработка деления на ноль — требуется стратегия по умолчанию
            raise Exception(f'Possible divide on zero situation. {current_node}:{denominator_data_row}')

        # Значение ratio на верхнем уровне вычисляется тут, т.к. для его расчёта
        # нужны данные числителя и знаменателя, которых ещё нет на этапе create
        current_drill_component.amts = DeviationAmts.mk(numerator_data_row.plan/denominator_data_row.plan, numerator_data_row.fact/denominator_data_row.fact)

        lgr.debug(f'RATIO value calculated: plan={current_drill_component.amts.plan:.6f}, '
                  f'fact={current_drill_component.amts.fact:.6f}, impact={current_drill_component.amts.impact:.6f}')

        # Метод цепных подстановок для ratio:
        #   numerator_impact   = |num_fact/den_plan| - |num_plan/den_plan|
        #   denominator_impact = |num_plan/den_fact| - |num_plan/den_plan|
        numerator_impact_direct_calc = abs(numerator_data_row.fact/denominator_data_row.plan) - abs(numerator_data_row.plan/denominator_data_row.plan)
        denominator_impact_direct_calc = abs(numerator_data_row.plan/denominator_data_row.fact) - abs(numerator_data_row.plan/denominator_data_row.plan)

        lgr.debug(f'RATIO direct impacts: numerator={numerator_impact_direct_calc:.6f}, denominator={denominator_impact_direct_calc:.6f}')

        # Пропорциональное распределение итогового отклонения
        numerator_impact_weighted = numerator_impact_direct_calc * current_drill_component.amts.impact /(numerator_impact_direct_calc + denominator_impact_direct_calc)
        denominator_impact_weighted = denominator_impact_direct_calc * current_drill_component.amts.impact /(numerator_impact_direct_calc + denominator_impact_direct_calc)

        lgr.debug(f'RATIO weighted impacts: numerator={numerator_impact_weighted:.6f}, denominator={denominator_impact_weighted:.6f}')

        numerator_deviation_amounts = DeviationAmts.mk_with_custom_impact(numerator_data_row.plan, numerator_data_row.fact, numerator_impact_weighted)
        denominator_deviation_amounts = DeviationAmts.mk_with_custom_impact(denominator_data_row.plan, denominator_data_row.fact, denominator_impact_weighted)

        deviation_detail_amts = DeviationDetailAmts(
            positive_contrib=_pos(numerator_impact_weighted) + _pos(denominator_impact_weighted),
            negative_contrib=_neg(numerator_impact_weighted) + _neg(denominator_impact_weighted)
        )

        drill = Drill(
            drill_type=EnumDrillType.HIER,
            detail_amts=deviation_detail_amts
        )

        current_drill_component.drills.append(drill)

        lgr.info(f'RATIO drill created for node id={current_node.id}, scheduling 2 child tasks (numerator + denominator)')

        # DrillComponent для числителя
        numerator_drill_component = DrillComponent(
            hier_ref=node_numerator,
            analyt_struct=current_drill_component.analyt_struct,
            parent=drill,
            amts=numerator_deviation_amounts
        )
        drill.components.append(numerator_drill_component)
        task_group.create_task(make_next_drill(numerator_drill_component, deviation_calc_params, data_access_client, task_group))

        # DrillComponent для знаменателя
        denominator_drill_component = DrillComponent(
            hier_ref=node_denominator,
            analyt_struct=current_drill_component.analyt_struct,
            parent = drill,
            amts = denominator_deviation_amounts
        )
        drill.components.append(denominator_drill_component)
        task_group.create_task(make_next_drill(denominator_drill_component, deviation_calc_params, data_access_client, task_group))

        return


# ---------------------------------------------------------------------------
# Drill-down по аналитическим разрезам
# ---------------------------------------------------------------------------

async def make_analyt_drill(current_drill_component:DrillComponent, deviation_calc_params:DeviationCalcParams, data_access_client:DataAccess, task_group:TaskGroup):
    """
    Разложение текущего показателя по аналитическим разрезам.

    Запускает все алгоритмы (Algorithm), привязанные к узлу иерархии,
    параллельно через task_group. Каждый алгоритм — это упорядоченный набор
    шагов нарезки (drill_order), выполняемых последовательно.

    Вложенные функции:
      - _process_algorithm(alg) — фильтрует шаги алгоритма с учётом уже
        выполненных аналитических нарезок (из analyt_struct) и запускает
        первый шаг. Замыкает current_drill_component, task_group.

      - _process_algorithm_step(dc, steps_left) — рекурсивно обходит шаги
        алгоритма. На каждом шаге: запрашивает данные, группируя по колонкам
        текущего шага, определяет факторы, создаёт DrillComponent для каждого
        фактора. Если шаги закончились — передаёт управление в make_next_drill
        (переход к иерархии или другому drill-type). Иначе — рекурсия на
        следующий шаг. Замыкает deviation_calc_params, data_access_client.

    Рекомендации:
      - Не вызывать _process_algorithm_step напрямую — только через _process_algorithm.
      - При добавлении новых типов нарезки модифицировать логику перехода
        в блоке `if len(next_steps) == 0`.
    """

    async def _process_algorithm_step(_dc:DrillComponent, steps_left:List[List[str]]):
        """Один шаг алгоритма: запрашивает данные, группируя по current_step,
        создаёт DrillComponent для каждого фактора, планирует следующий шаг
        или переход к make_next_drill."""
        lgr_step = get_logger()
        if len(steps_left) == 0:
            print('yo')

        current_step, *next_steps = steps_left


        lgr_step.debug(f'Processing algorithm step: group_by={current_step}, '
                       f'remaining_steps={len(next_steps)}, node_id={_dc.hier_ref.id}')

        _as = _dc.analyt_struct
        cond_set = None if len(_as.keys()) == 0 else ConditionSet(_as)

        # Запрос с группировкой по колонкам текущего шага
        data_res = await _query_data_from_data_access_layer(
            deviation_calc_params, data_access_client, _dc.hier_ref, cond_set, current_step
        )

        if not data_res.ok:
            lgr_step.error(f'Data query failed at algorithm step {current_step}: {data_res.err}')
            raise Exception(data_res.err)

        data_set = data_res.data

        lgr_step.debug(f'Algorithm step {current_step} returned {len(data_set)} rows')

        (factors, dev_det_amts) = get_factors(data_set, deviation_calc_params.search_dev_params)

        lgr_step.debug(f'Algorithm step {current_step}: {len(factors)} factors, '
                       f'positive_contrib={dev_det_amts.positive_contrib}, negative_contrib={dev_det_amts.negative_contrib}')

        drill = Drill(
            drill_type=EnumDrillType.ANALYTICAL,
            detail_amts=dev_det_amts
        )

        _dc.drills.append(drill)

        for f in factors:
            # Наследуем текущие аналитические разрезы + добавляем новые из фактора
            new_analyt_struct = current_drill_component.analyt_struct.copy()
            new_analyt_struct.update(f.dims)

            chld_dc = DrillComponent(
                hier_ref=_dc.hier_ref,
                analyt_struct=new_analyt_struct,
                parent=drill,
                amts=DeviationAmts.mk(f.plan, f.fact)
            )

            drill.components.append(chld_dc)

            if len(next_steps) == 0:
                # Шаги закончились — переходим к следующему типу погружения
                task_group.create_task(make_next_drill(chld_dc, deviation_calc_params, data_access_client, task_group))
            else:
                # Есть ещё шаги — продолжаем аналитическую нарезку
                task_group.create_task(_process_algorithm_step(chld_dc, next_steps.copy()))

        lgr_step.info(f'Algorithm step {current_step} completed: {len(factors)} child components scheduled')


    async def _process_algorithm(alg:Algorithm, an_meta:AnalyticalStructureMetadata):
        """Подготавливает шаги алгоритма, исключая уже выполненные нарезки,
        и запускает первый шаг через _process_algorithm_step."""
        lgr_alg = get_logger()
        current_analytical_slices = current_drill_component.analyt_struct.keys()
        steps = []

        for step in alg.drill_order:
            # Сначала от кодов нужно перейти к столбцам
            step_columns = [an_meta.get_dimension(x).column for x in step]
            # Оставляем только те колонки шага, по которым ещё не нарезано
            new_step = [x for x in step_columns if x not in current_analytical_slices]
            if len(new_step) == 0: continue
            steps.append(new_step)

        lgr_alg.info(f'Starting algorithm with {len(steps)} filtered steps '
                     f'(original drill_order length={len(alg.drill_order)})')
        lgr_alg.debug(f'Algorithm steps: {steps}')

        task_group.create_task(_process_algorithm_step(current_drill_component, steps.copy()))


    lgr = get_logger()
    lgr.info(f'make_analyt_drill started for node id={current_drill_component.hier_ref.id}, '
             f'name={current_drill_component.hier_ref.name}')

    # Запускаем все алгоритмы параллельно
    alg_count = len(current_drill_component.hier_ref.analyt_metadata.algorithms)
    lgr.info(f'Scheduling {alg_count} algorithm(s) for node id={current_drill_component.hier_ref.id}')

    for a in current_drill_component.hier_ref.analyt_metadata.algorithms.values():
        task_group.create_task(_process_algorithm(a, current_drill_component.hier_ref.analyt_metadata))


# ---------------------------------------------------------------------------
# Маршрутизатор погружения
# ---------------------------------------------------------------------------

def check_need_analyt_drill(node:MetricNode, an_str:Dict[str,Any])->bool:
    anmet = node.analyt_metadata

    if not anmet: return False

    columns_already = set(an_str.keys())

    if len(columns_already) == 0: return True

    for a in anmet.algorithms.values():
        columns_to_drill = []
        for st in a.drill_order:
            for x in st:
                c = anmet.get_dimension(x).column
                columns_to_drill.append(c)
        if columns_already.issubset(columns_to_drill): return False

    return True



async def make_next_drill(dc:DrillComponent, cp:DeviationCalcParams, da:DataAccess, tg:TaskGroup):
    """
    Определяет тип следующего погружения для DrillComponent.

    Приоритет: если у узла есть метаданные аналитического разложения (analyt_metadata),
    сначала выполняем аналитическую нарезку. Иначе — погружение по иерархии.

    Таким образом, на каждом уровне дерева факторного анализа есть ровно одна
    активная ветка: либо analyt_drill, либо hier_drill — но не обе одновременно.
    """
    lgr = get_logger()
    node = dc.hier_ref



    if check_need_analyt_drill(node, dc.analyt_struct):
        lgr.info(f'Routing node id={node.id}, name={node.name} to analytical drill')
        tg.create_task(make_analyt_drill(dc, cp, da, tg))
        return


    if not node.is_leaf():
        lgr.info(f'Routing node id={node.id}, name={node.name} to hierarchy drill')
        tg.create_task(make_hier_drill(dc, cp, da, tg))
        return


# ---------------------------------------------------------------------------
# Главная точка входа модуля
# ---------------------------------------------------------------------------

async def calculate_deviations(
        deviation_calc_params:DeviationCalcParams,
        data_access: DataAccess
    ) -> DrillComponent:
    """
    Главная точка входа факторного анализа отклонений.

    1. Определяет корневой узел иерархии.
    2. Для RATIO — создаёт DrillComponent без amts (они вычислятся при погружении).
       Для остальных — загружает данные корневого узла сразу.
    3. Запускает рекурсивный drill-down через TaskGroup (все уровни параллельно).
    4. Возвращает DrillComponent — корень дерева результатов факторного анализа.

    Вложенная функция __get_data_shortcut:
      - Локальный прокси для _query_data_from_data_access_layer с предзаполненными
        deviation_calc_params и data_access. Замыкает эти параметры.
      - Используется только для загрузки данных корневого узла. Не вызывать извне.

    Важно: TaskGroup гарантирует, что при выходе из async with все задачи завершены.
    """

    lgr = get_logger()
    lgr.info('calculate_deviations started')

    hier_root = deviation_calc_params.hier.get_root()
    lgr.debug(f'Root node: id={hier_root.id}, name={hier_root.name}, type={hier_root.type}')

    # --- Локальный прокси для запроса данных (замыкает deviation_calc_params, data_access) ---
    async def __get_data_shortcut(
            _node:MetricNode,
            current_analyt_conditions: ConditionSet = None,
            next_analyt_slices:List[str] = None
    ):
        return await _query_data_from_data_access_layer(
            deviation_calc_params,
            data_access,
            _node,
            current_analyt_conditions,
            next_analyt_slices
        )

    # --- Формируем корневой DrillComponent ---
    if hier_root.type == MetricType.RATIO:
        # Для RATIO amts вычисляется позже — при погружении (make_hier_drill → RATIO-ветка)
        lgr.info(f'Root node is RATIO type — amts will be calculated during drill-down')
        top_lvl_component = DrillComponent(
            hier_ref=hier_root
        )
    else:
        # Для SUM/MULTI — загружаем данные корневого узла сразу
        lgr.info(f'Root node is {hier_root.type} type — loading root data')
        top_lvl_res = await __get_data_shortcut(hier_root)

        if not top_lvl_res.ok:
            lgr.error(f'Failed to load root node data: {top_lvl_res.err}')
            raise Exception(top_lvl_res.err)

        top_lvl_data:DataRow = top_lvl_res.data[0]

        lgr.debug(f'Root data loaded: plan={top_lvl_data.plan}, fact={top_lvl_data.fact}')

        top_lvl_component = DrillComponent(
            hier_ref = hier_root,
            amts = DeviationAmts.mk(plan=top_lvl_data.plan, fact=top_lvl_data.fact)
        )

    lgr.info(f'Starting recursive drill-down from root node id={hier_root.id}')

    # Запускаем рекурсивный drill-down; TaskGroup дождётся всех потомков
    async with asyncio.TaskGroup() as task_group:
        task_group.create_task(make_next_drill(top_lvl_component, deviation_calc_params, data_access, task_group))

    lgr.info(f'calculate_deviations completed for root node id={hier_root.id}')
    return top_lvl_component
