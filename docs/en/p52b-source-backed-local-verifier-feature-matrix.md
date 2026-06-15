# P52B Source-Backed Local Verifier Feature Matrix

- Schema: `p52b-source-backed-local-verifier-feature-matrix-v1`
- Generated: 2026-06-15T19:17:32.316948+00:00
- Status: `self_test_only`
- Self-test: True
- Remote calls by P52B: 0
- LLM calls by P52B: 0
- Prompt construction by P52B: False
- Source reads attempted by P52B: True
- Tasks: 5 positive=3 no_gold=2
- Candidate pool availability: `partial`
- P52A report source: `not_provided`
- P49 report source: `not_provided`
- P50 report source: `not_provided`
- P48 report source: `not_provided`

## Purpose

P52B computes deterministic source-backed verifier feature diagnostics from bounded local source reads. It is a SCORE-phase-only feature matrix, not a verifier pass/fail phase and not an Evidence producer.

## Methodology

- Load `p25-policy-records-ephemeral-v1` records (or deterministic self-test records).
- Resolve a safe, local repo root for each task from `--repo-lock` or `--source-root` fallback using P52A helpers.
- Normalize candidates with P46/P49 helpers, preserving only public metadata.
- Perform bounded source reads per candidate, subject to P52A byte/line/file/candidate caps and secret-path/text scans.
- Discard raw text after aggregate source-shape heuristics; never store source, snippets, digests, paths, or spans.
- Classify each candidate into a source-feature risk bucket using bounded source shape and available metadata subtype signals.
- Rebuild P49 packs in-memory and report aggregate pack-level source-feature diagnostics.
- Gold/outcome signals are used only inside explicitly-marked SCORE-phase diagnostics `not_used_for_feature_construction=true`.

## Safety notes

- P52B does not create Evidence.
- P52B does not validate EvidenceCore.
- P52B does not admit candidates or change defaults.
- P52B does not produce a verifier pass/fail score or a local verifier score.
- Source-feature buckets are diagnostic only.
- P52B does not prove P51 quality and does not send source to providers.
- P52B does not call an LLM, construct prompts, or make remote calls.
- P52B stores no raw source, snippets, digests, paths, or spans.

## Source materialization metrics (P52A carry-forward)

| Denom | Attempts | Success | Resolved | RangeValid | DigestMatch |
|---:|---:|---:|---:|---:|---:|
| 11 | 11 | 8 | 8 | 5 | 1 |

## Source-backed feature availability

| Denom | BoundedSpanCandidates | BoundedSpanRate | HeuristicAvailRate |
|---:|---:|---:|---:|
| 11 | 5 | 0.4545 | 0.4545 |

## Source-shape heuristic features

| Feature | Checkable | PositiveRate |
|---|---|---:|
| span_nonempty | 5 | 1.0000 |
| span_blank_only | 5 | 0.0000 |
| span_comment_only_heuristic | 5 | 0.0000 |
| span_contains_code_like_token | 5 | 1.0000 |
| span_contains_assignment_like_token | 5 | 0.8000 |
| span_contains_call_like_token | 5 | 0.6000 |
| span_contains_definition_keyword | 5 | 0.6000 |
| signature_like_line_heuristic | 5 | 0.6000 |
| import_only_heuristic | 5 | 0.0000 |
| test_assertion_like_heuristic | 5 | 0.0000 |

## Source-vs-metadata consistency

| Checkable | Consistent | SourceTestAssert | TestDefinition | DocConfigCode | WidthMatches |
|---:|---:|---:|---:|---:|---:|
| 5 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |

## Source-feature bucket v0

| Bucket | Count | Rate |
|---|---:|---:|
| source_feature_low_risk | 1 | 0.0909 |
| source_feature_medium_risk | 2 | 0.1818 |
| source_feature_high_risk | 8 | 0.7273 |
| source_feature_unavailable | 0 | 0.0000 |

## Pack source-feature diagnostics (task-wide)

| Denom | LowRiskAnchor | HighRiskCand | AllAvail | AnyUnavail | AnyDigestMismatch | AnyCommentOnly | AnyImportOnly | AnySignatureLike | Diversity |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 12 | 0.2500 | 0.5000 | 0.7500 | 0.2500 | 0.2500 | 0.0000 | 0.0000 | 0.7500 | 0.2500 |
- Slot tagging: `unavailable_slot_tagging_not_wired`

## SCORE-phase diagnostic correlations (not used for feature construction)

| Bucket | Candidates | GoldFile | GoldSpan | FileRightSpanWrong |
|---:|---:|---:|---:|---:|
| source_feature_low_risk | 1 | 1.0000 | 1.0000 | 0.0000 |
| source_feature_medium_risk | 1 | 1.0000 | 0.0000 | 1.0000 |
| source_feature_high_risk | 1 | 1.0000 | 0.0000 | 1.0000 |
| source_feature_unavailable | 0 | n/a | n/a | n/a |

- No-gold high-risk candidate rate: 0.8750 (7/8)
- No-gold low-risk candidate rate: 0.0000 (0/8)
- Digest-mismatch gold-span rate: 0.0000 (0)
- Comment-only gold-span rate: 0.0000 (0)
- Signature-like gold-span rate: 1.0000 (1)

## Conclusion

- Self-test-only source-backed feature matrix diagnosed 11 synthetic candidates across 5 tasks; this is not quality evidence.
- P52B reads local source files only for bounded aggregate source-shape heuristics. Raw source text, snippets, digests, paths, and spans are not stored.
- Source-feature buckets are diagnostics only; they are not Evidence, do not admit candidates, and do not produce a verifier pass/fail score or default/promotion claim.
- Bounded-span feature availability: 5/11; heuristic feature availability rate: 0.454545.
