# 850 Supply Chain OS

```
850-scos/
├── data/                   DB files (self-contained)
├── data-engine/            Company computer (internal network)
│   ├── collector/          OMS data pull
│   ├── processor/          Business logic (merge/K1/daily/risk/KPI)
│   ├── storage/            SQLite
│   ├── publisher/          HTTPS push to Yumin
│   ├── scheduler.py        Orchestrator
│   └── main.py             Entry point
├── portal/                 Yumin computer (external + Tailscale)
│   ├── receiver/           Receive data push
│   ├── api/                REST API + HTTP Server
│   ├── dashboard/          PWA frontend
│   └── main.py             Entry point
├── start-all-silent.vbs    Launch both services silently
├── test-pipeline.bat       End-to-end test
├── setup-startup.ps1       Auto-start installer
└── README.md
```

## Deploy

### Company Computer

```powershell
pip install requests
set OMS_PASSWORD=your-password
set YUMIN_URL=https://yumin.taila2a2ad.ts.net/sync
cd data-engine
python main.py --daemon
```

| Feature | Address |
|---------|---------|
| Manual trigger | `POST http://localhost:8700/trigger` |
| Engine status | `GET http://localhost:8700/status` |
| Auto-start | `Win+R` → `shell:startup` → shortcut to `start.bat` |
| Network resume | Auto-detect, resumes on reconnect |

### Yumin Computer

```powershell
pip install requests
tailscale funnel --bg 5050
cd portal
python main.py
```

## Data Flow

```
OMS → Collector → Processor → SQLite → Publisher → HTTPS → Yumin Portal → PWA
```

## API

| Endpoint | Description |
|----------|-------------|
| POST /sync | Receive Data Engine push |
| GET /api/health | Portal health check |
| GET /api/cache/k1_summary | K1 dashboard data |
| GET /api/cache/daily_summary | Daily summary |
| GET /api/cache/risks | Risk list |
| GET /api/cache/kpi | CTO P1 KPI |
| GET /api/cache/e2e_kpi | E2E KPI analytics |
| GET /api/orders | Order query |
| POST /api/login | Login |
| POST /api/register | Register |

## Access

| Page | URL |
|------|-----|
| Portal Home | `http://localhost:5050` |
| K1 Dashboard | `http://localhost:5050/k1.html` |
| E2E KPI | `http://localhost:5050/e2e-kpi.html` |
| CTO Analysis | `http://localhost:5050/cto-analysis.html` |
| System Status | `http://localhost:5050/status.html` |
| Public | `https://yumin.taila2a2ad.ts.net` |
