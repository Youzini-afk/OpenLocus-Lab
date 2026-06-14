# P30-H2 Remote Smoke

- Runs summarized: `6` successful real-provider workflow runs
- Total tasks: `108`
- promotion_ready: `false`
- default_should_change: `false`
- EvidenceCore changed: `false`

## Aggregate result

| Policy | added_gold | added_false | mean ΔSpanF0.5 vs baseline | mean ΔPFP vs baseline | selected missing outcomes | quality comparable |
|---|---:|---:|---:|---:|---:|---|
| candidate_baseline | 27 | 102 | 0.0000 | 0.0000 | 0 | None |
| bucket_routed_v0 | 16 | 36 | -0.0052 | -0.0833 | 0 | None |
| admission_v3 | 12 | 18 | -0.0316 | -0.1389 | 45 | False |
| admission_v3_h1 | 18 | 87 | -0.0346 | -0.1389 | 0 | True |
| admission_v3_h2 | 15 | 90 | -0.0370 | -0.1389 | 0 | True |

## Interpretation

- P30-H2 stayed measurement-valid: `admission_v3_h2` had zero selected-action fallback in all six runs.
- P30-H2 failed the intended quality repair: it did not reduce H1 false spans and lost more gold.
- P25 `bucket_routed_v0` remains the stronger reference on this smoke, mainly because it keeps false spans much lower.
- The new bottleneck is not just broad primary admission. H2 shows that demoting to weak/supporting/filter actions can still preserve many false spans in aggregate metrics. P30 needs action-specific span-cost accounting, not only primary/PFP guards.

## Per-run summary

| run | repo | model | P25 gold/false | H1 gold/false | H2 gold/false | H2 missing | H2 actions |
|---|---|---|---:|---:|---:|---:|---|
| 27498973574 | py_flask | `[mk]DeepSeek-V4-Flash` | 5/8 | 2/14 | 1/15 | 0 | admit_rrf_primary:1, admit_symbol_regex_union:1, apply_llm_filter:9, supporting_only:4, weak_candidate_only:3 |
| 27498974031 | js_express | `[mk]DeepSeek-V4-Flash` | 1/7 | 4/15 | 4/15 | 0 | admit_symbol_regex_union:2, apply_llm_filter:8, supporting_only:6, weak_candidate_only:2 |
| 27498973556 | py_flask | `[mk]Kimi-K2.7-Code` | 5/8 | 2/14 | 1/15 | 0 | admit_rrf_primary:1, admit_symbol_regex_union:1, apply_llm_filter:9, supporting_only:4, weak_candidate_only:3 |
| 27498973983 | js_express | `[mk]Kimi-K2.7-Code` | 1/4 | 4/15 | 4/15 | 0 | admit_symbol_regex_union:2, apply_llm_filter:8, supporting_only:6, weak_candidate_only:2 |
| 27498973597 | py_flask | `[mk]GLM-5.1` | 3/7 | 2/14 | 1/15 | 0 | admit_rrf_primary:1, admit_symbol_regex_union:1, apply_llm_filter:9, supporting_only:4, weak_candidate_only:3 |
| 27498974042 | js_express | `[mk]GLM-5.1` | 1/2 | 4/15 | 4/15 | 0 | admit_symbol_regex_union:2, apply_llm_filter:8, supporting_only:6, weak_candidate_only:2 |

## Safety notes

- P30 made no remote calls; remote calls were only from the upstream P21 rich-candidate stage.
- P25/P30 per-task SCORE records remained ephemeral in runner temp and were not uploaded.
- This report stores only aggregate metrics, run IDs, model IDs, repo IDs, action counts, fallback counts, and safety flags.
- Raw queries, snippets, prompts, responses, gold spans, private labels, and provider keys are not stored.
