# BEA-v0.4-P1: Setwise Role-Proxy Smoke

Date: 2026-06-23 (BEA-v0.4-P1 setwise role-proxy smoke — eval-local
deterministic role-proxy setwise selection policy compared against BEA
v0.3 and same-budget controls on a fresh small external smoke slice;
answers whether role-proxy setwise selection changes v0.3 behavior and
reduces FD1 failure families without catastrophic quality regression)

BEA-v0.4-P1 is **P1 smoke evidence only**, not v0.4 proof/performance/
winner/default/calibration/downstream-value. It does NOT implement the
full v0.4 matrix. It does NOT run B16-K, does NOT tune v0.31 weights,
does NOT touch runtime/default/EvidenceCore, and does NOT add dense/
graph/QuIVer/provider scope.

> `claim_level = bea_v04_p1_setwise_role_proxy_smoke_only`. All no-claim /
> no-runtime-change flags false. `algorithm_changed_during_bea_v04_p1=false`,
> `weights_tuned_during_bea_v04_p1=false`, `v04_full_matrix_claimed=false`.

## Question

Can deterministic role-proxy setwise selection change BEA v0.3 behavior
and reduce FD1 failure families without catastrophic quality loss?

## Required arms (6; RRF included because cheap + stable)

`bm25_prefix_same_budget`, `bea_v0_3_anchor_span_latency`,
`role_proxy_only_same_budget`, `setwise_complementarity_v0_4_p1`,
`seeded_random_same_budget`, `rrf_same_budget`.

Treatment arm: `setwise_complementarity_v0_4_p1`.
Quality baseline: `bea_v0_3_anchor_span_latency`.

## Role-proxy fixed enum (deterministic, runtime-clean)

`target_proxy`, `support_proxy`, `unknown`. No gold/private labels used.
Signals: method agreement, BM25/RRF/regex/symbol source, query/path
token overlap, AST/path role-ish heuristics, span tightness, same-file/
cross-file relation, source diversity.

## v0.4 P1 setwise selection rules (frozen, no post-hoc tuning)

- At least one `target_proxy` if available (reserved target slot).
- Prefer `support_proxy` from a different file/symbol family.
- Penalize repeated same-file selections (strong penalty).
- Reward novelty / source diversity / span tightness.
- Frozen weights: target=0.40, support_cross_file=0.20,
  source_diversity=0.15, span_tight=0.10, novelty=0.10,
  dup_file_penalty=-0.35, weak_support_penalty=-0.15.

## Dataset / protocol

Fresh small external smoke (success-quota), fail-closed gates:
- `records_successful >= 30`
- `contextbench_successful >= 20`
- `repoqa_successful >= 10`

Fixed protocol: budget 5, methods `bm25,regex,symbol`, raw attempt
caps ContextBench 480 / RepoQA 240. Mandatory excluded windows:
BEA-2/3/4 (ContextBench [40,160), RepoQA [20,80)). BEA-5 overlap
disclosed, not excluded (BEA-5 used success-quota over the same full
frame and did not consume it entirely). BEA-0/BEA-1 best-effort
disclosed. This is P1 smoke evidence, not fresh disjoint validation.

If fresh disjoint yield is not feasible, the implementation fails closed
to `unavailable_with_reason`. Offline BEA-4/5 counterfactual replay is
documented as a future extension (private traces lack full candidate
lists, so v0.4 P1 selection cannot be re-run on the same candidates).

## Hard gates

Role-proxy feasibility:
- `role_proxy_assignment_rate >= 0.70`
- `target_proxy_available_rate >= 0.50`
- `support_proxy_available_rate >= 0.30`
- `unknown_only_record_rate <= 0.30`

Behavior:
- `setwise_selection_diff_rate_vs_v03 >= 0.25`
- `mean_duplicate_file_count_v04 <= mean_duplicate_file_count_v03`
- `mean_candidate_source_diversity_v04 >= mean_candidate_source_diversity_v03`

Quality safety:
- `file_recall@10_v04 >= v03 - 0.05`
- `mrr_v04 >= v03 - 0.05`
- `span_f0.5@10_v04 >= v03 - 0.02`
- `latency_seconds_v04 <= v03 * 1.25`

At least one directional improvement vs v0.3: lower duplicate_file_rate
OR lower gold_file_absent_rate OR lower correct_file_wrong_span_rate OR
higher quality_per_latency.

## Statuses

`bea_v04_p1_smoke_pass`, `partial_directional_signal`,
`no_go_proxy_unavailable`, `no_go_no_selection_change`,
`no_go_quality_regression`, `unavailable_with_reason`,
`offline_counterfactual_replay`, `fail_forbidden_scan`,
`fail_schema_contract`.

## Public artifact tables (records-only, natural keys)

- `source_run_records`: `(source_phase, source_ci_run_id)`
- `arm_metric_records`: `(arm, metric)`
- `arm_delta_records`: `(baseline_arm, treatment_arm, metric)`
- `role_proxy_summary_records`: `(role_proxy, summary_field)`
- `setwise_behavior_records`: `(behavior_field,)`
- `failure_family_records`: `(failure_family, policy_arm, availability)`
- `win_tie_loss_records`: `(baseline_arm, treatment_arm, metric)`
- `availability_records`: `(category, availability)`
- `benchmark_attempt_records`: `(benchmark,)`
- `private_score_manifest`, `private_decision_manifest`,
  `private_role_proxy_manifest`: aggregate-only (count/hash/storage/
  path_publicly_serialized=false)
- `forbidden_scan`: scan summary
- `hard_gate_records`: records-only aggregate gate values + booleans
- `failure_category_count_records`: records-only failure-category counts

No public record IDs, repo URLs, commits, paths, queries, gold labels,
spans, snippets, candidate files, decision order, score components, or
per-record role labels.

## Failure family enum (12, same as BEA-FD1)

`gold_file_absent`, `gold_span_absent`, `correct_file_wrong_span`,
`redundant_same_file_candidates`, `too_many_anchor_slots`,
`missing_support_candidate`, `support_selected_without_target`,
`target_selected_without_support`, `risk_penalty_removed_gold`,
`early_stop_too_early`, `budget_spent_on_low_marginal_gain`,
`latency_without_quality_gain`.

Available vs unavailable categories match BEA-FD1. v0.4 P1 adds
role-proxy-aware classification for `redundant_same_file_candidates`
(available via setwise behavior), while support-target categories
remain `unavailable_no_support_label` until private traces carry role
labels.

## Validation

```text
python3 -m py_compile eval/bea_v04_p1_setwise_role_proxy_smoke.py  => PASS
python3 eval/bea_v04_p1_setwise_role_proxy_smoke.py --self-test  => PASS (269/269 checks)
python3 eval/bea_v04_p1_setwise_role_proxy_smoke.py \
  --out artifacts/bea_v04_p1_setwise_role_proxy/\
bea_v04_p1_setwise_role_proxy_smoke_report.json  => PASS
  (status: unavailable_with_reason, no-network artifact,
   provider_calls=0, forbidden_scan=pass,
   algorithm_changed_during_bea_v04_p1=false,
   weights_tuned_during_bea_v04_p1=false,
   v04_full_matrix_claimed=false,
   self_test_checks_total=269, self_test_checks_passed=269)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

## Manual CI result — run `28017063082`

Manual network-enabled CI passed the fail-closed workflow and produced a valid
P1 smoke result, but the result is a **No-Go / weak negative** for the current
role-proxy mechanism:

- Status: `no_go_proxy_unavailable`.
- Denominator: 38 successful records (ContextBench 20, RepoQA 18), 46 attempted,
  8 excluded.
- Private traces: SCORE rows = 228 (`38 × 6 arms`), decision rows = 190,
  role-proxy rows = 760; all private manifests are `/tmp` only.
- Role proxy assignment rate = 1.0, support-proxy availability = 1.0, but
  target-proxy availability = 0.0, so the proxy gate failed.
- Setwise-vs-v0.3 selection-diff rate = 0.105263, below the 0.25 behavior gate.
- Quality did not catastrophically regress versus v0.3, but it also did not
  improve: file_recall@10 and MRR deltas are 0.0, span_f0.5@10 delta is
  -0.003036, latency delta is +0.001686s, quality_per_latency delta is
  -0.000809.

Interpretation: this P1 confirms that the deterministic setwise machinery can
run end-to-end with private traces and records-only public artifacts, but the
current runtime-clean role proxies do **not** expose target evidence on this
slice and do **not** change v0.3 selection often enough. Do not advance this
role-proxy design to a full v0.4 matrix without improving target-role features.

## Caveats

- BEA-v0.4-P1 is eval/diagnostic only. NOT benchmark/leaderboard/
  performance/method-winner/calibration/promotion/default/runtime/
  EvidenceCore/downstream-value claim. NOT v0.4 proof. NOT the full
  v0.4 matrix.
- v0.3 algorithm/weights frozen; `algorithm_changed_during_bea_v04_p1=false`.
- Role proxies are deterministic runtime-clean, no gold/private labels.
- Fresh smoke protocol discloses BEA-5 overlap (not fresh disjoint
  validation). CI run `28017063082` is the real smoke result; the default
  no-network artifact has been superseded.
- Private score / decision / role-proxy JSONL files are written ONLY
  under `/tmp` and NEVER uploaded.
