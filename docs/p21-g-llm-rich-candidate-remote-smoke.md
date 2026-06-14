# P21-G3L Remote LLM Rich Candidate Smoke

P21-G3L gives LLMs constrained candidate snippets from P21-G2E, then tests filter, abstain, and span-narrow roles. Model output remains candidate-only and is not Evidence.

## Run Set

- runs: `8`
- ok_runs: `6`
- degraded_runs: `2`
- llm_models: `[mk]DeepSeek-V4-Flash, [mk]DeepSeek-V4-Pro, [mk]GLM-5.1, [mk]Kimi-K2.7-Code`
- embedding_model: `Qwen/Qwen3-Embedding-4B`
- repos: `js_express, py_flask`

## Aggregate Results

| Strategy | SpanF0.5 avg | FileRecall@5 avg | PFP avg | Gold | False | ΔSpan vs candidate |
|---|---:|---:|---:|---:|---:|---:|
| candidate_baseline | 0.233477 | 0.85 | 0.0 | 76 | 107 | None |
| llm_abstain_filter | 0.186517 | 0.6625 | 0.0 | 54 | 34 | -0.046959 |
| llm_filter | 0.186517 | 0.6625 | 0.0 | 54 | 34 | -0.046959 |
| llm_span_narrow | 0.269258 | 0.6625 | 0.0 | 58 | 30 | 0.035782 |

## Per-Model Summary

### [mk]DeepSeek-V4-Flash

- provider_statuses: `{'ok': 2}`
- schema_error_count: `0`
- latency_ms_p50_avg: `854`

| Strategy | SpanF0.5 avg | Gold | False | ΔSpan vs candidate |
|---|---:|---:|---:|---:|
| candidate_baseline | 0.232851 | 19 | 27 | None |
| llm_filter | 0.221853 | 16 | 10 | -0.010998 |
| llm_span_narrow | 0.297787 | 17 | 9 | 0.064936 |
| llm_abstain_filter | 0.221853 | 16 | 10 | -0.010998 |

### [mk]DeepSeek-V4-Pro

- provider_statuses: `{'ok': 2}`
- schema_error_count: `0`
- latency_ms_p50_avg: `1130.5`

| Strategy | SpanF0.5 avg | Gold | False | ΔSpan vs candidate |
|---|---:|---:|---:|---:|
| candidate_baseline | 0.235352 | 19 | 26 | None |
| llm_filter | 0.213765 | 15 | 9 | -0.021587 |
| llm_span_narrow | 0.227122 | 16 | 8 | -0.00823 |
| llm_abstain_filter | 0.213765 | 15 | 9 | -0.021587 |

### [mk]GLM-5.1

- provider_statuses: `{'degraded': 2}`
- schema_error_count: `7`
- latency_ms_p50_avg: `8590`

| Strategy | SpanF0.5 avg | Gold | False | ΔSpan vs candidate |
|---|---:|---:|---:|---:|
| candidate_baseline | 0.232851 | 19 | 27 | None |
| llm_filter | 0.098012 | 8 | 5 | -0.134839 |
| llm_span_narrow | 0.266859 | 9 | 4 | 0.034007 |
| llm_abstain_filter | 0.098012 | 8 | 5 | -0.134839 |

### [mk]Kimi-K2.7-Code

- provider_statuses: `{'ok': 2}`
- schema_error_count: `0`
- latency_ms_p50_avg: `4426`

| Strategy | SpanF0.5 avg | Gold | False | ΔSpan vs candidate |
|---|---:|---:|---:|---:|
| candidate_baseline | 0.232851 | 19 | 27 | None |
| llm_filter | 0.212439 | 15 | 10 | -0.020412 |
| llm_span_narrow | 0.285265 | 16 | 9 | 0.052413 |
| llm_abstain_filter | 0.212439 | 15 | 10 | -0.020412 |

## Per-Repo Summary

| Repo | Candidate baseline | LLM filter | LLM span-narrow | LLM abstain |
|---|---:|---:|---:|---:|
| js_express | 0.218173 | 0.165202 | 0.224705 | 0.165202 |
| py_flask | 0.24878 | 0.207833 | 0.313811 | 0.207833 |

## Conclusion

- `llm_span_narrow` has the best average role signal, but the effect is repo/model-specific.
- `llm_filter` / `llm_abstain_filter` reduce false spans but often remove gold; they need better prompt/bucket routing before default use.
- GLM-5.1 had schema degradation; it needs prompt/schema repair before more budget.
- No LLM role is promotion-ready; keep candidate-only and EvidenceCore-bound.

## Run IDs

- `27485036627` — `[mk]DeepSeek-V4-Flash` on `js_express` status `ok`
- `27485036003` — `[mk]DeepSeek-V4-Flash` on `py_flask` status `ok`
- `27485040450` — `[mk]DeepSeek-V4-Pro` on `js_express` status `ok`
- `27485039701` — `[mk]DeepSeek-V4-Pro` on `py_flask` status `ok`
- `27485039008` — `[mk]GLM-5.1` on `js_express` status `degraded`
- `27485038396` — `[mk]GLM-5.1` on `py_flask` status `degraded`
- `27485037821` — `[mk]Kimi-K2.7-Code` on `js_express` status `ok`
- `27485037172` — `[mk]Kimi-K2.7-Code` on `py_flask` status `ok`
