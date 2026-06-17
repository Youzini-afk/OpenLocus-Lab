# B1C Cross-Model Rich Candidate Rerun

> 中文译本待补充。本文件先保留英文原文，避免内容丢失。

## English source / 英文原文

# B1C Cross-Model Rich Candidate Rerun

Date: 2026-06-17

B1C reruns the B1 live rich-candidate experiment after updating the active LLM roster. The goal is model breadth, not promotion: compare the current reference model against a 27B dense Qwen coverage point and the updated GLM profile on the same bounded public matrix.

B1C is a live quality experiment. It sends bounded public candidate snippets through the existing P21 rich-candidate harness. It does not admit Evidence, change defaults, or change EvidenceCore.

## Matrix

```text
repos: py_flask, js_express, go_gin, rust_ripgrep
dataset: ci_smoke
tasks per repo: 6
task_sample_mode: round_robin_public_buckets
pack_layout: topk_plain_v0
```

Models and output modes:

```text
[mk]Kimi-K2.7-Code: tool_call
[mk]Qwen3.6-27B: tool_call, json_schema_strict
[mk]GLM-5.2: tool_call, json_schema_strict
```

Run IDs:

| Model / mode | py_flask | js_express | go_gin | rust_ripgrep |
| --- | ---: | ---: | ---: | ---: |
| Kimi tool_call | 27679315379 | 27679316883 | 27679318221 | 27679319591 |
| Qwen tool_call | 27679321065 | 27679322323 | 27679323715 | 27679325182 |
| GLM tool_call | 27679326330 | 27679327829 | 27679329334 | 27679330585 |
| Qwen json_schema_strict | 27679882877 | 27679884241 | 27679886001 | 27679887698 |
| GLM json_schema_strict | 27679889143 | 27679890671 | 27679892076 | 27679893465 |

All 20 workflow runs completed successfully and passed artifact privacy gates.

## Aggregate results

| Run | Calls | Schema valid | Fallbacks | Schema errors | Input chars | Packed candidates | Mean latency p50 ms | span_narrow gold | span_narrow false | span_narrow false/gold | span_narrow mean SpanF0.5 | span_narrow mean PFP | filter gold | filter false |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Kimi tool_call | 24 | 24 | 0 | 0 | 31,506 | 44 | 1,961.2 | 9 | 5 | 0.556 | 0.2825 | 0.0625 | 7 | 7 |
| Qwen tool_call | 16 | 16 | 8 | 8 | 31,011 | 43 | 3,005.5 | 2 | 1 | 0.500 | 0.0482 | 0.0000 | 2 | 1 |
| GLM tool_call | 13 | 13 | 11 | 11 | 31,580 | 44 | 2,166.0 | 0 | 0 | n/a | 0.0000 | 0.0000 | 0 | 0 |
| Qwen json_schema_strict | 15 | 15 | 9 | 9 | 30,893 | 43 | 43,478.0 | 0 | 0 | n/a | 0.0000 | 0.0000 | 0 | 0 |
| GLM json_schema_strict | 24 | 23 | 1 | 1 | 30,922 | 43 | 2,575.2 | 7 | 7 | 1.000 | 0.2192 | 0.0625 | 5 | 9 |

Observed fallback/error modes:

```text
Qwen tool_call: rate_limit_exceeded=15, unknown=2
Qwen json_schema_strict: rate_limit_exceeded=7, unknown=2
GLM tool_call: bad_response_status_code=9, unknown=2
GLM json_schema_strict: no aggregate error counts; only one fallback/schema error
```

## Interpretation

Kimi-K2.7-Code in tool-call mode remains the reference: full schema stability, zero fallback, low latency, 9 added gold, 5 added false, and mean SpanF0.5 0.2825.

GLM-5.2 materially improves under `json_schema_strict`: 23/24 schema-valid calls, 7 added gold, 7 added false, and mean SpanF0.5 0.2192. It is viable for controlled cross-family comparison, but remains behind Kimi and more false-heavy.

Qwen3.6-27B broadens model-type coverage, but this run is not quality-interpretable because both output modes hit substantial rate-limit/fallback noise. Its low false count mostly reflects fallback/abstention, not strong conversion. Qwen should be rerun only with lower concurrency, smaller per-run task counts, or provider-specific rate-limit handling before any quality conclusion.

## Practical conclusion

```text
Kimi tool_call:
  primary Breakthrough Sprint reference.

GLM-5.2 json_schema_strict:
  secondary cross-family validation / ablation model.

GLM-5.2 tool_call:
  not suitable as default due bad_response_status_code noise.

Qwen3.6-27B:
  keep as 27B dense model coverage, but treat this run as plumbing/rate-limit evidence.
```

The next B3 request-more-context quality experiment should use Kimi tool_call as the main model and optionally GLM-5.2 json_schema_strict as a secondary check. Qwen should not be on the critical path until rate-limit handling is repaired.
