# /run-g3-directions — G3方向研判

## 命令说明

产出2-3个结构性不同的设计方向，每个方向包含完整的 form_handoff_brief。

## 前置检查

- `02_user_action_map.yaml` 和 `02_buyer_map.yaml` 必须存在
- G2硬门槛必须全部通过

## 执行步骤

**Step G3-1：调用 strategist + direction-space skill**

产出2-3个方向，每个方向必须包含：
- name / core_value / target_user / buying_reason / cost_tier / max_risk / oem_fit
- counter_argument（≥1条，针对核心假设）
- behavior_contradiction（格式：要[A]就损失[B]）
- form_handoff_brief（6个字段全部必填）

**Step G3-2：验证 form_handoff_brief 完整性**
- 6个字段全部有内容：visual_signal_to_embody / installation_context / engineering_redline / cost_ceiling_per_unit / must_not_look_like / must_keep_customer_signal
- 任一字段为UNKNOWN→停止，回G1补充

**Step G3-3：调用 reality-checker（review_mode: lite）**
- 验证counter_argument非空
- 验证form_handoff_brief 6字段非UNKNOWN
- 验证方向之间core_value结构性不同

**Step G3-4：strategist_recommendation**
- 推荐1个方向，同时填写 might_be_wrong

### 执行完成后

更新 `artifacts/projects/{project_id}/00_status_dashboard.md`：
- current_gate: G3（方向）
- gate_status: [待用户选择]
- next_action: "用户选定方向后执行 /run-g3-forms"

## 输出产物

- `artifacts/projects/{project_id}/03_direction_space.yaml`
- `artifacts/projects/{project_id}/00_status_dashboard.md`（更新）

## 关卡停止格式

```
━━━━━ G3方向 完成 ━━━━━
产物：03_direction_space.yaml
方向列表：
  D-A: [core_value一句话]
  D-B: [core_value一句话]
  D-C: [如有]
推荐：[D-X]（可能错在：[might_be_wrong]）
决策点：请明确选择方向，然后执行 /run-g3-forms
━━━━━━━━━━━━━━━━━━━━━━
```
