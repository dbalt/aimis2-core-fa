"""
Класс TemplateLiteNode для узла упрощённого шаблона сценария обхода.

TemplateLiteNode представляет собой отдельный узел дерева сценария обхода
данных для факторного анализа («lite»-версия метаданных). Каждый узел
содержит имя, роль (подстатья / разрез / тариф / база) и связь с
родительским узлом.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from sdk.core.logging import get_logger

from .enums import NodeRole

#: Ключ поля JSON-сценария, содержащего коды узлов управляющего куба.
#: Каждый элемент — объект с полями ``type_code``, ``fin_code`` и
#: ``node_code``; в :attr:`TemplateLiteNode.codes` каждый элемент
#: сохраняется как составной код ``f"{type_code}#{node_code}"`
#: (см. задачу ``31_temlate_lite__new_way_refac.md``). Поле ``fin_code``
#: намеренно не хранится (тип :attr:`codes` — ``List[str]``).
UPR_CUBE_CODES_KEY = "upr_cube_codes"

#: Ключ типа кода (``type_code``) внутри элемента ``upr_cube_codes``.
TYPE_CODE_KEY = "type_code"

#: Ключ отдельного кода узла (``node_code``) внутри элемента ``upr_cube_codes``.
NODE_CODE_KEY = "node_code"

#: Разделитель составного кода ``"<type_code>#<node_code>"`` в :attr:`codes`.
TYPE_CODE_SEP = "#"


@dataclass
class TemplateLiteNode:
    """
    Узел дерева сценария обхода данных (template lite).

    Attributes:
        id: Уникальный идентификатор узла в пределах одного сценария.
        name: Отображаемое имя узла (название статьи/разреза/тарифа/базы).
        role: Роль узла (см. :class:`NodeRole`).
        parent: ID родительского узла. ``None`` для корневого узла сценария.
        codes: Коды узлов управляющего куба. Каждый элемент — составной код
            ``"<type_code>#<node_code>"`` (например ``"PL#R_01_02"``),
            построенный из поля ``upr_cube_codes`` исходного JSON. Пустой
            список, если у элемента нет привязки к узлам куба. Используются при
            трансформации для формирования точного ``query`` MetricNode
            (``Query({'node_code': codes})``).

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

    #: Коды узлов управляющего куба. Каждый элемент — составной код вида
    #: ``"<type_code>#<node_code>"`` (например ``"PL#R_01_02"``), построенный
    #: из поля ``upr_cube_codes``. Пустой список, если элемент не привязан к
    #: узлам куба.
    codes: List[str] = field(default_factory=list)

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
        может быть ``None`` (как в исходном JSON). Поле ``upr_cube_codes``
        включается только при непустом :attr:`codes` и реконструируется из него:
        составной код ``"<type_code>#<node_code>"`` разбирается обратно в
        ``{type_code, node_code}``; код без разделителя (нет ``type_code``)
        сохраняется как ``{node_code}``. Поле ``fin_code`` намеренно не
        хранится (тип :attr:`codes` — ``List[str]``,
        см. задачу ``31_temlate_lite__new_way_refac.md``).

        Returns:
            Словарь с полями узла
        """
        result = {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "parent": self.parent,
        }
        if self.codes:
            upr_cube_codes = []
            for code in self.codes:
                if TYPE_CODE_SEP in code:
                    type_code, node_code = code.split(TYPE_CODE_SEP, 1)
                    upr_cube_codes.append(
                        {TYPE_CODE_KEY: type_code, NODE_CODE_KEY: node_code}
                    )
                else:
                    # Код без type_code — сохраняем как {node_code}.
                    upr_cube_codes.append({NODE_CODE_KEY: code})
            result[UPR_CUBE_CODES_KEY] = upr_cube_codes
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "TemplateLiteNode":
        """
        Создать узел из словаря (десериализованного JSON).

        Args:
            data: Словарь с обязательными ключами ``id``, ``name``, ``role``
                  и необязательными ``parent`` и ``upr_cube_codes``. Из
                  ``upr_cube_codes`` (список объектов с ``type_code``/
                  ``fin_code``/``node_code``) в :attr:`codes` попадают составные
                  коды ``f"{type_code}#{node_code}"`` (``fin_code`` не хранится;
                  при отсутствии ``type_code`` сохраняется просто ``node_code``).

        Returns:
            Экземпляр TemplateLiteNode

        Raises:
            ValueError: если обязательные поля отсутствуют, имеют неверный
                        тип или ``role`` содержит неизвестное значение

        Example:
            >>> data = {"id": 1, "name": "ЧКД+ ТБ", "role": "podstatya", "parent": None}
            >>> node = TemplateLiteNode.from_dict(data)
        """
        lgr = get_logger()
        lgr.debug(f"Десериализация узла из dict: {data}")

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

        # --- необязательное поле upr_cube_codes -> codes ---
        # Из каждого элемента upr_cube_codes (объект с type_code/fin_code/node_code)
        # строится составной код f"{type_code}#{node_code}". fin_code намеренно
        # отбрасывается (codes хранит List[str]). Если у элемента нет type_code,
        # в codes попадает просто node_code (без префикса) — это сохраняет
        # round-trip (to_dict -> from_dict) для узлов без type_code.
        codes: List[str] = []
        raw_codes = data.get(UPR_CUBE_CODES_KEY)
        if raw_codes is not None:
            if not isinstance(raw_codes, list):
                raise ValueError(
                    f"Поле {UPR_CUBE_CODES_KEY!r} должно быть списком, "
                    f"получено {type(raw_codes).__name__}"
                )
            for element in raw_codes:
                if not isinstance(element, dict) or NODE_CODE_KEY not in element:
                    lgr.warning(
                        f"Элемент {UPR_CUBE_CODES_KEY!r} без '{NODE_CODE_KEY}' "
                        f"пропущен: {element!r}"
                    )
                    continue
                node_code = element[NODE_CODE_KEY]
                if TYPE_CODE_KEY in element:
                    codes.append(
                        f"{element[TYPE_CODE_KEY]}{TYPE_CODE_SEP}{node_code}"
                    )
                else:
                    codes.append(node_code)
            lgr.debug(
                f"Из {UPR_CUBE_CODES_KEY!r} извлечено составных кодов: {len(codes)} шт."
            )

        lgr.debug(
            f"Узел создан: id={node_id} name={name!r} role={role.value} "
            f"parent={parent} codes={codes}"
        )
        return cls(id=node_id, name=name, role=role, parent=parent, codes=codes)

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
