# B12 Mechanism Decomposition

Date: 2026-06-18 (updated 2026-06-19: C1 private-records adapter wired in)

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

## C1 private per-record records (2026-06-19)

B12 now consumes **private per-record P21 records** via the shared C1 adapter
(`eval/c1_private_records.py`) instead of the planning-only public-aggregate
screen. The adapter loads the frozen P21 v1 payload
(`schema_version == "p25-policy-records-ephemeral-v1"`), validates the
top-level privacy flags (`not_artifact_for_commit=true`; raw
query/snippet/prompt/response flags false; `gold_spans_stored=false`), and
normalizes each record into an in-memory view with an explicit **three-category
taint model**:

1. **runtime-clean `route_features`** — the only category a runtime-clean policy
   may read.
2. **benchmark route labels** (`task_bucket`, `task_risk_tags`) — used to analyze
   frozen benchmark-routed policies (B10/B11/B12 variants A/C/D) but NOT a
   runtime-clean policy input.
3. **score/outcome/private fields** (`score_group`, per-strategy outcomes,
   `p31_score_gold`, `p31_candidate_pools`, `p33b_anchor_subtypes`) — allowed
   only because the file is runner-temp/private and never uploaded; never a
   routing input.

The adapter does NOT reject `p31_score_gold_spans_stored=true`: P31 gold spans
are allowed only under private runner-temp input. It never writes public
artifacts; stable private per-record hashes are kept in-memory/internal only and
never appear in the public B12 report. B12 derives aggregate-only metrics from
the adapter and runs its own forbidden-key scan.

See `.slim/deepwork/c1-private-per-record-research-records.md` for the full C1
research record.

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
| **B** (deterministic call-reduction control) | `P25 for all, but for records in `actual_call_avoided_set` use `candidate_baseline` instead` | Whether `weak_only` routing or just skipping the LLM call on the same records is what helps |
| **C** (ambiguous weak_only only) | Same as A (the balanced policy only has the ambiguous→weak_only rule) | Redundancy check; A≡C, merged in analysis |
| **D** (P25 default only) | `P25 for all` (no ambiguous→weak_only rule) — baseline | Whether the routing rule matters at all |
| **E** (random same-count call-reduction control) | `P25 for all, but deterministically hash-select the same number of records as `actual_call_avoided_set` from the P25 LLM-eligible population and use `candidate_baseline` on those` | H2 (is it just call reduction, on an arbitrary same-count subset?) |

### Key set definitions (FROZEN)

- `balanced_branch_set` = records where the balanced v1
  `ambiguous_or_query_noise` predicate fires (benchmark route labels
  `ambiguous` / `hallucination_risk` / `weak_candidates`, OR
  `route_features.query_noise > 0`). NOTE: this predicate reads benchmark
  route labels (category-2 taint), which is exactly why balanced_v1 is
  benchmark-routed, NOT runtime-clean.
- `p25_llm_subset` = records where D/P25 (`route_bucket_routed_v0`) would
  choose one of `llm_span_narrow`, `llm_filter`, `llm_abstain_filter` (the
  LLM-costing strategies).
- `actual_call_avoided_set = balanced_branch_set ∩ p25_llm_subset` — the
  records where the balanced policy's routing actually avoids an LLM call
  that D/P25 would have made. This is the B variant's intervention set.
- E random subset: a deterministic, frozen-seed (`e_random_seed=20260618`)
  hash-selection of `len(actual_call_avoided_set)` records from
  `p25_llm_subset`. Limitation: a single frozen seed is used; seed-averaging
  can be added later.

All four sets are reported in the public report as **COUNTS only**
(`total_records`, `complete_records`, `balanced_branch_count`,
`p25_llm_eligible_count`, `actual_call_avoided_count`,
`random_selected_count`). No per-record hash, task_id, raw/private repo_id,
path, span, or P31/P33 block is emitted. Aggregate group metrics use only public
preregistered repo labels for synthetic/preregistration fixtures or anonymized
`public_repo_group_NNN` labels for private `--input` replays.

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
within ±0.02 (absolute), and a "strict reduction" on a lower-is-better metric
(false_span, PFP, model_calls) means `(A - comparator) < -0.02` (A is strictly
lower/better). A "strict improvement" on RobustUtility means
`(A - comparator) > 0.02`. Primary quality metrics are `gold_span` and
`span_f0_5`.

> **Revised (C1) criteria.** The H1-H3 support criteria were revised before any
> empirical replay to align with the actual expected balanced_v1 mechanism:
> the balanced policy is expected to **preserve** gold/span vs D approximately
> (NOT increase gold/span), **reduce** false spans / PFP / model calls vs D,
> and **outperform** B/E on false/PFP/RobustUtility enough to support targeted
> ambiguous routing. A is **not** required to increase gold/span.

### H1 (ambiguous routing)

> The balanced policy's gains come from the `ambiguous→weak_only` routing rule
> specifically — it preserves primary quality, reduces false/PFP/model calls vs
> D, and beats B (deterministic call-reduction) and E (random same-count
> call-reduction) on false/PFP/RobustUtility. This supports targeted ambiguous
> routing rather than generic call-count reduction.

**Supported if** all four hold:

- `A ≈ D` on `gold_span` AND `span_f0_5` (preserve primary quality — A is NOT
  required to increase gold/span)
- `A < D` on `false_span` AND `primary_false_positive_rate` AND `model_calls`
  (strict reductions, all by > 0.02)
- `A < B` on `false_span` AND `primary_false_positive_rate`, AND
  `RobustUtility(A) > RobustUtility(B)` (the routing rule beats deterministic
  call-reduction)
- `A < E` on `false_span` AND `primary_false_positive_rate`, AND
  `RobustUtility(A) > RobustUtility(E)` (the routing rule beats random
  same-count call-reduction)

**Refuted if** any one of the four fails.

### H2 (LLM call reduction)

> The balanced policy's gains come from reducing LLM calls — any reduction
> would help, not the specific `weak_only` route.

**Supported if** both hold:

- `A ≈ E` on `gold_span` AND `span_f0_5` AND `false_span` AND
  `primary_false_positive_rate` (random same-count call-reduction matches the
  routing rule on quality and false/PFP)
- `A < D` on `model_calls` (reduction matters vs the P25 default)

**Refuted if** either fails.

### H3 (P25 fallback sufficiency)

> The `ambiguous→weak_only` routing rule doesn't help on primary quality; the
> P25 default action alone is sufficient on gold/SpanF0.5.

**Supported if** both hold:

- `D ≈ A` on `gold_span` (the P25 default alone matches the full balanced
  policy on gold)
- `D ≈ A` on `span_f0_5` (the P25 default alone matches the full balanced
  policy on SpanF0.5)

**Refuted if** either fails.

> Note: H3 is mutually exclusive with H1 on the primary-quality component (if
> A preserves but D diverges, H3 is refuted). H1 and H3 cannot both be
> supported on the same primary-quality evidence.

### H4 (model-specific)

> The balanced policy's effect sizes vary significantly across model families
> (e.g., `A > D` on Kimi but `A ≈ D` on DeepSeek).

**Supported if** the worst-case spread across model families on the `A - D`
`gold_span` delta exceeds 0.05 AND there are at least two known model families.

**Refuted / insufficient_data if** the spread is at most 0.05, or fewer than
two known model families are present. H4 defaults to `insufficient_data`
unless model-family metadata is known and spans ≥ 2 families.

### H4 insufficient_data does NOT block the H1-H3 mechanism verdict

The overall B12 verdict is computed over **H1-H3 only** when H4 is
`insufficient_data`. The public report carries two explicit flags to confirm
this policy:

- `h4_insufficient_data_blocks_overall_verdict=false`
- `h1_h3_verdict_independent_of_h4=true`

This means **single-model B12 CI slices can still evaluate H1-H3** (ambiguous
routing / LLM-call reduction / P25 fallback sufficiency) on the model family
that ran, while **H4 (model-specific) needs multi-model aggregation** (≥ 2
known model families) before it can be `supported` or `refuted`. A single-model
CI slice therefore emits `H4=insufficient_data` plus a real H1-H3 verdict
(`supported` / `refuted` / `partial`), NOT a global `insufficient_data`.

## Methodology

### Replay-based (preferred)

If P21 records are available (from B11 live runs or CI ephemeral records), B12
is a pure replay over the C1 private-records adapter:

1. The C1 adapter loads the private P21 v1 payload, validates privacy flags,
   and normalizes each record with the three-category taint model.
2. For each ablation variant (A-E), compute the per-record outcome by selecting
   the appropriate per-strategy outcome (per the frozen variant definitions and
   the `actual_call_avoided_set` / E-random-subset sets above):
   - **A**: `weak_candidate_only` for `balanced_branch_set`, else P25 outcome.
   - **B**: `candidate_baseline` for `actual_call_avoided_set`, else P25 outcome.
   - **C**: identical to A.
   - **D**: P25 outcome for all records.
   - **E**: `candidate_baseline` for the frozen-seed random subset, else P25.
3. Aggregate per-variant metrics (overall mean, worst-group, bootstrap CIs,
   RobustUtility) and report the count block
   (`balanced_branch_count` / `p25_llm_eligible_count` /
   `actual_call_avoided_count` / `random_selected_count`).
4. Apply the predeclared (revised C1) hypothesis criteria.

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
improvement on higher-is-better metrics; negative = reduction on
lower-is-better metrics). The thresholds below are FROZEN before any B12
ablation runs. The H1-H3 criteria were revised (C1, 2026-06-19) before any
empirical replay to align with the actual expected balanced_v1 mechanism.

| Hypothesis | Support criterion | Refute criterion |
| --- | --- | --- |
| H1 (ambiguous routing) | `A ≈ D` (gold/SpanF0.5 within ±0.02) AND `A < D` (false_span/PFP/model_calls, all by > 0.02) AND `A < B` (false_span/PFP) AND `A < E` (false_span/PFP) AND `RU(A) > RU(B)` AND `RU(A) > RU(E)` (all by > 0.02) | Any one fails |
| H2 (LLM call reduction) | `A ≈ E` (gold/SpanF0.5/false_span/PFP within ±0.02) AND `A < D` (model_calls by > 0.02) | Either fails |
| H3 (P25 fallback sufficiency) | `D ≈ A` (gold/SpanF0.5 within ±0.02) | Either fails |
| H4 (model-specific) | Worst-case model-family spread on `A - D` `gold_span` delta > 0.05 AND ≥ 2 known model families | Spread ≤ 0.05 OR < 2 known model families (insufficient_data) |

The B12 verdict framework emits one of:
- `supported` (all 4 hypotheses supported)
- `refuted` (all 4 hypotheses refuted)
- `partial` (some supported, some refuted)
- `insufficient_data` (synthetic fixture, too few records, or < 2 known model
  families for H4)
- `not_implemented` (reserved for legacy; the `--input` path is now real)

Scientific verdicts (`supported` / `refuted` / `partial` / `insufficient_data`)
return exit 0; mechanical/privacy/schema errors (file not found, wrong
schema_version, raw-private-flag violations, adapter errors) return nonzero. A
scientific no-result is a valid CI outcome and must NOT fail CI.

### Count reporting (aggregate-only)

The public B12 report carries a `replay_counts` block with COUNTS only:
`total_records`, `complete_records`, `balanced_branch_count`,
`p25_llm_eligible_count`, `actual_call_avoided_count`,
`random_selected_count`, `e_random_seed`, and the `e_seed_limitation` note. No
per-record hash, task_id, raw/private repo_id, path, span, candidate_id,
content_sha, P31/P33 block, or raw prompt/response/snippet/provider field is
ever emitted. Aggregate group metrics use only public preregistered repo labels
for synthetic/preregistration fixtures or anonymized `public_repo_group_NNN`
labels for private `--input` replays.

## CI workflow design

### P21 step integration

B12 is wired into the P21 step of
`.github/workflows/real-provider-benchmark.yml`: after B10B/B11 consume the
SAME ephemeral `$P25_RECORDS` and before `rm -f "$P25_RECORDS"`, B12 runs:

```bash
python3 eval/b12_mechanism_decomposition.py --input "$P25_RECORDS" \
  --out artifacts/real_provider_ci/b12_mechanism_decomposition_report.json
```

A scientific no-result (`insufficient_data` / `refuted` / `partial`) is a valid
result and must NOT fail CI; only file/parse/privacy/schema failures fail (the
validator block in the workflow enforces `schema_version`, `generated_by`,
no-promotion flags, the forbidden-key/value scan, and the required aggregate
sections). The validator's banned keys include `private_record_hash`,
`p31_candidate_pools`, `p31_score_gold`, `p33b_anchor_subtypes`,
`route_features`, `task_id`, `repo_id`, `path`, `content_sha`, and raw
prompt/response/provider fields.

### Workflow inputs (for future live ablation runs)

- `stage`: `b12_mechanism_decomposition`
- `replay_source`: `ci_ephemeral_records` (replay, current) or
  `live_ablation_runs` (fallback, not yet wired)
- `enable_remote_models`: `true` (only needed for live ablation runs)
- `model_family`: optional (for single-model-family runs)

### Run matrix

- Replay: 1 run (consumes B11/P21 ephemeral records). **Current.**
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
- `artifacts/real_provider_ci/b12_mechanism_decomposition_report.json`
  (CI ephemeral-records replay report; verdict is a scientific result, may be
  `insufficient_data` / `refuted` / `partial` / `supported`)

## Self-test

```bash
python3 eval/b12_mechanism_decomposition.py --self-test
python3 eval/c1_private_records.py --self-test
```

The B12 self-test verifies the report aggregator mechanics over a synthetic
fixture (verdict `insufficient_data`) AND a real `--input` replay over the C1
adapter's synthetic v1 payload (verdict is a real scientific verdict, NOT
`not_implemented`). It runs 10 checks:

1. `forbidden_scan` — forbidden public keys/values scan
2. `spec_hash_stable` — algorithm spec sha256 stability
3. `synthetic_fixture_metrics` — synthetic fixture (incl. A≡C equivalence)
4. `hypothesis_evaluation_stub` — hypothesis evaluation mechanics
5. `input_full_mode` — `--input` loads private P21 v1 records via the C1
   adapter, computes per-variant metrics + counts, and emits a real verdict
6. `reference_specs_pinned` — B10/B10B/B11 reference specs present on disk
7. `artifacts_regenerated` — on-disk artifacts regenerated from build functions
8. `on_disk_artifacts_validated` — on-disk spec + report verified
9. `ablation_variants_defined` — 5 ablation variants + A≡C equivalence
10. `hypotheses_defined` — 4 hypotheses + predeclared (revised C1) criteria

## What's autonomous vs. needs user action

### Autonomous (can be done now)

- B12 plan document (this file)
- B12 CI workflow integration (P21 step, after B10B/B11)
- B12 report aggregator (`eval/b12_mechanism_decomposition.py`) with real
  `--input` replay over the C1 private-records adapter + self-test
- C1 shared private-records adapter (`eval/c1_private_records.py`) + self-test
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
- B12's `--input` replay is real (no longer a stub), but its verdict is
  mechanism decomposition only. No promotion / no default change follows.
- B12's `balanced_branch_predicate` reads benchmark route labels (category-2
  taint); this is exactly why balanced_v1 is benchmark-routed and is NOT a
  runtime-clean general algorithm proof.

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
