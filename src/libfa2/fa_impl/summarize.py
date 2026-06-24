#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
summarize.py — многовариантная саммаризация факторного анализа
================================================================

Роутинг по состоянию показателя на одну из трёх веток:
  Ветка 1 — показатель В ЦЕЛОМ выполняет план (совокупный вклад в плюс),
            но ВНУТРИ есть ХОТЬ КАКОЙ-ЛИБО негатив → фокус на 🔴-негативе + чем скомпенсирован;
  Ветка 2 — показатель выполняет план и негатива НЕТ → только 🟢-позитив;
  Ветка 3 — верхнеуровневый показатель ОТКЛОНЯЕТСЯ (совокупный вклад в минус)
            → ИСКЛЮЧИТЕЛЬНО значимые 🔴-негативы.

Каждой ветке соответствует ПАРА промптов: (саммари, таблица).
Промпт саммари у каждой ветки свой; промпт таблицы единый (визуализация
знаконезависима) и тоже размечает влияние маркерами 🔴/🟢.
"""

from __future__ import annotations

import asyncio
import json
from typing import Dict, List, Optional, Tuple, Callable

from sdk.giga.client import GigaChatClientPartV2, DEFAULT_GIGA_MODEL
from sdk.giga.iface import MsgBase, AssistantMsg
from sdk.core.monadic import Res
from .summarize_prompts import SummarizerPrompt


# ===========================================================================
#                      Е Д И Н Ы Й   Х Е Л П Е Р   В Ы З О В А   L L M
# ===========================================================================
async def _base_llm_processing_function(
        system_prompt: str, data: Dict,
        llm_client: GigaChatClientPartV2,
        llm_model: str = "GigaChat-3-Ultra",
) -> Res[str]:
    system_prompt = MsgBase.system_prompt(system_prompt)

    usr_msg = f"data:{json.dumps(data, ensure_ascii=False)}"
    usr_msg = MsgBase.user_msg(usr_msg)

    resp: Res[MsgBase] = await llm_client.ask_giga(
        msgs=[system_prompt, usr_msg],
        model=llm_model,
    )

    if not resp.ok:
        return Res.mk_error(resp.err)

    answer: MsgBase = resp.data
    if answer.role != "assistant":
        return Res.mk_error(f"Unexpected answer from llm: {answer}")

    assistant_answer: AssistantMsg = answer
    return Res.mk_result(assistant_answer.message)


# ===========================================================================
#                       Р О У Т И Н Г  /  К Л А С С И Ф И К А Т О Р
# ===========================================================================
# Порог "любого негатива": негативом считается всё, что по модулю
# больше NEG_EPS (отсекаем лишь float-шум суб-рублёвого масштаба).
NEG_EPS = 1.0  # ру


def _root_node(obj: Dict) -> Dict:
    return obj["data"][0]


def _direct_children(node: Dict) -> List[Dict]:
    det = node.get("details") or {}
    return det.get("top_factors") or []


def _impact(node: Dict) -> float:
    return float(node.get("amounts", {}).get("impact_to_top_lvl", 0.0) or 0.0)


def _root_impact_total(obj: Dict) -> float:
    return _impact(_root_node(obj))


def _negative_contrib(obj: Dict) -> float:
    """Абсолютная величина негативного вклада на верхнем уровне.
    Из root.details.deviation_amounts.negative_contrib (по всем деревьям),
    иначе — сумма отрицательных impact прямых потомков."""
    total_neg, found = 0.0, False
    for tree in obj["data"]:
        da = (tree.get("details") or {}).get("deviation_amounts") or {}
        if da.get("negative_contrib") is not None:
            total_neg += float(da["negative_contrib"])
            found = True
    if found:
        return abs(total_neg)
    for tree in obj["data"]:
        for ch in _direct_children(tree):
            if _impact(ch) < 0:
                total_neg += _impact(ch)
    return abs(total_neg)


def _has_any_negative(obj: Dict) -> bool:
    """Есть ли на верхнем уровне ХОТЬ КАКОЙ-ЛИБО негатив (без порога значимости).
    NEG_EPS отсекает только float-шум суб-рублёвого масштаба."""
    return _negative_contrib(obj) > NEG_EPS


def classify(obj: Dict) -> int:
    """Возвращает номер ветки (1, 2 или 3).

    Роутинг (без порога значимости):
      • ветка 3 — совокупный вклад корня < 0 (показатель отклоняется);
      • ветка 1 — корень выполняет план, но внутри есть ХОТЬ КАКОЙ-ЛИБО негатив;
      • ветка 2 — корень выполняет план и негатива внутри нет.
    """
    root_imp = _root_impact_total(obj)

    if root_imp < 0:
        return 3
    if _has_any_negative(obj):
        return 1
    return 2


# ===========================================================================
#              С Т А Р Ы Е   Ф У Н К Ц И И   ( с о х р а н е н и е   A P I )
# ===========================================================================
async def build_deviations_visualization_table(
        data: Dict,
        llm_client: GigaChatClientPartV2,
        llm_model: str = "GigaChat-3-Ultra",
) -> Res[str]:
    """Старая функция — оставлена для обратной совместимости.
    Теперь использует единый TABLE_PROMPT с 🔴/🟢 маркерами."""
    return await _base_llm_processing_function(SummarizerPrompt.TABLE_PROMPT, data, llm_client, llm_model)


async def summarize_results(data: Dict, llm_client: GigaChatClientPartV2,
                            llm_model: str = "GigaChat-3-Ultra") -> Res[str]:
    """Старая функция — оставлена для обратной совместимости.
    Теперь использует роутинг по веткам + веточный промпт."""
    branch = classify(data)
    summary_prompt = SummarizerPrompt.PROMPT_PAIRS[branch][0]
    return await _base_llm_processing_function(summary_prompt, data, llm_client, llm_model)


# ===========================================================================
#              С Б О Р К А   О Т Ч Ё Т А   ( н о в а я   л о г и к а )
# ===========================================================================
async def build_branch_report(
        data: Dict,
        branch: int,
        llm_client_gen_fn: Callable,
        model_summary: str = "GigaChat-3-Ultra",
        model_table: str = "GigaChat-2-Max",
) -> Res[str]:
    """Собрать отчёт по выбранной ветке: параллельно саммари + таблица."""
    summary_prompt, table_prompt = SummarizerPrompt.PROMPT_PAIRS[branch]

    tsks = []
    async with asyncio.TaskGroup() as tg:
        tsks.append(tg.create_task(
            _base_llm_processing_function(
                summary_prompt, data, await llm_client_gen_fn(), model_summary
            )
        ))
        tsks.append(tg.create_task(
            _base_llm_processing_function(
                table_prompt, data, await llm_client_gen_fn(), model_table
            )
        ))

    summary_res, table_res = (t.result() for t in tsks)

    if not summary_res.ok:
        return Res.mk_error(f"Failed build summary. err: {summary_res.err}")
    if not table_res.ok:
        return Res.mk_error(f"Failed build deviations detailed table. err: {table_res.err}")

    return Res.mk_result(f"{summary_res.data}\n\n\n{table_res.data}")


# ===========================================================================
#                     О С Н О В Н А Я   Т О Ч К А   В Х О Д А
# ===========================================================================
async def summarize(
        data: Dict,
        llm_client_gen_fn: Callable,
        model_summary: str = "GigaChat-3-Ultra",
        model_details: str = "GigaChat-2-Max",
) -> Res[str]:
    """
    Главная функция саммаризации.
    """
    branch = classify(data)
    return await build_branch_report(
        data, branch, llm_client_gen_fn,
        model_summary=model_summary,
        model_table=model_details,
    )
