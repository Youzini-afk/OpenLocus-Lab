# BEA-v1-N10DL N10T File-Reach Residual Mechanism Analysis

Date: 2026-06-30

BEA-v1-N10DL is a direct residual mechanism analysis, not a policy execution. It reads the same scoped N1 span rows and public N10DK/N10DJ/N10DA context. It does not run retrieval/rerun/OpenLocus, generate/materialize/add/remove candidates, reorder candidates, execute a new promotion policy, run selector/reranker logic, change runtime/default behavior, or make heldout/generalization, method-winner, or downstream claims.

## Result

```text
status: n10t_file_reach_residual_analysis_complete_n10dm_authorized
self-test: 15 / 15
forbidden scan: pass
private span rows read: 213
top10 file hit / miss: 34 / 179
top20 file hit: 44
policy execution count: 0
N10DM authorized: true
```

## Residual buckets

N10DL buckets the 179 top10 file misses by first gold-file rank and top10 duplicate pressure. Ten misses have first gold-file evidence in ranks 11-20, eight in ranks 21-50, and 161 are absent from the local candidate pool. The rank-by-duplicate-pressure cross-tab matters: the 18 rank-11-50 reachable residuals all sit in the no-duplicate-pressure bucket, while the medium/high duplicate-pressure residuals are absent-from-pool cases. Public output contains only aggregate/bucket counts: no paths, filenames, snippets, spans, lines, candidate lists, exact ranks, or gold labels.

## Signals

The public report records bucketed signals only:

- no-duplicate-pressure deep-rank probe signal;
- deep-rank retrieval-gap signal as context, not the recommended N10DM policy signal;
- pool-absence signal if present;
- no-safe-signal flag if no gold-free field signal exists.

N10DL explicitly does **not** recommend duplicate-pressure-conditioned promotion: duplicate pressure is present, but its medium/high cases correspond to absent-from-pool residuals rather than reachable rank-11-50 gold files. The plausible next mechanism is a narrow no-duplicate-pressure deep-rank probe using candidate rank position, private file identity, file repeat count, and span-length bucket availability. Source/channel, method, and score buckets are marked unavailable unless complete.

## Handoff

N10DL authorizes only `BEA-v1-N10DM Residual-Aware Rank/File Promotion Rule Smoke`: same scoped rows, fixed variants, no-duplicate-pressure/rank buckets allowed, no gold policy, no retrieval/rerun, no candidate generation, and public aggregate output only.

## Artifact

- Script: `eval/bea_v1_n10dl_n10t_file_reach_residual_analysis.py`
- Report: `artifacts/bea_v1_n10dl_n10t_file_reach_residual_analysis/bea_v1_n10dl_n10t_file_reach_residual_analysis_report.json`
