# B19 Theoretical Synthesis — Model-Robust Selective Evidence Conversion

Date: 2026-06-19

B19 is the **theoretical synthesis** of the B10-B18 Breakthrough Sprint. It
is **synthesis-only**: it does NOT run any provider, does NOT change
retrieval / default / EvidenceCore, and does NOT claim promotion. It
synthesizes B10 / B10B / B11 / B12 / B13 / B14 / B15 / B16 / B17 / B18
into a single paper-style algorithm report for the candidate algorithm
concept **Model-Robust Selective Evidence Conversion**.

> **Important claim boundary.** B19 is a synthesis, NOT a new
> experiment. `is_synthesis_only=true`, `is_new_experiment=false`,
> `ran_providers=false`, `new_provider_calls=0`,
> `changed_retrieval_default_evidencecore=false`. The synthesis carries
> forward ONLY already-published public-aggregate findings from B10-B18
> and introduces NO new empirical claims. All no-promotion flags are
> explicitly false: `promotion_ready=false`,
> `default_should_change=false`, `evidencecore_semantics_changed=false`,
> `runtime_clean_policy_supported=false`,
> `downstream_agent_value_proven=false`, `ood_temporal_supported=false`,
> `quiver_systems_supported=false`. No fake metrics are introduced; the
> only empirical numbers carried forward verbatim are the B11 official
> integrated matrix deltas (balanced_v1 vs p25), and the self-test
> asserts them byte-for-byte against the source aggregate artifact.

> **CRITICAL anti-fabrication boundary.** The synthesis MUST NOT
> introduce new metrics, new verdicts, or new claims beyond B10-B18. The
> B12 / B13 / B14 / B15 / B16 / B17 / B18 no-go / screen-only / prior-
> screen statuses are carried forward UNCHANGED. B11 `partial_with_failure`
> is carried forward UNCHANGED. B10 `runtime_clean=false` and B10B
> `runtime_shadow_ambiguous_supported=false` are carried forward
> UNCHANGED. The synthesis prose is a re-statement of the B10-B18
> evidence boundary, not new evidence.

> **Public artifact boundary.** The B19 public artifact
> (`artifacts/b19_theoretical_synthesis/b19_theoretical_synthesis_report.json`)
> is aggregate-only and forbids raw records / paths / spans / snippets /
> prompts / responses / gold labels / `content_sha` / provider keys /
> api keys. The self-test runs a B19-specific forbidden-key scan
> (forbidden keys + digest-like values, with the report's own drift-
> guard self-hash whitelisted) and asserts it is clean.

## Algorithm concept

**Model-Robust Selective Evidence Conversion** is a model-robust,
runtime-clean, evidence-gated policy that selectively converts high-
reach / high-false-cost local candidate pools into current-source
`EvidenceCore` spans by decoupling recall from admission, routing LLM
roles selectively, and optimizing worst-group utility across model
adapters.

### Inputs

- `query`
- `local_candidate_pool`
- `runtime_observable_uncertainty`
- `model_capability_profile`
- `latency_cost_budget`

### Outputs / actions

- `local_only`
- `weak_or_supporting`
- `llm_span_narrow`
- `llm_filter`
- `abstain`
- `request_more_context`
- `evidencecore_materialization`

Every selected action terminates in a current-source `EvidenceCore`
materialization (path + start_line + end_line + content_sha + score +
why + channels) or in an explicit abstain / request-more-context
signal. No action may emit a candidate, an LLM output, or a supporting
view as Evidence.

### Core principles

1. **Recall / admission decoupling** — reach comes from local
   candidates; admission is a separate decision.
2. **LLM role-selective routing** — `span_narrow` / `filter` fire only
   when a runtime predicate matches and budget permits; LLMs are never
   a global default pass.
3. **Algorithm / model-adapter separation** — `algorithm_spec` is
   model-independent (runtime features + abstract capability slots
   only); `model_adapter` (model identity + output mode + provider
   credentials) is an excluded adapter layer.
4. **Runtime-observable features only (for a runtime-clean policy)** —
   no benchmark-private labels (`task_bucket`, `task_risk_tags`), no
   score-private fields (`has_gold`, `score_group`, outcome metrics),
   no raw model names in `algorithm_spec`.
5. **Worst-group / cross-model robust optimization** — optimize
   `min_group(SpanF0.5 - λ*PFP - μ*normalized_cost - ν*normalized_latency)`,
   not the in-distribution average.
6. **Candidate must materialize into current-source EvidenceCore** — the
   current-source read is the final fact authority; stale / mismatched
   `content_sha` candidates are rejected.

## Problem statement

Local candidate pools (RRF, symbol/regex, dense) reach the gold
file/span often but carry high false-span and primary-false-positive
cost. A single global LLM pass is unsafe across mixed task buckets, and
a benchmark-routed policy cannot be promoted because it depends on
labels unavailable at runtime. The problem is to convert high-reach /
high-false-cost candidates into low-false-cost, citation-valid
`EvidenceCore` spans without weakening the evidence contract, without
making any one model's behavior the OpenLocus algorithm, and without
mistaking an in-distribution average for cross-model / OOD / temporal
generalization.

## Algorithm sketch (pseudocode)

```text
function CONVERT(query, local_candidate_pool, runtime_uncertainty,
                 model_profile, latency_cost_budget):
    # 1. RUN-phase routing uses ONLY runtime-observable features.
    feats = observe_runtime_features(local_candidate_pool, query)
    if not feats.all_present:
        return ACTION_REQUEST_MORE_CONTEXT
    # 2. Recall / admission decoupling: reach comes from local
    #    candidates; admission is a separate decision.
    recall_pool = local_candidate_pool
    # 3. Worst-group / cross-model robust action selection.
    action = robust_select(
        features=feats,
        uncertainty=runtime_uncertainty,
        model_profile=model_profile,
        budget=latency_cost_budget,
        objective=RobustUtility_worst_group,
        adapter=model_adapter,  # NOT part of algorithm_spec
    )
    # 4. LLM role is SELECTIVE: span_narrow / filter only when the
    #    runtime predicate fires and budget permits.
    if action in {LLM_SPAN_NARROW, LLM_FILTER}:
        llm_view = model_adapter.call(action, recall_pool, budget)
        llm_view.not_evidence = True
    # 5. Candidate must materialize into current-source EvidenceCore.
    evidence = materialize_current_source_evidencecore(action, recall_pool, llm_view)
    if evidence is None:
        return ACTION_ABSTAIN or ACTION_REQUEST_MORE_CONTEXT
    return evidence  # EvidenceCore: path, start_line, end_line,
                     # content_sha, score, why, channels
```

## Evidence boundary

Every selected action terminates in a current-source `EvidenceCore`
materialization (path + start_line + end_line + content_sha + score +
why + channels) or in an explicit abstain / request-more-context
signal. LLM outputs are `not_evidence=true` candidate/supporting
channels only; they can narrow, filter, or disambiguate, but they can
never become Evidence, never produce gold labels, never produce
citation verdicts, and never produce promotion verdicts. The current-
source read is the final fact authority; stale / mismatched
`content_sha` candidates are rejected.

## Policy-learning loop

The loop is:

1. Freeze an `algorithm_spec` that uses only runtime-observable
   features.
2. Run a preregistered prospective validation with no retuning (B11).
3. Decompose mechanism via per-record replay (B12, needs per-record
   data).
4. Search a worst-group / cross-model robust policy (B13, needs
   per-record group/action outcomes).
5. Calibrate a model-independent uncertainty score (B14, needs
   per-record (uncertainty, outcome) pairs).
6. Learn a frozen PackPolicy from per-record atom effects (B15, needs
   per-record atom flags).
7. Evaluate downstream agent value (B16, needs paired agent runs).
8. Evaluate OOD / temporal generalization (B18, needs per-record time
   axis).

Every loop iteration that lacks the required per-record inputs emits a
no-go / prior-screen / `insufficient_data` verdict and does NOT auto-
promote. Promotion is a separate, future, evidence-gated decision; it
is never the output of the loop itself.

## Adapter boundary

`algorithm_spec` is model-independent: it references only runtime-
observable `route_features` and abstract `model_profile` capability
slots (`cost_class`, `latency_class`, `supports_reliable_span_narrow`,
`family_slots`). `model_adapter` (model identity + output mode +
provider credentials / endpoints / secrets) is an EXCLUDED adapter
layer, not part of the algorithm spec. Output mode (`tool_call` /
`json_schema_strict`) is a model-adapter configuration parameter, not
an OpenLocus algorithm variable. A noisy adapter cannot become a
quality conclusion about the algorithm, and an algorithm-quality claim
cannot be smuggled in as an adapter leaderboard.

## Evaluation protocol

Prospective, preregistered, no-retuning validation. Success / partial /
failure criteria are frozen BEFORE any live runs on explicit overall
and worst-group thresholds (`Δgold_span`, `ΔSpanF0.5`, `ΔPFP`,
`Δfalse_spans`, `ΔLLM_calls`) plus a worst-group
`RobustUtility = min_group(SpanF0.5 - λ*PFP - μ*normalized_cost -
ν*normalized_latency)` with `λ=1.0`, `μ=0.1`, `ν=0.1`. Validation uses
rotating leave-one-model-family-out rotations and stratified fresh-
validation splits. Per-record replay is the evidence boundary for
mechanism (B12), DRO (B13), calibration (B14), pack policy (B15),
downstream agent value (B16), QuIVer systems (B17), and OOD / temporal
(B18). Public artifacts are aggregate-only; per-record records stay
under runner temp.

## Synthesized evidence (B10-B18)

- **B10** — `balanced_policy_v1_benchmark_routed` was benchmark-routed,
  not runtime-clean. The `_ambiguous_like` branch reads the benchmark
  public labels `task_bucket` / `task_risk_tags`, so a runtime-feature-
  only mode would never fire the `ambiguous_query_weak_only` rule.
  `runtime_clean=false`, `runtime_feature_only_mode_supported=false`.
  Claim level: `benchmark_routed_algorithm_spec_only`.
- **B10B** — Provided a mechanics-validated runtime-shadow scaffold +
  CI integration. Empirical support is pending because the label-driven
  ambiguous denominator stayed below the 10-record hard gate in all
  B11 runs (max observed `label_driven_ambiguous_denominator_qn0=3`).
  Verdict on the synthetic fixture: `mechanics_only_synthetic_fixture`;
  on CI records: `empirical_replay_support_pending`. Claim level:
  `ambiguous_branch_runtime_shadow_only`.
- **B11** — Official integrated matrix: 32/32 final cells, 384 records,
  aggregate verdict `partial_with_failure` (success 8 / partial 23 /
  failure 1). Balanced v1 vs P25 deltas: `Δgold_span -0.002604`,
  `ΔSpanF0.5 -0.001899`, `Δfalse_span -0.054688`, `ΔPFP -0.020833`,
  `Δmodel_calls -0.354167`. Strengthens the algorithm-candidate
  signal but is NOT promotion. Claim level:
  `derived_aggregate_of_b11_prospective_validation_reports`.
- **B12** — The public aggregate cannot identify mechanism. Full B12
  per-record replay is impossible from the public B11 aggregate: it
  lacks per-record route decisions, ambiguous-subset membership,
  deterministic call-reduction variant B, random call-reduction variant
  E, and `weak_candidate_only` per-strategy outcomes. Emits per-
  hypothesis screen statuses only, never a single global `supported`
  verdict. Claim level:
  `bounded_public_aggregate_mechanism_screen_of_b11_aggregate`.
- **B13** — The public aggregate cannot run real DRO search. Real B13
  requires per-record group / action outcomes and rotating leave-one-
  model-family-out rotations over per-record records. Verdict:
  `no_go_public_aggregate_only`. Claim level:
  `bounded_public_aggregate_feasibility_screen_of_b11_b12_aggregates`.
- **B14** — Cannot calibrate uncertainty from public aggregates. Real
  B14 requires per-record uncertainty scores, per-record binary
  outcomes, paired cross-model outputs, schema-repair per-call rows,
  and candidate score distributions. Verdict:
  `no_go_public_aggregate_only`. Claim level:
  `bounded_public_aggregate_feasibility_screen_of_b11_b12_b13_aggregates`.
- **B15** — Cannot learn a Context Pack Policy from public aggregates.
  Real B15 requires per-record pack atom flags, per-record outcomes,
  role-specific paired outputs, model_profile paired blocks, randomized
  atom assignment, balance stats, and token-budget-matched controls.
  The current value of B15 is preregistration / prior screen only (B2
  usable only as a `low_n_single_model_aggregate_directional_prior`).
  Verdict: `prior_screen_only`. Claim level:
  `bounded_public_aggregate_prior_screen_of_b2_b14_and_optional_aggregates`.
- **B16** — Downstream agent value is unproven. Real B16 requires paired
  live downstream agent runs, per-run patches/diffs, test execution
  results, solve labels, first-file-before-first-edit events, wrong-
  file-edit annotations, tool-call/token/latency/cost rows, isolated
  workspace proof, randomized arm order, and a task oracle/hidden-test
  manifest. Retrieval improvements are NOT downstream agent
  improvements. Verdict: `no_go_public_aggregate_only`. Claim level:
  `bounded_public_aggregate_feasibility_screen_of_b11_b12_b13_b14_b15_aggregates`.
- **B17** — QuIVer systems track is no-go because the QuIVer graph /
  vector backend is missing. The existing R33 / R34 / R36 / R24 and
  real-provider P3 / P4 diagnostics are diagnostic-only carry-forward:
  they do NOT implement a QuIVer / Vamana graph backend, do NOT contain
  an HNSW run, and do NOT contain a candidate-set equivalence matrix
  across backends. This is a systems-only future track. Verdict:
  `no_go_quiver_graph_missing`. Claim level:
  `bounded_public_systems_diagnostic_carry_forward_screen_of_r33_r34_r36_real_p3_p4_r24`.
- **B18** — OOD / temporal evaluation is no-go from the public
  aggregate. Real B18 requires per-record temporal / repo / language /
  model_family / adversarial axes with a real time axis and commit
  chronology. The public B11 aggregate carries only weighted means and
  a sanitized failure slice list; the R15 / R20 / R26 repo locks are
  synthetic static snapshots. Verdict: `no_go_public_aggregate_only`.
  Claim level:
  `bounded_public_aggregate_no_go_screen_of_b11_r15_r20_r26`.

## Current empirical evidence

The strongest current empirical signal is the B11 official integrated
matrix (32/32, 384 records): balanced_v1 vs p25 deltas preserve near-
parity SpanF0.5 / gold_span while reducing false_span, PFP, and
model_calls on average.

```text
aggregate_verdict: partial_with_failure
verdict_counts:    {success: 8, partial: 23, failure: 1}
b10b_runtime_shadow_status: empirical_replay_support_pending_due_denominator

deltas_balanced_v1_vs_p25:
  gold_span                    : -0.002604
  span_f0_5                    : -0.001899
  false_span                   : -0.054688
  primary_false_positive_rate  : -0.020833
  model_calls                  : -0.354167
```

The current empirical evidence strengthens the algorithm-candidate
signal but does NOT prove a runtime-clean general algorithm. The B10B
runtime-shadow predicate is empirical-pending (label-driven
denominator < 10 in all B11 runs). B11 is mixed / partial; one Kimi
`py_fastapi` slice exceeded the `failure_spanf05_delta` threshold.

## No-go gaps

- **B12** — public aggregate cannot identify mechanism. Missing:
  per-record route decisions, ambiguous-subset membership, variant B,
  variant E, `weak_candidate_only` per-strategy outcomes.
- **B13** — public aggregate cannot run real DRO search. Missing:
  per-record group/action outcomes, rotating leave-one-model-family-out
  rotations over per-record records.
- **B14** — cannot calibrate uncertainty from public aggregates.
  Missing: per-record uncertainty scores, per-record binary outcomes,
  paired cross-model outputs, schema-repair per-call rows, candidate
  score distributions.
- **B15** — cannot learn Context Pack Policy from public aggregates.
  Missing: per-record pack atom flags, per-record outcomes, role-
  specific paired outputs, model_profile paired blocks, randomized
  atom assignment, balance stats, token-budget-matched controls.
- **B16** — downstream agent value unproven. Missing: paired live
  agent runs, per-run patches/diffs, test execution results, solve
  labels, first-file-before-first-edit events, wrong-file-edit
  annotations, tool-call/token/latency/cost per run, isolated workspace
  proof, randomized arm order, task oracle/hidden-test manifest.
- **B17** — QuIVer systems track no-go: graph / vector backend
  missing. Missing: QuIVer/Vamana graph backend implementation, HNSW
  backend run, candidate-set equivalence matrix across backends, shared
  frozen candidate-quality manifest.
- **B18** — OOD / temporal no-go from public aggregate. Missing: per-
  record records, time axis, commit chronology, per-repo-per-language
  cells, model_family x repo matrix, adversarial holdout outcomes,
  temporal holdout outcomes.

## Promotion blockers

1. B10 `runtime_clean=false`: the frozen `balanced_policy_v1` is
   benchmark-routed, not runtime-clean.
2. B10B `runtime_shadow_ambiguous_supported=false` on all B11 runs
   (label-driven denominator < 10 hard gate).
3. B11 `aggregate_verdict=partial_with_failure` (one Kimi `py_fastapi`
   slice exceeded `failure_spanf05_delta`).
4. B12 / B13 / B14 / B15 / B16 / B17 / B18 are public-aggregate no-go
   or screen-only; none authorizes promotion.
5. No per-record mechanism, DRO, calibration, pack-policy, downstream-
   agent, QuIVer, or OOD/temporal evidence exists in any current public
   artifact.
6. Promotion is a separate future evidence-gated decision; the B10-B18
   sprint does NOT produce it.

## Next research program

1. Replace the benchmark-routed ambiguous branch with pure runtime
   features (`query_noise`, `candidate_support_exists`, anchor
   disagreement) and run B10B on real CI ephemeral records until the
   10-record hard gate passes.
2. Collect per-record route / action / group outcomes so B12 mechanism
   decomposition and B13 DRO search can run for real.
3. Collect per-record (uncertainty, binary outcome) pairs so B14 can
   calibrate a model-independent uncertainty score.
4. Collect per-record pack atom flags + role + runtime_state +
   model_profile so B15 can learn a frozen PackPolicy.
5. Stand up a fixed downstream agent harness with isolated fresh
   workspaces, randomized arm order, and patch/test outcome capture so
   B16 can prove (or refute) downstream value.
6. Implement a QuIVer / Vamana graph backend and a shared frozen
   candidate-quality manifest so B17 can run a real systems bakeoff.
7. Collect per-record temporal / repo / language / model_family /
   adversarial axes with a real time axis and commit chronology so B18
   can run a real OOD / temporal evaluation under the no-retuning
   protocol.
8. Only after the above, open a separate promotion preregistration;
   the synthesis itself never authorizes promotion.

## Bottom line

```text
promotion_ready                     : false
default_should_change               : false
evidencecore_semantics_changed      : false
runtime_clean_policy_supported      : false
downstream_agent_value_proven       : false
ood_temporal_supported              : false
quiver_systems_supported            : false
is_synthesis_only                   : true
is_new_experiment                   : false
ran_providers                       : false
new_provider_calls                  : 0
changed_retrieval_default_evidencecore : false
aggregate_only_public_artifact      : true
forbidden_public_scan_clean         : true
report_drift_guarded                : true
```

The B10-B18 Breakthrough Sprint strengthens the **Model-Robust
Selective Evidence Conversion** algorithm-candidate signal (B11 near-
parity SpanF0.5 / gold with reduced false-span, PFP, and model calls)
but does NOT prove a runtime-clean general algorithm, does NOT promote,
does NOT change defaults, and does NOT alter EvidenceCore semantics.
Every downstream stage (mechanism, DRO, calibration, pack policy,
downstream agent, QuIVer systems, OOD / temporal) is currently blocked
on missing per-record data. The synthesis is a research candidate, not a
promotion.

## Artifacts

- `artifacts/b19_theoretical_synthesis/b19_theoretical_synthesis_report.json`
  (aggregate-only machine-readable synthesis; schema
  `b19-theoretical-synthesis-report-v0`; claim level
  `theoretical_synthesis_of_b10_through_b18`; all no-promotion flags
  false; B11 deltas exact; forbidden public scan clean; report content
  hash drift-guarded; no raw records / paths / spans / snippets /
  prompts / responses / gold labels / content_sha / provider keys /
  api keys)
- `eval/b19_theoretical_synthesis.py` (pure Python; `--self-test`
  read-only verifies required sections, no-promotion flags, B11 deltas,
  forbidden scan, docs links, drift guard; `--regenerate-artifacts`
  rewrites the canonical report and re-runs the self-test; `--input`
  is a `not_implemented` stub because B19 is synthesis-only)

## What's autonomous vs. needs user action

### Autonomous (this commit)

- B19 synthesis document (this file + `docs/zh/b19-theoretical-synthesis.md`)
- B19 synthesis report JSON
  (`artifacts/b19_theoretical_synthesis/b19_theoretical_synthesis_report.json`)
- B19 evaluator (`eval/b19_theoretical_synthesis.py`) with read-only
  `--self-test` and explicit `--regenerate-artifacts` mutating path
- B19 entries in `docs/en/research-summary.md`,
  `docs/zh/research-summary.md`, `docs/en/current-research-conclusions.md`,
  `docs/zh/current-research-conclusions.md`, `docs/en/research-log.md`,
  `docs/zh/research-log.md`

### Needs prospective per-record data collection (NOT this commit)

- B10B runtime-shadow empirical support (run on real CI ephemeral
  records until the 10-record hard gate passes)
- B12 mechanism decomposition per-record replay
- B13 DRO search over per-record group/action outcomes
- B14 uncertainty calibration over per-record (uncertainty, outcome)
  pairs
- B15 PackPolicy learning over per-record atom flags
- B16 downstream agent evaluation over paired live agent runs
- B17 QuIVer systems bakeoff after a graph backend exists
- B18 OOD / temporal evaluation over per-record temporal axes

### Needs user review

- Results interpretation
- Decision to open a separate promotion preregistration (the synthesis
  itself never authorizes promotion)

See [`current-research-conclusions.md`](current-research-conclusions.md)
for the B10-B19 bottom line.
