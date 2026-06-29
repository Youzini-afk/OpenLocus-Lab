# BEA-v1-N10CN Winning Hybrid Cost-Reduction Refinement Audit Package

Date: 2026-06-29

BEA-v1-N10CN is a public-only audit/package for the N10CM winning-hybrid cost-reduction refinement sweep. It reads public artifacts only and performs no private reads, no recompute, and no new variants.

## Result

```text
status: winning_hybrid_cost_refinement_package_complete_n10co_authorized
self-test: 14 / 14
forbidden scan: pass
private reads in N10CN: 0
recomputes in N10CN: 0
N10CO authorized: true
```

## Packaged facts

- Winning reference `short75_225_top3_all_pm200`: top10/top20 `25 / 31`, cost10/cost20 `3300 / 6300`.
- Refined result `short75_225_top2_all_pm200`: top10/top20 `25 / 31`, cost10/cost20 `3200 / 6200`, saving `100 / 100` vs the winning reference, with lost winning top10 hits `0`.
- `short75_225_top1_all_pm200`, `short75_225_top3_all_pm150`, and `short75_225_top3_all_pm175` drop to `24 / 30` with one lost winning top10 hit.
- N10CM found no `improves_winning` variants and one `preserves_winning_at_lower_cost` variant.
- Candidate pool/order remained unchanged.

## Boundary

N10CN packages a same-source N1 proxy result only. Policy inputs are observable span-length bucket and candidate-position bucket only; gold/outcome/direction/content/file identity are not policy inputs. N10CN does not authorize runtime/default enablement, existing evaluator hook-in, heldout/generalization, retrieval/rerun, candidate generation/add/remove/reorder, adaptive tuning, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Handoff

N10CN authorizes only `BEA-v1-N10CO Default-Off Adapter Smoke for Refined Hybrid short75_225_top2_all_pm200`.

## Artifact

- Script: `eval/bea_v1_n10cn_winning_hybrid_cost_refinement_audit_package.py`
- Report: `artifacts/bea_v1_n10cn_winning_hybrid_cost_refinement_audit_package/bea_v1_n10cn_winning_hybrid_cost_refinement_audit_package_report.json`
