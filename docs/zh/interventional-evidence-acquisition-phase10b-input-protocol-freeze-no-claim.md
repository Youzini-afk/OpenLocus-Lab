# 干预式证据获取 Phase 10B 全新/围栏化输入构造协议冻结（无执行，无物化，无声明）

日期：2026-07-09

状态：`phase10b_fresh_fenced_input_construction_protocol_freeze_no_execution_no_materialization_no_claim`

授权：Phase 10B 是为全新独立 Phase 10 校验线设立的 docs/report/validator-only 协议冻结检查点，聚焦于全新/围栏化输入构造。Phase 10 独立于 Phase 9；它不是 Phase 9R/9S 的延续、重新解释、修复、重跑、重算或加强。Phase 10B 冻结具体的输入构造协议，但不实例化其中任何内容。

公开报告：[`phase10b_input_protocol_freeze_no_execution_no_materialization_no_claim_report.json`](../../artifacts/phase10b_input_protocol_freeze_no_execution_no_materialization_no_claim/phase10b_input_protocol_freeze_no_execution_no_materialization_no_claim_report.json)

## 范围

Phase 10B 仅限文档/报告/校验器。它不执行、不发现、不 fetch、不 clone、不采样、不生成真实 packets/tasks、不评分、不裁决、不评估 correctness/evidence_success、不读取私有/源 artifacts。它不 fetch、clone、read 或 materialize 任何 repository 或 source；不读取被忽略的 `runs/`、任何 Phase 9 私有 artifacts 或任何 Phase 10A 私有 artifacts；不发现公开源；不读取候选校验目标的源代码；不生成 tasks、不抽取采样、不生成真实 packets；不发起任何 provider/LLM/model 调用；不引入超出 coarse fixed status/boundary fields 的 metrics/thresholds/rates/counts；并且不使用低资源自主启动经验性工作。

## 门引用

Phase 10B gate 于 Phase 9 已关闭于 commit `1d71f6a`、CI run `28999245247`、CI 成功、Phase 9 closed；以及 Phase 10A 已提交于 `67e8d984601d82a2a97992bb83fda06b09e06be0`、CI run `29002587099`、CI 成功、Phase 10A 状态 `phase10a_independent_validation_protocol_freeze_no_execution_no_claim`。这些是 Phase 10B 发布的唯一精确公开门引用。较旧的 Phase 9 精确 commit/CI 引用被 Phase 10B 刻意不重新发布（更紧的隐私）。本地同树 git commits 不被读取或比较；只有门常量是精确引用。

## 冻结的输入构造协议（仅定义，不实例化）

Phase 10B 为未来 Phase 10C 冻结以下具体输入构造规则，但不实例化其中任何内容：

- **源资格规则**：无需认证即可公开访问、源归档可在使用前物化、存在声明或可公开审计的许可证、默认分支或等效修订版可解析、可从公开元数据检测范围内语言或文件组合、非 Phase 9 artifact 或 Phase 9 衍生材料、非私有先前阶段或手动命名种子材料。
- **新鲜度/围栏化定义**：输入必须是全新的（非从 Phase 9 重用）、与 Phase 9 私有 artifacts 围栏化、需独立复现包生成、无 Phase 9 priors/sources/labels/outcomes 作为输入、在任何采样或包生成前验证新鲜度、围栏化违规为硬停止。
- **独立于 Phase 9 的检查**：Phase 9 artifacts 不能作为校验证据、Phase 9 源过滤/priors 不能重用、Phase 9 labels/outcomes 不能作为输入重用、Phase 9 采样输入不能重用、clean-room 操作员不得使用对 Phase 9 私有材料的记忆。
- **确定性源排序/选择规则**：预声明种子标签（仅版本，禁止随机性）、稳定通道后稳定公开元数据顺序、预声明确定性排序键、仅在采样前替换、替换原因仅限于可用性或资格、禁止基于性能的替换、Phase 10B 中无实际采样抽取。
- **上限和中止限制**：结构性协议上限（候选检查总上限 48、接受源目标上限 12、接受源最小上限 8、每通道上限 16）是 coarse fixed boundary fields，非成功指标。在配额/排序漂移、资格漂移、围栏化违规、Phase 9 污染或隐私违规时中止。
- **私有/公开 artifact 分割**：仅公开聚合或边界输出、私有材料仅在被忽略的 `runs/` 下、除白名单门引用外不发布 repo/source/url/owner/commit、不发布路径/片段/行范围/标识符/运行位置、不发布每源/每任务/每包事实、不发布单例桶。
- **独立复现包模式**：仅模式定义，Phase 10B 中不生成包。包必须仅包含公开源身份和围栏化获取元数据、不得包含 Phase 9 artifacts 或私有行/可观察项、必须在未来 Phase 10C 中独立生成、必须支持仅聚合公开报告。
- **隐私扫描器规则**：拒绝私有形状键/值、单例桶、声明措辞、占位符措辞、用户批准措辞、精确计数字段、长未批准数字运行 ID。门精确值仅允许在精确门路径。

## 未来 10C 交接门（仅定义）

Phase 10C 需要：Phase 10B commit、Phase 10B CI green、在 Phase 10B commit + CI green 后、Phase 10C 之前的独立边界审查，以及明确的执行和物化边界。Phase 10B 不授权 Phase 10C 执行。实际发现/fetch/物化最早在 Phase 10C 中进行。

## 无声明边界

Phase 10B 不做任何方法、产品、性能、训练、provider、model、运行时、默认、评分、outcome、evidence-success、correctness、泛化或校验声明。Phase 10B 仅为协议冻结检查点，而非 evidence/method/product/correctness/validation 成功。

保守建议为：`phase10b_fresh_fenced_input_construction_protocol_freeze_only_for_new_independent_validation_line_phase9_closed_at_recorded_commit_and_ci_phase10a_gate_passed_at_recorded_commit_and_ci_phase10b_makes_no_evidence_method_product_performance_correctness_or_generalization_claims_phase10b_does_not_execute_discover_fetch_clone_sample_or_materialize_phase10b_does_not_read_private_or_source_artifacts_phase10b_does_not_reuse_phase9_artifacts_as_validation_evidence_future_input_construction_requires_fresh_fenced_inputs_independent_from_phase9_source_eligibility_freshness_fencing_and_deterministic_ordering_rules_frozen_caps_and_abort_limits_frozen_as_structural_protocol_limits_not_success_metrics_replication_packet_schema_defined_only_no_packets_generated_in_phase10b_private_public_artifact_split_frozen_aggregate_only_public_reporting_privacy_scanner_rules_frozen_phase10c_requires_separate_boundary_review_after_phase10b_commit_and_ci_green_no_private_reads_no_source_reads_no_discovery_no_fetch_clone_no_task_generation_no_sampling_draw_no_packet_generation_no_scoring_adjudication_correctness_or_evidence_success_evaluation_no_metrics_thresholds_rates_counts_beyond_coarse_fixed_status_boundary_fields_no_product_method_performance_correctness_generalization_claim`。
