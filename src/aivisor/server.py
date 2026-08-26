from typing import Dict, AsyncIterable

from coredis import Redis as KeyDbClient

from sdk.core.base_api_server_app import BaseApiAppServerPart
from sdk.core.logging import get_logger
from sdk.datagate.dg_client import GeneralSQLDataGateClientPart

from datetime import date
from sdk.fa2026.client import FaClient

from sdk.tools.settings import get_conf
from libfa2.fa_impl.deviation_calc_metadata import DeviationCalcMetadata

from typing import Any



class AIVisorApiAppServerPart(BaseApiAppServerPart):
    """Серверная часть сервиса AIVisor.

    По коду отклонения и отчётной дате возвращает готовое саммари плана/факта,
    рассчитанное сервисом факторного анализа (FA). Доступ ограничен таблицей
    TBGOSB, заданной в конфигурации сервиса.
    """


    def __init__(self, keydb_client: KeyDbClient):
        super().__init__(keydb_client, 'aivisor', 'fa', 1)
        # Имя таблицы TBGOSB, из которой этому сервису разрешено читать данные.
        # Берётся из конфига; при отсутствии ключа используется таблица по умолчанию.
        self._tbgosb_table_name = get_conf(
            'configs.aivisor.table_name', 'missa_bidr.v_aimis__usl_facts_exp'
        )
        lgr = get_logger()
        lgr.info("AIVisorApiAppServerPart initialized; tbgosb_table_name=%s", self._tbgosb_table_name)

    @property
    def _force_single_response(self) -> bool:
        # AIVisor всегда отвечает одним итоговым сообщением, а не потоком чанков.
        # Логирование намеренно опущено: тривиальный константный геттер,
        # опрашиваемый базовым классом на каждый запрос.
        return True

    async def m__process_request(self, request_payload: Dict) -> AsyncIterable[Dict]:
        # Точка входа обработки запроса и одновременно граница перехвата ошибок:
        # любую неудачу фиксируем с трейсбэком и пробрасываем исключение дальше.
        lgr = get_logger()
        lgr.info(
            "AIVisor request received: code=%s, dt=%s",
            request_payload.get('code'), request_payload.get('dt'),
        )
        try:
            res = await self._do_work(payload=request_payload)
        except Exception:
            lgr.exception("AIVisor request failed")
            raise
        lgr.info("AIVisor request completed successfully")
        yield res

    async def _do_work(self, payload: Dict) -> str:
        # Основная логика: по коду и дате получить метаданные отклонения,
        # проверить права доступа к источнику данных и вернуть готовое саммари.
        lgr = get_logger()

        # --- Разбор и базовая проверка входных параметров ---
        if 'code' not in payload:
            lgr.warning("Payload is missing required <code> field; request rejected")
            raise Exception('No <code> field in payload')
        code = payload.get('code')
        lgr.debug("Request code=%s", code)

        if 'dt' not in payload:
            lgr.warning("Payload is missing required <dt> field; request rejected")
            raise Exception('No <dt> field in payload')
        dt_raw = payload.get('dt')
        lgr.debug("Request dt (raw)=%s", dt_raw)
        dt = date.fromisoformat(dt_raw)
        lgr.debug("Parsed report date dt=%s", dt.isoformat())

        # --- Получение метаданных отклонения по коду ---
        lgr.info("Fetching deviation metadata for code=%s", code)
        fac = FaClient(self._keydb_client)
        metadata_res = await fac.get_metadata(code)
        lgr.debug("get_metadata ok=%s", metadata_res.ok)
        if not metadata_res.ok:
            # Восходящий сервис вернул ошибку: восстановления не делаем,
            # просто пробрасываем отказ клиенту.
            lgr.warning(
                "No registered deviation for code=%s (upstream err=%s)",
                code, metadata_res.err,
            )
            raise Exception(f'No registered deviations with code: {code}')

        # --- Проверка источника данных ---
        # Сервису разрешён доступ только к зарегистрированной таблице TBGOSB.
        calc_metadata = DeviationCalcMetadata.from_dict(metadata_res.data)
        source_name = calc_metadata.source_params.source_name
        lgr.debug(
            "Deviation source_name=%s, allowed=%s", source_name, self._tbgosb_table_name,
        )
        if source_name != self._tbgosb_table_name:
            lgr.warning(
                "Access restricted: deviation source '%s' is not allowed for this service",
                source_name,
            )
            raise Exception(f'Restricted access to deviation with code: {code} ')

        # --- Получение готового саммари по плану/факту ---
        lgr.info("Fetching summary for code=%s, dt=%s", code, dt.isoformat())
        summary_res = await fac.get_summary(code, dt)
        lgr.debug("get_summary ok=%s", summary_res.ok)
        if not summary_res.ok:
            lgr.warning(
                "Failed to fetch summary for code=%s, dt=%s (upstream err=%s)",
                code, dt.isoformat(), summary_res.err,
            )
            raise Exception(summary_res.err)

        lgr.debug("Summary fetched successfully")
        return summary_res.data['summary']
