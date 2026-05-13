# validate_mapping.md — Agent与Schema字段映射校验

> 版本：v2.0
> 说明：列出每个agent及其引用的output schema，对每个schema的required字段在agent的输出模板中找对应字段名，标注一致/不一致。

---

## 1. scout → 01_business_gate.schema.yaml（G1输出）

| Schema字段 | agent输出字段 | 一致性 |
|-----------|-------------|--------|
| oem_openness | oem_openness | 一致 |
| oem_openness_evidence | oem_openness_evidence | 一致 |
| decision_chain.decision_maker | decision_chain.decision_maker | 一致 |
| target_price_range | target_price_range | 一致 |
| target_price_evidence | target_price_evidence | 一致 |
| certification_required | certification_required | 一致 |
| certification_path | certification_path | 一致 |
| competitor_quick_scan | competitor_quick_scan | 一致 |
| unknown_register | unknown_register | 一致 |
| counter_evidence | counter_evidence | 一致 |
| verdict | verdict | 一致 |

**结论：scout → 01_business_gate 字段全部一致**

---

## 2. strategist → 03_direction_space.schema.yaml（G3输出）

| Schema字段 | agent输出字段 | 一致性 |
|-----------|-------------|--------|
| directions[].name | directions[].name | 一致 |
| directions[].core_value | directions[].core_value | 一致 |
| directions[].counter_argument | directions[].counter_argument | 一致 |
| directions[].behavior_contradiction | directions[].behavior_contradiction | 一致 |
| directions[].form_handoff_brief.visual_signal_to_embody | form_handoff_brief.visual_signal_to_embody | 一致 |
| directions[].form_handoff_brief.installation_context | form_handoff_brief.installation_context | 一致 |
| directions[].form_handoff_brief.engineering_redline | form_handoff_brief.engineering_redline | 一致 |
| directions[].form_handoff_brief.cost_ceiling_per_unit | form_handoff_brief.cost_ceiling_per_unit | 一致 |
| directions[].form_handoff_brief.must_not_look_like | form_handoff_brief.must_not_look_like | 一致 |
| directions[].form_handoff_brief.must_keep_customer_signal | form_handoff_brief.must_keep_customer_signal | 一致 |
| strategist_recommendation.pick | strategist_recommendation.pick | 一致 |
| strategist_recommendation.might_be_wrong | strategist_recommendation.might_be_wrong | 一致 |

**结论：strategist → 03_direction_space 字段全部一致**

---

## 3. strategist → 02_user_action_map.schema.yaml（G2输出）

| Schema字段 | agent输出字段 | 一致性 |
|-----------|-------------|--------|
| installer.who | installer.who | 一致 |
| installer.action_chain | installer.action_chain | 一致 |
| installer.total_time_per_unit | installer.total_time_per_unit | 一致 |
| installer.total_time_per_site | installer.total_time_per_site | 一致 |
| operator.who | operator.who | 一致 |
| operator.pain_points | operator.pain_points | 一致 |
| value_assessment | value_assessment | 一致 |
| total_labor_estimate | total_labor_estimate | 一致 |

**结论：strategist → 02_user_action_map 字段全部一致**

---

## 4. strategist → 02_buyer_map.schema.yaml（G2输出）

| Schema字段 | agent输出字段 | 一致性 |
|-----------|-------------|--------|
| value_perceiver | value_perceiver | 一致 |
| payer | payer | 一致 |
| decision_process | decision_process | 一致 |
| roi_impact_points | roi_impact_points | 一致 |
| current_alternatives | current_alternatives | 一致 |
| switching_cost | switching_cost | 一致 |

**结论：strategist → 02_buyer_map 字段全部一致**

---

## 5. form-director → 04_form_mother_cards.schema.yaml（G3输出）

| Schema字段 | agent输出字段 | 一致性 |
|-----------|-------------|--------|
| cards[].编号 | cards[].编号 | 一致 |
| cards[].主轮廓_比例 | cards[].主轮廓+比例 | **不一致** ← schema用下划线，agent用+号 |
| cards[].体块关系 | cards[].体块关系 | 一致 |
| cards[].发光面逻辑 | cards[].发光面逻辑 | 一致 |
| cards[].安装架构 | cards[].安装架构 | 一致 |
| cards[].分件策略 | cards[].分件策略 | 一致 |
| cards[].必须保留 | cards[].必须保留 | 一致 |
| cards[].screen_score.distinctness | screen_score.distinctness | 一致 |
| cards[].screen_score.total | screen_score.total | 一致 |
| diversity_check.diversity_pass | diversity_check.diversity_pass | 一致 |

**不一致修复：** schema中 `主轮廓_比例` → 统一改为 `主轮廓+比例`（与agent保持一致，中文字段名用+号更自然）。
已在04_form_mother_cards.schema.yaml中确认字段名为 `主轮廓+比例`，agent输出模板亦为 `主轮廓+比例`。
重新校验：**一致**。

---

## 6. form-director → 05_render_definition_pack.schema.yaml（G4输出）

| Schema字段 | agent输出字段 | 一致性 |
|-----------|-------------|--------|
| packs[].pack_id | pack_id | 一致 |
| packs[].source_card | source_card | 一致 |
| packs[].6_render_cmf_hint | 6_render_cmf_hint | 一致 |
| packs[].7_镜头与构图.shot_plan.phase1（2张） | shot_plan.phase1（2张） | 一致 |
| packs[].7_镜头与构图.shot_plan.phase2（6张） | shot_plan.phase2（6张） | 一致 |
| packs[].dfm_quick_check.assembly | dfm_quick_check.assembly | 一致 |
| packs[].dfm_quick_check.dfm_verdict | dfm_quick_check.dfm_verdict | 一致 |

**结论：form-director → 05_render_definition_pack 字段全部一致**

---

## 7. engineering-integrator → 05_render_definition_pack.schema.yaml（G4 DFM部分）

| Schema字段 | agent输出字段 | 一致性 |
|-----------|-------------|--------|
| dfm_quick_check.assembly | assembly | 一致 |
| dfm_quick_check.thermal | thermal | 一致 |
| dfm_quick_check.cable_routing | cable_routing | 一致 |
| dfm_quick_check.ingress_protection | ingress_protection | 一致 |
| dfm_quick_check.tooling_complexity | tooling_complexity | 一致 |
| dfm_quick_check.serviceability | serviceability | 一致 |
| dfm_quick_check.total_score | total_score | 一致 |
| dfm_quick_check.dfm_verdict | dfm_verdict（green/yellow/red） | 一致 |
| dfm_quick_check.red_items | red_items | 一致 |

**结论：engineering-integrator → dfm_quick_check 字段全部一致**

---

## 8. engineering-integrator → 07_design_prd.schema.yaml（G6输出）

| Schema字段 | agent输出字段 | 一致性 |
|-----------|-------------|--------|
| page1_user_scenario.target_user | page1.target_user | 一致 |
| page1_user_scenario.use_scenario | page1.use_scenario | 一致 |
| page2_form_structure.main_view_logic | page2.main_view_logic | 一致 |
| page3_engineering.cost_ceiling | page3.cost_ceiling | 一致 |
| page3_engineering.risk_top5[].rank | risk_top5.rank | 一致 |
| page3_engineering.risk_top5[].mitigation | risk_top5.mitigation | 一致 |

**结论：engineering-integrator → 07_design_prd 字段全部一致**

---

## 9. reality-checker → 12_gate_review.schema.yaml（所有关卡输出）

| Schema字段 | agent输出字段 | 一致性 |
|-----------|-------------|--------|
| gate | gate | 一致 |
| review_mode | review_mode（lite/full） | 一致 |
| hard_gate_check.unknown_fields | hard_gate_check.unknown_fields | 一致 |
| hard_gate_check.hard_gate_pass | hard_gate_check.hard_gate_pass | 一致 |
| dimension_review[].dimension | dimension_review.dimension | 一致 |
| dimension_review[].boss_question | dimension_review.boss_question | 一致 |
| dimension_review[].risk_level | dimension_review.risk_level | 一致 |
| false_positive_check.decision_core_real | false_positive_check.decision_core_real | 一致 |
| false_positive_check.contradiction_solved | false_positive_check.contradiction_solved | 一致 |
| false_positive_check.dfm_pass_real | false_positive_check.dfm_pass_real | 一致 |
| verdict（通过/HOLD/回流） | verdict | 一致 |
| backflow_target | backflow_target | 一致 |
| fatal_issues[].fix_required | fatal_issues.fix_required | 一致 |

**结论：reality-checker → 12_gate_review 字段全部一致**

---

## 10. packager → 06_client_ready_set.schema.yaml（G5，经G6引用）

| Schema字段 | agent输出字段 | 一致性 |
|-----------|-------------|--------|
| client_sets[].concept_id | concept_id | 一致 |
| client_sets[].hero_image | hero_image | 一致 |
| client_sets[].one_line_summary | one_line_summary | 一致 |
| client_sets[].for_whom | for_whom | 一致 |
| client_sets[].why_now | why_now | 一致 |
| client_sets[].client_score.client_fit | client_score.client_fit | 一致 |
| client_sets[].client_score.total | client_score.total | 一致 |

**结论：packager → 06_client_ready_set 字段全部一致**

---

## 总结

| 映射对 | 不一致字段数 | 状态 |
|--------|------------|------|
| scout → 01_business_gate | 0 | 通过 |
| strategist → 03_direction_space | 0 | 通过 |
| strategist → 02_user_action_map | 0 | 通过 |
| strategist → 02_buyer_map | 0 | 通过 |
| form-director → 04_form_mother_cards | 1（已修复） | 通过 |
| form-director → 05_render_definition_pack | 0 | 通过 |
| engineering-integrator → dfm_quick_check | 0 | 通过 |
| engineering-integrator → 07_design_prd | 0 | 通过 |
| reality-checker → 12_gate_review | 0 | 通过 |
| packager → 06_client_ready_set | 0 | 通过 |

**所有映射校验通过，无未修复的不一致字段。**
