# R45 Promotion Candidate Report

R45 concludes the R30-R45 real-model readiness and diagnostic expansion pass. Full real-provider quality evidence is still pending, and default promotion remains blocked.

## Decision

- promotion_ready: `False`
- current_default_should_change: `False`
- best_recall_channel: `rrf`
- best_precision_anchor: `symbol`
- best_guard_candidate: `query_noise_plus_rrf_agree_min`
- dense_recommendation: `continue_harness_only_supporting_only`
- quiver_recommendation: `continue_diagnostics_only`
- llm_derived_recommendation: `continue_derived_only_supporting_only`
- graph_recommendation: `explainer_only`

## Blocking Buckets

- real embeddings not yet run on full R26/R20/R15 matrix
- QuIVer graph remains diagnostic_only; no Vamana/default backend
- LLM-derived views are offline/failure-discovery only, not evidence
- graph expansion remains blocked
- R39/R40 repairs need broad R26/R38 regression validation
- CORE-Bench/ContextBench compatibility not run

## Next Required Tests

- run R32 real embedding view bakeoff with path_plus_symbol then richer local-only views
- run R34-R36 on CI medium corpus with supporting-only outputs
- validate R39/R40 repair on R26 and R38 generated stress
- run R41/R42 admission rules on R26/R38 without changing defaults
- add CORE-Bench/ContextBench compatibility probe
