---
name: cmf-zoning
description: CMF分区绑定SOP。被engineering-integrator、packager调用。final_authority: true，覆盖G4的render_cmf_hint。
---

# cmf-zoning — CMF分区绑定SOP

## 执行时机

G6工作。本文件为CMF最终权威（`final_authority: true`），覆盖G4渲染包中的 `render_cmf_hint`（仅为建议值）。

## 分区定义规则

必须按物理分件边界划分分区，不按视觉区域划分：

```yaml
cmf_zones:
  - zone_name: "main_housing_front"
    material: "PC+ABS合金，UL94 V-0 [H/M/L]"
    surface_treatment: "喷涂+UV光油，哑光GU20以下"
    touch: "细砂感，防指纹"
    color_direction: "Pantone Cool Gray 7 C，#97999B"
    process_notes: "需百格附着力测试3B以上"
  - zone_name: "light_diffuser"
    material: "乳白PC，透光率45%"
    surface_treatment: "无喷涂，注塑纹理"
    touch: "光滑"
    color_direction: "natural white"
    process_notes: "需光学均匀性测试"
```

## 供应商沟通格式

每个分区必须输出可直接发给供应商的英文规格：

```
Zone: [zone_name]
Material: [material spec]
Surface: [surface treatment]
Color ref: [Pantone number or RAL code]
Touch quality: [描述]
Test requirement: [测试标准]
```

## CMF一致性检查

对照G5的 `client_ready_set` 中每套方案的图片，检查：
- 分区色彩是否与client_score通过的图像一致
- 材料规格是否与DFM评分兼容（不增加新的DFM风险）

## final_authority声明

```yaml
final_authority: true
overrides: "05_render_definition_pack.yaml 中所有 render_cmf_hint 字段"
effective_from: "G6执行后"
```

## 禁止事项

- 颜色只写"黑色/白色"不给Pantone/RAL编号（搜索失败则标UNKNOWN）
- 材料规格缺失认证等级（UL94/RoHS等）不标注
- 跳过final_authority声明
- 供应商沟通格式用中文写
