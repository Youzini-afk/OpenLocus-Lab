# BEA-v1-N10AT Exploratory Span-Window Variant Sweep Audit Package

Date: 2026-06-29

BEA-v1-N10AT is a public-only audit/package for the N10AS exploratory span-window variant sweep. It reads the public N10AS artifact only. It does not read private rows, recompute variants, perform extra sweeps, run retrieval/reruns/OpenLocus, generate candidates, tune windows adaptively, or make runtime/default, heldout, method-winner, or downstream-value claims.

## Result

```text
status: exploratory_span_window_variant_sweep_audit_package_complete_n10au_authorized
self-test: 13 / 13
forbidden scan: pass
private reads in N10AT: 0
variant recomputes in N10AT: 0
N10AU authorized: true
```

## Audited frontier tiers

N10AT confirms the public N10AS frontier tiers:

| Tier | Variant | top10/top20 | Cost proxy |
| --- | --- | --- | --- |
| low-cost frontier | `pm30` | 18 / 22 | 600 (`low`) |
| balanced frontier | `before25_after75` | 20 / 24 | 1000 (`medium`) |
| balanced frontier | `pm75` | 21 / 25 | 1500 (`medium`) |
| max-recall frontier | `pm200` | 25 / 30 | 4000 (`very_high`) |

The package preserves the N10AS interpretation: same-source N1 span-surface proxy only, not heldout, not N2-equivalent, not runtime/default, not a method winner, and not downstream-value evidence.

## Handoff

N10AT authorizes only `BEA-v1-N10AU Independent Recompute Exploratory Span-Window Variant Sweep` over the same scoped private rows and full fixed 15-variant grid. It does not authorize extra sweeps, new variants, heldout validation claims, runtime/default changes, retrieval/rerun, candidate generation, adaptive tuning, selector/reranker execution, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10at_exploratory_span_window_variant_sweep_audit_package.py`
- Report: `artifacts/bea_v1_n10at_exploratory_span_window_variant_sweep_audit_package/bea_v1_n10at_exploratory_span_window_variant_sweep_audit_package_report.json`
