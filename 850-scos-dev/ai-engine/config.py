"""AI Engine 配置 — SCOS 服务基址 + LLM 凭据（环境变量或 .env，绝不硬编码）。"""
import os
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _load_dotenv():
    """按序加载 .env：ai-engine/.env → 850-scos-dev/.env → skills/.env（已存在的环境变量优先）。"""
    for cand in (_HERE / '.env', _HERE.parent / '.env',
                 Path.home() / '.claude' / 'skills' / '.env'):
        if cand.exists():
            for line in cand.read_text(encoding='utf-8', errors='ignore').splitlines():
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, _, v = line.partition('=')
                    os.environ.setdefault(k.strip(), v.strip())


_load_dotenv()  # 必须先加载 .env，再读下面的配置

# SCOS Service Layer（AI 唯一数据入口）
API_BASE = os.environ.get('SCOS_API_BASE', 'http://localhost:5051')


def _env(*names, default=''):
    for n in names:
        v = os.environ.get(n, '').strip()
        if v:
            return v
    return default


# Service Layer 登录（全站认证后的服务账号）
AI_USER = _env('SCOS_AI_USER', 'ai-bot')
AI_PASSWORD = _env('SCOS_AI_PASSWORD', '')

# LLM 凭据（AI_* 优先，回退 SenseNova 的 SN_*，与 sn-ppt 技能族同约定）
LLM_API_KEY = _env('AI_API_KEY', 'SN_API_KEY', 'SN_CHAT_API_KEY', 'SN_TEXT_API_KEY')
LLM_BASE_URL = _env('AI_BASE_URL', 'SN_BASE_URL', 'SN_CHAT_BASE_URL', default='https://token.sensenova.cn/v1')
LLM_MODEL = _env('AI_MODEL', 'SN_MODEL', 'SN_CHAT_MODEL', default='sensenova-6.7-flash-lite')

MAX_TOOL_ITERS = 4   # 工具调用最大轮数
TIMEOUT = 120        # 单次 HTTP 超时（秒）
