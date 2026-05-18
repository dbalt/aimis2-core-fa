"""
Comprehensive unit tests for analytical structure metadata module.

Tests cover:
- Dimension class
- Algorithm class
- AnalyticalStructureMetadata class
- JSON serialization/deserialization
- Validation
- Full example from documentation
"""

from __future__ import annotations

import json

import pytest

from libfa2.analyt_struct_metadata import (
    Algorithm,
    AnalyticalStructureMetadata,
    Dimension,
    ValidationError,
    ValidationErrorType,
    ValidationReport,
)


# =============================================================================
# Dimension Class Tests
# =============================================================================

class TestDimension:
    """Test cases for the Dimension class."""

    def test_init_valid(self) -> None:
        """Test Dimension initialization with valid data."""
        dim = Dimension(
            code="segment",
            name="Сегмент",
            column="segment_id"
        )
        assert dim.code == "segment"
        assert dim.name == "Сегмент"
        assert dim.column == "segment_id"

    def test_init_empty_code(self) -> None:
        """Test that empty code raises ValueError."""
        with pytest.raises(ValueError, match="code must be a non-empty string"):
            Dimension(code="", name="Name", column="col")

    def test_init_empty_name(self) -> None:
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="name must be a non-empty string"):
            Dimension(code="code", name="", column="col")

    def test_init_empty_column(self) -> None:
        """Test that empty column raises ValueError."""
        with pytest.raises(ValueError, match="column must be a non-empty string"):
            Dimension(code="code", name="Name", column="")

    def test_to_dict(self) -> None:
        """Test converting Dimension to dictionary."""
        dim = Dimension(code="seg", name="Segment", column="seg_id")
        result = dim.to_dict()
        assert result == {
            "code": "seg",
            "name": "Segment",
            "column": "seg_id"
        }

    def test_from_dict(self) -> None:
        """Test creating Dimension from dictionary."""
        data = {
            "code": "segment",
            "name": "Сегмент",
            "column": "segment_id"
        }
        dim = Dimension.from_dict(data)
        assert dim.code == "segment"
        assert dim.name == "Сегмент"
        assert dim.column == "segment_id"

    def test_from_dict_missing_code(self) -> None:
        """Test from_dict with missing code raises KeyError."""
        data = {"name": "Name", "column": "col"}
        with pytest.raises(KeyError, match="'code'"):
            Dimension.from_dict(data)

    def test_from_dict_missing_name(self) -> None:
        """Test from_dict with missing name raises KeyError."""
        data = {"code": "code", "column": "col"}
        with pytest.raises(KeyError, match="'name'"):
            Dimension.from_dict(data)

    def test_from_dict_missing_column(self) -> None:
        """Test from_dict with missing column raises KeyError."""
        data = {"code": "code", "name": "Name"}
        with pytest.raises(KeyError, match="'column'"):
            Dimension.from_dict(data)

    def test_equality(self) -> None:
        """Test Dimension equality."""
        d1 = Dimension(code="a", name="A", column="a_col")
        d2 = Dimension(code="a", name="A", column="a_col")
        d3 = Dimension(code="b", name="B", column="b_col")
        assert d1 == d2
        assert d1 != d3
        assert d1 != "not a dimension"

    def test_hash(self) -> None:
        """Test Dimension hash for set membership."""
        d1 = Dimension(code="a", name="A", column="a_col")
        d2 = Dimension(code="a", name="A", column="a_col")
        dimensions = {d1}
        assert d2 in dimensions

    def test_repr(self) -> None:
        """Test Dimension string representation."""
        dim = Dimension(code="seg", name="Segment", column="seg_id")
        assert "Dimension" in repr(dim)
        assert "seg" in repr(dim)


# =============================================================================
# Algorithm Class Tests
# =============================================================================

class TestAlgorithm:
    """Test cases for the Algorithm class."""

    def test_init_valid(self) -> None:
        """Test Algorithm initialization with valid data."""
        algo = Algorithm(
            id=1,
            drill_order=[
                ["segment"],
                ["geo_structure"],
                ["product"]
            ]
        )
        assert algo.id == 1
        assert algo.drill_order == [["segment"], ["geo_structure"], ["product"]]

    def test_init_with_intersection(self) -> None:
        """Test Algorithm with dimension intersection in a step."""
        algo = Algorithm(
            id=1,
            drill_order=[
                ["segment"],
                ["geo_structure", "product"],
                ["sales_channel"]
            ]
        )
        assert len(algo.drill_order[1]) == 2

    def test_init_invalid_id(self) -> None:
        """Test that invalid ID raises ValueError."""
        with pytest.raises(ValueError, match="ID must be a positive integer"):
            Algorithm(id=0, drill_order=[["a"]])
        with pytest.raises(ValueError, match="ID must be a positive integer"):
            Algorithm(id=-1, drill_order=[["a"]])

    def test_init_empty_drill_order(self) -> None:
        """Test that empty drill_order raises ValueError."""
        with pytest.raises(ValueError, match="drill_order must be a non-empty list"):
            Algorithm(id=1, drill_order=[])

    def test_init_invalid_drill_step(self) -> None:
        """Test that invalid drill step raises ValueError."""
        with pytest.raises(ValueError, match="Drill step 0 must be a list"):
            Algorithm(id=1, drill_order=["not a list"])

    def test_init_empty_drill_step(self) -> None:
        """Test that empty drill step raises ValueError."""
        with pytest.raises(ValueError, match="Drill step 0 cannot be empty"):
            Algorithm(id=1, drill_order=[[]])

    def test_init_non_string_dimension_code(self) -> None:
        """Test that non-string dimension code raises ValueError."""
        with pytest.raises(ValueError, match="must be a string"):
            Algorithm(id=1, drill_order=[[123]])

    def test_step_count(self) -> None:
        """Test step_count property."""
        algo = Algorithm(id=1, drill_order=[["a"], ["b"], ["c"]])
        assert algo.step_count == 3

    def test_dimension_codes(self) -> None:
        """Test dimension_codes property."""
        algo = Algorithm(
            id=1,
            drill_order=[["segment"], ["geo"], ["product"]]
        )
        codes = algo.dimension_codes
        assert codes == {"segment", "geo", "product"}

    def test_dimension_codes_with_intersection(self) -> None:
        """Test dimension_codes with intersection step."""
        algo = Algorithm(
            id=1,
            drill_order=[["segment"], ["geo", "product"]]
        )
        codes = algo.dimension_codes
        assert codes == {"segment", "geo", "product"}

    def test_get_step_valid(self) -> None:
        """Test get_step with valid index."""
        algo = Algorithm(id=1, drill_order=[["a"], ["b"], ["c"]])
        step = algo.get_step(0)
        assert step == ["a"]

    def test_get_step_invalid(self) -> None:
        """Test get_step with invalid index."""
        algo = Algorithm(id=1, drill_order=[["a"]])
        assert algo.get_step(-1) is None
        assert algo.get_step(10) is None

    def test_to_dict(self) -> None:
        """Test converting Algorithm to dictionary."""
        algo = Algorithm(id=1, drill_order=[["segment"]])
        result = algo.to_dict()
        assert result == {"id": 1, "drill_order": [["segment"]]}

    def test_from_dict(self) -> None:
        """Test creating Algorithm from dictionary."""
        data = {
            "id": 1,
            "drill_order": [["segment"], ["geo"]]
        }
        algo = Algorithm.from_dict(data)
        assert algo.id == 1
        assert algo.drill_order == [["segment"], ["geo"]]

    def test_from_dict_missing_id(self) -> None:
        """Test from_dict with missing id raises KeyError."""
        data = {"drill_order": [["a"]]}
        with pytest.raises(KeyError, match="'id'"):
            Algorithm.from_dict(data)

    def test_from_dict_missing_drill_order(self) -> None:
        """Test from_dict with missing drill_order raises KeyError."""
        data = {"id": 1}
        with pytest.raises(KeyError, match="'drill_order'"):
            Algorithm.from_dict(data)

    def test_from_dict_invalid_drill_order_type(self) -> None:
        """Test from_dict with invalid drill_order type."""
        data = {"id": 1, "drill_order": "not a list"}
        with pytest.raises(ValueError, match="drill_order must be a list"):
            Algorithm.from_dict(data)

    def test_from_dict_invalid_step_type(self) -> None:
        """Test from_dict with invalid step type."""
        data = {"id": 1, "drill_order": ["not a list"]}
        with pytest.raises(ValueError, match="drill_order\\[0\\] must be a list"):
            Algorithm.from_dict(data)

    def test_from_dict_empty_step(self) -> None:
        """Test from_dict with empty step."""
        data = {"id": 1, "drill_order": [[]]}
        with pytest.raises(ValueError, match="drill_order\\[0\\] cannot be empty"):
            Algorithm.from_dict(data)

    def test_from_dict_non_string_dimension_code(self) -> None:
        """Test from_dict with non-string dimension code."""
        data = {"id": 1, "drill_order": [[123]]}
        with pytest.raises(ValueError, match="drill_order\\[0\\]\\[0\\] must be a string"):
            Algorithm.from_dict(data)

    def test_from_dict_strict_valid(self) -> None:
        """Test from_dict_strict with valid codes."""
        valid_codes = {"segment", "geo"}
        data = {"id": 1, "drill_order": [["segment"], ["geo"]]}
        algo = Algorithm.from_dict_strict(data, valid_codes)
        assert algo.id == 1

    def test_from_dict_strict_invalid_code(self) -> None:
        """Test from_dict_strict with invalid dimension code."""
        valid_codes = {"segment"}
        data = {"id": 1, "drill_order": [["segment"], ["unknown"]]}
        with pytest.raises(ValueError, match="unknown dimension code"):
            Algorithm.from_dict_strict(data, valid_codes)

    def test_equality(self) -> None:
        """Test Algorithm equality."""
        a1 = Algorithm(id=1, drill_order=[["a"]])
        a2 = Algorithm(id=1, drill_order=[["a"]])
        a3 = Algorithm(id=2, drill_order=[["a"]])
        assert a1 == a2
        assert a1 != a3
        assert a1 != "not an algorithm"

    def test_hash(self) -> None:
        """Test Algorithm hash for set membership."""
        a1 = Algorithm(id=1, drill_order=[["a"]])
        a2 = Algorithm(id=1, drill_order=[["a"]])
        algorithms = {a1}
        assert a2 in algorithms

    def test_repr(self) -> None:
        """Test Algorithm string representation."""
        algo = Algorithm(id=1, drill_order=[["a"]])
        assert "Algorithm" in repr(algo)
        assert "id=1" in repr(algo)


# =============================================================================
# AnalyticalStructureMetadata Class Tests
# =============================================================================

class TestAnalyticalStructureMetadata:
    """Test cases for the AnalyticalStructureMetadata class."""

    def test_init_empty(self) -> None:
        """Test AnalyticalStructureMetadata initialization."""
        metadata = AnalyticalStructureMetadata()
        assert len(metadata.algorithms) == 0
        assert len(metadata.dimensions) == 0

    def test_add_algorithm(self) -> None:
        """Test adding an algorithm to metadata."""
        metadata = AnalyticalStructureMetadata()
        algo = Algorithm(id=1, drill_order=[["a"]])
        metadata.add_algorithm(algo)
        assert 1 in metadata.algorithms

    def test_add_duplicate_algorithm_id(self) -> None:
        """Test that adding duplicate algorithm ID raises ValueError."""
        metadata = AnalyticalStructureMetadata()
        algo1 = Algorithm(id=1, drill_order=[["a"]])
        algo2 = Algorithm(id=1, drill_order=[["b"]])
        metadata.add_algorithm(algo1)
        with pytest.raises(ValueError, match="already exists"):
            metadata.add_algorithm(algo2)

    def test_remove_algorithm(self) -> None:
        """Test removing an algorithm from metadata."""
        metadata = AnalyticalStructureMetadata()
        algo = Algorithm(id=1, drill_order=[["a"]])
        metadata.add_algorithm(algo)
        metadata.remove_algorithm(1)
        assert 1 not in metadata.algorithms

    def test_remove_nonexistent_algorithm(self) -> None:
        """Test removing non-existent algorithm raises KeyError."""
        metadata = AnalyticalStructureMetadata()
        with pytest.raises(KeyError, match="not found"):
            metadata.remove_algorithm(999)

    def test_add_dimension(self) -> None:
        """Test adding a dimension to metadata."""
        metadata = AnalyticalStructureMetadata()
        dim = Dimension(code="segment", name="Segment", column="seg_id")
        metadata.add_dimension(dim)
        assert "segment" in metadata.dimensions

    def test_add_duplicate_dimension_code(self) -> None:
        """Test that adding duplicate dimension code raises ValueError."""
        metadata = AnalyticalStructureMetadata()
        dim1 = Dimension(code="a", name="A", column="a_col")
        dim2 = Dimension(code="a", name="B", column="b_col")
        metadata.add_dimension(dim1)
        with pytest.raises(ValueError, match="already exists"):
            metadata.add_dimension(dim2)

    def test_remove_dimension(self) -> None:
        """Test removing a dimension from metadata."""
        metadata = AnalyticalStructureMetadata()
        dim = Dimension(code="segment", name="Segment", column="seg_id")
        metadata.add_dimension(dim)
        metadata.remove_dimension("segment")
        assert "segment" not in metadata.dimensions

    def test_remove_nonexistent_dimension(self) -> None:
        """Test removing non-existent dimension raises KeyError."""
        metadata = AnalyticalStructureMetadata()
        with pytest.raises(KeyError, match="not found"):
            metadata.remove_dimension("not_found")

    def test_get_algorithm(self) -> None:
        """Test getting an algorithm by ID."""
        metadata = AnalyticalStructureMetadata()
        algo = Algorithm(id=1, drill_order=[["a"]])
        metadata.add_algorithm(algo)
        result = metadata.get_algorithm(1)
        assert result is not None
        assert result.id == 1

    def test_get_algorithm_not_found(self) -> None:
        """Test getting non-existent algorithm returns None."""
        metadata = AnalyticalStructureMetadata()
        assert metadata.get_algorithm(999) is None

    def test_get_dimension(self) -> None:
        """Test getting a dimension by code."""
        metadata = AnalyticalStructureMetadata()
        dim = Dimension(code="segment", name="Segment", column="seg_id")
        metadata.add_dimension(dim)
        result = metadata.get_dimension("segment")
        assert result is not None
        assert result.code == "segment"

    def test_get_dimension_not_found(self) -> None:
        """Test getting non-existent dimension returns None."""
        metadata = AnalyticalStructureMetadata()
        assert metadata.get_dimension("not_found") is None

    def test_algorithm_ids(self) -> None:
        """Test algorithm_ids property."""
        metadata = AnalyticalStructureMetadata()
        metadata.add_algorithm(Algorithm(id=1, drill_order=[["a"]]))
        metadata.add_algorithm(Algorithm(id=2, drill_order=[["b"]]))
        assert metadata.algorithm_ids == {1, 2}

    def test_dimension_codes(self) -> None:
        """Test dimension_codes property."""
        metadata = AnalyticalStructureMetadata()
        metadata.add_dimension(Dimension(code="a", name="A", column="a_col"))
        metadata.add_dimension(Dimension(code="b", name="B", column="b_col"))
        assert metadata.dimension_codes == {"a", "b"}

    def test_add_algorithms(self) -> None:
        """Test adding multiple algorithms."""
        metadata = AnalyticalStructureMetadata()
        algos = [
            Algorithm(id=1, drill_order=[["a"]]),
            Algorithm(id=2, drill_order=[["b"]])
        ]
        metadata.add_algorithms(algos)
        assert len(metadata.algorithms) == 2

    def test_add_dimensions(self) -> None:
        """Test adding multiple dimensions."""
        metadata = AnalyticalStructureMetadata()
        dims = [
            Dimension(code="a", name="A", column="a_col"),
            Dimension(code="b", name="B", column="b_col")
        ]
        metadata.add_dimensions(dims)
        assert len(metadata.dimensions) == 2

    def test_to_json(self) -> None:
        """Test serializing metadata to JSON."""
        metadata = AnalyticalStructureMetadata()
        metadata.add_dimension(Dimension(code="a", name="A", column="a_col"))
        json_str = metadata.to_json()
        data = json.loads(json_str)
        assert "algorithms" in data
        assert "dimensions" in data
        assert len(data["dimensions"]) == 1

    def test_from_json(self) -> None:
        """Test deserializing metadata from JSON."""
        json_str = '{"algorithms": [], "dimensions": []}'
        metadata = AnalyticalStructureMetadata.from_json(json_str)
        assert len(metadata.algorithms) == 0
        assert len(metadata.dimensions) == 0

    def test_from_json_with_data(self) -> None:
        """Test deserializing metadata with data."""
        json_str = '''{
            "algorithms": [{"id": 1, "drill_order": [["a"]]}],
            "dimensions": [{"code": "a", "name": "A", "column": "a_col"}]
        }'''
        metadata = AnalyticalStructureMetadata.from_json(json_str)
        assert len(metadata.algorithms) == 1
        assert len(metadata.dimensions) == 1

    def test_json_roundtrip(self) -> None:
        """Test JSON serialization roundtrip preserves data."""
        metadata = AnalyticalStructureMetadata()
        metadata.add_algorithm(Algorithm(id=1, drill_order=[["a"], ["b"]]))
        metadata.add_dimension(Dimension(code="a", name="A", column="a_col"))
        metadata.add_dimension(Dimension(code="b", name="B", column="b_col"))

        json_str = metadata.to_json()
        result = AnalyticalStructureMetadata.from_json(json_str)

        assert len(result.algorithms) == len(metadata.algorithms)
        assert len(result.dimensions) == len(metadata.dimensions)
        assert result.get_algorithm(1).drill_order == [["a"], ["b"]]

    def test_contains_with_int(self) -> None:
        """Test 'in' operator with algorithm ID."""
        metadata = AnalyticalStructureMetadata()
        metadata.add_algorithm(Algorithm(id=1, drill_order=[["a"]]))
        assert 1 in metadata
        assert 2 not in metadata

    def test_contains_with_str(self) -> None:
        """Test 'in' operator with dimension code."""
        metadata = AnalyticalStructureMetadata()
        metadata.add_dimension(Dimension(code="a", name="A", column="a_col"))
        assert "a" in metadata
        assert "b" not in metadata

    def test_contains_with_other_type(self) -> None:
        """Test 'in' operator with other type returns False."""
        metadata = AnalyticalStructureMetadata()
        assert 3.14 not in metadata

    def test_len(self) -> None:
        """Test AnalyticalStructureMetadata length."""
        metadata = AnalyticalStructureMetadata()
        assert len(metadata) == 0
        metadata.add_algorithm(Algorithm(id=1, drill_order=[["a"]]))
        metadata.add_dimension(Dimension(code="a", name="A", column="a_col"))
        assert len(metadata) == 2

    def test_equality(self) -> None:
        """Test AnalyticalStructureMetadata equality."""
        m1 = AnalyticalStructureMetadata()
        m2 = AnalyticalStructureMetadata()
        algo = Algorithm(id=1, drill_order=[["a"]])
        dim = Dimension(code="a", name="A", column="a_col")
        m1.add_algorithm(algo)
        m1.add_dimension(dim)
        m2.add_algorithm(algo)
        m2.add_dimension(dim)
        assert m1 == m2


# =============================================================================
# Validation Tests
# =============================================================================

class TestValidation:
    """Test cases for analytical structure metadata validation."""

    def test_valid_metadata(self) -> None:
        """Test validation of valid metadata."""
        metadata = AnalyticalStructureMetadata()
        metadata.add_dimension(Dimension(code="a", name="A", column="a_col"))
        metadata.add_algorithm(Algorithm(id=1, drill_order=[["a"]]))

        report = metadata.validate()
        assert report.is_valid
        assert len(report.errors) == 0

    def test_empty_algorithms(self) -> None:
        """Test detection of empty algorithms."""
        metadata = AnalyticalStructureMetadata()
        metadata.add_dimension(Dimension(code="a", name="A", column="a_col"))

        report = metadata.validate()
        assert not report.is_valid
        error_types = {e.type for e in report.errors}
        assert ValidationErrorType.EMPTY_ALGORITHMS in error_types

    def test_empty_dimensions(self) -> None:
        """Test detection of empty dimensions."""
        metadata = AnalyticalStructureMetadata()
        metadata.add_algorithm(Algorithm(id=1, drill_order=[["a"]]))

        report = metadata.validate()
        assert not report.is_valid
        error_types = {e.type for e in report.errors}
        assert ValidationErrorType.EMPTY_DIMENSIONS in error_types

    def test_duplicate_algorithm_id_prevented(self) -> None:
        """Test that duplicate algorithm IDs are prevented during add."""
        metadata = AnalyticalStructureMetadata()
        metadata.add_dimension(Dimension(code="a", name="A", column="a_col"))
        algo1 = Algorithm(id=1, drill_order=[["a"]])
        algo2 = Algorithm(id=1, drill_order=[["a"]])

        metadata.add_algorithm(algo1)
        with pytest.raises(ValueError, match="already exists"):
            metadata.add_algorithm(algo2)

    def test_duplicate_dimension_code_prevented(self) -> None:
        """Test that duplicate dimension codes are prevented during add."""
        metadata = AnalyticalStructureMetadata()
        dim1 = Dimension(code="a", name="A", column="a_col")
        dim2 = Dimension(code="a", name="B", column="b_col")

        metadata.add_dimension(dim1)
        with pytest.raises(ValueError, match="already exists"):
            metadata.add_dimension(dim2)

    def test_missing_dimension_reference(self) -> None:
        """Test detection of missing dimension reference in drill_order."""
        metadata = AnalyticalStructureMetadata()
        metadata.add_dimension(Dimension(code="a", name="A", column="a_col"))
        metadata.add_algorithm(Algorithm(id=1, drill_order=[["unknown"]]))

        report = metadata.validate()
        assert not report.is_valid
        error_types = {e.type for e in report.errors}
        assert ValidationErrorType.MISSING_DIMENSION_REFERENCE in error_types

    def test_invalid_algorithm_id(self) -> None:
        """Test detection of invalid algorithm ID (shouldn't happen in practice)."""
        metadata = AnalyticalStructureMetadata()
        metadata.add_dimension(Dimension(code="a", name="A", column="a_col"))
        # Manually set invalid ID to test validation
        algo = Algorithm(id=1, drill_order=[["a"]])
        object.__setattr__(algo, "id", -1)
        metadata.algorithms[-1] = algo

        report = metadata.validate()
        assert not report.is_valid
        error_types = {e.type for e in report.errors}
        assert ValidationErrorType.INVALID_ALGORITHM_ID in error_types

    def test_invalid_drill_order_structure(self) -> None:
        """Test detection of invalid drill_order structure (shouldn't happen)."""
        metadata = AnalyticalStructureMetadata()
        metadata.add_dimension(Dimension(code="a", name="A", column="a_col"))
        # Manually set invalid drill_order to test validation
        algo = Algorithm(id=1, drill_order=[["a"]])
        object.__setattr__(algo, "drill_order", [])
        metadata.algorithms[1] = algo

        report = metadata.validate()
        assert not report.is_valid
        error_types = {e.type for e in report.errors}
        assert ValidationErrorType.INVALID_DRILL_ORDER in error_types

    def test_validation_report_success(self) -> None:
        """Test ValidationReport.success factory method."""
        report = ValidationReport.success()
        assert report.is_valid
        assert len(report.errors) == 0

    def test_validation_report_failure(self) -> None:
        """Test ValidationReport.failure factory method."""
        errors = [
            ValidationError(type=ValidationErrorType.EMPTY_ALGORITHMS, message="Error 1"),
            ValidationError(type=ValidationErrorType.EMPTY_DIMENSIONS, message="Error 2"),
        ]
        report = ValidationReport.failure(errors)
        assert not report.is_valid
        assert len(report.errors) == 2


# =============================================================================
# Full Example Tests (from documentation)
# =============================================================================

class TestFullExample:
    """Integration tests with the full example from the documentation."""

    def test_full_example_serialization_deserialization(self) -> None:
        """
        Test serialization and deserialization of the full example from
        the documentation.
        """
        metadata = self._create_full_example_metadata()

        # Serialize to JSON
        json_str = metadata.to_json()

        # Verify JSON is valid
        data = json.loads(json_str)
        assert "algorithms" in data
        assert "dimensions" in data
        assert len(data["algorithms"]) == 5
        assert len(data["dimensions"]) == 6

        # Deserialize from JSON
        deserialized = AnalyticalStructureMetadata.from_json(json_str)

        # Verify the deserialized metadata matches the original
        assert len(deserialized.algorithms) == len(metadata.algorithms)
        assert len(deserialized.dimensions) == len(metadata.dimensions)

        # Verify algorithms
        assert deserialized.get_algorithm(1) is not None
        assert deserialized.get_algorithm(1).step_count == 3

        # Verify dimensions
        assert deserialized.get_dimension("segment") is not None
        assert deserialized.get_dimension("segment").column == "segment_id"

    def test_full_example_validation(self) -> None:
        """Test that the full example passes validation."""
        metadata = self._create_full_example_metadata()
        report = metadata.validate()
        assert report.is_valid
        assert len(report.errors) == 0

    def test_full_example_algorithm_properties(self) -> None:
        """Test algorithm properties on full example."""
        metadata = self._create_full_example_metadata()

        # Test algorithm 1
        algo1 = metadata.get_algorithm(1)
        assert algo1 is not None
        assert algo1.step_count == 3
        assert algo1.dimension_codes == {"segment", "geo_structure", "product"}

        # Test algorithm 3 (with intersection)
        algo3 = metadata.get_algorithm(3)
        assert algo3 is not None
        assert algo3.step_count == 3
        assert algo3.dimension_codes == {"segment", "geo_structure", "product", "sales_channel"}
        assert len(algo3.get_step(1) or []) == 2  # geo_structure + product

    def test_full_example_dimension_lookup(self) -> None:
        """Test dimension lookup on full example."""
        metadata = self._create_full_example_metadata()

        # Test getting all dimensions
        assert len(metadata.dimensions) == 6

        # Test specific dimensions
        segment = metadata.get_dimension("segment")
        assert segment is not None
        assert segment.name == "Сегмент"
        assert segment.column == "segment_id"

        currency = metadata.get_dimension("currency")
        assert currency is not None
        assert currency.name == "Валюта"
        assert currency.column == "currency_code"

    def _create_full_example_metadata(self) -> AnalyticalStructureMetadata:
        """
        Create the full example metadata from the documentation.

        This creates a complete metadata matching the example in
        factor_analysis__analytical_drill_metadata.md.
        """
        metadata = AnalyticalStructureMetadata()

        # Add dimensions
        metadata.add_dimensions([
            Dimension(code="segment", name="Сегмент", column="segment_id"),
            Dimension(code="geo_structure", name="Геоструктура", column="geo_structure_id"),
            Dimension(code="product", name="Продукт", column="product_id"),
            Dimension(code="sales_channel", name="Канал продаж", column="channel_id"),
            Dimension(code="client_type", name="Тип клиента", column="client_type_id"),
            Dimension(code="currency", name="Валюта", column="currency_code"),
        ])

        # Add algorithms
        metadata.add_algorithms([
            # Algorithm 1: Sequential decomposition
            Algorithm(
                id=1,
                drill_order=[
                    ["segment"],
                    ["geo_structure"],
                    ["product"]
                ]
            ),
            # Algorithm 2: Alternative order
            Algorithm(
                id=2,
                drill_order=[
                    ["geo_structure"],
                    ["segment"],
                    ["sales_channel"]
                ]
            ),
            # Algorithm 3: With intersection
            Algorithm(
                id=3,
                drill_order=[
                    ["segment"],
                    ["geo_structure", "product"],
                    ["sales_channel"]
                ]
            ),
            # Algorithm 4: Intersection on first step
            Algorithm(
                id=4,
                drill_order=[
                    ["segment", "product"],
                    ["geo_structure"]
                ]
            ),
            # Algorithm 5: Single level
            Algorithm(
                id=5,
                drill_order=[
                    ["segment"]
                ]
            ),
        ])

        return metadata


# =============================================================================
# JSON Structure Tests
# =============================================================================

class TestJsonStructure:
    """Tests for JSON serialization/deserialization edge cases."""

    def test_empty_json(self) -> None:
        """Test deserializing empty metadata."""
        json_str = '{"algorithms": [], "dimensions": []}'
        metadata = AnalyticalStructureMetadata.from_json(json_str)
        assert len(metadata.algorithms) == 0
        assert len(metadata.dimensions) == 0

    def test_json_compact_format(self) -> None:
        """Test compact JSON without indentation."""
        metadata = AnalyticalStructureMetadata()
        metadata.add_dimension(Dimension(code="a", name="A", column="a_col"))
        json_str = metadata.to_json(indent=None)
        assert json_str.count("\n") == 0

    def test_json_unicode_handling(self) -> None:
        """Test that JSON handles Unicode characters correctly."""
        metadata = AnalyticalStructureMetadata()
        metadata.add_dimension(Dimension(code="a", name="Сегмент", column="a_col"))
        json_str = metadata.to_json()
        assert "Сегмент" in json_str
        # Verify it's not escaped
        assert "\\u" not in json_str

    def test_algorithm_dict_immutable(self) -> None:
        """Test that to_dict returns independent copies."""
        metadata = AnalyticalStructureMetadata()
        metadata.add_algorithm(Algorithm(id=1, drill_order=[["a"]]))
        json_str = metadata.to_json()
        data = json.loads(json_str)

        # Modify the dict
        data["algorithms"][0]["id"] = 999

        # Original should be unchanged
        assert metadata.get_algorithm(1).id == 1

    def test_dimension_dict_immutable(self) -> None:
        """Test that dimension to_dict returns independent copy."""
        metadata = AnalyticalStructureMetadata()
        metadata.add_dimension(Dimension(code="a", name="A", column="a_col"))
        json_str = metadata.to_json()
        data = json.loads(json_str)

        # Modify the dict
        data["dimensions"][0]["name"] = "Changed"

        # Original should be unchanged
        assert metadata.get_dimension("a").name == "A"
