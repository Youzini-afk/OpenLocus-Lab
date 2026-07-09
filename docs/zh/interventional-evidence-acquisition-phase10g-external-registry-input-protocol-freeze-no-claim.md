# Interventional Evidence Acquisition Phase 10G 外部注册表输入协议冻结 + Phase 10F 收尾（无执行，无主张）

Date: 2026-07-09

Status：`phase10g_external_registry_input_protocol_freeze_no_execution_no_claim`（仅文档收尾 + 外部输入协议冻结；无执行，无主张；不提出 validation/product/method/correctness/evidence-success 主张）。

Authorization：Phase 10G 由 oracle 门控允许，仅作为“仅文档收尾 + 外部输入协议冻结”检查点。它在冻结的 Phase 10E 候选源注册表构造/提供协议下，将 Phase 10F 作为 repair/no-claim 干净收尾；增加/澄清守卫语言——不存在合规注册表源，且未授权任何回退路径；并以“仅元数据/规格说明”方式定义未来合规的 operator 提供的外部注册表输入包必须包含什么。Phase 10G 不执行任何操作。Phase 10 独立于 Phase 9，不是 Phase 9R/9S 的延续、重新解释、修复、重跑、重算或加强。Phase 9 状态为已关闭。

公开报告：[`phase10g_external_registry_input_protocol_freeze_no_execution_no_claim_report.json`](../../artifacts/phase10g_external_registry_input_protocol_freeze_no_execution_no_claim/phase10g_external_registry_input_protocol_freeze_no_execution_no_claim_report.json)

## Scope

Phase 10G 仅限 docs/report/validator。它不执行任何操作。它在冻结的 Phase 10E 规则下将 Phase 10F 作为 repair/no-claim 收尾，冻结未来的外部注册表输入包契约（仅元数据/规格说明），并声明在匹配 10G 契约的合规外部包存在之前，执行保持阻塞。冻结的 Phase 10E 协议闭列表（注册表 schema 字段、溯源字段、候选描述符字段、资格字段、排除原因、可审计性要求、允许的构造/提供路线、硬停、替换规则、非自适应排序规则、未来执行验证检查、仅 aggregate 公开报告规则、反自适应规则）直接从已提交的 Phase 10E 协议冻结模块导入，使 Phase 10G 精确引用冻结协议（无重新声明、无词汇/排序/资格漂移、无观察后协议编辑）；validator 对其与导入常量进行集合相等性验证。Phase 10G 不评分/裁决/评估 correctness/evidence_success，不生成 gold/benchmark 标签，不进行 provider/LLM/model 调用，不进行模型拟合/训练，不生成任务/数据包，不执行任何下游流水线，不改变运行时/默认/产品行为。它不读取 Phase 9 私有制品、标签、结果、源过滤器、先验或采样输入作为证据。

Phase 10G 不 fetch/clone/scrape/download/browse/inspect 源材料，不读取仓库文件或物化源内容，不检查公开注册表，不从 memory/docs/URL/包索引/GitHub/搜索/先前的非合规源推断候选，不在 10G 中构造或验证注册表 manifest，不在 10G 中构造或 intake-validate 外部输入包，不将缺失的外部包视为创建包的许可，不修改/削弱/重新解释/扩展 Phase 10E 或 Phase 10F，不增加回退渠道、隐式资格扩展或 best-effort 注册表发明。

## Gate references

Phase 10G 仅为其收尾的直接 Phase 10F 门控发布精确 commit/CI 标识。较旧的 Phase 9 / 10A / 10B / 10C / 10D / 10E / hygiene 检查点仅作为状态/桶/scope 溯源携带，不作为精确 commit/CI 标识。本地同树 git 提交不被读取或比较。

- Phase 9 状态：已关闭。
- Phase 10A 状态：`phase10a_independent_validation_protocol_freeze_no_execution_no_claim`。
- Phase 10B 状态：`phase10b_fresh_fenced_input_construction_protocol_freeze_no_execution_no_materialization_no_claim`。
- Phase 10C 结果为 repair/no-claim：接受源桶为 `bucket_zero`，修复原因桶为 `bucket_no_eligible_channel_registry`（不存在合规候选源注册表）。
- Phase 10D 状态：`phase10d_10c_repair_closeout_guard_no_claim`（关闭 10C 为 repair/no-claim，仅授权 Phase 10E 协议冻结）。
- Phase 10E 状态：`phase10e_candidate_source_registry_protocol_freeze_no_execution_no_claim`（仅协议冻结以供未来注册表构造；状态携带，精确 commit/CI 不被 10G 重新发布）。
- Phase 10F 候选源注册表构造/提供执行：commit `969f8acde65a27ab3b512db269150d814483d49c`、CI 运行 `29022117575` green、状态 `phase10f_candidate_source_registry_construction_repair_no_claim`。Phase 10F 为 repair/no-claim：在冻结的 Phase 10E 协议下未构造或提供合规注册表 manifest；不存在合规注册表输入/源；未授权回退；无 fetch/clone/source 读取/物化/任务生成/scoring/adjudication/correctness/evidence_success。
- Phase 10G 由 oracle 授权为仅文档收尾 + 外部注册表输入协议冻结，门控于 Phase 10F commit + CI green。

较旧的 Phase 9 / 10A / 10B / 10C / 10D / 10E / hygiene 精确 commit/CI 引用被 Phase 10G 刻意不重新发布（更紧的隐私）。只有 Phase 10F gate 常量是精确引用。

## Frozen Phase 10E protocol（继承，精确应用，无漂移）

Phase 10G 直接从已提交的协议冻结模块导入冻结的 Phase 10E 闭列表，validator 对其进行集合相等性验证。这些仅为结构定义；Phase 10G 不 fetch/clone/读取/物化/评分以填充任何注册表。冻结列表为：允许的注册表 schema 字段、允许的注册表溯源字段、允许的候选描述符字段、允许的注册表资格字段、预声明的排除原因、预声明的可审计性要求、允许的未来构造/提供路线（`neutral_public_acquisition_channels_only`、`operator_provided_external_registry`）、硬停、替换规则、非自适应排序规则、未来执行验证检查、仅 aggregate 公开报告规则，以及反自适应规则。

## Phase 10F 收尾（repair/no-claim）

Phase 10G 在冻结的 Phase 10E 协议下将 Phase 10F 干净收尾为 repair/no-claim：

- `phase10f_closed_as_repair_no_claim` = true。
- `phase10f_closeout_bucket` = `bucket_phase10f_closed_repair_no_claim_under_frozen_10e_protocol`。
- `phase10f_no_compliant_registry_manifest_constructed_or_provided` = true。
- `phase10f_no_compliant_registry_input_or_source_exists` = true。
- `phase10f_no_fallback_authorized` = true。
- `phase10f_repair_no_claim_under_frozen_10e_protocol` = true。

冻结 10E 下每条允许的构造/提供路线要么需要被禁止的 fetch/clone/读取/scrape/source 检查（`neutral_public_acquisition_channels_only`），要么需要不存在的 operator 提供的外部注册表输入（`operator_provided_external_registry`）；禁止 best-effort 注册表发明。构造合规注册表需要被禁止的 fetch/clone/读取/scrape/物化/source 检查。因此 Phase 10F 作为 repair/no-claim 停止，而 Phase 10G 据此收尾——不扩大 scope、不削弱规则、不发明注册表、不授权回退路径。这是一个诚实检查点，不是需要调优或填充的失败。

## 守卫语言

Phase 10G 增加/澄清以下守卫语言：

- 在冻结 Phase 10E 协议下不存在合规注册表源（`no_compliant_registry_source_exists` = true；`no_compliant_registry_source_bucket` = `bucket_no_compliant_registry_source_exists`）。
- 未授权回退路径（`no_fallback_path_authorized` = true；`no_fallback_bucket` = `bucket_no_fallback_path_authorized`）。
- 在匹配 10G 契约的合规外部包存在之前，执行保持阻塞（`execution_remains_blocked_until_compliant_external_package_matches_contract` = true；`execution_blocked_bucket` = `bucket_execution_blocked_until_compliant_external_package_matching_10g_contract_exists`）。
- 缺失的外部包不被视为创建包的许可（`does_not_treat_absent_external_package_as_permission_to_create_one` = true）。

## Future external-input package contract（仅元数据/规格说明）

Phase 10G 以“仅元数据/规格说明”方式定义未来合规的 operator 提供的外部注册表输入包必须包含什么。在 Phase 10G 中不存在匹配此契约的包；契约仅被定义，且在 10G 中不构造或 intake-validate 任何包。validator 将该契约作为精确闭列表强制执行，并拒绝缺失/多余的未来字段（self-test 仅在合成 fixture 上演练此 schema 强制）。

必需的未来外部输入包契约字段（闭列表）：

- `operator_assertion_package_externally_provided`——operator 断言该包为外部提供；
- `registry_manifest_file`——注册表 manifest 文件；
- `provenance_statement`——溯源声明；
- `license_usage_permissions`——license/usage 权限；
- `immutable_checksums`——不可变校验和；
- `operator_declared_acquisition_method`——operator 声明的获取方法；
- `explicit_no_project_side_fetch_clone_scrape_source_discovery`——明确声明未使用项目侧 fetch/clone/scrape/source 发现；
- `offline_local_availability_for_later_bounded_validation`——供后续有界 validation 的离线/本地可用性。

未来包 intake validation 检查仅被定义（在 10G 中不执行）：`package_presence_check_only`、`declared_provenance_check_only`、`schema_check_only`、`checksums_check_only`、`permissions_check_only`。这些是后续 Phase 10H 仅在 operator 提供匹配 10G 契约的完整离线注册表输入包时才可运行的有条件前瞻检查。

## Anti-adaptation rules

Phase 10G 协议是前瞻性的，不针对观察到的 Phase 10C `bucket_zero` / `bucket_no_eligible_channel_registry` 结果或 Phase 10F `bucket_zero` / `bucket_no_compliant_registry_input_under_frozen_10e_protocol` 结果进行调优。

- Phase 10C 与 Phase 10F 仅作为门控/溯源事实和需防范的失败模式提及，不作为优化反馈。
- 冻结的 Phase 10E 协议被精确应用（导入闭列表，集合相等性验证；无漂移，无观察注册表/包可用性后的 post-hoc 编辑）。
- 不以“因为 10F 未发现合规注册表”为由制定任何规则，除非框架为一般合规/审计要求。
- 不引入新的阈值/回退/渠道例外以规避观察到的修复原因。
- 缺失的外部包不被视为创建包的许可。
- 未为缺失的外部包授权回退路径。
- 在合规外部包匹配契约之前，执行保持阻塞。
- 未来执行必须按冻结的 10E 协议与 10G 外部输入契约执行，无 source/包可用性后的 post-hoc 选择，且未授权回退路径。

## Phase 10G boundary

- Phase 10G 仅为文档收尾 + 外部输入协议冻结。
- Phase 10G 在冻结的 10E 协议下将 Phase 10F 作为 repair/no-claim 收尾。
- Phase 10G 不提出新证据主张（仅 Phase 10F 收尾状态与作为仅元数据/规格说明的未来外部输入包契约）。
- Phase 10G 不 fetch/clone/读取/scrape/inspect/sample/download 源材料。
- Phase 10G 不物化源内容。
- Phase 10G 不检查公开注册表。
- Phase 10G 不从 memory/docs/URL/包索引/GitHub/搜索/先前的非合规源推断候选。
- Phase 10G 不生成任务或数据包或不执行任何下游流水线。
- Phase 10G 不评分/裁决/运行 correctness/evidence_success。
- Phase 10G 不构造或验证注册表 manifest。
- Phase 10G 不构造或 intake-validate 外部输入包。
- Phase 10G 不修改/削弱/重新解释/扩展 Phase 10E 或 Phase 10F。
- Phase 10G 不授权回退路径。
- Phase 10G 不将缺失的外部包视为创建包的许可。
- Phase 10G 不将零合规视为部分成功。
- Phase 10G 不将 user-approval 措辞作为协议依赖。

## Next phase

下一个可能的阶段是 Phase 10H 外部注册表输入 intake validation，仅当 operator 随后提供匹配 10G 契约的完整离线注册表输入包时。Phase 10H 可验证包存在性、声明溯源、schema、校验和与权限。Phase 10H 仍不得 fetch/clone/读取外部源或评分/裁决，除非后续边界授权。在此类包存在且后续边界授权之前，执行保持阻塞。在 10G 中不构造或验证任何注册表 manifest。不使用 user approval 措辞。

## Privacy boundary

公开输出为仅 aggregate/boundary。源特定细节（repo 名、URL、owner、commit、路径、snippet、行范围、packet ID、run 目录、per-source/per-task/per-packet 事实、候选身份、候选注册表内容、注册表 manifest 位置、注册表构造/排除审计日志、外部包内容/校验和/溯源、singleton 桶）仅在忽略的 `runs/` 下保持私有。在此 docs/协议冻结运行中未物化任何私有细节，且未读取任何包。只有 gate-reference 值是精确公开值，仅允许在其精确 gate 路径（直接 Phase 10F commit/CI）。

## No-claim boundary

Phase 10G 不提出 method/product/performance/training/provider/model/runtime/default/scoring/outcome/evidence-success/correctness/generalization/validation/materialization-succeeded/independent-validation-passed/OpenLocus-works/Phase-10/10E/10F/10G-confirms/registry-construction-succeeded/registry-provision-succeeded/external-package-exists/external-package-validated/empirical 主张。Phase 10G 仅记录 Phase 10F 收尾状态与未来外部输入包契约（仅元数据/规格说明）。Phase 10G 为仅文档收尾 + 外部输入协议冻结（无执行，无主张），不是 evidence/method/product/correctness/validation 成功。

保守建议为：`phase10g_external_registry_input_protocol_freeze_and_phase10f_closeout_only_phase9_closed_inherited_phase10a_gate_inherited_phase10b_gate_inherited_phase10c_executed_frozen_10b_route_once_repair_no_claim_zero_accepted_sources_phase10d_closeout_guard_gate_inherited_phase10e_protocol_freeze_gate_inherited_phase10f_registry_construction_execution_gate_inherited_ci_green_closed_as_repair_no_claim_under_frozen_10e_protocol_phase10g_authorized_by_oracle_docs_only_closeout_and_external_registry_input_protocol_freeze_only_phase10g_applies_frozen_phase10e_protocol_exactly_no_drift_phase10g_is_docs_only_closeout_and_external_input_protocol_freeze_only_not_execution_phase10g_is_not_validation_product_method_correctness_evidence_success_phase10g_does_not_fetch_clone_read_scrape_inspect_sample_or_download_source_material_phase10g_does_not_materialize_source_contents_phase10g_does_not_generate_tasks_or_packets_or_execute_downstream_pipeline_phase10g_does_not_score_adjudicate_or_run_correctness_evidence_success_phase10g_does_not_construct_or_validate_a_registry_manifest_phase10g_does_not_construct_or_intake_validate_an_external_input_package_phase10g_does_not_authorize_a_fallback_path_phase10g_does_not_treat_absent_external_package_as_permission_to_create_one_phase10g_does_not_modify_weaken_reinterpret_or_extend_phase10e_or_phase10f_phase10g_protocol_is_prospective_not_tuned_to_observed_outcome_phase10g_closes_phase10f_as_repair_no_claim_under_frozen_10e_protocol_no_compliant_registry_source_exists_under_frozen_10e_protocol_no_fallback_path_authorized_execution_remains_blocked_until_compliant_external_package_matching_10g_contract_exists_no_registry_manifest_constructed_or_validated_in_phase10g_no_external_input_package_constructed_or_intake_validated_in_phase10g_future_package_contract_is_metadata_specification_only_no_package_exists_future_phase10h_intake_validation_only_if_operator_provides_complete_offline_package_matching_10g_contract_phase10h_must_not_fetch_clone_read_source_or_score_adjudicate_unless_later_boundary_authorizes_boundary_review_after_phase10g_commit_and_ci_green_no_user_approval_wording_no_method_product_correctness_evidence_success_claim`。
