# BEA-v1-N2 Rank/Pack Actionability Decomposition

Date: 2026-06-27

BEA-v1-N2 is an empirical decomposition stage after BEA-v1-N1. N1 closed as a rank-blocked No-Go (`no_go_n1_inadequate_top10_actionable_denominator`): D0 scheduler preservation passed on the locked 272-record non-Python denominator, but all 40 D1 span opportunities were outside the actionable top-10 pack.

N2 asks why frozen P4 reaches the gold file somewhere in the final pool but does not place the gold-file evidence in the top-10 pack. It is **decomposition only**. It does not implement or authorize P5, BEA-v1-A, selector/reranker changes, runtime/default promotion, method-winner claims, broad retrieval expansion, or downstream-value claims.

## Inputs and replay contract

The evaluator validates the closed N1 public artifact from result checkpoint `e6772dc` / CI `28245155237`:

- status: `no_go_n1_inadequate_top10_actionable_denominator`;
- D0 locked denominator: 272;
- frozen scheduler reach: baseline 0, P2 55, P3 55, P4 52;
- P4 treatment hard-cap violations: 0;
- D1 total: 40;
- D1 top-10 actionable: 0;
- D1 rank-blocked: 40;
- public forbidden scan: pass.

Network-enabled N2 does not rely on the N1 public artifact alone, but it also does not rerun the full four-arm P4L scheduler validation. It binds closed N1's D0 scheduler-preservation artifact, regenerates FD1 private decomposition under `/tmp`, validates the private replay, reconstructs the P4L locked denominator, and calls `n1._run_frozen_p4_with_candidates(...)` directly so ordered final candidates retain private rank/score/method fields. Private rank/pack rows are written only under `/tmp`.

The default no-network artifact is intentionally `unavailable_with_reason` and is not an empirical result.

## D2 denominator

`D2_total` is the N1 rank-blocked subset where:

- gold line ranges are privately reconstructable;
- frozen P4 reaches the gold file somewhere in the final pool;
- the pre-refiner gold-file span has zero or inadequate overlap;
- the first gold-file evidence is not in top-10;
- candidate order/rank is privately available for the D2 row. Candidate-order
  misses outside the reconstructed D2=40 denominator are reported as diagnostics
  and do not block the mechanism decomposition.

Adequacy gates:

- `D2_total >= 20`: adequate;
- `10 <= D2_total < 20`: exploratory;
- `D2_total < 10`: No-Go.

## Analyses

For each D2 row, N2 computes private exact diagnostics and publishes only sanitized buckets:

- first gold-file rank bucket: `rank_11_20`, `rank_21_50`, `rank_51_100`, `rank_gt_100`, or `rank_missing_or_invalid`;
- top20/top50/top100 rank-preserving recovery buckets;
- rank-preserving unique-file top-10 recovery bucket;
- duplicate pressure bucket;
- evidence materialization boolean;
- primary blocker bucket, exactly one of `pack_budget_only`, `duplicate_file_pack_waste`, `extra_depth_append_blocked`, `candidate_order_blocked`, `scheduler_cap_or_stop_blocked`, `evidence_materialization_blocked`, or `mixed_or_unclassified`.

Classification counts must sum to `D2_total`; otherwise the run fail-closes.
The closed N1 D2 denominator is exactly 40; if candidate-order loss prevents
reconstructing those 40 rows, the run fail-closes rather than publishing a
partial mechanism claim.

## Design-only authorization

N2 may authorize only later design work, never implementation. The design-only thresholds are:

- pack-budget design: `top20_recovery_rate >= 0.50`;
- rank-preserving pack design: `unique_file_pack_recovery_at10 >= 0.25`;
- extra-depth merge-order design: `extra_depth_append_blocked_rate >= 0.50`;
- evidence materialization design: `evidence_materialization_blocked_rate >= 0.25`.

If one or more thresholds cross, `design_authorized=true` and `design_authorized_scope` is one of `pack_budget_design_only`, `rank_preserving_pack_design_only`, `extra_depth_merge_order_design_only`, `evidence_materialization_design_only`, or `mixed_design_audit_only`. Implementation, P5, BEA-v1-A, selector/reranker execution, runtime promotion, and broad retrieval expansion remain unauthorized.

## Status vocabulary

- `unavailable_with_reason` — default no-network artifact; not an empirical result.
- `fail_schema_contract` — fail-closed infrastructure, parser, replay, D0 drift, classification, or private-write failure.
- `fail_forbidden_scan` — public artifact privacy scanner detected forbidden content.
- `no_go_n2_n1_artifact_or_trace_unavailable` — required N1 artifact or regenerated private traces are unavailable.
- `no_go_n2_insufficient_rank_blocked_denominator` — `D2_total < 10`.
- `n2_rank_pack_decomposition_exploratory` — `10 <= D2_total < 20`.
- `n2_rank_pack_mechanism_inconclusive` — D2 adequate and classified, but no design threshold crossed.
- `n2_rank_pack_actionability_decomposition_pass` — D2 adequate, closed N1 D0 is bound, all rows classified, scanner passed, and at least one design-only threshold crossed.

## Privacy boundary

Public artifacts may include aggregate metrics plus scanner-validated sanitized rows only. They must not include raw paths, exact ranks, exact spans, gold lines, snippets/content, raw candidate lists, repo/task ids, private trace paths, prompts/responses, provider payloads, scores, or source-linkable hashes.

## Result

N2 is complete as a bounded empirical decomposition pass.

```text
empirical CI source: 28272769423
source checkpoint:   7c90213
status:              n2_rank_pack_actionability_decomposition_pass
D2 denominator:      40
design scope:        extra_depth_merge_order_design_only
```

The public artifact was copied from CI `28272769423` and then locally corrected
only for one non-gating D0 display field: `p4_p3_latency_ratio_observed` now
matches the closed N1 artifact value `0.662177`. The code fix for this display
bug is checkpoint `a5b519b`. Later reruns `28275921872` and `28277110197` did
not produce contradictory N2 evidence; they failed before a valid N2 artifact due
to transient locked-denominator reconstruction / FD1 prerequisite failure.

Key N2 findings:

- D2 reconstructed exactly: `40/40`.
- All D2 rows were classified: `40/40`.
- First gold-file rank bucket: `rank_21_50 = 40/40`.
- Top-20 recovery: `0/40`.
- Top-50 recovery: `40/40`.
- Top-100 recovery: `40/40`.
- Unique-file top-10 recovery: `0/40`.
- Primary blocker: `extra_depth_append_blocked = 40/40`.
- Evidence materializable: `40/40`.
- Hard-cap violations: `0`.
- Public forbidden scan: `pass`.

Decision: N2 authorizes only **extra-depth merge-order design** as the next
bounded research design problem. It does not authorize implementation, P5,
BEA-v1-A, selector/reranker execution, runtime/default promotion,
method-winner claims, broad retrieval expansion, downstream-value claims, or a
frozen P4 rerun.
