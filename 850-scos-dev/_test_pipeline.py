"""End-to-end pipeline test"""
import sys, os, json, time, subprocess
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'data-engine'))

print('=' * 50)
print('  850 SCOS Pipeline Test')
print('=' * 50)

# 0. Kill zombie processes (DEV port 5051 ONLY — never touch prod 5050)
PORT = 5051
os.environ['SCOS_PORTAL_PORT'] = str(PORT)  # spawned portal inherits dev port
print(f'\n[0/4] Cleaning port {PORT}...')
try:
    out = subprocess.check_output(f'netstat -ano | findstr :{PORT}', shell=True, text=True)
    for line in out.strip().split('\n'):
        parts = line.split()
        if len(parts) >= 5 and 'LISTENING' in line:
            pid = parts[-1]
            subprocess.run(f'taskkill /f /pid {pid}', shell=True, capture_output=True)
            print(f'  Killed PID {pid} on port {PORT}')
except subprocess.CalledProcessError:
    print(f'  Port {PORT} is free')

# 1. Start Portal
print(f'\n[1/4] Starting Portal (:{PORT})...')
portal_log = os.path.join(ROOT, '_portal_test.log')
with open(portal_log, 'w') as lf:
    portal = subprocess.Popen([sys.executable, os.path.join(ROOT, 'portal', 'main.py')],
        stdout=lf, stderr=lf, cwd=os.path.join(ROOT, 'portal'))
time.sleep(4)
print(f'  Portal PID: {portal.pid}')

# Check Portal is alive
import requests
for i in range(5):
    try:
        r = requests.get(f'http://localhost:{PORT}/api/health', timeout=5)
        if r.status_code == 200:
            print(f'  Portal ready (attempt {i+1})')
            break
    except: time.sleep(2)
else:
    print('  Portal failed to start. Log:')
    if os.path.exists(portal_log):
        with open(portal_log) as f:
            for line in f.readlines()[-10:]:
                print(f'    {line.rstrip()}')
    portal.kill(); sys.exit(1)

# 2. Run Data Engine
print('\n[2/4] Running Data Engine...')
from scheduler import run
result = run()
if result is None or result[0] is None:
    print('  FAILED: No data')
    portal.kill(); sys.exit(1)
records, pushed = result
print(f'  Records: {len(records)}, Pushed: {pushed}')

# 3. Verify Portal
print('\n[3/4] Verifying Portal (waiting for sync to settle)...')
time.sleep(3)
errors = []
try:
    h = requests.get(f'http://localhost:{PORT}/api/health', timeout=10)
    h.raise_for_status()
    hd = h.json()
    print(f'  Portal: {hd["db_records"]} records, K1={hd["k1_cached"]}, Risks={hd["risks_cached"]}, KPI={hd["kpi_cached"]}')
except Exception as e: errors.append(f'health: {e}')

try:
    k1 = requests.get(f'http://localhost:{PORT}/api/cache/k1_summary', timeout=10).json()
    print(f'  K1: {k1.get("total_qty",0):,} total, {k1.get("shipped",0):,} shipped, CTO_P1_unshipped={k1.get("cto_p1_unshipped",0)}')
    if k1.get('cto_p1_unshipped', 0) < 0: errors.append('CTO P1 unshipped NEGATIVE')
except Exception as e: errors.append(f'k1: {e}')

try:
    risks = requests.get(f'http://localhost:{PORT}/api/cache/risks', timeout=10).json()
    print(f'  Risks: {len(risks) if isinstance(risks,list) else "error"} items')
except Exception as e: errors.append(f'risks: {e}')

try:
    kpi = requests.get(f'http://localhost:{PORT}/api/cache/kpi', timeout=10).json()
    wk = kpi.get('weekly', {}).get(kpi.get('this_week_start', ''), {})
    print(f'  KPI: {wk.get("pct",0)}% ({wk.get("ok",0)}/{wk.get("total",0)}) ≥75:{kpi.get("target_75")} ≥90:{kpi.get("target_90")}')
except Exception as e: errors.append(f'kpi: {e}')

# 4. Result
portal.kill()
print()
if errors:
    print(f'  ❌ {len(errors)} errors: {errors}')
    sys.exit(1)
print('  ✅ Pipeline test PASSED!')
