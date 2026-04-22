Изучи имплементацию классов:

- DataRow (@src/libfa2/data_access/aggr.py)
- SearchDevParameters (@src/libfa2/fa_impl/units.py)
- DeviationDetailAmts (@src/libfa2/fa_impl/units.py)

Нужно разработать функцию
```
def get_factors(data_set:List[DataRow], params:SearchDevParameters) -> Tuple[List[DataRow], DeviationDetailAmts]:
    ...
```
data_set - это неотсортированное множество

Функция должна посчитать DeviationDetailAmts - разбиение итогового отклонения всего `data_set` на позитивную и негативную составляющую.

Если params.sign_negative_impact = -1, тогда негативные отклонения это отклонения < 0, и соответственно когда params.sign_negative_impact = 1, тогда негативные отклонения это отклонения > 0 

Также функция должна отбирать наиболее существенные факторы негативного влияние из data_set по принципу Парето.


Нужно также написать юниттесты проверяющие любой аспект доработки


Код нужно сохранить в @src/libfa2/fa_impl/search_factors.py

Отчет о проделанной работе в @reports/searc_fac_impl_rep.md 