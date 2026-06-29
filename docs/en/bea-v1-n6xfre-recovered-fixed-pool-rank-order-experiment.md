# BEA-v1-N6XFR-E Recovered Fixed-Pool Rank-Order Experiment

Date: 2026-06-29

BEA-v1-N6XFR-E revives the fixed-pool rank-order route using locally recovered private N2 rank-pack rows. It is a new public phase and does not rewrite N6 history. The evaluator reads recovered private row content only to compute fixed-pool order-transform outcomes, then publishes only scanner-safe N6F public buckets and aggregate counts.

## Result

```text
status: recovered_fixed_pool_rank_order_experiment_pass_n7_authorized
self-test: 14 / 14
forbidden scan: pass
private rank-pack rows read: 40
fixed arms: 4
private outcome rows computed: 160
public sanitized arm outcome rows: 160
best top10 recovery: 25 / 40
threshold: top10 >= 16 and regressions <= 2
N7 audit authorized: true
runtime/default promotion authorized: false
```

## Arms

The four N5 arms were evaluated as fixed-pool order transforms only:

- `baseline_n2_order`
- `extra_depth_promote_before_primary_prefix_4`
- `bounded_interleave_primary2_extra1`
- `late_extra_depth_demote_after_primary_prefix_8`

The evaluator used a deterministic recovered-row provenance rule without gold signal: original ranks up to 20 are primary and ranks above 20 are extra-depth evidence. All transforms preserve intra-bucket original order, add no candidates, remove no candidates, run no retrieval, and use no selector/reranker.

## Metrics

| Arm | Top-10 recovery | Top-20 recovery | Regressions | Status |
|---|---:|---:|---:|---|
| baseline_n2_order | 0 / 40 | 0 / 40 | 0 | below threshold |
| extra_depth_promote_before_primary_prefix_4 | 25 / 40 | 34 / 40 | 0 | passes threshold |
| bounded_interleave_primary2_extra1 | 10 / 40 | 14 / 40 | 0 | below threshold |
| late_extra_depth_demote_after_primary_prefix_8 | 0 / 40 | 0 / 40 | 0 | below threshold |

The N5 pass threshold remains top-10 recovery at least 16 over 40 with at most 2 regressions. The recovered experiment passes via `extra_depth_promote_before_primary_prefix_4` at 25 / 40 with 0 regressions.

## Decision

N6XFR-E authorizes only `BEA-v1-N7 Recovered Fixed-Pool Rank-Order Result Audit`. It does not authorize runtime/default promotion, policy changes, retrieval/reruns, candidate-pool generation/materialization, selector/reranker execution, P5, BEA-v1-A, counterfactuals, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n6xfre_recovered_fixed_pool_rank_order_experiment.py`
- Report: `artifacts/bea_v1_n6xfre_recovered_fixed_pool_rank_order_experiment/bea_v1_n6xfre_recovered_fixed_pool_rank_order_experiment_report.json`
