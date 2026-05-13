# /run-g5-review — G5图像回审+收敛

## 命令说明

审查GPT返回的图像，逐包判定可用性，收敛到5套客户版。

## 前置检查

- `05_render_definition_pack.yaml` 必须存在
- 用户必须已提供GPT返回的图像（phase1）

## 执行步骤

**Step G5-1：调用 form-director + image-review skill**
- 对照每个渲染定义包，逐包审查图像
- 判定偏差类型（轮廓/发光面/分件线/CMF/比例/禁止元素）
- 每包输出verdict：可用 / 需修正1轮 / 需修正2轮 / 废弃重出

**Step G5-2：Phase2出图（通过phase1审查的包）**
- 可用的包：出phase2（6张/包）
- 需修正的包：输出修正提示词，等待用户重出phase1图
- 废弃的包：标注，从漏斗中移除

**Step G5-3：收敛到5套客户版**
- 从可用包中选出最优5套
- 为每套产出 client_ready_set 字段

**Step G5-4：client_score评分（调用 reality-checker，review_mode: full）**

对每套方案打分：

| 字段 | 说明 |
|------|------|
| client_fit | 方案与客户需求匹配度（1-5） |
| image_fidelity | 图像与渲染包定义吻合度（1-5） |
| pricing_coherence | 定价逻辑一致性（1-5） |
| why_now_strength | 为什么现在买的说服力（1-5） |
| risk_level | 风险等级，5=低风险（1-5） |

**total<15分→不通过客户版，回流G4补出渲染包**
**通过后可用方案<5套→回流G4补出渲染包**

### 执行完成后

更新 `artifacts/projects/{project_id}/00_status_dashboard.md`：
- current_gate: G5
- gate_status: [通过N套/不足]
- next_action: [如≥5套通过则"执行 /run-g6-package"]

## 输出产物

- `artifacts/projects/{project_id}/06_image_review_matrix.yaml`
- `artifacts/projects/{project_id}/06_client_ready_set.yaml`
- `artifacts/projects/{project_id}/00_status_dashboard.md`（更新）

## 关卡停止格式

```
━━━━━ G5 完成 ━━━━━
产物：
  06_image_review_matrix.yaml
  06_client_ready_set.yaml
客户版汇总：
  通过（≥15分）：[N]套
  未通过（<15分）：[N]套 → 需回流G4
决策点：[若≥5套通过] 执行 /run-g6-package
━━━━━━━━━━━━━━━━━━━━━━
```
