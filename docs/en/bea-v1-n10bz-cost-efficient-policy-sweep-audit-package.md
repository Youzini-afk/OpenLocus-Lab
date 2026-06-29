# BEA-v1-N10BZ Same-Source Cost-Efficient Policy Sweep Audit Package

Date: 2026-06-29

BEA-v1-N10BZ is a public-only audit/package for the N10BY same-source cost-efficient span-window policy sweep. It reads public artifacts only. It performs no private reads, no recompute, no extra sweeps, no new variants, no adaptive tuning, no retrieval/rerun/OpenLocus execution, no candidate generation, and no runtime/default promotion.

## Result

```text
status: cost_efficient_policy_sweep_package_complete_n10ca_authorized
self-test: 14 / 14
forbidden scan: pass
private reads in N10BZ: 0
recomputes in N10BZ: 0
N10CA authorized: true
```

## Packaged N10BY facts

- N10BY completed with 12 predeclared variants.
- Anchor `cost80_before20_after60`: top10/top20 `20 / 24`, top10 cost `800`, top20 cost `1600`.
- Lower-cost fixed 70/72/75/78 variants: all `19 / 23`, each with one lost anchor top10 hit.
- Rank-conditioned variants: all `19 / 20`, with lost anchor counts `1 / 1 / 2`.
- `top10_only_cost80_before20_after60`: `20 / 21`.
- `top5_only_cost80_before20_after60`: `12 / 13`.
- `top20_only_cost80_before20_after60`: `20 / 24`, but without relevant top10 cost reduction versus the anchor.
- Cost-reduction successes: `0`; recall-improvement successes: `0`; successful variants: `0`.

Conclusion: this fixed-window cost-efficient policy sweep found no improvement beyond the cost80 anchor. Cost80 appears to be the current fixed-window-family boundary on the same-source N1 rows. This is useful negative research, not a stop condition.

## Handoff

N10BZ authorizes only `BEA-v1-N10CA Next Mechanism Search Outside Fixed-Window Family`: a bounded next mechanism search, same-source empirical if possible. It does not authorize runtime/default promotion, heldout/generalization claims, retrieval/rerun, candidate generation, selector/reranker execution, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10bz_cost_efficient_policy_sweep_audit_package.py`
- Report: `artifacts/bea_v1_n10bz_cost_efficient_policy_sweep_audit_package/bea_v1_n10bz_cost_efficient_policy_sweep_audit_package_report.json`
