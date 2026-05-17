в модуль libfa2.fa_impl нужно добавить класс `DeviationCalcMetadata`, он должен повторять структуру `DeviationCalcParams` за исключением:
- в `DeviationCalcMetadata` не должно быть поля rep_dt
- в `DeviationCalcMetadata` вместо поля `hier:Hierarchy` нужно сделать поле `hier_lst:List[Hierarchy`

Нужно сделать:
- методы сериализации из/в dict/json/json string
- Метод `def calc_params_lst(self, rep_dt:date) -> List[DeviationCalcParams]`
- Написать тесты
- Добавить вызовы логирования по правилам описанным в @agent_stuff/tasks/18.1_add_logs_to_get_aggr_data_py.md (взять оттуда только правила вызовов логирования !!!)
- Добавить всюду лаконичные комментарии



Подробный отчет о проделанной работе сохранить в agent_stuff/reports/25_multiple_hiers_glm_report.md