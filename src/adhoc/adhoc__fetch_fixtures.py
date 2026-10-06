"""
adhoc__fetch_fixtures.py — выгрузка JSON-фикстур для A/B-харнесса (AIMIS-2173)
==============================================================================

НЕ прод. Читает data из missa_aimis.t_aimis__fa__results по известным
кодам прод-инцидентов и складывает в tmp/json/{code}__{dt}.json.
Прод-саммари (сгенерированы старым промптом — сами инциденты)
сохраняются рядом в tmp/reports/{code}__{dt}__PROD.md для сверки.

Запуск: PYTHONPATH=src python src/adhoc/adhoc__fetch_fixtures.py
"""

from __future__ import annotations

import asyncio
import datetime
import json
from pathlib import Path

from sdk.tools.settings import FileTools

from libfa2.data_access.data_mgmt import DataMgmtDataGate

# 5 прод-инцидентов (коды дал заказчик, AIMIS-2173)
FIXTURES = [
    ("3ba67ea1550a87ab819262e232f9b559", "2026-09-30"),   # Чистая прибыль: выдуманные драйверы, «1 105 млн»
    ("611483b55cee04624baea7b28f27e468", "2026-09-30"),   # Чистая прибыль: выдуманная вложенность налога
    ("252fe9ff02fca7b0c1d2d84bc91fef67", "2026-08-31"),   # ОД после резервов: «рост страховых выплат»
    ("75a21dbcc2266e39a61d08d89c8ad589", "2026-08-31"),   # Инкассация: нарративная выдумка
    ("797d34cb9d715986fe9d8f9de7b7aac5", "2026-12-31"),   # ОД после резервов: REPACKED_PLAN_FACT
]


def get_tmp_path() -> str:
    # Корень проекта: src/adhoc/<script>.py → parents[2]
    return str(Path(__file__).resolve().parents[2] / 'tmp')


async def main() -> None:
    tmp = get_tmp_path()
    json_dir = FileTools.path_concat(tmp, 'json')
    prod_dir = FileTools.path_concat(tmp, 'reports')
    Path(json_dir).mkdir(parents=True, exist_ok=True)
    Path(prod_dir).mkdir(parents=True, exist_ok=True)

    from adhoc.adhoc_test_calc_dev import _instantiate_keydb
    kc = await _instantiate_keydb()
    dm = DataMgmtDataGate(
        kc, 'missa_aimis.t_aimis__fa__metadata', 'missa_aimis.t_aimis__fa__results'
    )

    for code, dt_str in FIXTURES:
        dt = datetime.date.fromisoformat(dt_str)
        res = await dm.get_results(code, dt)
        if not res.ok:
            print(f'FAIL {code}__{dt_str}: {res.err}')
            continue
        data, summary = res.data
        name = f'{code}__{dt_str}'
        data_path = FileTools.path_concat(json_dir, f'{name}.json')
        FileTools.write_to_file(data_path, json.dumps(data, ensure_ascii=False, indent=1))
        prod_path = FileTools.path_concat(prod_dir, f'{name}__PROD.md')
        FileTools.write_to_file(prod_path, summary)
        print(f'OK   {name}: data={len(json.dumps(data))} chars, prod_summary={len(summary)} chars')

    print('\nФикстуры готовы в tmp/json/ — можно запускать A/B:')


if __name__ == '__main__':
    asyncio.run(main())
