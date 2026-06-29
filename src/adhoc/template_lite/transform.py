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
   неразрезный) ``MetricNode`` добавляется ``AnalyticalStructureMetadata``, где
   все разрезы этого показателя образуют **один** алгоритм с цепочкой шагов в
   ``drill_order`` (по одному измерению на разрез); все наименования берутся из
   поля ``name``.
2. ``role == NodeRole.PODSTATYA`` у потомка означает ``type=MetricType.SUM`` у
   родителя; ``role`` в ``{TARIF, BAZA}`` — ``type=MetricType.MULTI`` у родителя,
   а сам узел получает ``componentMultiPartType`` (``RATE`` для тарифа, ``BASE``
   для базы).
3. Листовые ``MetricNode`` (``type is None``) и ``MetricNode`` с
   ``type=MetricType.MULTI`` получают ``query`` вида ``{'pl_code': <name>}``.
   Если у узла-источника заполнено поле ``codes`` (составные коды
   ``"<type_code>#<node_code>"`` из ``upr_cube_codes``), вместо ``pl_code``
   используется точный ключ запроса ``{'node_code': <codes>}``.
"""

from typing import Dict, List, Optional

from sdk.core.logging import get_logger

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
from .node import NODE_CODE_KEY
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

    lgr = get_logger()
    lgr.info(
        f"Старт преобразования: metric_name={template_lite.metric_name!r}, "
        f"узлов={template_lite.count_nodes()}, "
        f"mp_decomp_tp={mp_decomp_tp}"
    )

    nodes = template_lite.nodes  # Dict[int, TemplateLiteNode]

    # --- 1. Ближайший неразрезный предок («эффективный родитель») -------
    # Для разреза — это целевой MetricNode, куда пойдут его analyt_metadata.
    # Для неразрезного узла — это id родительского MetricNode в итоговом дереве
    # (поддерево разреза «подтягивается» на уровень его неразрезного предка).
    def _nearest_metric_ancestor(node_id: int) -> Optional[int]:
        lgr.debug(f"Поиск ближайшего неразрезного предка для node_id={node_id}")
        node = nodes.get(node_id)
        if node is None:
            lgr.warning(f"Узел {node_id} не найден в сценарии при поиске предка")
            return None
        current = node.parent
        while current is not None:
            current_node = nodes.get(current)
            if current_node is None:
                lgr.warning(
                    f"Цепочка parent обрывается: узел {current} не найден "
                    f"(при поиске предка для {node_id})"
                )
                return None
            if current_node.role != NodeRole.RAZREZ:
                lgr.debug(f"Неразрезный предок для {node_id}: {current}")
                return current
            current = current_node.parent
        lgr.debug(f"Неразрезный предок для {node_id} не найден (достигнут корень-разрез)")
        return None

    # --- 2. Узлы, становящиеся MetricNode (все, кроме разрезов) ---------
    metric_ids: List[int] = [
        nid for nid, n in nodes.items() if n.role != NodeRole.RAZREZ
    ]
    razrez_count = len(nodes) - len(metric_ids)
    lgr.info(
        f"Узлов-метрик: {len(metric_ids)}, узлов-разрезов (схлопываются): {razrez_count}"
    )

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
            lgr.warning(
                f"Разрез id={nid} name={node.name!r} без неразрезного предка — "
                f"пропускается"
            )
            continue
        razrez_by_target.setdefault(target, []).append(node.name)

    # --- 5. Сборка MetricNode -------------------------------------------
    lgr.info("Сборка MetricNode для каждого узла-метрики")
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

        lgr.debug(
            f"Узел id={nid} name={node.name!r} role={node.role.value} -> "
            f"metric_type={metric_type}"
        )

        # componentMultiPartType — для самих тарифов/баз (правило 2).
        if node.role == NodeRole.TARIF:
            component_multi_part_type = ComponentMultiPartType.RATE
        elif node.role == NodeRole.BAZA:
            component_multi_part_type = ComponentMultiPartType.BASE
        else:
            component_multi_part_type = None

        # query (правило 3 + приоритетное правило для codes).
        # Если у узла есть коды узлов куба (codes — составные коды вида
        # "<type_code>#<node_code>") — используем их как точный ключ запроса:
        # Query({'node_code': codes}). Это применимо к любому элементу с непустым
        # codes (листьям, тарифам/базам, а при наличии — и к MULTI/SUM). Иначе —
        # прежняя логика: pl_code для листьев и MULTI.
        # (Показатели типа ratio в template_lite отсутствуют, поэтому исключение
        # «кроме ratio» из правила не применимо и ни одного узла не исключает.)
        if node.codes:
            query: Optional[Query] = Query({NODE_CODE_KEY: node.codes})
            lgr.debug(
                f"Узел id={nid} name={node.name!r}: query по codes "
                f"({len(node.codes)} шт. составных кодов type_code#node_code)"
            )
        elif metric_type == MetricType.MULTI or metric_type is None:
            query = Query({PL_CODE_KEY: node.name})
        else:
            query = None

        # analyt_metadata — из сгруппированных разрезов (правило 1):
        # все разрезы этого показателя попадают в один алгоритм с цепочкой
        # шагов drill_order (None, если разрезов нет).
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

    lgr.info(
        f"Преобразование завершено: MetricNode построено={len(metric_ids)}, "
        f"разрезов распределено по метрикам={sum(len(v) for v in razrez_by_target.values())}"
    )
    return hierarchy


def _build_analyt_metadata(
    razrez_names: Optional[List[str]],
) -> Optional[AnalyticalStructureMetadata]:
    """
    Построить ``AnalyticalStructureMetadata`` по списку имён разрезов.

    Все разрезы попадают в **один** алгоритм (``Algorithm``), образуя цепочку
    шагов детализации в его ``drill_order`` (один шаг на разрез, в порядке
    исходного сценария). Каждый разрез даёт ровно одно измерение (``Dimension``);
    наименования (``code``, ``name``, ``column``) берутся из имени разреза. При
    совпадении имён к ``code``/``column`` добавляется числовой суффикс, чтобы
    избежать коллизий кодов измерений в пределах одного узла.

    Семантика: несколько разрезов одного показателя — это одна
    последовательность детализации (один порядок разложения), а не несколько
    независимых алгоритмов (см. ``factor_analysis__general_description.md``,
    раздел «Разложение по аналитическим разрезам» — «Порядок разложения»).

    Args:
        razrez_names: Упорядоченный список имён разрезов (поле ``name``)
            либо ``None``/пустой список.

    Returns:
        Готовая ``AnalyticalStructureMetadata`` либо ``None``, если разрезов нет.
    """
    lgr = get_logger()

    if not razrez_names:
        lgr.debug("Список разрезов пуст — analyt_metadata не строится")
        return None

    lgr.debug(f"Построение analyt_metadata по разрезам: {razrez_names}")

    metadata = AnalyticalStructureMetadata()
    codes: List[str] = []
    for name in razrez_names:
        code = _unique_dimension_code(metadata, name)
        metadata.add_dimension(Dimension(code=code, name=name, column=name))
        codes.append(code)

    # Все разрезы — один порядок разложения, поэтому один алгоритм с цепочкой
    # шагов в drill_order (по одному коду измерения на шаг, в порядке разрезов).
    drill_order: List[List[str]] = [[code] for code in codes]
    metadata.add_algorithm(Algorithm(id=1, drill_order=drill_order))

    lgr.info(
        f"Сгруппировано разрезов: {len(razrez_names)} -> построен один алгоритм "
        f"с drill_order из {len(drill_order)} шагов"
    )
    lgr.debug(
        f"analyt_metadata построена: измерений={len(metadata.dimensions)}, "
        f"алгоритмов={len(metadata.algorithms)}, drill_order={drill_order}"
    )
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
    code = f"{name}_{suffix}"
    lgr = get_logger()
    lgr.warning(
        f"Код измерения {name!r} уже занят — использован уникальный код {code!r}"
    )
    return code
