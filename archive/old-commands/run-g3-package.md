# /run-g3-package — 启动G3完整方案展开

## 调用角色
agent: packager

## 前置检查
1. 确认存在 `artifacts/projects/{project_id}/04_g2_concepts.yaml`
2. 确认用户已明确选择概念ID（如C-01）
3. 确认存在 `artifacts/projects/{project_id}/02_g1_intel.yaml`

## 执行步骤（严格顺序，每步完成后输出确认）
1. **Step 1 PRD**：packager生成1页PRD，输出"PRD完成"
2. **Step 2 落地性**：生成6类风险+Top10风险+BOM降级树，输出"落地性评估完成"
3. **Step 3 CMF**：调用 cmf-spec skill，输出"CMF完成"
4. **Step 4 效果图提示词**：调用 geometry-prompt skill，输出"提示词完成，请手动发GPT"
5. **Step 5 PPT**：调用 ppt-pack skill，生成 `final_pitch.pptx`，输出"PPT文件已生成"
6. 写入 `artifacts/projects/{project_id}/05_g3_package.yaml`（符合 `contracts/g3_package.schema.yaml`）

## 输出文件
- `artifacts/projects/{project_id}/05_g3_package.yaml`
- `artifacts/projects/{project_id}/final_pitch.pptx`

## 输出必须符合
`contracts/g3_package.schema.yaml`

## 关卡停止（强制输出）
```
━━━━━ G3 完成 ━━━━━
方案包：05_g3_package.yaml
PPT：final_pitch.pptx
效果图提示词：已就绪，请手动发GPT出图
决策：直接提交？或先跑 /run-gate-review？
━━━━━━━━━━━━━━━━
```
