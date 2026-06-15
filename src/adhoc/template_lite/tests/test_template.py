"""Тесты класса TemplateLite (контейнер сценария)."""

import json

import pytest

from adhoc.template_lite import (
    NodeRole,
    TemplateLite,
    TemplateLiteNode,
)


class TestTemplateConstruction:
    """Построение и управление узлами."""

    def test_empty_template(self):
        tpl = TemplateLite(metric_name="Пусто")
        assert tpl.metric_name == "Пусто"
        assert tpl.is_empty()
        assert tpl.count_nodes() == 0
        assert tpl.get_root() is None

    def test_add_node(self, root_node):
        tpl = TemplateLite(metric_name="M")
        tpl.add_node(root_node)
        assert tpl.count_nodes() == 1
        assert tpl.has_node(1)
        assert tpl.get_node(1) is root_node

    def test_add_duplicate_id_raises(self, root_node):
        tpl = TemplateLite(metric_name="M")
        tpl.add_node(root_node)
        with pytest.raises(ValueError, match="уже существует"):
            tpl.add_node(TemplateLiteNode(id=1, name="dup", role=NodeRole.PODSTATYA))

    def test_remove_node(self, root_node):
        tpl = TemplateLite(metric_name="M")
        tpl.add_node(root_node)
        removed = tpl.remove_node(1)
        assert removed is root_node
        assert tpl.is_empty()
        assert tpl.remove_node(999) is None


class TestTemplateNavigation:
    """Навигация по дереву."""

    def test_get_root(self, sample_template):
        root = sample_template.get_root()
        assert root is not None
        assert root.id == 1
        assert root.is_root()

    def test_get_children_ordered_by_id(self, sample_template):
        # Добавим второго потомка узла 3 с меньшим id-порядком для проверки сортировки
        children = sample_template.get_children(3)
        assert [c.id for c in children] == [4, 5]

    def test_get_children_empty(self, sample_template):
        assert sample_template.get_children(5) == []

    def test_get_parent(self, sample_template):
        assert sample_template.get_parent(4).id == 3
        assert sample_template.get_parent(1) is None
        assert sample_template.get_parent(999) is None

    def test_get_descendants(self, sample_template):
        desc_ids = {n.id for n in sample_template.get_descendants(1)}
        assert desc_ids == {2, 3, 4, 5}

    def test_get_ancestors(self, sample_template):
        anc_ids = [n.id for n in sample_template.get_ancestors(4)]
        assert anc_ids == [3, 2, 1]

    def test_get_path(self, sample_template):
        path_ids = [n.id for n in sample_template.get_path(4)]
        assert path_ids == [1, 2, 3, 4]

    def test_roots_single(self, sample_template):
        roots = sample_template.get_roots()
        assert len(roots) == 1


class TestTemplateRoleFilters:
    """Фильтрация узлов по ролям."""

    def test_get_podstatya(self, sample_template):
        ids = {n.id for n in sample_template.get_podstatya()}
        assert ids == {1, 3}

    def test_get_razrez(self, sample_template):
        ids = {n.id for n in sample_template.get_razrez()}
        assert ids == {2}

    def test_get_tarif(self, sample_template):
        ids = {n.id for n in sample_template.get_tarif()}
        assert ids == {4}

    def test_get_baza(self, sample_template):
        ids = {n.id for n in sample_template.get_baza()}
        assert ids == {5}

    def test_get_multiplier_nodes(self, sample_template):
        """Подстатья 3 имеет пару тариф(4)+база(5) -> она мультипликативная."""
        mult = sample_template.get_multiplier_nodes()
        assert [n.id for n in mult] == [3]

    def test_get_multiplier_nodes_none(self):
        """Подстатья без тарифа/базы не считается мультипликативной."""
        tpl = TemplateLite(metric_name="M")
        tpl.add_node(TemplateLiteNode(id=1, name="root", role=NodeRole.PODSTATYA))
        tpl.add_node(TemplateLiteNode(id=2, name="sub", role=NodeRole.PODSTATYA, parent=1))
        assert tpl.get_multiplier_nodes() == []


class TestTemplateSerialization:
    """Сериализация сценария."""

    def test_to_dict_structure(self, sample_template):
        d = sample_template.to_dict()
        assert d["metricName"] == "Тестовый показатель"
        assert len(d["nodes"]) == 5
        # Узлы упорядочены по id
        assert [n["id"] for n in d["nodes"]] == [1, 2, 3, 4, 5]

    def test_roundtrip_dict(self, sample_dict):
        tpl = TemplateLite.from_dict(sample_dict)
        assert tpl.to_dict() == sample_dict

    def test_json_string_roundtrip(self, sample_template):
        s = sample_template.to_json_string()
        restored = TemplateLite.from_json_string(s)
        assert restored == sample_template

    def test_json_string_valid_json(self, sample_template):
        s = sample_template.to_json_string()
        # Строка должна быть валидным JSON с правильной кодировкой кириллицы
        parsed = json.loads(s)
        assert parsed["metricName"] == "Тестовый показатель"

    def test_from_dict_missing_metricname(self):
        with pytest.raises(ValueError, match="metricName"):
            TemplateLite.from_dict({"nodes": []})

    def test_from_dict_missing_nodes(self):
        with pytest.raises(ValueError, match="nodes"):
            TemplateLite.from_dict({"metricName": "X"})

    def test_from_dict_nodes_not_list(self):
        with pytest.raises(ValueError, match="nodes"):
            TemplateLite.from_dict({"metricName": "X", "nodes": {}})


class TestTemplateValidation:
    """Валидация структуры сценария."""

    def test_valid_sample(self, sample_template):
        assert sample_template.is_valid(), sample_template.validate()

    def test_empty_metric_name(self):
        tpl = TemplateLite(metric_name="")
        tpl.add_node(TemplateLiteNode(id=1, name="r", role=NodeRole.PODSTATYA))
        errors = tpl.validate()
        assert any("metricName" in e for e in errors)

    def test_empty_nodes(self):
        tpl = TemplateLite(metric_name="M")
        errors = tpl.validate()
        assert any("хотя бы один узел" in e for e in errors)

    def test_no_root(self):
        tpl = TemplateLite(metric_name="M")
        # Все узлы имеют родителя -> корня нет
        tpl.add_node(TemplateLiteNode(id=1, name="a", role=NodeRole.PODSTATYA, parent=2))
        tpl.add_node(TemplateLiteNode(id=2, name="b", role=NodeRole.PODSTATYA, parent=1))
        errors = tpl.validate()
        assert any("корневой узел" in e for e in errors)

    def test_multiple_roots(self):
        tpl = TemplateLite(metric_name="M")
        tpl.add_node(TemplateLiteNode(id=1, name="a", role=NodeRole.PODSTATYA))
        tpl.add_node(TemplateLiteNode(id=2, name="b", role=NodeRole.PODSTATYA))
        errors = tpl.validate()
        assert any("один корневой" in e for e in errors)

    def test_root_must_be_podstatya(self):
        tpl = TemplateLite(metric_name="M")
        tpl.add_node(TemplateLiteNode(id=1, name="dim", role=NodeRole.RAZREZ))
        errors = tpl.validate()
        assert any("podstatya" in e for e in errors)

    def test_dangling_parent(self):
        tpl = TemplateLite(metric_name="M")
        tpl.add_node(TemplateLiteNode(id=1, name="root", role=NodeRole.PODSTATYA))
        tpl.add_node(
            TemplateLiteNode(id=2, name="orphan", role=NodeRole.PODSTATYA, parent=99)
        )
        errors = tpl.validate()
        assert any("несуществующего родителя" in e for e in errors)

    def test_cycle_detected(self):
        """Цикл в parent: 1<-2<-3<-1 (без корня) — нужно, но будет и ошибка корня.
        Проверим цикл при наличии корня-свидетеля через прямой конструктор."""
        tpl = TemplateLite(metric_name="M")
        # Ручное формирование цикла (add_node не проверяет parent)
        a = TemplateLiteNode(id=1, name="a", role=NodeRole.PODSTATYA)
        b = TemplateLiteNode(id=2, name="b", role=NodeRole.PODSTATYA, parent=3)
        c = TemplateLiteNode(id=3, name="c", role=NodeRole.PODSTATYA, parent=2)
        # a — корень-свидетель, b<->c образуют цикл
        tpl.add_node(a)
        tpl.add_node(b)
        tpl.add_node(c)
        errors = tpl.validate()
        assert any("цикл" in e for e in errors)


class TestTemplateDunder:
    """Dunder-методы и итерация."""

    def test_len(self, sample_template):
        assert len(sample_template) == 5

    def test_contains(self, sample_template):
        assert 1 in sample_template
        assert 999 not in sample_template

    def test_iter_ordered(self, sample_template):
        ids = [n.id for n in sample_template]
        assert ids == [1, 2, 3, 4, 5]

    def test_repr(self, sample_template):
        assert repr(sample_template) == "TemplateLite(metric_name='Тестовый показатель', nodes=5)"

    def test_equality(self, sample_dict):
        a = TemplateLite.from_dict(sample_dict)
        b = TemplateLite.from_dict(sample_dict)
        assert a == b

    def test_inequality(self, sample_dict):
        a = TemplateLite.from_dict(sample_dict)
        other = dict(sample_dict)
        other["metricName"] = "Другой"
        b = TemplateLite.from_dict(other)
        assert a != b
