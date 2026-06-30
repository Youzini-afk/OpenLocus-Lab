# BEA-v1-N10DO Candidate-Pool Absence Path-Normalization Correction

日期：2026-06-30

BEA-v1-N10DO 是对 same scoped N1 span rows 的 direct mechanism audit。Primary review 发现 exact normalized-path equality 低估了 file reach；suffix-safe file matching 现在是 file-reach analysis 的主口径。它不运行 retrieval，不 rerun OpenLocus，不 generate/materialize/add/remove candidates，不插入 oracle candidates，不运行 selector/reranker，也不改变 runtime/default behavior。

## 结果

```text
status: candidate_pool_absence_path_normalization_correction_complete_n10dmr_authorized
self-test: 13 / 13
forbidden scan: pass
private span rows read: 213
primary file match rule: suffix_safe_path_match
suffix-safe top10 file hit / miss: 44 / 169
suffix-safe top20 file hit: 58
suffix-safe absent from observed pool: 141
suffix-safe reachable rank 11-50: 28
prior exact top10 hit / absent: 34 / 161
N10DM-R authorized: true
N10DP authorized: false
```

## Key findings

- Exact matching 复现旧的历史计数：top10 file hit/miss `34/179`、top20 hit `44`、reachable rank11-50 `18`、absent-from-observed-pool `161`。
- Suffix-safe matching 取代它成为 file-reach analysis 主口径：top10 file hit/miss `44/169`、top20 hit `58`、reachable rank11-50 `28`、absent-from-observed-pool `141`。
- 由于 N10DL/N10DM 使用 exact matching，source-acquisition conclusion 必须等 N10DM-R 按 suffix-safe matching 重跑 fixed deep-rank smoke 后再判断。
- source/channel、retrieval method、score、language/repo/task 与 query/category fields 在当前 public-safe surface 中对 policy use 来说 incomplete 或 unavailable。

## Boundary

Gold/file identity 只用于 after-the-fact bucketed absence categorization。Public outputs 仅为 aggregate/bucket，不包含 paths、file names、snippets、spans/lines、gold labels、candidate lists、exact ranks 或 raw rows。

## Handoff

N10DO 只授权 `BEA-v1-N10DM-R Corrected Suffix-Safe Deep-Rank Promotion Smoke`。它不授权 N10DP、retrieval、rerun、candidate generation/materialization/add/remove 或 oracle insertion。

## Artifact

- Script: `eval/bea_v1_n10do_candidate_pool_absence_source_acquisition_audit.py`
- Report: `artifacts/bea_v1_n10do_candidate_pool_absence_source_acquisition_audit/bea_v1_n10do_candidate_pool_absence_source_acquisition_audit_report.json`
