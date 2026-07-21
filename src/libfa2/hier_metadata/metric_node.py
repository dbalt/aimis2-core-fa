"""
Класс MetricNode для узлов иерархии показателей.

MetricNode представляет собой отдельный узел в иерархии финансовых показателей
факторного анализа. Каждый узел содержит метаданные о показателе и связь
с родительским узлом.
"""

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING
from .enums import MetricType, ComponentMultiPartType, ComponentRatioPartType, MultipartDecompositionType
from .query import Query

if TYPE_CHECKING:
    from libfa2.analyt_struct_metadata import AnalyticalStructureMetadata


@dataclass
class MetricNode:
    """
    Узел в иерархии показателей факторного анализа.

    Каждый узел представляет собой финансовый показатель с метаданными,
    необходимыми для выполнения факторного анализа.

    Attributes:
        id: Уникальный идентификатор показателя.
        code: Код показателя для системного использования.
        name: Отображаемое название показателя.
        type: Тип показателя (sum, multi, ratio). Если None - это листовой элемент.
        parent: ID родительского показателя. None для корневого узла.
        query: Параметры запроса к БД для получения данных. None если данные
               вычисляются из потомков.
        componentMultiPartType: Тип компонента-множителя (rate или base).
                                Используется для дочерних элементов type=MULTI.
        componentRatioPartType: Тип компонента-отношения (numerator или denominator).
                                  Используется для дочерних элементов type=RATIO.
        analyt_metadata: Опциональные метаданные разложения по аналитическим разрезам.
                         Может быть None для узлов, для которых детализация не применима.

    Example:
        >>> node = MetricNode(
        ...     id=100,
        ...     code="NII",
        ...     name="Чистый процентный доход",
        ...     type=MetricType.SUM,
        ...     parent=None
        ... )
        >>> leaf = MetricNode(
        ...     id=101,
        ...     code="INT_INC",
        ...     name="Процентный доход",
        ...     type=MetricType.MULTI,
        ...     parent=100,
        ...     query=Query({"metricType": "interest_income"})
        ... )
    """

    #: Уникальный идентификатор показателя
    id: int

    #: Код показателя для системного использования
    code: str

    #: Отображаемое название показателя
    name: str

    #: Тип показателя (sum, multi, ratio). None - листовой элемент
    type: Optional[MetricType] = None

    #: ID родительского показателя. None для корня
    parent: Optional[int] = None

    #: Параметры запроса к БД для получения данных
    query: Optional[Query] = None

    #: Тип компонента-множителя (rate или base)
    componentMultiPartType: Optional[ComponentMultiPartType] = None

    #: Тип компонента-отношения (numerator или denominator)
    componentRatioPartType: Optional[ComponentRatioPartType] = None

    #: Опциональные метаданные разложения по аналитическим разрезам
    analyt_metadata: Optional["AnalyticalStructureMetadata"] = None

    #: Флаг типа ставки
    flg_rate_type: Optional[bool] = None

    #: Тип декомпозиции для показателя типа MULTI (обязателен при type=MULTI)
    mp_decomp_tp: Optional[MultipartDecompositionType] = None

    def is_root(self) -> bool:
        """
        Проверить, является ли узел корневым.

        Returns:
            True, если parent=None, иначе False
        """
        return self.parent is None

    def is_leaf(self) -> bool:
        """
        Проверить, является ли узел листовым.

        Листовой узел:
        - Не имеет типа (type=None)
        - Обязательное наличие query

        Returns:
            True, если узел листовой, иначе False
        """
        return self.type is None

    def has_query(self) -> bool:
        """
        Проверить, есть ли у узла параметры запроса к БД.

        Returns:
            True, если query не None и не пустой, иначе False
        """
        return self.query is not None and not self.query.is_empty()

    def to_dict(self) -> dict:
        """
        Преобразовать MetricNode в словарь.

        Все поля включаются, даже если равны None.

        Returns:
            Словарь с полями узла

        Example:
            >>> node = MetricNode(id=100, code="NII", name="ЧПД", type=MetricType.SUM)
            >>> d = node.to_dict()
            >>> d["id"]
            100
        """
        result = {
            "id": self.id,
            "code": self.code,
            "name": self.name,
        }

        # Добавляем необязательные поля
        if self.type is not None:
            result["type"] = self.type.value
        if self.parent is not None:
            result["parent"] = self.parent
        if self.query is not None:
            result["query"] = self.query.to_dict()
        if self.componentMultiPartType is not None:
            result["componentMultiPartType"] = self.componentMultiPartType.value
        if self.componentRatioPartType is not None:
            result["componentRatioPartType"] = self.componentRatioPartType.value
        if self.analyt_metadata is not None:
            import json
            result["analyt_metadata"] = json.loads(self.analyt_metadata.to_json())
        if self.flg_rate_type is not None:
            result["flg_rate_type"] = self.flg_rate_type
        if self.mp_decomp_tp is not None:
            result["mp_decomp_tp"] = self.mp_decomp_tp.value

        return result

    def to_json(self) -> dict:
        """
        Подготовить MetricNode для JSON-сериализации.

        Пустые поля (None, пустой query) исключаются из результата.

        Returns:
            Словарь, готовый для JSON-сериализации

        Example:
            >>> node = MetricNode(
            ...     id=100,
            ...     code="NII",
            ...     name="ЧПД",
            ...     type=MetricType.SUM,
            ...     parent=None
            ... )
            >>> json_dict = node.to_json()
            >>> "parent" in json_dict  # parent=None, поэтому не включается
            False
        """
        result = {
            "id": self.id,
            "code": self.code,
            "name": self.name,
        }

        # Добавляем только непустые необязательные поля
        if self.type is not None:
            result["type"] = self.type.value
        if self.parent is not None:
            result["parent"] = self.parent
        if self.query is not None and not self.query.is_empty():
            result["query"] = self.query.to_json()
        if self.componentMultiPartType is not None:
            result["componentMultiPartType"] = self.componentMultiPartType.value
        if self.componentRatioPartType is not None:
            result["componentRatioPartType"] = self.componentRatioPartType.value
        if self.analyt_metadata is not None:
            import json
            # AnalyticalStructureMetadata сериализуется как {fa_impl: [...], dimensions: [...]}
            result["analyt_metadata"] = json.loads(self.analyt_metadata.to_json())
        if self.flg_rate_type is not None:
            result["flg_rate_type"] = self.flg_rate_type
        # mp_decomp_tp включается только при type=MULTI
        if self.mp_decomp_tp is not None and self.type == MetricType.MULTI:
            result["mp_decomp_tp"] = self.mp_decomp_tp.value

        return result

    @classmethod
    def from_dict(cls, data: dict) -> "MetricNode":
        """
        Создать MetricNode из словаря.

        Args:
            data: Словарь с полями узла

        Returns:
            Экземпляр MetricNode

        Raises:
            ValueError: Если обязательные поля отсутствуют или имеют неверный тип

        Example:
            >>> data = {
            ...     "id": 100,
            ...     "code": "NII",
            ...     "name": "Чистый процентный доход",
            ...     "type": "sum"
            ... }
            >>> node = MetricNode.from_dict(data)
        """
        # Проверка обязательных полей
        if "id" not in data:
            raise ValueError("Обязательное поле 'id' отсутствует")
        if "code" not in data:
            raise ValueError("Обязательное поле 'code' отсутствует")
        if "name" not in data:
            raise ValueError("Обязательное поле 'name' отсутствует")

        node_id = data["id"]
        if not isinstance(node_id, int):
            raise ValueError(f"Поле 'id' должно быть int, получено {type(node_id)}")

        code = data["code"]
        if not isinstance(code, str):
            raise ValueError(f"Поле 'code' должно быть str, получено {type(code)}")

        name = data["name"]
        if not isinstance(name, str):
            raise ValueError(f"Поле 'name' должно быть str, получено {type(name)}")

        # Обработка необязательных полей
        metric_type = None
        if "type" in data and data["type"] is not None:
            try:
                metric_type = MetricType(data["type"])
            except ValueError:
                raise ValueError(f"Неверное значение 'type': {data['type']}")

        parent = data.get("parent")

        # Обработка query
        query = None
        if "query" in data and data["query"] is not None:
            query = Query.from_dict(data["query"])

        # Обработка componentMultiPartType
        component_multi_part_type = None
        if "componentMultiPartType" in data and data["componentMultiPartType"] is not None:
            try:
                component_multi_part_type = ComponentMultiPartType(data["componentMultiPartType"])
            except ValueError:
                raise ValueError(f"Неверное значение 'componentMultiPartType': {data['componentMultiPartType']}")

        # Обработка componentRatioPartType
        component_ratio_part_type = None
        if "componentRatioPartType" in data and data["componentRatioPartType"] is not None:
            try:
                component_ratio_part_type = ComponentRatioPartType(data["componentRatioPartType"])
            except ValueError:
                raise ValueError(f"Неверное значение 'componentRatioPartType': {data['componentRatioPartType']}")

        # Обработка analyt_metadata
        analyt_metadata = None
        if "analyt_metadata" in data and data["analyt_metadata"] is not None:
            from libfa2.analyt_struct_metadata import AnalyticalStructureMetadata
            import json
            analyt_metadata = AnalyticalStructureMetadata.from_json(json.dumps(data["analyt_metadata"]))

        # Обработка flg_rate_type
        flg_rate_type = data.get("flg_rate_type")

        # Обработка mp_decomp_tp (читается только при type=multi)
        mp_decomp_tp = None
        if metric_type == MetricType.MULTI and "mp_decomp_tp" in data and data["mp_decomp_tp"] is not None:
            try:
                mp_decomp_tp = MultipartDecompositionType(data["mp_decomp_tp"])
            except ValueError:
                raise ValueError(f"Неверное значение 'mp_decomp_tp': {data['mp_decomp_tp']}")

        return cls(
            id=node_id,
            code=code,
            name=name,
            type=metric_type,
            parent=parent,
            query=query,
            componentMultiPartType=component_multi_part_type,
            componentRatioPartType=component_ratio_part_type,
            analyt_metadata=analyt_metadata,
            flg_rate_type=flg_rate_type,
            mp_decomp_tp=mp_decomp_tp,
        )

    @classmethod
    def from_json(cls, data: dict) -> "MetricNode":
        """
        Создать MetricNode из JSON-объекта (словаря).

        Метод аналогичен from_dict, но название подчеркивает,
        что ожидается десериализованный JSON.

        Args:
            data: Словарь из JSON

        Returns:
            Экземпляр MetricNode
        """
        return cls.from_dict(data)

    def validate(self) -> list[str]:
        """
        Проверить корректность заполнения полей узла.

        Выполняет валидацию в соответствии с правилами формирования иерархии.

        Returns:
            Список строк с описанием ошибок. Пустой список - ошибок нет.

        Validation rules:
        - id должен быть положительным
        - code не должен быть пустым
        - name не должен быть пустым
        - parent не может быть равен id (циклическая ссылка)
        - Листовой узел (type=None) должен иметь query
        - Узел типа MULTI должен иметь query
        - componentMultiPartType устанавливается только при type родителя=MULTI
        - componentRatioPartType устанавливается только при type родителя=RATIO
        """
        errors = []

        # Проверка id
        if self.id <= 0:
            errors.append(f"ID должен быть положительным числом, получен {self.id}")

        # Проверка code
        if not self.code:
            errors.append("Поле 'code' не должно быть пустым")

        # Проверка name
        if not self.name:
            errors.append("Поле 'name' не должно быть пустым")

        # Проверка parent
        if self.parent is not None and self.parent == self.id:
            errors.append("Поле 'parent' не может быть равно 'id' (циклическая ссылка)")

        # Проверка type и query
        if self.type is None:
            # Листовой узел
            if not self.has_query():
                errors.append(f"Листовой узел (id={self.id}, code={self.code}) должен иметь query")
        elif self.type == MetricType.MULTI:
            # Узел типа MULTI обязан иметь query
            if not self.has_query():
                errors.append(f"Узел типа MULTI (id={self.id}, code={self.code}) должен иметь query")
            # Узел типа MULTI обязан иметь mp_decomp_tp
            if self.mp_decomp_tp is None:
                errors.append(f"Узел типа MULTI (id={self.id}, code={self.code}) должен иметь mp_decomp_tp")
        elif self.type == MetricType.RATIO:
            # Узел типа RATIO обычно не имеет query (значение вычисляется)
            pass
        elif self.type == MetricType.SUM:
            # Узел типа SUM может иметь или не иметь query
            pass

        # Проверка: не должно быть одновременно componentMultiPartType и componentRatioPartType
        if self.componentMultiPartType is not None and self.componentRatioPartType is not None:
            errors.append(f"Узел (id={self.id}, code={self.code}) не может иметь одновременно componentMultiPartType и componentRatioPartType")

        return errors

    def is_valid(self) -> bool:
        """
        Быстро проверить валидность узла.

        Returns:
            True, если узел валиден, иначе False
        """
        return len(self.validate()) == 0

    def __repr__(self) -> str:
        """Строковое представление MetricNode."""
        parts = [f"id={self.id}", f"code={self.code!r}", f"name={self.name!r}"]
        if self.type is not None:
            parts.append(f"type={self.type.value}")
        if self.parent is not None:
            parts.append(f"parent={self.parent}")
        if self.flg_rate_type is not None:
            parts.append(f"flg_rate_type={self.flg_rate_type}")
        return f"MetricNode({', '.join(parts)})"

    def __eq__(self, other: object) -> bool:
        """Проверить равенство двух MetricNode."""
        if not isinstance(other, MetricNode):
            return False
        return (
            self.id == other.id and
            self.code == other.code and
            self.name == other.name and
            self.type == other.type and
            self.parent == other.parent and
            self.query == other.query and
            self.componentMultiPartType == other.componentMultiPartType and
            self.componentRatioPartType == other.componentRatioPartType and
            self.analyt_metadata == other.analyt_metadata and
            self.flg_rate_type == other.flg_rate_type and
            self.mp_decomp_tp == other.mp_decomp_tp
        )

    def __hash__(self) -> int:
        """Хеш MetricNode для использования в множествах."""
        return hash((
            self.id,
            self.code,
            self.name,
            self.type,
            self.parent,
            tuple(sorted(self.query.items())) if self.query else None,
            self.componentMultiPartType,
            self.componentRatioPartType,
            hash(str(self.analyt_metadata)) if self.analyt_metadata else None,
            self.flg_rate_type,
            self.mp_decomp_tp
        ))
