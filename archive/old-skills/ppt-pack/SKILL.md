---
name: ppt-pack
description: PPT生成SOP。被packager调用。定义固定8页结构、每页字段来源、L置信度处理规则、.pptx文件生成要求。
---

# ppt-pack — PPT生成SOP

## 固定8页结构

每页的字段来源必须可追溯到具体yaml字段。

### Page 1：封面
```
产品名称       → g3_package.prd.product_name
项目代号       → brief.project_id
客户品牌       → brief.client
日期           → 当前日期
副标题         → g2_concepts.concepts[selected].title
```

### Page 2：市场机会
```
目标价格带     → knowledge/clients/{client}.acg.price_ceiling 或 brief.price_target
主要竞品       → g1_intel.competitor_matrix（前3名：品牌+价格+核心卖点）
市场痛点       → g1_intel.user_scenarios（高频痛点，最多3条）
机会陈述       → g1_directions[selected].core_claim（去掉[L]内容）
```

### Page 3：目标用户
```
用户描述       → g3_package.prd.target_user
使用场景       → g3_package.prd.use_scenario（必须有具体画面感）
行为矛盾       → g1_directions[selected].behavioral_contradiction
```

### Page 4：产品定义
```
功能列表       → g3_package.prd.function_list（只展示P0和P1）
关键规格       → g3_package.prd.key_specs（UNKNOWN字段不上正文，移备注页）
约束           → g3_package.prd.constraints
```

### Page 5：差异化卖点
```
核心差异       → g2_concepts.concepts[selected].differentiator
决策核         → g2_concepts.concepts[selected].decision_core
vs 竞品对比    → g1_intel.competitor_matrix（主要竞品的对比，必须有数据）
```

### Page 6：设计方案
```
造型意图摘要   → g3_package.render_prompts.styling_summary（英文，配效果图位置）
CMF摘要        → g3_package.cmf（颜色+材料+工艺各1句话）
结构路径       → g2_concepts.concepts[selected].structure_path
效果图         → [占位符：效果图待从GPT获取后插入]
```

### Page 7：制造可行性
```
DFM判定        → g2_concepts.concepts[selected].dfm_verdict
Top3风险+缓解  → g3_package.manufacturability.top10_risks（取前3条）
BOM估算        → g2_concepts.concepts[selected].bom_estimate
认证要求       → knowledge/clients/{client}.must_certify
```

### Page 8：推荐理由
```
提交建议       → 基于gate_review.verdict的说明（如有审查结果）
老板7维度得分  → gate_review.boss_7d_review（摘要）
下一步行动     → 验证计划中的第一个P0动作（g3_package.prd.validation_plan[0]）
```

## [L]置信度内容处理规则

在写入任何页面正文前检查：
- `[L]`内容→不得出现在正文
- 处理方式：
  - 有补充证据可升级→升级到[M]后写入
  - 无法升级→改为"待验证"格式移至备注页，正文用"[待确认]"占位

## 输出规则

- 必须生成 `.pptx` 文件（使用python-pptx或等效工具）
- 文件路径：`artifacts/projects/{project_id}/final_pitch.pptx`
- 语言：默认英文；如用户指定"内部汇报"则中文
- 效果图占位符：Page 6中在图片区域标注 `[效果图占位：发提示词至GPT后替换]`

## 禁止事项

- 只输出文字内容不生成.pptx文件
- 把[L]置信度内容直接写入正文
- Page 5的对比引用在g1_intel中不存在
- 字段来源不可追溯
