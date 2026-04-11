"""
MetricNode module for hierarchy node representation.

This module defines the MetricNode class which represents a single node
in the hierarchy of financial metrics used for factor analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from libfa2.hier_metadata.enums import DriverType, MetricType

if TYPE_CHECKING:
    from libfa2.hier_metadata.query import Query


@dataclass
class MetricNode:
    """
    Represents a single node in the metric hierarchy.

    A MetricNode can be:
    - A leaf node: A metric that can be directly retrieved from the database
    - A sum node: A composite metric equal to the sum of its children
    - A multi node: A composite metric equal to the product of its drivers
      (rate * base)

    Attributes:
        id: Unique numeric identifier of the metric.
        code: Short mnemonic code for API/UI usage.
        name: Human-readable display name of the metric.
        parent: ID of the parent metric, None for the root node.
        type: Type of composite metric ('sum' or 'multi'), optional.
        query: Query parameters for retrieving values from the database.
        driver_type: Type of driver ('rate' or 'base'), only for children
            of multi-type nodes.

    Examples:
        >>> node = MetricNode(
        ...     id=1001,
        ...     code="INT_INC",
        ...     name="Процентный доход",
        ...     parent=900,
        ...     query=Query({"segment": "corporate"})
        ... )

        >>> multi_node = MetricNode(
        ...     id=101,
        ...     code="INT_INC",
        ...     name="Процентный доход",
        ...     parent=10,
        ...     type=MetricType.MULTI,
        ...     query=Query({"metric": "interest_income"})
        ... )

        >>> rate_driver = MetricNode(
        ...     id=1001,
        ...     code="INT_RATE",
        ...     name="Ставка процентного дохода",
        ...     parent=101,
        ...     driver_type=DriverType.RATE
        ... )
    """

    id: int
    """Unique numeric identifier of the metric."""

    code: str
    """Short mnemonic code for API/UI usage."""

    name: str
    """Human-readable display name of the metric."""

    parent: int | None = None
    """ID of the parent metric. None for the root node."""

    type: MetricType | None = None
    """
    Type of composite metric.

    Required for non-leaf nodes:
    - MetricType.SUM: Equal to sum of children
    - MetricType.MULTI: Equal to product of drivers (rate * base)
    """

    query: Query | None = None
    """
    Query parameters for retrieving values from the database.

    Rules:
    - Required for MetricType.MULTI (for reverse rate calculation)
    - Optional for MetricType.SUM and leaf nodes
    - If present, DB values take precedence over calculated values
    """

    driver_type: DriverType | None = None
    """
    Type of driver for multi-type node children.

    Only applicable for children of nodes with type=MetricType.MULTI:
    - DriverType.RATE: Coefficient/rate (calculated: rate = multi / base)
    - DriverType.BASE: Volume/base metric
    """

    def __post_init__(self) -> None:
        """Validate the MetricNode after initialization."""
        # Import Query here to avoid circular dependency
        from libfa2.hier_metadata.query import Query

        if self.query is not None and not isinstance(self.query, Query):
            if isinstance(self.query, dict):
                self.query = Query(self.query)
            else:
                raise TypeError(
                    f"query must be a Query instance or dict, got {type(self.query)}"
                )

    @property
    def is_leaf(self) -> bool:
        """
        Check if this node is a leaf (has no children by definition).

        A node is considered a leaf by structure if it's a driver node
        (has driver_type) or if type is None.

        Note: The actual leaf status depends on the hierarchy structure,
        not just this property.

        Returns:
            True if this node is a leaf candidate, False otherwise.

        Examples:
            >>> node = MetricNode(id=1001, code="LEAF", name="Leaf", parent=10)
            >>> node.is_leaf
            True
            >>> parent = MetricNode(id=10, code="PARENT", name="Parent", type=MetricType.SUM)
            >>> parent.is_leaf
            False
        """
        return self.driver_type is not None or self.type is None

    @property
    def is_root(self) -> bool:
        """
        Check if this node is the root (has no parent).

        Returns:
            True if this node has no parent, False otherwise.

        Examples:
            >>> root = MetricNode(id=1, code="ROOT", name="Root")
            >>> root.is_root
            True
            >>> child = MetricNode(id=2, code="CHILD", name="Child", parent=1)
            >>> child.is_root
            False
        """
        return self.parent is None

    @property
    def is_sum_type(self) -> bool:
        """
        Check if this node is a sum-type composite metric.

        Returns:
            True if type is MetricType.SUM, False otherwise.

        Examples:
            >>> node = MetricNode(id=1, code="SUM", name="Sum", type=MetricType.SUM)
            >>> node.is_sum_type
            True
            >>> node = MetricNode(id=2, code="MULTI", name="Multi", type=MetricType.MULTI)
            >>> node.is_sum_type
            False
        """
        return self.type == MetricType.SUM

    @property
    def is_multi_type(self) -> bool:
        """
        Check if this node is a multi-type composite metric.

        Returns:
            True if type is MetricType.MULTI, False otherwise.

        Examples:
            >>> node = MetricNode(id=1, code="MULTI", name="Multi", type=MetricType.MULTI)
            >>> node.is_multi_type
            True
            >>> node = MetricNode(id=2, code="SUM", name="Sum", type=MetricType.SUM)
            >>> node.is_multi_type
            False
        """
        return self.type == MetricType.MULTI

    @property
    def is_rate_driver(self) -> bool:
        """
        Check if this node is a rate-type driver.

        Returns:
            True if driver_type is DriverType.RATE, False otherwise.

        Examples:
            >>> node = MetricNode(id=1, code="RATE", name="Rate", driver_type=DriverType.RATE)
            >>> node.is_rate_driver
            True
            >>> node = MetricNode(id=2, code="BASE", name="Base", driver_type=DriverType.BASE)
            >>> node.is_rate_driver
            False
        """
        return self.driver_type == DriverType.RATE

    @property
    def is_base_driver(self) -> bool:
        """
        Check if this node is a base-type driver.

        Returns:
            True if driver_type is DriverType.BASE, False otherwise.

        Examples:
            >>> node = MetricNode(id=1, code="BASE", name="Base", driver_type=DriverType.BASE)
            >>> node.is_base_driver
            True
            >>> node = MetricNode(id=2, code="RATE", name="Rate", driver_type=DriverType.RATE)
            >>> node.is_base_driver
            False
        """
        return self.driver_type == DriverType.BASE

    @property
    def requires_db_query(self) -> bool:
        """
        Check if this node requires a direct database query.

        Returns:
            True if the node has a query defined, False otherwise.

        Examples:
            >>> node = MetricNode(id=1, code="LEAF", name="Leaf", query=Query({"a": "b"}))
            >>> node.requires_db_query
            True
            >>> node = MetricNode(id=2, code="LEAF", name="Leaf")
            >>> node.requires_db_query
            False
        """
        return self.query is not None and not self.query.is_empty

    def to_dict(self) -> dict[str, object]:
        """
        Convert the MetricNode to a dictionary representation for JSON serialization.

        Empty/None fields are omitted from the output to keep the JSON compact.

        Returns:
            Dictionary representation of the MetricNode.

        Examples:
            >>> node = MetricNode(
            ...     id=1001,
            ...     code="INT_INC",
            ...     name="Процентный доход",
            ...     parent=900,
            ...     query=Query({"segment": "corporate"})
            ... )
            >>> d = node.to_dict()
            >>> d["id"]
            1001
            >>> d["code"]
            'INT_INC'
        """
        result: dict[str, object] = {
            "id": self.id,
            "code": self.code,
            "name": self.name,
        }

        # Add optional fields only if they have meaningful values
        if self.parent is not None:
            result["parent"] = self.parent
        if self.type is not None:
            result["type"] = self.type.value
        if self.query is not None and not self.query.is_empty:
            result["query"] = self.query.to_dict()
        if self.driver_type is not None:
            result["driverType"] = self.driver_type.value

        return result

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> MetricNode:
        """
        Create a MetricNode instance from a dictionary.

        Args:
            data: Dictionary containing the metric node data.

        Returns:
            A new MetricNode instance populated from the dictionary.

        Raises:
            KeyError: If required fields (id, code, name) are missing.
            ValueError: If type or driverType has an invalid value.

        Examples:
            >>> data = {
            ...     "id": 1001,
            ...     "code": "INT_INC",
            ...     "name": "Процентный доход",
            ...     "parent": 900,
            ...     "type": "multi",
            ...     "query": {"segment": "corporate"}
            ... }
            >>> node = MetricNode.from_dict(data)
            >>> node.id
            1001
            >>> node.code
            'INT_INC'
        """
        from libfa2.hier_metadata.query import Query

        # Extract required fields
        node_id = data["id"]
        code = data["code"]
        name = data["name"]

        # Extract optional fields
        parent = data.get("parent")
        type_str = data.get("type")
        query_dict = data.get("query")
        driver_type_str = data.get("driverType")

        # Convert string enums to enum values
        metric_type: MetricType | None = None
        if type_str is not None:
            try:
                metric_type = MetricType(type_str)
            except ValueError as e:
                raise ValueError(f"Invalid metric type: {type_str}") from e

        driver_type: DriverType | None = None
        if driver_type_str is not None:
            try:
                driver_type = DriverType(driver_type_str)
            except ValueError as e:
                raise ValueError(f"Invalid driver type: {driver_type_str}") from e

        # Create query if provided
        query: Query | None = None
        if query_dict is not None:
            if isinstance(query_dict, dict):
                query = Query(query_dict)
            else:
                raise TypeError(f"query must be a dict, got {type(query_dict)}")

        return cls(
            id=int(node_id),
            code=str(code),
            name=str(name),
            parent=int(parent) if parent is not None else None,
            type=metric_type,
            query=query,
            driver_type=driver_type,
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
            and self.driver_type == other.driver_type
        )

    def __repr__(self) -> str:
        """
        Return a detailed string representation of the MetricNode.

        Returns:
            A string representation containing all field values.

        Examples:
            >>> MetricNode(id=1, code="A", name="A")
            MetricNode(id=1, code='A', name='A', parent=None, type=None, query=None, driver_type=None)
        """
        return (
            f"MetricNode(id={self.id}, code={self.code!r}, name={self.name!r}, "
            f"parent={self.parent}, type={self.type}, query={self.query}, "
            f"driver_type={self.driver_type})"
        )

    def __hash__(self) -> int:
        """
        Return a hash value for the MetricNode.

        Returns:
            Hash value based on all field values.

        Examples:
            >>> hash(MetricNode(id=1, code="A", name="A")) == hash(MetricNode(id=1, code="A", name="A"))
            True
        """
        return hash((
            self.id,
            self.code,
            self.name,
            self.parent,
            self.type,
            self.query,
            self.driver_type,
        ))
