"""Тесты функции десериализации get_from_template_lite_json."""

import json
from pathlib import Path

import pytest

from adhoc_xxx.template_lite import (
    NodeRole,
    TemplateLite,
    TemplateLiteNode,
    get_from_template_lite_json,
)


class TestDeserializerFromDict:
    """Десериализация из dict."""

    def test_from_dict_basic(self, sample_dict):
        tpl = get_from_template_lite_json(sample_dict)
        assert isinstance(tpl, TemplateLite)
        assert tpl.metric_name == "Тестовый показатель"
        assert tpl.count_nodes() == 5

    def test_from_dict_preserves_roles(self, sample_dict):
        tpl = get_from_template_lite_json(sample_dict)
        assert tpl.get_node(4).role is NodeRole.TARIF
        assert tpl.get_node(5).role is NodeRole.BAZA


class TestDeserializerFromString:
    """Десериализация из JSON-строки."""

    def test_from_json_string(self, sample_dict):
        text = json.dumps(sample_dict, ensure_ascii=False)
        tpl = get_from_template_lite_json(text)
        assert tpl.metric_name == sample_dict["metricName"]
        assert tpl.count_nodes() == 5

    def test_from_json_string_kirillic(self):
        text = '{"metricName": "Показатель", "nodes": [{"id": 1, "name": "Корень", "role": "podstatya", "parent": null}]}'
        tpl = get_from_template_lite_json(text)
        assert tpl.metric_name == "Показатель"
        assert tpl.get_root().name == "Корень"


class TestDeserializerFromFile:
    """Десериализация из файла (str и Path)."""

    def test_from_file_str_path(self, sample_dict, tmp_path):
        path = tmp_path / "scenario.json"
        path.write_text(json.dumps(sample_dict, ensure_ascii=False), encoding="utf-8")
        tpl = get_from_template_lite_json(str(path))
        assert tpl.metric_name == "Тестовый показатель"

    def test_from_file_pathlib(self, sample_dict, tmp_path):
        path = tmp_path / "scenario.json"
        path.write_text(json.dumps(sample_dict, ensure_ascii=False), encoding="utf-8")
        tpl = get_from_template_lite_json(path)
        assert isinstance(tpl, TemplateLite)

    def test_from_file_kirillic_name(self, sample_dict, tmp_path):
        """Имя файла с кириллицей читается корректно."""
        path = tmp_path / "показатель_lite.json"
        path.write_text(json.dumps(sample_dict, ensure_ascii=False), encoding="utf-8")
        tpl = get_from_template_lite_json(str(path))
        assert tpl.count_nodes() == 5

    def test_json_string_not_file_treated_as_content(self):
        """Строка, не являющаяся путём к существующему файлу, трактуется как JSON-контент."""
        text = (
            '{"metricName": "X", "nodes": ['
            '{"id": 1, "name": "r", "role": "podstatya", "parent": null}]}'
        )
        tpl = get_from_template_lite_json(text)
        assert tpl.metric_name == "X"
        assert tpl.count_nodes() == 1

    def test_nonexistent_path_raises(self):
        """Строка, не являющаяся JSON-контентом, трактуется как путь к файлу;
        для несуществующего файла получаем FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            get_from_template_lite_json("not_a_file_path.json")

    def test_malformed_json_content_raises(self):
        """Некорректный JSON-контент (начинается с '{') вызывает JSONDecodeError."""
        with pytest.raises(json.JSONDecodeError):
            get_from_template_lite_json("{ not valid json ")


class TestDeserializerErrors:
    """Обработка ошибок десериализатора."""

    def test_unsupported_type_raises(self):
        with pytest.raises(TypeError):
            get_from_template_lite_json(123)  # type: ignore[arg-type]

    def test_unsupported_list_raises(self):
        with pytest.raises(TypeError):
            get_from_template_lite_json([1, 2, 3])  # type: ignore[arg-type]

    def test_invalid_role_raises(self):
        bad = {"metricName": "X", "nodes": [{"id": 1, "name": "r", "role": "ghost", "parent": None}]}
        with pytest.raises(ValueError, match="role"):
            get_from_template_lite_json(bad)
