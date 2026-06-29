# BEA-v1-N10R Targeted N2 Rank-Pack Row Generation Preflight

Date: 2026-06-29

BEA-v1-N10R is an actionable preflight for generating additional N2-equivalent rank-pack rows without a full P4L rerun. It may read scoped private N1/N2/P4L row schemas and counts and inspect the N2 builder code, but it does not execute OpenLocus, N2, P4L, retrieval, candidate generation, selector/reranker logic, P5, BEA-v1-A, or write generated private rows.

## Result

```text
status: no_go_n10r_target_denominator_insufficient
self-test: 15 / 15
forbidden scan: pass
known-good N2 rows: 40
N1 span rows: 213
N1 candidate/gold trace rows: 272
P4L private arm outcome rows: 1088
targeted N2 builder entrypoint identified: true
targeted denominator filter supported: false
can run without full P4L rerun: false
N10S authorized: false
```

## Findings

- The recovered N2 rank-pack rows are schema-valid and provide 40 known-good rows.
- N1/P4L private inputs provide broader row counts, but they are not already N2-equivalent rank-pack rows.
- Static inspection finds the N2 row builder helper and candidate-order semantics, but the available N2 CLI is a monolithic full locked-denominator reconstruction runner.
- No targeted denominator filter or targeted canary entrypoint is available in the existing builder.
- Therefore N10R cannot authorize N10S canary generation because there are no additional N2-equivalent rows to generate without changing the denominator definition.

## Decision

N10R closes as No-Go with blocker `n2_d2_filter_exhausted_full_denominator`. The next allowed phase is `none_for_n2_equivalent_broader_validation_without_new_denominator_definition`.

N10R does not materialize broader rows from N1 span evidence, write generated private rows, run OpenLocus/N2/P4L/retrieval, run selector/reranker logic, enter P5/BEA-v1-A, promote runtime/default policy, or make method-winner/downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10r_targeted_n2_rank_pack_generation_preflight.py`
- Report: `artifacts/bea_v1_n10r_targeted_n2_rank_pack_generation_preflight/bea_v1_n10r_targeted_n2_rank_pack_generation_preflight_report.json`
