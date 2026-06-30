# BEA-v1-N10DN-R Corrected Deep-Rank Promotion Public Package

日期：2026-06-30

BEA-v1-N10DN-R 是 corrected N10DM-R suffix-safe deep-rank promotion smoke 的 public-only package。它只读取 public artifacts，不进行 private reads 或 recompute。

## 结果

```text
status: corrected_deep_rank_promotion_public_package_complete_n10dor_authorized
self-test: 12 / 12
forbidden scan: pass
private reads in N10DN-R: 0
recomputes in N10DN-R: 0
anchor suffix-safe file top10/top20: 44 / 58
anchor projected span top10/top20: 39 / 49
positive variants: 0
harmful variants: 5
old negative conclusion still holds: true
```

## Package summary

N10DM-R 将 matching rule 校正为 suffix-safe file reach。校正后的 anchor 为 file `44 / 58`，projected span `39 / 49`。五个非 anchor 的 no-duplicate-pressure deep-rank promotion variants 仍然 harmful；最佳 interleave variants 仍低于 anchor，为 file `40 / 58` 与 projected span `36 / 49`。

因此该 package 在 suffix-safe matching 下继续关闭 deep-rank promotion line，并将机制路线转回 corrected candidate-pool absence/source analysis。

## Handoff

N10DN-R 只授权 `BEA-v1-N10DO-R Corrected Candidate-Pool Absence Source Mechanism Audit`。它不授权 retrieval、rerun、candidate generation/materialization/add/remove、oracle insertion、selector/reranker execution、runtime/default changes、P5、BEA-v1-A、heldout/generalization claims、method-winner claims、downstream-value claims 或 broad private reads。

## Artifact

- Script: `eval/bea_v1_n10dnr_corrected_deep_rank_promotion_public_package.py`
- Report: `artifacts/bea_v1_n10dnr_corrected_deep_rank_promotion_public_package/bea_v1_n10dnr_corrected_deep_rank_promotion_public_package_report.json`
