"""Adhoc: проверка совместимости A/B-харнесса (задача 4.3).

Запуск: .venv/bin/python src/adhoc/adhoc__check_ab_compat.py
Проверяет: импорт харнесса, варианты legacy/new на месте, прямые вызовы
summarize/enrich_display без cfg работают, MoCK-прогон run-пути.
"""

from __future__ import annotations

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, 'src'))

from sdk.giga.iface import AssistantMsg  # noqa: E402
from adhoc import adhoc__ab_prompt_runs as harness  # noqa: E402
from libfa2.fa_impl.value_formatter import enrich_display  # noqa: E402
from libfa2.fa_impl.summarize import summarize  # noqa: E402

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


def main() -> None:
    assert "legacy" in harness.VARIANTS and "new" in harness.VARIANTS, "варианты харнесса на месте"
    # прямые вызовы без cfg — как в харнессе
    enriched = enrich_display(DATA)
    assert "display" in enriched["data"][0]

    mock_client = MagicMock()
    mock_response = AsyncMock()
    mock_response.ok = True
    mock_response.data = AssistantMsg("## Краткое саммари\nтест")
    mock_client.ask_giga = AsyncMock(return_value=mock_response)

    for name, variant in harness.VARIANTS.items():
        provider = variant["prompt_provider"] if isinstance(variant, dict) else variant
        res = asyncio.run(summarize(
            DATA, AsyncMock(return_value=mock_client),
            prompt_provider=provider,
        ))
        assert res.ok, f"summarize failed for variant {name}: {res.err}"
        print(f"variant '{name}': summarize OK")

    # без явного провайдера тоже работает (дефолт)
    res = asyncio.run(summarize(DATA, AsyncMock(return_value=mock_client)))
    assert res.ok
    print("default (no provider): summarize OK")
    print("AB-COMPAT OK")


if __name__ == "__main__":
    main()
