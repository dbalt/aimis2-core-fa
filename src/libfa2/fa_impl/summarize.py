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
import re
import logging

from typing import Dict, List, Optional, Tuple, Callable

from sdk.giga.client import GigaChatClientPartV2, DEFAULT_GIGA_MODEL
from sdk.giga.iface import MsgBase, AssistantMsg
from sdk.core.monadic import Res
from .summarize_prompts import SummarizerPrompt
from .table_renderer import render_factor_table_wrapper, _get_scale_info
logger = logging.getLogger(__name__)


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

    # -- логирование JSON, к которому применяется промпт --
    logger.info("LLM DATA: %s", json.dumps(data, ensure_ascii=False, indent=2))


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

def _root_is_ratio(obj: Dict) -> bool:
    """Проверяет, является ли корневой узел типа RATIO."""
    root = _root_node(obj)
    return root.get("metric_type") == "ratio"



def classify(obj: Dict) -> int:
    """Возвращает номер ветки (1, 2 или 3).

    Роутинг (без порога значимости):
      • ветка 3 — совокупный вклад корня < 0 (показатель отклоняется);
      • ветка 1 — корень выполняет план, но внутри есть ХОТЬ КАКОЙ-ЛИБО негатив;
      • ветка 2 — корень выполняет план и негатива внутри нет.
      • ветка 4 - отдельно для случая ratio
    """
    root_imp = _root_impact_total(obj)

    if _root_is_ratio(obj):
        return 4
    if root_imp < 0:
        return 3
    if _has_any_negative(obj):
        return 1
    return 2


# ===========================================================================
#              С Б О Р К А   О Т Ч Ё Т А   (  н о в а я   л о г и к а )
# ===========================================================================
async def build_branch_report(
        data: Dict,
        branch: int,
        llm_client_gen_fn: Callable,
        model_summary: str = "GigaChat-3-Ultra",
        model_table: str = "GigaChat-2-Max",
) -> Res[str]:
    """Собрать отчёт по выбранной ветке: параллельно short_summary, key_factors, таблица."""
    summary_prompt = SummarizerPrompt.SHORT_SUMMARY_PROMPTS[branch]
    factors_prompt = SummarizerPrompt.KEY_FACTORS_PROMPTS[branch]

    scale_info = _get_scale_info(data)
    root = _root_node(data)
    plan_alias = data.get("plan_alias") or root.get("plan_alias") or "План"
    fact_alias = data.get("fact_alias") or root.get("fact_alias") or "Факт"
    scale_info["plan_alias"] = plan_alias.lower()
    scale_info["fact_alias"] = fact_alias.lower()
    data_with_scale = {**data, "scale_info": scale_info}

    # Подставляем алиасы вместо {{plan_alias}}/{{fact_alias}} в промпты
    summary_prompt = summary_prompt.replace("{{plan_alias}}", plan_alias).replace("{{fact_alias}}", fact_alias)
    factors_prompt = factors_prompt.replace("{{plan_alias}}", plan_alias).replace("{{fact_alias}}", fact_alias)
    motiv_prompt = SummarizerPrompt.MOTIV_PROMPT.replace("{{plan_alias}}", plan_alias).replace("{{fact_alias}}", fact_alias)

    tsks = []
    has_motiv = False
    async with asyncio.TaskGroup() as tg:
        tsks.append(tg.create_task(
            _base_llm_processing_function(
                summary_prompt, data_with_scale, await llm_client_gen_fn(), model_summary
            )
        ))
        tsks.append(tg.create_task(
            _base_llm_processing_function(
                factors_prompt, data_with_scale, await llm_client_gen_fn(), model_summary
            )
        ))
        tsks.append(tg.create_task(
            render_factor_table_wrapper(data)
        ))
        # LLM-запрос для мотивационной корректировки
        motiv = data.get("motiv_correction")
        if motiv is not None and (motiv.get("plan", 0) != 0 or motiv.get("fact", 0) != 0):
            has_motiv = True
            root_node_data = _root_node(data)
            amounts = root_node_data.get("amounts", {})
            plan_before = amounts.get("plan", 0) - motiv.get("plan", 0)
            fact_before = amounts.get("fact", 0) - motiv.get("fact", 0)

            motiv_data = {
                "motiv_correction": {
                    "plan": motiv.get("plan", 0),
                    "fact": motiv.get("fact", 0),
                    "label": motiv.get("label", ""),
                    "has_plan": motiv.get("has_plan", motiv.get("plan", 0) != 0),
                    "has_fact": motiv.get("has_fact", motiv.get("fact", 0) != 0),
                },
                "plan_before": plan_before,
                "fact_before": fact_before,
                "scale_info": scale_info,
            }
            tsks.append(tg.create_task(
                _base_llm_processing_function(
                    motiv_prompt, motiv_data, await llm_client_gen_fn(), model_summary
                )
            ))
        else:
            # Заглушка: возвращает Res.mk_result("") — пустой motiv_block
            tsks.append(tg.create_task(asyncio.sleep(0, Res.mk_result(""))))

    short_summary_res, key_factors_res, table_res, motiv_res = (t.result() for t in tsks)

    if not short_summary_res.ok:
        return Res.mk_error(f"Failed build short_summary. err: {short_summary_res.err}")
    if not key_factors_res.ok:
        return Res.mk_error(f"Failed build key_factors. err: {key_factors_res.err}")
    if table_res['ex']:
        return Res.mk_error(f"Failed build deviations detailed table. error: {table_res['ex']}")

    # Сборка финального отчёта: short_summary + key_factors + [motiv_block] + table
    final_report = f"{short_summary_res.data}\n\n\n{key_factors_res.data}"

    # Мотивационная корректировка — результат LLM (с явным заголовком-разделителем)
    if motiv_res.ok and motiv_res.data:
        final_report += f"\n\n\n## Влияние мотивационной корректировки\n\n\n{motiv_res.data}"

    # Таблица — в самом конце
    final_report += f"\n\n\n{table_res['table']}"

    return Res.mk_result(final_report)


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
    print(f"DEBUG summarize: branch={classify(data)}, metric_type={data.get('metric_type')}")  # добавь эту строку
    branch = classify(data)
    return await build_branch_report(
        data, branch, llm_client_gen_fn,
        model_summary=model_summary,
        model_table=model_details,
    )
