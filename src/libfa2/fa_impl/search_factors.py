from typing import List, Tuple

from ..data_access.aggr import DataRow
from .units import SearchDevParameters, DeviationDetailAmts

PARETO_THRESHOLD = 0.8


def _is_negative(deviation: float, sign_negative_impact: int) -> bool:
    if sign_negative_impact == -1:
        return deviation < 0
    return deviation > 0


def get_factors(
    data_set: List[DataRow], 
    params: SearchDevParameters,
    flg_all:bool = False
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
    negative_rows: List[DataRow] = []

    for row in data_set:
        dev = row.deviation
        if dev == 0: continue
        if _is_negative(dev, sign):
            negative_contrib += dev
            negative_rows.append(row)
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
    total_neg_abs = sum(abs(r.deviation) for r in negative_rows)
    if total_neg_abs == 0:
        return [], detail

    # Sort by |deviation| descending — biggest contributors first
    negative_rows.sort(key=lambda r: abs(r.deviation), reverse=True)

    cumulative = 0.0
    pareto_rows: List[DataRow] = []
    for row in negative_rows:
        pareto_rows.append(row)
        cumulative += abs(row.deviation)
        if cumulative / total_neg_abs >= PARETO_THRESHOLD:
            break

    return pareto_rows, detail
