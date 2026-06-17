# B3 Request-More-Context Quality Experiment

Date: 2026-06-17

B3 tests whether request-more-context routing improves live quality when it can
choose between a plain span-narrow pack and a hard-distractor filter pack. It is
a live quality experiment, not a gate: it runs two P21 rich-candidate layouts in
the same workflow job and merges the ephemeral per-task records into an
aggregate-only B3 report.

B3 does not admit Evidence, change defaults, or change EvidenceCore. Raw
per-task records remain in `$RUNNER_TEMP`; the public artifact contains only
aggregate treatment metrics.

## Run matrix

```text
stage: b3_rmc_quality
repos: py_flask, js_express, go_gin, rust_ripgrep
dataset: ci_smoke
tasks per repo: 6
task_sample_mode: round_robin_public_buckets
model: [mk]Kimi-K2.7-Code
output mode: tool_call
```

Runs:

```text
py_flask      27682471959
js_express    27682473463
go_gin        27682474976
rust_ripgrep  27682476342
```

All four workflow runs succeeded and uploaded only the B3 aggregate report/doc
plus sanitized `plan.json`.

## Treatments

```text
p25_bucket_routed_v0_plain:
  Current P25 bucket_routed_v0 over topk_plain_v0 records.

rmc_local_conservative_v0:
  No extra LLM route; suppresses negative/hard/no-gold/ambiguous cases to weak.

rmc_llm_pack_routed_v0:
  Routes positive cases to plain span_narrow and no-gold/hard/ambiguous cases
  to hard-distractor filter.

rmc_hybrid_v0:
  Uses weak/local resolution for unsupported cases, plain span_narrow for
  positive supported cases, and hard-distractor filter for no-gold/hard cases.
```

## Aggregate results

| Treatment | Gold | False | False/gold | Mean SpanF0.5 | Mean PFP | LLM actions | Net span value 2x | False reduction vs P25 | Gold kill vs P25 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `p25_bucket_routed_v0_plain` | 8 | 7 | 0.875 | 0.0890 | 0.0417 | 24 | -6 | 0 | 0 |
| `rmc_hybrid_v0` | 7 | 8 | 1.143 | 0.0820 | 0.0833 | 11 | -9 | -1 | 0 |
| `rmc_llm_pack_routed_v0` | 7 | 8 | 1.143 | 0.0820 | 0.0833 | 24 | -9 | -1 | 0 |
| `rmc_local_conservative_v0` | 4 | 18 | 4.500 | 0.0226 | 0.0000 | 0 | -32 | -11 | 3 |

Action counts:

| Treatment | plain span_narrow | hard filter | weak only | P25 plain filter | P25 plain abstain |
| --- | ---: | ---: | ---: | ---: | ---: |
| `p25_bucket_routed_v0_plain` | 4 | 0 | 0 | 8 | 12 |
| `rmc_hybrid_v0` | 4 | 7 | 13 | 0 | 0 |
| `rmc_llm_pack_routed_v0` | 4 | 20 | 0 | 0 | 0 |
| `rmc_local_conservative_v0` | 0 | 0 | 20 | 0 | 0 |

## Interpretation

B3 is a useful negative result: the first fixed RMC routing policies did **not**
beat the P25 reference. Both LLM-routed RMC variants lost one gold span, added
one false span, doubled mean PFP, and reduced mean SpanF0.5 relative to P25.
The local conservative variant avoided primary false positives but killed too
much gold and left many false baseline candidates.

The failure mode is now clearer:

```text
1. Plain span_narrow remains useful for positive-like cases.
2. Hard-distractor filter is not yet a safe replacement for P25's abstain/filter
   routing on all no-gold/hard/ambiguous cases.
3. Weak-only suppression is too blunt; it kills reach and does not repair false
   candidates already present in the baseline.
4. RMC needs a learned or searched routing surface, not fixed hand-written
   bucket rules.
```

## Algorithmic conclusion

B3 does not support adopting `rmc_llm_pack_routed_v0` or `rmc_hybrid_v0` as a
better policy. It points to B8-style interpretable policy search or a narrower
B3B routing repair:

```text
route plain span_narrow only where P25 currently under-recovers gold;
route hard-distractor filter only when P59/B2-style hard-distractor actionability
is high;
preserve P25 abstain/filter where it already has low PFP;
optimize against SpanF0.5, false/gold, PFP, and provider-call budget together.
```

B3 is therefore not a win, but it is high-value failure information: fixed RMC
routing is too crude, and the next improvement should come from policy search or
bucket-specific routing repair rather than more global RMC rules.
