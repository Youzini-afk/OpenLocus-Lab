# BEA-v1-N10EG Novel-First / Guarded Complementarity Slicing

日期：2026-06-30

BEA-v1-N10EG 在同一 scoped rows 上切分 N10EF 的 trade-off。它读取同一份 N10DZ top100 rows 和 N1 rows，但不运行 new retrieval、candidate generation、runtime/default changes 或 selector/reranker logic。

## 结果

```text
status: novel_first_guard_complementarity_slicing_complete_n10eh_authorized
self-test: 5 / 5
forbidden scan: pass
baseline top10: 5
full novel-first top10: 11
guarded top5 novel-distinct top10: 10
full/guard union top10: 13
intersection: 8
full-only: 3
guard-only: 2
```

## Interpretation

关键发现是：full novel-first 和 guarded top5 novel-distinct 不是严格替代关系。Full novel-first 是最强单规则，但 guarded top5 也恢复了 2 个 full novel-first 没命中的 top10 cases。二者 union 是 13，高于任一单规则。

所以下一步不是继续 package，而是固定 full/guard combination test：在不加候选、不检索的情况下，gold-free 组合能不能拿到更多 union 收益。

## Handoff

N10EG 只授权 N10EH：在同一 scoped rows 上做 fixed full/guard combination repacking。它不授权 new/scaled retrieval、runtime/default、selector/reranker、method-winner、downstream 或 heldout/generalization claims。

## Artifact

- Script: `eval/bea_v1_n10eg_novel_first_guard_complementarity_slicing.py`
- Report: `artifacts/bea_v1_n10eg_novel_first_guard_complementarity_slicing/bea_v1_n10eg_novel_first_guard_complementarity_slicing_report.json`
