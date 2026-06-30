# BEA-v1-N10EI Fixed Full/Guard Combination Package

日期：2026-06-30

BEA-v1-N10EI 打包 N10EH，不读取私有数据、不重算。

## 结果

```text
status: fixed_full_guard_combination_package_complete_n10ej_authorized
self-test: 5 / 5
forbidden scan: pass
variant count: 7
full novel-first top10: 11
best combination top10: 11
N10EG union bound: 13
any variant beats full novel-first: false
any variant reaches union bound: false
```

## 含义

N10EH 确认了一个负但有用的结果：简单固定组合不能超过 full novel-first。缺失的 union cases 需要差异分析，而不是继续朴素拼接。

## Handoff

N10EI 只授权 N10EJ full-only vs guard-only difference analysis over the same scoped rows。它不授权 new/scaled retrieval、candidate generation、runtime/default changes、selector/reranker execution、method-winner claims、downstream claims 或 heldout/generalization claims。

## Artifact

- Script: `eval/bea_v1_n10ei_fixed_full_guard_combination_package.py`
- Report: `artifacts/bea_v1_n10ei_fixed_full_guard_combination_package/bea_v1_n10ei_fixed_full_guard_combination_package_report.json`
