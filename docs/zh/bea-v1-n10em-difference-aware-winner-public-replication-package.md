# BEA-v1-N10EM Difference-Aware Winner Public Replication Package

日期：2026-06-30

BEA-v1-N10EM 打包 public N10EK/N10EL chain。它只读取 public artifacts，不读取 private rows，不 recompute transform，不运行 retrieval，不执行 OpenLocus，不生成 candidates，不使用 network，也不改变 runtime/default behavior。

## 结果

```text
status: difference_aware_winner_public_replication_package_complete_n10en_authorized
self-test: 8 / 8
forbidden scan: pass
N10EK winner top10/top20/top50/top100: 13 / 16 / 20 / 26
N10EL audit top10/top20/top50/top100: 13 / 16 / 20 / 26
lost baseline top10: 0
chain consistent: true
```

## Packaged policy boundary

- frozen rule: `if top5_novel_candidate_item_count >= 4 then guarded_top5_novel_distinct else full_novel_first`
- threshold 计数 top-5 candidate items，不是 distinct files
- old-pool membership 用来定义 novelty
- gold 不用于 policy
- full/guard outcome membership 不用于 policy
- N10EL audit 不调用 N10EK transform code

## 含义

N10EM 确认 same-source N10EK experiment 和 N10EL independent audit 一致。这是 difference-aware rule 的强 same-row replication package。它仍不是 runtime/default recommendation、method-winner claim、downstream-value claim 或 heldout/generalization claim。

## Handoff

N10EM 本身仍然是 public-only package，不执行 private reads、recompute、retrieval、OpenLocus execution、network access 或 candidate generation。

它的 handoff 只授权 N10EN bounded CI-validation actions：manual GitHub Actions canary over manifest-listed public repositories、public GitHub clone/fetch、local OpenLocus CLI build、local OpenLocus search against cloned public repos、runner temp space 内的 temporary public candidate materialization、RUN outputs 固定之后的 score-phase label generation，以及 sanitized aggregate-only report upload。

这不授权 provider/model network calls、remote embeddings、private assets、external benchmark downloads、raw candidate/label/query/path upload、runtime/default changes、selector/reranker execution、method-winner claims、downstream claims、heldout/generalization claims、scaled retrieval claims 或 production retrieval changes。

## Artifact

- Script: `eval/bea_v1_n10em_difference_aware_winner_public_replication_package.py`
- Report: `artifacts/bea_v1_n10em_difference_aware_winner_public_replication_package/bea_v1_n10em_difference_aware_winner_public_replication_package_report.json`
