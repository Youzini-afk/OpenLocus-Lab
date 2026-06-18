# B10B Runtime-Shadow Replay (Ambiguous Branch Only)

Date: 2026-06-18

B10B is the next step after the B10 freeze of
`balanced_policy_v1_benchmark_routed`. It does **not** run any model, does
**not** search, does **not** tune policy quality, and does **not** defaultize.
It only tests whether a fixed, predeclared runtime-feature-only shadow
predicate can reproduce the **ambiguous branch** of the frozen benchmark-routed
spec's action on the same records.

> **Important claim boundary.** B10B does **not** prove a runtime-clean balanced
> policy. It only tests whether runtime features can shadow the ambiguous
> branch. The default `use_p25_action` still delegates to the P25
> benchmark-routed behavior, so this is **ambiguous-branch runtime-shadow
> only**, not a runtime-feature-only policy, not a default change, not a
> promotion candidate, and does not change `EvidenceCore`.

## Scope and claim level

```text
algorithm_spec_id: balanced_policy_v1_runtime_shadow_ambiguous_branch
claim_level: ambiguous_branch_runtime_shadow_only
full_runtime_clean_policy: false
ambiguous_branch_runtime_shadow_only: true
promotion_ready: false
default_should_change: false
evidencecore_semantics_changed: false
policy_search_performed: false
quality_strategy_tuned: false
runtime_calls_by_replay: 0
model_calls_by_replay: 0
aggregate_only_public_artifact: true
```

## Target action (mirrors the B10 frozen spec)

The target action reproduces the frozen
`balanced_policy_v1_benchmark_routed` semantics on each record:

```text
target_action = weak_only if ambiguous_or_query_noise else use_p25_action
ambiguous_or_query_noise = _ambiguous_like(task) or _query_noise(task)
```

* `_ambiguous_like` reads the benchmark public labels `task_bucket` and
  `task_risk_tags` for `{ambiguous, hallucination_risk, weak_candidates}`
  (benchmark public dependency).
* `_query_noise` reads `route_features.query_noise` (deterministic runtime).

## Shadow action (runtime features only, predeclared, no search)

The shadow action reads **only** runtime `route_features` and never reads
`task_bucket`, `task_risk_tags`, `has_gold`, `score_group`, or outcome metrics:

```text
shadow_action = weak_only if runtime_shadow_ambiguous else use_p25_action
runtime_shadow_ambiguous = query_noise
                         OR (candidate_support_exists AND anchor_disagreement_proxy)
anchor_disagreement_proxy = local_anchor AND NOT rrf_backed_by_anchor
```

`anchor_disagreement_proxy` is the runtime-only proxy for the ambiguous
branch: an anchor exists locally (`local_anchor`) but is not corroborated by
RRF (`NOT rrf_backed_by_anchor`).

### Required runtime features

All four must be present for the shadow action to be evaluable on a record:

* `route_features.query_noise`
* `route_features.candidate_support_exists`
* `route_features.local_anchor`
* `route_features.rrf_backed_by_anchor`

**Missing-feature policy.** If any required runtime feature is missing on a
record, the record is marked `missing` and the shadow action is **NOT** silently
defaulted to `false`. If every record is missing some required feature, the
report status is `insufficient_runtime_features` instead of `ok`.

## Replay source parameter

The replay carries an explicit `replay_source` field declaring where the
records came from. Two values are allowed:

* `synthetic_fixture` — records synthesized in memory by the self-test. The
  verdict is short-circuited (see [Verdict framework](#verdict-framework)
  below) and can never produce an empirical-support claim regardless of how
  clean the metrics look.
* `ci_ephemeral_records` — records loaded via `--records <path>` from CI
  ephemeral policy-record JSON. The full predeclared gate evaluation runs and
  the verdict may (in principle) yield `empirical_replay_support`.

This separation prevents a synthetic fixture from being mistaken for empirical
support.

## Aggregate-only report

The public report emits aggregate counts only — no per-task / per-repo /
candidate / path / span / snippet / prompt / response / gold / provider keys,
and no raw path / digest / provider strings. The `replay` block carries:

* `denominator` — total record count.
* `complete_feature_count` / `complete_feature_rate` — records with all
  required shadow features present.
* `missing_feature_counts` / `missing_feature_rates` — per-feature missing
  counts and rates.
* `records_with_any_missing_feature_count` / `_rate`.
* `target_action_distribution` — `{weak_only, use_p25_action}` over all
  records.
* `shadow_action_distribution` — `{weak_only, use_p25_action, missing}`.
* `confusion_matrix_target_x_shadow` — `target_action x shadow_action` counts.
* `agreement_denominator` / `agreement_overall_rate` — agreed / complete
  records.
* `agreement_per_target_action` — per-target-action agreement on complete
  records.
* `target_weak_only_total` / `target_use_p25_total` /
  `shadow_weak_only_total` / `shadow_use_p25_total`.
* `target_weak_only_recall` — stratified recall on the weak_only target.
* `target_use_p25_specificity` — stratified specificity on the use_p25 target.
* `shadow_weak_only_precision` — stratified precision of the shadow weak_only
  prediction.
* `label_driven_ambiguous_recall_qn0` — recall on the label-driven subset
  where `query_noise == 0` (the non-tautological subset; shadow cannot
  trivially agree via shared query_noise).
* `label_driven_ambiguous_denominator_qn0` — size of that qn0 subset; under
  the predeclared floor this fails the verdict (HARD gate, see below).
* `query_noise_only_recall_qn1` — recall on the shared-feature qn1 subset
  (agreement expected high but partly tautological).
* `cohens_kappa` — Cohen's kappa on the binary is_weak_only classification
  (complete records only).
* `silent_failure_checks` — see [Silent-failure checks](#silent-failure-checks).
* `outcome_audit` — see [Outcome-equivalence audit](#outcome-equivalence-audit).
* `feature_provenance` — per-feature dependency class and read-by flags.
* `status` — `ok` or `insufficient_runtime_features`.

The report top level additionally carries: `replay_source`,
`predeclared_gates` (the 10 gates, see
[Predeclared acceptance gates](#predeclared-acceptance-gates)),
`runtime_shadow_ambiguous_supported` (bool verdict),
`support_claim`, and (when the verdict is False)
`support_claim_reason`.

## Leakage guard

The self-test asserts that mutating `task_bucket`, `task_risk_tags`,
`has_gold`, `score_group`, **and** `outcome_metrics` does **not** change the
shadow action, while flipping the ambiguous labels **does** change the target
action. This proves the shadow predicate is invariant to benchmark public
labels and to all score-private fields, including `outcome_metrics`.

A separate sub-test mutates **only** `outcome_metrics` (everything else held
at base values) and asserts that both the shadow action and the target action
are unchanged — outcomes are scoring outputs, never routing inputs, and
neither predicate reads `outcome_metrics`.

## Predeclared acceptance gates

The gates are declared upfront in the algorithm spec so the verdict cannot be
retro-fitted to whatever the replay produced. All gates are HARD (logical AND):

```text
complete_feature_rate_min: 0.95
overall_action_exact_agreement_min: 0.90
target_weak_only_recall_min: 0.85
target_use_p25_specificity_min: 0.90
label_driven_ambiguous_recall_qn0_min: 0.75
label_driven_ambiguous_min_denominator: 10     # HARD gate, NOT escape clause
shadow_weak_only_precision_min: 0.80
cohens_kappa_min: 0.40
outcome_metrics_leakage_tested: true
no_silent_failure_required: true
```

The `label_driven_ambiguous_min_denominator: 10` gate is a HARD gate: if the
qn0 subset denominator is below 10, the recall metric is too thin to trust and
the verdict is `False` with
`support_claim_reason="insufficient_label_driven_denominator"`. It is **not**
an escape clause (OR-branch) that lets a thin qn0 subset pass on agreement
alone.

## Verdict framework

The report carries an explicit boolean verdict and two supporting fields:

* `runtime_shadow_ambiguous_supported` — bool. True only on the
  `ci_ephemeral_records` path when every predeclared gate passes.
* `support_claim` — one of:
  * `mechanics_only_synthetic_fixture` — replay ran on the synthetic fixture;
    no empirical claim is made regardless of metrics.
  * `empirical_replay_support_pending` — replay ran on `ci_ephemeral_records`
    but at least one gate failed (denominator, agreement, silent failure, or
    leakage guard).
  * `empirical_replay_support` — replay ran on `ci_ephemeral_records` and
    every predeclared gate passed.
* `support_claim_reason` — present iff the verdict is `False`. One of:
  * `synthetic_fixture_only` — short-circuit reason for the synthetic fixture.
  * `insufficient_label_driven_denominator` — qn0 denominator below the hard
    floor of 10.
  * `silent_failure_detected` — a silent-failure check tripped.
  * `insufficient_agreement` — at least one agreement/precision/kappa gate
    failed.
  * `leakage_guard_incomplete` — unreachable fallback; would fire only if the
    leakage guard patch were removed.

**Synthetic-fixture short-circuit.** When `replay_source ==
"synthetic_fixture"`, the verdict is unconditionally `False` with
`support_claim="mechanics_only_synthetic_fixture"` and
`support_claim_reason="synthetic_fixture_only"` — the metrics are still
computed and reported, but no empirical claim is made.

## Outcome-equivalence audit

On the disagreement subset, the audit partitions records by
`(target_action, shadow_action)` and reports per-partition outcome-metric
means (`added_gold_span`, `added_false_span`, `span_f0_5`,
`primary_false_positive_rate`). Four partitions are tracked:

* `target_weak_shadow_use_p25` — target said weak_only, shadow said use_p25.
* `target_use_p25_shadow_weak` — target said use_p25, shadow said weak_only.
* `agreement_weak_only` — both weak_only.
* `agreement_use_p25` — both use_p25_action.

If no record has usable outcome metrics the audit status is
`no_outcome_data`. Outcomes are **audit-only**: they are computed after
actions are chosen and are NEVER fed back into routing. The shadow predicate
does not read `outcome_metrics`.

## Silent-failure checks

Four booleans guard against the replay looking healthy while actually being
degenerate:

* `all_shadow_ambiguous` — every complete record was classified weak_only by
  the shadow (shadow collapses to "always weak").
* `all_shadow_non_ambiguous` — every complete record was classified
  use_p25_action by the shadow (shadow collapses to "never weak").
* `base_rate_only_suspected` — `cohens_kappa <= 0.05` while
  `agreement_overall_rate > 0.5` (agreement is high but only because both
  sides agree on the majority class; kappa near zero exposes it).
* `no_silent_failure` — `not (all_shadow_ambiguous or
  all_shadow_non_ambiguous or base_rate_only_suspected)`. This is a
  predeclared HARD gate.

## Cohen's kappa

Cohen's kappa is computed directly on the binary `is_weak_only`
classification over complete records only — no numpy / sklearn dependency.
`p_o` is the observed agreement rate; `p_e` is the chance agreement
`p_target_weak * p_shadow_weak + (1 - p_target_weak) * (1 - p_shadow_weak)`;
`kappa = (p_o - p_e) / (1 - p_e)` with the `1 - p_e > 0` and finiteness
guards. Kappa is bounded to `[-1.0, 1.0]` and verified by the report
validator.

## Current verdict

With the synthetic fixture, the current verdict is:

```text
replay_source: synthetic_fixture
runtime_shadow_ambiguous_supported: false
support_claim: mechanics_only_synthetic_fixture
support_claim_reason: synthetic_fixture_only
```

This is a **mechanics-validated scaffold**, not an empirical-support claim.
Empirical support remains pending until B10B runs on real CI ephemeral
records (`--records <path>`) and every predeclared gate passes.

## Safety invariants

```text
claim_level=ambiguous_branch_runtime_shadow_only
full_runtime_clean_policy=false
ambiguous_branch_runtime_shadow_only=true
promotion_ready=false
default_should_change=false
evidencecore_semantics_changed=false
policy_search_performed=false
quality_strategy_tuned=false
runtime_calls_by_replay=0
model_calls_by_replay=0
aggregate_only_public_artifact=true
```

## Excluded adapter layer

`model_adapter`, `output_mode`, provider credentials, provider endpoints, and
provider secrets are **NOT** part of this spec. They are an excluded adapter
layer (see
[`b4-b9-model-robust-evidence-conversion.md`](b4-b9-model-robust-evidence-conversion.md)).
Output mode is treated as a model-adapter configuration parameter, not an
OpenLocus algorithm variable.

## What B10B does NOT prove

B10B does **not** prove a runtime-clean balanced policy. The default
`use_p25_action` still delegates to `p25.route_bucket_routed_v0`, which re-reads
`task_bucket`/`task_risk_tags` and the inherited runtime route_features. A
runtime-feature-only balanced policy would require replacing the default branch
as well; B10B only shadows the ambiguous branch. In particular B10B:

* does **not** prove runtime-clean balanced policy;
* does **not** change the default — `use_p25_action` still delegates to P25;
* does **not** validate empirical support on the synthetic fixture (the
  synthetic fixture short-circuits to `mechanics_only_synthetic_fixture`);
* does **not** authorize B11 as "supported validation";
* does **not** change `EvidenceCore` semantics;
* does **not** promote or defaultize any candidate.

### B11 framing

B11 should be framed as **exploratory prospective stress test**, not
"supported validation", until B10B runs on real CI ephemeral records and
passes every predeclared gate. The shadow predicate is FROZEN; no tuning
during B11. Any predicate change should start a new frozen spec / version.

## CI integration path

To run B10B against CI ephemeral records:

```bash
python3 eval/b10b_runtime_shadow_replay.py --records <path>
```

The `<path>` should point at the CI ephemeral p25-policy-record JSON written
to `$RUNNER_TEMP/p25-policy-records-ephemeral-v1/*.json` **before** the runner
cleans up. The replay runs in `replay_source="ci_ephemeral_records"` mode and
the full predeclared gate evaluation executes. The written report is
aggregate-only (no raw records, no per-task identifiers) and the raw records
are never committed.

## Artifacts

* `artifacts/b10b_runtime_shadow_replay/balanced_policy_v1_runtime_shadow_ambiguous_branch.algorithm.json`
* `artifacts/b10b_runtime_shadow_replay/b10b_runtime_shadow_replay_report.json`

## Self-test

```bash
python3 eval/b10b_runtime_shadow_replay.py --self-test
```

The self-test synthesizes p25-policy-record-like records in memory (it does
not require live artifacts) and runs 10 checks:

* `perfect_agreement` — query_noise fires and both target/shadow choose
  weak_only; no-noise + no-anchor-disagreement case where both choose
  use_p25_action.
* `disagreement` — target weak_only (ambiguous label) vs shadow use_p25_action;
  and target use_p25_action vs shadow weak_only (anchor disagreement proxy
  fires).
* `missing_feature` — `local_anchor` or `query_noise` absent marks the record
  missing; all-missing yields `status="insufficient_runtime_features"`.
* `leakage_guard` — mutating
  `task_bucket`/`task_risk_tags`/`has_gold`/`score_group`/`outcome_metrics`
  does not change the shadow action but changes the target action when
  relevant; an outcome_metrics-only sub-test asserts neither predicate reads
  outcomes.
* `replay_aggregate` — full aggregate block: confusion matrix, stratified
  metrics, label-driven qn0/qn1 subsets, Cohen's kappa, silent-failure
  checks, outcome audit partitions, verdict fields.
* `verdict_synthetic_fixture_unsupported` — a clean synthetic fixture must
  never yield an empirical-support verdict; verdict is `False` with
  `support_claim="mechanics_only_synthetic_fixture"`.
* `verdict_insufficient_denominator_unsupported` — a `ci_ephemeral_records`
  replay where every agreement gate passes but the qn0 denominator is below
  10 must yield verdict `False` with
  `support_claim="empirical_replay_support_pending"` and
  `support_claim_reason="insufficient_label_driven_denominator"`.
* `forbidden_scan` — forbidden public keys and conservative leaked-value
  patterns (content hashes, URLs, credential assignments, 64-hex digests,
  raw `/`-separated paths) are flagged; clean `module::symbol` provenance is
  not.
* `b10_reference` — the B10 frozen spec exists on disk and the B10B
  spec/report reference its id and hash-matched flag.
* `spec_hash_stable` — the on-disk algorithm spec loads, re-hashes, and
  re-loads to the same SHA-256; it equals `build_algorithm_spec()` output.

## CLI

```bash
python3 eval/b10b_runtime_shadow_replay.py --self-test
python3 eval/b10b_runtime_shadow_replay.py --records <path>
```

`--self-test` and `--records` are mutually exclusive; one of them is
required. `--self-test` runs in `replay_source="synthetic_fixture"` mode and
prints the self-test result JSON. `--records <path>` loads a JSON array of
p25-policy-record-like records, runs in `replay_source="ci_ephemeral_records"`
mode, writes the aggregate-only report artifact to
`artifacts/b10b_runtime_shadow_replay/b10b_runtime_shadow_replay_report.json`,
and prints a summary containing `replay_source`, `status`, agreement metrics,
`cohens_kappa`, `silent_failure_checks`, the verdict, `support_claim`, and (if
present) `support_claim_reason`.
