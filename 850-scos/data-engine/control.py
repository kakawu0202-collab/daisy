"""
SCOS Control Panel — monitoring-first console for company computer.
Normal operation: watch status only. Buttons appear when something needs attention.
Access: http://localhost:8900
"""
import os, sys, json, subprocess, sqlite3
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

PORT = 8900
BASE = os.path.dirname(os.path.abspath(__file__))
ENGINE_DB = os.path.join(BASE, '..', 'data', 'engine.db')

engine_proc = None

CONTROL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SCOS Monitor</title>
<style>
:root{--bg:#0B1220;--card:#111A2E;--card2:#18233B;--border:#1E293B;--fg:#E2E8F0;--muted:#64748B;--blue:#3B82F6;--green:#22C55E;--red:#EF4444;--amber:#F59E0B;--r:12px}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,sans-serif;background:var(--bg);color:var(--fg);padding:24px;min-height:100vh;font-size:14px}
h1{font-size:18px;margin-bottom:2px}.sub{font-size:11px;color:var(--muted);margin-bottom:20px}

/* Big status banner */
.banner{display:flex;align-items:center;gap:14px;background:var(--card);border:1px solid var(--border);border-radius:var(--r);padding:20px;margin-bottom:16px}
.banner .dot{width:16px;height:16px;border-radius:50%;flex-shrink:0;animation:pulse 2s infinite}
.banner .dot.ok{background:var(--green);box-shadow:0 0 12px rgba(34,197,94,.5)}
.banner .dot.warn{background:var(--amber);box-shadow:0 0 12px rgba(245,158,11,.5)}
.banner .dot.err{background:var(--red);box-shadow:0 0 12px rgba(239,68,68,.5)}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}
.banner .st{font-size:16px;font-weight:700}
.banner .st.ok{color:var(--green)}.banner .st.warn{color:var(--amber)}.banner .st.err{color:var(--red)}
.banner .dt{font-size:11px;color:var(--muted)}

/* Status grid */
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin-bottom:16px}
.sc{background:var(--card);border:1px solid var(--border);border-radius:var(--r);padding:14px}
.sc .l{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}
.sc .v{font-size:18px;font-weight:700}
.sc .v.ok{color:var(--green)}.sc .v.err{color:var(--red)}.sc .v.warn{color:var(--amber)}
.sc .s{font-size:10px;color:var(--muted);margin-top:2px}

/* Exception section — hidden unless needed */
.exception{display:none;background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.3);border-radius:var(--r);padding:16px;margin-bottom:16px}
.exception.show{display:block}
.exception h3{font-size:13px;color:var(--red);margin-bottom:8px}
.exception .msg{font-size:12px;color:var(--fg);margin-bottom:12px}
.btns{display:flex;gap:8px;flex-wrap:wrap}
.btn{padding:10px 18px;border:none;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;color:#fff}
.btn:hover{opacity:.85}
.btn:disabled{opacity:.4;cursor:not-allowed}
.btn-start{background:var(--green)}.btn-stop{background:var(--red)}.btn-push{background:var(--blue)}

/* Log */
.log{background:var(--card);border:1px solid var(--border);border-radius:var(--r);padding:14px;font-family:monospace;font-size:11px;max-height:260px;overflow:auto;white-space:pre-wrap;color:#94a3b8}
.foot{font-size:10px;color:var(--muted);margin-top:10px}
</style>
</head>
<body>
<h1>SCOS Monitor</h1>
<div class="sub">Company Computer · Data Engine</div>

<div class="banner">
  <span class="dot err" id="b-dot"></span>
  <div>
    <div class="st err" id="b-status">CHECKING...</div>
    <div class="dt" id="b-detail">--</div>
  </div>
</div>

<div class="exception" id="ex-box">
  <h3>⚠ Action Needed</h3>
  <div class="msg" id="ex-msg"></div>
  <div class="btns">
    <button class="btn btn-start" id="b-start" onclick="action('start')">▶ Start Engine</button>
    <button class="btn btn-push" id="b-push" onclick="action('trigger')">↻ Retry Push</button>
  </div>
</div>

<div class="grid">
  <div class="sc"><div class="l">Pipeline Cycles</div><div class="v" id="s-cycles">0</div><div class="s">runs completed</div></div>
  <div class="sc"><div class="l">Last Run</div><div class="v" id="s-last" style="font-size:14px">--</div><div class="s">local time</div></div>
  <div class="sc"><div class="l">Pull Result</div><div class="v" id="s-pull" style="font-size:13px">--</div><div class="s">OMS fetch</div></div>
  <div class="sc"><div class="l">Push Status</div><div class="v" id="s-push" style="font-size:13px">--</div><div class="s">to Yumin</div></div>
  <div class="sc"><div class="l">Records</div><div class="v" id="s-records">0</div><div class="s">in local DB</div></div>
</div>

<div class="log" id="log">Waiting for first status...</div>
<div class="foot">Auto-refresh every 5s · Buttons appear only when attention is needed</div>

<script>
async function refresh(){
  try{
    var r=await fetch('/status');var d=await r.json()
    var running=d.engine_running
    var es=d.engine_state||{}
    var pullOk=(es.last_result||'').startsWith('OK')
    var pushOk=(es.push_status||'').includes('OK')

    // Banner
    var dot=document.getElementById('b-dot'),st=document.getElementById('b-status'),dt=document.getElementById('b-detail')
    var level
    if(!running){level='err';st.textContent='ENGINE STOPPED';st.className='st err';dot.className='dot err';dt.textContent='Engine not running — start it'}
    else if(!pullOk){level='err';st.textContent='PULL FAILED';st.className='st err';dot.className='dot err';dt.textContent=es.last_result||''}
    else if(!pushOk){level='warn';st.textContent='RUNNING · PUSH PENDING';st.className='st warn';dot.className='dot warn';dt.textContent='Data saved locally, will retry next cycle'}
    else{level='ok';st.textContent='ALL NORMAL';st.className='st ok';dot.className='dot ok';dt.textContent='Auto-pull every 10 min · push confirmed'}

    // Grid
    document.getElementById('s-cycles').textContent=es.cycle||0
    document.getElementById('s-last').textContent=(es.last_run||'--').substring(11,19)
    var pr=document.getElementById('s-pull');pr.textContent=(es.last_result||'--').substring(0,40)
    pr.className='v '+(pullOk?'ok':'err')
    var pu=document.getElementById('s-push');pu.textContent=(es.push_status||'--').substring(0,40)
    pu.className='v '+(pushOk?'ok':running?'warn':'err')
    document.getElementById('s-records').textContent=(d.db_records||0).toLocaleString()

    // Exception box — show only when attention needed
    var ex=document.getElementById('ex-box'),em=document.getElementById('ex-msg')
    if(!running){ex.classList.add('show');em.textContent='Engine 已停止。点击 Start Engine 恢复自动抓取。';document.getElementById('b-start').disabled=false}
    else if(!pushOk){ex.classList.add('show');em.textContent='本地数据已保存，但推送到 Yumin 未确认。系统下个周期会自动重试；也可点击 Retry Push 立即重试。';document.getElementById('b-start').disabled=true}
    else{ex.classList.remove('show')}

    if(d.log)document.getElementById('log').textContent=d.log
  }catch(e){
    document.getElementById('b-status').textContent='CONTROL UNKNOWN'
  }
}
async function action(act){
  document.getElementById('log').textContent='Executing...'
  try{var r=await fetch('/'+act,{method:'POST'});var d=await r.json();document.getElementById('log').textContent=d.msg||'Done';setTimeout(refresh,3000)}
  catch(e){document.getElementById('log').textContent='Error: '+e.message}
}
setInterval(refresh,5000);refresh()
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ('/', '/index.html'):
            self._send_html(CONTROL_HTML)
        elif self.path == '/status':
            self._send_json(self._status())
        else:
            self._send_json({'error': 'not found'}, 404)

    def do_POST(self):
        global engine_proc
        path = self.path.strip('/')
        if path == 'start':
            if engine_proc and engine_proc.poll() is None:
                self._send_json({'msg': 'Engine already running'})
            else:
                try:
                    engine_proc = subprocess.Popen(
                        [sys.executable, os.path.join(BASE, 'main.py'), '--daemon'],
                        cwd=BASE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
                    self._send_json({'msg': 'Engine started — wait 30-60s for first pull'})
                except Exception as e:
                    self._send_json({'msg': f'Start failed: {e}'}, 500)
        elif path == 'stop':
            if engine_proc and engine_proc.poll() is None:
                engine_proc.terminate()
                engine_proc = None
            self._send_json({'msg': 'Engine stopped'})
        elif path == 'trigger':
            try:
                import requests as _r
                resp = _r.post('http://localhost:8700/trigger', timeout=10)
                self._send_json({'msg': resp.json().get('msg', 'Triggered')})
            except Exception as e:
                self._send_json({'msg': f'Trigger failed (engine not running?): {e}'}, 500)
        else:
            self._send_json({'error': 'not found'}, 404)

    def _status(self):
        es = {}
        running = False
        try:
            import requests as _r
            es = _r.get('http://localhost:8700/status', timeout=3).json()
            running = True  # engine responds on 8700 → it's alive
        except Exception:
            running = False
        db_records = 0
        try:
            db = sqlite3.connect(ENGINE_DB)
            db_records = db.execute('SELECT COUNT(*) FROM orders').fetchone()[0]
            db.close()
        except Exception:
            pass
        return {
            'engine_running': running,
            'engine_state': es,
            'db_records': db_records,
        }

    def _send_html(self, html):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def _send_json(self, data, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode('utf-8'))

    def log_message(self, *args):
        pass


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


if __name__ == '__main__':
    server = ThreadingHTTPServer(('0.0.0.0', PORT), Handler)
    print(f'SCOS Monitor: http://localhost:{PORT}')
    server.serve_forever()
