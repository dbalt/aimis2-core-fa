"""
Query module for database query parameters.

This module defines the Query class which represents the parameters
for filtering and retrieving plan/factual values from a database.
"""

from __future__ import annotations

from typing import Any, Self


class Query:
    """
    Represents database query parameters for retrieving metric values.

    The Query class encapsulates parameters for filtering and retrieving
    planned and factual values of a metric from the database. Each metric
    can have an optional query that defines how to fetch its data.

    Attributes:
        params (dict[str, Any] | None): Dictionary of field name to value
            mappings. Values can be single values or lists of values.
            None if the metric does not require a direct database query.

    Examples:
        >>> query = Query({"segment": "corporate", "product": "loans"})
        >>> query.params
        {'segment': 'corporate', 'product': 'loans'}

        >>> query = Query({"segment": ["corporate", "sme"]})
        >>> query.params
        {'segment': ['corporate', 'sme']}

        >>> empty_query = Query()
        >>> empty_query.params
        None
    """

    def __init__(self, params: dict[str, Any] | None = None) -> None:
        """
        Initialize a Query instance.

        Args:
            params: Dictionary of field name to value mappings. Can be None
                if the metric does not require a direct database query.

        Examples:
            >>> q = Query({"metric": "interest_income"})
            >>> q.params
            {'metric': 'interest_income'}
        """
        self.params = params if params else None

    @property
    def is_empty(self) -> bool:
        """
        Check if the query is empty (has no parameters).

        Returns:
            True if params is None or empty, False otherwise.

        Examples:
            >>> Query().is_empty
            True
            >>> Query({"segment": "corporate"}).is_empty
            False
        """
        return self.params is None or len(self.params) == 0

    def to_dict(self) -> dict[str, Any] | None:
        """
        Convert the Query to a dictionary representation.

        Returns:
            The params dictionary, or None if the query is empty.

        Examples:
            >>> Query({"segment": "corporate"}).to_dict()
            {'segment': 'corporate'}
            >>> Query().to_dict() is None
            True
        """
        return self.params

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Query:
        """
        Create a Query instance from a dictionary.

        Args:
            data: Dictionary containing query parameters. Can be None.

        Returns:
            A new Query instance with the given parameters.

        Examples:
            >>> Query.from_dict({"metric": "interest_income"}).params
            {'metric': 'interest_income'}
            >>> Query.from_dict(None).params
            None
        """
        return cls(params=data)

    def __eq__(self, other: object) -> bool:
        """
        Check equality with another Query instance.

        Args:
            other: Another object to compare with.

        Returns:
            True if other is a Query with the same params, False otherwise.

        Examples:
            >>> Query({"a": "b"}) == Query({"a": "b"})
            True
            >>> Query({"a": "b"}) == Query({"a": "c"})
            False
        """
        if not isinstance(other, Query):
            return False
        return self.params == other.params

    def __repr__(self) -> str:
        """
        Return a string representation of the Query.

        Returns:
            A string representation of the Query instance.

        Examples:
            >>> Query({"segment": "corporate"})
            Query(params={'segment': 'corporate'})
            >>> Query()
            Query(params=None)
        """
        return f"Query(params={self.params!r})"

    def __hash__(self) -> int:
        """
        Return a hash value for the Query.

        Returns:
            Hash value based on the params dictionary.

        Examples:
            >>> hash(Query({"a": "b"})) == hash(Query({"a": "b"}))
            True
        """
        if self.params is None:
            return hash(None)
        return hash(frozenset(
            (k, str(v) if isinstance(v, list) else v)
            for k, v in self.params.items()
        ))
