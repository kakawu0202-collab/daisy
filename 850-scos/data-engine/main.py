"""850 SCOS Data Engine — entry point.
Usage: python main.py [--daemon]
Manual trigger: POST http://localhost:8700/trigger
Status check: GET http://localhost:8700/status"""
import sys, os, time, json, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scheduler import run, PULL_INTERVAL

TRIGGER_PORT = 8700
_state = {'running': True, 'mode': 'daemon', 'last_run': None, 'last_result': '', 'next_run': None, 'cycle': 0,
          'push_target': os.environ.get('YUMIN_URL', 'https://yumin.taila2a2ad.ts.net/sync'),
          'push_status': '', 'push_time': None}


class TriggerHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/trigger':
            self._json({'msg': 'Pipeline triggered'})
            threading.Thread(target=_run_wrapper, daemon=True).start()
    def do_GET(self):
        if self.path == '/status': self._json(_state)
        elif self.path == '/health': self._json({'status': 'ok'})
        else: self._json({'error': 'Not found'}, 404)
    def _json(self, data, code=200):
        self.send_response(code); self.send_header('Content-Type', 'application/json'); self.send_header('Access-Control-Allow-Origin', '*'); self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode())
    def log_message(self, *args): pass


def _run_wrapper():
    _state['running'] = True; _state['last_run'] = datetime.now().isoformat()
    try:
        result = run()
        if result and result[0]:
            records, pushed = result
            _state['last_result'] = f'OK: {len(records):,} records'
            _state['push_status'] = f'OK → {pushed}' if pushed else 'FAILED → no target'
            _state['push_time'] = datetime.now().isoformat()
        else:
            _state['last_result'] = 'FAILED: no data or login failed'
    except Exception as e:
        _state['last_result'] = f'ERROR: {str(e)[:100]}'
    _state['running'] = False; _state['cycle'] += 1


def _start_trigger_server():
    srv = HTTPServer(('0.0.0.0', TRIGGER_PORT), TriggerHandler)
    print(f'  Manual trigger: http://localhost:{TRIGGER_PORT}/trigger')
    srv.serve_forever()


def _wait_network():
    """Check network once. Log warning if unreachable, continue anyway."""
    import requests
    targets = ['http://luxoms-vn-prod.luxshare-ict.com']
    for t in targets:
        try:
            requests.get(t, timeout=5)
            return
        except: pass
    print(f'[{datetime.now().strftime("%H:%M:%S")}] Network check failed — will retry on next cycle')


if __name__ == '__main__':
    threading.Thread(target=_start_trigger_server, daemon=True).start()

    if '--daemon' in sys.argv:
        print(f'850 SCOS Data Engine (every {PULL_INTERVAL//60}min, trigger :{TRIGGER_PORT})')
        print('Auto-resume: will retry after reboot/network loss.')
        _wait_network()
        _run_wrapper()
        while True:
            _state['next_run'] = (datetime.now().isoformat())[:19]
            time.sleep(PULL_INTERVAL)
            try:
                _wait_network()
                _run_wrapper()
            except Exception as e:
                print(f'Cycle error: {e}')
                time.sleep(30)
    else:
        _wait_network()
        _run_wrapper()
