"""
Unit tests для модуля hier_metadata.

Тесты проверяют функциональность классов:
- Query: параметры запросов к БД
- MetricNode: узлы иерархии
- Hierarchy: управление деревом метрик
- Enums: строковые константы

Тесты включают валидацию, сериализацию/десериализацию,
навигацию по иерархии и проверку целостности.
"""

import json
import pytest

from libfa2.hier_metadata import (
    Hierarchy,
    MetricNode,
    Query,
    MetricType,
    ComponentMultiPartType,
    ComponentRatioPartType,
)
from libfa2.analyt_struct_metadata import (
    AnalyticalStructureMetadata,
    Algorithm,
    Dimension,
)


# =============================================================================
# Tests for Query class
# =============================================================================

class TestQuery:
    """Тесты для класса Query."""

    def test_init_empty(self):
        """Создание пустого Query."""
        query = Query()
        assert query.is_empty()
        assert len(query) == 0

    def test_init_with_dict(self):
        """Создание Query с параметрами."""
        query = Query({"metricType": "interest_income"})
        assert not query.is_empty()
        assert len(query) == 1
        assert query["metricType"] == "interest_income"

    def test_add(self):
        """Добавление параметров."""
        query = Query()
        query.add("metricType", "interest_income")
        query.add("segment", "corporate")
        assert len(query) == 2
        assert query["metricType"] == "interest_income"
        assert query["segment"] == "corporate"

    def test_add_chain(self):
        """Цепочка вызовов add."""
        query = Query()
        result = query.add("metricType", "interest_income").add("segment", "corporate")
        assert result is query  # Возвращает self

    def test_get(self):
        """Получение значения параметра."""
        query = Query({"metricType": "interest_income"})
        assert query.get("metricType") == "interest_income"
        assert query.get("nonexistent", "default") == "default"
        assert query.get("nonexistent") is None

    def test_remove(self):
        """Удаление параметра."""
        query = Query({"metricType": "interest_income", "segment": "corporate"})
        query.remove("segment")
        assert "segment" not in query
        assert len(query) == 1

    def test_remove_nonexistent(self):
        """Удаление несуществующего параметра не вызывает ошибку."""
        query = Query({"metricType": "interest_income"})
        query.remove("nonexistent")
        assert len(query) == 1

    def test_keys_values_items(self):
        """Методы keys(), values(), items()."""
        query = Query({"a": 1, "b": 2})
        assert sorted(query.keys()) == ["a", "b"]
        assert sorted(query.values()) == [1, 2]
        assert sorted(query.items()) == [("a", 1), ("b", 2)]

    def test_to_dict(self):
        """Преобразование в словарь."""
        query = Query({"metricType": "interest_income"})
        d = query.to_dict()
        assert d == {"metricType": "interest_income"}

    def test_to_json_omits_empty(self):
        """to_json() исключает пустые значения."""
        query = Query({
            "metricType": "interest_income",
            "segment": None,
            "status": "",
            "tags": []
        })
        d = query.to_json()
        assert d == {"metricType": "interest_income"}

    def test_from_dict(self):
        """Создание Query из словаря."""
        d = {"metricType": "interest_income", "segment": "corporate"}
        query = Query.from_dict(d)
        assert query["metricType"] == "interest_income"
        assert query["segment"] == "corporate"

    def test_from_dict_empty(self):
        """Создание пустого Query из None."""
        query = Query.from_dict(None)
        assert query.is_empty()

    def test_from_json(self):
        """Создание Query из JSON-словаря."""
        d = {"metricType": "interest_income"}
        query = Query.from_json(d)
        assert query["metricType"] == "interest_income"

    def test_bool(self):
        """Преобразование в bool."""
        assert not Query()
        assert Query({"a": 1})
        assert not Query({})

    def test_equality(self):
        """Проверка равенства."""
        q1 = Query({"a": 1, "b": 2})
        q2 = Query({"a": 1, "b": 2})
        q3 = Query({"a": 1, "b": 3})
        assert q1 == q2
        assert q1 != q3

    def test_hash(self):
        """Проверка хеша для использования в множествах."""
        q1 = Query({"a": 1})
        q2 = Query({"a": 1})
        q3 = Query({"b": 1})
        assert hash(q1) == hash(q2)
        assert hash(q1) != hash(q3)

    def test_repr(self):
        """Строковое представление."""
        query = Query({"a": 1})
        assert repr(query) == "Query({'a': 1})"


# =============================================================================
# Tests for MetricNode class
# =============================================================================

class TestMetricNode:
    """Тесты для класса MetricNode."""

    def test_init_minimal(self):
        """Создание узла с минимальными полями."""
        node = MetricNode(id=100, code="NII", name="ЧПД")
        assert node.id == 100
        assert node.code == "NII"
        assert node.name == "ЧПД"
        assert node.type is None
        assert node.parent is None
        assert node.query is None

    def test_init_with_all_fields(self):
        """Создание узла со всеми полями."""
        query = Query({"metricType": "interest_income"})
        node = MetricNode(
            id=100,
            code="NII",
            name="ЧПД",
            type=MetricType.SUM,
            parent=None,
            query=query,
            componentMultiPartType=None,
            componentRatioPartType=None
        )
        assert node.id == 100
        assert node.type == MetricType.SUM
        assert node.query is not None

    def test_is_root(self):
        """Проверка корневого узла."""
        root = MetricNode(id=100, code="NII", name="ЧПД")
        child = MetricNode(id=101, code="INT_INC", name="Процентный доход", parent=100)
        assert root.is_root()
        assert not child.is_root()

    def test_is_leaf(self):
        """Проверка листового узла."""
        leaf = MetricNode(id=201, code="RATE", name="Ставка", parent=101)
        non_leaf = MetricNode(id=100, code="NII", name="ЧПД", type=MetricType.SUM)
        assert leaf.is_leaf()
        assert not non_leaf.is_leaf()

    def test_has_query(self):
        """Проверка наличия query."""
        node_with_query = MetricNode(
            id=101,
            code="INT_INC",
            name="Процентный доход",
            query=Query({"metricType": "interest_income"})
        )
        node_without_query = MetricNode(id=100, code="NII", name="ЧПД")
        node_with_empty_query = MetricNode(id=102, code="TEST", name="Test", query=Query())

        assert node_with_query.has_query()
        assert not node_without_query.has_query()
        assert not node_with_empty_query.has_query()

    def test_to_dict(self):
        """Преобразование в словарь."""
        node = MetricNode(
            id=100,
            code="NII",
            name="ЧПД",
            type=MetricType.SUM,
            parent=None,
            query=Query({"metricType": "interest_income"})
        )
        d = node.to_dict()
        assert d["id"] == 100
        assert d["code"] == "NII"
        assert d["name"] == "ЧПД"
        assert d["type"] == "sum"
        assert "parent" not in d  # None не включается
        assert d["query"] == {"metricType": "interest_income"}

    def test_to_json(self):
        """Преобразование в JSON-формат."""
        node = MetricNode(
            id=100,
            code="NII",
            name="ЧПД",
            type=MetricType.SUM,
            parent=None
        )
        d = node.to_json()
        assert d["id"] == 100
        assert d["code"] == "NII"
        assert d["name"] == "ЧПД"
        assert d["type"] == "sum"
        assert "parent" not in d  # None не включается
        assert "query" not in d
        assert "componentMultiPartType" not in d
        assert "componentRatioPartType" not in d

    def test_to_json_with_empty_query(self):
        """to_json() исключает пустой query."""
        node = MetricNode(
            id=100,
            code="NII",
            name="ЧПД",
            query=Query()
        )
        d = node.to_json()
        assert "query" not in d

    def test_from_dict(self):
        """Создание узла из словаря."""
        d = {
            "id": 100,
            "code": "NII",
            "name": "Чистый процентный доход",
            "type": "sum",
            "parent": None,
            "query": {"metricType": "interest_income"}
        }
        node = MetricNode.from_dict(d)
        assert node.id == 100
        assert node.code == "NII"
        assert node.type == MetricType.SUM
        assert node.query is not None
        assert node.query["metricType"] == "interest_income"

    def test_from_dict_missing_required_field(self):
        """Ошибка при отсутствии обязательного поля."""
        d = {"code": "NII", "name": "ЧПД"}
        with pytest.raises(ValueError, match="Обязательное поле 'id' отсутствует"):
            MetricNode.from_dict(d)

    def test_from_dict_invalid_type(self):
        """Ошибка при неверном типе обязательного поля."""
        d = {"id": "not_int", "code": "NII", "name": "ЧПД"}
        with pytest.raises(ValueError, match="Поле 'id' должно быть int"):
            MetricNode.from_dict(d)

    def test_from_dict_invalid_metric_type(self):
        """Ошибка при неверном значении type."""
        d = {"id": 100, "code": "NII", "name": "ЧПД", "type": "invalid"}
        with pytest.raises(ValueError, match="Неверное значение 'type'"):
            MetricNode.from_dict(d)

    def test_validate_valid_node(self):
        """Валидация корректного узла."""
        node = MetricNode(
            id=100,
            code="NII",
            name="ЧПД",
            type=MetricType.SUM
        )
        assert node.validate() == []
        assert node.is_valid()

    def test_validate_negative_id(self):
        """Ошибка при отрицательном id."""
        node = MetricNode(id=-1, code="TEST", name="Test")
        errors = node.validate()
        assert len(errors) > 0
        assert any("ID должен быть положительным" in e for e in errors)

    def test_validate_empty_code(self):
        """Ошибка при пустом code."""
        node = MetricNode(id=100, code="", name="Test")
        errors = node.validate()
        assert len(errors) > 0
        assert any("code" in e and "пуст" in e.lower() for e in errors)

    def test_validate_empty_name(self):
        """Ошибка при пустом name."""
        node = MetricNode(id=100, code="TEST", name="")
        errors = node.validate()
        assert len(errors) > 0
        assert any("name" in e and "пуст" in e.lower() for e in errors)

    def test_validate_circular_reference(self):
        """Ошибка при parent == id."""
        node = MetricNode(id=100, code="TEST", name="Test", parent=100)
        errors = node.validate()
        assert len(errors) > 0
        assert any("циклическая" in e.lower() for e in errors)

    def test_validate_leaf_without_query(self):
        """Ошибка при листовом узле без query."""
        node = MetricNode(id=201, code="RATE", name="Ставка", parent=101)
        errors = node.validate()
        assert len(errors) > 0
        assert any("должен иметь query" in e for e in errors)

    def test_validate_multi_without_query(self):
        """Ошибка при узле типа MULTI без query."""
        node = MetricNode(id=101, code="INT_INC", name="Процентный доход", type=MetricType.MULTI)
        errors = node.validate()
        assert len(errors) > 0
        assert any("должен иметь query" in e for e in errors)

    def test_equality(self):
        """Проверка равенства узлов."""
        n1 = MetricNode(id=100, code="NII", name="ЧПД")
        n2 = MetricNode(id=100, code="NII", name="ЧПД")
        n3 = MetricNode(id=101, code="NII", name="ЧПД")
        assert n1 == n2
        assert n1 != n3

    def test_repr(self):
        """Строковое представление."""
        node = MetricNode(id=100, code="NII", name="ЧПД", type=MetricType.SUM)
        r = repr(node)
        assert "id=100" in r
        assert "code='NII'" in r
        assert "type=sum" in r

    def test_init_with_analyt_metadata(self):
        """Создание узла с analyt_metadata."""
        analyt_metadata = AnalyticalStructureMetadata()
        analyt_metadata.add_dimension(Dimension(code="segment", name="Сегмент", column="segment_id"))
        analyt_metadata.add_algorithm(Algorithm(id=1, drill_order=[["segment"]]))

        node = MetricNode(
            id=100,
            code="NII",
            name="ЧПД",
            analyt_metadata=analyt_metadata
        )

        assert node.analyt_metadata is not None
        assert len(node.analyt_metadata.dimensions) == 1
        assert len(node.analyt_metadata.algorithms) == 1

    def test_to_dict_with_analyt_metadata(self):
        """to_dict() включает analyt_metadata."""
        analyt_metadata = AnalyticalStructureMetadata()
        analyt_metadata.add_dimension(Dimension(code="segment", name="Сегмент", column="segment_id"))
        analyt_metadata.add_algorithm(Algorithm(id=1, drill_order=[["segment"]]))

        node = MetricNode(
            id=100,
            code="NII",
            name="ЧПД",
            type=MetricType.SUM,
            analyt_metadata=analyt_metadata
        )

        d = node.to_dict()
        assert "analyt_metadata" in d
        assert "fa_impl" in d["analyt_metadata"]
        assert "dimensions" in d["analyt_metadata"]

    def test_to_dict_without_analyt_metadata(self):
        """to_dict() не включает пустой analyt_metadata."""
        node = MetricNode(id=100, code="NII", name="ЧПД")
        d = node.to_dict()
        assert "analyt_metadata" not in d

    def test_to_json_with_analyt_metadata(self):
        """to_json() включает analyt_metadata."""
        analyt_metadata = AnalyticalStructureMetadata()
        analyt_metadata.add_dimension(Dimension(code="segment", name="Сегмент", column="segment_id"))
        analyt_metadata.add_algorithm(Algorithm(id=1, drill_order=[["segment"]]))

        node = MetricNode(
            id=100,
            code="NII",
            name="ЧПД",
            type=MetricType.SUM,
            analyt_metadata=analyt_metadata
        )

        d = node.to_json()
        assert "analyt_metadata" in d
        assert "fa_impl" in d["analyt_metadata"]

    def test_to_json_without_analyt_metadata(self):
        """to_json() не включает пустой analyt_metadata."""
        node = MetricNode(id=100, code="NII", name="ЧПД")
        d = node.to_json()
        assert "analyt_metadata" not in d

    def test_from_dict_with_analyt_metadata(self):
        """from_dict() создает узел с analyt_metadata."""
        d = {
            "id": 100,
            "code": "NII",
            "name": "ЧПД",
            "type": "sum",
            "analyt_metadata": {
                "fa_impl": [
                    {
                        "id": 1,
                        "drill_order": [["segment"]]
                    }
                ],
                "dimensions": [
                    {
                        "code": "segment",
                        "name": "Сегмент",
                        "column": "segment_id"
                    }
                ]
            }
        }

        node = MetricNode.from_dict(d)
        assert node.analyt_metadata is not None
        assert len(node.analyt_metadata.dimensions) == 1
        assert len(node.analyt_metadata.algorithms) == 1

    def test_from_dict_without_analyt_metadata(self):
        """from_dict() создает узел без analyt_metadata."""
        d = {
            "id": 100,
            "code": "NII",
            "name": "ЧПД",
            "type": "sum"
        }

        node = MetricNode.from_dict(d)
        assert node.analyt_metadata is None

    def test_equality_with_analyt_metadata(self):
        """Равенство узлов с analyt_metadata."""
        analyt_metadata = AnalyticalStructureMetadata()
        analyt_metadata.add_dimension(Dimension(code="segment", name="Сегмент", column="segment_id"))

        n1 = MetricNode(id=100, code="NII", name="ЧПД", analyt_metadata=analyt_metadata)
        n2 = MetricNode(id=100, code="NII", name="ЧПД", analyt_metadata=analyt_metadata)
        n3 = MetricNode(id=100, code="NII", name="ЧПД")

        assert n1 == n2
        assert n1 != n3

    def test_hash_with_analyt_metadata(self):
        """Хеш узлов с одинаковым analyt_metadata."""
        analyt_metadata = AnalyticalStructureMetadata()
        analyt_metadata.add_dimension(Dimension(code="segment", name="Сегмент", column="segment_id"))

        n1 = MetricNode(id=100, code="NII", name="ЧПД", analyt_metadata=analyt_metadata)
        n2 = MetricNode(id=100, code="NII", name="ЧПД", analyt_metadata=analyt_metadata)

        assert hash(n1) == hash(n2)


# =============================================================================
# Tests for Hierarchy class
# =============================================================================

class TestHierarchy:
    """Тесты для класса Hierarchy."""

    def test_init_empty(self):
        """Создание пустой иерархии."""
        hierarchy = Hierarchy()
        assert hierarchy.is_empty()
        assert hierarchy.count_nodes() == 0

    def test_add_node(self):
        """Добавление узла."""
        hierarchy = Hierarchy()
        node = MetricNode(id=100, code="NII", name="ЧПД")
        hierarchy.add_node(node)
        assert hierarchy.count_nodes() == 1
        assert hierarchy.has_node(100)

    def test_add_duplicate_node(self):
        """Ошибка при добавлении дубликата узла."""
        hierarchy = Hierarchy()
        node = MetricNode(id=100, code="NII", name="ЧПД")
        hierarchy.add_node(node)
        with pytest.raises(ValueError, match="уже существует"):
            hierarchy.add_node(node)

    def test_remove_node(self):
        """Удаление узла."""
        hierarchy = Hierarchy()
        node = MetricNode(id=100, code="NII", name="ЧПД")
        hierarchy.add_node(node)
        removed = hierarchy.remove_node(100)
        assert removed == node
        assert hierarchy.is_empty()

    def test_remove_nonexistent_node(self):
        """Удаление несуществующего узла."""
        hierarchy = Hierarchy()
        assert hierarchy.remove_node(999) is None

    def test_get_node(self):
        """Получение узла по ID."""
        hierarchy = Hierarchy()
        node = MetricNode(id=100, code="NII", name="ЧПД")
        hierarchy.add_node(node)
        assert hierarchy.get_node(100) == node
        assert hierarchy.get_node(999) is None

    def test_get_parent(self):
        """Получение родительского узла."""
        hierarchy = Hierarchy()
        root = MetricNode(id=100, code="NII", name="ЧПД")
        child = MetricNode(id=101, code="INT_INC", name="Процентный доход", parent=100)
        hierarchy.add_node(root)
        hierarchy.add_node(child)
        assert hierarchy.get_parent(101) == root
        assert hierarchy.get_parent(100) is None

    def test_get_children(self):
        """Получение потомков."""
        hierarchy = Hierarchy()
        root = MetricNode(id=100, code="NII", name="ЧПД")
        child1 = MetricNode(id=101, code="INT_INC", name="Процентный доход", parent=100)
        child2 = MetricNode(id=102, code="INT_EXP", name="Процентный расход", parent=100)
        hierarchy.add_node(root)
        hierarchy.add_node(child1)
        hierarchy.add_node(child2)

        children = hierarchy.get_children(100)
        assert len(children) == 2
        assert child1 in children
        assert child2 in children

    def test_get_root(self):
        """Получение корневого узла."""
        hierarchy = Hierarchy()
        root = MetricNode(id=100, code="NII", name="ЧПД")
        child = MetricNode(id=101, code="INT_INC", name="Процентный доход", parent=100)
        hierarchy.add_node(root)
        hierarchy.add_node(child)
        assert hierarchy.get_root() == root

    def test_get_root_empty(self):
        """Корень пустой иерархии."""
        hierarchy = Hierarchy()
        assert hierarchy.get_root() is None

    def test_get_roots_multiple(self):
        """Несколько корней (невалидно, но метод работает)."""
        hierarchy = Hierarchy()
        root1 = MetricNode(id=100, code="NII", name="ЧПД")
        root2 = MetricNode(id=200, code="NII2", name="ЧПД2")
        hierarchy.add_node(root1)
        hierarchy.add_node(root2)
        assert len(hierarchy.get_roots()) == 2

    def test_get_leaves(self):
        """Получение листовых узлов."""
        hierarchy = Hierarchy()
        root = MetricNode(id=100, code="NII", name="ЧПД", type=MetricType.SUM)
        child1 = MetricNode(id=101, code="INT_INC", name="Процентный доход", type=MetricType.MULTI, parent=100)
        leaf1 = MetricNode(id=201, code="RATE", name="Ставка", parent=101,
                          componentMultiPartType=ComponentMultiPartType.RATE,
                          query=Query({"a": 1}))
        leaf2 = MetricNode(id=202, code="BASE", name="Объем", parent=101,
                          componentMultiPartType=ComponentMultiPartType.BASE,
                          query=Query({"a": 1}))
        hierarchy.add_node(root)
        hierarchy.add_node(child1)
        hierarchy.add_node(leaf1)
        hierarchy.add_node(leaf2)

        leaves = hierarchy.get_leaves()
        assert len(leaves) == 2
        assert leaf1 in leaves
        assert leaf2 in leaves

    def test_get_descendants(self):
        """Получение всех потомков."""
        hierarchy = Hierarchy()
        root = MetricNode(id=100, code="NII", name="ЧПД", type=MetricType.SUM)
        child = MetricNode(id=101, code="INT_INC", name="Процентный доход", type=MetricType.MULTI, parent=100)
        leaf1 = MetricNode(id=201, code="RATE", name="Ставка", parent=101,
                          componentMultiPartType=ComponentMultiPartType.RATE,
                          query=Query({"a": 1}))
        leaf2 = MetricNode(id=202, code="BASE", name="Объем", parent=101,
                          componentMultiPartType=ComponentMultiPartType.BASE,
                          query=Query({"a": 1}))
        hierarchy.add_node(root)
        hierarchy.add_node(child)
        hierarchy.add_node(leaf1)
        hierarchy.add_node(leaf2)

        descendants = hierarchy.get_descendants(100)
        assert len(descendants) == 3
        assert child in descendants
        assert leaf1 in descendants
        assert leaf2 in descendants

    def test_get_ancestors(self):
        """Получение предков."""
        hierarchy = Hierarchy()
        root = MetricNode(id=100, code="NII", name="ЧПД", type=MetricType.SUM)
        child = MetricNode(id=101, code="INT_INC", name="Процентный доход", type=MetricType.MULTI, parent=100)
        leaf = MetricNode(id=201, code="RATE", name="Ставка", parent=101,
                         componentMultiPartType=ComponentMultiPartType.RATE,
                         query=Query({"a": 1}))
        hierarchy.add_node(root)
        hierarchy.add_node(child)
        hierarchy.add_node(leaf)

        ancestors = hierarchy.get_ancestors(201)
        assert len(ancestors) == 2
        assert child in ancestors
        assert root in ancestors

    def test_get_path(self):
        """Получение пути от корня к узлу."""
        hierarchy = Hierarchy()
        root = MetricNode(id=100, code="NII", name="ЧПД", type=MetricType.SUM)
        child = MetricNode(id=101, code="INT_INC", name="Процентный доход", type=MetricType.MULTI, parent=100)
        leaf = MetricNode(id=201, code="RATE", name="Ставка", parent=101,
                         componentMultiPartType=ComponentMultiPartType.RATE,
                         query=Query({"a": 1}))
        hierarchy.add_node(root)
        hierarchy.add_node(child)
        hierarchy.add_node(leaf)

        path = hierarchy.get_path(201)
        assert len(path) == 3
        assert path[0] == root
        assert path[1] == child
        assert path[2] == leaf

    def test_clear(self):
        """Очистка иерархии."""
        hierarchy = Hierarchy()
        hierarchy.add_node(MetricNode(id=100, code="NII", name="ЧПД"))
        hierarchy.add_node(MetricNode(id=101, code="INT_INC", name="Процентный доход", parent=100))
        hierarchy.clear()
        assert hierarchy.is_empty()

    def test_to_dict_list(self):
        """Преобразование в список словарей."""
        hierarchy = Hierarchy()
        node = MetricNode(id=100, code="NII", name="ЧПД", type=MetricType.SUM)
        hierarchy.add_node(node)
        dict_list = hierarchy.to_dict_list()
        assert len(dict_list) == 1
        assert dict_list[0]["id"] == 100

    def test_to_json(self):
        """Преобразование в JSON-формат."""
        hierarchy = Hierarchy()
        node = MetricNode(id=100, code="NII", name="ЧПД", type=MetricType.SUM)
        hierarchy.add_node(node)
        json_dict = hierarchy.to_json()
        assert "nodes" in json_dict
        assert len(json_dict["nodes"]) == 1
        assert json_dict["nodes"][0]["id"] == 100

    def test_to_json_string(self):
        """Сериализация в JSON-строку."""
        hierarchy = Hierarchy()
        node = MetricNode(id=100, code="NII", name="ЧПД", type=MetricType.SUM)
        hierarchy.add_node(node)
        json_str = hierarchy.to_json_string()
        data = json.loads(json_str)
        assert "nodes" in data
        assert len(data["nodes"]) == 1

    def test_from_dict_list(self):
        """Создание иерархии из списка словарей."""
        data = [
            {"id": 100, "code": "NII", "name": "ЧПД", "type": "sum"},
            {"id": 101, "code": "INT_INC", "name": "Процентный доход", "type": "multi", "parent": 100}
        ]
        hierarchy = Hierarchy.from_dict_list(data)
        assert hierarchy.count_nodes() == 2
        assert hierarchy.get_node(100).type == MetricType.SUM

    def test_from_json(self):
        """Создание иерархии из JSON-словаря."""
        data = {
            "nodes": [
                {"id": 100, "code": "NII", "name": "ЧПД", "type": "sum"},
                {"id": 101, "code": "INT_INC", "name": "Процентный доход", "type": "multi", "parent": 100}
            ]
        }
        hierarchy = Hierarchy.from_json(data)
        assert hierarchy.count_nodes() == 2

    def test_from_json_string(self):
        """Десериализация из JSON-строки."""
        json_str = '{"nodes": [{"id": 100, "code": "NII", "name": "ЧПД", "type": "sum"}]}'
        hierarchy = Hierarchy.from_json_string(json_str)
        assert hierarchy.count_nodes() == 1

    def test_from_json_missing_nodes_field(self):
        """Ошибка при отсутствии поля 'nodes'."""
        data = {"items": [{"id": 100}]}
        with pytest.raises(ValueError, match="должен содержать поле 'nodes'"):
            Hierarchy.from_json(data)

    def test_validate_valid_hierarchy(self):
        """Валидация корректной иерархии."""
        hierarchy = self._create_valid_nii_hierarchy()
        assert hierarchy.validate() == []
        assert hierarchy.is_valid()

    def test_validate_no_root(self):
        """Ошибка при отсутствии корня."""
        hierarchy = Hierarchy()
        hierarchy.add_node(MetricNode(id=101, code="INT_INC", name="Процентный доход", parent=100))
        errors = hierarchy.validate()
        assert any("должна иметь ровно один корневой узел" in e for e in errors)

    def test_validate_multiple_roots(self):
        """Ошибка при нескольких корнях."""
        hierarchy = Hierarchy()
        hierarchy.add_node(MetricNode(id=100, code="NII", name="ЧПД"))
        hierarchy.add_node(MetricNode(id=200, code="NII2", name="ЧПД2"))
        errors = hierarchy.validate()
        assert any("должна иметь ровно один корневой узел" in e for e in errors)

    def test_validate_orphan_node(self):
        """Ошибка при узле с несуществующим родителем."""
        hierarchy = Hierarchy()
        hierarchy.add_node(MetricNode(id=100, code="NII", name="ЧПД"))
        hierarchy.add_node(MetricNode(id=102, code="INT_EXP", name="Процентный расход", parent=999))
        errors = hierarchy.validate()
        assert any("ссылается на несуществующий родитель" in e for e in errors)

    def test_validate_multi_missing_rate(self):
        """Ошибка при отсутствии потомка rate для MULTI."""
        hierarchy = Hierarchy()
        root = MetricNode(id=100, code="NII", name="ЧПД", type=MetricType.SUM)
        multi = MetricNode(id=101, code="INT_INC", name="Процентный доход", type=MetricType.MULTI, parent=100,
                         query=Query({"a": 1}))
        base = MetricNode(id=202, code="BASE", name="Объем", parent=101,
                         componentMultiPartType=ComponentMultiPartType.BASE,
                         query=Query({"a": 1}))
        hierarchy.add_node(root)
        hierarchy.add_node(multi)
        hierarchy.add_node(base)

        errors = hierarchy.validate()
        assert any("должен иметь ровно одного потомка с componentMultiPartType=rate" in e for e in errors)

    def test_validate_multi_missing_base(self):
        """Ошибка при отсутствии потомка base для MULTI."""
        hierarchy = Hierarchy()
        root = MetricNode(id=100, code="NII", name="ЧПД", type=MetricType.SUM)
        multi = MetricNode(id=101, code="INT_INC", name="Процентный доход", type=MetricType.MULTI, parent=100,
                         query=Query({"a": 1}))
        rate = MetricNode(id=201, code="RATE", name="Ставка", parent=101,
                         componentMultiPartType=ComponentMultiPartType.RATE,
                         query=Query({"a": 1}))
        hierarchy.add_node(root)
        hierarchy.add_node(multi)
        hierarchy.add_node(rate)

        errors = hierarchy.validate()
        assert any("должен иметь ровно одного потомка с componentMultiPartType=base" in e for e in errors)

    def test_validate_ratio_missing_parts(self):
        """Ошибка при отсутствии потомков для RATIO."""
        hierarchy = Hierarchy()
        ratio = MetricNode(id=300, code="COR", name="Cost of Risk", type=MetricType.RATIO)
        hierarchy.add_node(ratio)

        errors = hierarchy.validate()
        assert any("должен иметь ровно одного потомка с componentRatioPartType=numerator" in e for e in errors)
        assert any("должен иметь ровно одного потомка с componentRatioPartType=denominator" in e for e in errors)

    def test_validate_leaf_with_children(self):
        """Ошибка при листовом узле с потомками."""
        hierarchy = Hierarchy()
        leaf = MetricNode(id=201, code="RATE", name="Ставка", query=Query({"a": 1}))
        child = MetricNode(id=301, code="SUB_RATE", name="Подставка", parent=201, query=Query({"a": 1}))
        hierarchy.add_node(leaf)
        hierarchy.add_node(child)

        errors = hierarchy.validate()
        assert any("не может иметь потомков" in e for e in errors)

    def test_iterate(self):
        """Итерация по узлам."""
        hierarchy = Hierarchy()
        hierarchy.add_node(MetricNode(id=100, code="NII", name="ЧПД"))
        hierarchy.add_node(MetricNode(id=101, code="INT_INC", name="Процентный доход", parent=100))

        nodes = list(hierarchy)
        assert len(nodes) == 2

    def test_contains(self):
        """Проверка наличия узла через оператор in."""
        hierarchy = Hierarchy()
        hierarchy.add_node(MetricNode(id=100, code="NII", name="ЧПД"))
        assert 100 in hierarchy
        assert 200 not in hierarchy

    def test_len(self):
        """Получение количества узлов через len()."""
        hierarchy = Hierarchy()
        assert len(hierarchy) == 0
        hierarchy.add_node(MetricNode(id=100, code="NII", name="ЧПД"))
        assert len(hierarchy) == 1

    def test_visualize(self):
        """Визуализация иерархии."""
        hierarchy = self._create_valid_nii_hierarchy()
        viz = hierarchy.visualize()
        assert "NII" in viz
        assert "INT_INC" in viz
        assert "INT_EXP" in viz

    # =============================================================================
    # Helper methods
    # =============================================================================

    def _create_valid_nii_hierarchy(self) -> Hierarchy:
        """
        Создать валидную иерархию ЧПД для тестов.

        Структура:
        NII (sum)
        ├── INT_INC (multi)
        │   ├── RATE (rate)
        │   └── BASE (base)
        └── INT_EXP (multi)
            ├── RATE (rate)
            └── BASE (base)
        """
        hierarchy = Hierarchy()

        # Корень
        root = MetricNode(id=100, code="NII", name="Чистый процентный доход", type=MetricType.SUM)
        hierarchy.add_node(root)

        # Процентный доход (MULTI)
        int_inc = MetricNode(
            id=101,
            code="INT_INC",
            name="Процентный доход",
            type=MetricType.MULTI,
            parent=100,
            query=Query({"metricType": "interest_income"})
        )
        hierarchy.add_node(int_inc)

        # Ставка процентного дохода (rate)
        int_inc_rate = MetricNode(
            id=201,
            code="INT_INC_RATE",
            name="Ставка процентного дохода",
            parent=101,
            componentMultiPartType=ComponentMultiPartType.RATE,
            query=Query({"metricType": "interest_income", "component": "rate"})
        )
        hierarchy.add_node(int_inc_rate)

        # Объем требований по долговым фин. инструментам (base)
        int_inc_base = MetricNode(
            id=202,
            code="INT_INC_BASE",
            name="Объем требований по долговым фин. инструментам",
            parent=101,
            componentMultiPartType=ComponentMultiPartType.BASE,
            query=Query({"metricType": "interest_income", "component": "base"})
        )
        hierarchy.add_node(int_inc_base)

        # Процентный расход (MULTI)
        int_exp = MetricNode(
            id=102,
            code="INT_EXP",
            name="Процентный расход",
            type=MetricType.MULTI,
            parent=100,
            query=Query({"metricType": "interest_expense"})
        )
        hierarchy.add_node(int_exp)

        # Ставка процентного расхода (rate)
        int_exp_rate = MetricNode(
            id=301,
            code="INT_EXP_RATE",
            name="Ставка процентного расхода",
            parent=102,
            componentMultiPartType=ComponentMultiPartType.RATE,
            query=Query({"metricType": "interest_expense", "component": "rate"})
        )
        hierarchy.add_node(int_exp_rate)

        # Объем обязательств по долговым фин. инструментам (base)
        int_exp_base = MetricNode(
            id=302,
            code="INT_EXP_BASE",
            name="Объем обязательств по долговым фин. инструментам",
            parent=102,
            componentMultiPartType=ComponentMultiPartType.BASE,
            query=Query({"metricType": "interest_expense", "component": "base"})
        )
        hierarchy.add_node(int_exp_base)

        return hierarchy


# =============================================================================
# Tests for full serialization/deserialization cycle
# =============================================================================

class TestSerializationCycle:
    """Тесты полного цикла сериализации/десериализации."""

    def test_nii_hierarchy_serialization(self):
        """Полный цикл сериализации/десериализации для иерархии ЧПД."""
        # Создаем иерархию
        test_hierarchy = TestHierarchy()._create_valid_nii_hierarchy()

        # Сериализация
        json_str = test_hierarchy.to_json_string()

        # Десериализация
        restored = Hierarchy.from_json_string(json_str)

        # Проверка
        assert test_hierarchy.count_nodes() == restored.count_nodes()

        # Проверяем каждый узел
        for original_node in test_hierarchy:
            restored_node = restored.get_node(original_node.id)
            assert restored_node is not None
            assert restored_node.id == original_node.id
            assert restored_node.code == original_node.code
            assert restored_node.name == original_node.name
            assert restored_node.type == original_node.type
            assert restored_node.parent == original_node.parent

            # Проверка query
            if original_node.query is not None:
                assert restored_node.query is not None
                assert restored_node.query.to_dict() == original_node.query.to_dict()
            else:
                assert restored_node.query is None

        # Проверка валидности восстановленной иерархии
        assert restored.is_valid()

    def test_ratio_hierarchy_serialization(self):
        """Полный цикл сериализации/десериализации для иерархии COR (ratio)."""
        hierarchy = self._create_valid_cor_hierarchy()

        # Сериализация
        json_str = hierarchy.to_json_string()

        # Десериализация
        restored = Hierarchy.from_json_string(json_str)

        # Проверка
        assert hierarchy.count_nodes() == restored.count_nodes()
        assert restored.is_valid()

        # Проверяем структуру
        root = restored.get_root()
        assert root.code == "COR"
        assert root.type == MetricType.RATIO

        children = restored.get_children(root.id)
        assert len(children) == 2
        assert any(c.componentRatioPartType == ComponentRatioPartType.NUMERATOR for c in children)
        assert any(c.componentRatioPartType == ComponentRatioPartType.DENOMINATOR for c in children)

    def test_json_with_omitted_fields(self):
        """JSON с опущенными пустыми полями."""
        hierarchy = Hierarchy()
        node = MetricNode(
            id=100,
            code="NII",
            name="ЧПД",
            type=MetricType.SUM
        )
        hierarchy.add_node(node)

        json_str = hierarchy.to_json_string(include_empty_fields=False)
        data = json.loads(json_str)

        # Проверяем что parent, query не включены (они None)
        assert "parent" not in data["nodes"][0]
        assert "query" not in data["nodes"][0]

        # Но при этом основные поля есть
        assert data["nodes"][0]["id"] == 100
        assert data["nodes"][0]["code"] == "NII"
        assert data["nodes"][0]["type"] == "sum"

    def test_roundtrip_preserves_all_data(self):
        """Полный цикл сохраняет все данные."""
        test_hierarchy = TestHierarchy()._create_valid_nii_hierarchy()

        json_str = test_hierarchy.to_json_string()
        restored = Hierarchy.from_json_string(json_str)

        # Проверяем что структура идентична
        for node in test_hierarchy:
            restored_node = restored.get_node(node.id)
            assert restored_node == node, f"Node {node.id} not equal after roundtrip"

        # Проверка визуализации
        assert test_hierarchy.visualize() == restored.visualize()

    def _create_valid_cor_hierarchy(self) -> Hierarchy:
        """
        Создать валидную иерархию COR (ratio) для тестов.

        Структура:
        COR (ratio)
        ├── RES_EXP (numerator)
        │   ├── LOAN_RES
        │   │   ├── CORP_RES
        │   │   ├── RETAIL_RES
        │   │   └── SMB_RES
        │   └── OTHER_RES
        └── WA_AVG_ASSETS (denominator)
            ├── LOAN_PORTFOLIO
            │   ├── CORP_LOANS
            │   ├── RETAIL_LOANS
            │   └── SMB_LOANS
            └── OTHER_WORKING_ASSETS
        """
        hierarchy = Hierarchy()

        # Корень COR
        cor = MetricNode(id=300, code="COR", name="Cost of Risk", type=MetricType.RATIO)
        hierarchy.add_node(cor)

        # Числитель: Расходы на резервы
        res_exp = MetricNode(
            id=301,
            code="RES_EXP",
            name="Расходы на резервы",
            type=MetricType.SUM,
            parent=300,
            componentRatioPartType=ComponentRatioPartType.NUMERATOR
        )
        hierarchy.add_node(res_exp)

        # Результаты от резервов по кредитам
        loan_res = MetricNode(
            id=30101,
            code="LOAN_RES",
            name="Результаты от резервов по кредитам",
            type=MetricType.SUM,
            parent=301
        )
        hierarchy.add_node(loan_res)

        # Резервы по корпоративным кредитам
        corp_res = MetricNode(
            id=3010101,
            code="CORP_RES",
            name="Резервы по корпоративным кредитам",
            parent=30101,
            query=Query({"metricType": "loan_reserves", "segment": "corporate"})
        )
        hierarchy.add_node(corp_res)

        # Резервы по розничным кредитам
        retail_res = MetricNode(
            id=3010102,
            code="RETAIL_RES",
            name="Резервы по розничным кредитам",
            parent=30101,
            query=Query({"metricType": "loan_reserves", "segment": "retail"})
        )
        hierarchy.add_node(retail_res)

        # Резервы по кредитам МСБ
        smb_res = MetricNode(
            id=3010103,
            code="SMB_RES",
            name="Резервы по кредитам МСБ",
            parent=30101,
            query=Query({"metricType": "loan_reserves", "segment": "smb"})
        )
        hierarchy.add_node(smb_res)

        # Резервы по прочим активам
        other_res = MetricNode(
            id=30102,
            code="OTHER_RES",
            name="Резервы по прочим активам",
            parent=301,
            query=Query({"metricType": "other_reserves"})
        )
        hierarchy.add_node(other_res)

        # Знаменатель: Среднехронологические работающие активы
        wa_avg_assets = MetricNode(
            id=302,
            code="WA_AVG_ASSETS",
            name="Среднехронологические работающие активы",
            type=MetricType.SUM,
            parent=300,
            componentRatioPartType=ComponentRatioPartType.DENOMINATOR
        )
        hierarchy.add_node(wa_avg_assets)

        # Кредитный портфель
        loan_portfolio = MetricNode(
            id=30201,
            code="LOAN_PORTFOLIO",
            name="Кредитный портфель",
            type=MetricType.SUM,
            parent=302
        )
        hierarchy.add_node(loan_portfolio)

        # Корпоративные кредиты
        corp_loans = MetricNode(
            id=3020101,
            code="CORP_LOANS",
            name="Корпоративные кредиты",
            parent=30201,
            query=Query({"metricType": "wa_avg_assets", "segment": "corporate"})
        )
        hierarchy.add_node(corp_loans)

        # Розничные кредиты
        retail_loans = MetricNode(
            id=3020102,
            code="RETAIL_LOANS",
            name="Розничные кредиты",
            parent=30201,
            query=Query({"metricType": "wa_avg_assets", "segment": "retail"})
        )
        hierarchy.add_node(retail_loans)

        # Кредиты МСБ
        smb_loans = MetricNode(
            id=3020103,
            code="SMB_LOANS",
            name="Кредиты МСБ",
            parent=30201,
            query=Query({"metricType": "wa_avg_assets", "segment": "smb"})
        )
        hierarchy.add_node(smb_loans)

        # Прочие работающие активы
        other_working_assets = MetricNode(
            id=30202,
            code="OTHER_WORKING_ASSETS",
            name="Прочие работающие активы",
            parent=302,
            query=Query({"metricType": "other_working_assets"})
        )
        hierarchy.add_node(other_working_assets)

        return hierarchy


# =============================================================================
# Tests for Enums
# =============================================================================

class TestEnums:
    """Тесты для Enum классов."""

    def test_metric_type_values(self):
        """Значения MetricType."""
        assert MetricType.SUM.value == "sum"
        assert MetricType.MULTI.value == "multi"
        assert MetricType.RATIO.value == "ratio"

    def test_metric_type_from_string(self):
        """Создание MetricType из строки."""
        assert MetricType("sum") == MetricType.SUM
        assert MetricType("multi") == MetricType.MULTI
        assert MetricType("ratio") == MetricType.RATIO

    def test_metric_type_invalid_string(self):
        """Ошибка при неверной строке."""
        with pytest.raises(ValueError):
            MetricType("invalid")

    def test_component_multi_part_type_values(self):
        """Значения ComponentMultiPartType."""
        assert ComponentMultiPartType.RATE.value == "rate"
        assert ComponentMultiPartType.BASE.value == "base"

    def test_component_ratio_part_type_values(self):
        """Значения ComponentRatioPartType."""
        assert ComponentRatioPartType.NUMERATOR.value == "numerator"
        assert ComponentRatioPartType.DENOMINATOR.value == "denominator"

    def test_enums_are_strings(self):
        """Enum классы наследуются от str."""
        assert isinstance(MetricType.SUM, str)
        assert isinstance(ComponentMultiPartType.RATE, str)
        assert isinstance(ComponentRatioPartType.NUMERATOR, str)
