import os, sys, asyncio
sdk_path = os.environ.get('AIMIS_SDK_PATH')
print(f'=== SDK_PATH: {sdk_path} ===')
if sdk_path:
    sys.path.insert(0, sdk_path)

from aivisor.server import AIVisorApiAppServerPart
from sdk.tools.settings import env__init_keydb_instance
from sdk.core.logging import get_logger


import logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] {%(pathname)s:%(lineno)d} %(name)s %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

async def run():
    lgr = get_logger()
    kc = env__init_keydb_instance()

    server = AIVisorApiAppServerPart(
        kc
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
