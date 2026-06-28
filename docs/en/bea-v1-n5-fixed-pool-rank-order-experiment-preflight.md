# BEA-v1-N5 Fixed-Pool Rank-Order Experiment Preflight

Date: 2026-06-28

BEA-v1-N5 is a no-execution preflight for BEA-v1-N6. It reads only committed public N4, N2, N3, and P4L artifacts. It does not read `.openlocus/private`, run retrieval, rerun P4L/N1/N2/N3, execute selectors or rerankers, tune policy, change runtime behavior, or run counterfactuals.

## Result

```text
status: fixed_pool_rank_order_experiment_preflight_pass_n6_authorized
self-test: 15 / 15
forbidden scan: pass
eligible fixed-pool cases: 40
rank window: rank_21_50
top20 recovery: not_recovered
top50/top100 recovery: recovered
blocker: extra_depth_append_blocked
fixed-pool order-transform arms: 4
N6 authorized: true
```

## Frozen N6 case set

The preflight freezes exactly 40 N4 sanitized rank-blocker cases. The aggregate row is:

```text
eligible_case_count=40
rank_window_bucket=rank_21_50
top20_recovery_bucket=not_recovered
top50_or_top100_recovery_bucket=recovered
blocker_bucket=extra_depth_append_blocked
fixed_pool_deeper_present_bool=true
private_or_source_linkage_required_bool=false
case_set_frozen_bool=true
```

Public per-case rows, where present, contain only anonymous N5 case id, rank/window/pool/blocker/merge-order buckets, and language/source buckets.

## Fixed-pool arms

N6 may execute only these four arms:

1. `baseline_n2_order`
2. `extra_depth_promote_before_primary_prefix_4`
3. `bounded_interleave_primary2_extra1`
4. `late_extra_depth_demote_after_primary_prefix_8`

Each arm is fixed-pool order-transform only. Candidate pools must not change; new retrieval, selector/reranker execution, and policy tuning are all false.

## Metrics and pass gate

Primary metric: `top10_recovery_count_over_40_fixed_cases`.

Secondary metrics: `top20_recovery_count`, `rank_window_shift_bucket`, `hard_cap_violation_count`, and `case_regression_count`.

The pass threshold bucket is `top10_recovery_ge_16_and_regressions_le_2`. The baseline reference is `n2_baseline_order_zero_top10_over_40`. N5 does not declare a method winner and does not authorize downstream claims.

## Decision

N5 authorizes only **BEA-v1-N6 Fixed-Pool Rank-Order Experiment** scope: execute the predeclared fixed-pool order-transform arms over the 40 N4 sanitized rank-blocker cases using committed public N2/N3 fixed-pool fields. It does not authorize new retrieval, reruns, selector/reranker execution, private reads, runtime/policy changes, counterfactuals, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n5_fixed_pool_rank_order_experiment_preflight.py`
- Report: `artifacts/bea_v1_n5_fixed_pool_rank_order_experiment_preflight/bea_v1_n5_fixed_pool_rank_order_experiment_preflight_report.json`
