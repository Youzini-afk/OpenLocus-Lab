# P20-LS: LLM Large-Scale Derived Retrieval Study

P20-LS is an eval-only harness for LLM-derived query aliases and stress-label generation. It does not modify EvidenceCore or the Rust core. Default mode is offline deterministic; remote LLM access is opt-in only.

## P20-LS-A remote verdict

Direct LLM query-alias expansion is **blocked** for `[mk]Kimi-K2.7-Code` and should not be scaled further in its current form.

The remote provider behaved well enough at the safety/schema boundary, but retrieval quality failed. Across 9 real CI corpus runs (`py_flask`, `js_express`, `go_gin`, `rust_ripgrep`, `py_httpx`, `go_cobra`, `js_axios`, `rust_mdbook`, plus a 60-task `py_flask` confirmation), every run passed LS0/LS1 safety and every run failed LS1 quality.

Key aggregate numbers:

- real CI provider calls: `220`
- real CI quality-passed runs: `0 / 9`
- real added gold spans: `289`
- real added false spans: `8312`
- false:gold span ratio: `28.76 : 1`
- average fabricated identifier rate: `0.459`
- max fabricated identifier rate: `0.620`
- max schema violation rate: `0.25`
- invalid JSON rate: `0.0`
- missing `not_evidence` rate: `0.0`
- private labels written/uploaded: `false`

Interpretation: the model can emit parseable, policy-compliant alias records, but direct aliases add far more false span surface than gold. The failure mode is semantic/existence grounding, not provider plumbing. Continue only with a separately named guarded variant, e.g. existence-filtered aliases or guard-supporting aliases that cannot admit primary by themselves.

Detailed run summary is stored in `artifacts/p20_llm_large/p20_ls_a_remote_summary.json`.

| run | calls | safety | quality | help | harm | gold span | false span | fabricated | blockers |
|---|---:|---|---|---:|---:|---:|---:|---:|---|
| self_test_3 | 3 | true | false | 0.0000 | 0.0000 | 0 | 0 | 0.786 | fabricated_identifier_rate_gt_0.5 |
| py_flask_20 | 20 | true | false | 0.0750 | 0.0250 | 19 | 470 | 0.393 | alias_added_false_span_gt_gold_span |
| js_express_20 | 20 | true | false | 0.0125 | 0.0000 | 24 | 838 | 0.565 | fabricated_identifier_rate_gt_0.5; alias_added_false_span_gt_gold_span |
| go_gin_20 | 20 | true | false | 0.0000 | 0.0125 | 54 | 1366 | 0.456 | alias_harm_rate_gt_help_rate; alias_added_false_span_gt_gold_span |
| rust_ripgrep_20 | 20 | true | false | 0.0000 | 0.0625 | 35 | 627 | 0.489 | alias_harm_rate_gt_help_rate; alias_added_false_span_gt_gold_span |
| py_httpx_20 | 20 | true | false | 0.0250 | 0.0625 | 20 | 656 | 0.576 | fabricated_identifier_rate_gt_0.5; alias_harm_rate_gt_help_rate; alias_added_false_span_gt_gold_span |
| go_cobra_20 | 20 | true | false | 0.0000 | 0.0250 | 35 | 1189 | 0.348 | alias_harm_rate_gt_help_rate; alias_added_false_span_gt_gold_span |
| js_axios_20 | 20 | true | false | 0.0000 | 0.0125 | 46 | 830 | 0.289 | alias_harm_rate_gt_help_rate; alias_added_false_span_gt_gold_span |
| rust_mdbook_20 | 20 | true | false | 0.0000 | 0.0625 | 31 | 639 | 0.397 | alias_harm_rate_gt_help_rate; alias_added_false_span_gt_gold_span |
| py_flask_60 | 60 | true | false | 0.0208 | 0.0833 | 25 | 1697 | 0.620 | primary_false_positive_delta_increased; fabricated_identifier_rate_gt_0.5; alias_harm_rate_gt_help_rate; alias_added_false_span_gt_gold_span |

## Safety summary

- schema_version: `p20-llm-large-report-v1`
- promotion_ready: `False`
- llm_default_allowed: `False`
- llm_direct_evidence_allowed: `False`
- remote_enabled: `False`
- run_phase_public_only: `True`
- raw_prompt_response_stored: `False`

These local/offline values below remain the committed baseline artifact from the harness bring-up. The remote P20-LS-A summary above supersedes them for the scale-up decision.

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
