"""
Класс Hierarchy для управления деревом метрик факторного анализа.

Hierarchy представляет собой контейнер для всех узлов иерархии показателей,
обеспечивая навигацию, валидацию структуры и сериализацию/десериализацию.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Set
import json

from .metric_node import MetricNode
from .enums import MetricType, ComponentMultiPartType, ComponentRatioPartType
from .query import Query


@dataclass
class Hierarchy:
    """
    Контейнер для управления деревом метрик факторного анализа.

    Hierarchy хранит все узлы иерархии показателей и обеспечивает:
    - Навигацию по дереву (получение родителя, потомков, корня)
    - Валидацию целостности иерархии
    - Сериализацию/десериализацию в/из JSON
    - Добавление/удаление узлов

    Attributes:
        nodes: Словарь узлов, где ключ - id узла, значение - MetricNode

    Example:
        >>> hierarchy = Hierarchy()
        >>> node = MetricNode(id=100, code="NII", name="ЧПД", type=MetricType.SUM)
        >>> hierarchy.add_node(node)
        >>> root = hierarchy.get_root()
        >>> root.code
        'NII'
    """

    #: Словарь узлов иерархии (id -> MetricNode)
    nodes: Dict[int, MetricNode] = field(default_factory=dict)

    def add_node(self, node: MetricNode) -> None:
        """
        Добавить узел в иерархию.

        Args:
            node: Узел для добавления

        Raises:
            ValueError: Если узел с таким id уже существует

        Example:
            >>> hierarchy = Hierarchy()
            >>> node = MetricNode(id=100, code="NII", name="ЧПД")
            >>> hierarchy.add_node(node)
        """
        if node.id in self.nodes:
            raise ValueError(f"Узел с id={node.id} уже существует в иерархии")
        self.nodes[node.id] = node

    def remove_node(self, node_id: int) -> Optional[MetricNode]:
        """
        Удалить узел из иерархии.

        Args:
            node_id: ID узла для удаления

        Returns:
            Удаленный узел или None, если узел не найден

        Note:
            При удалении узла его потомки остаются в иерархии,
            но указывают на несуществующего родителя.
        """
        return self.nodes.pop(node_id, None)

    def get_node(self, node_id: int) -> Optional[MetricNode]:
        """
        Получить узел по ID.

        Args:
            node_id: ID искомого узла

        Returns:
            Узел MetricNode или None, если не найден

        Example:
            >>> hierarchy = Hierarchy()
            >>> node = hierarchy.get_node(100)
        """
        return self.nodes.get(node_id)

    def has_node(self, node_id: int) -> bool:
        """
        Проверить наличие узла в иерархии.

        Args:
            node_id: ID узла для проверки

        Returns:
            True, если узел существует, иначе False
        """
        return node_id in self.nodes

    def get_parent(self, node_id: int) -> Optional[MetricNode]:
        """
        Получить родительский узел.

        Args:
            node_id: ID узла

        Returns:
            Родительский узел или None, если у узла нет родителя или он не найден

        Example:
            >>> child = hierarchy.get_node(101)
            >>> parent = hierarchy.get_parent(101)
        """
        node = self.get_node(node_id)
        if node is None:
            return None
        if node.parent is None:
            return None
        return self.get_node(node.parent)

    def get_children(self, node_id: int) -> List[MetricNode]:
        """
        Получить список прямых потомков узла.

        Args:
            node_id: ID родительского узла

        Returns:
            Список дочерних узлов. Пустой список, если потомков нет

        Example:
            >>> children = hierarchy.get_children(100)
            >>> len(children)
            3
        """
        return [node for node in self.nodes.values() if node.parent == node_id]

    def get_root(self) -> Optional[MetricNode]:
        """
        Получить корневой узел иерархии.

        Returns:
            Корневой узел или None, если иерархия пуста

        Note:
            Иерархия может иметь только один корневой узел.
            Если корневых узлов несколько, возвращается первый найденный.

        Example:
            >>> root = hierarchy.get_root()
            >>> root.is_root()
            True
        """
        for node in self.nodes.values():
            if node.is_root():
                return node
        return None

    def get_roots(self) -> List[MetricNode]:
        """
        Получить список всех корневых узлов иерархии.

        Returns:
            Список корневых узлов

        Note:
            В корректной иерархии должен быть только один корневой узел.
        """
        return [node for node in self.nodes.values() if node.is_root()]

    def get_leaves(self) -> List[MetricNode]:
        """
        Получить список всех листовых узлов.

        Returns:
            Список листовых узлов (узлов без потомков)

        Example:
            >>> leaves = hierarchy.get_leaves()
            >>> for leaf in leaves:
            ...     print(f"{leaf.code}: {leaf.query}")
        """
        return [node for node in self.nodes.values() if node.is_leaf()]

    def get_descendants(self, node_id: int) -> List[MetricNode]:
        """
        Получить всех потомков узла (рекурсивно).

        Args:
            node_id: ID родительского узла

        Returns:
            Список всех потомков (прямых и косвенных)

        Example:
            >>> descendants = hierarchy.get_descendants(100)
            >>> len(descendants)
            5
        """
        children = self.get_children(node_id)
        result = []
        for child in children:
            result.append(child)
            result.extend(self.get_descendants(child.id))
        return result

    def get_ancestors(self, node_id: int) -> List[MetricNode]:
        """
        Получить всех предков узла (включая родителя).

        Args:
            node_id: ID узла

        Returns:
            Список предков от ближайшего к дальнему

        Example:
            >>> ancestors = hierarchy.get_ancestors(10201)
            >>> [a.code for a in ancestors]
            ['INT_EXP', 'NII']
        """
        node = self.get_node(node_id)
        if node is None:
            return []

        ancestors = []
        current_parent_id = node.parent

        while current_parent_id is not None:
            parent = self.get_node(current_parent_id)
            if parent is None:
                break
            ancestors.append(parent)
            current_parent_id = parent.parent

        return ancestors

    def get_path(self, node_id: int) -> List[MetricNode]:
        """
        Получить путь от корня к узлу.

        Args:
            node_id: ID целевого узла

        Returns:
            Список узлов от корня к указанному узлу

        Example:
            >>> path = hierarchy.get_path(10201)
            >>> [n.code for n in path]
            ['NII', 'INT_EXP', 'Ставка процентного расхода']
        """
        ancestors = self.get_ancestors(node_id)
        ancestors.reverse()  # От корня к родителю
        node = self.get_node(node_id)
        if node is not None:
            ancestors.append(node)
        return ancestors

    def count_nodes(self) -> int:
        """Возвращает количество узлов в иерархии."""
        return len(self.nodes)

    def is_empty(self) -> bool:
        """Проверяет, пуста ли иерархия."""
        return len(self.nodes) == 0

    def to_dict_list(self) -> List[dict]:
        """
        Преобразовать иерархию в список словарей.

        Все поля включаются, даже если равны None.

        Returns:
            Список словарей с данными всех узлов
        """
        return [node.to_dict() for node in self.nodes.values()]

    def to_json(self, *, include_empty_fields: bool = False) -> dict:
        """
        Подготовить иерархию для JSON-сериализации.

        Args:
            include_empty_fields: Если True, включать пустые поля в результат.
                                  Если False (по умолчанию), исключать пустые поля.

        Returns:
            Словарь, готовый для JSON-сериализации

        Example:
            >>> hierarchy = Hierarchy()
            >>> hierarchy.add_node(MetricNode(id=100, code="NII", name="ЧПД"))
            >>> json_dict = hierarchy.to_json()
            >>> json_str = json.dumps(json_dict, ensure_ascii=False, indent=2)
        """
        if include_empty_fields:
            return {"nodes": [node.to_dict() for node in self.nodes.values()]}
        return {"nodes": [node.to_json() for node in self.nodes.values()]}

    def to_json_string(self, *, indent: int = 2, include_empty_fields: bool = False) -> str:
        """
        Сериализовать иерархию в JSON-строку.

        Args:
            indent: Отступ для форматирования (по умолчанию 2)
            include_empty_fields: Если True, включать пустые поля

        Returns:
            JSON-строка с данными иерархии

        Example:
            >>> hierarchy = Hierarchy()
            >>> # ... добавляем узлы ...
            >>> json_str = hierarchy.to_json_string()
            >>> print(json_str)
        """
        data = self.to_json(include_empty_fields=include_empty_fields)
        return json.dumps(data, ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict_list(cls, data: List[dict]) -> "Hierarchy":
        """
        Создать иерархию из списка словарей.

        Args:
            data: Список словарей с данными узлов

        Returns:
            Экземпляр Hierarchy

        Raises:
            ValueError: При ошибке десериализации любого узла

        Example:
            >>> data = [
            ...     {"id": 100, "code": "NII", "name": "ЧПД", "type": "sum"},
            ...     {"id": 101, "code": "INT_INC", "name": "Процентный доход", "type": "multi", "parent": 100}
            ... ]
            >>> hierarchy = Hierarchy.from_dict_list(data)
        """
        hierarchy = cls()

        for node_data in data:
            try:
                node = MetricNode.from_dict(node_data)
                hierarchy.add_node(node)
            except ValueError as e:
                raise ValueError(f"Ошибка при десериализации узла {node_data}: {e}")

        return hierarchy

    @classmethod
    def from_json(cls, data: dict) -> "Hierarchy":
        """
        Создать иерархию из JSON-объекта (словаря).

        Args:
            data: Словарь из JSON, содержащий поле "nodes"

        Returns:
            Экземпляр Hierarchy

        Raises:
            ValueError: Если "nodes" отсутствует или не является списком

        Example:
            >>> json_dict = {"nodes": [
            ...     {"id": 100, "code": "NII", "name": "ЧПД"}
            ... ]}
            >>> hierarchy = Hierarchy.from_json(json_dict)
        """
        if "nodes" not in data:
            raise ValueError("JSON должен содержать поле 'nodes'")

        nodes_data = data["nodes"]
        if not isinstance(nodes_data, list):
            raise ValueError("Поле 'nodes' должно быть списком")

        return cls.from_dict_list(nodes_data)

    @classmethod
    def from_json_string(cls, json_string: str) -> "Hierarchy":
        """
        Десериализовать иерархию из JSON-строки.

        Args:
            json_string: JSON-строка с данными иерархии

        Returns:
            Экземпляр Hierarchy

        Raises:
            json.JSONDecodeError: При ошибке парсинга JSON
            ValueError: При ошибке структуры данных

        Example:
            >>> json_str = '{"nodes": [{"id": 100, "code": "NII", "name": "ЧПД"}]}'
            >>> hierarchy = Hierarchy.from_json_string(json_str)
        """
        data = json.loads(json_string)
        return cls.from_json(data)

    def validate(self) -> List[str]:
        """
        Проверить корректность структуры иерархии.

        Выполняет валидацию всех узлов и целостности связей.

        Returns:
            Список строк с описанием ошибок. Пустой список - ошибок нет.

        Validation rules:
        - Должен быть ровно один корневой узел
        - Родитель каждого узла должен существовать (кроме корня)
        - Не должно быть циклических ссылок
        - Узел типа MULTI должен иметь ровно двух потомков с rate и base
        - Узел типа RATIO должен иметь ровно двух потомков с numerator и denominator
        - Все узлы должны быть валидны индивидуально
        """
        errors = []

        # Валидация каждого узла
        for node in self.nodes.values():
            node_errors = node.validate()
            errors.extend([f"{node.code} (id={node.id}): {err}" for err in node_errors])

        # Проверка корневых узлов
        roots = self.get_roots()
        if len(roots) == 0:
            errors.append("Иерархия должна иметь ровно один корневой узел, найдено 0")
        elif len(roots) > 1:
            root_codes = [f"{r.code} (id={r.id})" for r in roots]
            errors.append(f"Иерархия должна иметь ровно один корневой узел, найдено {len(roots)}: {', '.join(root_codes)}")

        # Проверка существования родительских узлов
        for node in self.nodes.values():
            if node.parent is not None and node.parent not in self.nodes:
                errors.append(f"Узел {node.code} (id={node.id}) ссылается на несуществующий родитель (parent={node.parent})")

        # Проверка componentMultiPartType - должен использоваться только с родителем типа MULTI
        for node in self.nodes.values():
            if node.componentMultiPartType is not None:
                parent = self.get_parent(node.id)
                if parent is None or parent.type != MetricType.MULTI:
                    parent_info = f"parent={node.parent}" if parent is None else f"{parent.code} (type={parent.type.value})"
                    errors.append(f"Узел {node.code} (id={node.id}) имеет componentMultiPartType, но его родитель {parent_info} не имеет type=MULTI")

        # Проверка componentRatioPartType - должен использоваться только с родителем типа RATIO
        for node in self.nodes.values():
            if node.componentRatioPartType is not None:
                parent = self.get_parent(node.id)
                if parent is None or parent.type != MetricType.RATIO:
                    parent_info = f"parent={node.parent}" if parent is None else f"{parent.code} (type={parent.type.value})"
                    errors.append(f"Узел {node.code} (id={node.id}) имеет componentRatioPartType, но его родитель {parent_info} не имеет type=RATIO")

        # Проверка на циклические ссылки
        visited = set()
        recursion_stack = set()

        def has_cycle(node_id: int) -> bool:
            """Проверить наличие цикла, начиная с указанного узла."""
            visited.add(node_id)
            recursion_stack.add(node_id)

            for child in self.get_children(node_id):
                if child.id not in visited:
                    if has_cycle(child.id):
                        return True
                elif child.id in recursion_stack:
                    # Цикл найден - это не может произойти при правильной структуре дерева,
                    # так как потомки не ссылаются на родителей, но проверим на всякий случай
                    return True

            recursion_stack.remove(node_id)
            return False

        # Проверяем каждого корня на наличие циклов
        for root in roots:
            if has_cycle(root.id):
                errors.append(f"Обнаружен циклический путь, начинающийся с {root.code} (id={root.id})")

        # Проверка узлов типа MULTI
        for node in self.nodes.values():
            if node.type == MetricType.MULTI:
                children = self.get_children(node.id)
                rate_children = [c for c in children if c.componentMultiPartType == ComponentMultiPartType.RATE]
                base_children = [c for c in children if c.componentMultiPartType == ComponentMultiPartType.BASE]

                if len(rate_children) != 1:
                    errors.append(f"Узел MULTI {node.code} (id={node.id}) должен иметь ровно одного потомка с componentMultiPartType=rate, найдено {len(rate_children)}")
                if len(base_children) != 1:
                    errors.append(f"Узел MULTI {node.code} (id={node.id}) должен иметь ровно одного потомка с componentMultiPartType=base, найдено {len(base_children)}")

        # Проверка узлов типа RATIO
        for node in self.nodes.values():
            if node.type == MetricType.RATIO:
                children = self.get_children(node.id)
                numerator_children = [c for c in children if c.componentRatioPartType == ComponentRatioPartType.NUMERATOR]
                denominator_children = [c for c in children if c.componentRatioPartType == ComponentRatioPartType.DENOMINATOR]

                if len(numerator_children) != 1:
                    errors.append(f"Узел RATIO {node.code} (id={node.id}) должен иметь ровно одного потомка с componentRatioPartType=numerator, найдено {len(numerator_children)}")
                if len(denominator_children) != 1:
                    errors.append(f"Узел RATIO {node.code} (id={node.id}) должен иметь ровно одного потомка с componentRatioPartType=denominator, найдено {len(denominator_children)}")

                # Проверка: дети RATIO не могут быть типа RATIO
                for child in children:
                    if child.type == MetricType.RATIO:
                        errors.append(f"Дочерний узел {child.code} (id={child.id}) не может быть типа RATIO")

        # Проверка: потомки листовых узлов (node.type is None)
        for node in self.nodes.values():
            if node.is_leaf():
                children = self.get_children(node.id)
                if children:
                    errors.append(f"Листовой узел {node.code} (id={node.id}) не может иметь потомков, найдено {len(children)}")

        return errors

    def is_valid(self) -> bool:
        """
        Быстро проверить валидность иерархии.

        Returns:
            True, если иерархия валидна, иначе False
        """
        return len(self.validate()) == 0

    def clear(self) -> None:
        """Очистить иерархию, удалив все узлы."""
        self.nodes.clear()

    def __len__(self) -> int:
        """Возвращает количество узлов в иерархии."""
        return len(self.nodes)

    def __contains__(self, node_id: int) -> bool:
        """Проверить наличие узла по ID."""
        return node_id in self.nodes

    def __iter__(self):
        """Итерация по узлам иерархии."""
        return iter(self.nodes.values())

    def __repr__(self) -> str:
        """Строковое представление Hierarchy."""
        return f"Hierarchy(nodes={len(self.nodes)})"

    def __eq__(self, other: object) -> bool:
        """Проверить равенство двух Hierarchy."""
        if not isinstance(other, Hierarchy):
            return False
        return self.nodes == other.nodes

    def visualize(self, node_id: Optional[int] = None, *, max_depth: int = 0, indent: str = "  ") -> str:
        """
        Получить текстовое представление иерархии.

        Args:
            node_id: ID узла для начала визуализации. Если None, используется корень.
            max_depth: Максимальная глубина. 0 - без ограничения.
            indent: Отступ для вложенных уровней.

        Returns:
            Строковое представление дерева

        Example:
            >>> print(hierarchy.visualize())
            NII (id: 100)
              INT_INC (id: 101, type: multi)
                Ставка (id: 201, rate)
                Объем (id: 202, base)
        """
        if node_id is None:
            node_id = self.get_root().id if self.get_root() else None

        if node_id is None:
            return "<empty hierarchy>"

        node = self.get_node(node_id)
        if node is None:
            return f"<node {node_id} not found>"

        result = []

        def _visualize(n_id: int, depth: int, prefix: str) -> None:
            """Рекурсивная функция для визуализации."""
            if max_depth > 0 and depth > max_depth:
                return

            n = self.get_node(n_id)
            if n is None:
                return

            # Формируем строку для узла
            parts = [f"{n.code} (id: {n.id}"]
            if n.type is not None:
                parts.append(f", type: {n.type.value}")
            if n.componentMultiPartType is not None:
                parts.append(f", {n.componentMultiPartType.value}")
            if n.componentRatioPartType is not None:
                parts.append(f", {n.componentRatioPartType.value}")
            parts.append(")")

            result.append(f"{prefix}{', '.join(parts)}")

            # Рекурсивно обрабатываем потомков
            children = self.get_children(n_id)
            for i, child in enumerate(children):
                is_last = i == len(children) - 1
                child_prefix = prefix + ("└── " if is_last else "├── ")
                next_prefix = prefix + ("    " if is_last else "│   ")
                _visualize(child.id, depth + 1, child_prefix)
                if depth + 1 < max_depth or max_depth == 0:
                    # Рекурсивный вызов уже сделан выше, здесь просто проходим по потомкам
                    pass

        # Сначала добавляем корень
        parts = [f"{node.code} (id: {node.id}"]
        if node.type is not None:
            parts.append(f", type: {node.type.value}")
        if node.componentMultiPartType is not None:
            parts.append(f", {node.componentMultiPartType.value}")
        if node.componentRatioPartType is not None:
            parts.append(f", {node.componentRatioPartType.value}")
        parts.append(")")
        result.append(', '.join(parts))

        # Рекурсивно обрабатываем потомков
        children = self.get_children(node_id)
        for i, child in enumerate(children):
            is_last = i == len(children) - 1
            child_prefix = "├── " if not is_last else "└── "
            next_prefix = "│   " if not is_last else "    "

            # Формируем строку для ребенка
            parts = [f"{child.code} (id: {child.id}"]
            if child.type is not None:
                parts.append(f", type: {child.type.value}")
            if child.componentMultiPartType is not None:
                parts.append(f", {child.componentMultiPartType.value}")
            if child.componentRatioPartType is not None:
                parts.append(f", {child.componentRatioPartType.value}")
            parts.append(")")
            result.append(f"{child_prefix}{', '.join(parts)}")

            # Рекурсивно для потомков ребенка
            if max_depth == 0 or 2 <= max_depth:
                self._visualize_recursive(child.id, 2, next_prefix, max_depth, result)

        return "\n".join(result)

    def _visualize_recursive(self, node_id: int, current_depth: int, prefix: str, max_depth: int, result: List[str]) -> None:
        """Вспомогательный рекурсивный метод для визуализации."""
        if max_depth > 0 and current_depth > max_depth:
            return

        children = self.get_children(node_id)
        for i, child in enumerate(children):
            is_last = i == len(children) - 1
            child_prefix = prefix + ("└── " if is_last else "├── ")
            next_prefix = prefix + ("    " if is_last else "│   ")

            # Формируем строку для ребенка
            parts = [f"{child.code} (id: {child.id}"]
            if child.type is not None:
                parts.append(f", type: {child.type.value}")
            if child.componentMultiPartType is not None:
                parts.append(f", {child.componentMultiPartType.value}")
            if child.componentRatioPartType is not None:
                parts.append(f", {child.componentRatioPartType.value}")
            parts.append(")")
            result.append(f"{child_prefix}{', '.join(parts)}")

            # Рекурсивный вызов
            self._visualize_recursive(child.id, current_depth + 1, next_prefix, max_depth, result)
