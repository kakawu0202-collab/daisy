---
name: priority-sort-tool
description: 智能优先级排序工具 v3——FastAPI服务器+浏览器前端，支持层级排序链、例外管理、MSBD覆盖、语音控制
metadata: 
  node_type: memory
  type: project
  updated: 2026-07-02
  originSessionId: 51f8955d-e6f2-41b3-bd7e-c8ca576e12ba
---

# 智能优先级排序工具 v3

## 启动

```powershell
python d:\workspace\intelligent_sort\server.py --port 8766
```

浏览器打开 `http://127.0.0.1:8766`

## 项目结构

```
d:\workspace\intelligent_sort\
  server.py              FastAPI 服务器（HTTP API + WebSocket）
  sort_engine.py         排序引擎（层级排序链 + 例外 + MSBD覆盖 + 持久化）
  command_parser.py      命令解析器（中文关键词匹配 + LLM 回退）
  static/
    index.html           前端（语音条 + 排序链面板 + 例外管理 + 48列数据表）
```

数据来源：`d:\workspace\850PO_data\pull_XXX\RPT_850_PO.json`（自动选取最新有数据的 pull 目录）

## 排序链（从高到低，每层可开关+调整方向）

| 层 | 内容 | 默认 |
|------|------|------|
| 🔴例外置顶 | 手动指定PO强制排最前 | — |
| ①订单类型 | CTO P1 → CTO P2 → RTL → FGA（可拖拽调序） | 启用，组内按MSBD |
| ②MSBD | 物料齐套日期（早→晚/晚→早可选） | 启用 |
| ③接单时间 | PO_RECEIVE_DATE（早→晚/晚→早可选） | 启用 |
| ④Ship Mode | ✈️Air → 🚛Ground → 🚢Sea → 📦PA（可拖拽调序） | 启用 |
| 🟢例外置底 | 手动指定PO强制排最后 | — |

## 例外管理（持久化到文件，手动删除才消失）

| 类型 | 文件 | 说明 |
|------|------|------|
| 强制置顶 | `850PO_sort/exceptions.json` | 指定PO排最前，支持批量输入（逗号/换行分隔） |
| 强制置底 | 同上 | 指定PO排最后 |
| MSBD覆盖 | 同上 | 记录原MSBD+调整后MSBD，排序用调整值，原值灰字对比保留，不回写OMS |

## 界面功能

| 功能 | 操作 |
|------|------|
| 🎤语音控制 | 空格键说话 → Web Speech API识别 → 自动执行（Chrome/Edge） |
| ⌨️文字命令 | 输入框输入 → Enter发送 → 关键词匹配 |
| 排序链调整 | 拖拽类型/ShipMode标签调序，点「启用/关闭」开关，下拉改方向 |
| 例外操作 | 输入PO号+原因 → 置顶/置底；填PO+新日期 → MSBD覆盖 |
| 48列数据 | 左右滚动查看全部字段，自动列宽 |
| 分页 | 100行/页，← → 翻页 |
| 导出 | CSV + Excel(.xls) |
| WebSocket | 实时同步，服务器推送 |

## 语音/文字命令（关键词匹配，无需API Key）

常用命令：显示NACK的、显示Hold订单、显示CTO P1、按PSD排序、按优先级排序、空运的、APJ区域的、DNZA的、切换到小C/小O模式、导出CSV/Excel、恢复默认

## API Key 扩展

设置 `ANTHROPIC_API_KEY` 环境变量后，复杂自然语言命令走 Claude API 解析（如"把快超期的CTO订单提到最前面"），否则只走关键词匹配。

## 数据

- 2453条 PRD 订单（pull_20260626223432）
- 字段：PO、PO_LINE、DELL_SO、DPN、IPN、DESCRIPTION、PRIORITY、SUB_TYPE、MASTER_TYPE、PWA_TYPE、SSC_TYPE、PO_QTY、REMAIN_QTY、SHIP_QTY、PALLET_QTY、CARTON_QTY、PSD、MSBD、FINAL_MSBD、ORIGINAL_ESD、FINAL_ESD、PO_RECEIVE_DATE、STATUS、ACK_STATUS、IS_HOLD、HOLD_CODE、ERROR_MSG、IS_CANCEL、C-ID、C-QTY、SHIP_MODE、SCAC、SHIP_TO_COUNTRY、REGION、CUST、MCID、LAST_MCID、VALIDATION_STATUS、MODEL_ID、CFS_SERVICE_TYPE、ASN、HAWB、PALLET_TYPE、NETWEIGHT、GROSSWEIGHT、VW_KG_OR_CBM_M3、MEASUREMENTS_CM、NUM
- CTO P1: 1798条 | CTO P2: 141条 | RTL: 487条 | FGA: 27条
- 优先级分布：PRIORITY=1 (1825条), PRIORITY=2 (628条)

## 关联

- [[oms-workflow-v2]]
- [[role-assignment]]
- [[k1-prd-dashboard]]
