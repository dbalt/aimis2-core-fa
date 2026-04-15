"""
Hierarchy module for managing metric tree structure.

This module defines the Hierarchy class which manages a tree of
metric nodes for factor analysis hierarchy.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from libfa2.hier_metadata.enums import (
    MetricType,
    MultiplierType,
    ValidationErrorType,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from libfa2.hier_metadata.metric_node import MetricNode
    from libfa2.hier_metadata.query import Query


@dataclass
class ValidationError:
    """
    Represents a validation error for hierarchy metadata.

    Attributes:
        type: The type of validation error.
        message: Human-readable description of the error.
        metric_id: ID of the metric where the error occurred, if applicable.
        details: Additional context about the error.
    """

    type: ValidationErrorType
    """The type of validation error."""

    message: str
    """Human-readable description of the error."""

    metric_id: int | None = None
    """ID of the metric where the error occurred, if applicable."""

    details: dict[str, Any] | None = None
    """Additional context about the error."""

    def __repr__(self) -> str:
        """Return a string representation of the ValidationError."""
        metric_info = f", metric_id={self.metric_id}" if self.metric_id else ""
        return (
            f"ValidationError(type={self.type}, message={self.message!r}"
            f"{metric_info})"
        )


@dataclass
class ValidationReport:
    """
    Report containing the results of hierarchy validation.

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
class Hierarchy:
    """
    Manages a tree of metric nodes for factor analysis hierarchy.

    The Hierarchy class provides methods for:
    - Adding and removing metrics
    - Serializing to/from JSON
    - Validating the structure
    - Finding metrics by ID or code
    - Navigating the hierarchy (finding children, parents, paths)

    Attributes:
        metrics: Dictionary mapping metric IDs to MetricNode instances.
    """

    metrics: dict[int, MetricNode] = field(default_factory=dict)
    """Dictionary mapping metric IDs to MetricNode instances."""

    @property
    def metric_ids(self) -> set[int]:
        """
        Get the set of all metric IDs in the hierarchy.

        Returns:
            Set of all metric IDs.

        Examples:
            >>> from libfa2.hier_metadata.metric_node import MetricNode
            >>> h = Hierarchy()
            >>> h.add_metric(MetricNode(id=1, code="A", name="A"))
            >>> h.metric_ids
            {1}
        """
        return set(self.metrics.keys())

    @property
    def metric_codes(self) -> set[str]:
        """
        Get the set of all metric codes in the hierarchy.

        Returns:
            Set of all metric codes.

        Examples:
            >>> from libfa2.hier_metadata.metric_node import MetricNode
            >>> h = Hierarchy()
            >>> h.add_metric(MetricNode(id=1, code="A", name="A"))
            >>> h.metric_codes
            {'A'}
        """
        return {m.code for m in self.metrics.values()}

    @property
    def roots(self) -> list[MetricNode]:
        """
        Get all root nodes (nodes with no parent).

        Returns:
            List of root MetricNode instances.

        Examples:
            >>> from libfa2.hier_metadata.metric_node import MetricNode
            >>> h = Hierarchy()
            >>> h.add_metric(MetricNode(id=1, code="A", name="A", parent=None))
            >>> h.add_metric(MetricNode(id=2, code="B", name="B", parent=1))
            >>> len(h.roots)
            1
        """
        return [m for m in self.metrics.values() if m.is_root]

    @property
    def leaves(self) -> list[MetricNode]:
        """
        Get all leaf nodes (nodes with no children).

        Returns:
            List of leaf MetricNode instances.

        Examples:
            >>> from libfa2.hier_metadata.metric_node import MetricNode
            >>> h = Hierarchy()
            >>> h.add_metric(MetricNode(id=1, code="A", name="A"))
            >>> h.add_metric(MetricNode(id=2, code="B", name="B", parent=1))
            >>> len(h.leaves)
            1
        """
        return [m for m in self.metrics.values() if len(self.get_children(m.id)) == 0]

    def add_metric(self, metric: MetricNode) -> None:
        """
        Add a metric to the hierarchy.

        Args:
            metric: The MetricNode to add.

        Raises:
            ValueError: If a metric with the same ID or code already exists.

        Examples:
            >>> from libfa2.hier_metadata.metric_node import MetricNode
            >>> h = Hierarchy()
            >>> h.add_metric(MetricNode(id=1, code="A", name="A"))
            >>> 1 in h.metrics
            True
        """
        if metric.id in self.metrics:
            raise ValueError(f"Metric with id={metric.id} already exists")
        if metric.code in self.metric_codes:
            raise ValueError(f"Metric with code={metric.code!r} already exists")
        self.metrics[metric.id] = metric

    def add_metrics(self, metrics: Iterable[MetricNode]) -> None:
        """
        Add multiple metrics to the hierarchy.

        Args:
            metrics: Iterable of MetricNode instances to add.

        Raises:
            ValueError: If any metric with the same ID or code already exists.

        Examples:
            >>> from libfa2.hier_metadata.metric_node import MetricNode
            >>> h = Hierarchy()
            >>> metrics = [
            ...     MetricNode(id=1, code="A", name="A"),
            ...     MetricNode(id=2, code="B", name="B")
            ... ]
            >>> h.add_metrics(metrics)
            >>> len(h.metrics)
            2
        """
        # Check for duplicates first
        for metric in metrics:
            if metric.id in self.metrics:
                raise ValueError(f"Metric with id={metric.id} already exists")
            if metric.code in self.metric_codes:
                raise ValueError(f"Metric with code={metric.code!r} already exists")

        # Then add all
        for metric in metrics:
            self.metrics[metric.id] = metric

    def remove_metric(self, metric_id: int) -> None:
        """
        Remove a metric from the hierarchy.

        Args:
            metric_id: ID of the metric to remove.

        Raises:
            KeyError: If no metric with the given ID exists.

        Examples:
            >>> from libfa2.hier_metadata.metric_node import MetricNode
            >>> h = Hierarchy()
            >>> h.add_metric(MetricNode(id=1, code="A", name="A"))
            >>> h.remove_metric(1)
            >>> 1 not in h.metrics
            True
        """
        if metric_id not in self.metrics:
            raise KeyError(f"Metric with id={metric_id} not found")
        del self.metrics[metric_id]

    def get_metric(self, metric_id: int) -> MetricNode | None:
        """
        Get a metric by its ID.

        Args:
            metric_id: ID of the metric to retrieve.

        Returns:
            The MetricNode if found, None otherwise.

        Examples:
            >>> from libfa2.hier_metadata.metric_node import MetricNode
            >>> h = Hierarchy()
            >>> h.add_metric(MetricNode(id=1, code="A", name="A"))
            >>> h.get_metric(1).code
            'A'
            >>> h.get_metric(999) is None
            True
        """
        return self.metrics.get(metric_id)

    def get_metric_by_code(self, code: str) -> MetricNode | None:
        """
        Get a metric by its code.

        Args:
            code: Code of the metric to retrieve.

        Returns:
            The MetricNode if found, None otherwise.

        Examples:
            >>> from libfa2.hier_metadata.metric_node import MetricNode
            >>> h = Hierarchy()
            >>> h.add_metric(MetricNode(id=1, code="A", name="A"))
            >>> h.get_metric_by_code("A").id
            1
            >>> h.get_metric_by_code("not_found") is None
            True
        """
        for metric in self.metrics.values():
            if metric.code == code:
                return metric
        return None

    def get_children(self, metric_id: int) -> list[MetricNode]:
        """
        Get all direct children of a metric.

        Args:
            metric_id: ID of the parent metric.

        Returns:
            List of child MetricNode instances. Empty list if no children.

        Examples:
            >>> from libfa2.hier_metadata.metric_node import MetricNode
            >>> h = Hierarchy()
            >>> h.add_metric(MetricNode(id=1, code="A", name="A"))
            >>> h.add_metric(MetricNode(id=2, code="B", name="B", parent=1))
            >>> h.add_metric(MetricNode(id=3, code="C", name="C", parent=1))
            >>> len(h.get_children(1))
            2
        """
        return [m for m in self.metrics.values() if m.parent == metric_id]

    def get_parent(self, metric_id: int) -> MetricNode | None:
        """
        Get the parent of a metric.

        Args:
            metric_id: ID of the child metric.

        Returns:
            The parent MetricNode if found, None otherwise.

        Examples:
            >>> from libfa2.hier_metadata.metric_node import MetricNode
            >>> h = Hierarchy()
            >>> h.add_metric(MetricNode(id=1, code="A", name="A"))
            >>> h.add_metric(MetricNode(id=2, code="B", name="B", parent=1))
            >>> h.get_parent(2).code
            'A'
            >>> h.get_parent(1) is None
            True
        """
        metric = self.get_metric(metric_id)
        if metric is None or metric.parent is None:
            return None
        return self.get_metric(metric.parent)

    def get_ancestors(self, metric_id: int) -> list[MetricNode]:
        """
        Get all ancestors of a metric (from immediate parent to root).

        Args:
            metric_id: ID of the metric.

        Returns:
            List of ancestor MetricNode instances, ordered from parent to root.

        Examples:
            >>> from libfa2.hier_metadata.metric_node import MetricNode
            >>> h = Hierarchy()
            >>> h.add_metric(MetricNode(id=1, code="A", name="A"))
            >>> h.add_metric(MetricNode(id=2, code="B", name="B", parent=1))
            >>> h.add_metric(MetricNode(id=3, code="C", name="C", parent=2))
            >>> [m.code for m in h.get_ancestors(3)]
            ['B', 'A']
        """
        ancestors: list[MetricNode] = []
        current = self.get_parent(metric_id)
        while current is not None:
            ancestors.append(current)
            current = self.get_parent(current.id)
        return ancestors

    def get_descendants(self, metric_id: int) -> list[MetricNode]:
        """
        Get all descendants of a metric (all children, grandchildren, etc.).

        Args:
            metric_id: ID of the metric.

        Returns:
            List of descendant MetricNode instances (unordered).

        Examples:
            >>> from libfa2.hier_metadata.metric_node import MetricNode
            >>> h = Hierarchy()
            >>> h.add_metric(MetricNode(id=1, code="A", name="A"))
            >>> h.add_metric(MetricNode(id=2, code="B", name="B", parent=1))
            >>> h.add_metric(MetricNode(id=3, code="C", name="C", parent=2))
            >>> {m.code for m in h.get_descendants(1)}
            {'B', 'C'}
        """
        descendants: list[MetricNode] = []
        children = self.get_children(metric_id)
        for child in children:
            descendants.append(child)
            descendants.extend(self.get_descendants(child.id))
        return descendants

    def get_path_to_root(self, metric_id: int) -> list[MetricNode]:
        """
        Get the path from a metric to the root.

        Args:
            metric_id: ID of the metric.

        Returns:
            List of MetricNode instances from the metric to the root.

        Examples:
            >>> from libfa2.hier_metadata.metric_node import MetricNode
            >>> h = Hierarchy()
            >>> h.add_metric(MetricNode(id=1, code="A", name="A"))
            >>> h.add_metric(MetricNode(id=2, code="B", name="B", parent=1))
            >>> [m.code for m in h.get_path_to_root(2)]
            ['B', 'A']
        """
        metric = self.get_metric(metric_id)
        if metric is None:
            return []
        return [metric] + self.get_ancestors(metric_id)

    def get_depth(self, metric_id: int) -> int:
        """
        Get the depth of a metric in the hierarchy.

        Args:
            metric_id: ID of the metric.

        Returns:
            Depth of the metric (0 for root, 1 for root's children, etc.).

        Examples:
            >>> from libfa2.hier_metadata.metric_node import MetricNode
            >>> h = Hierarchy()
            >>> h.add_metric(MetricNode(id=1, code="A", name="A"))
            >>> h.add_metric(MetricNode(id=2, code="B", name="B", parent=1))
            >>> h.add_metric(MetricNode(id=3, code="C", name="C", parent=2))
            >>> h.get_depth(1)
            0
            >>> h.get_depth(3)
            2
        """
        return len(self.get_ancestors(metric_id))

    def get_max_depth(self) -> int:
        """
        Get the maximum depth of the hierarchy.

        Returns:
            Maximum depth of any metric in the hierarchy.

        Examples:
            >>> from libfa2.hier_metadata.metric_node import MetricNode
            >>> h = Hierarchy()
            >>> h.add_metric(MetricNode(id=1, code="A", name="A"))
            >>> h.add_metric(MetricNode(id=2, code="B", name="B", parent=1))
            >>> h.get_max_depth()
            1
        """
        max_depth = 0
        for metric_id in self.metric_ids:
            depth = self.get_depth(metric_id)
            if depth > max_depth:
                max_depth = depth
        return max_depth

    def is_ancestor_of(self, ancestor_id: int, descendant_id: int) -> bool:
        """
        Check if one metric is an ancestor of another.

        Args:
            ancestor_id: ID of the potential ancestor.
            descendant_id: ID of the potential descendant.

        Returns:
            True if ancestor_id is an ancestor of descendant_id, False otherwise.

        Examples:
            >>> from libfa2.hier_metadata.metric_node import MetricNode
            >>> h = Hierarchy()
            >>> h.add_metric(MetricNode(id=1, code="A", name="A"))
            >>> h.add_metric(MetricNode(id=2, code="B", name="B", parent=1))
            >>> h.add_metric(MetricNode(id=3, code="C", name="C", parent=2))
            >>> h.is_ancestor_of(1, 3)
            True
            >>> h.is_ancestor_of(3, 1)
            False
        """
        if ancestor_id == descendant_id:
            return False
        ancestors = {a.id for a in self.get_ancestors(descendant_id)}
        return ancestor_id in ancestors

    def to_json(self, indent: int | None = 2) -> str:
        """
        Serialize the hierarchy to a JSON string.

        Args:
            indent: Number of spaces for indentation. None for compact JSON.

        Returns:
            JSON string representation of the hierarchy.

        Examples:
            >>> from libfa2.hier_metadata.metric_node import MetricNode
            >>> h = Hierarchy()
            >>> h.add_metric(MetricNode(id=1, code="A", name="A"))
            >>> json_str = h.to_json()
            >>> '"metrics"' in json_str
            True
        """
        result = {
            "metrics": [metric.to_dict() for metric in self.metrics.values()],
        }
        return json.dumps(result, indent=indent, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> Hierarchy:
        """
        Deserialize hierarchy from a JSON string.

        Args:
            json_str: JSON string containing the hierarchy data.

        Returns:
            A new Hierarchy instance populated from the JSON.

        Raises:
            json.JSONDecodeError: If the JSON is invalid.
            ValueError: If the data is invalid.

        Examples:
            >>> json_str = '{"metrics": []}'
            >>> h = Hierarchy.from_json(json_str)
            >>> len(h.metrics)
            0
        """
        from libfa2.hier_metadata.metric_node import MetricNode

        data = json.loads(json_str)

        if not isinstance(data, dict):
            raise ValueError("Invalid JSON format: expected object")

        hierarchy = cls()

        # Load metrics
        metrics_data = data.get("metrics", [])
        if metrics_data:
            if not isinstance(metrics_data, list):
                raise ValueError("'metrics' must be a list")
            for metric_data in metrics_data:
                if not isinstance(metric_data, dict):
                    raise ValueError("Each metric must be a dictionary")
                metric = MetricNode.from_dict(metric_data)
                hierarchy.add_metric(metric)

        return hierarchy

    def validate(self) -> ValidationReport:
        """
        Validate the hierarchy metadata.

        Checks for:
        - Empty metrics
        - Multiple roots or no root
        - Duplicate metric IDs and codes
        - Missing parent references
        - Missing numerator/denominator references for ratio metrics
        - Invalid metric and multiplier types
        - Multiplier type on non-multi children
        - Missing query for multi metrics
        - Missing numerator/denominator for ratio metrics
        - Ratio metrics not at root or with children
        - Cyclic references
        - Disconnected subtrees
        - Incomplete multi children (missing rate or base)

        Returns:
            ValidationReport with results.

        Examples:
            >>> from libfa2.hier_metadata.metric_node import MetricNode
            >>> h = Hierarchy()
            >>> h.add_metric(MetricNode(id=1, code="A", name="A", parent=None))
            >>> report = h.validate()
            >>> report.is_valid
            True
        """
        errors: list[ValidationError] = []

        # Check for empty metrics
        if len(self.metrics) == 0:
            errors.append(ValidationError(
                type=ValidationErrorType.EMPTY_METRICS,
                message="Metrics list is empty",
            ))
            return ValidationReport(is_valid=False, errors=errors)

        # Check for duplicate metric IDs (shouldn't happen due to add_metric check)
        id_counts: dict[int, int] = {}
        for metric_id in self.metric_ids:
            id_counts[metric_id] = id_counts.get(metric_id, 0) + 1
        for metric_id, count in id_counts.items():
            if count > 1:
                errors.append(ValidationError(
                    type=ValidationErrorType.DUPLICATE_METRIC_ID,
                    message=f"Duplicate metric ID found: {metric_id} ({count} occurrences)",
                    metric_id=metric_id,
                ))

        # Check for duplicate metric codes (shouldn't happen due to add_metric check)
        code_counts: dict[str, int] = {}
        for code in self.metric_codes:
            code_counts[code] = code_counts.get(code, 0) + 1
        for code, count in code_counts.items():
            if count > 1:
                errors.append(ValidationError(
                    type=ValidationErrorType.DUPLICATE_METRIC_CODE,
                    message=f"Duplicate metric code found: {code!r} ({count} occurrences)",
                ))

        # Check for multiple roots
        root_nodes = self.roots
        if len(root_nodes) == 0:
            errors.append(ValidationError(
                type=ValidationErrorType.NO_ROOT,
                message="No root node found (at least one metric should have parent: null)",
            ))
        elif len(root_nodes) > 1:
            root_codes = [r.code for r in root_nodes]
            errors.append(ValidationError(
                type=ValidationErrorType.MULTIPLE_ROOTS,
                message=f"Multiple root nodes found: {root_codes} (should have exactly one)",
            ))

        # Check for cyclic references
        cycles = self._find_cycles()
        for cycle in cycles:
            cycle_path = " -> ".join(m.code for m in cycle)
            errors.append(ValidationError(
                type=ValidationErrorType.CYCLIC_REFERENCE,
                message=f"Cyclic reference detected: {cycle_path}",
                details={"cycle_ids": [m.id for m in cycle]},
            ))

        # Check for disconnected subtrees (metrics not reachable from root)
        if len(root_nodes) == 1:
            root_id = root_nodes[0].id
            reachable_ids = {m.id for m in self.get_descendants(root_id)} | {root_id}
            for metric_id in self.metric_ids:
                if metric_id not in reachable_ids:
                    metric = self.get_metric(metric_id)
                    errors.append(ValidationError(
                        type=ValidationErrorType.DISCONNECTED_SUBTREE,
                        message=f"Disconnected subtree found: metric {metric.code!r} (id={metric_id}) is not reachable from root",
                        metric_id=metric_id,
                    ))

        # Validate each metric
        for metric in self.metrics.values():
            # Validate parent reference
            if metric.parent is not None:
                parent = self.get_metric(metric.parent)
                if parent is None:
                    errors.append(ValidationError(
                        type=ValidationErrorType.MISSING_PARENT_REFERENCE,
                        message=f"Metric {metric.code!r} (id={metric.id}) references non-existent parent id={metric.parent}",
                        metric_id=metric.id,
                        details={"parent_id": metric.parent},
                    ))
                else:
                    # Validate multiplier type for children of 'multi' nodes
                    if metric.multiplier_type is not None:
                        if parent.type != MetricType.MULTI:
                            errors.append(ValidationError(
                                type=ValidationErrorType.INVALID_MULTIPLIER_FOR_NON_MULTI,
                                message=f"Metric {metric.code!r} (id={metric.id}) has multiplier_type but its parent {parent.code!r} (id={parent.id}) is not type 'multi'",
                                metric_id=metric.id,
                                details={"parent_id": parent.id, "parent_type": parent.type.value if parent.type else None},
                            ))

            # Validate ratio metrics
            if metric.type == MetricType.RATIO:
                # Ratio must be at root
                if not metric.is_root:
                    errors.append(ValidationError(
                        type=ValidationErrorType.RATIO_NOT_AT_ROOT,
                        message=f"Metric {metric.code!r} (id={metric.id}) has type 'ratio' but is not at root (parent={metric.parent})",
                        metric_id=metric.id,
                    ))

                # Ratio should not have children
                children = self.get_children(metric.id)
                if len(children) > 0:
                    errors.append(ValidationError(
                        type=ValidationErrorType.RATIO_HAS_CHILDREN,
                        message=f"Metric {metric.code!r} (id={metric.id}) has type 'ratio' but has {len(children)} children (ratio should be leaf)",
                        metric_id=metric.id,
                        details={"child_count": len(children)},
                    ))

                # Validate numerator reference
                if metric.numerator is not None:
                    if self.get_metric(metric.numerator) is None:
                        errors.append(ValidationError(
                            type=ValidationErrorType.MISSING_NUMERATOR_REFERENCE,
                            message=f"Metric {metric.code!r} (id={metric.id}) references non-existent numerator id={metric.numerator}",
                            metric_id=metric.id,
                            details={"numerator_id": metric.numerator},
                        ))

                # Validate denominator reference
                if metric.denominator is not None:
                    if self.get_metric(metric.denominator) is None:
                        errors.append(ValidationError(
                            type=ValidationErrorType.MISSING_DENOMINATOR_REFERENCE,
                            message=f"Metric {metric.code!r} (id={metric.id}) references non-existent denominator id={metric.denominator}",
                            metric_id=metric.id,
                            details={"denominator_id": metric.denominator},
                        ))

            # Validate multi metrics have query
            if metric.type == MetricType.MULTI and metric.query is None:
                errors.append(ValidationError(
                    type=ValidationErrorType.MISSING_QUERY_FOR_MULTI,
                    message=f"Metric {metric.code!r} (id={metric.id}) has type 'multi' but is missing query (required for reverse calculation of rate)",
                    metric_id=metric.id,
                ))

            # Validate multi children have both rate and base
            if metric.type == MetricType.MULTI:
                children = self.get_children(metric.id)
                if len(children) > 0:
                    has_rate = any(c.multiplier_type == MultiplierType.RATE for c in children)
                    has_base = any(c.multiplier_type == MultiplierType.BASE for c in children)
                    if not has_rate:
                        errors.append(ValidationError(
                            type=ValidationErrorType.INCOMPLETE_MULTI_CHILDREN,
                            message=f"Metric {metric.code!r} (id={metric.id}) has type 'multi' but no child with multiplier_type 'rate'",
                            metric_id=metric.id,
                        ))
                    if not has_base:
                        errors.append(ValidationError(
                            type=ValidationErrorType.INCOMPLETE_MULTI_CHILDREN,
                            message=f"Metric {metric.code!r} (id={metric.id}) has type 'multi' but no child with multiplier_type 'base'",
                            metric_id=metric.id,
                        ))

        return ValidationReport(is_valid=len(errors) == 0, errors=errors)

    def _find_cycles(self) -> list[list[MetricNode]]:
        """
        Find cyclic references in the hierarchy using DFS.

        Returns:
            List of cycles, where each cycle is a list of MetricNode instances.
        """
        visited: set[int] = set()
        rec_stack: set[int] = set()
        cycles: list[list[MetricNode]] = []

        def _dfs(node_id: int, path: list[MetricNode]) -> None:
            """Depth-first search to detect cycles."""
            visited.add(node_id)
            rec_stack.add(node_id)

            # Get parent
            metric = self.get_metric(node_id)
            if metric and metric.parent is not None:
                parent = self.get_metric(metric.parent)
                if parent:
                    if parent.id in rec_stack:
                        # Found a cycle
                        cycle_start = path.index(parent)
                        cycles.append(path[cycle_start:] + [parent])
                    elif parent.id not in visited:
                        _dfs(parent.id, path + [parent])

            rec_stack.remove(node_id)

        for metric_id in self.metric_ids:
            if metric_id not in visited:
                _dfs(metric_id, [self.get_metric(metric_id)])  # type: ignore

        return cycles

    def __eq__(self, other: object) -> bool:
        """
        Check equality with another Hierarchy instance.

        Args:
            other: Another object to compare with.

        Returns:
            True if other is a Hierarchy with the same metrics, False otherwise.
        """
        if not isinstance(other, Hierarchy):
            return False
        return self.metrics == other.metrics

    def __len__(self) -> int:
        """Return the total number of metrics in the hierarchy."""
        return len(self.metrics)

    def __contains__(self, key: int | str) -> bool:
        """
        Check if a metric ID or code exists in the hierarchy.

        Args:
            key: Either a metric ID (int) or metric code (str).

        Returns:
            True if the key exists, False otherwise.

        Examples:
            >>> from libfa2.hier_metadata.metric_node import MetricNode
            >>> h = Hierarchy()
            >>> h.add_metric(MetricNode(id=1, code="A", name="A"))
            >>> 1 in h
            True
            >>> "A" in h
            True
            >>> 2 in h
            False
        """
        if isinstance(key, int):
            return key in self.metrics
        elif isinstance(key, str):
            return key in self.metric_codes
        return False

    def __repr__(self) -> str:
        """Return a string representation of Hierarchy."""
        return f"Hierarchy(metrics={len(self.metrics)})"
