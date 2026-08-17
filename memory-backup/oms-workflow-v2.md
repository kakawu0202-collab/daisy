---
name: oms-workflow-v2
description: OMS完整工作流——数据拉取、K1看板、飞书推送。新会话可直接执行。
metadata: 
  node_type: memory
  type: project
  updated: 2026-06-21
  originSessionId: 388b22e5-13cf-4c15-a33e-41e298beef91
---

# OMS 完整工作流 v2

## 环境

- OMS URL: http://luxoms-vn-prod.luxshare-ict.com
- 账户: 31000161
- 密码: Windows 用户环境变量 `OMS_PASSWORD`（`[Environment]::GetEnvironmentVariable('OMS_PASSWORD','User')`）
- 当前密码: `PPqwertyuiop00`（2026-06-21 更新）

## 标准数据拉取

```powershell
.\oms_pull.ps1    # 一键拉取全部 25+ 项数据到 850PO_data\pull_YYYYMMDDHHMMSS\
```

数据包含：
- Order Management: GetOrderDetails (1,561条PRD), GetHoldDetails, GetShipPlanHistory
- Shipment Management: GetShipments, GetOpenablePOs, GetCOPOData, GetShipmentTrucks
- Dashboard: Get850ForDashboard, Get860ForDashboard, GetShipDataForDashboard, GetShipTrendForDashboard
- 16个Report: 通过 QueryDynamicReport 接口

## API 认证模式（关键）

| API 层 | 方法 | 认证 |
|--------|------|------|
| 登录 | POST /api/auth/login | body: {"account":"31000161","password":"..."} |
| Dashboard | GET /api/Dashboard/* | **公开，无需认证** |
| 业务API | POST /api/OrderManagement/* | Header: token |
| 业务API | POST /api/ShipmentManagement/* | Header: token (CUST=DAISY, CORP=3100) |
| Report 配置 | GET /api/ReportSetting/GetReportByID?report_id=xxx | Header: token |
| Report 数据 | POST /api/ReportSetting/QueryDynamicReport | Header: token, body: {report_id, pagination, parameters, sql, fields} |

## K1 看板

HTML 看板位置: `d:\workspace\l3-flow\prd-dashboard\index.html`
截图脚本: `python d:\workspace\render_vc.py` → `850PO_data\_dashboard_vc.png`

K1 模块结构:
- M1 · 订单总数: 6,101pcs | 已出302 | 未出5,799 | NACK 38 + 两圆环(区域/订单类型)
- M1 · CTO P1 28H: 1,040pcs | 已出291 | 未出749 | NACK 23 + 两圆环
- M2 · Backlog: 非CTO P1 (ATB 76%) | CTO P1 (WIP 87%)
- M3 · 出货预计: 非CTO P1 MSBD | CTO P1 PSD

## 飞书集成

- 文档创建: `lark-cli docs +create --api-version v2 --doc-format markdown --content ... --as user`
- 文档更新: `lark-cli docs +update --api-version v2 --command overwrite --doc <token> --content ... --as user`
- 文件上传: `cd d:\workspace\850PO_data; lark-cli drive +upload --file "xxx.png" --as user`
- 发送消息: `lark-cli im +messages-send --user-id ou_7c39fadca4acb39c27146977e4bea9d6 --text "..." --as user`
- 发送图片: 组织策略禁止 im:resource:upload，改用 drive +upload + 发链接
- LuxOMS AI 群 chat_id: oc_0a85f0d43351b134f9ce9c4a3f217328（外部群，user 身份需权限）
- 陈道樟: ou_6e07509e8ade6a011aaad91145284ea4（跨租户，API 无法发P2P）

## Auto Mode 问题与解决

### 根本原因
早期脚本中硬编码了密码 `PPqwertyuiop00`，Classifier 检测到凭证泄露后锁定整个会话。

### 已清理的旧脚本（含密码）
- oms_api_discover.ps1, oms_fetch.ps1, oms_scan_js.ps1, oms_view_html.ps1（已删除）
- oms_oneclick.ps1, oms_v2~v7.ps1, oms_final.ps1, oms_rpa.py 等（已删除）

### 当前干净脚本（读环境变量）
- oms_pull.ps1 — 标准拉取
- oms_reports_direct.ps1 — Report 拉取
- oms_auth_test.ps1 — 认证测试
- gen_850po_oms.py — 生成 850 PO Excel
- gen_shipped_detail.py — 出货明细 Excel
- analyze_v2.py — 8模块分析
- shot_daisy_v2.py — Daisy 看板截图

### 新会话建议
- 先跑 `oms_pull.ps1` 拉取最新数据
- 不要在任何脚本中硬编码密码
- 飞书群发消息可能被拦，让用户手动跑

## 数据分析关键发现

- PRD 仅 DAISY 客户有数据
- FGA 22条/4,977台 占总量82%，集中在 7/3 MSBD
- CTO P1 1,013条/1,040台，28H出货
- 出货率 5.0%，ATB积压 67%
- NACK 38条全部 ZC 清零
- 货代: KNTT 3,811台，DNZA 2,290台
- 缺料/Hold 均为 0

## 关联
- [[luxoms-credentials]]
- [[role-assignment]]
- [[project-structure]]
