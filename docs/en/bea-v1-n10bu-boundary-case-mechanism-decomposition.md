# BEA-v1-N10BU Boundary Case Mechanism Decomposition

Date: 2026-06-29

BEA-v1-N10BU is a direct empirical decomposition of the single plateau-core case that fixed `25/75` misses at total cost 75 but recovers at total cost 80. It reads only the same scoped N1 span rows and public N10BT/N10BS/N10BR artifacts. It does not add variants, tune adaptively, run retrieval/reruns/OpenLocus, generate candidates, or make runtime/default, heldout/generalization, method-winner, or downstream-value claims.

## Result

```text
status: boundary_case_mechanism_decomposition_complete_n10bv_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
boundary comparison: cost75 19/23 vs cost80 20/24
recovered-at-80/missed-at-75 cases: 1
N10BV authorized: true
```

## Boundary comparison

| Cost | top10/top20 | Lost plateau core | File-hit top10 count | Transition count |
| ---: | ---: | ---: | ---: | ---: |
| 75 | 19 / 23 | 1 | 34 | 1 recovered at 80 |
| 80 | 20 / 24 | 0 | 34 | 1 recovered at 80 |

## Mechanism facts

For the single recovered-at-80/missed-at-75 case:

- gap bucket: `before_gold_gap`
- distance-to-expanded-window bucket: `near_1_5`
- file hit remains top10: true
- span overlap is just outside the 75-cost window: true
- recovered at cost 80: true

All facts are bucket/count only. No private path, line number, span, snippet, gold content, candidate list, exact rank, or row identifier is public.

## Handoff

N10BU authorizes only `BEA-v1-N10BV Boundary Case Mechanism Package`, a public package of this one-case boundary mechanism result.

## Artifact

- Script: `eval/bea_v1_n10bu_boundary_case_mechanism_decomposition.py`
- Report: `artifacts/bea_v1_n10bu_boundary_case_mechanism_decomposition/bea_v1_n10bu_boundary_case_mechanism_decomposition_report.json`
