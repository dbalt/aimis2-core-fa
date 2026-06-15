"""
Класс TemplateLiteNode для узла упрощённого шаблона сценария обхода.

TemplateLiteNode представляет собой отдельный узел дерева сценария обхода
данных для факторного анализа («lite»-версия метаданных). Каждый узел
содержит имя, роль (подстатья / разрез / тариф / база) и связь с
родительским узлом.
"""

from dataclasses import dataclass
from typing import Optional

from .enums import NodeRole


@dataclass
class TemplateLiteNode:
    """
    Узел дерева сценария обхода данных (template lite).

    Attributes:
        id: Уникальный идентификатор узла в пределах одного сценария.
        name: Отображаемое имя узла (название статьи/разреза/тарифа/базы).
        role: Роль узла (см. :class:`NodeRole`).
        parent: ID родительского узла. ``None`` для корневого узла сценария.

    Example:
        >>> node = TemplateLiteNode(
        ...     id=1,
        ...     name="ЧКД+ ТБ",
        ...     role=NodeRole.PODSTATYA,
        ... )
        >>> node.is_root()
        True
        >>> tarif = TemplateLiteNode(
        ...     id=14, name="Маржа", role=NodeRole.TARIF, parent=6
        ... )
        >>> tarif.role == NodeRole.TARIF
        True
    """

    #: Уникальный идентификатор узла
    id: int

    #: Отображаемое имя узла
    name: str

    #: Роль узла (подстатья / разрез / тариф / база)
    role: NodeRole

    #: ID родительского узла. None для корня сценария
    parent: Optional[int] = None

    # --- Проверки ролей -------------------------------------------------

    def is_root(self) -> bool:
        """
        Проверить, является ли узел корневым.

        Returns:
            True, если parent is None, иначе False
        """
        return self.parent is None

    def is_podstatya(self) -> bool:
        """True, если узел — подстатья (суммируемый компонент)."""
        return self.role == NodeRole.PODSTATYA

    def is_razrez(self) -> bool:
        """True, если узел — аналитический разрез/срез данных."""
        return self.role == NodeRole.RAZREZ

    def is_tarif(self) -> bool:
        """True, если узел — тариф (компонент-множитель)."""
        return self.role == NodeRole.TARIF

    def is_baza(self) -> bool:
        """True, если узел — база (объёмный показатель)."""
        return self.role == NodeRole.BAZA

    # --- Сериализация ---------------------------------------------------

    def to_dict(self) -> dict:
        """
        Преобразовать узел в словарь.

        Поля ``role`` и ``parent`` включаются всегда, при этом ``parent``
        может быть ``None`` (как в исходном JSON).

        Returns:
            Словарь с полями узла
        """
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "parent": self.parent,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TemplateLiteNode":
        """
        Создать узел из словаря (десериализованного JSON).

        Args:
            data: Словарь с обязательными ключами ``id``, ``name``, ``role``
                  и необязательным ``parent``

        Returns:
            Экземпляр TemplateLiteNode

        Raises:
            ValueError: если обязательные поля отсутствуют, имеют неверный
                        тип или ``role`` содержит неизвестное значение

        Example:
            >>> data = {"id": 1, "name": "ЧКД+ ТБ", "role": "podstatya", "parent": None}
            >>> node = TemplateLiteNode.from_dict(data)
        """
        # --- обязательные поля ---
        if "id" not in data:
            raise ValueError("Обязательное поле 'id' отсутствует")
        node_id = data["id"]
        if not isinstance(node_id, int) or isinstance(node_id, bool):
            raise ValueError(f"Поле 'id' должно быть int, получено {type(node_id).__name__}")

        if "name" not in data:
            raise ValueError("Обязательное поле 'name' отсутствует")
        name = data["name"]
        if not isinstance(name, str):
            raise ValueError(f"Поле 'name' должно быть str, получено {type(name).__name__}")

        if "role" not in data:
            raise ValueError("Обязательное поле 'role' отсутствует")
        raw_role = data["role"]
        try:
            role = NodeRole(raw_role)
        except ValueError:
            valid = ", ".join(r.value for r in NodeRole)
            raise ValueError(
                f"Неверное значение 'role': {raw_role!r}. "
                f"Допустимые значения: {valid}"
            )

        # --- необязательное поле parent ---
        parent = data.get("parent")
        if parent is not None and not isinstance(parent, int):
            raise ValueError(
                f"Поле 'parent' должно быть int или null, получено {type(parent).__name__}"
            )

        return cls(id=node_id, name=name, role=role, parent=parent)

    # --- Валидация одного узла -----------------------------------------

    def validate(self) -> list[str]:
        """
        Проверить корректность заполнения полей узла.

        Returns:
            Список строк с описанием ошибок. Пустой список — ошибок нет.
        """
        errors: list[str] = []

        if not isinstance(self.id, int) or isinstance(self.id, bool) or self.id <= 0:
            errors.append(f"Поле 'id' должно быть положительным целым, получено {self.id!r}")

        if not self.name:
            errors.append(f"Поле 'name' не должно быть пустым (id={self.id})")

        if self.parent is not None and self.parent == self.id:
            errors.append(
                f"Поле 'parent' не может быть равно 'id' (циклическая ссылка, id={self.id})"
            )

        return errors

    def is_valid(self) -> bool:
        """True, если узел валиден."""
        return len(self.validate()) == 0

    # --- Dunder-методы --------------------------------------------------

    def __repr__(self) -> str:
        parent_repr = f", parent={self.parent}" if self.parent is not None else ""
        return (
            f"TemplateLiteNode(id={self.id}, name={self.name!r}, "
            f"role={self.role.value}{parent_repr})"
        )
