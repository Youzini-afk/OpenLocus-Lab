# R32 Embedding View Bakeoff

> 中文译本待补充。The full Chinese translation is pending.
> 这是同名文件的占位符：保留英文原文，方便未来翻译对照。

## English source / 英文原文

# R32 Embedding View Bakeoff

R32 introduces a reusable view bakeoff harness for dense candidate channels. The committed artifact uses the offline `local_token_hash` provider as a safety/reproducibility smoke; real providers require explicit manual opt-in and remain candidate/supporting-only.

## Safety

- provider: `local_token_hash`
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
| path_plus_symbol | ok | 4 | 0.6666666666666666 | 0.5434782608695652 | 0.0 | 1.0 |
| signature_only | ok | 3 | 0.3333333333333333 | 0.3571428571428571 | 0.0 | 1.0 |
| signature_plus_doc | ok | 3 | 0.3333333333333333 | 0.1923076923076923 | 0.0 | 1.0 |
| ast_header | ok | 3 | 0.0 | 0.11494252873563218 | 0.0 | 1.0 |
| raw_code_trimmed | ok | 3 | 0.3333333333333333 | 0.29411764705882354 | 0.0 | 1.0 |
| comment_docstring | ok | 1 | 0.0 | 0.0 | 0.0 | 1.0 |
| test_name_plus_assert_terms | ok | 1 | 0.0 | 0.0 | 0.0 | 1.0 |
| config_key_plus_context | ok | 1 | 0.3333333333333333 | 0.19607843137254902 | 0.0 | 1.0 |
| route_plus_handler_signature | ok | 0 | 0.0 | 0.0 | 0.0 | 1.0 |
| mixed_all_views | ok | 9 | 0.6666666666666666 | 0.37878787878787873 | 0.0 | 1.0 |

## Conclusion

- best_dense_view: `path_plus_symbol`
- worst_dense_view: `route_plus_handler_signature`
- dense_should_remain_supporting_only: `True`
- All R32 outputs must report `delta_vs_r29_rrf`, `delta_vs_r29_query_noise_guard`, and `delta_vs_r29_symbol` inside `delta_vs_r29_baseline`.

