# P21-G2E Constrained/Fused Dense Hybrid

> 中文译本待补充。The full Chinese translation is pending.
> 这是同名文件的占位符：保留英文原文，方便未来翻译对照。

## English source / 英文原文

# P21-G2E Constrained/Fused Dense Hybrid

P21-G2E tests whether embedding context atoms become useful when constrained or fused with RRF/symbol/regex anchors. Dense remains candidate/supporting-only.

## Safety

- provider: `local_token_hash`
- embedding_model: `local_token_hash`
- remote_file_filter_applied: `True`
- raw_text_stored: `False`
- raw_snippets_committed: `False`
- promotion_ready: `False`
- default_should_change: `False`

## Strategy Results

| Strategy | FileRecall@5 | SpanF0.5 | PFP | Gold | False | ΔSpanF0.5 vs RRF | diagnostic_only | supporting_useful |
|---|---:|---:|---:|---:|---:|---:|---|---|
| rrf_baseline | 0.6666666666666666 | 0.29069767441860467 | 0.0 | 2 | 3 | None | False | False |
| dense_pack2_evidence_sketch_only | 0.6666666666666666 | 0.29411764705882354 | 0.0 | 4 | 2 | 0.0034199726402188713 | True | False |
| dense_pack2_evidence_sketch_rrf_file_constrained | 0.6666666666666666 | 0.29411764705882354 | 0.0 | 4 | 2 | 0.0034199726402188713 | False | True |
| dense_pack2_evidence_sketch_symbol_regex_file_constrained | 0.3333333333333333 | 0.101010101010101 | 0.0 | 3 | 2 | -0.18968757340850367 | False | False |
| rrf_plus_dense_pack2_evidence_sketch_supporting | 0.6666666666666666 | 0.29069767441860467 | 0.0 | 4 | 3 | 0.0 | False | False |
| rrf_dense_pack2_evidence_sketch_late_fusion_anchor_constrained | 0.6666666666666666 | 0.29069767441860467 | 0.0 | 4 | 3 | 0.0 | False | False |
| query_noise_guard_rrf_dense_pack2_evidence_sketch | 0.6666666666666666 | 0.29069767441860467 | 0.0 | 4 | 3 | 0.0 | False | False |
| dense_atom_signature_only | 0.3333333333333333 | 0.3571428571428571 | 0.0 | 1 | 0 | 0.06644518272425243 | True | False |
| dense_atom_signature_rrf_file_constrained | 0.3333333333333333 | 0.3571428571428571 | 0.0 | 1 | 0 | 0.06644518272425243 | False | True |
| dense_atom_signature_symbol_regex_file_constrained | 0.3333333333333333 | 0.3571428571428571 | 0.0 | 1 | 0 | 0.06644518272425243 | False | True |
| rrf_plus_dense_atom_signature_supporting | 0.6666666666666666 | 0.29069767441860467 | 0.0 | 3 | 3 | 0.0 | False | False |
| rrf_dense_atom_signature_late_fusion_anchor_constrained | 0.6666666666666666 | 0.29069767441860467 | 0.0 | 3 | 3 | 0.0 | False | False |
| query_noise_guard_rrf_dense_atom_signature | 0.6666666666666666 | 0.29069767441860467 | 0.0 | 3 | 3 | 0.0 | False | False |

## Conclusion

- best_span_strategy: `dense_atom_signature_rrf_file_constrained`
- best_file_strategy: `dense_pack2_evidence_sketch_rrf_file_constrained`
- helpful_vs_rrf_without_pfp_increase: `['dense_pack2_evidence_sketch_rrf_file_constrained', 'dense_atom_signature_rrf_file_constrained', 'dense_atom_signature_symbol_regex_file_constrained']`
- dense_should_remain_supporting_only: `True`

