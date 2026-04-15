"""
Query module for database query parameter representation.

This module defines the Query class which represents database query
parameters used for fetching plan/actual values of metrics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Query:
    """
    Represents database query parameters for fetching metric values.

    The Query class defines filters and parameters used to retrieve
    plan and actual values for a metric from the database. Query
    parameters are stored as key-value pairs where values can be
    either strings or lists of strings.

    Attributes:
        fields: Dictionary of field name to field value mappings.
            Values can be strings or lists of strings.

    Examples:
        >>> query = Query(fields={"segment": "corporate"})
        >>> query.fields
        {'segment': 'corporate'}

        >>> query = Query(fields={
        ...     "segment": ["corporate", "sme"],
        ...     "metric": "interest_income"
        ... })
        >>> len(query.fields)
        2

        >>> empty = Query()
        >>> len(empty.fields)
        0
    """

    fields: dict[str, str | list[str]] | None = None
    """
    Dictionary of field name to field value mappings.

    Values can be:
    - str: Single value for the field
    - list[str]: Multiple values for the field (e.g., segment filter)

    None indicates no query parameters (metric calculated from children).
    """

    def __post_init__(self) -> None:
        """
        Validate the Query after initialization.

        Ensures that:
        - All field names are non-empty strings
        - All field values are non-empty strings or non-empty lists of strings
        - List values contain only non-empty strings
        """
        if self.fields is None:
            return

        if not isinstance(self.fields, dict):
            raise ValueError("Query fields must be a dictionary")

        for key, value in self.fields.items():
            # Validate field name
            if not isinstance(key, str) or not key:
                raise ValueError("Query field name must be a non-empty string")

            # Validate field value
            if isinstance(value, str):
                if not value:
                    raise ValueError(f"Query field '{key}' must not be empty")
            elif isinstance(value, list):
                if len(value) == 0:
                    raise ValueError(f"Query field '{key}' list must not be empty")
                for i, item in enumerate(value):
                    if not isinstance(item, str) or not item:
                        raise ValueError(
                            f"Query field '{key}'[{i}] must be a non-empty string"
                        )
            else:
                raise ValueError(
                    f"Query field '{key}' must be a string or list of strings"
                )

    def get_field(self, name: str) -> str | list[str] | None:
        """
        Get a field value by name.

        Args:
            name: Name of the field to retrieve.

        Returns:
            The field value if found, None otherwise.

        Examples:
            >>> query = Query(fields={"segment": "corporate"})
            >>> query.get_field("segment")
            'corporate'
            >>> query.get_field("not_found") is None
            True
        """
        if self.fields is None:
            return None
        return self.fields.get(name)

    def get_field_as_list(self, name: str) -> list[str]:
        """
        Get a field value as a list (always returns a list).

        Single string values are wrapped in a list.

        Args:
            name: Name of the field to retrieve.

        Returns:
            List of field values. Empty list if field not found.

        Examples:
            >>> query = Query(fields={"segment": "corporate"})
            >>> query.get_field_as_list("segment")
            ['corporate']

            >>> query = Query(fields={"segment": ["a", "b"]})
            >>> query.get_field_as_list("segment")
            ['a', 'b']
        """
        value = self.get_field(name)
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return list(value)

    def is_empty(self) -> bool:
        """
        Check if the query has no fields.

        Returns:
            True if the query has no fields, False otherwise.

        Examples:
            >>> Query().is_empty()
            True
            >>> Query(fields={"a": "b"}).is_empty()
            False
        """
        return self.fields is None or len(self.fields) == 0

    def to_dict(self) -> dict[str, object] | None:
        """
        Convert the Query to a dictionary representation for JSON serialization.

        Returns None if the query is empty (no fields).

        Returns:
            Dictionary representation of the Query, or None if empty.

        Examples:
            >>> query = Query(fields={"segment": "corporate"})
            >>> query.to_dict()
            {'segment': 'corporate'}

            >>> Query().to_dict() is None
            True
        """
        if self.is_empty():
            return None
        # Return a copy to prevent external modification
        return dict(self.fields)

    @classmethod
    def from_dict(cls, data: dict[str, object] | None) -> Query:
        """
        Create a Query instance from a dictionary.

        Args:
            data: Dictionary containing the query data, or None for empty query.

        Returns:
            A new Query instance populated from the dictionary.

        Raises:
            ValueError: If any field has an invalid value.

        Examples:
            >>> data = {"segment": "corporate", "metric": "interest_income"}
            >>> query = Query.from_dict(data)
            >>> query.get_field("segment")
            'corporate'

            >>> Query.from_dict(None).is_empty()
            True
        """
        if data is None or len(data) == 0:
            return cls()

        # Process and validate fields
        fields: dict[str, str | list[str]] = {}
        for key, value in data.items():
            if not isinstance(key, str) or not key:
                raise ValueError("Query field name must be a non-empty string")

            if value is None:
                # Skip None values (equivalent to not having the field)
                continue

            if isinstance(value, str):
                if not value:
                    raise ValueError(f"Query field '{key}' must not be empty")
                fields[key] = value
            elif isinstance(value, list):
                if len(value) == 0:
                    raise ValueError(f"Query field '{key}' list must not be empty")
                processed_list: list[str] = []
                for i, item in enumerate(value):
                    if isinstance(item, str) and item:
                        processed_list.append(item)
                    elif item is None:
                        # Skip None values in list
                        continue
                    else:
                        raise ValueError(
                            f"Query field '{key}'[{i}] must be a non-empty string"
                        )
                if len(processed_list) == 0:
                    # All items were None, skip this field
                    continue
                fields[key] = processed_list
            elif isinstance(value, (int, float, bool)):
                # Convert numeric/boolean values to strings
                fields[key] = str(value)
            else:
                raise ValueError(
                    f"Query field '{key}' must be a string, list, number, or boolean"
                )

        return cls(fields=fields if fields else None)

    def __eq__(self, other: object) -> bool:
        """
        Check equality with another Query instance.

        Args:
            other: Another object to compare with.

        Returns:
            True if other is a Query with the same field values,
            False otherwise.

        Examples:
            >>> q1 = Query(fields={"a": "b"})
            >>> q2 = Query(fields={"a": "b"})
            >>> q1 == q2
            True
        """
        if not isinstance(other, Query):
            return False
        return self.fields == other.fields

    def __repr__(self) -> str:
        """
        Return a detailed string representation of the Query.

        Returns:
            A string representation containing all field values.

        Examples:
            >>> Query(fields={"a": "b"})
            Query(fields={'a': 'b'})
        """
        return f"Query(fields={self.fields!r})"

    def __hash__(self) -> int:
        """
        Return a hash value for the Query.

        Note: Lists in fields are converted to tuples for hashing.

        Returns:
            Hash value based on all field values.

        Examples:
            >>> q1 = Query(fields={"a": "b"})
            >>> q2 = Query(fields={"a": "b"})
            >>> hash(q1) == hash(q2)
            True
        """
        if self.fields is None:
            return hash(None)
        # Convert lists to tuples for hashing
        hashable_fields: dict[str, str | tuple[str, ...]] = {}
        for key, value in self.fields.items():
            if isinstance(value, list):
                hashable_fields[key] = tuple(value)
            else:
                hashable_fields[key] = value
        return hash(frozenset(hashable_fields.items()))
