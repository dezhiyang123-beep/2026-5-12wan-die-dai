---
name: concept-card
description: 概念卡生成SOP。被conceptor调用。定义人格驱动流程、TRIZ矛盾提取、概念卡模板、同质性检查规则。
---

# concept-card — 概念卡生成SOP

## 人格驱动流程

读取 `knowledge/perspectives/personas-8.md`，对每个选定人格执行：

**Step 1：读取人格的价值函数**
价值函数 = 该人格最大化什么，绝对排除什么

**Step 2：用驱动问题确定核心主张**
驱动问题是该人格面对这个品类会问的第一个问题。
用驱动问题的答案确定概念的核心主张（不可替代点）。

**Step 3：用绝对排除做负向过滤**
把概念中违背该人格绝对排除原则的元素去掉。
（例：Rams人格会去掉所有装饰性元素）

**Step 4：用价值函数验证**
检查：这个概念最大化的指标，是否符合该人格的价值函数？
输出匹配度：高/中/低。低匹配度需说明原因或重新生成。

## TRIZ矛盾提取精简流程

读取 `knowledge/methods/triz-core.md`：

1. **找改善参数**：从选定方向的behavioral_contradiction中提取"要提升的X"
2. **找恶化参数**：改善X会导致什么Y变差
3. **输出矛盾陈述**：`要提升[X]，但会导致[Y]变差`
4. **给2个解法方向**：
   - 方向A：从材料/结构层面解
   - 方向B：从用户行为/使用模式层面解

TRIZ驱动的概念：每个解法方向出1个概念，进入概念总数。

## 概念卡输出模板

```yaml
concept_id: C-0X
driven_by: "[人格名] 或 TRIZ矛盾解法[A/B]"
title: "[10字以内]"
core_concept: "[核心概念描述，≤100字]"
decision_core: "[去掉这个点它就变成别的东西——不可替代点]"
counterfactual: "[如果不这样做，用户会[具体后果]]"
differentiator: "[和[竞品名]相比，[具体差异]——必须引用竞品名]"
structure_path: "[核心实现方式，2句话]"
bom_estimate: "$X-Y [超价格带25%标'激进备选']"
dfm_flag: "[最大制造风险，1句话]"
dfm_verdict: "PASS / FAIL / CONDITIONAL"
```

**字数控制**：core_concept + decision_core + counterfactual + differentiator + structure_path ≤ 200字总计

## 同质性检查规则

检查时机：所有概念生成后，输出前。

检查标准：如果≥3个概念满足以下任意2条：
- structure_path描述的核心机制相同（如都是"折叠结构"）
- differentiator引用同一竞品且差异点相同
- driven_by是同类思考起点

触发时：替换相似度最高的概念，改用人格库中未使用的人格重新生成。

## BOM超标处理

BOM > 目标价格带 × 125%：
- 标注：`[激进备选，BOM超标]`
- 在dfm_flag中追加：`BOM超出目标价格带XX%`
- 仍保留在候选中，让用户判断
