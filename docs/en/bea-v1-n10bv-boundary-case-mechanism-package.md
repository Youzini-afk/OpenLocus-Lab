# BEA-v1-N10BV Boundary Case Mechanism Package

Date: 2026-06-29

BEA-v1-N10BV is a public-only package for the N10BU one-case boundary mechanism decomposition. It reads public artifacts only and does not read private rows, recompute metrics, add variants, tune adaptively, run retrieval/reruns/OpenLocus, generate candidates, or make runtime/default, heldout/generalization, method-winner, or downstream-value claims.

## Result

```text
status: boundary_case_mechanism_package_complete_n10bw_authorized
self-test: 14 / 14
forbidden scan: pass
private reads in N10BV: 0
recomputes in N10BV: 0
N10BW authorized: true
```

## Packaged boundary-case facts

Fixed `25/75` cost75 vs cost80 comparison:

| Cost | top10/top20 | Lost plateau core | File-hit top10 count |
| ---: | ---: | ---: | ---: |
| 75 | 19 / 23 | 1 | 34 |
| 80 | 20 / 24 | 0 | 34 |

Transition counts: recovered-at-80/missed-at-75 `1`; reverse count `0`.

Boundary case mechanism: before_gold_gap `1`, after_gold_gap `0`, already_overlap `0`, other `0`, distance bucket `near_1_5`, file_hit_top10 `true`, just_outside_75_window `true`, recovered_at_80 `true`.

No exact lines, spans, paths, snippets, gold content, candidate lists, ranks, or private row identifiers are public.

## Handoff

N10BV authorizes only `BEA-v1-N10BW Adapter Operating-Point Smoke for cost80_before25_after75`: default-off eval-only adapter path, same scoped N1 span rows, fixed operating point only, and no runtime/default promotion or existing evaluator hook-in.

## Artifact

- Script: `eval/bea_v1_n10bv_boundary_case_mechanism_package.py`
- Report: `artifacts/bea_v1_n10bv_boundary_case_mechanism_package/bea_v1_n10bv_boundary_case_mechanism_package_report.json`
