---
name: k1-prd-dashboard
description: K1 PRD看板飞书同步——Webhook推送+文档更新 完整流程
metadata: 
  node_type: memory
  type: project
  updated: 2026-06-21
  originSessionId: 30fc2640-2d8d-4bf4-8cad-ccd53b5edac8
---

# K1 PRD 看板 — 飞书同步流程

## 通道一览

| 通道 | 方式 | 状态 |
|------|------|:---:|
| LuxOMS AI 群推送 | Ka姐 Webhook (V2) | ✅ |
| 飞书文档更新 | lark-cli docs +update | ✅ |
| 群消息读取 | lark-cli --profile cli_aa86c52155b89bde | ✅ |

## Ka姐 Bot — 统一消息推送

- **App ID**: `cli_aa86c52155b89bde`
- **Bot**: Ka姐 | open_id: `ou_c140ed94199e6c2d259db0ca131ef8de`
- **统一脚本**: `d:\workspace\ka_send.py`
- **方式**: 全部通过 Bot API（不再用 Webhook）

### 发送命令

```powershell
python ka_send.py dashboard              # 发仪表盘截图 + 文档链接
python ka_send.py text "消息内容"         # 发纯文本
python ka_send.py image path.png         # 发图片
python ka_send.py card '{"header":...}'  # 发卡片消息
```

### 关键细节
- content 必须是 JSON **字符串**（`json.dumps(obj)`），不是 JSON 对象
- 图片先上传 IM API 拿 image_key，再发消息

## 飞书文档更新

- **文档**: `https://ucnywv6jgnkh.feishu.cn/docx/LI1sdNFhloUD91xuk4GcZ0ivnod`
- **Doc Token**: `LI1sdNFhloUD91xuk4GcZ0ivnod`

```powershell
lark-cli --profile cli_aa86c52155b89bde docs +update --doc LI1sdNFhloUD91xuk4GcZ0ivnod --api-version v2 --command overwrite --content <markdown内容> --as user
```

## 完整更新流程

当用户通知"更新K1看板"时：

### Step 1: 拉取最新数据
```powershell
.\oms_pull.ps1
```

### Step 2: 分析生成 K1 Markdown
按 M1(订单总数/CTO P1) + M2(Backlog) + M3(出货预计) 结构生成

### Step 3: 推送到群（Ka姐 Webhook）
使用上述 Webhook 模板发送摘要

### Step 4: 更新飞书文档
使用 `lark-cli --profile cli_aa86c52155b89bde docs +update --command overwrite`

## Profile 管理

```powershell
lark-cli profile list                                    # 查看所有 profile
lark-cli --profile cli_aa86c52155b89bde <command>        # 用用户身份
lark-cli --profile bot <command>                         # 用 bot 身份(Kaka的智能助手)
```

## 关联

- [[oms-workflow-v2]]
- [[role-assignment]]
