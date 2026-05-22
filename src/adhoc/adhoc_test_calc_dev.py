
from libfa2.data_access.aggr import DataRow, DataAccessDataGate, DataAccess, DataAccessDbWrapper
from libfa2.data_access.dbwrapper import DbWrapper
from libfa2.fa_impl.summarize import summarize
from sdk.giga.client import GigaChatClientPartV2
import os

from libfa2.hier_metadata import Hierarchy, MetricNode, MetricType, Query
from libfa2.analyt_struct_metadata import AnalyticalStructureMetadata, Algorithm, Dimension
from libfa2.fa_impl.calc import calculate_deviations,DeviationCalcParams,SourceParameters,SearchDevParameters
from datetime import date
import asyncio, logging

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] {%(filename)s:%(lineno)d} %(name)s %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

async def _instantiate_keydb():
    from sdk.tools.settings import env__init_keydb_instance
    kdb = env__init_keydb_instance()
    return kdb


def make_test_hierarchy()->Hierarchy:
    h = Hierarchy()


    an_tb = AnalyticalStructureMetadata()
    an_tb.add_algorithm(
        Algorithm(
            id = 1,
            drill_order=[
                ['tb']
            ]
        )
    )
    an_tb.add_dimension(
        Dimension(
            code = 'tb',
            name='Террбанк',
            column='tb_name'
        )
    )


    an_seg = AnalyticalStructureMetadata()
    an_seg.add_algorithm(
        Algorithm(
            id = 2,
            drill_order=[
                ['segment']
            ]
        )
    )
    an_seg.add_dimension(
        Dimension(
            code = 'segment',
            name = 'Сегмент',
            column='segment'
        )
    )



    od = MetricNode(
        id=1,
        code='chod_kib',
        name='ЧОД КИБ',
        type=MetricType.SUM
    )
    h.add_node(od)

    od_chkd = MetricNode(
        id=2,
        code='chkd_kib',
        name='ЧКД КИБ',
        parent=od.id,
        analyt_metadata=an_tb,
        query=Query({'code':'chkd_kib'})

    )
    h.add_node(od_chkd)

    od_chpd = MetricNode(
        id=3,
        code='chpd_kib',
        name='ЧПД КИБ',
        parent=od.id,
        analyt_metadata=an_tb,
        query=Query({'code': 'chpd_kib'})

    )
    h.add_node(od_chpd)

    od_oth = MetricNode(
        id=4,
        code='prochie_dohod_kib',
        name='Прочие доходы КИБ',
        parent=od.id,
        analyt_metadata=an_seg,
        query=Query({'code': 'prochie_dohod_kib'})

    )
    h.add_node(od_oth)

    return h

async def get_llm_client()->GigaChatClientPartV2:
    kc = await _instantiate_keydb()
    ggc = GigaChatClientPartV2(kc, source='default')
    return ggc

async def get_data_access_client_aimis()->DataAccess:
    kc = await _instantiate_keydb()
    da = DataAccessDataGate(kc)
    return da

async def get_data_access_client()->DataAccess:
    res = await get_data_access_client_direct_click()
    return res


async def get_data_access_client_direct_click()->DataAccess:
    from asynch import Connection
    async def _dbw_gen():
        conn = Connection(
            None,
            os.environ.get('CLICKHOUSE_USER'),
            os.environ.get('CLICKHOUSE_PASSWORD'),
            os.environ.get('CLICKHOUSE_HOST'),
            database=os.environ.get('CLICKHOUSE_DB'),
            port=os.environ.get('CLICKHOUSE_PORT', 9440),
            secure=bool(os.environ.get('CLICKHOUSE_SECURE', True)),
            verify=bool(os.environ.get('CLICKHOUSE_VERIFY', False))
        )
        await conn.connect()

        dbw = DbWrapper(conn, tp = 'ch')
        return dbw

    dal = DataAccessDbWrapper(_dbw_gen)
    return dal


async def test_hier():
    from adhoc2 import mk_hier
    from libfa2.fa_impl.collect import collect_for_summary
    import json
    h = mk_hier()
    # h = make_test_hierarchy()
    dal = await get_data_access_client()
    cp = DeviationCalcParams(
        code = 'tst',
        rep_dt=date(2026,2,28),
        source_params= SourceParameters(
            source_name='missa_bidr.t_aimis_fa__metrics_bsp',
            rep_dt_column='rep_dt'
        ),
        search_dev_params= SearchDevParameters(
            plan_column='plan',
            fact_column='fact',
            sign_negative_impact=-1
        ),
        hier= h
    )

    res = await calculate_deviations(cp, dal)
    fac = collect_for_summary(res)
    json_str = json.dumps(fac, ensure_ascii=False)
    print(json_str)


    # [summary, table] = await asyncio.gather(
    #     summarize_results(fac.copy(), llm_client1, llm_model),
    #     build_deviations_visualization_table(fac.copy(), llm_client2, llm_model)
    # )

    summary_res = await summarize(fac, get_llm_client)


    if not summary_res.ok:
        print(f'Summary err: {summary_res.err}')
        return


    summary_text = summary_res.data

    print(summary_text)



def main():
    import asyncio, os
    os.environ['CLICKHOUSE_HOST'] = os.environ.get('CLICKHOUSE_HOST', 'tklis-mis300051.vm.mos.cloud.sbrf.ru')
    os.environ['CLICKHOUSE_USER'] = os.environ.get('CLICKHOUSE_USER', 'missa_bidr')
    os.environ['CLICKHOUSE_PASSWORD'] = os.environ.get('CLICKHOUSE_PASSWORD', 'P@$$w0rdbidr')
    os.environ['CLICKHOUSE_DB'] = os.environ.get('CLICKHOUSE_DB', 'missa_bidr')
    asyncio.run(test_hier())


if __name__ == '__main__':
    main()