# BEA-v1-N10BI Asymmetric Window Direction Mechanism Decomposition

日期：2026-06-29

BEA-v1-N10BI 是在 same scoped N1 span rows 上进行的 direct empirical mechanism decomposition。它只比较 fixed symmetric `pm50` 与 asymmetric `before25_after75`。它不添加 variants，不进行 adaptive tuning，不改变 runtime/default behavior，不运行 retrieval/reruns/OpenLocus，不生成 candidates，也不作 heldout/generalization、method-winner 或 downstream-value claims。

## 结果

```text
status: asymmetric_window_direction_decomposition_complete_n10bj_authorized
self-test: 15 / 15
forbidden scan: pass
private span rows read: 213
pm50 top10/top20: 19 / 23
before25_after75 top10/top20: 20 / 24
net gain: +1 / +1
lost pm50 top10 hits: 0
```

## Direction mechanism

N10BI 只在内部使用 private line ranges，并且只公开 aggregate buckets。

| Comparison bucket | Direction bucket | Top10 case count |
| --- | --- | ---: |
| gained_by_before25_after75_vs_pm50 | before_gold_gap | 1 |
| gained_by_before25_after75_vs_pm50 | after_gold_gap | 0 |
| gained_by_before25_after75_vs_pm50 | already_overlap | 0 |
| gained_by_before25_after75_vs_pm50 | other | 0 |
| lost_by_before25_after75_vs_pm50 | before_gold_gap | 0 |
| lost_by_before25_after75_vs_pm50 | after_gold_gap | 0 |
| lost_by_before25_after75_vs_pm50 | already_overlap | 0 |
| lost_by_before25_after75_vs_pm50 | other | 0 |

该 asymmetric point 在与 pm50 相同 cost 下增加 1 个 top-10 span hit，并且没有丢失 pm50 top-10 hits。该增益在 fixed global window shape 下归入 before-gold gap recovery bucket。

## Policy boundary

被比较的 windows 是 fixed global variants。Gold 或 miss direction 不用于选择 per-record windows。这只是 same-source N1 proxy mechanism decomposition，不是 runtime/default rule，也不是 heldout evidence。

## Handoff

N10BI 只授权 `BEA-v1-N10BJ Asymmetric Window Direction Mechanism Package`，即 public package。它不授权 private reads、new variants、adaptive tuning、runtime/default behavior、retrieval/rerun、candidate generation、selector/reranker execution、P5、BEA-v1-A、heldout/generalization claims、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10bi_asymmetric_window_direction_decomposition.py`
- Report: `artifacts/bea_v1_n10bi_asymmetric_window_direction_decomposition/bea_v1_n10bi_asymmetric_window_direction_decomposition_report.json`
