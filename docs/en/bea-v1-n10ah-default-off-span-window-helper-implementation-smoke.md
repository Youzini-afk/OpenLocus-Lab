# BEA-v1-N10AH Default-Off Span Window Helper Implementation Smoke

Date: 2026-06-29

BEA-v1-N10AH implements an isolated, pure, default-off span-window helper and validates it with synthetic checks only. It does not hook into existing evaluators or runtime/retrieval code.

## Result

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

- `expand_span_window(start, end, *, expansion_each_side, min_line=1)` returns `expanded_start_line` and `expanded_end_line`; validates integer inputs, `start <= end`, non-negative expansion, and `min_line >= 1`; clamps start to `min_line`.
- `expand_evidence_span_record(record, *, expansion_each_side)` returns a copy of the input mapping with `start_line`/`end_line` expanded; it preserves other fields and does not mutate input.

The helper requires no path, content, or gold input and performs no filesystem IO.

## Synthetic checks

N10AH validates pm20, pm50, and pm100 arithmetic; min-line clamp; zero expansion; invalid inputs; input immutability; and no path/content requirement.

## Boundary

N10AH is implementation-smoke only. It does not authorize hook-in, runtime/default enablement, retrieval/rerun, selector/reranker, P5, BEA-v1-A, private reads, candidate generation, gold-as-policy behavior, adaptive tuning, method-winner claims, or downstream-value claims.

## Decision

N10AH authorizes only `BEA-v1-N10AI Default-Off Span Window Helper Integration Preflight`; no actual hook-in or runtime/default promotion is authorized.

## Artifact

- Helper: `eval/bea_v1_span_window_repair_helpers.py`
- Script: `eval/bea_v1_n10ah_default_off_span_window_helper_implementation_smoke.py`
- Report: `artifacts/bea_v1_n10ah_default_off_span_window_helper_implementation_smoke/bea_v1_n10ah_default_off_span_window_helper_implementation_smoke_report.json`
