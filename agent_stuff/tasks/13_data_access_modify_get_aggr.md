Нужно доработать модули libfa2.data_access.aggr и libfa2.data_access.conditions

Документация на модуль libfa2.data_access.conditions находится в @agent_stuff/docs/data_access_combine_doc.md

Нужно разработать функцию 
```
def get_where_clause_part(condition:ConditionBase) -> str
```
Она должна формировать часть условия where на основе переданного ConditionBase


Параметр `conditions` функции `get_aggr_data` должен иметь тип ConditionBase из модуля libfa2.data_access.conditions

Нужно переписать тело функции `get_aggr_data` так, что теперь часть where генерируется с помощью функции `get_where_clause_part`

Нужно обновить юнит тесты

Нужно сохранить подробный отчет о выполненной работе в файл @agent_stuff/reports/update_libfa2_data_access_glm_report.md
