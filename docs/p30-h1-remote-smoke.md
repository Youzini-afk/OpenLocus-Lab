# P30-H1 Remote Smoke

- Runs summarized: `6` successful real-provider workflow runs
- Total tasks: `108`
- promotion_ready: `false`
- default_should_change: `false`
- EvidenceCore changed: `false`

## Aggregate result

| Policy | added_gold | added_false | mean ΔSpanF0.5 vs baseline | mean ΔPFP vs baseline | selected missing outcomes | quality comparable |
|---|---:|---:|---:|---:|---:|---|
| candidate_baseline | 27 | 101 | 0.0000 | 0.0000 | 0 | None |
| bucket_routed_v0 | 20 | 37 | 0.0020 | -0.0833 | 0 | None |
| admission_v3 | 12 | 17 | -0.0316 | -0.1389 | 45 | False |
| admission_v3_h1 | 18 | 87 | -0.0350 | -0.1389 | 0 | True |

## Interpretation

- P30-H1 succeeded as a measurement repair: `admission_v3_h1` had zero selected-action fallback in all six runs.
- P30-H1 failed as a quality improvement: it preserved less gold and produced far more false spans than P25 `bucket_routed_v0`.
- Legacy `admission_v3` still has missing outcomes by design, preserving the old fallback-constrained behavior for comparison; it is not quality-comparable.
- The main diagnosis is not “missing handoff” anymore. The next bottleneck is the scorecard: `symbol_regex_union` admission is too broad and needs stricter agreement/bucket guards.

## Per-run summary

| run | repo | model | bucket gold/false | legacy missing | h1 gold/false | h1 missing | h1 actions |
|---|---|---|---:|---:|---:|---:|---|
| 27497770393 | py_flask | `[mk]DeepSeek-V4-Flash` | 6/8 | 7 | 2/14 | 0 | abstain:4, admit_symbol_regex_union:2, apply_llm_filter:7, supporting_only:5 |
| 27497770871 | js_express | `[mk]DeepSeek-V4-Flash` | 1/6 | 8 | 4/15 | 0 | abstain:5, admit_symbol_regex_union:2, apply_llm_filter:5, supporting_only:6 |
| 27497770414 | py_flask | `[mk]Kimi-K2.7-Code` | 5/8 | 7 | 2/14 | 0 | abstain:4, admit_symbol_regex_union:2, apply_llm_filter:7, supporting_only:5 |
| 27497770893 | js_express | `[mk]Kimi-K2.7-Code` | 1/3 | 8 | 4/15 | 0 | abstain:5, admit_symbol_regex_union:2, apply_llm_filter:5, supporting_only:6 |
| 27497770404 | py_flask | `[mk]GLM-5.1` | 6/8 | 7 | 2/14 | 0 | abstain:4, admit_symbol_regex_union:2, apply_llm_filter:7, supporting_only:5 |
| 27497770885 | js_express | `[mk]GLM-5.1` | 1/4 | 8 | 4/15 | 0 | abstain:5, admit_symbol_regex_union:2, apply_llm_filter:5, supporting_only:6 |

## Safety notes

- P30 made no remote calls; remote calls were only from the upstream P21 rich-candidate stage.
- P25/P30 per-task SCORE records remained ephemeral in runner temp and were not uploaded.
- This report stores only aggregate metrics, run IDs, model IDs, repo IDs, action counts, fallback counts, and safety flags.
- Raw queries, snippets, prompts, responses, gold spans, private labels, and provider keys are not stored.
