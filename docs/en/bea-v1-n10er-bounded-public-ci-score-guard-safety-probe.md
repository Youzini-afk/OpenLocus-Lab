# BEA-v1-N10ER Bounded Public CI Score/Guard Safety Probe

Date: 2026-06-30

BEA-v1-N10ER is the **bounded public CI score/guard safety probe** — a real
execution phase after the N10EQ checkpoint `7963831`. It executes the
N10EQ-designed safety probe on a held-out manifest-listed public CI sample,
computes the seven N10EQ-designed safety features as **aggregate buckets
only**, and emits a sanitized aggregate-only report. It reuses N10EN's
retrieval/order plumbing (frozen transforms, clone, generate-tasks, OpenLocus
search) **verbatim** — it does **not** mutate N10EN semantics or artifacts.

## Default behavior

When `enable_public_github_network` is `false` (the default), N10ER emits a
fail-closed/unavailable artifact **without** cloning, building, or searching:

```text
status: n10er_safety_probe_unavailable_network_disabled
network_run: false
clone_run: false
search_run: false
n10er_execution_authorized: false
```

The safe default never touches the network, never mutates the repo, and never
reads private diagnostic inputs.

## CI result

GitHub Actions run `28457213423` executed `canary_small_heldout` with public
GitHub network explicitly enabled. Status is
`n10er_safety_probe_complete_no_signal_reproduced_n10es_authorized`: the sample
met minimums (`public_task_count=80`, `scored_task_count=60`,
`task_with_gold_count=40`) and the heldout overlap check passed (`overlap_zero`),
but the safety signal did not reproduce. The risk bucket was sufficient
(`task_count=26`), yet full/guard/diffaware each lost `0` baseline top-10 hits
inside the risk bucket and `guard_would_preserve_full_loss_count=0`.

Arm aggregates: baseline `37/39/40/40`; full `36/39/40/40` with lost baseline
top10 `1`; guard `38/39/40/40` with lost baseline top10 `0`; diffaware
`37/39/40/40` with lost baseline top10 `1`. These arm aggregates are reported
for context; the N10ER top-level status is based on the safety signal gate.

## N10EQ source lock

```text
n10eq_checkpoint: 7963831
n10ep_checkpoint: 0a54b49 (upstream source lock)
status: n10eq_score_guard_safety_probe_design_pass_n10er_contract_authorized
n10er_contract_authorized: true
n10er_execution_authorized: false (design-only contract)
next_phase: BEA-v1-N10ER Bounded Public CI Score/Guard Safety Probe
source_locked: true
```

## Enabled run (held-out public CI sample)

When `--enable-public-github-network` is set, N10ER:

- clones **manifest-listed public repos only** (reusing `ci_clone_and_lock_repo`);
- generates public tasks with `--no-labels` first (RUN phase sees no gold);
- builds/uses the checked-out local OpenLocus CLI to materialize temporary
  public candidates (BM25 limit 100; old-pool proxy = regex-top20 ∪
  symbol-top20 file identities);
- applies the four frozen transforms **verbatim from N10EN** (baseline, full
  novel-first, guarded top5, diffaware) **without** mutating N10EN;
- fixes RUN-phase orders, THEN generates score-phase labels and scores the
  fixed orders (labels/gold for aggregate scoring only, never policy);
- computes the seven safety probe features as aggregate buckets;
- uploads only a sanitized aggregate-only report.

The held-out sample uses `canary_small_heldout` with target/scored/gold
`80/50/30` and `canary_medium_heldout` with `160/100/60`. Held-out selection uses manifest-listed repos after the
corresponding N10EN reference repo prefix. N10ER privately checks repo overlap
against that reference prefix and publishes only overlap count/bucket aggregates,
never repo/task identities.

## Status vocabulary

```text
n10er_safety_probe_pass_signal_reproduced_n10es_authorized
n10er_safety_probe_complete_no_signal_reproduced_n10es_authorized
n10er_safety_probe_inconclusive_insufficient_risk_bucket_n10es_authorized
n10er_safety_probe_inconclusive_insufficient_sample_n10es_authorized
n10er_safety_probe_unavailable_network_disabled  # default off (exit 0)
no_go_n10eq_gate_failed                          # contract failure (exit 1)
fail_no_public_tasks_generated                   # infra failure (exit 1)
fail_run_phase_candidate_generation              # infra failure (exit 1)
fail_clone_or_build                              # infra failure (exit 1)
fail_forbidden_scan                               # privacy failure (exit 1)
fail_schema_contract                              # schema failure (exit 1)
fail_contract_violation                           # contract failure (exit 1)
```

The top-level result answers whether the low-novelty + strong-baseline
full-displacement / guard-preservation safety signal reproduces. Arm aggregate
outcomes remain reported, but they do not alone define the phase status. The
workflow fails on contract/privacy/build/clone failures, not on valid no-signal
or inconclusive research results, including insufficient sample.

## Safety feature buckets (7, aggregate-only)

| Feature | Buckets |
|---|---|
| `top5_novel_candidate_item_count_bucket` | 0_to_2 / 3 / 4_to_5 |
| `baseline_prefix_strength` | strong_prefix_le_5 / weak_prefix_gt_5 / no_baseline_hit |
| `baseline_gold_proxy` | baseline_hit_proxy / baseline_miss_proxy |
| `full_displacement_risk` | low_novelty_strong_prefix_displacement_risk / other_no_displacement_risk |
| `guard_preservation_ref` | guard_preserved_baseline / guard_lost_or_no_baseline |
| `candidate_available_beyond_top10` | candidate_available_beyond_top10 / candidate_missing_or_within_top10 |
| `arm_selection` | full_novel_first / guarded_top5_novel_distinct |

All features are computed on aggregate buckets; no per-task raw
candidates/paths/ranks/gold are published. `gold_used_for_policy_bool=false`.

## Pass/fail gates (9, designed in N10EQ/N10ER)

1. `n10er_private_execution_inputs_aggregate_publication_only` — private bounded-CI orders/candidates/retrieval/labels may be used internally after freeze; raw publication is forbidden.
2. `n10er_displacement_risk_aggregate_only` — no per-task raw output.
3. `n10er_no_threshold_tuning` — frozen threshold >= 4 unchanged.
4. `n10er_no_method_winner_claim` — no guard/full/diffaware promotion.
5. `n10er_no_runtime_default_change` — safety probe stays opt-in/eval-only.
6. `risk_bucket_sufficiency_gate` — risk bucket has at least 5 tasks.
7. `low_novelty_strong_baseline_signal_gate` — full loses more baseline hits than guard and guard preserves at least one full loss.
8. `guard_reference_non_regression_gate` — guard does not lose more baseline hits than full/diffaware in the risk bucket.
9. `displacement_mechanism_classification_gate` — risk-bucket displacement classification is complete.

All gates evaluated on aggregate buckets; `gate_uses_gold_for_policy_bool=false`.

## Execution boundary

N10ER may privately produce/read orders/candidates/retrieval output/per-task
diagnostics/score-phase labels **after** RUN-phase orders are frozen. These
stay private/temp only; the public artifact is aggregate-only.
`n10en_artifact_mutated_bool=false`,
`n10en_semantics_reused_verbatim_bool=true`,
`n10en_private_task_ids_read_bool=false`, `frozen_rule_changed_bool=false`,
`threshold_tuned_bool=false`, `public_artifact_aggregate_only_bool=true`.

## Boundary

N10ER authorizes only the bounded public CI safety probe execution on a
held-out manifest-listed public sample plus the **N10ES audit** handoff (next
phase). It does **not** authorize: N10ER re-run, threshold tuning, new policy
experiments, frozen-rule changes, promotion of guard/full/diffaware,
runtime/default changes, method-winner claims, downstream/scaled retrieval,
selector/reranker, provider/model network, raw diagnostic publication, CI
variant execution, or any change to the frozen rule. All claim/stop fields
for these are `false`. `n10er_contract_authorized_bool=true` (from N10EQ) but
`n10er_execution_authorized_bool` is only `true` when the network is explicitly
enabled for this run.

Next allowed phase: **BEA-v1-N10ES Bounded Public CI Safety Probe Audit**.

## Workflow

- Workflow: `.github/workflows/bea-v1-n10er-bounded-public-ci-score-guard-safety-probe.yml`
- Inputs: `enable_public_github_network` (default `false`),
  `stage` (`canary_small_heldout` / `canary_medium_heldout`),
  `max_repos` (optional). Uploads only the sanitized aggregate JSON.

## Artifact

- Helper: `eval/bea_v1_n10er_bounded_public_ci_score_guard_safety_probe.py`
- Report: `artifacts/bea_v1_n10er_bounded_public_ci_score_guard_safety_probe/bea_v1_n10er_bounded_public_ci_score_guard_safety_probe_report.json`
