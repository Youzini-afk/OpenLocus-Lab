# R33 QuIVer Readiness

R33 measures BQ2 readiness for future QuIVer research. It does **not** implement QuIVer graph search and does **not** emit QuIVer quality numbers.

## Safety

- provider: `openai-compatible`
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
| BQ_overlap@10 | 1.0 |
| BQ_overlap@50 | 1.0 |
| BQ_overlap@100 | 1.0 |
| BQ_vs_f32_MRR | 0.6666666666666666 |
| sign_entropy_mean | 0.37186322919739884 |
| sign_entropy_std | 0.4297542815607398 |
| angular_gap@10 | 0.12836819247660844 |
| angular_gap@50 | 0.12836819247660844 |
| query_corpus_centroid_angle | 0.2480443402240376 |
| language_shard_variance | 0.14175235212047 |
| view_shard_variance | 0.0 |
| effective_dimension_proxy | 1445.9460927367115 |

## Recommendation

- quiver_fit: `mixed`
- recommendation: `continue_diagnostics_then_proto`
- Next step remains R34 prototype only after diagnostics; unavailable graph search must stay reason-only.
