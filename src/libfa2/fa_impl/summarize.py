
from sdk.giga.client import GigaChatClientPartV2, DEFAULT_GIGA_MODEL
from sdk.giga.iface import MsgBase, AssistantMsg
from sdk.core.monadic import Res
from sdk.core.tools import cast

from typing import Dict, List

import json

async def summarize(data: Dict, llm_client:GigaChatClientPartV2, llm_model:str = 'GigaChat-3-Ultra')->Res[str]:
    system_prompt = '''
В пользовательском вводе ты получишь данные по факторному анализу отклонения факта от плана определенного финансового показателя в формате JSON. Ввод будет по шаблону "data:<json строка>"

Изучи данные, разберись в структуре и сформируй лаконичное саммари об отклонениях в целом. 
Выдели top 5 отклонений среди всех остальных, и дай по ним информацию, в том числе с разбивкой по аналитическим разрезам (если возможно) 
'''
    system_prompt = MsgBase.system_prompt(system_prompt)

    usr_msg = f'data:{json.dumps(data, ensure_ascii=False)}'
    usr_msg = MsgBase.user_msg(usr_msg)


    resp:Res[MsgBase] = await llm_client.ask_giga(
        msgs = [system_prompt, usr_msg],
        model=llm_model
    )

    if not resp.ok:
        return Res.mk_error(resp.err)

    answer:MsgBase = resp.data

    if answer.role != 'assistant':
        return Res.mk_error(f'Unexpected answer from llm: {answer}')

    assistant_answer:AssistantMsg = answer

    text = assistant_answer.message

    return Res.mk_result(text)




