# P21-G3B Bucketed Rich LLM Role Smoke

> 中文译本待补充。The full Chinese translation is pending.
> 这是同名文件的占位符：保留英文原文，方便未来翻译对照。

## English source / 英文原文

# P21-G3B Bucketed Rich LLM Role Smoke

This study reruns rich LLM roles with public bucket sampling enabled. Public tasks expose only `task_bucket` and `task_risk_tags`; labels/gold remain private until scoring.

## Run Set

- runs: `6`
- repos: `js_express, py_flask`
- models: `[mk]DeepSeek-V4-Flash, [mk]GLM-5.1, [mk]Kimi-K2.7-Code`
- task_sample_mode: `round_robin_public_buckets`
- provider concurrency cap respected: `<=6`

## By Model

| Model | Statuses | Schema errors | Candidate Span | SpanNarrow Δ | Filter Δ | Filter PFP Δ |
|---|---|---:|---:|---:|---:|---:|
| [mk]DeepSeek-V4-Flash | `{'ok': 2}` | 0 | 0.149915 | -0.040145 | -0.046132 | -0.237374 |
| [mk]GLM-5.1 | `{'degraded': 1, 'ok': 1}` | 4 | 0.149915 | -0.034852 | -0.031122 | -0.191919 |
| [mk]Kimi-K2.7-Code | `{'ok': 2}` | 0 | 0.149915 | -0.065402 | -0.046132 | -0.237374 |

## By Repo

| Repo | Candidate Span | SpanNarrow Δ | Filter Δ | Filter PFP Δ |
|---|---:|---:|---:|---:|
| js_express | 0.126599 | -0.089653 | -0.092265 | -0.333333 |
| py_flask | 0.17323 | -0.003947 | 0.010007 | -0.111111 |

## Key Buckets

| Bucket | SpanNarrow Δ | Filter Δ | Filter PFP Δ |
|---|---:|---:|---:|
| expected_behavior:abstain | 0 | 0 | -0.208333 |
| expected_behavior:primary_evidence | 0.003137 | -0.040997 | 0 |
| expected_behavior:weak_candidates | 0 | 0 | -0.277778 |
| gold:has_gold | 0.003137 | -0.040997 | 0 |
| gold:no_gold | 0 | 0 | -0.222222 |
| oracle_type:deterministic | -0.067582 | -0.067747 | 0 |
| oracle_type:stress | 0 | 0 | -0.300595 |
| risk_tag:ambiguous | 0 | 0 | -0.277778 |
| risk_tag:dense_false_positive | 0 | 0 | -0.416667 |
| risk_tag:exact_symbol_match | -0.124839 | -0.146768 | 0 |
| risk_tag:frontend_backend_confusion | 0.105669 | 0 | 0 |
| risk_tag:hallucination_risk | 0 | 0 | 0 |
| risk_tag:quiver_not_implemented | 0 | 0 | -0.416667 |
| risk_tag:same_name_disambiguation | 0.017488 | 0 | 0 |
| risk_tag:same_name_symbol | 0.031701 | 0 | 0 |
| risk_tag:stale_index_confusion | 0 | 0 | -0.25 |
| risk_tag:stale_index_like | 0 | 0 | -0.25 |
| risk_tag:test_source_confusion | 0 | 0 | 0 |
| source_category:ambiguous | 0 | 0 | -0.277778 |
| source_category:dense_quiver_trap | 0 | 0 | -0.416667 |
| source_category:hard_distractor | 0.036005 | 0 | 0 |
| source_category:negative | 0 | 0 | 0 |
| source_category:positive | -0.124839 | -0.146768 | 0 |
| source_category:stale-like | 0 | 0 | -0.25 |

## Conclusion

- Bucketed sampling changed the interpretation: global span_narrow is not stable across mixed buckets.
- LLM roles reduced primary false positives, but often by killing gold spans.
- `span_narrow` should be routed to likely-positive/high-confidence candidate tasks, not all tasks.
- `filter`/`abstain` should be tested only on negative / dense_false_positive / ambiguous buckets.
- No role is promotion-ready or default-ready.

