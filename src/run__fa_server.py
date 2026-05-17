from libfa2.fa_server import FaServerImpl
from libfa2.data_access.data_mgmt import DataMgmtDataGate
from libfa2.data_access.aggr import DataAccessDataGate
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
    da = DataAccessDataGate(kc)

    tbl_metadata = get_conf('configs.fa2026.tables.metadata')
    tbl_results = get_conf('configs.fa2026.tables.results')
    dm = DataMgmtDataGate(kc, tbl_metadata, tbl_results)

    def get_llm_client():
        return GigaChatClientPartV2(kc)

    server = FaServerImpl(
        kc,
        dm,
        da,
        get_llm_client
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
