# Interventional Evidence Acquisition Phase 9E Public Source Fetch/Clone Materialization Protocol Freeze

Date: 2026-07-09

Status: `phase9e_public_source_fetch_clone_materialization_protocol_freeze_no_execution_no_scoring_no_claim`

Authorization: docs/report/validator-only protocol freeze

Public report: [`phase9e_public_source_fetch_clone_materialization_protocol_freeze_no_execution_no_scoring_no_claim_report.json`](../../artifacts/phase9e_public_source_fetch_clone_materialization_protocol_freeze_no_execution_no_scoring_no_claim/phase9e_public_source_fetch_clone_materialization_protocol_freeze_no_execution_no_scoring_no_claim_report.json)

## Scope

Phase 9E is a docs/report/validator-only protocol freeze. It freezes the future public source fetch/clone/materialization rules after the Phase 9D zero-materialization repair checkpoint. It does not fetch, clone, read, or materialize any repository or source. It does not read ignored `runs/` or private registries/manifests. It does not generate task rows, labels, outcomes, scoring rows, or evidence_success. It makes no method/product/performance/model/provider/training/runtime/default/scoring/outcome/evidence-success claim.

Phase 9E is gated on Phase 9D status `repair_task_materialization_no_claim`, zero rows, and public fetch/clone false. Future execution under the Phase 9E protocol requires Phase 9E commit and CI green.

## Frozen protocol summary

The frozen future protocol requires:

- Public-only fetch/clone under explicit confirmation only.
- Fetch/clone into ignored workspace (`runs/` only), never into tracked artifacts.
- License, access, default-branch, currentness, and hash checks before any task row acceptance.
- Exact paths, ranges, hashes, and snippets remain private only.
- Deterministic source order with no random shuffle.
- Task-candidate target bucket 48-72, hard cap up to 96, per-source cap up to 8, minimum distinct sources at least 8.
- Stop or repair if zero materialization occurs after caps.
- Stop or repair if source or task diversity falls below the minimum after caps.
- Stop or repair on privacy leak or singleton public bucket need.
- Replacement before labels/outcomes/scoring only, with no performance/evidence-success feedback.
- Task types limited to evidence-finding file-localizable code tasks.
- Provider/LLM tasks forbidden.
- No unit public per-source or per-task reporting.
- Future strategy scoring requires another frozen boundary.

## No-claim boundary

Phase 9E makes no method, product, performance, training, provider, model, runtime, default, scoring, outcome, or evidence-success claim. The frozen protocol is aggregate-bucketed only. Public output excludes repo names, source names, URLs, owners, commits, hashes, paths, snippets, task IDs, row IDs, manifest locations, run locations, per-source facts, per-task facts, and singleton buckets.
