Для доступа к sql данным используется класс GeneralSQLDataGateClientPart из aimis-sdk (определен в /Users/baltakov-df/source/repos/aimis-sdk/sdk/datagate/dg_client.py)

В рамках этого проекта нужно спроектировать отдельный data access layer, который под капотом будет использовать GeneralSQLDataGateClientPart 

У класса должен быть метод get_aggr_data с такой сигнатурой:

```
async def get_aggr_data(
    source:str, # Имя таблицы в формате schema.table
    grp_by_columns:List[str], # Перечень столбцов таблицы, по которым будет группировка
    aggr_columns: List[str], # Перечень столбцов по которым будет sum.
    conditions: Dict[str, Any|List[Any]] # параметры из которых нужно будет построить where часть для запроса
) -> Res[List[Dict[str,Any]]]
```

Res определен в /Users/baltakov-df/source/repos/aimis-sdk/sdk/core/monadic.py

Внутри метода нужно сформировать sql запрос и вызвать get_data из GeneralSQLDataGateClientPart

например для вызова 

```
await get_aggr_data(
    'missa_bidr.t_aimis_fa__metrics_bsp',
    ['gosb_name'],
    ['plan', 'fact'],
    {
        'rep_dt': datetime.date(2026,2,28),
        'kpi_name': 'Чистая прибыль',
        'tb_name': ['Уральский банк', 'Байкальский банк']
    }
)
```

внутри должен быть сгенерирован запрос такой:


```
select 
    t.gosb_name,
    sum(t.fact) as fact,
    sum(t.plan) as plan
from missa_bidr.t_aimis_fa__metrics_bsp t
where 1=1
    and t.rep_dt = %(rep_dt)s
    and t.kpi_name = %(kpi_name)s
    and t.tb_name in %(tb_name)s
group by 
    t.gosb_name

```

При этом, если значением ключа в словаре conditions является список - то нужен оператор `in` в секции where, если одиночное значение то `=`

Код нужно поместить в модуль libfa2.data_access (в @src/libfa2/data_access/)

По итогам нужно сформировать мини саммари о проделанной работе и положить в @agent_stuff/reports/data_access_module_impl_report.md
