# P31-H2 Strategy Reach Matrix Remote Smoke

## Summary

- Runs summarized: `6` successful; `1` excluded artifact-upload failure (`27507065788`, GitHub `ECONNRESET`).
- Total tasks: `108`
- Positive tasks: `48`
- Diagnostic only: `promotion_ready=false`, `default_should_change=false`, `candidate_not_fact=true`.

## Main finding

`symbol_regex_union` has the highest candidate reach ceiling but must not be treated as safe primary evidence.

At K=5:

| strategy | GoldFileReach | GoldSpanReach | CandidateAbsentRate | FileRightSpanWrongRate | UniqueGoldSpanReach |
|---|---:|---:|---:|---:|---:|
| `candidate_baseline` | 0.5000 | 0.5000 | 0.5000 | 0.0000 | 0.0000 |
| `rrf_primary` | 0.4375 | 0.4375 | 0.5625 | 0.0000 | 0.0000 |
| `symbol_regex_union` | 0.9375 | 0.8750 | 0.0625 | 0.0667 | 0.3750 |
| `llm_span_narrow` | 0.3333 | 0.3333 | 0.6667 | 0.0000 | 0.0000 |
| `llm_filter` | 0.3333 | 0.3333 | 0.6667 | 0.0000 | 0.0000 |
| `llm_abstain_filter` | 0.3333 | 0.3333 | 0.6667 | 0.0000 | 0.0000 |

Concrete counts:

- `candidate_baseline`: `24/48` span reach at K=5.
- `rrf_primary`: `21/48` span reach at K=5.
- `symbol_regex_union`: `42/48` span reach at K=5.
- `symbol_regex_union` unique span reach: `18/48`.

## Combination reach

| combination | UnionGoldSpanReach@5 | UnionGoldFileReach@5 |
|---|---:|---:|
| `candidate_baseline__plus__llm_span_narrow` | 0.5000 | 0.5000 |
| `candidate_baseline__plus__rrf_primary` | 0.5000 | 0.5000 |
| `candidate_baseline__plus__symbol_regex_union` | 0.8750 | 0.9375 |
| `candidate_baseline__plus__symbol_regex_union__plus__rrf_primary` | 0.8750 | 0.9375 |
| `symbol_regex_union__plus__rrf_primary` | 0.8750 | 0.9375 |

The useful ceiling jump is almost entirely from adding `symbol_regex_union`:

- `candidate_baseline + rrf_primary`: `0.5000` span reach.
- `candidate_baseline + llm_span_narrow`: `0.5000` span reach.
- `candidate_baseline + symbol_regex_union`: `0.8750` span reach.

## Same-run policy context

| policy | added_gold_span | added_false_span |
|---|---:|---:|
| `bucket_routed_v0` | 16 | 44 |
| `admission_v3_h1` | 18 | 87 |
| `admission_v3_h2` | 15 | 90 |

This reconciles P31 and P30-H3:

- P31-H2 says `symbol_regex_union` is valuable for candidate reach.
- P30-H3 says local primary-admit actions, especially `admit_symbol_regex_union`, dominate false-span cost.
- Therefore the next step is not to discard `symbol_regex_union`; it should be repaired/calibrated as candidate expansion and then guarded by action budgets before primary admission.

## Interpretation

Allowed conclusion:

> `symbol_regex_union` is a high-reach candidate expansion source in this smoke, but same-run reach does not prove it is safe as primary evidence.

Disallowed conclusions:

- Do not promote `symbol_regex_union` to default.
- Do not change EvidenceCore.
- Do not route future tasks from same-run reach matrix without held-out validation.
- Do not treat candidate reach as evidence quality.

## Next step

Proceed with:

1. `P33 Reach-Preserving Precision Anchor Repair`: repair/calibrate symbol/regex anchors and measure whether the high reach can be retained without increasing false primary.
2. `P32 / P30-H4 Action-Specific Span Budget`: require budgeted guards before `symbol_regex_union` or `rrf_primary` can become primary.

## Safety notes

- Private P31-H1 candidate pools and gold spans stayed in ephemeral runner records.
- This report stores only aggregate counts/rates.
- No task IDs, candidate paths/spans, gold spans, raw snippets, prompts, responses, or provider fields are stored here.
