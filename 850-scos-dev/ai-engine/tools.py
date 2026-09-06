"""工具定义 — AI 的唯一数据入口。

每个工具都映射到 Service Layer 端点；AI 引擎禁止直接访问 SQLite / Data Engine。
返回 (payload, computed_at)：computed_at 用于回答附"数据更新时间"。
"""
import requests
from config import API_BASE, TIMEOUT

META = {'meta': '1'}


def _get(path, params=None):
    r = requests.get(API_BASE + path, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def _freshness():
    """订单数据新鲜度 = health 的 last_sync_time。"""
    try:
        return _get('/api/health').get('last_sync_time', '')
    except Exception:
        return ''


_ORDER_FILTERS = ('region', 'sub_type', 'cto_p1', 'priority', 'shipped', 'ack_status',
                  'is_hold', 'cust', 'msbd', 'msbd_from', 'msbd_to', 'ship_mode', 'scac', 'mcid', 'limit')

TOOLS = [
    {
        'type': 'function',
        'function': {
            'name': 'query_orders',
            'description': '按条件查询订单明细。支持：region(DAO/APJ/EMEA)、sub_type(FGA/RTL/CTO)、'
                           'cto_p1(Y=是CTO P1)、priority、shipped(1已出货/0未出货)、'
                           'ack_status(REJECT=NACK被拒)、is_hold(Y=Hold中)、cust(如DAISY/DAISY 35)、'
                           'msbd(单日YYYY-MM-DD)、msbd_from/msbd_to(日期范围)、ship_mode、scac、mcid、limit。'
                           '注意：总量/笔数等统计请优先用汇总工具（get_k1_summary 等），本工具只用于明细下钻。',
            'parameters': {'type': 'object',
                           'properties': {k: {'type': 'string'} for k in _ORDER_FILTERS}},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_k1_summary',
            'description': 'K1 看板总览。重要：所有数量单位是件数(pcs)，不是笔数；笔数必须用 query_orders 统计 total。'
                           '字段语义（务必按需取用，勿混）：'
                           'total_qty/shipped/unshipped=全部订单总量/已出货/未出货(件)；'
                           'backlog_xreg=未出货订单按类型×区域(DAO/APJ/EMEA)的件数矩阵——问"Backlog/未出货分布"用这个；'
                           'cross_region=全部订单类型×区域矩阵；shipped_xreg=已出货类型×区域矩阵；'
                           'region_cnt=仅CTO P1的区域件数分布(不是全部订单)；'
                           'type_cnt=各类型全量件数(含已出货，不是Backlog)；'
                           'cto_p1_qty/fga_qty/rtl_qty/cto_p2_qty 及对应 shipped/unshipped=各类型的全量/已出货/未出货件数；'
                           'cto_p1_gpp/others_gpp/fga_gpp/rtl_gpp=GPP生产状态件数；'
                           'msbd_plan=MSBD出货计划(非CTO P1)；cto_timeline=CTO P1 28H计划。',
            'parameters': {'type': 'object', 'properties': {}},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_backlog_distribution',
            'description': 'Backlog（未出货）订单分布——问"Backlog/未出货的分布（按区域/类型）"必须用这个工具，'
                           '不要用 get_k1_summary 自己找字段。返回单位 pcs(件)。'
                           '返回结构：by_type={类型:{qty:件数, regions:{DAO/APJ/EMEA:件数}}}、'
                           'by_region={区域:件数}、total_unshipped=未出货总件数。'
                           '若用户要"笔数/单数"，需要再调 query_orders(shipped=0) 看 total 条数。',
            'parameters': {'type': 'object', 'properties': {}},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_daily_summary',
            'description': '日报摘要：今日新收订单（VN 5:00-5:00 窗口）、今日出货、ASN（N/S/ACK/NACK 计数）、'
                           'SN S、车辆数、30 日趋势、今日 MSBD/CTO 28H 计划。',
            'parameters': {'type': 'object', 'properties': {}},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_risks',
            'description': '风险清单（R1-R6 规则）：CTO P1 28H 超时、MSBD 到期未出、STBL 异常、'
                           'ATB 预警、入库未开 ASN、各段超时预警。',
            'parameters': {'type': 'object', 'properties': {}},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_kpi',
            'description': 'CTO P1 28H KPI：每日/每周达标率（周六-周五周口径）、75%/90% 目标线达标情况。',
            'parameters': {'type': 'object', 'properties': {}},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_e2e_kpi',
            'description': 'E2E 全流程 KPI：Planning/Build/Shuttle/Shipment/Kitting 等段达标率、'
                           'Clean 28H vs Non-Clean 48H、MSBD 准时率、瓶颈分析。',
            'parameters': {'type': 'object', 'properties': {}},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_nack_orders',
            'description': 'NACK（被拒）订单列表。可加 region/sub_type/limit 过滤。',
            'parameters': {'type': 'object',
                           'properties': {'region': {'type': 'string'},
                                          'sub_type': {'type': 'string'},
                                          'limit': {'type': 'string'}}},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'check_asn',
            'description': 'ASN 校验：输入 ASN 编号，返回出货状态（PASS/PARTIAL/PENDING/NACK/HOLD/OPEN/NOT_FOUND）'
                           '及关联 PO 明细。',
            'parameters': {'type': 'object', 'properties': {'asn': {'type': 'string'}},
                           'required': ['asn']},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'check_st',
            'description': 'SHIP_STATUS 出货状态校验：输入 PO 或 ASN，返回一致性校验'
                           '（NACK/数据异常/超发/Hold/部分出货）。',
            'parameters': {'type': 'object',
                           'properties': {'po': {'type': 'string'}, 'asn': {'type': 'string'}}},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_cto_asn_missing',
            'description': 'CTO P1 已入库未开 ASN 提醒清单（含 28H 目标出货时间、已入库时长、逾期标记）。',
            'parameters': {'type': 'object', 'properties': {}},
        },
    },
]


def execute(name, args):
    """执行工具 → Service Layer。返回 (payload, computed_at)。"""
    if name == 'query_orders':
        args = dict(args)
        if 'limit' not in args:
            args['limit'] = '50'  # 默认截断，防止把全表灌给 LLM；总数用汇总工具
        return _get('/api/orders', args), _freshness()
    if name == 'get_nack_orders':
        args = dict(args)
        if 'limit' not in args:
            args['limit'] = '50'
        return _get('/api/nack', args), _freshness()
    if name == 'get_k1_summary':
        d = _get('/api/k1', META)
        return d['data'], d.get('computed_at', '')
    if name == 'get_backlog_distribution':
        d = _get('/api/k1', META)
        k1 = d['data']
        bx = k1.get('backlog_xreg', {}) or {}
        by_type = {}
        region_totals = {}
        for t, regions in bx.items():
            tsum = sum(regions.values())
            by_type[t] = {'qty': tsum, 'regions': dict(regions)}
            for r, v in regions.items():
                region_totals[r] = region_totals.get(r, 0) + v
        return {
            'unit': 'pcs(件)',
            'by_type': by_type,
            'by_region': region_totals,
            'total_unshipped': k1.get('unshipped'),
        }, d.get('computed_at', '')
    if name == 'get_daily_summary':
        d = _get('/api/daily', META)
        return d['data'], d.get('computed_at', '')
    if name == 'get_kpi':
        d = _get('/api/kpi', META)
        return d['data'], d.get('computed_at', '')
    if name == 'get_e2e_kpi':
        d = _get('/api/e2e', META)
        return d['data'], d.get('computed_at', '')
    if name == 'get_risks':
        return _get('/api/risk'), _freshness()
    if name == 'check_asn':
        d = _get('/api/asn', {'asn': args.get('asn', '')})
        return d, d.get('computed_at', '')
    if name == 'check_st':
        d = _get('/api/st', {'po': args.get('po', ''), 'asn': args.get('asn', '')})
        return d, d.get('computed_at', '')
    if name == 'get_cto_asn_missing':
        d = _get('/api/cto-asn-missing', META)
        return d.get('data', d), d.get('computed_at', '')
    raise ValueError(f'unknown tool: {name}')
