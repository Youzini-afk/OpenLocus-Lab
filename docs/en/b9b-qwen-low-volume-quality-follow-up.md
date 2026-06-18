# B9B Qwen Low-Volume Quality Follow-up

Date: 2026-06-18

B9B follows the B9A adapter-health screen for `[mk]Qwen3.6-27B`. B9A showed
that Qwen's `json_schema_strict` adapter could be health-stable under a small
sequential screen. B9B asks the next question: with the same cautious
low-volume setup, does Qwen produce quality-interpretable rich-candidate
span-narrow/filter signal?

This is not a model leaderboard and does not compare output modes as algorithm
variables. `json_schema_strict` is treated as the chosen Qwen model-adapter
configuration.

## Run matrix

```text
model: [mk]Qwen3.6-27B
adapter/output mode: json_schema_strict
stage: p21_llm_rich
dataset: ci_smoke
pack_layout: topk_plain_v0
task_sample_mode: round_robin_public_buckets
max_tasks: 6
execution: sequential workflow jobs, not parallel
```

Run IDs:

```text
py_flask:      27741089224
js_express:    27741221937
go_gin:        27741346694
rust_ripgrep:  27741457523
```

All four runs completed successfully and passed artifact privacy gates.

## Adapter health

```text
total_calls: 24
successful_calls: 24
schema_valid_calls: 24
schema_valid_rate: 1.0
fallback_used_count: 0
schema_error_count: 0
infra_failure_rate: 0.0
input_chars_total: 30,871
packed_candidates_total: 43
mean_latency_p50_ms: 3,730.5
```

B9B confirms B9A's health finding: Qwen3.6-27B is usable as a structured
bounded-candidate adapter under low-volume sequential `json_schema_strict` runs.

## Quality aggregate

| Strategy | Tasks | Added gold | Added false | False/gold | Mean SpanF0.5 | Mean PFP |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| candidate_baseline | 24 | 8 | 43 | 5.375 | 0.1099 | 0.1250 |
| llm_span_narrow | 24 | 7 | 4 | 0.571 | 0.2831 | 0.0625 |
| llm_filter | 24 | 5 | 6 | 1.200 | 0.1880 | 0.0625 |
| llm_abstain_filter | 24 | 5 | 6 | 1.200 | 0.1880 | 0.0625 |

The important signal is `llm_span_narrow`: it sharply reduced false spans and
matched the B1/B1C span-narrow quality band, though it recovered fewer gold spans
than Kimi on the same broad matrix.

## Interpretation

Qwen3.6-27B should no longer be treated only as plumbing/rate-limit evidence when
run with this adapter profile. Under low-volume sequential `json_schema_strict`,
it produced health-stable and quality-interpretable span-narrow results.

However, this remains a small, single-adapter follow-up:

```text
not a default model
not a promotion signal
not Evidence admission
not an output-mode leaderboard
not a replacement for Kimi reference runs
```

## Practical conclusion

```text
Qwen3.6-27B json_schema_strict:
  promote from plumbing-only to secondary quality-interpretable adapter candidate
  for low-volume sequential runs.

Critical path:
  keep Kimi tool_call as the primary reference for now.

Next validation:
  run frozen balanced-policy validation under Qwen json_schema_strict, with the
  same low-volume/sequential discipline, before calling it model-robust.
```
