# B15 Context Pack Policy

Date: 2026-06-18

B15 is the **context pack policy** phase. The goal is a **frozen,
preregistered PackPolicy** that maps `(role, runtime_state, model_profile)`
to a deterministic **atom set** (the pack-layout atoms a context pack
should expose for a given decision role under a given runtime state and
abstract model profile), validated against per-record pack-atom flags +
per-record outcomes + role + runtime_state + model_profile + group
membership from B11/B13 live runs.

B15 is a **bounded planning / feasibility phase**, NOT an empirical
atom-level ablation. The shipped skeleton performs NO empirical atom
ablation and NO PackPolicy learning. The frozen preregistration
(`eval/b15_context_pack_policy.py`) defines the PackPolicy contract,
the atom registry, the role set, the runtime_state contract, the
model_profile abstraction, the metric registry, the hard gates, and the
experimental structure (no-LLM feasibility → fractional factorial live
atom screen → freeze candidate policy → fresh validation); the bounded
public-aggregate prior / no-go screen
(`eval/b15_public_aggregate_prior_screen.py`) reads already-published
public aggregates (including the B2 contrastive-pack experiment as a
weak directional prior) and emits a `no_go_public_aggregate_only` or
`prior_screen_only` verdict.

> **Important claim boundary.** B15 IS the context-pack-policy *stage*
> (`stage_is_context_pack_policy=true`), but the shipped skeleton performs
> NO empirical atom ablation (`atom_ablation_performed=false`) and NO
> PackPolicy learning (`pack_policy_learned=false`). The synthetic-fixture
> / `--input` stub report sets `per_record_inputs_available=false`,
> `promotion_ready=false`, `default_should_change=false`,
> `evidencecore_semantics_changed=false`, `policy_search_performed=false`,
> `quality_strategy_tuned=false`, `new_provider_calls=0` so the public
> artifact cannot be mistaken for an empirical B15 PackPolicy result.
> This commit is strictly a skeleton / no-go commit: the current flags
> (`pack_policy_learned=false`, `atom_ablation_performed=false`,
> `promotion_ready=false`, `default_should_change=false`,
> `evidencecore_semantics_changed=false`) remain false. Any future real
> B15 empirical path would require its own separate preregistration;
> the exact flag schema for that future path (including any
> `pack_policy_learned` / `atom_ablation_performed` settings) is future
> work and is NOT present in this skeleton. B15 results in this commit
> are research candidates only: they inform future context-pack routing,
> but this skeleton/no-go commit authorizes no default change, no
> policy promotion, no PackPolicy promotion, and no EvidenceCore
> modification.

> **Important public-aggregate boundary.** Real B15 PackPolicy
> preregistration + validation requires private / ephemeral per-record
> inputs: per-record pack atom flags (which atoms were present in the
> pack sent to the model), per-record outcomes (was the selected span /
> candidate correct), role-specific paired outputs (the same record
> answered under different roles), runtime_state per record (candidate
> pool shape, score distribution, schema-repair state), model_profile
> paired blocks (the same record answered under different abstract
> capability profiles), group membership for worst-group splits, and
> randomized atom assignment + balance stats. None of those are present
> in any current public artifact. The bounded public-aggregate prior /
> no-go screen at `eval/b15_public_aggregate_prior_screen.py` reads the
> published B2 pack experiment, the B14 public-aggregate feasibility
> report, and (when present) the B4-B9 / P21-G / P49 public aggregates,
> and emits a `no_go_public_aggregate_only` (or `prior_screen_only`
> when at least the B2 directional prior is available) report under
> `artifacts/b15_context_pack_policy/`. The screen never claims
> empirical PackPolicy learning, never computes an atom-effect metric
> from aggregate means, never declares a winner.

> **CRITICAL anti-fabrication boundary.** The skeleton MUST NOT compute
> fake atom-effect metrics from aggregate means. Aggregate means (e.g.
> the B2 pack-layout aggregate SpanF0.5 / PFP) do not contain per-record
> (atom_flag, outcome) pairs, so any atom-level causal effect computed
> from them would be a fabrication. The B2 pack experiment is usable
> ONLY as a `low_n_single_model_aggregate_directional_prior` (a weak
> directional hint that contrastive structure is not automatically
> better), NOT as atom-level causality, role-specific PackPolicy, or a
> calibrated policy proof. The synthetic fixture validates only that
> the atom registry, role set, runtime_state contract, model_profile
> abstraction, metric names, and hard gates are wired correctly; it
> does not present synthetic atom-effect values as empirical B15
> results. The report surfaces `atom_ablation_performed=false`,
> `pack_policy_learned=false`, and
> `no_fake_atom_effects_from_aggregate_means=true` so a reader cannot
> mistake the skeleton for an empirical B15 PackPolicy result.

## Preregistration declaration

The following artifacts, PackPolicy contract, atom registry, role set,
runtime_state contract, model_profile abstraction, metric registry,
hard gates, experimental structure, and predeclared success/partial/
failure criteria are **FROZEN** before any B15 empirical runs. No
retuning of the atom registry, the role set, the runtime_state
contract, the model_profile abstraction, the metric registry, the hard
gates, or the success criteria is allowed after B15 empirical runs
begin. Any post-hoc analysis must be labeled exploratory and require a
separate validation round.

### Frozen artifacts

- `balanced_policy_v1_benchmark_routed` (B10 frozen spec) — referenced,
  not modified
- `balanced_policy_v1_runtime_shadow_ambiguous_branch` (B10B shadow
  predicate) — referenced, not modified
- B11/B12/B13/B14 frozen criteria — referenced, not modified
- B15 algorithm spec itself
  (`artifacts/b15_context_pack_policy/b15_context_pack_policy.algorithm.json`)
  — frozen before any PackPolicy runs; stable sha256
- Existing pack layouts referenced (definitions only, not modified):
  `topk_plain_v0`, `topk_scores_provenance_v0`,
  `contrastive_competitor_v0`, `hard_distractor_contrast_v0`
  (from `eval/p21_llm_rich_candidate.py` `PACK_LAYOUTS`), the P49
  contrastive candidate pack scaffold, and the P21-G atom/pack
  experiments

## Objective

Produce a **frozen, preregistered PackPolicy**

```text
PackPolicy(role, runtime_state, model_profile) -> atom set
```

that maps a decision role, a runtime state, and an abstract model
profile to the deterministic set of pack-layout atoms a context pack
should expose. The PackPolicy is NOT learned inside B15; it is frozen
from the preregistration + the bounded live atom screen, then
validated fresh. B15 does NOT learn an LLM, does NOT change EvidenceCore,
does NOT promote a default, and does NOT claim an atom-level causal
conclusion.

## Roles

The PackPolicy is indexed by the decision role the pack is being
assembled for. Roles are FROZEN:

- `span_narrow` — narrow a top-k candidate pool to the most relevant
  span(s)
- `filter_reject` — reject false-positive candidates that should not
  enter EvidenceCore
- `request_more_context` — decide whether the current pack is
  sufficient or more context (neighbor window, larger top-k, source
  materialization) should be requested
- `source_test_disambiguation` — disambiguate between same-anchor /
  same-path candidates by surfacing source-backed test / type / signature
  atoms

A PackPolicy row is `(role, runtime_state, model_profile) -> atom set`.
The same `(runtime_state, model_profile)` may map to different atom
sets across roles.

## Runtime state contract

`runtime_state` is a model-independent, label-free description of the
candidate pool and request state at the moment the pack is assembled.
It is computed from runtime-observable features only; **no**
benchmark-private labels, **no** score-private fields, **no** raw model
names. Allowed runtime_state features (FROZEN):

- `candidate_count`
- `candidate_support_exists`
- `score_distribution_spread`
- `top1_top2_score_gap`
- `anchor_disagreement`
- `rrf_backed_by_anchor`
- `dense_support_present`
- `path_kind_inferable`
- `neighbor_context_available`
- `signature_available`
- `hard_distractor_proxy_available`
- `same_file_competitor_present`
- `schema_repair_invoked`

> Note: `path_kind_inferable` is a runtime_state feature (a coarse
> inference over the candidate's path kind, label-free). The distinct
> `path_kind_flag` is a pack **atom** (a flag surfaced inside the
> pack). The two are deliberately separate; do not conflate them.

## Model profile abstraction

`model_profile` is an **abstract capability profile**, NOT a raw model
name. The PackPolicy must use abstract capability slots
(`profile_slot_a`, `profile_slot_b`, `profile_slot_c`, `profile_slot_d`)
and capability descriptors only. B15 must NOT reference raw model names
like "Kimi", "Qwen", "DeepSeek", or "GLM" in `algorithm_spec`. The
abstract capability descriptors (FROZEN) are:

- `long_context_window`
- `structured_output_stable`
- `span_narrow_strict`
- `hard_distractor_sensitive`
- `score_provenance_sensitive`
- `neighbor_context_sensitive`

A `model_profile` is a subset of these descriptors attached to an
abstract slot; the PackPolicy may branch on capability descriptors but
must never branch on raw model identity.

## Atom registry

The atom registry is the FROZEN set of pack-layout atoms a PackPolicy
may include or exclude. Each atom is a pack-layout feature that can be
turned on or off independently (modulo the experimental-structure
constraints below). The atom registry (FROZEN):

- `signature` — symbol/signature metadata for the candidate
- `matched_lines` — explicit matched line ranges (numbers only; no raw
  snippet content)
- `raw_snippet` — bounded raw source snippet text
- `neighbor_context` — neighbor window lines around the candidate
- `scores` — retrieval score / channel weight values
- `provenance` — retrieval channel / source provenance metadata
- `hard_distractor` — hard-distractor proxy slot
- `same_file_competitor` — same-file competitor slot
- `path_kind_flag` — coarse path-kind flag (test / vendor / generated /
  source)

Atoms are toggled at the pack level; the PackPolicy output is a subset
of the atom registry. The atom registry is closed: a candidate PackPolicy
may not introduce atoms outside this registry without a separate
preregistration round.

## Forbidden labels / forbidden features

B15 must NOT use benchmark-private labels or score-private fields as
PackPolicy inputs (features). Per-record outcomes (was the selected
span correct) are the validation TARGET, not a feature; they are
required as evaluation targets but must NEVER enter the PackPolicy.

Forbidden PackPolicy features (FROZEN):

- `task_bucket`, `task_risk_tags` (benchmark-private labels)
- `has_gold`, `score_group`, `outcome_metrics` (score-private fields)
- `gold_spans`, `must_not_primary`, `expected_behavior`, `oracle_type`,
  `risk_tags` (label / oracle fields)
- raw model names (`kimi`, `qwen`, `deepseek`, `glm`) — the PackPolicy
  uses abstract `model_profile` slots only

**NO model names in `algorithm_spec`**: B15 must use abstract
`model_profile` slots (`profile_slot_a`/`profile_slot_b`/
`profile_slot_c`/`profile_slot_d`) and capability descriptors, not raw
model names. The B15 evaluator enforces this with the special invariant
`algorithm_spec_has_no_model_names=true`.

## Required per-record inputs

Real B15 PackPolicy validation requires ALL of the following per record.
If any is missing, real B15 cannot run and the skeleton emits
`insufficient_data` / `not_implemented`.

- `per_record_pack_atom_flags` (which atoms were present in the pack)
- `per_record_outcome_binary` (was the selected span / candidate
  correct; the validation TARGET)
- `role_specific_paired_outputs` (the same record answered under
  different roles)
- `runtime_state_per_record` (candidate pool shape, score distribution,
  schema-repair state)
- `model_profile_paired_blocks` (the same record answered under
  different abstract capability profiles)
- `group_membership_for_worst_group_split` (model_family × repo ×
  role, for stratified split and worst-group reporting)
- `randomized_atom_assignment` (randomized atom on/off assignment per
  record, for causal atom-effect estimation)
- `randomization_balance_stats` (covariate balance per atom arm)
- `denominator_by_atom_role_model` (denominator counts per atom × role
  × model_profile cell, to prevent small-denominator atom-effect
  claims)
- `token_budget_matched_controls` (token-budget-matched control packs,
  so atom effects are not confounded with pack size)

## Experimental structure (FROZEN)

Real B15 proceeds in four frozen stages. No stage may be skipped, and
no stage's output may feed back into an earlier stage:

1. **no_llm_feasibility** — verify the per-record inputs above are
   present, the atom registry is closed, the role set is closed, the
   runtime_state contract is label-free, the model_profile abstraction
   has no raw model names, and the denominator-by-atom/role/model cells
   are non-empty. No LLM calls. Emits a feasibility verdict only.
2. **fractional_factorial_live_atom_screen** — a fractional factorial
   design over the atom registry (no full 2^9 factorial; a frozen
   resolution-IV fraction) run on ephemeral per-record inputs with
   randomized atom assignment. Estimates atom-level effects ONLY with
   per-record (atom_flag, outcome) pairs and balance stats. No
   PackPolicy is learned at this stage; only atom effects are screened.
3. **freeze_candidate_policy** — a candidate PackPolicy is frozen from
   the atom screen + the preregistered rules. The freeze is one-shot:
   no retuning after this point. `pack_policy_learned=false` is still
   surfaced because the candidate is a frozen research candidate, not a
   promoted policy.
4. **fresh_validation** — the frozen candidate PackPolicy is validated
   on a fresh per-record split (no overlap with the atom screen). The
   validation reports per-role, per-runtime_state, per-model_profile
   outcomes against the predeclared criteria. `success` / `partial` /
   `failure` are reserved for this stage and are NOT emitted by the
   skeleton.

## Metric registry (FROZEN)

The metric NAMES B15 will compute when real per-record inputs are
available. The skeleton defines them and validates the hard gates, but
does NOT compute fake metric values from aggregate means.

- `atom_effect_per_atom` (per-atom causal effect on outcome, from
  randomized atom assignment)
- `role_pack_outcome` (per-role PackPolicy outcome)
- `runtime_state_pack_outcome` (per-runtime_state PackPolicy outcome)
- `model_profile_pack_outcome` (per-model_profile PackPolicy outcome)
- `worst_group_pack_outcome` (worst-group PackPolicy outcome over
  `{model_family, repo, role, language}` groups)
- `cvar_20_pack_outcome` (CVaR_20% tail average of pack outcome)
- `token_budget_parity` (token-budget-matched control parity)
- `denominator_per_atom_role_model` (denominator counts per cell)
- `randomization_balance_per_arm` (covariate balance per atom arm)

Every metric requires per-record (atom_flag, outcome, role,
runtime_state, model_profile) tuples; none can be computed from
aggregate means.

## Hard gates (FROZEN)

The following hard gates are FROZEN before any B15 empirical runs. A
candidate PackPolicy that fails any gate is rejected, regardless of
its aggregate outcome.

- **privacy_gate**: `aggregate_only_public_artifact=true`; no raw
  records, task IDs, candidate IDs, paths, spans, snippets, prompts,
  responses, gold spans, private labels, provider keys, base URLs,
  API keys/secrets/tokens, content SHAs, digests, or line ranges in
  any public artifact; `new_provider_calls=0` in the skeleton.
- **leakage_gate**: no benchmark-private label, no score-private
  field, no raw model name enters the PackPolicy
  (`forbidden_signal_features` enforced); `algorithm_spec_has_no_model_names=true`.
- **adapter_health_gate**: no `model_adapter`, `output_mode`,
  provider credentials, provider endpoints, provider secrets, or raw
  model names in `algorithm_spec` (`excluded_adapter_layer` enforced).
- **randomization_balance_gate**: per-arm covariate balance must be
  within the frozen threshold; randomized atom assignment must cover
  every (atom, role, model_profile) cell. The skeleton does not
  evaluate this gate (no real per-record inputs); it only defines it.
- **denominator_gate**: every (atom, role, model_profile) cell must
  have a denominator ≥ the frozen minimum; no small-denominator
  atom-effect claim may be promoted. The skeleton does not evaluate
  this gate (no real per-record inputs); it only defines it.
- **token_budget_gate**: atom effects must be reported against
  token-budget-matched controls; no atom may be claimed effective
  solely because it enlarged the pack. The skeleton does not evaluate
  this gate (no real per-record inputs); it only defines it.
- **promotion_false_gate**: `promotion_ready=false`,
  `default_should_change=false`,
  `evidencecore_semantics_changed=false`, `pack_policy_learned=false`,
  `atom_ablation_performed=false`, `policy_search_performed=false`,
  `quality_strategy_tuned=false` are always present, so a skeleton /
  stub / no-go report cannot be misread as a promoted PackPolicy.

## Split protocol (FROZEN)

Real B15 splits per-record inputs into an **atom-screen split** and a
**fresh-validation split**, stratified by (model_family, repo, role).
The split protocol is `stratified_by_model_family_repo_role` with
`atom_screen_fraction=0.50` and `fresh_validation_fraction=0.50`. The
fresh-validation split is held out and reported once
(`fresh_validation_split_reported_once=true`). No metric on the
fresh-validation split may feed back into the atom screen or the
candidate-policy freeze.

## Worst-group reporting

B15 reports worst-group metrics over `{model_family, repo, role,
language}` groups, plus a `CVaR_20%` tail average (worst 20% of group
metrics). The CVaR tail fraction is `cvar_alpha=0.20` (frozen).

## Privacy / publication gates

Public artifacts must be aggregate-only. The B15 evaluator enforces:

- **no** raw records, task IDs, repo IDs, candidate IDs, paths, spans,
  snippets, prompts, responses, gold spans, private labels, provider
  keys, base URLs, API keys/secrets/tokens, content SHAs, digests, or
  line ranges in any public artifact;
- **no** raw filesystem path strings, 64-char hex digests, http(s)
  URLs, or credential assignments as values;
- **no** raw model names in `algorithm_spec` (`model_profile` slots
  only);
- `aggregate_only_public_artifact=true`;
- `new_provider_calls=0` (skeleton; no live LLM calls);
- `forbidden_public_key_scan_clean=true`.

## Predeclared success / partial / failure criteria

The criteria below are FROZEN before any B15 empirical runs
(`PREDECLARED_CRITERIA`):

| Outcome | Criterion |
| --- | --- |
| **Success** | The frozen candidate PackPolicy improves per-role pack outcome on the fresh-validation split by ≥ `0.02` over the reference (best single pack layout) on EVERY role, with worst-group pack outcome ≤ `0.15` worse than the per-role mean, AND every atom effect estimated in the screen is within the frozen denominator and randomization-balance gates, AND token-budget parity holds for every atom claimed effective. |
| **Partial** | Some roles improve but not all; or worst-group pack outcome regresses on one role; or one atom effect is within the denominator/balance gates but another is not. |
| **Failure** | No role improves on the fresh-validation split, OR any atom effect is estimated outside the denominator / randomization-balance / token-budget gates, OR the privacy / leakage / adapter-health gates fail. |

Frozen numeric gates:

- `strictly_greater_threshold = 0.02`
- `approx_equal_threshold = 0.02`
- `worst_group_pack_outcome_regression_threshold = 0.15`
- `cvar_alpha = 0.20`
- `atom_screen_fraction = 0.50`
- `fresh_validation_fraction = 0.50`
- `min_denominator_per_atom_role_model_cell = 30`
- `randomization_balance_max_imbalance = 0.05`
- `token_budget_match_tolerance = 0.10`

The B15 verdict framework emits one of:

- `success` (all roles improve, all gates pass on the fresh-validation
  split)
- `failure` (no improvement, or any hard gate fails)
- `partial` (some roles improve, not all; or one gate is borderline)
- `insufficient_data` (synthetic fixture, or too few records)
- `not_implemented` (`--input` stub, real PackPolicy validation
  deferred)

The skeleton only emits `insufficient_data` (synthetic fixture) or
`not_implemented` (ci_ephemeral_records stub); `success` / `failure` /
`partial` are NOT emitted by this skeleton. Any future real B15
empirical path that might emit them would require its own separate
preregistration, and its exact flag schema (including any
`pack_policy_learned` / `atom_ablation_performed` settings) is future
work and is NOT present in this skeleton. This commit keeps
`pack_policy_learned=false` and `atom_ablation_performed=false`
strictly.

## B2 prior usage boundary

The published B2 contrastive-pack experiment
(`docs/en/b2-contrastive-pack-quality-experiment.md`) is a **single-
model, low-N (24 tasks per layout), aggregate-only** pack-layout
comparison on four repos. B2's main conclusion — that contrastive
structure is **not automatically better** and that the best pack
depends on which error matters — is usable ONLY as a
`low_n_single_model_aggregate_directional_prior`: a weak directional
hint that PackPolicy should be role- and runtime_state-conditioned
rather than a single global pack layout.

B2 is NOT:

- atom-level causality (B2 reports pack-layout aggregates, not
  per-atom effects)
- a role-specific PackPolicy proof (B2 did not vary role)
- a calibrated policy (B2 did not calibrate anything)
- cross-model robustness (B2 used one model profile)
- a hard-distractor general rule (B2's hard-distractor result is
  single-model, low-N)
- a scores/provenance general win (B2's scores/provenance result was
  mixed and higher-latency)
- a default change or promotion (B2 explicitly did not promote)
- an EvidenceCore change (B2 explicitly did not change EvidenceCore)

The B15 public-aggregate prior screen carries B2 forward ONLY as
`b2_prior_usable=true` +
`b2_prior_claim_level=low_n_single_model_aggregate_directional_prior`.
Real B15 PackPolicy validation requires the per-record inputs listed
above; B2 alone is insufficient.

## Safety invariants

```text
promotion_ready=false
default_should_change=false
evidencecore_semantics_changed=false
stage_is_context_pack_policy=true (B15 stage IS context pack policy)
pack_policy_learned=false (skeleton performs no PackPolicy learning)
atom_ablation_performed=false (skeleton performs no empirical atom ablation)
per_record_inputs_available=false (skeleton; no real per-record inputs)
policy_search_performed=false
quality_strategy_tuned=false
new_provider_calls=0 (skeleton; no live LLM calls)
no_fake_atom_effects_from_aggregate_means=true
aggregate_only_public_artifact=true
algorithm_spec_has_no_model_names=true (B15 special invariant)
```

## What B15 does NOT prove

- B15 does **not** learn a PackPolicy.
- B15 does **not** perform empirical atom ablation.
- B15 does **not** estimate atom-level causal effects from aggregate
  means.
- B15 does **not** promote any PackPolicy.
- B15 does **not** change any defaults.
- B15 does **not** change `EvidenceCore` semantics.
- B15 does **not** authorize B16 without separate user review.
- B15 results are research candidates only; a B15-frozen candidate
  PackPolicy is NOT a promoted policy and is NOT the new default until
  separately promoted via the standard promotion process.
- B15's `--input` path is a stub (`verdict="not_implemented"`); full
  PackPolicy validation is deferred to a later task.
- B15 does **not** compute atom-effect / role-pack-outcome / worst-
  group-pack-outcome metrics from aggregate means.
- B2 is **not** atom-level causality, role-specific PackPolicy,
  calibrated policy, cross-model robustness, a hard-distractor general
  rule, a scores/provenance general win, a default change, a
  promotion, or an EvidenceCore change.

## Self-test (read-only) and explicit artifact regeneration

```bash
python3 eval/b15_context_pack_policy.py --self-test
python3 eval/b15_context_pack_policy.py --regenerate-artifacts
python3 eval/b15_context_pack_policy.py --self-test
python3 eval/b15_public_aggregate_prior_screen.py --self-test
python3 eval/b15_public_aggregate_prior_screen.py \
    --out artifacts/b15_context_pack_policy/b15_public_aggregate_prior_screen_report.json
```

The `eval/b15_context_pack_policy.py --self-test` run is **read-only**:
it verifies the PackPolicy contract, atom registry, role set,
runtime_state contract, model_profile abstraction, metric registry,
hard gates, and experimental structure against a synthetic fixture
(definitions-only; no per-record (atom_flag, outcome) pairs, no
computed atom-effect values) and compares the in-memory expected
algorithm spec + report to the on-disk artifacts, **failing on drift**.
It does NOT mutate checked-in artifacts. It emits
`stage_is_context_pack_policy=true`,
`pack_policy_learned=false`, `atom_ablation_performed=false`,
`per_record_inputs_available=false`, `promotion_ready=false`,
`default_should_change=false`, `evidencecore_semantics_changed=false`,
`policy_search_performed=false`, `quality_strategy_tuned=false`,
`new_provider_calls=0`,
`no_fake_atom_effects_from_aggregate_means=true`, so the synthetic-
fixture report is unambiguously NOT an empirical B15 PackPolicy result.

The read-only self-test runs these checks:

1. `forbidden_scan` — forbidden public keys/values scan (incl. raw
   model-name scan on the algorithm spec)
2. `spec_hash_stable` — algorithm spec sha256 stability
3. `atom_registry_closed` — atom registry is closed and disjoint from
   forbidden features
4. `role_set_closed` — 4 roles, closed set
5. `runtime_state_contract` — runtime_state features are label-free
   and model-name-free
6. `model_profile_abstraction` — abstract capability slots only, no
   raw model names in spec
7. `metric_registry` — 9 metric names defined; no aggregate-mean
   metrics
8. `hard_gates_defined` — privacy / leakage / adapter-health /
   randomization-balance / denominator / token-budget / promotion-false
   gates defined
9. `experimental_structure_frozen` — 4 frozen stages; no feedback
10. `no_fake_atom_effects_from_aggregate_means` — synthetic fixture
    has no per-record pairs and no atom-effect values
11. `input_stub_not_implemented` — `--input` stub returns
    `not_implemented`
12. `reference_specs_pinned` — B10/B10B/B11/B12/B13/B14 reference
    specs present on disk
13. `artifacts_match_in_memory` — read-only drift check: in-memory
    expected spec + report match the on-disk artifacts

`python3 eval/b15_context_pack_policy.py --regenerate-artifacts` is
the ONLY path that mutates checked-in artifacts: it (re)writes the
on-disk algorithm spec + synthetic-fixture report from the current
build functions. After mutating, re-run `--self-test` to confirm the
on-disk artifacts now match the in-memory expected objects (no drift).

The `--input` path is a non-canonical stub path: it requires an
explicit `--out` destination and refuses to write the checked-in
`b15_context_pack_policy_report.json`. It can write a temporary stub
report for development, but it does not mutate checked-in B15
artifacts.

The `eval/b15_public_aggregate_prior_screen.py --self-test` run
verifies the bounded public-aggregate prior / no-go screen against a
synthetic minimal B2 + B14 + optional B4-B9 / P21-G / P49 fixture. It
emits `verdict=no_go_public_aggregate_only` or
`prior_screen_only`, with `pack_policy_learned=false`,
`atom_ablation_performed=false`, `per_record_inputs_available=false`,
`atom_level_inference_possible=false`,
`role_specific_policy_possible=false`, `calibration_possible=false`,
`new_live_runs_required=true`, `b2_prior_usable=true`,
`b2_prior_claim_level=low_n_single_model_aggregate_directional_prior`.

## Artifacts

- `artifacts/b15_context_pack_policy/b15_context_pack_policy.algorithm.json`
  (frozen spec; deterministic, stable sha256; regenerated only via
  `--regenerate-artifacts`)
- `artifacts/b15_context_pack_policy/b15_context_pack_policy_report.json`
  (synthetic-fixture self-test report, verdict `insufficient_data`;
  `pack_policy_learned=false`, `atom_ablation_performed=false`,
  `per_record_inputs_available=false`,
  `stage_is_context_pack_policy=true`,
  `no_fake_atom_effects_from_aggregate_means=true`;
  no empirical per-atom metric values)
- `artifacts/b15_context_pack_policy/b15_public_aggregate_prior_screen_report.json`
  (bounded public-aggregate prior / no-go screen report;
  `verdict=no_go_public_aggregate_only` or `prior_screen_only`;
  `b2_prior_usable=true`,
  `b2_prior_claim_level=low_n_single_model_aggregate_directional_prior`,
  `atom_level_inference_possible=false`,
  `role_specific_policy_possible=false`,
  `calibration_possible=false`, `new_live_runs_required=true`)

## What's autonomous vs. needs user action

### Autonomous (can be done now)

- B15 plan document (this file)
- B15 evaluator skeleton (`eval/b15_context_pack_policy.py`) +
  read-only `--self-test` (compares in-memory expected artifacts to
  on-disk artifacts, fails on drift) and explicit `--regenerate-artifacts`
  mutating path
- B15 frozen algorithm spec + synthetic-fixture report artifacts
- B15 bounded public-aggregate prior / no-go screen
  (`eval/b15_public_aggregate_prior_screen.py`) + self-test +
  `artifacts/b15_context_pack_policy/b15_public_aggregate_prior_screen_report.json`
  (reads the published B2 + B14 artifacts and, when present, the
  B4-B9 / P21-G / P49 public aggregates; emits
  `no_go_public_aggregate_only` / `prior_screen_only`; never claims
  empirical PackPolicy learning, never computes an atom-effect metric,
  never declares a winner)

### Needs per-record ephemeral inputs

- B15 real PackPolicy validation requires per-record pack atom flags,
  per-record outcomes, role-specific paired outputs, runtime_state
  per record, model_profile paired blocks, group membership,
  randomized atom assignment, randomization balance stats,
  denominator-by-atom/role/model cells, and token-budget-matched
  controls from B11/B13 live runs. If those records are not yet
  produced, B15 emits `insufficient_data` / `not_implemented`.

### Needs user review

- Results interpretation
- Decision to proceed to B16 (downstream agent evaluation) using a
  B15-frozen candidate PackPolicy as a research candidate
- Decision to expand from the minimum viable atom registry to a
  larger atom set (separate preregistration required)

## Next steps after B15

- **B15 success**: a frozen candidate PackPolicy improves per-role
  pack outcome on the fresh-validation split, all hard gates pass.
  Proceed to B16 to test it downstream as a context-pack routing
  candidate.
- **B15 failure**: no candidate PackPolicy meets the predeclared
  criteria. The default pack layout (`topk_plain_v0`) continues; B16
  should use the existing pack layout.
- **B15 partial**: some roles improve, not all. Investigate role-
  conditional PackPolicy; possibly expand the atom registry in a
  separate B15B round (separate preregistration required).
