

async def main():
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



if __name__ == '__main__':
    import asyncio
    asyncio.run(main())