# R34-R36 QuIVer Diagnostic Prototype and Anchor-Seeded Dense

This phase implements an offline diagnostic prototype: flat f32 search, BQ top-k + f32 rerank, sharding layouts, and anchor-seeded candidate-pool restriction. It does not implement Vamana/QuIVer graph search.

## Safety

- quiver_mode: `diagnostic_only`
- quiver_graph_implemented: `False`
- promotion_ready: `False`
- default_should_change: `False`
- evidencecore_semantics_changed: `False`
- run_phase_public_only: `True`
- labels_loaded_after_run: `True`
- quiver_default_allowed: `False`
- quiver_supporting_channel_allowed: `True`

## Best Net Strategies

| Strategy | SpanF0.5 | added_gold_span | added_false_span | semantic_trap_nonempty | default_expansion_blocked |
|---|---:|---:|---:|---:|---:|
| flat_f32__source_vs_test_split__anchor_regex | 0.3246753246753246 | 9 | 0 | 0 | False |
| bq_topk_f32_rerank__source_vs_test_split__anchor_regex | 0.3246753246753246 | 9 | 0 | 0 | False |
| flat_f32__source_vs_test_split__anchor_symbol | 0.3246753246753246 | 9 | 0 | 0 | False |
| bq_topk_f32_rerank__source_vs_test_split__anchor_symbol | 0.3246753246753246 | 9 | 0 | 0 | False |
| flat_f32__source_vs_test_split__anchor_regex_or_symbol | 0.3246753246753246 | 9 | 0 | 0 | False |

## Decision

- `quiver_mode=diagnostic_only`; no QuIVer graph quality numbers are claimed.
- Global/default expansion remains blocked.
- Anchor-seeded dense/QuIVer remains a research direction for R43, supporting-only.
