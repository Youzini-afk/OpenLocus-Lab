# Interventional Evidence Acquisition Phase 9E Public Source Fetch/Clone Materialization Protocol Freeze

日期：2026-07-09

Status：`phase9e_public_source_fetch_clone_materialization_protocol_freeze_no_execution_no_scoring_no_claim`

Authorization：docs/report/validator-only protocol freeze

Public report：[`phase9e_public_source_fetch_clone_materialization_protocol_freeze_no_execution_no_scoring_no_claim_report.json`](../../artifacts/phase9e_public_source_fetch_clone_materialization_protocol_freeze_no_execution_no_scoring_no_claim/phase9e_public_source_fetch_clone_materialization_protocol_freeze_no_execution_no_scoring_no_claim_report.json)

## Scope

Phase 9E 是 docs/report/validator-only protocol freeze。它在 Phase 9D zero-materialization repair checkpoint 之后冻结 future public source fetch/clone/materialization rules。它不 fetch、clone、read 或 materialize 任何 repository 或 source。它不读取 ignored `runs/` 或 private registries/manifests。它不生成 task rows、labels、outcomes、scoring rows 或 evidence_success。它不提出 method/product/performance/model/provider/training/runtime/default/scoring/outcome/evidence-success claim。

Phase 9E gate 于 Phase 9D status `repair_task_materialization_no_claim`、zero rows 以及 public fetch/clone false。Future execution 在 Phase 9E protocol 下需要 Phase 9E commit 与 CI green。

## Frozen protocol summary

Frozen future protocol 要求：

- Public-only fetch/clone，仅在显式 confirmation 下进行。
- Fetch/clone 只进入 ignored workspace（`runs/` only），不进入 tracked artifacts。
- License、access、default-branch、currentness 与 hash checks 在任何 task row acceptance 之前。
- Exact paths、ranges、hashes 与 snippets 只保持 private。
- Deterministic source order，不使用 random shuffle。
- Task-candidate target bucket 48-72，hard cap 最多 96，per-source cap 最多 8，minimum distinct sources 至少 8。
- Stop 或 repair 如果 zero materialization 在 caps 之后发生。
- Stop 或 repair 如果 source 或 task diversity 在 caps 之后低于 minimum。
- Stop 或 repair 如果发生 privacy leak 或 singleton public bucket need。
- Replacement 只能在 labels/outcomes/scoring 之前，且不使用 performance/evidence-success feedback。
- Task types 仅限于 evidence-finding file-localizable code tasks。
- Provider/LLM tasks forbidden。
- 不公开 unit per-source 或 per-task reporting。
- Future strategy scoring 需要另一个 frozen boundary。

## No-claim boundary

Phase 9E 不提出 method、product、performance、training、provider、model、runtime、default、scoring、outcome 或 evidence-success claim。Frozen protocol 仅 aggregate-bucketed。Public output 不包含 repo names、source names、URLs、owners、commits、hashes、paths、snippets、task IDs、row IDs、manifest locations、run locations、per-source facts、per-task facts 或 singleton buckets。
