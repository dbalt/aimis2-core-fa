Изучи @agent_stuff/tasks/23_fa_server.md и @agent_stuff/tasks/23.2_fa_server_logging.md
Эти задачи уже выполнены (!!!)

Нужно добавить в FaServerImpl отработку следующих actions:
- `delete_metadata` - нужно вызвать метод DataMgmt.delete_metadata
- `save_metadata` - нужно вызвать метод DataMgmt.save_metadata
- `get_metadata` - DataMgmt.get_metadata
- `delete_results` - DataMgmt.get_metadata
- `delete_results_for_dt` - DataMgmt.delete_results_for_dt

все actions нужно вынести в отдельный enum class и использовать его

также нужно доработать класс FaClient добавив в него все эти методы тоже


подробный отчет о проделанной работе сохранить в agent_stuff/reports/24_fa_server__add_methods_glm_report.md