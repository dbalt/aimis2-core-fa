from .units import DrillComponent, EnumDrillType
from typing import List, Dict
from sdk.core.tools import search_first_in_lst_or


def _has_negative_in_tree(dc: DrillComponent) -> bool:
    """
    Рекурсивно проверяет, есть ли в дереве DrillComponent хотя бы один
    компонент с отрицательным impact.

    Использует эвристику: impact < 0 (предполагает sign_negative_impact == -1,
    что является стандартным значением в проде).

    Args:
        dc: Корневой компонент поддерева для проверки.

    Returns:
        True, если в поддереве (включая сам корень) есть хотя бы один
        компонент с impact < 0. Иначе False.
    """
    if dc.amts.impact < 0:
        return True
    for drill in dc.drills:
        for component in drill.components:
            if _has_negative_in_tree(component):
                return True
    return False


def collect_for_summary(root_drill_component:DrillComponent)->Dict:

    data = {}
    map = {}

    # NOTE (known issue): map — мутатный общий словарь для всей рекурсии.
    # На глубоких уровнях ключи могут перезаписываться, если на разных
    # уровнях hier_ref.analyt_metadata содержит измерения с одинаковыми column.
    # На практике не влияет, т.к. analyt_metadata заполнен только для
    # корневых узлов иерархии (dc.hier_ref для листов обычно None).
    def _update_map_dim_names_to_columns(dc:DrillComponent):
        if dc.hier_ref.analyt_metadata:
            for dim in dc.hier_ref.analyt_metadata.dimensions.values():
                map[dim.column] = dim.name

    def _process_drill_component(dc:DrillComponent, d:Dict):
        _update_map_dim_names_to_columns(dc)

        d['hieararchy_node'] = dc.hier_ref.name

        # Добавляем flg_rate_type из метаданных иерархии (если задан)
        if dc.hier_ref.flg_rate_type is not None:
            d['flg_rate_type'] = dc.hier_ref.flg_rate_type

        if dc.analyt_struct:
            analyt_slice = {map.get(k, k):v for (k,v) in dc.analyt_struct.items()}
            d['analytic_slice'] = analyt_slice

        d['amounts'] = dc.amts.as_dict_for_summary()

        if len(dc.drills) > 0:
            drill = dc.drills[0]

            # Проверяем: есть ли негатив в детализации (в поддереве)
            has_negative = _has_negative_in_tree(dc)

            if has_negative:
                # Ветка содержит негатив — включаем полную детализацию
                det = {}
                d['details'] = det

                if drill.drill_type == EnumDrillType.HIER:
                    det['type'] = 'Детализация по компонентам иерархии'
                else:
                    s = [f'[{map.get(x, x)}]' for x in drill.analyt_slice]
                    s = ' + '.join(s)
                    s = f'Детализация по: {s}'
                    det['type'] = s

                det['deviation_amounts'] = drill.detail_amts.as_dict_for_summary()
                tf = []
                det['top_factors'] = tf

                for x in drill.components:
                    xd = {}
                    tf.append(xd)
                    _process_drill_component(x, xd)
            # else: has_negative=False → ветка без негатива, details НЕ включаем

    _process_drill_component(root_drill_component, data)

    return data