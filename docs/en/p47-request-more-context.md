# P47 Request-More-Context / Span-Geometry Diagnostic

- Schema: `p47-request-more-context-v1`
- Generated: 2026-06-15T15:20:59.395483+00:00
- Status: `self_test_only`
- Self-test: True
- Remote calls by P47: 0
- Source reads attempted: False
- Source read availability: `not_attempted_first_tranche`
- AST trim availability: `unavailable_no_source_root`
- Candidate pool availability: `partial`
- Gold span availability: `available`
- Reach metrics available: True
- Tasks: 4 positive=3 no_gold=1

## Purpose

P47 measures whether enlarging candidate line ranges captures gold spans without reading source files or changing Rust/EvidenceCore semantics. It is a diagnostic-only, SCORE-phase follow-on that uses ephemeral metadata from P25/P46.

## Methodology

- Variants: raw candidate span, ±small neighbor window, ±medium neighbor window with width cap, conservative request-more-context gate, and AST/source-trim (unavailable).
- Metrics are aggregate only: reach, absent rate, file-right-span-wrong, repair-after-expansion, line budgets, and gap-type breakdowns.
- No source files are read; no remote model calls are made.
- Gold spans are used only after RUN for aggregate SCORE-phase metrics.

## Current placeholder findings

- This report is `self_test_only`; do not use it as quality evidence.
- Reach metrics available: True.
- Source reads: `False`; AST/source trim: `unavailable_no_source_root`.

## Variant metrics by strategy and K

| Strategy | Variant | K | GoldFileReach | GoldSpanReach | CandidateAbsent | FRSW | FRSWRepair | GoldGain | NoGoldExpanded | LineBudget | MeanLines | P95Lines | Overfetch |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| candidate_baseline | raw_candidate_span | 1 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 16 | 5.3333 | 5.9000 | 0.0000 |
| candidate_baseline | raw_candidate_span | 3 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 22 | 5.5000 | 6.0000 | 0.0000 |
| candidate_baseline | raw_candidate_span | 5 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 22 | 5.5000 | 6.0000 | 0.0000 |
| candidate_baseline | raw_candidate_span | 10 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 22 | 5.5000 | 6.0000 | 0.0000 |
| candidate_baseline | raw_candidate_span | 20 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 22 | 5.5000 | 6.0000 | 0.0000 |
| candidate_baseline | neighbor_window_small | 1 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 1.0000 | 28 | 9.3333 | 11.6000 | 0.7500 |
| candidate_baseline | neighbor_window_small | 3 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 1.0000 | 40 | 10.0000 | 12.0000 | 0.8182 |
| candidate_baseline | neighbor_window_small | 5 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 1.0000 | 40 | 10.0000 | 12.0000 | 0.8182 |
| candidate_baseline | neighbor_window_small | 10 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 1.0000 | 40 | 10.0000 | 12.0000 | 0.8182 |
| candidate_baseline | neighbor_window_small | 20 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 1.0000 | 40 | 10.0000 | 12.0000 | 0.8182 |
| candidate_baseline | neighbor_window_medium | 1 | 1.0000 | 1.0000 | 0.0000 | 0.5000 | 1.0000 | 0.5000 | 1.0000 | 55 | 18.3333 | 24.0000 | 2.4375 |
| candidate_baseline | neighbor_window_medium | 3 | 1.0000 | 1.0000 | 0.0000 | 0.5000 | 1.0000 | 0.5000 | 1.0000 | 81 | 20.2500 | 25.8500 | 2.6818 |
| candidate_baseline | neighbor_window_medium | 5 | 1.0000 | 1.0000 | 0.0000 | 0.5000 | 1.0000 | 0.5000 | 1.0000 | 81 | 20.2500 | 25.8500 | 2.6818 |
| candidate_baseline | neighbor_window_medium | 10 | 1.0000 | 1.0000 | 0.0000 | 0.5000 | 1.0000 | 0.5000 | 1.0000 | 81 | 20.2500 | 25.8500 | 2.6818 |
| candidate_baseline | neighbor_window_medium | 20 | 1.0000 | 1.0000 | 0.0000 | 0.5000 | 1.0000 | 0.5000 | 1.0000 | 81 | 20.2500 | 25.8500 | 2.6818 |
| candidate_baseline | request_more_context_gate_v0 | 1 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 22 | 7.3333 | 11.3000 | 0.3750 |
| candidate_baseline | request_more_context_gate_v0 | 3 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 28 | 7.0000 | 11.1000 | 0.2727 |
| candidate_baseline | request_more_context_gate_v0 | 5 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 28 | 7.0000 | 11.1000 | 0.2727 |
| candidate_baseline | request_more_context_gate_v0 | 10 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 28 | 7.0000 | 11.1000 | 0.2727 |
| candidate_baseline | request_more_context_gate_v0 | 20 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 28 | 7.0000 | 11.1000 | 0.2727 |
| candidate_baseline | ast_symbol_trim_unavailable | - | `unavailable_no_source_root` | - | - | - | - | - | - | - | - | - | - |
| rrf_primary | raw_candidate_span | 1 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 11 | 5.5000 | 5.9500 | 0.0000 |
| rrf_primary | raw_candidate_span | 3 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 11 | 5.5000 | 5.9500 | 0.0000 |
| rrf_primary | raw_candidate_span | 5 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 11 | 5.5000 | 5.9500 | 0.0000 |
| rrf_primary | raw_candidate_span | 10 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 11 | 5.5000 | 5.9500 | 0.0000 |
| rrf_primary | raw_candidate_span | 20 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 11 | 5.5000 | 5.9500 | 0.0000 |
| rrf_primary | neighbor_window_small | 1 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 20 | 10.0000 | 11.8000 | 0.8182 |
| rrf_primary | neighbor_window_small | 3 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 20 | 10.0000 | 11.8000 | 0.8182 |
| rrf_primary | neighbor_window_small | 5 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 20 | 10.0000 | 11.8000 | 0.8182 |
| rrf_primary | neighbor_window_small | 10 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 20 | 10.0000 | 11.8000 | 0.8182 |
| rrf_primary | neighbor_window_small | 20 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 20 | 10.0000 | 11.8000 | 0.8182 |
| rrf_primary | neighbor_window_medium | 1 | 1.0000 | 1.0000 | 0.0000 | 0.5000 | 1.0000 | 0.5000 | n/a | 40 | 20.0000 | 24.5000 | 2.6364 |
| rrf_primary | neighbor_window_medium | 3 | 1.0000 | 1.0000 | 0.0000 | 0.5000 | 1.0000 | 0.5000 | n/a | 40 | 20.0000 | 24.5000 | 2.6364 |
| rrf_primary | neighbor_window_medium | 5 | 1.0000 | 1.0000 | 0.0000 | 0.5000 | 1.0000 | 0.5000 | n/a | 40 | 20.0000 | 24.5000 | 2.6364 |
| rrf_primary | neighbor_window_medium | 10 | 1.0000 | 1.0000 | 0.0000 | 0.5000 | 1.0000 | 0.5000 | n/a | 40 | 20.0000 | 24.5000 | 2.6364 |
| rrf_primary | neighbor_window_medium | 20 | 1.0000 | 1.0000 | 0.0000 | 0.5000 | 1.0000 | 0.5000 | n/a | 40 | 20.0000 | 24.5000 | 2.6364 |
| rrf_primary | request_more_context_gate_v0 | 1 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 17 | 8.5000 | 11.6500 | 0.5455 |
| rrf_primary | request_more_context_gate_v0 | 3 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 17 | 8.5000 | 11.6500 | 0.5455 |
| rrf_primary | request_more_context_gate_v0 | 5 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 17 | 8.5000 | 11.6500 | 0.5455 |
| rrf_primary | request_more_context_gate_v0 | 10 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 17 | 8.5000 | 11.6500 | 0.5455 |
| rrf_primary | request_more_context_gate_v0 | 20 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 17 | 8.5000 | 11.6500 | 0.5455 |
| rrf_primary | ast_symbol_trim_unavailable | - | `unavailable_no_source_root` | - | - | - | - | - | - | - | - | - | - |
| symbol_primary | raw_candidate_span | 1 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | n/a | 0.0000 | n/a | 6 | 6.0000 | 6.0000 | 0.0000 |
| symbol_primary | raw_candidate_span | 3 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | n/a | 0.0000 | n/a | 6 | 6.0000 | 6.0000 | 0.0000 |
| symbol_primary | raw_candidate_span | 5 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | n/a | 0.0000 | n/a | 6 | 6.0000 | 6.0000 | 0.0000 |
| symbol_primary | raw_candidate_span | 10 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | n/a | 0.0000 | n/a | 6 | 6.0000 | 6.0000 | 0.0000 |
| symbol_primary | raw_candidate_span | 20 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | n/a | 0.0000 | n/a | 6 | 6.0000 | 6.0000 | 0.0000 |
| symbol_primary | neighbor_window_small | 1 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | n/a | 0.0000 | n/a | 12 | 12.0000 | 12.0000 | 1.0000 |
| symbol_primary | neighbor_window_small | 3 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | n/a | 0.0000 | n/a | 12 | 12.0000 | 12.0000 | 1.0000 |
| symbol_primary | neighbor_window_small | 5 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | n/a | 0.0000 | n/a | 12 | 12.0000 | 12.0000 | 1.0000 |
| symbol_primary | neighbor_window_small | 10 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | n/a | 0.0000 | n/a | 12 | 12.0000 | 12.0000 | 1.0000 |
| symbol_primary | neighbor_window_small | 20 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | n/a | 0.0000 | n/a | 12 | 12.0000 | 12.0000 | 1.0000 |
| symbol_primary | neighbor_window_medium | 1 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | n/a | 0.0000 | n/a | 25 | 25.0000 | 25.0000 | 3.1667 |
| symbol_primary | neighbor_window_medium | 3 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | n/a | 0.0000 | n/a | 25 | 25.0000 | 25.0000 | 3.1667 |
| symbol_primary | neighbor_window_medium | 5 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | n/a | 0.0000 | n/a | 25 | 25.0000 | 25.0000 | 3.1667 |
| symbol_primary | neighbor_window_medium | 10 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | n/a | 0.0000 | n/a | 25 | 25.0000 | 25.0000 | 3.1667 |
| symbol_primary | neighbor_window_medium | 20 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | n/a | 0.0000 | n/a | 25 | 25.0000 | 25.0000 | 3.1667 |
| symbol_primary | request_more_context_gate_v0 | 1 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | n/a | 0.0000 | n/a | 12 | 12.0000 | 12.0000 | 1.0000 |
| symbol_primary | request_more_context_gate_v0 | 3 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | n/a | 0.0000 | n/a | 12 | 12.0000 | 12.0000 | 1.0000 |
| symbol_primary | request_more_context_gate_v0 | 5 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | n/a | 0.0000 | n/a | 12 | 12.0000 | 12.0000 | 1.0000 |
| symbol_primary | request_more_context_gate_v0 | 10 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | n/a | 0.0000 | n/a | 12 | 12.0000 | 12.0000 | 1.0000 |
| symbol_primary | request_more_context_gate_v0 | 20 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | n/a | 0.0000 | n/a | 12 | 12.0000 | 12.0000 | 1.0000 |
| symbol_primary | ast_symbol_trim_unavailable | - | `unavailable_no_source_root` | - | - | - | - | - | - | - | - | - | - |
| regex_primary | raw_candidate_span | 1 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| regex_primary | raw_candidate_span | 3 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| regex_primary | raw_candidate_span | 5 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| regex_primary | raw_candidate_span | 10 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| regex_primary | raw_candidate_span | 20 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| regex_primary | neighbor_window_small | 1 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| regex_primary | neighbor_window_small | 3 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| regex_primary | neighbor_window_small | 5 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| regex_primary | neighbor_window_small | 10 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| regex_primary | neighbor_window_small | 20 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| regex_primary | neighbor_window_medium | 1 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| regex_primary | neighbor_window_medium | 3 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| regex_primary | neighbor_window_medium | 5 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| regex_primary | neighbor_window_medium | 10 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| regex_primary | neighbor_window_medium | 20 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| regex_primary | request_more_context_gate_v0 | 1 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| regex_primary | request_more_context_gate_v0 | 3 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| regex_primary | request_more_context_gate_v0 | 5 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| regex_primary | request_more_context_gate_v0 | 10 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| regex_primary | request_more_context_gate_v0 | 20 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| regex_primary | ast_symbol_trim_unavailable | - | `unavailable_no_source_root` | - | - | - | - | - | - | - | - | - | - |
| symbol_regex_union | raw_candidate_span | 1 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 17 | 5.6667 | 6.0000 | 0.0000 |
| symbol_regex_union | raw_candidate_span | 3 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 17 | 5.6667 | 6.0000 | 0.0000 |
| symbol_regex_union | raw_candidate_span | 5 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 17 | 5.6667 | 6.0000 | 0.0000 |
| symbol_regex_union | raw_candidate_span | 10 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 17 | 5.6667 | 6.0000 | 0.0000 |
| symbol_regex_union | raw_candidate_span | 20 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 17 | 5.6667 | 6.0000 | 0.0000 |
| symbol_regex_union | neighbor_window_small | 1 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 1.0000 | 32 | 10.6667 | 12.0000 | 0.8824 |
| symbol_regex_union | neighbor_window_small | 3 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 1.0000 | 32 | 10.6667 | 12.0000 | 0.8824 |
| symbol_regex_union | neighbor_window_small | 5 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 1.0000 | 32 | 10.6667 | 12.0000 | 0.8824 |
| symbol_regex_union | neighbor_window_small | 10 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 1.0000 | 32 | 10.6667 | 12.0000 | 0.8824 |
| symbol_regex_union | neighbor_window_small | 20 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 1.0000 | 32 | 10.6667 | 12.0000 | 0.8824 |
| symbol_regex_union | neighbor_window_medium | 1 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 1.0000 | 66 | 22.0000 | 25.9000 | 2.8824 |
| symbol_regex_union | neighbor_window_medium | 3 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 1.0000 | 66 | 22.0000 | 25.9000 | 2.8824 |
| symbol_regex_union | neighbor_window_medium | 5 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 1.0000 | 66 | 22.0000 | 25.9000 | 2.8824 |
| symbol_regex_union | neighbor_window_medium | 10 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 1.0000 | 66 | 22.0000 | 25.9000 | 2.8824 |
| symbol_regex_union | neighbor_window_medium | 20 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 1.0000 | 66 | 22.0000 | 25.9000 | 2.8824 |
| symbol_regex_union | request_more_context_gate_v0 | 1 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 23 | 7.6667 | 11.4000 | 0.3529 |
| symbol_regex_union | request_more_context_gate_v0 | 3 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 23 | 7.6667 | 11.4000 | 0.3529 |
| symbol_regex_union | request_more_context_gate_v0 | 5 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 23 | 7.6667 | 11.4000 | 0.3529 |
| symbol_regex_union | request_more_context_gate_v0 | 10 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 23 | 7.6667 | 11.4000 | 0.3529 |
| symbol_regex_union | request_more_context_gate_v0 | 20 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 23 | 7.6667 | 11.4000 | 0.3529 |
| symbol_regex_union | ast_symbol_trim_unavailable | - | `unavailable_no_source_root` | - | - | - | - | - | - | - | - | - | - |
| llm_span_narrow | raw_candidate_span | 1 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 12 | 6.0000 | 6.0000 | 0.0000 |
| llm_span_narrow | raw_candidate_span | 3 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 12 | 6.0000 | 6.0000 | 0.0000 |
| llm_span_narrow | raw_candidate_span | 5 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 12 | 6.0000 | 6.0000 | 0.0000 |
| llm_span_narrow | raw_candidate_span | 10 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 12 | 6.0000 | 6.0000 | 0.0000 |
| llm_span_narrow | raw_candidate_span | 20 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 12 | 6.0000 | 6.0000 | 0.0000 |
| llm_span_narrow | neighbor_window_small | 1 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 24 | 12.0000 | 12.0000 | 1.0000 |
| llm_span_narrow | neighbor_window_small | 3 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 24 | 12.0000 | 12.0000 | 1.0000 |
| llm_span_narrow | neighbor_window_small | 5 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 24 | 12.0000 | 12.0000 | 1.0000 |
| llm_span_narrow | neighbor_window_small | 10 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 24 | 12.0000 | 12.0000 | 1.0000 |
| llm_span_narrow | neighbor_window_small | 20 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 24 | 12.0000 | 12.0000 | 1.0000 |
| llm_span_narrow | neighbor_window_medium | 1 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 51 | 25.5000 | 25.9500 | 3.2500 |
| llm_span_narrow | neighbor_window_medium | 3 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 51 | 25.5000 | 25.9500 | 3.2500 |
| llm_span_narrow | neighbor_window_medium | 5 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 51 | 25.5000 | 25.9500 | 3.2500 |
| llm_span_narrow | neighbor_window_medium | 10 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 51 | 25.5000 | 25.9500 | 3.2500 |
| llm_span_narrow | neighbor_window_medium | 20 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 51 | 25.5000 | 25.9500 | 3.2500 |
| llm_span_narrow | request_more_context_gate_v0 | 1 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 18 | 9.0000 | 11.7000 | 0.5000 |
| llm_span_narrow | request_more_context_gate_v0 | 3 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 18 | 9.0000 | 11.7000 | 0.5000 |
| llm_span_narrow | request_more_context_gate_v0 | 5 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 18 | 9.0000 | 11.7000 | 0.5000 |
| llm_span_narrow | request_more_context_gate_v0 | 10 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 18 | 9.0000 | 11.7000 | 0.5000 |
| llm_span_narrow | request_more_context_gate_v0 | 20 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 18 | 9.0000 | 11.7000 | 0.5000 |
| llm_span_narrow | ast_symbol_trim_unavailable | - | `unavailable_no_source_root` | - | - | - | - | - | - | - | - | - | - |
| llm_filter | raw_candidate_span | 1 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 11 | 5.5000 | 5.9500 | 0.0000 |
| llm_filter | raw_candidate_span | 3 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 11 | 5.5000 | 5.9500 | 0.0000 |
| llm_filter | raw_candidate_span | 5 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 11 | 5.5000 | 5.9500 | 0.0000 |
| llm_filter | raw_candidate_span | 10 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 11 | 5.5000 | 5.9500 | 0.0000 |
| llm_filter | raw_candidate_span | 20 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 11 | 5.5000 | 5.9500 | 0.0000 |
| llm_filter | neighbor_window_small | 1 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 20 | 10.0000 | 11.8000 | 0.8182 |
| llm_filter | neighbor_window_small | 3 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 20 | 10.0000 | 11.8000 | 0.8182 |
| llm_filter | neighbor_window_small | 5 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 20 | 10.0000 | 11.8000 | 0.8182 |
| llm_filter | neighbor_window_small | 10 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 20 | 10.0000 | 11.8000 | 0.8182 |
| llm_filter | neighbor_window_small | 20 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 20 | 10.0000 | 11.8000 | 0.8182 |
| llm_filter | neighbor_window_medium | 1 | 1.0000 | 1.0000 | 0.0000 | 0.5000 | 1.0000 | 0.5000 | n/a | 40 | 20.0000 | 24.5000 | 2.6364 |
| llm_filter | neighbor_window_medium | 3 | 1.0000 | 1.0000 | 0.0000 | 0.5000 | 1.0000 | 0.5000 | n/a | 40 | 20.0000 | 24.5000 | 2.6364 |
| llm_filter | neighbor_window_medium | 5 | 1.0000 | 1.0000 | 0.0000 | 0.5000 | 1.0000 | 0.5000 | n/a | 40 | 20.0000 | 24.5000 | 2.6364 |
| llm_filter | neighbor_window_medium | 10 | 1.0000 | 1.0000 | 0.0000 | 0.5000 | 1.0000 | 0.5000 | n/a | 40 | 20.0000 | 24.5000 | 2.6364 |
| llm_filter | neighbor_window_medium | 20 | 1.0000 | 1.0000 | 0.0000 | 0.5000 | 1.0000 | 0.5000 | n/a | 40 | 20.0000 | 24.5000 | 2.6364 |
| llm_filter | request_more_context_gate_v0 | 1 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 17 | 8.5000 | 11.6500 | 0.5455 |
| llm_filter | request_more_context_gate_v0 | 3 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 17 | 8.5000 | 11.6500 | 0.5455 |
| llm_filter | request_more_context_gate_v0 | 5 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 17 | 8.5000 | 11.6500 | 0.5455 |
| llm_filter | request_more_context_gate_v0 | 10 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 17 | 8.5000 | 11.6500 | 0.5455 |
| llm_filter | request_more_context_gate_v0 | 20 | 1.0000 | 0.5000 | 0.0000 | 0.5000 | 0.0000 | 0.0000 | n/a | 17 | 8.5000 | 11.6500 | 0.5455 |
| llm_filter | ast_symbol_trim_unavailable | - | `unavailable_no_source_root` | - | - | - | - | - | - | - | - | - | - |
| llm_abstain_filter | raw_candidate_span | 1 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| llm_abstain_filter | raw_candidate_span | 3 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| llm_abstain_filter | raw_candidate_span | 5 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| llm_abstain_filter | raw_candidate_span | 10 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| llm_abstain_filter | raw_candidate_span | 20 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| llm_abstain_filter | neighbor_window_small | 1 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| llm_abstain_filter | neighbor_window_small | 3 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| llm_abstain_filter | neighbor_window_small | 5 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| llm_abstain_filter | neighbor_window_small | 10 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| llm_abstain_filter | neighbor_window_small | 20 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| llm_abstain_filter | neighbor_window_medium | 1 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| llm_abstain_filter | neighbor_window_medium | 3 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| llm_abstain_filter | neighbor_window_medium | 5 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| llm_abstain_filter | neighbor_window_medium | 10 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| llm_abstain_filter | neighbor_window_medium | 20 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| llm_abstain_filter | request_more_context_gate_v0 | 1 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| llm_abstain_filter | request_more_context_gate_v0 | 3 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| llm_abstain_filter | request_more_context_gate_v0 | 5 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| llm_abstain_filter | request_more_context_gate_v0 | 10 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| llm_abstain_filter | request_more_context_gate_v0 | 20 | 0.0000 | 0.0000 | 1.0000 | n/a | n/a | 0.0000 | n/a | 0 | n/a | n/a | n/a |
| llm_abstain_filter | ast_symbol_trim_unavailable | - | `unavailable_no_source_root` | - | - | - | - | - | - | - | - | - | - |

## Request-more-context gate summary @5

| Strategy | Accepted | Rejected (raw kept) | AcceptRate | ExpandedCandidates |
|---|---:|---:|---:|---:|
| candidate_baseline | 1 | 3 | 0.2500 | 1 |
| rrf_primary | 1 | 1 | 0.5000 | 1 |
| symbol_primary | 1 | 0 | 1.0000 | 1 |
| regex_primary | 0 | 0 | n/a | 0 |
| symbol_regex_union | 1 | 2 | 0.3333 | 1 |
| llm_span_narrow | 1 | 1 | 0.5000 | 1 |
| llm_filter | 1 | 1 | 0.5000 | 1 |
| llm_abstain_filter | 0 | 0 | n/a | 0 |

## Hypothetical upper bound (gate accepts every top-5 candidate)

> This section is explicitly **not evidence**. It shows the small-window expansion upper bound on the same candidate set.

| Strategy | CandidateCount | GoldFileReach | GoldSpanReach | LineBudget | Overfetch | AcceptRate |
|---|---:|---:|---:|---:|---:|---:|
| candidate_baseline | 4 | 1.0000 | 0.5000 | 40 | 0.8182 | 1.0000 |
| rrf_primary | 2 | 1.0000 | 0.5000 | 20 | 0.8182 | 1.0000 |
| symbol_primary | 1 | 1.0000 | 1.0000 | 12 | 1.0000 | 1.0000 |
| regex_primary | 0 | 0.0000 | 0.0000 | 0 | n/a | n/a |
| symbol_regex_union | 3 | 1.0000 | 0.5000 | 32 | 0.8824 | 1.0000 |
| llm_span_narrow | 2 | 1.0000 | 0.5000 | 24 | 1.0000 | 1.0000 |
| llm_filter | 2 | 1.0000 | 0.5000 | 20 | 0.8182 | 1.0000 |
| llm_abstain_filter | 0 | 0.0000 | 0.0000 | 0 | n/a | n/a |

## Gap type breakdown (top candidate)

| Strategy | Adjacent/Overlap | SameFileNear | SameFileFar | CandidateAbsent |
|---|---:|---:|---:|---:|
| candidate_baseline | 0.5000 | 0.5000 | 0.0000 | 0.0000 |
| rrf_primary | 0.5000 | 0.5000 | 0.0000 | 0.0000 |
| symbol_primary | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| regex_primary | n/a | n/a | n/a | n/a |
| symbol_regex_union | 0.5000 | 0.0000 | 0.5000 | 0.0000 |
| llm_span_narrow | 0.5000 | 0.0000 | 0.5000 | 0.0000 |
| llm_filter | 0.5000 | 0.5000 | 0.0000 | 0.0000 |
| llm_abstain_filter | n/a | n/a | n/a | n/a |

## Safety notes

- No remote model calls were made during P47 evaluation.
- No source files were read and no AST/source trim was attempted.
- This report contains only aggregate counts/rates by strategy, variant, and gap type.
- No task IDs, candidate IDs, paths, spans, gold spans, private labels, route features, snippets, prompts, responses, or provider keys are stored.
- `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `candidate_not_fact=true`, `remote_calls_by_p47=0`, `source_reads_attempted=false`, `score_phase_only_metrics=true`, `aggregate_only_public_artifact=true`.
