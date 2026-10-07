"""Adhoc: проверка сервера на фикстуре (задача 5.2 aimis-2173-precompute-config).

Запуск: .venv/bin/python src/adhoc/adhoc__check_server_fixture.py
Проверяет:
1. FaServerImpl с дефолтным конфигом (None) стартует
2. FaServerImpl с numbers=llm стартует (валидация проходит)
3. Невалидный конфиг → ValueError на старте (fail-fast)
4. Отчёт с дефолтным конфигом идентичен отчёту без конфига (текущее поведение)
5. numbers=llm даёт legacy-подобный отчёт (промпт со SCALING, без display)
"""

from __future__ import annotations

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, 'src'))

from sdk.giga.iface import AssistantMsg  # noqa: E402
from libfa2.fa_server import FaServerImpl  # noqa: E402
from libfa2.fa_impl.summarize import build_branch_report  # noqa: E402

_FAKE_ANSWER = "## Краткое саммари\nКорень отклонился на -21,7 п.п."

DATA = {
    "data": [{
        "hieararchy_node": "ОД",
        "amounts": {"plan": 100.0, "fact": 80.0,
                    "deviation": -20.0, "impact_to_top_lvl": -20.0},
        "details": {"top_factors": [{
            "hieararchy_node": "Резервы",
            "amounts": {"plan": 100.0, "fact": 80.0,
                        "deviation": -20.0, "impact_to_top_lvl": -20.0},
            "details": {"top_factors": []},
        }]},
    }],
}


def _mock_llm_fn():
    client = MagicMock()
    response = AsyncMock()
    response.ok = True
    response.data = AssistantMsg(_FAKE_ANSWER)
    client.ask_giga = AsyncMock(return_value=response)
    return AsyncMock(return_value=client)


def check_server_construction() -> None:
    kc, dm, da = MagicMock(), MagicMock(), MagicMock()
    # дефолт (конфиг отсутствует) — стартует
    FaServerImpl(kc, dm, da, _mock_llm_fn())
    # numbers=llm — стартует
    FaServerImpl(kc, dm, da, _mock_llm_fn(),
                 precompute_cfg={"numbers": {"mode": "llm"}})
    # невалидный конфиг — fail-fast на конструкторе
    try:
        FaServerImpl(kc, dm, da, _mock_llm_fn(),
                     precompute_cfg={"numbers": {"mode": "bad"}})
    except ValueError as e:
        print(f"fail-fast OK: {e}")
    else:
        raise AssertionError("невалидный конфиг не должен давать серверу стартовать")
    print("server construction OK (default / numbers=llm / invalid)")


async def _report(precompute_cfg=None) -> str:
    client = MagicMock()
    response = AsyncMock()
    response.ok = True
    response.data = AssistantMsg(_FAKE_ANSWER)
    client.ask_giga = AsyncMock(return_value=response)
    res = await build_branch_report(
        DATA, 3, AsyncMock(return_value=client),
        precompute_cfg=precompute_cfg,
    )
    assert res.ok, res.err
    return res.data


def check_report_identity() -> None:
    baseline = asyncio.run(_report(None))
    default_cfg = asyncio.run(_report({}))
    assert baseline == default_cfg, "дефолтный конфиг должен давать отчёт, идентичный текущему"
    print("report identity OK (default cfg == no cfg)")

    llm_client = MagicMock()
    first_prompt = MagicMock()

    async def _capture(prompt_provider_unused=None, cfg=None):
        client = MagicMock()
        response = AsyncMock()
        response.ok = True
        response.data = AssistantMsg(_FAKE_ANSWER)
        client.ask_giga = AsyncMock(return_value=response)
        res = await build_branch_report(
            DATA, 3, AsyncMock(return_value=client),
            precompute_cfg=cfg,
        )
        assert res.ok
        return client.ask_giga.call_args_list[0][1]["msgs"][0].prompt

    llm_prompt = asyncio.run(_capture(cfg={"numbers": {"mode": "llm"}}))
    assert "SCALING" in llm_prompt and "display." not in llm_prompt
    print("numbers=llm report path OK (legacy-подобный промпт со SCALING)")


if __name__ == "__main__":
    check_server_construction()
    check_report_identity()
    print("SERVER-FIXTURE CHECK OK")
