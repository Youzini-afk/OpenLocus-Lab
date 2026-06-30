# BEA-v1-N10DP Oracle Candidate-Insertion Ceiling Smoke

日期：2026-06-30

BEA-v1-N10DP 是 non-policy upper-bound smoke。它估计：如果未来 source 能为 gold file 不在 observed pool 中的 cases 添加一个匿名 gold-file candidate，file-reach ceiling 会是多少。它不运行 retrieval，不 rerun OpenLocus，不生成或 materialize real candidates，不运行 selector/reranker，也不改变 runtime/default behavior。

## 结果

```text
status: oracle_candidate_insertion_ceiling_smoke_complete_n10dq_authorized
self-test: 12 / 12
forbidden scan: pass
private span rows read: 213
current suffix-safe top10/top20 file reach: 44 / 58
affected absent-pool cases: 141
rank1/rank5/rank10 oracle top10 file ceiling: 185 / 213
rank1/rank5/rank10 oracle top20 file ceiling: 199 / 213
append-after-top10 oracle top10/top20 ceiling: 44 / 199
span overlap status: not_evaluated_no_oracle_span
```

## Interpretation

对 141 个 absent-pool cases 在 top10 内放置一个匿名 oracle gold-file candidate，会将 top10 file reach 从 `44` 提升到 `185`。追加到 top10 之后不会改变 top10，但会将 top20 file reach 提升到 `199`。由于没有真实 oracle span candidate，span utility 未评估；N10DP 不伪造 span overlap。

## Boundary

这是 oracle ceiling，不是 feasible policy 或 runtime/default recommendation。Public outputs 仅为 aggregate/bucket，不包含 private paths、file names、spans、lines、snippets、gold labels、candidate lists、exact ranks 或 raw rows。

## Handoff

N10DP 只授权 `BEA-v1-N10DQ Oracle Candidate-Insertion Ceiling Public Package`。它不授权 retrieval、source acquisition、real candidate generation、selector/reranker execution、runtime/default changes、P5、BEA-v1-A、heldout/generalization claims、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10dp_oracle_candidate_insertion_ceiling_smoke.py`
- Report: `artifacts/bea_v1_n10dp_oracle_candidate_insertion_ceiling_smoke/bea_v1_n10dp_oracle_candidate_insertion_ceiling_smoke_report.json`
