# R32 Embedding View Bakeoff

R32 introduces a reusable view bakeoff harness for dense candidate channels. The committed artifact uses the offline `local_token_hash` provider as a safety/reproducibility smoke; real providers require explicit manual opt-in and remain candidate/supporting-only.

## Safety

- provider: `openai-compatible`
- run_phase_public_only: `True`
- labels_loaded_after_run: `True`
- promotion_ready: `False`
- default_should_change: `False`
- evidencecore_semantics_changed: `False`
- raw_text_stored: `False`
- raw_query_stored: `False`

## View Results

| View | Status | Records | FileRecall@1 | SpanF0.5 | primary_false_positive_rate | citation_validity |
|---|---|---:|---:|---:|---:|---:|
| path_plus_symbol | ok | 4 | 0.6666666666666666 | 0.16025641025641027 | 1.0 | 1.0 |

## Conclusion

- best_dense_view: `path_plus_symbol`
- worst_dense_view: `path_plus_symbol`
- dense_should_remain_supporting_only: `True`
- All R32 outputs must report `delta_vs_r29_rrf`, `delta_vs_r29_query_noise_guard`, and `delta_vs_r29_symbol` inside `delta_vs_r29_baseline`.
