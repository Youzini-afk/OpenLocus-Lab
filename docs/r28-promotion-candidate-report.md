# R28 Promotion Candidate Report

R28 is a conservative synthesis of R21/R23/R24/R25/R26 reports over the R20/R26 failure-surface datasets. It is **not** a promotion step. It exists to state what cannot yet be promoted and why.

```json
{
  "promotion_ready": false,
  "best_default_candidate": "no_change_current_evidence_gated_local_retrieval",
  "best_recall_channel": "rrf",
  "best_precision_anchor": "symbol",
  "best_dense_candidate": "none_available_for_default; dense_mock is safety/noise probe only",
  "quiver_recommendation": "hold",
  "graph_recommendation": "hold_default_expansion; graph may remain explicit/supporting only",
  "dense_recommendation": "supporting_only_after_real_embedding_bakeoff; mock dense rejected for quality",
  "default_should_change": false
}
```

## Direct answers

1. **Current default should change?** No. RRF is strongest recall, but false-primary risk remains high; guard strategies still have bucket regressions; graph/dense expansions are net-negative.
2. **If not, why?** The evidence base is failure-oriented rather than promotion-grade: R20 labels are weak/mined, R26 oracle types are deterministic/metamorphic/mined/stress, no human-verified promotion tier covers the new stress space, and R26 has no retrieval runner/scorer matrix yet.
3. **`query_noise_plus_rrf_agree_min` stable on auto-wide/auto-stress?** Not stable enough. R21 shows useful risk reduction without recall kill, but R23 finds bucket regressions across the entire sweep and R26 has not been run through a retrieval runner/scorer matrix yet.
4. **QuIVer/TDB independent quality gain?** No evidence. QuIVer is not implemented; TDB is not an ANN/search backend in default build.
5. **QuIVer/TDB gains by bucket?** Unknown; unavailable/not_measured.
6. **QuIVer/TDB risks by bucket?** Hypothesized dense semantic traps, proper-name/API/config regressions, and stale candidates; R26 now has stress data for future measurement.
7. **Graph adds gold more than noise?** No. R25 graph contribution: added_gold=0, added_false=435; default expansion blocked.
8. **Dense/QuIVer supporting channel only?** Yes. Dense mock is noisy and non-semantic; QuIVer is unavailable. Future dense/QuIVer must remain candidate/supporting until real bakeoff evidence exists.
9. **Coverage gaps?** See blocking gaps below.

## Key metrics

| Finding | Evidence |
|---|---|
| RRF recall | FileRecall@1=0.693, MRR=0.753, primary_false_positive_rate=0.495 |
| Symbol precision anchor | SpanPrecision=0.448, SpanF0.5=0.215, primary_false_positive_rate=0.167, abstain_rate=0.517 |
| Query-noise guard | FileRecall@1=0.693, primary_false_positive_rate=0.221, guard_recall_kill_rate=0.000 |
| R23 guard sweep | sweep_count=51, strategies_with_bucket_regression=51/51, total_bucket_regressions=6877 |
| Dense mock | candidates=5264, FileRecall@1=0.024, primary_false_positive_rate=0.878, token_waste=0.850 |
| Graph ablation | added_gold=0, added_false=435, blocked=True |
| Dense ablation | added_gold=2, added_false=20273, blocked=True |
| R26 stress coverage | tasks=1100, categories=10, safety_passed=True |

## Blocking evidence gaps

- R26 auto-stress has static validation only; no retrieval runner/scorer matrix yet.
- R20 labels are weak/mined and R26 oracle types are deterministic/metamorphic/mined/stress; neither is human-verified promotion evidence.
- R23 all 51 guard strategies have bucket regressions; guard generalization is blocked.
- QuIVer is not implemented, so no BQ/ANN compatibility or quality evidence exists.
- Dense real provider is unavailable; dense_mock is non-semantic and mostly noise.
- Graph depth=1 ablation adds more false spans than gold spans.
- No broad human-verified stress/negative benchmark for default policy decisions.

## Next required tests

- Run R26 auto-stress with R21/R24/R25 strategy matrix under runner/scorer separation.
- Add human-verified labels for high-impact R20/R26 failure buckets.
- Implement real embedding provider bakeoff only after R26 runner gates exist.
- If QuIVer is implemented, run per-view/per-language/per-repo sharded compatibility diagnostics before quality claims.
- Extend failure attribution to consume R24/R25/R26 artifacts, not only R21 artifacts.
- Add guard bucket regression gates to any candidate default policy.

## Safety and scope

- promotion_ready=false
- not_promotion_evidence=true
- core_changes=false
- remote_calls=0
- R28 source validation checks schema versions, promotion flags, safety gates, core_changes, remote_calls, dense_or_llm_claim flags where present, selected non-null key metrics, and R26 task count consistency before synthesis.
- Candidate remains candidate: no BM25/RRF/regex/symbol/graph/dense/TDB/QuIVer/LLM-derived output is treated as fact without EvidenceCore materialization.

