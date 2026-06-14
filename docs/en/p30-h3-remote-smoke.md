# P30-H3 Remote Smoke — Action-Specific Span-Cost Accounting

- Runs: `6` successful real-provider P21→P25→P30 runs
- Total tasks: `108`
- Diagnostic only: `promotion_ready=false`, `default_should_change=false`

## Aggregate policy comparison

| policy | gold | false | false/gold | mean ΔSpanF0.5 | mean ΔPFP | primary false | non-primary false | unclassified false |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `candidate_baseline` | 27 | 102 | 3.78 | 0.0000 | 0.0000 | 0 | 0 | 0 |
| `bucket_routed_v0` | 19 | 45 | 2.37 | -0.0023 | -0.1019 | 4 | 41 | 0 |
| `admission_v3_h1` | 18 | 88 | 4.89 | -0.0362 | -0.1296 | 87 | 1 | 0 |
| `admission_v3_h2` | 15 | 90 | 6.00 | -0.0386 | -0.1389 | 90 | 0 | 0 |

## Main diagnosis

- P25 `bucket_routed_v0` remains the strongest reference in this smoke: false spans fall `102 -> 45`, while gold spans fall `27 -> 19`.
- P30-H1/H2 reduce PFP but carry much higher span-level false cost than P25.
- H3 shows the P30-H1/H2 false-span cost is dominated by **primary local-admit actions**, not by non-primary actions.
- The largest P30 costs are `admit_symbol_regex_union` and, in H2, `admit_rrf_primary`.
- `supporting_only` has low false-span cost in H1/H2, but it kills gold; its cost is recall loss rather than false-span pollution.

## Worst actions by false cost

### `bucket_routed_v0`

| action | kind | selected | gold | false | false/gold |
|---|---|---:|---:|---:|---:|
| `llm_abstain_filter` | non_primary | 63 | 15 | 35 | 2.33 |
| `llm_filter` | non_primary | 33 | 0 | 6 | n/a |
| `llm_span_narrow` | primary | 9 | 4 | 4 | 1.00 |
| `candidate_baseline` | unclassified | 3 | 0 | 0 | n/a |

### `admission_v3_h1`

| action | kind | selected | gold | false | false/gold |
|---|---|---:|---:|---:|---:|
| `admit_symbol_regex_union` | primary | 12 | 18 | 87 | 4.83 |
| `abstain` | non_primary | 27 | 0 | 1 | n/a |
| `apply_llm_filter` | non_primary | 33 | 0 | 0 | n/a |
| `supporting_only` | non_primary | 36 | 0 | 0 | n/a |

### `admission_v3_h2`

| action | kind | selected | gold | false | false/gold |
|---|---|---:|---:|---:|---:|
| `admit_symbol_regex_union` | primary | 9 | 15 | 60 | 4.00 |
| `admit_rrf_primary` | primary | 3 | 0 | 30 | n/a |
| `apply_llm_filter` | non_primary | 48 | 0 | 0 | n/a |
| `supporting_only` | non_primary | 33 | 0 | 0 | n/a |
| `weak_candidate_only` | non_primary | 15 | 0 | 0 | n/a |

## Next step

P30-H4 should not just tighten all routes. It should use explicit action budgets:

- `admit_symbol_regex_union`: require stronger span-level agreement or demote.
- `admit_rrf_primary`: block unless RRF has local span agreement and low-risk bucket.
- `supporting_only`: track gold-kill as recall loss, not as free safety.
- Keep P25 `bucket_routed_v0` as the reference until P30 beats it on false spans, gold retention, and SpanF0.5.

## Safety notes

- H3 is SCORE/ACCOUNT-phase aggregate accounting over fixed actions.
- H3 is not used for same-run routing.
- Public artifacts contain aggregate metrics only; no raw queries, snippets, prompts, responses, gold spans, private labels, or per-task routing are stored.
