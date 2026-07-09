# 干预式证据获取 Phase 10E 候选源注册表构造协议冻结（无执行，无主张）

日期: 2026-07-09

状态: `phase10e_candidate_source_registry_protocol_freeze_no_execution_no_claim`（仅协议冻结，无执行，无主张）。

授权: Phase 10E 是仅协议冻结检查点，定义如何在后续独立审查的阶段中构造或提供合格候选源注册表。Phase 10E 本身不构造、不 fetch、不 clone、不读取、不选择、不过滤、不物化、不填充、不执行任何注册表或源候选。Phase 10 独立于 Phase 9，不是 Phase 9R/9S 的延续、重新解释、修复、重跑、重算或加强。Phase 9 已关闭。

公开报告: [`phase10e_candidate_source_registry_protocol_freeze_no_execution_no_claim_report.json`](../../artifacts/phase10e_candidate_source_registry_protocol_freeze_no_execution_no_claim/phase10e_candidate_source_registry_protocol_freeze_no_execution_no_claim_report.json)

## 范围

Phase 10E 仅定义合格的未来候选源注册表如何被允许构造/提供。它定义必需的注册表 manifest/schema 字段、溯源字段、资格字段、排除原因、可审计性要求，以及仅 aggregate 公开报告规则。它定义允许的未来构造/提供路线但不执行。它定义硬停、替换规则、非自适应排序规则，以及未来执行阶段的验证检查。Phase 10E 不提出任何经验、验证、correctness、scoring、product、method、performance 或 generalization 主张。任何实际的注册表构造/提供/执行需在 Phase 10E commit + CI green 后的后续独立审查阶段进行。

Phase 10E 不构造/编辑/选择/过滤/提供/物化/填充候选注册表，不 fetch/clone/读取/scrape/inspect/sample 源仓库/材料，不重跑 Phase 10C 物化或变更冻结的 Phase 10B 协议，不评分/裁决/评估 correctness/计算 evidence_success/生成 metrics/创建验证证据，不增加阈值/回退/例外/渠道特定救援路径，不将 `bucket_zero` 视为部分成功，不将 Phase 9 artifacts 用作验证证据，不变更运行时/默认行为，不将用户批准措辞作为协议依赖。

## 门控引用

Phase 10E 只公开 immediate Phase 10D gate 的精确 commit/CI。较旧的 Phase 9 / 10A / 10B / 10C / hygiene 检查点只以 status/bucket/scope 级溯源携带，不作为精确 commit/CI 标识符重新发布。本地同树 git 提交不被读取或比较。

- Phase 9 状态：已关闭。
- Phase 10A 状态：`phase10a_independent_validation_protocol_freeze_no_execution_no_claim`。
- Phase 10B 状态：`phase10b_fresh_fenced_input_construction_protocol_freeze_no_execution_no_materialization_no_claim`。
- Phase 10C 结果为 repair/no-claim: 接受源桶为 `bucket_zero`，修复原因桶为 `bucket_no_eligible_channel_registry`（无合格候选源注册表可用）。
- 独立 CI 卫生 scope：仅 CI 基础设施，不属于经验证据/结果的一部分。
- Phase 10D 收尾/守卫 commit `acaa189`，CI 运行 `29016304662` green，状态 `phase10d_10c_repair_closeout_guard_no_claim`。Phase 10D 将 10C 关闭为 repair/no-claim，并仅授权 Phase 10E 候选源注册表构造协议冻结（仅协议冻结，非构造/执行）。

较旧的 Phase 9 / 10A / 10B / 10C / hygiene 精确 commit/CI 引用被 Phase 10E 刻意不重新发布（更紧的隐私）。只有 Phase 10D gate 常量是精确引用。

## 冻结的候选源注册表构造协议

以下仅为结构性协议冻结定义。Phase 10E 不执行、不构造、不 fetch、不 clone、不读取、不选择、不过滤、不物化、不填充、不评分、不裁决、不评估任何注册表或源候选。

- **允许的注册表 schema 字段**: `registry_provenance`, `registry_construction_route`, `registry_source_channel_classes`, `registry_deterministic_order_rule`, `registry_minimum_eligible_sources`, `registry_caps`, `registry_no_phase9_private_reuse`, `registry_operator_clean_room_attestation`, `registry_construction_audit_log`, `registry_exclusion_audit_log`, `registry_replacement_audit_log`, `registry_aggregate_only_public_projection`。
- **允许的注册表溯源字段**: `registry_construction_route`, `registry_source_channel_classes`, `registry_deterministic_order_rule`, `registry_no_phase9_private_reuse`, `registry_operator_clean_room_attestation`。
- **允许的候选描述符字段**: `normalized_public_project_identity`, `default_branch_name`, `public_metadata_stable_rank`, `channel_local_index`, `license_precheck`, `access_precheck`, `default_branch_precheck`, `currentness_precheck`, `content_integrity_precheck`。
- **允许的注册表资格字段**: `license_precheck`, `access_precheck`, `default_branch_precheck`, `currentness_precheck`, `content_integrity_precheck`。
- **预声明的排除原因**: `license_precheck_failed`, `access_precheck_failed`, `default_branch_precheck_failed`, `currentness_precheck_failed`, `content_integrity_precheck_failed`, `candidate_below_minimum_eligibility`, `candidate_duplicate_identity`, `candidate_not_from_allowed_channel_class`。
- **预声明的可审计性要求**: `registry_construction_audit_log_required`, `registry_exclusion_audit_log_required`, `registry_replacement_audit_log_required`, `registry_deterministic_order_verified`, `registry_no_phase9_private_reuse_verified`, `registry_aggregate_only_public_projection_verified`。
- **允许的未来构造/提供路线**: `neutral_public_acquisition_channels_only`, `operator_provided_external_registry`。
- **硬停**: 非零 Phase 9 私有重用停止构造; 自适应调优至观察结果停止构造; 源可用性后的后验选择停止构造; 排序或选择中的非零随机性停止构造; 观察后的注册表构造停止构造; 将零接受视为部分成功停止构造。
- **替换规则**: 仅在 labels/outcomes/scoring 之前替换; 仅从冻结资格池替换; 替换不基于观察结果; 替换确定性无随机性。
- **非自适应排序规则**: 冻结渠道顺序然后冻结公开元数据排序键; 无随机洗牌; 观察后无后验重排序; 确定性排序键预声明。
- **未来执行验证检查**: `registry_schema_fields_valid`, `registry_provenance_fields_complete`, `registry_eligibility_fields_present`, `registry_exclusion_reasons_in_predeclared_set`, `registry_audit_log_complete`, `registry_deterministic_order_verified`, `registry_minimum_eligible_sources_met_or_repair`, `registry_no_phase9_private_reuse_verified`, `registry_aggregate_only_public_projection_verified`。
- **仅 aggregate 公开报告规则**: 注册表内容不公开; 注册表候选细节不公开; 仅 aggregate 桶公开; 排除原因仅 aggregate; 无每源/每任务公开事实。

## 反自适应规则

Phase 10E 协议作为前瞻性构造/提供规则冻结，不调优以修复观察到的 Phase 10C `bucket_zero` / `bucket_no_eligible_channel_registry` 结果。

- Phase 10C 仅作为门控/溯源事实和需防范的失败模式被提及，而非优化反馈。
- 候选源资格、排序、替换、排除和审计规则为确定性且预声明。
- 无规则以"因为 10C 发现零接受源"为理由，除非表述为通用合规/审计要求。
- 未引入新的阈值/回退/渠道例外以专门避免 `bucket_no_eligible_channel_registry`。
- 未来执行必须按冻结的 10E 协议原文使用，在看到源可用性后无后验选择。

## Phase 10E 边界

- Phase 10E 不执行任何操作。
- Phase 10E 不提出新的证据主张。
- Phase 10E 不构造/编辑/选择/过滤/提供/物化/填充候选注册表。
- Phase 10E 不 fetch/clone/读取/scrape/inspect/sample 源材料。
- Phase 10E 不重跑 Phase 10C 物化。
- Phase 10E 不变更冻结的 Phase 10B 协议。
- Phase 10E 不评分/裁决/运行 correctness/evidence_success。
- Phase 10E 不增加阈值/回退/例外/渠道特定救援路径。
- Phase 10E 不将 `bucket_zero` 视为部分成功。
- Phase 10E 不将用户批准措辞作为协议依赖。

## 下一阶段

任何实际的候选源注册表构造/提供/执行需在 Phase 10E commit + CI green 后的后续独立审查阶段进行。未来执行必须按冻结的 10E 协议原文使用，在看到源可用性后无后验选择。不使用用户批准措辞。

## 隐私边界

公开输出仅限 aggregate/boundary。源特定细节（仓库名、URL、所有者、提交、路径、片段、行范围、数据包 ID、运行目录、每源/每任务/每数据包事实、候选身份、候选注册表内容、注册表 manifest 位置、注册表构造/排除审计日志、单例桶）仅保留在 ignored `runs/` 下。仅门控引用值为确切公开值，且仅允许在其确切门控路径上。

## 无主张边界

Phase 10E 不提出 method、product、performance、training、provider、model、runtime、default、scoring、outcome、evidence-success、correctness、generalization、validation、materialization-succeeded、independent-validation-passed、OpenLocus-works、Phase-10/10C/10D/10E-confirms、registry-construction-succeeded、registry-provision-succeeded 或 empirical 主张。Phase 10E 仅为协议冻结，而非 evidence/method/product/correctness/validation 成功。

保守建议为: `phase10e_candidate_source_registry_construction_protocol_freeze_only_phase9_closed_inherited_phase10a_gate_inherited_phase10b_gate_inherited_phase10c_executed_frozen_10b_route_once_repair_no_claim_zero_accepted_sources_phase10d_closeout_guard_gate_inherited_authorized_10e_protocol_freeze_only_phase10e_is_protocol_freeze_only_for_future_registry_construction_phase10e_does_not_construct_edit_select_filter_supply_materialize_or_populate_candidate_registry_phase10e_does_not_fetch_clone_read_scrape_inspect_or_sample_source_material_phase10e_does_not_rerun_10c_materialization_or_change_frozen_10b_protocol_phase10e_does_not_score_adjudicate_or_run_correctness_evidence_success_phase10e_does_not_add_thresholds_fallbacks_exceptions_or_channel_rescue_paths_phase10e_does_not_treat_bucket_zero_as_partial_success_phase10e_protocol_is_prospective_not_tuned_to_10c_zero_outcome_phase10e_10c_referenced_only_as_gate_and_failure_mode_not_optimization_feedback_candidate_eligibility_ordering_replacement_exclusion_audit_deterministic_and_predeclared_no_threshold_fallback_or_channel_exception_for_observed_repair_reason_future_execution_uses_frozen_10e_protocol_no_post_hoc_selection_after_source_availability_hygiene_commit_is_ci_infrastructure_only_not_empirical_evidence_future_registry_construction_or_provision_or_execution_requires_separate_phase_after_10e_commit_and_ci_green_boundary_review_after_phase10e_commit_and_ci_green_no_user_approval_wording_no_method_product_correctness_evidence_success_claim`。
