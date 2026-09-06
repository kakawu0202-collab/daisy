"""薄 LLM 客户端 — OpenAI 兼容 chat/completions + function calling。"""
import requests
from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, TIMEOUT


def chat(messages, tools=None):
    if not LLM_API_KEY:
        raise RuntimeError(
            '未找到 LLM API Key。请在 ai-engine/.env 写入（或设置环境变量）：\n'
            '  SN_API_KEY=<你的key>\n'
            '可选：SN_BASE_URL（默认 https://token.sensenova.cn/v1）、SN_MODEL（默认 sensenova-6.7-flash-lite）')
    url = LLM_BASE_URL.rstrip('/') + '/chat/completions'
    body = {'model': LLM_MODEL, 'messages': messages, 'temperature': 0}
    if tools:
        body['tools'] = tools
        body['tool_choice'] = 'auto'
    r = requests.post(url,
                      headers={'Authorization': f'Bearer {LLM_API_KEY}',
                               'Content-Type': 'application/json'},
                      json=body, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def assistant_text(resp):
    return (resp.get('choices') or [{}])[0].get('message', {}).get('content') or ''


def tool_calls(resp):
    return (resp.get('choices') or [{}])[0].get('message', {}).get('tool_calls') or []
