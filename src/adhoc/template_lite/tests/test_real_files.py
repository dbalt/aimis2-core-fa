"""
Тесты на реальных JSON-файлах сценариев из src/tmp/template_lite.

Проверяют end-to-end десериализацию реальных данных, round-trip
сериализацию и структуру разобранных деревьев.
"""

import json

import pytest

from adhoc.template_lite import (
    NodeRole,
    TemplateLite,
    get_from_template_lite_json,
)


def _real_files(template_lite_dir):
    """Список реальных JSON-файлов сценариев."""
    return sorted(template_lite_dir.glob("*.json"))


def test_real_files_exist(template_lite_dir):
    """Каталог с реальными сценариями существует и содержит файлы."""
    files = _real_files(template_lite_dir)
    assert len(files) >= 1, f"Не найдено JSON-файлов в {template_lite_dir}"


@pytest.mark.parametrize("idx", [0, 1])
def test_deserialize_real_file(idx, template_lite_dir):
    """Каждый реальный файл десериализуется без ошибок."""
    files = _real_files(template_lite_dir)
    if idx >= len(files):
        pytest.skip("Недостаточно реальных файлов для этого индекса")
    tpl = get_from_template_lite_json(str(files[idx]))
    assert isinstance(tpl, TemplateLite)
    assert tpl.metric_name
    assert tpl.count_nodes() > 0


def test_real_files_roundtrip(template_lite_dir):
    """Round-trip: десериализация -> to_dict() эквивалентен исходному JSON."""
    for path in _real_files(template_lite_dir):
        original = json.loads(path.read_text(encoding="utf-8"))
        tpl = get_from_template_lite_json(str(path))
        rebuilt = tpl.to_dict()
        # metricName должен совпасть
        assert rebuilt["metricName"] == original["metricName"]
        # Набор узлов по id должен совпадать
        orig_nodes = {n["id"]: n for n in original["nodes"]}
        new_nodes = {n["id"]: n for n in rebuilt["nodes"]}
        assert set(orig_nodes) == set(new_nodes)
        for nid, orig in orig_nodes.items():
            assert new_nodes[nid] == orig, f"Расхождение в узле id={nid} ({path.name})"


def test_real_files_valid_structure(template_lite_dir):
    """Каждый реальный сценарий проходит валидацию структуры."""
    for path in _real_files(template_lite_dir):
        tpl = get_from_template_lite_json(str(path))
        errors = tpl.validate()
        assert not errors, f"{path.name}: ошибки валидации: {errors}"


def test_real_files_roles_consistent(template_lite_dir):
    """Все роли узлов в реальных файлах принадлежат известному enum-множеству."""
    valid_roles = {r.value for r in NodeRole}
    for path in _real_files(template_lite_dir):
        tpl = get_from_template_lite_json(str(path))
        for node in tpl:
            assert node.role.value in valid_roles


def test_real_files_tarif_baza_pairing(template_lite_dir):
    """Каждый тариф-узел имеет соседний база-узел под тем же родителем
    (инвариант мультипликативной статьи)."""
    for path in _real_files(template_lite_dir):
        tpl = get_from_template_lite_json(str(path))
        for node in tpl:
            if node.role == NodeRole.TARIF:
                siblings = tpl.get_children(node.parent)
                assert any(s.role == NodeRole.BAZA for s in siblings), (
                    f"Тариф id={node.id} без парной базы в {path.name}"
                )


def test_operacionnyj_dohod_specifics(template_lite_dir):
    """Проверка известных фактов о файле 'операционный доход до резервов'."""
    target = next(
        (p for p in _real_files(template_lite_dir) if "операцион" in p.name.lower()),
        None,
    )
    if target is None:
        pytest.skip("Файл операционного дохода не найден")
    tpl = get_from_template_lite_json(str(target))
    assert tpl.count_nodes() == 72
    # Корень — подстатья «Операционный доход до резервов»
    root = tpl.get_root()
    assert root.is_podstatya()
    assert "Операционный доход" in root.name
    # Есть мультипликативные статьи (пары Маржа/СДО)
    assert len(tpl.get_multiplier_nodes()) > 0


def test_chkd_specifics(template_lite_dir):
    """Проверка известных фактов о файле 'чкд+'."""
    target = next(
        (p for p in _real_files(template_lite_dir) if "чкд" in p.name.lower()),
        None,
    )
    if target is None:
        pytest.skip("Файл ЧКД+ не найден")
    tpl = get_from_template_lite_json(str(target))
    assert tpl.count_nodes() == 33
    # В ЧКД+ нет тарифов/баз — только подстатьи и разрезы
    assert len(tpl.get_tarif()) == 0
    assert len(tpl.get_baza()) == 0
    assert len(tpl.get_razrez()) > 0
