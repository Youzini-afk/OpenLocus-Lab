# OpenLocus v2 FRK Product Workflow Bounded Retrieval Repair Prototype

Status: `frk_product_workflow_bounded_retrieval_repair_prototype_complete_no_lift_stop_or_failure_decomposition`

Public report: [`artifacts/frk_product_workflow_bounded_retrieval_repair_prototype/frk_product_workflow_bounded_retrieval_repair_prototype_report.json`](../../artifacts/frk_product_workflow_bounded_retrieval_repair_prototype/frk_product_workflow_bounded_retrieval_repair_prototype_report.json)

Evaluator: `eval/frk_product_workflow_bounded_retrieval_repair_prototype.py`

## Scope

This phase is an executable bounded prototype of the previously authorized same-budget retrieval repair. It adds exactly one prototype arm: `frk_bounded_repair_wrong_file_guard_fixed_budget`.

The evaluator reads the Phase-5 benchmark report, Phase-6 decomposition report, Phase-7 design report, and existing private product-workflow traces only after `--confirm-private-input`. It writes private Phase-1 schema-valid prototype rows under ignored `runs/frk_product_workflow_bounded_repair_private_*/` only after `--confirm-private-output`.

## Execution contract

- local OpenLocus actions only
- same task set as Phase 5
- same candidate/read/validate cap buckets: `count_2_to_5`
- channel families restricted to existing `bm25_text`, `symbol_regex`, and `existing_hybrid_retrieve`
- no new channels, providers, network, CI, source scan, candidate generation, candidate expansion, training, runtime/default changes, or kernel hardening
- wrong-file/intent guard runs before the second read; if undecidable, fixed deterministic ordering is used
- labels/gold are used only after action selection for private scoring

## Result

The prototype completed with schema/privacy/currentness gates passing, but it did not lift over the previous hybrid or the best fixed baseline:

- prototype utility bucket: `rate_25_to_50`
- previous hybrid bucket: `rate_25_to_50`
- best fixed baseline bucket: `rate_50_to_75`
- delta vs previous hybrid: `negative_delta`
- delta vs best fixed baseline: `negative_delta`

Mechanism-impact buckets remain aggregate-only and cover wrong-file/rank-miss, read-budget/top-k pressure, no-hit, stale/currentness failure, and validation failure.

## Stop/go

Closeout decision: stop the current bounded repair candidate. Authorized next route: `none_for_current_repair_candidate`, except a separately justified future `new_product_workflow_pain_or_new_trace_evidence_decision`.

Not authorized: D2/model scaling, RPM training, runtime/default changes, provider/network/CI, method/scale/winner/default claims, broad source scan, candidate expansion, new channel families, kernel hardening, raw/private trace publication, FRK-J, FRK-B/C resurrection, FRK-I revival, LDI-B easy continuation, HAAE-SG, or HAAE-T.
