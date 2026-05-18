"""
libfa2 - Library for Factor Analysis of variances between actual and planned values.

This library provides tools for performing factor analysis on financial metrics,
including hierarchical metric management and deviation analysis.

Modules:
    hier_metadata: Classes for managing hierarchical metric metadata
    analyt_struct_metadata: Classes for managing analytical structure metadata
"""

from libfa2 import analyt_struct_metadata
from libfa2 import hier_metadata

__all__ = ["hier_metadata", "analyt_struct_metadata"]
