"""Тесты enum-класса NodeRole."""

import pytest

from adhoc.template_lite import NodeRole


class TestNodeRole:
    """Тесты перечисления ролей узла."""

    def test_enum_has_four_members(self):
        """В enum ровно четыре значения, соответствующие данным."""
        assert len(NodeRole) == 4

    @pytest.mark.parametrize(
        "value,member",
        [
            ("podstatya", NodeRole.PODSTATYA),
            ("razrez", NodeRole.RAZREZ),
            ("tarif", NodeRole.TARIF),
            ("baza", NodeRole.BAZA),
        ],
    )
    def test_value_maps_to_member(self, value, member):
        """Строковое значение из JSON отображается в нужный член enum."""
        assert NodeRole(value) is member

    def test_values_match_json(self):
        """Строковые значения enum совпадают с ролями исходных JSON-файлов."""
        assert {m.value for m in NodeRole} == {"podstatya", "razrez", "tarif", "baza"}

    def test_is_str_enum(self):
        """NodeRole наследует str — удобно для сериализации и сравнения со строкой."""
        assert isinstance(NodeRole.PODSTATYA, str)
        assert NodeRole.PODSTATYA == "podstatya"

    def test_unknown_role_raises(self):
        """Неизвестная роль вызывает ValueError."""
        with pytest.raises(ValueError):
            NodeRole("unknown_role")
