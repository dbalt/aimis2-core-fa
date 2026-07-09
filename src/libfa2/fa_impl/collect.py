from .units import DrillComponent, EnumDrillType
from typing import List, Dict
from sdk.core.tools import search_first_in_lst_or


def collect_for_summary(root_drill_component:DrillComponent)->Dict:

    data = {}
    map = {}

    def _update_map_dim_names_to_columns(dc:DrillComponent):
        if dc.hier_ref.analyt_metadata:
            for dim in dc.hier_ref.analyt_metadata.dimensions.values():
                map[dim.column] = dim.name

    def _get_component_type(dc:DrillComponent) -> str | None:
        """
        Определяет тип компонента на основе метаданных узла иерархии.
        Возвращает: 'rate', 'base', 'ratio_num', 'ratio_den' или None
        """
        if dc.hier_ref.componentMultiPartType:
            return dc.hier_ref.componentMultiPartType.value
        if dc.hier_ref.componentRatioPartType:
            return dc.hier_ref.componentRatioPartType.value
        return None

    def _process_drill_component(dc:DrillComponent, d:Dict):
        _update_map_dim_names_to_columns(dc)

        d['hieararchy_node'] = dc.hier_ref.name

        if dc.analyt_struct:
            analyt_slice = {map.get(k, k):v for (k,v) in dc.analyt_struct.items()}
            d['analytic_slice'] = analyt_slice

        # Добавляем тип компонента (rate/base/ratio_num/ratio_den) если есть
        comp_type = _get_component_type(dc)
        if comp_type:
            d['amount_type'] = comp_type

        d['amounts'] = dc.amts.as_dict_for_summary()

        if len(dc.drills) > 0:
            # at now, it can be not more than one drill
            drill = dc.drills[0]
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

    _process_drill_component(root_drill_component, data)

    return data