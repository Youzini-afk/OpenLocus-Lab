# BEA-v1-N6 Fixed-Pool Rank-Order Experiment

Date: 2026-06-28

BEA-v1-N6 is the fixed-pool rank-order experiment authorized by N5, but this local public-artifact run is a valid No-Go. N6 reads only committed public N5, N4, N2, N3, and P4L artifacts. It does not read `.openlocus/private`, run retrieval, rerun P4L/N1/N2/N3, execute selectors or rerankers, tune policy, change runtime behavior, or run counterfactuals.

## Result

```text
status: no_go_n6_public_fixed_pool_arm_fields_insufficient
self-test: 16 / 16
forbidden scan: pass
fixed case set consistent: true
N5 arms checked: 4
exact public per-case arm mappings: 0 / 4
per-case arm outcome rows evaluated: 0
N7 result audit authorized: false
```

## Why N6 is No-Go

N5 authorized four exact fixed-pool arms:

1. `baseline_n2_order`
2. `extra_depth_promote_before_primary_prefix_4`
3. `bounded_interleave_primary2_extra1`
4. `late_extra_depth_demote_after_primary_prefix_8`

Committed public artifacts do not contain exact per-case top-10 recovery/regression outcomes for those exact N6 arms. N2 provides baseline indicators but not raw rank/order fields. N3 has public per-case rows for analogous design arms, but their names and semantics are not the exact N5/N6 arms. N6 therefore refuses to map N3 analogues as N6 results and refuses to infer arm outcomes from aggregate counts.

## Arm mapping boundary

The evaluator records each N5 arm with an inexact public mapping:

- `baseline_n2_order` has analogue bucket `frozen_p4_order`, but exact public N6 per-case outcomes are unavailable.
- `extra_depth_promote_before_primary_prefix_4` has analogue bucket `early_extra_depth_quota_3`, but exact public N6 per-case outcomes are unavailable.
- `bounded_interleave_primary2_extra1` has analogue bucket `fixed_interleave_2_primary_1_extra_after_4`, but exact public N6 per-case outcomes are unavailable.
- `late_extra_depth_demote_after_primary_prefix_8` has analogue bucket `bounded_promotion_after_primary_prefix_4_3`, but exact public N6 per-case outcomes are unavailable.

All four arms are marked `no_result_not_evaluated`; `per_case_arm_outcome_records` is present as an empty list.

## Decision

N6 does not authorize N7 result audit. The next allowed phase is `none_until_public_fixed_pool_arm_fields_exist`. It also does not authorize new retrieval, reruns, selector/reranker execution, private reads, runtime/policy changes, counterfactuals, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n6_fixed_pool_rank_order_experiment.py`
- Report: `artifacts/bea_v1_n6_fixed_pool_rank_order_experiment/bea_v1_n6_fixed_pool_rank_order_experiment_report.json`
