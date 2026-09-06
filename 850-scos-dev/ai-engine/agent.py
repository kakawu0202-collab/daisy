"""Agent — 自然语言 → function calling → Service Layer → 中文答案（附数据更新时间）。"""
import json
import llm
from config import MAX_TOOL_ITERS
from tools import TOOLS, execute

SYSTEM = """你是 850 SCOS 供应链系统的数据助手。你只能通过提供的工具查询数据。
硬性规则：
1. 回答任何数据问题前，必须先调用工具查询。禁止凭记忆或猜测编造数字——没有工具结果就没有答案。
2. 只回答数据能支撑的问题；查不到就明说，不要猜。
3. 统计类问题（总量/笔数/百分比）优先用汇总工具（get_k1_summary/get_daily_summary/get_kpi/get_risks 等）。
   例如"NACK 多少笔"用 get_daily_summary 的 nack_count 字段；明细下钻才用 query_orders/get_nack_orders
   （明细默认最多返回 50 条，总数看 total 字段）。
4. 回答用简洁中文，给出数字和口径说明（例如"非 CTO P1 口径"）。
5. 回答末尾不要自己写数据更新时间——系统会自动附加，你只管给数字和结论。
6. 口径常识：NACK=ack_status=REJECT；CTO P1=cto_p1=Y；MSBD 出货卡片不含 CTO P1；RTL 无 GPP 生产数据属正常现象。
7. 单位口径：K1/日报里的数字都是件数(pcs)。用户问"笔数/单数/订单数"时，必须用 query_orders 或 get_nack_orders 返回的 total 字段（记录条数），严禁把件数当笔数回答。
8. 所有数量必须带单位，用英文 pcs 或中文「台」（如「5,975 pcs」或「5,975 台」）；禁止只写裸数字。"""


def ask(question, debug=False):
    messages = [
        {'role': 'system', 'content': SYSTEM},
        {'role': 'user', 'content': question},
    ]
    last_at = ''
    tool_used = False
    last_text = ''
    for i in range(MAX_TOOL_ITERS):
        resp = llm.chat(messages, tools=TOOLS)
        calls = llm.tool_calls(resp)
        if debug:
            print(f"[iter {i}] finish_reason={resp['choices'][0].get('finish_reason')} tool_calls={len(calls)}")
        if not calls:
            last_text = llm.assistant_text(resp)
            if not tool_used and last_text:
                # 模型没查数据就想回答——强制它查一次
                messages.append({'role': 'assistant', 'content': last_text})
                messages.append({'role': 'user', 'content': '你刚才没有调用工具查询数据。必须调用工具获取真实数据后再回答，禁止编造数字。'})
                continue
            break
        tool_used = True
        messages.append(resp['choices'][0]['message'])
        for c in calls:
            fn = c['function']
            name, args = fn['name'], json.loads(fn.get('arguments') or '{}')
            if debug:
                print(f'[iter {i}] → {name}({args})')
            try:
                data, at = execute(name, args)
                last_at = at or last_at
                content = json.dumps(data, ensure_ascii=False, default=str)
            except Exception as e:
                content = json.dumps({'error': str(e)}, ensure_ascii=False)
            messages.append({'role': 'tool', 'tool_call_id': c['id'], 'content': content})
    if not tool_used:
        return f'⚠️ 模型未调用任何数据工具，回答不可信（已拦截）。模型原话：{last_text or "（空）"}'
    if not last_text:
        return '（模型未返回答案，请换个问法）'
    return last_text + (f'\n\n数据更新时间：{last_at}' if last_at else '')
