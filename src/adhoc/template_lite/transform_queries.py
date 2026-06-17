from libfa2.hier_metadata import MetricType
from libfa2.hier_metadata.hierarchy import Hierarchy, MetricNode
from .grp_map import find_parts_by_name, split_custom_name
from .pl_map_setup import find_node_address_by_name, find_node_address_by_fin_code

from sdk.core.logging import get_logger




def calculate_and_set_query_prop(node:MetricNode):
    lgr = get_logger()

    nm = node.name
    if '(***)' in nm:
        # ищем в рассшифровке, там может быть одно минус другое
        parts = find_parts_by_name(nm)
        if len(parts) == 0:
            node.query = {'BAD_FIELD':''}
            return

        include_lst = []
        exclude_lst = []
        for (node_full_name, sign) in parts:
            (node_fin_code, node_name) = split_custom_name(node_full_name)
            node_code_lst = find_node_address_by_fin_code(node_fin_code)
            if node_code_lst is None:
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
                print(f'ERROR: elem {x} not in include_lst')
                node.query = {'BAD_FIELD': ''}
                return

        diff_lst = [x for x in include_lst if x not in exclude_lst]

        node.query = {'node_code': diff_lst}
        return


    # we have direct name
    node_code_lst = find_node_address_by_name(nm)
    if node_code_lst is None:
        node.query = {'BAD_FIELD': ''}
        return

    node.query = {'node_code': node_code_lst}
    return





def transform_next_step(hier:Hierarchy) -> Hierarchy:

    root = hier.get_root()


    def process_node(n:MetricNode):
        if n.type == MetricType.MULTI:
            calculate_and_set_query_prop(n)

        children = hier.get_children(n.id)

        if len(children) == 0:
            calculate_and_set_query_prop(n)

        for chld in children:
            process_node(chld)


    process_node(root)

    return hier