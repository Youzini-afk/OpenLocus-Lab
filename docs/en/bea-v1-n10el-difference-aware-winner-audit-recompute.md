# BEA-v1-N10EL Audit/Recompute of Difference-Aware Winner

Date: 2026-06-30

BEA-v1-N10EL independently recomputes the N10EK winning fixed rule over the same scoped N10DZ top100 private rows and N1 rows. It may read the N10EK public artifact for expected aggregate values, but the policy transform is reimplemented independently and does not import or call the N10EK evaluator.

The audited frozen policy is the exact N10EK rule: if `top5_novel_candidate_item_count >= 4`, use `guarded_top5_novel_distinct`; otherwise use `full_novel_first`. This threshold counts top-5 candidate items, not distinct files.

N10EL does not run retrieval, OpenLocus binary execution, candidate generation, network, runtime/default changes, or selector/reranker logic.

## Result

```text
status: difference_aware_winner_audit_recompute_complete_n10em_authorized
self-test: 8 / 8
forbidden scan: pass
expected top10/top20/top50/top100: 13 / 16 / 20 / 26
observed top10/top20/top50/top100: 13 / 16 / 20 / 26
expected lost baseline top10: 0
observed lost baseline top10: 0
expected/observed counts match: true
n10ek code call count: 0
```

## Policy boundary

The public artifact records the policy contract explicitly:

- `gold_used_for_policy_bool = false`
- `old_pool_membership_used_for_policy_bool = true`
- `full_guard_outcome_membership_used_for_policy_bool = false`
- `threshold_frozen_bool = true`
- threshold feature: `top5_novel_candidate_item_count`
- threshold operator/value: `>= 4`
- `n10ek_code_call_count = 0`

The public artifact is aggregate/bucket only. It does not publish paths, filenames, queries, candidates, gold labels, spans, or exact ranks.

## Aggregate buckets

- `top5_novel_candidate_item_count_0_to_2`: 41 cases
- `top5_novel_candidate_item_count_3`: 2 cases
- `top5_novel_candidate_item_count_4_to_5`: 17 cases
- selected `full_novel_first`: 43 cases
- selected `guarded_top5_novel_distinct`: 17 cases

## Meaning

The N10EK winner independently reproduces its aggregate result without using N10EK transform code. Gold is used only for scoring, not for the policy. Old-pool membership is intentionally used to define novelty; full-only/guard-only outcome membership is not used to choose per case. This remains same-source audit evidence only; it is not a runtime/default recommendation, method-winner claim, downstream claim, or heldout/generalization claim.

## Handoff

N10EL authorizes only N10EM public replication package, followed by a decision about broader sample or CI validation. It does not authorize new/scaled retrieval, OpenLocus binary execution, candidate generation, network, runtime/default changes, selector/reranker execution, method-winner claims, downstream claims, or heldout/generalization claims.

## Artifact

- Script: `eval/bea_v1_n10el_difference_aware_winner_audit_recompute.py`
- Report: `artifacts/bea_v1_n10el_difference_aware_winner_audit_recompute/bea_v1_n10el_difference_aware_winner_audit_recompute_report.json`
