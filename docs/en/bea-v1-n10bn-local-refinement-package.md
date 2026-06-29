# BEA-v1-N10BN After-Heavy Local Asymmetry Refinement Package

Date: 2026-06-29

BEA-v1-N10BN is a public-only package for the N10BM after-heavy local asymmetry refinement sweep. It reads public artifacts only and does not read private rows, recompute metrics, add variants, tune adaptively, change cost budgets, run retrieval/reruns/OpenLocus, generate/materialize candidates, or make runtime/default, heldout/generalization, method-winner, or downstream-value claims.

## Result

```text
status: local_refinement_package_complete_n10bo_authorized
self-test: 14 / 14
forbidden scan: pass
private reads in N10BN: 0
recomputes in N10BN: 0
N10BO authorized: true
```

## Packaged local-refinement facts

All variants use fixed total cost proxy `100`. The winner rule is top10 primary, top20 tiebreak.

| Variant | top10/top20 | Winner / plateau member |
| --- | ---: | --- |
| before10_after90 | 20 / 23 | false |
| before15_after85 | 20 / 23 | false |
| before20_after80 | 20 / 24 | true |
| before25_after75 | 20 / 24 | true |
| before30_after70 | 20 / 24 | true |
| before35_after65 | 20 / 24 | true |
| before40_after60 | 20 / 24 | true |

Conclusion: `before25_after75` is a local optimum plateau member, not a unique magic value. The plateau spans `before20_after80` through `before40_after60`. Candidate pool and order are unchanged, and fixed global windows are used without per-row adaptation.

## Handoff

N10BN authorizes only `BEA-v1-N10BO Plateau Mechanism Decomposition`: same scoped N1 span rows, plateau variants only (`20/80`, `25/75`, `30/70`, `35/65`, `40/60`), common recovered cases, variant-specific gains/losses, before/after bucket contributions, and lost original hits. Output must remain public aggregate/bucket only.

## Artifact

- Script: `eval/bea_v1_n10bn_local_refinement_package.py`
- Report: `artifacts/bea_v1_n10bn_local_refinement_package/bea_v1_n10bn_local_refinement_package_report.json`
