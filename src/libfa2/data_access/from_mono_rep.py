
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Tuple, List
from .dbwrapper import DbWrapper
import asyncio
import json

from sdk.core.logging import get_logger

@dataclass
class DataSourceConfig:
    tp:str = ''
    host:str = ''
    db:str = ''
    user:str = ''
    scrt:str = ''
    pool_size:int = 5
    tmp_schema:str = ''
    port:int = 9440
    secure:bool = True
    verify:bool = False

    def to_dic(self)->Dict:
        dic = {}
        dic.update(self.__dict__)
        return dic

    def to_json_str(self)->str:
        dic = self.to_dic()
        json_str = json.dumps(dic, ensure_ascii=False)
        return json_str

    @classmethod
    def from_dic(cls, dic: Dict) -> 'DataSourceConfig':
        return DataSourceConfig(**dic)

    @classmethod
    def from_json_str(cls, json_str) -> 'DataSourceConfig':
        dic = json.loads(json_str)
        return cls.from_dic(dic)



async def connection_factory(dsconf:DataSourceConfig):


    # Создаем безопасный конфиг для логов без пароля
    safe_conf = dsconf.to_dic()
    safe_conf['scrt'] = '***'

    try:
        if dsconf.tp == 'ch':
            from asynch import Connection
            try:
                conn =  Connection(
                    None,
                    dsconf.user,
                    dsconf.scrt,
                    dsconf.host,
                    database=dsconf.db,
                    port=dsconf.port,
                    secure=dsconf.secure,
                    verify=dsconf.verify
                )
                await conn.connect()
                return conn
            except Exception as e:
                raise

    except Exception as e:
         raise

    raise Exception(f'Connections of <{dsconf.tp}> type are not implemented yet')



class ConnectionPoolBase(ABC):

    def __init__(self, dsconf:DataSourceConfig):
        self._dsconf = dsconf

    @property
    def dsconf(self)->DataSourceConfig:
        return self._dsconf

    @property
    def pool_size(self):
        return self._dsconf.pool_size

    @classmethod
    def from_conf(cls, conf:DataSourceConfig):
        return ConnectionPoolAlwaysNew(conf)

    @abstractmethod
    async def acquire_db_wrapper(self)->DbWrapper:
        pass

    @abstractmethod
    def release_db_wrapper(self, dbwrapper:DbWrapper):
        pass



class ConnectionPoolAlwaysNew(ConnectionPoolBase):

    def __init__(self, dsconf: DataSourceConfig):
        super().__init__(dsconf)
        self._current_connections = 0
        # self._log_elk = get_logger_elk()
        # self._log_audit = get_logger_audit()
        self._lock = asyncio.Lock()

    async def acquire_db_wrapper(self) -> DbWrapper|None:
        l = get_logger()
        # l = self._log_elk
        # l_audit = self._log_audit

        async def _release_func(wrapped_func=None):
            async with self._lock:
                if wrapped_func is not None:
                    await wrapped_func()
                curr_conn = self._current_connections
                l.info(f'ConnPool {self._dsconf.tp}: decrementing conn count {curr_conn} -> {curr_conn - 1}')
                # l_audit.info(f'ConnPool {self._dsconf.tp}: decrementing conn count {curr_conn} -> {curr_conn - 1}')
                self._current_connections = self._current_connections - 1
        dbw:DbWrapper = None
        while True:
            async with self._lock:
                if self._current_connections < self._dsconf.pool_size:
                    conn = await connection_factory(self._dsconf)
                    dbw = DbWrapper(conn, _release_func, self._dsconf.tp)

                    l.info(f'ConnPool {self._dsconf.tp}: incrementing conn count {self._current_connections} -> {self._current_connections + 1}')
                    # l_audit.info(f'ConnPool {self._dsconf.tp}: incrementing conn count {self._current_connections} -> {self._current_connections + 1}')
                    self._current_connections = self._current_connections + 1
                    break
                else:
                    l.info(f"Pool saturated ({self._current_connections}/{self._dsconf.pool_size}). Waiting...")

            await asyncio.sleep(0.5)


        return dbw



    async def release_db_wrapper(self, dbwrapper: DbWrapper):
        # lock есть внутри dbwrapper, тут пропускаем
        await dbwrapper.release()