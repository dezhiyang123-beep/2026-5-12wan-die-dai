---
name: direction-space
description: 方向研判SOP。被strategist调用。定义方向结构、反论据规则、行为矛盾提取、form_handoff_brief 6字段要求。
---

# direction-space — 方向研判SOP

## 方向生成规则

输出2-3个方向，方向之间必须在 `core_value` 层面结构性不同（不是同一思路的变体）。

## 每个方向必须包含的字段

```yaml
directions:
  - name: "D-A: [简短名称]"
    core_value: "[核心价值主张，1句话，去掉就变成别的东西]"
    target_user: "[具体目标用户描述]"
    buying_reason: "[用户购买的真实理由，非设计师自嗨]"
    cost_tier: "[成本层级：$X-Y BOM]"
    max_risk: "[最大风险点，1句话]"
    oem_fit: "high / medium / low"
    counter_argument: "[为什么这个方向可能是错的，≥1条，必填]"
    behavior_contradiction: "[行为矛盾，格式：要[A]就损失[B]]"
    form_handoff_brief:
      visual_signal_to_embody: "[≥15字，具体视觉信号]"
      installation_context: "[安装场景物理约束]"
      engineering_redline: "[不可逾越的工程红线]"
      cost_ceiling_per_unit: "$X.XX"
      must_not_look_like: "[1-3个参照物]"
      must_keep_customer_signal: "[客户品牌识别信号]"
```

## form_handoff_brief 6字段规则

- 6个字段**全部必填**，不接受UNKNOWN
- 任一字段为UNKNOWN→回G1补充信息，不得进入G3造型
- `visual_signal_to_embody` 必须≥15字，描述具体，不接受"现代感"/"简洁"等通用词
- `cost_ceiling_per_unit` 必须有计算依据（目标零售价×推算BOM占比）

## 行为矛盾提取方法

从 `02_user_action_map.yaml` 的 `error_scenarios` 和 `pain_points` 中提取：
格式：`要[功能A的用户利益]就损失[功能B的用户利益]`
示例：`要安装便捷就损失防水可靠性` / `要亮度够就损失便携重量`

## 反论据规则

- counter_argument 不得为空
- 反论据必须针对该方向的核心假设（不是次要细节）
- 示例：`竞品[X]已经验证了这个方向，但售价更低，本方向的溢价空间存疑 [M]`

## strategist_recommendation

```yaml
strategist_recommendation:
  pick: "D-A / D-B / D-C"
  reason: "[推荐理由，≤2句话，基于商务逻辑]"
  might_be_wrong: "[推荐可能错在哪，≤1句话，必填]"
```

## 禁止事项

- 输出超过3个方向
- counter_argument为空
- form_handoff_brief任一字段为UNKNOWN
- 方向之间core_value高度相似
- strategist_recommendation不填might_be_wrong
