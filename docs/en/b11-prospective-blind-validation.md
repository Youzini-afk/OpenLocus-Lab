# B11 Prospective Blind Validation

Date: 2026-06-18

B11 is the first true **prospective** validation of the frozen balanced policy
`balanced_policy_v1_benchmark_routed` (B10). Prior validation
(B6C/B6E/B6F/B8-lite/B9C) shared the same task generation and research
universe. B11 uses **new repos and tasks generated after the 2026-06-18 policy
freeze**, with no retuning of policies, thresholds, or success criteria.

> **Important claim boundary.** B11 is a prospective stress test, not a
> promotion step. Even if B11 succeeds, `promotion_ready=false`,
> `default_should_change=false`, and `EvidenceCore` semantics are unchanged.
> B11's outcome only decides whether the balanced policy is a credible
> algorithm candidate worth further research (B12 mechanism decomposition, B13
> distributionally robust policy search).

## Preregistration declaration

The following artifacts, thresholds, and criteria are **FROZEN** before any
prospective validation runs. No retuning is allowed after B11 live runs begin.
Any post-hoc analysis must be labeled exploratory and require a separate
validation round.

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
- All success/failure/partial criteria in this document

## Objective

Test whether the frozen balanced policy generalizes to unseen repos, languages,
and model families. Specifically:

> Does Balanced v1 preserve gold/SpanF0.5 while reducing false spans, PFP, and
> LLM calls on prospective data, with worst-group metrics not regressing beyond
> predeclared thresholds?

## Scope

### Minimum viable B11 (recommended first round)

- 8 repos across 5 languages
- ~120 tasks (15 per repo)
- 4 model families
- 4 policies
- Estimated runtime: 4-6 hours of CI per model family

### Full B11 (if minimum viable is promising)

- 12-16 repos across 5+ languages
- 300-500 tasks
- 4 model families
- 4 policies

## Repos (new, not used in B6B/B6C/B6E/B6F/B8-lite)

**Already used (excluded):** `py_flask`, `js_express`, `go_gin`,
`rust_ripgrep`, `go_cobra`, `py_httpx`, `js_axios`, `rust_mdbook`.

### Minimum viable B11 repo selection (8 repos, 5 languages)

| repo_id | Public repo | Language | Tier | Domain |
| --- | --- | --- | --- | --- |
| `py_fastapi` | fastapi/fastapi | Python | nightly_medium | web framework |
| `py_pytest` | pytest-dev/pytest | Python | nightly_medium | testing framework |
| `ts_vite` | vitejs/vite | TypeScript | nightly_medium | build tool |
| `ts_hono` | honojs/hono | TypeScript | nightly_medium | web framework |
| `go_chi` | go-chi/chi | Go | nightly_medium | web framework |
| `go_prometheus` | prometheus/prometheus | Go | nightly_medium | monitoring |
| `rust_deno` | denoland/deno | Rust | weekly_large | runtime |
| `java_spring_petclinic` | spring-projects/spring-petclinic | Java | nightly_medium | web app |

### Full B11 additional repos (4-8 more)

| repo_id | Public repo | Language | Tier | Domain |
| --- | --- | --- | --- | --- |
| `py_requests` | psf/requests | Python | nightly_medium | HTTP client |
| `py_rich` | Textualize/rich | Python | nightly_medium | terminal UI |
| `go_gh_cli` | cli/cli | Go | nightly_medium | CLI |
| `ts_vue_core` | vuejs/core | TypeScript | nightly_medium | framework |
| `kotlin_okhttp` | square/okhttp | Kotlin | nightly_medium | HTTP client |
| `c_curl` | curl/curl | C | nightly_medium | networking |
| `ruby_rails` | rails/rails | Ruby | weekly_large | framework |
| `cpp_json` | nlohmann/json | C++ | nightly_medium | header-only |

All repos are public/open-source and listed in `eval/ci_repos/openlocus-ci-repos-v1.yaml`.

## Model adapters

| Model family | Model ID | Output mode | Rationale |
| --- | --- | --- | --- |
| Kimi (reference) | `[mk]Kimi-K2.7-Code` | `tool_call` | Primary reference; established in B1/B6C/B6E/B6F |
| Qwen (secondary) | `[mk]Qwen3.6-27B` | `json_schema_strict` | Health-stable per B9B/B9C; direction consistent with Kimi |
| DeepSeek Flash (recall) | `[mk]DeepSeek-V4-Flash` | `json_schema_strict` | Health-stable per B9D; recall-oriented profile |
| DeepSeek Pro (conservative) | `[mk]DeepSeek-V4-Pro` | `json_schema_strict` | Health-stable per B9D; conservative profile |

**GLM-5.2 is excluded** (noisy per B9A/B6D; `schema_valid` 0.75-0.833,
`infra_failure` 0.25-0.5). GLM remains opt-in/exploratory, not critical path.

**Output mode is a model-adapter configuration parameter, NOT an OpenLocus
algorithm variable** (per project memory 237). No output-mode leaderboards.

## Policies compared

| Policy | Spec ID | Description |
| --- | --- | --- |
| Local baseline | (no LLM) | Pure local retrieval (regex + BM25 + symbol + RRF); no LLM calls |
| P25 | `p25.route_bucket_routed_v0` | Benchmark-routed bucket policy; depends on `task_bucket`/`task_risk_tags` |
| Balanced v1 | `balanced_policy_v1_benchmark_routed` | Frozen balanced policy; ambiguous→`weak_only`, else P25; depends on `task_bucket`/`task_risk_tags` |
| Conservative | `rmc_local_conservative_v0` | Frozen conservative policy; avoids false positives but kills recall |

## Task generation

Tasks are generated **AFTER** policy freeze (2026-06-18) using the existing CI
task generation pipeline (`eval/ci_repos/openlocus-ci-repos-v1.yaml` + openlocus
CLI). Tasks are deterministic/mined from repo content (not human-written). Task
generation does NOT read labels in RUN phase (same RUN/SCORE separation as
existing P21/P25/P30 evaluators).

## Metrics

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
  - Repo (8 or 12-16 repos)
  - Language (Python/TypeScript/Go/Rust/Java + others)
  - Task bucket (positive/negative/ambiguous/hard-distractor)

### Statistical

- 95% bootstrap confidence intervals (10,000 resamples, stratified by repo)
- Leave-one-repo-out sensitivity
- Leave-one-model-family-out sensitivity
- Paired deltas (Balanced v1 vs. each baseline)
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

Suggested parameters (predeclared; can be varied in sensitivity analysis):
- `λ = 1.0`
- `μ = 0.1`
- `ν = 0.1`

## Predeclared success/failure/partial criteria

All deltas are `Balanced_v1 - baseline` (positive = improvement, negative =
regression), computed per-task and aggregated.

### Success (all must hold)

- Balanced v1 preserves gold: `Δgold_span vs P25 ≥ -max(1, 0.01 * P25_gold)`
- Balanced v1 preserves SpanF0.5: `ΔSpanF0.5 vs P25 ≥ -0.02`
- Balanced v1 reduces false spans: `Δfalse_spans vs P25 < 0`
- Balanced v1 reduces PFP: `ΔPFP vs P25 ≤ 0`
- Balanced v1 reduces LLM calls: `ΔLLM_calls vs P25 < 0`
- Worst-group metrics don't regress beyond thresholds:
  - Worst-group `Δgold_span ≥ -max(2, 0.02 * P25_gold)`
  - Worst-group `ΔSpanF0.5 ≥ -0.05`
  - Worst-group `ΔPFP ≤ +0.05`

### Failure (any one)

- Balanced v1 regresses on overall gold: `Δgold_span < -max(2, 0.02 * P25_gold)`
- Balanced v1 regresses on overall SpanF0.5: `ΔSpanF0.5 < -0.05`
- Worst-group `Δgold_span < -max(3, 0.03 * P25_gold)`
- Worst-group `ΔSpanF0.5 < -0.10`

### Partial (neither success nor failure)

- Mixed results: some metrics improve, some regress, but not beyond failure
  thresholds. B11 should be followed by B12 (mechanism decomposition) to
  understand which conditions drive the mixed results.

## CI workflow design

### New stage: `b11_prospective`

Add a new stage `b11_prospective` to
`.github/workflows/real-provider-benchmark.yml`. The stage runs P21 with the
frozen policies on the new B11 repos, then runs the B11 report aggregator and
B10B replay.

### Workflow inputs

- `stage`: `b11_prospective`
- `dataset`: `b11_prospective_v1`
- `llm_model`: one of `[mk]Kimi-K2.7-Code`, `[mk]Qwen3.6-27B`,
  `[mk]DeepSeek-V4-Flash`, `[mk]DeepSeek-V4-Pro`
- `enable_remote_models`: `true`
- `repo_id`: optional (for single-repo runs)

### Run matrix

- 4 model families × 8 repos (minimum viable) = 32 runs, OR
- 4 model families × 1 batch of 8 repos = 4 runs (each run covers all repos)
- Each run produces P21 ephemeral records + B10B replay report

### B10B integration

- B10B `--records` runs in CI after each B11 run (already integrated in the P21
  step via commit `2cbdd0c`)
- This gives B10B its first empirical validation
  (`replay_source="ci_ephemeral_records"`)
- If B10B passes all 10 predeclared gates, it upgrades from
  "mechanics-validated" to "empirically-supported"
- If B10B fails, B11 still proceeds (B10B is ambiguous-branch shadow only; B11
  tests the benchmark-routed policy)

## B11 report aggregator

New evaluator: `eval/b11_prospective_validation.py`

Reads P21 outputs from 4 model × N repo runs and computes:

- Per-policy metrics (Local, P25, Balanced v1, Conservative)
- Overall mean + worst-group
- Bootstrap CIs
- Leave-one-repo-out, leave-one-model-family-out
- `RobustUtility`
- Verdict (`success` / `failure` / `partial`)

## Safety invariants

```text
promotion_ready=false
default_should_change=false
evidencecore_semantics_changed=false
runtime_calls_by_replay=0 (for B10B replay)
model_calls_by_replay=0 (for B10B replay)
aggregate_only_public_artifact=true
policy_search_performed=false (no policy tuning during B11)
quality_strategy_tuned=false
```

## What's autonomous vs. needs user action

### Autonomous (can be done now)

- B11 plan document (this file)
- B11 CI workflow definition
- B11 report aggregator script (skeleton + self-test)
- Repo selection (from existing CI manifest)
- Model adapter configuration (existing profiles)

### Needs workflow_dispatch

- Actual live LLM runs (require `enable_remote_models=true` +
  `OPENLOCUS_ALLOW_REMOTE=1`)
- User triggers each model family run

### Needs user review

- Results interpretation
- Decision to proceed to B12 (mechanism decomposition) or B13
  (distributionally robust policy search)
- Decision to expand from minimum viable to full B11

## Artifacts

- `artifacts/b11_prospective_validation/b11_prospective_validation_report.json`
- `artifacts/b11_prospective_validation/b11_prospective_validation_plan.json`
  (this preregistration, machine-readable)
- `artifacts/real_provider_ci/b10b_runtime_shadow_replay_report.json` (B10B
  empirical data from B11 runs)

## Self-test

```bash
python3 eval/b11_prospective_validation.py --self-test
```

Verifies the report aggregator mechanics without live runs (synthetic fixture
only; `replay_source="synthetic_fixture"`; verdict `partial` or
`insufficient_data`).

## What B11 does NOT prove

- B11 does **not** prove the balanced policy is ready for promotion.
- B11 does **not** prove the runtime-shadow predicate (B10B) is empirically
  supported (that requires B10B to pass gates on real CI records).
- B11 does **not** change `EvidenceCore` semantics.
- B11 does **not** change any defaults.
- B11 does **not** authorize B12/B13 without separate user review.

## Next steps after B11

- **B11 success**: proceed to B12 (mechanism decomposition) to understand why
  the balanced policy works; then B13 (distributionally robust policy search)
  to optimize worst-group.
- **B11 failure**: the balanced policy is likely overfit to the B6C/B6E/B6F
  universe. Restart policy search with distributionally robust objectives
  (B13) on the combined B6C+B11 data.
- **B11 partial**: proceed to B12 to identify which conditions drive the mixed
  results; B12 informs whether to adjust the policy (B13) or accept partial
  generalization.
