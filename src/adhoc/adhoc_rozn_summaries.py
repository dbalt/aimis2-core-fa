import logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] {%(pathname)s:%(lineno)d} %(name)s %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)


async def get_and_save_rozn_summaries():
    from sdk.fa2026.client import FaClient
    from sdk.tools.settings import env__init_keydb_instance
    from datetime import date
    from libfa2.fa_impl.deviation_calc_metadata import DeviationCalcMetadata, SourceParameters, SearchDevParameters
    from sdk.tools.settings import FileTools

    dates = (
        date(2026, 1, 31),
        date(2026, 2, 28),
        date(2025, 5, 31),
    )

    kc = await env__init_keydb_instance()
    fac = FaClient(kc)


    code = 'rozn_kd'
    for dt in dates:
        res = await fac.get_summary(code, dt)
        if not res.ok:
            print(f'Error!!!====={res.err}====')
            continue
        summary = res.data
        print(summary)
        path = FileTools.path_concat(
            FileTools.home_path(),
            'source',
            'repo',
            'aimis2-core-fa-refac',
            'src',
            'tmp',
            'reports',
            f'rozn_kd__{dt.isoformat()}.md'
        )
        FileTools.write_to_file(path, summary)


def main():
    import asyncio
    asyncio.run(get_and_save_rozn_summaries())

if __name__ == '__main__':
    main()
