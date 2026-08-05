## 1. Модификация calc.py — SUM-ветка

- [ ] 1.1 После `get_factors(...)` в SUM-ветке (строка ~223) добавить проверку `all_positive = all(f.deviation > 0 for f in factors)`
- [ ] 1.2 Заменить текущую логику дриллинга (`is_negative or force_drill`) на условную ветку: если `all_positive` — дриллим каждого, иначе — только negative + force_drill

## 2. Модификация calc.py — ANALYT-ветка

- [ ] 2.1 Добавить `flg_positive=True` к вызову `get_factors` в `_process_algorithm_step` (строка ~526)
- [ ] 2.2 Вынести `factors` из вложенной области видимости — сделать `factors` доступным в цикле `for f in factors` (после вызова get_factors)
- [ ] 2.3 Добавить проверку `all_positive` перед циклом по факторам
- [ ] 2.4 В цикле: если `all_positive` — дриллим каждого, иначе — только negative + force_drill

## 3. Модификация collect.py — `_has_negative_in_tree`

- [ ] 3.1 Добавить функцию `_has_negative_in_tree(dc: DrillComponent) -> bool` — рекурсивная проверка наличия `impact < 0` в поддереве
- [ ] 3.2 Добавить docstring с указанием эвристики `impact < 0` для `sign_negative_impact == -1`

## 4. Модификация collect.py — `collect_for_summary`

- [ ] 4.1 В `_process_drill_component` перед добавлением `details` — вызвать `_has_negative_in_tree(dc)`
- [ ] 4.2 Если `has_negative` → включить полную детализацию (как сейчас)
- [ ] 4.3 Если не `has_negative` → НЕ включать поле `details`

## 5. Модификация collect.py — документация

- [ ] 5.1 Добавить комментарий в `_update_map_dim_names_to_columns` о known issue: мутатный `map` может перезаписываться на глубоких уровнях

## 6. Тесты

- [ ] 6.1 Тест SUM-ветка: все положительные — дриллим всех
- [ ] 6.2 Тест SUM-ветка: все отрицательные — Pareto работает
- [ ] 6.3 Тест SUM-ветка: микс — дриллим только negative
- [ ] 6.4 Тест ANALYT-ветка: все положительные — дриллим всех
- [ ] 6.5 Тест ANALYT-ветка: микс — дриллим только negative
- [ ] 6.6 Тест collect: ветка с негативом — details включены
- [ ] 6.7 Тест collect: ветка без негатива — details НЕ включены
- [ ] 6.8 Тест collect: негатив на глубине 2 — все уровни включены
- [ ] 6.9 Тест collect: вложенные ветки (негатив + позитив) — корректная фильтрация
