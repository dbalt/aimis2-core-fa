import os, sys, asyncio
sdk_path = os.environ.get('AIMIS_SDK_PATH')
print(f'=== SDK_PATH: {sdk_path} ===')
if sdk_path:
    sys.path.insert(0, sdk_path)

from libfa2.fa_server import FaServerImpl
from libfa2.data_access.data_mgmt import DataMgmtDataGate, DataMgmtDbWrapper
from libfa2.data_access.aggr import DataAccessDataGate
from libfa2.fa_impl.precompute_config import validate_precompute_cfg
from sdk.tools.settings import env__init_keydb_instance
from sdk.giga.client import GigaChatClientPartV2
from sdk.core.logging import get_logger
from sdk.tools.settings import get_conf

import logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] {%(pathname)s:%(lineno)d} %(name)s %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

async def run():
    lgr = get_logger()
    kc = await env__init_keydb_instance()
    # da = DataAccessDataGate(kc)

    # trying local DbWraper based pool
    '''
        Этот кусок - временный workaround, чтобы разгрузить обращения к DataGate через keydb
    '''
    from libfa2.data_access.aggr import DataAccessDbWrapper
    from libfa2.data_access.from_mono_rep import DataSourceConfig, ConnectionPoolAlwaysNew
    ds_json = get_conf('secman.datasources.ch01')
    ds_conf = DataSourceConfig.from_dic(ds_json)

    conn_pool = ConnectionPoolAlwaysNew(ds_conf)

    async def dbw_gen_func():
        dbw = await conn_pool.acquire_db_wrapper()
        return dbw

    da = DataAccessDbWrapper(dbw_gen_func)



    tbl_metadata = get_conf('configs.fa2026.tables.metadata')
    tbl_results = get_conf('configs.fa2026.tables.results')
    gigachat_cert_source = get_conf('configs.fa2026.gigachat_cert_source', 'navi_signal')
    model_summary = get_conf('configs.fa2026.models.summary', 'GigaChat-3-Ultra')
    model_details = get_conf('configs.fa2026.models.details', 'GigaChat-3-Ultra')
    # предвычисления саммаризации: отсутствие ключа = дефолт (всё code);
    # невалидный конфиг падает здесь (fail-fast, сервер не стартует)
    precompute_cfg = validate_precompute_cfg(
        get_conf('configs.fa2026.summarize.precompute', None)
    )

    # dm = DataMgmtDataGate(kc, tbl_metadata, tbl_results)
    dm = DataMgmtDbWrapper(dbw_gen_func, tbl_metadata, tbl_results)

    async def get_llm_client():
        return GigaChatClientPartV2(kc, source=gigachat_cert_source)

    server = FaServerImpl(
        kc,
        dm,
        da,
        get_llm_client,
        model_summary,
        model_details,
        precompute_cfg=precompute_cfg
    )

    try:
        lgr.info(f'Registering ...')
        await server.register()
        lgr.info(f'Doing on_start things ...')
        await server.on_start()
        lgr.info('serving ...')
        await server.serve()
    except Exception as e:
        lgr.exception(f'Something goes wrong: {repr(e)}')
    finally:
        lgr.info(f'Trying to unregister')
        await server.unregister()


def main():
    import asyncio
    asyncio.run(run())

if __name__ == '__main__':
    main()
