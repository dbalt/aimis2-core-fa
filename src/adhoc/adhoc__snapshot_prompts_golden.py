"""Adhoc: снять golden-снапшот промптов (до разметки плейсхолдерами).

Запуск: .venv/bin/python src/adhoc/adhoc__snapshot_prompts_golden.py
Создаёт tests/golden_prompts_precompute.json — эталон текстов на момент
старта change aimis-2173-precompute-config (для регрессионного теста).
"""

from __future__ import annotations

import json
import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, 'src'))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, 'src', 'libfa2', 'fa_impl'))

import summarize_prompts as sp  # noqa: E402

OUT_PATH = os.path.join(_PROJECT_ROOT, 'tests', 'golden_prompts_precompute.json')

data = {
    'short': sp.SHORT_SUMMARY_PROMPTS,
    'key': sp.KEY_FACTORS_PROMPTS,
    'motiv': sp.MOTIV_PROMPT,
}
with open(OUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=1)
print('snapshotted ->', OUT_PATH)
