"""Пакет API-клиента для платформы «Среда» (IFT)."""

from .client import SredaAPIClient, SredaClientConfig
from .exceptions import SredaAPIError, SredaHTTPError

__all__ = [
    "SredaAPIClient",
    "SredaClientConfig",
    "SredaAPIError",
    "SredaHTTPError",
]
