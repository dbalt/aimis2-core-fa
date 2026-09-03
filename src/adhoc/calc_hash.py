import json, hashlib

params = {
    "deprt": "ТБ",
    "deviation_type": "fact",
    "indicator_code": "cor",
    "scalcmethod": "Факт vs План",
    "speriodtype": "ytd"
}

params_json = json.dumps(params, sort_keys=True, ensure_ascii=False)
code = hashlib.md5(params_json.encode('utf-8')).hexdigest()
print(f"code: {code}")

import json, hashlib

meta = {
    "code": "cor",
    "source_params": {
        "source_name": "missa_bidr.v_aimis__usl_facts_test_dl",
        "rep_dt_column": "report_dt"
    },
    "search_dev_params": {
        "plan_column": "plan",
        "fact_column": "fact",
        "sign_negative_impact": -1
    },
    "hier_lst": [
        {
            "nodes": [
                {
                    "id": 1,
                    "code": "cor",
                    "name": "Стоимость риска (COR)",
                    "type": "ratio"
                },
                {
                    "id": 2,
                    "code": "rnr",
                    "name": "Расходы на резервы",
                    "parent": 1,
                    "componentRatioPartType": "numerator",
                    "query": {
                        "node_code": ["PL"]
                    }
                },
                {
                    "id": 3,
                    "code": "portfel",
                    "name": "Кредитный портфель",
                    "parent": 1,
                    "componentRatioPartType": "denominator",
                    "query": {
                        "node_code": ["BS"]
                    }
                }
            ]
        }
    ]
}

params_json = json.dumps(meta, sort_keys=True, ensure_ascii=False)
code = hashlib.md5(params_json.encode('utf-8')).hexdigest()
print(f"Хэш: {code}")