import datetime
from asyncio import TaskGroup
from datetime import date

from adhoc.template_lite.deserializer import get_from_template_lite_json
from adhoc.template_lite.transform import transform_template_lite_to_hierarchy
from adhoc.template_lite.transform_queries import calculate_query_prop, calculate_query_prop_v2
from adhoc.template_lite.transform_analytical_structs import transform_analytical_structs
from libfa2.hier_metadata import Query
from libfa2.fa_impl.deviation_calc_metadata import DeviationCalcMetadata, SearchDevParameters, SourceParameters
from libfa2.hier_metadata.hierarchy import Hierarchy, MetricNode, MultipartDecompositionType, MetricType
from libfa2.data_access.conditions import ConditionBase, ConditionSet, ConditionOr, ConditionAnd, reduce_condition
from functools import reduce

from sdk.tools.settings import FileTools
from sdk.core.logging import get_logger
from sdk.tools.settings import env__init_keydb_instance

from coredis import Redis
from typing import Tuple,List,Dict




import logging
logging.basicConfig(
    level=logging.INFO,
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

#
# async def make_and_save_metadata(
#         code:str,
#         table_name:str = 'missa_bidr.v_aimis__usl_facts_exp',
#         rep_dt_column_name:str = 'dt',
#         plan_val_column_name:str = 'val_plan',
#         fact_val_column_name:str = 'val_fact',
#         sign_neg:int = -1
#     ):
#     from sdk.tools.settings import env__init_keydb_instance
#     from sdk.fa2026.client import FaClient
#     from libfa2.fa_impl.deviation_calc_metadata import DeviationCalcMetadata, SourceParameters, SearchDevParameters
#
#     kc = await env__init_keydb_instance()
#     fac = FaClient(kc)
#
#     h = make_hier(code)
#
#     meta = DeviationCalcMetadata(
#         code,
#         SourceParameters(
#             table_name,
#             rep_dt_column_name
#         ),
#         SearchDevParameters(
#             plan_val_column_name,
#             fact_val_column_name,
#             sign_neg
#         ),
#         [h,]
#     )
#
#     meta_json = meta.to_json()
#
#     await fac.save_metadata(code, meta_json)



def bubble_and_reduce_query_to_top(h:Hierarchy):
    root = h.get_root()

    def _visit_node(node:MetricNode)->ConditionBase|None:
        if node.type == MetricType.MULTI or node.is_leaf():
            cond = ConditionSet.from_dict(
                node.query.to_dict()
            )
            return cond


        if node.type == MetricType.SUM:
            conds = []
            for n in h.get_children(node.id):
                cond = _visit_node(n)
                if cond is None:
                    raise Exception(f'EMPTY COND!!!! for node {n}')
                conds.append(cond)

            if len(conds) == 0:
                return None

            if len(conds) == 1:
                return conds[0]

            cond = ConditionOr(conds)
            return cond

        return None

    total_cond = _visit_node(root)
    total_cond = reduce_condition(total_cond)
    return total_cond.to_dict()





async def setup_od_pao(kc:Redis):
    from sdk.tools.settings import env__init_keydb_instance
    from sdk.fa2026.client import FaClient

    h1 = make_hier('odpao1')
    h2 = make_hier('odpao2')

    total_cond = bubble_and_reduce_query_to_top(h2)
    root_h1 = h1.get_root()
    root_h1.query = Query(total_cond)

    hier_lst = [
        h1, h2
    ]

    meta = DeviationCalcMetadata(
        'odpao',
        SourceParameters(
            'missa_bidr.v_aimis__usl_facts_exp',
            'dt'
        ),
        SearchDevParameters(
            'val_plan',
            'val_fact',
            -1
        ),
        hier_lst
    )

    meta_json = meta.to_json()

    fac = FaClient(kc)

    await fac.delete_metadata('odpao')
    await fac.save_metadata('odpao', meta_json)
    await kc.connection_pool.disconnect()



async def calc_od_pao(kc:Redis):
    code = 'odpao'

    from sdk.fa2026.client import FaClient
    fac = FaClient(kc)
    dt= date(2026,4,30)
    await fac.delete_results(code,dt)
    res = await fac.get_summary(code, dt)
    print(res)


TB_SETUP = {
    'sib':'Сибирский банк',
    'bb':'Байкальский банк',
    'ura':'Уральский банк',
    'vv':'Волго-Вятский банк',
    'sthwst':'Юго-Западный банк',
    'cenblk':'Центрально-Черноземный банк',
    'midrus':'Среднерусский банк',
    'fareast':'Дальневосточный банк',
    'nrthwst':'Северо-Западный банк',
    'pov':'Поволжский банк',
    'msk':'Московский банк',
}

async def setup_od_tb(kc:Redis):


    from sdk.fa2026.client import FaClient

    h1 = make_hier('odtb1')
    h2 = make_hier('odtb2')

    total_cond = bubble_and_reduce_query_to_top(h2)
    root_h1 = h1.get_root()
    root_h1.query = Query(total_cond)



    for (tb_code, tbname) in TB_SETUP.items():
        hc1 = Hierarchy.from_json(h1.to_json())
        hc2 = Hierarchy.from_json(h2.to_json())

        r1 = hc1.get_root()
        r1.name = f'{r1.name} ({tbname})'

        r2 = hc2.get_root()
        r2.name = f'{r2.name} ({tbname})'

        for n in hc1.nodes.values():
            if n.query:
                dic = {}
                dic.update(n.query.to_dict())
                dic.update({
                    'tb': tbname
                })
                n.query = Query(dic)

        for n in hc2.nodes.values():
            if n.query:
                dic = {}
                dic.update(n.query.to_dict())
                dic.update({
                    'tb': tbname
                })
                n.query = Query(dic)

        hier_lst = [
            hc1, hc2
        ]

        code = f'odtb_{tb_code}'

        meta = DeviationCalcMetadata(
            code,
            SourceParameters(
                'missa_bidr.v_aimis__usl_facts_exp',
                'dt'
            ),
            SearchDevParameters(
                'val_plan',
                'val_fact',
                -1
            ),
            hier_lst
        )

        meta_json = meta.to_json()

        fac = FaClient(kc)

        await fac.delete_metadata(code)
        await fac.save_metadata(code, meta_json)








async def calc_od_tb(kc:Redis):
    from sdk.tools.settings import env__init_keydb_instance
    from sdk.fa2026.client import FaClient

    for tbcode in TB_SETUP.keys():
        code = f'odtb_{tbcode}'

        fac = FaClient(kc)
        dt= date(2026,4,30)
        await fac.delete_results(code,dt)
        res = await fac.get_summary(code, dt)
        print(res)






async def setup_tbgosb_pao(prefix:str, kc:Redis):

    from sdk.fa2026.client import FaClient


    code = f'{prefix}pao'

    h1 = make_hier(f'{code}1')
    h2 = make_hier(f'{code}2')

    total_cond = bubble_and_reduce_query_to_top(h2)
    root_h1 = h1.get_root()
    root_h1.query = Query(total_cond)

    hier_lst = [
        h1, h2
    ]

    meta = DeviationCalcMetadata(
        code,
        SourceParameters(
            'missa_bidr.v_aimis__usl_facts_exp',
            'dt'
        ),
        SearchDevParameters(
            'val_plan',
            'val_fact',
            -1
        ),
        hier_lst
    )

    meta_json = meta.to_json()

    fac = FaClient(kc)

    await fac.delete_metadata(code)
    await fac.save_metadata(code, meta_json)




async def calc_tbgosb_pao(prefix:str, dt:date, kc:Redis):

    from sdk.fa2026.client import FaClient

    code = f'{prefix}pao'

    fac = FaClient(kc)

    await fac.delete_results(code, dt)
    res = await fac.get_summary(code, dt)
    print(res)




"""
    ###################################################################################
        Разбор json-ов посвященных ТБ
    ###################################################################################
"""
def build_hierarchies_based_on_source_jsons(prefix:str)->Tuple[Dict,Dict]:
    code_pref = f'{prefix}tb'

    h1 = make_hier(f'{code_pref}1')
    h2 = make_hier(f'{code_pref}2')

    total_cond = bubble_and_reduce_query_to_top(h2)
    root_h1 = h1.get_root()
    root_h1.query = Query(total_cond)

    return (h1.to_json(), h2.to_json())


async def setup_and_save_for_one_tb(prefix:str, kc:Redis, h1json:Dict, h2json:Dict, tb_code:str, tbname:str):
    from sdk.fa2026.client import FaClient

    code_pref = f'{prefix}tb'

    hc1 = Hierarchy.from_json(h1json)
    hc2 = Hierarchy.from_json(h2json)

    r1 = hc1.get_root()
    r1.name = f'{r1.name} ({tbname})'

    r2 = hc2.get_root()
    r2.name = f'{r2.name} ({tbname})'

    for n in hc1.nodes.values():
        if n.query:
            dic = {}
            dic.update(n.query.to_dict())
            dic.update({
                'tb': tbname
            })
            n.query = Query(dic)

    for n in hc2.nodes.values():
        if n.query:
            dic = {}
            dic.update(n.query.to_dict())
            dic.update({
                'tb': tbname
            })
            n.query = Query(dic)

    hier_lst = [
        hc1, hc2
    ]

    code = f'{code_pref}_{tb_code}'

    meta = DeviationCalcMetadata(
        code,
        SourceParameters(
            'missa_bidr.v_aimis__usl_facts_exp',
            'dt'
        ),
        SearchDevParameters(
            'val_plan',
            'val_fact',
            -1
        ),
        hier_lst
    )

    meta_json = meta.to_json()

    fac = FaClient(kc)

    await fac.delete_metadata(code)
    await fac.save_metadata(code, meta_json)


async def setup_tbgosb_tb(prefix:str, kc:Redis, tg:TaskGroup):
    (h1_json, h2_json) = build_hierarchies_based_on_source_jsons(prefix)
    for (tb_code, tbname) in TB_SETUP.items():
        await setup_and_save_for_one_tb(prefix, kc, h1_json, h2_json, tb_code, tbname)




async def calc_tbgosb_onetb(prefix:str, dt:date, kc:Redis, tbcode:str):
    from sdk.fa2026.client import FaClient

    code = f'{prefix}tb_{tbcode}'

    fac = FaClient(kc)
    await fac.delete_results(code,dt)
    res = await fac.get_summary(code, dt)
    print(res)






def main():
    dt = date(2026, 4, 30)

    all_prefixes = [
        'od',
        'rez',
        'operpl',
        'opex',
        'chkd',
        'chpda',
        'chpdp'
    ]
    # prefix = 'operpl'

    import asyncio




    async def run():
        import asyncio

        kc = env__init_keydb_instance()

        for prefix in all_prefixes:
            # async def _run():
            #     try:
            #         await setup_tbgosb_pao(prefix, kc)
            #         await asyncio.sleep(0.1)
            #         await calc_tbgosb_pao(prefix, dt, kc)
            #     except:
            #         print(f'SOME ERR {prefix} PAO')
            #
            # await _run()


            (h1_json, h2_json) = build_hierarchies_based_on_source_jsons(prefix)
            for (tb_code, tbname) in TB_SETUP.items():
                await setup_and_save_for_one_tb(prefix, kc, h1_json, h2_json, tb_code, tbname)
                await calc_tbgosb_onetb(prefix, dt, kc, tb_code)


            await asyncio.sleep(0.1)





        # for prefix in all_prefixes:
        #     print(f'Processing prefix {prefix}')
        #     await setup_tbgosb_pao(prefix, kc)
        #     await calc_tbgosb_pao(prefix, dt, kc)
        #     await setup_tbgosb_tb(prefix, kc)
        #     await calc_tbgosb_tb(prefix, dt, kc)

    asyncio.run(run())


    # code = 'opextb'
    # # asyncio.run(make_and_save_metadata(code))
    #
    # h1 = make_hier('odpao1')
    # h2 = make_hier('odpao2')
    #
    # t1 = mk_custom_tree(h1)
    # t2 = mk_custom_tree(h2)
    #
    # total_cond = bubble_and_reduce_query_to_top(h2)
    #
    # root_h1 = h1.get_root()
    # root_h1.query = Query(total_cond)
    #
    # # now we need to bubble and reduce query from t2 to top
    #
    #
    #
    #
    # print(t2)



if __name__ == '__main__':
    main()
