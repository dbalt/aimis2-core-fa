from copy import deepcopy

from libfa2.hier_metadata.hierarchy import Hierarchy, MetricNode, Query

def split_to_motiv_adj(h:Hierarchy)->Hierarchy:
    """ Нужно сделать новый root, с именем как у текущего.
        Нужно переименовать текущий root (добавить типа без мотивационной корректировки) и подвязать его к новому
        Нужно сделать лист мотивационная корректировка с бабблед query
    """
    from adhoc.run_template_lite_transforms import bubble_and_reduce_query_to_top

    top_query = bubble_and_reduce_query_to_top(h)

    old_root = h.get_root()

    src_name = old_root.name

    new_root = MetricNode.from_dict(old_root.to_dict())
    new_root.analyt_metadata = None
    new_root.id = -100
    new_root.parent = None
    new_root.name = src_name
    old_root.code = f'{old_root.code}_no_madj'
    old_root.name = f'{src_name} без учета мотивационной корректировки'
    old_root.parent = new_root.id
    old_root.force_drill = True

    h.add_node(new_root)


    new_query = deepcopy(top_query)
    new_query['flg_correction'] = 1

    motiv_corr = MetricNode(
        id = -200,
        name = 'Мотивационная корректировка',
        code = 'madj',
        parent=new_root.id,
        query=Query(new_query)
    )
    h.add_node(motiv_corr)

    # from adhoc.run_template_lite_transforms import mk_custom_tree
    # t = mk_custom_tree(h)

    return h

