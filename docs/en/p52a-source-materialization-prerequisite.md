# P52A Source Materialization / Local Verifier Prerequisite

- Schema: `p52a-source-materialization-prerequisite-v1`
- Generated: 2026-06-15T18:38:59.288011+00:00
- Status: `self_test_only`
- Self-test: True
- Remote calls by P52A: 0
- LLM calls by P52A: 0
- Prompt construction by P52A: False
- Source reads attempted by P52A: True
- Tasks: 5 positive=3 no_gold=2
- Repo lock source: `provided`
- Source root source: `provided`
- Source read availability: `partial`
- Materialization prerequisite availability: `partial`

## Purpose

P52A reads local source files only for bounded aggregate materialization diagnostics. It is a SCORE-phase-only prerequisite evaluator, not a verifier pass/fail phase.

## Methodology

- Load `p25-policy-records-ephemeral-v1` records (or deterministic self-test records).
- Resolve a safe, local repo root for each task from `--repo-lock` or `--source-root` fallback.
- Normalize candidates with P46/P49 helpers, preserving only public metadata.
- Perform bounded source reads per candidate, subject to byte/line/file/candidate caps and secret-path/text scans.
- Discard raw text after aggregate counters and lightweight heuristics; never store source, snippets, digests, paths, or spans.
- Rebuild P49 packs in-memory and report aggregate pack-level materialization diagnostics.
- Gold/outcome signals are used only inside explicitly-marked SCORE-phase diagnostics `not_used_for_materialization_decision=true`.

## Safety notes

- P52A reads local source only for bounded aggregate materialization diagnostics.
- P52A stores no raw source, snippets, digests, paths, or spans.
- Source read is not Evidence.
- Materialized candidate is not Evidence.
- P52A does not validate EvidenceCore.
- P52A does not produce verifier pass/fail or default/promotion claims.
- P52A does not call an LLM, construct prompts, or make remote calls.

## Source materialization metrics

| Denom | Attempts | Success | Resolved | Missing | InvalidPath | Escape | TooLarge | Binary | Secret | RangeValid | DigestMatch |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 11 | 11 | 8 | 8 | 1 | 2 | 0 | 0 | 0 | 1 | 5 | 1 |

- Span width after read (valid ranges): mean=5.4000, p95=6.0000; over cap (80 lines): 0
- Line range clamped: `not_performed_no_silent_clamp` (count=None); invalid ranges are counted, not silently clamped.

## Source-required verifier availability

| Verifier | Availability | Checkable | Positive |
|---|---|---:|---:|
| line_range_verified_against_current_file | `available` | 5.0000 | n/a |
| source_text_span_width_verified | `available` | 5.0000 | n/a |
| content_digest_verified | `available_if_candidate_digest_present` | 3.0000 | 1.0000 |
| comment_only_flag | `partial_heuristic_line_prefix_only` | 5.0000 | n/a |
| signature_like_line_heuristic | `partial_heuristic_regex_only` | 5.0000 | 3.0000 |
| ast_node_kind | `unavailable_ast_parser_not_wired` | n/a | n/a |
| exact_identifier_in_span | `unavailable_raw_query_not_public` | n/a | n/a |
| query_terms_in_span | `unavailable_raw_query_not_public` | n/a | n/a |
| signature_match | `unavailable_parser_not_wired` | n/a | n/a |
| identifier_density | `unavailable_parser_not_wired` | n/a | n/a |
| term_density | `unavailable_raw_query_not_public` | n/a | n/a |
| intent_identifier_match | `unavailable_raw_query_not_public` | n/a | n/a |
| import_only_flag | `unavailable_parser_not_wired` | n/a | n/a |
| test_assertion_context | `unavailable_parser_not_wired` | n/a | n/a |

## Pack materialization metrics (task-wide)

| Denom | AllResolved | StaleDigest | InvalidRange | NeedsSource | PrereqAvail |
|---:|---:|---:|---:|---:|---:|
| 12 | 0.7500 | 0.2500 | 0.2500 | 0.7500 | 0.5000 |

## SCORE-phase diagnostics (not used for materialization decisions)

| GoldFileReadable | GoldSpanRangeValid | GoldSpanPrereq | FileRightSpanWrong | NoGoldReadable | NoGoldRangeValid |
|---:|---:|---:|---:|---:|---:|
| 0.6667 | 0.3333 | 0.3333 | 0.6667 | 1.0000 | 1.0000 |

## Conclusion

- Self-test-only materialization prerequisite diagnosed 11 synthetic candidates across 5 tasks; this is not quality evidence.
- P52A reads local source files only for bounded aggregate materialization diagnostics. Raw source text, snippets, digests, paths, and spans are not stored.
- Source read is not Evidence; materialized candidate is not Evidence; P52A does not validate EvidenceCore and does not produce verifier pass/fail or default/promotion claims.
- Source-read availability: `partial`; materialization prerequisite availability: `partial`.
