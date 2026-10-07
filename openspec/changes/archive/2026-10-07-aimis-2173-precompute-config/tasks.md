# Tasks: aimis-2173-precompute-config

## 1. Конфиг и валидатор

- [x] 1.1 Создать модуль предвычисл-конфига: `DEFAULT_PRECOMPUTE` (все mode=code, threshold=0.30, similarity=0.15), `validate_precompute_cfg(raw)` — нормализация, проверка типов `code|llm`, диапазонов (0 < threshold, 0 < similarity < 1), неизвестных ключей; ошибки с именем ключа и допустимыми значениями; мастер-нормализация `numbers: llm` → llm для markers/selection/names
- [x] 1.2 Unit-тесты валидатора: дефолт при None/пустом, каждое нарушение (режим, порог, similarity, неизвестный ключ), нормализация numbers=llm, граничные значения

## 2. Параметризация value_formatter

- [x] 2.1 `enrich_display(data, precompute_cfg=None)`: code-ручки кладут поля (числа/маркер/significant/children_names), llm-ручки — не кладут; `collect_allowed_names` только при names.allowed=code; прокинуть cfg в `_walk`/`_display_for_node`
- [x] 2.2 Unit-тесты: дефолт = текущий вывод (golden), каждый llm-режим удаляет свои поля, numbers=llm затрагивает мотив/margin-пары, selection.threshold=0.5 меняет разметку значимости (root всегда significant)

## 3. Промпты по конфигу

- [x] 3.1 Разметить актуальные промпты плейсхолдерами `{{numbers_rule}}`/`{{marker_rule}}`/`{{selection_rule}}`/`{{names_rule}}` на местах code-инструкций; вынести similarity-число в подстановку
- [x] 3.2 `make_prompt_provider(cfg, plan_alias, fact_alias, allowed_names)`: code-фрагменты (цитирование display) + llm-фрагменты из `summarize_prompts_legacy` с подстановкой порогов; вернуть объект с интерфейсом `SummarizerPrompt`; зафиксировать в коде: legacy-тексты более не удаляются (источник llm-правил)
- [x] 3.3 `build_branch_report`/`summarize`: параметр `precompute_cfg=None`, замена дефолта prompt_provider на сборку по cfg
- [x] 3.4 Unit-тесты сборки: все code → текущие тексты (golden), selection llm → правило «>= {{threshold}} максимума» без ссылки на флаг, numbers llm → SCALING-правило, все llm → нет ссылок на display-поля

## 4. Плумбинг и запуск

- [x] 4.1 `run__fa_server.py`: `get_conf('configs.fa2026.summarize.precompute', None)` → validate → `FaServerImpl(..., precompute_cfg=...)`
- [x] 4.2 Прокинуть `precompute_cfg` через `FaServerImpl` → `calculate_and_summarize_deviation` → `summarize` (keyword-аргументы с дефолтом None)
- [x] 4.3 Проверить совместимость A/B-харнесса (`adhoc__ab_prompt_runs.py`) — прямые вызовы summarize работают без cfg

## 5. Верификация

- [x] 5.1 Прогнать полный юнит-тест-сьют и линтер проекта
- [x] 5.2 Adhoc-проверка на фикстуре: сервер с дефолтным конфигом даёт отчёт, идентичный текущему; сервер с numbers=llm стартует и даёт legacy-подобный отчёт
