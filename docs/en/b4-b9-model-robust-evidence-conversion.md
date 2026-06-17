# B4/B9 Model-Robust Evidence Conversion

Date: 2026-06-17

This aggregate-only report separates ``algorithm_spec`` (model-independent strategy definitions) from ``model_adapter`` (model + output-mode health).  It re-encodes the live quality cells documented in B1, B1C, B2 and B3.

B4/B9 is not a gate, not a precondition-only stage, and does not change ``EvidenceCore``.  LLM outputs are still candidates, not Evidence.

## Algorithm spec vs model adapter

An **algorithm_spec** describes what the research harness does: pack layout, role (span_narrow, filter, policy), and routing rule.  It is intentionally independent of the model.

A **model_adapter** adds the actual model, output mode, and observed call health.  An adapter can be `quality_interpretable=true` (clean fallback profile, usable for quality averaging) or degraded (rate-limit, bad response) and therefore excluded from the quality aggregate.

## Model adapter health

| Adapter | Interpretable | Health | Notes |
| --- | --- | --- | --- |
| `glm_5_2_json_schema_strict` | yes | `secondary_cross_family_validation` | Viable for controlled cross-family comparison, but weaker than Kimi tool_call. |
| `glm_5_2_tool_call` | no | `degraded_bad_response` | Tool-call mode produced bad-response-status-code noise; not suitable for quality aggregate. |
| `kimi_k2_7_code_json_schema_strict` | yes | `healthy_but_slower_and_weaker` | Schema-stable but slower and leaves more false spans than tool_call. |
| `kimi_k2_7_code_tool_call` | yes | `healthy_primary_reference` | Primary Breakthrough Sprint reference: full schema stability, low fallback, strong span-narrow signal. |
| `qwen3_6_27b_json_schema_strict` | no | `degraded_rate_limit` | Severe rate-limit/fallback noise and very high latency; not quality-interpretable. |
| `qwen3_6_27b_tool_call` | no | `degraded_rate_limit` | Both Qwen output modes hit substantial rate-limit/fallback noise; do not include in quality aggregate until lower-concurrency fix. |

## Aggregate live quality cells

| Algorithm spec | Adapter | Role | Tasks | Gold | False | SpanF0.5 | PFP | Source |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `candidate_baseline_topk_plain_v0` | `kimi_k2_7_code_tool_call` | baseline | 24 | 8 | 43 | 0.1099 | 0.1250 | docs/en/b1-live-llm-rich-candidate-run.md |
| `span_narrow_topk_plain_v0` | `kimi_k2_7_code_tool_call` | span_narrow | 24 | 9 | 5 | 0.2849 | 0.0625 | docs/en/b1-live-llm-rich-candidate-run.md |
| `filter_topk_plain_v0` | `kimi_k2_7_code_tool_call` | filter | 24 | 7 | 7 | 0.1884 | 0.0625 | docs/en/b1-live-llm-rich-candidate-run.md |
| `p25_bucket_routed_v0_plain` | `kimi_k2_7_code_tool_call` | policy | 24 | 8 | 6 | 0.1139 | 0.0417 | docs/en/b1-live-llm-rich-candidate-run.md |
| `candidate_baseline_topk_plain_v0` | `kimi_k2_7_code_json_schema_strict` | baseline | 24 | 8 | 44 | 0.1099 | 0.1250 | docs/en/b1-live-llm-rich-candidate-run.md |
| `span_narrow_topk_plain_v0` | `kimi_k2_7_code_json_schema_strict` | span_narrow | 24 | 9 | 8 | 0.2829 | 0.1250 | docs/en/b1-live-llm-rich-candidate-run.md |
| `filter_topk_plain_v0` | `kimi_k2_7_code_json_schema_strict` | filter | 24 | 7 | 10 | 0.1884 | 0.1250 | docs/en/b1-live-llm-rich-candidate-run.md |
| `p25_bucket_routed_v0_plain` | `kimi_k2_7_code_json_schema_strict` | policy | 24 | 8 | 9 | 0.0914 | 0.0833 | docs/en/b1-live-llm-rich-candidate-run.md |
| `span_narrow_topk_plain_v0` | `qwen3_6_27b_tool_call` | span_narrow | 16 | 2 | 1 | 0.0482 | 0.0000 | docs/en/b1c-cross-model-rich-candidate-rerun.md |
| `filter_topk_plain_v0` | `qwen3_6_27b_tool_call` | filter | 16 | 2 | 1 | n/a | 0.0000 | docs/en/b1c-cross-model-rich-candidate-rerun.md |
| `span_narrow_topk_plain_v0` | `qwen3_6_27b_json_schema_strict` | span_narrow | 15 | 0 | 0 | 0.0000 | 0.0000 | docs/en/b1c-cross-model-rich-candidate-rerun.md |
| `filter_topk_plain_v0` | `qwen3_6_27b_json_schema_strict` | filter | 15 | 0 | 0 | n/a | 0.0000 | docs/en/b1c-cross-model-rich-candidate-rerun.md |
| `span_narrow_topk_plain_v0` | `glm_5_2_tool_call` | span_narrow | 13 | 0 | 0 | 0.0000 | 0.0000 | docs/en/b1c-cross-model-rich-candidate-rerun.md |
| `filter_topk_plain_v0` | `glm_5_2_tool_call` | filter | 13 | 0 | 0 | n/a | 0.0000 | docs/en/b1c-cross-model-rich-candidate-rerun.md |
| `span_narrow_topk_plain_v0` | `glm_5_2_json_schema_strict` | span_narrow | 24 | 7 | 7 | 0.2192 | 0.0625 | docs/en/b1c-cross-model-rich-candidate-rerun.md |
| `filter_topk_plain_v0` | `glm_5_2_json_schema_strict` | filter | 24 | 5 | 9 | n/a | 0.0625 | docs/en/b1c-cross-model-rich-candidate-rerun.md |
| `span_narrow_topk_plain_v0` | `kimi_k2_7_code_tool_call` | span_narrow | 24 | 9 | 6 | 0.2691 | 0.0625 | docs/en/b2-contrastive-pack-quality-experiment.md |
| `filter_topk_plain_v0` | `kimi_k2_7_code_tool_call` | filter | 24 | 7 | 8 | 0.1751 | 0.0625 | docs/en/b2-contrastive-pack-quality-experiment.md |
| `span_narrow_topk_scores_provenance_v0` | `kimi_k2_7_code_tool_call` | span_narrow | 24 | 9 | 7 | 0.2829 | 0.1250 | docs/en/b2-contrastive-pack-quality-experiment.md |
| `filter_topk_scores_provenance_v0` | `kimi_k2_7_code_tool_call` | filter | 24 | 7 | 9 | 0.1884 | 0.1250 | docs/en/b2-contrastive-pack-quality-experiment.md |
| `span_narrow_contrastive_competitor_v0` | `kimi_k2_7_code_tool_call` | span_narrow | 24 | 9 | 8 | 0.2694 | 0.1250 | docs/en/b2-contrastive-pack-quality-experiment.md |
| `filter_contrastive_competitor_v0` | `kimi_k2_7_code_tool_call` | filter | 24 | 7 | 10 | 0.1751 | 0.1250 | docs/en/b2-contrastive-pack-quality-experiment.md |
| `span_narrow_hard_distractor_contrast_v0` | `kimi_k2_7_code_tool_call` | span_narrow | 24 | 7 | 5 | 0.2820 | 0.1250 | docs/en/b2-contrastive-pack-quality-experiment.md |
| `filter_hard_distractor_contrast_v0` | `kimi_k2_7_code_tool_call` | filter | 24 | 5 | 7 | 0.1880 | 0.1250 | docs/en/b2-contrastive-pack-quality-experiment.md |
| `p25_bucket_routed_v0_plain` | `kimi_k2_7_code_tool_call` | policy | 12 | 8 | 7 | 0.0890 | 0.0417 | docs/en/b3-rmc-quality-experiment.md |
| `rmc_hybrid_v0` | `kimi_k2_7_code_tool_call` | policy | 12 | 7 | 8 | 0.0820 | 0.0833 | docs/en/b3-rmc-quality-experiment.md |
| `rmc_llm_pack_routed_v0` | `kimi_k2_7_code_tool_call` | policy | 12 | 7 | 8 | 0.0820 | 0.0833 | docs/en/b3-rmc-quality-experiment.md |
| `rmc_local_conservative_v0` | `kimi_k2_7_code_tool_call` | policy | 12 | 4 | 18 | 0.0226 | 0.0000 | docs/en/b3-rmc-quality-experiment.md |

## Model-averaged treatment effects

Effects are computed only over adapters marked `quality_interpretable`. The delta is mean SpanF0.5 of the algorithm spec minus the matching baseline for the same adapter.

| Algorithm spec | Adapters | Avg Δ SpanF0.5 | Effect | Leave-one-model | Variance |
| --- | ---: | ---: | --- | --- | --- |
| `span_narrow_topk_plain_v0` | 2 | 0.1740 | `low_n_directional_signal` / `low_n_directional_signal` | `leave_one_positive_low_n` | `low` |
| `filter_topk_plain_v0` | 2 | 0.0785 | `low_n_directional_signal` / `observed_only` | `leave_one_positive_low_n` | `low` |
| `p25_bucket_routed_v0_plain` | 2 | 0.0000 | `negative_or_flat` / `observed_only` | `leave_one_non_positive` | `low` |
| `span_narrow_topk_scores_provenance_v0` | 1 | 0.0138 | `low_n_fragile_signal` / `fragile_signal` | `insufficient_model_overlap` | `insufficient_model_overlap` |
| `filter_topk_scores_provenance_v0` | 1 | 0.0133 | `low_n_fragile_signal` / `fragile_signal` | `insufficient_model_overlap` | `insufficient_model_overlap` |
| `span_narrow_contrastive_competitor_v0` | 1 | 0.0003 | `low_n_fragile_signal` / `fragile_signal` | `insufficient_model_overlap` | `insufficient_model_overlap` |
| `filter_contrastive_competitor_v0` | 1 | 0.0000 | `single_adapter_caution` / `fragile_signal` | `insufficient_model_overlap` | `insufficient_model_overlap` |
| `span_narrow_hard_distractor_contrast_v0` | 1 | 0.0129 | `low_n_fragile_signal` / `not_supported` | `insufficient_model_overlap` | `insufficient_model_overlap` |
| `filter_hard_distractor_contrast_v0` | 1 | 0.0129 | `low_n_fragile_signal` / `not_supported` | `insufficient_model_overlap` | `insufficient_model_overlap` |
| `rmc_hybrid_v0` | 1 | -0.0070 | `single_adapter_caution` / `not_supported` | `insufficient_model_overlap` | `insufficient_model_overlap` |
| `rmc_llm_pack_routed_v0` | 1 | -0.0070 | `single_adapter_caution` / `not_supported` | `insufficient_model_overlap` | `insufficient_model_overlap` |
| `rmc_local_conservative_v0` | 1 | -0.0664 | `single_adapter_caution` / `not_supported` | `insufficient_model_overlap` | `insufficient_model_overlap` |

## Recommendations

| Algorithm / adapter | Claim | Recommendation |
| --- | --- | --- |
| `algorithm_spec::span_narrow_topk_plain_v0` | `low_n_directional_signal` | Positive on matched aggregate cells, but not general: verify on a broader public corpus and held-out models before any default change. |
| `algorithm_spec::span_narrow_hard_distractor_contrast_v0` | `not_supported` | Not globally supported as a span-narrow pack; route hard-distractor contrast only to selective filter/no-gold cases after repair. |
| `algorithm_spec::filter_hard_distractor_contrast_v0` | `not_supported` | Hard-distractor filter lost gold in this bounded sample; do not adopt globally without repair. |
| `algorithm_spec::span_narrow_topk_scores_provenance_v0` | `fragile_signal` | Fragile trade-off: higher SpanF0.5 but more false spans, higher PFP, and higher latency. Use selectively, not as default. |
| `algorithm_spec::rmc_hybrid_v0` | `not_supported` | Fixed RMC hybrid did not beat P25; needs interpretable policy search or narrower bucket-specific routing. |
| `algorithm_spec::rmc_llm_pack_routed_v0` | `not_supported` | Fixed RMC LLM routing did not beat P25; needs searched routing. |
| `algorithm_spec::rmc_local_conservative_v0` | `not_supported` | Local conservative route avoided false positives but collapsed recall. |
| `model_adapter::qwen3_6_27b_tool_call` | `not_supported` | Adapter degraded/rate-limit; exclude from quality aggregation until a lower-concurrency fix is validated. |
| `model_adapter::qwen3_6_27b_json_schema_strict` | `not_supported` | Adapter degraded/rate-limit; exclude from quality aggregation until a lower-concurrency fix is validated. |
| `model_adapter::glm_5_2_json_schema_strict` | `observed_only` | Usable as secondary cross-family validation; do not use as primary reference. |

## Safety notes

- Public artifact is aggregate-only; no task IDs, candidate IDs, paths, line ranges, digests, snippets, prompts, responses, or private labels.
- ``promotion_ready=false``, ``default_should_change=false``, ``evidencecore_semantics_changed=false``, ``llm_direct_evidence_allowed=false``.
- Repo variance is not available at this aggregate level; per-repo breakdowns remain in the source docs only.

