Ранее был разработан модуль adhoc.template_lite на основе требований из задачи @agent_stuff/tasks/26_template_light_base.md, и затем доработан с учетом требований из @agent_stuff/tasks/27_transform_logic.md и @agent_stuff/tasks/28_improve_adhoc_transform_routines.md 

Нужно доработать модуль adhoc.template_lite в части формирования аналитической структуры у узлов Иерархии. 
Сейчас реализовано так, что если по дереву идут два узла с типом razrez, то они превращаются в объект `AnalyticalStructureMetadata` у которого два алгоритма (`Algorithm`). Нужно доработать таким образом, чтобы `Algorithm` был 1, но в котором было бы два элемента в свойстве drill_order (в верхнеуровнем элементе этого списка). То есть то что сейчас кладется в отдельный алгоритм, должно попадать в цепочку drill_order-ов

Нужно учесть рекомендации по логированию из @agent_stuff/tasks/28_improve_adhoc_transform_routines.md

Подробный отчет о проделанной работе сохранить в agent_stuff/reports/29_template_lite__refac_x1___report.md

