"""
summarize.py — многовариантная саммаризация факторного анализа
================================================================

Роутинг по состоянию показателя на одну из трёх веток:
  Ветка 1 — показатель В ЦЕЛОМ выполняет план (совокупный вклад в плюс),
            но ВНУТРИ есть ХОТЬ КАКОЙ-ЛИБО негатив → фокус на 🔴-негативе + чем скомпенсирован;
  Ветка 2 — показатель выполняет план и негатива НЕТ → только ❇️-позитив;
  Ветка 3 — верхнеуровневый показатель ОТКЛОНЯЕТСЯ (совокупный вклад в минус)
            → ИСКЛЮЧИТЕЛЬНО значимые 🔴-негативы.

Каждой ветке соответствует ПАРА промптов: (саммари, таблица).
Промпт саммари у каждой ветки свой; промпт таблицы единый (визуализация
знаконезависима) и тоже размечает влияние маркерами 🔴/❇️.
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
from .summarize_prompts import SummarizerPrompt, make_prompt_provider
from .table_renderer import render_factor_table_wrapper, _get_scale_info
from .value_formatter import enrich_display, format_abs, collect_allowed_names
from .precompute_config import MODE_CODE, validate_precompute_cfg
logger = logging.getLogger(__name__)


# ===========================================================================
#                      Е Д И Н Ы Й   Х Е Л П Е Р   В Ы З О В А   L L M
# ===========================================================================
async def _base_llm_processing_function(
        system_prompt: str, data: Dict,
        llm_client: GigaChatClientPartV2,
        llm_model: str = "GigaChat-3-Ultra",
        client_session_id: str = '-1',
        temperature: float | None = None,
) -> Res[str]:
    system_prompt = MsgBase.system_prompt(system_prompt)

    usr_msg = f"data:{json.dumps(data, ensure_ascii=False)}"
    usr_msg = MsgBase.user_msg(usr_msg)

    # -- логирование JSON, к которому применяется промпт --
    logger.info("LLM DATA: %s", json.dumps(data, ensure_ascii=False, indent=2))


    resp: Res[MsgBase] = await llm_client.ask_giga(
        msgs=[system_prompt, usr_msg],
        model=llm_model,
        client_session_id=client_session_id,
        temperature=temperature,
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



def _tree_has_details_top_factors(tree: Dict) -> bool:
    """Проверяет, есть ли у дерева details.top_factors."""
    return bool((tree.get("details") or {}).get("top_factors"))


def _prune_wrapper_trees(data: Dict) -> Dict:
    """Убирает из data[] только пустые обёртки — узлы без top_factors
    и без meaningful amounts.deviation.

    Узлы с meaningful amounts.deviation != 0 оставляются даже если
    details/top_factors отсутствует — это корневые показатели без
    детализации (например, когда все дети положительные).

    Если есть дубликаты (два дерева с одинаковым именем и deviation),
    оставляет то, у которого есть details.top_factors.
    """
    cleaned_data = json.loads(json.dumps(data))
    trees = cleaned_data.get("data", [])

    cleaned_data["data"] = [
        tree for tree in trees
        if _tree_has_details_top_factors(tree)
        or bool((tree.get("amounts") or {}).get("deviation", 0) != 0)
    ]

    # Дедупlication УДАЛЁН — он ломает аналитические разрезы (одинаковое
    # имя + deviation, но разные analytic_slice / details).
    # Фильтр выше уже отсеивает пустые обёртки.
    return cleaned_data


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
        model_table: str = "GigaChat-3-Ultra",
        client_session_id: str = '-1',
        prompt_provider=SummarizerPrompt,
        precompute_cfg: Optional[Dict] = None,
        temperature: float | None = None,
) -> Res[str]:
    """Собрать отчёт по выбранной ветке: параллельно short_summary, key_factors, таблица.

    prompt_provider — набор промптов (SummarizerPrompt или legacy-набор
    из summarize_prompts_legacy для A/B-харнесса). precompute_cfg — конфиг
    предвычислений (None → дефолт: всё code). Если передан cfg и провайдер
    не переопределён явно — провайдер собирается по конфигу
    (make_prompt_provider); явный провайдер имеет приоритет (харнесс).
    """
    scale_info = _get_scale_info(data)
    root = _root_node(data)
    plan_alias = data.get("plan_alias") or root.get("plan_alias") or "План"
    fact_alias = data.get("fact_alias") or root.get("fact_alias") or "Факт"
    scale_info["plan_alias"] = plan_alias.lower()
    scale_info["fact_alias"] = fact_alias.lower()

    # Конфиг предвычислений: None → дефолт (всё code, текущее поведение)
    cfg = validate_precompute_cfg(precompute_cfg)
    names_code = cfg["names"]["allowed"] == MODE_CODE
    numbers_code = cfg["numbers"]["mode"] == MODE_CODE

    # Убираем sibling-duplicate: два элемента data[] с одинаковыми суммами,
    # где один без top_factors (пустая обёртка), а другой — с детализацией
    cleaned_data = _prune_wrapper_trees(data)

    # Белый список имён — только при names.allowed=code (llm-режим не ограничивает)
    allowed_names = collect_allowed_names(cleaned_data) if names_code else []

    # Сборка провайдера по конфигу — ДО извлечения промптов; явный
    # провайдер (A/B-харнесс) имеет приоритет над cfg-сборкой.
    if precompute_cfg is not None and prompt_provider is SummarizerPrompt:
        prompt_provider = make_prompt_provider(
            cfg, plan_alias, fact_alias,
            allowed_names if names_code else None,
        )

    summary_prompt = prompt_provider.SHORT_SUMMARY_PROMPTS[branch]
    factors_prompt = prompt_provider.KEY_FACTORS_PROMPTS[branch]

    # Уровень A (AIMIS-2173): числа для текста готовит форматтер — LLM цитирует
    # display-строки; сырые amounts остаются в данных для контекста.
    # numbers=llm (мастер-режим): display не строится — LLM считает сама.
    display_data = enrich_display(cleaned_data, cfg)
    data_with_display = {**display_data, "scale_info": scale_info}
    if names_code:
        # Белый список имён: LLM может упоминать только существующие узлы/срезы
        data_with_display["allowed_names"] = allowed_names

    # Подставляем алиасы вместо {{plan_alias}}/{{fact_alias}} в промпты
    summary_prompt = summary_prompt.replace("{{plan_alias}}", plan_alias).replace("{{fact_alias}}", fact_alias)
    factors_prompt = factors_prompt.replace("{{plan_alias}}", plan_alias).replace("{{fact_alias}}", fact_alias)
    motiv_prompt = prompt_provider.MOTIV_PROMPT.replace("{{plan_alias}}", plan_alias).replace("{{fact_alias}}", fact_alias)

    # Белый список имён инлайн в промпт — надёжнее ссылки на массив в JSON
    allowed_names_str = ", ".join(allowed_names)
    summary_prompt = summary_prompt.replace("{{allowed_names}}", allowed_names_str)
    factors_prompt = factors_prompt.replace("{{allowed_names}}", allowed_names_str)

    tsks = []
    has_motiv = False

    # Прямые последовательные вызовы LLM (без asyncio.create_task — односоединённый прокси)
    client1 = await llm_client_gen_fn()
    short_summary_res = await _base_llm_processing_function(
        summary_prompt, data_with_display, client1, model_summary, client_session_id,
        temperature=temperature
    )
    
    await asyncio.sleep(2)  # пауза между запросами к прокси
    
    client2 = await llm_client_gen_fn()
    key_factors_res = await _base_llm_processing_function(
        factors_prompt, data_with_display, client2, model_summary, client_session_id,
        temperature=temperature
    )
    
    table_res = await render_factor_table_wrapper(cleaned_data)

    # Mотивационная корректировка — последовательно после факторов
    motiv_res_data = ""
    motiv = data.get("motiv_correction")
    if motiv is not None and (motiv.get("plan", 0) != 0 or motiv.get("fact", 0) != 0):
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
        if numbers_code:
            # display-строки мотива готовит код; при numbers=llm их нет —
            # мотив-промпт сам форматирует числа (ветка «display отсутствует»)
            motiv_data["display"] = {
                "plan": format_abs(motiv.get("plan", 0)),
                "fact": format_abs(motiv.get("fact", 0)),
                "plan_before": format_abs(plan_before),
                "fact_before": format_abs(fact_before),
            }
        
        await asyncio.sleep(2)  # пауза после факторов
        motiv_res = await _base_llm_processing_function(
            motiv_prompt, motiv_data, await llm_client_gen_fn(), model_summary, client_session_id,
            temperature=temperature
        )
        motiv_res_data = motiv_res.data if motiv_res.ok else ""

    if not short_summary_res.ok:
        return Res.mk_error(f"Failed build short_summary. err: {short_summary_res.err}")
    if not key_factors_res.ok:
        return Res.mk_error(f"Failed build key_factors. err: {key_factors_res.err}")
    if table_res['ex']:
        return table_res['ex']

    # Сборка финального отчёта
    final_report = short_summary_res.data + "\n\n" + key_factors_res.data

    # Мотивационная корректировка — результат LLM (с явным заголовком-разделителем)
    if motiv_res_data:
        final_report += f"\n\n\n## Влияние мотивационной корректировки\n\n\n{motiv_res_data}"

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
        model_details: str = "GigaChat-3-Ultra",
        client_session_id: str = '-1',
        prompt_provider=SummarizerPrompt,
        precompute_cfg: Optional[Dict] = None,
        temperature: float | None = None,
) -> Res[str]:
    """
    Главная функция саммаризации.
    """
    branch = classify(data)
    return await build_branch_report(
        data, branch, llm_client_gen_fn,
        model_summary=model_summary,
        model_table=model_details,
        client_session_id=client_session_id,
        prompt_provider=prompt_provider,
        precompute_cfg=precompute_cfg,
        temperature=temperature,
    )
