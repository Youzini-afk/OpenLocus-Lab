# Interventional Evidence Acquisition Phase 9C Task Construction/Materialization Protocol Freeze

日期：2026-07-09

Status: `phase9c_task_construction_materialization_protocol_freeze_no_execution_no_scoring_no_claim`

Authorization: `task_construction_materialization_protocol_freeze_no_execution_no_scoring_no_claim`

Public report: [`phase9c_task_construction_materialization_protocol_freeze_no_execution_no_scoring_no_claim_report.json`](../../artifacts/phase9c_task_construction_materialization_protocol_freeze_no_execution_no_scoring_no_claim/phase9c_task_construction_materialization_protocol_freeze_no_execution_no_scoring_no_claim_report.json)

## 范围

Phase 9C 仅为 docs/report/validator。它在 Phase 9B clean-room source construction audit 之后冻结 future task construction 与 source materialization protocol；Phase 9B reference 为 commit `cfb25cd`、CI run `28967621378`、status `phase9b_clean_room_source_construction_audit_no_scoring_no_claim`。

Phase 9C 不生成 tasks，不 materialize sources，不读取 source archives，不读取 Phase 9B ignored private accepted source registry，不生成 labels，不生成 outcomes，不执行 scoring，不评估 evidence success，不 fit models，不调用 providers/LLMs，也不改变 runtime/default/product behavior。

## Frozen future protocol

Future Phase 9D 可以使用 Phase 9B 产生的 ignored private accepted source registry，但 Phase 9C 本身不读取它。Source ordering 冻结为 deterministic Phase 9B private registry order，且 no random shuffle。Later task-candidate construction 只使用 aggregate bucketed caps：conservative target bucket 48-72、hard cap bucket up to 96、per-source task cap bucket up to 8、minimum distinct sources bucket at least 8。禁止 singleton public per-source 或 per-task reporting。

Later task candidates 必须只基于 later execution boundary 中的 current source materialization，而不是 Phase 9C 中的 materialization。Candidate 在 later execution 中被接受前，必须能私下取得 source path/range/hash/currentness。Task types 仅限 evidence-finding、file-localizable code tasks；禁止 provider/LLM tasks。不得从 Phase 8B、Phase 7 或 Phase 5 private materials 派生 tasks。

## Materialization, eligibility, and replacement

Future source archives 只能在 later phase 中私下 materialize 到 ignored `runs/` 下。任何 later task row 被接受前，必须通过 currentness/hash reread check、license/access checks 和 default-branch checks。Exact paths、ranges、hashes 与 snippets 均保持 private。

若 generated candidates 需要 private access、需要公开 exact public identity、source unavailable、path/range ambiguous、缺少 license/currentness/hash checks，或会泄露 per-task details，则必须 reject。Replacement 使用同一 source 的 next deterministic candidate；若该 source exhausted，则转到 frozen order 中的 next source。Replacement 只能发生在 labels/outcomes/scoring 之前，且不能使用 performance 或 evidence-success feedback。

## Later Phase 9D boundary

Phase 9C 不包含 scoring、labels、outcomes 或 evidence-success evaluation。若 future Phase 9D 在 Phase 9C commit 且 CI green 后被单独授权，它只能 construct 与 materialize task candidates。Strategy scoring 需要另一个 frozen boundary。Later execution 若在 caps 后低于 minimum source/task diversity，或出现 private leak / singleton public bucket need，必须 stop。

## Public/private boundary

Public report 仅 aggregate-only。Future private manifests 只能在 later phase 中位于 ignored `runs/` 下。不得公开 repository/source names、URLs、owners、commits、hashes、paths、snippets、task IDs、row IDs、manifests、run directories、per-source facts 或 per-task facts。

## No-claim boundary

该 checkpoint 不提出 method、product、performance、training、provider、model、scoring、outcome、evidence-success、runtime、default、deployment 或 product claim。
