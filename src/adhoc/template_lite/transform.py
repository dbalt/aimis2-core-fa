"""
Трансформация упрощённого шаблона сценария (TemplateLite) в метаданные
иерархии показателей (Hierarchy).

Модуль реализует функцию :func:`transform_template_lite_to_hierarchy`, которая
развёртывает «lite»-сценарий обхода данных в полноценную иерархию метрик
факторного анализа (:mod:`libfa2.hier_metadata`) с метаданными аналитических
разрезов (:mod:`libfa2.analyt_struct_metadata`).

Правила отображения (см. задачу ``27_transform_logic.md``):

1. Узел с ``role == NodeRole.RAZREZ`` — это описание аналитического разреза.
   Он **не** становится отдельным ``MetricNode``: в его родительский (ближайший
   неразрезный) ``MetricNode`` добавляется ``AnalyticalStructureMetadata`` с
   одним алгоритмом и одним измерением; все наименования берутся из поля ``name``.
2. ``role == NodeRole.PODSTATYA`` у потомка означает ``type=MetricType.SUM`` у
   родителя; ``role`` в ``{TARIF, BAZA}`` — ``type=MetricType.MULTI`` у родителя,
   а сам узел получает ``componentMultiPartType`` (``RATE`` для тарифа, ``BASE``
   для базы).
3. Листовые ``MetricNode`` (``type is None``) и ``MetricNode`` с
   ``type=MetricType.MULTI`` получают ``query`` вида ``{'pl_code': <name>}``.
"""

from typing import Dict, List, Optional

from libfa2.analyt_struct_metadata import (
    Algorithm,
    AnalyticalStructureMetadata,
    Dimension,
)
from libfa2.hier_metadata import (
    ComponentMultiPartType,
    Hierarchy,
    MetricNode,
    MetricType,
    MultipartDecompositionType,
    Query,
)

from .enums import NodeRole
from .template import TemplateLite

#: Ключ параметра запроса, в который кладётся имя статьи-источника.
PL_CODE_KEY = "pl_code"

#: Тип декомпозиции MULTI по умолчанию — метод цепных подстановок
#: (влияние базы считается прямым счётом, влияние ставки — обратным).
#: Соответствует документу ``algo__chain_substs_method.md``.
DEFAULT_MULTI_DECOMP_TP = MultipartDecompositionType.DIRECT_BASE


def transform_template_lite_to_hierarchy(
    template_lite: TemplateLite,
    *,
    mp_decomp_tp: MultipartDecompositionType = DEFAULT_MULTI_DECOMP_TP,
) -> Hierarchy:
    """
    Преобразовать упрощённый шаблон сценария в иерархию показателей.

    Узлы-разрезы (``NodeRole.RAZREZ``) не создают собственных ``MetricNode``:
    они «схлопываются», добавляя аналитический разрез в ближайший неразрезный
    предок, а их поддерево подтягивается на уровень этого предка. Это
    необходимо для построения корректного дерева ``Hierarchy`` (без висящих
    ссылок на parent), так как в исходных сценариях разрезы нередко содержат
    собственное поддерево статей.

    Args:
        template_lite: Объект :class:`TemplateLite` — разобранный «lite»-сценарий.
        mp_decomp_tp: Тип декомпозиции для показателей ``MULTI``. По умолчанию
            :attr:`DEFAULT_MULTI_DECOMP_TP` (``DirectBase``). Используется, так
            как модель ``MetricNode`` требует ``mp_decomp_tp`` для ``MULTI``.

    Returns:
        Построенная :class:`~libfa2.hier_metadata.Hierarchy`.

    Raises:
        TypeError: если ``template_lite`` не является экземпляром :class:`TemplateLite`.

    Example:
        >>> from adhoc.template_lite import (
        ...     get_from_template_lite_json,
        ...     transform_template_lite_to_hierarchy,
        ... )
        >>> tpl = get_from_template_lite_json("src/tmp/template_lite/чкд+_тб_business_lite.json")
        >>> hierarchy = transform_template_lite_to_hierarchy(tpl)
        >>> hierarchy.is_valid()
        True
        >>> hierarchy.get_root().name
        'ЧКД+ ТБ'
    """
    if not isinstance(template_lite, TemplateLite):
        raise TypeError(
            f"Ожидался TemplateLite, получен {type(template_lite).__name__}"
        )

    nodes = template_lite.nodes  # Dict[int, TemplateLiteNode]

    # --- 1. Ближайший неразрезный предок («эффективный родитель») -------
    # Для разреза — это целевой MetricNode, куда пойдут его analyt_metadata.
    # Для неразрезного узла — это id родительского MetricNode в итоговом дереве
    # (поддерево разреза «подтягивается» на уровень его неразрезного предка).
    def _nearest_metric_ancestor(node_id: int) -> Optional[int]:
        node = nodes.get(node_id)
        if node is None:
            return None
        current = node.parent
        while current is not None:
            current_node = nodes.get(current)
            if current_node is None:
                return None
            if current_node.role != NodeRole.RAZREZ:
                return current
            current = current_node.parent
        return None

    # --- 2. Узлы, становящиеся MetricNode (все, кроме разрезов) ---------
    metric_ids: List[int] = [
        nid for nid, n in nodes.items() if n.role != NodeRole.RAZREZ
    ]

    # --- 3. Эффективные дети (по ролям) для определения типа ------------
    # eff_children_roles[parent_id] — роли неразрезных потомков, чьим
    # ближайшим неразрезным предком является parent_id.
    eff_children_roles: Dict[int, List[NodeRole]] = {nid: [] for nid in metric_ids}
    for nid in metric_ids:
        ancestor = _nearest_metric_ancestor(nid)
        if ancestor is not None:
            eff_children_roles[ancestor].append(nodes[nid].role)

    # --- 4. Группировка разрезов по целевому MetricNode -----------------
    # razrez_by_target[parent_id] — упорядоченный список имён разрезов (name),
    # относящихся к данному MetricNode. Порядок детерминирован (по id узла).
    razrez_by_target: Dict[int, List[str]] = {}
    for nid in sorted(nodes):
        node = nodes[nid]
        if node.role != NodeRole.RAZREZ:
            continue
        target = _nearest_metric_ancestor(nid)
        if target is None:
            # Разрез без неразрезного предка (корень-разрез) — невозможен,
            # т.к. корень сценария обязан быть подстатьей. На всякий случай
            # пропускаем, чтобы не сломать сборку.
            continue
        razrez_by_target.setdefault(target, []).append(node.name)

    # --- 5. Сборка MetricNode -------------------------------------------
    hierarchy = Hierarchy()
    for nid in metric_ids:
        node = nodes[nid]
        child_roles = set(eff_children_roles[nid])

        # Тип показателя определяется по ролям эффективных потомков (правило 2).
        if NodeRole.TARIF in child_roles or NodeRole.BAZA in child_roles:
            metric_type = MetricType.MULTI
        elif NodeRole.PODSTATYA in child_roles:
            metric_type = MetricType.SUM
        else:
            metric_type = None  # листовой элемент

        # componentMultiPartType — для самих тарифов/баз (правило 2).
        if node.role == NodeRole.TARIF:
            component_multi_part_type = ComponentMultiPartType.RATE
        elif node.role == NodeRole.BAZA:
            component_multi_part_type = ComponentMultiPartType.BASE
        else:
            component_multi_part_type = None

        # query — для листьев и MULTI (правило 3).
        # (Показатели типа ratio в template_lite отсутствуют, поэтому исключение
        # «кроме ratio» из правила не применимо и ни одного узла не исключает.)
        if metric_type == MetricType.MULTI or metric_type is None:
            query: Optional[Query] = Query({PL_CODE_KEY: node.name})
        else:
            query = None

        # analyt_metadata — из сгруппированных разрезов (правило 1).
        analyt_metadata = _build_analyt_metadata(razrez_by_target.get(nid))

        # mp_decomp_tp обязателен для MULTI в модели MetricNode.
        decomp_tp = mp_decomp_tp if metric_type == MetricType.MULTI else None

        metric_node = MetricNode(
            id=node.id,
            code=node.name,
            name=node.name,
            type=metric_type,
            parent=_nearest_metric_ancestor(nid),
            query=query,
            componentMultiPartType=component_multi_part_type,
            componentRatioPartType=None,
            analyt_metadata=analyt_metadata,
            mp_decomp_tp=decomp_tp,
        )
        hierarchy.add_node(metric_node)

    return hierarchy


def _build_analyt_metadata(
    razrez_names: Optional[List[str]],
) -> Optional[AnalyticalStructureMetadata]:
    """
    Построить ``AnalyticalStructureMetadata`` по списку имён разрезов.

    Каждый разрез даёт ровно одно измерение (``Dimension``) и один алгоритм
    (``Algorithm``) с ``drill_order=[[<code>]]``. Наименования (``code``,
    ``name``, ``column``) берутся из имени разреза. При совпадении имён к
    ``code``/``column`` добавляется числовой суффикс, чтобы избежать коллизий
    кодов измерений в пределах одного узла.

    Args:
        razrez_names: Упорядоченный список имён разрезов (поле ``name``)
            либо ``None``/пустой список.

    Returns:
        Готовая ``AnalyticalStructureMetadata`` либо ``None``, если разрезов нет.
    """
    if not razrez_names:
        return None

    metadata = AnalyticalStructureMetadata()
    for index, name in enumerate(razrez_names, start=1):
        code = _unique_dimension_code(metadata, name)
        metadata.add_dimension(Dimension(code=code, name=name, column=name))
        metadata.add_algorithm(Algorithm(id=index, drill_order=[[code]]))
    return metadata


def _unique_dimension_code(metadata: AnalyticalStructureMetadata, name: str) -> str:
    """
    Вернуть незанятый код измерения на основе ``name``.

    Если ``name`` уже используется как код измерения в ``metadata``, к нему
    последовательно добавляются суффиксы ``_2``, ``_3``, ... до получения
    уникального кода.
    """
    if name not in metadata.dimensions:
        return name
    suffix = 2
    while f"{name}_{suffix}" in metadata.dimensions:
        suffix += 1
    return f"{name}_{suffix}"
