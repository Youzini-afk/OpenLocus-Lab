# B1 Live LLM Rich Candidate Run

> 中文译本待补充。本文件先保留英文原文，避免内容丢失。

## English source / 英文原文

# B1 Live LLM Rich Candidate Run

Date: 2026-06-17

This report records the first Breakthrough Sprint live quality run after the
diagnostic-only P51-B/P57/P58/P59/P60/P61/P62/P63 sequence. B1 uses the existing
P21 rich-candidate harness and P25 policy scorer to send bounded public
candidate snippets to the configured LLM provider and measure quality, false
cost, latency, schema stability, and failure modes.

B1 does **not** promote a default strategy, does not admit Evidence, and does
not change `EvidenceCore`. LLM outputs remain candidate decisions only. Raw
prompts, raw provider responses, raw snippets, private labels, gold spans,
provider keys, and provider URLs are not uploaded or committed.

## Run matrix

```text
repos: py_flask, js_express, go_gin, rust_ripgrep
dataset: ci_smoke
tasks per repo: 6
task_sample_mode: round_robin_public_buckets
stage: p21_llm_rich
model: [mk]Kimi-K2.7-Code via openai-compatible provider
roles available through P21/P25: candidate_baseline, llm_span_narrow, llm_filter, llm_abstain_filter, P25 bucket_routed_v0
```

Two output modes were run on the same bounded matrix:

```text
tool_call:
  py_flask      27674929320
  js_express    27674930653
  go_gin        27674932153
  rust_ripgrep  27674933629

json_schema_strict:
  py_flask      27675200878
  js_express    27675202356
  go_gin        27675203807
  rust_ripgrep  27675205460
```

All eight workflow runs completed successfully and passed the existing artifact
privacy gates.

## Aggregate quality and cost results

### Tool-call mode

```text
successful_calls: 24
schema_valid_calls: 24
fallback_events: 0
schema_errors: 0
input_chars_total: 34,024
packed_candidates_total: 43
mean per-repo latency_p50_ms: 2,310
```

| Strategy | Tasks | Added gold | Added false | False/gold | Mean SpanF0.5 | Mean PFP |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| candidate_baseline | 24 | 8 | 43 | 5.375 | 0.1099 | 0.1250 |
| llm_span_narrow | 24 | 9 | 5 | 0.556 | 0.2849 | 0.0625 |
| llm_filter | 24 | 7 | 7 | 1.000 | 0.1884 | 0.0625 |
| llm_abstain_filter | 24 | 7 | 7 | 1.000 | 0.1884 | 0.0625 |
| P25 bucket_routed_v0 | 24 | 8 | 6 | 0.750 | 0.1139 | 0.0417 |

Key result: `llm_span_narrow` sharply reduced false spans while slightly
increasing added gold relative to the candidate baseline. It also exceeded the
P25 bucket-routed reference on mean SpanF0.5 in this bounded sample, at the cost
of a slightly higher primary false-positive rate than P25.

### JSON-schema-strict mode

```text
successful_calls: 24
schema_valid_calls: 24
fallback_events: 0
schema_errors: 0
input_chars_total: 34,714
packed_candidates_total: 44
mean per-repo latency_p50_ms: 3,528.5
```

| Strategy | Tasks | Added gold | Added false | False/gold | Mean SpanF0.5 | Mean PFP |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| candidate_baseline | 24 | 8 | 44 | 5.500 | 0.1099 | 0.1250 |
| llm_span_narrow | 24 | 9 | 8 | 0.889 | 0.2829 | 0.1250 |
| llm_filter | 24 | 7 | 10 | 1.429 | 0.1884 | 0.1250 |
| llm_abstain_filter | 24 | 7 | 10 | 1.429 | 0.1884 | 0.1250 |
| P25 bucket_routed_v0 | 24 | 8 | 9 | 1.125 | 0.0914 | 0.0833 |

Key result: `json_schema_strict` remained schema-stable, but it was slower and
left more false spans than `tool_call` on the same bounded sample.

## Interpretation

B1 provides the first post-gate live quality result for the candidate-to-evidence
sprint:

```text
Rich candidate LLM span narrowing is not just safe to run; it produced useful
quality signal on the bounded four-repo public sample.
```

The strongest observed role was `llm_span_narrow`, especially in `tool_call`
mode. It preserved FileRecall@5, increased added gold from 8 to 9, and reduced
added false spans from 43 to 5 across 24 tasks. `filter` and `abstain_filter`
also reduced false spans, but killed more gold and underperformed span narrowing
on SpanF0.5.

This validates the research pivot away from low-context aliases and toward
bounded rich candidate reasoning. The model did not need more aggregate
preconditions; it needed candidate snippets, IDs, scores/provenance, and role
constraints.

## Failure and risk notes

- The sample remains small: 4 repos x 6 tasks x 2 output modes.
- Only one model profile was used: `[mk]Kimi-K2.7-Code`.
- P25 bucket routing still has lower PFP than global span narrowing in tool-call
  mode, so the next policy question is not "use LLM everywhere". It is where
  span narrowing should be routed.
- B1 used the existing P21/P25 pack and role structure. It did not yet run the
  full P49/P59 contrastive-pack A-F comparison.
- B1 did not produce Evidence. LLM-selected spans still require EvidenceCore
  materialization before they can become facts.

## Next research move

The immediate next step should be B2/B3 rather than more precondition gates:

```text
B2: contrastive pack quality experiment
  Compare ordinary top-k packs against packs with hard distractors,
  source/test/docs flags, same-file competitors, and bounded snippets.

B3: request_more_context quality experiment
  Compare P25, H4B, RMC-local, RMC-LLM, and RMC-hybrid using the observed
  B1 span-narrow/filter behavior.
```

The B1 result justifies targeted expansion, but not promotion/default changes.
