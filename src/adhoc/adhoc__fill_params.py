


async def fill_params():
    from adhoc2 import mk_hier
    from libfa2.fa_impl.calc import calculate_deviations, DeviationCalcParams, SourceParameters, SearchDevParameters
    from libfa2.data_access.data_mgmt import DataMgmt, DataMgmtDataGate, GeneralSQLDataGateClientPart
    from sdk.tools.settings import env__init_keydb_instance

    h = mk_hier()
    cp = DeviationCalcParams(
        code='tst',
        rep_dt=None,
        source_params=SourceParameters(
            source_name='missa_bidr.t_aimis_fa__metrics_bsp',
            rep_dt_column='rep_dt'
        ),
        search_dev_params=SearchDevParameters(
            plan_column='plan',
            fact_column='fact',
            sign_negative_impact=-1
        ),
        hier=h
    )

    kc = await env__init_keydb_instance()
    dm:DataMgmt = DataMgmtDataGate(kc, 'missa_aimis.t_aimis__fa__metadata', 'missa_aimis.t_aimis__fa__results')

    cp_json_dic = cp.to_json()

    res = await dm.save_metadata(cp.code, cp_json_dic)
    print(res)






def main():
    import asyncio
    asyncio.run(fill_params())


if __name__ == '__main__':
    main()