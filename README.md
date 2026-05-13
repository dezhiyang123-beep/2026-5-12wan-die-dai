# ID-design 工业设计AI工作流系统

工业设计师的AI外脑。4关卡门控，5个角色，强制用户决策。

---

## 快速开始

### 1. 新建一个项目

```bash
# 复制brief模板
cp artifacts/_templates/00_brief.template.yaml artifacts/projects/{你的project_id}/00_brief.yaml

# 填写4个必填字段
# project_id: YYYYMMDD-客户缩写-品类缩写
# client: acg 或其他（必须匹配 knowledge/clients/ 文件名）
# category: 产品品类关键词
# brief_text: 需求原文
```

### 2. 运行关卡

```
/run-g0-scout        G0：值不值得做（快速扫描）
/run-g1-analysis     G1：往哪做（情报+方向）
/run-g2-concepts     G2：哪个概念深化（概念生成）
/run-g3-package      G3：能不能过老板（完整展开）
/run-gate-review     任意关卡审查（建议G3后必跑）
```

---

## 关卡流程

```
用户填写 brief
     ↓
G0 ← /run-g0-scout
用户决策：继续G1？放弃？
     ↓（继续）
G1 ← /run-g1-analysis
用户决策：选方向 D-A/B/C？
     ↓（选定）
G2 ← /run-g2-concepts
用户决策：选概念 C-01/02/03？
     ↓（选定）
G3 ← /run-g3-package
     ↓
审查 ← /run-gate-review（推荐）
用户决策：提交方案？
```

每个关卡是硬停止点，必须等用户明确决策才继续。

---

## 关卡产物对照

| 关卡 | 产物文件 | Schema |
|------|---------|--------|
| 输入 | 00_brief.yaml | brief.schema.yaml |
| G0 | 01_g0_scan.yaml | g0_scan.schema.yaml |
| G1情报 | 02_g1_intel.yaml | g1_intel.schema.yaml |
| G1方向 | 03_g1_directions.yaml | g1_directions.schema.yaml |
| G2 | 04_g2_concepts.yaml | g2_concepts.schema.yaml |
| G3 | 05_g3_package.yaml | g3_package.schema.yaml |
| 审查 | 06_gate_review.yaml | gate_review.schema.yaml |

---

## 效果图说明

系统在G3会输出效果图英文提示词（在05_g3_package.yaml的render_prompts字段）。

**手动操作**：把 `en_prompts` 中的提示词复制，发到GPT或Midjourney出图。
完成后把图片插入 `final_pitch.pptx` 的Page 6占位符位置。

---

## 文件结构

```
.claude/agents/      5个角色（scout/analyst/conceptor/packager/reviewer）
.claude/skills/      7个skill（research-pack/hypothesis-check/concept-card/cmf-spec/geometry-prompt/boss-review/ppt-pack）
.claude/commands/    5个命令入口
knowledge/           知识库（客户档案/方法论/人格/合规/案例）
contracts/           YAML schema（定义关卡接口）
artifacts/           项目文件夹 + 模板
archive/             旧系统文件归档
```

---

## 添加新客户

```bash
cp knowledge/clients/_template.md knowledge/clients/{客户缩写小写}.md
# 填写：价格带/认证要求/风格禁忌（3个必填字段）
```

---

## 注意事项

- 每个关卡产物必须符合对应的contracts/ schema
- 搜索失败的字段标UNKNOWN，不脑补
- 信息标注：事实[H] / 推断[M] / 假设[L]
- 效果图需手动发GPT，系统只出提示词
