# R37-R38 LLM-Derived Views and Stress Expansion

> 中文译本待补充。The full Chinese translation is pending.
> 这是同名文件的占位符：保留英文原文，方便未来翻译对照。

## English source / 英文原文

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

- provider: `offline_deterministic`
- llm_status: `not_requested`
- remote_calls: `0`
- derived_view_count: `20`
- stress_public_task_count: `32`
- stress_private_label_count: `32`

## Derived Kinds

- chunk_role: `1`
- config_role: `2`
- query_aliases: `8`
- route_intent: `1`
- symbol_tags: `6`
- test_intent: `2`

## Stress Categories

- ambiguous_vague: `4`
- dense_quiver_specific_trap: `4`
- frontend_backend_confusion: `4`
- hard_distractor: `4`
- misspell_noise_variant: `4`
- proper_name_api_config_regression: `4`
- semantic_trap: `4`
- test_source_confusion: `4`

## Decision

- LLM-derived views are not Evidence.
- R38 stress labels are failure-discovery only and not promotion evidence.
- No default strategy changes.

