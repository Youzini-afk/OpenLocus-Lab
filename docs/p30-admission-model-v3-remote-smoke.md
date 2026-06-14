# P30 Admission Model V3 Remote Smoke

- Runs summarized: `6` successful real-provider workflow runs
- Total tasks: `108`
- promotion_ready: `false`
- default_should_change: `false`
- EvidenceCore changed: `false`

## Aggregate result

| Policy | added_gold | added_false | mean ΔSpanF0.5 vs baseline | mean ΔPFP vs baseline |
|---|---:|---:|---:|---:|
| candidate_baseline | 27 | 102 | 0.0000 | 0.0000 |
| bucket_routed_v0 | 19 | 39 | 0.0010 | -0.0833 |
| admission_v3 | 17 | 41 | -0.0102 | -0.0833 |

## Interpretation

- `bucket_routed_v0` remains the stronger policy on this smoke: it preserved more gold and produced fewer false spans than `admission_v3`.
- `admission_v3` matched the PFP reduction but was over-conservative: it lost more gold and had negative mean SpanF0.5 delta versus baseline.
- Non-zero P30 fallback counts show the current P21/P25 ephemeral records still lack measured outcomes for some admission actions, especially `weak_candidate_only`.
- P30 should stay research-only. The next implementation step is richer local-anchor handoff: measured `symbol_regex_union` / `rrf_primary` outcomes and safe RUN-phase route features.

## Per-run summary

| run | repo | model | mode | bucket gold/false | p30 gold/false | p30 ΔSpan | p30 ΔPFP | fallback missing | actions |
|---|---|---|---|---:|---:|---:|---:|---:|---|
| 27496427996 | py_flask | `[mk]DeepSeek-V4-Flash` | `json_object` | 4/8 | 4/8 | -0.0022 | 0.0000 | 2 | abstain:6, apply_llm_filter:10, weak_candidate_only:2 |
| 27496428496 | js_express | `[mk]DeepSeek-V4-Flash` | `json_object` | 1/7 | 1/7 | -0.0270 | -0.1667 | 1 | abstain:8, apply_llm_filter:9, weak_candidate_only:1 |
| 27496427981 | py_flask | `[mk]Kimi-K2.7-Code` | `json_object` | 6/8 | 5/9 | 0.0124 | 0.0000 | 2 | abstain:6, apply_llm_filter:10, weak_candidate_only:2 |
| 27496428438 | js_express | `[mk]Kimi-K2.7-Code` | `json_object` | 1/3 | 1/3 | -0.0270 | -0.1667 | 1 | abstain:8, apply_llm_filter:9, weak_candidate_only:1 |
| 27496428015 | py_flask | `[mk]GLM-5.1` | `tool_call` | 6/9 | 5/10 | 0.0098 | 0.0000 | 2 | abstain:6, apply_llm_filter:10, weak_candidate_only:2 |
| 27496428505 | js_express | `[mk]GLM-5.1` | `tool_call` | 1/4 | 1/4 | -0.0270 | -0.1667 | 1 | abstain:8, apply_llm_filter:9, weak_candidate_only:1 |

## Safety notes

- P30 made no remote calls; remote calls were only from the upstream P21 rich-candidate stage.
- P25/P30 per-task SCORE records remained ephemeral in runner temp and were not uploaded.
- This report stores only aggregate metrics, run IDs, model IDs, repo IDs, actions, and safety flags.
- Raw queries, snippets, prompts, responses, gold spans, private labels, and provider keys are not stored.
