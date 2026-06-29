# BEA-v1-N10AH Default-Off Span Window Helper Implementation Smoke

日期：2026-06-29

BEA-v1-N10AH 实现 isolated、pure、default-off span-window helper，并仅用 synthetic checks 验证。它不 hook into existing evaluators，也不修改 runtime/retrieval code。

## 结果

```text
status: default_off_span_window_helper_implementation_smoke_pass_n10ai_authorized
self-test: 15 / 15
forbidden scan: pass
helper functions: 2
synthetic validations: 8
private reads: 0
helper filesystem IO: false
hook-in to existing evaluators: false
runtime/default config changed: false
```

## Helper API

- `expand_span_window(start, end, *, expansion_each_side, min_line=1)` 返回 `expanded_start_line` 与 `expanded_end_line`；验证 integer inputs、`start <= end`、non-negative expansion 与 `min_line >= 1`；并将 start clamp 到 `min_line`。
- `expand_evidence_span_record(record, *, expansion_each_side)` 返回 input mapping 的 copy，只扩展 `start_line`/`end_line`；保留其他字段且不 mutate input。

该 helper 不需要 path、content 或 gold input，也不执行 filesystem IO。

## Synthetic checks

N10AH 验证 pm20、pm50、pm100 arithmetic；min-line clamp；zero expansion；invalid inputs；input immutability；以及 no path/content requirement。

## Boundary

N10AH 仅为 implementation-smoke。不授权 hook-in、runtime/default enablement、retrieval/rerun、selector/reranker、P5、BEA-v1-A、private reads、candidate generation、gold-as-policy behavior、adaptive tuning、method-winner claims 或 downstream-value claims。

## 决策

N10AH 只授权 `BEA-v1-N10AI Default-Off Span Window Helper Integration Preflight`；不授权 actual hook-in 或 runtime/default promotion。

## Artifact

- Helper: `eval/bea_v1_span_window_repair_helpers.py`
- Script: `eval/bea_v1_n10ah_default_off_span_window_helper_implementation_smoke.py`
- Report: `artifacts/bea_v1_n10ah_default_off_span_window_helper_implementation_smoke/bea_v1_n10ah_default_off_span_window_helper_implementation_smoke_report.json`
