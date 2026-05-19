from libfa2.hier_metadata import Hierarchy, MetricNode, MetricType, Query, ComponentMultiPartType, ComponentRatioPartType, MultipartDecompositionType
from libfa2.analyt_struct_metadata import AnalyticalStructureMetadata, Algorithm, Dimension
from libfa2.fa_impl.deviation_calc_metadata import DeviationCalcMetadata, SearchDevParameters, SourceParameters
from typing import Dict, List, Tuple


import logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] {%(pathname)s:%(lineno)d} %(name)s %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)


def _mk_hier1()->Hierarchy:

    h = Hierarchy()

    an = AnalyticalStructureMetadata()
    an.add_algorithm(
        Algorithm(
            1,
            [['pay_type']]
        )
    )
    an.add_dimension(
        Dimension(
            'pay_type',
            'Тип платежа',
            'pay_type'
        )
    )

    kd = MetricNode(
        id = 1,
        code = 'kd',
        name = 'Комиссионный доход',
        query=Query({'code':'kd_rozn', 'terr_level':'СБ'}),
        analyt_metadata=an,
        type=MetricType.MULTI,
        mp_decomp_tp=MultipartDecompositionType.INTEGRAL

    )
    h.add_node(kd)


    kd_rate = MetricNode(
        id = 2,
        code = 'kd_rate',
        name = 'Ставка КД',
        componentMultiPartType=ComponentMultiPartType.RATE,
        parent=kd.id
    )
    h.add_node(kd_rate)

    kd_oborot = MetricNode(
        id = 3,
        code = 'kd_oborot',
        name = 'Оборот',
        componentMultiPartType=ComponentMultiPartType.BASE,
        parent = kd.id,
        query = Query({'terr_level':'СБ', 'code':'oborot_rozn'}),
        type = MetricType.MULTI,
        mp_decomp_tp=MultipartDecompositionType.INTEGRAL
    )
    h.add_node(kd_oborot)


    kd_oborot_mau = MetricNode(
        id = 4,
        code = 'kd_oborot_mau',
        name = 'MAU',
        componentMultiPartType=ComponentMultiPartType.BASE,
        parent = kd_oborot.id,
        query = Query({'code':'mau_rozn', 'terr_level':'СБ'})
    )
    h.add_node(kd_oborot_mau)

    kd_oborot_avg_bill = MetricNode(
        id = 5,
        code = 'kd_oborot_avg_bill',
        name = 'Средний чек',
        componentMultiPartType=ComponentMultiPartType.RATE,
        parent = kd_oborot.id
    )
    h.add_node(kd_oborot_avg_bill)

    return h





def _mk_hier2()->Hierarchy:

    h = Hierarchy()

    an = AnalyticalStructureMetadata()
    an.add_algorithm(
        Algorithm(
            1,
            [['tb_name']]
        )
    )
    an.add_dimension(
        Dimension(
            'tb_name',
            'Тербанк',
            'tb_name'
        )
    )

    kd = MetricNode(
        id = 1,
        code = 'kd',
        name = 'Комиссионный доход',
        query=Query({'code':'kd_rozn', 'terr_level':'ТБ'}),
        analyt_metadata=an,
        type=MetricType.MULTI
    )
    h.add_node(kd)


    kd_rate = MetricNode(
        id = 2,
        code = 'kd_rate',
        name = 'Ставка КД',
        componentMultiPartType=ComponentMultiPartType.RATE,
        parent=kd.id
    )
    h.add_node(kd_rate)

    kd_oborot = MetricNode(
        id = 3,
        code = 'kd_oborot',
        name = 'Оборот',
        componentMultiPartType=ComponentMultiPartType.BASE,
        parent = kd.id,
        query = Query({'terr_level':'ТБ', 'code':'oborot_rozn'})
    )
    h.add_node(kd_oborot)
    return h


async def setup_hier():
    from sdk.tools.settings import env__init_keydb_instance
    from libfa2.fa_client import FaClient
    hier_lst = [
        _mk_hier1(),
        _mk_hier2()
    ]


    meta = DeviationCalcMetadata(
        'rozn_kd',
        SourceParameters(
            'missa_bidr.vw_aimis_fa__metrics_rozn',
            'rep_dt'
        ),
        SearchDevParameters(
            'plan',
            'fact',
            -1
        ),
        hier_lst
    )

    meta_json = meta.to_json()

    kc = await env__init_keydb_instance()
    fac = FaClient(kc)

    await fac.save_metadata('rozn_kd', meta_json)



def main():
    import asyncio
    asyncio.run(setup_hier())


if __name__ == '__main__':
    main()
