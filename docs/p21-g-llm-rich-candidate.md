# P21-G3L LLM Rich Candidate Pilot

LLM sees constrained candidate snippets and may filter, abstain, or narrow spans. Its output is not Evidence.

## Safety

- llm_remote_enabled: `False`
- llm_model: `offline_deterministic`
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
  "packed_candidates_total": 1
}
```
