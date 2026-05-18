import pytest

from libfa2.data_access.aggr import DataRow
from libfa2.fa_impl.units import SearchDevParameters
from libfa2.fa_impl.search_factors import get_factors


def _params(sign: int = -1) -> SearchDevParameters:
    return SearchDevParameters(
        plan_column="plan",
        fact_column="fact",
        sign_negative_impact=sign,
    )


def _row(plan: float, fact: float, **dims) -> DataRow:
    return DataRow(dims=dims, plan=plan, fact=fact)


# ── DeviationDetailAmts ────────────────────────────────────────────────


class TestDeviationDetailAmts:
    def test_positive_and_negative_split(self):
        rows = [
            _row(100, 120),  # +20
            _row(200, 150),  # -50  (negative when sign=-1)
            _row(50, 80),    # +30
        ]
        _, detail = get_factors(rows, _params(-1))
        assert detail.positive_contrib == pytest.approx(50)   # 20 + 30
        assert detail.negative_contrib == pytest.approx(-50)
        assert detail.total == pytest.approx(0)               # 50 + (-50)

    def test_all_positive(self):
        rows = [_row(10, 20), _row(30, 50)]
        _, detail = get_factors(rows, _params(-1))
        assert detail.positive_contrib == pytest.approx(30)
        assert detail.negative_contrib == pytest.approx(0)

    def test_all_negative(self):
        rows = [_row(100, 50), _row(200, 100)]
        _, detail = get_factors(rows, _params(-1))
        assert detail.positive_contrib == pytest.approx(0)
        assert detail.negative_contrib == pytest.approx(-150)

    def test_empty_data_set(self):
        _, detail = get_factors([], _params(-1))
        assert detail.positive_contrib == 0
        assert detail.negative_contrib == 0
        assert detail.total == 0


# ── sign_negative_impact = 1 ───────────────────────────────────────────


class TestPositiveSignNegativeImpact:
    """When sign_negative_impact=1, positive deviations are the 'negative' ones."""

    def test_positive_devs_are_negative(self):
        rows = [
            _row(100, 120),  # +20 — this is the "negative" impact
            _row(200, 150),  # -50 — this is the "positive" impact
        ]
        pareto, detail = get_factors(rows, _params(sign=1))
        assert detail.negative_contrib == pytest.approx(20)
        assert detail.positive_contrib == pytest.approx(-50)

    def test_pareto_selects_positive_devs(self):
        rows = [
            _row(100, 200),  # +100 (negative impact when sign=1)
            _row(100, 110),  # +10  (negative impact when sign=1)
            _row(100, 105),  # +5   (negative impact when sign=1)
            _row(200, 150),  # -50  (positive impact when sign=1)
        ]
        pareto, detail = get_factors(rows, _params(sign=1))
        # 100 covers 100/115 ≈ 87% > 80% → only first row selected
        assert len(pareto) == 1
        assert pareto[0].deviation == pytest.approx(100)


# ── Pareto selection ───────────────────────────────────────────────────


class TestParetoSelection:
    def test_single_big_factor(self):
        """One row covers >80 % of total negative impact."""
        rows = [
            _row(100, 0, name="A"),      # -100
            _row(100, 90, name="B"),      #  -10
            _row(100, 95, name="C"),      #   -5
            _row(100, 110, name="D"),     #  +10
        ]
        pareto, _ = get_factors(rows, _params(-1))
        # |A| = 100, total_neg_abs = 115 → 100/115 ≈ 87 % > 80 %
        assert len(pareto) == 1
        assert pareto[0].dims["name"] == "A"

    def test_two_rows_needed_for_80pct(self):
        """Need two rows to exceed 80 % threshold."""
        rows = [
            _row(100, 50, name="A"),   # -50
            _row(100, 55, name="B"),   # -45
            _row(100, 90, name="C"),   # -10
            _row(100, 95, name="D"),   #  -5
        ]
        pareto, _ = get_factors(rows, _params(-1))
        # total_neg_abs = 110
        # |A| = 50  → cum 50/110 ≈ 45 %  (< 80 %, keep going)
        # |B| = 45  → cum 95/110 ≈ 86 %  (≥ 80 %, stop)
        assert len(pareto) == 2
        assert pareto[0].dims["name"] == "A"
        assert pareto[1].dims["name"] == "B"

    def test_all_rows_selected(self):
        """Every negative row is needed when values are evenly distributed."""
        rows = [
            _row(100, 50, name="A"),  # -50
            _row(100, 50, name="B"),  # -50
        ]
        pareto, _ = get_factors(rows, _params(-1))
        # 50/100 = 50 % → 100/100 = 100 %
        assert len(pareto) == 2

    def test_zero_deviation_not_negative(self):
        """A row with deviation == 0 is not negative."""
        rows = [
            _row(100, 100, name="zero"),
            _row(100, 50, name="neg"),
        ]
        pareto, detail = get_factors(rows, _params(-1))
        assert detail.positive_contrib == pytest.approx(0)  # zero dev → positive bucket
        assert detail.negative_contrib == pytest.approx(-50)
        assert len(pareto) == 1

    def test_preserves_dims(self):
        rows = [
            _row(100, 0, segment="Corp", region="MSK"),
            _row(100, 80, segment="Retail", region="SPB"),
        ]
        pareto, _ = get_factors(rows, _params(-1))
        assert pareto[0].dims["segment"] == "Corp"
        assert pareto[0].dims["region"] == "MSK"


# ── Unordered input ────────────────────────────────────────────────────


class TestUnorderedInput:
    def test_result_sorted_by_abs_deviation(self):
        rows = [
            _row(100, 80, name="small"),    # -20
            _row(100, 50, name="big"),       # -50
            _row(100, 75, name="medium"),    # -25
        ]
        pareto, _ = get_factors(rows, _params(-1))
        # total_neg_abs = 95
        # Sorted by |deviation| desc: big(-50), medium(-25), small(-20)
        # big: 50/95 ≈ 53%; +medium: 75/95 ≈ 79%; +small: 95/95 = 100%
        # → all three needed to cross 80 %
        assert [r.dims["name"] for r in pareto] == ["big", "medium", "small"]
