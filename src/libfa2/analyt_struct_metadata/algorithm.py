"""
Algorithm module for drill-down algorithm representation.

This module defines the Algorithm class which represents a single
drill-down algorithm for factor analysis by analytical dimensions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable


@dataclass
class Algorithm:
    """
    Represents a drill-down algorithm for factor analysis.

    An Algorithm defines the order of sequential data detailing from
    total to the most detailed level using analytical dimensions.
    Each step in the drill_order can involve one or more dimensions
    simultaneously (e.g., intersection of segment + product).

    Attributes:
        id: Unique numeric identifier of the algorithm.
        drill_order: Order of breakdown - array of steps, where each step
            is an array of dimension codes.

    Examples:
        >>> algo = Algorithm(
        ...     id=1,
        ...     drill_order=[
        ...         ["segment"],
        ...         ["geo_structure"],
        ...         ["product"]
        ...     ]
        ... )
        >>> algo.id
        1

        >>> algo = Algorithm(
        ...     id=2,
        ...     drill_order=[
        ...         ["segment"],
        ...         ["geo_structure", "product"],
        ...         ["sales_channel"]
        ...     ]
        ... )
    """

    id: int
    """Unique numeric identifier of the algorithm."""

    drill_order: list[list[str]]
    """
    Order of breakdown - array of steps, where each step is an array
    of dimension codes.
    """

    def __post_init__(self) -> None:
        """Validate the Algorithm after initialization."""
        if not isinstance(self.id, int) or self.id <= 0:
            raise ValueError("Algorithm ID must be a positive integer")
        if not isinstance(self.drill_order, list) or len(self.drill_order) == 0:
            raise ValueError("drill_order must be a non-empty list")
        for i, step in enumerate(self.drill_order):
            if not isinstance(step, list):
                raise ValueError(f"Drill step {i} must be a list")
            if len(step) == 0:
                raise ValueError(f"Drill step {i} cannot be empty")
            for j, dim_code in enumerate(step):
                if not isinstance(dim_code, str):
                    raise ValueError(
                        f"Dimension code at drill_order[{i}][{j}] must be a string"
                    )

    @property
    def step_count(self) -> int:
        """
        Get the number of steps in the drill order.

        Returns:
            Number of steps in the drill_order.

        Examples:
            >>> algo = Algorithm(id=1, drill_order=[["a"], ["b"]])
            >>> algo.step_count
            2
        """
        return len(self.drill_order)

    @property
    def dimension_codes(self) -> set[str]:
        """
        Get all unique dimension codes referenced in the drill order.

        Returns:
            Set of all dimension codes used in the algorithm.

        Examples:
            >>> algo = Algorithm(
            ...     id=1,
            ...     drill_order=[["segment"], ["geo"], ["product"]]
            ... )
            >>> algo.dimension_codes
            {'segment', 'geo', 'product'}
        """
        codes: set[str] = set()
        for step in self.drill_order:
            codes.update(step)
        return codes

    def get_step(self, step_index: int) -> list[str] | None:
        """
        Get a specific step from the drill order.

        Args:
            step_index: Zero-based index of the step to retrieve.

        Returns:
            List of dimension codes for the step, or None if index is invalid.

        Examples:
            >>> algo = Algorithm(id=1, drill_order=[["a"], ["b"], ["c"]])
            >>> algo.get_step(0)
            ['a']
            >>> algo.get_step(10) is None
            True
        """
        if 0 <= step_index < len(self.drill_order):
            return self.drill_order[step_index].copy()
        return None

    def to_dict(self) -> dict[str, object]:
        """
        Convert the Algorithm to a dictionary representation for JSON serialization.

        All fields are included as they are required.

        Returns:
            Dictionary representation of the Algorithm.

        Examples:
            >>> algo = Algorithm(id=1, drill_order=[["segment"]])
            >>> d = algo.to_dict()
            >>> d["id"]
            1
        """
        return {
            "id": self.id,
            "drill_order": [step.copy() for step in self.drill_order],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Algorithm:
        """
        Create an Algorithm instance from a dictionary.

        Args:
            data: Dictionary containing the algorithm data.

        Returns:
            A new Algorithm instance populated from the dictionary.

        Raises:
            KeyError: If required field 'id' is missing.
            ValueError: If any field has an invalid value.

        Examples:
            >>> data = {
            ...     "id": 1,
            ...     "drill_order": [["segment"], ["geo"]]
            ... }
            >>> algo = Algorithm.from_dict(data)
            >>> algo.id
            1
        """
        # Extract required fields
        algo_id = data.get("id")
        if algo_id is None:
            raise KeyError("Missing required field: 'id'")

        drill_order_data = data.get("drill_order")
        if drill_order_data is None:
            raise KeyError("Missing required field: 'drill_order'")

        if not isinstance(drill_order_data, list):
            raise ValueError("drill_order must be a list")

        # Convert drill_order to list of lists of strings
        drill_order: list[list[str]] = []
        for i, step in enumerate(drill_order_data):
            if not isinstance(step, list):
                raise ValueError(f"drill_order[{i}] must be a list")
            step_strs: list[str] = []
            for j, dim_code in enumerate(step):
                if not isinstance(dim_code, str):
                    raise ValueError(
                        f"drill_order[{i}][{j}] must be a string"
                    )
                step_strs.append(str(dim_code))
            if len(step_strs) == 0:
                raise ValueError(f"drill_order[{i}] cannot be empty")
            drill_order.append(step_strs)

        if len(drill_order) == 0:
            raise ValueError("drill_order cannot be empty")

        return cls(
            id=int(algo_id),
            drill_order=drill_order,
        )

    @classmethod
    def from_dict_strict(cls, data: dict[str, object], valid_dimension_codes: set[str] | None = None) -> Algorithm:
        """
        Create an Algorithm instance from a dictionary with strict validation.

        This method additionally validates that all dimension codes
        in drill_order exist in the provided valid_dimension_codes set.

        Args:
            data: Dictionary containing the algorithm data.
            valid_dimension_codes: Set of valid dimension codes to validate against.
                If None, this validation is skipped.

        Returns:
            A new Algorithm instance populated from the dictionary.

        Raises:
            KeyError: If required fields are missing.
            ValueError: If any field has an invalid value or dimension code
                is not in valid_dimension_codes.

        Examples:
            >>> valid_codes = {"segment", "geo"}
            >>> data = {"id": 1, "drill_order": [["segment"], ["geo"]]}
            >>> algo = Algorithm.from_dict_strict(data, valid_codes)
            >>> algo.id
            1
        """
        algo = cls.from_dict(data)

        if valid_dimension_codes is not None:
            for i, step in enumerate(algo.drill_order):
                for j, dim_code in enumerate(step):
                    if dim_code not in valid_dimension_codes:
                        raise ValueError(
                            f"drill_order[{i}][{j}] references unknown dimension code: '{dim_code}'"
                        )

        return algo

    def __eq__(self, other: object) -> bool:
        """
        Check equality with another Algorithm instance.

        Args:
            other: Another object to compare with.

        Returns:
            True if other is an Algorithm with the same field values,
            False otherwise.

        Examples:
            >>> a1 = Algorithm(id=1, drill_order=[["a"]])
            >>> a2 = Algorithm(id=1, drill_order=[["a"]])
            >>> a1 == a2
            True
        """
        if not isinstance(other, Algorithm):
            return False
        return self.id == other.id and self.drill_order == other.drill_order

    def __repr__(self) -> str:
        """
        Return a detailed string representation of the Algorithm.

        Returns:
            A string representation containing all field values.

        Examples:
            >>> Algorithm(id=1, drill_order=[["a"]])
            Algorithm(id=1, drill_order=[['a']])
        """
        return f"Algorithm(id={self.id}, drill_order={self.drill_order!r})"

    def __hash__(self) -> int:
        """
        Return a hash value for the Algorithm.

        Returns:
            Hash value based on id and drill_order.

        Examples:
            >>> a1 = Algorithm(id=1, drill_order=[["a"]])
            >>> a2 = Algorithm(id=1, drill_order=[["a"]])
            >>> hash(a1) == hash(a2)
            True
        """
        # Convert drill_order to tuples for hashing
        order_tuples = tuple(tuple(step) for step in self.drill_order)
        return hash((self.id, order_tuples))
