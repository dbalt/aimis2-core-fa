Нужно добавить json сериализацию и десериализацию в класс DeviationCalcParams (@src/libfa2/fa_impl/deviation_calc_params.py) и во все используемые им (и так далее рекурсивно):
- `to_dict()` — преобразовать в словарь
- `to_json()` — преобразовать в словарь, исключая пустые значения (None, "", [])
- `from_dict(data)` / `from_json(data)` — создать из словаря/JSON
- `to_json_str()` - то же самое что `to_json()`, только к получившемуся словарю применяется `json.dumps()` с параметром ensure_ascii=False
- `from_json_str()` - десериализация из строки, эквивалентной той которую можно получить методом `to_json_str()`

Нужно написать/обновить unit тесты
Подробный отчет о проделанной работе сохранить в agent_stuff/reports/21_json_serde_calc_params_report.md

