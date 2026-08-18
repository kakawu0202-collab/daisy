"""M1 拆层回归验证 — baseline(旧代码) vs new(新代码)，同输入逐值对比。

用法：
  python regression_test.py baseline    # 用 OLD 代码(processor/*)生成 baseline.json
  python regression_test.py check       # 用 NEW 代码(business-engine)对比 baseline.json
  python regression_test.py golden      # 快照 dev portal.db 现有 cache 为 golden/*.json

输入：dev engine.db 现有 orders 记录（与 merge 输出同构）+ 空 raw ship/asn
验收：check 模式 diff 必须为空（100% 一致）。
"""
import sys, os, json, sqlite3
ROOT = os.path.dirname(os.path.abspath(__file__))
REGRESSION = os.path.join(ROOT, 'regression')
BASELINE_FILE = os.path.join(REGRESSION, 'baseline.json')
GOLDEN_DIR = os.path.join(REGRESSION, 'golden')
DE_PATH = os.path.join(ROOT, 'data-engine')
BE_PATH = os.path.join(ROOT, 'business-engine')
sys.path.insert(0, DE_PATH)


def load_inputs():
    """records(orders表) + 重建的 e2e 记录 + 空 raw。新旧代码共用同一输入。"""
    sys.path.insert(0, DE_PATH)
    from storage.db import get_db
    conn = get_db()
    rows = [dict(r) for r in conn.execute('SELECT * FROM orders').fetchall()]
    conn.close()
    # e2e-like records reconstructed from orders（缺真实 PO_STATUS，新旧同输入一致性不受影响）
    e2e_recs = []
    for r in rows:
        if not r.get('sn_cdt'):
            continue
        st = str(r.get('status') or '').strip()
        e2e_recs.append({
            'PO': r.get('po', ''), 'PO_LINE': r.get('po_line', '1'),
            'PO_QTY': r.get('po_qty', 0), 'PRIORITY': r.get('priority', ''),
            'DPN': r.get('dpn', ''), 'IPN': r.get('ipn', ''),
            'SN_CDT': r.get('sn_cdt'),
            'PO_STATUS': 'CLOSE' if st.lower() == 'close' else st.upper(),
        })
    return rows, e2e_recs, [], []


def run_old(rows, e2e_recs, raw_ship, raw_asn):
    sys.path.insert(0, DE_PATH)
    from processor.k1 import compute as k1
    from processor.daily import compute as daily
    from processor.risk import compute as risk
    from processor.kpi import compute as kpi
    from processor.e2e_kpi import compute_all as e2e
    return dict(
        k1_summary=k1(rows),
        daily_summary=daily(rows, raw_ship, raw_asn),
        risks=risk(rows),
        kpi=kpi(rows),
        e2e_kpi=e2e(e2e_recs, rows),
    )


def run_new(rows, e2e_recs, raw_ship, raw_asn):
    sys.path.insert(0, BE_PATH)
    from engine import run
    return run(rows, raw_ship, raw_asn, e2e_recs)


def deep_diff(a, b, path=''):
    """返回差异路径列表。字典按 key 遍历；列表逐项对比（顺序相关）。"""
    diffs = []
    if type(a) != type(b):
        return [f'{path}: TYPE {type(a).__name__} vs {type(b).__name__}']
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a: diffs.append(f'{path}.{k}: MISSING in new')
            elif k not in b: diffs.append(f'{path}.{k}: MISSING in baseline')
            else: diffs += deep_diff(a[k], b[k], f'{path}.{k}')
    elif isinstance(a, list):
        if len(a) != len(b):
            diffs.append(f'{path}: LEN {len(a)} vs {len(b)}')
        for i, (x, y) in enumerate(zip(a, b)):
            diffs += deep_diff(x, y, f'{path}[{i}]')
    else:
        if a != b:
            diffs.append(f'{path}: {a!r} vs {b!r}')
    return diffs


def cmd_baseline():
    rows, e2e_recs, raw_ship, raw_asn = load_inputs()
    print(f'Inputs: {len(rows)} orders, {len(e2e_recs)} e2e-like records')
    print('Running OLD code (processor/*)...')
    result = run_old(rows, e2e_recs, raw_ship, raw_asn)
    os.makedirs(REGRESSION, exist_ok=True)
    with open(BASELINE_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, default=str)
    size = os.path.getsize(BASELINE_FILE) / 1024
    print(f'baseline.json saved: {size:.0f} KB')
    print(f'  k1 total={result["k1_summary"]["total_qty"]:,} | risks={len(result["risks"])} | '
          f'kpi this_week={result["kpi"].get("this_week", "")}')


def cmd_check():
    if not os.path.exists(BASELINE_FILE):
        print('ERROR: baseline.json not found — run "python regression_test.py baseline" first')
        sys.exit(1)
    with open(BASELINE_FILE, encoding='utf-8') as f:
        baseline = json.load(f)
    rows, e2e_recs, raw_ship, raw_asn = load_inputs()
    print(f'Inputs: {len(rows)} orders, {len(e2e_recs)} e2e-like records')
    print('Running NEW code (business-engine)...')
    new = run_new(rows, e2e_recs, raw_ship, raw_asn)
    diffs = deep_diff(baseline, new)
    if diffs:
        print(f'\n❌ {len(diffs)} differences found:')
        for d in diffs[:40]:
            print('  ' + d)
        sys.exit(1)
    print('\n✅ 100% identical — old vs new outputs match exactly.')


def cmd_golden():
    """Snapshot current dev portal.db cache as golden reference."""
    os.makedirs(GOLDEN_DIR, exist_ok=True)
    portal_db = os.path.join(ROOT, 'data', 'portal.db')
    conn = sqlite3.connect(portal_db)
    for key in ('k1_summary', 'daily_summary', 'risks', 'risk_summary', 'kpi', 'e2e_kpi'):
        row = conn.execute('SELECT data, computed_at FROM cache WHERE key=?', (key,)).fetchone()
        if not row:
            print(f'  {key}: MISSING in portal cache')
            continue
        with open(os.path.join(GOLDEN_DIR, f'{key}.json'), 'w', encoding='utf-8') as f:
            f.write(row[0])
        print(f'  {key}: saved ({row[1][:19]})')
    conn.close()


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'check'
    if mode == 'baseline': cmd_baseline()
    elif mode == 'check': cmd_check()
    elif mode == 'golden': cmd_golden()
    else:
        print(__doc__)
        sys.exit(1)
