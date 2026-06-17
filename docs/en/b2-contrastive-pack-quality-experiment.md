# B2 Contrastive Pack Quality Experiment

Date: 2026-06-17

B2 tests whether adding explicit contrastive structure to live rich-candidate LLM packs improves span narrowing and filtering quality. It extends the existing P21 live rich-candidate harness with `--pack-layout` and compares four pack layouts on the same four-repo public matrix.

B2 is a live quality experiment. It sends bounded public candidate snippets to the configured LLM provider. It does not admit Evidence, does not promote any default strategy, and does not change `EvidenceCore`. LLM outputs remain candidate decisions only.

## Implementation note: P21 public report privacy repair

Before B2 live runs, P21's uploaded JSON report was changed to be aggregate-only. Per-task/per-candidate `decision_records` and `candidate_meta` are no longer uploaded in the public P21 JSON artifact; detailed decision records remain available only in the ephemeral `$P25_RECORDS` handoff inside the workflow. The workflow privacy gate now rejects persisted task IDs, candidate IDs, paths, line ranges, content digests, snippets, prompts, responses, labels, `decision_records`, and `candidate_meta` in the public P21 report.

## Pack layouts

```text
topk_plain_v0:
  Ordinary top-k bounded snippets.

topk_scores_provenance_v0:
  Top-k snippets plus retrieval score/provenance/channel metadata.

contrastive_competitor_v0:
  Top-k snippets plus competitor slots, without explicit hard-distractor proxy injection.

hard_distractor_contrast_v0:
  Contrastive competitor pack with metadata-selected hard-distractor proxies.
```

All layouts used `llm_output_mode=tool_call`, `dataset=ci_smoke`, `max_tasks=6`, and `task_sample_mode=round_robin_public_buckets`.

## Run matrix

```text
repos: py_flask, js_express, go_gin, rust_ripgrep
tasks per layout: 24
model: [mk]Kimi-K2.7-Code
```

| Layout | py_flask | js_express | go_gin | rust_ripgrep |
| --- | ---: | ---: | ---: | ---: |
| `topk_plain_v0` | 27676829411 | 27676830935 | 27676832373 | 27676833797 |
| `topk_scores_provenance_v0` | 27677245697 | 27677246972 | 27677248171 | 27677249614 |
| `contrastive_competitor_v0` | 27677251043 | 27677252254 | 27677253878 | 27677255224 |
| `hard_distractor_contrast_v0` | 27676835457 | 27676837060 | 27676838404 | 27676839848 |

All 16 workflow runs completed successfully and passed artifact privacy gates.

## Aggregate results

### Span narrowing

| Pack layout | Added gold | Added false | False/gold | Mean SpanF0.5 | Mean PFP | Input chars | Mean latency p50 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `topk_plain_v0` | 9 | 6 | 0.667 | 0.2691 | 0.0625 | 31,484 | 3,641.75 |
| `topk_scores_provenance_v0` | 9 | 7 | 0.778 | 0.2829 | 0.1250 | 39,120 | 5,547.00 |
| `contrastive_competitor_v0` | 9 | 8 | 0.889 | 0.2694 | 0.1250 | 40,144 | 2,823.75 |
| `hard_distractor_contrast_v0` | 7 | 5 | 0.714 | 0.2820 | 0.1250 | 41,494 | 3,074.00 |

### Filtering

| Pack layout | Added gold | Added false | False/gold | Mean SpanF0.5 | Mean PFP |
| --- | ---: | ---: | ---: | ---: | ---: |
| `topk_plain_v0` | 7 | 8 | 1.143 | 0.1751 | 0.0625 |
| `topk_scores_provenance_v0` | 7 | 9 | 1.286 | 0.1884 | 0.1250 |
| `contrastive_competitor_v0` | 7 | 10 | 1.429 | 0.1751 | 0.1250 |
| `hard_distractor_contrast_v0` | 5 | 7 | 1.400 | 0.1880 | 0.1250 |

### Pack structure counters

| Pack layout | Packed candidates | Hard-distractor proxy slots | Competitor slots |
| --- | ---: | ---: | ---: |
| `topk_plain_v0` | 44 | 0 | 0 |
| `topk_scores_provenance_v0` | 44 | 0 | 0 |
| `contrastive_competitor_v0` | 44 | 0 | 32 |
| `hard_distractor_contrast_v0` | 44 | 25 | 33 |

## Interpretation

B2's main conclusion is that contrastive structure is **not automatically better**. The best pack depends on which error matters:

```text
topk_plain_v0:
  Best PFP and best gold retention for span_narrow.

topk_scores_provenance_v0:
  Highest mean SpanF0.5, but more false spans, higher PFP, and higher latency.

contrastive_competitor_v0:
  Added competitor structure without hard-distractor proxies, but worsened false spans without meaningful SpanF0.5 gain.

hard_distractor_contrast_v0:
  Reduced span_narrow false spans from 6 to 5, but killed two gold spans and doubled mean PFP relative to plain top-k.
```

This is a useful negative/nuanced result: hard-distractor proxies help suppress some false spans, but the current proxy/pack wording is too aggressive or too noisy and can cause gold loss. Contrastive packs should not be adopted wholesale.

## Algorithmic conclusion

The immediate policy should not be "always use contrastive hard distractors". Instead:

```text
1. Keep `topk_plain_v0` as the safest low-PFP live span-narrow pack.
2. Use score/provenance features selectively, not globally.
3. Route hard-distractor contrast only to filter/no-gold/hard-distractor buckets, not to all span_narrow positives.
4. Repair hard-distractor proxy selection before expanding it.
```

B2 points directly to B3: request_more_context should choose between plain span-narrow, local verifier, and hard-distractor/filter packs based on bucket and risk, instead of treating one pack layout as universal.

## Limitations

- Sample size is still small: 24 tasks per layout.
- Only one model profile was used.
- B2 used P21's current role scoring and prompt template; it did not yet compare fully independent prompt wording.
- B2 did not produce Evidence. All LLM-selected spans still require EvidenceCore materialization.
