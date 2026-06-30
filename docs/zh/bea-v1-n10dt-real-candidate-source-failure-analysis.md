# BEA-v1-N10DT Real Candidate-Source Canary Failure Mechanism Analysis

日期：2026-06-30

BEA-v1-N10DT 是 N10DR bounded local candidate-source canary 的 analysis-only follow-up。它读取 existing private canary rows/log buckets 与 same scoped N1 span rows。它不运行 new retrieval、OpenLocus、network、clone、provider、candidate generation、selector/reranker 或 runtime/default changes。

## 结果

```text
status: real_candidate_source_failure_analysis_complete_n10du_authorized
self-test: 12 / 12
forbidden scan: pass
private canary rows read: 30
same scoped N1 rows read: 213
zero candidate cases: 8
command failed cases: 2
nonzero no-gold cases: 20
gold top50: 0
N10DU authorized: targeted small canary only
```

## Findings

- Candidate 与 original N1 pool 的 overlap 仅以 bucket 形式输出；public output 不包含 candidate lists 或 filenames。
- Nonzero-result cases 大多重复/重叠 existing pool；返回的 channel metadata 为 bm25-only，且 zero-candidate/failed cases 形成 reliability tail。主要解释是 `source_repeats_existing_pool_with_channel_skew_and_query_mismatch`。
- Query shape 与 channel metadata 只以 buckets 公开；raw queries 不公开。
- Targeted channel/query-shape small canary 有依据，但不应进行 scaled retrieval。

## Boundary

N10DT 是 analysis-only。它不授权 scaled retrieval、network access、git clone、provider calls、candidate generation/materialization、selector/reranker execution、runtime/default changes、P5、BEA-v1-A、method-winner claims、downstream-value claims、heldout/generalization claims 或 broad private reads。

## Handoff

N10DT 只授权 scoped constraints 下的 `BEA-v1-N10DU Targeted Candidate-Source Variant Canary`。

## Artifact

- Script: `eval/bea_v1_n10dt_real_candidate_source_failure_analysis.py`
- Report: `artifacts/bea_v1_n10dt_real_candidate_source_failure_analysis/bea_v1_n10dt_real_candidate_source_failure_analysis_report.json`
