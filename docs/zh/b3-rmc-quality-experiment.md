# B3 Request-More-Context Quality Experiment

> 中文译本待补充。本文件先保留英文原文，避免内容丢失。

## English source / 英文原文

# B3 Request-More-Context Quality Experiment

Date: 2026-06-17

B3 is a live quality experiment that compares P25 bucket routing against fixed request-more-context treatments on the same frozen task set. It uses two live P21 rich-candidate pack layouts inside one workflow job:

```text
topk_plain_v0:
  positive / likely-positive span_narrow source

hard_distractor_contrast_v0:
  no-gold / hard-distractor filter source
```

Detailed P21 per-task records remain in `$RUNNER_TEMP`; the public B3 report is aggregate-only.

## Treatments

```text
p25_bucket_routed_v0_plain:
  Current P25 bucket_routed_v0 over topk_plain_v0 records.

rmc_local_conservative_v0:
  No extra LLM route; suppresses negative/hard/no-gold/ambiguous cases to weak.

rmc_llm_pack_routed_v0:
  Routes positive cases to plain span_narrow and negative/no-gold/hard cases to hard-distractor filter.

rmc_hybrid_v0:
  Uses weak/local resolution for unsupported or ambiguous cases, plain span_narrow for positive supported cases, and hard-distractor filter for no-gold/hard-distractor cases.
```

## Metrics

B3 reports, per treatment:

```text
added_gold_span
added_false_span
false_per_gold
mean_span_f05
mean_primary_false_positive_rate
no_gold_false_primary_rate
action_counts
effective_llm_action_count
provider_call_estimate (labeled estimate, not measured extra calls)
gold_kill_count_vs_p25
false_reduction_vs_p25
net_span_value_2x
```

## Safety boundary

B3 does not admit Evidence, change defaults, or change EvidenceCore. LLM outputs remain candidate decisions. Public artifacts must not contain task IDs, candidate IDs, paths, line ranges, content digests, raw snippets, prompts, responses, labels, or gold spans.
