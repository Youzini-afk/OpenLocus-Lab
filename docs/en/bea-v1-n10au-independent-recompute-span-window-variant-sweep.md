# BEA-v1-N10AU Independent Recompute Exploratory Span-Window Variant Sweep

Date: 2026-06-29

BEA-v1-N10AU independently recomputes the full 15-variant N10AS exploratory span-window grid over the same scoped private N1 span rows. It reads the N10AS/N10AT public artifacts only for expected aggregate comparison and reads exactly the scoped private span-row source for recompute. It does not import or call the N10AS evaluator.

## Result

```text
status: independent_recompute_span_window_variant_sweep_pass_n10av_authorized
self-test: 14 / 14
forbidden scan: pass
private span rows read: 213
variants recomputed: 15
all N10AS aggregate metrics matched: true
frontier tiers matched: true
N10AS evaluator imported: false
N10AS evaluator called: false
N10AV authorized: true
```

## Matched frontier tiers

N10AU confirms the N10AS/N10AT frontier tiers exactly:

| Tier | Variant | top10/top20 | Cost proxy |
| --- | --- | --- | --- |
| low-cost frontier | `pm30` | 18 / 22 | 600 (`low`) |
| balanced frontier | `before25_after75` | 20 / 24 | 1000 (`medium`) |
| balanced frontier | `pm75` | 21 / 25 | 1500 (`medium`) |
| max-recall frontier | `pm200` | 25 / 30 | 4000 (`very_high`) |

All 15 variant aggregates match N10AS. Candidate pool/order changed counts remain zero, no rank/order arm sweep was performed, and no per-record adaptive windows or gold-based window selection were used.

## Claim boundary

N10AU is still same-source exploratory N1 span-surface proxy evidence only. It is not heldout validation, not N2-equivalent validation, not runtime/default behavior, not a method-winner claim, and not downstream-value evidence.

## Handoff

N10AU authorizes only `BEA-v1-N10AV Exploratory Span-Window Variant Sweep Replication Package`, a public replication/audit package. It does not authorize private reads, extra sweeps, new variants, heldout validation claims, runtime/default changes, retrieval/rerun, candidate generation, adaptive tuning, selector/reranker execution, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10au_independent_recompute_span_window_variant_sweep.py`
- Report: `artifacts/bea_v1_n10au_independent_recompute_span_window_variant_sweep/bea_v1_n10au_independent_recompute_span_window_variant_sweep_report.json`
