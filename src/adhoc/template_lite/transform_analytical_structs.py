from libfa2.hier_metadata.hierarchy import MetricNode, MetricType, Hierarchy
from libfa2.analyt_struct_metadata import AnalyticalStructureMetadata, Algorithm, Dimension
from sdk.core.logging import get_logger

dim_tb = Dimension('tb', 'ТБ', 'tb')
dim_gosb = Dimension('gosb', 'ГОСБ', 'gosb')
dim_bb = Dimension('bb', 'Бизнес блок', 'biz_block')

_SETUP = {
    'ТБ/ГОСБ': (('tb', 'gosb',), (dim_tb, dim_gosb,),),
    'Блок/Подблок(Сегмент КИБ)': (('bb',), (dim_bb,)),
}

def transform_analytical_structs(hier:Hierarchy)->Hierarchy:

    lgr = get_logger()

    root = hier.get_root()

    def _process_node(node:MetricNode):
        if node.analyt_metadata:
            # we have to change it based on drill orders
            drills = []
            dims = []
            for x in node.analyt_metadata.algorithms[1].drill_order:
                x = x[0]
                if not x in _SETUP.keys():
                    lgr.warning(f'No {x} in _SETUP !!!')
                    continue

                (new_drills, new_dims) = _SETUP[x]
                drills.extend([[x] for x in new_drills])
                dims.extend(new_dims)

            new_analyt_metadata = AnalyticalStructureMetadata()
            new_analyt_metadata.add_dimensions(dims)
            new_analyt_metadata.add_algorithm(
                Algorithm(1, drills)
            )
            node.analyt_metadata = new_analyt_metadata

        for chld_node in hier.get_children(node.id):
            _process_node(chld_node)

    _process_node(root)
    return hier


