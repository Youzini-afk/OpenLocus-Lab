# B13 Distributionally Robust Policy Search

Date: 2026-06-18

B13 is the **distributionally robust policy search** phase that follows B12
(mechanism decomposition). The goal is to find a policy with 6-10 rules that
optimizes **worst-group utility** (not the average), using only
runtime-observable features, and to validate it via rotating
leave-one-model-family-out.

> **Important claim boundary.** B13 IS the policy-search *stage*
> (`stage_is_policy_search=true`), but the shipped skeleton performs NO
> empirical policy search (`empirical_policy_search_performed=false`). The
> synthetic-fixture / `--input` stub reports set
> `policy_search_performed=false` so the public artifact cannot be mistaken
> for an empirical B13 run. Even when a future empirical B13 search runs,
> the results are NOT promoted. `promotion_ready=false`,
> `default_should_change=false`, and `EvidenceCore` semantics are unchanged.
> B13 results are research candidates only: they inform B14 (uncertainty
> calibration) and B16 (downstream agent evaluation), but B13 does not
> authorize any default change, any policy promotion, or any EvidenceCore
> modification. B13 is the last "immediate priority" item in the B10-B19
> Breakthrough Sprint; the remaining items (B14-B19) are second priority or
> parallel tracks.

> **Important public-aggregate boundary.** Real B13 distributionally robust
> policy search requires private / ephemeral per-record P21 records with
> `route_features` + per-strategy outcomes + group membership, plus the
> rotating leave-one-model-family-out train/test splits. None of those are
> present in the public B11 aggregate or the B12 public-aggregate screen, so
> real B13 search cannot be performed from public aggregates alone. The
> bounded public-aggregate feasibility / no-go screen at
> `eval/b13_public_aggregate_feasibility_screen.py` reads the published B11
> and B12 artifacts and emits a `no_go_public_aggregate_only` (or, when the
> B11 aggregate itself has no records, `insufficient_data_public_aggregate_only`)
> feasibility report under `artifacts/b13_dro_policy_search/`. The screen
> never claims empirical policy search, never selects a rule, and never
> declares a winner.

## Preregistration declaration

The following artifacts, rule grammar constraints, optimization objective,
search constraints, validation methodology, and predeclared success/failure
criteria are **FROZEN** before any B13 search runs. No retuning of the
objective, the rule grammar, the search budget, or the success criteria is
allowed after B13 search runs begin. Any post-hoc analysis must be labeled
exploratory and require a separate validation round.

### Frozen artifacts

- `balanced_policy_v1_benchmark_routed` (B10 frozen spec; sha256 in
  `artifacts/b10_runtime_feature_audit/balanced_policy_v1_benchmark_routed.algorithm.json`)
  — referenced, not modified
- `balanced_policy_v1_runtime_shadow_ambiguous_branch` (B10B shadow predicate)
  — referenced, not modified
- B11/B12 frozen criteria — referenced, not modified
- B13 algorithm spec itself
  (`artifacts/b13_dro_policy_search/b13_dro_policy_search.algorithm.json`)
  — frozen before any search runs; stable sha256

## Objective

Find a policy with 6-10 rules, using only runtime-observable features, that
maximizes worst-group utility:

> **Maximize** `worst_group = min over {model_family, repo, language, task_bucket}`
> of `RobustUtility`, **OR** `CVaR_20%` (average of worst 20% of per-group
> utilities).

Where:

```text
RobustUtility = SpanF0.5
              - λ * PFP
              - μ * normalized_cost
              - ν * normalized_latency
```

Predeclared parameters (mirror B11/B12):

- `λ = 1.0` (PFP weight; `ROBUST_UTILITY_LAMBDA`)
- `μ = 0.1` (normalized cost weight; `ROBUST_UTILITY_MU`)
- `ν = 0.1` (normalized latency weight; `ROBUST_UTILITY_NU`)
- `CVaR α = 0.20` (worst-20% tail average; `CVAR_ALPHA`)

## Rule grammar constraints

### Maximum rules

- Minimum rules: 6
- Maximum rules: 10 (`MAX_RULES = 10`)
- Maximum search iterations: 1000 (`MAX_SEARCH_ITERATIONS = 1000`)

### Allowed runtime features

Each rule uses **ONLY** runtime-observable features from `route_features`
(`ALLOWED_RUNTIME_FEATURES`):

- `query_noise`
- `candidate_support_exists`
- `local_anchor`
- `rrf_backed_by_anchor`
- `candidate_count`
- `symbol_regex_agree_file`
- `symbol_regex_agree_span`
- `rrf_anchor_agree_file`
- `rrf_anchor_agree_span`
- `dense_support_present`

### Forbidden features

- **NO benchmark-private labels**: `task_bucket`, `task_risk_tags` are
  benchmark-private dependencies of the B10 benchmark-routed spec; B13 must
  not read them.
- **NO score-private fields**: `has_gold`, `score_group`, `outcome_metrics`
  are score-phase-only and must not be read by any routing rule.
- **NO model names in `algorithm_spec`**: B13 must use `model_profile`
  capabilities (e.g., `adapter.supports_reliable_span_narrow`,
  `adapter.cost_class`, `adapter.latency_class`), not raw model names like
  "Kimi", "Qwen", "DeepSeek", or "GLM". The B13 evaluator enforces this with
  the special invariant `algorithm_spec_has_no_model_names=true`.

### Allowed model_profile capabilities (referenced, not searched)

Rules may read `model_profile` capability fields:

- `supports_reliable_span_narrow` (boolean)
- `cost_class` (enum: low / medium / high)
- `latency_class` (enum: low / medium / high)

These capabilities are NOT model names; they are abstract adapter-level
capability descriptors.

### Rule grammar

Rules are simple predicates over the allowed features, e.g.:

- `query_noise > 0`
- `candidate_support_exists AND NOT rrf_backed_by_anchor`
- `local_anchor AND symbol_regex_agree_span`

### Allowed actions

Each rule maps to one action (`ALLOWED_ACTIONS`):

- `weak_only`
- `use_p25_action`
- `use_local_baseline`

**NO LLM actions**: B13 is a replay/search-only evaluator; it does not emit any
live LLM call action. The action space is LLM-free by construction.

### Search method

- Bounded grid + greedy refinement (no learned classifier, no neural policy).
- Pure Python: no numpy / sklearn / scipy.
- Maximum rules: 10.
- Maximum search iterations: 1000.

## Validation methodology

### Rotating leave-one-model-family-out

B13 must pass **all 3 rotations** for a candidate policy to be considered
"distributionally robust":

| Rotation | Train on | Test on |
| --- | --- | --- |
| `loo_kimi` | Qwen + DeepSeek (Flash + Pro) | Kimi |
| `loo_qwen` | Kimi + DeepSeek (Flash + Pro) | Qwen |
| `loo_deepseek` | Kimi + Qwen | DeepSeek (Flash + Pro) |

The held-out model family is used only for evaluation; no rule, threshold, or
action from the train families may peek at the test family. A policy that
regresses on any rotation beyond the predeclared thresholds is NOT
distributionally robust.

## Predeclared success/failure criteria

The criteria below are FROZEN before any B13 search runs (`PREDECLARED_CRITERIA`):

| Outcome | Criterion |
| --- | --- |
| **Success** | Found a policy with worst-group utility ≥ B10 balanced policy's worst-group utility AND all 3 rotations pass (no regression beyond thresholds). |
| **Failure** | No policy found that improves worst-group utility beyond B10's. |
| **Partial** | Policy improves some groups but not all (e.g., improves worst-group on 2 of 3 rotations but regresses on the third). |

Rotation regression thresholds (mirrors B11/B12 `≈` and `>` thresholds):

- `worst_group_delta_threshold = 0.02` (a rotation passes if the policy's
  worst-group `RobustUtility` is within ±0.02 of B10's, or strictly better)
- `strictly_greater_threshold = 0.02` (strict improvement margin)
- `cvar_alpha = 0.20` (CVaR tail fraction)

The B13 verdict framework emits one of:

- `success` (policy found + all 3 rotations pass + worst-group utility ≥ B10's)
- `failure` (no policy found improving worst-group utility beyond B10's)
- `partial` (some groups improved, not all)
- `insufficient_data` (synthetic fixture, or too few records to search)
- `not_implemented` (`--input` stub, real search deferred)

## Data requirement

B13 needs P21 records from B11 live runs (4 model families × 8 repos).
Each P21 record contains per-strategy outcomes, so each candidate rule's
per-record outcome can be computed by selecting the appropriate per-strategy
outcome from existing records (replay). No new live LLM calls are required for
the search itself.

If P21 records are not available, B13 cannot run a real search; the evaluator
emits `insufficient_data` (synthetic fixture self-test) or `not_implemented`
(`--input` stub).

## CI workflow design

### New stage: `b13_dro_policy_search`

Add a new stage `b13_dro_policy_search` to
`.github/workflows/real-provider-benchmark.yml`. The stage runs the B13 search
aggregator against P21 ephemeral records produced by B11 live runs (replay).
The search itself is replay-only and emits no live LLM calls.

### Workflow inputs

- `stage`: `b13_dro_policy_search`
- `replay_source`: `ci_ephemeral_records` (replay only)
- `enable_remote_models`: not required (search is replay-only)

### Run matrix

- Replay: 1 run (consumes B11 P21 records across 4 model families × 8 repos).

## B10B/B11/B12 integration

- B13 search consumes B11 P21 records (`replay_source="ci_ephemeral_records"`).
- B13 references (does not modify) the B10 frozen spec, the B10B shadow
  predicate, and the B11/B12 frozen criteria.
- B13 results feed into B14 (uncertainty calibration) and B16 (downstream
  agent evaluation). A B13-found policy that passes all 3 rotations is a
  research candidate for B14/B16; it is NOT promoted.

## Safety invariants

```text
promotion_ready=false
default_should_change=false
evidencecore_semantics_changed=false
stage_is_policy_search=true (B13 stage IS policy search)
empirical_policy_search_performed=false (skeleton performs no empirical search)
policy_search_performed=false (synthetic/stub report; use stage_is_policy_search
                              =true to mark the stage)
quality_strategy_tuned=false
runtime_calls_by_replay=0 (replay makes no new live calls)
model_calls_by_replay=0 (replay makes no new LLM calls)
aggregate_only_public_artifact=true
algorithm_spec_has_no_model_names=true (B13 special invariant)
```

The `policy_search_performed=false` flag in the synthetic / stub report is
deliberate: it prevents the public artifact from being misread as an
empirical B13 search. `stage_is_policy_search=true` carries the stage
definition (B13 *is* the policy-search stage); `empirical_policy_search_performed=false`
states plainly that no empirical search has been performed by the skeleton.

## What B13 does NOT prove

- B13 does **not** promote any policy.
- B13 does **not** change any defaults.
- B13 does **not** change `EvidenceCore` semantics.
- B13 does **not** authorize B14/B16 without separate user review.
- B13 results are research candidates only; a B13-found policy is NOT the
  new default until separately promoted via the standard promotion process.
- B13's `--input` path is a stub (`verdict="not_implemented"`); full search
  computation is deferred to a later task.

## Self-test (read-only) and explicit artifact regeneration

```bash
python3 eval/b13_dro_policy_search.py --self-test
python3 eval/b13_dro_policy_search.py --regenerate-artifacts
python3 eval/b13_public_aggregate_feasibility_screen.py --self-test
```

The `eval/b13_dro_policy_search.py --self-test` run is **read-only**: it
verifies the report aggregator mechanics without live runs (synthetic
fixture only; `replay_source="synthetic_fixture"`; verdict
`insufficient_data`) and compares the in-memory expected algorithm spec +
report to the on-disk artifacts, **failing on drift**. It does NOT write
anything to disk. It emits `stage_is_policy_search=true`,
`empirical_policy_search_performed=false`, and
`policy_search_performed=false`, plus top-level `policy_found=false`,
`rotations_evaluated=false`, `rotations_defined=true`, `rotation_count=3`,
`winner_declared=false`, so the synthetic-fixture report is unambiguously
NOT an empirical B13 search. Synthetic / stub reports emit only rotation
*definitions* (`rotations_defined=true`, `rotation_count=3`,
`rotations_evaluated=false`); they never emit per-rotation `passes=true`,
`all_rotations_pass=true`, `test_worst_group_utility`, or
`delta_vs_b10_reference` as if empirical. The skeleton verdict framework
emits only `insufficient_data` (synthetic fixture) or `not_implemented`
(ci_ephemeral_records stub); `success` / `failure` / `partial` are reserved
for a future empirical `policy_search_performed=true` path that is NOT
present in this skeleton.

The read-only self-test runs 9 checks:

1. `forbidden_scan` — forbidden public keys/values scan (incl. raw model-name
   scan on the algorithm spec)
2. `spec_hash_stable` — algorithm spec sha256 stability
3. `synthetic_fixture_metrics` — synthetic fixture metrics
4. `rule_grammar_valid` — rule grammar (allowed features + actions only)
5. `search_mechanics_stub` — bounded-grid + greedy-refinement mechanics stub
6. `leave_one_out_rotations_defined` — 3 leave-one-model-family-out rotations
   (definitions only; no empirical per-rotation passes / utilities / deltas)
7. `input_stub_not_implemented` — `--input` stub returns `not_implemented`
8. `reference_specs_pinned` — B10/B10B/B11/B12 reference specs present on disk
9. `artifacts_match_in_memory` — read-only drift check: in-memory expected
   spec + report match the on-disk artifacts

`python3 eval/b13_dro_policy_search.py --regenerate-artifacts` is the ONLY
mutating path: it (re)writes the on-disk algorithm spec + synthetic-fixture
report from the current build functions. After mutating, re-run
`--self-test` to confirm the on-disk artifacts now match the in-memory
expected objects (no drift).

The `eval/b13_public_aggregate_feasibility_screen.py --self-test` run
verifies the bounded public-aggregate feasibility / no-go screen against a
synthetic minimal B11 + B12 fixture. It emits
`verdict=no_go_public_aggregate_only` (or
`insufficient_data_public_aggregate_only` when the B11 aggregate has no
records), with `policy_search_performed=false`,
`empirical_policy_search_performed=false`, `policy_found=false`, and
`rotations_evaluated=false`. It runs 4 checks: `happy_path`,
`input_validation_blocks`, `insufficient_data_branch`, and
`forbidden_scan`.

## Artifacts

- `artifacts/b13_dro_policy_search/b13_dro_policy_search.algorithm.json`
  (frozen spec; deterministic, stable sha256; regenerated only via
  `--regenerate-artifacts`)
- `artifacts/b13_dro_policy_search/b13_dro_policy_search_report.json`
  (synthetic-fixture self-test report, verdict `insufficient_data`;
  `policy_search_performed=false`,
  `empirical_policy_search_performed=false`,
  `stage_is_policy_search=true`, `policy_found=false`,
  `rotations_evaluated=false`, `rotations_defined=true`,
  `rotation_count=3`, `winner_declared=false`; no empirical per-rotation
  passes / utilities / deltas)
- `artifacts/b13_dro_policy_search/b13_public_aggregate_feasibility_report.json`
  (bounded public-aggregate feasibility / no-go screen report;
  `verdict=no_go_public_aggregate_only` or
  `insufficient_data_public_aggregate_only`; `policy_found=false`,
  `rotations_evaluated=false`,
  `full_b13_possible_from_public_artifacts=false`)

## What's autonomous vs. needs user action

### Autonomous (can be done now)

- B13 plan document (this file)
- B13 CI workflow definition (new stage `b13_dro_policy_search`)
- B13 report aggregator skeleton (`eval/b13_dro_policy_search.py`) +
  read-only `--self-test` (compares in-memory expected artifacts to on-disk
  artifacts, fails on drift) and explicit `--regenerate-artifacts` mutating
  path (emits `stage_is_policy_search=true`,
  `empirical_policy_search_performed=false`,
  `policy_search_performed=false`, `policy_found=false`,
  `rotations_evaluated=false`, `rotations_defined=true`, `rotation_count=3`,
  `winner_declared=false`; no empirical per-rotation passes / utilities /
  deltas)
- B13 frozen algorithm spec + synthetic-fixture report artifacts
- B13 bounded public-aggregate feasibility / no-go screen
  (`eval/b13_public_aggregate_feasibility_screen.py`) + self-test +
  `artifacts/b13_dro_policy_search/b13_public_aggregate_feasibility_report.json`
  (reads the published B11 aggregate + B12 public screen; emits
  `no_go_public_aggregate_only` / `insufficient_data_public_aggregate_only`;
  never claims empirical policy search, never selects a rule, never declares
  a winner)

### Needs P21 records

- B13 real search requires P21 records from B11 live runs (4 model families ×
  8 repos). If those records are not yet produced, B13 emits
  `insufficient_data` / `not_implemented`.

### Needs user review

- Results interpretation
- Decision to proceed to B14 (uncertainty calibration) or B16 (downstream
  agent evaluation) using a B13-found policy as a research candidate
- Decision to expand from minimum viable to full B13 (more rules, more
  features, more rotations)

## Next steps after B13

- **B13 success**: a distributionally robust policy candidate is identified
  (worst-group utility ≥ B10's, all 3 rotations pass). Proceed to B14 to
  calibrate uncertainty on the candidate, and B16 to test it downstream.
- **B13 failure**: no policy improves worst-group utility beyond B10's. B10
  remains the frozen balanced policy; B14/B16 should use B10 as the
  reference policy.
- **B13 partial**: some groups improve, not all. Investigate group-conditional
  rules; possibly relax the worst-group objective or expand the rule grammar
  in a separate B13B round (separate preregistration required).
