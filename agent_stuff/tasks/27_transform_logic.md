Изучи отчет @agent_stuff/reports/26_template_lite_base_report.md 
Это отчет по имплементации фич, описанных в задаче @agent_stuff/tasks/26_template_light_base.md

Также изучи отчеты:
- @agent_stuff/reports/hieararchy_drill_metadata_module_impl_report.md
- @agent_stuff/reports/modify_hier_docs_and_impl_glm_report.md

Теперь нужно написать функцию трансформации из объекта `TemplateLite` в `Hierarchy` из libfa2.hier_metadata,
по следующим правилам:

1. Если у узла TemplateLiteNode поле role == NodeRole.RAZREZ - то это описание аналитического разреза, в родительский MetricNode нужно добавить AnalyticalStructureMetadata. В нем один алгоритм и одно измерение. Все наименования берутся из `name` поля. 
Если у TemplateLiteNode поле role != NodeRole.RAZREZ - то это описание MetricNode

2. Если role == NodeRole.PODSTATYA, то у родительского MetricNode поле `type` должно быть MetricType.SUM. 
Если role == NodeRole.TARIF или role == NodeRole.BAZA, это означает что у родительского MetricNode поле `type` должно быть равно MetricType.MULTI, а у текущего MetricNode должно быть заполнено componentMultiPartType

3. У листовых элементов MetricNode (кроме тех у которых componentMultiPartType === ratio) и у тех, у которых `type` = MetricType.MULTI должно быть заполнено поле query. Примерно по такому шаблону: {'pl_code': <name from TemplateLiteNode>}

функцию назвать `transform_template_lite_to_hierarchy`, поместить в модуль adhoc.template_lite

подробный отчет о проделанной работе сохранить в agent_stuff/reports/27_transform_logic_report.md