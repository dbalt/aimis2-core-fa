"""Adhoc: проверка golden-резолюции промптов против снапшота.

Запуск: .venv/bin/python src/adhoc/adhoc__check_golden_prompts.py
"""

from __future__ import annotations

import difflib
import json
import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, 'src'))

from libfa2.fa_impl import summarize_prompts as sp  # noqa: E402

snap = json.load(open(os.path.join(_PROJECT_ROOT, 'tests', 'golden_prompts_precompute.json')))
ok = True
for b in (1, 2, 3, 4):
    for name, got in (('short', sp.SHORT_SUMMARY_PROMPTS[b]),
                      ('key', sp.KEY_FACTORS_PROMPTS[b])):
        want = snap[name][str(b)]
        if got != want:
            ok = False
            print(f'MISMATCH {name}[{b}]')
            for line in list(difflib.unified_diff(
                    want.splitlines(), got.splitlines(), lineterm=''))[:30]:
                print(line)
if sp.MOTIV_PROMPT != snap['motiv']:
    ok = False
    print('MISMATCH motiv')
print('GOLDEN OK' if ok else 'GOLDEN FAIL')
