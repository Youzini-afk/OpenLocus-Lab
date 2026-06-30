# BEA-v1-N10DQ Oracle Candidate-Insertion Ceiling Public Package

日期：2026-06-30

BEA-v1-N10DQ 是 N10DP oracle candidate-insertion ceiling smoke 的 public-only package。它只读取 public artifacts，不进行 private reads、recomputation 或 oracle insertion。

## 结果

```text
status: oracle_candidate_ceiling_public_package_complete_n10dr_authorized
self-test: 11 / 11
forbidden scan: pass
private reads in N10DQ: 0
recomputes in N10DQ: 0
oracle insertion executions in N10DQ: 0
N10DR authorized: future oracle-scoped canary only
```

## Packaged ceiling

- Current suffix-safe anchor file reach：top10/top20 `44 / 58`。
- Affected absent-pool cases：`141`。
- Oracle rank1/rank5/rank10 insertion ceiling：top10/top20 `185 / 199`，相对 anchor 增量 `+141 / +141`。
- Oracle append-after-top10 ceiling：top10/top20 `44 / 199`，增量 `+0 / +141`。
- Span metric boundary：`not_evaluated_no_oracle_span`。

## Boundary

这是 candidate-source acquisition 的 upper-bound value signal，不是 feasible policy、retrieval result、source-acquisition result、method winner、downstream-value claim、heldout/generalization claim 或 runtime/default recommendation。

## Handoff

N10DQ 只授权未来 oracle/orchestrator contract 下的 `BEA-v1-N10DR Real Candidate-Source Canary`。N10DQ 本身不授权 retrieval、rerun、source acquisition execution、real candidate generation、selector/reranker execution、P5、BEA-v1-A、runtime/default changes、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10dq_oracle_candidate_ceiling_public_package.py`
- Report: `artifacts/bea_v1_n10dq_oracle_candidate_ceiling_public_package/bea_v1_n10dq_oracle_candidate_ceiling_public_package_report.json`
