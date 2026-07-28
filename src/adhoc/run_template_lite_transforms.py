import datetime
from asyncio import TaskGroup
from datetime import date
from lib2to3.fixes.fix_print import parend_expr

from wrapt import with_signature

from adhoc.template_lite.deserializer import get_from_template_lite_json
from adhoc.template_lite.transform import transform_template_lite_to_hierarchy
from adhoc.template_lite.transform_queries import calculate_query_prop, calculate_query_prop_v2
from adhoc.template_lite.split_to_motivation_corr import split_to_motiv_adj
from adhoc.template_lite.transform_analytical_structs import transform_analytical_structs
from libfa2.analyt_struct_metadata import Algorithm
from libfa2.hier_metadata import Query
from libfa2.fa_impl.deviation_calc_metadata import DeviationCalcMetadata, SearchDevParameters, SourceParameters
from libfa2.hier_metadata.hierarchy import Hierarchy, MetricNode, MultipartDecompositionType, MetricType
from libfa2.data_access.conditions import ConditionBase, ConditionSet, ConditionOr, ConditionAnd, reduce_condition
from functools import reduce

from sdk.tools.settings import FileTools
from sdk.core.logging import get_logger
from sdk.tools.settings import env__init_keydb_instance
from sdk.fa2026.client import FaClient

from coredis import Redis as KeyDBClient
from typing import Tuple,List,Dict, Iterable




import logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] {%(pathname)s:%(lineno)d} %(name)s %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)


TABLE_NAME_USL_FACTS = 'missa_bidr.v_aimis__usl_facts_exp'


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

TB_GOSB_SETUP = (
    ('Байкальский банк', 'Аппарат ББ'),
    ('Байкальский банк', 'Бурятское отделение №8601'),
    ('Байкальский банк', 'Иркутское отделение №8586'),
    ('Байкальский банк', 'Читинское отделение №8600'),
    ('Байкальский банк', 'Якутское отделение №8603'),
    ('Волго-Вятский банк', 'Аппарат ВВБ'),
    ('Волго-Вятский банк', 'Банк Татарстан отделение №8610'),
    ('Волго-Вятский банк', 'Владимирское отделение №8611'),
    ('Волго-Вятский банк', 'Кировское отделение №8612'),
    ('Волго-Вятский банк', 'Марий Эл отделение №8614'),
    ('Волго-Вятский банк', 'Мордовское отделение №8589'),
    ('Волго-Вятский банк', 'Нижегородское отделение №9042'),
    ('Волго-Вятский банк', 'Пермское отделение №6984'),
    ('Волго-Вятский банк', 'Удмуртское отделение №8618'),
    ('Волго-Вятский банк', 'Чувашское отделение №8613'),
    ('Дальневосточный банк', 'Аппарат ДВБ'),
    ('Дальневосточный банк', 'Биробиджанское отделение №4157'),
    ('Дальневосточный банк', 'Благовещенское отделение №8636'),
    ('Дальневосточный банк', 'Головное отделение №9070'),
    ('Дальневосточный банк', 'Камчатское отделение №8556'),
    ('Дальневосточный банк', 'Приморское отделение №8635'),
    ('Дальневосточный банк', 'Северо-Восточное отделение №8645'),
    ('Дальневосточный банк', 'Чукотское отделение №1009'),
    ('Дальневосточный банк', 'Южно-Сахалинское отделение №8567'),
    ('Московский банк', 'Аппарат МБ'),
    ('Московский банк', 'Головное отделение Московский банк'),
    ('Поволжский банк', 'Аппарат ПВБ'),
    ('Поволжский банк', 'Астраханское отделение №8625'),
    ('Поволжский банк', 'Волгоградское отделение №8621'),
    ('Поволжский банк', 'Оренбургское отделение №8623'),
    ('Поволжский банк', 'Пензенское отделение №8624'),
    ('Поволжский банк', 'Самарское отделение №6991'),
    ('Поволжский банк', 'Саратовское отделение №8622'),
    ('Поволжский банк', 'Ульяновское отделение №8588'),
    ('Северо-Западный банк', 'Аппарат СЗБ'),
    ('Северо-Западный банк', 'Архангельское отделение №8637'),
    ('Северо-Западный банк', 'Вологодское отделение №8638'),
    ('Северо-Западный банк', 'Головное отделение №9055'),
    ('Северо-Западный банк', 'Головное отделение №9056'),
    ('Северо-Западный банк', 'Калининградское отделение №8626'),
    ('Северо-Западный банк', 'Карельское отделение №8628'),
    ('Северо-Западный банк', 'Коми отделение №8617'),
    ('Северо-Западный банк', 'Мурманское отделение №8627'),
    ('Северо-Западный банк', 'Новгородское отделение №8629'),
    ('Северо-Западный банк', 'Псковское отделение №8630'),
    ('Сибирский банк', 'Абаканское отделение №8602'),
    ('Сибирский банк', 'Алтайское отделение №8644'),
    ('Сибирский банк', 'Аппарат Сиб'),
    ('Сибирский банк', 'Кемеровское отделение №8615'),
    ('Сибирский банк', 'Красноярское отделение №8646'),
    ('Сибирский банк', 'Кызылское отделение №8591'),
    ('Сибирский банк', 'Новосибирское отделение №8047'),
    ('Сибирский банк', 'Омское отделение №8634'),
    ('Сибирский банк', 'Томское отделение №8616'),
    ('Среднерусский банк', 'Аппарат СРБ'),
    ('Среднерусский банк', 'Брянское отделение №8605'),
    ('Среднерусский банк', 'Восточное Головное отделение №1023'),
    ('Среднерусский банк', 'Западное Головное отделение №1025'),
    ('Среднерусский банк', 'Ивановское отделение №8639'),
    ('Среднерусский банк', 'Калужское отделение №8608'),
    ('Среднерусский банк', 'Костромское отделение №8640'),
    ('Среднерусский банк', 'Рязанское отделение №8606'),
    ('Среднерусский банк', 'Северное Головное отделение №1026'),
    ('Среднерусский банк', 'Смоленское отделение №8609'),
    ('Среднерусский банк', 'Тверское отделение №8607'),
    ('Среднерусский банк', 'Тульское отделение №8604'),
    ('Среднерусский банк', 'Южное Головное отделение №1024'),
    ('Среднерусский банк', 'Ярославское отделение №17'),
    ('Уральский банк', 'Аппарат УБ'),
    ('Уральский банк', 'Башкирское отделение №8598'),
    ('Уральский банк', 'Западно-Сибирское отделение №8647'),
    ('Уральский банк', 'Курганское отделение №8599'),
    ('Уральский банк', 'Свердловское отделение №7003'),
    ('Уральский банк', 'Челябинское отделение №8597'),
    ('Уральский банк', 'Югорское отделение №5940'),
    ('Уральский банк', 'Ямало-Ненецкое отделение №8369'),
    ('Центрально-Черноземный банк', 'Аппарат ЦЧБ'),
    ('Центрально-Черноземный банк', 'Белгородское отделение №8592'),
    ('Центрально-Черноземный банк', 'Воронежское отделение №9013'),
    ('Центрально-Черноземный банк', 'Курское отделение №8596'),
    ('Центрально-Черноземный банк', 'Липецкое отделение №8593'),
    ('Центрально-Черноземный банк', 'Луганское отделение №9014'),
    ('Центрально-Черноземный банк', 'Орловское отделение №8595'),
    ('Центрально-Черноземный банк', 'Тамбовское отделение №8594'),
    ('Юго-Западный банк', 'Адыгейское отделение №8620'),
    ('Юго-Западный банк', 'Аппарат ЮЗБ'),
    ('Юго-Западный банк', 'Дагестанское отделение №8590'),
    ('Юго-Западный банк', 'Донецкое отделение №9053'),
    ('Юго-Западный банк', 'Ингушское отделение №8633'),
    ('Юго-Западный банк', 'Кабардино-Балкарское отделение №8631'),
    ('Юго-Западный банк', 'Калмыцкое отделение №8579'),
    ('Юго-Западный банк', 'Карачаево-Черкесское отделение №8585'),
    ('Юго-Западный банк', 'Краснодарское отделение №8619'),
    ('Юго-Западный банк', 'Крымское отделение №9052'),
    ('Юго-Западный банк', 'Ростовское отделение №5221'),
    ('Юго-Западный банк', 'Северо-Осетинское отделение №8632'),
    ('Юго-Западный банк', 'Ставропольское отделение №5230'),
    ('Юго-Западный банк', 'Чеченское отделение №8643'),
)


BB_SETUP = (
    ("КИБ (Все)", "КИБ - Прочие", "КИБ СОП", "КСБ", "Гос. Сектор", "ММБ", "Машиностроение",),
    ("КСБ",),
    ("Гос. Сектор",),
    ("Машиностроение",),
    ("ММБ",),
    ("B2C", "БСП",),
)


"""
    ###################################################################################
        Универсальная функция разбора
    ###################################################################################
"""
def build_universal_metadata_hierarchy(code:str, biz_block_lst:List[str] = None, tb:str = None, gosb:str = None) -> DeviationCalcMetadata:

    file_name_prefix = 'pao' if tb is None else 'tb'
    file_name_prefix = f'{code}{file_name_prefix}'

    h2 = make_hier(f'{file_name_prefix}2')

    if gosb is None:
        h1 = make_hier(f'{file_name_prefix}1')
        hiers = [h1, h2]

        q = bubble_and_reduce_query_to_top(h2)
        h1_root = h1.get_root()
        h1_root.query = Query(q)

    else:
        hiers = [h2]

    if biz_block_lst is not None:
        """ Нужно в иерархии h2 убрать разрез с ББ """

        def visit_node(node:MetricNode):
            if node.analyt_metadata:
                alg:Algorithm = list(node.analyt_metadata.algorithms.values())[0]
                if alg.drill_order[0][0] == 'bb':
                    node.analyt_metadata = None
                    return

            for child_node in h2.get_children(node.id):
                visit_node(child_node)

        visit_node(h2.get_root())


    query_mixin = {}

    for (k, v) in (
        ('biz_block', biz_block_lst),
        ('tb', tb),
        ('gosb', gosb)
    ):
        if v: query_mixin.update({k:v})

    query_mixin.update({'flg_correction': 0})

    """ Подмешиваем в query нашу mixin"""

    for h in hiers:
        for n in h.nodes.values():
            if n.query:
                q:Dict = n.query.to_dict()
                q.update(query_mixin)
                n.query = Query(q)

    meta = DeviationCalcMetadata(
        code,
        SourceParameters(
            TABLE_NAME_USL_FACTS,
            'dt'
        ),
        SearchDevParameters(
            'val_plan',
            'val_fact',
            -1
        ),
        hiers
    )

    return meta


async def save_metadata(full_code:str, meta:DeviationCalcMetadata, fac:FaClient):
    res = await fac.delete_metadata(full_code)
    if not res.ok: raise Exception(res.err)

    res = await fac.save_metadata(full_code, meta.to_json())
    if not res.ok: raise Exception(res.err)


async def recalc_summaries(full_code:str, dt:date, fac:FaClient):
    res = await fac.delete_results(full_code, dt)
    if not res.ok: raise Exception(res.err)

    res = await fac.get_summary(full_code, dt)
    if not res.ok: raise Exception(res.err)

    return res.data




def get_full_code(code:str, biz_block_lst:List[str] = None, tb:str = None, gosb:str = None):
    parts = [code]
    if biz_block_lst: parts.append(', '.join(biz_block_lst))
    if tb: parts.append(tb)
    if gosb: parts.append(gosb)
    res = ';'.join(parts)
    res = f'[{res}]'
    return res

async def calc_full(kc:KeyDBClient, dt:date, code:str, biz_block_lst:List[str] = None, tb:str = None, gosb:str = None):
    l = get_logger()
    l.info(f'Processing code:{code}, biz_block:{biz_block_lst}, tb:{tb}, gosb:{gosb}')

    fac = FaClient(kc)

    full_code = get_full_code(code, biz_block_lst, tb, gosb)

    try:

        l.info('Build metadata ...')
        meta:DeviationCalcMetadata = build_universal_metadata_hierarchy(code, biz_block_lst, tb, gosb)
        l.info('metadata ok')

        l.info('Save metadata to db ...')
        await save_metadata(full_code, meta, fac)
        l.info('metadata saved')

        # l.info('Calc and save summary ...')
        # res = await recalc_summaries(full_code, dt, fac)
        # l.info('summary done !')
        # l.info(f'#Summary#: {res}')
    except Exception as e:
        l.warning(repr(e))






#
# """
#     ###################################################################################
#         Разбор json-ов посвященных ТБ
#     ###################################################################################
# """
# def build_hierarchies_based_on_source_jsons(prefix:str)->Tuple[Dict,Dict]:
#     code_pref = f'{prefix}tb'
#
#     h1 = make_hier(f'{code_pref}1')
#     h2 = make_hier(f'{code_pref}2')
#
#     total_cond = bubble_and_reduce_query_to_top(h2)
#     root_h1 = h1.get_root()
#     root_h1.query = Query(total_cond)
#
#     return (h1.to_json(), h2.to_json())
#
#
# async def setup_and_save_for_one_tb(prefix:str, kc:Redis, h1json:Dict, h2json:Dict, tb_code:str, tbname:str):
#     from sdk.fa2026.client import FaClient
#
#     code_pref = f'{prefix}tb'
#
#     hc1 = Hierarchy.from_json(h1json)
#     hc2 = Hierarchy.from_json(h2json)
#
#     r1 = hc1.get_root()
#     r1.name = f'{r1.name} ({tbname})'
#
#     r2 = hc2.get_root()
#     r2.name = f'{r2.name} ({tbname})'
#
#     hc1 = split_to_motiv_adj(hc1)
#     hc2 = split_to_motiv_adj(hc2)
#
#     for n in hc1.nodes.values():
#         if n.query:
#             dic = {}
#             dic.update(n.query.to_dict())
#             dic.update({
#                 'tb': tbname
#             })
#             n.query = Query(dic)
#
#     for n in hc2.nodes.values():
#         if n.query:
#             dic = {}
#             dic.update(n.query.to_dict())
#             dic.update({
#                 'tb': tbname
#             })
#             n.query = Query(dic)
#
#     hier_lst = [
#         hc1, hc2
#     ]
#
#     code = f'{code_pref}_{tb_code}'
#
#     meta = DeviationCalcMetadata(
#         code,
#         SourceParameters(
#             TABLE_NAME_USL_FACTS,
#             'dt'
#         ),
#         SearchDevParameters(
#             'val_plan',
#             'val_fact',
#             -1
#         ),
#         hier_lst
#     )
#
#     meta_json = meta.to_json()
#
#     fac = FaClient(kc)
#
#     await fac.delete_metadata(code)
#     await fac.save_metadata(code, meta_json)
#
#
# async def setup_tbgosb_tb(prefix:str, kc:Redis, tg:TaskGroup):
#     (h1_json, h2_json) = build_hierarchies_based_on_source_jsons(prefix)
#     for (tb_code, tbname) in TB_SETUP.items():
#         await setup_and_save_for_one_tb(prefix, kc, h1_json, h2_json, tb_code, tbname)
#
#
#
#
# async def calc_tbgosb_onetb(prefix:str, dt:date, kc:Redis, tbcode:str):
#     from sdk.fa2026.client import FaClient
#
#     code = f'{prefix}tb_{tbcode}'
#
#     fac = FaClient(kc)
#     await fac.delete_results(code,dt)
#     res = await fac.get_summary(code, dt)
#     print(res)
#
#
#
#

class Mgr():
    def __init__(self, MAX:int = 10):
        self._MAX:int = MAX
        self._current:int = 0

    def incr(self):
        print(f'incr {self._current} -> {self._current + 1}')
        self._current += 1

    def decr(self):
        print(f'decr {self._current} -> {self._current - 1}')
        self._current -= 1

    def check(self)->bool:
        return self._current < self._MAX


def main():


    # meta = build_universal_metadata_hierarchy('chkd', tb = 'Московский')
    # print(meta)
    # return

    dt = date(2026, 4, 30)



    all_prefixes = [
        'od',
        # 'rez',
        # 'operpl',
        # 'opex',
        # 'chkd',
        # 'chpda',
        # 'chpdp'
    ]
    # prefix = 'operpl'

    import asyncio




    async def run():
        import asyncio
        from typing import Set

        kc = env__init_keydb_instance()


        tb_lst = [x for (x,y) in TB_GOSB_SETUP]
        tb_lst = list(set(tb_lst))

        def gosb_lst(src_tb:str) -> Iterable[str]:
            for (tb, gosb) in TB_GOSB_SETUP:
                if src_tb == tb: yield gosb

        mgr = Mgr()

        tasks:Set[asyncio.Task] = set()


        lock = asyncio.Lock()


        async def task_done_callback(t:asyncio.Task):
            async with lock:
                mgr.decr()
                tasks.discard(t)

        async def place_task(coro, tg:TaskGroup):
            while True:
                async with lock:
                    if mgr.check():
                        t = tg.create_task(coro)
                        tasks.add(t)
                        mgr.incr()
                        t.add_done_callback(task_done_callback)
                        break
                await asyncio.sleep(0.1)
            print('TASK PLACED')


        async with asyncio.TaskGroup() as tg:

            for prefix in all_prefixes:

                # Сначала пустой
                await place_task(calc_full(kc, dt, prefix), tg)

                # Теперь только по ББ
                for bb_lst in BB_SETUP:
                    await place_task(calc_full(kc, dt, prefix, biz_block_lst=list(bb_lst)), tg)

                for tb in tb_lst:
                    # тупо ТБ
                    await place_task(calc_full(kc, dt, prefix, tb = tb), tg)

                    # тб по бб
                    for bb_lst in BB_SETUP:
                        await place_task(calc_full(kc, dt, prefix, biz_block_lst=list(bb_lst), tb = tb), tg)

                    for gosb in gosb_lst(tb):
                        # тупо ГОСБ
                        await place_task(calc_full(kc, dt, prefix, tb=tb, gosb = gosb), tg)

                        for bb_lst in BB_SETUP:
                            await place_task(calc_full(kc, dt, prefix, biz_block_lst=list(bb_lst), tb=tb, gosb = gosb), tg)


        print('yo')
        return

            # async def _run():
            #     try:
            #         await setup_tbgosb_pao(prefix, kc)
            #         await asyncio.sleep(0.1)
            #         await calc_tbgosb_pao(prefix, dt, kc)
            #     except:
            #         print(f'SOME ERR {prefix} PAO')
            #
            # await _run()


            # (h1_json, h2_json) = build_hierarchies_based_on_source_jsons(prefix)
            # for (tb_code, tbname) in TB_SETUP.items():
            #     await setup_and_save_for_one_tb(prefix, kc, h1_json, h2_json, tb_code, tbname)
            #     await calc_tbgosb_onetb(prefix, dt, kc, tb_code)
            #
            #
            # await asyncio.sleep(0.1)





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
