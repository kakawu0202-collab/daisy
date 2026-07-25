import os, sys, server

if getattr(sys, "frozen", False):
    exe_dir = os.path.dirname(sys.executable)
else:
    exe_dir = os.path.dirname(os.path.abspath(__file__))

os.chdir(exe_dir)
server.STATIC_DIR = os.path.join(exe_dir, "static")
server.DATA_DIR = os.path.join(exe_dir, "data")
server.CACHE_FILE = os.path.join(server.DATA_DIR, "oms_cache.json")
server.FGA_HOLD_FILE = os.path.join(server.DATA_DIR, "fga_hold.csv")
server.FGA_STATUS_FILE = os.path.join(server.DATA_DIR, "fga_status.csv")
os.makedirs(server.DATA_DIR, exist_ok=True)
import webbrowser, threading
threading.Timer(1.5, lambda: webbrowser.open('http://localhost:8500')).start()
server.main()
