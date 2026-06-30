"""
Тесты функции ``transform_template_lite_to_hierarchy``.

Покрывают правила трансформации (роль → тип, разрез → analyt_metadata,
query для листьев/MULTI), подъём поддерева разреза (lifting), объединение
нескольких разрезов одного узла, значение ``mp_decomp_tp`` и end-to-end
преобразование реальных файлов.
"""

import pytest

from adhoc_xxx.template_lite import (
    NodeRole,
    TemplateLite,
    TemplateLiteNode,
    transform_template_lite_to_hierarchy,
)
from libfa2.analyt_struct_metadata import AnalyticalStructureMetadata
from libfa2.hier_metadata import (
    ComponentMultiPartType,
    Hierarchy,
    MetricNode,
    MetricType,
    MultipartDecompositionType,
)


# ---------------------------------------------------------------------------
# Вспомогательные построители сценариев
# ---------------------------------------------------------------------------

def _make_template(spec) -> TemplateLite:
    """Собрать TemplateLite из списка кортежей (id, name, role, parent)."""
    tpl = TemplateLite(metric_name="Тест")
    for node_id, name, role, parent in spec:
        tpl.add_node(
            TemplateLiteNode(id=node_id, name=name, role=role, parent=parent)
        )
    return tpl


# ---------------------------------------------------------------------------
# Базовое поведение и тип результата
# ---------------------------------------------------------------------------

def test_returns_hierarchy(sample_template):
    """Функция возвращает объект Hierarchy."""
    result = transform_template_lite_to_hierarchy(sample_template)
    assert isinstance(result, Hierarchy)


def test_invalid_input_type_raises():
    """Не-TemplateLite на входе вызывает TypeError."""
    with pytest.raises(TypeError):
        transform_template_lite_to_hierarchy("not a template")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        transform_template_lite_to_hierarchy({"metricName": "x"})  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Правило 1: RAZREZ → analyt_metadata на родителе (без собственного узла)
# ---------------------------------------------------------------------------

def test_razrez_does_not_become_node():
    """Разрез не создаёт MetricNode, а добавляет analyt_metadata родителю."""
    tpl = _make_template([
        (1, "Показатель", NodeRole.PODSTATYA, None),
        (2, "Разрез ТБ", NodeRole.RAZREZ, 1),
    ])
    h = transform_template_lite_to_hierarchy(tpl)

    # Разрез id=2 схлопнут: остался только узел-показатель.
    assert h.count_nodes() == 1
    assert h.has_node(1)
    assert not h.has_node(2)

    parent = h.get_node(1)
    assert parent.analyt_metadata is not None
    assert isinstance(parent.analyt_metadata, AnalyticalStructureMetadata)


def test_razrez_metadata_one_algorithm_one_dimension():
    """AnalyticalStructureMetadata содержит ровно один алгоритм и одно
    измерение, наименования берутся из поля name разреза."""
    tpl = _make_template([
        (1, "Показатель", NodeRole.PODSTATYA, None),
        (2, "Сегмент", NodeRole.RAZREZ, 1),
    ])
    h = transform_template_lite_to_hierarchy(tpl)
    meta = h.get_node(1).analyt_metadata

    assert len(meta.dimensions) == 1
    assert len(meta.algorithms) == 1

    dim = next(iter(meta.dimensions.values()))
    assert dim.code == "Сегмент"
    assert dim.name == "Сегмент"
    assert dim.column == "Сегмент"

    algo = next(iter(meta.algorithms.values()))
    assert algo.drill_order == [["Сегмент"]]


def test_razrez_without_metric_parent_is_skipped():
    """Разрез под разрезом поднимается до ближайшего неразрезного предка."""
    tpl = _make_template([
        (1, "Показатель", NodeRole.PODSTATYA, None),
        (2, "Внешний разрез", NodeRole.RAZREZ, 1),
        (3, "Внутренний разрез", NodeRole.RAZREZ, 2),
        (4, "Статья", NodeRole.PODSTATYA, 3),
    ])
    h = transform_template_lite_to_hierarchy(tpl)

    # Оба разреза (id=2, id=3) схлопнуты; статья id=4 поднята к корню id=1.
    assert h.count_nodes() == 2
    assert {n.id for n in h} == {1, 4}
    assert h.get_node(4).parent == 1

    # Оба разреза привязаны к ближайшему неразрезному предку (id=1).
    dims = {d.name for d in h.get_node(1).analyt_metadata.dimensions.values()}
    assert dims == {"Внешний разрез", "Внутренний разрез"}


def test_multiple_razrez_same_parent_are_merged():
    """Несколько разрезов под одним родителем объединяются в один
    analyt_metadata: ровно один алгоритм, по одному измерению на разрез,
    а drill_order — цепочка шагов в порядке разрезов сценария."""
    tpl = _make_template([
        (1, "Показатель", NodeRole.PODSTATYA, None),
        (2, "ТБ/ГОСБ", NodeRole.RAZREZ, 1),
        (3, "Блок/Подблок", NodeRole.RAZREZ, 1),
    ])
    h = transform_template_lite_to_hierarchy(tpl)
    meta = h.get_node(1).analyt_metadata

    # По одному измерению на разрез.
    assert len(meta.dimensions) == 2
    dim_names = {d.name for d in meta.dimensions.values()}
    assert dim_names == {"ТБ/ГОСБ", "Блок/Подблок"}

    # Ровно один алгоритм с цепочкой из двух шагов в порядке разрезов
    # (по id узла: сначала id=2, затем id=3).
    assert len(meta.algorithms) == 1
    algo = next(iter(meta.algorithms.values()))
    assert algo.id == 1
    assert algo.drill_order == [["ТБ/ГОСБ"], ["Блок/Подблок"]]
    # Каждый шаг ссылается на существующее измерение.
    for step in algo.drill_order:
        for code in step:
            assert code in meta.dimensions


def test_many_razrez_form_single_algorithm_chain():
    """N разрезов (N >= 3) дают один алгоритм с цепочкой из N шагов
    в порядке исходного сценария."""
    tpl = _make_template([
        (1, "Показатель", NodeRole.PODSTATYA, None),
        (2, "Сегмент", NodeRole.RAZREZ, 1),
        (3, "Геоструктура", NodeRole.RAZREZ, 1),
        (4, "Канал", NodeRole.RAZREZ, 1),
    ])
    h = transform_template_lite_to_hierarchy(tpl)
    meta = h.get_node(1).analyt_metadata

    assert len(meta.dimensions) == 3
    assert len(meta.algorithms) == 1
    algo = next(iter(meta.algorithms.values()))
    assert algo.drill_order == [["Сегмент"], ["Геоструктура"], ["Канал"]]


def test_duplicate_razrez_names_get_suffixed_codes():
    """При совпадении имён разрезов коды измерений получают суффикс и
    корректно попадают в цепочку drill_order единственного алгоритма."""
    tpl = _make_template([
        (1, "Показатель", NodeRole.PODSTATYA, None),
        (2, "Сегмент", NodeRole.RAZREZ, 1),
        (3, "Сегмент", NodeRole.RAZREZ, 1),
    ])
    h = transform_template_lite_to_hierarchy(tpl)
    meta = h.get_node(1).analyt_metadata

    codes = set(meta.dimensions)
    assert codes == {"Сегмент", "Сегмент_2"}
    # Один алгоритм; оба уникальных кода — в его цепочке drill_order.
    assert len(meta.algorithms) == 1
    algo = next(iter(meta.algorithms.values()))
    assert algo.drill_order == [["Сегмент"], ["Сегмент_2"]]
    assert algo.dimension_codes == codes


def test_node_without_razrez_has_no_metadata():
    """У узла без разрезов analyt_metadata отсутствует (None)."""
    tpl = _make_template([
        (1, "Корень", NodeRole.PODSTATYA, None),
        (2, "Подстатья", NodeRole.PODSTATYA, 1),
    ])
    h = transform_template_lite_to_hierarchy(tpl)
    assert h.get_node(1).analyt_metadata is None
    assert h.get_node(2).analyt_metadata is None


# ---------------------------------------------------------------------------
# Правило 2: роли потомков → type родителя; componentMultiPartType
# ---------------------------------------------------------------------------

def test_podstatya_children_make_parent_sum():
    """Подстатья-потомок даёт родителю type=SUM."""
    tpl = _make_template([
        (1, "Корень", NodeRole.PODSTATYA, None),
        (2, "Подстатья A", NodeRole.PODSTATYA, 1),
        (3, "Подстатья B", NodeRole.PODSTATYA, 1),
    ])
    h = transform_template_lite_to_hierarchy(tpl)
    assert h.get_node(1).type == MetricType.SUM


def test_tarif_baza_children_make_parent_multi():
    """Пара тариф+база под подстатьей даёт родителю type=MULTI."""
    tpl = _make_template([
        (1, "Корень", NodeRole.PODSTATYA, None),
        (2, "Статья", NodeRole.PODSTATYA, 1),
        (3, "Маржа", NodeRole.TARIF, 2),
        (4, "СДО", NodeRole.BAZA, 2),
    ])
    h = transform_template_lite_to_hierarchy(tpl)
    article = h.get_node(2)
    assert article.type == MetricType.MULTI
    # Сама статья-множитель не имеет componentMultiPartType.
    assert article.componentMultiPartType is None


def test_tarif_gets_rate_baza_gets_base():
    """Тариф получает RATE, база — BASE."""
    tpl = _make_template([
        (1, "Корень", NodeRole.PODSTATYA, None),
        (2, "Статья", NodeRole.PODSTATYA, 1),
        (3, "Маржа", NodeRole.TARIF, 2),
        (4, "СДО", NodeRole.BAZA, 2),
    ])
    h = transform_template_lite_to_hierarchy(tpl)
    assert h.get_node(3).componentMultiPartType == ComponentMultiPartType.RATE
    assert h.get_node(4).componentMultiPartType == ComponentMultiPartType.BASE


def test_leaf_podstatya_has_no_type():
    """Подстатья без потомков становится листом (type=None)."""
    tpl = _make_template([
        (1, "Корень", NodeRole.PODSTATYA, None),
        (2, "Лист", NodeRole.PODSTATYA, 1),
    ])
    h = transform_template_lite_to_hierarchy(tpl)
    assert h.get_node(2).type is None


def test_multi_node_is_valid_with_rate_and_base():
    """Узел MULTI имеет ровно одного потомка rate и одного base."""
    tpl = _make_template([
        (1, "Корень", NodeRole.PODSTATYA, None),
        (2, "Статья", NodeRole.PODSTATYA, 1),
        (3, "Маржа", NodeRole.TARIF, 2),
        (4, "СДО", NodeRole.BAZA, 2),
    ])
    h = transform_template_lite_to_hierarchy(tpl)
    children = h.get_children(2)
    rates = [c for c in children if c.componentMultiPartType == ComponentMultiPartType.RATE]
    bases = [c for c in children if c.componentMultiPartType == ComponentMultiPartType.BASE]
    assert len(rates) == 1
    assert len(bases) == 1


# ---------------------------------------------------------------------------
# Подъём поддерева разреза (lifting)
# ---------------------------------------------------------------------------

def test_razrez_subtree_lifted_to_parent(sample_template):
    """Поддерево под разрезом подтягивается к неразрезному предку,
    а разрез, имевший поддерево, превращает приёмника в MULTI."""
    # sample_template: 1(podstatya) > 2(razrez) > 3(podstatya) > 4(tarif),5(baza)
    h = transform_template_lite_to_hierarchy(sample_template)

    # 5 узлов сценария → 4 узла иерархии (разрез id=2 схлопнут).
    assert h.count_nodes() == 4
    # Подстатья id=3 поднята под корень id=1.
    assert h.get_node(3).parent == 1
    # id=3 получила пару тариф/база → MULTI.
    assert h.get_node(3).type == MetricType.MULTI
    # Корень id=1 — SUM (подстатья-потомок id=3).
    assert h.get_node(1).type == MetricType.SUM
    # Разрез «Разрез по ТБ» у корня.
    dims = {d.name for d in h.get_node(1).analyt_metadata.dimensions.values()}
    assert dims == {"Разрез по ТБ"}
    # Построенная иерархия проходит валидацию.
    assert not h.validate()


def test_podstatya_whose_only_child_is_razrez_becomes_multi():
    """Подстатья, единственный потомок которой — разрез с парой тариф/база,
    после подъёма становится MULTI."""
    tpl = _make_template([
        (1, "Корень", NodeRole.PODSTATYA, None),
        (2, "Кредиты физлицам", NodeRole.PODSTATYA, 1),
        (3, "Продукт ЕК", NodeRole.RAZREZ, 2),
        (4, "Маржа", NodeRole.TARIF, 3),
        (5, "СДО", NodeRole.BAZA, 3),
    ])
    h = transform_template_lite_to_hierarchy(tpl)
    node = h.get_node(2)
    assert node.type == MetricType.MULTI
    dims = {d.name for d in node.analyt_metadata.dimensions.values()}
    assert dims == {"Продукт ЕК"}
    # Тариф/база подняты под id=2.
    assert h.get_node(4).parent == 2
    assert h.get_node(5).parent == 2
    assert not h.validate()


# ---------------------------------------------------------------------------
# Правило 3: query для листьев и MULTI
# ---------------------------------------------------------------------------

def test_leaf_nodes_get_pl_code_query():
    """Листовые узлы получают query {'pl_code': <name>}."""
    tpl = _make_template([
        (1, "Корень", NodeRole.PODSTATYA, None),
        (2, "Листовая статья", NodeRole.PODSTATYA, 1),
    ])
    h = transform_template_lite_to_hierarchy(tpl)
    leaf = h.get_node(2)
    assert leaf.has_query()
    assert leaf.query.to_dict() == {"pl_code": "Листовая статья"}


def test_multi_nodes_get_pl_code_query():
    """Узлы MULTI получают query {'pl_code': <name>}."""
    tpl = _make_template([
        (1, "Корень", NodeRole.PODSTATYA, None),
        (2, "Мульти статья", NodeRole.PODSTATYA, 1),
        (3, "Маржа", NodeRole.TARIF, 2),
        (4, "СДО", NodeRole.BAZA, 2),
    ])
    h = transform_template_lite_to_hierarchy(tpl)
    multi = h.get_node(2)
    assert multi.has_query()
    assert multi.query.to_dict() == {"pl_code": "Мульти статья"}


def test_tarif_baza_leaves_get_query():
    """Тариф/база (листья с componentMultiPartType) тоже получают query."""
    tpl = _make_template([
        (1, "Корень", NodeRole.PODSTATYA, None),
        (2, "Статья", NodeRole.PODSTATYA, 1),
        (3, "Маржа", NodeRole.TARIF, 2),
        (4, "СДО", NodeRole.BAZA, 2),
    ])
    h = transform_template_lite_to_hierarchy(tpl)
    assert h.get_node(3).has_query()
    assert h.get_node(4).has_query()
    assert h.get_node(3).query.to_dict() == {"pl_code": "Маржа"}
    assert h.get_node(4).query.to_dict() == {"pl_code": "СДО"}


def test_sum_node_without_query():
    """SUM-узел без собственных данных не получает query."""
    tpl = _make_template([
        (1, "Корень", NodeRole.PODSTATYA, None),
        (2, "Подстатья", NodeRole.PODSTATYA, 1),
        (3, "Лист", NodeRole.PODSTATYA, 2),
    ])
    h = transform_template_lite_to_hierarchy(tpl)
    assert h.get_node(1).query is None
    assert h.get_node(2).query is None


# ---------------------------------------------------------------------------
# Правило 3 (расширение): codes -> query {'node_code': <codes>}
# ---------------------------------------------------------------------------

def _make_template_with_codes(spec) -> TemplateLite:
    """Собрать TemplateLite из (id, name, role, parent, codes)."""
    tpl = TemplateLite(metric_name="Тест")
    for node_id, name, role, parent, codes in spec:
        tpl.add_node(
            TemplateLiteNode(
                id=node_id, name=name, role=role, parent=parent, codes=codes
            )
        )
    return tpl


def test_leaf_with_codes_gets_node_code_query():
    """Листовой узел с codes получает query {'node_code': codes}."""
    tpl = _make_template_with_codes([
        (1, "Корень", NodeRole.PODSTATYA, None, []),
        (2, "Кредиты банкам", NodeRole.PODSTATYA, 1, ["R_01_02", "R_01_99"]),
    ])
    h = transform_template_lite_to_hierarchy(tpl)
    leaf = h.get_node(2)
    assert leaf.has_query()
    assert leaf.query.to_dict() == {"node_code": ["R_01_02", "R_01_99"]}


def test_codes_take_priority_over_pl_code():
    """При наличии codes query строится по node_code, а не по pl_code (name)."""
    tpl = _make_template_with_codes([
        (1, "Корень", NodeRole.PODSTATYA, None, []),
        (2, "Статья", NodeRole.PODSTATYA, 1, ["R_01_02"]),
    ])
    h = transform_template_lite_to_hierarchy(tpl)
    assert h.get_node(2).query.to_dict() == {"node_code": ["R_01_02"]}
    # pl_code по имени НЕ используется, когда есть codes.
    assert "pl_code" not in h.get_node(2).query.to_dict()


def test_single_code_query():
    """Одиночный node_code попадает в query списком из одного элемента."""
    tpl = _make_template_with_codes([
        (1, "Корень", NodeRole.PODSTATYA, None, []),
        (2, "Статья", NodeRole.PODSTATYA, 1, ["R_01_05_01"]),
    ])
    h = transform_template_lite_to_hierarchy(tpl)
    assert h.get_node(2).query.to_dict() == {"node_code": ["R_01_05_01"]}


def test_baza_with_codes_gets_node_code_query():
    """База (лист с componentMultiPartType) с codes получает node_code query."""
    tpl = _make_template_with_codes([
        (1, "Корень", NodeRole.PODSTATYA, None, []),
        (2, "Статья", NodeRole.PODSTATYA, 1, []),
        (3, "Маржа", NodeRole.TARIF, 2, []),
        (4, "СДО", NodeRole.BAZA, 2, ["R_01_05_01", "R_11_08_14"]),
    ])
    h = transform_template_lite_to_hierarchy(tpl)
    baza = h.get_node(4)
    assert baza.componentMultiPartType == ComponentMultiPartType.BASE
    assert baza.query.to_dict() == {"node_code": ["R_01_05_01", "R_11_08_14"]}


def test_multi_node_with_codes_uses_node_code():
    """MULTI-узел с codes получает node_code query (MULTI обязан иметь query)."""
    tpl = _make_template_with_codes([
        (1, "Корень", NodeRole.PODSTATYA, None, []),
        (2, "Статья", NodeRole.PODSTATYA, 1, ["R_multi"]),
        (3, "Маржа", NodeRole.TARIF, 2, []),
        (4, "СДО", NodeRole.BAZA, 2, []),
    ])
    h = transform_template_lite_to_hierarchy(tpl)
    multi = h.get_node(2)
    assert multi.type == MetricType.MULTI
    assert multi.query.to_dict() == {"node_code": ["R_multi"]}


def test_leaf_without_codes_still_uses_pl_code():
    """Без codes сохраняется прежнее поведение: query {'pl_code': name}."""
    tpl = _make_template([
        (1, "Корень", NodeRole.PODSTATYA, None),
        (2, "Листовая статья", NodeRole.PODSTATYA, 1),
    ])
    h = transform_template_lite_to_hierarchy(tpl)
    assert h.get_node(2).query.to_dict() == {"pl_code": "Листовая статья"}


def test_mixed_codes_and_no_codes_in_one_tree():
    """В одном дереве часть листьев с codes, часть без — query строятся раздельно."""
    tpl = _make_template_with_codes([
        (1, "Корень", NodeRole.PODSTATYA, None, []),
        (2, "С кодами", NodeRole.PODSTATYA, 1, ["R_01"]),
        (3, "Без кодов", NodeRole.PODSTATYA, 1, []),
    ])
    h = transform_template_lite_to_hierarchy(tpl)
    assert h.get_node(2).query.to_dict() == {"node_code": ["R_01"]}
    assert h.get_node(3).query.to_dict() == {"pl_code": "Без кодов"}


# ---------------------------------------------------------------------------
# mp_decomp_tp
# ---------------------------------------------------------------------------

def test_multi_node_default_decomp_tp():
    """По умолчанию MULTI-узлы получают mp_decomp_tp=DirectBase."""
    tpl = _make_template([
        (1, "Корень", NodeRole.PODSTATYA, None),
        (2, "Статья", NodeRole.PODSTATYA, 1),
        (3, "Маржа", NodeRole.TARIF, 2),
        (4, "СДО", NodeRole.BAZA, 2),
    ])
    h = transform_template_lite_to_hierarchy(tpl)
    assert h.get_node(2).mp_decomp_tp == MultipartDecompositionType.DIRECT_BASE


def test_multi_node_decomp_tp_is_overridable():
    """Тип декомпозиции MULTI можно переопределить параметром."""
    tpl = _make_template([
        (1, "Корень", NodeRole.PODSTATYA, None),
        (2, "Статья", NodeRole.PODSTATYA, 1),
        (3, "Маржа", NodeRole.TARIF, 2),
        (4, "СДО", NodeRole.BAZA, 2),
    ])
    h = transform_template_lite_to_hierarchy(
        tpl, mp_decomp_tp=MultipartDecompositionType.INTEGRAL
    )
    assert h.get_node(2).mp_decomp_tp == MultipartDecompositionType.INTEGRAL


def test_non_multi_nodes_have_no_decomp_tp():
    """Узлы не-MULTI не получают mp_decomp_tp."""
    tpl = _make_template([
        (1, "Корень", NodeRole.PODSTATYA, None),
        (2, "Лист", NodeRole.PODSTATYA, 1),
    ])
    h = transform_template_lite_to_hierarchy(tpl)
    assert h.get_node(1).mp_decomp_tp is None
    assert h.get_node(2).mp_decomp_tp is None


# ---------------------------------------------------------------------------
# Результирующая иерархия валидна и сериализуема
# ---------------------------------------------------------------------------

def test_resulting_hierarchy_is_valid(sample_template):
    """Построенная иерархия проходит полную валидацию Hierarchy."""
    h = transform_template_lite_to_hierarchy(sample_template)
    assert h.is_valid(), h.validate()


def test_hierarchy_roundtrip_preserves_structure(sample_template):
    """Round-trip to_json_string -> from_json_string сохраняет структуру,
    включая analyt_metadata."""
    h = transform_template_lite_to_hierarchy(sample_template)
    restored = Hierarchy.from_json_string(h.to_json_string())

    assert restored.count_nodes() == h.count_nodes()
    assert restored.is_valid()
    # analyt_metadata корня пережил сериализацию.
    root = restored.get_root()
    assert root.analyt_metadata is not None
    assert {d.name for d in root.analyt_metadata.dimensions.values()} == {"Разрез по ТБ"}


# ---------------------------------------------------------------------------
# End-to-end на реальных файлах
# ---------------------------------------------------------------------------

def test_real_files_produce_valid_hierarchy(template_lite_dir):
    """Каждый реальный сценарий преобразуется в валидную иерархию."""
    from adhoc_xxx.template_lite import get_from_template_lite_json

    for path in sorted(template_lite_dir.glob("*.json")):
        tpl = get_from_template_lite_json(str(path))
        h = transform_template_lite_to_hierarchy(tpl)
        assert h.is_valid(), f"{path.name}: {h.validate()}"
        # Корень сохраняет имя показателя.
        assert h.get_root().name == tpl.get_root().name
        # Разрезы схлопнуты: узлов меньше, чем в сценарии.
        assert h.count_nodes() == tpl.count_nodes() - len(tpl.get_razrez())


def test_real_file_od_bef_rez_specifics(template_lite_dir):
    """Известные факты о файле «операционный доход до резервов»."""
    from adhoc_xxx.template_lite import get_from_template_lite_json

    target = next(
        (p for p in template_lite_dir.glob("*.json") if "od_bef" in p.name.lower()),
        None,
    )
    if target is None:
        pytest.skip("Файл операционного дохода не найден")

    tpl = get_from_template_lite_json(str(target))
    h = transform_template_lite_to_hierarchy(tpl)

    # 72 узла сценария, 3 разреза → 69 узлов иерархии.
    assert h.count_nodes() == 69
    # Корень — SUM с двумя аналитическими разрезами.
    root = h.get_root()
    assert root.type == MetricType.SUM
    assert len(root.analyt_metadata.dimensions) == 2
    dim_names = {d.name for d in root.analyt_metadata.dimensions.values()}
    assert dim_names == {"ТБ/ГОСБ", "Блок/Подблок(Сегмент КИБ)"}
    # Оба разреза корня — один алгоритм с цепочкой drill_order из двух шагов
    # (порядок по id узла: «ТБ/ГОСБ» id=2, затем «Блок/Подблок(Сегмент КИБ)» id=3).
    assert len(root.analyt_metadata.algorithms) == 1
    root_algo = next(iter(root.analyt_metadata.algorithms.values()))
    assert root_algo.drill_order == [["ТБ/ГОСБ"], ["Блок/Подблок(Сегмент КИБ)"]]
    # Есть MULTI-узлы (пары Маржа/СДО), включая «Кредиты физлицам»,
    # чьи тариф/база были вложены под разрез «Продукт ЕК».
    multi_nodes = [n for n in h if n.type == MetricType.MULTI]
    assert len(multi_nodes) >= 7
