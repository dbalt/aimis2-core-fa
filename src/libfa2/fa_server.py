from datetime import date

from coredis import Redis as KeyDbClient

from sdk.core.base_api_server_app import BaseAppServerPart
from sdk.core.monadic import Res
from sdk.core.logging import get_logger
from typing import Dict, AsyncIterable

from libfa2.data_access.data_mgmt import DataMgmt
from libfa2.data_access.aggr import DataAccess
from libfa2.fa_impl.deviation_calc_params import DeviationCalcParams
from libfa2.fa_impl.calc import calculate_deviations
from libfa2.fa_impl.collect import collect_for_summary
from libfa2.fa_impl.summarize import summarize
from libfa2.enums import FaServerAction

FA_PROTOCOL = 'fa2026'


class FaServerImpl(BaseAppServerPart):
    def __init__(
        self,
        keydb_client: KeyDbClient,
        data_mgmt: DataMgmt,
        data_access: DataAccess,
        llm_client_gen_fn,
    ):
        super().__init__(keydb_client, FA_PROTOCOL)
        self._data_mgmt = data_mgmt
        self._data_access = data_access
        self._llm_client_gen_fn = llm_client_gen_fn

    async def m__process_request(self, request_payload: Dict) -> AsyncIterable[Dict]:
        lgr = get_logger()
        action = request_payload.get('action')
        payload = request_payload.get('payload', {})
        lgr.debug(f'request_payload: {request_payload}')

        if action == FaServerAction.GET_DEVIATION_SUMMARY:
            result = await self._handle_get_deviation_summary(payload)
            yield result
            return

        if action == FaServerAction.DELETE_METADATA:
            async for resp in self._handle_delete_metadata(payload):
                yield resp
            return

        if action == FaServerAction.SAVE_METADATA:
            async for resp in self._handle_save_metadata(payload):
                yield resp
            return

        if action == FaServerAction.GET_METADATA:
            async for resp in self._handle_get_metadata(payload):
                yield resp
            return

        if action == FaServerAction.DELETE_RESULTS:
            async for resp in self._handle_delete_results(payload):
                yield resp
            return

        if action == FaServerAction.DELETE_RESULTS_FOR_DT:
            async for resp in self._handle_delete_results_for_dt(payload):
                yield resp
            return

        lgr.warning(f'Unsupported action received: {action}')
        raise Exception(f'Unsupported action: {action}')

    async def _handle_get_deviation_summary(self, payload: Dict) -> Dict:
        lgr = get_logger()
        code = payload['code']
        dt = date.fromisoformat(payload['dt'])
        lgr.info(f'Processing get_deviation_summary: code={code}, dt={dt}')

        # Step 1: check cached results
        results_res = await self._data_mgmt.get_results(code, dt)
        if results_res.ok:
            lgr.info(f'Cached results found for code={code}, dt={dt}')
            _, summary = results_res.data
            lgr.debug(f'CACHED summary length={len(summary)}')
            return {'summary': summary}

        lgr.info(f'No cached results, proceeding to calculate: code={code}, dt={dt}')

        # Step 2: fetch metadata
        metadata_res = await self._data_mgmt.get_metadata(code)
        if not metadata_res.ok:
            lgr.exception(f'Metadata not found for code="{code}": {metadata_res.err}')
            raise Exception(f'Metadata not found for code "{code}": {metadata_res.err}')
        lgr.debug(f'Metadata loaded for code={code}')

        # Step 3: deserialize params and set report date
        calc_params = DeviationCalcParams.from_dict(metadata_res.data)
        calc_params.rep_dt = dt
        lgr.info(f'Deserialized calc_params for code={code}, rep_dt set to {dt}')

        # Step 4: calculate deviations
        lgr.info(f'Starting deviation calculation: code={code}, dt={dt}')
        drill_component = await calculate_deviations(calc_params, self._data_access)
        lgr.info(f'Deviation calculation completed: code={code}, dt={dt}')

        # Step 5: collect data for summary
        data = collect_for_summary(drill_component)
        lgr.debug(f'Collected data for summary, keys={list(data.keys())}')

        # Step 6: generate summary via LLM
        lgr.info(f'Starting summarization: code={code}, dt={dt}')
        summary_res = await summarize(data, self._llm_client_gen_fn)
        if not summary_res.ok:
            lgr.exception(f'Summarization failed: code={code}, dt={dt}: {summary_res.err}')
            raise Exception(f'Summarization failed: {summary_res.err}')
        summary = summary_res.data
        lgr.info(f'Summarization completed: code={code}, dt={dt}, summary length={len(summary)}')

        # Step 7: persist results (best-effort)
        save_res = await self._data_mgmt.save_results(code, dt, data, summary)
        if not save_res.ok:
            lgr.warning(f'Failed to save results for code={code}, dt={dt}: {save_res.err}')

        # Step 8: return summary
        lgr.info(f'Returning summary: code={code}, dt={dt}')
        return {'summary': summary}

    async def _handle_delete_metadata(self, payload: Dict) -> AsyncIterable[Dict]:
        lgr = get_logger()
        code = payload['code']
        lgr.info(f'Processing delete_metadata: code={code}')

        res = await self._data_mgmt.delete_metadata(code)
        if not res.ok:
            lgr.exception(f'delete_metadata failed: code={code}: {res.err}')
            raise Exception(f'delete_metadata failed: {res.err}')

        lgr.info(f'delete_metadata completed: code={code}')
        yield {}

    async def _handle_save_metadata(self, payload: Dict) -> AsyncIterable[Dict]:
        lgr = get_logger()
        code = payload['code']
        data = payload['data']
        lgr.info(f'Processing save_metadata: code={code}')

        res = await self._data_mgmt.save_metadata(code, data)
        if not res.ok:
            lgr.exception(f'save_metadata failed: code={code}: {res.err}')
            raise Exception(f'save_metadata failed: {res.err}')

        lgr.info(f'save_metadata completed: code={code}')
        yield {}

    async def _handle_get_metadata(self, payload: Dict) -> AsyncIterable[Dict]:
        lgr = get_logger()
        code = payload['code']
        lgr.info(f'Processing get_metadata: code={code}')

        res = await self._data_mgmt.get_metadata(code)
        if not res.ok:
            lgr.exception(f'get_metadata failed: code={code}: {res.err}')
            raise Exception(f'get_metadata failed: {res.err}')

        lgr.info(f'get_metadata completed: code={code}')
        yield {'metadata': res.data}

    async def _handle_delete_results(self, payload: Dict) -> AsyncIterable[Dict]:
        lgr = get_logger()
        code = payload['code']
        dt = date.fromisoformat(payload['dt'])
        lgr.info(f'Processing delete_results: code={code}, dt={dt}')

        res = await self._data_mgmt.delete_results(code, dt)
        if not res.ok:
            lgr.exception(f'delete_results failed: code={code}, dt={dt}: {res.err}')
            raise Exception(f'delete_results failed: {res.err}')

        lgr.info(f'delete_results completed: code={code}, dt={dt}')
        yield {}

    async def _handle_delete_results_for_dt(self, payload: Dict) -> AsyncIterable[Dict]:
        lgr = get_logger()
        dt = date.fromisoformat(payload['dt'])
        lgr.info(f'Processing delete_results_for_dt: dt={dt}')

        res = await self._data_mgmt.delete_results_for_dt(dt)
        if not res.ok:
            lgr.exception(f'delete_results_for_dt failed: dt={dt}: {res.err}')
            raise Exception(f'delete_results_for_dt failed: {res.err}')

        lgr.info(f'delete_results_for_dt completed: dt={dt}')
        yield {}
