# Interventional Evidence Acquisition Phase 9J Annotation-Input Execution

日期：2026-07-09

Status：`phase9j_annotation_input_rows_generated_no_scoring_no_claim`

授权：在全部十五个显式 confirmations 和 frozen Phase 9I annotation protocol 之下，只读取 Phase 9H private materialized inventory（在 ignored `runs/` 之下），只在 ignored `runs/` 之下生成 private annotation-input rows/manifests，并只发布 aggregate public report。不进行 outcome acquisition、scoring rows、gold labels、benchmark labels、evidence_success、provider/LLM/network/fetch/clone/source refresh、model fitting/training、runtime/default/product changes，也不提出 method/product/performance/provider/model claim。

Public report：[`phase9j_annotation_input_execution_no_scoring_no_claim_report.json`](../../artifacts/phase9j_annotation_input_execution_no_scoring_no_claim/phase9j_annotation_input_execution_no_scoring_no_claim_report.json)

## Scope

Phase 9J 是 bounded annotation-input execution。在全部十五个显式 confirmations 之下，它只读取 Phase 9H private materialized inventory（在 ignored `runs/` 之下），只在 ignored `runs/` 之下生成 private annotation-input rows/manifests，并只发布 aggregate/bucketed public report。它不进行 outcome acquisition、scoring rows、gold labels、benchmark labels、evidence_success、provider/LLM/network/fetch/clone/source refresh、model fitting/training 或 runtime/default/product changes。它不提出 method、product、performance、training、provider、model、runtime、default、scoring、outcome、evidence-success 或 annotation-truth claim。

Phase 9J gate 于 Phase 9H remote commit `d997caab5487e66c544f657645d70c97f3b780e2`、CI run `28976655118`、CI success、Phase 9H status `phase9h_candidate_source_pool_public_source_network_fetch_materialization_readiness_no_scoring_no_claim`、Phase 9I remote commit `fe9eabba744ff00526fadd7184801c3721677fba`、CI run `28979060368`、CI success、Phase 9I status `phase9i_materialized_inventory_to_task_annotation_protocol_freeze_no_execution_no_scoring_no_claim` 以及 Phase 9I protocol freeze。Phase 9G（status `phase9g_candidate_source_pool_network_fetch_protocol_freeze_no_execution_no_scoring_no_claim`、CI success、protocol freeze）与 Phase 9F status `phase9f_public_source_fetch_clone_materialization_repair_no_claim` 作为 bucketed inherited provenance carry forward；Phase 9J report/docs 中刻意不公开 Phase 9G/9F remote commit/CI run 的精确值，因此只有 Phase 9H 和 Phase 9I 的 full commit SHA 与 CI run 作为 public gate references。Local same-tree git commits 不被读取或比较；supplied confirmation 值只与 frozen public gate constants 比对。

## Annotation-input rows

Annotation-input rows 是 routing/precondition metadata only，不是 benchmark truth。每个 private annotation-input row 只包含 frozen Phase 9I protocol 字段：

- Task eligibility input（routing/precondition metadata only，不是 benchmark truth）
- Evidence-localization requirement
- Expected evidence form
- Outcome-acquisition preconditions
- Adjudication rules
- Rejection/replacement-before-scoring rules

Annotation-input rows 不得包含 outcomes、gold labels、scoring rows、evidence_success、result labels、benchmark labels 或任何 truth/expected-answer 字段。Eligibility annotations 是 routing/precondition metadata only，不是 benchmark truth。

## Private input/output locations

Phase 9H private materialized inventory 与 Phase 9J private annotation-input rows/manifests 只在 ignored `runs/` 之下。Phase 9J 只在显式 confirmation 且 Phase 9H/9I gates green 之后才读取 Phase 9H private inventory。Private annotation-input rows 与 manifests 只写入 ignored `runs/` 之下（精确 private run directory 不在 tracked docs/report 中公开；`run_locations_public=false`）。

## No-claim boundary

Phase 9J 不提出 method、product、performance、training、provider、model、runtime、default、scoring、outcome、evidence-success 或 annotation-truth claim。Public report 是 aggregate/bucketed only。Public output 排除 repo names、source names、URLs、owners、commits（除了 whitelisted Phase 9H/9I gate constants）、hashes、paths、snippets、task IDs、row IDs、manifest locations、run locations、per-source facts、per-task facts、annotation-input rows 与 singleton buckets。Phase 9J 不暗示 annotation、outcome acquisition、evidence_success、scoring 或任何 evidence-acquisition method works；annotation-input rows 是 routing/precondition metadata only，不是 benchmark truth。Phase 9J 不是 evidence/method/product success 或 product readiness。

Conservative recommendation：`annotation_input_rows_are_routing_precondition_only_not_benchmark_truth_future_outcome_acquisition_and_scoring_require_separate_frozen_boundary_no_evidence_success_no_method_product_claim`。
