# 项目状态面板

> 每关卡执行后更新本文件。只读，不编辑。

## 项目基本信息

```
project_id: [YYYYMMDD-客户-品类]
client_name: [客户名称]
mode: M1 / M2 / M3
started_at: [YYYY-MM-DD]
```

## 当前状态

```
current_gate: [G0 / G1 / G2 / G3方向 / G3母题 / G4 / G5 / G6]
gate_status: [go / hold / stop / 待用户选择 / 等待出图 / 完成]
last_updated: [YYYY-MM-DD HH:MM]
```

## 阻断项（Blockers）

```yaml
blockers:
  - type: "HOLD / 红灯包 / UNKNOWN字段"
    description: "[具体描述]"
    action_required: "[用户需要做的动作]"
```

## 已完成关卡摘要

```yaml
completed_gates:
  G0:
    status: 完成
    products: ["00_project_brief.yaml"]
    verdict: go
    notes: "[关键发现]"
  G1:
    status: 完成
    products: ["01_business_gate.yaml"]
    verdict: go / hold / stop
    hold_reason: "[如有]"
  G2:
    status: 完成
    products: ["02_user_action_map.yaml", "02_buyer_map.yaml"]
    notes: "[关键用户洞察]"
  G3_directions:
    status: 待用户选择 / 完成
    products: ["03_direction_space.yaml"]
    selected_direction: "[D-A / D-B / D-C]"
  G3_forms:
    status: 待用户筛选 / 完成
    products: ["04_form_mother_cards.yaml"]
    weak_cards: ["M-XX"]
    selected_cards: ["M-XX × 8"]
  G4:
    status: 等待phase1出图 / 完成
    products: ["05_render_definition_pack.yaml"]
    dfm_red: []
    dfm_yellow: []
  G5:
    status: 完成
    products: ["06_image_review_matrix.yaml", "06_client_ready_set.yaml"]
    passed_count: 0
    failed_count: 0
  G6:
    status: Step1完成 / Step3完成
    products: []
    review_verdict: 通过 / 不通过
```

## 下一步

```
next_action: "[具体下一步操作，如：执行 /run-g3-forms，或：用户选定方向后执行]"
next_command: "[可直接执行的命令，如：/run-g3-forms]"
```

---
*由各关卡命令自动更新，不要手动编辑*
