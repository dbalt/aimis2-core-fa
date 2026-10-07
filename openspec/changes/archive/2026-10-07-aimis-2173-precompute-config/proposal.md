# Proposal: aimis-2173-precompute-config — конфигурация предвычислений саммаризации

## Why

После AIMIS-2173 (уровень A) предвычисления для LLM (display-строки чисел, маркеры 🔴/❇️, отбор значимых факторов по порогу 30%, белый список имён) жёстко зашиты в коде: `value_formatter.py` и тексты `summarize_prompts.py`. Нужна возможность через конфиг сервиса выбирать для каждого параметра, готовит ли его код или отдает на откуп LLM (как в legacy-промптах до AIMIS-2173), а порог значимости 30% — настраивать. Пригодится и для A/B-сравнения «код vs LLM» тем же механизмом.

## What Changes

- Новый конфиг KeyDB `configs.fa2026.summarize.precompute` — вложенный словарь с ручкой `mode: code|llm` на каждый предвычисляемый параметр:
  - `numbers` — display-строки чисел (план/факт/отклонение/вклад; включает мотив-блок и margin-пару ratio — неразделимы, одна ручка);
  - `markers` — маркеры 🔴/❇️;
  - `selection` — отбор значимых факторов, с настраиваемыми `threshold` (по умолчанию 0.30) и `similarity` (0.15);
  - `names.allowed` — белый список имён; `names.children` — children_names/EDGE CASE «Главного драйвера».
- Дефолт (конфиг отсутствует) — все ручки `code`, пороги 0.30/0.15: поведение не меняется.
- `mode: "llm"` — параметр считает LLM по правилам legacy-промптов (`summarize_prompts_legacy.py`); соответствующие поля display не генерируются. `numbers: "llm"` форсирует `llm` для остальных ручек (display-полей нет — не на что ссылаться).
- Сборка промптов по конфигу: плейсхолдеры `{{numbers_rule}}`/`{{marker_rule}}`/`{{selection_rule}}`/`{{names_rule}}` в актуальных промптах; `llm`-варианты правил — из legacy-текстов с подстановкой порогов.
- `make_prompt_provider(cfg, plan_alias, fact_alias, allowed_names)` — функция вместо статического класса `SummarizerPrompt` в `build_branch_report` (расширение параметризации AIMIS-2173, интерфейс совместим с A/B-харнессом).
- Плумбинг конфига по образцу `model_summary`/`model_details`: `run__fa_server.py` → `FaServerImpl` → `calculate_and_summarize_deviation` → `summarize`/`build_branch_report` → `enrich_display(data, cfg)`.
- Валидация конфига на старте сервера (fail-fast): типы значений `code|llm`, диапазоны порогов (0 < threshold, 0 < similarity < 1), неизвестные ключи; невалидно — raise, сервер не стартует.

## Capabilities

### New Capabilities
- `summarize-precompute-config`: конфигурируемые предвычисления саммаризации — выбор code/llm на параметр, настраиваемые пороги отбора, валидация на старте, дефолт = всё кодом.

### Modified Capabilities

## Impact

- Код: `src/libfa2/fa_impl/value_formatter.py` (параметризация), `summarize_prompts.py` (плейсхолдеры), `summarize.py` (make_prompt_provider, cfg-плумбинг), `fa_server.py`, `run__fa_server.py` (чтение get_conf + валидация), `all_together.py` (передача cfg).
- Конфиг: новый ключ `configs.fa2026.summarize.precompute` в KeyDB (не обязателен — есть дефолт в коде).
- Протокол `fa2026`, SDK, БД — без изменений. Юнит-тесты: `value_formatter`, валидатор конфига, сборка промптов по комбинациям ручек.
