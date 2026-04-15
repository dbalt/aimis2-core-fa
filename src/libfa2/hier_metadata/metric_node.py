"""
Metric node module for hierarchy representation.

This module defines the MetricNode class which represents a single
metric node in the factor analysis hierarchy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from libfa2.hier_metadata.enums import MetricType, MultiplierType

if TYPE_CHECKING:
    from libfa2.hier_metadata.query import Query


@dataclass
class MetricNode:
    """
    Represents a single metric node in the factor analysis hierarchy.

    A MetricNode can be:
    - A leaf node: fetched directly from the database
    - A composite node of type 'sum': calculated as sum of children
    - A composite node of type 'multi': calculated as product of rate and base
    - A composite node of type 'ratio': calculated as numerator / denominator

    Attributes:
        id: Unique numeric identifier of the metric.
        code: Short mnemonic code for API/UI usage.
        name: Human-readable display name of the metric.
        parent: ID of the parent metric, or None for root.
        type: Type of the metric (sum, multi, ratio) for composite nodes.
        query: Database query parameters for fetching plan/actual values.
        multiplier_type: Type of multiplier component (rate or base) for children of 'multi'.
        numerator: ID of the numerator metric for 'ratio' type.
        denominator: ID of the denominator metric for 'ratio' type.

    Examples:
        >>> node = MetricNode(
        ...     id=1,
        ...     code="FP",
        ...     name="Финансовый результат",
        ...     parent=None,
        ...     type=MetricType.SUM
        ... )
        >>> node.id
        1

        >>> leaf = MetricNode(
        ...     id=1001,
        ...     code="INT_INC",
        ...     name="Процентный доход",
        ...     parent=10,
        ...     query=Query(fields={"metric": "interest_income"})
        ... )
    """

    id: int
    """Unique numeric identifier of the metric."""

    code: str
    """Short mnemonic code for API/UI usage."""

    name: str
    """Human-readable display name of the metric."""

    parent: int | None = None
    """ID of the parent metric, or None for root node."""

    type: MetricType | None = None
    """
    Type of the metric for composite nodes.

    - None: Leaf node (or to be inferred)
    - MetricType.SUM: Sum of child components
    - MetricType.MULTI: Product of rate and base children
    - MetricType.RATIO: Ratio of numerator and denominator (root only)
    """

    query: Query | None = None
    """
    Database query parameters for fetching plan/actual values.

    Required for:
    - type: multi (for reverse calculation of rate)
    - Leaf nodes that are fetched directly from DB

    Optional for:
    - type: sum (if subtotal is stored in DB)
    - type: ratio (if ratio value is stored in DB)
    """

    multiplier_type: MultiplierType | None = None
    """
    Type of multiplier component for children of 'multi' nodes.

    - MultiplierType.RATE: Normalized indicator (calculated: rate = parent / base)
    - MultiplierType.BASE: Volumetric indicator (fetched from DB)

    Only applicable for child nodes of a 'multi' parent.
    """

    numerator: int | None = None
    """
    ID of the numerator metric for 'ratio' type.

    Required for metrics with type: MetricType.RATIO.
    The numerator can be a metric of type 'sum' or 'multi' with its own hierarchy.
    """

    denominator: int | None = None
    """
    ID of the denominator metric for 'ratio' type.

    Required for metrics with type: MetricType.RATIO.
    The denominator can be a metric of type 'sum' or 'multi' with its own hierarchy.
    """

    def __post_init__(self) -> None:
        """Validate the MetricNode after initialization."""
        # Validate ID
        if not isinstance(self.id, int) or self.id <= 0:
            raise ValueError("Metric ID must be a positive integer")

        # Validate code
        if not isinstance(self.code, str) or not self.code:
            raise ValueError("Metric code must be a non-empty string")

        # Validate name
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("Metric name must be a non-empty string")

        # Validate parent (if not None)
        if self.parent is not None and not isinstance(self.parent, int):
            raise ValueError("Metric parent must be an integer or None")

        # Validate numerator (if not None)
        if self.numerator is not None and not isinstance(self.numerator, int):
            raise ValueError("Metric numerator must be an integer or None")

        # Validate denominator (if not None)
        if self.denominator is not None and not isinstance(self.denominator, int):
            raise ValueError("Metric denominator must be an integer or None")

        # Type-specific validation
        if self.type == MetricType.MULTI:
            # 'multi' type MUST have a query
            if self.query is None:
                raise ValueError("Metric of type 'multi' must have a query")
            # 'multi' type cannot have numerator/denominator
            if self.numerator is not None or self.denominator is not None:
                raise ValueError("Metric of type 'multi' cannot have numerator/denominator")
        elif self.type == MetricType.RATIO:
            # 'ratio' type MUST have numerator and denominator
            if self.numerator is None:
                raise ValueError("Metric of type 'ratio' must have numerator")
            if self.denominator is None:
                raise ValueError("Metric of type 'ratio' must have denominator")
            # 'ratio' type cannot have multiplier_type
            if self.multiplier_type is not None:
                raise ValueError("Metric of type 'ratio' cannot have multiplier_type")

    @property
    def is_leaf(self) -> bool:
        """
        Check if this is a leaf node (has no type or is a child of sum/multi/ratio without children).

        Returns:
            True if this node appears to be a leaf, False otherwise.

        Examples:
            >>> node = MetricNode(id=1, code="A", name="A")
            >>> node.is_leaf
            True
        """
        # A node is a leaf if it doesn't have a type
        # (children will be determined by the Hierarchy class)
        return self.type is None

    @property
    def is_root(self) -> bool:
        """
        Check if this is a root node (has no parent).

        Returns:
            True if this node is a root, False otherwise.

        Examples:
            >>> node = MetricNode(id=1, code="A", name="A", parent=None)
            >>> node.is_root
            True
        """
        return self.parent is None

    @property
    def is_composite(self) -> bool:
        """
        Check if this is a composite node (has a type).

        Returns:
            True if this node has a type (sum, multi, or ratio), False otherwise.

        Examples:
            >>> node = MetricNode(id=1, code="A", name="A", type=MetricType.SUM)
            >>> node.is_composite
            True
        """
        return self.type is not None

    @property
    def is_multi_child(self) -> bool:
        """
        Check if this is a child of a 'multi' node.

        Returns:
            True if this node has a multiplier_type, False otherwise.

        Examples:
            >>> node = MetricNode(
            ...     id=1, code="A", name="A",
            ...     multiplier_type=MultiplierType.RATE
            ... )
            >>> node.is_multi_child
            True
        """
        return self.multiplier_type is not None

    @property
    def is_ratio_root(self) -> bool:
        """
        Check if this is a ratio-type root node.

        Returns:
            True if this node has type RATIO and is a root, False otherwise.

        Examples:
            >>> node = MetricNode(
            ...     id=1, code="COR", name="COR", parent=None,
            ...     type=MetricType.RATIO, numerator=501, denominator=502
            ... )
            >>> node.is_ratio_root
            True
        """
        return self.is_root and self.type == MetricType.RATIO

    @property
    def is_rate_multiplier(self) -> bool:
        """
        Check if this is a rate-type multiplier component.

        Returns:
            True if this node has multiplier_type RATE, False otherwise.

        Examples:
            >>> node = MetricNode(
            ...     id=1, code="A", name="A",
            ...     multiplier_type=MultiplierType.RATE
            ... )
            >>> node.is_rate_multiplier
            True
        """
        return self.multiplier_type == MultiplierType.RATE

    @property
    def is_base_multiplier(self) -> bool:
        """
        Check if this is a base-type multiplier component.

        Returns:
            True if this node has multiplier_type BASE, False otherwise.

        Examples:
            >>> node = MetricNode(
            ...     id=1, code="A", name="A",
            ...     multiplier_type=MultiplierType.BASE
            ... )
            >>> node.is_base_multiplier
            True
        """
        return self.multiplier_type == MultiplierType.BASE

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the MetricNode to a dictionary representation for JSON serialization.

        Empty/None fields are omitted from the output unless they are required.

        Returns:
            Dictionary representation of the MetricNode.

        Examples:
            >>> from libfa2.hier_metadata.query import Query
            >>> node = MetricNode(
            ...     id=1,
            ...     code="A",
            ...     name="A",
            ...     parent=None
            ... )
            >>> result = node.to_dict()
            >>> result["id"]
            1
        """
        result: dict[str, Any] = {
            "id": self.id,
            "code": self.code,
            "name": self.name,
        }

        # Add optional fields only if they have values
        if self.parent is not None:
            result["parent"] = self.parent

        if self.type is not None:
            result["type"] = self.type.value

        if self.query is not None and not self.query.is_empty():
            result["query"] = self.query.to_dict()

        if self.multiplier_type is not None:
            result["multiplierType"] = self.multiplier_type.value

        if self.numerator is not None:
            result["numerator"] = self.numerator

        if self.denominator is not None:
            result["denominator"] = self.denominator

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MetricNode:
        """
        Create a MetricNode instance from a dictionary.

        Args:
            data: Dictionary containing the metric node data.

        Returns:
            A new MetricNode instance populated from the dictionary.

        Raises:
            KeyError: If required fields (id, code, name) are missing.
            ValueError: If any field has an invalid value.

        Examples:
            >>> data = {
            ...     "id": 1,
            ...     "code": "A",
            ...     "name": "A Metric",
            ...     "parent": None,
            ...     "type": "sum"
            ... }
            >>> node = MetricNode.from_dict(data)
            >>> node.code
            'A'
        """
        from libfa2.hier_metadata.query import Query

        # Extract required fields
        node_id = data.get("id")
        if node_id is None:
            raise KeyError("Missing required field: 'id'")

        code = data.get("code")
        if code is None:
            raise KeyError("Missing required field: 'code'")

        name = data.get("name")
        if name is None:
            raise KeyError("Missing required field: 'name'")

        # Extract optional fields
        parent = data.get("parent")
        type_str = data.get("type")
        query_data = data.get("query")
        multiplier_type_str = data.get("multiplierType")
        numerator = data.get("numerator")
        denominator = data.get("denominator")

        # Process type
        metric_type: MetricType | None = None
        if type_str is not None:
            try:
                metric_type = MetricType(type_str)
            except ValueError as e:
                raise ValueError(f"Invalid metric type: {type_str}") from e

        # Process multiplier_type
        multiplier_type: MultiplierType | None = None
        if multiplier_type_str is not None:
            try:
                multiplier_type = MultiplierType(multiplier_type_str)
            except ValueError as e:
                raise ValueError(f"Invalid multiplier type: {multiplier_type_str}") from e

        # Process query
        query: Query | None = None
        if query_data is not None:
            if not isinstance(query_data, dict):
                raise ValueError("Query must be a dictionary")
            query = Query.from_dict(query_data)
            if query.is_empty():
                query = None

        return cls(
            id=int(node_id),
            code=str(code),
            name=str(name),
            parent=int(parent) if parent is not None else None,
            type=metric_type,
            query=query,
            multiplier_type=multiplier_type,
            numerator=int(numerator) if numerator is not None else None,
            denominator=int(denominator) if denominator is not None else None,
        )

    def __eq__(self, other: object) -> bool:
        """
        Check equality with another MetricNode instance.

        Args:
            other: Another object to compare with.

        Returns:
            True if other is a MetricNode with the same field values,
            False otherwise.

        Examples:
            >>> n1 = MetricNode(id=1, code="A", name="A")
            >>> n2 = MetricNode(id=1, code="A", name="A")
            >>> n1 == n2
            True
        """
        if not isinstance(other, MetricNode):
            return False
        return (
            self.id == other.id
            and self.code == other.code
            and self.name == other.name
            and self.parent == other.parent
            and self.type == other.type
            and self.query == other.query
            and self.multiplier_type == other.multiplier_type
            and self.numerator == other.numerator
            and self.denominator == other.denominator
        )

    def __repr__(self) -> str:
        """
        Return a detailed string representation of the MetricNode.

        Returns:
            A string representation containing key field values.

        Examples:
            >>> MetricNode(id=1, code="A", name="A")
            MetricNode(id=1, code='A', name='A')
        """
        return (
            f"MetricNode(id={self.id}, code={self.code!r}, name={self.name!r}"
            f", parent={self.parent}, type={self.type}"
            f", multiplier_type={self.multiplier_type}"
            f", numerator={self.numerator}, denominator={self.denominator})"
        )

    def __hash__(self) -> int:
        """
        Return a hash value for the MetricNode.

        Returns:
            Hash value based on all field values.

        Examples:
            >>> n1 = MetricNode(id=1, code="A", name="A")
            >>> n2 = MetricNode(id=1, code="A", name="A")
            >>> hash(n1) == hash(n2)
            True
        """
        return hash((
            self.id,
            self.code,
            self.name,
            self.parent,
            self.type,
            self.query,
            self.multiplier_type,
            self.numerator,
            self.denominator,
        ))
