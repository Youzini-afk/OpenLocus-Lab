# P31-H1 Candidate Reach Ceiling Remote Smoke

> 中文译本待补充。当前文件先作为 `docs/en/p31-h1-remote-smoke.md` 的 1:1 中文镜像，保留英文原文以保证内容不丢失和链接可回溯。

## English source / 英文原文

# P31-H1 Candidate Reach Ceiling Remote Smoke

- Scope: 6 real-provider P21 rich-candidate runs (`Flash/Kimi/GLM × py_flask/js_express`).
- P31-H1 handoff was detected in all runs; reach metrics were available in all runs.
- Diagnostic only: `promotion_ready=false`, `default_should_change=false`.

## Aggregate reach ceiling

| K | GoldFileReach | GoldSpanReach | GoldSpanExactReach | CandidateAbsent | FileRightSpanWrong |
|---:|---:|---:|---:|---:|---:|
| 1 | 0.2500 | 0.1875 | 0.0000 | 0.7500 | 0.25 |
| 3 | 0.5000 | 0.5000 | 0.0000 | 0.5000 | 0.0 |
| 5 | 0.5000 | 0.5000 | 0.0000 | 0.5000 | 0.0 |
| 10 | 0.5000 | 0.5000 | 0.0000 | 0.5000 | 0.0 |
| 20 | 0.5000 | 0.5000 | 0.0000 | 0.5000 | 0.0 |

At K=5, candidate_baseline reaches only `24/48` positive tasks at both file and span level (`0.5000`). `FileRightSpanWrongRate@5` is `0/24 = 0.0`, so in this smoke the first bottleneck is candidate absence, not within-file span localization.

## By repo

| Repo | Runs | Positive tasks | GoldFileReach@5 | GoldSpanReach@5 | FileRightSpanWrong@5 |
|---|---:|---:|---:|---:|---:|
| js_express | 3 | 21 | 0.4286 | 0.4286 | 0.0000 |
| py_flask | 3 | 27 | 0.5556 | 0.5556 | 0.0000 |

## Policy totals from the same runs

| Policy | Added gold | Added false |
|---|---:|---:|
| `bucket_routed_v0` | 20 | 46 |
| `admission_v3_h1` | 18 | 87 |
| `admission_v3_h2` | 15 | 90 |

P25 `bucket_routed_v0` remains a stronger false-span reference than P30-H1/H2 on this smoke, but P31 shows admission tuning alone cannot recover the missing half of positive tasks: candidate reach ceiling is currently the limiting factor.

## Per-run reach@5

| Run | Repo | Model | Mode | Positive | GoldFile@5 | GoldSpan@5 | CandidateAbsent@5 |
|---|---|---|---|---:|---:|---:|---:|
| 27505747950 | py_flask | `[mk]DeepSeek-V4-Flash` | `json_object` | 9 | 0.5556 | 0.5556 | 0.4444 |
| 27505748397 | js_express | `[mk]DeepSeek-V4-Flash` | `json_object` | 7 | 0.4286 | 0.4286 | 0.5714 |
| 27505748934 | py_flask | `[mk]Kimi-K2.7-Code` | `json_object` | 9 | 0.5556 | 0.5556 | 0.4444 |
| 27505749395 | js_express | `[mk]Kimi-K2.7-Code` | `json_object` | 7 | 0.4286 | 0.4286 | 0.5714 |
| 27505749809 | py_flask | `[mk]GLM-5.1` | `tool_call` | 9 | 0.5556 | 0.5556 | 0.4444 |
| 27505750274 | js_express | `[mk]GLM-5.1` | `tool_call` | 7 | 0.4286 | 0.4286 | 0.5714 |

## Safety notes

- The private P31-H1 handoff contains candidate paths/spans and gold spans only in `$RUNNER_TEMP`; it is not uploaded.
- This public report contains aggregate metrics only.
- Raw queries, snippets, prompts, responses, provider keys, candidate paths/spans, gold spans, route features, and per-task rows are not stored here.
