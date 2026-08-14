"""
Конвертер данных из API Среды → DeviationCalcMetadata.

Пайплайн:
  1. API record → AnalytStep / DrillStepComponent / QueryFilterDetail (sreda_models)
  2. API record + children → MetricNode (hier_metadata)
  3. MetricNode[] → Hierarchy (hier_metadata)
  4. Hierarchy[] + SourceParameters + SearchDevParameters → DeviationCalcMetadata
"""

from __future__ import annotations

import json
from typing import Any, Optional

from ..hier_metadata import Hierarchy, MetricNode, MetricType
from ..hier_metadata.query import Query
from ..analyt_struct_metadata import AnalyticalStructureMetadata, Algorithm, Dimension
from ..fa_impl.deviation_calc_metadata import DeviationCalcMetadata
from ..fa_impl.units import SourceParameters, SearchDevParameters

from sdk.core.logging import get_logger
from sdk.core.monadic import Res

from ..sreda_api import SredaAPIClient
from ..sreda_models import (
    AnalytStep,
    DrillStepComponent,
    QueryFilterDetail,
    map_metric_type,
    map_multi_part_type,
    map_mp_decomposition_type,
    map_ratio_part_type,
)

logger = get_logger()


class SredaToDeviationCalcConverter:
    """Конвертер API-данных Среды → DeviationCalcMetadata."""

    def __init__(
        self,
        client: SredaAPIClient,
        metric_guide_id: str,
        query_guide_id: str,
        step_guide_id: str,
        metrics_source: str = "missa_bidr.t_aimis_fa__metrics_bsp",
        rep_dt_column: str = "rep_dt",
        plan_column: str = "val_plan",
        fact_column: str = "val_fact",
        sign_negative_impact: int = -1,
    ) -> None:
        self._client = client
        self._metric_guide_id = metric_guide_id
        self._query_guide_id = query_guide_id
        self._step_guide_id = step_guide_id
        self._metrics_source = metrics_source
        self._rep_dt_column = rep_dt_column
        self._plan_column = plan_column
        self._fact_column = fact_column
        self._sign_negative_impact = sign_negative_impact

    def transform(
        self,
        code: Optional[str] = None,
        aliases: Optional[dict[str, str]] = None,
    ) -> Res[DeviationCalcMetadata]:
        """
        Загрузить полное дерево из API Среды и трансформировать в DeviationCalcMetadata.

        Args:
            code: Системный код метаданных (default: берётся из первого record).
            aliases: Маппинг старых кодов → новых.

        Returns:
            Res[DeviationCalcMetadata] — успех или ошибка.
        """
        logger.info("Сбор полного дерева из API Среды...")
        tree = self._client.build_full_tree(
            self._metric_guide_id,
            self._query_guide_id,
            self._step_guide_id,
        )

        scenarios = tree.get("scenarios", [])
        if not scenarios:
            return Res.mk_error("sreda_tree.scenarios is empty")

        hiers: list[Hierarchy] = []
        meta_code = code

        for scenario in scenarios:
            record = scenario["record"]
            query_filters = scenario.get("query_filters", [])
            drill_steps = scenario.get("drill_steps", [])
            children = scenario.get("children", [])

            if meta_code is None:
                meta_code = record.get("name", "").strip()

            hierarchy = self._build_hierarchy(
                record, query_filters, drill_steps, children
            )
            if hierarchy.is_valid():
                hiers.append(hierarchy)
            else:
                errors = hierarchy.validate()
                logger.warning("Hierarchy validation errors: %s", errors)

        if not hiers:
            return Res.mk_error("No valid hierarchies built from sreda_tree")

        source_params = SourceParameters(
            source_name=self._metrics_source,
            rep_dt_column=self._rep_dt_column,
        )
        search_dev_params = SearchDevParameters(
            plan_column=self._plan_column,
            fact_column=self._fact_column,
            sign_negative_impact=self._sign_negative_impact,
        )

        dcm = DeviationCalcMetadata(
            code=meta_code,
            source_params=source_params,
            search_dev_params=search_dev_params,
            hier_lst=hiers,
            aliases=aliases,
            motiv_correction=None,
        )

        logger.info(
            "built DeviationCalcMetadata: code=%s, hier_count=%d",
            dcm.code,
            len(dcm.hier_lst),
        )
        return Res.mk_result(dcm)

    def _build_hierarchy(
        self,
        root_record: dict,
        root_filters: list,
        root_steps: list,
        children: list,
    ) -> Hierarchy:
        hierarchy = Hierarchy()
        root_node = self._api_record_to_node(
            root_record, root_filters, root_steps, parent_id=None, children=children
        )
        hierarchy.add_node(root_node)
        self._attach_children(hierarchy, root_record["id"], children)
        return hierarchy

    def _api_record_to_node(
        self,
        api_record: dict,
        filters: list[dict],
        drill_steps: list[dict],
        *,
        parent_id: Optional[str],
        children: Optional[list] = None,
    ) -> MetricNode:
        """Конвертировать API запись → MetricNode."""
        raw_code = api_record.get("name", "").strip()
        system_code = self._name_to_system_code(raw_code)

        # Build Query from filters
        query = self._build_query(filters)

        # Build analyt_steps
        analyt_steps = [AnalytStep.from_api_record(s) for s in drill_steps]

        # Build analyt_metadata from drill steps components
        analyt_metadata = self._build_analyt_metadata(drill_steps)

        # Inferred type: if node_type is null from API, infer from structure
        api_type = map_metric_type(api_record.get("node_type"))
        has_children = bool(children) if children else False
        has_analyt = bool(drill_steps)
        has_query = bool(api_record.get("query"))

        # Root node with children but no explicit type → likely SUM
        if api_type is None and has_children:
            api_type = MetricType.SUM

        # Leaf node: no children, has query → keep None (leaf)
        # Leaf node: no children, no query → still leaf (None)
        # Node with children but no explicit type → SUM

        # Clear component types if type is not MULTI/RATIO (API bug)
        comp_multi = None
        comp_ratio = None
        mp_decomp = None

        if api_type == MetricType.MULTI:
            comp_multi = map_multi_part_type(api_record.get("multi_part_type"))
            comp_ratio = map_ratio_part_type(api_record.get("ratio_part_type"))
            mp_decomp = map_mp_decomposition_type(api_record.get("mp_decomp_type"))
        elif api_type == MetricType.RATIO:
            comp_ratio = map_ratio_part_type(api_record.get("ratio_part_type"))
        elif api_type is None:
            # Leaf node: compute fields have multi_part_type but no query
            # (e.g., маржа ЮЛ/ФЛ)
            if api_record.get("multi_part_type") is not None:
                comp_multi = map_multi_part_type(api_record.get("multi_part_type"))
            if api_record.get("ratio_part_type") is not None:
                comp_ratio = map_ratio_part_type(api_record.get("ratio_part_type"))

        # Clear type-specific fields for SUM nodes (API bug)
        # (API sends multi_part_type, ratio_part_type, mp_decomp_type for SUM nodes)
        if api_type == MetricType.SUM:
            comp_multi = None
            comp_ratio = None
            mp_decomp = None

        node = MetricNode(
            id=int(
                api_record.get("id", "00000000000000000000000000000000").replace("-", ""), 16
            )
            % (2**31),
            code=system_code,
            name=api_record.get("pres_name") or api_record.get("name", ""),
            type=api_type,
            parent=(
                int(parent_id.replace("-", ""), 16) % (2**31) if parent_id else None
            ),
            query=query,
            analyt_metadata=analyt_metadata,
            analyt_steps=analyt_steps,
            flg_rate_type=api_record.get("flg_rate"),
            mp_decomp_tp=mp_decomp,
            force_drill=api_record.get("flg_force_drill"),
            componentMultiPartType=comp_multi,
            componentRatioPartType=comp_ratio,
            api_uuid=api_record.get("id"),
        )
        return node

    def _attach_children(
        self,
        hierarchy: Hierarchy,
        parent_id: str,
        children: list,
    ) -> None:
        """Рекурсивно добавить детей в Hierarchy, resolving query_filters для каждого."""
        for child in children:
            child_filters: list[dict] = []
            child_steps: list[dict] = []
            child_query_ref = child.get("query")
            if child_query_ref:
                child_filters = self._client.fetch_query_filters(
                    child_query_ref, self._query_guide_id
                )

            child_steps = []
            child_tp = child.get("TabularParts", {})
            analyt_tab = "t_aimis_fa__metric_hier__analyt_steps"
            if analyt_tab in child_tp:
                for step_item in child_tp[analyt_tab]:
                    step_uuid = step_item.get("step")
                    if step_uuid:
                        components = self._client.fetch_step_algorithm(
                            step_uuid, self._step_guide_id
                        )
                        step_item["_components"] = components
                child_steps = child_tp[analyt_tab]

            child_node = self._api_record_to_node(
                child, child_filters, child_steps, parent_id=parent_id,
                children=child.get("_children"),
            )
            hierarchy.add_node(child_node)

            # Recurse for grandchildren
            if child.get("_children"):
                self._attach_children(hierarchy, child["id"], child["_children"])

    def _build_query(self, filters: list[dict]) -> Optional[Query]:
        """Собрать Query из API фильтров."""
        if not filters:
            return None

        details = [QueryFilterDetail.from_api_record(f) for f in filters]
        result: dict[str, Any] = {}

        for d in sorted(details, key=lambda x: x.rank):
            val = d.value
            if isinstance(val, str) and val.startswith("["):
                try:
                    val = json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    pass
            else:
                try:
                    val = int(val)
                except (ValueError, TypeError):
                    pass
            result[d.col_name] = val

        return Query(result) if result else None

    def _build_analyt_metadata(
        self, drill_steps: list[dict]
    ) -> Optional[AnalyticalStructureMetadata]:
        """Построить AnalyticalStructureMetadata из drill_steps."""
        if not drill_steps:
            return None

        metadata = AnalyticalStructureMetadata()
        drill_order_parts: list[list[str]] = []
        dimensions: dict[str, Dimension] = {}

        for step in drill_steps:
            components = step.get("_components", [])
            if not components:
                continue

            step_details = [
                DrillStepComponent.from_api_record(c) for c in components
            ]

            for comp in step_details:
                drill_order_parts.append([comp.col_name])
                dimensions[comp.col_name] = Dimension(
                    code=comp.col_name,
                    name=comp.col_descr,
                    column=comp.col_name,
                )

        if not drill_order_parts:
            return None

        algo = Algorithm(id=1, drill_order=drill_order_parts)
        metadata.add_algorithm(algo)

        for dim in dimensions.values():
            metadata.add_dimension(dim)

        return metadata

    @staticmethod
    def _name_to_system_code(name: str) -> str:
        """Преобразовать human name → machine code."""
        if ":" in name:
            name = name.split(":", 1)[1].strip()
        name = name.rstrip()
        return name.replace(" ", "_")
