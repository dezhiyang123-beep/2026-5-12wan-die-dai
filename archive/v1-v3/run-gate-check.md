# /run-gate-check — 任意关卡审查

## 命令说明

调用 reality-checker 对指定关卡的产物执行审查。支持 review_mode 参数覆盖默认模式。

## 使用方式

```
/run-gate-check [关卡] [review_mode]
```

示例：
- `/run-gate-check G1` — G1 lite审查（默认）
- `/run-gate-check G6` — G6 full审查（默认）
- `/run-gate-check G3 full` — G3使用full模式（覆盖默认lite）

## 默认 review_mode

| 关卡 | 默认模式 |
|------|---------|
| G1 | lite |
| G2 | lite |
| G3 | lite |
| G5 | full |
| G6 | full |

## lite模式审查内容

- G1：4项硬门槛（oem_openness / target_price_range / certification_path / decision_maker）
- G2：4项硬门槛（installer.who / operator.who / value_assessment / buyer_map.payer）
- G3：母题三维度多样性（主轮廓≥4 / 安装架构≥3 / 发光面逻辑≥3）

## full模式审查内容

- 完整7维度追问（每个维度必须引用竞品数据）
- 假阳性3条（决策核真实性 / 矛盾消解 / DFM PASS真实性）
- 致命问题拦截

## 执行步骤

1. 读取对应关卡的最新产物文件
2. 读取 `01_business_gate.yaml` 获取竞品矩阵（full模式用于对比引用）
3. 调用 reality-checker 执行指定模式的审查
4. 产出 `12_gate_review.yaml`

## 执行完成后

更新 `artifacts/projects/{project_id}/00_status_dashboard.md`：
- gate_status: [通过/HOLD/回流]
- blockers: [致命问题列表，如有]

## 输出产物

- `artifacts/projects/{project_id}/12_gate_review.yaml`
- `artifacts/projects/{project_id}/00_status_dashboard.md`（更新）

## 关卡停止格式

```
━━━━━ 关卡审查完成 ━━━━━
模式：lite / full
关卡：[G1/G2/G3/G5/G6]
判定：通过 / HOLD / 回流→[目标关卡]
致命问题：[N]个
[列出致命问题]
━━━━━━━━━━━━━━━━━━━━━━
```
