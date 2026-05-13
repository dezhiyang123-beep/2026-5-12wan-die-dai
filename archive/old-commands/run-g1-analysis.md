# /run-g1-analysis — 启动G1深度情报+方向研判

## 调用角色
agent-1: scout（深度情报）
agent-2: analyst（方向研判）

## 前置检查
1. 确认存在 `artifacts/projects/{project_id}/01_g0_scan.yaml`
2. 确认用户已明确选择"继续G1"（不得自动进入G1）

## 执行步骤（顺序执行，不并行）
**Step 1 — scout深度情报：**
- 调用 research-pack skill 执行G1全量搜索
- 竞品矩阵目标：≥5个直接竞品
- 输出 `artifacts/projects/{project_id}/02_g1_intel.yaml`（符合 `contracts/g1_intel.schema.yaml`）
- 输出"情报包完成，竞品[N]个，UNKNOWN字段[N]个，继续方向研判..."

**Step 2 — analyst方向研判：**
- 读取 02_g1_intel.yaml
- 调用 hypothesis-check skill
- 输出 `artifacts/projects/{project_id}/03_g1_directions.yaml`（符合 `contracts/g1_directions.schema.yaml`）

## 输出文件
- `artifacts/projects/{project_id}/02_g1_intel.yaml`
- `artifacts/projects/{project_id}/03_g1_directions.yaml`

## 输出必须符合
- `contracts/g1_intel.schema.yaml`
- `contracts/g1_directions.schema.yaml`

## 关卡停止（强制输出）
```
━━━━━ G1 完成 ━━━━━
情报：[N]个竞品 | [N]个UNKNOWN字段
方向候选：
  D-A: [标题] — [core_claim一句话]
  D-B: [标题] — [core_claim一句话]
  D-C: [标题] — [core_claim一句话]（如有）
决策：请选择方向 D-A / D-B / D-C，或说"都不选"
━━━━━━━━━━━━━━━━
```
