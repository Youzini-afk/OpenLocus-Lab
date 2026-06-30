# BEA-v1-N10DR Real Candidate-Source Canary

日期：2026-06-30

BEA-v1-N10DR 是 bounded local candidate-source canary。它只针对 existing local clone repositories 运行 local OpenLocus CLI，使用 scoped N1 private span rows 和 deterministic 30-case absent-pool sample。它不进行 network access、git clone、provider call、selector/reranker execution、runtime/default change、P5 或 BEA-v1-A action。

## 结果

```text
status: real_candidate_source_canary_complete_no_recovery
self-test: 12 / 12
forbidden scan: pass
sampled cases: 30
executed cases: 30
local repos available: 30
retrieval command successes: 28
gold file recovered top10/top20/top50: 0 / 0 / 0
N10DS authorized: true
```

## Canary design

- Sample source：corrected suffix-safe absent-pool residuals。
- Target sample：10 个 tiny-pool、10 个 moderate-pool、10 个 rich-wrong-pool cases。
- Sampling：deterministic，按 stable private row order；不使用 random sampling。
- Retrieval command boundary：local OpenLocus CLI retrieval，channels 为 `regex,bm25,symbol`，max results `50`，JSON output，working directory 为 existing clone repository。
- Private outputs：写入 3 个 ignored project-private output files，用于 candidate rows、manifest 和 bucketed logs。

## Findings

- sampled cases 中没有任何 case 在 top50 returned candidates 中恢复 gold file。
- 按 pool richness 的恢复为：tiny `0/10`，moderate `0/10`，rich-wrong `0/10`。
- 这不改变 full-denominator anchor，也不证明 broader source failure；它只说明此 bounded local canary 没有发现恢复。

## Boundary

N10DR 是 local canary，不是 scaled retrieval result、method winner、downstream-value claim、heldout/generalization claim 或 runtime/default recommendation。Public outputs 只包含 aggregate/bucket records，不包含 private paths、filenames、candidate lists、snippets、spans/lines、gold labels、exact ranks 或 raw rows。

## Handoff

N10DR 只授权 `BEA-v1-N10DS Real Candidate-Source Canary Audit Package`。它不授权 scaled retrieval、network access、git clone、provider calls、candidate generation/materialization、selector/reranker execution、runtime/default changes、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10dr_real_candidate_source_canary.py`
- Report: `artifacts/bea_v1_n10dr_real_candidate_source_canary/bea_v1_n10dr_real_candidate_source_canary_report.json`
