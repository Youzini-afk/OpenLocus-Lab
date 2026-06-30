# BEA-v1-N10DS Real Candidate-Source Canary Audit Package

日期：2026-06-30

BEA-v1-N10DS 是 N10DR bounded local candidate-source canary 的 public-only audit/package。它只读取 public N10DR artifact，不进行 private reads、recomputation、retrieval 或 candidate generation。

## 结果

```text
status: real_candidate_source_canary_audit_package_complete_n10dt_authorized
self-test: 10 / 10
forbidden scan: pass
private reads in N10DS: 0
recomputes in N10DS: 0
N10DT authorized: true
```

## Packaged canary facts

- N10DR sampled and executed `30` cases，且 `30` 个 local repositories available。
- Local retrieval command successes：`28`。
- Nonzero-candidate cases：`20`。
- Gold file recovered top10/top20/top50：`0 / 0 / 0`。
- Tiny、moderate 与 rich-wrong pool buckets 均恢复 `0 / 10` cases。

## Interpretation

这是 valid negative canary，不是 infrastructure failure。Bounded local source 在 sampled corrected absent-pool residuals 上没有恢复，因此在 failure-mechanism analysis 之前不应直接 scale 该 source。

## Handoff

N10DS 只授权 `BEA-v1-N10DT Real Candidate-Source Canary Failure Mechanism Analysis`。它不授权 scaled retrieval、network access、git clone、candidate generation/materialization、selector/reranker execution、runtime/default changes、P5、BEA-v1-A、method-winner claims、downstream-value claims、heldout/generalization claims 或 broad private reads。

## Artifact

- Script: `eval/bea_v1_n10ds_real_candidate_source_canary_audit_package.py`
- Report: `artifacts/bea_v1_n10ds_real_candidate_source_canary_audit_package/bea_v1_n10ds_real_candidate_source_canary_audit_package_report.json`
