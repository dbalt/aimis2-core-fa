Нужно имплементировать модуль data_mgmt

Есть две таблицы:
```
create table missa_aimis.t_aimis__fa__metadata (
    code String,     
    metadata String
) 
engine = MergeTree()
primary key code
order by code;

create table t_aimis__fa__results (
    code String,
    dt date,
    data String,
    summary String
) 
engine = MergeTree()
primary key code
order by code
;
```

Нужно реализовать функционал управления данными в этих таблицах в виде класса со следующими методами:

- `async def delete_metadata(self, code:str)` - удаляет данные из t_aimis__fa__metadata по заданному code

- `async def save_metadata(self, code:str, data:str)` -  Сначала нужно удалить из t_aimis__fa__metadata с этим code, затем сделать insert`

- `async def get_metadata(self, code:str)->str` - возвращает строку метаданных из t_aimis__fa__metadata по заданному code

- `async def delete_results(self, code:str, dt:date)` - удаляет из t_aimis__fa__results по code и rep_dt

- `async def save_results(self, code:str, dt:date, data:Dict, summary:str)` -  сохраняет результаты в таблицу t_aimis__fa__results

- `async def get_results(self, code:str, dt:date)->Tuple[Dict,str]` - достает 


ВАЖНО!!!:
- Имена таблиц (missa_aimis.t_aimis__fa__metadata и missa_aimis.t_aimis__fa__results) могут быть другими и должны передаваться как параметры конструктора

- Должна быть минииерархия классов для работы как с GeneralSQLDataGateClientPart иак и с DbWrapper (по аналогии как в libfa2.data_access.aggr)

- Для каждого sql запроса нужно создавать новый экземпляр GeneralSQLDataGateClientPart/DbWrapper. Функция создания нового экземпляра - передается в параметрах конструктора


Нужно написать unit тесты. Использовать версию для GeneralSQLDataGateClientPart 
Инстанцирование экземпляра GeneralSQLDataGateClientPart для тестов:
```
async def get_dg_client()->GeneralSQLDataGateClientPart:
    from sdk.tools.settings import env__init_keydb_instance
    kdb = env__init_keydb_instance()
    dgc = GeneralSQLDataGateClientPart(kdb)
    return kc
```
Наименования таблиц: missa_aimis.t_aimis__fa__metadata и missa_aimis.t_aimis__fa__results


Каждый метод нужно снабдить комментариями (лаконичными)




Также нужно добавить вызов функций логирования.
Объект логгера нужно получать вызовом функции `get_logger()`
```
from sdk.core.logging import get_logger
```

делать это нужно в начале каждого метода (поскольку он анализирует точку вызова и добавляет ее в log). По факту возвращается стандартный питоновский логгер, сконфигурированный определенным образом.

Нужно добавить:
- lgr.debug(...) почти повсеместно, для трейса значений переменных и т.д
- lgr.info(...) там где происходит развилка или переход к следующему блоку логики. Другими словами, чтобы было понятно что конкретно происходит
- lgr.warning(...) в каких то местах, где мы поймав исключение - обрабатываем его и возвращаемся к нормальному выполнению, или делаем какое то существенное предположение, или где забиваем на обработку ошибок или проверку входящих данных.
- lgr.exception(...) для логирования исключений




подробный отчет о выполненной работе сохранить в agent_stuff/reports/22_data_mgmt_report.md