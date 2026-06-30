# BEA-v1-N10DO-R Corrected Candidate-Pool Absence / Source Mechanism Audit

Date: 2026-06-30

BEA-v1-N10DO-R reruns the candidate-pool absence/source audit with suffix-safe file matching as the primary rule. It reads the same scoped N1 span rows and public N10DO/N10DM-R/N10DN-R/N10DL artifacts. It does not run retrieval, rerun OpenLocus, generate/materialize/add/remove candidates, insert oracle candidates, run selector/reranker logic, or change runtime/default behavior.

## Result

```text
status: corrected_candidate_pool_absence_source_audit_complete_n10dp_authorized
self-test: 12 / 12
forbidden scan: pass
private span rows read: 213
top10 file hit / miss: 44 / 169
top20 file hit: 58
rank11-20 reachable: 14
rank21-50 reachable: 14
absent from observed pool: 141
```

## Findings

- Suffix-safe matching is the primary file-reach rule.
- Of 169 top10 file misses, 141 have the gold file absent from the observed N1 pool.
- Same-pool movement can address only 28 misses in ranks 11-50.
- Source/channel, retrieval method, score, language/repo/task, and query/category fields are unavailable or incomplete for targeted policy use.

## Handoff

N10DO-R authorizes only `BEA-v1-N10DP Oracle Candidate-Insertion Ceiling Smoke`. N10DO-R itself does not authorize retrieval, rerun, candidate generation, materialization, oracle insertion, selector/reranker execution, runtime/default changes, P5, BEA-v1-A, method-winner claims, downstream-value claims, or heldout/generalization claims.

## Artifact

- Script: `eval/bea_v1_n10dor_corrected_candidate_pool_absence_source_audit.py`
- Report: `artifacts/bea_v1_n10dor_corrected_candidate_pool_absence_source_audit/bea_v1_n10dor_corrected_candidate_pool_absence_source_audit_report.json`
