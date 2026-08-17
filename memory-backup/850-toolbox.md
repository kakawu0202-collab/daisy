---
name: 850-toolbox
description: 850 Toolbox v3.3 — K1双Tab看板(PRD+当日)+排序+出货历史+无窗口EXE
metadata: 
  node_type: memory
  type: project
  updated: 2026-07-10
  originSessionId: 51f8955d-e6f2-41b3-bd7e-c8ca576e12ba
---

# 850 Toolbox v2.0

## 概述

本地 Web 工具箱，双击即用。整合 OMS 数据拉取、K1 PRD 看板（V2）、优先级排序、出货历史。

## 启动

**分发版（免 Python）：**
- 双击 `d:\workspace\850-toolbox\dist\850-Toolbox\850-Toolbox.exe`
- 自动打开 `http://localhost:8500`

**开发版：**
- `cd d:\workspace\850-toolbox && python server.py`

## 文件结构

```
850-toolbox/
  server.py              HTTP 服务器（OMS 代理 + 数据缓存 + 所有 API）
  _launcher.py           PyInstaller 打包入口
  启动.bat               开发版启动
  static/
    index.html           工具箱首页（OMS 刷新 + 工具入口）
    sort.html            优先级排序工具
    k1.html              K1 PRD 看板 V2
    shipped.html         出货历史
  dist/850-Toolbox/      免 Python 分发版
```

## 功能矩阵

| 工具 | 功能 |
|------|------|
| 首页 | OMS 账号密码输入 + 一键拉取 5 个报告（850/E2E/GPP/ASN/Shipment） |
| K1 看板 V2 | 4 KPI + 出货统计 + 类型×区域 + 生产状态 + MSBD/CTO P1 图表 + 悬浮日期筛选 + 全卡片下钻 + 飞书推送 |
| 优先级排序 | CTO P1 分组 → 订单类型 → MSBD → Ship Mode + 例外管理 + OMS 数据加载 |
| 出货历史 | 按天/周/月/季/年统计出货量柱状图 |
| **870 FGA 优先级分配** | 同 IPN+MCID 组内分配；850 从 OMS，Hold/Status **上传** CSV；扁平结果表 + remark + 导出（2026-07-11） |

## 870 FGA 分配（新增 2026-07-11）

**页面**：`static/fga870.html`（首页有入口卡片）
**引擎**：`fga870_allocate.py`（复制自 `d:\workspace\fga870`，纯逻辑无依赖）+ `fga870_loader.py`（850行+CSV→PO）
**server 端点**：
- `GET /api/fga-status` — 850/Hold/Status 就绪状态
- `POST /api/fga-upload` `{type:'hold'|'status', content}` — 上传 CSV（存 data/fga_hold.csv、fga_status.csv）
- `GET /api/fga-allocate` — 用缓存 rpt_850_po(FGA) + 上传的两表跑分配，返回 JSON

**用法**：首页刷新 OMS（拿 850）→ 开 870 FGA → 上传 T_HOLD_PO.csv + T_STATUS_PO.csv → 运行分配。

**分配算法要点**（详见 [[fga870-allocation]]）：好产出 SS/BS/SCH 上浮高优先级；缺料 A11 按材料从最低 PO 往上集中(MAX,展示前3)；A05 质量hold 落最低有产出PO、吃BS/SS、溢出SCH/ACK报alert；ACK=残差；逐 PO 平衡。真实数据 29 FGA PO 全平衡。

⚠ 引擎在 toolbox 有独立副本，改算法需同步 `d:\workspace\fga870\fga870_allocate.py`。

**EXE 重打包**（PyInstaller 6.16，onedir）：
- `_launcher.py` 已补 `server.FGA_HOLD_FILE`/`server.FGA_STATUS_FILE` 路径覆盖（冻结后必须）；`850-toolbox.spec` 的 hiddenimports 已含 `fga870_loader`/`fga870_allocate`。
- 命令：`cd d:\workspace\850-toolbox; python -m PyInstaller 850-toolbox.spec --noconfirm --clean; Copy-Item static dist\850-Toolbox\static -Recurse -Force`（static 不在 spec datas 里，需手动拷到 exe 同级；data 初始化为空）。
- 产物：`dist\850-Toolbox\`（29MB，双击 850-Toolbox.exe）。验证：`/api/fga-allocate` 返回"无850数据"而非"模块未加载"即模块已 bundle。
- FGA 只用 CSV+OMS-JSON，不需要 openpyxl（openpyxl 仅独立版读 Excel 用）。

## K1 V2 功能详情

### 卡片
- 4 KPI 卡片（订单总数/已出货/Backlog/NACK）→ 下钻弹出明细
- CTO P1 出货 + 其他订单出货
- 类型 × 区域分布（表格 + 堆叠柱状图）
- 生产状态（STBL/ATB/WIP/FG/SN = GPP 状态，基于 E2E 计算）
- MSBD 出货计划（未完成 + 未来 7 天柱状图）
- CTO P1 28H 出货计划（PO received + 28H 柱状图）

### 筛选
- 右侧悬浮侧边栏：📥 PO 接收 和 📅 MSBD 两个日期筛选
- 每个筛选独立影响对应卡片组
- Apply（蓝底白字）/ Clear（灰底黄字）按钮

### 下钻
- 点击任何 KPI 数字 / 出货统计 / 区域表格 / 生产状态数字 → 弹窗显示 500 条明细
- 19 列完整字段（PO/PO_LINE/DELL_SO/DPN/IPN/PO_QTY/MSBD/PSD/SN_CDT/REGION/STATUS_LABEL/ASN/HAWB...）
- 📥 CSV 下载按钮

### 飞书推送
- K1 右上角「📤 发送飞书」→ 推送摘要到 LuxOMS AI 群

## 数据源

| 报告 | ID | 用途 |
|------|------|------|
| RPT_850_PO | 0848012288 | 订单主数据 |
| RPT_E2E | 1593920512 | 生产站别状态 |
| RPT_GPP | 0320073728 | 物料齐套（常超时，用 E2E 替代） |
| RPT_ASN_Status | 0886717440 | ASN 出货状态 |
| RPT_Shipment_Rpt | 1780017152 | 出货明细（SHIP_DATE + SHIP_QTY） |

## 实际出货判断

```
ACTUAL_SHIPPED = (SN_STATUS = 'S' in ASN report) OR (SHIP_DATE non-empty in Shipment report)
```

MSBD 计划中 actual 列 = ACTUAL_SHIPPED PO 的 PO_QTY 合计。

## 生产状态（E2E 计算）

| 状态 | 判断 |
|------|------|
| STBL | 无任何站别活动 |
| ATB | 无 INPUT_CDT，有后续站别 |
| WIP | 有 INPUT_CDT，无 STOCKIN_CDT |
| FG | 有 STOCKIN_CDT，无 SN_CDT |
| SN | 有 SN_CDT |

## STATUS_LABEL 映射

| STATUS | ACK | SN_CDT | → 标签 |
|------|------|------|------|
| Open | ACCEPT | 无 | OPEN (Backlog) |
| E | - | - | V (校验中未pass) |
| ZC | - | - | ZC (已取消) |
| Close | - | - | CLOSE (正常关闭) |
| 任意 | REJECT | - | NACK (被拒绝) |

## 分发

- 免 Python：复制 `dist/850-Toolbox` 文件夹 → 双击 exe（13MB，内含 Python 运行时）
- 有 Python：复制整个 `850-toolbox` 文件夹 → 双击 `启动.bat`

## 关联

- [[priority-sort-tool]]
- [[oms-workflow-v2]]
- [[k1-prd-dashboard]]
- [[role-assignment]]
