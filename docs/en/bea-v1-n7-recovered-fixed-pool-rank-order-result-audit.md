# BEA-v1-N7 Recovered Fixed-Pool Rank-Order Result Audit

Date: 2026-06-29

BEA-v1-N7 is a public-artifact-only audit of the N6XFR-E recovered fixed-pool rank-order experiment. It reads the committed public N6XFR-E report and supporting public N5/N6F contracts only. It does not read private rows, inspect ignored/private storage, recompute outcomes, run OpenLocus, rerun retrieval, generate candidates, or modify the N6XFR-E artifact.

## Result

```text
status: recovered_fixed_pool_rank_order_result_audit_pass_n8_authorized
self-test: 14 / 14
forbidden scan: pass
case count: 40
arm count: 4
public arm outcome rows: 160
best arm: extra_depth_promote_before_primary_prefix_4
best top10 recovery: 25 / 40
best regression count: 0
threshold: top10 >= 16 and regressions <= 2
N8 authorized: true
```

## Audit findings

- N6XFR-E source status is `recovered_fixed_pool_rank_order_experiment_pass_n7_authorized` and its forbidden scan passes.
- Public outcome schema matches the N6F 14-field schema for all 160 rows.
- All four arms use fixed-pool order-transform semantics with provenance rule bucket `original_rank_le_20_primary_rank_gt_20_extra_depth_no_gold_signal`.
- Candidate-pool changed count, new-retrieval count, selector/reranker count, gold-used-for-ordering count, hard-cap violations, and private-read count are all zero for this audit boundary.
- The best arm is `extra_depth_promote_before_primary_prefix_4`, with top-10 recovery 25/40 and 0 regressions; the N5 threshold passes.

## Decision

N7 authorizes only `BEA-v1-N8 Independent Recompute Same Private Rows Same Four Arms`. N8 is an audit/recompute scope only. N7 does not authorize P5, BEA-v1-A, selector/reranker execution, retrieval expansion, reruns outside N8 scope, runtime/default promotion, policy changes, counterfactuals, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n7_recovered_fixed_pool_rank_order_result_audit.py`
- Report: `artifacts/bea_v1_n7_recovered_fixed_pool_rank_order_result_audit/bea_v1_n7_recovered_fixed_pool_rank_order_result_audit_report.json`
