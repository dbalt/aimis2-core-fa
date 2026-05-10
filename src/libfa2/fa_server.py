from coredis import Redis as KeyDbClient

from sdk.core.base_api_server_app import BaseAppServerPart
from typing import Dict, List, Iterable, Tuple, AsyncIterable

from sdk.core.msgunit import MsgUnit

FA_PROTOCOL = 'fa2026'

class FaServerImpl(BaseAppServerPart):
    def __init__(self, keydb_client: KeyDbClient):
        super().__init__(keydb_client, FA_PROTOCOL)

    async def m__process_request(self, request_payload: Dict) -> AsyncIterable[Dict]:
        pass












