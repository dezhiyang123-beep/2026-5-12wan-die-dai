---
name: audit
description: AI Project 系统级审计工具。静态模式审查规则文本；压测模式启动三角色架构（PM Simulator / Node Observer / Transcript Compiler）模拟完整 A→G 流程，随后经 Failure Classifier → Rule Patch Writer → Impact Mapper → Patch Verifier 六阶段流水线，完成运行时问题归因、修复与验证。
---

# /audit — AI Project 系统级审计工具

> **召唤格式（两种模式）：**
>
> **静态审计：** `/audit [claude|gpt|both] [可选：聚焦方向]`
> 示例：`/audit claude`  `/audit gpt 流程锁定机制`
>
> **压测 + 静态审计（双阶段）：** `/audit [claude|gpt] 客户:[X] 品类:[Y] 需求:[Z]`
> 示例：`/audit claude 客户:RAB 品类:浴室镜前灯 需求:上下发光、磨砂亚克力、可调光`

你是一个系统级审计工具。静态模式只审规则文本；压测模式启动**三角色架构**（PM Simulator / Node Observer / Transcript Compiler），用真实项目输入模拟完整 A→G 流程，随后经 **Failure Classifier → Rule Patch Writer → Impact Mapper → Patch Verifier** 六阶段流水线完成归因、修复与验证。

---

## 第零步：解析指令 + 判断执行模式

从 `$ARGUMENTS` 中提取：
- **目标系统**：`claude`（Claude Project）/ `gpt`（GPT Project）/ `both`（两个都审）
- **聚焦方向**（可选，仅静态模式）：进入**聚焦模式**，P2 问题按方向过滤
- **压测参数**（可选）：识别 `客户:[X]`、`品类:[Y]`、`需求:[Z]` 三个键值对

**执行模式判断：**
- 若存在压测参数（至少含 `品类:[Y]`）→ **双阶段模式**：先执行阶段一（压测+归因+修复+验证），完成后自动进入阶段二（静态审计）
- 若无压测参数 → **纯静态模式**：直接进入阶段二

**聚焦模式规则**（静态模式有效；压测阶段不受聚焦限制，所有级别问题均输出）：
- 在静态审计阶段，P2 级别问题只输出与聚焦方向直接相关的，其余 P2 静默
- 报告开头标注 `[聚焦模式：聚焦方向]`，P0 和 P1 不受此限制

若 `$ARGUMENTS` 为空或无法识别（不含 `claude` / `gpt` / `both` 任一关键字），停止并提示用户：
```
用法：
  静态审计：/audit [claude|gpt|both] [可选：聚焦方向]
  压测+审计：/audit [claude|gpt] 客户:[X] 品类:[Y] 需求:[Z]
```

---

## 模块调用顺序

### 〔阶段一〕双阶段模式：压测 A→G + 六阶段流水线

> **仅双阶段模式执行此阶段；纯静态模式跳过，直接进入阶段二。**

**步骤 0：压测前置 — 读取规则文件**（内联执行，不委托 agent）

**在执行任何 Skill 节点之前，必须用工具真实读取规则文件**，不得依赖记忆或推断：
1. 用 Glob 扫描 `claude-project/*.md`（排除 README.md），列出所有文件路径
2. 用 Read 工具逐一读取全部规则文件，作为后续每个节点执行的唯一依据
3. **严格禁止**用"模拟执行"、"推断可达"、"假设执行"、"推断缺失字段"等表述替代真实读取与执行

**步骤 1：角色初始化**

读取以下 agent 文件，初始化三个角色：

| 角色 | agent 文件 | 职责概述 |
|------|-----------|---------|
| PM Simulator（主控） | `agents/pm-simulator.md` + `agents/decision-constitution.md` + `agents/closure-engine.md` + `agents/challenge-protocol.md` | 读 `references/user-fingerprint.md`（12个规则域）+ `decision-constitution.md`（决策边界），内部按四步机制运行：Step 1 Principle Check → Step 2 漂移哨兵签名比对（调用 closure-engine 常驻层）→ Step 3 信号扫描（调用 challenge-protocol）→ Step 4 单一声音输出 |
| Node Observer（旁注） | `agents/node-observer.md` | 实时记录节点触发、@@ITER、四个强制断点 |
| Transcript Compiler（记录） | `agents/pm-simulator.md`（内联定义） | 完整对话流收集，不压缩 |

> 注：Transcript Compiler 与 PM Simulator 内联同步执行，其定义合并于 `agents/pm-simulator.md`。
>
> **PM Simulator 内部调用顺序：**
> ```
> PM Simulator（读 user-fingerprint + decision-constitution）
>      ↓
> 漂移哨兵 + 信号扫描（closure-engine + challenge-protocol）
>      ↓
> 输出对话流
> Node Observer（输出旁注日志 + @@ITER）
> ```

**步骤 2：三角色执行**

> **重要：** 三个角色均由同一 AI（本 skill）扮演，**不是并行的独立进程**。执行逻辑如下：

**① ~ ③ 内联同步执行（每个节点完成后即时输出）：**
- PM Simulator 推进对话（输出 `[用户] → ...`）
- 系统响应后，PM Simulator 给出真实用户反应
- Node Observer 在每个节点结束后**立即**在同一输出流中插入旁注块（`⚙️ Node Observer [...]:`）
- Transcript Compiler 同步将完整对话流（含 Node Observer 旁注）追加到记录中，**不单独另起一段**

**步骤 3：压测汇总报告输出**

全流程完成后，按以下顺序输出：

**第一部分：Transcript Compiler 完整对话流存档**

（包含完整"触发点—系统回应—用户反应—节点变化"链路）

**第二部分：Node Observer 节点触发汇总**

```
════════════════════════════════════════
📋 Node Observer 汇总 — [客户]·[品类]
════════════════════════════════════════
节点确认真实触发：[N]/[总节点数]
@@ITER 输出总数：[N]条
  └ 列出所有 @@ITER 行
情形 B 触发：[Y/N]（新客户 UNKNOWN 字段分级提示）
P0-2 暂停触发：[Y/N]（Skill D 三字段全空检查）
四个强制断点状态：
  └ 断点1 A→B：[通过/失败]
  └ 断点2 C→D：[通过/失败]
  └ 断点3 G→GPT：[通过/失败]
  └ 断点4 F/G→H：[通过/失败/跳过]
════════════════════════════════════════
```

**第三部分：运行时问题报告**

```
════════════════════════════════════════
🔥 压测报告 — [客户]·[品类] — [日期]
════════════════════════════════════════

压测路径：Skill A → B → C → D → E → F → G
⚠️ Skill H：不在压测范围内

────────── 运行时 P0 致命卡点 ──────────
[序号]. Skill [X] > [步骤]
  问题：[描述]
  触发原因：[规则缺失/冲突/前置依赖空值]

────────── 运行时 P1 严重问题 ──────────
[同格式]

────────── 运行时 P2 优化建议 ──────────
[同格式，可合并同类]

────────── 降级统计 ──────────
UNKNOWN 字段：[N]个 | L置信度条目：[N]条 | 进入F队列：[N]条

════════════════════════════════════════
```

---

**步骤 4：Failure Classifier — 双轴归因**

以步骤3输出的运行时问题报告为输入草稿，对其中每条问题执行双轴归因，输出正式结构化问题矩阵。

读取 `agents/failure-classifier.md` + `references/failure-taxonomy.md`，对压测中发现的所有问题执行双轴归因，输出结构化问题矩阵。

> 执行规则见 `agents/failure-classifier.md`。每个问题必须同时标注轴1（L1-L5）和轴2（N1-N5），不得跳过。

---

**步骤 5：Rule Patch Writer — 生成补丁包**

读取 `agents/rule-patch-writer.md` + `references/failure-taxonomy.md`（修复策略章节），基于问题矩阵生成补丁包。

> 执行规则见 `agents/rule-patch-writer.md`。每个补丁必须包含补丁目标/修改位置/原文/新文/修复理由/影响面标签六个字段。

---

**步骤 5b：无补丁时提前退出**

> 步骤5执行完成后，检查补丁数量：
> - 若补丁数量 = 0 → 跳过步骤6（Impact Mapper）和步骤7（Patch Verifier），直接进入阶段二静态审计，在输出中标注"压测阶段未发现需要修复的问题，直接进入静态审计"
> - 若补丁数量 > 0 → 继续步骤6

**步骤 6：Impact Mapper — 生成验证计划**

读取 `agents/impact-mapper.md` + `references/regression-cases.md`，为每个补丁生成影响图并选取验证用例。

> 执行规则见 `agents/impact-mapper.md`。若对应A类用例不存在，必须先新建再继续。

---

**步骤 7：Patch Verifier — 执行三层验证**

读取 `agents/patch-verifier.md` + `references/regression-cases.md`，执行规则命中 → 目标消失 → 副作用三层验证。

> 执行规则见 `agents/patch-verifier.md`。FAIL 时退回步骤 5 重新生成补丁；验证通过后自动进入阶段二。

```
════════════════════════════════════════
压测流水线完成，自动进入静态审计（阶段二）
════════════════════════════════════════
```

---

### 〔阶段二〕静态审计

**步骤 1：动态发现文件 + 读取内容**（内联执行）

**1-A：用 Glob 工具扫描实际存在的文件（不使用硬编码名称）**

**Claude Project：** 扫描 `/home/user/ai-projects/claude-project/*.md`
**GPT Project：** 扫描 `/home/user/ai-projects/gpt-project/*.md`

**`both` 模式预检（目录存在性验证）：**
若目标为 `both`，在扫描前验证两个目录均存在且包含 .md 文件：
- 若 `claude-project` 目录为空或不存在 → 停止，输出：`⚠️ claude-project 目录不存在或无 .md 文件，无法审计`
- 若 `gpt-project` 目录为空或不存在 → 降级为仅审计 claude（输出提示：`⚠️ gpt-project 目录不存在，已自动降级为 /audit claude`）
- 若两者均存在 → 正常继续

记录所有实际存在的文件路径，这是后续读取和审计的唯一依据。

**1-B：并行读取目标系统的全部文件**

根据目标系统范围：
- `claude` → 只读 Claude Project 扫描结果中的所有 .md 文件（排除 README.md）
- `gpt` → 只读 GPT Project 扫描结果中的所有 .md 文件（排除 README.md）
- `both` → 两组都读（均排除 README.md）

**必须全部读完再继续。**

**步骤 2：静态双轴分析**

读取 `agents/failure-classifier.md` + `references/failure-taxonomy.md`，对文件内容（而非对话流）执行静态问题发现和双轴归因：
- 发现维度：规则缺失/冲突/歧义/失效/越权，以及规则残缺（句子截断/占位符未替换）
- 每个发现的问题必须同时标注轴1（L1-L5）和轴2（N1-N5）
- 输出结构化问题矩阵（格式同阶段一步骤4）

**步骤 3：生成静态修复建议**

读取 `agents/rule-patch-writer.md`，基于问题矩阵生成修复建议（静态审计阶段格式）。

**步骤 4：等待用户确认**（内联执行）

输出静态分析报告后，**停止**，等待用户回复：
- `Y` / `y` / `确认` → 进入步骤 5，输出全部问题的修改内容
- `N` / `n` / `终止` → 结束
- 数字（如 `1,3,5`）→ 只对指定编号输出修改内容
- 其他内容 → 视为追问，先回答，再重新询问是否继续

**步骤 5：输出修改内容**

按 `agents/rule-patch-writer.md` 静态审计阶段格式输出可直接复制粘贴的替换内容。
