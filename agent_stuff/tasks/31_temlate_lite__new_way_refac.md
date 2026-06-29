Изучи файлы:
- @agent_stuff/tasks/26_template_light_base.md 
- @agent_stuff/tasks/27_transform_logic.md
- @agent_stuff/tasks/28_improve_adhoc_transform_routines.md
- @agent_stuff/tasks/29_template_lite__refac_x1.md

Это задачи, которые последовательно были выполнены, в результате получился модуль adhoc.template_lite

Нужно доработать с учетом новых требований:
в базовом json, у элементов появилось новое поле `upr_cube_codes`, которое по сути список элементов с тремя полями `type_code`, `fin_code` и `node_code`. 

Задачи:
- Нужно добавить поле `codes` в `TemplateLiteNode` с типом `List[str]`. 
- Модифицировать функцию `get_from_template_lite_json` добавив логику заполнения поля `codes`: брать `node_code` из каждого элемента поля `upr_cube_codes` и складывать списком в `codes`
- Модифицировать функцию `transform_template_lite_to_hierarchy` - при преобразовании тех элементов, у которых непустой `codes`, нужно в инстансе `MetricNode` заполнять поле `query` значением типа `Query({'node_code': <codes из TemplateLiteNode>})`

подробный отчет о проделанной работе сохранить в agent_stuff/reports/30_template_lite__new_way_report.md
