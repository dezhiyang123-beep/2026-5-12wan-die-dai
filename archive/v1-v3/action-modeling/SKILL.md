---
name: action-modeling
description: 用户动作建模SOP。被strategist调用。定义6问题框架、工时估算、G2硬门槛4项、buyer_map结构。
---

# action-modeling — 用户动作建模SOP

## 6问题框架

对每个角色（安装者/操作者/维护者）逐一执行：

1. **谁来做**（who）：具体职业/年龄/技能水平
2. **做什么动作**（action_chain）：按时间顺序列出每个步骤，动词开头
3. **用什么工具**（tools_needed）：列出每步骤所需工具
4. **花多少时间**（time_estimate）：每步骤时间 + 总时间
5. **什么地方会出错**（error_scenarios）：≥2个具体失误场景
6. **感受到的价值**（value_assessment）：用户在哪个动作节点感受到价值

## 工时估算方法

```yaml
total_labor_estimate:
  per_unit_install: "X分钟/件 [M]"
  per_site_install: "Y小时/项目 [M]（N件×X分钟）"
  per_week_operate: "Z分钟/周 [M]"
  labor_cost_implication: "$X/项目（按当地人工成本计算）[L]"
```

工时估算来源优先级：
1. 用户访谈/现场观察 [H]
2. 类比同品类安装时间 [M]
3. 理论估算 [L]

## G2四项硬门槛（任一UNKNOWN→HOLD）

1. `installer.who`：安装者是谁（有具体描述，不接受"专业人员"）
2. `operator.who`：操作者是谁（有具体描述）
3. `value_assessment`：用户在哪个节点感受到价值（有具体动作描述）
4. `buyer_map.payer`：谁付钱（个人/企业/项目方，有确认）

## action_chain输出格式

```yaml
installer:
  who: "电工师傅，35-50岁，有基础工具使用经验"
  action_chain:
    - step: 1
      action: "关闭电源，用验电笔确认断电"
      tool: "验电笔"
      time_min: 2
    - step: 2
      action: "取出固定支架，对准安装孔位"
      tool: "无"
      time_min: 3
  tools_needed: ["验电笔", "螺丝刀", "电钻"]
  total_time_per_unit: "15分钟 [M]"
  total_time_per_site: "3小时（12件）[M]"
```

## buyer_map输出格式

```yaml
buyer_map:
  value_perceiver: "谁感受到价值（用户）"
  payer: "谁付钱（个人/企业/项目方）[必填]"
  decision_process: "从发现需求到下单的步骤"
  roi_impact_points: ["影响ROI的关键节点"]
  current_alternatives: ["目前替代方案"]
  switching_cost: "从替代方案切换的成本/阻力"
```

## 禁止事项

- installer.who / operator.who 填"专业人员"等模糊描述
- value_assessment 没有具体动作节点
- 工时估算不标置信度
- buyer_map.payer 为UNKNOWN时不HOLD
