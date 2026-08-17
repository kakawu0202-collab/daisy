---
name: luxoms-workflow
description: OMS数据拉取标准工作流——API已全通，一键拉取无需RPA
metadata: 
  node_type: memory
  type: reference
  originSessionId: 388b22e5-13cf-4c15-a33e-41e298beef91
---

# LuxOMS 数据工作流

## 系统信息
- URL: http://luxoms-vn-prod.luxshare-ict.com
- 账户: 31000161
- 密码: 存于 Windows 用户环境变量 `OMS_PASSWORD`，通过 `[Environment]::GetEnvironmentVariable('OMS_PASSWORD','User')` 读取
- 认证: POST /api/auth/login → token 头 → 所有业务API

## 标准拉取
```powershell
.\oms_pull.ps1    # 一键拉取全部27项数据到 pull_YYYYMMDDHHMMSS/
```

## API架构（全部通过 token 头认证）
- Dashboard: GET /api/Dashboard/* (公开)
- 订单: POST /api/OrderManagement/GetOrderDetails (CUST=DAISY)
- 出货: POST /api/ShipmentManagement/* (CUST=DAISY, CORP=3100)
- 报表: POST /api/ReportSetting/QueryDynamicReport (report_id + sql + fields)

## 菜单结构
- Order Management (7项): 850Processing, 860Processing, Order Operation, Hold PO, 850 PO, Ship Plan, RawFileDownload
- Shipment Management (4项): OpenShipment, Shipment Operation, Truck Info, COPO
- Report (16项): PO Report, PSD Report, ShipmentInfo, BOM, DAISY_ASN_STATUS, DAISY_SHORTACK_LIST, DAISY_SHIPMENT_REPORT, BOOKING, SHIPMENT_PALLET, ORDER_PALLET, DPN DAILY, AIR FORECAST, E2E Report, SHIPPING TRACKING, GPP Report, BAM

## 链接
- 数据目录: [[../../planning-kb/04-订单管理/850PO数据/README|README]]
- 上次分析: [[luxoms-credentials]]
- 角色: [[role-assignment]] (小O负责)
