"""
Общие фикстуры для тестов модуля template_lite.

Содержит путь к каталогу с реальными «lite»-сценариями
(``src/tmp/template_lite``) и эталонный мини-сценарий для юнит-тестов.
"""

from pathlib import Path

import pytest

from adhoc.template_lite import (
    NodeRole,
    TemplateLite,
    TemplateLiteNode,
)


@pytest.fixture
def template_lite_dir() -> Path:
    """Путь к каталогу с реальными JSON-файлами сценариев."""
    # __file__: .../src/adhoc/template_lite/tests/conftest.py
    # parents[3] -> src
    src_root = Path(__file__).resolve().parents[3]
    return src_root / "tmp" / "template_lite"


@pytest.fixture
def sample_dict() -> dict:
    """Эталонный мини-сценарий в виде dict (одна мультипликативная статья)."""
    return {
        "metricName": "Тестовый показатель",
        "nodes": [
            {"id": 1, "name": "Корневой показатель", "role": "podstatya", "parent": None},
            {"id": 2, "name": "Разрез по ТБ", "role": "razrez", "parent": 1},
            {"id": 3, "name": "Подстатья", "role": "podstatya", "parent": 2},
            {"id": 4, "name": "Маржа", "role": "tarif", "parent": 3},
            {"id": 5, "name": "СДО", "role": "baza", "parent": 3},
        ],
    }


@pytest.fixture
def sample_template(sample_dict) -> TemplateLite:
    """Эталонный мини-сценарий в виде объекта TemplateLite."""
    return TemplateLite.from_dict(sample_dict)


@pytest.fixture
def root_node() -> TemplateLiteNode:
    """Корневой узел-подстатья."""
    return TemplateLiteNode(id=1, name="Корень", role=NodeRole.PODSTATYA)
