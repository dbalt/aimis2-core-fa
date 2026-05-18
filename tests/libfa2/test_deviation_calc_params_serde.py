import json
import pytest
from datetime import date

from libfa2.fa_impl.deviation_calc_params import DeviationCalcParams
from libfa2.fa_impl.units import SourceParameters, SearchDevParameters
from libfa2.hier_metadata import Hierarchy, MetricNode, Query
from libfa2.hier_metadata.enums import MetricType, ComponentMultiPartType
from libfa2.analyt_struct_metadata import AnalyticalStructureMetadata, Algorithm, Dimension


# ---- helpers ----

def _make_hierarchy():
    h = Hierarchy()
    h.add_node(MetricNode(id=1, code="ROOT", name="Root", type=MetricType.SUM))
    h.add_node(MetricNode(id=2, code="LEAF", name="Leaf", parent=1,
                           query=Query({"metricType": "income"})))
    return h


def _make_params(**overrides):
    defaults = dict(
        rep_dt=date(2025, 6, 15),
        source_params=SourceParameters(source_name="src", rep_dt_column="rep_dt"),
        search_dev_params=SearchDevParameters(plan_column="plan_val", fact_column="fact_val"),
        hier=_make_hierarchy(),
    )
    defaults.update(overrides)
    return DeviationCalcParams(**defaults)


# ========================== SourceParameters ==========================

class TestSourceParametersSerde:

    def test_to_dict_defaults(self):
        sp = SourceParameters()
        d = sp.to_dict()
        assert d == {"source_name": "", "rep_dt_column": "rep_dt"}

    def test_to_dict_custom(self):
        sp = SourceParameters(source_name="my_src", rep_dt_column="dt")
        d = sp.to_dict()
        assert d == {"source_name": "my_src", "rep_dt_column": "dt"}

    def test_to_json_excludes_empty(self):
        sp = SourceParameters(source_name="", rep_dt_column="")
        j = sp.to_json()
        assert j == {}

    def test_to_json_keeps_non_empty(self):
        sp = SourceParameters(source_name="src")
        j = sp.to_json()
        assert j == {"source_name": "src", "rep_dt_column": "rep_dt"}

    def test_to_json_str(self):
        sp = SourceParameters(source_name="источник")
        s = sp.to_json_str()
        assert "источник" in s
        assert json.loads(s) == sp.to_json()

    def test_from_dict(self):
        sp = SourceParameters.from_dict({"source_name": "x", "rep_dt_column": "y"})
        assert sp.source_name == "x"
        assert sp.rep_dt_column == "y"

    def test_from_dict_defaults(self):
        sp = SourceParameters.from_dict({})
        assert sp.source_name == ""
        assert sp.rep_dt_column == "rep_dt"

    def test_from_json_same_as_from_dict(self):
        data = {"source_name": "a", "rep_dt_column": "b"}
        assert SourceParameters.from_json(data) == SourceParameters.from_dict(data)

    def test_from_json_str(self):
        json_str = '{"source_name": "s", "rep_dt_column": "c"}'
        sp = SourceParameters.from_json_str(json_str)
        assert sp.source_name == "s"
        assert sp.rep_dt_column == "c"

    def test_roundtrip_dict(self):
        sp = SourceParameters(source_name="abc", rep_dt_column="col")
        assert SourceParameters.from_dict(sp.to_dict()) == sp

    def test_roundtrip_json(self):
        sp = SourceParameters(source_name="abc")
        assert SourceParameters.from_json(sp.to_json()) == sp

    def test_roundtrip_json_str(self):
        sp = SourceParameters(source_name="abc")
        assert SourceParameters.from_json_str(sp.to_json_str()) == sp


# ========================== SearchDevParameters ==========================

class TestSearchDevParametersSerde:

    def test_to_dict(self):
        sdp = SearchDevParameters(plan_column="p", fact_column="f")
        d = sdp.to_dict()
        assert d == {"plan_column": "p", "fact_column": "f", "sign_negative_impact": -1}

    def test_to_dict_custom_sign(self):
        sdp = SearchDevParameters(plan_column="p", fact_column="f", sign_negative_impact=1)
        d = sdp.to_dict()
        assert d["sign_negative_impact"] == 1

    def test_to_json_excludes_empty(self):
        sdp = SearchDevParameters(plan_column="p", fact_column="f")
        j = sdp.to_json()
        assert j == {"plan_column": "p", "fact_column": "f", "sign_negative_impact": -1}

    def test_to_json_str(self):
        sdp = SearchDevParameters(plan_column="план", fact_column="факт")
        s = sdp.to_json_str()
        assert "план" in s
        parsed = json.loads(s)
        assert parsed["plan_column"] == "план"

    def test_from_dict(self):
        sdp = SearchDevParameters.from_dict({"plan_column": "p", "fact_column": "f"})
        assert sdp.plan_column == "p"
        assert sdp.fact_column == "f"
        assert sdp.sign_negative_impact == -1

    def test_from_dict_custom_sign(self):
        sdp = SearchDevParameters.from_dict({
            "plan_column": "p", "fact_column": "f", "sign_negative_impact": 1
        })
        assert sdp.sign_negative_impact == 1

    def test_from_dict_missing_required_raises(self):
        with pytest.raises(KeyError):
            SearchDevParameters.from_dict({"plan_column": "p"})

    def test_from_json(self):
        data = {"plan_column": "x", "fact_column": "y"}
        assert SearchDevParameters.from_json(data) == SearchDevParameters.from_dict(data)

    def test_from_json_str(self):
        json_str = '{"plan_column": "p", "fact_column": "f", "sign_negative_impact": 1}'
        sdp = SearchDevParameters.from_json_str(json_str)
        assert sdp.plan_column == "p"
        assert sdp.sign_negative_impact == 1

    def test_roundtrip_dict(self):
        sdp = SearchDevParameters(plan_column="p", fact_column="f", sign_negative_impact=1)
        assert SearchDevParameters.from_dict(sdp.to_dict()) == sdp

    def test_roundtrip_json(self):
        sdp = SearchDevParameters(plan_column="p", fact_column="f")
        assert SearchDevParameters.from_json(sdp.to_json()) == sdp

    def test_roundtrip_json_str(self):
        sdp = SearchDevParameters(plan_column="p", fact_column="f")
        assert SearchDevParameters.from_json_str(sdp.to_json_str()) == sdp


# ========================== DeviationCalcParams ==========================

class TestDeviationCalcParamsSerde:

    def test_to_dict(self):
        params = _make_params()
        d = params.to_dict()
        assert d["rep_dt"] == "2025-06-15"
        assert isinstance(d["source_params"], dict)
        assert isinstance(d["search_dev_params"], dict)
        assert isinstance(d["hier"], dict)
        assert "nodes" in d["hier"]

    def test_to_dict_hier_nodes_included(self):
        params = _make_params()
        d = params.to_dict()
        assert len(d["hier"]["nodes"]) == 2

    def test_to_json(self):
        params = _make_params()
        j = params.to_json()
        assert j["rep_dt"] == "2025-06-15"
        assert isinstance(j["source_params"], dict)
        assert isinstance(j["search_dev_params"], dict)
        assert "nodes" in j["hier"]

    def test_to_json_str(self):
        params = _make_params()
        s = params.to_json_str()
        parsed = json.loads(s)
        assert parsed["rep_dt"] == "2025-06-15"

    def test_to_json_str_unicode(self):
        params = _make_params(
            source_params=SourceParameters(source_name="источник"),
        )
        s = params.to_json_str()
        assert "источник" in s

    def test_from_dict(self):
        params = _make_params()
        d = params.to_dict()
        restored = DeviationCalcParams.from_dict(d)
        assert restored.rep_dt == date(2025, 6, 15)
        assert restored.source_params == params.source_params
        assert restored.search_dev_params == params.search_dev_params
        assert restored.hier == params.hier

    def test_from_dict_date_as_date_object(self):
        params = _make_params()
        d = params.to_dict()
        d["rep_dt"] = date(2025, 6, 15)
        restored = DeviationCalcParams.from_dict(d)
        assert restored.rep_dt == date(2025, 6, 15)

    def test_from_json(self):
        params = _make_params()
        j = params.to_json()
        restored = DeviationCalcParams.from_json(j)
        assert restored == params

    def test_from_json_str(self):
        params = _make_params()
        s = params.to_json_str()
        restored = DeviationCalcParams.from_json_str(s)
        assert restored == params

    def test_roundtrip_dict(self):
        params = _make_params()
        restored = DeviationCalcParams.from_dict(params.to_dict())
        assert restored == params

    def test_roundtrip_json(self):
        params = _make_params()
        restored = DeviationCalcParams.from_json(params.to_json())
        assert restored == params

    def test_roundtrip_json_str(self):
        params = _make_params()
        restored = DeviationCalcParams.from_json_str(params.to_json_str())
        assert restored == params

    def test_roundtrip_with_analyt_metadata(self):
        from libfa2.hier_metadata.enums import MetricType
        hier = Hierarchy()
        root = MetricNode(id=1, code="R", name="Root", type=MetricType.SUM)
        root.analyt_metadata = AnalyticalStructureMetadata()
        root.analyt_metadata.add_algorithm(Algorithm(id=1, drill_order=[["seg"]]))
        root.analyt_metadata.add_dimension(Dimension(code="seg", name="Segment", column="seg_id"))
        hier.add_node(root)
        hier.add_node(MetricNode(id=2, code="L", name="Leaf", parent=1,
                                  query=Query({"m": "v"})))

        params = _make_params(hier=hier)
        restored = DeviationCalcParams.from_json_str(params.to_json_str())
        assert restored == params

    def test_roundtrip_with_multi_nodes(self):
        hier = Hierarchy()
        hier.add_node(MetricNode(id=1, code="MULTI_ROOT", name="Multi Root",
                                  type=MetricType.MULTI))
        hier.add_node(MetricNode(id=2, code="RATE", name="Rate", parent=1,
                                  query=Query({"t": "rate"}),
                                  componentMultiPartType=ComponentMultiPartType.RATE))
        hier.add_node(MetricNode(id=3, code="BASE", name="Base", parent=1,
                                  query=Query({"t": "base"}),
                                  componentMultiPartType=ComponentMultiPartType.BASE))

        params = _make_params(hier=hier)
        restored = DeviationCalcParams.from_json_str(params.to_json_str())
        assert restored == params
        assert restored.hier.get_node(1).type == MetricType.MULTI
        assert restored.hier.get_node(2).componentMultiPartType == ComponentMultiPartType.RATE
