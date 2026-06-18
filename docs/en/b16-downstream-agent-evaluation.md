# B16 Downstream Coding-Agent Evaluation

Date: 2026-06-18

B16 is the **downstream coding-agent evaluation** phase. The goal is a
**frozen, preregistered paired within-task randomized controlled trial
(RCT)** that measures whether a candidate retrieval/context variant
improves a downstream coding agent (not just retrieval aggregates) on
real, paired, isolated-workspace agent runs.

B16 is a **bounded planning / feasibility phase**, NOT live downstream
agent evaluation. The shipped skeleton performs NO live downstream
agent runs, NO patch execution, NO agent-behavior metrics evaluation,
and NO solve-rate evaluation. The frozen preregistration
(`eval/b16_downstream_agent_evaluation.py`) defines the arm set, the
task types, the metric registry, the hard gates, and the experimental
structure (no-LLM feasibility → paired live agent RCT → freeze candidate
retrieval variant → fresh validation); the bounded public-aggregate
feasibility / no-go screen
(`eval/b16_public_aggregate_feasibility_screen.py`) reads the
already-published B11 matrix + B12/B13/B14/B15 public screens and
emits a `no_go_public_aggregate_only` (or
`insufficient_data_public_aggregate_only`) verdict.

> **Important claim boundary.** B16 IS the downstream-agent-evaluation
> *stage* (`stage_is_downstream_agent_evaluation=true`), but the
> shipped skeleton performs NO live downstream agent runs
> (`downstream_agent_runs_performed=false`), NO patch execution
> (`patch_execution_performed=false`), NO agent-behavior metrics
> evaluation (`agent_behavior_metrics_evaluated=false`), and NO
> solve-rate evaluation (`solve_rate_evaluated=false`). The
> synthetic-fixture / `--input` stub report sets
> `per_record_inputs_available=false`, `promotion_ready=false`,
> `default_should_change=false`,
> `evidencecore_semantics_changed=false`, `retrieval_variant_promoted=false`,
> `policy_search_performed=false`, `quality_strategy_tuned=false`,
> `new_provider_calls=0` so the public artifact cannot be mistaken for
> an empirical B16 downstream agent result. This commit is strictly a
> skeleton / no-go commit: the current flags
> (`downstream_agent_runs_performed=false`,
> `patch_execution_performed=false`,
> `agent_behavior_metrics_evaluated=false`,
> `solve_rate_evaluated=false`, `per_record_inputs_available=false`,
> `promotion_ready=false`, `default_should_change=false`,
> `evidencecore_semantics_changed=false`,
> `retrieval_variant_promoted=false`) remain false. Any future real
> B16 empirical path would require its own separate preregistration;
> the exact flag schema for that future path is future work and is
> NOT present in this skeleton. B16 results in this commit are research
> candidates only: this skeleton/no-go commit authorizes no default
> change, no retrieval-variant promotion, no EvidenceCore
> modification, and no claim that retrieval improvements improve coding
> agents.

> **Important retrieval-vs-downstream boundary.** The B10-B15
> retrieval/context candidate research is **retrieval research**; it
> does NOT prove downstream coding-agent value. Retrieval improvements
> are NOT downstream agent improvements. B15 PackPolicy is NOT a
> downstream agent improvement. Real B16 downstream agent evaluation
> requires private / ephemeral per-run paired agent outputs: paired
> live downstream agent runs of the same task under two arms, per-run
> agent event logs (tool calls, first-file-before-edit timing,
> wrong-file-edit annotations), per-run patches / diffs, per-run test
> execution results, per-run solve labels, per-run tool-call / token /
> latency / cost rows, per-run isolated fresh workspace proof, per-run
> randomized arm order, and a task oracle / hidden-test manifest. None
> of those are present in any current public artifact. The bounded
> public-aggregate feasibility / no-go screen at
> `eval/b16_public_aggregate_feasibility_screen.py` reads the
> published B11 matrix, the B12 public screen, the B13 public
> feasibility, the B14 public feasibility, and the B15 public
> prior-screen reports and emits a `no_go_public_aggregate_only` (or
> `insufficient_data_public_aggregate_only`) report under
> `artifacts/b16_downstream_agent_evaluation/`. The screen never claims
> downstream agent value, never computes a solve-rate / tool-call /
> token / latency / cost metric from retrieval aggregates, never
> promotes a retrieval variant, never freezes a candidate retrieval
> variant, and never declares a winner.

> **CRITICAL anti-fabrication boundary.** The skeleton MUST NOT
> compute fake solve-rate / correct-file-before-first-edit /
> wrong-file-edits / tool-call / token / latency / cost metrics from
> retrieval aggregates. The B11/B12/B13/B14/B15 artifacts are
> retrieval/context candidate research; they do NOT contain per-run
> paired agent outputs, so any downstream agent metric computed from
> them would be a fabrication. The synthetic fixture validates only
> that the arm set, task types, metric names, and hard gates are wired
> correctly; it does NOT present synthetic metric values as empirical
> B16 results. The report surfaces
> `downstream_agent_runs_performed=false`,
> `patch_execution_performed=false`,
> `agent_behavior_metrics_evaluated=false`,
> `solve_rate_evaluated=false`, and
> `no_fake_downstream_metrics_from_retrieval_aggregates=true` so a
> reader cannot mistake the skeleton for an empirical B16 downstream
> agent result.

## Preregistration declaration

The following artifacts, arm set, task types, metric registry, hard
gates, experimental structure, and predeclared success/partial/
failure criteria are **FROZEN** before any B16 empirical runs. No
retuning of the arm set, the task types, the metric registry, the hard
gates, or the success criteria is allowed after B16 empirical runs
begin. Any post-hoc analysis must be labeled exploratory and require a
separate validation round.

### Frozen artifacts

- `balanced_policy_v1_benchmark_routed` (B10 frozen spec) — referenced,
  not modified
- `balanced_policy_v1_runtime_shadow_ambiguous_branch` (B10B shadow
  predicate) — referenced, not modified
- B11/B12/B13/B14/B15 frozen criteria — referenced, not modified
- B16 algorithm spec itself
  (`artifacts/b16_downstream_agent_evaluation/b16_downstream_agent_evaluation.algorithm.json`)
  — frozen before any downstream agent runs; stable sha256

## Objective

Produce a **frozen, preregistered paired within-task RCT** that
measures whether a candidate retrieval/context variant improves a
downstream coding agent on paired live agent runs with isolated fresh
workspace, randomized arm order, same budget/tools/prompt except the
retrieval/context variant, and no cross-run memory. The B16 RCT is NOT
a retrieval aggregate analysis; it is a downstream agent RCT. B16 does
NOT learn an LLM, does NOT change EvidenceCore, does NOT promote a
default, does NOT promote a retrieval variant, and does NOT claim that
retrieval improvements improve coding agents.

## Arms (FROZEN)

The arm set is the closed set of retrieval/context variants a B16
paired RCT may compare:

- `control_current_retrieval_v0` — the current retrieval stack
  (control arm)
- `balanced_v1_retrieval_candidate` — the balanced_v1 retrieval
  candidate (treatment arm)
- `candidate_pack_policy_v0` — EXPLORATORY ONLY; included only if a
  real B15 candidate PackPolicy exists (`only_if_b15_real_candidate_exists`).
  The B15 skeleton does NOT produce one (`pack_policy_learned=false`), so
  this arm is EXCLUDED by default.
- `gold_context_ceiling` — DEBUGGING-ONLY; supplies the gold context as
  a ceiling reference (`debugging_only_never_promoted`). NEVER used for
  promotion; EXCLUDED by default.

Primary comparison arms (always present): `control_current_retrieval_v0`
vs `balanced_v1_retrieval_candidate`.

## Task types (FROZEN)

The task-type set is the closed set of downstream coding-agent tasks a
B16 paired RCT may evaluate. Task types are model-independent and
label-free: they describe the agent task shape, not the
benchmark-private oracle or hidden tests.

- `bug_localization`
- `small_code_edit`
- `test_selection`
- `multi_file_feature`
- `refactor_impact`

## Paired within-task randomization (FROZEN)

Real B16 is a paired within-task randomized controlled trial. Each
task is run twice under two arms (control and treatment) with:

- **paired within-task randomization** — the same task is answered
  under both arms so per-task noise is differenced out;
- **isolated fresh workspace** per run — no state leaks between runs;
- **randomized arm order** — arm order is randomized per task to
  deconfound arm from run order;
- **same budget / tools / prompt EXCEPT the retrieval/context variant**
  — the ONLY varied factor is the retrieval/context variant
  (`operational_parity_same_tools_budget_prompt_except_retrieval_variant=true`);
- **no cross-run memory** — the agent has no memory of the paired run
  (`operational_parity_no_cross_run_memory=true`).

A real B16 run must produce per-run event logs, patches/diffs, test
execution results, solve labels, and tool-call/token/latency/cost rows.

## Metric registry (FROZEN)

The metric NAMES B16 will compute when real per-run paired agent
inputs are available. The skeleton defines them and validates the
hard gates, but does NOT compute fake metric values from retrieval
aggregates.

- `solve_rate` (per-arm paired-task solve rate from solve labels)
- `correct_file_before_first_edit` (per-arm fraction of runs where the
  first edit landed in the correct file, from the first-file-before-
  first-edit event)
- `wrong_file_edits` (per-arm count or rate of edits to wrong files,
  from wrong-file-edit annotations)
- `tool_calls_before_first_edit` (per-arm tool-call count before the
  first edit, from agent event logs)
- `context_tokens` (per-arm context token count, from per-run token
  rows)
- `tests_pass` (per-arm fraction of runs whose tests passed, from test
  execution results)
- `latency` (per-arm run latency, from per-run latency rows)
- `cost` (per-arm run cost, from per-run cost rows)

Every metric requires per-run paired agent outputs; none can be
computed from retrieval aggregates.

## Hard gates (FROZEN)

The following hard gates are FROZEN before any B16 downstream agent
runs. A candidate retrieval variant that fails any gate is rejected,
regardless of its aggregate solve-rate or any retrieval-aggregate
signal.

- **feasibility_gate**: real B16 requires paired live agent runs, agent
  event logs, patches/diffs, test execution results, solve labels,
  first-file-before-first-edit events, wrong-file-edit annotations,
  tool-call/token/latency/cost rows, isolated workspace proof,
  randomized arm order, and a task oracle/hidden-test manifest. The
  skeleton does not evaluate this gate (no real per-run inputs); it
  only defines it.
- **denominator_gate**: every (task_type, arm) cell must have a
  denominator ≥ the frozen minimum (`min_denominator_per_task_type_arm_cell=30`);
  no small-denominator solve-rate claim may be promoted. The skeleton
  does not evaluate this gate (no real per-run inputs); it only
  defines it.
- **leakage_gate**: no benchmark-private label, no hidden-test
  answer, no solve label enters the retrieval variant or the agent
  prompt as a feature; solve labels are the validation TARGET, never
  an input.
- **operational_parity_gate**: arms must share the same budget, tools,
  and prompt EXCEPT the retrieval/context variant, with isolated fresh
  workspace per run, randomized arm order, and no cross-run memory
  (`operational_parity_token_budget_match_tolerance=0.10`,
  `operational_parity_latency_match_tolerance=0.15`). The skeleton
  does not evaluate this gate; it only defines it.
- **privacy_gate**: `aggregate_only_public_artifact=true`; no raw
  records, task IDs, repo IDs, candidate IDs, paths, spans, snippets,
  prompts, responses, diffs, patches, test execution results, solve
  labels, first-file-before-first-edit events, wrong-file-edit
  annotations, tool-call/token/latency/cost rows, agent event logs,
  gold spans, private labels, provider keys, base URLs, API
  keys/secrets/tokens, content SHAs, digests, or line ranges in any
  public artifact; `new_provider_calls=0` in the skeleton.
- **promotion_false_gate**: `promotion_ready=false`,
  `default_should_change=false`,
  `evidencecore_semantics_changed=false`,
  `retrieval_variant_promoted=false`,
  `downstream_agent_runs_performed=false`,
  `patch_execution_performed=false`,
  `agent_behavior_metrics_evaluated=false`,
  `solve_rate_evaluated=false`,
  `policy_search_performed=false`,
  `quality_strategy_tuned=false` are always present, so a skeleton /
  stub / no-go report cannot be misread as a promoted retrieval variant
  or a downstream agent result.

## Split protocol (FROZEN)

Real B16 splits per-run inputs into a **task-screen split** and a
**fresh-validation split**, stratified by (task_type, repo,
model_family). The split protocol is
`stratified_by_task_type_repo_model_family` with
`task_screen_fraction=0.50` and `fresh_validation_fraction=0.50`. The
fresh-validation split is held out and reported once
(`fresh_validation_split_reported_once=true`). No metric on the
fresh-validation split may feed back into the task screen or the
candidate-retrieval-variant freeze.

## Worst-group reporting

B16 reports worst-group metrics over `{task_type, repo, model_family,
language}` groups, plus a `CVaR_20%` tail average (worst 20% of group
metrics). The CVaR tail fraction is `cvar_alpha=0.20` (frozen).

## Privacy / publication gates

Public artifacts must be aggregate-only. The B16 evaluator enforces:

- **no** raw records, task IDs, repo IDs, candidate IDs, paths, spans,
  snippets, prompts, responses, diffs, patches, test execution
  results, solve labels, first-file-before-first-edit events,
  wrong-file-edit annotations, tool-call/token/latency/cost rows,
  agent event logs, gold spans, private labels, provider keys, base
  URLs, API keys/secrets/tokens, content SHAs, digests, or line ranges
  in any public artifact;
- **no** raw filesystem path strings, 64-char hex digests, http(s)
  URLs, or credential assignments as values;
- `aggregate_only_public_artifact=true`;
- `new_provider_calls=0` (skeleton; no live LLM calls and no live
  downstream agent runs);
- `forbidden_public_key_scan_clean=true`.

## Predeclared success / partial / failure criteria

The criteria below are FROZEN before any B16 empirical runs
(`PREDECLARED_CRITERIA`):

| Outcome | Criterion |
| --- | --- |
| **Success** | The frozen candidate retrieval variant improves solve rate on the fresh-validation split by ≥ `0.02` over the control arm on EVERY task type, with `correct_file_before_first_edit` improvement ≥ `0.02`, `wrong_file_edits` regression ≤ `0.15`, AND every metric estimated is within the frozen denominator and operational-parity gates, AND cost reported per arm. |
| **Partial** | Some task types improve on solve rate but not all; or `wrong_file_edits` regresses on one task type; or one metric is within the denominator/operational-parity gates but another is not. |
| **Failure** | No task type improves on solve rate on the fresh-validation split, OR any hard gate fails (feasibility, denominator, leakage, operational parity, privacy, promotion false). |

Frozen numeric gates:

- `solve_rate_strictly_greater_threshold = 0.02`
- `correct_file_before_first_edit_strictly_greater_threshold = 0.02`
- `wrong_file_edits_regression_threshold = 0.15`
- `cvar_alpha = 0.20`
- `task_screen_fraction = 0.50`
- `fresh_validation_fraction = 0.50`
- `min_denominator_per_task_type_arm_cell = 30`
- `randomization_balance_max_imbalance = 0.05`
- `operational_parity_token_budget_match_tolerance = 0.10`
- `operational_parity_latency_match_tolerance = 0.15`
- `cost_reported_per_arm = true`

The B16 verdict framework emits one of:

- `success` (all task types improve on solve rate, all gates pass on
  the fresh-validation split)
- `failure` (no improvement, or any hard gate fails)
- `partial` (some task types improve, not all; or one gate is
  borderline)
- `insufficient_data` (synthetic fixture, or too few runs)
- `not_implemented` (`--input` stub, real downstream agent RCT
  deferred)

The skeleton only emits `insufficient_data` (synthetic fixture) or
`not_implemented` (ci_ephemeral_records stub); `success` / `failure` /
`partial` are NOT emitted by this skeleton. Any future real B16
empirical path that might emit them would require its own separate
preregistration, and its exact flag schema is future work and is NOT
present in this skeleton. This commit keeps
`downstream_agent_runs_performed=false`,
`patch_execution_performed=false`,
`agent_behavior_metrics_evaluated=false`, and
`solve_rate_evaluated=false` strictly.

## Required per-record inputs (real-B16 data contract)

Real B16 downstream agent evaluation requires ALL of the following per
run. If any is missing, real B16 cannot run and the skeleton emits
`insufficient_data` / `not_implemented`.

- `per_run_paired_arm_assignment`
- `per_run_agent_event_log`
- `per_run_patch_or_diff`
- `per_run_test_execution_result`
- `per_run_solve_label`
- `per_run_first_file_before_first_edit_event`
- `per_run_wrong_file_edit_annotation`
- `per_run_tool_calls_tokens_latency_cost`
- `per_run_isolated_fresh_workspace_proof`
- `per_run_randomized_arm_order`
- `per_run_no_cross_run_memory_proof`
- `per_task_oracle_or_hidden_test_manifest`

## Retrieval-vs-downstream boundary

The B10-B15 retrieval/context candidate research is **retrieval
research**; it does NOT prove downstream coding-agent value.

- B11 matrix deltas are retrieval deltas, NOT downstream solve-rate
  improvements.
- B12 mechanism decomposition is a retrieval mechanism screen, NOT a
  downstream agent mechanism proof.
- B13 policy search is a retrieval policy search, NOT a downstream
  agent policy.
- B14 uncertainty calibration is a retrieval calibration feasibility
  screen, NOT a downstream agent calibration.
- B15 PackPolicy is a retrieval/context pack-policy candidate, NOT a
  downstream agent improvement.

Retrieval improvements are NOT downstream agent improvements. B15
PackPolicy is NOT a downstream agent improvement. B16 is the ONLY
phase that can measure downstream agent value, and the B16 skeleton
does NOT do so.

## Safety invariants

```text
promotion_ready=false
default_should_change=false
evidencecore_semantics_changed=false
retrieval_variant_promoted=false
stage_is_downstream_agent_evaluation=true (B16 stage IS downstream agent evaluation)
downstream_agent_runs_performed=false (skeleton performs no live agent runs)
patch_execution_performed=false (skeleton performs no patch execution)
agent_behavior_metrics_evaluated=false (skeleton evaluates no agent behavior metrics)
solve_rate_evaluated=false (skeleton evaluates no solve rate)
per_record_inputs_available=false (skeleton; no real per-run inputs)
policy_search_performed=false
quality_strategy_tuned=false
new_provider_calls=0 (skeleton; no live LLM calls)
no_fake_downstream_metrics_from_retrieval_aggregates=true
aggregate_only_public_artifact=true
```

## What B16 does NOT prove

- B16 does **not** run live downstream agent runs.
- B16 does **not** execute patches.
- B16 does **not** evaluate agent-behavior metrics.
- B16 does **not** evaluate solve rate.
- B16 does **not** compute solve-rate / correct-file-before-first-edit
  / wrong-file-edits / tool-call / token / latency / cost metrics from
  retrieval aggregates.
- B16 does **not** promote any retrieval variant.
- B16 does **not** change any defaults.
- B16 does **not** change `EvidenceCore` semantics.
- B16 does **not** claim that retrieval improvements improve coding
  agents.
- B16 does **not** claim that B15 PackPolicy improves downstream
  agents.
- B16 results are research candidates only; a B16-frozen candidate
  retrieval variant is NOT a promoted retrieval variant and is NOT the
  new default until separately promoted via the standard promotion
  process.
- B16's `--input` path is a stub (`verdict="not_implemented"`); full
  downstream agent RCT is deferred to a later task.
- B10-B15 retrieval/context candidate research is **not** downstream
  agent value.

## Self-test (read-only) and explicit artifact regeneration

```bash
python3 eval/b16_downstream_agent_evaluation.py --self-test
python3 eval/b16_downstream_agent_evaluation.py --regenerate-artifacts
python3 eval/b16_downstream_agent_evaluation.py --self-test
python3 eval/b16_public_aggregate_feasibility_screen.py --self-test
python3 eval/b16_public_aggregate_feasibility_screen.py \
    --out artifacts/b16_downstream_agent_evaluation/b16_public_aggregate_feasibility_report.json
```

The `eval/b16_downstream_agent_evaluation.py --self-test` run is
**read-only**: it verifies the arm set, task types, metric registry,
hard gates, and experimental structure against a synthetic fixture
(definitions-only; no per-run paired agent outputs, no computed metric
values) and compares the in-memory expected algorithm spec + report to
the on-disk artifacts, **failing on drift**. It does NOT mutate
checked-in artifacts. It emits
`stage_is_downstream_agent_evaluation=true`,
`downstream_agent_runs_performed=false`,
`patch_execution_performed=false`,
`agent_behavior_metrics_evaluated=false`,
`solve_rate_evaluated=false`, `per_record_inputs_available=false`,
`promotion_ready=false`, `default_should_change=false`,
`evidencecore_semantics_changed=false`,
`retrieval_variant_promoted=false`,
`policy_search_performed=false`, `quality_strategy_tuned=false`,
`new_provider_calls=0`,
`no_fake_downstream_metrics_from_retrieval_aggregates=true`, so the
synthetic-fixture report is unambiguously NOT an empirical B16
downstream agent result.

The read-only self-test runs these checks:

1. `forbidden_scan` — forbidden public keys/values scan
2. `spec_hash_stable` — algorithm spec sha256 stability
3. `arm_set_closed` — primary / exploratory / debug arms are closed
   and mutually disjoint; control and treatment distinct
4. `task_types_closed` — 5 closed-set task types
5. `metric_registry` — 8 metric names defined; no aggregate-mean
   metrics
6. `hard_gates_defined` — feasibility / denominator / leakage /
   operational-parity / privacy / promotion-false gates defined
7. `experimental_structure_frozen` — 4 frozen stages; no feedback
8. `no_fake_downstream_metrics_from_retrieval_aggregates` — synthetic
   fixture has no per-run paired agent outputs and no metric values
9. `input_stub_not_implemented` — `--input` stub returns
   `not_implemented`
10. `reference_specs_pinned` — B10/B10B/B11/B12/B13/B14/B15 reference
    specs present on disk
11. `artifacts_match_in_memory` — read-only drift check: in-memory
    expected spec + report match the on-disk artifacts

`python3 eval/b16_downstream_agent_evaluation.py --regenerate-artifacts`
is the ONLY path that mutates checked-in artifacts: it (re)writes the
on-disk algorithm spec + synthetic-fixture report from the current
build functions. After mutating, re-run `--self-test` to confirm the
on-disk artifacts now match the in-memory expected objects (no drift).

The `--input` path is a non-canonical stub path: it requires an
explicit `--out` destination and refuses to write ANY path inside
`artifacts/b16_downstream_agent_evaluation/` (canonical report,
algorithm spec, or public-aggregate feasibility report). It can write a
temporary stub report for development, but it does not mutate
checked-in B16 artifacts.

The `eval/b16_public_aggregate_feasibility_screen.py --self-test` run
verifies the bounded public-aggregate feasibility / no-go screen
against a synthetic minimal B11 + B12 + B13 + B14 + B15 fixture. It
emits `verdict=no_go_public_aggregate_only` (or
`insufficient_data_public_aggregate_only`), with
`downstream_agent_runs_performed=false`,
`patch_execution_performed=false`,
`agent_behavior_metrics_evaluated=false`,
`solve_rate_evaluated=false`,
`per_record_inputs_available=false`,
`retrieval_variant_promoted=false`,
`full_b16_possible_from_public_artifacts=false`.

## Artifacts

- `artifacts/b16_downstream_agent_evaluation/b16_downstream_agent_evaluation.algorithm.json`
  (frozen spec; deterministic, stable sha256; regenerated only via
  `--regenerate-artifacts`)
- `artifacts/b16_downstream_agent_evaluation/b16_downstream_agent_evaluation_report.json`
  (synthetic-fixture self-test report, verdict `insufficient_data`;
  `downstream_agent_runs_performed=false`,
  `patch_execution_performed=false`,
  `agent_behavior_metrics_evaluated=false`,
  `solve_rate_evaluated=false`,
  `per_record_inputs_available=false`,
  `stage_is_downstream_agent_evaluation=true`,
  `no_fake_downstream_metrics_from_retrieval_aggregates=true`;
  no empirical per-run metric values)
- `artifacts/b16_downstream_agent_evaluation/b16_public_aggregate_feasibility_report.json`
  (bounded public-aggregate feasibility / no-go screen report;
  `verdict=no_go_public_aggregate_only` (or
  `insufficient_data_public_aggregate_only`);
  `full_b16_possible_from_public_artifacts=false`;
  carries forward B11 `partial_with_failure` and B12/B13/B14/B15
  no-go or screen-only statuses; aggregate-only, no raw event
  traces, paths, diffs, prompts/responses, hidden tests, or task IDs)

## What's autonomous vs. needs user action

### Autonomous (can be done now)

- B16 plan document (this file)
- B16 evaluator skeleton (`eval/b16_downstream_agent_evaluation.py`) +
  read-only `--self-test` (compares in-memory expected artifacts to
  on-disk artifacts, fails on drift) and explicit `--regenerate-artifacts`
  mutating path
- B16 frozen algorithm spec + synthetic-fixture report artifacts
- B16 bounded public-aggregate feasibility / no-go screen
  (`eval/b16_public_aggregate_feasibility_screen.py`) + self-test +
  `artifacts/b16_downstream_agent_evaluation/b16_public_aggregate_feasibility_report.json`
  (reads the published B11 matrix + B12/B13/B14/B15 public screens;
  emits `no_go_public_aggregate_only` /
  `insufficient_data_public_aggregate_only`; never claims downstream
  agent value, never computes a downstream metric from retrieval
  aggregates, never promotes a retrieval variant, never declares a
  winner)

### Needs per-run ephemeral paired agent outputs

- B16 real downstream agent evaluation requires paired live downstream
  agent runs, per-run agent event logs, per-run patches/diffs, per-run
  test execution results, per-run solve labels, per-run first-file-
  before-first-edit events, per-run wrong-file-edit annotations,
  per-run tool-call/token/latency/cost rows, per-run isolated fresh
  workspace proof, per-run randomized arm order, and a task oracle/
  hidden-test manifest. If those records are not yet produced, B16
  emits `insufficient_data` / `not_implemented`.

### Needs user review

- Results interpretation
- Decision to proceed to a real B16 empirical path (separate
  preregistration required)
- Decision to expand from the minimum viable task-type set to a
  larger set (separate preregistration required)

## Next steps after B16

- **B16 success** (future real B16 path): a frozen candidate retrieval
  variant improves solve rate on the fresh-validation split, all hard
  gates pass. Proceed via the standard promotion process; B16 success
  does NOT auto-promote.
- **B16 failure** (future real B16 path): no candidate retrieval variant
  meets the predeclared criteria. The current retrieval stack
  continues; no retrieval variant is promoted.
- **B16 partial** (future real B16 path): some task types improve, not
  all. Investigate task-type-conditional retrieval variants; possibly
  expand the task-type set in a separate B16B round (separate
  preregistration required).
- **B16 skeleton / no-go** (this commit): the bounded public-aggregate
  feasibility / no-go screen confirms real B16 cannot be performed
  from public aggregates alone. Real B16 requires ephemeral per-run
  paired agent outputs.
