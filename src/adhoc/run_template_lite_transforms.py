
from adhoc.template_lite.deserializer import get_from_template_lite_json
from adhoc.template_lite.transform import transform_template_lite_to_hierarchy
from adhoc.template_lite.transform_queries import calculate_query_prop, calculate_query_prop_v2
from adhoc.template_lite.transform_analytical_structs import transform_analytical_structs
from libfa2.hier_metadata.hierarchy import Hierarchy, MetricNode

from sdk.tools.settings import FileTools
from sdk.core.logging import get_logger

import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] {%(pathname)s:%(lineno)d} %(name)s %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)


class YoTreeNode:
    def __init__(self, payload):
        self.payload = payload
        self.children = []
        self.parent = None

    def add_child(self, child:'YoTreeNode'):
        if child in self.children: return
        child.parent = self
        self.children.append(child)

    @property
    def is_root(self)->bool:
        return self.parent is None

    @property
    def is_leaf(self)->bool:
        return len(self.children) == 0

    def __str__(self):
        return f'@ {str(self.payload)} @'




def mk_custom_tree(hier:Hierarchy):
    def _process_tree_node(node: YoTreeNode):
        mnode = node.payload
        if mnode.query:
            print(f'query:{mnode.query} for node {mnode}')
        for mchld in hier.get_children(mnode.id):
            chld = YoTreeNode(mchld)
            node.add_child(chld)
            _process_tree_node(chld)

    root = hier.get_root()
    _tree_root = YoTreeNode(root)
    _process_tree_node(_tree_root)
    return _tree_root




def make_hier(code:str)->Hierarchy:
    lgr = get_logger()

    path = FileTools.path_concat(
        FileTools.home_path(),
        'source', 'repos', 'aimis2-core-fa-refac',
        'src', 'tmp', 'template_lite',
        f'{code}.json'
    )
    lgr.info(f'Запуск преобразования template_lite. Файл-источник: {path}')

    try:
        lgr.debug('Шаг 1/4: десериализация template_lite из JSON')
        data = get_from_template_lite_json(path)
        lgr.info(
            f'Шаг 1/4 завершён: получен TemplateLite '
            f'(metric_name={data.metric_name!r}, узлов={data.count_nodes()})'
        )

        lgr.debug('Шаг 2/4: преобразование TemplateLite -> Hierarchy')
        next_data = transform_template_lite_to_hierarchy(data)
        lgr.info(
            f'Шаг 2/4 завершён: построена Hierarchy '
            f'(узлов={len(next_data.nodes)})'
        )

        lgr.debug('Шаг 3/4: расчёт query-свойств узлов (transform_next_step)')
        next_data:Hierarchy = calculate_query_prop_v2(next_data)
        lgr.info('Шаг 3/4 завершён: query-свойства расставлены')


        lgr.debug('Шаг 4/4: трансформация аналитических метаданных')
        h:Hierarchy = transform_analytical_structs(next_data)
        lgr.info('Шаг 4/4 завершён: новые analyt metadata')


        lgr.info('Преобразование template_lite успешно завершено')

        return h
    except Exception:
        lgr.exception('Ошибка при выполнении преобразования template_lite')
        raise


async def make_and_save_metadata(
        code:str,
        table_name:str = 'missa_bidr.v_aimis__usl_facts_exp',
        rep_dt_column_name:str = 'dt',
        plan_val_column_name:str = 'val_plan',
        fact_val_column_name:str = 'val_fact',
        sign_neg:int = -1
    ):
    from sdk.tools.settings import env__init_keydb_instance
    from sdk.fa2026.client import FaClient
    from libfa2.fa_impl.deviation_calc_metadata import DeviationCalcMetadata, SourceParameters, SearchDevParameters

    kc = await env__init_keydb_instance()
    fac = FaClient(kc)

    h = make_hier(code)

    meta = DeviationCalcMetadata(
        code,
        SourceParameters(
            table_name,
            rep_dt_column_name
        ),
        SearchDevParameters(
            plan_val_column_name,
            fact_val_column_name,
            sign_neg
        ),
        [h,]
    )

    meta_json = meta.to_json()

    await fac.save_metadata(code, meta_json)




def setup_od_pao()


def main():
    import asyncio
    code = 'opextb'
    # asyncio.run(make_and_save_metadata(code))

    h1 = make_hier('odpao1')
    h2 = make_hier('odpao2')

    t1 = mk_custom_tree(h1)
    t2 = mk_custom_tree(h2)
    print(h)



if __name__ == '__main__':
    main()
