"""
Класс TemplateLite — контейнер упрощённого шаблона сценария обхода данных.

TemplateLite хранит имя показателя и дерево узлов сценария (статьи, разрезы,
тарифы, базы), обеспечивая навигацию по дереву, фильтрацию узлов по ролям,
валидацию структуры и сериализацию/десериализацию в/из JSON.
"""

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .enums import NodeRole
from .node import TemplateLiteNode


@dataclass
class TemplateLite:
    """
    Контейнер упрощённого шаблона сценария обхода данных (template lite).

    Attributes:
        metric_name: Имя показателя, для которого построен сценарий
                     (значение поля ``metricName`` исходного JSON).
        nodes: Словарь узлов сценария, где ключ — ``id`` узла,
               значение — :class:`TemplateLiteNode`.

    Example:
        >>> from libfa2.adhoc.template_lite import TemplateLite, TemplateLiteNode, NodeRole
        >>> root = TemplateLiteNode(id=1, name="ЧКД+ ТБ", role=NodeRole.PODSTATYA)
        >>> dim = TemplateLiteNode(id=2, name="ТБ/ГОСБ", role=NodeRole.RAZREZ, parent=1)
        >>> tpl = TemplateLite(metric_name="ЧКД+ ТБ")
        >>> tpl.add_node(root)
        >>> tpl.add_node(dim)
        >>> tpl.count_nodes()
        2
        >>> tpl.get_root().name
        'ЧКД+ ТБ'
    """

    #: Имя показателя сценария
    metric_name: str

    #: Словарь узлов сценария (id -> TemplateLiteNode)
    nodes: Dict[int, TemplateLiteNode] = field(default_factory=dict)

    # --- Управление узлами ---------------------------------------------

    def add_node(self, node: TemplateLiteNode) -> None:
        """
        Добавить узел в сценарий.

        Args:
            node: Узел для добавления

        Raises:
            ValueError: если узел с таким ``id`` уже существует
        """
        if node.id in self.nodes:
            raise ValueError(f"Узел с id={node.id} уже существует в сценарии")
        self.nodes[node.id] = node

    def remove_node(self, node_id: int) -> Optional[TemplateLiteNode]:
        """
        Удалить узел из сценария.

        Args:
            node_id: ID удаляемого узла

        Returns:
            Удалённый узел или ``None``, если узел не найден

        Note:
            Потомки удалённого узла остаются в сценарии, но будут ссылаться
            на несуществующего родителя (подобное выявляется в :meth:`validate`).
        """
        return self.nodes.pop(node_id, None)

    def get_node(self, node_id: int) -> Optional[TemplateLiteNode]:
        """Получить узел по ID или ``None``, если узел не найден."""
        return self.nodes.get(node_id)

    def has_node(self, node_id: int) -> bool:
        """True, если узел с указанным ID присутствует в сценарии."""
        return node_id in self.nodes

    # --- Навигация по дереву -------------------------------------------

    def get_parent(self, node_id: int) -> Optional[TemplateLiteNode]:
        """Получить родительский узел или ``None``."""
        node = self.get_node(node_id)
        if node is None or node.parent is None:
            return None
        return self.get_node(node.parent)

    def get_children(self, node_id: int) -> List[TemplateLiteNode]:
        """
        Получить список прямых потомков узла.

        Returns:
            Список дочерних узлов (в порядке возрастания ``id`` для
            детерминированности). Пустой список, если потомков нет.
        """
        children = [n for n in self.nodes.values() if n.parent == node_id]
        children.sort(key=lambda n: n.id)
        return children

    def get_root(self) -> Optional[TemplateLiteNode]:
        """
        Получить корневой узел сценария.

        Returns:
            Корневой узел (``parent is None``) или ``None``.
            Если корневых узлов несколько, возвращается первый по ``id``.
        """
        roots = self.get_roots()
        return roots[0] if roots else None

    def get_roots(self) -> List[TemplateLiteNode]:
        """Получить все корневые узлы (упорядочены по ``id``)."""
        roots = [n for n in self.nodes.values() if n.is_root()]
        roots.sort(key=lambda n: n.id)
        return roots

    def get_descendants(self, node_id: int) -> List[TemplateLiteNode]:
        """
        Получить всех потомков узла рекурсивно (обход в глубину).

        Returns:
            Список всех потомков (прямых и косвенных).
        """
        result: List[TemplateLiteNode] = []
        for child in self.get_children(node_id):
            result.append(child)
            result.extend(self.get_descendants(child.id))
        return result

    def get_ancestors(self, node_id: int) -> List[TemplateLiteNode]:
        """
        Получить всех предков узла от ближайшего к дальнему.
        """
        node = self.get_node(node_id)
        if node is None:
            return []
        ancestors: List[TemplateLiteNode] = []
        current = node.parent
        while current is not None:
            parent = self.get_node(current)
            if parent is None:
                break
            ancestors.append(parent)
            current = parent.parent
        return ancestors

    def get_path(self, node_id: int) -> List[TemplateLiteNode]:
        """
        Получить путь от корня к узлу (включая сам узел).
        """
        path = list(reversed(self.get_ancestors(node_id)))
        node = self.get_node(node_id)
        if node is not None:
            path.append(node)
        return path

    # --- Фильтрация по ролям -------------------------------------------

    def get_podstatya(self) -> List[TemplateLiteNode]:
        """Все узлы-подстатьи сценария."""
        return self._by_role(NodeRole.PODSTATYA)

    def get_razrez(self) -> List[TemplateLiteNode]:
        """Все узлы-разрезы сценария."""
        return self._by_role(NodeRole.RAZREZ)

    def get_tarif(self) -> List[TemplateLiteNode]:
        """Все узлы-тарифы сценария."""
        return self._by_role(NodeRole.TARIF)

    def get_baza(self) -> List[TemplateLiteNode]:
        """Все узлы-базы сценария."""
        return self._by_role(NodeRole.BAZA)

    def _by_role(self, role: NodeRole) -> List[TemplateLiteNode]:
        result = [n for n in self.nodes.values() if n.role == role]
        result.sort(key=lambda n: n.id)
        return result

    def get_multiplier_nodes(self) -> List[TemplateLiteNode]:
        """
        Получить подстатьи, заданные как мультипликативный показатель
        (имеющие пару потомков «тариф + база»).

        Returns:
            Список подстатей, у которых есть хотя бы один потомок-тариф
            и хотя бы один потомок-база.
        """
        result: List[TemplateLiteNode] = []
        for node in self.nodes.values():
            if not node.is_podstatya():
                continue
            children = self.get_children(node.id)
            roles = {c.role for c in children}
            if NodeRole.TARIF in roles and NodeRole.BAZA in roles:
                result.append(node)
        result.sort(key=lambda n: n.id)
        return result

    # --- Сводная информация --------------------------------------------

    def count_nodes(self) -> int:
        """Количество узлов в сценарии."""
        return len(self.nodes)

    def is_empty(self) -> bool:
        """True, если в сценарии нет ни одного узла."""
        return len(self.nodes) == 0

    # --- Сериализация --------------------------------------------------

    def to_dict(self) -> dict:
        """
        Преобразовать сценарий в словарь, соответствующий исходному JSON.

        Узлы упорядочиваются по ``id`` для детерминированного вывода.
        """
        nodes_sorted = sorted(self.nodes.values(), key=lambda n: n.id)
        return {
            "metricName": self.metric_name,
            "nodes": [n.to_dict() for n in nodes_sorted],
        }

    def to_json(self) -> dict:
        """
        Подготовить сценарий к JSON-сериализации.

        Алиас :meth:`to_dict`, сохранённый для единообразия с другими
        модулями проекта (см. ``libfa2.hier_metadata.Hierarchy.to_json``).
        """
        return self.to_dict()

    def to_json_string(self, *, indent: int = 2) -> str:
        """
        Сериализовать сценарий в JSON-строку.

        Args:
            indent: Отступ для форматирования (по умолчанию 2)
        """
        return json.dumps(self.to_json(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> "TemplateLite":
        """
        Создать сценарий из словаря (десериализованного JSON).

        Args:
            data: Словарь с ключами ``metricName`` и ``nodes``

        Returns:
            Экземпляр TemplateLite

        Raises:
            ValueError: если структура некорректна либо при ошибке
                        десериализации отдельного узла
        """
        if not isinstance(data, dict):
            raise ValueError(f"Ожидался dict, получен {type(data).__name__}")

        if "metricName" not in data:
            raise ValueError("JSON должен содержать поле 'metricName'")
        metric_name = data["metricName"]
        if not isinstance(metric_name, str):
            raise ValueError(
                f"Поле 'metricName' должно быть str, получено {type(metric_name).__name__}"
            )

        if "nodes" not in data:
            raise ValueError("JSON должен содержать поле 'nodes'")
        nodes_data = data["nodes"]
        if not isinstance(nodes_data, list):
            raise ValueError("Поле 'nodes' должно быть списком")

        template = cls(metric_name=metric_name)
        for raw_node in nodes_data:
            try:
                node = TemplateLiteNode.from_dict(raw_node)
            except ValueError as exc:
                raise ValueError(f"Ошибка десериализации узла {raw_node}: {exc}")
            template.add_node(node)
        return template

    @classmethod
    def from_json_string(cls, json_string: str) -> "TemplateLite":
        """
        Десериализовать сценарий из JSON-строки.

        Raises:
            json.JSONDecodeError: при ошибке парсинга JSON
            ValueError: при ошибке структуры данных
        """
        return cls.from_dict(json.loads(json_string))

    # --- Валидация структуры ------------------------------------------

    def validate(self) -> List[str]:
        """
        Проверить корректность структуры сценария.

        Returns:
            Список строк с описанием ошибок. Пустой список — ошибок нет.

        Проверяемые правила:
        - ``metric_name`` не пусто;
        - в сценарии есть хотя бы один узел;
        - ровно один корневой узел (``parent is None``);
        - каждый ``parent`` указывает на существующий узел;
        - корневой узел имеет роль ``podstatya`` (сценарий описывает показатель);
        - отсутствуют циклы в связях ``parent``.
        """
        errors: List[str] = []

        if not self.metric_name:
            errors.append("Поле 'metricName' не должно быть пустым")

        # Валидация отдельных узлов
        for node in self.nodes.values():
            errors.extend(
                f"node id={node.id}: {err}" for err in node.validate()
            )

        if self.is_empty():
            errors.append("Сценарий должен содержать хотя бы один узел")
            return errors

        # Проверка корневых узлов
        roots = self.get_roots()
        if len(roots) == 0:
            errors.append("Сценарий должен иметь ровно один корневой узел, найдено 0")
        elif len(roots) > 1:
            root_ids = ", ".join(str(r.id) for r in roots)
            errors.append(
                f"Сценарий должен иметь ровно один корневой узел, найдено {len(roots)}: "
                f"[{root_ids}]"
            )
        else:
            root = roots[0]
            if not root.is_podstatya():
                errors.append(
                    f"Корневой узел (id={root.id}) должен иметь роль 'podstatya', "
                    f"получено '{root.role.value}'"
                )

        # Проверка существования родительских узлов
        for node in self.nodes.values():
            if node.parent is not None and node.parent not in self.nodes:
                errors.append(
                    f"Узел id={node.id} ({node.name!r}) ссылается на несуществующего "
                    f"родителя (parent={node.parent})"
                )

        # Проверка циклов
        cycle = self._find_cycle()
        if cycle is not None:
            errors.append(
                f"Обнаружен цикл в связях parent: {' -> '.join(str(i) for i in cycle)}"
            )

        return errors

    def is_valid(self) -> bool:
        """True, если сценарий валиден."""
        return len(self.validate()) == 0

    def _find_cycle(self) -> Optional[List[int]]:
        """
        Найти цикл в связях ``parent``. Возвращает цепочку id узлов цикла
        или ``None``, если циклов нет.
        """
        visited: set[int] = set()
        for start in self.nodes:
            if start in visited:
                continue
            path: List[int] = []
            seen_on_path: Dict[int, int] = {}
            current: Optional[int] = start
            while current is not None and current not in visited:
                if current in seen_on_path:
                    # Цикл найден: возвращаем кольцо
                    idx = seen_on_path[current]
                    return path[idx:] + [current]
                seen_on_path[current] = len(path)
                path.append(current)
                node = self.get_node(current)
                current = node.parent if node is not None else None
            visited.update(seen_on_path.keys())
        return None

    # --- Dunder-методы -------------------------------------------------

    def __len__(self) -> int:
        return len(self.nodes)

    def __contains__(self, node_id: int) -> bool:
        return node_id in self.nodes

    def __iter__(self):
        """Итерация по узлам сценария (в порядке возрастания id)."""
        for node in sorted(self.nodes.values(), key=lambda n: n.id):
            yield node

    def __repr__(self) -> str:
        return (
            f"TemplateLite(metric_name={self.metric_name!r}, "
            f"nodes={len(self.nodes)})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TemplateLite):
            return False
        return self.metric_name == other.metric_name and self.nodes == other.nodes
