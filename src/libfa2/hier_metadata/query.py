"""
Класс Query для параметров запросов к БД.

Query представляет собой контейнер для параметров запроса к базе данных,
необходимых для получения значений показателя. Параметры могут быть
строками, числами или списками значений.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict
from collections.abc import Mapping


@dataclass
class Query:
    """
    Контейнер параметров запроса к базе данных.

    Параметры запроса используются для получения данных показателя
    из базы данных. Каждый параметр может быть:
    - Строкой
    - Числом (int, float)
    - Списком значений
    - Любым JSON-сериализуемым типом

    Attributes:
        params: Словарь параметров запроса. Ключ - имя параметра,
               значение - значение параметра (может быть списком).

    Example:
        >>> query = Query({"metricType": "interest_income"})
        >>> query = Query({"metricType": "interest_income", "segment": ["corporate", "retail"]})
    """

    #: Словарь параметров запроса
    params: Dict[str, Any] = field(default_factory=dict)

    def __init__(self, params: Dict[str, Any] | None = None):
        """
        Инициализация Query.

        Args:
            params: Словарь параметров запроса. Если None, создается пустой словарь.
        """
        self.params = params if params is not None else {}

    def add(self, key: str, value: Any) -> "Query":
        """
        Добавить или обновить параметр запроса.

        Args:
            key: Имя параметра
            value: Значение параметра

        Returns:
            Self для цепочки вызовов

        Example:
            >>> query = Query()
            >>> query.add("metricType", "interest_income").add("segment", "corporate")
        """
        self.params[key] = value
        return self

    def get(self, key: str, default: Any = None) -> Any:
        """
        Получить значение параметра.

        Args:
            key: Имя параметра
            default: Значение по умолчанию, если параметр не найден

        Returns:
            Значение параметра или default
        """
        return self.params.get(key, default)

    def remove(self, key: str) -> "Query":
        """
        Удалить параметр из запроса.

        Args:
            key: Имя параметра для удаления

        Returns:
            Self для цепочки вызовов
        """
        self.params.pop(key, None)
        return self

    def is_empty(self) -> bool:
        """
        Проверить, что запрос не содержит параметров.

        Returns:
            True, если запрос пустой, иначе False
        """
        return len(self.params) == 0

    def keys(self) -> list[str]:
        """Возвращает список ключей параметров."""
        return list(self.params.keys())

    def values(self) -> list[Any]:
        """Возвращает список значений параметров."""
        return list(self.params.values())

    def items(self) -> list[tuple[str, Any]]:
        """Возвращает список кортежей (ключ, значение)."""
        return list(self.params.items())

    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразовать Query в словарь.

        Returns:
            Словарь параметров запроса
        """
        return dict(self.params)

    def to_json(self) -> Dict[str, Any]:
        """
        Подготовить Query для JSON-сериализации.

        В отличие от to_dict(), этот метод удаляет пустые параметры
        (None, пустые строки, пустые списки).

        Returns:
            Словарь параметров, готовый для JSON-сериализации
        """
        return {k: v for k, v in self.params.items()
                if v is not None and v != "" and v != []}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Query":
        """
        Создать Query из словаря.

        Args:
            data: Словарь параметров

        Returns:
            Экземпляр Query

        Example:
            >>> data = {"metricType": "interest_income", "segment": "corporate"}
            >>> query = Query.from_dict(data)
        """
        return cls(dict(data) if data else None)

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "Query":
        """
        Создать Query из JSON-объекта (словаря).

        Метод аналогичен from_dict, но название подчеркивает,
        что ожидается десериализованный JSON.

        Args:
            data: Словарь из JSON

        Returns:
            Экземпляр Query
        """
        # Позволяем пустой словарь - это валидный пустой запрос
        if data is None:
            return cls()
        return cls(dict(data))

    def __bool__(self) -> bool:
        """
        Query является True, если содержит параметры.

        Returns:
            True, если параметры есть, иначе False
        """
        return not self.is_empty()

    def __len__(self) -> int:
        """Возвращает количество параметров."""
        return len(self.params)

    def __contains__(self, key: str) -> bool:
        """Проверить наличие параметра по ключу."""
        return key in self.params

    def __getitem__(self, key: str) -> Any:
        """Получить значение параметра по ключу."""
        return self.params[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """Установить значение параметра по ключу."""
        self.params[key] = value

    def __delitem__(self, key: str) -> None:
        """Удалить параметр по ключу."""
        del self.params[key]

    def __repr__(self) -> str:
        """Строковое представление Query."""
        return f"Query({self.params})"

    def __eq__(self, other: object) -> bool:
        """Проверить равенство двух Query."""
        if not isinstance(other, Query):
            return False
        return self.params == other.params

    def __hash__(self) -> int:
        """Хеш Query для использования в множествах и как ключ словаря."""
        # Преобразуем в кортеж отсортированных элементов для детерминированного хеша
        return hash(tuple(sorted(self.items())))
