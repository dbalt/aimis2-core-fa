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


def _strip_fin_code(node: dict) -> dict:
    """Привести узел к виду, который round-trip-ится через codes (List[str]).

    codes хранит составные коды ``"<type_code>#<node_code>"`` (либо просто
    ``node_code``, если ``type_code`` отсутствует); поле ``fin_code`` намеренно
    не сохраняется (см. :meth:`TemplateLiteNode.to_dict`). Поэтому из эталонного
    ``upr_cube_codes`` убираем ``fin_code`` — после этого узлы должны совпадать
    с результатом ``to_dict``.
    """
    ucc = node.get("upr_cube_codes")
    if not ucc:
        return node
    normalized = dict(node)
    normalized["upr_cube_codes"] = [
        {k: v for k, v in el.items() if k != "fin_code"} for el in ucc
    ]
    return normalized


def test_real_files_roundtrip(template_lite_dir):
    """Round-trip: десериализация -> to_dict() эквивалентен исходному JSON.

    Поле ``upr_cube_codes`` реконструируется из ``codes`` (``List[str]``) без
    ``fin_code``, поэтому эталон нормализуется (``fin_code`` убирается) перед
    сравнением.
    """
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
            expected = _strip_fin_code(orig)
            assert new_nodes[nid] == expected, (
                f"Расхождение в узле id={nid} ({path.name})"
            )


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


# ---------------------------------------------------------------------------
# Поле upr_cube_codes (задача 30): node_code -> codes -> query
# ---------------------------------------------------------------------------

def _files_with_upr_cube_codes(template_lite_dir):
    """Рекурсивно найти JSON-сценарии, содержащие поле upr_cube_codes."""
    found = []
    for path in sorted(template_lite_dir.glob("**/*.json")):
        text = path.read_text(encoding="utf-8")
        if "upr_cube_codes" in text:
            found.append(path)
    return found


def test_upr_cube_codes_parsed_into_codes(template_lite_dir):
    """В реальных файлах с upr_cube_codes поле codes заполняется составными
    кодами "<type_code>#<node_code>"."""
    files = _files_with_upr_cube_codes(template_lite_dir)
    if not files:
        pytest.skip("Нет файлов с upr_cube_codes")

    total_with_codes = 0
    combined_seen = False
    for path in files:
        tpl = get_from_template_lite_json(str(path))
        for node in tpl:
            if not node.is_valid():
                continue
            # codes — всегда список строк.
            assert isinstance(node.codes, list)
            assert all(isinstance(c, str) for c in node.codes)
            for code in node.codes:
                # Реальные элементы всегда содержат type_code -> код вида
                # "<type_code>#<node_code>" с непустыми частями.
                if "#" in code:
                    combined_seen = True
                    type_code, node_code = code.split("#", 1)
                    assert type_code and node_code
            if node.codes:
                total_with_codes += 1
    assert total_with_codes > 0, "Ни один узел не получил codes из upr_cube_codes"
    assert combined_seen, "Составной код type_code#node_code не встретился"


def test_upr_cube_codes_flow_into_node_code_query(template_lite_dir):
    """Узлы с codes после трансформации получают query {'node_code': codes}."""
    from adhoc.template_lite import transform_template_lite_to_hierarchy

    files = _files_with_upr_cube_codes(template_lite_dir)
    if not files:
        pytest.skip("Нет файлов с upr_cube_codes")

    checked = 0
    for path in files:
        tpl = get_from_template_lite_json(str(path))
        h = transform_template_lite_to_hierarchy(tpl)
        assert h.is_valid(), f"{path.name}: {h.validate()}"
        for tl_node in tpl:
            if not tl_node.codes:
                continue
            metric = h.get_node(tl_node.id)
            assert metric is not None
            assert metric.query is not None
            assert metric.query.to_dict() == {"node_code": tl_node.codes}
            checked += 1
    assert checked > 0


def test_specific_od_tbgosb_file_codes(template_lite_dir):
    """Известный факт: «Кредиты банкам» в файле «2 ветка ОД (от блока)»
    имеет ровно один составной код PL#R_01_02 (type_code=PL, node_code=R_01_02)."""
    target = next(
        (
            p for p in _files_with_upr_cube_codes(template_lite_dir)
            if "от блока" in p.name and "тотала" in str(p).lower()
        ),
        None,
    )
    if target is None:
        pytest.skip("Файл «2 ветка ОД (от блока)» не найден")
    tpl = get_from_template_lite_json(str(target))
    # Найти узел «Кредиты банкам».
    node = next(
        (n for n in tpl if n.name == "Кредиты банкам" and n.codes), None
    )
    assert node is not None, "Узел «Кредиты банкам» с codes не найден"
    assert node.codes == ["PL#R_01_02"]
