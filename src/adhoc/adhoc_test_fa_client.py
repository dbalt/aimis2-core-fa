import logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] {%(pathname)s:%(lineno)d} %(name)s %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)



async def test_fa_client():
    from libfa2.fa_client import FaClient
    from sdk.tools.settings import env__init_keydb_instance
    from datetime import date
    from libfa2.fa_impl.deviation_calc_metadata import DeviationCalcMetadata, SourceParameters, SearchDevParameters
    from adhoc2 import mk_hier
    from libfa2.fa_impl.collect import collect_for_summary
    import json
    h = mk_hier()
    # h = make_test_hierarchy()
    cp = DeviationCalcMetadata(
        code = 'tst',

        source_params= SourceParameters(
            source_name='missa_bidr.t_aimis_fa__metrics_bsp',
            rep_dt_column='rep_dt'
        ),
        search_dev_params= SearchDevParameters(
            plan_column='plan',
            fact_column='fact',
            sign_negative_impact=-1
        ),
        hier_lst=[h]
    )

    dt = date(2026, 2, 28)

    kc = await env__init_keydb_instance()
    fac = FaClient(kc)
    code = 'tstx'

    await fac.save_metadata(code, cp.to_json())

    await fac.delete_results(code, dt)

    summ = await fac.get_summary(code, dt)
    print(summ)



def main():
    import asyncio
    asyncio.run(test_fa_client())


if __name__ == '__main__':
    main()