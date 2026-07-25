# 850 Toolbox — 开发/运维文档

## 文件结构

```
850-toolbox/
├── server.py              ← 后端入口（HTTP 服务器 + OMS 代理 + auto_pull）
├── 启动.bat                ← 桌面启动（有黑窗口，调试用）
├── 启动-静默.vbs           ← 静默启动（无窗口，日常用）
├── 850-Toolbox.spec        ← PyInstaller 打包配置
├── _launcher.py            ← EXE 打包入口
├── _verify_data.py         ← 数据校验脚本
├── fga870_loader.py        ← FGA 分配引擎
├── fga870_allocate.py      ← FGA 分配算法
│
├── data/
│   ├── oms_cache.json      ← OMS 缓存（自动更新，每10分钟）
│   ├── fga_hold.csv        ← FGA Hold 上传
│   └── fga_status.csv      ← FGA Status 上传
│
├── static/                 ← 前端文件
│   ├── index.html          ← 工具箱首页
│   ├── k1.html             ← K1 看板 V3.3（PRD + 当日双Tab）
│   ├── shipped.html        ← 出货历史
│   ├── sort.html           ← 优先级排序
│   ├── fga870.html         ← 870 FGA 分配
│   ├── manifest.json       ← PWA 安装清单
│   ├── sw.js               ← Service Worker（离线缓存）
│   ├── app.js              ← 共享 PWA 逻辑
│   ├── offline.html        ← 离线降级页
│   └── icons/
│       ├── icon-192.png    ← PWA 小图标
│       └── icon-512.png    ← PWA 大图标
│
└── dist/850-Toolbox/       ← 免 Python 分发版
    └── 850-Toolbox.exe
```

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 健康检查 + auto_pull 状态 |
| `/api/cache` | GET | 缓存状态 |
| `/api/k1-summary` | GET | K1 看板汇总数据 |
| `/api/daily-summary` | GET | 当日看板数据 |
| `/api/sort-data` | GET | 筛选 + 下钻明细 |
| `/api/shipped-history` | GET | 出货历史统计 |
| `/api/oms-pull` | POST | 手动触发 OMS 拉取 |
| `/api/k1-send` | POST | 飞书群推送 |
| `/api/fga-status` | GET | FGA 就绪状态 |
| `/api/fga-allocate` | GET | FGA 分配结果 |
| `/api/fga-upload` | POST | 上传 FGA CSV |
| `/sw.js` | GET | Service Worker（no-cache 头） |
| `/manifest.json` | GET | PWA 清单 |

## auto_pull 机制

```python
# server.py 第 148-180 行
AUTO_PULL_INTERVAL = 10 * 60  # 每 10 分钟

# 启动流程：
# 1. 读取 OMS_PASSWORD 环境变量
# 2. 等待 3 秒让 server 初始化
# 3. 立刻执行首次拉取
# 4. 每 10 分钟循环拉取

# 状态查看：
# GET /api/health → auto_pull.running / last_pull / last_result / next_pull
```

## 环境依赖

| 依赖 | 说明 |
|------|------|
| Python 3.x | `python` 在 PATH 中 |
| `requests` 库 | `pip install requests` |
| OMS_PASSWORD | Windows 用户环境变量 |
| Tailscale | 公网访问（Funnel） |
| Windows 防火墙 | 入站规则开放端口 8500 |

## 部署清单（新电脑配置）

### 1. 复制文件
将 `850-toolbox/` 文件夹复制到目标电脑。

### 2. 安装 Python 依赖
```powershell
pip install requests
```

### 3. 设置 OMS 密码
```powershell
[Environment]::SetEnvironmentVariable('OMS_PASSWORD', '你的密码', 'User')
```

### 4. 启动
双击 `启动-静默.vbs`（或 `启动.bat` 看日志）。

### 5. 公网访问（可选）
安装 Tailscale → 登录 → 执行：
```powershell
& "C:\Program Files\Tailscale\tailscale.exe" funnel --bg 8500
```

### 6. 开机自启（可选）
`Win+R` → `shell:startup` → 放入 `启动-静默.vbs` 快捷方式。

## 故障排查

| 症状 | 检查 |
|------|------|
| 页面打不开 | `netstat -ano \| findstr 8500` 看 server 是否在跑 |
| 数据不更新 | 访问 `/api/health` 看 `last_result` 是否是 OK |
| 登录失败 | 确认 `OMS_PASSWORD` 环境变量正确，重启 server |
| 手机打不开 | 检查防火墙入站规则、同 WiFi、公网地址 |
| Funnel 失效 | `tailscale funnel status` 检查，需要时重新 `funnel --bg 8500` |
| 看板数字不准 | `python _verify_data.py` 校验原始 数据 |

## 密码更新

```powershell
[Environment]::SetEnvironmentVariable('OMS_PASSWORD', '新密码', 'User')
taskkill /f /im python.exe
# 然后重新启动 server
```

## 版本

当前版本：V3.3-pwa（2026-07-13）  
公网地址：`https://yumin.taila2a2ad.ts.net`
