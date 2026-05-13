# /start-project — G0+G1立项+商务验证

## 命令说明

G0和G1合并执行。G0通过后自动续G1，不需要用户中途确认。

## 执行步骤

### G0：项目立项

**Step G0-1：读取并确认brief**
- 读取 `00_project_brief.yaml`
- 如不存在，引导用户填写以下必填字段：
  - project_id（格式：YYYYMMDD-客户缩写-品类缩写）
  - client_name
  - client_type（oem_push / brand_rd）
  - category
  - target_market
  - mode（M1 / M2 / M3）
  - success_definition

**Step G0-2：调用 scout 执行三圈层搜索**
- 执行 research-pack SOP
- 第一圈≥5直接竞品，第二圈≥3 OEM，第三圈≥2相邻品类
- 所有搜索结果写入 `00_project_brief.yaml` 的市场快照部分

**Step G0-3：模式确认**
- 确认 mode 字段
- M2/M3 模式写入对应的约束（方向≤2，母题8张，客户版5套）

### G1：商务前提验证（G0自动续）

**Step G1-1：调用 strategist 执行 business-gate**
- 验证4项硬门槛：oem_openness / target_price_range / certification_path / decision_maker
- 任一UNKNOWN→输出HOLD，停止执行

**Step G1-2：产出 `01_business_gate.yaml`**
- 符合 `contracts/01_business_gate.schema.yaml`
- 写入 verdict（go / hold / stop）

**Step G1-3：调用 reality-checker（review_mode: lite）**
- 验证4项硬门槛不含UNKNOWN
- HOLD则停止，等用户补充

### 执行完成后

更新 `artifacts/projects/{project_id}/00_status_dashboard.md`：
- current_gate: G1
- gate_status: [go/hold/stop]
- next_action: [如go则"执行 /run-g2-actions"]

## 输出产物

- `artifacts/projects/{project_id}/00_project_brief.yaml`
- `artifacts/projects/{project_id}/01_business_gate.yaml`
- `artifacts/projects/{project_id}/00_status_dashboard.md`（更新）

## 关卡停止格式

```
━━━━━ G0+G1 完成 ━━━━━
产物：
  00_project_brief.yaml
  01_business_gate.yaml
决策点：
  G1 verdict: [go/hold/stop]
  [若go] 执行 /run-g2-actions 继续
  [若hold] 请先完成以下验证：[hold_action]
━━━━━━━━━━━━━━━━━━━━━━
```
