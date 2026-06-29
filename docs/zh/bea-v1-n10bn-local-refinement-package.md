# BEA-v1-N10BN After-Heavy Local Asymmetry Refinement Package

日期：2026-06-29

BEA-v1-N10BN 是 N10BM after-heavy local asymmetry refinement sweep 的 public-only package。它只读取 public artifacts，不读取 private rows，不 recompute metrics，不添加 variants，不进行 adaptive tuning，不改变 cost budgets，不运行 retrieval/reruns/OpenLocus，不生成或 materialize candidates，也不作 runtime/default、heldout/generalization、method-winner 或 downstream-value claims。

## 结果

```text
status: local_refinement_package_complete_n10bo_authorized
self-test: 14 / 14
forbidden scan: pass
private reads in N10BN: 0
recomputes in N10BN: 0
N10BO authorized: true
```

## Packaged local-refinement facts

所有 variants 均使用 fixed total cost proxy `100`。Winner rule 为 top10 primary、top20 tiebreak。

| Variant | top10/top20 | Winner / plateau member |
| --- | ---: | --- |
| before10_after90 | 20 / 23 | false |
| before15_after85 | 20 / 23 | false |
| before20_after80 | 20 / 24 | true |
| before25_after75 | 20 / 24 | true |
| before30_after70 | 20 / 24 | true |
| before35_after65 | 20 / 24 | true |
| before40_after60 | 20 / 24 | true |

结论：`before25_after75` 是 local optimum plateau member，而不是唯一的 magic value。Plateau 覆盖 `before20_after80` 到 `before40_after60`。Candidate pool 与 order 均未改变，并且使用 fixed global windows、无 per-row adaptation。

## Handoff

N10BN 只授权 `BEA-v1-N10BO Plateau Mechanism Decomposition`：same scoped N1 span rows，仅 plateau variants（`20/80`、`25/75`、`30/70`、`35/65`、`40/60`），分析 common recovered cases、variant-specific gains/losses、before/after bucket contributions 与 lost original hits。输出必须保持 public aggregate/bucket only。

## Artifact

- Script: `eval/bea_v1_n10bn_local_refinement_package.py`
- Report: `artifacts/bea_v1_n10bn_local_refinement_package/bea_v1_n10bn_local_refinement_package_report.json`
