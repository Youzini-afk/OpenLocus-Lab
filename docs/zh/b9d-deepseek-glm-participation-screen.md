# B9D DeepSeek / GLM Participation Screen

> 中文译本待补充。本文件先保留英文原文，避免内容丢失。

## English source / 英文原文

# B9D DeepSeek / GLM Participation Screen

Date: 2026-06-18

B9D is a small adapter participation screen. It is not a model leaderboard and
does not rank output modes as algorithm variables. It answers one practical
question: which DeepSeek/GLM profiles are healthy enough to participate in later
OpenLocus algorithm experiments without making adapter noise the research topic?

## DeepSeek screen

```text
models: [mk]DeepSeek-V4-Flash, [mk]DeepSeek-V4-Pro
adapter modes: tool_call, json_schema_strict
repos: py_flask, js_express
stage: p21_llm_rich
dataset: ci_smoke
max_tasks: 6
task_sample_mode: round_robin_public_buckets
execution: sequential jobs
```

Run IDs:

| Adapter | py_flask | js_express |
| --- | ---: | ---: |
| DeepSeek-V4-Flash tool_call | 27747232993 | 27747356948 |
| DeepSeek-V4-Flash json_schema_strict | 27747484524 | 27747593323 |
| DeepSeek-V4-Pro tool_call | 27747734960 | 27747855440 |
| DeepSeek-V4-Pro json_schema_strict | 27748077321 | 27748278004 |

All eight workflow runs completed successfully.

## Aggregate readout

| Adapter | Calls | Schema valid | Infra failure | Span-narrow gold | Span-narrow false | PFP | Participation read |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Flash tool_call | 12 | 1.0 | 0.0 | 4 | 3 | 0.125 | healthy; more recall-oriented |
| Flash json_schema_strict | 12 | 1.0 | 0.0 | 4 | 3 | 0.125 | similar to Flash tool_call |
| Pro tool_call | 12 | 1.0 | 0.0 | 2 | 1 | 0.125 | healthy; more conservative |
| Pro json_schema_strict | 12 | 1.0 | 0.0 | 2 | 1 | 0.125 | similar to Pro tool_call |

DeepSeek did not show adapter-health problems in this small screen. Flash looks
more useful for recall-oriented exploration; Pro looks more conservative. The
two output modes were similar enough that the choice should stay in model/user
configuration rather than becoming an OpenLocus algorithm claim.

## GLM status

GLM-5.2 remains supported but noisy based on B9A and B6D:

```text
B9A GLM-5.2 tool_call:
  schema_valid_rate: 0.833
  infra_failure_rate: 0.500

B9A GLM-5.2 json_schema_strict:
  schema_valid_rate: 0.833
  infra_failure_rate: 0.333

B6D GLM-5.2 json_schema_strict:
  status: not_quality_interpretable
  schema_valid_rate: 0.75
  infra_failure_rate: 0.25
```

GLM can remain an opt-in exploratory adapter, but it should not be on the current
critical path until its adapter health is repaired.

## Recommendation

```text
DeepSeek-V4-Flash:
  allow future exploratory participation when recall/latency matters.

DeepSeek-V4-Pro:
  allow future exploratory participation as a conservative long-context profile.

GLM-5.2:
  supported but noisy; keep opt-in/exploratory, not critical path.

Qwen3.6-27B json_schema_strict:
  remains the current best secondary validation adapter from B9B/B9C.

Kimi-K2.7-Code tool_call:
  remains the primary reference adapter.
```

B9D intentionally stops at participation recommendations. The main research
should return to OpenLocus algorithm work: policy validation, context atom
ablation, local dense/QuIVer tie-breakers, and evidence conversion.
