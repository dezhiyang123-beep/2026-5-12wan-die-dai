---
name: render-definition
description: 渲染定义包SOP。被form-director调用。9段式固定格式、shot_plan分阶段、GPT理解检查规则。
---

# render-definition — 渲染定义包SOP

## 9段式固定格式

每个渲染定义包必须按以下9段输出，字段名不可更改：

```yaml
render_definition_pack:
  pack_id: "RDP-01 至 RDP-08"
  source_card: "M-XX（来源母题卡编号）"

  1_产品定义:
    product_type: "[英文，产品类型+尺寸量级]"
    use_context: "[英文，主要使用场景一句话]"
    key_feature: "[英文，最重要的视觉特征]"

  2_主轮廓与比例:
    silhouette: "[英文，主轮廓描述，含具体比例数字]"
    mass_distribution: "[英文，体块重心分布]"

  3_分件与接口:
    parting_lines: "[英文，主要分件线位置描述]"
    interface_locations: "[英文，接口/按键/连接件位置]"

  4_发光与光学:
    light_emission_area: "[英文，发光面形态和位置]"
    optic_logic: "[英文，光学设计逻辑]"

  5_安装与走线:
    mounting_method: "[英文，安装方式]"
    cable_path: "[英文，线缆路径]"

  6_render_cmf_hint:
    primary_material_hint: "[英文，主材料建议，非最终定义]"
    color_hint: "[英文，色彩方向建议]"
    finish_hint: "[英文，表面处理建议]"

  7_镜头与构图:
    shot_plan:
      phase1:
        - angle: "45-degree isometric front-left"
          purpose: "主造型验证"
        - angle: "side elevation"
          purpose: "分件线和比例验证"
      phase2:
        - angle: "front elevation"
        - angle: "rear elevation"
        - angle: "top-down"
        - angle: "detail close-up: light emission area"
        - angle: "detail close-up: mounting interface"
        - angle: "in-context installation shot"

  8_必须保留:
    - "[来自form_handoff_brief.must_keep_customer_signal的转化，英文]"

  9_严格禁止:
    - "[来自form_handoff_brief.must_not_look_like的转化，英文]"
    - "[其他绝对排除元素]"
```

## 感受词三层过滤（进入任何段之前执行）

- ✅ 直接用：matte / glossy / brushed / translucent / warm white / cool white
- ⚠️ 需转译：厚重感→`thick wall section 8mm+` / 轻盈感→`tapered profile 30% thinner at top`
- ❌ 禁止：高级感 / 科技感 / 机甲感 / 未来感（直接出现在任何段中）

## shot_plan分阶段规则

- **phase1：2张**（概念快速验证，先发GPT出图）
- **phase2：6张**（只在phase1图像通过GPT理解检查后执行）

## GPT理解检查（8包生成后，phase1出图前）

从8个包中抽取2个（选screen_score最高和最低各1个），发phase1提示词给GPT：
- 检查点1：GPT输出的主轮廓是否与1_产品定义+2_主轮廓与比例一致
- 检查点2：发光面位置和形态是否与4_发光与光学一致
- 检查点3：安装方式是否与5_安装与走线一致

**任一检查点偏差→修正对应段的文字描述，再出图。**

## 禁止事项

- 9段中出现❌层感受词
- 6_render_cmf_hint段字段名写为"材质与表面"
- phase1跳过GPT理解检查直接出phase2
- 提示词含中文字符
