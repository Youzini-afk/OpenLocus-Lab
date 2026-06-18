# B12 Mechanism Decomposition

Date: 2026-06-18

B12 is the **mechanism decomposition** phase that follows B11 (prospective
blind validation). The goal is to understand **WHY** the frozen balanced policy
`balanced_policy_v1_benchmark_routed` (B10) works (if B11 confirms it
generalizes), via five ablation variants (A-E) and four predeclared hypotheses
(H1-H4).

> **Important claim boundary.** B12 is mechanism decomposition, not a
> promotion step. Even if B12 supports one or more hypotheses,
> `promotion_ready=false`, `default_should_change=false`, and `EvidenceCore`
> semantics are unchanged. B12's outcome only decides which mechanism
> (ambiguous routing, LLM-call reduction, P25 fallback sufficiency, or
> model-specific behaviour) drives the balanced policy's gains, which informs
> B13 (distributionally robust policy search).

## Preregistration declaration

The following artifacts, ablation variant definitions, and hypothesis
support/refute criteria are **FROZEN** before any B12 ablation runs. No
retuning is allowed after B12 ablation runs begin. Any post-hoc analysis must
be labeled exploratory and require a separate validation round.

### Frozen artifacts

- `balanced_policy_v1_benchmark_routed` (B10 frozen spec; sha256 in
  `artifacts/b10_runtime_feature_audit/balanced_policy_v1_benchmark_routed.algorithm.json`)
- `balanced_policy_v1_runtime_shadow_ambiguous_branch` (B10B shadow predicate;
  sha256 `c201eb709dc0112c2bb91db33917c6d20ea48582924821a2bda7950709e754ba`)
- `rmc_local_conservative_v0` (Conservative policy; frozen in
  `eval/b6_lite_interpretable_policy_search.py`)
- `p25.route_bucket_routed_v0` (P25 policy; frozen in `eval/p25_bucket_policy.py`)
- B10B 10 predeclared acceptance gates (including
  `label_driven_ambiguous_min_denominator: 10` hard gate)
- B10B verdict framework (`runtime_shadow_ambiguous_supported` +
  `support_claim` + `support_claim_reason`)
- All ablation variant definitions (A-E) and hypothesis criteria (H1-H4) in
  this document

## Objective

Decompose the mechanism behind the balanced policy's gains into one (or more)
of four candidate explanations:

> Do the balanced policy's gains come from (H1) the `ambiguous→weak_only`
> routing rule specifically, (H2) a generic reduction in LLM calls, (H3) the
> P25 default action being sufficient on its own, or (H4) model-family-specific
> behaviour?

## Scope

B12 can be done as a **replay** if P21 records are available (each record
contains per-strategy outcomes, so each ablation variant can be computed by
selecting the appropriate per-strategy outcome from existing records). If P21
records are not available, B12 needs new live ablation runs (workflow_dispatch
+ `enable_remote_models=true`).

### Minimum viable B12

- Same 8 repos, 4 model families, 4 policies as B11 (so B12 can replay against
  B11 live run records directly).
- 5 ablation variants (A-E) computed per record.
- Estimated runtime: minutes (replay) or 4-6 hours CI per model family (live
  ablation runs).

## Ablation variants

The balanced policy `balanced_policy_v1_benchmark_routed` has only one routing
rule: `ambiguous→weak_only, else P25`. The 5 ablation variants below decompose
that rule into the components that could plausibly drive its gains.

| Variant | Definition | Tests |
| --- | --- | --- |
| **A** (full balanced) | `ambiguous→weak_only, else P25` — the full balanced policy | Reference (the policy under analysis) |
| **B** (deterministic LLM reduction) | `P25 for all, but skip LLM for ambiguous tasks` (use `candidate_baseline` instead) | Whether `weak_only` or just skipping LLM is what helps |
| **C** (ambiguous weak_only only) | Same as A (the balanced policy only has the ambiguous→weak_only rule) | Redundancy check; A≡C, merged in analysis |
| **D** (P25 default only) | `P25 for all` (no ambiguous→weak_only rule) — baseline | Whether the routing rule matters at all |
| **E** (random LLM reduction) | `P25 for all, but randomly skip the same number of LLM calls as A` | H2 (is it just call reduction?) |

### A≡C equivalence

Variant A and Variant C are **identical by construction**: the balanced policy
`balanced_policy_v1_benchmark_routed` has only one routing rule
(`ambiguous→weak_only, else P25`), so "the full balanced policy" (A) and
"ambiguous weak_only only" (C) produce the same per-record outcome. This
redundancy is declared explicitly up-front (it is not a post-hoc discovery):
in the analysis, A≡C, and Variant C is collapsed into Variant A for every
hypothesis test. Variant C is kept in the variant list for traceability and
defensive auditing (the evaluator's A-vs-C delta check must always be zero on
every metric).

## Hypotheses

All deltas are `variant_a - comparator` on overall-mean metrics. "≈" means
within ±0.02 (absolute), and ">" means strictly greater by more than 0.02 (so
a delta of exactly +0.02 is treated as "≈", not ">"). Primary quality metrics
are `gold_span` and `span_f0_5`.

### H1 (ambiguous routing)

> The balanced policy's gains come from the `ambiguous→weak_only` routing rule
> specifically, not from a generic LLM-call reduction and not from the P25
> default alone.

**Supported if** all three hold:

- `A > D` on `gold_span` AND `A > D` on `span_f0_5` (the routing rule beats the
  P25 default)
- `A > E` on `gold_span` AND `A > E` on `span_f0_5` (the routing rule beats
  random LLM-call reduction)
- `A > B` on `gold_span` AND `A > B` on `span_f0_5` (the routing rule beats
  deterministic LLM skipping)

**Refuted if** any one of the three fails.

### H2 (LLM call reduction)

> The balanced policy's gains come from reducing LLM calls — any reduction
> would help, not the specific `weak_only` route.

**Supported if** both hold:

- `A ≈ E` on `gold_span` AND `A ≈ E` on `span_f0_5` (random LLM-call reduction
  matches the routing rule)
- `A > D` on `gold_span` AND `A > D` on `span_f0_5` (reduction matters vs the
  P25 default)

**Refuted if** either fails.

### H3 (P25 fallback sufficiency)

> The `ambiguous→weak_only` routing rule doesn't help; the P25 default action
> alone is sufficient.

**Supported if** both hold:

- `D ≈ A` on `gold_span` (the P25 default alone matches the full balanced
  policy on gold)
- `D ≈ A` on `span_f0_5` (the P25 default alone matches the full balanced
  policy on SpanF0.5)

**Refuted if** either fails.

> Note: H3 is mutually exclusive with H1 (if the routing rule beats the P25
> default, H3 is refuted). H1 and H3 cannot both be supported simultaneously.

### H4 (model-specific)

> The balanced policy's effect sizes vary significantly across model families
> (e.g., `A > D` on Kimi but `A ≈ D` on DeepSeek).

**Supported if** the worst-case spread across model families on the `A - D`
`gold_span` delta exceeds 0.05.

**Refuted if** the spread is at most 0.05.

## Methodology

### Replay-based (preferred)

If P21 records are available (from B11 live runs or CI ephemeral records), B12
is a pure replay:

1. For each P21 record, the per-strategy outcome is already present
   (`candidate_baseline`, `llm_span_narrow`, `llm_filter`, etc.).
2. For each ablation variant (A-E), compute the per-record outcome by
   selecting the appropriate per-strategy outcome:
   - **A**: select `weak_only` outcome for ambiguous tasks, `p25` outcome
     otherwise.
   - **B**: select `candidate_baseline` outcome for ambiguous tasks, `p25`
     outcome otherwise.
   - **C**: identical to A.
   - **D**: select `p25` outcome for all tasks.
   - **E**: select `p25` outcome, but for a randomly-chosen subset of the same
     size as A's ambiguous-task subset, select `candidate_baseline` instead
     (deterministic seed).
3. Aggregate per-variant metrics (overall mean, worst-group, bootstrap CIs,
   RobustUtility).
4. Apply the predeclared hypothesis criteria.

### Live ablation runs (fallback)

If P21 records are not available, B12 needs new live runs. Run P21 with each
ablation variant as a different policy:

- 5 variants × 4 model families × 8 repos = 160 live runs (or batched).
- Each run produces P21 ephemeral records (which can then be replayed too).
- Requires `workflow_dispatch` + `enable_remote_models=true`.

The replay path is strongly preferred: it makes no new LLM calls, costs
nothing, and is fully deterministic.

## Metrics

Same as B11.

### Primary metrics

- `SpanF0.5`
- `MRR`
- Gold retention (`added_gold_span`)
- False spans (`added_false_span`)
- PFP (`primary_false_positive_rate`)
- LLM calls (`model_calls`)
- Cost (estimated provider cost)
- Latency (p50/p95)

### Aggregation

- Overall mean (across all tasks)
- **Worst-group** by:
  - Model family (Kimi/Qwen/DeepSeek Flash/DeepSeek Pro)
  - Repo (8 repos)
  - Language (Python/TypeScript/Go/Rust/Java)
  - Task bucket (positive/negative/ambiguous/hard-distractor)

### Statistical

- 95% bootstrap confidence intervals (10,000 resamples, stratified by repo)
- Leave-one-repo-out sensitivity
- Leave-one-model-family-out sensitivity
- Paired deltas (Variant A vs. each comparator)
- Holm-Bonferroni correction for multiple comparisons

### RobustUtility

```text
RobustUtility = min_group(
    SpanF0.5
    - λ * PFP
    - μ * normalized_cost
    - ν * normalized_latency
)
```

Predeclared parameters (mirrors B11):
- `λ = 1.0`
- `μ = 0.1`
- `ν = 0.1`

## Predeclared hypothesis support/refute criteria

All deltas are `variant_a - comparator` on overall-mean metrics (positive =
improvement). The thresholds below are FROZEN before any B12 ablation runs.

| Hypothesis | Support criterion | Refute criterion |
| --- | --- | --- |
| H1 (ambiguous routing) | `A > D` AND `A > E` AND `A > B` (gold/SpanF0.5, all by > 0.02) | Any one fails |
| H2 (LLM call reduction) | `A ≈ E` (gold/SpanF0.5 within ±0.02) AND `A > D` | Either fails |
| H3 (P25 fallback sufficiency) | `D ≈ A` (gold/SpanF0.5 within ±0.02) | Either fails |
| H4 (model-specific) | Worst-case model-family spread on `A - D` `gold_span` delta > 0.05 | Spread ≤ 0.05 |

The B12 verdict framework emits one of:
- `supported` (all 4 hypotheses supported)
- `refuted` (all 4 hypotheses refuted)
- `partial` (some supported, some refuted)
- `insufficient_data` (synthetic fixture, or too few records to evaluate)
- `not_implemented` (`--input` stub, real computation deferred)

## CI workflow design

### New stage: `b12_mechanism_decomposition`

Add a new stage `b12_mechanism_decomposition` to
`.github/workflows/real-provider-benchmark.yml`. The stage runs the B12 report
aggregator against P21 ephemeral records produced by B11 live runs (replay), or
against new live ablation runs (fallback).

### Workflow inputs

- `stage`: `b12_mechanism_decomposition`
- `replay_source`: `ci_ephemeral_records` (replay) or `live_ablation_runs`
  (fallback)
- `enable_remote_models`: `true` (only needed for live ablation runs)
- `model_family`: optional (for single-model-family runs)

### Run matrix

- Replay: 1 run (consumes B11 records).
- Live ablation: 5 variants × 4 model families × 8 repos = 160 runs (batched).

## B10B/B11 integration

- B12 replays against B11 live run records (`replay_source="ci_ephemeral_records"`).
- B12 does not re-run B10B (B10B is an ambiguous-branch shadow predicate, not
  an ablation variant).
- B12's frozen artifacts include the B10, B10B, B11, P25, and Conservative
  specs (the same set as B11, plus the B11 spec itself).
- B12's evaluator skeleton verifies that the B10/B10B/B11 reference specs are
  present on disk and pinned (`frozen_reference_specs_pinned_on_disk`).

## Safety invariants

```text
promotion_ready=false
default_should_change=false
evidencecore_semantics_changed=false
runtime_calls_by_replay=0 (replay makes no new live calls)
model_calls_by_replay=0 (replay makes no new LLM calls)
aggregate_only_public_artifact=true
policy_search_performed=false (no policy tuning during B12)
quality_strategy_tuned=false
replay_only_no_live_ablation_runs_in_evaluator=true
```

## Artifacts

- `artifacts/b12_mechanism_decomposition/b12_mechanism_decomposition.algorithm.json`
  (frozen spec; deterministic, stable sha256)
- `artifacts/b12_mechanism_decomposition/b12_mechanism_decomposition_report.json`
  (synthetic-fixture self-test report, verdict `insufficient_data`)

## Self-test

```bash
python3 eval/b12_mechanism_decomposition.py --self-test
```

Verifies the report aggregator mechanics without live runs (synthetic fixture
only; `replay_source="synthetic_fixture"`; verdict `insufficient_data`). The
self-test runs 10 checks:

1. `forbidden_scan` — forbidden public keys/values scan
2. `spec_hash_stable` — algorithm spec sha256 stability
3. `synthetic_fixture_metrics` — synthetic fixture (incl. A≡C equivalence)
4. `hypothesis_evaluation_stub` — hypothesis evaluation mechanics
5. `input_stub_not_implemented` — `--input` stub returns `not_implemented`
6. `reference_specs_pinned` — B10/B10B/B11 reference specs present on disk
7. `artifacts_regenerated` — on-disk artifacts regenerated from build functions
8. `on_disk_artifacts_validated` — on-disk spec + report verified
9. `ablation_variants_defined` — 5 ablation variants + A≡C equivalence
10. `hypotheses_defined` — 4 hypotheses + predeclared criteria

## What's autonomous vs. needs user action

### Autonomous (can be done now)

- B12 plan document (this file)
- B12 CI workflow definition (new stage `b12_mechanism_decomposition`)
- B12 report aggregator skeleton (`eval/b12_mechanism_decomposition.py`) +
  self-test
- B12 frozen algorithm spec + synthetic-fixture report artifacts

### Needs workflow_dispatch

- Live ablation runs (if P21 records unavailable; require
  `enable_remote_models=true` + `OPENLOCUS_ALLOW_REMOTE=1`)
- User triggers each model family live ablation run

### Needs user review

- Results interpretation
- Decision to proceed to B13 (distributionally robust policy search)
- Decision to expand from minimum viable to full B12

## What B12 does NOT prove

- B12 does **not** prove the balanced policy is ready for promotion.
- B12 does **not** change any defaults.
- B12 does **not** change `EvidenceCore` semantics.
- B12 does **not** authorize B13 without separate user review.
- B12 does **not** tune the balanced policy (no policy search; the policy is
  frozen from B10).
- B12's `--input` path is a stub (`verdict="not_implemented"`); full per-record
  replay computation is deferred to a later task.

## Next steps after B12

- **B12 supports H1**: the `ambiguous→weak_only` routing rule is the active
  mechanism. Proceed to B13 to optimize the routing rule with distributionally
  robust objectives.
- **B12 supports H2**: the gain is just LLM-call reduction. The balanced
  policy is over-engineered; a simpler random-skip policy would work. B13
  should search for the simplest sufficient policy.
- **B12 supports H3**: the routing rule doesn't help; the P25 default is
  sufficient. The balanced policy adds complexity without benefit. B13 should
  consider whether the routing rule should be dropped.
- **B12 supports H4**: the mechanism is model-family-specific. B13 should
  search for model-family-conditional policies.
- **B12 refutes all**: the balanced policy's gains are not explained by any of
  the four candidate mechanisms. B13 should explore alternative mechanisms
  (e.g., candidate-pool size effects, task-difficulty interactions).
