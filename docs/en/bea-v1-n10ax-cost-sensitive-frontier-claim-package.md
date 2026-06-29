# BEA-v1-N10AX Cost-Sensitive Frontier Claim Package

Date: 2026-06-29

BEA-v1-N10AX is a public-only claim package for the N10AW cost-sensitive mechanism decomposition and the N10AV/N10AU/N10AS frontier evidence. It reads public artifacts only. It does not read private rows, recompute metrics, add variants, tune adaptively, run retrieval/reruns/OpenLocus, generate/materialize candidates, hook existing evaluators, or change runtime/default behavior.

## Result

```text
status: cost_sensitive_frontier_claim_package_complete_n10ay_authorized
self-test: 14 / 14
forbidden scan: pass
private reads: 0
recomputes: 0
new variants: 0
N10AY authorized: true
```

## Packaged frontier tiers

| Tier | top10/top20 span overlap | Cost bucket | Lost previous hits |
| --- | ---: | --- | ---: |
| baseline | 9 / 10 | zero | 0 |
| pm30 | 18 / 22 | low | 0 |
| before25_after75 | 20 / 24 | medium | 0 |
| pm75 | 21 / 25 | medium | 0 |
| pm200 | 25 / 30 | very_high | 0 |

## Packaged mechanism claim

The marginal gains remain before/after gold-window gap recovery:

- baseline -> pm30: +9, with 8 before-gold-gap and 1 after-gold-gap cases.
- pm30 -> before25_after75: +2, with 2 before-gold-gap cases.
- before25_after75 -> pm75: +1, with 1 after-gold-gap case.
- pm75 -> pm200: +4, with 3 before-gold-gap and 1 after-gold-gap cases.

N10AX therefore packages the N10AW interpretation: the pm200 max-recall tier is wider recovery of the same before/after miss pattern, not a qualitatively new pm200 mechanism.

## Claim boundary

Allowed claim: scoped same-source N1 span-surface proxy cost-sensitive frontier summary. Forbidden claims remain false: heldout/generalization, N2-equivalent validation, runtime/default promotion, method winner, downstream value, selector/reranker, P5/BEA-v1-A, retrieval/rerun, candidate generation, and adaptive tuning.

## Handoff

N10AX authorizes only `BEA-v1-N10AY Cost-Aware Adapter Frontier Smoke`: a direct empirical follow-up over the same scoped N1 rows using adapter/helper imports only. N10AX itself authorizes no runtime/default changes or broader claims.

## Artifact

- Script: `eval/bea_v1_n10ax_cost_sensitive_frontier_claim_package.py`
- Report: `artifacts/bea_v1_n10ax_cost_sensitive_frontier_claim_package/bea_v1_n10ax_cost_sensitive_frontier_claim_package_report.json`
