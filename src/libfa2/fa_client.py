from datetime import date
from typing import Dict, Any
from uuid import uuid4

from coredis import Redis as KeyDbClient

from sdk.core.dappclient import DClientBase
from sdk.core.monadic import Res

from .enums import FaServerAction
from .fa_server import FA_PROTOCOL


class FaClient(DClientBase):

    def __init__(self, keydb_client: KeyDbClient):
        super().__init__(keydb_client, FA_PROTOCOL, str(uuid4()))

    async def get_summary(self, code: str, dt: date) -> Res[str]:
        data = {
            'action': FaServerAction.GET_DEVIATION_SUMMARY,
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

    async def delete_metadata(self, code: str) -> Res[None]:
        data = {
            'action': FaServerAction.DELETE_METADATA,
            'payload': {
                'code': code
            }
        }

        data_res_dict = await self._send_request(data)
        data_res = Res.from_dic(data_res_dict)

        if data_res.ok:
            return Res.mk_result(None)

        return Res.mk_error(data_res.err)

    async def save_metadata(self, code: str, metadata: Dict[str, Any]) -> Res[None]:
        data = {
            'action': FaServerAction.SAVE_METADATA,
            'payload': {
                'code': code,
                'data': metadata
            }
        }

        data_res_dict = await self._send_request(data)
        data_res = Res.from_dic(data_res_dict)

        if data_res.ok:
            return Res.mk_result(None)

        return Res.mk_error(data_res.err)

    async def get_metadata(self, code: str) -> Res[Dict[str, Any]]:
        data = {
            'action': FaServerAction.GET_METADATA,
            'payload': {
                'code': code
            }
        }

        data_res_dict = await self._send_request(data)
        data_res = Res.from_dic(data_res_dict)

        if data_res.ok:
            return Res.mk_result(data_res.data['metadata'])

        return Res.mk_error(data_res.err)

    async def delete_results(self, code: str, dt: date) -> Res[None]:
        data = {
            'action': FaServerAction.DELETE_RESULTS,
            'payload': {
                'code': code,
                'dt': dt.isoformat()
            }
        }

        data_res_dict = await self._send_request(data)
        data_res = Res.from_dic(data_res_dict)

        if data_res.ok:
            return Res.mk_result(None)

        return Res.mk_error(data_res.err)

    async def delete_results_for_dt(self, dt: date) -> Res[None]:
        data = {
            'action': FaServerAction.DELETE_RESULTS_FOR_DT,
            'payload': {
                'dt': dt.isoformat()
            }
        }

        data_res_dict = await self._send_request(data)
        data_res = Res.from_dic(data_res_dict)

        if data_res.ok:
            return Res.mk_result(None)

        return Res.mk_error(data_res.err)
