# BEA-v1-N10CK Default-Off Adapter Smoke for Winning Hybrid

Date: 2026-06-29

BEA-v1-N10CK is an implementation smoke for the winning hybrid `short75_225_top3_all_pm200` using the existing default-off eval-only span-window adapter path. It is not runtime/default promotion and does not hook existing validated evaluators.

## Result

```text
status: winning_hybrid_adapter_smoke_pass_n10cl_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
winning hybrid: short75_225_top3_all_pm200
top10/top20 span overlap: 25 / 31
cost10/cost20: 3300 / 6300
lost short75/225 hits: 0
file-hit top10 count: 34
candidate pool/order changed: false
N10CL authorized: true
```

## Adapter semantics

N10CK uses the default-off eval-only adapter/helper path. For each evidence item in the existing order:

- short original span (`<=10` lines): expand before `75`, after `225`;
- top3 evidence positions: apply all-span pm200 (`200 / 200`) regardless of span length;
- if both apply, the wider top3 pm200 window is used;
- otherwise no expansion.

Gold is used only after projection for evaluation. Candidate pool and order are unchanged.

## Boundary

N10CK does not modify runtime/default behavior, does not hook existing validated evaluators, does not run retrieval/reruns/OpenLocus, does not generate/add/remove/reorder candidates, does not tune adaptively, and does not make heldout/generalization, method-winner, or downstream-value claims.

## Handoff

N10CK authorizes only `BEA-v1-N10CL Winning Hybrid Adapter Smoke Package`, a public audit/package with no additional private reads.

## Artifact

- Script: `eval/bea_v1_n10ck_default_off_adapter_winning_hybrid_smoke.py`
- Report: `artifacts/bea_v1_n10ck_default_off_adapter_winning_hybrid_smoke/bea_v1_n10ck_default_off_adapter_winning_hybrid_smoke_report.json`
