# P25 Bucket-Routed Policy Remote Smoke

> 中文译本待补充。The full Chinese translation is pending.
> 这是同名文件的占位符：保留英文原文，方便未来翻译对照。

## English source / 英文原文

# P25 Bucket-Routed Policy Remote Smoke

- Runs summarized: `6` success, `1` failed/retried-excluded
- Total tasks: `108`
- promotion_ready: `false`
- default_should_change: `false`

## Aggregate result

- Added false spans: baseline `108` -> bucket-routed `28`
- Added gold spans: baseline `24` -> bucket-routed `21`
- Mean PFP delta: `-0.0926`
- Mean SpanF0.5 delta: `0.0026`

## Interpretation

- Bucket-routed v0 is a strong false-primary reducer on this small smoke.
- It is also conservative: it loses some gold spans, especially on mixed JS buckets.
- It is not promotion-ready; it should feed P30 Admission V3 as a false-reduction component, not become a default policy.

## Per-run summary

| run | repo | model | mode | span_delta | pfp_delta | gold baseline->routed | false baseline->routed |
|---|---|---|---|---:|---:|---:|---:|
| 27494552238 | py_flask | `[mk]DeepSeek-V4-Flash` | `json_object` | 0.0146 | 0.0000 | 5->6 | 9->8 |
| 27494653491 | js_express | `[mk]DeepSeek-V4-Flash` | `json_object` | -0.0099 | -0.1667 | 3->2 | 27->4 |
| 27494553127 | py_flask | `[mk]Kimi-K2.7-Code` | `json_object` | 0.0424 | 0.0000 | 5->6 | 10->8 |
| 27494553537 | js_express | `[mk]Kimi-K2.7-Code` | `json_object` | -0.0116 | -0.1667 | 3->2 | 26->2 |
| 27494553963 | py_flask | `[mk]GLM-5.1` | `tool_call` | -0.0081 | -0.0556 | 5->3 | 10->4 |
| 27494554434 | js_express | `[mk]GLM-5.1` | `tool_call` | -0.0116 | -0.1667 | 3->2 | 26->2 |

## Safety notes

- The remote workflow uploaded only aggregate P25 policy metrics.
- Ephemeral per-task P25 records stayed in runner temp and were trap-deleted.
- Raw queries, snippets, prompts, responses, gold spans, and private labels are not stored in this report.

