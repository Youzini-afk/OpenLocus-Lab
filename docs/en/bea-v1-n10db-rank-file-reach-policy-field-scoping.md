# BEA-v1-N10DB Rank/File-Reach Policy Field Scoping

Date: 2026-06-30

BEA-v1-N10DB is a short empirical scoping phase for rank/file-reach policy fields. It inspects only the same scoped N1 span rows and public N10DA/N10CZ/N10T/N10X artifacts. It does not execute a rank/file policy, compute policy outcomes, add/remove/reorder candidates, run retrieval/reruns/OpenLocus, use selector/reranker logic, enter P5/BEA-v1-A, or change runtime/default behavior.

## Result

```text
status: rank_file_reach_policy_field_scoping_pass_n10dc_authorized
self-test: 15 / 15
forbidden scan: pass
private span rows read: 213
policy outcome computations: 0
selected policy family: file_dedup_distinct_file_packing
N10DC authorized: true
```

## Field scoping findings

- `p4_evidence` is present as an ordered evidence list on the 213 scoped rows.
- Candidate file identifiers are present privately and are usable as a gold-free policy input, but no paths or filenames are serialized publicly.
- Span boundary fields are present for future evaluation context, but no spans or line values are public.
- Score/method/channel/source fields are not available as complete candidate-level policy fields in this row surface, so source/channel interleave and score/method ordering are not recommended for N10DC.
- Candidate pool length is sufficient for rank/file reach scoping: 176 rows have at least 20 evidence items.
- Gold fields are available for future evaluation only; they are not used for policy selection or outcome computation in N10DB.

## Duplicate pressure

Duplicate-file pressure is material in the existing top-k lists:

| Bucket | Top10 rows | Top20 rows |
| --- | ---: | ---: |
| none | 44 | 25 |
| low | 67 | 24 |
| medium | 69 | 40 |
| high | 33 | 124 |

This supports selecting `file_dedup_distinct_file_packing` for the next scoped smoke.

## Handoff

N10DB authorizes only `BEA-v1-N10DC Distinct-File Packing Rank/File-Reach Smoke`: same scoped rows, same candidate pool, gold-free file-dedup packing variants, no candidate generation, and public aggregate outputs only. Preview variants are `baseline_existing_order`, `distinct_file_top10_greedy`, `distinct_file_top20_greedy_then_top10`, `max_per_file_1_top10`, and `max_per_file_2_top10`; N10DB documents them but does not execute them.

N10DB does not authorize retrieval/rerun, candidate generation/materialization, selector/reranker execution, P5, BEA-v1-A, runtime/default changes, heldout/generalization claims, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10db_rank_file_reach_policy_field_scoping.py`
- Report: `artifacts/bea_v1_n10db_rank_file_reach_policy_field_scoping/bea_v1_n10db_rank_file_reach_policy_field_scoping_report.json`
