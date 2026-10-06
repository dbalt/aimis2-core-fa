"""
summary_validator.py — валидатор-оракул саммари ФА (тестовый, AIMIS-2173)
==========================================================================

Проверяет сгенерированный LLM отчёт по правилам уровня A. НЕ входит в
прод-контур: используется только A/B-харнессом и unit-тестами.

Проверки (вход: отчёт + обогащённые display-данные):
  1. Числа — каждое число текста должно быть цитатой display-строки
     (допуск на эквивалентные представления той же величины);
  2. Имена факторов — подмножество имён узлов входа;
  3. Маркер ↔ знак числа (🔴 только с минусом, ❇️ только с плюсом);
  4. Нет эмодзи кроме 🔴/❇️ (🟢 и прочие — ошибка);
  5. Нет слов динамики («рост», «снижение» и производные);
  6. Имена после «Главный драйвер» — только у узлов с детьми, имя —
     существующий дочерний узел (иначе INVENTED_DRIVER).

Классы ошибок: INVENTED_NUMBER, INVENTED_FACTOR, WRONG_SCALE,
INVENTED_DRIVER, WRONG_MARKER, DYNAMICS_LANGUAGE, UNALLOWED_NAME,
REPACKED_PLAN_FACT.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

# --- классы ошибок (таксономия design.md) -----------------------------------
INVENTED_NUMBER = "INVENTED_NUMBER"
INVENTED_FACTOR = "INVENTED_FACTOR"
WRONG_SCALE = "WRONG_SCALE"
INVENTED_DRIVER = "INVENTED_DRIVER"
WRONG_MARKER = "WRONG_MARKER"
DYNAMICS_LANGUAGE = "DYNAMICS_LANGUAGE"
UNALLOWED_NAME = "UNALLOWED_NAME"
REPACKED_PLAN_FACT = "REPACKED_PLAN_FACT"

ALL_ERROR_CLASSES = [
    INVENTED_NUMBER, INVENTED_FACTOR, WRONG_SCALE, INVENTED_DRIVER,
    WRONG_MARKER, DYNAMICS_LANGUAGE, UNALLOWED_NAME, REPACKED_PLAN_FACT,
]

# --- лексика ----------------------------------------------------------------
# Слова динамики (в любой форме, включая приставки «с-», «по-», «вы-»)
DYNAMICS_WORDS = [
    "рост", "роста", "росту", "ростом", "росте", "росты",
    "снижение", "снижения", "снижению", "снижением", "снижении",
    "снизил", "снизилa", "снизились", "снизился", "снизилась",
    "падение", "падения", "падению", "падением", "падении",
    "упал", "упала", "упало", "упали",
    "вырос", "выросла", "выросло", "выросли",
    "увеличение", "увеличения", "увеличению", "увеличением", "увеличении",
    "увеличил", "увеличила", "увеличило", "увеличились", "увеличился",
    "прирост", "прироста", "приросту", "приростом", "приросте", "приросты",
    "опережающего роста", "замедление", "замедления",
]
_ALLOWED_EMOJI = {"🔴", "❇️"}


@dataclass
class ValidationError:
    """Одна ошибка валидации."""
    error_class: str
    fragment: str          # фрагмент текста, где найдена ошибка
    detail: str = ""       # пояснение (ожидаемое/найденное)

    def to_dict(self) -> Dict[str, str]:
        return {"error_class": self.error_class, "fragment": self.fragment, "detail": self.detail}


@dataclass
class ValidationResult:
    """Результат валидации одного отчёта."""
    errors: List[ValidationError] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def classes(self) -> Dict[str, int]:
        """Счётчик ошибок по классам."""
        out = {c: 0 for c in ALL_ERROR_CLASSES}
        for e in self.errors:
            out[e.error_class] = out.get(e.error_class, 0) + 1
        return out

    def to_dict(self) -> Dict:
        return {"ok": self.ok, "errors": [e.to_dict() for e in self.errors]}


# --- извлечение данных из display --------------------------------------------

def _walk_nodes(nodes: List[Dict]) -> List[Dict]:
    for n in nodes:
        yield n
        children = (n.get("details") or {}).get("top_factors") or []
        yield from _walk_nodes(children)


def collect_display_strings(data: Dict) -> Set[str]:
    """Множество всех display-строк (plan/fact/deviation/impact/margin) входа."""
    out: Set[str] = set()
    for tree in data.get("data") or []:
        for node in _walk_nodes([tree]):
            d = node.get("display") or {}
            for key in ("plan", "fact", "deviation", "impact", "margin_impact", "margin_rub"):
                s = d.get(key)
                if s:
                    out.add(s)
    return out


def collect_node_names(data: Dict) -> Set[str]:
    """Множество имён всех узлов входа (нормализованные)."""
    out: Set[str] = set()
    for tree in data.get("data") or []:
        for node in _walk_nodes([tree]):
            name = (node.get("hieararchy_node") or "").strip()
            if name:
                out.add(name.lower())
            for v in (node.get("analytic_slice") or {}).values():
                if v:
                    out.add(str(v).strip().lower())
    return out


def collect_nodes_with_children(data: Dict) -> Set[str]:
    """Имена узлов, у которых ЕСТЬ дети (для проверок «Главный драйвер»)."""
    out: Set[str] = set()
    for tree in data.get("data") or []:
        for node in _walk_nodes([tree]):
            if (node.get("details") or {}).get("top_factors"):
                name = (node.get("hieararchy_node") or "").strip().lower()
                if name:
                    out.add(name)
    return out


# --- нормализация чисел (допуск на эквивалентные представления) --------------

def _parse_number_str(s: str) -> Optional[float]:
    """'-535,5 млн' / '29 213,6 млрд' / '200 %' → float в базовых единицах.

    Возвращает величину строки в единицах её суффикса (или None, если
    строка не распознана как число с суффиксом).
    """
    s = s.strip()
    m = re.match(r"^([+\-−–]?)((?:\d[\d ]*\d|\d)(?:,\d+)?)(\s*(?:млрд|млн|тыс\.?|руб\.?|п\.п\.|%)?)$", s)
    if not m:
        return None
    sign = -1.0 if m.group(1) else 1.0
    num = float(m.group(2).replace(" ", "").replace(",", "."))
    unit = m.group(3).strip()
    mult = 1.0
    if unit == "млрд":
        mult = 1e9
    elif unit == "млн":
        mult = 1e6
    elif unit in ("тыс.", "тыс"):
        mult = 1e3
    return sign * num * mult


# --- проверки ----------------------------------------------------------------

# число в тексте: [+-]?цифры с пробелами/запятой + опц. суффикс (все виды минусов)
_NUM_RE = re.compile(
    r"[+\-−–]?\d[\d ]*(?:,\d+)?\s*(?:млрд|млн|тыс\.|руб\.|п\.п\.|%)?"
)

_SCALE_JUMPS = (0.001, 0.01, 0.1, 10.0, 100.0, 1000.0)


def _is_scale_jump(val: float, dv: float) -> bool:
    """val ≈ dv × 10^k (k=±1..3) с допуском 5% — потеря/сдвиг разряда или масштаба."""
    if dv == 0:
        return False
    ratio = abs(val) / abs(dv)
    return any(0.95 <= ratio / j <= 1.05 for j in _SCALE_JUMPS)


def _extract_numbers(text: str) -> List[str]:
    """Все числовые токены текста (с суффиксами)."""
    out = []
    for m in _NUM_RE.finditer(text):
        tok = m.group(0).strip()
        if re.search(r"\d", tok):
            out.append(tok)
    return out


def _classify_number(tok: str, display_strings: Set[str]) -> Optional[ValidationError]:
    """Токен → None (цитата/эквивалент), WRONG_SCALE или INVENTED_NUMBER.

    Двухфазно: сперва ищем точное/эквивалентное (1%) совпадение среди ВСЕХ
    display-строк, и лишь потом — сдвиг разряда. Иначе порядок обхода set
    порождает ложный WRONG_SCALE (точная цитата затеняётся соседним числом).
    """
    val = _parse_number_str(tok)
    if val is None:
        return None
    tok_unit = (re.search(r"(млрд|млн|тыс\.?|руб\.?|п\.п\.|%)$", tok) or [None, ""])[1]
    # фаза 1: эквивалентное совпадение (та же величина, тот же суффикс)
    for s in display_strings:
        sv = _parse_number_str(s)
        if sv is None:
            continue
        if abs(val - sv) <= 0.01 * max(abs(val), abs(sv), 1.0):
            ds_unit = (re.search(r"(млрд|млн|тыс\.?|руб\.?|п\.п\.|%)$", s) or [None, ""])[1]
            if tok_unit != ds_unit:
                return ValidationError(WRONG_SCALE, tok, f"та же величина в других единицах, ожидалось «{s}»")
            return None
    # фаза 2: сдвиг разряда/масштаба
    for s in display_strings:
        sv = _parse_number_str(s)
        if sv is None:
            continue
        if _is_scale_jump(val, sv):
            return ValidationError(WRONG_SCALE, tok, f"сдвиг разряда/масштаба относительно «{s}»")
    return ValidationError(INVENTED_NUMBER, tok, "число не является цитатой display-строки")


def _validate_numbers(report: str, display_strings: Set[str]) -> List[ValidationError]:
    errs = []
    for tok in _extract_numbers(report):
        e = _classify_number(tok, display_strings)
        if e is not None:
            errs.append(e)
    return errs


# маркер, затем имя; терминатор — тире с пробелом после, «(» или конец строки.
# Дефис/тире БЕЗ пробела после — часть слова («Инвестиционно-накопительное»).
_BULLET_RE = re.compile(r"(🔴|❇️)\s*\*{0,2}([^*\n]{2,120}?)\*{0,2}\s*(?:[—−–](?=\s)|(?=\())")


def _words_match(a: str, b: str) -> bool:
    """Слово совпадает при падежных формах: вложение или общий префикс ≥5.

    Короткие слова (≤3, союзы/предлоги) — только точное совпадение,
    иначе «и» матчится с «итог» и маскирует выдуманные имена.
    """
    if a == b:
        return True
    if len(a) <= 3 or len(b) <= 3:
        return False
    if a.startswith(b) or b.startswith(a):
        return True
    common = 0
    for ca, cb in zip(a, b):
        if ca != cb:
            break
        common += 1
    return common >= 5


def _name_allowed(head: str, names: Set[str]) -> bool:
    """Имя допустимо, если это точное имя или содержит имя узла как
    непрерывную последовательность слов (падежные формы)."""
    if head in names:
        return True
    hw = re.findall(r"[а-яёa-z]+", head)
    if not hw:
        return False
    for n in names:
        nw = re.findall(r"[а-яёa-z]+", n)
        if not nw or len(nw) > len(hw):
            continue
        for i in range(len(hw) - len(nw) + 1):
            if all(_words_match(hw[i + j], nw[j]) for j in range(len(nw))):
                return True
    return False


def _validate_names(report: str, names: Set[str]) -> List[ValidationError]:
    errs = []
    for m in _BULLET_RE.finditer(report):
        marker, name = m.group(1), m.group(2).strip()
        name_clean = name.strip().lower()
        # имя может быть составным («Название — вклад ...»): берём до первого разделителя
        head = re.split(r"\s+[—,]\s*|\s*\(", name_clean)[0].strip()
        if head and not _name_allowed(head, names):
            errs.append(ValidationError(UNALLOWED_NAME, name, "имя отсутствует во входных данных"))
    return errs


def _validate_markers(report: str) -> List[ValidationError]:
    errs = []
    # маркер ↔ знак: первое число после маркера в строке
    for line in report.splitlines():
        for m in re.finditer(r"(🔴|❇️)", line):
            after = line[m.end():]
            num_match = re.search(r"([+\-−–]?\d[\d ]*(?:,\d+)?)", after)
            if num_match:
                neg = num_match.group(1).startswith(("-", "−", "–"))
                if m.group(1) == "🔴" and not neg:
                    errs.append(ValidationError(WRONG_MARKER, line.strip()[:80], "🔴 с положительным числом"))
                if m.group(1) == "❇️" and neg:
                    errs.append(ValidationError(WRONG_MARKER, line.strip()[:80], "❇️ с отрицательным числом"))
    # запрещённые эмодзи
    for ch in report:
        if ch in _ALLOWED_EMOJI:
            continue
        if 0x1F300 <= ord(ch) <= 0x1FAFF or ord(ch) == 0x1F7E2:
            errs.append(ValidationError(WRONG_MARKER, ch, f"эмодзи {ch!r} не разрешён (только 🔴/❇️)"))
    return errs


def _validate_dynamics(report: str) -> List[ValidationError]:
    errs = []
    lowered = report.lower()
    for w in DYNAMICS_WORDS:
        for m in re.finditer(re.escape(w), lowered):
            start, end = m.start(), m.end()
            # не слово-фрагмент (проверяем границы слова)
            before = lowered[start - 1] if start > 0 else " "
            after = lowered[end] if end < len(lowered) else " "
            if not (before.isalpha() or after.isalpha()):
                frag = report[max(0, start - 30):end + 30]
                errs.append(ValidationError(DYNAMICS_LANGUAGE, frag.strip(), f"слово динамики «{w}»"))
    return errs


_DRIVER_LINE_RE = re.compile(r"[Гг]лавный драйвер[^\n]*")
# имя после «драйвер» — до тире с пробелом после / «(» / конца строки
_DRIVER_NAME_RE = re.compile(r"драйвер\s*[—:-]?\s*\*{0,2}([^*\n(]{2,120}?)\*{0,2}\s*(?:[—−–](?=\s)|(?=\()|$)")


def collect_plan_fact_strings_of_leaves(data: Dict) -> Set[str]:
    """Display-строки plan/fact ЛИСТОВЫХ узлов — их цитата в роли «драйвера»
    означает переупаковку plan/fact (REPACKED_PLAN_FACT)."""
    out: Set[str] = set()
    for tree in data.get("data") or []:
        for node in _walk_nodes([tree]):
            if not (node.get("details") or {}).get("top_factors"):
                d = node.get("display") or {}
                for key in ("plan", "fact"):
                    s = d.get(key)
                    if s:
                        out.add(s)
    return out


def _validate_drivers(report: str, names: Set[str], plan_fact_strings: Set[str]) -> List[ValidationError]:
    errs = []
    for m in _DRIVER_LINE_RE.finditer(report):
        line = m.group(0)
        name_match = _DRIVER_NAME_RE.search(line)
        if not name_match:
            continue
        name = name_match.group(1).strip()
        head = re.split(r"\s+[—,]\s*|\s*\(", name.lower())[0].strip()
        if not _name_allowed(head, names):
            errs.append(ValidationError(
                INVENTED_DRIVER, name, "«Главный драйвер» с именем, отсутствующим в JSON",
            ))
            continue
        # переупаковка plan/fact листового узла в «драйвер»:
        # в строке драйвера фигурирует цитата plan/fact (а не вклада)
        for tok in _extract_numbers(line):
            if tok in plan_fact_strings:
                errs.append(ValidationError(
                    REPACKED_PLAN_FACT, line.strip()[:120],
                    f"«драйвер» со значением plan/fact узла ({tok}); у листового узла нет драйверов",
                ))
                break
    return errs


# --- главная точка входа ------------------------------------------------------

def validate_report(report: str, data: Dict) -> ValidationResult:
    """Валидация отчёта по обогащённым display-данным (enrich_display)."""
    display_strings = collect_display_strings(data)
    names = collect_node_names(data)
    plan_fact_strings = collect_plan_fact_strings_of_leaves(data)

    errors: List[ValidationError] = []
    errors += _validate_numbers(report, display_strings)
    errors += _validate_names(report, names)
    errors += _validate_markers(report)
    errors += _validate_dynamics(report)
    errors += _validate_drivers(report, names, plan_fact_strings)
    return ValidationResult(errors=errors)


def validate_report_json(report: str, data_json: str) -> ValidationResult:
    """Удобная обёртка: данные как JSON-строка."""
    return validate_report(report, json.loads(data_json))
