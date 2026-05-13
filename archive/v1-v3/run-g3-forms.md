# /run-g3-forms — G3造型母题池

## 命令说明

基于用户选定的方向，生成12张造型母题卡，用户从中筛选8张进入G4。

## 前置检查

- `03_direction_space.yaml` 必须存在
- 用户必须已明确选定方向（D-A / D-B / D-C）

## 执行步骤

**Step G3F-1：读取 form_handoff_brief**
- 从用户选定方向的 form_handoff_brief 读取6个字段
- 这是造型母题的硬约束

**Step G3F-2：调用 form-director + form-mother-card skill**
- 生成12张母题卡
- 每张卡：6个必填详细字段 + 7个短语字段 + screen_score评分
- 12张必须覆盖≥4种主轮廓、≥3种安装架构、≥3种发光面逻辑

**Step G3F-3：差异性检查**
- 自动检查12张母题的多样性
- 不满足要求→替换直到满足

**Step G3F-4：screen_score汇总**
- 输出每张卡的total分
- total<15分的卡标"弱（建议淘汰）"

**Step G3F-5：调用 reality-checker（review_mode: lite）**
- 验证三维度多样性
- HOLD条件：任一维度<要求数量

### 执行完成后

更新 `artifacts/projects/{project_id}/00_status_dashboard.md`：
- current_gate: G3（母题）
- gate_status: [待用户筛选]
- next_action: "用户筛选到8张后执行 /run-g4-render"

## 输出产物

- `artifacts/projects/{project_id}/04_form_mother_cards.yaml`
- `artifacts/projects/{project_id}/00_status_dashboard.md`（更新）

## 关卡停止格式

```
━━━━━ G3母题 完成 ━━━━━
产物：04_form_mother_cards.yaml
12张母题生成完毕：
  弱评分（<15分）：[M-XX, M-XX]建议淘汰
  强评分（≥20分）：[M-XX, M-XX]推荐保留
决策点：请从12张中筛选8张，然后执行 /run-g4-render
━━━━━━━━━━━━━━━━━━━━━━
```
