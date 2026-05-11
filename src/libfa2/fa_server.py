from datetime import date

from coredis import Redis as KeyDbClient

from sdk.core.base_api_server_app import BaseAppServerPart
from sdk.core.logging import get_logger
from typing import Dict, AsyncIterable

from libfa2.data_access.data_mgmt import DataMgmt
from libfa2.data_access.aggr import DataAccess
from libfa2.fa_impl.deviation_calc_params import DeviationCalcParams
from libfa2.fa_impl.calc import calculate_deviations
from libfa2.fa_impl.collect import collect_for_summary
from libfa2.fa_impl.summarize import summarize

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

        if action == 'get_deviation_summary':
            code = payload['code']
            dt = date.fromisoformat(payload['dt'])
            lgr.info(f'Processing get_deviation_summary: code={code}, dt={dt}')

            # Step 1: check cached results
            results_res = await self._data_mgmt.get_results(code, dt)
            if results_res.ok:
                lgr.info(f'Cached results found for code={code}, dt={dt}')
                _, summary = results_res.data
                lgr.debug(f'CACHED summary length={len(summary)}')
                yield {'summary': summary}
                return
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
            yield {'summary': summary}
            return

        lgr.warning(f'Unsupported action received: {action}')
        raise Exception(f'Unsupported action: {action}')












