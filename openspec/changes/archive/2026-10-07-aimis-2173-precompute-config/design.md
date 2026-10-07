# Design: aimis-2173-precompute-config

## Context

См. proposal.md — Why. Уровень A (AIMIS-2173) дал 5 предвычислений в `value_formatter.py` + `collect_allowed_names()`: display-строки чисел, маркеры 🔴/❇️, флаг `significant` (порог 0.30, константа `SIGNIFICANCE_RATIO`), margin-пара ratio, allowed_names (+`children_names` внутри display). Все — безусловно кодом; промпты жёстко ссылаются на готовые поля («Включай факторы ТОЛЬКО с display.significant = true»). Legacy-промпты (`summarize_prompts_legacy.py`) — готовый источник «llm»-правил: SCALING (строки 49–54), маркеры по знаку (43–44, 60), отбор «>= 30% of largest» (299).

Инфраструктура: параметризация промптов уже есть (`prompt_provider` в `summarize()`/`build_branch_report` — наследие A/B-харнесса); паттерн чтения конфига — `get_conf('configs.fa2026....', default)` в `run__fa_server.py` → конструктор `FaServerImpl` → вниз по цепочке (`all_together.py` → `summarize`). Прокси GigaChat односоединённый — на архитектуру не влияет.

## Goals / Non-Goals

**Goals:**

- Ручка `code|llm` на каждый предвычисляемый параметр + настраиваемые пороги отбора; дефолт — текущее поведение.
- Сборка промптов по конфигу (одна база промптов + плейсхолдеры, не 2⁵ наборов).
- Fail-fast валидация конфига на старте сервера.
- Сохранение совместимости с A/B-харнессом (любой вариант = конфиг).

**Non-Goals:**

- Runtime-перечитывание конфига на каждый запрос (конфиг читается один раз на старте).
- Новые предвычисления сверх существующих пяти (расширение списка — будущий change).
- Изменения протокола `fa2026`, SDK, KeyDB-инфраструктуры.
- Ретраи/очереди прокси.

## Decisions

### D1. Форма конфига: вложенный словарь с плоскими ручками mode

```python
DEFAULT_PRECOMPUTE = {
    "numbers":  {"mode": "code"},   # + мотив-блок + margin-пара ratio (неразделимы)
    "markers":  {"mode": "code"},
    "selection": {"mode": "code", "threshold": 0.30, "similarity": 0.15},
    "names":    {"allowed": "code", "children": "code"},
}
```

- Пороги живут внутри своих секций (требование «вложенность для 30%»); применяются в обоих режимах: `code` — кодом, `llm` — подстановкой в промпт.
- `similarity` всегда в промпте (компоновка текста, код её не вычисляет) — ручка лишь параметризует число.
- **Мастер-переключатель**: `numbers: "llm"` форсирует `llm` для `markers`/`selection`/`names` (display-полей нет — код-правилам не на что ссылаться). Нормализация выполняется в валидаторе: конфиг после `validate()` всегда внутренне согласован.
- **Мотив-блок и margin-пара — за `numbers`**, отдельных ручек нет (решение по итогам обсуждения: раздельные режимы дали бы смешанные правила цитирования чисел в одном отчёте).

**Альтернатива (отклонена):** валидировать противоречивые комбинации ошибкой вместо нормализации — жёстче, но неудобно операционно: частичное включение `numbers: llm` — типовой сценарий «вернуть LLM всё, кроме…», а не ошибка конфигурации.

### D2. Валидатор — чистая функция, fail-fast на старте

`validate_precompute_cfg(raw) -> NormalizedPrecomputeCfg` (модуль рядом с `value_formatter.py` или в `summarize.py`): типы (`code|llm`), диапазоны (0 < threshold, 0 < similarity < 1), неизвестные ключи → `ValueError` с именем ключа и допустимыми значениями. Вызов в `run__fa_server.py` сразу после `get_conf`; невалидно — сервер не стартует. Unit-тестируется без KeyDB.

### D3. Сборка промптов: плейсхолдеры + make_prompt_provider

- Актуальные промпты (`summarize_prompts.py`) размечаются плейсхолдерами: `{{numbers_rule}}`, `{{marker_rule}}`, `{{selection_rule}}`, `{{names_rule}}` (в местах, где сейчас захардкожены code-инструкции).
- `make_prompt_provider(cfg, plan_alias, fact_alias, allowed_names) -> PromptProvider` — функция, собирающая наборы промптов: для `code`-ручек подставляются текущие инструкции (цитирование display), для `llm` — фрагменты из legacy-текстов с подстановкой порогов. Возвращает объект с тем же интерфейсом (`SHORT_SUMMARY_PROMPTS`, `KEY_FACTORS_PROMPTS`, `MOTIV_PROMPT`), что и `SummarizerPrompt` — `build_branch_report` меняется минимально (замена дефолта `prompt_provider=SummarizerPrompt` на `prompt_provider=None` → сборка по cfg).
- A/B-харнесс совместим: `summarize_prompts_legacy` продолжает работать как provider; новая ручка конфига покрывает тот же спектр без monkeypatch.
- **Legacy-тексты более не удаляются по завершении AIMIS-2173** — остаются в коде как источник `llm`-правил (правка решения того change'а).

**Альтернатива (отклонена):** полный набор промптов на каждую комбинацию ручек (2⁵) — комбинаторный взрыв и дублирование текстов.

### D4. Параметризация value_formatter

`enrich_display(data, precompute_cfg)` (+ параметр в `_walk`/`_display_for_node`): `code`-ручки кладут свои поля в `display`; `llm`-ручки — не кладут (числа → нет display вообще; markers → нет ключа `marker`; selection → нет `significant`; names.children → нет `children_names`). Дефолт cfg — текущее поведение. `collect_allowed_names()` вызывается только при `names.allowed: "code"`.

### D5. Плумбинг

```
run__fa_server.py: get_conf('configs.fa2026.summarize.precompute', DEFAULT)
  → validate_precompute_cfg() → raise при невалидном
  → FaServerImpl(..., precompute_cfg)          # доп. аргумент конструктора
  → calculate_and_summarize_deviation(..., precompute_cfg)
  → summarize(..., precompute_cfg) → build_branch_report
      ├─ enrich_display(cleaned_data, precompute_cfg)
      └─ make_prompt_provider(precompute_cfg, plan_alias, fact_alias, allowed_names)
```

По образцу `model_summary`/`model_details`; во всех сигнатурах — keyword-аргумент с дефолтом `None` (= DEFAULT), публичные вызовы назад совместимы.

## Risks / Trade-offs

- [Комбинаторика промптов: 2⁵ теоретически, меньше после нормализации] → плейсхолдеры вместо наборов; юнит-тесты на ключевые комбинации (все code; все llm; numbers llm + остальное code; selection с порогами).
- [LLM-режим возвращает класс ошибок AIMIS-2173 (масштаб, выдумки)] → это осознанный выбор конфига; правила из legacy-промптов — проверенное до-Ultra поведение; A/B-сравнение доступно тем же механизмом.
- [Двойной источник правды правил (промпты ↔ legacy)] → `llm`-фрагменты вырезаются из legacy-текстов единообразно; при правке code-правил синхронно проверять llm-фрагменты (пункт в tasks).
- [Забыть прокинуть cfg в новую точку вызова summarize] → дефолт `None` = DEFAULT cfg: пропуск плумбинга деградирует к текущему поведению, не к ошибке; тест на прокидку из fa_server.
- [threshold=0 / similarity→1 вырожденные конфиги] → валидация диапазонов; граничные значения фиксируются юнит-тестами (0 < threshold, не запрещаем threshold > 1 — «значим только максимум» легитимно).

## Migration Plan

1. Валидатор + DEFAULT_PRECOMPUTE + unit-тесты.
2. Параметризация `enrich_display`/`collect_allowed_names` + тесты.
3. Плейсхолдеры в промптах + `make_prompt_provider` + тесты комбинаций.
4. Плумбинг (`run__fa_server` → `FaServerImpl` → `all_together` → `summarize`).
5. Деплой без изменений в KeyDB (дефолт = текущее поведение); включение ручек — операционная задача конфига, не кода.
6. Откат: revert; конфиг-ключ опционален и просто игнорируется старой версией.

## Open Questions

- ~~Точное место модуля валидатора (рядом с `value_formatter.py` vs отдельный `precompute_config.py`)~~ — РЕШЕНО при имплементации: отдельный модуль `src/libfa2/fa_impl/precompute_config.py` (его импортируют `value_formatter`, `summarize_prompts`, `summarize`, `fa_server`, `run__fa_server` — отдельный файл исключает циклические импорты).
