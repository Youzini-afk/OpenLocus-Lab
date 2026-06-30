# BEA-v1-N10DO Candidate-Pool Absence Path-Normalization Correction

Date: 2026-06-30

BEA-v1-N10DO is a direct mechanism audit over the same scoped N1 span rows. During primary review it found that exact normalized-path equality undercounted file reach; suffix-safe file matching is now the primary file identity rule for file-reach analysis. It does not run retrieval, rerun OpenLocus, generate/materialize/add/remove candidates, insert oracle candidates, run selector/reranker logic, or change runtime/default behavior.

## Result

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

- Exact matching reproduces the prior historical count: top10 file hit/miss `34/179`, top20 hit `44`, reachable rank11-50 `18`, and absent-from-observed-pool `161`.
- Suffix-safe matching supersedes it for file-reach analysis: top10 file hit/miss `44/169`, top20 hit `58`, reachable rank11-50 `28`, and absent-from-observed-pool `141`.
- Because N10DL/N10DM used exact matching, source-acquisition conclusions must wait until N10DM-R reruns the fixed deep-rank smoke under suffix-safe matching.
- Source/channel, retrieval method, score, language/repo/task, and query/category fields are incomplete or unavailable for policy use in the current public-safe surface.

## Boundary

Gold/file identity is used only for after-the-fact bucketed absence categorization. Public outputs are aggregate/bucket-only and do not include paths, file names, snippets, spans/lines, gold labels, candidate lists, exact ranks, or raw rows.

## Handoff

N10DO authorizes only `BEA-v1-N10DM-R Corrected Suffix-Safe Deep-Rank Promotion Smoke`. It does not authorize N10DP, retrieval, rerun, candidate generation/materialization/add/remove, or oracle insertion.

## Artifact

- Script: `eval/bea_v1_n10do_candidate_pool_absence_source_acquisition_audit.py`
- Report: `artifacts/bea_v1_n10do_candidate_pool_absence_source_acquisition_audit/bea_v1_n10do_candidate_pool_absence_source_acquisition_audit_report.json`
