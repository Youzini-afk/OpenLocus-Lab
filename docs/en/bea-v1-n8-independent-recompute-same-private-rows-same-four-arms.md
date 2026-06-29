# BEA-v1-N8 Independent Recompute Same Private Rows Same Four Arms

Date: 2026-06-29

BEA-v1-N8 independently recomputes the recovered fixed-pool rank-order experiment using the same scoped private N2 rows and the same four N5 arms. The transform logic is implemented directly in N8; it does not import or call the N6XFR-E evaluator. The public artifact reports only buckets, counts, and booleans.

## Result

```text
status: independent_recompute_same_private_rows_pass_n9_authorized
self-test: 14 / 14
forbidden scan: pass
private rank-pack rows read: 40
other private files read: 0
arms recomputed: 4
best arm: extra_depth_promote_before_primary_prefix_4
best top10 recovery: 25 / 40
best top20 recovery: 34 / 40
regressions: 0
per-arm comparison to N6XFR-E: match
threshold reproduced: true
```

## Recompute boundary

N8 reads exactly one scoped private input bucket and no other private files. It does not publish the private input path, file name, candidate lists, gold paths, exact ranks, source identifiers, snippets, hashes, or provider payloads. It performs no retrieval, no rerun, no candidate generation/materialization, no selector/reranker execution, no P5, no BEA-v1-A, no counterfactual, and no runtime/default change.

## Independent arms

The four arms are recomputed with fixed-pool order-transform semantics and the provenance rule bucket `original_rank_le_20_primary_rank_gt_20_extra_depth_no_gold_signal`:

- `baseline_n2_order`: 0/40 top-10, 0/40 top-20.
- `extra_depth_promote_before_primary_prefix_4`: 25/40 top-10, 34/40 top-20.
- `bounded_interleave_primary2_extra1`: 10/40 top-10, 14/40 top-20.
- `late_extra_depth_demote_after_primary_prefix_8`: 0/40 top-10, 0/40 top-20.

All per-arm top-10/top-20/regression counts match N6XFR-E. The N5 threshold is reproduced: top-10 recovery is at least 16/40 and regressions are 0.

## Decision

N8 authorizes only `BEA-v1-N9 Recovered Fixed-Pool Result Replication Package`. It does not authorize P5, BEA-v1-A, selector/reranker execution, retrieval expansion, additional reruns, runtime/default promotion, policy changes, counterfactuals, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n8_independent_recompute_same_private_rows_same_four_arms.py`
- Report: `artifacts/bea_v1_n8_independent_recompute_same_private_rows_same_four_arms/bea_v1_n8_independent_recompute_same_private_rows_same_four_arms_report.json`
