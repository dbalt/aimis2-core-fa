from typing import Dict, AsyncIterable

from coredis import Redis as KeyDbClient

from sdk.core.base_api_server_app import BaseApiAppServerPart

from sdk.datagate.dg_client import GeneralSQLDataGateClientPart

from datetime import date
from sdk.fa2026.client import FaClient

from sdk.tools.settings import get_conf
from libfa2.fa_impl.deviation_calc_metadata import DeviationCalcMetadata

from typing import Any



class AIVisorApiAppServerPart(BaseApiAppServerPart):


    def __init__(self, keydb_client: KeyDbClient):
        super().__init__(keydb_client, 'aivisor', 'fa', 1)
        self._tbgosb_table_name = get_conf('configs.aivisor.table_name', 'missa_bidr.v_aimis__usl_facts_exp')

    @property
    def _force_single_response(self) -> bool:
        return True

    async def m__process_request(self, request_payload: Dict) -> AsyncIterable[Dict]:
        res = await self._do_work(payload=request_payload)
        yield res

    async def _do_work(self, payload:Dict)->str:
        if 'code' not in payload:
            raise Exception('No <code> field in payload')

        code = payload.get('code')

        if 'dt' not in payload:
            raise Exception('No <dt> field in payload')

        dt = payload.get('dt')
        dt = date.fromisoformat(dt)

        fac = FaClient(self._keydb_client)

        metadata_res = await fac.get_metadata(code)

        if not metadata_res.ok:
            raise Exception(f'No registered deviations with code: {code}')

        calc_metadata = DeviationCalcMetadata.from_dict(metadata_res.data)
        if calc_metadata.source_params.source_name != self._tbgosb_table_name:
            raise Exception(f'Restricted access to deviation with code: {code} ')

        summary_res = await fac.get_summary(code, dt)

        if not summary_res.ok:
            raise Exception(summary_res.err)

        return summary_res.data

