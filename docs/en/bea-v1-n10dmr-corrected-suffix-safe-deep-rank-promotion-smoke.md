# BEA-v1-N10DM-R Corrected Suffix-Safe Deep-Rank Promotion Smoke

Date: 2026-06-30

BEA-v1-N10DM-R reruns the no-duplicate-pressure deep-rank promotion smoke using suffix-safe file matching as the primary file-reach rule. It reads only the same scoped N1 private span rows and public N10DO/N10DM/N10DL artifacts. It does not run retrieval/rerun/OpenLocus, generate/add/remove candidates, run selector/reranker logic, or change runtime/default behavior.

## Result

```text
status: suffix_safe_deep_rank_promotion_smoke_complete_n10dnr_authorized
self-test: 12 / 12
forbidden scan: pass
private span rows read: 213
anchor file top10/top20: 44 / 58
anchor projected span top10/top20: 39 / 49
positive variants: 0
harmful variants: 5
old negative conclusion still holds: true
```

## Corrected counts

Suffix-safe matching increases the N10T anchor from the prior exact file counts `34 / 44` to `44 / 58`. Projected span counts under the same fixed projection are `39 / 49`.

All five no-duplicate-pressure deep-rank promotion variants remain harmful under suffix-safe matching. The best interleave variants reach file `40 / 58` and projected span `36 / 49`, still below the suffix-safe anchor.

## Boundary

This is still same-source analysis over the existing candidate pool. Candidate generation, materialization, addition, removal, retrieval, rerun, selector/reranker execution, runtime/default promotion, heldout/generalization claims, method-winner claims, and downstream-value claims remain unauthorized. Public outputs are aggregate/bucket-only.

## Handoff

N10DM-R authorizes only `BEA-v1-N10DN-R Corrected Deep-Rank Promotion Package`.

## Artifact

- Script: `eval/bea_v1_n10dmr_corrected_suffix_safe_deep_rank_promotion_smoke.py`
- Report: `artifacts/bea_v1_n10dmr_corrected_suffix_safe_deep_rank_promotion_smoke/bea_v1_n10dmr_corrected_suffix_safe_deep_rank_promotion_smoke_report.json`
