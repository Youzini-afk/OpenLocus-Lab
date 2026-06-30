# BEA-v1-N10EG Novel-First / Guarded Complementarity Slicing

Date: 2026-06-30

BEA-v1-N10EG slices the N10EF trade-off over the same scoped rows. It reads the same N10DZ top100 rows and N1 rows, but does not run new retrieval, candidate generation, runtime/default changes, or selector/reranker logic.

## Result

```text
status: novel_first_guard_complementarity_slicing_complete_n10eh_authorized
self-test: 5 / 5
forbidden scan: pass
baseline top10: 5
full novel-first top10: 11
guarded top5 novel-distinct top10: 10
full/guard union top10: 13
intersection: 8
full-only: 3
guard-only: 2
```

## Interpretation

This is the key finding: full novel-first and guarded top5 novel-distinct are not strict substitutes. Full novel-first is the best single rule, but guarded top5 recovers 2 top10 cases that full novel-first misses. Their union is 13, higher than either rule alone.

That means the next useful experiment is not another package. It is a fixed full/guard combination test: can a gold-free combination recover more of the union without adding candidates or retrieval?

## Handoff

N10EG authorizes only N10EH: fixed full/guard combination repacking over the same scoped rows. It does not authorize new/scaled retrieval, runtime/default, selector/reranker, method-winner, downstream, or heldout/generalization claims.

## Artifact

- Script: `eval/bea_v1_n10eg_novel_first_guard_complementarity_slicing.py`
- Report: `artifacts/bea_v1_n10eg_novel_first_guard_complementarity_slicing/bea_v1_n10eg_novel_first_guard_complementarity_slicing_report.json`
