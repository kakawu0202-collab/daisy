---
name: fga870-allocation
description: 870 FGA 优先级分配的完整业务规则与算法（多轮与用户确认后定稿）
metadata: 
  node_type: memory
  type: project
  updated: 2026-07-11
  originSessionId: a8494c1f-a46e-4073-9c2e-88fb668c8911
---

# 870 FGA 优先级分配 —— 业务规则与算法

**代码**：独立版 `d:\workspace\fga870\`（allocate 引擎 + run loader + test 33断言）；toolbox 版见 [[850-toolbox]]。
**"870"** = Dell 缺料 hold code 系列（A11→A12/A14 演进）。

## 数据源（真实字段）
- **T_STATUS_PO**（好产出）：`AC_PO/AC_PO_LINE/STATUS_CODE/KEY_QTY`。SS/BS/SCH 带真实数量，按 PO 汇总。**是累计里程碑不是分区**（SCH→BS→SS 按 STATUS_TIME，SS_cum≈PO_QTY），直接相加会超量。GCF/LDA/C01-03=0量事件忽略，LABEL/LASER 忽略。
- **T_HOLD_PO**（缺口）：`AC_PO/HOLD_TYPE(OH取,IH忽略)/HOLD_CODE/HOLD_REASON/KEY_REF/KEY_QTY/FLAG(取H)`。A11/A12/A14=缺料(KEY_REF=材料,KEY_QTY=缺量)；A01/A05=质量hold(KEY_QTY=hold量,真实有效)；A32=整单锁。
- **850 主数据**：IPN/MCID/MSBD/PO_QTY/SHIP_QTY/SUB_TYPE(=FGA)/IS_CANCEL/STATUS。scope=FGA 且未取消、PO_QTY>0、STATUS 非 NACK/ZC/CLOSE。

## 折算当前态（loader）
每 PO：`SN=SHIP_QTY`；`open=PO_QTY-SN`；好产出 SS/BS/SCH 由累计里程碑差分(prod_ss=ss_cum-sn, prod_bs=bs_cum-ss_cum,...)、按 open 封顶；ACK 由引擎算残差；ASN 暂记0(fold入SN)。

## 分配（引擎，同 IPN+MCID 组内，MSBD 升序 P1最优先）
1. **好产出上浮**：SS/BS/SCH 池化，从 P1→Pn 依次喂满（单PO内 SS→BS→SCH）。
2. **A05/A01 质量hold 下沉**（生产中hold，只能落已产出货）：从最低优先、有 BS/SS 的 PO 往上灌，先吃该PO的BS/SS吃完再上移；溢出到 SCH 或 ACK → **报 alert**（hold了没造出的货）。
3. **缺料 A11 集中下沉**：同组材料共享（每PO都要用组内所有料，缺任一即整段不可产）。每种材料从最低优先 PO 往上灌，每PO每种料可占到其缺口(MAX 可叠加、溢出上抬)。平衡量=**MAX(各材料)**，展示前3种。
4. **ACK=残差**；**A32** 整单锁(qty-asn-sn)、好产出退回组内池。
5. 逐 PO 平衡：`ACK+SCH+BS+SS+ASN+SN+MAX(A11)+A05+A32 = PO_QTY`。

## 与用户确认的关键决策
- 好产出消耗顺序 SS→BS→SCH（SS 最ready先给高优先）。
- 缺料/hold 都下沉低优先；缺料按材料分别集中到最低PO，不是单一数量池。
- A05 是物理不良品/生产中hold → 落"最低有产出PO"、可跨PO移动（fungible FGA）。
- 缺料量用真实上报值，未被卡的余量转 ACK（不是拿整单当缺料）。
- remark 格式：`ACK-0,SCH-314,BS-0,SS-0,ASN-0,SN-0,A11-mat-qty,...,A05-20`。

## 关联
- [[850-toolbox]]
- [[oms-workflow-v2]]
