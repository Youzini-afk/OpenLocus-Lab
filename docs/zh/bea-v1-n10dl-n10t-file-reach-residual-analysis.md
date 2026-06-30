# BEA-v1-N10DL N10T File-Reach Residual Mechanism Analysis

日期：2026-06-30

BEA-v1-N10DL 是 direct residual mechanism analysis，不是 policy execution。它读取 same scoped N1 span rows 以及 public N10DK/N10DJ/N10DA context。它不运行 retrieval/rerun/OpenLocus，不生成/materialize/add/remove candidates，不重排 candidates，不执行 new promotion policy，不运行 selector/reranker logic，不改变 runtime/default behavior，也不作 heldout/generalization、method-winner 或 downstream claims。

## 结果

```text
status: n10t_file_reach_residual_analysis_complete_n10dm_authorized
self-test: 15 / 15
forbidden scan: pass
private span rows read: 213
top10 file hit / miss: 34 / 179
top20 file hit: 44
policy execution count: 0
N10DM authorized: true
```

## Residual buckets

N10DL 按 first gold-file rank 和 top10 duplicate pressure 对 179 个 top10 file misses 进行分桶。10 个 miss 的 first gold-file evidence 在 ranks 11-20，8 个在 ranks 21-50，161 个在本地候选池中不存在。rank-by-duplicate-pressure cross-tab 很关键：这 18 个 rank-11-50 reachable residual 全部在 no-duplicate-pressure bucket；medium/high duplicate-pressure residual 则是 absent-from-pool cases。Public output 只有 aggregate/bucket counts：不包含 paths、filenames、snippets、spans、lines、candidate lists、exact ranks 或 gold labels。

## Signals

Public report 只记录 bucketed signals：

- no-duplicate-pressure deep-rank probe signal；
- deep-rank retrieval-gap signal 只作为 context，不是推荐的 N10DM policy signal；
- 若存在则记录 pool-absence signal；
- 若不存在 gold-free field signal 则记录 no-safe-signal flag。

N10DL 明确**不**推荐 duplicate-pressure-conditioned promotion：duplicate pressure 确实存在，但 medium/high cases 对应的是 absent-from-pool residual，而不是 reachable rank-11-50 gold files。可行的下一机制是更窄的 no-duplicate-pressure deep-rank probe，使用 candidate rank position、private file identity、file repeat count 和 span-length bucket availability。Source/channel、method 与 score buckets 仅在 complete 时可用，否则标记为 unavailable。

## Handoff

N10DL 只授权 `BEA-v1-N10DM Residual-Aware Rank/File Promotion Rule Smoke`：same scoped rows、fixed variants、允许 no-duplicate-pressure/rank buckets、无 gold policy、无 retrieval/rerun、无 candidate generation，且仅输出 public aggregate。

## Artifact

- Script: `eval/bea_v1_n10dl_n10t_file_reach_residual_analysis.py`
- Report: `artifacts/bea_v1_n10dl_n10t_file_reach_residual_analysis/bea_v1_n10dl_n10t_file_reach_residual_analysis_report.json`
