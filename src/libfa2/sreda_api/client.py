"""
API-клиент для платформы «Среда» (IFT).

Реализует mTLS-аутентификацию + cookie SID, рекурсивный обход
иерархии по guide_id, получение tabular parts, query-фильтров
и drill-step алгоритмов.

GUID guide передаются как параметры методов, не захардкожены.
"""

from __future__ import annotations

import json
import ssl
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import httpx

from sdk.core.logging import get_logger

from .exceptions import SredaAPIError, SredaHTTPError


logger = get_logger()

SREDA_DEFAULT_HOST = "https://sredamo.apps.a623plp0.k8s.delta.sbrf.ru"
SREDA_ENDPOINT_TEMPLATE = "/api/metadata/guide/{guide_id}"
SREDA_TIMEOUT = httpx.Timeout(30.0)


@dataclass
class SredaClientConfig:
    """Конфигурация HTTP-клиента Среды."""

    host: str = SREDA_DEFAULT_HOST
    cert_dir: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent / "cert_aimis_gen"
    )
    cookies: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.cert_dir.exists():
            raise FileNotFoundError(
                f"Директория с сертификатами не найдена: {self.cert_dir}"
            )


class SredaAPIClient:
    """HTTP-клиент для API платформы «Среда» с mTLS и cookie SID."""

    def __init__(self, config: Optional[SredaClientConfig] = None) -> None:
        self._config = config or SredaClientConfig()
        self._ssl_ctx = self._build_ssl_context()
        self._session: Optional[httpx.Client] = None

    def _build_ssl_context(self) -> ssl.SSLContext:
        """
        Build TLS context with client certificate (mTLS).

        Server certificate is NOT verified (per task requirements).
        Client cert bundle = cert.pem + chain.pem, private key = private.key.
        """
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        # Combine leaf cert + chain into a temp file for load_cert_chain
        bundle = (self._config.cert_dir / "cert.pem").read_text()
        bundle += (self._config.cert_dir / "chain.pem").read_text()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".pem", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(bundle)
            bundle_path = Path(tmp.name)

        try:
            ctx.load_cert_chain(
                certfile=str(bundle_path),
                keyfile=str(self._config.cert_dir / "private.key"),
            )
        finally:
            bundle_path.unlink(missing_ok=True)

        return ctx

    def _get_session(self) -> httpx.Client:
        """Lazy init httpx session."""
        if self._session is None:
            self._session = httpx.Client(
                verify=self._ssl_ctx,
                timeout=SREDA_TIMEOUT,
                cookies=self._config.cookies,
            )
        return self._session

    def close(self) -> None:
        """Close the underlying httpx session."""
        if self._session:
            self._session.close()
            self._session = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def fetch_guide(
        self,
        guide_id: str,
        *,
        limit: int = 200,
        where: Optional[dict[str, Any]] = None,
        with_tabular_parts: bool = True,
    ) -> dict[str, Any]:
        """
        Запросить данные из guide по guide_id.

        Args:
            guide_id:     GUID объекта конфигурации (справочник, перечисление).
            limit:        Макс. число записей (default=200).
            where:        Фильтр в формате API.
            with_tabular_parts:  Включать табличные части (default=True).

        Returns:
            dict с полями 'rows' и 'cols'.

        Raises:
            SredaHTTPError: при status != 200.
        """
        url = f"{self._config.host}{SREDA_ENDPOINT_TEMPLATE.format(guide_id=guide_id)}"

        options: dict[str, Any] = {
            "limit": limit,
            "offset": 0,
            "withOutCount": True,
            "withTabularParts": with_tabular_parts,
            "metaAccessWhere": {},
            "order": [["code", "ASC"]],
        }
        if where:
            options["where"] = where

        response = self._get_session().get(
            url, params={"options": json.dumps(options, ensure_ascii=False)}
        )

        if response.status_code != 200:
            raise SredaHTTPError(guide_id, response.status_code, response.text)

        return response.json()

    def fetch_children(
        self,
        parent_id: str,
        guide_id: str,
        *,
        max_depth: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Рекурсивно обходить иерархию, начиная с parent_id.

        Каждый элемент содержит поля `_depth` и `_children`.

        Args:
            parent_id:  UUID корневого узла для обхода.
            guide_id:   GUID guide таблицы метрик.
            max_depth:  Максимальная глубина рекурсии (default=5).

        Returns:
            Список записей с вложенными `_children`.
        """

        def _recurse(pid: str, depth: int) -> list[dict]:
            if depth > max_depth:
                return []

            data = self.fetch_guide(guide_id, where={"parent": pid})
            result: list[dict] = []

            for row in data.get("rows", []):
                entry = dict(row)
                entry["_depth"] = depth
                entry["_children"] = _recurse(row["id"], depth + 1)
                result.append(entry)

            return result

        return _recurse(parent_id, depth=0)

    def fetch_query_filters(
        self, query_uuid: str, query_guide_id: str
    ) -> list[dict]:
        """
        Получить query-фильтры для заданного query UUID.

        Args:
            query_uuid:     UUID записи query (поле query в metric_hier).
            query_guide_id: GUID guide таблицы query_guide.

        Returns:
            Список записей из TabularParts.t_aimis_fa__query_filters__details.
        """
        data = self.fetch_guide(query_guide_id, where={"id": query_uuid})
        rows = data.get("rows", [])
        if not rows:
            return []

        tp = rows[0].get("TabularParts", {})
        tab_name = "t_aimis_fa__query_filters__details"
        return tp.get(tab_name, []) if tab_name in tp else []

    def fetch_step_algorithm(
        self, step_uuid: str, step_guide_id: str
    ) -> list[dict]:
        """
        Получить DrillStepComponent из step_guide.

        Args:
            step_uuid:     Значение поля `step` из analyt_steps metric_hier.
            step_guide_id: GUID таблицы шагов алгоритмов.

        Returns:
            Список записей из TabularParts.t_aimis_fa__analyt_drill_steps__components.
        """
        data = self.fetch_guide(step_guide_id)
        rows = data.get("rows", [])

        for row in rows:
            if row["id"] == step_uuid:
                tp = row.get("TabularParts", {})
                tab_name = "t_aimis_fa__analyt_drill_steps__components"
                return tp.get(tab_name, []) if tab_name in tp else []

        return []

    def build_full_tree(
        self,
        metric_guide_id: str,
        query_guide_id: str,
        step_guide_id: str,
    ) -> dict[str, Any]:
        """
        Собрать полное дерево сценариев: метрики + query-фильтры + drill-шаги + дети.

        GUID передаются как параметры, не захардкожены.

        Args:
            metric_guide_id:  GUID guide таблицы metric_hier.
            query_guide_id:   GUID guide таблицы query_guide.
            step_guide_id:    GUID guide таблицы drill_steps.

        Returns:
            dict с ключом 'scenarios': каждый сценарий содержит
            'record', 'query_filters', 'drill_steps', 'children'.
        """
        meta_data = self.fetch_guide(metric_guide_id)
        top_records = meta_data.get("rows", [])

        scenarios: list[dict[str, Any]] = []

        for record in top_records:
            rid = record["id"]

            # Resolve query filters
            query_filters: list[dict] = []
            query_ref = record.get("query")
            if query_ref:
                query_filters = self.fetch_query_filters(query_ref, query_guide_id)

            # Resolve drill steps from analyt_steps tabular part
            drill_steps: list[dict] = []
            tp = record.get("TabularParts", {})
            analyt_tab = "t_aimis_fa__metric_hier__analyt_steps"
            if analyt_tab in tp:
                for step_item in tp[analyt_tab]:
                    step_uuid = step_item.get("step")
                    if step_uuid:
                        components = self.fetch_step_algorithm(
                            step_uuid, step_guide_id
                        )
                        step_item["_components"] = components
                drill_steps = tp[analyt_tab]

            # Recursive children
            children = self.fetch_children(rid, metric_guide_id)

            scenarios.append(
                {
                    "record": record,
                    "query_filters": query_filters,
                    "drill_steps": drill_steps,
                    "children": children,
                }
            )

        return {"scenarios": scenarios}
