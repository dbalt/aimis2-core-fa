from sdk.tools.settings import env__init_keydb_instance
from sdk.fa2026.client import FaClient
from sdk.datagate.dg_client import GeneralSQLDataGateClientPart
from sdk.tools.settings import FileTools
from datetime import date

async def do_work(path:str):

    kc = await env__init_keydb_instance()
    dg = GeneralSQLDataGateClientPart(kc)
    fac = FaClient(kc)

    sql = '''
select t.code, t.dt
from missa_aimis.t_aimis__fa__results t
    '''

    res = await dg.get_data(sql)
    for r in res.data:
        print(r)
        code = r['code']
        dt = r['dt']
        out_name = FileTools.path_concat(path, f'{code}__{dt}.md')
        content = await fac.get_summary(code, date.fromisoformat(dt))
        print(f'writing file {out_name} ...')
        FileTools.write_to_file(out_name, content.data)




def main():
    import asyncio
    asyncio.run(do_work('mds'))

if __name__ == '__main__':
    main()