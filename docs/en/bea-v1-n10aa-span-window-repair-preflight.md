# BEA-v1-N10AA Span-Window Repair Preflight

Date: 2026-06-29

BEA-v1-N10AA is a design/preflight phase for a fixed span-window repair smoke. It reads public N10Z/N10X/N10Y artifacts only. It performs no private reads, no span expansion evaluation, and no repair execution.

## Result

```text
status: span_window_repair_preflight_pass_n10ab_authorized
self-test: 14 / 14
forbidden scan: pass
file-hit/no-top10-span gap: 25
same-file before-gold bucket: 17
same-file after-gold bucket: 8
same-file/no-overlap dominates: true
variants: 3
primary variant: fixed_symmetric_span_expansion_pm50_lines
baseline N10X best-arm span top10: 9
N10AB threshold: pm50 top10 expanded span overlap >= 11
```

## Repair design for N10AB

- Primary variant: `fixed_symmetric_span_expansion_pm50_lines`.
- Optional sensitivity variants: `fixed_symmetric_span_expansion_pm20_lines` and `fixed_symmetric_span_expansion_pm100_lines`.
- Rule: for each evidence span in top 10 after the N10T best arm, expand symmetrically by the fixed window with the lower bound clamped to 1.
- No gold signal may choose the amount, shift toward gold, or alter the window.
- No content-aware adjustment, path changes, candidate addition/removal, candidate generation, retrieval, rerun, selector/reranker, or new-arm search.

## N10AB metric contract

Primary metric: `top10_expanded_span_overlap_count_pm50`. Baseline is the N10X best-arm top-10 span overlap count of 9. N10AB passes only if the pm50 top-10 expanded span overlap count is at least 11. Secondary metrics include top-20 expanded overlap, delta versus N10X, and expansion-overreach buckets. Public output must not include line numbers.

## Decision

N10AA authorizes only `BEA-v1-N10AB Fixed Span-Window Repair Smoke` over the same private span rows. N10AA itself authorizes no private read and no repair execution. Retrieval/reruns, OpenLocus execution, candidate generation/materialization, new-arm search, selector/reranker execution, P5, BEA-v1-A, counterfactuals, runtime/default promotion, method-winner claims, and downstream-value claims remain unauthorized.

## Artifact

- Script: `eval/bea_v1_n10aa_span_window_repair_preflight.py`
- Report: `artifacts/bea_v1_n10aa_span_window_repair_preflight/bea_v1_n10aa_span_window_repair_preflight_report.json`
