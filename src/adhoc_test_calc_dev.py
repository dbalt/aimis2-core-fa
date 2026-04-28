from libfa2.data_access.aggr import DataRow, DataAccess
from libfa2.hier_metadata import Hierarchy, MetricNode, MetricType, Query
from libfa2.analyt_struct_metadata import AnalyticalStructureMetadata, Algorithm, Dimension
from libfa2.fa_impl.service import calculate_deviations,DeviationCalcParams,SourceParameters,SearchDevParameters
from datetime import date
import asyncio, logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] {%(pathname)s:%(lineno)d} %(name)s %(levelname)s - %(message)s',
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
        analyt_metadata=an_tb,
        query=Query({'code': 'prochie_dohod_kib'})

    )
    h.add_node(od_oth)

    return h



async def get_data_access_client()->DataAccess:
    kc = await _instantiate_keydb()
    da = DataAccess(kc)
    return da


async def test_hier():
    h = make_test_hierarchy()
    dal = await get_data_access_client()
    cp = DeviationCalcParams(
        rep_dt=date(2026,1,31),
        source_params= SourceParameters(
            source_name='missa_bidr.t_aimis_fa__metrics',
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
    print(res)



def main():
    import asyncio
    asyncio.run(test_hier())


if __name__ == '__main__':
    main()