# /run-g2-actions — G2用户动作建模

## 命令说明

建模安装者/操作者/维护者的完整动作链。产出buyer_map。

## 前置检查

- `01_business_gate.yaml` 必须存在且 `verdict: go`
- 如 verdict 不是 go，输出错误："G1未通过，请先完成G1"

## 执行步骤

**Step G2-1：调用 strategist + action-modeling skill**

对三个角色逐一建模：
- installer：安装者（who/action_chain/tools_needed/total_time_per_unit/total_time_per_site）
- operator：操作者（who/action_chain/total_time_per_week/pain_points）
- maintainer：维护者（who/frequency/action_chain/tools_needed）
- error_scenarios：≥2个失误场景
- value_assessment：用户价值感知节点

**Step G2-2：检查4项G2硬门槛**
- installer.who（具体描述）
- operator.who（具体描述）
- value_assessment（有动作节点）
- buyer_map.payer（付钱的人）
- 任一UNKNOWN→调用 reality-checker（review_mode: lite），HOLD

**Step G2-3：产出 buyer_map**
- value_perceiver / payer / decision_process / roi_impact_points / current_alternatives / switching_cost
- payer为UNKNOWN→HOLD

**Step G2-4：工时估算**
- total_labor_estimate（per_unit_install / per_site_install / per_week_operate / labor_cost_implication）

### 执行完成后

更新 `artifacts/projects/{project_id}/00_status_dashboard.md`：
- current_gate: G2
- gate_status: [go/hold]
- next_action: [如go则"执行 /run-g3-directions"]

## 输出产物

- `artifacts/projects/{project_id}/02_user_action_map.yaml`
- `artifacts/projects/{project_id}/02_buyer_map.yaml`
- `artifacts/projects/{project_id}/00_status_dashboard.md`（更新）

## 关卡停止格式

```
━━━━━ G2 完成 ━━━━━
产物：
  02_user_action_map.yaml
  02_buyer_map.yaml
决策点：
  G2硬门槛：[全通过/HOLD]
  [若通过] 执行 /run-g3-directions 继续
━━━━━━━━━━━━━━━━━━━━
```
