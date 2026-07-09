# 干预式证据获取 Phase 10F 候选源注册表构造/提供执行（修复，无主张）

日期: 2026-07-09

状态: `phase10f_candidate_source_registry_construction_repair_no_claim`（注册表 manifest 构造/提供执行；repair/no-claim；不提出 validation/product/method/correctness/evidence-success 主张）。

授权: Phase 10F 由 oracle 门控与冻结的 Phase 10E 候选源注册表构造/提供协议允许，仅构造和/或提供候选源注册表 *manifest*，严格遵循冻结的 Phase 10E 规则。Phase 10F 允许仅构造/提供注册表 manifest、验证 manifest 资格/提供协议、记录 10E 所需的注册表级元数据、将任何私有/非公开注册表细节存储在 ignored `runs/` 下、并仅发布 aggregate/bucket 级公开报告。Phase 10 独立于 Phase 9，不是 Phase 9R/9S 的延续、重新解释、修复、重跑、重算或加强。Phase 9 已关闭。

公开报告: [`phase10f_registry_construction_execution_no_claim_report.json`](../../artifacts/phase10f_registry_construction_execution_no_claim/phase10f_registry_construction_execution_no_claim_report.json)

## 范围

Phase 10F 仅在冻结的 Phase 10E 协议下执行候选源注册表 manifest 构造/提供。冻结的 Phase 10E 协议闭列表（注册表 schema 字段、溯源字段、候选描述符字段、资格字段、排除原因、可审计性要求、允许的构造/提供路线、硬停、替换规则、非自适应排序规则、未来执行验证检查、仅 aggregate 公开报告规则、反自适应规则）直接从已提交的 Phase 10E 协议冻结模块导入，使 Phase 10F 严格应用冻结协议（无重新声明、无词汇/排序/资格漂移、观察后无协议编辑）。Phase 10F 不评分、不裁决、不评估 correctness/evidence_success、不生成 gold/benchmark 标签、不进行任何 provider/LLM/model 调用、不进行模型拟合/训练、不生成任务/数据包、不执行任何下游流水线、不变更运行时/默认/product。它不将 Phase 9 私有 artifacts/标签/结果/源过滤器/先验/采样输入用作证据。

Phase 10F 不 fetch/clone/scrape/download/inspect 源材料，不读取仓库文件或物化源内容，不生成任务/数据包或不执行任何超出 10E 允许的注册表级 manifest 的下游流水线，不在看到注册表可用性后修改/削弱/重新解释/扩展 10E，不增加回退渠道、隐式资格扩展或 best-effort 注册表发明。

## 门控引用

Phase 10F 只公开 immediate Phase 10E gate 的精确 commit/CI。较旧的 Phase 9 / 10A / 10B / 10C / 10D / hygiene 检查点只以 status/bucket/scope 级溯源携带，不作为精确 commit/CI 标识符重新发布。本地同树 git 提交不被读取或比较。

- Phase 9 状态：已关闭。
- Phase 10A 状态：`phase10a_independent_validation_protocol_freeze_no_execution_no_claim`。
- Phase 10B 状态：`phase10b_fresh_fenced_input_construction_protocol_freeze_no_execution_no_materialization_no_claim`。
- Phase 10C 结果为 repair/no-claim: 接受源桶为 `bucket_zero`，修复原因桶为 `bucket_no_eligible_channel_registry`（无合格候选源注册表可用）。
- Phase 10D 状态：`phase10d_10c_repair_closeout_guard_no_claim`（将 10C 关闭为 repair/no-claim，并仅授权 Phase 10E 协议冻结）。
- Phase 10E 候选源注册表构造协议冻结: commit `285543ba4006773a65b813f0a5fdeb7a840d7d3c`，CI 运行 `29018708378` green，状态 `phase10e_candidate_source_registry_protocol_freeze_no_execution_no_claim`。Phase 10E 仅冻结构造/提供协议（无执行、无构造）。
- Phase 10F 由 oracle 授权为仅候选源注册表构造/提供，门控于 Phase 10E commit + CI green。

较旧的 Phase 9 / 10A / 10B / 10C / 10D / hygiene 精确 commit/CI 引用被 Phase 10F 刻意不重新发布（更紧的隐私）。只有 Phase 10E gate 常量是精确引用。

## 冻结的 Phase 10E 协议（严格应用，无漂移）

Phase 10F 直接从已提交的协议冻结模块导入冻结的 Phase 10E 闭列表，并由验证器进行集合相等性检查。这些仅为结构性定义；Phase 10F 不 fetch/clone/读取/物化/评分以填充任何注册表。冻结列表为：允许的注册表 schema 字段、允许的注册表溯源字段、允许的候选描述符字段、允许的注册表资格字段、预声明的排除原因、预声明的可审计性要求、允许的未来构造/提供路线（`neutral_public_acquisition_channels_only`、`operator_provided_external_registry`）、硬停、替换规则、非自适应排序规则、未来执行验证检查、仅 aggregate 公开报告规则、以及反自适应规则。

## 修复/无主张结果

本次执行运行为 repair/no-claim。在冻结的 Phase 10E 协议下未构造或提供任何合格的候选源注册表 manifest：

- `registry_manifest_compliance_bucket` = `bucket_zero`。
- `compliant_candidate_source_bucket` = `bucket_zero`。
- `repair_reason_bucket` = `bucket_no_compliant_registry_input_under_frozen_10e_protocol`。
- `repair_no_claim` = true；`registry_manifest_construction_attempted` = false；`compliant_registry_manifest_constructed` = false；`compliant_registry_manifest_provided` = false；`no_private_registry_manifest_materialized` = true。

冻结 10E 下的每条允许的构造/提供路线要么需要被禁止的 fetch/clone/读取/scrape/源检查（`neutral_public_acquisition_channels_only`），要么需要不存在的 operator 提供的外部注册表输入（`operator_provided_external_registry`）；best-effort 注册表发明被禁止。构造合格注册表将需要被禁止的 fetch/clone/读取/scrape/物化/源检查，且资格依赖于在没有被禁止检查下不可用的信息。因此 Phase 10F 作为 repair/no-claim 停止，而非扩大范围、削弱规则或发明注册表。这是一个诚实检查点，而非需调优或填充的失败。

## 反自适应规则

Phase 10F 协议为前瞻性，不调优以修复观察到的 Phase 10C `bucket_zero` / `bucket_no_eligible_channel_registry` 结果。

- Phase 10C 仅作为门控/溯源事实和需防范的失败模式被提及，而非优化反馈。
- 冻结的 Phase 10E 协议被严格应用（导入闭列表，集合相等性验证；无漂移，看到注册表可用性后无后验编辑）。
- 无规则以"因为 10C 发现零接受源"为理由，除非表述为通用合规/审计要求。
- 未引入新的阈值/回退/渠道例外以专门避免 `bucket_no_compliant_registry_input_under_frozen_10e_protocol`。
- 未来执行必须按冻结的 10E 协议原文使用，在看到源可用性后无后验选择。

## Phase 10F 边界

- Phase 10F 仅在冻结的 10E 协议下进行构造/提供。
- Phase 10F 不提出新的证据主张（仅注册表 manifest 构造/提供状态）。
- Phase 10F 不 fetch/clone/读取/scrape/inspect/sample/download 源材料。
- Phase 10F 不物化源内容。
- Phase 10F 不生成任务或数据包或不执行任何下游流水线。
- Phase 10F 不评分/裁决/运行 correctness/evidence_success。
- Phase 10F 不修改、削弱、重新解释或扩展 Phase 10E。
- Phase 10F 不增加回退渠道、隐式资格扩展或 best-effort 注册表发明。
- Phase 10F 不将零合规视为部分成功。
- Phase 10F 不将用户批准措辞作为协议依赖。

## 下一阶段

任何实际的候选源注册表构造/提供/执行或下游流水线需在 Phase 10F commit + CI green 后的后续独立审查阶段进行。未来执行必须按冻结的 10E 协议原文使用，在看到源可用性后无后验选择。不使用用户批准措辞。

## 隐私边界

公开输出仅限 aggregate/boundary。源特定细节（仓库名、URL、所有者、提交、路径、片段、行范围、数据包 ID、运行目录、每源/每任务/每数据包事实、候选身份、候选注册表内容、注册表 manifest 位置、注册表构造/排除审计日志、单例桶）仅保留在 ignored `runs/` 下。在此修复/无主张运行中，未物化任何私有注册表细节。仅门控引用值为确切公开值，且仅允许在其确切门控路径上。

## 无主张边界

Phase 10F 不提出 method、product、performance、training、provider、model、runtime、default、scoring、outcome、evidence-success、correctness、generalization、validation、materialization-succeeded、independent-validation-passed、OpenLocus-works、Phase-10/10E/10F-confirms、registry-construction-succeeded、registry-provision-succeeded 或 empirical 主张。Phase 10F 仅记录注册表 manifest 构造/提供状态。Phase 10F 仅为构造/提供执行（repair/no-claim），而非 evidence/method/product/correctness/validation 成功。

保守建议为: `phase10f_candidate_source_registry_construction_or_provision_only_under_frozen_phase10e_protocol_phase9_closed_inherited_phase10a_gate_inherited_phase10b_gate_inherited_phase10c_executed_frozen_10b_route_once_repair_no_claim_zero_accepted_sources_phase10d_closeout_guard_gate_inherited_phase10e_protocol_freeze_gate_inherited_ci_green_authorized_phase10f_candidate_source_registry_construction_or_provision_only_by_oracle_phase10f_applies_frozen_phase10e_protocol_exactly_no_drift_phase10f_is_candidate_source_registry_construction_or_provision_only_not_validation_product_method_correctness_evidence_success_phase10f_does_not_fetch_clone_read_scrape_inspect_sample_or_download_source_material_phase10f_does_not_materialize_source_contents_phase10f_does_not_generate_tasks_or_packets_or_execute_downstream_pipeline_phase10f_does_not_score_adjudicate_or_run_correctness_evidence_success_phase10f_does_not_modify_weaken_reinterpret_or_extend_phase10e_phase10f_does_not_add_fallback_channels_or_implicit_eligibility_expansion_or_best_effort_registry_invention_phase10f_does_not_treat_zero_compliance_as_partial_success_phase10f_protocol_is_prospective_not_tuned_to_observed_outcome_phase10f_repair_no_claim_no_compliant_registry_manifest_constructed_or_provided_under_frozen_10e_protocol_constructing_compliant_registry_would_require_forbidden_fetch_clone_read_scrape_or_source_inspection_no_compliant_registry_input_or_operator_provided_external_registry_available_under_frozen_10e_protocol_private_registry_details_under_ignored_runs_only_none_materialized_future_registry_construction_or_provision_or_execution_or_downstream_requires_separate_phase_after_10f_commit_and_ci_green_boundary_review_after_phase10f_commit_and_ci_green_no_user_approval_wording_no_method_product_correctness_evidence_success_claim`。
