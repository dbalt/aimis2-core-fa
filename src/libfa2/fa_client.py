from coredis import Redis as KeyDbClient


from sdk.core.dappclient import DClientBase
from sdk.core.monadic import Res

from .fa_server import FA_PROTOCOL
from uuid import uuid4
from datetime import date




class FaClient(DClientBase):

    def __init__(self, keydb_client: KeyDbClient):
        super().__init__(keydb_client, FA_PROTOCOL, str(uuid4()))



    async def get_summary(self, code:str, dt:date)->Res[str]:
        data = {
            'action': 'get_deviation_summary',
            'payload': {
                'code': code,
                'dt': dt.isoformat()
            }
        }

        data_res_dict = await self._send_request(data)
        data_res = Res.from_dic(data_res_dict)

        if data_res.ok:
            return Res.mk_result(data_res.data['summary'])

        return Res.mk_error(data_res.err)







