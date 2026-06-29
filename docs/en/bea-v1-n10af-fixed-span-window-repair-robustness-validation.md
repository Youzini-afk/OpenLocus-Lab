# BEA-v1-N10AF Fixed Span-Window Repair Robustness/Subgroup Validation

Date: 2026-06-29

BEA-v1-N10AF is a direct empirical subgroup validation of the fixed span-window repair smoke. It reads exactly the scoped recovered N1 span rows and public N10AE/N10AD/N10AB/N10Z artifacts. It evaluates only the predeclared target arm `span_extra_depth_promote_before_primary_prefix_4` with the fixed primary repair variant `fixed_symmetric_span_expansion_pm50_lines`.

## Result

```text
status: fixed_span_window_repair_robustness_validation_pass_n10ag_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
baseline top10 span overlap: 9
pm50 top10 span overlap: 19
delta top10 span overlap: 10
pm50 lost original span hits: 0
pm50 file top10 count: 34
positive-delta predeclared subgroups: 5
baseline-span-hit negative-delta subgroups: 0
```

## Subgroup signal

The global N10AE result is reproduced exactly. Positive delta is present in multiple predeclared subgroup families, including:

- `baseline_file_hit_no_span_top10`: +10.
- `pm50_file_hit_top10`: +10.
- `not_span_reachable`: +10 under the original unexpanded span-reach bucket, reflecting window repair of same-file non-overlap cases.
- `before_gold`: +9 and `after_gold`: +1.
- Evidence-count buckets `21_50`: +8 and `gt50`: +2.

The `baseline_span_hit_top10` subgroup has delta 0 and loses no original span hits.

## Boundary

N10AF does not tune windows adaptively, search new arms, add/remove candidates, run retrieval/reruns, execute OpenLocus, generate/materialize candidates, run selector/reranker logic, enter P5/BEA-v1-A, run counterfactuals, promote runtime/default behavior, or make method-winner/downstream-value claims. Public output contains only aggregate and subgroup counts/buckets.

## Decision

The robustness gate passes: global metrics match N10AE, lost hits are zero, at least two predeclared subgroups have positive delta, and no baseline-span-hit subgroup has negative delta. N10AF authorizes only `BEA-v1-N10AG Fixed Span-Window Repair Claim-Boundary Audit Package`, public package/audit scope only.

## Artifact

- Script: `eval/bea_v1_n10af_fixed_span_window_repair_robustness_validation.py`
- Report: `artifacts/bea_v1_n10af_fixed_span_window_repair_robustness_validation/bea_v1_n10af_fixed_span_window_repair_robustness_validation_report.json`
