from typing import Tuple, Dict, List, Callable
from datetime import date
from .deviation_calc_metadata import DeviationCalcMetadata
from ..data_access import DataMgmt, DataAccess

from sdk.giga.client import GigaChatClientPartV2
from sdk.core.logging import get_logger
from sdk.core.monadic import Res

from .deviation_calc_params import DeviationCalcParams
from .calc import calculate_deviations
from .collect import collect_for_summary
from .summarize import summarize
from .units import DrillComponent
import asyncio

async def calculate_and_summarize_deviation(
        code:str,
        dt:date,
        deviation_calc_metadata:DeviationCalcMetadata,
        data_access:DataAccess,
        fn_get_llm_client:Callable
    )->Res[Tuple[Dict, str]]:

    lgr = get_logger()

    lgr.info(f'Starting deviation calculation: code={code}, dt={dt}')

    calc_params_lst = deviation_calc_metadata.calc_params_lst(dt)

    async with asyncio.TaskGroup() as tg:
        tsk_lst = [tg.create_task(calculate_deviations(x, data_access)) for x in calc_params_lst]

    drills = [x.result() for x in tsk_lst]
    lgr.info(f'Deviation calculation completed: code={code}, dt={dt}')

    data_lst = [collect_for_summary(x) for x in drills]
    lgr.debug(f'Collected data for summary')

    lgr.info(f'Starting summarization: code={code}, dt={dt}')

    data = {
        "data": data_lst
    }

    summary_res = await summarize(data, fn_get_llm_client)
    if not summary_res.ok:
        lgr.warning(f'Summarization failed: code={code}, dt={dt}: {summary_res.err}')
        return Res.mk_error(summary_res.err)

    summary = summary_res.data
    lgr.info(f'Summarization completed: code={code}, dt={dt}, summary length={len(summary)}')

    return Res.mk_result((data, summary))




