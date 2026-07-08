# Interventional Evidence Acquisition Phase 9C Task Construction/Materialization Protocol Freeze

Date: 2026-07-09

Status: `phase9c_task_construction_materialization_protocol_freeze_no_execution_no_scoring_no_claim`

Authorization: `task_construction_materialization_protocol_freeze_no_execution_no_scoring_no_claim`

Public report: [`phase9c_task_construction_materialization_protocol_freeze_no_execution_no_scoring_no_claim_report.json`](../../artifacts/phase9c_task_construction_materialization_protocol_freeze_no_execution_no_scoring_no_claim/phase9c_task_construction_materialization_protocol_freeze_no_execution_no_scoring_no_claim_report.json)

## Scope

Phase 9C is docs/report/validator only. It freezes a future task construction and source materialization protocol after the Phase 9B clean-room source construction audit, which is referenced at commit `cfb25cd`, CI run `28967621378`, and status `phase9b_clean_room_source_construction_audit_no_scoring_no_claim`.

Phase 9C does not generate tasks, materialize sources, read source archives, read the Phase 9B ignored private accepted source registry, generate labels, generate outcomes, score, evaluate evidence success, fit models, call providers/LLMs, or change runtime/default/product behavior.

## Frozen future protocol

Future Phase 9D may use the ignored private accepted source registry produced by Phase 9B, but Phase 9C itself does not read it. Source ordering is frozen as deterministic Phase 9B private registry order with no random shuffle. Later task-candidate construction is limited to aggregate bucketed caps: conservative target bucket 48-72, hard cap bucket up to 96, per-source task cap bucket up to 8, and minimum distinct sources bucket at least 8. No singleton public per-source or per-task reporting is allowed.

Later task candidates must be based only on current source materialization in that later execution boundary, not in Phase 9C. A candidate must have source path/range/hash/currentness available privately before acceptance in the later execution. Task types are limited to evidence-finding, file-localizable code tasks; provider/LLM tasks are forbidden. No tasks may derive from Phase 8B, Phase 7, or Phase 5 private materials.

## Materialization, eligibility, and replacement

Future source archives must materialize privately under ignored `runs/` only. A currentness/hash reread check, license/access checks, and default-branch checks must pass before any later task row is accepted. Exact paths, ranges, hashes, and snippets remain private.

Generated candidates must be rejected if they require private access, exact public identity disclosure, unavailable source material, ambiguous path/range, missing license/currentness/hash checks, or leaking per-task details. Replacement must use the next deterministic candidate from the same source, or the next source in frozen order if that source is exhausted. Replacement occurs only before labels/outcomes/scoring and cannot use performance or evidence-success feedback.

## Later Phase 9D boundary

Phase 9C contains no scoring, labels, outcomes, or evidence-success evaluation. A later Phase 9D, if separately authorized after Phase 9C is committed and CI green, may only construct and materialize task candidates. Strategy scoring requires another frozen boundary. Later execution must stop if source/task diversity falls below the minimum after caps, or if a private leak or singleton public bucket need appears.

## Public/private boundary

The public report is aggregate-only. Private future manifests may exist only under ignored `runs/` in a later phase. No repository/source names, URLs, owners, commits, hashes, paths, snippets, task IDs, row IDs, manifests, run directories, per-source facts, or per-task facts are public.

## No-claim boundary

This checkpoint makes no method, product, performance, training, provider, model, scoring, outcome, evidence-success, runtime, default, deployment, or product claim.
