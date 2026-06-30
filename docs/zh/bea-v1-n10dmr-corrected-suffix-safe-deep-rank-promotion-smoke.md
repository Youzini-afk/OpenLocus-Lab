# BEA-v1-N10DM-R Corrected Suffix-Safe Deep-Rank Promotion Smoke

日期：2026-06-30

BEA-v1-N10DM-R 使用 suffix-safe file matching 作为 primary file-reach rule，重跑 no-duplicate-pressure deep-rank promotion smoke。它只读取 same scoped N1 private span rows 以及 public N10DO/N10DM/N10DL artifacts。它不运行 retrieval/rerun/OpenLocus，不 generate/add/remove candidates，不运行 selector/reranker，也不改变 runtime/default behavior。

## 结果

```text
status: suffix_safe_deep_rank_promotion_smoke_complete_n10dnr_authorized
self-test: 12 / 12
forbidden scan: pass
private span rows read: 213
anchor file top10/top20: 44 / 58
anchor projected span top10/top20: 39 / 49
positive variants: 0
harmful variants: 5
old negative conclusion still holds: true
```

## Corrected counts

Suffix-safe matching 将 N10T anchor 从 prior exact file counts `34 / 44` 提升到 `44 / 58`。在同一 fixed projection 下，projected span counts 为 `39 / 49`。

五个 no-duplicate-pressure deep-rank promotion variants 在 suffix-safe matching 下仍然 harmful。最佳 interleave variants 达到 file `40 / 58` 与 projected span `36 / 49`，仍低于 suffix-safe anchor。

## Boundary

这仍是 existing candidate pool 上的 same-source analysis。Candidate generation、materialization、addition、removal、retrieval、rerun、selector/reranker execution、runtime/default promotion、heldout/generalization claims、method-winner claims 与 downstream-value claims 均不授权。Public outputs 仅为 aggregate/bucket。

## Handoff

N10DM-R 只授权 `BEA-v1-N10DN-R Corrected Deep-Rank Promotion Package`。

## Artifact

- Script: `eval/bea_v1_n10dmr_corrected_suffix_safe_deep_rank_promotion_smoke.py`
- Report: `artifacts/bea_v1_n10dmr_corrected_suffix_safe_deep_rank_promotion_smoke/bea_v1_n10dmr_corrected_suffix_safe_deep_rank_promotion_smoke_report.json`
