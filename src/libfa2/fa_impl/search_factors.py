from typing import List, Tuple

from ..data_access.aggr import DataRow
from .units import SearchDevParameters, DeviationDetailAmts

PARETO_THRESHOLD = 0.8
MINIMAL_COUNT = 5


def _is_negative(deviation: float, sign_negative_impact: int) -> bool:
    if sign_negative_impact == -1:
        return deviation < 0
    return deviation > 0

def _is_positive(deviation: float, sign_negative_impact: int) -> bool:
    if sign_negative_impact == -1:
        return deviation > 0
    return deviation < 0


def _select_pareto_rows(source: List[DataRow], total: float) -> List[DataRow]:
    source.sort(key=lambda r: abs(r.deviation), reverse=True)
    cum = 0.0
    res: List[DataRow] = []
    cnt = 0
    for row in source:
        cnt += 1
        res.append(row)
        cum += abs(row.deviation)
        if cum / abs(total) >= PARETO_THRESHOLD and cnt >= MINIMAL_COUNT:
            break
    return res


def get_factors(
    data_set: List[DataRow], 
    params: SearchDevParameters,
    flg_all:bool = False,
    flg_positive:bool = False
) -> Tuple[List[DataRow], DeviationDetailAmts]:
    """
    Разбивает итоговое отклонение data_set на позитивную и негативную
    составляющую и отбирает наиболее существенные факторы негативного
    влияния по принципу Парето (80% совокупного негатива).

    Returns:
        (pareto_rows, detail_amts) — отобранные строки-факторы и
        структура с положительной / отрицательной составляющими.
    """
    sign = params.sign_negative_impact

    positive_contrib = 0.0
    negative_contrib = 0.0
    # negative_rows: List[DataRow] = []

    for row in data_set:
        dev = row.deviation
        if dev == 0: continue
        if _is_negative(dev, sign):
            negative_contrib += dev
            # negative_rows.append(row)
        else:
            positive_contrib += dev

    detail = DeviationDetailAmts(
        positive_contrib=positive_contrib,
        negative_contrib=negative_contrib,
    )

    if flg_all:
        ret_lst = [x for x in data_set if x.deviation != 0]
        return ret_lst, detail

    # --- Pareto selection ---------------------------------------------------
    res = []
    if negative_contrib != 0:
        neg_rows = [x for x in data_set if _is_negative(x.deviation, sign)]
        neg_rows = _select_pareto_rows(neg_rows, negative_contrib)
        res.extend(neg_rows)

    if flg_positive and positive_contrib != 0:
        pos_rows = [x for x in data_set if _is_positive(x.deviation, sign)]
        pos_rows = _select_pareto_rows(pos_rows, positive_contrib)
        res.extend(pos_rows)

    return res, detail



