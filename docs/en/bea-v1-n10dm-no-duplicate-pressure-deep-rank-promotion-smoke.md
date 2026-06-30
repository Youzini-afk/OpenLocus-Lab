# BEA-v1-N10DM No-Duplicate-Pressure Deep-Rank Promotion Smoke

Date: 2026-06-30

BEA-v1-N10DM is a direct empirical same-source smoke over the scoped N1 span rows. It activates fixed deeper-rank promotion variants only when top10 duplicate pressure is absent; otherwise it leaves the N10T order unchanged. Gold is used only for scoring, never as a policy input.

## Result

```text
status: no_duplicate_pressure_deep_rank_promotion_smoke_complete_n10dn_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
variant count: 6
anchor file top10/top20: 34 / 44
anchor projected span top10/top20: 30 / 36
N10DN authorized: true
```

## Findings

The six fixed variants are completed, including the N10T anchor and five no-duplicate-pressure promotions. Public metrics report only aggregate/bucket counts: file reach, projected span reach, deltas against anchor, recovered reachable residuals, activation counts, and harm counts. Candidate pool membership is unchanged and candidate add/remove/materialization counts remain zero.

## Boundary

N10DM does not run retrieval/rerun/OpenLocus, does not generate/materialize/add/remove candidates, does not run selector/reranker logic, does not change runtime/default behavior, and does not make heldout/generalization, method-winner, or downstream claims. No private paths, filenames, exact ranks, spans, snippets, lines, candidate lists, or gold labels are public.

## Handoff

N10DM authorizes only `BEA-v1-N10DN No-Duplicate-Pressure Deep-Rank Promotion Public Package`.

## Artifact

- Script: `eval/bea_v1_n10dm_no_duplicate_pressure_deep_rank_promotion_smoke.py`
- Report: `artifacts/bea_v1_n10dm_no_duplicate_pressure_deep_rank_promotion_smoke/bea_v1_n10dm_no_duplicate_pressure_deep_rank_promotion_smoke_report.json`
