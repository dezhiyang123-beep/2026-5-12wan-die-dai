# /run-g0-scout — 启动G0快速扫描

## 调用角色
agent: scout

## 前置检查
1. 确认用户已提供：客户名称 + 产品品类关键词
2. 读取 `knowledge/clients/{client}.md`，提取price_ceiling/must_certify/style_forbidden
3. 如客户档案不存在，scout自动取证4个字段并警告"客户档案缺失，取证结果需用户核实"

## 执行步骤
1. 如果用户未填brief，先生成 `artifacts/projects/{project_id}/00_brief.yaml`（从用户输入提取字段）
2. scout调用 research-pack skill 执行G0扫描
3. 输出 `artifacts/projects/{project_id}/01_g0_scan.yaml`（符合 `contracts/g0_scan.schema.yaml`）
4. 输出关卡停止格式

## 输出文件
- `artifacts/projects/{project_id}/00_brief.yaml`
- `artifacts/projects/{project_id}/01_g0_scan.yaml`

## 输出必须符合
`contracts/g0_scan.schema.yaml`

## 关卡停止（强制输出）
```
━━━━━ G0 完成 ━━━━━
决策：继续G1深度情报？还是放弃此品类？
请明确回答：继续 / 放弃
━━━━━━━━━━━━━━━━
```
