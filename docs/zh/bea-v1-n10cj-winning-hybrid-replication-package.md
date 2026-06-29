# BEA-v1-N10CJ Winning Hybrid Public Replication Package

日期：2026-06-29

BEA-v1-N10CJ 是 N10CG/N10CH/N10CI winning hybrid chain 的 public-only replication package。它只读取 public artifacts，不进行 private reads、不 recompute，也不添加 new variants。

## 结果

```text
status: winning_hybrid_replication_package_complete_n10ck_authorized
self-test: 13 / 13
forbidden scan: pass
private reads in N10CJ: 0
recomputes in N10CJ: 0
N10CK authorized: true
```

## Replicated winning hybrid

Winning hybrid：`short75_225_top3_all_pm200`。

- N10CG result：`25 / 31`，cost10/cost20 `3300 / 6300`，相对 pm200 节省 `700 / 1700`，lost short75/225 hits `0`。
- N10CI independent recompute：完全匹配，为 `25 / 31`，cost10/cost20 `3300 / 6300`，lost short75/225 hits `0`。
- Candidate pool/order 保持不变。
- N10CI 没有 import、call 或 reuse N10CG evaluator code；N10CG code call count 为 `0`。

## Policy rule boundary

该 policy rule 只使用 observable original span-length bucket 与 candidate-position bucket：short-span broad expansion 加 top3 all-span pm200。它不使用 gold、outcome、miss direction、file identity 或 content 作为 policy inputs。

## Claim boundary

这仍然只是 same-source N1 proxy evidence。它不是 heldout/generalization evidence，不是 runtime/default behavior，不是 retrieval/rerun，不是 candidate generation，不是 adaptive tuning，不是 P5/BEA-v1-A，也不是 method/downstream claim。

## Handoff

N10CJ 只授权 `BEA-v1-N10CK Default-Off Adapter Smoke for Winning Hybrid`。它不授权 runtime/default enablement、existing evaluator hook-in、heldout/generalization claims、retrieval/rerun、candidate generation/add/remove/reorder、adaptive tuning、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10cj_winning_hybrid_replication_package.py`
- Report: `artifacts/bea_v1_n10cj_winning_hybrid_replication_package/bea_v1_n10cj_winning_hybrid_replication_package_report.json`
