# BEA-v1-N10BD Operating-Point Tradeoff Decomposition Audit Package

Date: 2026-06-29

BEA-v1-N10BD is a public-only audit/package for the N10BC operating-point tradeoff decomposition. It reads public artifacts only. It does not read private rows, recompute metrics, add variants, tune adaptively, run retrieval/reruns/OpenLocus, generate/materialize candidates, or change runtime/default behavior.

## Result

```text
status: operating_point_tradeoff_package_complete_n10be_authorized
self-test: 13 / 13
forbidden scan: pass
private reads in N10BD: 0
recomputes in N10BD: 0
N10BE authorized: true
```

## Packaged tradeoff facts

| Step | Variant | Cumulative top10/top20 | Marginal top10/top20 | Marginal cost | Cost bucket | Lost previous hits |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| baseline | baseline | 9 / 10 | +9 / +10 | 0 | baseline | 0 |
| low_cost | pm30 | 18 / 22 | +9 / +12 | +600 | low | 0 |
| balanced | before25_after75 | 20 / 24 | +2 / +2 | +400 | medium | 0 |
| max_recall | pm200 | 25 / 30 | +5 / +6 | +3000 | very_high | 0 |

Candidate pool and candidate order remain unchanged.

## Mechanism package

All marginal top-10 gains are before/after gold-window gap recoveries:

- baseline -> low_cost: 8 before-gold gap, 1 after-gold gap.
- low_cost -> balanced: 2 before-gold gap.
- balanced -> max_recall: 3 before-gold gap, 2 after-gold gap.

N10BD therefore packages the N10BC interpretation that max_recall uses the same mechanism as the lower-cost points, not a qualitatively new mechanism.

## Handoff

N10BD authorizes only `BEA-v1-N10BE Cost-Aware Operating-Point Decision Smoke`: same scoped N1 rows, no new variants, budget buckets `strict_budget <=600 -> low_cost`, `moderate_budget <=1000 -> balanced`, and `recall_budget <=4000 -> max_recall`, with public aggregate/bucket output only and no runtime/default recommendation.

## Artifact

- Script: `eval/bea_v1_n10bd_operating_point_tradeoff_package.py`
- Report: `artifacts/bea_v1_n10bd_operating_point_tradeoff_package/bea_v1_n10bd_operating_point_tradeoff_package_report.json`
