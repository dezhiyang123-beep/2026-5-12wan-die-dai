---
name: cmf-spec
description: CMF（色彩/材料/工艺）输出SOP。被packager调用。定义C/M/F三层规格模板，缺失字段标UNKNOWN规则。
---

# cmf-spec — CMF输出SOP

## 执行前提

packager在调用此skill前必须已完成Step1（PRD）和Step2（落地性评估）。
CMF必须与PRD中的约束和落地性评估中的材料风险对齐。

## C — Color（色彩）

**输出格式：**
```yaml
color:
  primary:
    pantone: "Pantone XXXX C"         # 搜索失败标UNKNOWN
    hex: "#XXXXXX"                     # 由Pantone推导，搜索失败标UNKNOWN
    ratio: "主色占比，如'75%外壳'"
    tolerance: "ΔE ≤ X.X"             # 客户档案有要求则引用，否则标UNKNOWN
  secondary:
    pantone: "Pantone XXXX C"
    ratio: "..."
  forbidden_colors:
    - "[颜色描述]（原因）"              # 从客户档案style_forbidden中提取
```

**取色规则：**
- 优先从客户历史产品和竞品中提取色彩体系
- 新品类颜色参考竞品矩阵中的主流色系
- 不得使用客户档案中forbidden_colors列出的颜色
- Pantone编号无法确认时标UNKNOWN+给验证动作

## M — Material（材料）

**输出格式：**
```yaml
material:
  primary_body:
    system: "材料体系，如'PC+ABS合金'"
    grade: "等级要求，如'UL94 V-0阻燃'"
    touch_target: "触感目标描述，如'哑光/微砂感'"
    structure_role: "结构作用，如'外壳承力件'"
    cost_estimate: "$X/kg或$X/件[M]"    # 标[M]，基于市场估算
  sealing:
    system: "如'IP54密封圈，硅胶'"
    spec: "如'邵氏硬度40A'"
  unknown_fields: []                    # 无法确认的材料字段
```

**材料选择约束：**
- 必须符合客户档案的材料偏好和排除材料
- 含锂电池产品必须在材料清单中标注电芯规格（缺失标UNKNOWN）
- 北美渠道产品必须注明Prop65合规材料要求

## F — Finish（表面工艺）

**输出格式：**
```yaml
finish:
  process: "工艺名称，如'喷涂+UV光油'"
  gloss_level: "光泽度，如'哑光 GU20以下'"
  texture: "纹理描述，如'皮纹/细拉丝/喷砂'"
  touch_result: "触感结果，如'防指纹哑面'"
  durability_test: "耐久测试标准，如'百格附着力测试3B以上'"
  unknown_fields: []
```

## 缺失字段处理规则

以下字段缺失时的处理：

| 字段 | 缺失原因 | 处理方式 |
|------|---------|---------|
| Pantone编号 | 无参考色稿 | 标UNKNOWN+验证动作：提供色稿后确认 |
| 材料等级 | 认证未定 | 标UNKNOWN+验证动作：按认证要求确认 |
| 成本估算 | 供应链未询价 | 标UNKNOWN[M]，用市场估算注明推断 |
| 耐久测试标准 | 客户未指定 | 标UNKNOWN，给行业惯例作为参考 |

**禁止**：用"待定/TBD/同行业标准"代替UNKNOWN。UNKNOWN必须附验证动作。
