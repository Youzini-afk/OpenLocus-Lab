# P21-G3L-R GLM Structured Output Smoke

> 中文译本待补充。The full Chinese translation is pending.
> 这是同名文件的占位符：保留英文原文，方便未来翻译对照。

## English source / 英文原文

# P21-G3L-R GLM Structured Output Smoke

This study compares provider-level structured output modes for `[mk]GLM-5.1` on the same constrained P21-G3L candidate packs. Outputs remain candidate-only and are not Evidence.

## Run Set

- runs: `8`
- llm_model: `[mk]GLM-5.1`
- embedding_model: `Qwen/Qwen3-Embedding-4B`
- repos: `js_express, py_flask`
- modes: `prompt_only, json_object, json_schema_strict, tool_call`

## By Output Mode

| Mode | Schema error rate | Repairs | Repair success | SpanNarrow Δ avg | SpanNarrow SpanF0.5 avg | Filter SpanF0.5 avg | p50 latency avg | Fallback events |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| prompt_only | 0.8 | 0 | None | -0.232851 | 0.0 | 0.0 | 9192 | 16 |
| json_object | 0.55 | 0 | None | -0.120318 | 0.112533 | 0.05185 | 5761 | 11 |
| json_schema_strict | 0.35 | 0 | None | -0.007218 | 0.226321 | 0.098012 | 7875.5 | 7 |
| tool_call | 0.3 | 5 | 0.6 | 0.067713 | 0.300565 | 0.152382 | 5500 | 9 |

## Per Repo / Mode

| Repo | Mode | Status | Schema errors | Repairs | SpanNarrow Δ | SpanNarrow SpanF0.5 | Actual modes |
|---|---|---|---:|---:|---:|---:|---|
| js_express | prompt_only | degraded | 8 | 0/0 | -0.2181734317343173 | 0.0 | `['prompt_only']` |
| js_express | json_object | degraded | 6 | 0/0 | -0.14999161355249913 | 0.06818181818181818 | `['json_object']` |
| js_express | json_schema_strict | degraded | 2 | 0/0 | 0.14877904447099777 | 0.36832740213523135 | `['json_schema_strict']` |
| js_express | tool_call | degraded | 4 | 3/1 | 0.03843576366798157 | 0.2566091954022989 | `['tool_call']` |
| py_flask | prompt_only | degraded | 8 | 0/0 | -0.2475294867708001 | 0.0 | `['prompt_only']` |
| py_flask | json_object | degraded | 5 | 0/0 | -0.09064510901263598 | 0.15688437775816413 | `['json_object']` |
| py_flask | json_schema_strict | degraded | 5 | 0/0 | -0.1632143056478217 | 0.08431518112297842 | `['json_schema_strict']` |
| py_flask | tool_call | degraded | 2 | 2/2 | 0.0969912117350239 | 0.344520698505824 | `['tool_call']` |

## Conclusion

- `tool_call` is the preferred GLM structured-output mode for the next rerun: best average span-narrow delta and successful schema repair behavior.
- `prompt_only` should be blocked for GLM in P21-G3L.
- `json_object` is insufficient for GLM in this provider setup.
- `json_schema_strict` is mixed: better schema stability than json_object, but repo-dependent quality.
- Some errors are `provider_http_429`; rerun tool_call with lower concurrency before finalizing GLM capability.
- No strategy is promotion-ready or default-ready.

## Run IDs

- `27486264487` — `json_object` on `js_express` status `degraded` errors `6`
- `27486263720` — `json_object` on `py_flask` status `degraded` errors `5`
- `27486265801` — `json_schema_strict` on `js_express` status `degraded` errors `2`
- `27486265157` — `json_schema_strict` on `py_flask` status `degraded` errors `5`
- `27486263046` — `prompt_only` on `js_express` status `degraded` errors `8`
- `27486262392` — `prompt_only` on `py_flask` status `degraded` errors `8`
- `27486267106` — `tool_call` on `js_express` status `degraded` errors `4`
- `27486266480` — `tool_call` on `py_flask` status `degraded` errors `2`


## Low-Concurrency Tool Call Rerun

After the 4-mode comparison showed `tool_call` as the best GLM output mode but included provider HTTP 429 events, two `tool_call` runs were repeated sequentially.

| Repo | Run | Schema errors | Repairs | 429 errors | Candidate SpanF0.5 | SpanNarrow SpanF0.5 | SpanNarrow Δ |
|---|---:|---:|---:|---:|---:|---:|---:|
| py_flask | 27486409148 | 1 | 2/1 | 0 | 0.25253018003954625 | 0.330024030274233 | 0.07749385023468675 |
| js_express | 27486473166 | 1 | 2/1 | 0 | 0.21954835766423358 | 0.4142346304193319 | 0.1946862727550983 |

Aggregate:

- schema_error_rate: `0.1`
- schema_repair_success_rate: `0.5`
- rate_limit_error_count: `0`
- llm_span_narrow avg ΔSpanF0.5: `0.13609`

Conclusion: low-concurrency `tool_call` removes the observed 429 noise and strengthens GLM span-narrow signal. Use `tool_call` for GLM in the next bucketed P21-G3L run, but keep all LLM outputs candidate-only and non-default.

