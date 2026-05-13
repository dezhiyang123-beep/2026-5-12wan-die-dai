---
name: design-prd
description: 设计版PRD三页SOP。被engineering-integrator、packager调用。定义三页结构和必填字段。
---

# design-prd — 设计版PRD三页SOP

## 三页结构

### 页1：用户场景页

```yaml
page1_user_scenario:
  target_user: "[具体描述，职业/年龄/技能水平，≥20字]"
  use_scenario: "[使用场景画面描述，有时间/地点/动作，≥30字]"
  core_value: "[用户在哪个动作节点感受到的核心价值，1句话]"
  buying_reason: "[购买真实理由，非设计师自嗨，引用buyer_map数据]"
```

### 页2：造型结构页

```yaml
page2_form_structure:
  main_view_logic: "[主视角造型逻辑，来自母题卡主轮廓+比例字段]"
  parting_lines: "[主要分件线位置，来自母题卡分件策略字段]"
  interfaces: "[接口/按键/连接件清单，含位置描述]"
  installation_method: "[安装方式详述，来自母题卡安装架构字段]"
  maintenance_access: "[维护入口位置，工具要求]"
```

### 页3：工程边界页

```yaml
page3_engineering:
  optical_specs:
    luminous_flux: "X流明 [H/M/L]"
    color_temperature: "XK [H/M/L]"
    beam_angle: "X度 [H/M/L]"
  thermal_constraints: "[散热方式和温度上限]"
  cost_ceiling: "$X.XX BOM上限（来自form_handoff_brief.cost_ceiling_per_unit）"
  certification_required: ["FCC", "UL", "..."]
  risk_top5:
    - rank: 1
      category: "结构/电气/可靠性/人因/成本/法规"
      risk: "[风险描述]"
      level: "H/M/L"
      mitigation: "[缓解动作]"
      owner: "[负责人/角色]"
```

## 字段来源追溯规则

每个字段必须可追溯到上游文件：
- `target_user` ← `02_user_action_map.yaml.installer.who` 或 `operator.who`
- `use_scenario` ← `02_user_action_map.yaml.operator.action_chain`
- `buying_reason` ← `02_buyer_map.yaml.roi_impact_points`
- `cost_ceiling` ← `03_direction_space.yaml.form_handoff_brief.cost_ceiling_per_unit`
- `main_view_logic` ← `04_form_mother_cards.yaml.[selected_card].主轮廓+比例`

## 禁止事项

- 三页顺序打乱（必须按页1→页2→页3）
- risk_top5缺少mitigation字段
- optical_specs中流明/色温等关键参数标为[H]但无来源
- cost_ceiling与form_handoff_brief.cost_ceiling_per_unit不一致
