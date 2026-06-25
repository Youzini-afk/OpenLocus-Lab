# BEA-v1-N1: Frozen P4 + Span-Refiner Smoke

Date: 2026-06-25

BEA-v1-N1 is the first Report-4 span phase for BEA v1 hierarchical actionable evidence acquisition. It is a **retrieval-layer span smoke only**: regenerate/replay FD1 plus the frozen P4L locked denominator, preserve file/scheduler behavior, form a private wrong-span denominator, and test a post-P4 span refiner that may only adjust line ranges inside files already selected by frozen P4.

## Binding source context

- P4L source checkpoint: `f1bac81`; CI `28184096209`.
- Locked non-Python denominator: 272.
- Source reach: baseline 0, P2 55, P3 55, P4 52.
- P4 retained P2 gain: 0.945455.
- P4/P3 latency ratio: 0.656763.
- P4 treatment hard-cap violations: 0.

Network-enabled N1 is a real empirical replay, not a manual-row control plane. It regenerates FD1 private decomposition under `/tmp`, validates the 86040-row / 239-group FD1 replay and manifest hash, reconstructs the P4L locked non-Python denominator, privately re-reads raw benchmark frames to recover gold line ranges, runs the frozen P4 policy with private candidate `path/start_line/end_line` ranges, forms D1, and then emits an honest pass/preflight/exploratory/No-Go result. If infrastructure, parser, clone, replay, private-write, or invariant checks fail, the evaluator emits `fail_schema_contract`. The legacy manual private-input CLI path is debug-only and is not the network CI contract.

## Two-denominator design

- **D0 scheduler-preservation denominator** = P4L locked non-Python 272. D0 proves N1 instrumentation/wrapping preserves frozen scheduler behavior. It is **not** the span-success denominator.
- **D1 P4-compatible wrong-span denominator** = private records where gold line ranges are reconstructable, frozen P4 reaches a gold file, frozen P4 has candidate `start_line`/`end_line` for selected or packed evidence, and pre-refiner P4 evidence on the gold file has zero or inadequate line overlap.

D1 adequacy: pass/preflight adequate at `>=20`, exploratory at `10-19`, No-Go at `<10`.

## Refiner constraints

The N1 refiner is post-P4 and file-preserving only. It can narrow or expand line ranges inside files already selected/reached by frozen P4. It must not add, evict, or reorder files; change scheduler actions; use gold lines for refinement; run selector/reranker/P5/BEA-v1-A; or place latency in candidate relevance.

## Public artifact contract

The public report contains aggregate metrics plus scanner-validated sanitized per-record analysis rows only. Public rows use anonymous local IDs and bucketed fields:

- `anonymous_local_id`
- `denominator`
- `arm`
- `source_bucket`
- `language_bucket`
- `pre_span_bucket`
- `post_span_bucket`
- `span_delta_bucket`
- `file_reach_preserved`
- `evidencecore_valid`
- `hard_cap_violation`

Forbidden in public artifacts: raw prompts/responses/snippets/provider payloads, exact paths/spans, gold labels/lines, raw candidate lists, task IDs/row IDs/repo names if identifying, linkable content hashes, private paths, and unsanitized private per-record rows. Private manifests expose counts/hash provenance only; private trace paths are not serialized.

## Status vocabulary

- `unavailable_with_reason` — default no-network only; not a pass/no-go empirical result.
- `fail_schema_contract` — fail-closed instrumentation, parser, replay, private-write, or invariant failure.
- `fail_forbidden_scan` — public artifact privacy scanner blocked serialization.
- `no_go_n1_locked_denominator_unavailable` — the live P4L/P4K locked-denominator reconstruction drifted, so N1 did not run span claims.
- `n1_preflight_pass_wrong_span_denominator_adequate` — D0 preserved and D1 is adequate, but refiner improvement gates did not establish a positive span result.
- `n1_exploratory_insufficient_power` — D0 preserved but D1 is only 10-19.
- `no_go_n1_inadequate_wrong_span_denominator` — D0 preserved but D1 is below 10.
- `bea_v1_n1_frozen_p4_span_refiner_pass` — D0 preserved, D1 adequate, file-preserving invariant holds, and post-refiner span metrics improve.

## Metrics

Public metric tables are split into:

1. `d0_scheduler_preservation_records` — frozen P4L scheduler-preservation aggregates over the 272-record denominator.
2. `d1_span_efficacy_records` — pre/post retrieval span metrics on the D1 wrong-span denominator using canonical span metrics from `eval/score.py`.

## Explicit non-claims

This is not a default change, downstream-agent evaluation, selector/reranker result, P5 result, BEA-v1-A result, method-winner claim, provider result, or full benchmark claim. It is only a bounded retrieval-layer span smoke for frozen-P4-compatible wrong-span cases.
