# P32 / P30-H4 Budget Overlay Remote Smoke

> 中文译本待补充。The full Chinese translation is pending.
> 这是同名文件的占位符：保留英文原文，方便未来翻译对照。

## English source / 英文原文

# P32 / P30-H4 Budget Overlay Remote Smoke

- Runs: `6` successful real-provider runs
- promotion_ready: `false`
- default_should_change: `false`
- remote_calls_by_h4: `0`

## Aggregate comparison

| policy | added_gold | added_false | mean SpanF0.5 | mean PFP | Δgold vs P25 | Δfalse vs P25 |
|---|---:|---:|---:|---:|---:|---:|
| `candidate_baseline` | 30 | 189 | 0.0321 | 0.1111 | 3 | 155 |
| `bucket_routed_v0` | 27 | 34 | 0.0768 | 0.0463 | 0 | 0 |
| `admission_v3_h1` | 15 | 48 | 0.0281 | 0.0000 | -12 | 14 |
| `admission_v3_h2` | 15 | 48 | 0.0281 | 0.0000 | -12 | 14 |
| `admission_v3_h4` | 0 | 0 | 0.0000 | 0.0000 | -27 | -34 |

## H4 result

P30-H4 is intentionally conservative, but this smoke shows it is too conservative to be useful as a retrieval/admission policy:

- `admission_v3_h4` added gold spans: `0`
- `admission_v3_h4` added false spans: `0`
- `admission_v3_h4` mean SpanF0.5: `0.0000`
- selected-action fallback rate: `0` across all runs

It behaves like a safety lower bound: it removes primary false spans by demoting/filtering everything, but it also removes all useful gold evidence.

## Interpretation

- P33-B was correct that no observed local-anchor subtype is primary-safe.
- However, “no local-anchor primary” as a policy is too blunt.
- P25 `bucket_routed_v0` remains the strongest reference: it retains `27` added gold spans with only `34` added false spans on this smoke.
- H4 must evolve from all-demotion to budgeted selective re-admission or request-more-context variants.

## Per-run H4 action counts

| run | repo | model | actions |
|---|---|---|---|
| 27542977766 | py_flask | `[mk]DeepSeek-V4-Flash` | apply_llm_filter:10, supporting_only:5, weak_candidate_only:3 |
| 27542981300 | js_express | `[mk]DeepSeek-V4-Flash` | apply_llm_filter:8, supporting_only:6, weak_candidate_only:4 |
| 27542984556 | py_flask | `[mk]Kimi-K2.7-Code` | apply_llm_filter:10, supporting_only:5, weak_candidate_only:3 |
| 27542987887 | js_express | `[mk]Kimi-K2.7-Code` | apply_llm_filter:8, supporting_only:6, weak_candidate_only:4 |
| 27542990941 | py_flask | `[mk]GLM-5.1` | apply_llm_filter:10, supporting_only:5, weak_candidate_only:3 |
| 27542994147 | js_express | `[mk]GLM-5.1` | apply_llm_filter:8, supporting_only:6, weak_candidate_only:4 |

## Safety notes

- H4 uses only existing measured action outcomes, so the comparison is quality-comparable.
- Public artifacts are aggregate-only and do not include candidate pools, subtype rows, candidate IDs, paths/spans, gold spans, prompts, responses, or provider fields.
- H4 does not change EvidenceCore, Rust core, defaults, or production admission semantics.
