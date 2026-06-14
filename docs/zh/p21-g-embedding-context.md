# P21-G1E Embedding Context Atom Screening

> 中文译本待补充。The full Chinese translation is pending.
> 这是同名文件的占位符：保留英文原文，方便未来翻译对照。

## English source / 英文原文

# P21-G1E Embedding Context Atom Screening

P21-G1E tests embedding context atoms/packs as candidate/supporting signals. It does not change EvidenceCore and does not promote dense results to primary/default.

## Safety / Policy

- provider: `local_token_hash`
- embedding_model: `local_token_hash`
- rich_context_remote_allowed: `False`
- run_phase_public_only: `True`
- labels_loaded_after_run: `True`
- promotion_ready: `False`
- default_should_change: `False`
- raw_text_stored: `False`
- raw_snippets_committed: `False`
- remote_file_filter_mode: `self_test_generated_public`
- remote_file_filter_applied: `True`

## Strategy Results

| Strategy | Records | FileRecall@5 | SpanF0.5 | PFP | added_gold | added_false | false:gold | citation | remote calls |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| atom_path_symbol | 4 | 0.6666666666666666 | 0.5434782608695652 | 0.0 | 2 | 0 | 0.0 | 1.0 | 0 |
| atom_signature | 3 | 0.3333333333333333 | 0.3571428571428571 | 0.0 | 1 | 0 | 0.0 | 1.0 | 0 |
| atom_matched_lines | 3 | 0.3333333333333333 | 0.11494252873563218 | 0.0 | 1 | 2 | 2.0 | 1.0 | 0 |
| atom_body_window | 3 | 0.6666666666666666 | 0.29411764705882354 | 0.0 | 2 | 1 | 0.5 | 1.0 | 0 |
| pack1_metadata | 7 | 0.6666666666666666 | 0.5434782608695652 | 0.0 | 2 | 0 | 0.0 | 1.0 | 0 |
| pack2_evidence_sketch | 13 | 0.6666666666666666 | 0.29411764705882354 | 0.0 | 4 | 2 | 0.5 | 1.0 | 0 |
| pack3_local_code | 16 | 0.6666666666666666 | 0.29411764705882354 | 0.0 | 5 | 2 | 0.4 | 1.0 | 0 |
| pack5_contrastive | 19 | 0.6666666666666666 | 0.29411764705882354 | 0.0 | 5 | 2 | 0.4 | 1.0 | 0 |

## Conclusion

- best_span_strategy: `atom_path_symbol`
- best_file_strategy: `atom_path_symbol`
- dense_should_remain_supporting_only: `True`
- blocked_primary_strategies: `['atom_matched_lines']`

