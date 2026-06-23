# BEA-v0.4-P3: Support/Complementarity Proxy Repair Smoke

Date: 2026-06-23 (BEA-v0.4-P3 support/complementarity proxy repair smoke —
the final bounded role-proxy repair phase after P1/P2 that answers whether
runtime-clean support/complementarity features, conditioned on the repaired
P2 target anchor, create non-degenerate support availability, select
target+support pairs, materially change setwise selections versus
P1/P2/v0.3, and avoid quality regression)

BEA-v0.4-P3 is **support/complementarity repair evidence only**, not v0.4
proof, not the full v0.4 matrix, not benchmark/leaderboard/performance, not
method-winner, not calibration, not promotion, not default/policy change,
not runtime/retriever/pack/backend/EvidenceCore semantic change, and not
fresh disjoint validation. It does NOT modify P1/P2 result files/artifacts;
the frozen P1 and P2 proxies are reused as-is for the
`setwise_complementarity_v0_4_p1` and
`setwise_complementarity_v0_4_p2_target_repair` control arms. It does NOT
tune v0.3 or v0.4 weights post hoc, does NOT run the full v0.4 matrix, and
does NOT add dense/graph/QuIVer/provider scope. This is the last bounded
role-proxy repair smoke; no P4/P5.

> `claim_level = bea_v04_p3_support_complementarity_repair_smoke_only`. All
> no-claim / no-runtime-change flags false.
> `algorithm_changed_during_bea_v04_p3=false`,
> `weights_tuned_during_bea_v04_p3=false`,
> `v03_tuned_during_bea_v04_p3=false`, `p1_artifact_modified=false`,
> `p2_artifact_modified=false`, `v04_full_matrix_claimed=false`.

## Question

Can runtime-clean **support/complementarity** features, conditioned on the
repaired P2 target anchor, create non-degenerate support availability,
select target+support pairs, materially change setwise selections versus
P1/P2/v0.3, and avoid quality regression?

## P2 root cause and P3 repair

P2 produced a valid No-Go (status `no_go_target_proxy_still_unavailable`):
target availability fixed to `1.0` and target-selected `1.0`, but support
availability collapsed to `0.0` and selections barely changed
(`selection_diff_p2_vs_v03=0.105263`, `selection_diff_p2_vs_p1=0.0`);
quality safety held. The P2 root cause: P2 absorbed near-best candidates
into the target role (`target_near_best`, within `0.15` of the best
intrinsic target score), leaving no candidates for the support role.

P3 repair (deterministic, runtime-clean, no gold/private labels):

- P3 reuses the P2 repaired target anchor (intrinsic query-match score) and
  reserves the target role for the **anchor only** (top-1, if it meets the
  P2 target threshold `>= 0.40`). This frees the near-best candidates that
  P2 absorbed into target.
- P3 support role is a **richer complementarity score** relative to the
  target anchor: different file + dir/package relation + method-source
  complementarity + rank complementarity + span locality/tightness +
  not-duplicate-of-target + cross-file same package/module prefix +
  symbol-ish name overlap already available from retrieval output +
  target-support pair diversity, thresholded (`>= 0.25`). This avoids both
  P1's support=everything (different-file alone contributes only `0.15`,
  insufficient) and P2's support=nothing (more signals + lower threshold
  reach the band).

## Required arms (7; no v0.2, no seeded_random, no synergy-only, no
full-matrix arms)

`bea_v0_3_anchor_span_latency`, `setwise_complementarity_v0_4_p1` (frozen
old proxy), `setwise_complementarity_v0_4_p2_target_repair` (frozen P2
control), `support_complementarity_repair_only_same_budget`,
`setwise_complementarity_v0_4_p3_support_repair` (P3 treatment),
`bm25_prefix_same_budget`, `rrf_same_budget`.

Treatment arm: `setwise_complementarity_v0_4_p3_support_repair`.
Quality baseline: `bea_v0_3_anchor_span_latency`.

## Allowed support/complementarity signals

Repaired P2 target anchor(s); query/path token relation; candidate file
differs from target file; candidate dir/package relation to target path;
method-source complementarity; rank complementarity; span
locality/tightness; candidate not duplicate of target; cross-file but same
package/module prefix; symbol-ish name overlap already available from
retrieval output; target-support pair diversity. No gold/private labels, no
manual row inspection, no provider/LLM calls, no dense/graph/QuIVer, no
per-repo tuning, no post-hoc threshold search.

## Dataset / protocol

Same P1/P2 development frame, success-quota, fail-closed gates:
- `records_successful >= 30`
- `contextbench_successful >= 20`
- `repoqa_successful >= 10`

Fixed protocol: budget 5, methods `bm25,regex,symbol`, raw attempt caps
ContextBench 480 / RepoQA 240. Mandatory excluded windows: BEA-2/3/4
(ContextBench [40,160), RepoQA [20,80)). BEA-5 overlap disclosed, not
excluded. BEA-v0.4-P1 and BEA-v0.4-P2 overlap disclosed, not excluded: P3
reuses the P1/P2 frame and reuses the P2 repaired target anchor; it does
NOT infer from the P1/P2 aggregate. P1+P2+P3 record overlap is possible.
This is P3 support/complementarity repair evidence, not fresh disjoint
validation.

If fresh disjoint yield is not feasible, the implementation fails closed to
`unavailable_with_reason`.

## Hard gates

Proxy feasibility (repaired):
- `target_proxy_available_rate_p3 >= 0.70`
- `target_proxy_selected_rate_p3 >= 0.70`
- `support_proxy_available_rate_p3 >= 0.30` and `<= 0.90`
- `support_proxy_selected_rate_p3 >= 0.20`
- `target_support_pair_available_rate_p3 >= 0.25`
- `target_support_pair_selected_rate_p3 >= 0.20`
- `unknown_only_record_rate_p3 <= 0.30`

Non-degeneracy:
- `mean_support_candidates_per_record_p3 >= 1.0` and `<= 8.0`
- `same_file_support_rate_p3 <= 0.50`

Behavior:
- `selection_diff_rate_p3_vs_v03 >= 0.25`
- `selection_diff_rate_p3_vs_p2 >= 0.20`
- `selection_diff_rate_p3_vs_p1 >= 0.20`
- `mean_duplicate_file_count_v04_p3 <= mean_duplicate_file_count_v03`
- `mean_candidate_source_diversity_v04_p3 >= mean_candidate_source_diversity_v03`

Quality safety:
- `file_recall@10_v04_p3 >= v03 - 0.05`
- `mrr_v04_p3 >= v03 - 0.05`
- `span_f0.5@10_v04_p3 >= v03 - 0.02`
- `latency_seconds_v04_p3 <= v03 * 1.25`

At least one directional improvement vs v0.3: lower duplicate_file_rate OR
lower label_file_absent_rate OR lower correct_file_wrong_span_rate OR lower
latency_without_quality_gain OR lower budget_spent_on_low_marginal_gain OR
higher quality_per_latency.

## Statuses

`bea_v04_p3_support_complementarity_repair_pass`,
`partial_support_proxy_signal`,
`no_go_support_proxy_still_unavailable`,
`no_go_support_proxy_degenerate`, `no_go_no_selection_change`,
`no_go_quality_regression`, `unavailable_with_reason`,
`fail_forbidden_scan`, `fail_schema_contract`.

## Public artifact tables (records-only, natural keys)

- `source_run_records`: `(source_phase, source_ci_run_id)`
- `arm_metric_records`: `(arm, metric)`
- `arm_delta_records`: `(baseline_arm, treatment_arm, metric)`
- `role_proxy_summary_records`: `(role_proxy, summary_field)`
- `setwise_behavior_records`: `(behavior_field,)`
- `support_complementarity_records`: `(support_field,)`
- `failure_family_records`: `(failure_family, policy_arm, availability)`
- `win_tie_loss_records`: `(baseline_arm, treatment_arm, metric)`
- `availability_records`: `(category, availability)`
- `benchmark_attempt_records`: `(benchmark,)`
- `manifests`: `(manifest_name,)` records-only table containing entries
  named `private_score_manifest`, `private_decision_manifest`,
  `private_role_proxy_manifest`, `private_support_feature_manifest`, and
  `private_pair_feature_manifest`; aggregate-only
  count/hash/storage/path_publicly_serialized=false
- `forbidden_scan`: scan summary
- `hard_gate_records`: records-only aggregate gate values + booleans
- `failure_category_count_records`: records-only failure-category counts

No public record IDs, repo URLs, commits, paths, queries, gold labels,
spans, snippets, candidate files, decision order, score components, or
per-record role labels. No top-level manifest dict mirrors and no dynamic
dicts like `hard_gates`/`failure_category_counts`.

## Private `/tmp` JSONL files

Five private JSONL files are written under `/tmp` only and NEVER uploaded:
score rows (one per policy arm per record; `record_count ==
records_successful * len(fixed_arms)`), decision rows (one per P3 accepted
action; expected count recorded in `source_run_records`), role-proxy rows
(P3 repaired assignment per candidate), support-feature rows (P3
support/complementarity diagnostics per candidate), and pair-feature rows
(one per record, target-support pair diagnostics). The public artifact
carries only manifest summaries (count + hash + storage class;
`path_publicly_serialized=false`). The implementation fails closed if
private writes are incomplete.

## Failure family enum (12, same as BEA-FD1)

`label_file_absent`, `label_span_absent`, `correct_file_wrong_span`,
`redundant_same_file_candidates`, `too_many_anchor_slots`,
`missing_support_candidate`, `support_selected_without_target`,
`target_selected_without_support`, `risk_penalty_removed_gold`,
`early_stop_too_early`, `budget_spent_on_low_marginal_gain`,
`latency_without_quality_gain`.

## Validation

```text
python3 -m py_compile eval/bea_v04_p3_support_complementarity_repair_smoke.py  => PASS
python3 eval/bea_v04_p3_support_complementarity_repair_smoke.py --self-test  => PASS (400/400 checks)
python3 eval/bea_v04_p3_support_complementarity_repair_smoke.py \
  --out artifacts/bea_v04_p3_support_complementarity_repair/\
bea_v04_p3_support_complementarity_repair_smoke_report.json  => PASS
  (status: unavailable_with_reason, no-network default artifact,
   provider_calls=0, forbidden_scan=pass,
   algorithm_changed_during_bea_v04_p3=false,
   weights_tuned_during_bea_v04_p3=false,
   v03_tuned_during_bea_v04_p3=false,
   p1_artifact_modified=false, p2_artifact_modified=false,
   v04_full_matrix_claimed=false,
   self_test_checks_total=400, self_test_checks_passed=400)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

The default no-network artifact honestly returns `unavailable_with_reason`
(`network_mode=disabled_opt_in`). A real smoke run requires explicit
`--enable-external-benchmark-network` and public network access (manual CI
`workflow_dispatch` only). If P3 passes, next step is a frozen full v0.4
matrix design. If P3 fails support availability, is support-degenerate,
does not change selections, or regresses quality, the role-proxy line stops
and the project pivots to direct FD1-objective setwise acquisition. No
P4/P5 proxy repair.

## Caveats

- BEA-v0.4-P3 is eval/diagnostic only. NOT benchmark/leaderboard/
  performance/method-winner/calibration/promotion/default/runtime/
  EvidenceCore/downstream-value claim. NOT v0.4 proof. NOT the full v0.4
  matrix. NOT fresh disjoint validation.
- P3 repairs only support/complementarity proxy features, conditioned on
  the frozen P2 repaired target anchor. It does NOT run the full v0.4
  matrix, does NOT tune v0.3, and does NOT perform post-hoc threshold
  search. v0.3 algorithm/weights frozen;
  `v03_tuned_during_bea_v04_p3=false`; `p1_artifact_modified=false`;
  `p2_artifact_modified=false`.
- Role proxies are deterministic runtime-clean, no gold/private labels,
  no provider/LLM calls.
- Fresh smoke protocol discloses BEA-5, BEA-v0.4-P1, and BEA-v0.4-P2
  overlap (not fresh disjoint validation).
- Private score/decision/role-proxy/support-feature/pair-feature JSONL
  files are written ONLY under `/tmp` and NEVER uploaded.
