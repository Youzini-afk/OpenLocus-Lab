# R39-R40 Symbol and Regex Repair

> 中文译本待补充。The full Chinese translation is pending.
> 这是同名文件的占位符：保留英文原文，方便未来翻译对照。

## English source / 英文原文

# R39-R40 Symbol and Regex Repair

This phase evaluates symbol extraction and regex normalization repairs without changing default retrieval behavior.

## Safety

- promotion_ready: `False`
- default_should_change: `False`
- evidencecore_semantics_changed: `False`
- run_phase_public_only: `True`

## Symbol Repair

- symbol_FileRecall_delta: `0.2`
- symbol_abstain_delta: `-0.20000000000000007`
- symbol_false_primary_delta: `0.0`
- gate_false_primary_within_plus_0_02: `True`

## Regex Repair

- best_regex_mode: `regex_hybrid_normalized`
- default_recommendation: `do_not_use_raw_regex_for_user_query_by_default`

| Mode | parse_error_rate | FileRecall@1 | SpanF0.5 | primary_false_positive_rate |
|---|---:|---:|---:|---:|
| regex_raw | 0.0 | 0.6 | 0.5172413793103449 | 0.0 |
| regex_escaped_literal | 0.0 | 0.6 | 0.5172413793103449 | 0.0 |
| regex_tokenized | 0.0 | 0.8 | 0.717948717948718 | 0.0 |
| regex_identifier_mode | 0.2 | 0.6 | 0.6 | 0.0 |
| regex_path_mode | 0.0 | 0.6 | 0.5172413793103449 | 0.0 |
| regex_hybrid_normalized | 0.0 | 0.8 | 0.8333333333333334 | 0.0 |

## Decision

- User queries should not be interpreted as raw regex by default.
- Symbol repair remains a candidate for later integration only after broader R26/R38 validation.

