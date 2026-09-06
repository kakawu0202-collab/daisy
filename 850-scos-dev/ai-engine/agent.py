"""Agent — 自然语言 → function calling → Service Layer → 中文答案（附数据更新时间）。"""
import json
import llm
from config import MAX_TOOL_ITERS
from tools import TOOLS, execute

SYSTEM = """你是 850 SCOS 供应链系统的数据助手。你只能通过提供的工具查询数据，禁止编造数字。
规则：
1. 只回答数据能支撑的问题；查不到就明说，不要猜。
2. 统计类问题（总量/笔数/百分比）优先用汇总工具（get_k1_summary/get_daily_summary/get_kpi/get_risks 等），
   不要拉全量订单明细自己数。
3. 回答用简洁中文，给出数字和口径说明（例如"非 CTO P1 口径"）。
4. 回答末尾必须附一行「数据更新时间：<工具结果里的 computed_at>」（没有 computed_at 就用系统给的 last_sync_time）。
5. 口径常识：NACK=ack_status=REJECT；CTO P1=cto_p1=Y；MSBD 出货卡片不含 CTO P1；RTL 无 GPP 生产数据属正常现象。"""


def ask(question):
    messages = [
        {'role': 'system', 'content': SYSTEM},
        {'role': 'user', 'content': question},
    ]
    last_at = ''
    for _ in range(MAX_TOOL_ITERS):
        resp = llm.chat(messages, tools=TOOLS)
        calls = llm.tool_calls(resp)
        if not calls:
            text = llm.assistant_text(resp)
            if not text:
                return '（模型未返回答案，请换个问法）'
            return text + (f'\n\n数据更新时间：{last_at}' if last_at else '')
        messages.append(resp['choices'][0]['message'])
        for c in calls:
            fn = c['function']
            name, args = fn['name'], json.loads(fn.get('arguments') or '{}')
            try:
                data, at = execute(name, args)
                last_at = at or last_at
                content = json.dumps(data, ensure_ascii=False, default=str)
            except Exception as e:
                content = json.dumps({'error': str(e)}, ensure_ascii=False)
            messages.append({'role': 'tool', 'tool_call_id': c['id'], 'content': content})
    return '（多次工具调用后仍无法回答，请换个问法）'
