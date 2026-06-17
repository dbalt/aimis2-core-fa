
from adhoc.template_lite.deserializer import get_from_template_lite_json
from adhoc.template_lite.transform import transform_template_lite_to_hierarchy
from adhoc.template_lite.transform_queries import transform_next_step
from libfa2.hier_metadata.hierarchy import Hierarchy

from sdk.tools.settings import FileTools





def main():
    path = FileTools.path_concat(
        FileTools.home_path(),
        'source', 'repos', 'aimis2-core-fa-refac',
        'src', 'tmp', 'template_lite',
        'od_bef_rez_tb.json'
    )
    data = get_from_template_lite_json(path)
    print(data)

    next_data = transform_template_lite_to_hierarchy(data)
    next_data = transform_next_step(next_data)
    print(next_data)



if __name__ == '__main__':
    main()