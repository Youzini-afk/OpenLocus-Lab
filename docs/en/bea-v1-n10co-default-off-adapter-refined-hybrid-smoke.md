# BEA-v1-N10CO Default-Off Adapter Smoke for Refined Hybrid

Date: 2026-06-29

BEA-v1-N10CO is an implementation smoke that uses the existing default-off eval-only adapter/helper path to reproduce the refined hybrid `short75_225_top2_all_pm200`. It is not runtime/default promotion and does not hook existing validated evaluators.

## Result

```text
status: refined_hybrid_adapter_smoke_pass_n10cp_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
refined hybrid: short75_225_top2_all_pm200
top10/top20 span overlap: 25 / 31
cost10/cost20: 3200 / 6200
lost winning top10 hits: 0
file-hit top10 count: 34
N10CP authorized: true
```

## Adapter smoke contract

- Short spans use before75/after225.
- Top2 positions override to all-span pm200 before200/after200 regardless of span length.
- Otherwise, spans are not expanded.
- Candidate pool/order is unchanged.
- Gold is used only for aggregate evaluation.

## Boundary

The adapter remains default-off: adapter default enabled `false`, private read by default `false`, runtime default enabled `false`, runtime config changed `false`, and policy default changed `false`. N10CO does not modify adapter/helper modules, does not hook existing evaluators, and does not run retrieval/rerun/OpenLocus, candidate generation/add/remove/reorder, adaptive tuning, selector/reranker, P5, BEA-v1-A, heldout/generalization claims, method-winner claims, or downstream-value claims.

## Handoff

N10CO authorizes only `BEA-v1-N10CP Refined Hybrid Adapter Smoke Package`, a public adapter-smoke package with no additional private reads or runtime/default changes.

## Artifact

- Script: `eval/bea_v1_n10co_default_off_adapter_refined_hybrid_smoke.py`
- Report: `artifacts/bea_v1_n10co_default_off_adapter_refined_hybrid_smoke/bea_v1_n10co_default_off_adapter_refined_hybrid_smoke_report.json`
