# P32 / P30-H4B Selective Re-admission Remote Smoke

- Runs: `6` successful real-provider runs
- promotion_ready: `false`
- default_should_change: `false`
- remote_calls_by_h4b: `0`

## Aggregate comparison

| policy | added_gold | added_false | false/gold | net 2x | mean SpanF0.5 | mean PFP | Δgold vs P25 | Δfalse vs P25 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `candidate_baseline` | 30 | 188 | 6.27 | -346 | 0.0321 | 0.1111 | 5 | 158 |
| `bucket_routed_v0` | 25 | 30 | 1.20 | -35 | 0.0683 | 0.0463 | 0 | 0 |
| `admission_v3_h1` | 15 | 48 | 3.20 | -81 | 0.0281 | 0.0000 | -10 | 18 |
| `admission_v3_h2` | 15 | 48 | 3.20 | -81 | 0.0281 | 0.0000 | -10 | 18 |
| `admission_v3_h4` | 0 | 0 | n/a | 0 | 0.0000 | 0.0000 | -25 | -30 |
| `admission_v3_h4b` | 24 | 41 | 1.71 | -58 | 0.0433 | 0.0463 | -1 | 11 |

## H4B result

- H4B is quality-comparable and selected-action fallback-free across all runs.
- H4B recovers useful evidence compared with H4A all-demotion: `0/0 -> 24/41` added gold/false.
- H4B does **not** beat P25 `bucket_routed_v0`: P25 is `25/30` with higher mean SpanF0.5 (`0.0683` vs H4B `0.0433`).
- H4B is therefore a useful research direction, not a promotion candidate.

## H4B rule counts

| rule | count |
|---|---:|
| `demote_same_file` | 0 |
| `demote_span_overlap` | 0 |
| `filter_dangerous_subtype` | 9 |
| `hard_guard` | 36 |
| `missing_handoff` | 54 |
| `other` | 0 |
| `strict_rrf_re_admit` | 9 |
| `strict_union_re_admit` | 0 |

## Per-run H4B summary

| run | repo | model | H4B gold/false | H4B primary opportunities | H4B actions |
|---|---|---|---:|---:|---|
| 27545198001 | py_flask | `[mk]DeepSeek-V4-Flash` | 3/6 | 3 | admit_rrf_primary:3, apply_llm_filter:6, weak_candidate_only:9 |
| 27545201458 | js_express | `[mk]DeepSeek-V4-Flash` | 5/8 | 0 | apply_llm_filter:9, weak_candidate_only:9 |
| 27545204934 | py_flask | `[mk]Kimi-K2.7-Code` | 3/6 | 3 | admit_rrf_primary:3, apply_llm_filter:6, weak_candidate_only:9 |
| 27545208778 | js_express | `[mk]Kimi-K2.7-Code` | 4/6 | 0 | apply_llm_filter:9, weak_candidate_only:9 |
| 27545212209 | py_flask | `[mk]GLM-5.1` | 3/6 | 3 | admit_rrf_primary:3, apply_llm_filter:6, weak_candidate_only:9 |
| 27545215753 | js_express | `[mk]GLM-5.1` | 6/9 | 0 | apply_llm_filter:9, weak_candidate_only:9 |

## Interpretation

H4B demonstrates that selective re-admission is better than all-demotion, but the current strict RRF re-admission still lets too much false span through. The next iteration should either tighten the strict primary gate further or introduce a `request_more_context`-style action before primary admission.

## Safety notes

- H4B uses existing measured action outcomes only; no new action names were introduced.
- Public artifacts are aggregate-only and do not include candidate pools, subtype rows, candidate IDs, paths/spans, gold spans, prompts, responses, or provider fields.
- H4B does not change EvidenceCore, Rust core, defaults, or production admission semantics.
