# B18 OOD / Temporal Evaluation

Date: 2026-06-19

B18 is the **OOD (out-of-distribution) / temporal evaluation** phase.
The goal is a **frozen, preregistered OOD / temporal evaluation** of
the retrieval / candidate / Evidence pipeline across five FROZEN split
axes — `temporal_split`, `repo_split`, `language_split`,
`model_family_split`, `adversarial_split` — **under a no-retuning
protocol** (no policy search, no quality strategy tuning, no retrieval
policy change, no EvidenceCore semantics change, no default change, no
promotion) so an in-distribution average cannot be mistaken for OOD or
temporal generalization.

B18 is a **bounded preregistration + public-aggregate no-go screen
phase**, NOT a real OOD / temporal evaluation, NOT a policy search,
NOT a quality strategy tuning, NOT a default change, NOT an
EvidenceCore semantics change, NOT a promotion. The shipped skeleton
performs NO real OOD / temporal evaluation, NO per-record replay, NO
commit-chronology temporal split, NO adversarial holdout, NO
per-repo / per-language / per-model-family cell computation, NO
worst-group or CVaR metric computation. The frozen preregistration
(`eval/b18_ood_temporal_evaluation.py`) defines the split axes, the
required per-record inputs, the metric registry, the hard gates, and
the experimental structure (no-OOD-temporal-evaluation feasibility →
frozen no-retuning protocol → per-axis holdout evaluation → worst-
group / CVaR reporting); the bounded public-aggregate no-go screen
(reads the already-published B11 prospective matrix aggregate report
plus optional R15 / R20 / R26 repo locks and dataset manifests and
emits a `no_go_public_aggregate_only` (or
`public_aggregate_carry_forward_only`) verdict.

> **Important claim boundary.** B18 IS the ood-temporal-evaluation
> *stage* (`stage_is_ood_temporal_evaluation=true`), but the shipped
> skeleton performs NO real OOD / temporal evaluation
> (`ood_temporal_evaluation_performed=false`), NO metrics evaluation
> (`metrics_evaluated=false`), NO policy search
> (`policy_search_performed=false`), NO quality strategy tuning
> (`quality_strategy_tuned=false`), and NO promotion
> (`promotion_ready=false`). The synthetic-fixture / `--input` stub
> report sets `promotion_ready=false`, `default_should_change=false`,
> `evidencecore_semantics_changed=false`, `retrieval_policy_changed=false`,
> `metrics_evaluated=false`, `new_provider_calls=0` so the public
> artifact cannot be mistaken for an empirical B18 OOD / temporal
> result. This commit is strictly a skeleton / no-go commit: the
> current flags (`ood_temporal_evaluation_performed=false`,
> `metrics_evaluated=false`, `policy_search_performed=false`,
> `quality_strategy_tuned=false`, `real_ood_temporal_supported=false`)
> remain false. Any future real B18 empirical path would require its
> own separate preregistration; the exact flag schema for that future
> path is future work and is NOT present in this skeleton. B18 results
> in this commit are research candidates only: this skeleton / no-go
> commit authorizes no default change, no retrieval-policy change, no
> backend quality promotion, no OOD / temporal evaluation, no
> EvidenceCore modification, and no claim that any retrieval variant
> improves a downstream agent.

> **Important no-retuning boundary.** The OOD / temporal evaluation is
> a **generalization** comparison under a **frozen no-retuning
> protocol**. A retrieval variant that wins on the in-distribution
> task-screen split but regresses on the temporal / repo / language /
> model_family / adversarial holdout is rejected regardless of its
> in-distribution numbers. The no-retuning protocol is the
> precondition that makes the OOD / temporal evaluation meaningful:
> without it, OOD / temporal comparisons would silently trade
> generalization for in-distribution fit.

> **CRITICAL anti-fabrication boundary.** The skeleton MUST NOT
> compute fake ood_generalization_gap / temporal_holdout_delta /
> repo_holdout_metric / language_holdout_metric /
> model_family_holdout_metric / adversarial_robustness_score /
> worst_group_metric / cvar_tail_metric / per_cell_denominator /
> temporal_split_integrity / no_retuning_proof_metric /
> citation_validity / stale_evidencecore_rejection_rate metrics from
> the existing B11 aggregate means or from the R15 / R20 / R26 repo
> locks. The B11 aggregate carries public model-family means + repo
> slice list + sanitized failure slices but NO per-record, per-time-
> index, per-repo-per-language cell, model_family x repo matrix,
> adversarial holdout outcome, or temporal holdout outcome; the R15 /
> R20 / R26 repo locks are synthetic / static snapshots with no real
> commit chronology or time axis, so any B18 OOD / temporal metric
> computed from them would be a fabrication. The synthetic fixture
> validates only that the split axes, metric names, hard gates, and
> required inputs are wired correctly; it does NOT present synthetic
> metric values as empirical B18 OOD / temporal results. The report
> surfaces `ood_temporal_evaluation_performed=false`,
> `metrics_evaluated=false`, `policy_search_performed=false`,
> `quality_strategy_tuned=false`, `real_ood_temporal_supported=false`,
> and `no_fake_ood_metrics_from_aggregate_means=true` so a reader
> cannot mistake the skeleton for an empirical B18 OOD / temporal
> result.

## Preregistration declaration

The following artifacts, split axes, required per-record inputs, metric
registry, hard gates, experimental structure, and predeclared
success / partial / failure criteria are **FROZEN** before any B18
empirical OOD / temporal evaluation. No retuning of the split axes,
the no-retuning protocol, the metric registry, the hard gates, or the
success criteria is allowed after B18 empirical OOD / temporal runs
begin. Any post-hoc analysis must be labeled exploratory and require a
separate validation round.

### Frozen artifacts

- `b11_prospective_matrix_aggregate` (B11 prospective matrix aggregate
  report) — referenced, not modified; **aggregate-only carry-forward**,
  not promotion evidence, not quality proof, not OOD / temporal proof
- `r15_repos_lock` (R15 repos.lock.jsonl) — referenced, not modified;
  **metadata-only carry-forward** (repo counts, language metadata
  availability); synthetic static snapshot, not temporal proof
- `r20_auto_wide_repos_lock` (R20 repos.lock.jsonl) — referenced, not
  modified; **metadata-only carry-forward**; synthetic static snapshot
- `r26_auto_stress_repos_lock` (R26 repos.lock.jsonl) — referenced,
  not modified; **metadata-only carry-forward**; synthetic static
  snapshot
- B18 algorithm spec itself
  (`artifacts/b18_ood_temporal_evaluation/b18_ood_temporal_evaluation.algorithm.json`)
  — frozen before any OOD / temporal evaluation; stable sha256

## Generalization-only objective (FROZEN)

Produce a **frozen, preregistered OOD / temporal evaluation** across
the five frozen split axes under a **no-retuning protocol** so an in-
distribution average cannot be mistaken for OOD / temporal
generalization. B18 does NOT perform a real OOD / temporal evaluation
in this skeleton, does NOT search a policy, does NOT tune a quality
strategy, does NOT change EvidenceCore, does NOT promote a default,
does NOT change retrieval policy, and does NOT claim that any
retrieval variant improves a downstream agent.

## Split axes (FROZEN)

The split axes are the closed set of OOD / temporal axes a B18
evaluation must report. Each axis has a FROZEN holdout definition; a
B18 evaluation that omits any axis is incomplete.

- `temporal_split` — a chronological time / commit-chronology holdout
  (later commits held out from earlier commits per repo); the R15 /
  R20 / R26 repo locks carry only a single static snapshot commit
  label (e.g. `r15-snapshot`), NOT a real chronological ordering
- `repo_split` — a leave-one-repo-out holdout (a repo held out from
  the rest); the B11 aggregate carries only a sanitized repo slice
  list, NOT per-repo outcome cells
- `language_split` — a leave-one-language-out holdout (a primary
  language held out from the rest); the B11 aggregate has no per-
  language cells
- `model_family_split` — a leave-one-model-family-out holdout (a
  model family held out from the rest); the B11 aggregate reports
  per-model-family means only, NOT the model_family x repo matrix
- `adversarial_split` — an adversarial holdout (stress-category
  outcomes held out from in-distribution outcomes); the R20 / R26
  manifests carry stress category availability, NOT adversarial
  holdout outcomes

## No-retuning protocol (FROZEN)

The no-retuning protocol is FROZEN before any B18 empirical OOD /
temporal evaluation:

- `no_retuning_protocol = true`
- `no_policy_search = true` (`policy_search_performed=false`)
- `no_quality_strategy_tuning = true` (`quality_strategy_tuned=false`)
- `no_retrieval_policy_change = true` (`retrieval_policy_changed=false`)
- `no_evidencecore_semantics_change = true`
  (`evidencecore_semantics_changed=false`)
- `no_default_change = true` (`default_should_change=false`)
- `no_promotion = true` (`promotion_ready=false`)

No metric on any holdout split may feed back into the task screen, the
no-retuning protocol, the retrieval policy, or the EvidenceCore
semantics.

## Metric registry (FROZEN)

The metric NAMES B18 will compute when real per-record OOD / temporal
inputs are available. The skeleton defines them and validates the hard
gates, but does NOT compute fake metric values from the B11 aggregate
means or from the R15 / R20 / R26 repo locks.

- `ood_generalization_gap`
- `temporal_holdout_delta`
- `repo_holdout_metric`
- `language_holdout_metric`
- `model_family_holdout_metric`
- `adversarial_robustness_score`
- `worst_group_metric`
- `cvar_tail_metric`
- `per_cell_denominator`
- `temporal_split_integrity`
- `no_retuning_proof_metric`
- `citation_validity`
- `stale_evidencecore_rejection_rate`

Every metric requires per-record OOD / temporal inputs (per-record
records, per-record time index, per-record commit chronology, per-
record repo / language / model_family axes, per-record task category,
per-record adversarial holdout membership, per-record temporal holdout
membership, per-record outcome label, per-record citation validity,
per-record stale rejection, per-record EvidenceCore rejection, per-
record randomized run order proof, per-record no-retuning proof,
shared frozen evaluation protocol manifest); none can be computed
from the B11 aggregate means or from the R15 / R20 / R26 repo locks.

## Hard gates (FROZEN)

The following hard gates are FROZEN before any B18 OOD / temporal
evaluation. A split axis or evaluation run that fails any gate is
rejected, regardless of its aggregate OOD / temporal metrics.

- **per_record_data_gate**: the B18 OOD / temporal evaluation cannot
  complete without per-record outcome records. The skeleton does not
  evaluate this gate; it only defines it and reports the current
  status.
- **time_axis_gate**: every per-record outcome must carry a real time
  index (not a single static snapshot commit label). The skeleton
  does not evaluate this gate; it only defines it.
- **commit_chronology_gate**: every repo must carry a real commit
  chronology (a chronological ordering of commits, not a single
  snapshot). The R15 / R20 / R26 repo locks fail this gate (single
  static snapshot commit label). The skeleton does not evaluate this
  gate; it only defines it.
- **no_retuning_gate**: every B18 evaluation run must carry a
  no-retuning proof (no policy search, no quality strategy tuning, no
  retrieval policy change, no EvidenceCore semantics change). The
  skeleton does not evaluate this gate; it only defines it.
- **adversarial_holdout_gate**: every B18 evaluation must report
  adversarial holdout outcomes per axis. The skeleton does not
  evaluate this gate; it only defines it.
- **temporal_holdout_gate**: every B18 evaluation must report
  temporal holdout outcomes per axis. The skeleton does not evaluate
  this gate; it only defines it.
- **evidencecore_materialization_gate**: every per-record outcome
  must materialize through EvidenceCore with citation-valid evidence;
  no B18 path may bypass EvidenceCore. The skeleton does not evaluate
  this gate; it only defines it.
- **stale_citation_gate**: stale and EvidenceCore-rejected candidates
  must be rejected on every axis; citation validity must be `1.0`. The
  skeleton does not evaluate this gate; it only defines it.
- **privacy_gate**: `aggregate_only_public_artifact=true`; no raw
  records, task IDs, repo IDs, candidate IDs, paths, file paths,
  spans, snippets, prompts, responses, diffs, patches, test execution
  results, solve labels, agent event logs, per-record records, time
  indices, commit chronology, outcome labels, gold spans, private
  labels, provider keys, base URLs, API keys/secrets/tokens, content
  SHAs, digests, or line ranges in any public artifact;
  `new_provider_calls=0` in the skeleton.
- **promotion_false_gate**: `promotion_ready=false`,
  `default_should_change=false`,
  `evidencecore_semantics_changed=false`,
  `retrieval_policy_changed=false`,
  `backend_quality_promoted=false`,
  `stage_is_ood_temporal_evaluation=true`,
  `ood_temporal_evaluation_performed=false`,
  `metrics_evaluated=false`, `policy_search_performed=false`,
  `quality_strategy_tuned=false`,
  `real_ood_temporal_supported=false` are always present, so a
  skeleton / stub / no-go report cannot be misread as a promoted
  retrieval variant or a B18 OOD / temporal result.

## Split protocol (FROZEN)

Real B18 splits per-record inputs into a **task-screen split** and a
**fresh-validation split**, stratified by `(repo, language,
model_family, time)`. The split protocol is
`stratified_by_repo_language_model_family_time` with
`task_screen_fraction=0.50` and `fresh_validation_fraction=0.50`. The
fresh-validation split is held out and reported once
(`fresh_validation_split_reported_once=true`). No metric on the
fresh-validation split may feed back into the task screen or the
no-retuning protocol.

## Worst-group reporting

B18 reports worst-group metrics over `{repo, language, model_family,
time, adversarial_category}` groups, plus a `CVaR_20%` tail average
(worst 20% of group metrics). The CVaR tail fraction is
`cvar_alpha=0.20` (frozen). The minimum per-cell denominator is
`min_denominator_per_cell=30`; cells below this denominator are
suppressed and reported as `insufficient_data`.

## Privacy / publication gates

Public artifacts must be aggregate-only. The B18 evaluator enforces:

- **no** raw records, task IDs, repo IDs, candidate IDs, paths, file
  paths, spans, snippets, prompts, responses, diffs, patches, test
  execution results, solve labels, agent event logs, per-record
  records, time indices, commit chronology, outcome labels, gold
  spans, private labels, provider keys, base URLs, API keys/secrets/
  tokens, content SHAs, digests, or line ranges in any public artifact;
- **no** raw filesystem path strings, 64-char hex digests, http(s)
  URLs, or credential assignments as values;
- `aggregate_only_public_artifact=true`;
- `new_provider_calls=0` (skeleton; no live LLM calls and no live
  OOD / temporal evaluation);
- `forbidden_public_key_scan_clean=true`.

The public no-go screen uses both the B18 evaluator's own
`_recursive_key_scan` (stricter forbidden-key list including
`file_path`, `gold`, `commit`, `commit_chronology`, `span`, `raw_record`,
etc.) and `b6_lite_interpretable_policy_search._walk_forbidden` (the
shared public-output scan used by B11 / B12 / B13 / B14 / B15 / B16 /
B17 public screens).

## Predeclared success / partial / failure criteria

The criteria below are FROZEN before any B18 empirical OOD / temporal
evaluation (`PREDECLARED_CRITERIA`):

| Outcome | Criterion |
| --- | --- |
| **Success** | Every split axis reports a per-cell denominator above the frozen minimum, the OOD generalization gap is within the frozen tolerance, the temporal holdout delta is within the frozen tolerance, the worst-group metric meets the frozen minimum, the no-retuning proof holds, citation validity is `1.0`, AND every hard gate passes on the fresh-validation split. |
| **Partial** | Some split axes report a sufficient per-cell denominator but not all; or one axis is within the OOD / temporal tolerances but another is not; or the no-retuning proof holds but adversarial / temporal holdout outcomes are incomplete. |
| **Failure** | No split axis reports a sufficient per-cell denominator on the fresh-validation split, OR any hard gate fails (per-record data, time axis, commit chronology, no-retuning, adversarial holdout, temporal holdout, EvidenceCore materialization, stale / citation, privacy, promotion false). |

Frozen numeric gates:

- `ood_generalization_gap_maximum = 0.10`
- `temporal_holdout_delta_tolerance = 0.05`
- `worst_group_metric_minimum = 0.50`
- `citation_validity_required = 1.0`
- `stale_evidencecore_rejection_required = true`
- `no_default_expansion_required = true`
- `evidencecore_materialization_required = true`
- `cvar_alpha = 0.20`
- `min_denominator_per_cell = 30`
- `task_screen_fraction = 0.50`
- `fresh_validation_fraction = 0.50`
- `fresh_validation_split_reported_once = true`
- `no_retuning_protocol = true`
- `no_policy_search = true`
- `no_quality_strategy_tuning = true`
- `no_retrieval_policy_change = true`
- `no_evidencecore_semantics_change = true`
- `no_default_change = true`
- `no_promotion = true`

The B18 verdict framework emits one of:

- `success` (every split axis reports a sufficient per-cell
  denominator, OOD / temporal tolerances met, worst-group minimum met,
  no-retuning proof holds, all gates pass on the fresh-validation
  split)
- `failure` (no axis reports a sufficient per-cell denominator, or
  any hard gate fails)
- `partial` (some axes report a sufficient denominator, not all; or
  no-retuning proof holds but holdout outcomes incomplete)
- `insufficient_data` (synthetic fixture, or too few per-record inputs)
- `not_implemented` (`--input` stub, real B18 OOD / temporal
  evaluation deferred)

The skeleton only emits `insufficient_data` (synthetic fixture) or
`not_implemented` (ci_ephemeral_records stub); `success` / `failure` /
`partial` are NOT emitted by this skeleton. Any future real B18
empirical path that might emit them would require its own separate
preregistration, and its exact flag schema is future work and is NOT
present in this skeleton. This commit keeps
`ood_temporal_evaluation_performed=false`,
`metrics_evaluated=false`, `policy_search_performed=false`,
`quality_strategy_tuned=false`, and
`real_ood_temporal_supported=false` strictly.

## Required per-record inputs (real-B18 data contract)

Real B18 OOD / temporal evaluation requires ALL of the following per
record. If any is missing, real B18 cannot run and the skeleton emits
`insufficient_data` / `not_implemented`.

- `per_record_record`
- `per_record_time_index`
- `per_record_commit_chronology`
- `per_record_repo_axis`
- `per_record_language_axis`
- `per_record_model_family_axis`
- `per_record_task_category`
- `per_record_adversarial_holdout_membership`
- `per_record_temporal_holdout_membership`
- `per_record_outcome_label`
- `per_record_citation_validity`
- `per_record_stale_rejection`
- `per_record_evidencecore_rejection`
- `per_record_randomized_run_order_proof`
- `per_record_no_retuning_proof`
- `shared_frozen_evaluation_protocol_manifest`

## Existing B11 / R15 / R20 / R26 aggregate carry-forward

The existing public artifacts are **aggregate-only / metadata-only
carry-forward**, not OOD / temporal proof and not promotion evidence:

- B11 prospective matrix aggregate
  (`artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json`):
  public model-family means + sanitized repo slice list + sanitized
  failure slices; `promotion_ready=false`;
  `aggregate_only_public_artifact=true`; NO per-record records, NO
  time axis, NO commit chronology, NO per-repo-per-language cells, NO
  model_family x repo matrix, NO adversarial holdout outcomes, NO
  temporal holdout outcomes
- R15 repos.lock.jsonl (`fixtures/r15/repos.lock.jsonl`): repo count
  + primary language metadata; single static snapshot commit label
  (`r15-snapshot`); NO commit chronology, NO time axis
- R20 repos.lock.jsonl (`fixtures/r20_auto_wide/repos.lock.jsonl`):
  repo count + primary language metadata + stress category
  availability (from `dataset_manifest.json`); single static snapshot
  commit label (`r20-snapshot`); NO commit chronology, NO time axis
- R26 repos.lock.jsonl (`fixtures/r26_auto_stress/repos.lock.jsonl`):
  repo count + primary language metadata + stress category
  availability (from `dataset_manifest.json`); single static snapshot
  commit label (`r26-snapshot`); NO commit chronology, NO time axis

These artifacts are pre-B18 signals only. They do NOT contain
per-record OOD / temporal inputs, do NOT contain a real time axis or
commit chronology, and do NOT contain per-repo-per-language cells or
a model_family x repo matrix. They are carried forward as
**aggregate-only / metadata-only**, not as OOD / temporal proof.

## Missing inputs that block real B18

The bounded public-aggregate no-go screen enumerates the specific
missing inputs that block real B18 from the public aggregates:

- `no_per_record_records`
- `no_time_axis`
- `no_commit_chronology`
- `no_per_repo_per_language_cells_in_public_b11`
- `no_model_family_x_repo_matrix`
- `no_adversarial_holdout_outcomes`
- `no_temporal_holdout_outcomes`

## Safety invariants

```text
promotion_ready=false
default_should_change=false
evidencecore_semantics_changed=false
retrieval_policy_changed=false
backend_quality_promoted=false
stage_is_ood_temporal_evaluation=true (B18 stage IS OOD / temporal evaluation)
ood_temporal_evaluation_performed=false (skeleton performs no OOD / temporal evaluation)
metrics_evaluated=false (skeleton; no fake OOD / temporal metrics from aggregate means)
policy_search_performed=false (no-retuning protocol)
quality_strategy_tuned=false (no-retuning protocol)
real_ood_temporal_supported=false
new_provider_calls=0 (skeleton; no live LLM calls)
no_fake_ood_metrics_from_aggregate_means=true
aggregate_only_public_artifact=true
```

## What B18 does NOT prove

- B18 does **not** perform a real OOD / temporal evaluation.
- B18 does **not** replay per-record outcomes.
- B18 does **not** construct a real temporal / commit-chronology split.
- B18 does **not** construct an adversarial holdout.
- B18 does **not** compute per-repo / per-language / per-model-family
  cells.
- B18 does **not** compute ood_generalization_gap /
  temporal_holdout_delta / repo_holdout_metric /
  language_holdout_metric / model_family_holdout_metric /
  adversarial_robustness_score / worst_group_metric /
  cvar_tail_metric / per_cell_denominator / temporal_split_integrity
  / no_retuning_proof_metric / citation_validity /
  stale_evidencecore_rejection_rate metrics from the B11 aggregate
  means or from the R15 / R20 / R26 repo locks.
- B18 does **not** search a policy.
- B18 does **not** tune a quality strategy.
- B18 does **not** promote any retrieval variant.
- B18 does **not** change any defaults.
- B18 does **not** change retrieval policy.
- B18 does **not** change `EvidenceCore` semantics.
- B18 does **not** claim that any retrieval variant improves a
  downstream agent.
- B18 results are research candidates only; a B18-frozen retrieval
  candidate is NOT a promoted retrieval variant and is NOT the new
  default until separately promoted via the standard promotion
  process.
- B18's `--input` path is a stub (`verdict="not_implemented"`); full
  per-record OOD / temporal evaluation is deferred to a later task.
- The existing B11 / R15 / R20 / R26 aggregates are **not** OOD /
  temporal proof; they are aggregate-only / metadata-only carry-
  forward.

## Self-test (read-only) and explicit artifact regeneration

```bash
python3 eval/b18_ood_temporal_evaluation.py --self-test
python3 eval/b18_ood_temporal_evaluation.py --regenerate-artifacts
python3 eval/b18_ood_temporal_evaluation.py --self-test
python3 eval/b18_ood_temporal_evaluation.py \
    --public-screen --out artifacts/b18_ood_temporal_evaluation/b18_public_ood_temporal_screen_report.json
```

The `eval/b18_ood_temporal_evaluation.py --self-test` run is
**read-only**: it verifies the split axes, required per-record inputs,
metric registry, hard gates, and experimental structure against a
synthetic fixture (definitions-only; no per-record OOD / temporal
inputs, no computed metric values) and compares the in-memory expected
algorithm spec + report to the on-disk artifacts, **failing on
drift**. It does NOT mutate checked-in artifacts. It does NOT emit a
raw spec sha256 in stdout (mirrors B17; only the boolean
`algorithm_spec_sha256_matched` / `algorithm_spec_sha256_stable` flags
are surfaced). It emits `stage_is_ood_temporal_evaluation=true`,
`ood_temporal_evaluation_performed=false`, `metrics_evaluated=false`,
`policy_search_performed=false`, `quality_strategy_tuned=false`,
`real_ood_temporal_supported=false`, `new_provider_calls=0`,
`no_fake_ood_metrics_from_aggregate_means=true`, so the synthetic-
fixture report is unambiguously NOT an empirical B18 OOD / temporal
result.

The read-only self-test runs these checks:

1. `forbidden_scan` — forbidden public keys/values scan (covers the
   task-spec list: raw records, task_id, path, file_path, span,
   snippet, prompt, response, gold, label, content_sha, provider_key,
   api_key)
2. `spec_hash_stable` — algorithm spec sha256 stability
3. `split_axes_closed` — 5 frozen axes; no-retuning protocol frozen
4. `required_per_record_inputs` — required inputs (the real-B18 data
   contract)
5. `missing_inputs_for_real_b18` — the 7 frozen gaps from the task
   spec are present
6. `metric_registry` — 13 metric names defined; no aggregate-mean
   metrics
7. `hard_gates_defined` — per-record data / time axis / commit
   chronology / no-retuning / adversarial holdout / temporal holdout
   / EvidenceCore materialization / stale-citation / privacy /
   promotion-false gates defined
8. `experimental_structure_frozen` — 4 frozen stages; no feedback
9. `no_fake_ood_metrics_from_aggregate_means` — synthetic fixture has
   no per-record OOD / temporal inputs and no metric values
10. `input_stub_not_implemented` — `--input` stub returns
    `not_implemented`
11. `reference_artifacts_pinned` — B11 aggregate + R15 / R20 / R26
    repo locks present on disk
12. `public_screen_no_go` — bounded public no-go screen emits
    `no_go_public_aggregate_only` and no fake metrics
13. `public_screen_optional_artifacts_absent` — absent R15 / R20 / R26
    artifacts are reported as `not_present` rather than failing
14. `artifacts_match_in_memory` — read-only drift check: in-memory
    expected spec + report match the on-disk artifacts

`python3 eval/b18_ood_temporal_evaluation.py --regenerate-artifacts`
is the ONLY path that mutates checked-in artifacts: it (re)writes
the on-disk algorithm spec + synthetic-fixture report + canonical
public no-go screen report from the current build functions. After
mutating, re-run `--self-test` to confirm the on-disk artifacts now
match the in-memory expected objects (no drift).

The `--input` path is a non-canonical stub path: it requires an
explicit `--out` destination and refuses to write ANY path inside
`artifacts/b18_ood_temporal_evaluation/` (canonical report, algorithm
spec, or public no-go screen report). It can write a temporary stub
report for development, but it does not mutate checked-in B18
artifacts.

The `--public-screen --out <path>` path runs the bounded public-
aggregate no-go screen from the current public artifacts (B11
aggregate + optional R15 / R20 / R26 repo locks and manifests) and
writes to the explicit `--out` path. If `--out` is absent, the
canonical public screen artifact is written ONLY when invoked from
`--regenerate-artifacts`; otherwise `--out` is required for non-self-
test to avoid accidental checked-in mutation.

The `--public-screen` self-test (via the `public_screen_no_go` and
`public_screen_optional_artifacts_absent` self-test checks) verifies
the bounded public no-go screen against the real on-disk B11 + R15 +
R20 + R26 public artifacts. It emits
`verdict=no_go_public_aggregate_only` (or
`public_aggregate_carry_forward_only`), with
`ood_temporal_evaluation_performed=false`, `metrics_evaluated=false`,
`policy_search_performed=false`, `quality_strategy_tuned=false`,
`real_ood_temporal_supported=false`,
`full_b18_ood_temporal_evaluation_possible_from_public_artifacts=false`.

## Artifacts

- `artifacts/b18_ood_temporal_evaluation/b18_ood_temporal_evaluation.algorithm.json`
  (frozen spec; deterministic, stable sha256; regenerated only via
  `--regenerate-artifacts`)
- `artifacts/b18_ood_temporal_evaluation/b18_ood_temporal_evaluation_report.json`
  (synthetic-fixture self-test report, verdict `insufficient_data`;
  `ood_temporal_evaluation_performed=false`, `metrics_evaluated=false`,
  `policy_search_performed=false`, `quality_strategy_tuned=false`,
  `real_ood_temporal_supported=false`,
  `stage_is_ood_temporal_evaluation=true`,
  `no_fake_ood_metrics_from_aggregate_means=true`;
  no empirical per-record metric values)
- `artifacts/b18_ood_temporal_evaluation/b18_public_ood_temporal_screen_report.json`
  (bounded public-aggregate no-go screen report;
  `verdict=no_go_public_aggregate_only` (or
  `public_aggregate_carry_forward_only`);
  `full_b18_ood_temporal_evaluation_possible_from_public_artifacts=false`;
  carries forward B11 `promotion_ready=false`,
  `aggregate_only_public_artifact=true`, and the absence of per-record
  / time / cell / matrix / holdout axes; carries forward R15 / R20 /
  R26 repo counts, language metadata availability, and stress
  category availability; aggregate-only / metadata-only, no raw
  records, paths, prompts, responses, snippets, diffs, patches, test
  results, task IDs, repo IDs, content SHAs, or commit chronology)

## What's autonomous vs. needs user action

### Autonomous (can be done now)

- B18 plan document (this file)
- B18 evaluator skeleton (`eval/b18_ood_temporal_evaluation.py`) +
  read-only `--self-test` (compares in-memory expected artifacts to
  on-disk artifacts, fails on drift) and explicit
  `--regenerate-artifacts` mutating path + `--public-screen --out`
  bounded public no-go screen path
- B18 frozen algorithm spec + synthetic-fixture report artifacts
- B18 bounded public-aggregate no-go screen +
  `artifacts/b18_ood_temporal_evaluation/b18_public_ood_temporal_screen_report.json`
  (reads the published B11 matrix + optional R15 / R20 / R26 repo
  locks and manifests; emits `no_go_public_aggregate_only` /
  `public_aggregate_carry_forward_only`; never claims OOD / temporal
  evaluation, never computes an OOD / temporal metric from aggregate
  means, never promotes a retrieval variant, never changes retrieval
  policy, never declares a winner)

### Needs prospective per-record data collection

- B18 real OOD / temporal evaluation requires prospective per-record
  outcome records with a real time axis and commit chronology per
  repo, plus per-repo / per-language / per-model-family cells and
  adversarial and temporal holdout memberships under a frozen no-
  retuning protocol, plus per-record citation validity, stale
  rejection, EvidenceCore rejection, randomized run order proof, no-
  retuning proof, and a shared frozen evaluation protocol manifest.
  If those records are not yet produced, B18 emits
  `insufficient_data` / `not_implemented`.

### Needs user review

- Results interpretation
- Decision to proceed to a real B18 empirical OOD / temporal
  evaluation path (separate preregistration required; must include
  prospective per-record data collection with a real time axis and
  commit chronology)
- Decision to expand from the minimum viable split axis set to a
  larger set (separate preregistration required)

## Next steps after B18

- **B18 success** (future real B18 path): every split axis reports a
  sufficient per-cell denominator, OOD / temporal tolerances met,
  worst-group minimum met, no-retuning proof holds, all hard gates
  pass. Proceed via the standard promotion process; B18 success does
  NOT auto-promote.
- **B18 failure** (future real B18 path): no split axis reports a
  sufficient per-cell denominator. The current retrieval stack
  continues; no retrieval variant is promoted.
- **B18 partial** (future real B18 path): some axes report a
  sufficient denominator, not all. Investigate axis-conditional
  candidate-quality policies; possibly expand the axis set in a
  separate B18B round (separate preregistration required).
- **B18 skeleton / no-go** (this commit): the bounded public-
  aggregate no-go screen confirms real B18 cannot be performed from
  public aggregates alone — the public artifacts lack per-record
  records, a time axis, commit chronology, per-repo-per-language
  cells, a model_family x repo matrix, adversarial holdout outcomes,
  and temporal holdout outcomes. Real B18 requires prospective per-
  record data collection with a real time axis and commit chronology.
