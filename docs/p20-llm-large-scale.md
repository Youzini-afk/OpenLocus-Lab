# P20-LLM Large-Scale Eval Harness

P20-LS is an eval-only harness for LLM-derived query aliases and stress-label generation. It does not modify EvidenceCore or the Rust core. Default mode is offline deterministic; remote LLM access is opt-in only.

## Safety summary

- schema_version: `p20-llm-large-report-v1`
- promotion_ready: `False`
- llm_default_allowed: `False`
- llm_direct_evidence_allowed: `False`
- remote_enabled: `False`
- run_phase_public_only: `True`
- raw_prompt_response_stored: `False`

## LS0 safety gates

- actual_alias_artifact_validated: `True`
- alias_not_evidence_coverage: `True`
- alias_schema_issues: []
- alias_schema_version_coverage: `True`
- artifact_raw_source_hits: `0`
- artifact_secret_scan_clean: `True`
- artifact_secret_scan_hits: `0`
- default_should_change: `False`
- evidencecore_semantics_changed: `False`
- llm_outputs_not_evidence_labels_judge_router_default_promotion: `True`
- ls0_passed: `True`
- private_labels_not_uploaded: `True`
- promotion_ready: `False`
- public_task_schema_clean: `True`
- public_task_schema_issues: []
- raw_prompt_response_stored: `False`
- raw_source_sent: `False`
- remote_explicit_gate_enabled: `False`
- run_phase_public_only: `True`

## LS1 alias retrieval matrix

LLM aliases are candidate/supporting-only and not promotion evidence. A quality failure does not change defaults.

- alias_count: `8`
- ls1_safety_passed: `True`
- ls1_quality_passed: `False`
- alias_help_rate: `0.0`
- alias_harm_rate: `0.46875`
- fabricated_identifier_rate: `1.0`
- quality_blocking_reasons: `['primary_false_positive_delta_increased', 'fabricated_identifier_rate_gt_0.5', 'alias_harm_rate_gt_help_rate', 'alias_added_false_span_gt_gold_span']`
- provider_calls: `0`
- provider_cost_estimate: `0.0`

| strategy | FileRecall@1 | SpanF0.5 | PFP | no_gold_nonempty |
|---|---:|---:|---:|---:|
| regex_original | 0.0 | 0.0 | 0.375 | 0.375 |
| bm25_original | 0.0 | 0.0 | 0.375 | 0.375 |
| rrf_original | 0.0 | 0.0 | 0.375 | 0.375 |
| query_noise_guard | 0.0 | 0.0 | 0.375 | 0.375 |
| regex_llm_aliases | 0.0 | 0.0 | 1.0 | 1.0 |
| bm25_llm_aliases | 0.0 | 0.0 | 1.0 | 1.0 |
| rrf_llm_aliases | 0.0 | 0.0 | 1.0 | 1.0 |
| query_noise_guard_plus_llm_aliases_supporting | 0.0 | 0.0 | 0.375 | 0.375 |

## LS3 stress split

- stress_task_count: `8`
- stress_label_count: `8`
- private_labels_written: `False`
- private_labels_not_uploaded: `True`

| failure cluster | count |
|---|---:|
| DENSE_DOC_SOURCE_CONFUSION | 1 |
| DENSE_FILE_RIGHT_SPAN_WRONG | 1 |
| DENSE_FRONTEND_BACKEND_CONFUSION | 1 |
| DENSE_MODULE_RIGHT_FUNCTION_WRONG | 1 |
| DENSE_SAME_NAME_SYMBOL_CONFUSION | 1 |
| DENSE_TEST_SOURCE_CONFUSION | 1 |
| GUARD_RECALL_KILL | 1 |
| RRF_INHERITED_BM25_FALSE_POSITIVE | 1 |
