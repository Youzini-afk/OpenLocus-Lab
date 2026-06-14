# R37-R38 LLM-Derived Views and Stress Expansion

This phase introduces derived-view and stress-expansion artifacts. The committed run is offline deterministic; real LLM use is manual-only and remains derived/stress-only.

## Safety

- no_evidence_generation: `True`
- no_gold_label_authority: `True`
- no_citation_verdicts: `True`
- no_promotion_verdict: `True`
- derived_views_have_not_evidence: `True`
- stress_labels_not_promotion: `True`
- artifact_secret_scan_clean: `True`

## Counts

- provider: `openai-compatible`
- llm_status: `ok`
- remote_calls: `1`
- derived_view_count: `20`
- stress_public_task_count: `8`
- stress_private_label_count: `8`

## Derived Kinds

- chunk_role: `1`
- config_role: `2`
- query_aliases: `8`
- route_intent: `1`
- symbol_tags: `6`
- test_intent: `2`

## Stress Categories

- ambiguous_vague: `1`
- dense_quiver_specific_trap: `1`
- frontend_backend_confusion: `1`
- hard_distractor: `1`
- misspell_noise_variant: `1`
- proper_name_api_config_regression: `1`
- semantic_trap: `1`
- test_source_confusion: `1`

## Decision

- LLM-derived views are not Evidence.
- R38 stress labels are failure-discovery only and not promotion evidence.
- No default strategy changes.
