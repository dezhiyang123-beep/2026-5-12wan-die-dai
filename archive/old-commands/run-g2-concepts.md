# /run-g2-concepts — 启动G2概念生成

## 调用角色
agent: conceptor

## 前置检查
1. 确认存在 `artifacts/projects/{project_id}/03_g1_directions.yaml`
2. 确认用户已明确选择方向ID（D-A/D-B/D-C）
3. 确认存在 `artifacts/projects/{project_id}/02_g1_intel.yaml`（需要竞品矩阵）

## 执行步骤
1. 读取用户选定的方向（从03_g1_directions.yaml中提取对应方向ID的数据）
2. 读取 `knowledge/perspectives/personas-8.md` 选3-4个人格
3. 从选定方向的behavioral_contradiction提取TRIZ矛盾（读取 `knowledge/methods/triz-core.md`）
4. conceptor调用 concept-card skill 生成3-5个概念卡
5. 执行同质性检查，必要时替换
6. 输出 `artifacts/projects/{project_id}/04_g2_concepts.yaml`（符合 `contracts/g2_concepts.schema.yaml`）

## 输出文件
`artifacts/projects/{project_id}/04_g2_concepts.yaml`

## 输出必须符合
`contracts/g2_concepts.schema.yaml`

## 关卡停止（强制输出）
```
━━━━━ G2 完成 ━━━━━
概念清单：
  C-01: [标题] | 驱动:[人格/TRIZ] | BOM:[$X] | DFM:[PASS/FAIL]
  C-02: [标题] | ...
  C-03: [标题] | ...
决策：请选择深化哪个概念（输入编号，如C-01）
━━━━━━━━━━━━━━━━
```
