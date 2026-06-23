# BEA-FD2-A: Direct FD1-Objective Setwise Acquisition Smoke

Date: 2026-06-23 (BEA-FD2-A direct FD1-objective setwise acquisition smoke
— the direct algorithmic follow-on after BEA-v0.4-P3 stopped the role-proxy
line. A setwise selector directly optimizes frozen FD1 failure-loss
reduction derived from the committed FD1 aggregate artifact, without
target/support proxies and without quality regression.)

BEA-FD2-A is NOT P4/P5, NOT a full v0.4 matrix, NOT a v0.31/v0.32 weight
tweak, and NOT fresh disjoint validation. It is one bounded algorithm-change
smoke on the same P1/P2/P3 success-quota frame.

> `claim_level = bea_fd2a_direct_fd1_objective_setwise_smoke_only`. All
> no-claim / no-runtime-change flags false. `role_proxy_used=false` and
> `target_support_proxy_used=false` are binding self-tested invariants.

## Prior-phase binding context

P1 failure: `target_proxy_available_rate=0.0`, support degenerate to 1.0.
P2 repair: target availability fixed to 1.0 but support collapsed to 0.0 and
selections barely changed vs v0.3 (`0.105263`). P3 repair: restored support
availability but selections/quality could not hold across the full frame.
FD2-A pivots away from role proxies entirely — the FD2-A treatment does NOT
use role-proxy assignment logic.

## Fixed arms (5)

1. `bm25_prefix_same_budget`
2. `rrf_same_budget`
3. `bea_v0_3_anchor_span_latency` (quality baseline)
4. `fd1_coverage_only_same_budget` (relevance + coverage/diversity, no FD1 weights)
5. `fd1_loss_weighted_setwise_same_budget` (treatment: adds frozen FD1 weights)

No P1/P2/P3 role-proxy arms, no seeded random, no v0.2/v0 controls, no
dense/graph/QuIVer/provider arms. Budget 5; methods bm25,regex,symbol;
candidate pool bm25/regex/symbol + derived RRF as needed.

## FD1 weight derivation (read-only input, frozen before evaluation)

FD2-A reads ONLY the public aggregate `category_metric_loss_records` from the
committed FD1 artifact
(`artifacts/bea_fd1_failure_decomposition/bea_fd1_failure_decomposition_report.json`)
as read-only input. It aggregates `loss_sum` per FD1 category (across
source_phase / benchmark / baseline_arm / treatment_arm / metric) and
normalizes the four derivable categories to sum to 1.0:

- `gold_file_absent` (loss_sum ≈ 1097.33) → weight ≈ 0.2539 → `file_reach`
- `correct_file_wrong_span` (loss_sum ≈ 548.24) → weight ≈ 0.1268 → `span_precision`
- `budget_spent_on_low_marginal_gain` (loss_sum ≈ 1125.36) → weight ≈ 0.2604 → `novelty_diminishing_returns`
- `latency_without_quality_gain` (loss_sum ≈ 1551.05) → weight ≈ 0.3589 → `latency_cost` (penalty)
- `redundant_same_file_candidates` (unavailable_missing_trace in FD1) → fixed default 0.10 → `duplicate_penalty` (penalty)

The FD1 artifact is NEVER modified. No private decomposition rows, gold
labels, or per-record data are read during selection. Weights are frozen at
derivation time and are NOT tuned from FD2-A outcomes (no post-hoc threshold
search). The fifth category uses a fixed default because FD1 marked it
`unavailable_missing_trace`; FD2-A can now compute duplicates directly from
accepted evidence.

## Treatment objective

Greedy setwise under budget 5. Score = coverage-only base priority
(relevance + coverage/diversity via v0.2 agreement + bm25_norm + diversity +
overlap − risk − duplication) + FD1 loss-weighted objective:

```
fd1_objective = w_gold_file_absent * file_reach
              + w_correct_file_wrong_span * span_precision
              + w_budget_spent_on_low_marginal_gain * novelty_diminishing_returns
              - w_latency_without_quality_gain * latency_cost
              - w_redundant_same_file_candidates * duplicate_penalty
```

Reward components (file_reach, span_precision, novelty) are added; penalty
components (latency_cost, duplicate_penalty) are subtracted. The
`fd1_coverage_only_same_budget` ablation uses ONLY the coverage-only base
priority (no FD1 weights), isolating the FD1 weight contribution.

## Runtime-clean invariants (binding, self-tested)

- `role_proxy_used=false`, `target_support_proxy_used=false` (self-tested at
  mechanism level and report level).
- `private_decomposition_used_for_selection=false`,
  `gold_labels_used_for_selection=false`, `posthoc_threshold_search=false`.
- FD2-A does NOT import any BEA-v0.4-P1/P2/P3 module; the treatment does
  not call role-proxy assignment logic.
- Runtime-clean invariance: tainted candidates with gold/row_id/label
  fields produce identical selections.

## Frame (same P1/P2/P3 success-quota frame)

38 records target (ContextBench >=20, RepoQA >=10) with BEA-2/3/4 mandatory
exclusion windows and BEA-5/P1/P2/P3 overlap disclosed. This is NOT fresh
disjoint validation — it isolates the algorithm change where role-proxy
repair failed. If FD2-A passes, heldout/disjoint FD2-B can follow.

## Gates

- Denominator: records_successful >=30, ContextBench >=20, RepoQA >=10.
- Fixed budget/methods/arms.
- Behavior: selection diff vs v0.3 >=0.25; diff vs coverage-only >=0.15;
  duplicate count <= v0.3; source diversity >= v0.3.
- FD1 mechanism: composite FD1 loss improves vs v0.3 AND vs coverage-only;
  at least one dominant category improves.
- Quality safety: file_recall@10 >= v0.3-0.03; MRR >= v0.3-0.05;
  span_f0.5@10 >= v0.3-0.02; latency <= v0.3*1.15.

## Public artifact tables (records-only, natural keys)

- `source_run_records`: `(source_phase, source_ci_run_id)`
- `arm_metric_records`: `(arm, metric)`
- `arm_delta_records`: `(baseline_arm, treatment_arm, metric)`
- `win_tie_loss_records`: `(baseline_arm, treatment_arm, metric)`
- `fd1_category_loss_records`: `(policy_arm, fd1_category)`
- `fd1_category_rate_records`: `(policy_arm, fd1_category)`
- `fd1_objective_component_records`: `(component,)`
- `ablation_delta_records`: `(component, baseline_arm, treatment_arm)`
- `setwise_behavior_records`: `(behavior_field,)`
- `benchmark_attempt_records`: `(benchmark,)`
- `hard_gate_records`: `(gate,)`
- `failure_category_count_records`: `(failure_category,)`
- `manifests`: `(manifest_name,)` — path never serialized; counts/hashes/storage only
- `framing`, `forbidden_scan`

No public record IDs, paths, repos, queries, gold labels, spans, snippets,
candidate files, decision order, per-record features, FD1 private
decomposition rows, role-proxy labels, or objective-config file paths.

## Private artifacts (under `/tmp` only)

- private SCORE JSONL (records × 5 arms)
- private decision JSONL (treatment selected order/features)
- private FD1-objective feature JSONL (per-candidate runtime-clean components)
- private post-hoc decomposition JSONL (record × arm × category attribution)
- private objective-config JSON (frozen FD1 weights + source artifact hash)

## Statuses

`bea_fd2a_direct_fd1_objective_pass` | `partial_fd1_objective_signal` |
`no_go_no_selection_change` | `no_go_no_fd1_loss_reduction` |
`no_go_objective_ablation_only` | `no_go_quality_regression` |
`unavailable_with_reason` | `fail_forbidden_scan` | `fail_schema_contract`

## Validation

```text
python3 -m py_compile eval/bea_fd2a_direct_fd1_objective_setwise_smoke.py  => PASS
python3 eval/bea_fd2a_direct_fd1_objective_setwise_smoke.py --self-test  => PASS (373/373 checks)
python3 eval/bea_fd2a_direct_fd1_objective_setwise_smoke.py \
  --out artifacts/bea_fd2a_direct_fd1_objective/bea_fd2a_direct_fd1_objective_setwise_smoke_report.json  => PASS
  (status: unavailable_with_reason, no-network artifact,
   provider_calls=0, forbidden_scan=pass,
   role_proxy_used=false, target_support_proxy_used=false,
   fd1_artifact_modified=false, records_successful=0,
   self_test_checks_total=373, self_test_checks_passed=373)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

## Stop rules

Pass earns only a heldout/disjoint FD2-B; it is NOT v0.4 proof or a default
change. On failure: do not scale, do not tune v0.31/v0.32, do not resurrect
role proxies.

## Caveats

- BEA-FD2-A is eval/diagnostic only. NOT benchmark/leaderboard/performance/
  method-winner/calibration/promotion/default/runtime/EvidenceCore/
  downstream-value claim.
- The default no-network artifact is honestly `unavailable_with_reason`
  with `provider_calls=0` and `records_successful=0`; it is NOT a fake pass.
- FD1 weights are derived from the committed FD1 aggregate loss records;
  if the FD1 artifact is missing or has no loss records, the run is
  `unavailable_with_reason` (`fd1_artifact_missing` /
  `fd1_loss_records_missing`).
- `redundant_same_file_candidates` uses a fixed default weight (0.10)
  because FD1 marked it `unavailable_missing_trace`; FD2-A can now compute
  duplicate counts directly, so this category becomes `available` in FD2-A's
  own post-hoc decomposition.
- This is the same P1/P2/P3 success-quota frame with disclosed overlap; it
  is not fresh disjoint validation.
