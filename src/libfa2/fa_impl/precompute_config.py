"""
precompute_config.py — конфигурация предвычислений саммаризации
================================================================

Ручка code|llm на каждый параметр, который до этого изменения код готовил
для LLM безусловно (уровень A, AIMIS-2173):

    numbers    — display-строки чисел (+ мотив-блок и margin-пара ratio:
                 неразделимы с числами, отдельной ручки нет);
    markers    — маркеры 🔴/❇️;
    selection  — отбор значимых факторов (threshold — доля от максимума
                 |вклада| среди соседей; similarity — порог похожести
                 соседних факторов в промпте);
    names      — allowed (белый список имён) и children (ограничения
                 «Главного драйвера»).

Режим "code" — значение готовит код (текущее поведение, дефолт);
режим "llm" — значение вычисляет LLM по правилам legacy-промптов,
соответствующие поля в данных не генерируются.

Мастер-нормализация: numbers=llm форсирует llm для markers/selection/names —
без display-строк остальным code-правилам не на что ссылаться.

Валидация fail-fast: вызывается на старте сервера; невалидный конфиг —
ValueError с именем ключа и допустимыми значениями.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, Optional

MODE_CODE = "code"
MODE_LLM = "llm"
_MODES = (MODE_CODE, MODE_LLM)

DEFAULT_THRESHOLD = 0.30
DEFAULT_SIMILARITY = 0.15

# Дефолт = текущее поведение: всё считается кодом.
DEFAULT_PRECOMPUTE: Dict[str, Dict[str, Any]] = {
    "numbers": {"mode": MODE_CODE},
    "markers": {"mode": MODE_CODE},
    "selection": {
        "mode": MODE_CODE,
        "threshold": DEFAULT_THRESHOLD,
        "similarity": DEFAULT_SIMILARITY,
    },
    "names": {"allowed": MODE_CODE, "children": MODE_CODE},
}


def _err(key: str, expected: str, got: Any) -> ValueError:
    return ValueError(
        f"configs.fa2026.summarize.precompute: некорректное значение {key!r}: "
        f"{got!r}. Ожидалось: {expected}"
    )


def _mode(section: Dict[str, Any], key: str, path: str, default: str) -> str:
    """Читает mode-ручку (значение code|llm) из секции."""
    if key not in section:
        return default
    val = section[key]
    if val not in _MODES:
        raise _err(f"{path}.{key}", "'code' или 'llm'", val)
    return val


def _number(section: Dict[str, Any], key: str, path: str, default: float,
            lo: float, hi: Optional[float]) -> float:
    """Читает числовой порог: lo < value < hi (hi=None — без верхней границы)."""
    if key not in section:
        return default
    val = section[key]
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise _err(f"{path}.{key}", "число", val)
    if not (lo < val and (hi is None or val < hi)):
        bound = f"число в диапазоне {lo} < значение" + (f" < {hi}" if hi is not None else "")
        raise _err(f"{path}.{key}", bound, val)
    return float(val)


def _known_keys(raw: Dict[str, Any], allowed: tuple, path: str) -> None:
    unknown = set(raw) - set(allowed)
    if unknown:
        raise _err(path, f"ключи {sorted(allowed)}", f"неизвестные ключи {sorted(unknown)}")


def validate_precompute_cfg(raw: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """raw → полная нормализованная конфигурация (deep copy).

    None/пустой словарь → DEFAULT_PRECOMPUTE. Неизвестные ключи, недопустимые
    значения режимов и порогов вне диапазонов → ValueError. После нормализации
    конфиг внутренне согласован: numbers=llm форсирует llm для остальных ручек.
    """
    if raw is None:
        return copy.deepcopy(DEFAULT_PRECOMPUTE)
    if not isinstance(raw, dict):
        raise _err("", "словарь (dict)", type(raw).__name__)
    _known_keys(raw, ("numbers", "markers", "selection", "names"), "")

    numbers = raw.get("numbers") or {}
    markers = raw.get("markers") or {}
    selection = raw.get("selection") or {}
    names = raw.get("names") or {}
    for path, section, allowed in (
        ("numbers", numbers, ("mode",)),
        ("markers", markers, ("mode",)),
        ("selection", selection, ("mode", "threshold", "similarity")),
        ("names", names, ("allowed", "children")),
    ):
        if not isinstance(section, dict):
            raise _err(path, "словарь (dict)", type(section).__name__)
        _known_keys(section, allowed, path)

    cfg: Dict[str, Dict[str, Any]] = {
        "numbers": {"mode": _mode(numbers, "mode", "numbers", MODE_CODE)},
        "markers": {"mode": _mode(markers, "mode", "markers", MODE_CODE)},
        "selection": {
            "mode": _mode(selection, "mode", "selection", MODE_CODE),
            "threshold": _number(selection, "threshold", "selection",
                                 DEFAULT_THRESHOLD, 0.0, None),
            "similarity": _number(selection, "similarity", "selection",
                                  DEFAULT_SIMILARITY, 0.0, 1.0),
        },
        "names": {
            "allowed": _mode(names, "allowed", "names", MODE_CODE),
            "children": _mode(names, "children", "names", MODE_CODE),
        },
    }

    # Мастер-нормализация: без display-строк чисел остальным code-правилам
    # не на что ссылаться.
    if cfg["numbers"]["mode"] == MODE_LLM:
        cfg["markers"]["mode"] = MODE_LLM
        cfg["selection"]["mode"] = MODE_LLM
        cfg["names"]["allowed"] = MODE_LLM
        cfg["names"]["children"] = MODE_LLM
    return cfg


def pct_str(value: float) -> str:
    """0.30 → '30', 0.075 → '7,5' — для подстановки в тексты промптов."""
    s = f"{value * 100:g}".replace(".", ",")
    return s
