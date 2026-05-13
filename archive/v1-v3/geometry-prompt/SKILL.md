---
name: geometry-prompt
description: 功能→几何→效果图提示词转译SOP。被packager调用。定义感受词三层分类、功能几何转译规则、英文提示词模板。
---

# geometry-prompt — 功能→几何→提示词SOP

## 感受词三层分类（执行前必须完成分类）

在写任何提示词之前，先对所有感受词执行分类：

**✅ 第一层：可直接使用（光感/材质/触感类）**
- 示例：matte / glossy / brushed aluminum / rubber grip / translucent / warm white / cool white
- 规则：直接写入提示词，无需转译

**⚠️ 第二层：需转译后使用（体量/力量/比例类）**
- 示例：厚重感/轻盈感/力量感/紧凑感/大气/精致
- 规则：必须转译为几何参数后才能写入提示词
- 转译格式：`[感受词] → [几何参数]`
- 转译示例：
  - 厚重感 → `thick wall section 8mm+, bottom-heavy mass distribution`
  - 轻盈感 → `tapered profile 30% thinner at top, undercut at grip zone`
  - 力量感 → `ribbed surface every 12mm, beveled edges 2mm chamfer`

**❌ 第三层：禁止使用（气质/情绪/风格类）**
- 示例：高级感/简约感/机甲感/科技感/未来感/温暖/冷酷
- 规则：禁止直接出现在提示词中。必须全部转译为第一/二层词汇

## 功能→几何转译规则

对PRD中每条功能执行转译：
`功能描述 → 几何特征 → 位置/尺寸关系 → 分件线位置`

**转译步骤：**
1. 这个功能的交互点在哪里（位置）
2. 交互点的外观形态是什么（几何特征）
3. 它如何和周围部件分界（分件线）
4. 它的比例关系（尺寸参考）

**输出格式：**
```
功能[X] → 几何特征：[描述] | 位置：[描述] | 分件线：[描述]
```

**3个转译示例（从旧系统Skill G迁移）：**

示例1 — 磁吸底座功能：
```
功能：底部磁吸吸附金属面
→ 几何特征：circular inset disc, flush with base, diameter 40mm
→ 位置：centered on bottom face, 5mm recessed
→ 分件线：circular parting line 42mm diameter on bottom face
```

示例2 — 手持握持功能：
```
功能：单手握持操作
→ 几何特征：oval cross-section, widest 38mm, indented grip zone 25mm long
→ 位置：mid-body, 30-55mm from base
→ 分件线：longitudinal parting line along grip centerline
```

示例3 — 模式切换按键功能：
```
功能：三挡模式切换
→ 几何特征：raised rocker button, 18×10mm, 1.5mm proud of surface
→ 位置：top face, offset 8mm from center toward thumb-accessible side
→ 分件线：rectangular cutout 20×12mm with 1mm fillet
```

## 造型意图摘要模板（英文）

```
Product type: [类型]
Use scenario: [场景]
Feeling words (approved only): [只写✅第一层词汇]
Form logic: [核心造型逻辑，2句话]
CMF summary: [材料/颜色/工艺各1句话]
Must include: [必须出现的视觉元素]
Must exclude: [绝对不能出现的元素，来自客户style_forbidden]
Reference direction: [竞品或参考风格，1句话]
```

## 备用英文提示词模板（每角度一条）

```
subject: [产品名称和类型]
background: [plain white studio / dark workshop / outdoor scene]
lighting: [soft diffused light / dramatic side light / product photography lighting]
camera: [角度描述：front view / 45-degree isometric / top-down / detail close-up]
material: [来自✅层感受词 + ⚠️层转译后的几何参数]
color: [Pantone色号转英文描述 + ratio]
realism: [photorealistic product render / studio photography style]
exclude: [来自客户style_forbidden的排除项]
```

## 角度清单（至少3个）

标准角度组合（可根据产品类型调整）：
1. 正面45°俯视（主视角，展示整体造型）
2. 侧面90°平视（展示厚度和分件线）
3. 底部/使用状态（展示核心功能交互点）
4. 细节特写（展示CMF和关键结构）

**提示词必须是英文。不得出现中文字符。**
