---
name: 850-toolbox-pwa
description: 850 Toolbox V4.1 PWA+公网+账号+ASN口径已出货+CTO28H精确匹配（2026-07-22）
metadata: 
  node_type: memory
  type: project
  updated: 2026-07-22
  originSessionId: ddb7381f-26f9-4a3d-9f81-709809c70d25
---

# 850 Toolbox V4.1

## 访问地址
- **公网**: `https://yumin.taila2a2ad.ts.net`
- **K1 看板**: `/k1.html`
- **管理员**: `/admin.html`（密码 `TOOLBOX_ADMIN` 环境变量，默认 `admin850`）
- **登录**: 自动跳转 `/login.html`

## V4.1 关键改动

### 已出货口径（ASN 报告）
- 总数: ASN 报告 S+SN ACK 的 QTY，仅 PRD
- 分类: ASN QTY 按 Shipment SHIP_QTY 比例拆分到 CTO P1/FGA/RTL/CTO P2
- 出货历史: 同步改为 ASN QTY

### CTO P1 28H 精确匹配
- 计划 = PO_RECEIVE_DATE + 28H
- 已出货 = 同一 28H 截止日的 PO 中 ACTUAL_SHIPPED=True 的数量
- 自动隐藏已完成和空柱子
- 范围从最早未出货到最晚未出货

### Backlog 逻辑
- 已出货只含 SN_STATUS = S 或 SN ACK
- NONE ASN = ASN待S，留在 Backlog，不计入已出货
- Backlog 卡片自动显示 ASN待S 数量

### MSBD & CTO 28H 过滤
- 过去已完成的日期自动隐藏
- 只显示未完成的

### 生产状态
- 移除 SN 列（只留 STBL/ATB/WIP/FG）
- 增加合计行

### 其他
- 移除发送飞书按钮
- SN S 当日按 SHIP_DATE 自然天计算
- 出货(Shipment)用自然天，收单用 VN 5:00-5:00

## 账号系统
- 自助注册 → 管理员审批 → 30天免登
- 用户数据: `data/users.db` (SQLite)
- 禁用即踢下线

## 环境变量
```
OMS_PASSWORD      — OMS 密码
TOOLBOX_ADMIN     — 管理后台密码（默认 admin850）
```

## 部署
1. 复制 850-toolbox 文件夹
2. `pip install requests`
3. 设置 OMS_PASSWORD + TOOLBOX_ADMIN 环境变量
4. 双击 启动-静默.vbs

## 备份
- `850toolbox-V4-20260721.zip`

## 关联
- [[850-toolbox]]
- [[k1-prd-dashboard]]
- [[oms-workflow-v2]]
