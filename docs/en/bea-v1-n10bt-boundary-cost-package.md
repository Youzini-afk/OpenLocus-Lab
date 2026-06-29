# BEA-v1-N10BT Boundary-Cost Package

Date: 2026-06-29

BEA-v1-N10BT is a public-only package for the N10BS boundary-cost refinement sweep. It reads public artifacts only and does not read private rows, recompute metrics, add variants, tune adaptively, run retrieval/reruns/OpenLocus, generate/materialize candidates, or make runtime/default, heldout/generalization, method-winner, or downstream-value claims.

## Result

```text
status: boundary_cost_package_complete_n10bu_authorized
self-test: 14 / 14
forbidden scan: pass
private reads in N10BT: 0
recomputes in N10BT: 0
N10BU authorized: true
```

## Packaged boundary-cost facts

Fixed ratio: `25/75`. Costs: `65`, `70`, `75`, `80`, `85`, `90`, `95`.

| Total cost | top10/top20 | Lost plateau core | Preserved plateau |
| ---: | ---: | ---: | --- |
| 65 | 19 / 22 | 1 | false |
| 70 | 19 / 22 | 1 | false |
| 75 | 19 / 23 | 1 | false |
| 80 | 20 / 24 | 0 | true |
| 85 | 20 / 24 | 0 | true |
| 90 | 20 / 24 | 0 | true |
| 95 | 20 / 24 | 0 | true |

Boundary summary: minimum preserving cost `80`; first failing value below boundary `75`; margin `5`; monotonicity bucket `nondecreasing_top10`. The chosen research point is `cost80_before25_after75`, explicitly not a runtime/default recommendation and not a method-winner claim.

## Handoff

N10BT authorizes only `BEA-v1-N10BU Boundary Case Mechanism Decomposition`: same scoped rows, compare fixed 25/75 at costs 75 and 80, and analyze only bucketed mechanism for the one case recovered at 80 and missed at 75.

## Artifact

- Script: `eval/bea_v1_n10bt_boundary_cost_package.py`
- Report: `artifacts/bea_v1_n10bt_boundary_cost_package/bea_v1_n10bt_boundary_cost_package_report.json`
