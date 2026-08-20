"""Исключения API-клиента Среды."""


class SredaAPIError(Exception):
    """Базовое исключение для ошибок API Среды."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class SredaHTTPError(SredaAPIError):
    """Ошибка HTTP-запроса к API Среды."""

    def __init__(self, guide_id: str, status_code: int, body: str) -> None:
        self.guide_id = guide_id
        self.status_code = status_code
        self.body = body
        super().__init__(
            f"Sreda API error: guide={guide_id[:12]} status={status_code}"
        )
