# BEA-v1-HAAE-R0 Hierarchical Actionable Evidence Acquisition Route Design / Schema Preflight

日期：2026-06-30

BEA-v1-HAAE-R0 是下一 acquisition route 的 **public-only design/schema preflight**，由 N10ET 收尾（checkpoint `26d817e`）开启。它 **不是** 执行阶段。HAAE-R0 只读取 public artifacts/docs/current conclusions/research logs/README 与 git metadata：

- 已提交的 N10ET public aggregate report（授权 HAAE-R0 的 close-out design/decision）；
- N10ET evaluator，仅用于 schema/status 校验（不执行——不 rerun/recompute）；
- N10ET EN/ZH docs、EN/ZH current-research-conclusions、EN/ZH research-log/summary 与 README public readback；
- git metadata：记录 N10ET 结果的 `26d817e` checkpoint。

禁止：任何 private reads（project-private roots、temporary rerun paths、CI raw logs、repo clones、raw candidates/orders/labels/paths/queries/tasks/repos、per-task diagnostics）、任何 CI rerun、任何 retrieval/recompute、任何 candidate generation/materialization、任何 arm scoring、任何 selector/reranker execution、任何 threshold tuning、任何 promotion、任何 runtime/default change、任何 method/downstream/heldout claim、任何 OpenLocus execution、任何 provider/embedding network call、任何 P5/BEA-v1-A 授权、或任何 runtime/default promotion。

## N10ET source lock

```text
n10et checkpoint: 26d817e
n10et status: n10et_public_safety_probe_design_decision_complete_haae_r0_authorized
n10et next allowed phase: BEA-v1-HAAE-R0 Hierarchical Actionable Evidence Acquisition
                           Route Design / Schema Preflight
haae r0 authorized by n10et: true (haae_r0_design_only_schema_preflight_authorized_bool)
haae r0 execution authorized by n10et: false (haae_r0_execution_authorized_bool)
bea_v1_a authorized by n10et: false (bea_v1_a_authorized_bool)
p5 authorized by n10et: false (p5_authorized_bool)
selector/reranker authorized by n10et: false (selector_reranker_authorized_bool)
runtime/default change authorized by n10et: false
n10et haae r0 non-identity booleans: 全部为 true (not_bea_v1_a, not_selector_only,
  not_selector_reranker_execution, not_p5, not_runtime_default_promotion)
n10et source locked: true
no_ci_rerun / no_retrieval / no_recompute / no_private_input_read: true
```

## 结果

```text
status: haae_r0_design_schema_preflight_complete_haae_r1_authorized
self-test: 132 / 132
forbidden scan: pass
private input reads: 0
retrieval executions: 0
recomputes: 0
CI reruns: 0
candidate generations: 0
arm scorings: 0
openlocus executions: 0
n10et source locked: true (checkpoint 26d817e)
next allowed phase: BEA-v1-HAAE-R1 Unified Private Trace Schema Feasibility Inventory
```

## HAAE-R0 显式 non-identities

HAAE-R0 明确 **不是** 以下任何一项（每条 control-plane record 与 stop/go record 都带有对应的 non-identity boolean）：

- **不是 BEA-v1-A** —— 它不是 coverage-preserving selector route。
- **不是 selector-only** —— 它不是 selector-only design。
- **不是 selector/reranker execution** —— 它不执行 selector 或 reranker。
- **不是 P5** —— 它不是 P5 selector/reranker 阶段。
- **不是 runtime/default promotion** —— 它不改 runtime/default 行为。

## Route architecture（4 个 hierarchical layers，design-only）

HAAE route 被设计为 4-layer hierarchical、actionable-evidence acquisition route。每个 layer 保留 `EvidenceCore` 并在 current-source evidence 不可用时 abstain。HAAE-R0 不执行任何 layer。

1. **source_acquisition** —— anchor/source-acquisition layer 定义如何从 current source surface 获取 candidate sources（identifier-normalized BM25、exact search、symbol、graph）。它在无 current-source evidence 时 abstain，并仅输出 aggregate candidate-pool buckets（无 raw candidates/paths/queries）。
2. **rank_pack_depth_to_head** —— rank/pack depth-to-head layer 定义如何将深度 candidates 打包到 head（novel-vs-old-pool-first、bounded merge-order、difference-aware guarded/else-full）。它仅在 aggregate rank/pack buckets 上操作，不执行 selector 或 reranker。
3. **span_projection** —— span-projection layer 定义如何在已获取内容上投影 spans（symmetric/asymmetric span windows、shape-gated expansion）。它仅输出 aggregate span-overlap buckets，并在 current source 无法产生 citation-valid span 时 abstain。
4. **scheduler_operating_point** —— scheduler-operating-point layer 定义如何在 cost/budget gate 下调度 retrieval actions（BEA-v1 P4 scheduler operating-point contract）。它在 action-cost frontier 上选择 operating point，并在会违反 EvidenceCore 或超出 budget 时 abstain。此处仅 design；不执行 scheduler。

## Unified private trace schema spec（10 groups，design-only）

HAAE-R0 设计了 10 groups 的 unified private trace schema。每个 group 都是 **private-root-only** 且 **aggregate-bucket-only**：永不发布 raw per-task paths/queries/candidates/labels/spans/ranks。HAAE-R0 不做 replay、不 scoring、不 retrieval、不 candidate generation。

| # | Group | Aggregate columns (bucket-only) |
|---|---|---|
| 0 | task_identity | anonymous_task_id, repo_bucket, language_bucket |
| 1 | anchor_source | anchor_kind_bucket, acquisition_cost_bucket |
| 2 | candidate_pool | candidate_count_bucket, depth_distribution_bucket |
| 3 | rank_pack | topk_pack_bucket, novel_vs_old_pool_bucket |
| 4 | span_projection | span_window_bucket, span_overlap_bucket |
| 5 | scheduler_action | scheduled_action_bucket, action_cost_bucket |
| 6 | evidence_core | path_bucket, line_range_bucket, content_sha_bucket, score_bucket, why_bucket, channels_bucket |
| 7 | arm_assignment | arm_bucket, budget_bucket |
| 8 | outcome_metric | citation_validity_bucket, file_recovery_topk_bucket, lost_baseline_top10_bucket |
| 9 | safety_probe_signal | full_guard_diffaware_loss_bucket, risk_bucket_signal |

## Public aggregation contract（4 aggregations，design-only）

Unified private trace schema 通过 4 个 aggregation contract 聚合成 public buckets（全部 aggregate-bucket-only，无 raw release）：

- **task_count_aggregate** —— public_task_count / scored_task_count / task_with_gold_count / repo_count（来自 task_identity + candidate_pool）。
- **arm_aggregate** —— per-arm top10/top20/top50/top100 file-recovery 与 lost_baseline_top10（来自 arm_assignment + outcome_metric）。
- **risk_bucket_aggregate** —— risk_bucket task_count 与 full/guard/diffaware loss counts（来自 safety_probe_signal + outcome_metric）。
- **citation_aggregate** —— citation_valid_count / citation_total_count（来自 evidence_core + outcome_metric）。

## Arm specs（5 个 same-budget arms，design-only）

指定 5 个 same-budget arms。HAAE-R0 不执行或 scoring 任何 arm；HAAE-R0 不 tuning。全部 aggregate-bucket-only。

- **BM25_same_budget** —— same-budget BM25 baseline arm（B16-F/N10ES comparator）。
- **RRF_same_budget** —— same-budget reciprocal-rank-fusion comparator arm。
- **BEA_v0.3_frozen** —— frozen BEA v0.3 policy arm（frozen；不 tuning）。
- **V1_sched_span** —— BEA-v1 scheduler over span projection arm。
- **V1_sched_span_rank** —— BEA-v1 scheduler over span + rank/pack arm。

## Metric specs（6 个 aggregate metrics，design-only）

指定 6 个 aggregate metrics，全部 aggregate-bucket-only、无 per-task、HAAE-R0 不 recompute：

- citation_validity、file_recovery_top_k、lost_baseline_top10、risk_bucket_signal、span_overlap、action_cost。

## Held-out protocol（design-only）

Held-out protocol 在任何未来 HAAE execution 的 training/held-out split 与已关闭的 N10ES/N10ER public held-out sample 之间强制 `overlap_zero`。Gold 永不用于 policy selection；发布仅 aggregate-bucket-only。HAAE-R0 不 materialize 任何 split；不 claim held-out generalization。

## Stop rules（4 个 abstain rules，design-only）

4 个 stop rules 保留 `EvidenceCore`：

1. **abstain_when_current_source_unavailable** —— 当 current source 无法产生 candidate evidence 时 abstain。
2. **stop_when_citation_invalid** —— 当 citation-validation 低于阈值时 stop。
3. **stop_when_budget_exhausted** —— 当 action-cost budget 耗尽时 stop。
4. **stop_when_evidence_core_violated** —— 当 action 会违反 EvidenceCore 时 stop。

## Synthetic validator（embedded synthetic fixture，design-only）

一个 embedded synthetic fixture（4 个 synthetic tasks，仅 aggregate buckets）验证 schema/arm/metric/heldout/stop-rule/HAAE-R1 contracts 是 machine-readable 且自洽的。该 fixture **不是** real data、**不是** replay、**不是** retrieval、**不是** candidate generation；它仅用于证明 control-plane 非空且内部一致。validator 在进程内运行；`validates_schema_bool`、`validates_arms_bool`、`validates_metrics_bool`、`validates_heldout_bool`、`validates_stop_rules_bool`、`validates_haae_r1_contract_bool` 全部为 `true`。

## HAAE-R1 contract（design-only，只授权 feasibility inventory）

HAAE-R0 设计并 **只** 授权下一阶段：**BEA-v1-HAAE-R1 —— Unified Private Trace Schema Feasibility Inventory**。HAAE-R1 明确限于：

- 对 unified private trace schema 进行 feasibility inventory（10 schema groups 是否能从 explicit private roots 填充）；
- **explicit project-private root buckets only**；
- **aggregate buckets only**；
- **no replay、no scoring、no retrieval、no candidate generation**；
- **no execution of any HAAE layer**；
- 它是 feasibility check，**不是** execution。

`feasibility_inventory_only_bool=true`、`no_execution_of_haae_layers_bool=true`、`execution_authorized_bool=false`。

## Risk controls

| Risk | Mitigation |
|---|---|
| HAAE-R0 drift into selector / P5 / runtime | 每条 control-plane record 带有 non-identity booleans；selector_reranker_authorized_bool=false；bea_v1_a_authorized_bool=false；p5_authorized_bool=false；runtime_default_change_authorized_bool=false |
| HAAE-R0 drift into execution | 每条 record 带有 design_only_bool=true、schema_preflight_bool=true、execution_authorized_bool=false；synthetic validator 仅在进程内对 embedded fixture 运行，并带有 no_replay/no_retrieval/no_candidate_generation/no_scoring=true |
| HAAE-R0 empty control-plane | artifact 带有 concrete machine-readable records：4 个 route architecture layers、10 个 schema groups、4 个 aggregation contracts、5 个 arm specs、6 个 metric specs、1 个 heldout protocol、4 个 stop rules，以及一个带有 4-task embedded fixture 的 synthetic validator，在进程内验证所有 contracts |
| HAAE-R1 scope creep beyond feasibility inventory | HAAE-R1 contract record 明确将 HAAE-R1 限于 feasibility_inventory_only_bool=true、private_roots_only_bool=true、aggregate_buckets_only_bool=true、no_replay/no_scoring/no_retrieval/no_candidate_generation=true、no_execution_of_haae_layers_bool=true |
| private diagnostic leakage | HAAE-R0 只读取 public aggregate artifacts/docs/git metadata；forbidden_scan 阻断 raw per-task/paths/orders/labels keys 与 private rerun paths；每个 schema group 带有 aggregate_buckets_only_bool=true、private_root_only_bool=true、no_raw_release_bool=true |
| runtime/default creep | runtime_default_change_authorized_bool=false；任何 HAAE route 保持 opt-in/eval-only；无 runtime 或 default change |

## Pass/fail gates（27 个 audit gates，aggregate-only）

1. `n10et_public_source_locked` —— N10ET public report 已锁定，status 与所有 locked fields 匹配。
2. `n10et_status_locked` —— N10ET status 匹配 locked value。
3. `n10et_haae_r0_authorized_match` —— N10ET 授权 HAAE-R0 design/schema preflight。
4. `n10et_haae_r0_execution_false_match` —— N10ET 未授权 HAAE-R0 execution。
5. `n10et_bea_v1_a_false_match` —— N10ET 未授权 BEA-v1-A。
6. `n10et_non_identity_match` —— N10ET 带有 HAAE-R0 non-identity booleans。
7. `haae_r0_no_threshold_tuning` —— frozen thresholds 未改。
8. `haae_r0_no_method_winner_claim` —— 不 claim method-winner。
9. `haae_r0_no_runtime_default_change` —— 收尾保持 public/eval-only。
10. `haae_r0_no_promotion_or_frozen_rule_change` —— 不 promotion，不改 rule。
11. `haae_r0_no_ci_rerun_retrieval_recompute_candidate_generation` —— 无 CI rerun、retrieval、recompute 或 candidate generation。
12. `haae_r0_no_private_input_read` —— 不读取 private dirs/logs/clones/raw candidates/orders/labels/paths/queries/tasks/repos 或 per-task diagnostics。
13. `haae_r0_no_selector_reranker_no_p5_no_bea_v1_a` —— 无 selector/reranker、无 P5、无 BEA-v1-A。
14. `haae_r0_no_arm_scoring` —— 无 arm scoring。
15. `haae_r0_no_openlocus_execution` —— 无 OpenLocus execution。
16. `haae_r0_route_architecture_design_only` —— 4 个 route architecture layers 全部 design-only，不执行。
17. `haae_r0_schema_groups_concrete` —— 10 个 unified private schema groups 存在。
18. `haae_r0_arm_specs_concrete` —— 5 个 arm specs 存在。
19. `haae_r0_metric_specs_concrete` —— 6 个 metric specs 存在。
20. `haae_r0_synthetic_validator_passes` —— embedded synthetic validator 通过。
21. `haae_r0_non_identity_gate` —— HAAE-R0 non-identity booleans 全部为 true。
22. `docs_readback_match_gate` —— EN/ZH HAAE-R0 + N10ET docs 匹配。
23. `readme_readback_match_gate` —— README 匹配。
24. `current_conclusions_match_gate` —— EN/ZH current conclusions 匹配。
25. `research_log_match_gate` —— EN/ZH research logs 匹配。
26. `research_summary_match_gate` —— EN/ZH research summaries 匹配。
27. `haae_r1_contract_feasibility_inventory_only_gate` —— HAAE-R1 contract 限于 feasibility inventory only。

所有 gates 都是 aggregate-only，`gate_uses_gold_for_policy_bool=false`、`gate_performs_ci_rerun_bool=false`、`gate_reads_private_input_bool=false`。

## Claim boundary

HAAE-R0 是 public-only、aggregate-buckets-only、design-only、schema-preflight-only。所有 execution、rerun、retrieval、recompute、candidate generation、arm scoring、OpenLocus execution、tuning、promotion、runtime/default、method-winner、downstream/scaled retrieval、raw diagnostic publication、selector/reranker、provider/model network、network-run、gold-for-policy 字段均为 `false`。`candidate_generation_bool=false`、`arm_scoring_bool=false`、`openlocus_execution_bool=false`、`haae_r0_execution_authorized_bool=false`、`haae_r1_execution_authorized_bool=false`、`haae_r1_replay_authorized_bool=false`、`haae_r1_scoring_authorized_bool=false`、`haae_r1_retrieval_authorized_bool=false`、`haae_r1_candidate_generation_authorized_bool=false`。HAAE-R0 non-identity booleans（`haae_r0_not_bea_v1_a_bool`、`haae_r0_not_selector_only_bool`、`haae_r0_not_selector_reranker_execution_bool`、`haae_r0_not_p5_bool`、`haae_r0_not_runtime_default_promotion_bool`）全部为 `true`。

## Stop/go

HAAE-R0 只授权 **BEA-v1-HAAE-R1 Unified Private Trace Schema Feasibility Inventory** 交接（public-only、design-only、explicit private roots only、aggregate buckets only、no replay/scoring/retrieval/candidate generation）：
`haae_r1_unified_private_trace_schema_feasibility_inventory_authorized_bool=true`、
`haae_r1_execution_authorized_bool=false`、
`haae_r1_replay_authorized_bool=false`、
`haae_r1_scoring_authorized_bool=false`、
`haae_r1_retrieval_authorized_bool=false`、
`haae_r1_candidate_generation_authorized_bool=false`。它 **不** 授权：N10ET re-run、任何 HAAE-R0 execution、任何 execution、rerun、retrieval、recompute、candidate generation、arm scoring、OpenLocus execution、threshold tuning、新 policy experiments、frozen-rule changes、guard/full/diffaware promotion、runtime/default changes、method-winner claims、downstream/scaled retrieval、raw diagnostic publication、CI variant execution、selector/reranker、BEA-v1-A、P5、provider/model network 或 network runs。所有这类 stop/go 字段均为 `false`。

## Workflow

- Design/schema-preflight helper：`eval/bea_v1_haae_r0_hierarchical_actionable_evidence_acquisition_design_schema_preflight.py`
- 该 helper 暴露 `--self-test`、`--validate-report`、`--out`。它只读取 N10ET public report 与 public docs，不进行任何 execution/rerun/recompute/candidate generation/arm scoring/OpenLocus execution。

## Artifact

- Helper：`eval/bea_v1_haae_r0_hierarchical_actionable_evidence_acquisition_design_schema_preflight.py`
- Report：`artifacts/bea_v1_haae_r0_hierarchical_actionable_evidence_acquisition_design_schema_preflight/bea_v1_haae_r0_hierarchical_actionable_evidence_acquisition_design_schema_preflight_report.json`
