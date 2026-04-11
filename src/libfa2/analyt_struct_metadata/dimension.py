"""
Dimension module for analytical dimension representation.

This module defines the Dimension class which represents a single
analytical dimension used for drill-down in factor analysis.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Dimension:
    """
    Represents a single analytical dimension for drill-down analysis.

    A Dimension defines a measurement/dimension that can be used to
    detail financial data, such as segment, geographic structure,
    product, sales channel, etc.

    Attributes:
        code: Unique code for referencing this dimension in drill_order.
        name: Human-readable display name of the dimension.
        column: Database column name containing values for this dimension.

    Examples:
        >>> dim = Dimension(
        ...     code="segment",
        ...     name="Сегмент",
        ...     column="segment_id"
        ... )
        >>> dim.code
        'segment'

        >>> dim = Dimension(
        ...     code="geo_structure",
        ...     name="Геоструктура",
        ...     column="geo_structure_id"
        ... )
    """

    code: str
    """Unique code for referencing this dimension in drill_order."""

    name: str
    """Human-readable display name of the dimension."""

    column: str
    """Database column name containing values for this dimension."""

    def __post_init__(self) -> None:
        """Validate the Dimension after initialization."""
        if not self.code or not isinstance(self.code, str):
            raise ValueError("Dimension code must be a non-empty string")
        if not self.name or not isinstance(self.name, str):
            raise ValueError("Dimension name must be a non-empty string")
        if not self.column or not isinstance(self.column, str):
            raise ValueError("Dimension column must be a non-empty string")

    def to_dict(self) -> dict[str, object]:
        """
        Convert the Dimension to a dictionary representation for JSON serialization.

        All fields are included as they are required.

        Returns:
            Dictionary representation of the Dimension.

        Examples:
            >>> dim = Dimension(
            ...     code="segment",
            ...     name="Сегмент",
            ...     column="segment_id"
            ... )
            >>> d = dim.to_dict()
            >>> d["code"]
            'segment'
        """
        return {
            "code": self.code,
            "name": self.name,
            "column": self.column,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Dimension:
        """
        Create a Dimension instance from a dictionary.

        Args:
            data: Dictionary containing the dimension data.

        Returns:
            A new Dimension instance populated from the dictionary.

        Raises:
            KeyError: If required fields (code, name, column) are missing.
            ValueError: If any field has an invalid value.

        Examples:
            >>> data = {
            ...     "code": "segment",
            ...     "name": "Сегмент",
            ...     "column": "segment_id"
            ... }
            >>> dim = Dimension.from_dict(data)
            >>> dim.code
            'segment'
        """
        # Extract required fields
        code = data.get("code")
        name = data.get("name")
        column = data.get("column")

        if code is None:
            raise KeyError("Missing required field: 'code'")
        if name is None:
            raise KeyError("Missing required field: 'name'")
        if column is None:
            raise KeyError("Missing required field: 'column'")

        return cls(
            code=str(code),
            name=str(name),
            column=str(column),
        )

    def __eq__(self, other: object) -> bool:
        """
        Check equality with another Dimension instance.

        Args:
            other: Another object to compare with.

        Returns:
            True if other is a Dimension with the same field values,
            False otherwise.

        Examples:
            >>> d1 = Dimension(code="seg", name="Seg", column="seg_id")
            >>> d2 = Dimension(code="seg", name="Seg", column="seg_id")
            >>> d1 == d2
            True
        """
        if not isinstance(other, Dimension):
            return False
        return (
            self.code == other.code
            and self.name == other.name
            and self.column == other.column
        )

    def __repr__(self) -> str:
        """
        Return a detailed string representation of the Dimension.

        Returns:
            A string representation containing all field values.

        Examples:
            >>> Dimension(code="seg", name="Seg", column="seg_id")
            Dimension(code='seg', name='Seg', column='seg_id')
        """
        return (
            f"Dimension(code={self.code!r}, name={self.name!r}, "
            f"column={self.column!r})"
        )

    def __hash__(self) -> int:
        """
        Return a hash value for the Dimension.

        Returns:
            Hash value based on all field values.

        Examples:
            >>> d1 = Dimension(code="seg", name="Seg", column="seg_id")
            >>> d2 = Dimension(code="seg", name="Seg", column="seg_id")
            >>> hash(d1) == hash(d2)
            True
        """
        return hash((self.code, self.name, self.column))
