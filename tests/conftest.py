"""Конфигурация pytest: настройка sys.path для импорта пакетов проекта.

Пакет libfa2 использует абсолютные импорты вида ``from libfa2 import ...``,
поэтому каталог ``src`` должен быть в sys.path. SDK (``sdk``) ставится
как editable-пакет aimis-sdk и импортируется напрямую.
"""

from __future__ import annotations

import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC_DIR = os.path.join(_PROJECT_ROOT, 'src')

# sdk.core.logging по умолчанию пишет в /app/logs (недоступно локально) —
# переопределяем до импорта sdk.
os.environ.setdefault('AIMIS_LOGS_DIR', os.path.join(_PROJECT_ROOT, 'logs', 'tests'))

for path in (_PROJECT_ROOT, _SRC_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)
