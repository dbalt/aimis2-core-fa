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
SREDA_LOGIN_ENDPOINT = "/api/auth/login"
SREDA_TIMEOUT = httpx.Timeout(30.0)

# Автопоиск guide-идентификаторов по схеме метаданных Среды.
# Корень дерева схемы — жестко заданный системный идентификатор (не GUID данных).
SREDA_METADATA_ROOT_ID = "00000000-0000-0000-0000-000000000000"
SREDA_TREE_ENDPOINT = "/api/metadata/v3/tree/{node_id}"

# Имена справочников ФА в схеме. Глобально уникальны (префикс «ФА») и
# используются как маркеры при авто-поиске вместо хардкода GUID.
SREDA_GUIDE_NAMES = {
    "metric_guide": "ФАИерархииПоказателей",
    "query_guide": "ФАФильтрыЗапроса",
    "step_guide": "ФАШагАлгоритмаАналитическогоРазложения",
    "scenario_guide": "ФАСценарии",
    "src_params_guide": "ФАПараметрыИсточников",
}
SREDA_GUIDE_CLASS_NAME = "Guide"

# Табличная часть ФАСценарии, связывающая сценарий с иерархиями metric_hier.
SREDA_SCENARIO_HIERS_TAB = "t_aimis_fa__scenario__hiers"


@dataclass
class SredaClientConfig:
    """Конфигурация HTTP-клиента Среды."""

    host: str = SREDA_DEFAULT_HOST
    cert_dir: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent / "cert_aimis_gen"
    )
    cookies: dict[str, str] = field(default_factory=dict)

    # Креды для автоматического логина через POST /api/auth/login.
    # Если заданы (auto_login=True), SID получается программно вместо ручного таскания cookie.
    login: Optional[str] = None
    password: Optional[str] = None
    # Origin для fallback: если /api/auth/login отдаёт 501, запрос повторяется с этим заголовком.
    origin: Optional[str] = None
    auto_login: bool = True

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

    def login(self) -> None:
        """
        Авторизоваться через POST /api/auth/login и сохранить cookie в сессию.

        Если /api/auth/login отдаёт 501 — повторяем запрос с заголовком Origin
        (fallback на случай, когда эндпоинт требует CORS-контекст).

        Raises:
            SredaAPIError: если креды не заданы или авторизация не удалась.
        """
        if not self._config.login or not self._config.password:
            raise SredaAPIError(
                "Не заданы креды для авторизации (login/password)"
            )

        session = self._get_session()
        body = {
            "login": self._config.login,
            "password": self._config.password,
        }
        response = session.post(
            f"{self._config.host}{SREDA_LOGIN_ENDPOINT}", json=body
        )

        if response.status_code == 501 and self._config.origin:
            logger.info("login вернул 501, повторяю с Origin")
            response = session.post(
                f"{self._config.host}{SREDA_LOGIN_ENDPOINT}",
                json=body,
                headers={"Origin": self._config.origin},
            )

        if response.status_code != 200:
            raise SredaAPIError(
                f"Авторизация Среды не удалась: status={response.status_code}"
            )

        session.cookies.update(response.cookies)
        logger.info("Авторизация Среды выполнена")

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
        """Lazy init httpx session (и автологин при необходимости)."""
        if self._session is None:
            self._session = httpx.Client(
                verify=self._ssl_ctx,
                timeout=SREDA_TIMEOUT,
                cookies=self._config.cookies,
            )
            # Если креды заданы и нет готовой cookie из конфига —
            # логинимся программно, чтобы не тащить SID вручную.
            if (
                self._config.auto_login
                and self._config.login
                and self._config.password
                and not self._config.cookies
            ):
                self.login()
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

    def _fetch_tree(self, node_id: str) -> list[dict[str, Any]]:
        """
        Получить дочерние узлы дерева схемы метаданных Среды.

        GET /api/metadata/v3/tree/{node_id} → список дочерних объектов.
        """
        url = (
            f"{self._config.host}"
            f"{SREDA_TREE_ENDPOINT.format(node_id=node_id)}"
        )
        response = self._get_session().get(url)
        if response.status_code != 200:
            raise SredaHTTPError(node_id, response.status_code, response.text)
        payload = response.json()
        return payload if isinstance(payload, list) else []

    def discover_guides(self) -> dict[str, str]:
        """
        Найти guide_id справочников ФА автоматически, без хардкода GUID.

        Проходит по дереву схемы метаданных (/api/metadata/v3/tree):
          1. Корень → ищем узел класса Guide («Справочники»).
          2. Список справочников → ищем по заданным именам (префикс «ФА»).

        Returns:
            dict вида {"metric_guide": str, "query_guide": str, "step_guide": str}.
        """
        root_nodes = self._fetch_tree(SREDA_METADATA_ROOT_ID)
        guide_class_id: Optional[str] = None
        for node in root_nodes:
            if node.get("class") == SREDA_GUIDE_CLASS_NAME:
                guide_class_id = node.get("id")
                break

        if not guide_class_id:
            raise SredaAPIError(
                "Не найден класс Guide в схеме метаданных Среды"
            )

        guides = self._fetch_tree(guide_class_id)

        found: dict[str, str] = {}
        wanted = set(SREDA_GUIDE_NAMES.values())
        for node in guides:
            name = node.get("name")
            if name in wanted:
                gid = node.get("id")
                if gid:
                    key = next(
                        (k for k, v in SREDA_GUIDE_NAMES.items() if v == name),
                        None,
                    )
                    if key:
                        found[key] = gid

        missing = set(SREDA_GUIDE_NAMES) - set(found)
        if missing:
            raise SredaAPIError(
                "Не удалось найти справочники ФА в схеме Среды: "
                + ", ".join(sorted(missing))
            )

        logger.info(
            "Автопоиск guide_id: metric=%s, query=%s, step=%s",
            found["metric_guide"],
            found["query_guide"],
            found["step_guide"],
        )
        return found

    def build_full_tree(
        self,
        metric_guide_id: Optional[str] = None,
        query_guide_id: Optional[str] = None,
        step_guide_id: Optional[str] = None,
        scenario_guide_id: Optional[str] = None,
        src_params_guide_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Собрать полное дерево сценариев: метрики + query-фильтры + drill-шаги + дети.

        GUID можно передать явно либо опустить — тогда они будут найдены
        автоматически через discover_guides() (без хардкода).

        Args:
            metric_guide_id:  GUID guide таблицы metric_hier (опционально).
            query_guide_id:   GUID guide таблицы query_guide (опционально).
            step_guide_id:    GUID guide таблицы drill_steps (опционально).
            scenario_guide_id:  GUID guide ФАСценарии (опционально).
            src_params_guide_id: GUID guide ФАПараметрыИсточников (опционально).

        Returns:
            dict с ключами 'scenarios' и 'guides'. Каждый сценарий содержит
            'record', 'query_filters', 'drill_steps', 'children' и, при наличии,
            'scenario' (метаданные сценария из ФАСценарии) и 'source_params'
            (параметры источника из ФАПараметрыИсточников).
        """
        if metric_guide_id and query_guide_id and step_guide_id:
            metric_guide, query_guide, step_guide = (
                metric_guide_id,
                query_guide_id,
                step_guide_id,
            )
        else:
            discovered = self.discover_guides()
            metric_guide = metric_guide_id or discovered.get("metric_guide")
            query_guide = query_guide_id or discovered.get("query_guide")
            step_guide = step_guide_id or discovered.get("step_guide")

        scenario_guide = scenario_guide_id
        src_params_guide = src_params_guide_id
        if (not scenario_guide or not src_params_guide):
            try:
                discovered = self.discover_guides()
                scenario_guide = scenario_guide or discovered.get("scenario_guide")
                src_params_guide = src_params_guide or discovered.get("src_params_guide")
            except Exception:
                # Справочники сценариев/источников не обязательны — без них
                # сценарий просто не получит source-параметров из API.
                scenario_guide = None
                src_params_guide = None

        # Предзагружаем справочник параметров источников по GUID источника.
        source_map: dict[str, dict[str, Any]] = {}
        if src_params_guide:
            src_data = self.fetch_guide(src_params_guide)
            for src_row in src_data.get("rows", []):
                sid = src_row.get("id")
                if sid:
                    source_map[sid] = src_row

        meta_data = self.fetch_guide(metric_guide)
        top_records = meta_data.get("rows", [])

        scenarios: list[dict[str, Any]] = []

        for record in top_records:
            rid = record["id"]

            # Resolve query filters
            query_filters: list[dict] = []
            query_ref = record.get("query")
            if query_ref:
                query_filters = self.fetch_query_filters(query_ref, query_guide)

            # Resolve drill steps from analyt_steps tabular part
            drill_steps: list[dict] = []
            tp = record.get("TabularParts", {})
            analyt_tab = "t_aimis_fa__metric_hier__analyt_steps"
            if analyt_tab in tp:
                for step_item in tp[analyt_tab]:
                    step_uuid = step_item.get("step")
                    if step_uuid:
                        components = self.fetch_step_algorithm(
                            step_uuid, step_guide
                        )
                        step_item["_components"] = components
                drill_steps = tp[analyt_tab]

            # Resolve scenario (ФАСценарии) и параметры источника
            scenario_meta: Optional[dict[str, Any]] = None
            if scenario_guide:
                scenario_meta = self._resolve_scenario(source_map, rid, scenario_guide)

            # Recursive children
            children = self.fetch_children(rid, metric_guide)

            scenario_entry: dict[str, Any] = {
                "record": record,
                "query_filters": query_filters,
                "drill_steps": drill_steps,
                "children": children,
            }
            if scenario_meta:
                scenario_entry["scenario"] = scenario_meta["scenario"]
                scenario_entry["source_params"] = scenario_meta["source_params"]

            scenarios.append(scenario_entry)

        # Провайдим использованные guide_id, чтобы не переоткрывать автопоиск.
        return {
            "scenarios": scenarios,
            "guides": {
                "metric_guide": metric_guide,
                "query_guide": query_guide,
                "step_guide": step_guide,
                "scenario_guide": scenario_guide,
                "src_params_guide": src_params_guide,
            },
        }

    def _resolve_scenario(
        self,
        source_map: dict[str, dict[str, Any]],
        hierarchy_id: str,
        scenario_guide: str,
    ) -> Optional[dict[str, Any]]:
        """
        Найти запись ФАСценарии, привязанную к иерархии metric_hier, и вернуть
        метаданные сценария + параметры его источника.

        Связка по GUID: в ТабличнаяЧасть t_aimis_fa__scenario__hiers подиерархиями
        поле `hier` = id корневого узла metric_hier. Если несколько сценариев
        ссылаются на одну иерархию — берётся первый (rank ASC).

        Args:
            source_map:      mapping id ФАПараметрыИсточников → запись источника.
            hierarchy_id:    id корневого узла metric_hier (иерархия).
            scenario_guide:  GUID guide ФАСценарии.

        Returns:
            dict {'scenario': {...}, 'source_params': {...}} или None.
        """
        data = self.fetch_guide(scenario_guide)
        rows = data.get("rows", [])
        rows.sort(key=lambda r: r.get("code") or 0)

        for scenario in rows:
            tp = scenario.get("TabularParts", {})
            hiers = tp.get(SREDA_SCENARIO_HIERS_TAB, [])
            for hrow in hiers:
                if hrow.get("hier") == hierarchy_id:
                    source_guid = scenario.get("source")
                    src = source_map.get(source_guid) if source_guid else None
                    return {
                        "scenario": scenario,
                        "source_params": src,
                    }
        return None
