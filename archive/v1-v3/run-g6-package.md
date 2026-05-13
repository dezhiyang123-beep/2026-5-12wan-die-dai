# /run-g6-package — G6三步封装

## 命令说明

三步顺序执行：5套轻版→用户确认→Top 2-3深版+PPT。

## 前置检查

- `06_client_ready_set.yaml` 必须存在，且≥5套方案 client_score≥15分

## 执行步骤

### Step 1：5套轻版（全做，等用户确认）

调用 packager，对5套方案各产出：
- 1页方案摘要（concept_id + hero_image + one_line_summary）
- supporting_images（来自 client_ready_set）
- 一句话买单理由（for_whom + solves_what + why_now + why_not_wait）

**Step 1完成后停止，更新dashboard，等用户明确选定Top 2-3套。**

### Step 2：用户确认（等待，不推荐）

输出：
```
━━━━━ G6 Step 1完成 ━━━━━
5套轻版已就绪，请选择需要深化的2-3套（输入方案编号）
━━━━━━━━━━━━━━━━━━━━━━━━━
```
等用户输入确认后执行Step 3。

### Step 3：深版（Top 2-3）+ PPT

调用 engineering-integrator + packager：

**深版内容：**
- 设计版PRD三页（调用 design-prd skill）
- CMF分区绑定表（调用 cmf-zoning skill，final_authority: true）
- BOM+成本ROI（09_roi_pricing.yaml）
- 落地风险Top5（10_engineering_risk.yaml）
- 认证路径说明

**PPT（调用 ppt-pack skill）：**
- 固定8页结构
- 必须生成 .pptx 文件
- 针对用户指定的决策者版本（技术版/ROI版/接口版）

**Step 3完成后调用 reality-checker（review_mode: full）**
执行G6全审查（7维度+假阳性3条）。

### 执行完成后

更新 `artifacts/projects/{project_id}/00_status_dashboard.md`：
- current_gate: G6
- gate_status: [通过/不通过]
- next_action: [通过则"提交，执行 /run-gate-check G6 确认"]

## 输出产物

Step 1：
- `artifacts/projects/{project_id}/07_design_prd.yaml`（轻版摘要）

Step 3：
- `artifacts/projects/{project_id}/07_design_prd.yaml`（完整三页）
- `artifacts/projects/{project_id}/08_cmf_zoning.yaml`
- `artifacts/projects/{project_id}/09_roi_pricing.yaml`
- `artifacts/projects/{project_id}/10_engineering_risk.yaml`
- `artifacts/projects/{project_id}/11_pitch_deck.yaml`
- `artifacts/projects/{project_id}/final_pitch.pptx`
- `artifacts/projects/{project_id}/12_gate_review.yaml`
- `artifacts/projects/{project_id}/00_status_dashboard.md`（更新）
