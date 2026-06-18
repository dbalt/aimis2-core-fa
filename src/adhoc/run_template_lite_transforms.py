
from adhoc.template_lite.deserializer import get_from_template_lite_json
from adhoc.template_lite.transform import transform_template_lite_to_hierarchy
from adhoc.template_lite.transform_queries import transform_next_step
from libfa2.hier_metadata.hierarchy import Hierarchy

from sdk.tools.settings import FileTools
from sdk.core.logging import get_logger




def main():
    lgr = get_logger()

    path = FileTools.path_concat(
        FileTools.home_path(),
        'source', 'repos', 'aimis2-core-fa-refac',
        'src', 'tmp', 'template_lite',
        'od_bef_rez_tb.json'
    )
    lgr.info(f'Запуск преобразования template_lite. Файл-источник: {path}')

    try:
        lgr.debug('Шаг 1/3: десериализация template_lite из JSON')
        data = get_from_template_lite_json(path)
        lgr.info(
            f'Шаг 1/3 завершён: получен TemplateLite '
            f'(metric_name={data.metric_name!r}, узлов={data.count_nodes()})'
        )

        lgr.debug('Шаг 2/3: преобразование TemplateLite -> Hierarchy')
        next_data = transform_template_lite_to_hierarchy(data)
        lgr.info(
            f'Шаг 2/3 завершён: построена Hierarchy '
            f'(узлов={len(next_data.nodes)})'
        )

        lgr.debug('Шаг 3/3: расчёт query-свойств узлов (transform_next_step)')
        next_data = transform_next_step(next_data)
        lgr.info('Шаг 3/3 завершён: query-свойства расставлены')

        lgr.info('Преобразование template_lite успешно завершено')
        return next_data
    except Exception:
        lgr.exception('Ошибка при выполнении преобразования template_lite')
        raise



if __name__ == '__main__':
    main()
