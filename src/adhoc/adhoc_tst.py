


async def _instantiate_keydb():
    from sdk.tools.settings import env__init_keydb_instance
    kdb = env__init_keydb_instance()
    return kdb


async def test_data_access():
    from libfa2.data_access.aggr import DataAccess
    from libfa2.data_access.conditions import ConditionSet
    from datetime import date




    kdb = await _instantiate_keydb()
    da = DataAccess(kdb)

    _conds = ConditionSet.from_dict({
        'fact_dt': date(2025,5,31),
        'kpi_name': 'ТБ. Операционная прибыль',
        'segment': 'ММБ',
        'tb_id': 55
    })

    res = await da.get_aggr_data(
        source='missa_bidr.t_aimis_all_kpi',
        grp_by_columns=[],
        aggr_columns=['plan', 'fact'],
        conditions=_conds
    )

    print(res)


async def run_test_dg():
    from sdk.tools.settings import env__init_keydb_instance
    from sdk.datagate.dg_client import GeneralSQLDataGateClientPart
    from datetime import date, datetime

    kdb = env__init_keydb_instance()
    cl = GeneralSQLDataGateClientPart(kdb)

    sql = '''
select t.*
from missa_bidr.t_aimis_fa__metrics_bsp t
where 1=1
    and t.detail_kpi_name_2 in %(detail_kpi_name_2)s
    and t.tb_name in %(tb_name)s
    and t.rep_dt = %(rep_dt)s
limit 1000 
    '''


    params = {
        'detail_kpi_name_2': ['ОД до резервов', 'Операционные расходы'],
        'tb_name': ['Уральский банк', 'Поволжский банк'],
        'rep_dt': date(2026,2, 28),
    }


    res = await cl.get_data(sql, params)

    print(res)


def main():
    import asyncio
    asyncio.run(test_data_access())


if __name__ == '__main__':
    main()