# BEA-v1-N10BM After-Heavy Local Asymmetry Refinement Sweep

日期：2026-06-29

BEA-v1-N10BM 是在 same scoped N1 span rows 上进行的 direct empirical local refinement sweep。它检验 N10BK/N10BL 的 after-heavy winner `before25_after75` 是 local optimum 还是 coarse-grid artifact。它只使用 fixed total cost proxy `100`，只使用 7 个预声明 variants，并且只输出 public aggregate/bucket。

## 结果

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

`before25_after75` 仍位于 local optimum plateau。该 sweep 有多个 equal top-10 winners，其中 `before20_after80` 到 `before40_after60` 均达到最佳 top10/top20 值。因此 local result 支持 after-heavy plateau，而不是单个尖锐 optimum。

## Boundary

所有窗口都是 fixed globally。没有使用 gold 或 miss-direction signal 来选择 per-row windows。不授权 new cost budget、adaptive per-row choice、runtime/default behavior、retrieval/rerun、candidate generation、selector/reranker execution、P5、BEA-v1-A、heldout/generalization claim、method-winner claim 或 downstream-value claim。

## Handoff

N10BM 只授权 `BEA-v1-N10BN After-Heavy Local Asymmetry Refinement Package`，即该 local-refinement result 的 public package。

## Artifact

- Script: `eval/bea_v1_n10bm_after_heavy_local_asymmetry_refinement.py`
- Report: `artifacts/bea_v1_n10bm_after_heavy_local_asymmetry_refinement/bea_v1_n10bm_after_heavy_local_asymmetry_refinement_report.json`
