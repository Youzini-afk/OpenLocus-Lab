# BEA-v1-N3 Extra-Depth Merge-Order Design Simulation

Date: 2026-06-27

BEA-v1-N3 is an offline deterministic design simulation over the closed BEA-v1-N2 D2=40 private candidate rows. It asks whether a frozen, non-learning, non-gold, merge-order-only policy can move N2's extra-depth gold-file candidates from ranks 21-50 into the actionable top-10 pack using the same candidate pool and budget.

N3 is **design/simulation only**. It does not implement or authorize P5, BEA-v1-A, selector/reranker execution, provider calls, new retrieval, broad retrieval expansion, runtime/default promotion, frozen P4 promotion, method-winner claims, or downstream-value claims.

## Closed N2 input contract

The evaluator validates the closed N2 public artifact from result checkpoint `ce47caf`, source checkpoint `7c90213`, empirical CI `28272769423`:

- status: `n2_rank_pack_actionability_decomposition_pass`;
- D2: 40;
- primary blocker `extra_depth_append_blocked`: 40;
- first gold-file rank bucket `rank_21_50`: 40;
- top20 recovery: 0;
- top50/top100 recovery: 40/40;
- unique-file top10 recovery: 0;
- evidence materializable: 40;
- forbidden scan: pass.

Network-enabled N3 regenerates private ordered rows under `/tmp` using N2/N1 helpers and reconstructs private D2 rows. It does **not** rerun the full P4L four-arm scheduler validation. The default no-network artifact is intentionally `unavailable_with_reason`.

## D3 denominator

`D3_total` equals the closed N2 D2 design denominator and is expected to be exactly 40:

- part of closed N2 D2;
- frozen P4 reaches gold file somewhere in the final pool;
- first gold-file rank bucket is `rank_21_50`;
- gold file absent from top-10;
- gold file present by top-50;
- evidence materializable;
- candidate order and channel/source metadata privately available.

If D3 cannot reconstruct exactly, N3 must emit a No-Go or fail-schema status rather than an approximate mechanism claim.

## Predeclared simulation arms

All arms reorder only existing frozen P4 candidates by source/channel/phase/original order. They use no gold labels in policy, no snippets/content relevance scoring, no learned weights, no new retrieval, and no new files.

1. `frozen_p4_order` — baseline diagnostic.
2. `fixed_interleave_2_primary_1_extra_after_4` — keep first 4 original candidates, then merge remaining primary and extra-depth as 2 primary : 1 extra.
3. `early_extra_depth_quota_3` — reserve 3 top-10 slots for first extra-depth candidates, preserving order.
4. `bounded_promotion_after_primary_prefix_4_3` — keep first 4 primary candidates fixed, then insert first 3 extra-depth candidates before remaining primary candidates.

## Pass criteria

`n3_merge_order_design_simulation_pass` requires: closed N2 artifact valid, `D3_total==40`, scanner pass, candidate pool unchanged, no retrieval expansion, no selector/reranker/P5/v1-A/provider path, and at least one non-baseline predeclared arm with:

- `top10_gold_file_recovery_rate >= 0.50`;
- hard-cap violation count 0;
- recovered evidence materializable rate >= 0.95;
- original top-10 file retention rate >= 0.50.

Recovery only with unacceptable retention/materialization/hard-cap tradeoff is `n3_merge_order_tradeoff_no_go`; no recovery threshold crossing is `n3_merge_order_design_inconclusive`.

## Public/private boundary

Public artifacts contain aggregate metrics plus scanner-validated sanitized rows only. Sanitized row fields are exactly: `anonymous_local_id`, `denominator`, `source_bucket`, `language_bucket`, `baseline_first_gold_rank_bucket`, `sim_arm`, `top10_recovery_bucket`, `evidencecore_materializable`, `original_top10_retention_bucket`, `duplicate_pressure_delta_bucket`, `hard_cap_violation`.

Forbidden publicly: raw paths, exact ranks, exact spans, gold lines, snippets/content, candidate lists, scores, task IDs, repo names if identifying, source-linkable hashes, private trace paths, prompts/responses, and provider payloads.

## Status vocabulary

- `unavailable_with_reason`
- `fail_schema_contract`
- `fail_forbidden_scan`
- `no_go_n3_n2_artifact_or_trace_unavailable`
- `no_go_n3_insufficient_design_denominator`
- `no_go_n3_incomplete_closed_n2_reconstruction`
- `n3_merge_order_design_exploratory`
- `n3_merge_order_design_inconclusive`
- `n3_merge_order_tradeoff_no_go`
- `n3_merge_order_design_simulation_pass`

## Result

N3 is complete as a bounded design-simulation run.

```text
local checkpoint: 76ebd32
manual CI:        28278662782
status:           n3_merge_order_design_inconclusive
D3 denominator:   40
```

The workflow passed, but the research result is **not** an N3 pass. D3
reconstructed exactly (`40/40`), the public forbidden scan passed, and the
simulation remained offline/deterministic with no candidate-pool changes, no new
retrieval, no selector/reranker, no P5, no BEA-v1-A, and no provider calls. The
predeclared merge-order arms did not reach the pass threshold:

```text
frozen_p4_order recovery:                       0 / 40
fixed_interleave_2_primary_1_extra_after_4:     8 / 40
early_extra_depth_quota_3:                     10 / 40
bounded_promotion_after_primary_prefix_4_3:    10 / 40

pass_eligible_nonbaseline_arm_count: 0
tradeoff_nonbaseline_arm_count:      0
```

The best recovery rate was `0.25`, below the predeclared `0.50` pass gate. The
two strongest arms preserved original top-10 file retention at `0.975`, recovered
evidence materializable rate was `1.0`, and hard-cap violations were `0`, but the
recovery threshold did not cross. Therefore N3 authorizes no implementation
smoke, no P5 selector/reranker, no BEA-v1-A, no runtime/default promotion, no
method-winner claim, no broad retrieval expansion, no downstream-value claim, and
no frozen P4 rerun.

Interpretation: the N2 blocker is not solved by these simple extra-depth
merge-order designs. The next research step, if any, must be separately scoped;
N3 itself only says these three bounded merge-order designs are insufficient.
