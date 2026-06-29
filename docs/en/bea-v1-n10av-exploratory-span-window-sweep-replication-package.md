# BEA-v1-N10AV Exploratory Span-Window Variant Sweep Replication Package

Date: 2026-06-29

BEA-v1-N10AV is a public-only replication package consolidating N10AS, N10AT, and N10AU. It reads only public artifacts. It does not read private rows, recompute variants, run extra sweeps, introduce new variants, tune adaptively, run retrieval/reruns/OpenLocus, generate candidates, or make runtime/default, heldout/generalization, N2-equivalent, method-winner, or downstream-value claims.

## Result

```text
status: exploratory_span_window_sweep_replication_package_complete_n10aw_authorized
self-test: 14 / 14
forbidden scan: pass
private reads: 0
variant recomputes: 0
N10AS -> N10AT -> N10AU chain complete: true
N10AU all 15 aggregate matches: true
```

## Frontier package

| Tier | Variant | top10/top20 | Cost proxy |
| --- | --- | --- | --- |
| low-cost frontier | `pm30` | 18 / 22 | 600 (`low`) |
| balanced frontier | `before25_after75` | 20 / 24 | 1000 (`medium`) |
| balanced frontier | `pm75` | 21 / 25 | 1500 (`medium`) |
| max-recall frontier | `pm200` | 25 / 30 | 4000 (`very_high`) |

The package records only the scoped same-source exploratory frontier. It does not convert the frontier into a runtime/default recommendation or a method/downstream claim.

## Next research options

N10AV lists concrete non-immediate options: cost-sensitive window mechanism decomposition, default-off adapter variants over selected frontier points, or broader/heldout replay only if new source authorization or data exists. The only authorized next step is `BEA-v1-N10AW Exploratory Span-Window Follow-Up Selection Audit`, a mechanism/cost-focused follow-up selection audit.

## Artifact

- Script: `eval/bea_v1_n10av_exploratory_span_window_sweep_replication_package.py`
- Report: `artifacts/bea_v1_n10av_exploratory_span_window_sweep_replication_package/bea_v1_n10av_exploratory_span_window_sweep_replication_package_report.json`
