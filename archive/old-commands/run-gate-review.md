# /run-gate-review — 启动关卡审查

## 调用角色
agent: reviewer

## 调用时机
可在任意关卡完成后调用。常见场景：
- G3完成后调用（推荐）：`/run-gate-review g3`
- G2完成后提前审查概念质量：`/run-gate-review g2`
- G1完成后审查方向：`/run-gate-review g1`

## 前置检查
1. 用户指定审查关卡（g0/g1/g2/g3）
2. 对应yaml文件必须存在：
   - g0: `01_g0_scan.yaml`
   - g1: `03_g1_directions.yaml`
   - g2: `04_g2_concepts.yaml`
   - g3: `05_g3_package.yaml`
3. 尝试读取 `02_g1_intel.yaml`（竞品对比用），不存在时输出警告"竞品数据缺失，对比受限"

## 执行步骤
1. reviewer读取指定关卡的yaml文件
2. 调用 boss-review skill 执行7维度审查+假阳性3条检查
3. 输出 `artifacts/projects/{project_id}/06_gate_review.yaml`（符合 `contracts/gate_review.schema.yaml`）

## 输出文件
`artifacts/projects/{project_id}/06_gate_review.yaml`

## 输出必须符合
`contracts/gate_review.schema.yaml`

## 关卡停止（强制输出）
```
━━━━━ 审查完成 ━━━━━
关卡：[G0/G1/G2/G3]
判定：[通过 / 不通过 / 条件通过]
致命问题：[N]个
非致命问题：[N]个
[如不通过] 修复后重新运行 /run-gate-review
━━━━━━━━━━━━━━━━
```
