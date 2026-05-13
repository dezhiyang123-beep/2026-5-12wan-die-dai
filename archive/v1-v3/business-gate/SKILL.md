---
name: business-gate
description: 商务前提验证SOP。被strategist调用。定义OEM分流、4项硬门槛、HOLD规则、verdict输出格式。
---

# business-gate — 商务前提验证SOP

## OEM分流（G0执行）

根据 `client_type` 字段路由：

| client_type | G1重点 | G3方向要求 |
|------------|--------|-----------|
| oem_push | OEM开放度+采购价 | 包含"易被OEM接受的卖点" |
| brand_rd | 决策链+认证路径 | 可更激进 |

`client_type` 未填→停止G0，要求用户明确选择。

## 4项硬门槛验证

每项必须有可追溯证据，否则标UNKNOWN：

### 门槛1：OEM开放度
- 验证方式：有对话记录/邮件/采购记录
- UNKNOWN验证动作：发询价邮件，等待3-5个工作日回复
- 输出：`oem_openness: open/closed/unknown` + `oem_openness_evidence: [来源]`

### 门槛2：目标采购价格带
- 验证方式：客户档案/历史订单/竞品反推
- UNKNOWN验证动作：询价历史产品或竞品的采购单价
- 输出：`target_price_range: "$X-Y" [H/M/L]` + `target_price_evidence: [来源]`

### 门槛3：认证路径
- 验证方式：FCC/UL/CE数据库 + 目标渠道要求
- UNKNOWN验证动作：查询Home Depot/Amazon平台规定的认证要求
- 输出：`certification_required: [列表]` + `certification_path: clear/unclear/unknown`

### 门槛4：决策链（拍板人）
- 验证方式：有名字+职位+联系方式
- UNKNOWN验证动作：询问客户联系人谁有采购决策权
- 输出：`decision_chain.decision_maker: {name/title/contact}` 或 `UNKNOWN`

## HOLD判定规则

任一门槛为UNKNOWN→输出：
```yaml
verdict: hold
hold_action: "[最小验证动作，格式：动作+预计耗时+负责人]"
```

全部门槛有证据→进入verdict判断：
```yaml
verdict: go / stop
verdict_reason: "[1-2句话，基于证据]"
```

`stop` 判定条件：oem_openness=closed 且无其他渠道；或 target_price_range 无法支持盈利。

## counter_evidence要求

每个verdict必须附counter_evidence（即使是go）：
```yaml
counter_evidence: "[可能让这个判断错误的信息，1句话]"
```

## 禁止事项

- 任一门槛UNKNOWN时输出go
- verdict不附counter_evidence
- 用推断填充硬门槛字段
