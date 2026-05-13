# 素材索引目录

本目录存放视觉素材库的 DNA 卡（YAML 文件）。

## 文件夹结构
按品类分文件夹，每个YAML文件聚合同品牌同子品类的多个产品：

```
素材索引/
├── lighting/          # 灯具品类
│   ├── outdoor/       # 户外灯具
│   ├── indoor/        # 室内灯具
│   ├── grow_light/    # 种植灯
│   └── ...
├── consumer_electronics/  # 消费电子
├── power_tools/       # 电动工具
├── furniture/         # 家具
├── cross_category/    # 跨品类参照
└── ...
```

## DNA 卡命名规则
`{品牌}_{子品类}_{序号}.yaml`，如 `bega_室内吸顶灯_1.yaml`

每个文件内包含 `products` 数组，每个产品有唯一 `product_id`（如 `bega_室内吸顶灯_001`），下挂 `source_images` 数组。下游步骤通过 `product_id` 引用素材。

## 入库流程
1. 图片存入用户桌面 `~/Desktop/设计素材库/` 对应文件夹
2. 使用 AI 读图生成 DNA 卡初版
3. 用户校对关键字段（problem_solved, form_response, transferable_technique）
4. 校对通过后存入本目录对应品类文件夹
