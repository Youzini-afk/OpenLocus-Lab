# R33 QuIVer Readiness

R33 measures BQ2 readiness for future QuIVer research. It does **not** implement QuIVer graph search and does **not** emit QuIVer quality numbers.

## Safety

- provider: `local_token_hash`
- provider_status: `ok`
- quiver_graph_implemented: `False`
- BQ_diagnostics_only: `True`
- quiver_quality_metrics_emitted: `False`
- promotion_ready: `False`
- default_should_change: `False`
- evidencecore_semantics_changed: `False`

## BQ Diagnostics

| Metric | Value |
|---|---:|
| BQ_overlap@10 | 0.5666666666666667 |
| BQ_overlap@50 | 1.0 |
| BQ_overlap@100 | 1.0 |
| BQ_vs_f32_MRR | 0.15132275132275133 |
| sign_entropy_mean | 0.043338776310816535 |
| sign_entropy_std | 0.1762111091099084 |
| angular_gap@10 | 0.2526450760875365 |
| angular_gap@50 | 0.3135031380325549 |
| query_corpus_centroid_angle | 0.4771721980972285 |
| language_shard_variance | 0.24736077154114083 |
| view_shard_variance | 0.2342472932467008 |
| effective_dimension_proxy | 22.58509171939 |

## Recommendation

- quiver_fit: `mixed`
- recommendation: `continue_diagnostics_then_proto`
- Next step remains R34 prototype only after diagnostics; unavailable graph search must stay reason-only.
