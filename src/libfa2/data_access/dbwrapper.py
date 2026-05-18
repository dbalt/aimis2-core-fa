from typing import AsyncIterable, Dict
from datetime import datetime
import asyncio
import time


class DbWrapper(object):
    def _upd_ts(self):
        self._last_ts = datetime.now()

    def __init__(self, conn, fn_release=None, tp: str = 'unknown'):
        # connection here already opened.
        self._conn = conn
        self._cursor = conn.cursor()
        self._fn_release = fn_release
        self._is_released = False
        self._tp = tp
        self._last_ts = None

    @property
    def tp(self) -> str:
        return self._tp

    def release(self):
        if self._is_released: return
        if self._fn_release is not None and callable(self._fn_release):
            self._fn_release()
            close_core = self._conn.close()
            if asyncio.iscoroutine(close_core):
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(close_core)
                except RuntimeError:
                    pass
        self._is_released = True

    def reset_cursor(self):
        self._cursor = None

    @property
    def is_released(self):
        if not (self._fn_release is not None and callable(self._fn_release)): return True
        return self._is_released

    @property
    def last_ts(self):
        return self._last_ts

    async def query(self, sql, params=None) -> AsyncIterable[Dict]:
        '''
            Когда надо выполнить sql запрос и вернуть результат в виде итератора
        '''
        self._upd_ts()

        if self._is_released:
            raise Exception(F'connection already released, cant use this instance anymore')

        start_ts = time.time()

        try:
            cur = self._cursor
            if params is None:
                await cur.execute(sql)
            else:
                await cur.execute(sql, params)

            continue_flag = True
            column_names = [x[0] for x in cur.description]
            row_count = 0
            while continue_flag:
                x = await cur.fetchone()
                if x is not None:
                    row_count += 1
                    yield dict(zip(column_names, x))
                else:
                    continue_flag = False

            duration = time.time() - start_ts

        except Exception as e:
            raise

    async def exec(self, sql, params=None):
        '''
        Когда надо просто какой то запрос без возращаемого значения
        upd/ins/del/create table
        '''
        self._upd_ts()
        if self._is_released:
            raise Exception(F'connection already released, cant use this instance anymore')

        start_ts = time.time()

        try:
            cur = self._cursor
            await cur.execute(sql, params)
            if self.tp == 'gp' or self.tp == 'pg':
                await self._conn.commit()

            duration = time.time() - start_ts
        except Exception as e:
            raise
