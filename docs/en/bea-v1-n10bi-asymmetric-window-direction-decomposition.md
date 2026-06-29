# BEA-v1-N10BI Asymmetric Window Direction Mechanism Decomposition

Date: 2026-06-29

BEA-v1-N10BI is a direct empirical mechanism decomposition over the same scoped N1 span rows. It compares only fixed symmetric `pm50` against asymmetric `before25_after75`. It does not add variants, tune adaptively, change runtime/default behavior, run retrieval/reruns/OpenLocus, generate candidates, or make heldout/generalization, method-winner, or downstream-value claims.

## Result

```text
status: asymmetric_window_direction_decomposition_complete_n10bj_authorized
self-test: 15 / 15
forbidden scan: pass
private span rows read: 213
pm50 top10/top20: 19 / 23
before25_after75 top10/top20: 20 / 24
net gain: +1 / +1
lost pm50 top10 hits: 0
```

## Direction mechanism

N10BI uses private line ranges only internally and publishes aggregate buckets only.

| Comparison bucket | Direction bucket | Top10 case count |
| --- | --- | ---: |
| gained_by_before25_after75_vs_pm50 | before_gold_gap | 1 |
| gained_by_before25_after75_vs_pm50 | after_gold_gap | 0 |
| gained_by_before25_after75_vs_pm50 | already_overlap | 0 |
| gained_by_before25_after75_vs_pm50 | other | 0 |
| lost_by_before25_after75_vs_pm50 | before_gold_gap | 0 |
| lost_by_before25_after75_vs_pm50 | after_gold_gap | 0 |
| lost_by_before25_after75_vs_pm50 | already_overlap | 0 |
| lost_by_before25_after75_vs_pm50 | other | 0 |

The asymmetric point gains one top-10 span hit at the same cost as pm50 and loses no pm50 top-10 hits. The gain is bucketed as a before-gold gap recovery under the fixed global window shape.

## Policy boundary

The compared windows are fixed global variants. Gold or miss direction is not used to choose per-record windows. This is a same-source N1 proxy mechanism decomposition only, not a runtime/default rule and not heldout evidence.

## Handoff

N10BI authorizes only `BEA-v1-N10BJ Asymmetric Window Direction Mechanism Package`, a public package. It does not authorize private reads, new variants, adaptive tuning, runtime/default behavior, retrieval/rerun, candidate generation, selector/reranker execution, P5, BEA-v1-A, heldout/generalization claims, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10bi_asymmetric_window_direction_decomposition.py`
- Report: `artifacts/bea_v1_n10bi_asymmetric_window_direction_decomposition/bea_v1_n10bi_asymmetric_window_direction_decomposition_report.json`
