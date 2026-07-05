# OpenLocus v2 FRK Product Workflow Trace Benchmark

Status: `frk_product_workflow_trace_benchmark_complete_no_lift_failure_decomposition_or_trace_expansion`

Public report: [`artifacts/frk_product_workflow_trace_benchmark/frk_product_workflow_trace_benchmark_report.json`](../../artifacts/frk_product_workflow_trace_benchmark/frk_product_workflow_trace_benchmark_report.json)

Evaluator: `eval/frk_product_workflow_trace_benchmark.py`

## Scope

This phase implements the next executable OpenLocus v2 trace-driven evidence-acquisition benchmark. It is a fixed, bounded, local product-workflow benchmark, not a preflight, audit, kernel-hardening continuation, training run, provider run, CI claim, runtime/default change, method claim, scale claim, or winner claim.

The benchmark executes local OpenLocus CLI actions where available and compares same-budget local arms:

- `text_bm25_baseline`
- `symbol_regex_baseline`
- `openlocus_hybrid_retrieve`

The public artifact is aggregate-only. Private task identifiers, expected labels, paths, ranges, hashes, snippets, queries, per-task outcomes, private references, evidence filenames, and private trace paths remain under ignored private storage and are not published.

## Execution and coverage

The executed public aggregate report records:

- task coverage bucket: `count_6_to_20`
- workflow family coverage: CLI/API lookup, EvidenceCore/currentness/citation validation, trace/report/schema debugging, docs/readback consistency, and index/search behavior
- arm coverage: three same-budget arms
- episode coverage bucket: `count_gt_50`
- row coverage bucket: `count_gt_50`
- action coverage: `bounded_retrieval`, `read_current_source`, `validate_evidence`, and `workflow_step`
- Phase-1 RPM trace schema pass, labels-after-action isolation, pre-action currentness non-leakage, privacy pass, and aggregate-only publication

The primary success proxy is `validated_current_evidence_matches_private_expected_workflow_need`, published only as aggregate buckets.

## Result

The benchmark achieved adequate diversity and real local execution, but the OpenLocus hybrid retrieve arm did **not** beat the best fixed baseline in this run:

- best fixed baseline bucket: `rate_50_to_75`
- candidate arm bucket: `rate_25_to_50`
- candidate-vs-best-baseline delta bucket: `negative_vs_best_baseline`

Therefore this is a no-lift product-workflow result. It is not a method, default, scale, winner, runtime, provider, network, CI, or training claim.

## Stop/go

Authorized next phase: `frk_product_workflow_failure_decomposition_or_trace_expansion`.

Not authorized: D2/training, runtime/default changes, provider/network/CI claims, method/scale/winner/default claims, raw publication, private trace publication, broad source scan, candidate expansion, kernel hardening continuation, old heuristic chains, FRK-J, FRK-B/C resurrection, FRK-I variants, LDI-B easy continuation, HAAE-SG, or HAAE-T.
