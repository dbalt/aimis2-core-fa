"""
Мотивационная корректировка — внешний аддитивный фактор факторного анализа.

Модуль предоставляет:
- MotivCorrectionMetadata: метаданные для загрузки корректировки из БД
- get_motiv_correction_data(): асинхронная загрузка DataRow из БД
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from sdk.core.logging import get_logger
from sdk.core.monadic import Res

from ..data_access.aggr import DataAccess, DataRow
from ..data_access.conditions import ConditionAnd, ConditionSet
from ..hier_metadata.query import Query
from .units import SourceParameters, SearchDevParameters


@dataclass
class MotivCorrectionMetadata:
    """
    Метаданные для загрузки мотивационной корректировки.

    Attributes:
        query: Параметры WHERE-фильтрации для БД-запроса.
    """

    query: Query

    def to_dict(self) -> dict:
        """Преобразовать в словарь."""
        return {
            "query": self.query.to_dict(),
        }

    def to_json(self) -> dict:
        """Подготовить для JSON-сериализации (без пустых полей)."""
        result = {}
        if self.query and not self.query.is_empty():
            result["query"] = self.query.to_json()
        return result

    def to_json_str(self) -> str:
        """Сериализовать в JSON-строку."""
        import json
        return json.dumps(self.to_json(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict) -> "MotivCorrectionMetadata":
        """Создать из словаря."""
        return cls(
            query=Query.from_dict(data["query"])
        )

    @classmethod
    def from_json(cls, data: dict) -> "MotivCorrectionMetadata":
        """Создать из JSON-объекта (словаря)."""
        return cls.from_dict(data)

    @classmethod
    def from_json_str(cls, json_str: str) -> "MotivCorrectionMetadata":
        """Десериализовать из JSON-строки."""
        import json
        return cls.from_json(json.loads(json_str))


async def get_motiv_correction_data(
    metadata: Optional["MotivCorrectionMetadata"],
    rep_dt: date,
    data_access: DataAccess,
    fallback_source_params: SourceParameters,
    fallback_search_dev_params: SearchDevParameters,
) -> Res[Optional[DataRow]]:
    """
    Загрузить один ряд данных мотивационной корректировки из БД.

    Args:
        metadata: Метаданные корректировки. Если None — возвращает None.
        rep_dt: Отчётная дата для фильтрации.
        data_access: Доступ к БД.
        fallback_source_params: Fallback source_params, если в metadata не указаны.
        fallback_search_dev_params: Fallback search_dev_params, если в metadata не указаны.

    Returns:
        Res[DataRow | None] — данные или None, если ничего не найдено.
    """
    lgr = get_logger()

    # 1. Если metadata is None — вернуть None
    if metadata is None:
        lgr.debug("MotivCorrectionMetadata is None, returning None")
        return Res.mk_result(None)

    # 2. Определить source_params и search_dev_params
    source_params = fallback_source_params
    search_dev_params = fallback_search_dev_params

    # 3. Сформировать ConditionSet из query
    query_dict = metadata.query.to_dict()
    cond_set = ConditionSet.from_dict(query_dict)
    lgr.debug(f"MotivCorrection query condition: {cond_set}")

    # 4. Добавить фильтр по rep_dt_column
    rep_dt_column = source_params.rep_dt_column
    full_cond = ConditionAnd([
        cond_set,
        ConditionSet({rep_dt_column: rep_dt}),
    ])
    lgr.debug(f"Full condition for motiv correction: {full_cond}")

    # 5. Выполнить запрос
    source = source_params.source_name
    plan_column = search_dev_params.plan_column
    fact_column = search_dev_params.fact_column

    lgr.info(
        f"Fetching motiv correction from source={source}, "
        f"plan_col={plan_column}, fact_col={fact_column}, rep_dt={rep_dt}"
    )

    result = await data_access.get_aggr_data(
        source=source,
        grp_by_columns=None,
        aggr_columns=[plan_column, fact_column],
        conditions=full_cond,
    )

    if not result.ok:
        return Res.mk_error(f"Failed to fetch motiv correction: {result.err}")

    rows = result.data

    # 6. Если данных нет — вернуть None
    if not rows or len(rows) == 0:
        lgr.debug("No motiv correction data found in DB result")
        return Res.mk_result(None)

    # 7. Вернуть DataRow
    row = DataRow.from_dict(rows[0], search_dev_params)
    lgr.info(
        f"Motiv correction loaded: plan={row.plan}, fact={row.fact}"
    )
    return Res.mk_result(row)
