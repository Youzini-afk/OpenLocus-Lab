# BEA-v1-N10CS Local Saturation Sweep Public Package

日期：2026-06-30

BEA-v1-N10CS 是 N10CR mechanism-guided local saturation sweep 的 public-only package。它只读取 public artifacts，不进行 private reads、recompute 或 new variants。

## 结果

```text
status: local_saturation_package_complete_n10ct_authorized
self-test: 12 / 12
forbidden scan: pass
private reads in N10CS: 0
recomputes in N10CS: 0
N10CT authorized: true
```

## Packaged facts

- N10CR completed with 8 fixed variants。
- Refined anchor `anchor_refined_top2_pm200_short75_225`：top10/top20 `25 / 31`，cost10/cost20 `3200 / 6200`。
- `pm200_all_spans`：top10/top20 `25 / 30`，cost10/cost20 `4000 / 8000`。
- Positive local result：`top2_pm300_short75_225` 达到 top10/top20 `26 / 32`，cost10/cost20 `3600 / 6600`，lost refined top10 hits `0`，candidate pool/order 不变。
- Saturation decision：`local_window_not_saturated`；`overall_saturation=false`；N10CR 中 rank/file-reach pivot allowed next 为 `false`。
- `top2_pm300_short75_225` 下的 residual：file-not-in-top10 仍为 `167`，same-file/no-span-overlap 从 `9` 降到 `8`，span-overlap-beyond-top10 仍为 `12`。

## Boundary

N10CS 只打包 same-source N1 proxy result。它不授权 runtime/default enablement、existing evaluator hooks、heldout/generalization、retrieval/rerun、candidate generation/add/remove/reorder、rank/file promotion、adaptive tuning、selector/reranker execution、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Handoff

N10CS 只授权 `BEA-v1-N10CT Exploration Around top2_pm300_short75_225`，下一步需由 oracle contract 限定为 adapter smoke 或 bounded pm300-neighborhood follow-up。

## Artifact

- Script: `eval/bea_v1_n10cs_local_saturation_package.py`
- Report: `artifacts/bea_v1_n10cs_local_saturation_package/bea_v1_n10cs_local_saturation_package_report.json`
