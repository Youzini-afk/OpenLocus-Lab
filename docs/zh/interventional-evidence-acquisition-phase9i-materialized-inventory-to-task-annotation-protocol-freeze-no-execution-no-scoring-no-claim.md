# Interventional Evidence Acquisition Phase 9I Materialized Inventory to Task Annotation Protocol Freeze

日期：2026-07-09

Status：`phase9i_materialized_inventory_to_task_annotation_protocol_freeze_no_execution_no_scoring_no_claim`

Authorization：docs/report/validator-only protocol freeze，用于 future conversion of Phase 9H private materialized source inventory into task annotation/outcome-acquisition inputs；no execution、no labels、no outcomes、no scoring、no evidence_success、no claims

Public report：[`phase9i_materialized_inventory_to_task_annotation_protocol_freeze_no_execution_no_scoring_no_claim_report.json`](../../artifacts/phase9i_materialized_inventory_to_task_annotation_protocol_freeze_no_execution_no_scoring_no_claim/phase9i_materialized_inventory_to_task_annotation_protocol_freeze_no_execution_no_scoring_no_claim_report.json)

## Scope

Phase 9I 是 docs/report/validator-only protocol freeze。它冻结 future protocol，用于将 Phase 9H private materialized source inventory 转换为 future task annotation / outcome-acquisition inputs。它不 fetch、clone、read 或 materialize 任何 repository 或 source。它不读取 ignored `runs/`、private candidate pools/registries/manifests 或 Phase 9H private materialized inventory。它不生成 task annotations（labels）、outcomes、gold rows、evidence_success 或 scoring/evaluation rows。它不提出 method/product/performance/model/provider/training/runtime/default/scoring/outcome/evidence-success claim。

Phase 9I gate 于 Phase 9H remote commit `d997caab5487e66c544f657645d70c97f3b780e2`、CI run `28976655118`、CI success 以及 Phase 9H status `phase9h_candidate_source_pool_public_source_network_fetch_materialization_readiness_no_scoring_no_claim`。Phase 9G（status `phase9g_candidate_source_pool_network_fetch_protocol_freeze_no_execution_no_scoring_no_claim`、CI success、protocol freeze）与 Phase 9F status `phase9f_public_source_fetch_clone_materialization_repair_no_claim` 作为 bucketed inherited provenance carry forward；Phase 9I report/docs 中刻意不公开 Phase 9G remote commit/CI run 的精确值，因此只有 Phase 9H full commit SHA 与 CI run 作为 public gate references。Local same-tree git commits 不被读取或比较；supplied confirmation 值只与 frozen public gate constants 比对。Future execution 在 Phase 9I protocol 下需要 Phase 9I commit 与 CI green。

Phase 9I 记录 Phase 9H 是 source-materialization readiness only 且 NOT proof 任何 annotation、outcome、evidence_success、scoring 或 evaluation works。Phase 9H 不生成 task annotations、outcomes、gold rows、evidence_success 或 scoring rows；它只在 ignored `runs/` 之下生成 private materialized inventory rows。Phase 9I 不读取该 private inventory。

## Frozen future annotation types

Frozen future protocol 只允许这些 annotation types（尽可能使用中性词 "annotation" 而非 "labels"）：

- Task eligibility annotation
- Evidence-localization requirement
- Expected evidence form
- Outcome-acquisition preconditions
- Adjudication rules
- Rejection/replacement rules before scoring

## Frozen future annotation protocol

Frozen future protocol 要求：

- 只将 private Phase 9H materialized inventory 转换为 future task annotation inputs。
- Task eligibility annotation 仅在显式 future confirmation 下进行。
- Evidence-localization requirement 仅限 file-localizable code tasks。
- Expected evidence form 必须匹配 Phase 9H inventory shape。
- Outcome-acquisition preconditions 必须在任何 outcome acquisition 之前设定。
- Adjudication rules 必须在任何 annotation execution 之前冻结。
- Rejection/replacement rules 只能在 scoring 之前。
- Phase 9I 不执行 annotation execution。
- Phase 9I 不生成 outcomes、gold rows、evidence_success 或 scoring/evaluation rows。
- Phase 9I 不进行 provider/LLM/model/default/runtime change。
- Private Phase 9H inventory 只在 Phase 9I commit 与 CI green 且显式 confirmation 之后读取。
- Future annotation execution 需要单独的 Phase 9J boundary。
- Aggregate public report only：不公开 private inventory 或 annotation details。
- No singleton public buckets。

## Inherited aggregate caps/buckets from Phase 9H

Frozen protocol 完全继承 Phase 9H aggregate caps/buckets：

- Target inventory bucket：48-72
- Hard cap bucket：最多 96
- Per-source cap bucket：最多 8
- Minimum distinct sources bucket：至少 8

## Future private input/output locations

Future private inputs/outputs（Phase 9H private materialized inventory、future annotation rows、future outcome-acquisition rows）只保留在 ignored `runs/` 之下。Phase 9I 不读取它们。Future Phase 9J 只在 Phase 9I commit 与 CI green 且显式 confirmations 之后才可读取 Phase 9H private inventory。

## Future Phase 9J gate conditions

Future Phase 9J execution 需要以下所有 confirmations：

- Confirm Phase 9H commit 与 CI green
- Confirm Phase 9I protocol freeze
- Confirm read Phase 9H private materialized inventory
- Confirm ignored runs workspace
- Confirm private-output-only
- Confirm no scoring/evidence_success
- Confirm no provider/LLM/model/default/runtime change
- Confirm aggregate public report only

Phase 9J 只在 Phase 9I commit 与 CI green 之后才可读取 Phase 9H private inventory。Phase 9J 在另一个 frozen boundary 之前保持 no-scoring 与 no-evidence_success。

## No-claim boundary

Phase 9I 不提出 method、product、performance、training、provider、model、runtime、default、scoring、outcome 或 evidence-success claim。Frozen protocol 仅 aggregate-bucketed。Public output 不包含 repo names、source names、URLs、owners、commits、hashes、paths、snippets、task IDs、row IDs、manifest locations、run locations、per-source facts、per-task facts 或 singleton buckets。Phase 9I 不暗示 annotation、outcome acquisition、evidence_success、scoring 或任何 evidence-acquisition method works；Phase 9H source-materialization readiness 不是 annotation、outcome、evidence_success 或 scoring 成功的 proof。Phase 9I 不是 execution，也不是 evidence/method/product success。

Conservative recommendation 为：`future_annotation_execution_requires_separate_phase9j_boundary_and_explicit_private_phase9h_inventory_read_confirmation`。
