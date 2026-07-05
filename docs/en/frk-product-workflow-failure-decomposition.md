# OpenLocus v2 FRK Product Workflow Failure Decomposition

Status: `frk_product_workflow_failure_decomposition_query_channel_budget_repair_design_authorized`

Public report: [`artifacts/frk_product_workflow_failure_decomposition/frk_product_workflow_failure_decomposition_report.json`](../../artifacts/frk_product_workflow_failure_decomposition/frk_product_workflow_failure_decomposition_report.json)

Evaluator: `eval/frk_product_workflow_failure_decomposition.py`

## Scope

This phase explains why `openlocus_hybrid_retrieve` lost to the best fixed baseline in the FRK product-workflow trace benchmark. It is an executable empirical decomposition over existing private trace rows only.

Allowed inputs are limited to the latest ignored private product-workflow trace rows and labels, the committed public benchmark report, the benchmark script for schema/action/arm naming readback, and the Phase-1 schema validator. The evaluator requires `--confirm-private-input` before reading private rows. It does not rerun retrieval, search, read, citation validation, source scanning, candidate generation, provider/model calls, network work, CI, training, model scaling, runtime/default changes, method/winner claims, or kernel hardening.

## Result

The public report is aggregate-only. It records the benchmark no-lift readback, private row/episode count buckets, arm-vs-best-baseline outcome matrix buckets, family-level loss concentration buckets, and mechanism count buckets without exposing private trace paths, label paths, task ids, rows, paths, ranges, queries, snippets, hashes, private refs, evidence filenames, exact labels, per-task outcomes, or per-task mechanisms.

Primary mechanism: `wrong_file_or_rank_miss`.

Secondary mechanism: `read_budget_or_topk_limit`.

Confidence bucket: `high`.

The decomposition indicates a query/channel/budget repair-design problem for the current hybrid retrieve candidate rather than evidence of a winning/default method.

## Stop/go

Authorized next phase: `frk_product_workflow_specific_retrieval_repair_design`.

Forbidden: D2/model scaling, RPM training, runtime/default changes, provider/network/CI claims, method/scale/winner/default claims, broad source scans, candidate expansion, new retrieval experiments, kernel hardening continuation, old heuristic chains, raw/private trace publication, FRK-J, FRK-B/C resurrection, FRK-I variants, LDI-B easy continuation, HAAE-SG, or HAAE-T.
