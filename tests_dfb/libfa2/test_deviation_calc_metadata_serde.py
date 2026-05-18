import json
import pytest
from datetime import date

from libfa2.fa_impl.deviation_calc_metadata import DeviationCalcMetadata
from libfa2.fa_impl.deviation_calc_params import DeviationCalcParams
from libfa2.fa_impl.units import SourceParameters, SearchDevParameters
from libfa2.hier_metadata import Hierarchy, MetricNode, Query
from libfa2.hier_metadata.enums import MetricType, ComponentMultiPartType
from libfa2.analyt_struct_metadata import AnalyticalStructureMetadata, Algorithm, Dimension


# ---- helpers ----

def _make_hierarchy(root_code="ROOT", leaf_code="LEAF"):
    h = Hierarchy()
    h.add_node(MetricNode(id=1, code=root_code, name="Root", type=MetricType.SUM))
    h.add_node(MetricNode(id=2, code=leaf_code, name="Leaf", parent=1,
                           query=Query({"metricType": "income"})))
    return h


def _make_metadata(**overrides):
    defaults = dict(
        code="test_code",
        source_params=SourceParameters(source_name="src", rep_dt_column="rep_dt"),
        search_dev_params=SearchDevParameters(plan_column="plan_val", fact_column="fact_val"),
        hier_lst=[_make_hierarchy()],
    )
    defaults.update(overrides)
    return DeviationCalcMetadata(**defaults)


# ========================== to_dict / from_dict ==========================

class TestDeviationCalcMetadataDict:

    def test_to_dict_structure(self):
        meta = _make_metadata()
        d = meta.to_dict()
        assert "code" in d
        assert "source_params" in d
        assert "search_dev_params" in d
        assert "hier_lst" in d
        assert isinstance(d["hier_lst"], list)
        assert len(d["hier_lst"]) == 1

    def test_to_dict_hier_content(self):
        meta = _make_metadata()
        d = meta.to_dict()
        assert "nodes" in d["hier_lst"][0]
        assert len(d["hier_lst"][0]["nodes"]) == 2

    def test_from_dict(self):
        meta = _make_metadata()
        d = meta.to_dict()
        restored = DeviationCalcMetadata.from_dict(d)
        assert restored.code == meta.code
        assert restored.source_params == meta.source_params
        assert restored.search_dev_params == meta.search_dev_params
        assert restored.hier_lst == meta.hier_lst

    def test_from_dict_multiple_hiers(self):
        meta = _make_metadata(hier_lst=[
            _make_hierarchy("A1", "A2"),
            _make_hierarchy("B1", "B2"),
        ])
        d = meta.to_dict()
        restored = DeviationCalcMetadata.from_dict(d)
        assert len(restored.hier_lst) == 2
        assert restored.hier_lst[0] == meta.hier_lst[0]
        assert restored.hier_lst[1] == meta.hier_lst[1]

    def test_roundtrip_dict(self):
        meta = _make_metadata()
        assert DeviationCalcMetadata.from_dict(meta.to_dict()) == meta

    def test_roundtrip_dict_code_none(self):
        meta = _make_metadata(code=None)
        restored = DeviationCalcMetadata.from_dict(meta.to_dict())
        assert restored.code is None


# ========================== to_json / from_json ==========================

class TestDeviationCalcMetadataJson:

    def test_to_json_omits_none_code(self):
        meta = _make_metadata(code=None)
        j = meta.to_json()
        assert "code" not in j

    def test_to_json_includes_code(self):
        meta = _make_metadata(code="c1")
        j = meta.to_json()
        assert j["code"] == "c1"

    def test_from_json(self):
        meta = _make_metadata()
        j = meta.to_json()
        restored = DeviationCalcMetadata.from_json(j)
        assert restored == meta

    def test_roundtrip_json(self):
        meta = _make_metadata()
        assert DeviationCalcMetadata.from_json(meta.to_json()) == meta


# ========================== to_json_str / from_json_str ==========================

class TestDeviationCalcMetadataJsonStr:

    def test_to_json_str_unicode(self):
        meta = _make_metadata(
            source_params=SourceParameters(source_name="источник"),
        )
        s = meta.to_json_str()
        assert "источник" in s

    def test_from_json_str(self):
        meta = _make_metadata()
        s = meta.to_json_str()
        restored = DeviationCalcMetadata.from_json_str(s)
        assert restored == meta

    def test_roundtrip_json_str(self):
        meta = _make_metadata()
        assert DeviationCalcMetadata.from_json_str(meta.to_json_str()) == meta

    def test_roundtrip_json_str_multiple_hiers(self):
        meta = _make_metadata(hier_lst=[
            _make_hierarchy("X1", "X2"),
            _make_hierarchy("Y1", "Y2"),
        ])
        restored = DeviationCalcMetadata.from_json_str(meta.to_json_str())
        assert restored == meta
        assert len(restored.hier_lst) == 2


# ========================== calc_params_lst ==========================

class TestCalcParamsLst:

    def test_single_hierarchy(self):
        meta = _make_metadata()
        params_lst = meta.calc_params_lst(date(2025, 6, 15))
        assert len(params_lst) == 1
        assert isinstance(params_lst[0], DeviationCalcParams)
        assert params_lst[0].rep_dt == date(2025, 6, 15)
        assert params_lst[0].code == "test_code"

    def test_multiple_hierarchies(self):
        meta = _make_metadata(hier_lst=[
            _make_hierarchy("A1", "A2"),
            _make_hierarchy("B1", "B2"),
        ])
        params_lst = meta.calc_params_lst(date(2025, 1, 1))
        assert len(params_lst) == 2
        assert params_lst[0].hier == meta.hier_lst[0]
        assert params_lst[1].hier == meta.hier_lst[1]

    def test_shared_source_and_search_params(self):
        meta = _make_metadata()
        params_lst = meta.calc_params_lst(date(2025, 6, 15))
        p = params_lst[0]
        assert p.source_params == meta.source_params
        assert p.search_dev_params == meta.search_dev_params

    def test_empty_hier_lst(self):
        meta = _make_metadata(hier_lst=[])
        params_lst = meta.calc_params_lst(date(2025, 6, 15))
        assert params_lst == []

    def test_calc_params_roundtrip_via_metadata(self):
        """Сериализация metadata → calc_params → сериализация params."""
        meta = _make_metadata(hier_lst=[
            _make_hierarchy("H1_R", "H1_L"),
            _make_hierarchy("H2_R", "H2_L"),
        ])
        params_lst = meta.calc_params_lst(date(2025, 3, 10))
        for p in params_lst:
            restored = DeviationCalcParams.from_json_str(p.to_json_str())
            assert restored == p

    def test_calc_params_with_analyt_metadata(self):
        h = Hierarchy()
        root = MetricNode(id=1, code="R", name="Root", type=MetricType.SUM)
        root.analyt_metadata = AnalyticalStructureMetadata()
        root.analyt_metadata.add_algorithm(Algorithm(id=1, drill_order=[["seg"]]))
        root.analyt_metadata.add_dimension(Dimension(code="seg", name="Segment", column="seg_id"))
        h.add_node(root)
        h.add_node(MetricNode(id=2, code="L", name="Leaf", parent=1,
                                query=Query({"m": "v"})))

        meta = _make_metadata(hier_lst=[h])
        params = meta.calc_params_lst(date(2025, 6, 15))
        restored = DeviationCalcParams.from_json_str(params[0].to_json_str())
        assert restored == params[0]
