from libfa2.fa_impl.summarize import summarize

from sdk.giga.client import GigaChatClientPartV2
from sdk.tools.settings import FileTools

from adhoc_test_calc_dev import get_llm_client

import json


def get_tmp_path()->str:
    from pathlib import Path
    p = Path(__file__).parent
    return FileTools.path_concat(str(p.resolve()), '../tmp')


async def main():
    tmp_path = get_tmp_path()
    for x in FileTools.iterate_files(FileTools.path_concat(tmp_path, 'json')):
        try:
            print(f'==== Processing {x} ======')
            data = json.loads(FileTools.read_all_file_contents(x))
            sum_res = await summarize(data, get_llm_client)
            if not sum_res.ok:
                print(f'something wrong: {sum_res.err}')

            file_name = FileTools.file_name(x, False)
            tgt = FileTools.path_concat(tmp_path, 'reports', f'{file_name}.md')
            FileTools.write_to_file(tgt, sum_res.data)
            print(f'==== done: {x} ======')
        except Exception as e:
            print(repr(e))





if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
