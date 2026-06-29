"""Тесты класса TemplateLiteNode."""

import pytest

from adhoc.template_lite import NodeRole, TemplateLiteNode


class TestNodeCreation:
    """Создание и поля узла."""

    def test_create_root_podstatya(self):
        node = TemplateLiteNode(id=1, name="Корень", role=NodeRole.PODSTATYA)
        assert node.id == 1
        assert node.name == "Корень"
        assert node.role is NodeRole.PODSTATYA
        assert node.parent is None
        assert node.is_root()

    def test_create_child_with_parent(self):
        node = TemplateLiteNode(id=2, name="Маржа", role=NodeRole.TARIF, parent=1)
        assert node.parent == 1
        assert not node.is_root()


class TestNodeRoleChecks:
    """Методы-классификаторы роли."""

    @pytest.mark.parametrize(
        "role,checker",
        [
            (NodeRole.PODSTATYA, "is_podstatya"),
            (NodeRole.RAZREZ, "is_razrez"),
            (NodeRole.TARIF, "is_tarif"),
            (NodeRole.BAZA, "is_baza"),
        ],
    )
    def test_role_checker_true(self, role, checker):
        node = TemplateLiteNode(id=1, name="x", role=role)
        assert getattr(node, checker)()

    def test_role_checkers_mutually_exclusive(self):
        node = TemplateLiteNode(id=1, name="x", role=NodeRole.TARIF)
        assert node.is_tarif()
        assert not node.is_baza()
        assert not node.is_podstatya()
        assert not node.is_razrez()


class TestNodeSerialization:
    """Сериализация/десериализация узла."""

    def test_to_dict_root(self):
        node = TemplateLiteNode(id=1, name="Корень", role=NodeRole.PODSTATYA)
        assert node.to_dict() == {
            "id": 1,
            "name": "Корень",
            "role": "podstatya",
            "parent": None,
        }

    def test_to_dict_child(self):
        node = TemplateLiteNode(id=4, name="Маржа", role=NodeRole.TARIF, parent=3)
        assert node.to_dict() == {
            "id": 4,
            "name": "Маржа",
            "role": "tarif",
            "parent": 3,
        }

    @pytest.mark.parametrize("role_value", ["podstatya", "razrez", "tarif", "baza"])
    def test_from_dict_roundtrip(self, role_value):
        data = {"id": 7, "name": "Узел", "role": role_value, "parent": 2}
        node = TemplateLiteNode.from_dict(data)
        assert node.to_dict() == data

    def test_from_dict_parent_null(self):
        data = {"id": 1, "name": "Корень", "role": "podstatya", "parent": None}
        node = TemplateLiteNode.from_dict(data)
        assert node.parent is None

    def test_from_dict_parent_missing_defaults_none(self):
        data = {"id": 1, "name": "Корень", "role": "podstatya"}
        node = TemplateLiteNode.from_dict(data)
        assert node.parent is None


class TestNodeCodes:
    """Поле codes (составные коды "<type_code>#<node_code>" из upr_cube_codes)."""

    def test_codes_default_empty(self):
        """По умолчанию codes — пустой список."""
        node = TemplateLiteNode(id=1, name="x", role=NodeRole.PODSTATYA)
        assert node.codes == []

    def test_codes_can_be_set(self):
        """codes задаётся явно при создании."""
        node = TemplateLiteNode(
            id=1, name="x", role=NodeRole.PODSTATYA, codes=["PL#R_01_02", "PL#R_01_03"]
        )
        assert node.codes == ["PL#R_01_02", "PL#R_01_03"]

    def test_from_dict_builds_combined_codes(self):
        """from_dict строит "<type_code>#<node_code>" из каждого элемента
        upr_cube_codes (fin_code отбрасывается)."""
        data = {
            "id": 5,
            "name": "Кредиты банкам",
            "role": "podstatya",
            "parent": 4,
            "upr_cube_codes": [
                {"type_code": "PL", "fin_code": "A.01.02", "node_code": "R_01_02"},
                {"type_code": "PL", "fin_code": "A.01.99", "node_code": "R_01_99"},
            ],
        }
        node = TemplateLiteNode.from_dict(data)
        assert node.codes == ["PL#R_01_02", "PL#R_01_99"]

    def test_from_dict_without_upr_cube_codes_defaults_empty(self):
        """Нет upr_cube_codes -> codes пустой."""
        data = {"id": 5, "name": "x", "role": "podstatya", "parent": 4}
        node = TemplateLiteNode.from_dict(data)
        assert node.codes == []

    def test_from_dict_empty_upr_cube_codes(self):
        """Пустой список upr_cube_codes -> codes пустой."""
        data = {
            "id": 5, "name": "x", "role": "podstatya", "parent": 4,
            "upr_cube_codes": [],
        }
        node = TemplateLiteNode.from_dict(data)
        assert node.codes == []

    def test_from_dict_single_element(self):
        """Одиночный элемент upr_cube_codes -> один составной код."""
        data = {
            "id": 5, "name": "x", "role": "podstatya", "parent": 4,
            "upr_cube_codes": [
                {"type_code": "BS", "fin_code": "B.01.06", "node_code": "R_01_05_01"},
            ],
        }
        node = TemplateLiteNode.from_dict(data)
        assert node.codes == ["BS#R_01_05_01"]

    def test_from_dict_skips_elements_without_node_code(self):
        """Элементы без node_code пропускаются (не ломают разбор). Элементы без
        type_code попадают в codes как простой node_code (без префикса)."""
        data = {
            "id": 5, "name": "x", "role": "podstatya", "parent": 4,
            "upr_cube_codes": [
                {"type_code": "PL", "fin_code": "A.01.02", "node_code": "R_01_02"},
                {"type_code": "PL", "fin_code": "A.01.99"},  # без node_code
                {"node_code": "R_02"},  # только node_code (без type_code)
            ],
        }
        node = TemplateLiteNode.from_dict(data)
        assert node.codes == ["PL#R_01_02", "R_02"]

    def test_from_dict_upr_cube_codes_not_list_raises(self):
        """upr_cube_codes не списком -> ValueError."""
        data = {
            "id": 5, "name": "x", "role": "podstatya", "parent": 4,
            "upr_cube_codes": "R_01_02",
        }
        with pytest.raises(ValueError, match="upr_cube_codes"):
            TemplateLiteNode.from_dict(data)

    def test_to_dict_omits_upr_cube_codes_when_empty(self):
        """to_dict не включает upr_cube_codes при пустом codes."""
        node = TemplateLiteNode(id=1, name="x", role=NodeRole.PODSTATYA)
        assert "upr_cube_codes" not in node.to_dict()

    def test_to_dict_splits_combined_codes_into_type_and_node(self):
        """to_dict разбирает составные коды обратно в {type_code, node_code}."""
        node = TemplateLiteNode(
            id=1, name="x", role=NodeRole.PODSTATYA,
            codes=["PL#R_01_02", "BS#R_01_99"],
        )
        d = node.to_dict()
        assert d["upr_cube_codes"] == [
            {"type_code": "PL", "node_code": "R_01_02"},
            {"type_code": "BS", "node_code": "R_01_99"},
        ]

    def test_to_dict_plain_code_without_type_code(self):
        """Код без '#' (нет type_code) сериализуется как {node_code}."""
        node = TemplateLiteNode(
            id=1, name="x", role=NodeRole.PODSTATYA, codes=["R_01_02"]
        )
        d = node.to_dict()
        assert d["upr_cube_codes"] == [{"node_code": "R_01_02"}]

    def test_to_dict_roundtrip_preserves_codes(self):
        """to_dict -> from_dict сохраняет составные codes."""
        node = TemplateLiteNode(
            id=1, name="x", role=NodeRole.PODSTATYA, parent=None,
            codes=["PL#R_01_02", "BS#R_01_99"],
        )
        restored = TemplateLiteNode.from_dict(node.to_dict())
        assert restored.codes == node.codes

    def test_to_dict_roundtrip_preserves_plain_codes(self):
        """Round-trip сохраняет коды без type_code (без добавления '#')."""
        node = TemplateLiteNode(
            id=1, name="x", role=NodeRole.PODSTATYA, parent=None,
            codes=["R_01_02"],
        )
        restored = TemplateLiteNode.from_dict(node.to_dict())
        assert restored.codes == ["R_01_02"]


class TestNodeValidation:
    """Валидация отдельного узла."""

    def test_valid_node(self):
        node = TemplateLiteNode(id=1, name="Корень", role=NodeRole.PODSTATYA)
        assert node.is_valid()

    def test_zero_id_invalid(self):
        node = TemplateLiteNode(id=0, name="x", role=NodeRole.PODSTATYA)
        assert not node.is_valid()
        assert any("id" in e for e in node.validate())

    def test_negative_id_invalid(self):
        node = TemplateLiteNode(id=-5, name="x", role=NodeRole.PODSTATYA)
        assert not node.is_valid()

    def test_empty_name_invalid(self):
        node = TemplateLiteNode(id=1, name="", role=NodeRole.PODSTATYA)
        assert not node.is_valid()
        assert any("name" in e for e in node.validate())

    def test_self_parent_invalid(self):
        node = TemplateLiteNode(id=1, name="x", role=NodeRole.PODSTATYA, parent=1)
        errors = node.validate()
        assert any("parent" in e for e in errors)


class TestNodeFromDictErrors:
    """Обработка некорректного входа from_dict."""

    def test_missing_id(self):
        with pytest.raises(ValueError, match="id"):
            TemplateLiteNode.from_dict({"name": "x", "role": "podstatya"})

    def test_missing_name(self):
        with pytest.raises(ValueError, match="name"):
            TemplateLiteNode.from_dict({"id": 1, "role": "podstatya"})

    def test_missing_role(self):
        with pytest.raises(ValueError, match="role"):
            TemplateLiteNode.from_dict({"id": 1, "name": "x"})

    def test_invalid_role_value(self):
        with pytest.raises(ValueError, match="role"):
            TemplateLiteNode.from_dict({"id": 1, "name": "x", "role": "nope"})

    def test_id_must_be_int(self):
        with pytest.raises(ValueError, match="id"):
            TemplateLiteNode.from_dict({"id": "1", "name": "x", "role": "podstatya"})

    def test_id_bool_rejected(self):
        """bool является подтипом int в Python — его нужно отклонить."""
        with pytest.raises(ValueError, match="id"):
            TemplateLiteNode.from_dict({"id": True, "name": "x", "role": "podstatya"})

    def test_parent_must_be_int_or_null(self):
        with pytest.raises(ValueError, match="parent"):
            TemplateLiteNode.from_dict(
                {"id": 1, "name": "x", "role": "podstatya", "parent": "1"}
            )


class TestNodeRepr:
    """Строковое представление."""

    def test_repr_root(self):
        node = TemplateLiteNode(id=1, name="Корень", role=NodeRole.PODSTATYA)
        assert repr(node) == "TemplateLiteNode(id=1, name='Корень', role=podstatya)"

    def test_repr_child_includes_parent(self):
        node = TemplateLiteNode(id=4, name="Маржа", role=NodeRole.TARIF, parent=3)
        assert "parent=3" in repr(node)
