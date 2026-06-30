# BEA-v1-N10DK N10T-Order Rank-Promotion Public Package

Date: 2026-06-30

BEA-v1-N10DK is a public-only package for the N10DJ N10T-order file-reach rank-promotion smoke. It reads public artifacts only and performs no private reads, no recompute, and no new rank-promotion variants.

## Result

```text
status: n10t_order_rank_promotion_public_package_complete_n10dl_authorized
self-test: 13 / 13
forbidden scan: pass
private reads in N10DK: 0
recomputes in N10DK: 0
N10DL authorized: true
```

## Packaged conclusions

- N10DJ completed with 8 fixed variants over the same N10T-best-order candidate list.
- Anchor file top10/top20 is `34 / 44`; anchor projected span top10/top20 is `30 / 36`.
- Naive deeper-rank promotion is harmful:
  - `promote_rank11_20_before_rank6_10`: file/span `24 / 44` and `22 / 36`.
  - `interleave_top10_with_rank11_20_1to1_after_top5`: file/span `29 / 44` and `26 / 36`.
  - `promote_rank21_50_after_top5_before_rank6_10`: file/span `23 / 30` and `22 / 27`.
- Distinct-fill rank11-50/rank11-100 and max-per-file-2 variants are neutral: `34 / 44` file and `30 / 36` projected span.

Interpretation: do not blindly promote fixed deeper bands. The next useful question is why correct files remain absent from the N10T top10 and which observable structure predicts safe promotion.

## Boundary

N10DK does not authorize runtime/default behavior, heldout/generalization claims, retrieval/rerun, candidate generation/materialization/add/remove, selector/reranker execution, P5, BEA-v1-A, method-winner claims, downstream-value claims, or broad private reads.

## Handoff

N10DK authorizes only `BEA-v1-N10DL N10T Top10 File-Reach Residual Analysis` over the same scoped rows under the next oracle contract.

## Artifact

- Script: `eval/bea_v1_n10dk_n10t_order_rank_promotion_public_package.py`
- Report: `artifacts/bea_v1_n10dk_n10t_order_rank_promotion_public_package/bea_v1_n10dk_n10t_order_rank_promotion_public_package_report.json`
