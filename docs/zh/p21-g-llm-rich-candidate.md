# P21-G3L LLM Rich Candidate Pilot

> 中文译本待补充。The full Chinese translation is pending.
> 这是同名文件的占位符：保留英文原文，方便未来翻译对照。

## English source / 英文原文

# P21-G3L LLM Rich Candidate Pilot

LLM sees constrained candidate snippets and may filter, abstain, or narrow spans. Its output is not Evidence.

## Safety

- llm_remote_enabled: `False`
- llm_model: `offline_deterministic`
- requested_output_mode: `tool_call`
- candidate_strategy: `dense_atom_signature_rrf_file_constrained`
- raw_snippets_sent_to_provider: `False`
- raw_snippets_committed: `False`
- raw_prompts_stored: `False`
- promotion_ready: `False`

## Results

| Strategy | FileRecall@5 | SpanF0.5 | PFP | Gold | False | ΔSpan vs candidate |
|---|---:|---:|---:|---:|---:|---:|
| candidate_baseline | 0.3333333333333333 | 0.3571428571428571 | 0.0 | 1 | 0 | None |
| llm_filter | 0.3333333333333333 | 0.3571428571428571 | 0.0 | 1 | 0 | 0.0 |
| llm_span_narrow | 0.3333333333333333 | 0.3571428571428571 | 0.0 | 1 | 0 | 0.0 |
| llm_abstain_filter | 0.3333333333333333 | 0.3571428571428571 | 0.0 | 1 | 0 | 0.0 |

## Call Summary

```json
{
  "latency_ms_p50": 0,
  "input_chars_total": 0,
  "schema_error_count": 0,
  "schema_repair_attempted_count": 0,
  "schema_repair_success_count": 0,
  "actual_output_modes": [],
  "fallback_used_count": 0,
  "fallback_event_count": 0,
  "fallback_events": [],
  "packed_candidates_total": 1
}
```

