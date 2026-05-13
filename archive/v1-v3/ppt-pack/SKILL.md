---
name: ppt-pack
description: PPT生成SOP。被packager调用。定义固定8页结构、每页字段来源、决策者版本、.pptx文件生成要求。
---

# ppt-pack — PPT生成SOP

## 固定8页结构

### Page 1：封面
```
产品名称       ← 07_design_prd.page2_form_structure（或方案名称）
项目代号       ← 00_project_brief.project_id
客户品牌       ← 00_project_brief.client_name
日期           ← 执行当天日期
副标题         ← 06_client_ready_set.one_line_summary
```

### Page 2：市场机会
```
目标价格带     ← 01_business_gate.target_price_range
主要竞品       ← 01_business_gate.competitor_quick_scan（前3名）
市场痛点       ← 01_business_gate中提取（最多3条）
机会陈述       ← 03_direction_space.directions[selected].core_value
```

### Page 3：目标用户
```
用户描述       ← 07_design_prd.page1_user_scenario.target_user
使用场景       ← 07_design_prd.page1_user_scenario.use_scenario
行为矛盾       ← 03_direction_space.directions[selected].behavior_contradiction
```

### Page 4：产品定义
```
功能列表       ← 07_design_prd（P0和P1，UNKNOWN字段移备注页）
关键规格       ← 07_design_prd.page3_engineering.optical_specs
约束           ← 07_design_prd.page3_engineering.cost_ceiling
```

### Page 5：差异化
```
核心差异       ← 03_direction_space.directions[selected].core_value
vs竞品对比     ← 01_business_gate.competitor_quick_scan（必须有数字对比）
```

### Page 6：设计方案
```
造型意图摘要   ← 英文（render_definition_pack中提取，感受词已过滤）
CMF摘要        ← 08_cmf_zoning.yaml（每分区1句话）
效果图         ← [占位符：效果图来自G5 client_ready_set.hero_image]
```

### Page 7：制造可行性
```
DFM判定        ← 05_render_definition_pack.dfm_quick_check.verdict
风险Top3       ← 10_engineering_risk.risk_top5（取前3条）
BOM估算        ← 09_roi_pricing.bom_estimate
认证要求       ← 07_design_prd.page3_engineering.certification_required
```

### Page 8：推荐理由
```
审查判定摘要   ← 12_gate_review.verdict + verdict_reason
下一步行动     ← 10_engineering_risk.risk_top5[1].mitigation（最高优先级缓解动作）
```

## [L]置信度处理规则

- `[L]` 内容不得出现在正文
- 处理方式：有证据可升级→升级到[M]写入；无法升级→移备注页，正文用"[待确认]"占位

## 决策者版本差异

| 版本 | 给谁 | 强调重点 | 调整页面 |
|------|------|---------|---------|
| 技术版 | Head Grower | 制造可行性+规格细节 | Page 7加详细DFM数据 |
| ROI版 | Owner | 成本ROI+市场规模 | Page 2加销售预测；Page 7用ROI替换DFM |
| 接口版 | 品牌方技术 | 认证路径+接口规范 | Page 4加接口规范；Page 7加认证时间线 |

## 输出规则

- 必须生成 `.pptx` 文件（使用python-pptx或等效工具）
- 文件路径：`artifacts/projects/{project_id}/final_pitch.pptx`
- 语言：默认英文；用户指定"内部汇报"则中文
- Page 6效果图占位符：`[效果图占位：发提示词至GPT后替换]`

## 禁止事项

- 只输出文字内容不生成 .pptx 文件
- [L]内容直接写入正文
- Page 5的对比数据在竞品矩阵中不存在
- 字段来源不可追溯
