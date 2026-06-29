# BEA-v1-N10BM After-Heavy Local Asymmetry Refinement Sweep

Date: 2026-06-29

BEA-v1-N10BM is a direct empirical local refinement sweep over the same scoped N1 span rows. It tests whether the N10BK/N10BL after-heavy winner `before25_after75` is a local optimum or a coarse-grid artifact. It uses fixed total cost proxy `100` only, the seven predeclared variants only, and public aggregate/bucket output only.

## Result

```text
status: after_heavy_local_asymmetry_refinement_complete_n10bn_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
variant count: 7
fixed total cost proxy: 100
N10BN authorized: true
```

## Local refinement metrics

| Variant | top10/top20 | Delta vs before25_after75 | Delta vs pm50 | Lost before25_after75 top10 | Lost pm50 top10 |
| --- | ---: | ---: | ---: | ---: | ---: |
| before10_after90 | 20 / 23 | 0 / -1 | +1 / 0 | 0 | 0 |
| before15_after85 | 20 / 23 | 0 / -1 | +1 / 0 | 0 | 0 |
| before20_after80 | 20 / 24 | 0 / 0 | +1 / +1 | 0 | 0 |
| before25_after75 | 20 / 24 | 0 / 0 | +1 / +1 | 0 | 0 |
| before30_after70 | 20 / 24 | 0 / 0 | +1 / +1 | 0 | 0 |
| before35_after65 | 20 / 24 | 0 / 0 | +1 / +1 | 0 | 0 |
| before40_after60 | 20 / 24 | 0 / 0 | +1 / +1 | 0 | 0 |

`before25_after75` remains on the local optimum plateau. The sweep has multiple equal top-10 winners, with `before20_after80` through `before40_after60` matching the best top10/top20 values. The local result therefore supports an after-heavy plateau rather than a single sharp optimum.

## Boundary

All windows are fixed globally. No gold or miss-direction signal was used to choose per-row windows. No new cost budget, adaptive per-row choice, runtime/default behavior, retrieval/rerun, candidate generation, selector/reranker execution, P5, BEA-v1-A, heldout/generalization claim, method-winner claim, or downstream-value claim is authorized.

## Handoff

N10BM authorizes only `BEA-v1-N10BN After-Heavy Local Asymmetry Refinement Package`, a public package of this local-refinement result.

## Artifact

- Script: `eval/bea_v1_n10bm_after_heavy_local_asymmetry_refinement.py`
- Report: `artifacts/bea_v1_n10bm_after_heavy_local_asymmetry_refinement/bea_v1_n10bm_after_heavy_local_asymmetry_refinement_report.json`
