"""
Metadata module for analytical structure management.

This module defines the AnalyticalStructureMetadata class which manages
a collection of drill-down fa_impl and analytical dimensions, providing
methods for validation, serialization, and navigation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from libfa2.analyt_struct_metadata.enums import ValidationErrorType

if TYPE_CHECKING:
    from collections.abc import Iterable

    from libfa2.analyt_struct_metadata.algorithm import Algorithm
    from libfa2.analyt_struct_metadata.dimension import Dimension


@dataclass
class ValidationError:
    """
    Represents a validation error for analytical structure metadata.

    Attributes:
        type: The type of validation error.
        message: Human-readable description of the error.
        algorithm_id: ID of the algorithm where the error occurred, if applicable.
        dimension_code: Code of the dimension where the error occurred, if applicable.
        details: Additional context about the error.
    """

    type: ValidationErrorType
    """The type of validation error."""

    message: str
    """Human-readable description of the error."""

    algorithm_id: int | None = None
    """ID of the algorithm where the error occurred, if applicable."""

    dimension_code: str | None = None
    """Code of the dimension where the error occurred, if applicable."""

    details: dict[str, Any] | None = None
    """Additional context about the error."""

    def __repr__(self) -> str:
        """Return a string representation of the ValidationError."""
        algo_info = f", algorithm_id={self.algorithm_id}" if self.algorithm_id else ""
        dim_info = f", dimension_code={self.dimension_code!r}" if self.dimension_code else ""
        return (
            f"ValidationError(type={self.type}, message={self.message!r}"
            f"{algo_info}{dim_info})"
        )


@dataclass
class ValidationReport:
    """
    Report containing the results of analytical structure validation.

    Attributes:
        is_valid: True if no errors were found, False otherwise.
        errors: List of validation errors found.
    """

    is_valid: bool
    """True if no errors were found, False otherwise."""

    errors: list[ValidationError] = field(default_factory=list)
    """List of validation errors found."""

    @classmethod
    def success(cls) -> ValidationReport:
        """Create a success report with no errors."""
        return cls(is_valid=True, errors=[])

    @classmethod
    def failure(cls, errors: list[ValidationError]) -> ValidationReport:
        """Create a failure report with the given errors."""
        return cls(is_valid=False, errors=errors)


@dataclass
class AnalyticalStructureMetadata:
    """
    Manages a collection of drill-down fa_impl and analytical dimensions.

    The AnalyticalStructureMetadata class provides methods for:
    - Adding and removing fa_impl and dimensions
    - Serializing to/from JSON
    - Validating the structure
    - Finding fa_impl and dimensions

    Attributes:
        algorithms: Dictionary mapping algorithm IDs to Algorithm instances.
        dimensions: Dictionary mapping dimension codes to Dimension instances.
    """

    algorithms: dict[int, Algorithm] = field(default_factory=dict)
    """Dictionary mapping algorithm IDs to Algorithm instances."""

    dimensions: dict[str, Dimension] = field(default_factory=dict)
    """Dictionary mapping dimension codes to Dimension instances."""

    @property
    def algorithm_ids(self) -> set[int]:
        """
        Get the set of all algorithm IDs in the metadata.

        Returns:
            Set of all algorithm IDs.

        Examples:
            >>> metadata = AnalyticalStructureMetadata()
            >>> metadata.add_algorithm(Algorithm(id=1, drill_order=[["a"]]))
            >>> metadata.algorithm_ids
            {1}
        """
        return set(self.algorithms.keys())

    @property
    def dimension_codes(self) -> set[str]:
        """
        Get the set of all dimension codes in the metadata.

        Returns:
            Set of all dimension codes.

        Examples:
            >>> metadata = AnalyticalStructureMetadata()
            >>> metadata.add_dimension(Dimension(code="seg", name="Seg", column="seg_id"))
            >>> metadata.dimension_codes
            {'seg'}
        """
        return set(self.dimensions.keys())

    def add_algorithm(self, algorithm: Algorithm) -> None:
        """
        Add an algorithm to the metadata.

        Args:
            algorithm: The Algorithm to add.

        Raises:
            ValueError: If an algorithm with the same ID already exists.

        Examples:
            >>> metadata = AnalyticalStructureMetadata()
            >>> algo = Algorithm(id=1, drill_order=[["segment"]])
            >>> metadata.add_algorithm(algo)
            >>> 1 in metadata.fa_impl
            True
        """
        if algorithm.id in self.algorithms:
            raise ValueError(f"Algorithm with id={algorithm.id} already exists")
        self.algorithms[algorithm.id] = algorithm

    def add_algorithms(self, algorithms: Iterable[Algorithm]) -> None:
        """
        Add multiple fa_impl to the metadata.

        Args:
            algorithms: Iterable of Algorithm instances to add.

        Raises:
            ValueError: If any algorithm with the same ID already exists.

        Examples:
            >>> metadata = AnalyticalStructureMetadata()
            >>> algos = [
            ...     Algorithm(id=1, drill_order=[["a"]]),
            ...     Algorithm(id=2, drill_order=[["b"]])
            ... ]
            >>> metadata.add_algorithms(algos)
            >>> len(metadata.fa_impl)
            2
        """
        for algo in algorithms:
            if algo.id in self.algorithms:
                raise ValueError(f"Algorithm with id={algo.id} already exists")
        for algo in algorithms:
            self.algorithms[algo.id] = algo

    def remove_algorithm(self, algorithm_id: int) -> None:
        """
        Remove an algorithm from the metadata.

        Args:
            algorithm_id: ID of the algorithm to remove.

        Raises:
            KeyError: If no algorithm with the given ID exists.

        Examples:
            >>> metadata = AnalyticalStructureMetadata()
            >>> algo = Algorithm(id=1, drill_order=[["a"]])
            >>> metadata.add_algorithm(algo)
            >>> metadata.remove_algorithm(1)
            >>> 1 not in metadata.fa_impl
            True
        """
        if algorithm_id not in self.algorithms:
            raise KeyError(f"Algorithm with id={algorithm_id} not found")
        del self.algorithms[algorithm_id]

    def add_dimension(self, dimension: Dimension) -> None:
        """
        Add a dimension to the metadata.

        Args:
            dimension: The Dimension to add.

        Raises:
            ValueError: If a dimension with the same code already exists.

        Examples:
            >>> metadata = AnalyticalStructureMetadata()
            >>> dim = Dimension(code="segment", name="Segment", column="seg_id")
            >>> metadata.add_dimension(dim)
            >>> "segment" in metadata.dimensions
            True
        """
        if dimension.code in self.dimensions:
            raise ValueError(
                f"Dimension with code={dimension.code!r} already exists"
            )
        self.dimensions[dimension.code] = dimension

    def add_dimensions(self, dimensions: Iterable[Dimension]) -> None:
        """
        Add multiple dimensions to the metadata.

        Args:
            dimensions: Iterable of Dimension instances to add.

        Raises:
            ValueError: If any dimension with the same code already exists.

        Examples:
            >>> metadata = AnalyticalStructureMetadata()
            >>> dims = [
            ...     Dimension(code="seg", name="Seg", column="seg_id"),
            ...     Dimension(code="geo", name="Geo", column="geo_id")
            ... ]
            >>> metadata.add_dimensions(dims)
            >>> len(metadata.dimensions)
            2
        """
        for dim in dimensions:
            if dim.code in self.dimensions:
                raise ValueError(
                    f"Dimension with code={dim.code!r} already exists"
                )
        for dim in dimensions:
            self.dimensions[dim.code] = dim

    def remove_dimension(self, dimension_code: str) -> None:
        """
        Remove a dimension from the metadata.

        Args:
            dimension_code: Code of the dimension to remove.

        Raises:
            KeyError: If no dimension with the given code exists.

        Examples:
            >>> metadata = AnalyticalStructureMetadata()
            >>> dim = Dimension(code="segment", name="Segment", column="seg_id")
            >>> metadata.add_dimension(dim)
            >>> metadata.remove_dimension("segment")
            >>> "segment" not in metadata.dimensions
            True
        """
        if dimension_code not in self.dimensions:
            raise KeyError(f"Dimension with code={dimension_code!r} not found")
        del self.dimensions[dimension_code]

    def get_algorithm(self, algorithm_id: int) -> Algorithm | None:
        """
        Get an algorithm by its ID.

        Args:
            algorithm_id: ID of the algorithm to retrieve.

        Returns:
            The Algorithm if found, None otherwise.

        Examples:
            >>> metadata = AnalyticalStructureMetadata()
            >>> algo = Algorithm(id=1, drill_order=[["a"]])
            >>> metadata.add_algorithm(algo)
            >>> metadata.get_algorithm(1).id
            1
            >>> metadata.get_algorithm(999) is None
            True
        """
        return self.algorithms.get(algorithm_id)

    def get_dimension(self, dimension_code: str) -> Dimension | None:
        """
        Get a dimension by its code.

        Args:
            dimension_code: Code of the dimension to retrieve.

        Returns:
            The Dimension if found, None otherwise.

        Examples:
            >>> metadata = AnalyticalStructureMetadata()
            >>> dim = Dimension(code="segment", name="Segment", column="seg_id")
            >>> metadata.add_dimension(dim)
            >>> metadata.get_dimension("segment").code
            'segment'
            >>> metadata.get_dimension("not_found") is None
            True
        """
        return self.dimensions.get(dimension_code)

    def to_json(self, indent: int | None = 2) -> str:
        """
        Serialize the metadata to a JSON string.

        Args:
            indent: Number of spaces for indentation. None for compact JSON.

        Returns:
            JSON string representation of the metadata.

        Examples:
            >>> metadata = AnalyticalStructureMetadata()
            >>> metadata.add_dimension(Dimension(code="a", name="A", column="a_col"))
            >>> json_str = metadata.to_json()
            >>> '"fa_impl"' in json_str
            True
        """
        result = {
            "fa_impl": [algo.to_dict() for algo in self.algorithms.values()],
            "dimensions": [dim.to_dict() for dim in self.dimensions.values()],
        }
        return json.dumps(result, indent=indent, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> AnalyticalStructureMetadata:
        """
        Deserialize metadata from a JSON string.

        Args:
            json_str: JSON string containing the metadata data.

        Returns:
            A new AnalyticalStructureMetadata instance populated from the JSON.

        Raises:
            json.JSONDecodeError: If the JSON is invalid.
            ValueError: If the data is invalid.

        Examples:
            >>> json_str = '{"fa_impl": [], "dimensions": []}'
            >>> metadata = AnalyticalStructureMetadata.from_json(json_str)
            >>> len(metadata.fa_impl)
            0
        """
        from libfa2.analyt_struct_metadata.algorithm import Algorithm
        from libfa2.analyt_struct_metadata.dimension import Dimension

        data = json.loads(json_str)

        if not isinstance(data, dict):
            raise ValueError("Invalid JSON format: expected object")

        metadata = cls()

        # Load fa_impl
        algorithms_data = data.get("fa_impl", [])
        if algorithms_data:
            if not isinstance(algorithms_data, list):
                raise ValueError("'fa_impl' must be a list")
            for algo_data in algorithms_data:
                if not isinstance(algo_data, dict):
                    raise ValueError("Each algorithm must be a dictionary")
                algo = Algorithm.from_dict(algo_data)
                metadata.add_algorithm(algo)

        # Load dimensions
        dimensions_data = data.get("dimensions", [])
        if dimensions_data:
            if not isinstance(dimensions_data, list):
                raise ValueError("'dimensions' must be a list")
            for dim_data in dimensions_data:
                if not isinstance(dim_data, dict):
                    raise ValueError("Each dimension must be a dictionary")
                dim = Dimension.from_dict(dim_data)
                metadata.add_dimension(dim)

        return metadata

    def validate(self) -> ValidationReport:
        """
        Validate the analytical structure metadata.

        Checks for:
        - Duplicate algorithm IDs
        - Duplicate dimension codes
        - Missing dimension references in drill_order
        - Invalid algorithm IDs
        - Invalid dimension codes
        - Invalid drill_order structure
        - Empty fa_impl or dimensions

        Returns:
            ValidationReport with results.

        Examples:
            >>> metadata = AnalyticalStructureMetadata()
            >>> metadata.add_dimension(Dimension(code="a", name="A", column="a_col"))
            >>> algo = Algorithm(id=1, drill_order=[["a"]])
            >>> metadata.add_algorithm(algo)
            >>> report = metadata.validate()
            >>> report.is_valid
            True
        """
        errors: list[ValidationError] = []

        # Check for empty fa_impl
        if len(self.algorithms) == 0:
            errors.append(ValidationError(
                type=ValidationErrorType.EMPTY_ALGORITHMS,
                message="Algorithms list is empty",
            ))

        # Check for empty dimensions
        if len(self.dimensions) == 0:
            errors.append(ValidationError(
                type=ValidationErrorType.EMPTY_DIMENSIONS,
                message="Dimensions list is empty",
            ))

        # Check for duplicate algorithm IDs
        id_counts: dict[int, int] = {}
        for algo_id in self.algorithm_ids:
            id_counts[algo_id] = id_counts.get(algo_id, 0) + 1
        for algo_id, count in id_counts.items():
            if count > 1:
                errors.append(ValidationError(
                    type=ValidationErrorType.DUPLICATE_ALGORITHM_ID,
                    message=f"Duplicate algorithm ID found: {algo_id} ({count} occurrences)",
                    algorithm_id=algo_id,
                ))

        # Check for duplicate dimension codes
        code_counts: dict[str, int] = {}
        for code in self.dimension_codes:
            code_counts[code] = code_counts.get(code, 0) + 1
        for code, count in code_counts.items():
            if count > 1:
                errors.append(ValidationError(
                    type=ValidationErrorType.DUPLICATE_DIMENSION_CODE,
                    message=f"Duplicate dimension code found: {code!r} ({count} occurrences)",
                    dimension_code=code,
                ))

        # Validate each algorithm
        for algo in self.algorithms.values():
            # Validate algorithm ID
            if not isinstance(algo.id, int) or algo.id <= 0:
                errors.append(ValidationError(
                    type=ValidationErrorType.INVALID_ALGORITHM_ID,
                    message=f"Invalid algorithm ID: {algo.id} (must be positive integer)",
                    algorithm_id=algo.id,
                ))

            # Validate drill_order structure
            if not isinstance(algo.drill_order, list) or len(algo.drill_order) == 0:
                errors.append(ValidationError(
                    type=ValidationErrorType.INVALID_DRILL_ORDER,
                    message=f"Invalid drill_order for algorithm {algo.id}: must be non-empty list",
                    algorithm_id=algo.id,
                ))
            else:
                for i, step in enumerate(algo.drill_order):
                    if not isinstance(step, list):
                        errors.append(ValidationError(
                            type=ValidationErrorType.INVALID_DRILL_STEP,
                            message=f"Drill step {i} for algorithm {algo.id} must be a list",
                            algorithm_id=algo.id,
                            details={"step_index": i},
                        ))
                    elif len(step) == 0:
                        errors.append(ValidationError(
                            type=ValidationErrorType.INVALID_DRILL_STEP,
                            message=f"Drill step {i} for algorithm {algo.id} cannot be empty",
                            algorithm_id=algo.id,
                            details={"step_index": i},
                        ))
                    else:
                        for dim_code in step:
                            if not isinstance(dim_code, str) or not dim_code:
                                errors.append(ValidationError(
                                    type=ValidationErrorType.INVALID_DRILL_STEP,
                                    message=f"Invalid dimension code in drill_order[{i}] for algorithm {algo.id}",
                                    algorithm_id=algo.id,
                                    details={"step_index": i, "dimension_code": dim_code},
                                ))

            # Check for missing dimension references
            for dim_code in algo.dimension_codes:
                if dim_code not in self.dimensions:
                    errors.append(ValidationError(
                        type=ValidationErrorType.MISSING_DIMENSION_REFERENCE,
                        message=f"Algorithm {algo.id} references unknown dimension code: {dim_code!r}",
                        algorithm_id=algo.id,
                        dimension_code=dim_code,
                    ))

        # Validate each dimension
        for dim in self.dimensions.values():
            # Validate dimension code
            if not isinstance(dim.code, str) or not dim.code:
                errors.append(ValidationError(
                    type=ValidationErrorType.INVALID_DIMENSION_CODE,
                    message=f"Invalid dimension code for dimension: {dim.code!r}",
                    dimension_code=dim.code,
                ))

            # Validate dimension name
            if not isinstance(dim.name, str) or not dim.name:
                errors.append(ValidationError(
                    type=ValidationErrorType.INVALID_DIMENSION_NAME,
                    message=f"Invalid dimension name for dimension {dim.code!r}: name is empty",
                    dimension_code=dim.code,
                ))

            # Validate dimension column
            if not isinstance(dim.column, str) or not dim.column:
                errors.append(ValidationError(
                    type=ValidationErrorType.INVALID_DIMENSION_COLUMN,
                    message=f"Invalid dimension column for dimension {dim.code!r}: column is empty",
                    dimension_code=dim.code,
                ))

        return ValidationReport(is_valid=len(errors) == 0, errors=errors)

    def __eq__(self, other: object) -> bool:
        """
        Check equality with another AnalyticalStructureMetadata instance.

        Args:
            other: Another object to compare with.

        Returns:
            True if other is an AnalyticalStructureMetadata with the same
            fa_impl and dimensions, False otherwise.
        """
        if not isinstance(other, AnalyticalStructureMetadata):
            return False
        return (
            self.algorithms == other.algorithms
            and self.dimensions == other.dimensions
        )

    def __len__(self) -> int:
        """Return the total number of fa_impl and dimensions."""
        return len(self.algorithms) + len(self.dimensions)

    def __contains__(self, key: int | str) -> bool:
        """
        Check if an algorithm ID or dimension code exists in the metadata.

        Args:
            key: Either an algorithm ID (int) or dimension code (str).

        Returns:
            True if the key exists, False otherwise.
        """
        if isinstance(key, int):
            return key in self.algorithms
        elif isinstance(key, str):
            return key in self.dimensions
        return False

    def __repr__(self) -> str:
        """Return a string representation of the AnalyticalStructureMetadata."""
        return (
            f"AnalyticalStructureMetadata(fa_impl={len(self.algorithms)}, "
            f"dimensions={len(self.dimensions)})"
        )
