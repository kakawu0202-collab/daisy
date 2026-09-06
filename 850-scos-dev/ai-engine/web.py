"""AI Assistant Web — 聊天页 + /api/ask（默认 http://localhost:5099）。

架构约束：本服务只调 Service Layer 与 LLM；浏览器用户直接提问，无需终端。
启动：python web.py（或双击 start-ai.bat）
"""
import os, json, sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agent import ask

PORT = int(os.environ.get('SCOS_AI_PORT', '5099'))

CHAT_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>850 SCOS · AI Assistant</title>
<style>
:root{--bg:#0f172a;--card:#1e293b;--b2:#334155;--text:#f1f5f9;--muted:#94a3b8;--accent:#3b82f6;--rd:10px}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,sans-serif;background:var(--bg);color:var(--text);height:100vh;display:flex;flex-direction:column}
header{padding:14px 20px;border-bottom:1px solid var(--b2);display:flex;justify-content:space-between;align-items:center}
header h1{font-size:16px}header .t{font-size:11px;color:var(--muted)}
#chat{flex:1;overflow-y:auto;padding:20px;max-width:900px;width:100%;margin:0 auto}
.msg{margin-bottom:14px;display:flex;gap:10px}
.msg .bubble{max-width:80%;padding:10px 14px;border-radius:12px;font-size:13px;line-height:1.65;white-space:pre-wrap}
.msg.user{justify-content:flex-end}
.msg.user .bubble{background:var(--accent);color:#fff;border-bottom-right-radius:4px}
.msg.ai .bubble{background:var(--card);border:1px solid var(--b2);border-bottom-left-radius:4px}
.msg.ai .bubble .src{display:block;margin-top:8px;font-size:10px;color:var(--muted)}
#inputbar{display:flex;gap:8px;padding:14px 20px;border-top:1px solid var(--b2);max-width:900px;width:100%;margin:0 auto}
#q{flex:1;padding:11px 14px;background:var(--card);border:1px solid var(--b2);border-radius:10px;color:var(--text);font-size:13px}
#q:focus{outline:none;border-color:var(--accent)}
#send{padding:11px 22px;background:var(--accent);color:#fff;border:none;border-radius:10px;cursor:pointer;font-size:13px}
#send:disabled{opacity:.5;cursor:wait}
.hint{font-size:10px;color:var(--muted);text-align:center;padding-bottom:8px}
</style>
</head>
<body>
<header><h1>850 SCOS · AI Assistant</h1><span class="t">自然语言问数据 · 答案附数据更新时间</span></header>
<div id="chat">
  <div class="msg ai"><div class="bubble">你好！我是 850 SCOS 数据助手，可以问我：
例如「目前有多少笔 NACK 订单？」「CTO P1 未出货的订单有多少？」「查 ASN LUXBVN000000158 的出货状态」「风险最高的 PO 是哪些」<span class="src">数据来自 SCOS Service Layer</span></div></div>
</div>
<div class="hint" id="fresh">回答需 10-60 秒（模型查询+生成），请耐心等待</div>
<div id="inputbar">
  <input id="q" placeholder="输入你的问题，回车发送…" autocomplete="off" onkeydown="if(event.key==='Enter'){event.preventDefault();doSend();}">
  <button id="send" type="button" onclick="doSend()">发送</button>
</div>
<script>
var chat=document.getElementById('chat'),q=document.getElementById('q'),sendBtn=document.getElementById('send');
window.onerror=function(m){try{var d=document.createElement('div');d.className='msg ai';d.innerHTML='<div class="bubble">⚠️ JS错误：'+m+'</div>';chat.appendChild(d);}catch(e){}return false;};
function addMsg(who,text){
  var d=document.createElement('div');d.className='msg '+who;
  var b=document.createElement('div');b.className='bubble';b.textContent=text;
  d.appendChild(b);chat.appendChild(d);b.scrollIntoView({block:'end'});
}
function doSend(){
  var t=q.value.trim();
  if(!t){q.focus();q.style.borderColor='#ef4444';setTimeout(function(){q.style.borderColor=''},1200);return;}
  if(sendBtn.disabled)return;
  q.style.borderColor='';
  addMsg('user',t);q.value='';sendBtn.disabled=true;
  var ai=document.createElement('div');ai.className='msg ai';
  var ab=document.createElement('div');ab.className='bubble';ab.textContent='思考中…';ai.appendChild(ab);chat.appendChild(ai);ab.scrollIntoView({block:'end'});
  fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:t})})
    .then(function(r){return r.json()})
    .then(function(d){ab.textContent=d.answer||'(空回答)';ab.scrollIntoView({block:'end'});})
    .catch(function(e){ab.textContent='⚠️ 调用失败：'+e.message;})
    .finally(function(){sendBtn.disabled=false;q.focus();});
}
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        p = urlparse(self.path).path
        if p in ('/', '/index.html'):
            self._html(CHAT_HTML)
        else:
            self._json({'error': 'not found'}, 404)

    def do_POST(self):
        p = urlparse(self.path).path
        if p == '/api/ask':
            try:
                length = int(self.headers.get('Content-Length', 0))
                body = json.loads(self.rfile.read(length)) if length > 0 else {}
                question = str(body.get('question', '')).strip()
                if not question:
                    self._json({'answer': '请输入问题'}, 400)
                    return
                answer = ask(question)
                self._json({'answer': answer})
            except RuntimeError as e:
                self._json({'answer': f'⚠️ {e}'}, 500)
            except Exception as e:
                self._json({'answer': f'⚠️ 调用失败：{e}'}, 500)
        else:
            self._json({'error': 'not found'}, 404)

    def _html(self, content):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))

    def _json(self, data, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def log_message(self, *args):
        pass


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


if __name__ == '__main__':
    server = ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
    print(f'850 SCOS AI Assistant: http://localhost:{PORT}')
    server.serve_forever()
