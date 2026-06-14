# R37-R38 LLM-Derived Views and Stress Expansion

> 中文译本待补充。The full Chinese translation is pending.
> 这是同名文件的占位符：保留英文原文，方便未来翻译对照。

## English source / 英文原文

# R37-R38 LLM-Derived Views and Stress Expansion

This phase introduces derived-view and stress-expansion artifacts. The committed run performed one real LLM safe status/schema call, then generated derived/stress artifacts with deterministic, failure-discovery-only rules. Real LLM output remains derived/stress-only and is not Evidence, not labels, and not a citation verdict.

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
- stress_public_task_count: `24`
- stress_private_label_count: `24`

## Derived Kinds

- chunk_role: `1`
- config_role: `2`
- query_aliases: `8`
- route_intent: `1`
- symbol_tags: `6`
- test_intent: `2`

## Stress Categories

- ambiguous_vague: `3`
- dense_quiver_specific_trap: `3`
- frontend_backend_confusion: `3`
- hard_distractor: `3`
- misspell_noise_variant: `3`
- proper_name_api_config_regression: `3`
- semantic_trap: `3`
- test_source_confusion: `3`

## Decision

- LLM-derived views are not Evidence.
- R38 stress labels are failure-discovery only and not promotion evidence.
- No default strategy changes.

