"""
adhoc__ab_prompt_runs.py — A/B-харнесс промптов и моделей саммаризации (AIMIS-2173)
====================================================================================

НЕ прод: запускается вручную с доступом к GigaChat-прокси и KeyDB.

Схема (design.md D3):
  для каждой фикстуры из tmp/json/*.json:
    для variant in [legacy, new]:                    # legacy = снимок до ревизии
      для model in [AB_MODEL, AB_MODEL_LEGACY]:      # две модели для сравнения
        для run in 1..RUNS (10):
          summarize() → отчёт (последовательно, штатная параллельность внутри)
          → валидатор-оракул → ошибки по 8 классам
  выход:
    tmp/reports/{fixture}__{variant}__{model}__run{i}.md
    tmp/ab_report.json
    сводная таблица fixture × variant × model × класс ошибки в stdout

Условия честного сравнения: пониженная температура (AB_TEMPERATURE=0.1),
кэша в пути summarize нет, прогоны строго последовательные. LLM-клиент
кэшируется (один на весь харнесс вместо трёх на отчёт). Между прогонами —
пауза (защита от 429 односоединённого прокси).

Запуск:
  PYTHONPATH=src python src/adhoc/adhoc__ab_prompt_runs.py [--runs 10] [--pause 5]
"""

from __future__ import annotations

import asyncio
import datetime
import json
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional

from sdk.tools.settings import FileTools

from libfa2.fa_impl import summarize_prompts, summarize_prompts_legacy
from libfa2.fa_impl.summarize import summarize
from libfa2.fa_impl.value_formatter import enrich_display

from adhoc.adhoc_test_calc_dev import get_llm_client
from adhoc.summary_validator import validate_report

# --- конфиг харнесса ----------------------------------------------------------
RUNS_PER_VARIANT = 10
# Две модели: основная (GigaChat-3-Ultra) и legacy-модель для сравнения
AB_MODEL = "GigaChat-3-Ultra"
AB_MODEL_LEGACY = "GigaChat-3-Ultra-legacy"
# Пониженная температура для обеих сторон: детерминированное цитирование display.
# 0.0 рискует повторами, 0.1 — минимальный шум без вырождения. Прод-дефолт не меняется.
AB_TEMPERATURE = 0.1
PAUSE_BETWEEN_RUNS_SEC = 5.0     # пауза между прогонами (односоединённый прокси)
PAUSE_ON_ERROR_SEC = 30.0        # пауза при ошибке/429 перед повтором
MAX_RETRIES = 3
VARIANTS: Dict[str, type] = {
    "legacy": summarize_prompts_legacy.SummarizerPrompt,
    "new": summarize_prompts.SummarizerPrompt,
}
MODELS: List[str] = [AB_MODEL, AB_MODEL_LEGACY]
# фильтры быстрой итерации (задаются через --fixture/--variant)
FIXTURE_FILTER: Optional[str] = None
VARIANT_FILTER: Optional[str] = None
# Таблица рендерится детерминированно и не валидируется оракулом —
# отрезаем её от LLM-части отчёта по заголовку
TABLE_HEADER_MARKER = "### Детализация факторного анализа"


_client_cache: Optional[object] = None


async def get_llm_client_cached():
    """Свежий клиент на каждый вызов (как в проде: llm_client_gen_fn вызывается
    на каждый LLM-запрос). Долгоживущий закэшированный клиент копит стейл
    pub/sub-состояние KeyDB и падает ConnectionError через несколько прогонов
    («push messages still pending»). Имя сохранено для совместимости с тестами.
    """
    return await get_llm_client()


def get_tmp_path() -> str:
    # Корень проекта: src/adhoc/<script>.py → parents[2]; tmp/ лежит в корне,
    # а не в src/tmp (куда писали старые adhoc-скрипты)
    return str(Path(__file__).resolve().parents[2] / 'tmp')


def _llm_part_of_report(report: str) -> str:
    """LLM-текст без детерминированной таблицы (числа таблицы — не цитаты display)."""
    idx = report.find(TABLE_HEADER_MARKER)
    return report if idx < 0 else report[:idx]


async def _summarize_with_retry(
        data: Dict, client_fn: Callable, prompt_provider, model: str
):
    """summarize() с повторами при ошибке (429/сеть).

    client_session_id="system" — системный бессессионный вызов (требование
    SDK _check_csid на реальном стенде; прод передаёт реальный csid).
    Соединительные исключения (coredis/сеть) ловятся и ретраятся как ошибки.
    """
    res = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            res = await summarize(
                data, client_fn,
                model_summary=model, model_details=model,
                client_session_id="system",
                prompt_provider=prompt_provider,
                temperature=AB_TEMPERATURE,
            )
            if res.ok:
                return res
        except Exception as e:  # coredis ConnectionError, сеть и пр.
            res = _ResProxy(str(e))
        if attempt < MAX_RETRIES:
            print(f'    summarize failed ({res.err}); retry {attempt}/{MAX_RETRIES - 1} '
                  f'after {PAUSE_ON_ERROR_SEC}s')
            await asyncio.sleep(PAUSE_ON_ERROR_SEC)
    return res


class _ResProxy:
    """Заглушка Res для соединительных исключений (ok=False, err=str)."""

    def __init__(self, err: str):
        self.ok = False
        self.err = err
        self.data = None


async def run_variant(
        fixture_name: str,
        data: Dict,
        variant_name: str,
        prompt_provider,
        model: str,
        reports_dir: str,
) -> List[Dict]:
    """10 последовательных независимых прогонов одного варианта; возвращает логи."""
    enriched = enrich_display(data)
    logs: List[Dict] = []
    for i in range(1, RUNS_PER_VARIANT + 1):
        t0 = datetime.datetime.now()
        res = await _summarize_with_retry(data, get_llm_client_cached, prompt_provider, model)
        dt = (datetime.datetime.now() - t0).total_seconds()

        entry: Dict = {"run": i, "ok": bool(res.ok), "sec": round(dt, 1)}
        if res.ok:
            report = res.data
            validation = validate_report(_llm_part_of_report(report), enriched)
            entry["validation"] = validation.to_dict()
        else:
            entry["error"] = str(res.err)

        fname = FileTools.path_concat(
            reports_dir, f'{fixture_name}__{variant_name}__{model}__run{i}.md'
        )
        FileTools.write_to_file(fname, res.data if res.ok else f'ERROR: {res.err}')

        err_cnt = 0 if not res.ok else len(entry["validation"]["errors"])
        print(f'    [{variant_name}/{model[:12]}] run {i}/{RUNS_PER_VARIANT}: '
              f'{"ok" if res.ok else "FAILED"}, errors={err_cnt}, {dt:.1f}s')

        logs.append(entry)
        if i < RUNS_PER_VARIANT:
            await asyncio.sleep(PAUSE_BETWEEN_RUNS_SEC)
    return logs


def _aggregate(logs: List[Dict]) -> Dict:
    """Счётчики ошибок по классам для списка прогонов."""
    totals = {c: 0 for c in (
        "INVENTED_NUMBER", "INVENTED_FACTOR", "WRONG_SCALE", "INVENTED_DRIVER",
        "WRONG_MARKER", "DYNAMICS_LANGUAGE", "UNALLOWED_NAME", "REPACKED_PLAN_FACT",
    )}
    ok_runs, failed_runs = 0, 0
    for entry in logs:
        if entry.get("ok"):
            ok_runs += 1
            for e in entry.get("validation", {}).get("errors", []):
                totals[e["error_class"]] = totals.get(e["error_class"], 0) + 1
        else:
            failed_runs += 1
    return {"ok_runs": ok_runs, "failed_runs": failed_runs,
            "total_errors": sum(totals.values()), "by_class": totals}


async def main() -> None:
    tmp_path = get_tmp_path()
    reports_dir = FileTools.path_concat(tmp_path, 'reports')
    json_dir = FileTools.path_concat(tmp_path, 'json')
    Path(reports_dir).mkdir(parents=True, exist_ok=True)

    fixtures = sorted(Path(json_dir).glob('*.json'))
    if not fixtures:
        print(f'Нет фикстур в {json_dir} — положите JSON-файлы (задача 5.4)')
        sys.exit(1)
    if FIXTURE_FILTER:
        fixtures = [f for f in fixtures if FIXTURE_FILTER in f.name]
        print(f'Фильтр fixture={FIXTURE_FILTER!r}: {len(fixtures)} шт.')
    variants = {k: v for k, v in VARIANTS.items() if VARIANT_FILTER in (None, k)}
    if VARIANT_FILTER:
        print(f'Фильтр variant={VARIANT_FILTER!r}: {list(variants)}')

    print(f'A/B: fixtures={len(fixtures)}, variants={list(VARIANTS)}, '
          f'models={MODELS}, runs={RUNS_PER_VARIANT}/variant, '
          f'temp={AB_TEMPERATURE}')

    ab_report: Dict = {
        "model": MODELS,
        "runs_per_variant": RUNS_PER_VARIANT,
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "fixtures": {},
    }

    for fx in fixtures:
        fixture_name = fx.stem
        print(f'==== Fixture {fixture_name} ======')
        raw = json.loads(FileTools.read_all_file_contents(str(fx)))
        data = raw if "data" in raw else {"data": [raw]}

        fx_result: Dict = {}
        for variant_name, provider in variants.items():
            fx_result[variant_name] = {"runs": [], "totals": {}}
            for model in MODELS:
                print(f'  -- variant: {variant_name}, model: {model} --')
                logs = await run_variant(fixture_name, data, variant_name,
                                         provider, model, reports_dir)
                fx_result[variant_name]["runs"].extend(
                    [{"model": model, **r} for r in logs]
                )
                fx_result[variant_name]["totals"].update(_aggregate(logs))

        ab_report["fixtures"][fixture_name] = fx_result

    # сводка по variant+model
    present_variants = [v for v in VARIANTS
                        if any(v in fx for fx in ab_report["fixtures"].values())]
    ab_report["summary"] = {
        f"{v}@{m}": {
            "total_errors": sum(
                fx[v]["totals"]["total_errors"] for fx in ab_report["fixtures"].values()
                if v in fx
            ),
            "by_class": {
                cls: sum(fx[v]["totals"]["by_class"].get(cls, 0)
                         for fx in ab_report["fixtures"].values() if v in fx)
                for cls in _aggregate([])
            } if ab_report["fixtures"] else {},
        }
        for v in present_variants
        for m in MODELS
    }

    out_path = FileTools.path_concat(tmp_path, 'ab_report.json')
    FileTools.write_to_file(out_path, json.dumps(ab_report, ensure_ascii=False, indent=2))

    print('\n==== A/B SUMMARY (fixture × variant × model × class) ====')
    classes = list(_aggregate([])["by_class"])
    header = f'{"fixture":<28} {"variant":<8} {"model":<22} {"ok":>3} {"fail":>4} {"total":>5} | ' + ' '.join(f'{c[:12]:>12}' for c in classes)
    print(header)
    for fname, fx in ab_report["fixtures"].items():
        for v in fx:
            for m in MODELS:
                key = f"{v}@{m}"
                t = fx[v]["totals"]
                label = f'{v}×{m[:8]}'
                print(f'{fname[:28]:<28} {label:<8} {t["ok_runs"]:>3} {t["failed_runs"]:>4} {t["total_errors"]:>5} | '
                      + ' '.join(f'{t["by_class"].get(c, 0):>12}' for c in classes))
    print(f'\nОтчёт: {out_path}')

    # критерий приёмки: new на основной модели — 0 ошибок
    new_main = ab_report["summary"].get(f"new@{AB_MODEL}", {}).get("total_errors", 0)
    print(f'CRITERION new@{AB_MODEL[:12]}=0 errors: {"PASS ✓" if new_main == 0 else f"FAIL ({new_main} errors) — править промпт и повторить (задача 6.3)"}')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='A/B прогонов промптов и моделей саммаризации')
    parser.add_argument('--runs', type=int, default=RUNS_PER_VARIANT)
    parser.add_argument('--pause', type=float, default=PAUSE_BETWEEN_RUNS_SEC)
    parser.add_argument('--fixture', type=str, default=None,
                        help='подстрока имени файла фикстуры (быстрая итерация)')
    parser.add_argument('--variant', type=str, default=None, choices=list(VARIANTS),
                        help='только один вариант (new/legacy)')
    parser.add_argument('--model', type=str, default=None, choices=MODELS,
                        help='только одна модель')
    args = parser.parse_args()
    RUNS_PER_VARIANT = args.runs
    PAUSE_BETWEEN_RUNS_SEC = args.pause
    FIXTURE_FILTER = args.fixture
    VARIANT_FILTER = args.variant
    if args.model:
        MODELS[:] = [args.model]  # mutate в place
    asyncio.run(main())
