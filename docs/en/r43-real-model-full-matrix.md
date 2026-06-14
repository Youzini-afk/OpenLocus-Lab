# R43 Consolidated Real-Model Readiness Matrix

R43 consolidates R30-R42 offline, diagnostic, and provider-smoke artifacts. It does not claim a completed full real-provider quality matrix, rerun unavailable providers, or emit fake quality numbers.

| Strategy | Source | Role | Status |
|---|---|---|---|
| r29_rrf | R30 baseline freeze | current_best_recall_channel | ok |
| r29_query_noise_plus_rrf_agree_min | R30 baseline freeze | current_best_guard_candidate | ok |
| r29_symbol | R30 baseline freeze | current_best_precision_anchor | ok |
| dense_view_ast_header | R32 view bakeoff | dense candidate/supporting-only | ok |
| dense_view_comment_docstring | R32 view bakeoff | dense candidate/supporting-only | ok |
| dense_view_config_key_plus_context | R32 view bakeoff | dense candidate/supporting-only | ok |
| dense_view_mixed_all_views | R32 view bakeoff | dense candidate/supporting-only | ok |
| dense_view_path_plus_symbol | R32 view bakeoff | dense candidate/supporting-only | ok |
| dense_view_raw_code_trimmed | R32 view bakeoff | dense candidate/supporting-only | ok |
| dense_view_route_plus_handler_signature | R32 view bakeoff | dense candidate/supporting-only | ok |
| dense_view_signature_only | R32 view bakeoff | dense candidate/supporting-only | ok |
| dense_view_signature_plus_doc | R32 view bakeoff | dense candidate/supporting-only | ok |
| dense_view_test_name_plus_assert_terms | R32 view bakeoff | dense candidate/supporting-only | ok |
| quiver_readiness_bq_diag | R33 BQ diagnostics | diagnostic_only | ok |
| quiver_diag_bq_topk_f32_rerank__generated_excluded__anchor_global | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_bq_topk_f32_rerank__generated_excluded__anchor_regex | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_bq_topk_f32_rerank__generated_excluded__anchor_regex_or_symbol | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_bq_topk_f32_rerank__generated_excluded__anchor_symbol | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_bq_topk_f32_rerank__global_mixed_all__anchor_global | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_bq_topk_f32_rerank__global_mixed_all__anchor_regex | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_bq_topk_f32_rerank__global_mixed_all__anchor_regex_or_symbol | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_bq_topk_f32_rerank__global_mixed_all__anchor_symbol | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_bq_topk_f32_rerank__per_language__anchor_global | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_bq_topk_f32_rerank__per_language__anchor_regex | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_bq_topk_f32_rerank__per_language__anchor_regex_or_symbol | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_bq_topk_f32_rerank__per_language__anchor_symbol | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_bq_topk_f32_rerank__per_view__anchor_global | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_bq_topk_f32_rerank__per_view__anchor_regex | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_bq_topk_f32_rerank__per_view__anchor_regex_or_symbol | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_bq_topk_f32_rerank__per_view__anchor_symbol | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_bq_topk_f32_rerank__per_view_plus_language__anchor_global | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_bq_topk_f32_rerank__per_view_plus_language__anchor_regex | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_bq_topk_f32_rerank__per_view_plus_language__anchor_regex_or_symbol | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_bq_topk_f32_rerank__per_view_plus_language__anchor_symbol | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_bq_topk_f32_rerank__source_vs_test_split__anchor_global | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_bq_topk_f32_rerank__source_vs_test_split__anchor_regex | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_bq_topk_f32_rerank__source_vs_test_split__anchor_regex_or_symbol | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_bq_topk_f32_rerank__source_vs_test_split__anchor_symbol | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_flat_f32__generated_excluded__anchor_global | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_flat_f32__generated_excluded__anchor_regex | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_flat_f32__generated_excluded__anchor_regex_or_symbol | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_flat_f32__generated_excluded__anchor_symbol | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_flat_f32__global_mixed_all__anchor_global | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_flat_f32__global_mixed_all__anchor_regex | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_flat_f32__global_mixed_all__anchor_regex_or_symbol | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_flat_f32__global_mixed_all__anchor_symbol | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_flat_f32__per_language__anchor_global | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_flat_f32__per_language__anchor_regex | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_flat_f32__per_language__anchor_regex_or_symbol | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_flat_f32__per_language__anchor_symbol | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_flat_f32__per_view__anchor_global | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_flat_f32__per_view__anchor_regex | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_flat_f32__per_view__anchor_regex_or_symbol | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_flat_f32__per_view__anchor_symbol | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_flat_f32__per_view_plus_language__anchor_global | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_flat_f32__per_view_plus_language__anchor_regex | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_flat_f32__per_view_plus_language__anchor_regex_or_symbol | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_flat_f32__per_view_plus_language__anchor_symbol | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_flat_f32__source_vs_test_split__anchor_global | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_flat_f32__source_vs_test_split__anchor_regex | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_flat_f32__source_vs_test_split__anchor_regex_or_symbol | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| quiver_diag_flat_f32__source_vs_test_split__anchor_symbol | R34-R36 diagnostic prototype | candidate/supporting-only | ok |
| llm_derived_views | R37 derived views | derived-only not evidence | ok |
| r38_failure_discovery_stress | R38 stress expansion | failure_discovery_only not promotion | ok |
| symbol_new | R39 symbol repair | precision-anchor repair candidate | ok |
| regex_hybrid_normalized | R40 regex repair | query normalization candidate | ok |
| graph_supporting_only | R41 graph role research | supporting_or_explainer_only | ok |
| admission_v2_rules | R42 admission rules | explainable research only | ok |

## Required Future Work

- run real embeddings on CI corpus
- run R38 failure-discovery stress in non-promotion mode
- add CORE-Bench/ContextBench compatibility sample
