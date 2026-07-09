# 干预式证据获取 Phase 10P0 operator-package 协议冻结（不生成包，不执行 Phase 10 校验，无主张）

日期：2026-07-09

Status：`phase10p0_operator_package_protocol_freeze_no_package_generation_no_phase10_validation_no_claim`（仅 operator-package 协议冻结；不生成包，不执行 Phase 10 校验，无主张；不提出 validation/product/method/correctness/evidence-success 主张）。

Authorization：Phase 10P0 由 oracle 门控允许，仅作为“仅 operator-package 协议冻结”检查点。它门控于冻结的 Phase 10G 外部注册表输入协议冻结门（commit `c9c85aaf8e1811068acb8cf8265ddb2f4097f126`、CI green），并由 oracle 授权为仅 operator-package 协议冻结。Phase 10P0 冻结 operator 预备的离线注册表输入包的协议/规格说明；它不生成包内容，也不执行 Phase 10 校验。Phase 10 独立于 Phase 9，不是 Phase 9R/9S 或 Phase 10G 的延续、重新解释、修复、重跑、重算或加强。Phase 9 状态为已关闭。

公开报告：[`phase10p0_operator_package_protocol_freeze_no_package_generation_no_phase10_validation_no_claim_report.json`](../../artifacts/phase10p0_operator_package_protocol_freeze_no_package_generation_no_phase10_validation_no_claim/phase10p0_operator_package_protocol_freeze_no_package_generation_no_phase10_validation_no_claim_report.json)

## Scope

Phase 10P0 仅限 docs/report/validator。它冻结 operator 预备的离线注册表输入包的协议/规格说明：包目录布局、manifest schema、必需元数据字段、校验和/哈希算法、审计日志格式、隐私脱敏规则、溯源字段、源获取规则、纳入/排除标准、不可变性/冻结规则、operator 工作流，以及反调优守卫栏。它同时为后续生成的包提交溯源语言。在 Phase 10P0 中不生成、不选择、不 fetch、不 clone、不读取、不 scrape、不采样、不下载或不检查任何包。

必需措辞（已冻结、已提交）：

> Phase 10P0 freezes the protocol for an operator-prepared offline registry-input package. This phase does not generate package contents and does not perform Phase 10 validation.

未来包溯源措辞（已冻结、已提交）：

> operator-prepared package, produced by the current agent/operator preparation line under the frozen Phase 10P0 protocol; external to the Phase 10 validation pipeline, but not independent external-human generated.

Phase 10P0 不执行任何操作。它不评分/裁决/评估 correctness/evidence_success，不生成 gold/benchmark 标签，不进行 provider/LLM/model 调用，不进行模型拟合/训练，不生成任务/数据包，不执行任何下游流水线，不改变运行时/默认/产品行为。它不读取 Phase 9 私有制品、标签、结果、源过滤器、先验或采样输入作为证据。它不运行 Phase 10H intake validation。它不修改/削弱/重新解释/扩展 Phase 10G 或任何先前冻结的 Phase 10 协议。

## Gate references

Phase 10P0 仅为其冻结所依据的直接 Phase 10G 门控发布精确 commit/CI 标识。较旧的 Phase 9 / 10A / 10B / 10C / 10D / 10E / 10F / hygiene 检查点仅作为状态/桶/scope 溯源携带，不作为精确 commit/CI 标识。本地同树 git 提交不被读取或比较。

- Phase 9 状态：已关闭。
- Phase 10A 状态：`phase10a_independent_validation_protocol_freeze_no_execution_no_claim`。
- Phase 10B 状态：`phase10b_fresh_fenced_input_construction_protocol_freeze_no_execution_no_materialization_no_claim`。
- Phase 10C 结果为 repair/no-claim：接受源桶为 `bucket_zero`，修复原因桶为 `bucket_no_eligible_channel_registry`（不存在合规候选源注册表）。
- Phase 10D 状态：`phase10d_10c_repair_closeout_guard_no_claim`。
- Phase 10E 状态：`phase10e_candidate_source_registry_protocol_freeze_no_execution_no_claim`。
- Phase 10F 结果为 repair/no-claim：接受源桶为 `bucket_zero`，修复原因桶为 `bucket_no_compliant_registry_input_under_frozen_10e_protocol`（status `phase10f_candidate_source_registry_construction_repair_no_claim`）。
- Phase 10G status：`phase10g_external_registry_input_protocol_freeze_no_execution_no_claim`；gate commit `c9c85aaf8e1811068acb8cf8265ddb2f4097f126`、CI green。冻结的 Phase 10G status/phase 常量直接从已提交的 Phase 10G 协议冻结模块精确导入（无重新声明、无漂移、集合相等性验证）。
- Phase 10P0 由 oracle 授权为仅 operator-package 协议冻结，门控于 Phase 10G commit + CI green。

较旧的 Phase 9 / 10A / 10B / 10C / 10D / 10E / 10F / hygiene 精确 commit/CI 引用被 Phase 10P0 刻意不重新发布（更紧的隐私）。只有 Phase 10G gate commit 与 CI-green 标志是精确引用。

## 冻结的 operator-package 协议（闭列表，仅定义）

Phase 10P0 将以下协议/规格说明项冻结为精确闭列表。validator 将每一项作为集合相等性闭列表强制执行，并拒绝缺失/多余成员（self-test 仅在合成 fixture 上演练此 schema 强制）。这些仅为结构定义；不生成、不 fetch、不选择任何包以填充它们。

- 包目录布局字段：`manifest_json`、`sources_directory`、`audit_log_directory`、`checksums_sha256_file`、`provenance_json`、`package_readme_md`。
- Manifest schema 必需字段：`package_protocol_version`、`package_prepared_by`、`package_preparation_line`、`source_count_bucket`、`checksum_algorithm`、`immutable_freeze_timestamp`、`audit_log_format`、`privacy_redaction_applied`。
- 校验和/哈希算法：`sha256`（单一冻结算法）。
- 审计日志格式字段：`entry_type`、`entry_timestamp`、`entry_actor`、`entry_action`、`entry_subject_bucket`。
- 隐私脱敏规则：`redact_repo_urls`、`redact_owner_identities`、`redact_concrete_source_contents`、`publish_aggregate_buckets_only`、`confine_contents_to_ignored_private_path`。
- 溯源字段：`provenance_statement`、`provenance_preparation_line`、`provenance_externality`、`provenance_not_independent_external_human_generated`。
- 源获取规则：`operator_acquires_sources_offline`、`no_project_side_fetch_clone_scrape`、`sources_must_be_locally_available_before_package_sealed`、`acquisition_method_declared_by_operator`。
- 纳入/排除标准：`include_only_license_permitted_sources`、`exclude_sources_requiring_forbidden_fetch`、`exclude_sources_with_unresolved_license`、`deterministic_source_ordering_no_randomness`。
- 不可变性/冻结规则：`package_immutable_after_seal`、`checksums_frozen_at_seal_time`、`no_post_seal_modification`、`protocol_version_pinned_to_phase10p0`。
- Operator 工作流步骤：`operator_prepares_package_offline`、`operator_seals_package_with_checksums`、`operator_declares_provenance`、`package_written_to_ignored_private_path`。
- 反调优守卫栏：`protocol_not_tuned_to_phase10c_or_10f_zero_outcomes`、`no_threshold_padding_for_zero_outcomes`、`no_fallback_to_invent_sources`、`protocol_prospective_not_reactive`、`future_execution_uses_frozen_protocol_no_post_hoc_selection`。
- 未来包校验检查（仅定义，在 10P0 中不执行）：`package_layout_check_only`、`manifest_schema_check_only`、`checksum_algorithm_check_only`、`audit_log_format_check_only`、`privacy_redaction_check_only`、`provenance_wording_check_only`。这些是后续 Phase 10P1 在生成包时可运行、后续 Phase 10H 在 intake-validate 生成的包时可运行的前瞻检查。

## 反调优守卫栏

Phase 10P0 协议是前瞻性的，不针对观察到的 Phase 10C `bucket_zero` / `bucket_no_eligible_channel_registry` 结果或 Phase 10F `bucket_zero` / `bucket_no_compliant_registry_input_under_frozen_10e_protocol` 结果进行调优。

- Phase 10C 与 Phase 10F 仅作为门控/溯源事实和需防范的失败模式被提及，不作为优化反馈。
- 不以“因为 10C/10F 发现为零”为由制定任何规则，除非框架为一般合规/审计要求。
- 不引入新的阈值/回退/渠道例外以规避观察到的零结果。
- 未来包生成（Phase 10P1）必须按冻结的 10P0 协议原文使用，在看到源可用性后无 post-hoc 选择。

## 边界桶

Phase 10P0 记录以下边界桶：

- `bucket_no_package_contents_generated_or_selected_in_phase10p0`——未生成或选择包内容。
- `bucket_no_phase10_validation_performed_in_phase10p0`——未执行 Phase 10 校验。
- `bucket_phase10p0_protocol_freeze_only`——仅协议冻结。
- `bucket_package_generation_for_phase10p1_into_ignored_private_path`——包生成推迟至后续 Phase 10P1，写入忽略/私有路径。
- `bucket_phase10h_intake_validation_for_later_separately_authorized_phase`——Phase 10H intake validation 推迟至后续独立授权阶段。

## Phase 10P0 boundary

- Phase 10P0 仅为 operator-package 协议冻结。
- Phase 10P0 不生成包内容。
- Phase 10P0 不选择具体 repo 或源。
- Phase 10P0 不 fetch/clone/download/scrape/inspect 候选源。
- Phase 10P0 不创建含真实 repo URL 或身份的 manifest。
- Phase 10P0 不运行 Phase 10H intake validation。
- Phase 10P0 不评分/裁决/评估 correctness/evidence_success。
- Phase 10P0 不基于 Phase 10C 或 10F 零结果调优协议。
- Phase 10P0 不主张包为 independent external-human generated。
- Phase 10P0 不主张 validation 成功、恢复或 evidence 改进。
- Phase 10P0 不使用被禁止的溯源措辞。
- Phase 10P0 不修改/削弱/重新解释/扩展 Phase 10G。
- Phase 10P0 不将 user-approval 措辞作为协议依赖。

## 下一阶段

包生成仍留给后续 Phase 10P1，该阶段会在冻结的 10P0 协议下将任何包写入忽略/私有路径。Phase 10H intake validation 仍为后续独立授权阶段。仅当 operator 在冻结的 10P0 协议下提供完整离线包时，后续 Phase 10H 才可校验包布局、manifest schema、校验和算法、审计日志格式、隐私脱敏与溯源措辞。在此之前，不生成任何包，也不执行任何 Phase 10 校验。不使用 user-approval 措辞。

## 隐私边界

公开输出为仅 aggregate/boundary。源特定细节（repo 名、URL、owner、commit、路径、snippet、行范围、packet ID、run 目录、per-source/per-task/per-packet 事实、候选身份、包内容/校验和/溯源、manifest 中的真实 repo URL 或 owner 身份、singleton 桶）保持私有。在此协议冻结运行中未物化任何私有细节，未读取任何包，未 fetch 或 inspect 任何源。只有 Phase 10G gate commit 与 CI-green 标志是精确公开引用；所有较旧检查点仅作为状态/桶/scope。

## 无主张边界

Phase 10P0 不提出 method/product/performance/training/provider/model/runtime/default/scoring/outcome/evidence-success/correctness/generalization/validation/package-generated/package-validated/package-independent-external-human-generated/empirical 主张。Phase 10P0 仅记录冻结的 operator-package 协议规格说明与已提交的溯源语言。Phase 10P0 仅为协议冻结（不生成包，不执行 Phase 10 校验，无主张），不是 evidence/method/product/correctness/validation 成功。
