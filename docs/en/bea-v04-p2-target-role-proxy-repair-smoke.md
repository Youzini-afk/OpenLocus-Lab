# BEA-v0.4-P2: Target-Role Proxy Repair Smoke

Date: 2026-06-23 (BEA-v0.4-P2 target-role proxy repair smoke — a bounded
continuation of BEA-v0.4-P1 that repairs the concrete P1 failure
`target_proxy_available_rate=0.0` and answers whether runtime-clean
repaired target-role proxy features produce nonzero target availability
and materially change setwise selections versus both BEA v0.3 and the
frozen P1 proxy, without catastrophic quality regression)

BEA-v0.4-P2 is **target-role repair evidence only**, not v0.4 proof, not
the full v0.4 matrix, not benchmark/leaderboard/performance, not
method-winner, not calibration, not promotion, not default/policy change,
not runtime/retriever/pack/backend/EvidenceCore semantic change, and not
fresh disjoint validation. It does NOT modify P1 result files/artifact;
the frozen P1 proxy is reused as-is for the `setwise_complementarity_v0_4_p1`
control arm. It does NOT tune v0.3 or v0.4 weights post hoc, does NOT run
the full v0.4 matrix, and does NOT add dense/graph/QuIVer/provider scope.

> `claim_level = bea_v04_p2_target_proxy_repair_smoke_only`. All no-claim /
> no-runtime-change flags false. `algorithm_changed_during_bea_v04_p2=false`,
> `weights_tuned_during_bea_v04_p2=false`, `v03_tuned_during_bea_v04_p2=false`,
> `p1_artifact_modified=false`, `v04_full_matrix_claimed=false`.

## Question

Can runtime-clean **repaired** target-role proxy features produce nonzero
target availability and materially change setwise selections versus both
BEA v0.3 and the frozen P1 proxy, without catastrophic quality loss?

## P1 root cause and P2 repair

P1 produced a valid No-Go / weak negative (status `no_go_proxy_unavailable`,
CI run `28017063082`): `target_proxy_available_rate=0.0`,
`support_proxy_available_rate=1.0`,
`setwise_selection_diff_rate_vs_v03=0.105263`. Explorer mapped two root
causes, both repaired here with deterministic runtime-clean features (no
gold/private labels):

- P1 target gate required exact same-span multi-method agreement
  (`agreement >= 2`) plus tight span/path overlap. Real candidates rarely
  satisfy same-span agreement>=2, so target availability collapsed to 0.0.
  P2 drops the hard `agreement >= 2` gate and assigns target role by an
  **intrinsic query-match score** (query/path token overlap + span
  tightness + bm25/symbol presence + continuous agreement + path-depth
  locality), thresholded (`>= 0.40`) and top-N capped (within `0.15` of the
  best).
- P1 support gate was evaluated against empty `accepted_paths/dirs` in the
  batch assignment, so every candidate was "new file" and support
  availability was a degenerate 1.0. P2 assigns support **relative to the
  target anchor** (different file/dir + different method source + span
  tightness + query overlap), not against an empty accepted set.

## Required arms (6; seeded_random omitted per plan)

`bm25_prefix_same_budget`, `bea_v0_3_anchor_span_latency`,
`setwise_complementarity_v0_4_p1` (frozen old proxy),
`target_role_repair_only_same_budget`,
`setwise_complementarity_v0_4_p2_target_repair`, `rrf_same_budget`.

Treatment arm: `setwise_complementarity_v0_4_p2_target_repair`.
Quality baseline: `bea_v0_3_anchor_span_latency`.

## Allowed repair signals

Query tokens; candidate path/basename tokens; already available
symbol-ish retrieval output; method rank/source agreement; span
tightness/locality; file/type/path heuristics; source diversity and
duplicate-file state. No gold/private labels, no provider/LLM calls, no
dense/graph/QuIVer, no per-repo tuning, no manual row inspection, no
post-hoc threshold search.

## Dataset / protocol

Same P1 development frame, success-quota, fail-closed gates:
- `records_successful >= 30`
- `contextbench_successful >= 20`
- `repoqa_successful >= 10`

Fixed protocol: budget 5, methods `bm25,regex,symbol`, raw attempt caps
ContextBench 480 / RepoQA 240. Mandatory excluded windows: BEA-2/3/4
(ContextBench [40,160), RepoQA [20,80)). BEA-5 overlap disclosed, not
excluded. BEA-v0.4-P1 overlap disclosed, not excluded: P2 reuses the P1
frame and re-runs candidate pools and arms in one process; it does NOT
infer from the P1 aggregate. P1+P2 record overlap is possible. This is P2
target-role repair evidence, not fresh disjoint validation.

If fresh disjoint yield is not feasible, the implementation fails closed
to `unavailable_with_reason`.

## Hard gates

Role-proxy feasibility (repaired):
- `target_proxy_available_rate_p2 >= 0.30`
- `support_proxy_available_rate_p2 >= 0.30`
- `target_proxy_selected_rate_p2 >= 0.20`
- `unknown_only_record_rate_p2 <= 0.30`

Behavior:
- `selection_diff_rate_p2_vs_v03 >= 0.25`
- `selection_diff_rate_p2_vs_p1 >= 0.20`
- `mean_duplicate_file_count_v04_p2 <= mean_duplicate_file_count_v03`
- `mean_candidate_source_diversity_v04_p2 >= mean_candidate_source_diversity_v03`

Quality safety:
- `file_recall@10_v04_p2 >= v03 - 0.05`
- `mrr_v04_p2 >= v03 - 0.05`
- `span_f0.5@10_v04_p2 >= v03 - 0.02`
- `latency_seconds_v04_p2 <= v03 * 1.25`

At least one directional improvement vs v0.3: lower duplicate_file_rate
OR lower label_file_absent_rate OR lower correct_file_wrong_span_rate OR
lower latency_without_quality_gain OR lower budget_spent_on_low_marginal_gain
OR higher quality_per_latency.

## Statuses

`bea_v04_p2_target_proxy_repair_pass`, `partial_target_proxy_signal`,
`no_go_target_proxy_still_unavailable`, `no_go_no_selection_change`,
`no_go_quality_regression`, `unavailable_with_reason`,
`fail_forbidden_scan`, `fail_schema_contract`.

## Public artifact tables (records-only, natural keys)

- `source_run_records`: `(source_phase, source_ci_run_id)`
- `arm_metric_records`: `(arm, metric)`
- `arm_delta_records`: `(baseline_arm, treatment_arm, metric)`
- `role_proxy_summary_records`: `(role_proxy, summary_field)`
- `setwise_behavior_records`: `(behavior_field,)`
- `target_proxy_repair_records`: `(repair_field,)`
- `failure_family_records`: `(failure_family, policy_arm, availability)`
- `win_tie_loss_records`: `(baseline_arm, treatment_arm, metric)`
- `availability_records`: `(category, availability)`
- `benchmark_attempt_records`: `(benchmark,)`
- `manifests`: `(manifest_name,)` records-only table containing entries named
  `private_score_manifest`, `private_decision_manifest`,
  `private_role_proxy_manifest`, and `private_target_feature_manifest`;
  aggregate-only count/hash/storage/path_publicly_serialized=false
- `forbidden_scan`: scan summary
- `hard_gate_records`: records-only aggregate gate values + booleans
- `failure_category_count_records`: records-only failure-category counts

No public record IDs, repo URLs, commits, paths, queries, gold labels,
spans, snippets, candidate files, decision order, score components, or
per-record role labels.

## Private `/tmp` JSONL files

Four private JSONL files are written under `/tmp` only and NEVER uploaded:
score rows (one per policy arm per record; `record_count ==
records_successful * len(fixed_arms)`), decision rows (one per P2 accepted
action; expected count recorded in `source_run_records`), role-proxy rows
(P2 repaired assignment per candidate), and
target-feature rows (P2 target-feature diagnostics per candidate). The
public artifact carries only manifest summaries (count + hash + storage
class; `path_publicly_serialized=false`). The implementation fails closed
if private writes are incomplete.

## Failure family enum (12, same as BEA-FD1)

`label_file_absent`, `label_span_absent`, `correct_file_wrong_span`,
`redundant_same_file_candidates`, `too_many_anchor_slots`,
`missing_support_candidate`, `support_selected_without_target`,
`target_selected_without_support`, `risk_penalty_removed_gold`,
`early_stop_too_early`, `budget_spent_on_low_marginal_gain`,
`latency_without_quality_gain`.

## Validation

```text
python3 -m py_compile eval/bea_v04_p2_target_role_proxy_repair_smoke.py  => PASS
python3 eval/bea_v04_p2_target_role_proxy_repair_smoke.py --self-test  => PASS (335/335 checks)
python3 eval/bea_v04_p2_target_role_proxy_repair_smoke.py \
  --out artifacts/bea_v04_p2_target_role_proxy_repair/\
bea_v04_p2_target_role_proxy_repair_smoke_report.json  => PASS
  (status: unavailable_with_reason, no-network default artifact,
   provider_calls=0, forbidden_scan=pass,
   algorithm_changed_during_bea_v04_p2=false,
   weights_tuned_during_bea_v04_p2=false,
   v03_tuned_during_bea_v04_p2=false,
   p1_artifact_modified=false,
   v04_full_matrix_claimed=false,
   self_test_checks_total=335, self_test_checks_passed=335)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

Manual CI run `28020331024` passed the fail-closed workflow and supersedes
the default no-network artifact. The result is a valid P2 No-Go: status
`no_go_target_proxy_still_unavailable`, records_successful=38
(ContextBench 20, RepoQA 18), attempted=46, excluded=8, forbidden_scan=pass,
private SCORE rows=228, decision rows=190, role-proxy rows=760, and
target-feature rows=760.

P2 fixed the target-role proxy availability failure from P1: target proxy
availability moved from 0.0 to 1.0 and target-selected rate was 1.0. But the
repair exposed a new blocker: support proxy availability fell from 1.0 to 0.0,
P2-vs-P1 selection difference remained 0.0, and P2-vs-v0.3 selection
difference remained only 0.105263 (<0.25). Quality did not catastrophically
regress versus v0.3 (file_recall@10 and MRR deltas 0.0, span_f0.5@10
-0.003036, latency +0.001789s, quality_per_latency -0.000857), but P2 does
not justify entering the full v0.4 matrix.

## Caveats

- BEA-v0.4-P2 is eval/diagnostic only. NOT benchmark/leaderboard/
  performance/method-winner/calibration/promotion/default/runtime/
  EvidenceCore/downstream-value claim. NOT v0.4 proof. NOT the full v0.4
  matrix. NOT fresh disjoint validation.
- P2 repairs only target-role proxy features. It does NOT run the full
  v0.4 matrix, does NOT tune v0.3, and does NOT perform post-hoc threshold
  search. v0.3 algorithm/weights frozen;
  `v03_tuned_during_bea_v04_p2=false`; `p1_artifact_modified=false`.
- Role proxies are deterministic runtime-clean, no gold/private labels,
  no provider/LLM calls.
- Fresh smoke protocol discloses BEA-5 and BEA-v0.4-P1 overlap (not fresh
  disjoint validation).
- Private score/decision/role-proxy/target-feature JSONL files are written
  ONLY under `/tmp` and NEVER uploaded.
