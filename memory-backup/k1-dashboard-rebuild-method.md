---
name: k1-dashboard-rebuild-method
description: K1仪表盘HTML重建的正确方法——从数据生成完整HTML，不修补
metadata: 
  node_type: memory
  type: project
  updated: 2026-07-04
  originSessionId: 30fc2640-2d8d-4bf4-8cad-ccd53b5edac8
---

# K1 仪表盘 HTML 重建方法

## 核心原则

**不修补旧HTML，直接从最新数据生成全新HTML。**

之前多次失败的原因：用 `str.replace()` 修补旧HTML，但文件被多次部分修改后数字混乱，且Python内联命令的转义问题导致替换失败。

## 正确流程

### Step 1: 拉数据
```powershell
.\oms_pull.ps1  # 拉取 Order/Shipment 数据
# 然后手动修复 Report 拉取（加 reportName 字段）
```

### Step 2: 修复 Report 拉取
Report API 新增了 `reportName` 必填字段。在 QueryDynamicReport body 中加：
```json
{
  "reportName": "850 PO_DAISY",  // 或 "E2E Report_DAISY" 等
  "report_id": "...",
  "pagination": {"page": 1, "pageSize": 10000},
  "parameters": {},
  "parentContext": null,
  "sql": "...",
  "fields": [...]
}
```

### Step 3: 生成 HTML
用 `d:\workspace\rebuild_k1_html.py` —— 它：
- 读取 RPT_850_PO.json + RPT_E2E.json
- 计算所有 K1 指标（总数、已出、未出、NACK、区域分布、类型分布、CTO P1、Backlog ATB/WIP/FG）
- 用 `w()` 函数逐行写入 HTML（避免 f-string 与 JS `{}` 冲突）
- JS 代码放在多行 f-string 中，`{{}}` 自动转义为 `{}`

### Step 4: 渲染 + 推送
```powershell
python render_vc.py     # Playwright 截图
python ka_send.py dashboard  # Ka姐推送图片+链接
```

## 关键脚本

| 脚本 | 用途 |
|------|------|
| `rebuild_k1_html.py` | 从数据生成完整 K1 HTML |
| `render_vc.py` | Playwright 渲染 HTML → PNG |
| `ka_send.py dashboard` | 推送截图 + 文档链接到群 |
| `gen_k1_data.py` | 生成 K1 Markdown（纯数据，不含推送） |

## 注意

- 不要用 `python -c "..."` 内联命令，PowerShell 5.1 对引号/转义处理有严重问题
- 不要在旧 HTML 上 `str.replace()`，每次重新生成
- Report API 需要 `reportName` 字段（2026-06-25 起）
- FGA WIP 计算：INPUT+AFT+OBE+REPAIR+SWDL+LABEL，不含 SS
- 排除 ZC/Close/已出货(SN>0) 的订单

## 关联

- [[k1-prd-dashboard]]
- [[oms-workflow-v2]]
