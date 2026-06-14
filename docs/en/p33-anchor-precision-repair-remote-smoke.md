# P33 Anchor Precision Repair Remote Smoke

## Summary

- Runs summarized: `6/6` successful.
- Task observations: `108` (`48` positive, `60` no-gold).
- Diagnostic only: `promotion_ready=false`, `default_should_change=false`, `candidate_not_fact=true`.

## Main finding

P33 confirms the P31-H2/P30-H3 tension: symbol/regex-derived anchors can have high reach, but same-run anchor buckets still carry high false-span cost. No observed bucket is ready for primary admission.

## Selected anchor buckets

| bucket | tasks | positive/no-gold | GoldSpanReach@5 | added_gold | added_false | false_per_gold | net_span_value_2x | class |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `symbol_regex_agree_span` | 9 | 9/0 | 1.0 | 15 | 60 | 4.0 | -105 | `insufficient_denominator` |
| `symbol_regex_agree_span_low_risk` | 9 | 9/0 | 1.0 | 15 | 60 | 4.0 | -105 | `insufficient_denominator` |
| `rrf_anchor_agree_span` | 60 | 48/12 | 0.875 | 48 | 528 | 11.0 | -1008 | `blocked_high_false_cost` |
| `symbol_regex_disagree` | 39 | 30/9 | 0.9 | 27 | 363 | 13.444444444444445 | -699 | `blocked_high_false_cost` |
| `regex_only` | 15 | 9/6 | 0.6666666666666666 | 6 | 135 | 22.5 | -264 | `insufficient_denominator` |
| `query_noise_low` | 93 | 45/48 | 0.8666666666666667 | 45 | 450 | 10.0 | -855 | `blocked_high_false_cost` |
| `query_noise_high` | 9 | 3/6 | 1.0 | 3 | 78 | 26.0 | -153 | `insufficient_denominator` |
| `positive_bucket` | 12 | 12/0 | 1.0 | 18 | 87 | 4.833333333333333 | -156 | `blocked_high_false_cost` |

## Calibration summary

| cell | tasks | positive/no-gold | GoldSpanReach@5 | added_gold | added_false | false_per_gold | net_span_value_2x |
|---|---:|---:|---:|---:|---:|---:|---:|
| `a3_r0_s2` | 48 | 48/0 | 0.875 | 48 | 417 | 8.6875 | -786 |

In this smoke the only populated calibration cell is `a3_r0_s2`: span-agreement, low-risk, RRF-span-backed. It reaches `42/48` positive spans but has `false_per_gold≈8.69`, so even the apparently strongest local-anchor cell is not primary-safe without additional budget guards.

## Interpretation

- `symbol_regex_agree_span` reaches all 9 positive observations in that bucket, but `false_per_gold=4.0` and `net_span_value_2x=-105`.
- `symbol_regex_disagree` still has high reach (`27/30`) but much worse false cost (`false_per_gold≈13.44`).
- `regex_only` is especially risky (`false_per_gold=22.5`).
- `query_noise_low` is not sufficient as a safety condition by itself (`false_per_gold=10.0`).

## P33 -> P32/H4 handoff

Same-run P33 produces no primary-safe bucket. It identifies budget candidates only:

- keep `symbol_regex_union` as a candidate-expansion source;
- require stricter action budgets before `admit_symbol_regex_union` or `admit_rrf_primary`;
- distinguish span agreement from file-only or disagree cases;
- do not treat query-noise-low or RRF-span-backed as sufficient safety evidence.

## Safety notes

- P33 made no remote calls; remote calls came from the enclosing P21 workflow only.
- Private P31 candidate pools and SCORE gold spans stayed in runner temp records.
- This report stores only aggregate counts/rates.
- No task IDs, candidate coordinates, gold spans, raw snippets, prompts, responses, route features, provider keys, or base URLs are stored.
