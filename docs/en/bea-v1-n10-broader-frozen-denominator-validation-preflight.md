# BEA-v1-N10 Broader Frozen Denominator Validation Preflight

Date: 2026-06-29

BEA-v1-N10 is a preflight-only check for whether the recovered N6XFR-E/N8 fixed-pool result can be validated on a broader frozen denominator using already-existing N2-equivalent rank-pack rows. It reads public artifacts and only bucketed metadata for known recovered-private outputs. It does not read private content, compute new arm outcomes, rerun N6XFR-E/N8, run retrieval, rerun P4L/N1/N2/N3, execute OpenLocus, generate candidates, run selector/reranker logic, enter P5/BEA-v1-A, or promote runtime/default behavior.

## Result

```text
status: no_go_n10_broader_rank_pack_denominator_unavailable
self-test: 14 / 14
forbidden scan: pass
recovered result: 25 / 40 top-10, 34 / 40 top-20, 0 regressions
candidate denominators checked: 4
broader N2-equivalent rank-pack rows available: false
blocker: no_broader_n2_equivalent_rank_pack_rows
N11 authorized: false
```

## Candidate denominators

- `n2_recovered_40_rank_blocked`: exact recovered rank-pack fields are available, but this is the same 40-case denominator and is not broader.
- `p4l_locked_272`: broader context exists, but N2-equivalent rank-pack fields are not available from public artifacts or metadata-only checks.
- `n1_candidate_gold_trace_272`: broader trace context exists, but N2-equivalent rank-pack fields are not available from public artifacts or metadata-only checks.
- `n1_span_rows_213`: span context exists, but N2-equivalent rank-pack fields are not available from public artifacts or metadata-only checks.

## Decision

N10 is a No-Go because no broader N2-equivalent rank-pack row denominator exists under the current read-only preflight boundary. The next allowed phase is `none_until_broader_n2_equivalent_rank_pack_rows_exist`.

N10 does not authorize N11, private content reads, retrieval, reruns, candidate generation/materialization, selector/reranker execution, P5, BEA-v1-A, counterfactuals, runtime/default promotion, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10_broader_frozen_denominator_validation_preflight.py`
- Report: `artifacts/bea_v1_n10_broader_frozen_denominator_validation_preflight/bea_v1_n10_broader_frozen_denominator_validation_preflight_report.json`
