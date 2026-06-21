
from adhoc.template_lite.deserializer import get_from_template_lite_json
from adhoc.template_lite.transform import transform_template_lite_to_hierarchy
from adhoc.template_lite.transform_queries import transform_next_step
from adhoc.template_lite.transform_analytical_structs import transform_analytical_structs
from libfa2.hier_metadata.hierarchy import Hierarchy, MetricNode

from sdk.tools.settings import FileTools
from sdk.core.logging import get_logger

import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] {%(pathname)s:%(lineno)d} %(name)s %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)


class YoTreeNode:
    def __init__(self, payload):
        self.payload = payload
        self.children = []
        self.parent = None

    def add_child(self, child:'YoTreeNode'):
        if child in self.children: return
        child.parent = self
        self.children.append(child)

    @property
    def is_root(self)->bool:
        return self.parent is None

    @property
    def is_leaf(self)->bool:
        return len(self.children) == 0

    def __str__(self):
        return f'@ {str(self.payload)} @'


def main():
    lgr = get_logger()

    path = FileTools.path_concat(
        FileTools.home_path(),
        'source', 'repos', 'aimis2-core-fa-refac',
        'src', 'tmp', 'template_lite',
        'tmp.json'
    )
    lgr.info(f'Запуск преобразования template_lite. Файл-источник: {path}')

    try:
        lgr.debug('Шаг 1/4: десериализация template_lite из JSON')
        data = get_from_template_lite_json(path)
        lgr.info(
            f'Шаг 1/4 завершён: получен TemplateLite '
            f'(metric_name={data.metric_name!r}, узлов={data.count_nodes()})'
        )

        lgr.debug('Шаг 2/4: преобразование TemplateLite -> Hierarchy')
        next_data = transform_template_lite_to_hierarchy(data)
        lgr.info(
            f'Шаг 2/4 завершён: построена Hierarchy '
            f'(узлов={len(next_data.nodes)})'
        )

        lgr.debug('Шаг 3/4: расчёт query-свойств узлов (transform_next_step)')
        next_data:Hierarchy = transform_next_step(next_data)
        lgr.info('Шаг 3/4 завершён: query-свойства расставлены')


        lgr.debug('Шаг 4/4: трансформация аналитических метаданных')
        next_data:Hierarchy = transform_analytical_structs(next_data)
        lgr.info('Шаг 4/4 завершён: новые analyt metadata')


        lgr.info('Преобразование template_lite успешно завершено')

        def _process_tree_node(node: YoTreeNode):
            mnode = node.payload
            if mnode.query:
                print(f'query:{mnode.query} for node {mnode}')
            for mchld in next_data.get_children(mnode.id):
                chld = YoTreeNode(mchld)
                node.add_child(chld)
                _process_tree_node(chld)

        root = next_data.get_root()
        _tree_root = YoTreeNode(root)
        _process_tree_node(_tree_root)
        print('stop')

        return next_data
    except Exception:
        lgr.exception('Ошибка при выполнении преобразования template_lite')
        raise







if __name__ == '__main__':
    main()
