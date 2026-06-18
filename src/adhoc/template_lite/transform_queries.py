from libfa2.hier_metadata import MetricType
from libfa2.hier_metadata.hierarchy import Hierarchy, MetricNode
from .grp_map import find_parts_by_name, split_custom_name
from .pl_map_setup import find_node_address_by_name, find_node_address_by_fin_code

from sdk.core.logging import get_logger




def calculate_and_set_query_prop(node:MetricNode):
    lgr = get_logger()

    nm = node.name
    lgr.debug(f'Расчёт query для узла id={node.id} name={nm!r}')

    if '(***)' in nm:
        # ищем в рассшифровке, там может быть одно минус другое
        lgr.info(f'Имя содержит "(***)": ищем составные части по grp-карте ({nm!r})')
        parts = find_parts_by_name(nm)
        if len(parts) == 0:
            lgr.warning(f'Составные части для имени {nm!r} не найдены в grp-карте — query=BAD_FIELD')
            node.query = {'BAD_FIELD':''}
            return

        include_lst = []
        exclude_lst = []
        for (node_full_name, sign) in parts:
            (node_fin_code, node_name) = split_custom_name(node_full_name)
            lgr.debug(f'Часть {node_full_name!r} -> fin_code={node_fin_code!r} name={node_name!r} sign={sign}')
            node_code_lst = find_node_address_by_fin_code(node_fin_code)
            if node_code_lst is None:
                lgr.warning(
                    f'Адрес узла по fin_code={node_fin_code!r} не найден в pl-карте — query=BAD_FIELD'
                )
                node.query = {'BAD_FIELD': ''}
                return

            if sign > 0:
                include_lst.extend(node_code_lst)
            else:
                exclude_lst.extend(node_code_lst)

        # now we have to find disunction of two lsts

        # check all exclude lst in include
        for x in exclude_lst:
            if not x in include_lst:
                lgr.warning(
                    f'Элемент {x} из exclude_lst отсутствует в include_lst — query=BAD_FIELD'
                )
                node.query = {'BAD_FIELD': ''}
                return

        diff_lst = [x for x in include_lst if x not in exclude_lst]
        lgr.debug(
            f'Разность списков: include={len(include_lst)} exclude={len(exclude_lst)} -> {len(diff_lst)} кодов'
        )

        node.query = {'node_code': diff_lst}
        return


    # we have direct name
    lgr.info(f'Прямое имя: ищем адрес по pl-карте ({nm!r})')
    node_code_lst = find_node_address_by_name(nm)
    if node_code_lst is None:
        lgr.warning(f'Адрес узла по имени {nm!r} не найден в pl-карте — query=BAD_FIELD')
        node.query = {'BAD_FIELD': ''}
        return

    node.query = {'node_code': node_code_lst}
    return




def transform_next_step(hier:Hierarchy) -> Hierarchy:
    lgr = get_logger()

    root = hier.get_root()
    lgr.info(
        f'Старт transform_next_step: корень id={root.id if root else None} '
        f'name={root.name if root else None!r}'
    )

    def process_node(n:MetricNode):
        plgr = get_logger()

        if n.type == MetricType.MULTI:
            plgr.debug(f'Узел id={n.id} MULTI — расчёт query')
            calculate_and_set_query_prop(n)

        children = hier.get_children(n.id)

        if len(children) == 0:
            plgr.debug(f'Узел id={n.id} листовой — расчёт query')
            calculate_and_set_query_prop(n)

        for chld in children:
            process_node(chld)


    process_node(root)

    lgr.info('transform_next_step завершён')
    return hier
