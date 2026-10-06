from typing import Tuple, Dict, List, Callable
from datetime import date
from .deviation_calc_metadata import DeviationCalcMetadata
from .motiv_correction import get_motiv_correction_data
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
        fn_get_llm_client:Callable,
        model_summary:str = 'GigaChat-3-Ultra',
        model_details:str = 'GigaChat-3-Ultra',
        client_session_id: str = '-1',
    )->Res[Tuple[Dict, str]]:

    lgr = get_logger()

    lgr.info(f'Starting deviation calculation: code={code}, dt={dt}')

    calc_params_lst = deviation_calc_metadata.calc_params_lst(dt)

    async with asyncio.TaskGroup() as tg:
        tsk_lst = [tg.create_task(calculate_deviations(x, data_access)) for x in calc_params_lst]

        if deviation_calc_metadata.motiv_correction is not None:
            tsk_lst.append(tg.create_task(
                get_motiv_correction_data(
                    deviation_calc_metadata.motiv_correction,
                    dt,
                    data_access,
                    deviation_calc_metadata.source_params,
                    deviation_calc_metadata.search_dev_params,
                )
            ))

    # Распаковываем результаты: первые N — drills, последний (если есть) — мотив. кор
    drills = [t.result() for t in tsk_lst[:-1]] if len(tsk_lst) > len(calc_params_lst) else [t.result() for t in tsk_lst]

    # Получаем мотив. корректировку (если была добавлена задача)
    motiv_res = None
    if len(tsk_lst) > len(calc_params_lst):
        motiv_res = tsk_lst[-1].result()

    if motiv_res is not None and not motiv_res.ok:
        lgr.warning(f'Failed to load motiv correction: {motiv_res.err}')
        motiv_row = None
    elif motiv_res is not None:
        motiv_row = motiv_res.data
    else:
        motiv_row = None

    lgr.info(f'Deviation calculation completed: code={code}, dt={dt}')

    data_lst = [collect_for_summary(x, motiv_correction_row=motiv_row) for x in drills]
    lgr.debug(f'Collected data for summary')

    lgr.info(f'Starting summarization: code={code}, dt={dt}')

    data = {
        "data": data_lst
    }

    # Добавляем motiv_correction на корневой уровень data
    if motiv_row is not None and (motiv_row.plan != 0 or motiv_row.fact != 0):
        m_dev = motiv_row.fact - motiv_row.plan
        from .units import _rnd
        data["motiv_correction"] = {
            "plan": _rnd(motiv_row.plan),
            "fact": _rnd(motiv_row.fact),
            "deviation": _rnd(m_dev),
            "label": "мотивационной корректировки",
            "has_plan": motiv_row.plan != 0,
            "has_fact": motiv_row.fact != 0,
        }

    aliases = deviation_calc_metadata.aliases or {}
    if aliases.get("plan_alias"):
        data["plan_alias"] = aliases["plan_alias"]
    if aliases.get("fact_alias"):
        data["fact_alias"] = aliases["fact_alias"]

    # Добавил sign_negative_impact для корректного определения зеленого/красного значка в таблице
    data["sign_negative_impact"] = deviation_calc_metadata.search_dev_params.sign_negative_impact

    summary_res = await summarize(data, fn_get_llm_client, model_summary, model_details, client_session_id=client_session_id)
    if not summary_res.ok:
        lgr.warning(f'Summarization failed: code={code}, dt={dt}: {summary_res.err}')
        return Res.mk_error(summary_res.err)

    summary = summary_res.data
    lgr.info(f'Summarization completed: code={code}, dt={dt}, summary length={len(summary)}')

    return Res.mk_result((data, summary))




