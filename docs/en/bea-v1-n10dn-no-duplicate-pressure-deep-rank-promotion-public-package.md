# BEA-v1-N10DN No-Duplicate-Pressure Deep-Rank Promotion Public Package

Date: 2026-06-30

BEA-v1-N10DN is a public-only package/audit for N10DM. It reads committed public artifacts only. It performs no private reads, no recompute, no retrieval/rerun, no candidate generation/materialization/add/remove, no selector/reranker execution, and no runtime/default change.

## Result

```text
status: no_duplicate_pressure_deep_rank_promotion_public_package_complete_n10do_authorized
self-test: 13 / 13
forbidden scan: pass
private reads in N10DN: 0
recomputes in N10DN: 0
N10DO authorized: true
```

## Packaged N10DM facts

- N10T anchor file top10/top20: `34 / 44`.
- N10T projected span top10/top20: `30 / 36`.
- Six variants were evaluated in N10DM; five gated promotion variants activated only when top10 duplicate pressure was none.
- Positive variants: `0`.
- Harmful variants: `5`.
- Best non-anchor interleave variants fall to file `29 / 44` and projected span `26 / 36`.
- Direct promotion can recover up to `5` rank11-20 residuals, but loses up to `14` anchor file top10 hits and `10` anchor span top10 hits.

## Conclusion

The fixed deep-rank promotion line is closed unless a new observable signal appears. The negative result is useful: the reachable residuals are not enough to justify blind or duplicate-pressure-none gated deep-rank promotion, because anchor harm dominates recovered residuals.

## Handoff

N10DN authorizes only `BEA-v1-N10DO Candidate-Pool Absence Source Acquisition Mechanism Audit`, focused on the 161 absent-from-pool residuals. It does not authorize runtime/default, heldout/generalization, retrieval/rerun, candidate generation/materialization/add/remove, selector/reranker, P5, BEA-v1-A, adaptive tuning, method-winner claims, downstream-value claims, broad private reads, or further fixed deep-rank promotion.

## Artifact

- Script: `eval/bea_v1_n10dn_no_duplicate_pressure_deep_rank_promotion_public_package.py`
- Report: `artifacts/bea_v1_n10dn_no_duplicate_pressure_deep_rank_promotion_public_package/bea_v1_n10dn_no_duplicate_pressure_deep_rank_promotion_public_package_report.json`
