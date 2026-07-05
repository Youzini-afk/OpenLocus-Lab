# OpenLocus v2 FRK Product Workflow Specific Retrieval Repair Design

Status: `frk_product_workflow_specific_retrieval_repair_design_complete_bounded_prototype_authorized`

Public report: [`artifacts/frk_product_workflow_specific_retrieval_repair_design/frk_product_workflow_specific_retrieval_repair_design_report.json`](../../artifacts/frk_product_workflow_specific_retrieval_repair_design/frk_product_workflow_specific_retrieval_repair_design_report.json)

Evaluator: `eval/frk_product_workflow_specific_retrieval_repair_design.py`

## Scope

This phase is a design-with-static-replay-simulation for a narrow same-budget repair to the product-workflow hybrid retrieve arm. It uses the existing trace evidence and public reports to sanity-check a bounded repair design; it is not a prose-only design, not a prototype execution, and not a new retrieval experiment.

Allowed inputs are the public product-workflow benchmark and failure-decomposition reports, evaluator scripts for schema/action/arm naming readback, the Phase-1 schema validator, and the latest ignored private product-workflow traces only after `--confirm-private-input`. The evaluator does not rerun retrieval, search, read, citation validation, source scanning, candidate generation, training/scaling, provider/model calls, network/CI, runtime/default changes, or kernel hardening.

## Design

The selected design family is `wrong_file_guard_fixed_budget_read_allocation`:

- preserve the same candidate cap bucket: `count_2_to_5`
- preserve the same read cap bucket: `count_2_to_5`
- use only the existing benchmark channel families: `bm25_text`, `symbol_regex`, `existing_hybrid_retrieve`
- preserve EvidenceCore currentness and label-after-action discipline
- add a wrong-file/intent consistency guard before the second read
- treat top-k pressure as a fixed-budget read allocation problem, not as authorization for candidate expansion

## Static replay result

Static replay over existing private traces found nonzero affected-loss coverage and no dominant unresolved/proxy-risk blocker:

- replayable trace coverage bucket: `count_6_to_20`
- mechanism coverage bucket: `count_6_to_20`
- estimated affected-loss bucket: `count_6_to_20`
- unresolved/inconclusive bucket: `count_0`
- proxy-risk bucket: `low`
- confidence bucket: `high`

All concrete-design gates passed, including exact readback of the source mechanisms `wrong_file_or_rank_miss` and `read_budget_or_topk_limit`, same budget, no new channel family, schema-valid private replay, and aggregate-only privacy.

## Stop/go

Authorized next phase: `frk_product_workflow_bounded_retrieval_repair_prototype`.

Forbidden: D2/model scaling, RPM training, runtime/default changes, provider/network/CI claims, method/scale/winner/default claims, broad source scans, candidate expansion, new retrieval experiments in this design phase, kernel hardening continuation, old heuristic chains, raw/private trace publication, FRK-J, FRK-B/C resurrection, FRK-I variants, LDI-B easy continuation, HAAE-SG, or HAAE-T.
