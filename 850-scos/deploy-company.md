# Company Computer Deployment Guide

## Files Needed

Copy the entire `850-scos` folder to the company computer.

## Folder Layout

SCOS is self-contained — just place it anywhere.

```
D:\...\
├── 850-scos\              ← Copy the whole folder here
├── 850-toolbox\            ← Already exists (optional)
└── Daisy850-data\          ← Already exists (optional)
```

## Setup Steps

### 1. Install dependencies

```powershell
pip install requests
```

### 2. Verify OMS password

```powershell
[Environment]::GetEnvironmentVariable('OMS_PASSWORD', 'User')
```

If not set:
```powershell
[Environment]::SetEnvironmentVariable('OMS_PASSWORD', 'your-password', 'User')
```

### 3. Auto-start (optional)

```powershell
cd 850-scos
powershell -ExecutionPolicy Bypass -File setup-startup.ps1 -Engine
```

### 4. Launch

Double-click `data-engine/start-silent.vbs` (silent, no window).

Or with logs:
```powershell
cd data-engine
python main.py --daemon
```

### 5. Manual sync trigger

Status check: `http://localhost:8700/status`

Trigger:
```powershell
python -c "import requests; requests.post('http://localhost:8700/trigger')"
```

## Not Needed on Company Computer

- `portal/` directory — runs on Yumin only
- `_test_pipeline.py` — dev test tool
- `test-pipeline.bat` — dev test tool
