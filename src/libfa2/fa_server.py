from coredis import Redis as KeyDbClient

from sdk.core.dserverbase import DServerBase
from uuid import uuid4
from typing import Dict, List, Iterable, Tuple


from sdk.core.msgunit import MsgUnit

FA_PROTOCOL = 'fa2026'

class FaServerImpl(DServerBase):
    def __init__(self, keydb_client: KeyDbClient):
        super().__init__(keydb_client, FA_PROTOCOL, str(uuid4()))

    async def m__do_work(self, mu: MsgUnit):
        data:Dict = mu.data






