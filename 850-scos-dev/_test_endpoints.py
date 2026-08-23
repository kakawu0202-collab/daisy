"""Phase 2 Service Layer 端点回归 — 新端点 vs 旧端点载荷一致性 + 兼容性。

用法：先启动 dev Portal（start-dev.bat），然后 python _test_endpoints.py
"""
import requests, json, sys

BASE = 'http://localhost:5051'
errors = []

# 1. 新标准端点 == 旧 /api/cache/* 载荷（raw 模式逐字节一致）
pairs = [
    ('/api/k1', '/api/cache/k1_summary'),
    ('/api/daily', '/api/cache/daily_summary'),
    ('/api/kpi', '/api/cache/kpi'),
    ('/api/e2e', '/api/cache/e2e_kpi'),
    ('/api/risk', '/api/cache/risks'),
]
for new, old in pairs:
    try:
        a = requests.get(BASE + new, timeout=10)
        b = requests.get(BASE + old, timeout=10)
        assert a.status_code == 200, f'{new} HTTP {a.status_code}'
        assert a.content == b.content, f'{new} payload differs from {old}'
        print(f'  {new} == {old}  ({len(a.content)//1024} KB)  OK')
    except Exception as e:
        errors.append(f'{new}: {e}'); print(f'  {new}  FAIL: {e}')

# 2. ?meta=1 数据溯源（AI 用：来源 + 更新时间）
try:
    m = requests.get(BASE + '/api/k1?meta=1', timeout=10).json()
    assert set(m.keys()) == {'key', 'computed_at', 'data'}, f'meta keys: {list(m.keys())}'
    print(f'  /api/k1?meta=1  OK  (computed_at={m["computed_at"][:19]}, data.total_qty={m["data"]["total_qty"]:,})')
except Exception as e:
    errors.append(f'meta: {e}'); print(f'  /api/k1?meta=1  FAIL: {e}')

# 3. /api/nack — 只含 REJECT 记录
try:
    n = requests.get(BASE + '/api/nack', timeout=10).json()
    recs = n['records']
    bad = [r for r in recs if str(r.get('ACK_STATUS', '')).upper() != 'REJECT']
    assert not bad, f'{len(bad)} non-REJECT rows in nack result'
    print(f'  /api/nack  OK  ({n["total"]} NACK records, all REJECT)')
except Exception as e:
    errors.append(f'nack: {e}'); print(f'  /api/nack  FAIL: {e}')

# 4. 旧兼容别名不受影响
for old in ('/api/k1-summary', '/api/daily-summary', '/api/sort-data', '/api/shipped-history'):
    try:
        r = requests.get(BASE + old, timeout=10)
        assert r.status_code == 200, f'HTTP {r.status_code}'
        print(f'  {old}  compat OK')
    except Exception as e:
        errors.append(f'{old}: {e}'); print(f'  {old}  FAIL: {e}')

print()
if errors:
    print(f'❌ {len(errors)} errors:\n' + '\n'.join(errors))
    sys.exit(1)
print('✅ Phase 2 endpoints all pass — new endpoints consistent with old, compat preserved.')
