# /run-g4-render — G4渲染定义包+DFM检查

## 命令说明

基于用户筛选的8张母题卡，生成8个渲染定义包，执行DFM快速评分，先出phase1（2张）等待图像回来。

## 前置检查

- `04_form_mother_cards.yaml` 必须存在
- 用户必须已确认筛选的8张母题（M-XX × 8）

## 执行步骤

**Step G4-1：调用 form-director + render-definition skill**
- 基于8张筛选的母题卡
- 生成8个渲染定义包（9段式固定格式）
- 第6段字段名必须是 `render_cmf_hint`

**Step G4-2：GPT理解检查（8包生成后立即执行）**
- 从8个包中抽取2个（最高分和最低分各1个）
- 输出这2个包的phase1提示词，提示用户发给GPT检查
- 等待用户反馈理解是否偏差
- 有偏差→修正对应包的文字描述，然后继续

**Step G4-3：调用 engineering-integrator 执行6轴DFM评分**
- 对每个渲染包评分：assembly / thermal / cable_routing / ingress_protection / tooling_complexity / serviceability（各0/1/2）
- 总分0-3=绿，4-7=黄，8-12=红
- 红灯包标注 `dfm_verdict: red` + `red_items: [导致红灯的轴]`
- 红灯包不得进入G5，输出：`⚠️ RDP-XX DFM红灯，需回G3修改母题`

**Step G4-4：phase1出图（2张/包）**
- 为每个通过DFM的包输出phase1提示词（2个角度）
- 等待用户发图给GPT出图
- 图像回来后执行 /run-g5-review

**M2快速模式补丁：**
如 mode=M2 且 G4后废弃包（DFM红灯）≥3个，导致可用包<6个：
- 自动回G3补出2张母题
- 提示用户："快速模式漏斗保护：可用包不足，回补2张母题"

### 执行完成后

更新 `artifacts/projects/{project_id}/00_status_dashboard.md`：
- current_gate: G4
- gate_status: [等待phase1出图]
- blockers: [红灯包列表，如有]
- next_action: "GPT出图后执行 /run-g5-review"

## 输出产物

- `artifacts/projects/{project_id}/05_render_definition_pack.yaml`
- `artifacts/projects/{project_id}/00_status_dashboard.md`（更新）

## 关卡停止格式

```
━━━━━ G4 完成 ━━━━━
产物：05_render_definition_pack.yaml
DFM评分汇总：
  绿灯：[N]个包
  黄灯：[N]个包（标注风险）
  红灯：[N]个包（需回G3）
Phase1提示词：已就绪（[N]个包，2张/包）
决策点：请将phase1提示词发给GPT出图，图像回来后执行 /run-g5-review
━━━━━━━━━━━━━━━━━━━━━━
```
