# OpenLocus Current Research Conclusions

Date: 2026-06-20

Scope: R0-R45 through the B-series mechanism/policy work, C1-C4 external benchmark/readiness work, and Step 6 / D-series dual-rubric control-plane harnesses through the D4-series rollup.

Status: Research summary, not a promotion request.

## 2026-06-20 Historical State: C4 Readiness Complete; D4-Series Rollup Complete; D5-H Blocked

OpenLocus has now completed the C4 external benchmark readiness sequence and the
Step 6 / D-series dual-rubric control-plane sequence through the D4-series
rollup. The latest committed checkpoint is `b7c65dd` (`add D4 harness rollup`),
which records `claim_level=d4_series_harness_rollup_only` and
`status=d5_blocked_no_real_human_manual_labels`.

The C4 sequence established external benchmark readiness boundaries without
claiming benchmark performance: ContextBench schema and verified row-mapping
smokes, SWE-Explore row-mapping with a negative line-budget shape observation,
CORE-Bench source-readiness no-go, and RepoQA source/schema-contract readiness.
All public artifacts remain aggregate-only and do not persist raw benchmark rows,
labels, row-level hashes, paths, spans, prompts, responses, snippets, provider
payloads, or private identifiers.

The D-series sequence moved Step 6 dual-rubric relevance from deterministic
scaffold through proxy mappability, true-label protocol preregistration, and the
complete D4 control-plane chain:

```text
D4a execution gate / dry-run
-> D4b true-label bundle harness
-> D4c annotation packet builder harness
-> D4d human annotation runbook/checklist
-> D4e filled-packet -> D4b bundle converter harness
-> D4f D4b bundle validation / gate-check harness
-> D4-series rollup / D5 blocked status
```

This is control-plane readiness, not empirical true E/S calibration. The D4
rollup blocks only D5-H / human-reference calibration because no real
human/manual labels exist, no D4e real local conversion over real labels has run,
no D4f real local validation over real labels has run, and min-N/k/agreement/CI
gates have not passed for real labels. The D4 rollup states these human-reference
blockers explicitly in both flat fields and a nested `d5_prerequisites` object.
This historical control-plane state is superseded for ongoing automated research
by the D5-A0 empirical pivot below: lack of human/manual labels does not block the
automated/programmatic D5-A path.

Current no-claim state remains unchanged:

```text
promotion_ready=false
default_should_change=false
evidencecore_semantics_changed=false
runtime_clean_general_algorithm_claimed=false
downstream_agent_value_proven=false
true_e_s_calibration_claimed=false
external_benchmark_performance_claimed=false
d5_public_aggregate_candidate_allowed=false
```

Therefore this historical section should not be read as a global research stop.
It only prevents human-calibrated claims and runtime/default-policy changes. The
active next work is D5-A automated empirical calibration and downstream/external
benchmark experimentation, not another control-plane-only E1 preregistration.

## 2026-06-20 D5-A0 Automated E/S Calibration Smoke (Empirical Pivot)

Following the D4-series rollup, the trajectory was corrected: the
control-plane-only stages stop here, and D5-A0 produces the first empirical,
post-control-plane smoke. The D5-H / human-reference / human-calibrated audit
remains out of scope/unavailable until real human/manual true E/S labels are
collected; the D5-A automated/programmatic empirical path is active and
continues. D5-A0 derives **automated E labels** and **deterministic S-proxy
labels** from the existing committed r14 sanity span labels (gold spans + hard
negatives) over real OpenLocus retrieval outputs (regex, bm25, symbol, rrf),
invoking `eval/run_retrieval.py` into transient `/tmp` outputs (never
committed). The committed artifact is aggregate-only: no raw predictions, no
per-candidate rows, no paths/spans/snippets/hashes/queries/gold/hard-negative
labels are committed.

This is smoke-only. It does NOT claim true E/S calibration, does NOT collect
new human/manual labels, does NOT audit human reference labels, does NOT pass
any public-release gate, does NOT promote any candidate, and does NOT unblock
D5-H / human-reference / human-calibrated claims or default/policy/public-release
claims. The automated E/S labels are derived from existing committed span labels
(originally collected for span-recall metrics, not for true E/S rubric scoring);
they are NOT true human/manual E/S scores and are NOT the D3 dual-rubric E/S
scores. D5-A0 does not unlock default/policy/public release or human-calibrated
claims; the D5-H / human-reference / human-calibrated audit remains out of scope
until human labels. All no-claim / no-runtime-change flags remain false
(`promotion_ready=false`, `default_should_change=false`,
`retriever_changed=false`, `pack_builder_changed=false`,
`model_calls_changed=false`, `backend_changed=false`,
`default_policy_changed=false`, `evidencecore_semantics_changed=false`,
`runtime_clean_general_algorithm_claimed=false`,
`downstream_agent_value_proven=false`,
`external_benchmark_performance_claimed=false`,
`human_e_s_calibration_claimed=false`,
`automated_e_s_calibration_claimed=false`,
`d5_human_reference_calibration_unblocked=false`,
`automated_d5a_path_active=true`). No runtime/retriever/pack/model/
backend/default-policy files were modified. See the
[D5-A0 detailed report](d5a-automated-es-calibration.md).

## 2026-06-20 B16-A Minimal Mock Downstream Paired Run (Empirical Downstream-Agent Smoke)

Following D5-A0, B16-A produces the first B16-style downstream-agent
empirical run that is **not** control-plane-only. B16-A
(`eval/b16a_minimal_mock_agent_paired_run.py` ->
`artifacts/b16a_minimal_mock_agent_paired_run/b16a_minimal_mock_agent_paired_run_report.json`,
schema `b16a_minimal_mock_agent_paired_run.v1`,
`claim_level=deterministic_mock_downstream_paired_smoke_only`,
`status=mock_downstream_paired_smoke_pass`,
`mode=public_aggregate_synthetic_micro_tasks`, phase `B16-A`) generates
deterministic synthetic public micro bug tasks in code, creates a fresh
`/tmp` workspace per task+arm with real tiny Python modules + stdlib
tests, runs a **deterministic mock agent** (no live LLM, no provider
calls, no remote calls) that performs **real file edits** and runs
**real subprocess tests**, and computes aggregate behavior metrics over
paired control/treatment arms. The treatment pack causally alters the
mock agent's behavior (treatment solve_rate=1.0 vs control
solve_rate=0.0) for a designed subset.

This is smoke-only. It does NOT claim downstream agent value, does NOT
claim live agent generalization, does NOT claim external benchmark
performance, does NOT claim a real user task, does NOT promote any
candidate, and does NOT change runtime/retriever/pack/backend/
default-policy/EvidenceCore semantics. The per-run event logs,
patches, and test output stay under `/tmp` only and are NEVER committed
or uploaded. The committed artifact is aggregate-only: no task IDs,
workspace paths, file paths, source snippets, patches/diffs, test
output, raw event logs, per-run rows, private IDs, or provider/model
info beyond the deterministic mock identity. All no-claim /
no-runtime-change flags remain false (`live_llm_agent=false`,
`provider_calls_made=false`, `remote_calls_made=false`,
`downstream_agent_value_proven=false`, `promotion_ready=false`,
`default_should_change=false`, `runtime_behavior_changed=false`,
`retriever_changed=false`, `pack_builder_changed=false`,
`backend_changed=false`, `default_policy_changed=false`,
`evidencecore_semantics_changed=false`,
`external_benchmark_performance_claimed=false`,
`live_agent_generalization_claimed=false`,
`real_user_task_claimed=false`). The deterministic-mock-run flags
(`downstream_agent_runs_performed=true`,
`deterministic_mock_agent=true`, `synthetic_micro_tasks_used=true`,
`paired_arms_evaluated=true`, `real_file_edits_performed=true`,
`real_test_commands_executed=true`,
`agent_behavior_metrics_evaluated=true`,
`aggregate_only_public_artifact=true`, `diagnostic_only=true`) are the
only additional true flags. No runtime/retriever/pack/model/
backend/default-policy files were modified. The full B16
downstream-coding-agent evaluation phase remains a bounded planning /
feasibility stage that requires live paired agent runs with real
provider calls. See the
[B16-A detailed report](b16a-minimal-mock-agent-paired-run.md).

## 2026-06-21 B16-B Less-Separable Mock Downstream Paired-Agent Stress

Following B16-A, B16-B extends the deterministic/mock downstream
paired-agent empirical run from deliberately separable micro bugs to a
harder **less-separable multi-cue stress** task family. B16-B
(`eval/b16b_less_separable_mock_paired_run.py` ->
`artifacts/b16b_less_separable_mock_paired_run/b16b_less_separable_mock_paired_run_report.json`,
schema `b16b_less_separable_mock_paired_run.v1`,
`claim_level=deterministic_mock_downstream_paired_stress_only`,
`status=mock_downstream_paired_stress_pass`,
`mode=public_aggregate_synthetic_stress_tasks`, phase `B16-B`) generates
deterministic synthetic public less-separable stress tasks in code,
creates a fresh `/tmp` workspace per task+arm with real multi-file
Python modules (target.py with decoy symbol, distractor.py with same
symbol, support.py with offset constant, test_target.py) + stdlib
tests, runs a **deterministic mock agent** (no live LLM, no provider
calls, no remote calls) that performs **real file edits** and runs
**real subprocess tests**, and computes aggregate behavior metrics
over paired control_sparse/treatment_multi_cue arms. Solving requires
combining four cues (target_file + target_symbol + operation_hint +
support_relation); missing any cue causes a deterministic wrong
action. The treatment multi-cue pack causally alters the mock agent's
behavior (treatment solve_rate=1.0 vs control solve_rate=0.0).

This is stress-only. It does NOT claim downstream agent value, does NOT
claim live agent generalization, does NOT claim external benchmark
performance, does NOT claim a real user task, does NOT promote any
candidate, and does NOT change runtime/retriever/pack/backend/
default-policy/EvidenceCore semantics. It emits NO `winner`,
`best_arm`, `recommended_default`, `preferred_policy`, or `promotion`
recommendation field. The per-run event logs, patches, and test
output stay under `/tmp` only and are NEVER committed or uploaded.
The committed artifact is aggregate-only. All no-claim /
no-runtime-change flags remain false (`live_llm_agent=false`,
`provider_calls_made=false`,
`remote_provider_calls_made=false`,
`downstream_agent_value_proven=false`,
`live_agent_generalization_claimed=false`,
`promotion_ready=false`, `default_should_change=false`,
`runtime_behavior_changed=false`, `retriever_changed=false`,
`pack_builder_changed=false`, `backend_changed=false`,
`default_policy_changed=false`,
`evidencecore_semantics_changed=false`,
`external_benchmark_performance_claimed=false`). The
deterministic-mock-stress-run flags
(`downstream_agent_runs_performed=true`,
`deterministic_mock_agent=true`, `paired_run_executed=true`,
`real_file_edits_performed=true`,
`subprocess_tests_executed=true`,
`less_separable_stress_tasks=true`,
`aggregate_only_public_artifact=true`, `diagnostic_only=true`) are the
only additional true flags. No runtime/retriever/pack/model/
backend/default-policy files were modified. The full B16
downstream-coding-agent evaluation phase remains a bounded planning /
feasibility stage that requires live paired agent runs with real
provider calls. See the
[B16-B detailed report](b16b-less-separable-mock-paired-run.md).

## 2026-06-21 B16-C Live-Provider Downstream Paired Smoke (Empirical Live-Provider Pivot)

Following B16-A/B16-B (deterministic/mock), B16-C produces the first
**live-provider** B16-style downstream-agent empirical run. B16-C
(`eval/b16c_live_provider_paired_smoke.py` + shared
`eval/provider_client.py` ->
`artifacts/b16c_live_provider_paired_smoke/b16c_live_provider_paired_smoke_report.json`,
schema `b16c_live_provider_paired_smoke.v1`,
`claim_level=live_provider_downstream_paired_smoke_only`,
`mode=public_aggregate_synthetic_micro_tasks`, phase `B16-C`)
generates deterministic synthetic public micro bug tasks, creates a
fresh `/tmp` workspace per task+arm, runs a **live LLM agent**
(OpenAI-compatible) only when `--allow-remote` +
`OPENLOCUS_ALLOW_REMOTE=1` + provider env are all set, applies the
model's structured edit action locally (allowlisted `target.py` only;
actions `replace_return_value` / `no_op` only; no arbitrary paths, no
shell), runs real subprocess tests, and computes aggregate behavior
metrics over paired `control_sparse` / `treatment_context_pack` arms.

Manual CI run `27900913599` (`real-provider-benchmark`,
`stage=b16c_live_provider_paired_smoke`, `enable_remote_models=true`)
completed `status=live_provider_paired_smoke_pass`; the committed
artifact now mirrors that sanitized aggregate CI report. The run executed
2 synthetic tasks / 4 live provider calls, 4/4 calls succeeded,
invalid_json_count=0, and the workflow privacy validator passed. Both
arms solved both trivial micro tasks (`control_sparse` solve_rate=1.0;
`treatment_context_pack` solve_rate=1.0), so the
treatment-minus-control solve-rate delta is 0.0. The default local
no-env path remains truthful (`blocked_remote_not_enabled` /
`unavailable_no_local_provider_env`) when remote opt-in/provider env are
not available.

This is smoke-only. It does NOT claim downstream agent value, does NOT
claim live agent generalization, does NOT claim external benchmark
performance, does NOT claim a real user task, does NOT promote any
candidate, and does NOT change runtime/retriever/pack/backend/
default-policy/EvidenceCore semantics. Per-run prompts, responses,
event logs, patches, and test output stay under `/tmp` only and are
NEVER committed or uploaded. The committed artifact is aggregate-only
with records-shaped `arm_results` and `paired_deltas`. All no-claim /
no-runtime-change flags remain false
(`downstream_agent_value_proven=false`,
`live_agent_generalization_claimed=false`, `promotion_ready=false`,
`default_should_change=false`,
`external_benchmark_performance_claimed=false`,
`real_user_task_claimed=false`, `runtime_behavior_changed=false`,
`retriever_changed=false`, `pack_builder_changed=false`,
`backend_changed=false`, `default_policy_changed=false`,
`evidencecore_semantics_changed=false`). Live-run flags are true ONLY
when a live run actually executed; otherwise false. No raw model
routing prefix is emitted; only the normalized
`model_display_category` is recorded. No runtime/retriever/pack/model/
backend/default-policy files were modified. The B16-C upload surface is
dedicated to the sanitized aggregate report only; generic `real-provider`
artifacts such as `plan.json` are excluded from the B16-C artifact
upload. The full B16 downstream-coding-agent evaluation phase remains a
bounded planning / feasibility stage. See the
[B16-C detailed report](b16c-live-provider-paired-smoke.md).

## 2026-06-21 B16-D Less-Trivial Live-Provider Downstream Paired Smoke (Harder Live Smoke)

Following B16-C, B16-D is a harder live-provider paired smoke with a
less-trivial synthetic public task family. B16-D
(`eval/b16d_less_trivial_live_provider_paired_smoke.py`, reusing
`eval/provider_client.py` from B16-C) ->
`artifacts/b16d_less_trivial_live_provider_paired_smoke/b16d_less_trivial_live_provider_paired_smoke_report.json`,
schema `b16d_less_trivial_live_provider_paired_smoke.v1`,
`claim_level=less_trivial_live_provider_downstream_paired_smoke_only`,
`mode=public_aggregate_synthetic_less_trivial_tasks`, phase `B16-D`)
generates deterministic less-trivial multi-file tasks (target.py +
distractor.py + support.py + test_target.py; same-symbol distractor;
support relation required), creates a fresh `/tmp` workspace per
task+arm, runs a **live LLM agent** (OpenAI-compatible) only when
`--allow-remote` + `OPENLOCUS_ALLOW_REMOTE=1` + provider env are all
set, applies the model's structured edit action locally (allowlisted
`target.py` only; actions `replace_return_value` /
`choose_helper_constant` / `no_op`; distractor/support NOT editable),
runs real subprocess tests, and computes aggregate behavior metrics
over paired `control_sparse` / `treatment_context_pack` arms. Treatment
includes target file cue, target symbol cue, support-relation cue,
and exact edit constraint; control lacks the decisive cues.

Manual CI run `27901644438` (`real-provider-benchmark`,
`stage=b16d_less_trivial_live_provider_paired_smoke`,
`enable_remote_models=true`) completed
`live_provider_less_trivial_paired_smoke_pass` and passed privacy
validation. The committed artifact now mirrors that sanitized aggregate
CI report: 4 synthetic tasks / 8 live provider calls, 8/8 provider
calls succeeded, invalid JSON count 0, control solve_rate=0.5,
treatment solve_rate=1.0, treatment-minus-control solve_rate delta
`+0.5`, tests_pass_rate delta `+0.5`, and
`context_pack_signal_observed=true`. The default local no-provider-env
path remains truthful (`blocked_remote_not_enabled` with live-run flags
false).

This is smoke-only. It does NOT claim downstream agent value, does NOT
claim live agent generalization, does NOT claim external benchmark
performance, does NOT claim a real user task, does NOT promote any
candidate, and does NOT change runtime/retriever/pack/backend/
default-policy/EvidenceCore semantics. CI pass means live run
completed + privacy scan passed + artifact is honest; CI pass does NOT
require treatment improvement (zero/negative delta is valid). Per-run
prompts, responses, event logs, patches, and test output stay under
`/tmp` only and are NEVER committed or uploaded. Honest signal fields
(`context_pack_signal_observed`, `treatment_solve_rate_delta`,
`treatment_wrong_file_edits_delta`) are diagnostic smoke outcomes only,
NEVER promotion/default/value claims. All no-claim /
no-runtime-change flags remain false. Live-run flags are true ONLY when
a live run actually executed; otherwise false. No raw model routing
prefix is emitted; only the normalized `model_display_category` is
recorded. No runtime/retriever/pack/model/backend/default-policy files
were modified. The positive treatment delta is a tiny synthetic smoke
signal, not proof of downstream value or generalization. The full B16 downstream-coding-agent evaluation phase
remains a bounded planning / feasibility stage. See the
[B16-D detailed report](b16d-less-trivial-live-provider-paired-smoke.md).

## 2026-06-21 B16-E Broader Live-Provider Downstream Paired Smoke (Task-Family Matrix)

Following B16-D, B16-E broadens the live-provider paired smoke into a
heterogeneous synthetic task-family matrix with four fixed families.
B16-E
(`eval/b16e_broader_live_provider_paired_smoke.py`, reusing
`eval/provider_client.py`) ->
`artifacts/b16e_broader_live_provider_paired_smoke/b16e_broader_live_provider_paired_smoke_report.json`,
schema `b16e_broader_live_provider_paired_smoke.v1`,
`claim_level=broader_live_provider_downstream_paired_smoke_only`,
`mode=public_aggregate_synthetic_task_family_matrix`, phase `B16-E`)
generates 8 deterministic tasks across four families
(`same_symbol_support_relation`, `operation_ambiguity`,
`boundary_condition`, `helper_dependency_choice`), creates a fresh
`/tmp` workspace per task+arm, runs a **live LLM agent**
(OpenAI-compatible) only when `--allow-remote` +
`OPENLOCUS_ALLOW_REMOTE=1` + provider env, applies the model's
structured edit action locally (allowlisted `target.py` only), runs
real subprocess tests, and computes aggregate behavior metrics +
family-level records over paired `control_sparse` /
`treatment_context_pack` arms.

Manual CI run `27902925812` (`real-provider-benchmark`,
`stage=b16e_broader_live_provider_paired_smoke`,
`enable_remote_models=true`) completed
`broader_live_provider_paired_smoke_pass` and passed privacy
validation. The committed artifact now mirrors that sanitized aggregate
CI report: 8 synthetic tasks / 16 live provider calls; 16/16 provider
calls succeeded; invalid JSON count 0; forbidden scan pass;
control_sparse solve_rate=0.125 and tests_pass_rate=0.125;
treatment_context_pack solve_rate=1.0 and tests_pass_rate=1.0;
treatment-minus-control solve/test delta `+0.875`; 4/4 families had
positive solve-rate delta; `context_pack_signal_observed=true`.

This is smoke-only. It does NOT claim downstream agent value, does NOT
claim live agent generalization, does NOT claim external benchmark
performance, does NOT claim a real user task, does NOT promote any
candidate, and does NOT change runtime/retriever/pack/backend/
default-policy/EvidenceCore semantics. CI pass means live run
completed + privacy scan passed + artifact is honest; CI pass does NOT
require treatment improvement (zero/negative delta is valid).
`honest_signals` and `family_signal_summary` are diagnostic smoke
outcomes only, NEVER promotion/default/value claims. All no-claim /
no-runtime-change flags remain false. Live-run flags are true ONLY when
a live run actually executed; otherwise false. No raw model routing
prefix is emitted; only the normalized `model_display_category` is
recorded. No runtime/retriever/pack/model/backend/default-policy files
were modified. See the
[B16-E detailed report](b16e-broader-live-provider-paired-smoke.md).

## 2026-06-21 F1-B Retrieval-Derived Counterfactual Utility Smoke

F1-B moves F1 from purely synthetic context variants to
**retrieval-derived** counterfactual utility. F1-B
(`eval/f1b_retrieval_derived_counterfactual_utility_smoke.py`,
importing C5-A helpers backward-compatibly) ->
`artifacts/f1b_retrieval_derived_counterfactual_utility/f1b_retrieval_derived_counterfactual_utility_report.json`,
schema `f1b_retrieval_derived_counterfactual_utility_smoke.v1`,
`claim_level=retrieval_derived_counterfactual_utility_smoke_only`,
`mode=public_aggregate_contextbench_retrieval_counterfactual`, phase
`F1-B`) uses real ContextBench verified rows, transient /tmp repo
clones, real OpenLocus retrieval (bm25,regex,symbol), and
`eval/score.py` metrics to compute aggregate counterfactual
candidate-set utility deltas. Five variants and four effects; metrics
are `file_recall@10`, `mrr`, `span_f0.5@10`, `success_rate`.
Records-shaped only; no dynamic dict mirrors; no winner/best/default
fields; no E/S calibration notation. No provider calls.
Manual CI run `27903995230` passed: 5 rows fetched/successful,
forbidden scan pass, `bm25_topk` file_recall@10=0.4 / mrr=0.225 /
span_f0.5@10=0.015905 / success_rate=1.0, `regex_topk` and
`symbol_topk` file_recall@10=0.0, and `symbol_added_to_bm25` delta=0.0.

This is smoke-only. It is NOT downstream utility, NOT true E/S
calibration, NOT an external benchmark performance claim, NOT a
leaderboard entry, NOT a promotion/default/runtime/retriever/pack/
backend/EvidenceCore semantic change. All no-claim /
no-runtime-change flags remain false.
`retrieval_derived_counterfactual_utility_smoke=true` only when a real
network run actually executed. See the
[F1-B detailed report](f1b-retrieval-derived-counterfactual-utility.md).

## 2026-06-21 D5-A2 Heldout Feature Validation Smoke

D5-A2 validates whether D5-A1's retrieval-derived feature bucket
reproduces on fresh heldout external retrieval samples. D5-A2
(`eval/d5a2_heldout_feature_validation.py`) ->
`artifacts/d5a2_heldout_feature_validation/d5a2_heldout_feature_validation_report.json`,
schema `d5a2_heldout_feature_validation.v1`,
`claim_level=heldout_retrieval_feature_validation_smoke_only`, phase
`D5-A2`) loads the D5-A1 committed artifact as preregistered feature
source (fail-closed), runs fresh heldout ContextBench rows 21-40 +
RepoQA needles 11-20 with bm25/regex/symbol, computes the same fixed
retrieval-derived utility proxy, and checks 4 retrieval-feature
validations (bm25_vs_empty magnitude/sign stability; regex/symbol
vs_bm25 sign stability). 88/88 self-test checks pass. Local heldout run
and manual CI run `27915252367` passed: status `heldout_feature_validation_pass`,
`validation_outcome=retrieval_feature_validation_supported`, 20 rows
fetched, 10 needles seen, all 4 features reproduce on heldout data
(bm25_vs_empty heldout +0.727961 positive; bm25 sign stability heldout
file_recall +0.6 positive; regex/symbol_vs_bm25 heldout -0.977961
negative). The heldout bm25 file_recall@10=0.7 on ContextBench (vs
0.35 on original rows 1-20) supports the bm25 positive retrieval
feature on this heldout slice.

This is heldout feature validation, NOT calibration. It is NOT
calibration, NOT a calibrated model claim, NOT a policy/default
recommendation, NOT a benchmark result, NOT downstream utility, NOT
true E/S calibration, NOT an external benchmark performance claim, NOT
a leaderboard entry, NOT a method winner, NOT a promotion/default/
runtime/retriever/pack/backend/EvidenceCore semantic change. It
validates only retrieval-feature stability from D5-A1; it does NOT
validate live-provider/downstream alignment. All no-claim /
no-runtime-change flags remain false. See the
[D5-A2 detailed report](d5a2-heldout-feature-validation.md).

## 2026-06-21 D5-A1 Automated Calibration Feature Table

D5-A1 moves from empirical smokes to **calibration-ready weak-
supervision features** by machine-reading committed aggregate
artifacts. D5-A1
(`eval/d5a1_automated_calibration_feature_table.py`, reusing F1-D
scanner primitives backward-compatibly; none modified) ->
`artifacts/d5a1_automated_calibration_feature_table/d5a1_automated_calibration_feature_table_report.json`,
schema `d5a1_automated_calibration_feature_table.v1`,
`claim_level=automated_calibration_feature_extraction_only`,
`status=automated_calibration_feature_table_pass|fail_input_contract|fail_forbidden_scan`,
`mode=committed_aggregate_feature_extraction`, phase `D5-A1`)
machine-reads committed aggregate artifacts (F1-D, F1-C, C5-C, C5-F,
B16-E required; D5-A0, B16-D optional if present and claim-safe),
validates their schemas and claim flags fail-closed, extracts numeric
aggregate signals (retrieval robustness from F1-D; external benchmark
agreement/disagreement from C5-C+C5-F; live provider delta from
B16-E), and computes deterministic calibration feature/bucket records
and readiness buckets (`ready_for_manual_review`,
`needs_more_live_downstream`, `retrieval_only_insufficient`,
`conflicting_signals`, `insufficient_signal`). Recommended next
measurements are measurement-only (`manual_reference_audit`,
`heldout_benchmark_scale`, `live_downstream_scale`), NOT policy/
default/method winner. Records-shaped lists only; no per-unit metric
arrays, no raw input artifact paths/content, no B16 task text, no
winner/best/default/calibrated-model/policy-recommendation fields, no
E/S calibration notation. 126/126 self-test checks pass. Local feature
extraction run passed: status
`automated_calibration_feature_table_pass`, forbidden scan pass, 7
input artifacts loaded (5 required + 2 optional), 9 signals, 7
features, 5 bucket records, 2 measurements;
cross_signal_alignment=`retrieval_robust_positive_plus_live_positive`,
readiness_bucket=`ready_for_manual_review`.

This is feature extraction only, NOT calibration. It is NOT
calibration, NOT a calibrated model claim, NOT a policy/default
recommendation, NOT a benchmark result, NOT downstream utility, NOT
true E/S calibration, NOT an external benchmark performance claim, NOT
a leaderboard entry, NOT a method winner, NOT a formal confidence
interval, NOT a promotion/default/runtime/retriever/pack/backend/
EvidenceCore semantic change. All no-claim / no-runtime-change flags
remain false. `automated_calibration_feature_extraction_performed=true`
only when feature extraction actually executed. See the
[D5-A1 detailed report](d5a1-automated-calibration-feature-table.md).

## 2026-06-21 F1-D Cross-Benchmark Retrieval Utility Robustness Smoke

F1-D extends F1-C from point estimates to **diagnostic paired-bootstrap
confidence/sign-stability estimates**. F1-D
(`eval/f1d_cross_benchmark_retrieval_robustness.py`,
reusing F1-C/C5-C/C5-E/C5-A/C5-D primitives backward-compatibly; none
modified) ->
`artifacts/f1d_cross_benchmark_retrieval_robustness/f1d_cross_benchmark_retrieval_robustness_report.json`,
schema `f1d_cross_benchmark_retrieval_robustness.v1`,
`claim_level=cross_benchmark_retrieval_utility_robustness_smoke_only`,
`status=cross_benchmark_retrieval_robustness_pass|partial|unavailable_with_reason|fail_forbidden_scan|fail_schema_contract`,
`mode=bounded_contextbench_repoqa_retrieval_robustness`, phase `F1-D`)
**reruns real bounded external data** for two benchmarks
(ContextBench verified 20-row + RepoQA 10-needle Python), intercepts
per-unit score metrics **before aggregation** (in memory or `/tmp`
only), computes a fixed retrieval-derived utility proxy
(`utility = file_recall@10 + 0.25*mrr + 0.5*span_f0.5@10 - miss_penalty`
where `miss_penalty=0.25 if file_recall@10 == 0 else 0`; unchanged
from F1-C), cross-benchmark weighted means (by sample counts), and
paired bootstrap confidence/sign-stability statistics for 5 fixed
effects (`bm25_vs_empty`, `regex_vs_empty`, `symbol_vs_empty`,
`regex_vs_bm25`, `symbol_vs_bm25`) over 5 metrics
(`file_recall@10`, `mrr`, `span_f0.5@10`, `success_rate`,
`retrieval_utility`) = 25 bootstrap effect records.
`empty_retrieval` is the explicit zero-context baseline (no retrieval
run; all metrics/utility 0). Cross-benchmark resampling preserves
benchmark sample counts (ContextBench 20, RepoQA 10). Records-shaped
only (`benchmark_method_means`, `cross_benchmark_method_means`,
`bootstrap_effect_records`, `input_summary`, `bootstrap_summary`); no
dynamic dict mirrors; no per-unit metric arrays; no F1-C container
names; no winner/best/default fields; no E/S calibration notation;
ContextBench and RepoQA failure categories kept separate. No provider
calls. Bootstrap replicates default 1000 (hard cap 2000), fixed seed
20240621. 185/185 self-test checks pass. Local real-network run
passed: 20 ContextBench rows fetched, 10 RepoQA needles seen, status
`cross_benchmark_retrieval_robustness_pass`, forbidden scan pass,
provider_calls=0, bootstrap_record_count=25; point estimates match
F1-C deltas (`bm25_vs_empty` retrieval_utility = +0.465035,
`regex_vs_bm25` = -0.715035); `bm25_vs_empty` retrieval_utility
bootstrap CI=[+0.298938, +0.464512, +0.624026], sign_positive=1.0;
`regex_vs_bm25` retrieval_utility CI=[-0.874026, -0.714511,
-0.548938], sign_negative=1.0.

This is smoke-only. The bootstrap statistics are diagnostic robustness
estimates, NOT formal external benchmark confidence intervals. It is
NOT downstream utility, NOT true E/S calibration, NOT an external
benchmark performance claim, NOT a leaderboard entry, NOT a method
winner, NOT a formal confidence interval, NOT a promotion/default/
runtime/retriever/pack/backend/EvidenceCore semantic change. All
no-claim / no-runtime-change flags remain false.
`retrieval_utility_robustness_smoke=true` and `bootstrap_computed=true`
only when a real network run actually executed. See the
[F1-D detailed report](f1d-cross-benchmark-retrieval-robustness.md).

## 2026-06-21 F1-C Cross-Benchmark Retrieval-Derived Utility Smoke

F1-C is the **cross-benchmark** retrieval-derived utility smoke. F1-C
(`eval/f1c_cross_benchmark_retrieval_utility.py`,
reusing C5-C/C5-E/C5-A/C5-D primitives backward-compatibly; none
modified) ->
`artifacts/f1c_cross_benchmark_retrieval_utility/f1c_cross_benchmark_retrieval_utility_report.json`,
schema `f1c_cross_benchmark_retrieval_utility.v1`,
`claim_level=cross_benchmark_retrieval_derived_utility_smoke_only`,
`mode=bounded_contextbench_repoqa_retrieval_utility`, phase `F1-C`)
**reruns real bounded external data** for two benchmarks
(ContextBench verified 20-row + RepoQA 10-needle Python) and computes a
fixed retrieval-derived utility proxy
(`utility = file_recall@10 + 0.25*mrr + 0.5*span_f0.5@10 - miss_penalty`
where `miss_penalty=0.25 if file_recall@10 == 0 else 0`) per
benchmark/method, cross-benchmark weighted means (by sample counts),
and 5 fixed counterfactual effects (`bm25_vs_empty`,
`regex_vs_empty`, `symbol_vs_empty`, `regex_vs_bm25`,
`symbol_vs_bm25`). `empty_retrieval` is the explicit zero-context
baseline (no retrieval run; all metrics/utility 0). Records-shaped
only; no dynamic dict mirrors; no winner/best/default fields; no E/S
calibration notation; ContextBench and RepoQA failure categories kept
separate. No provider calls. Local real-network run and manual CI run `27911651758` passed: 20
ContextBench rows fetched, 10 RepoQA needles seen, status
`cross_benchmark_retrieval_utility_pass`, forbidden scan pass,
provider_calls=0; bm25 cross-benchmark weighted-mean
file_recall@10=0.4 / mrr=0.218477 / span_f0.5@10=0.020831 /
success_rate=1.0 / retrieval_utility=0.465035; `bm25_vs_empty`
retrieval_utility delta=+0.465035; `regex_vs_bm25` and
`symbol_vs_bm25` retrieval_utility delta=-0.715035.

This is smoke-only. It is NOT downstream utility, NOT true E/S
calibration, NOT an external benchmark performance claim, NOT a
leaderboard entry, NOT a method winner, NOT a promotion/default/
runtime/retriever/pack/backend/EvidenceCore semantic change. All
no-claim / no-runtime-change flags remain false.
`retrieval_derived_counterfactual_utility_smoke=true` only when a
real network run actually executed. See the
[F1-C detailed report](f1c-cross-benchmark-retrieval-utility.md).

## 2026-06-21 F1 Counterfactual Evidence Utility Smoke

Following D5-A0, B16-A, and C5-A, F1 produces the first counterfactual
evidence utility smoke. F1
(`eval/f1_counterfactual_evidence_utility_smoke.py` ->
`artifacts/f1_counterfactual_evidence_utility/f1_counterfactual_evidence_utility_report.json`,
schema `f1_counterfactual_evidence_utility_smoke.v1`,
`claim_level=counterfactual_evidence_utility_smoke_only`,
`status=counterfactual_evidence_utility_smoke_pass`,
`mode=public_aggregate_synthetic_micro_tasks`, phase `F1`) generates
deterministic synthetic public micro bug tasks in code, creates a
fresh `/tmp` workspace per task+variant with real tiny Python modules
+ stdlib tests, runs a **deterministic mock agent** (no live LLM, no
provider calls, no remote calls) that performs **real file edits** and
runs **real subprocess tests** under **six counterfactual context
variants** (`base_no_context`, `primary_only`, `support_only`,
`primary_plus_support`, `distractor_only`, `primary_plus_distractor`),
computes aggregate behavior metrics per variant, and computes **five
marginal utility deltas** from aggregate variant metrics
(`primary_context_vs_base`, `support_context_vs_base`,
`distractor_context_vs_base`, `support_added_to_primary`,
`distractor_added_to_primary`). The deltas are causal-shaped (variant
vs variant) and use utility-specific names that deliberately avoid
`E_primary` / `S_support` field-name shape. A `theory_mapping` block
records that `primary_context_vs_base` corresponds to an E-utility
smoke proxy and `support_added_to_primary` /
`distractor_added_to_primary` correspond to S-conditional utility smoke
proxies, but F1 is explicitly NOT true E/S calibration
(`true_e_s_calibration_claimed=false`,
`automated_e_s_full_calibration_claimed=false`,
`human_e_s_calibration_claimed=false`). 162/162 self-test checks pass;
24 tasks; 6 variants; 144 total runs.

This is smoke-only. It does NOT claim downstream agent value, does NOT
claim live agent generalization, does NOT claim external benchmark
performance, does NOT claim a real user task, does NOT claim true E/S
calibration, does NOT promote any candidate, and does NOT change
runtime/retriever/pack/backend/default-policy/EvidenceCore semantics.
The per-run event logs, patches, and test output stay under `/tmp` only
and are NEVER committed or uploaded. The committed artifact is
aggregate-only. All no-claim / no-runtime-change flags remain false
(`live_llm_agent=false`, `provider_calls_made=false`,
`remote_provider_calls_made=false`,
`downstream_agent_value_proven=false`, `promotion_ready=false`,
`default_should_change=false`, `runtime_behavior_changed=false`,
`retriever_changed=false`, `pack_builder_changed=false`,
`backend_changed=false`, `default_policy_changed=false`,
`evidencecore_semantics_changed=false`,
`external_benchmark_performance_claimed=false`,
`live_agent_generalization_claimed=false`,
`real_user_task_claimed=false`,
`true_e_s_calibration_claimed=false`,
`automated_e_s_full_calibration_claimed=false`,
`human_e_s_calibration_claimed=false`). The deterministic-mock-run
flags (`counterfactual_context_variants_executed`,
`deterministic_mock_agent`, `real_file_edits_performed`,
`subprocess_tests_executed`, `marginal_utility_metrics_computed`,
`aggregate_only_public_artifact`, `diagnostic_only`) are the only
additional true flags. No runtime/retriever/pack/model/
backend/default-policy files were modified. See the
[F1 detailed report](f1-counterfactual-evidence-utility.md).

## P52A Source Materialization / Local Verifier Prerequisite

P52A reads local source files only for bounded aggregate materialization prerequisite diagnostics. It stores no raw source, snippets, digests, paths, or spans. Source read is not Evidence, and materialized candidate is not Evidence. P52A does not validate EvidenceCore and does not produce verifier pass/fail or default/promotion claims. See the [P52A detailed report](p52a-source-materialization-prerequisite.md).

## P52B Source-Backed Local Verifier Feature Matrix

P52B reads local source files only for bounded aggregate source-shape heuristic diagnostics and source-feature risk buckets. It computes deterministic source-backed verifier feature diagnostics from bounded spans, using source-shape heuristics only and marking AST/query-dependent features as unavailable. P52B stores no raw source, snippets, digests, paths, or spans. Source-feature buckets are diagnostic only; they are not Evidence and do not admit candidates. P52B does not validate EvidenceCore, does not produce a verifier pass/fail score or a local verifier score, does not prove P51 quality, and does not send source to providers. It does not call an LLM, construct prompts, or make remote calls. See the [P52B detailed report](p52b-source-backed-local-verifier-feature-matrix.md).

## P52C Diagnostic Local Verifier Scoring Simulator

P52C is a deterministic, gold-free diagnostic scoring simulator over P52B/P52A/P52/P49/P48 features. It computes fixed diagnostic score buckets and aggregate retrospective correlations using bounded source-backed features when available and metadata-only fallback when source reads are unavailable. P52C does not produce a verifier pass/fail, evidence validity, admission/default/promotion, or quality-over-P25 claim. It emits only aggregate buckets (`diagnostic_score_high`, `diagnostic_score_medium`, `diagnostic_score_low`, `diagnostic_score_unavailable`) and binned score distributions, never raw candidate scores. Gold spans and outcomes are used only inside the explicitly-marked `score_phase_diagnostic_correlation` after score buckets are fixed. See the [P52C detailed report](p52c-local-verifier-scoring-simulator.md).

## P51 LLM Span Narrow 2.0 / Candidate Filter Diagnostic

P51 first tranche is a deterministic, no-LLM, no-remote, no-prompt-construction diagnostic scaffold. It selects candidate pools for a future span-narrow/filter/abstain phase using aggregate metadata, public task bucket/risk tags, and P49 contrast-pack feasibility only; P47/P48 RMC overlay availability is reported separately. It publishes prompt-blueprint metadata (pack shapes, source-line/context-char budgets, strategy/path-kind/risk-bucket mixes) and never constructs raw prompts. Existing P21 role outcomes are replayed only after selection and only when present; missing outcomes are reported as unavailable. P51 does not create Evidence, validate EvidenceCore, admit candidates, or change defaults. See the [P51 detailed report](p51-llm-span-narrow-2-diagnostic.md).

## P51-B LLM Opt-In Contract / Dry-Run Payload Validator

P51-B defines and dry-validates a future live LLM opt-in contract without provider calls, prompt construction, or persistent raw payloads.
 It computes aggregate eligibility and request-envelope blueprint metadata from P51 selection, P49 candidate metadata, and P52C source-backed availability, and validates synthetic role-output schemas fail-closed (`not_evidence=true`, role enum, no unknown fields, bounded candidate ref/line delta). Public artifacts contain no prompts, responses, snippets, source text, queries, paths, spans, digests, providers, models, or keys. `remote_calls_by_p51b=0`, `llm_calls_by_p51b=0`, `remote_requests_by_p51b=0`, `prompt_construction_by_p51b=false`, `dry_run_payload_validation_only=true`. It is not Evidence, not quality evidence, and not a live/default/promotion gate. See the [P51-B detailed report](p51b-llm-opt-in-contract.md).

## P51-C0 Live LLM Micro-Run Planner / Explicit Opt-In Gate

P51-C0 is a planner-only, explicit opt-in gate that validates whether a future P51-C live LLM micro-run may be manually launched. It consumes only the aggregate P61 pre-spend gate report and P51-B dry-run opt-in contract, performs no provider calls, constructs no prompts, reads no source, admits no Evidence, changes no defaults, and authorizes no spend. It requires an explicit `--p51c-live-opt-in` flag, a matching `I_UNDERSTAND_P51C_NOT_EVIDENCE` acknowledgement, `dataset=ci_smoke`, a repo in the public allowlist, a supported output mode (`json_schema_strict` or `tool_call`), P61 `micro_run_preconditions_met` with provider spend and authorization flags false, and a ready P51-B contract with source-backed eligibility, schema validity, redaction preconditions satisfied, and budget caps respected. It publishes only aggregate planning/gate information, using `repo_scope='public_ci_smoke_allowlist'` and never exposing raw repo identity, paths, spans, prompts, responses, providers, models, URLs, or keys. `remote_calls_by_p51c=0`, `llm_calls_by_p51c=0`, `remote_requests_by_p51c=0`, `prompt_construction_by_p51c=false`, `p51c_live_calls_disabled=true`, `provider_spend_authorized=false`, `live_run_authorized=false`. It is not Evidence, not quality evidence, not authorization, and not a live/default/promotion gate. See the [P51-C0 detailed report](p51c-live-micro-run-planner.md).

## P57 Generalization Gate v0

P57 is a deterministic, no-live-LLM, no-provider aggregate-only generalization-readiness gate that runs after P51B. It consumes only existing aggregate report JSON (P46, P47, P48, P49, P50, P52, P52A, P52B, P52C, optional P51, required P51B) and verifies upstream safety flags, completeness, and availability. It does not read source files, candidate pools, prompts, responses, or provider configs, and it publishes no paths, identifiers, spans, digests, or keys. For single-slice/self-test runs P57 reports `insufficient_matrix` by design; it is not quality evidence, not a promotion/default gate, and not live-readiness evidence. See the [P57 detailed report](p57-generalization-gate.md).

## P58 Source-Backed Verifier Calibration v0

P58 is a deterministic, no-live-LLM, no-provider aggregate-only calibration report that runs after P57. It consumes only the existing aggregate JSON from P48, P52C, P51B, and P57 (and optionally P52B/P52A/P49) and turns upstream availability/distributions into coarse planning/action-hint buckets. It is not a verifier, not admission, not Evidence, not default/promotion, and not live readiness. It does not read source files, candidate pools, tasks, prompts, responses, repo locks, or provider configs, and it emits only aggregate counts, rates, and calibration buckets. See the [P58 detailed report](p58-source-backed-verifier-calibration.md).

## P59 Contrastive Pack Coverage & Counterfactual Study v0

P59 is a deterministic, no-live-LLM, no-provider, aggregate-only pre-spend diagnostic that runs after P58. It rebuilds P49 contrastive candidate packs in memory from the same ephemeral P25 records and measures whether the frozen packs contain the prerequisite contrastive information a later LLM role would need, before any LLM spend. It is not a quality evaluator, not admission, not Evidence, not default/promotion, and not live readiness. Pack construction is gold-free and uses only candidate metadata; private labels are loaded only after packs are frozen, inside the explicitly-marked `score_phase_gold_coverage` block. It does not read source files, construct prompts, or call providers. See the [P59 detailed report](p59-contrastive-pack-coverage-counterfactual.md).

## P60 RMC Policy v2 v0

P60 is a deterministic, no-live-LLM, no-provider, aggregate-only diagnostic policy COMPARISON layer that advances `request_more_context` (RMC) from P47/P48 geometry/overlay into a comparable policy matrix. For the same frozen candidate/task inputs, each policy selects only the NEXT diagnostic action; P60 reports aggregate routing counts plus SCORE-phase gold reach / false cost diagnostics and labeled cost/latency ESTIMATES. RMC is not evidence/admission/default. P60 declares NO winner and recommends NO default. See the [P60 detailed report](p60-rmc-policy-v2.md).

## P61 Pre-Spend Gate v0

P61 is a deterministic, no-live-LLM, no-provider, aggregate-only pre-spend readiness gate that runs after P60. It consumes only existing aggregate reports (P57, P58, P59, P60, P51-B required; P52C optional) and emits a precondition-readiness decision about whether a future P51-C live LLM micro-run is worth considering. P61 does not call providers, construct prompts, read source/ephemeral records, admit Evidence, change defaults, promote, or authorize provider spend. It only reports preconditions; opening a live run remains a separate explicit workflow_dispatch or human decision. For single-slice/self-test runs, P61 reports `insufficient_inputs` or `self_test_only` by design. It is not quality evidence, not a promotion/default gate, and not live-readiness authorization. See the [P61 detailed report](p61-pre-spend-gate.md).

## P62 Generalization Matrix Aggregator v0

P62 is a deterministic, no-live-LLM, no-provider, aggregate-only generalization matrix aggregator that runs after P61. It consumes only the published aggregate reports from multiple slices (P57, P58, P59, P60, P51-B required) and combines each slice's aggregate report set into a >=4 distinct-slice generalization matrix. P62 does not read source files, gold labels, private labels, ephemeral records, candidate pools, prompts, responses, or provider configs; it does not call providers, construct prompts, admit Evidence, change defaults, or authorize provider spend. P62 builds a canonical sanitized summary per eligible slice and uses an internal SHA-256 signature to deduplicate slices so that the same slice repeated four times cannot inflate `slice_count`. P62 publishes only counts (`content_distinct_input_count`, `duplicate_input_count`, `eligible_distinct_slice_count`, `exact_duplicate_inputs_rejected_count`) and never repo identities, datasets, paths, digests, or signatures. When >=4 distinct eligible slices are present, P62 writes a P57-compatible `--input-matrix` JSON handoff containing only the P57-required report paths for P57 to consume. It is not quality evidence, not a promotion/default gate, and not live-readiness evidence. See the [P62 detailed report](p62-generalization-matrix-aggregator.md).

## P63 Cross-Run Slice Collector / Matrix Runner v0

P63 is a deterministic, offline, no-provider, no-live-LLM, aggregate-only cross-run slice collector and orchestrator that runs after P62. It accepts only already-downloaded local per-run artifact directories, validates that each directory contains only the allowlisted aggregate report JSON files, builds a P62 slice manifest, and then runs P62 -> P57 -> P61 offline. P63 does not fetch artifacts from a network, call providers, construct prompts, read source files, tasks, candidates, prompts, responses, traces, or ephemeral records, and it does not expose run, repo, dataset, or directory identity. It is not a fetcher, not quality evidence, not provider spend authorization, not repo or dataset diversity proof, and not a promotion/default gate or live-readiness authorization. P63 emits only aggregate counts and status enums; any future live provider run requires a separate workflow_dispatch or human decision. See the [P63 detailed report](p63-cross-run-slice-collector.md).

The first real cross-run dry-run used four successful `ci_smoke` runs with `max_tasks=6` and `round_robin_public_buckets` (`py_flask`, `js_express`, `go_gin`, `rust_ripgrep`). P63 accepted all four sanitized slice directories, P62 reported four distinct eligible slices, and P57 reached `diagnostic_matrix_complete` over 24 aggregate tasks (`positive=9`, `no_gold=15`). P61 initially blocked with `blocked_missing_actionability` because P59 reported `blocked_missing_hard_distractor`.

P59B then repaired the hard-distractor/actionability precondition using a gold-free `metadata_hard_distractor_proxy_v1` and stricter workflow gates; it did not relax P61 and did not use labels to construct packs. P51-B then added a redaction-policy precondition so P61 can distinguish `required_defined_satisfied` from missing redaction policy without constructing prompts or payloads. A second four-slice round-robin dry-run (`py_flask` 27643271948, `js_express` 27643273360, `go_gin` 27643274763, `rust_ripgrep` 27643276402) reached `P61 status=micro_run_preconditions_met` with reason `all_required_preconditions_present`. This is still only a precondition signal: it does not authorize live LLM spend, does not change defaults, does not promote any policy, and does not alter EvidenceCore. A true P51-C live micro-run remains a separate explicit workflow_dispatch or human decision.

## B1 Live LLM Rich Candidate Run

B1 is the first Breakthrough Sprint live quality experiment after the pre-spend gates. It used the existing P21 rich-candidate harness and P25 scorer on four public repos (`py_flask`, `js_express`, `go_gin`, `rust_ripgrep`) with six round-robin public-bucket tasks per repo. `Kimi-K2.7-Code` was run in both `tool_call` and `json_schema_strict` modes. All eight runs succeeded and passed privacy gates. The strongest result was `llm_span_narrow` in `tool_call` mode: across 24 tasks, added gold rose from 8 to 9, added false spans fell from 43 to 5, mean SpanF0.5 improved from 0.1099 to 0.2849, and mean primary false-positive rate fell from 0.1250 to 0.0625. `json_schema_strict` remained schema-stable but was slower and left more false spans. B1 shows real quality signal for rich candidate span narrowing, but it is not Evidence, not promotion, and not a default change. See the [B1 detailed report](b1-live-llm-rich-candidate-run.md).

## B2 Contrastive Pack Quality Experiment

B2 extends the P21 live rich-candidate harness with `--pack-layout` and compares four live pack structures over the same four-repo, six-task matrix: `topk_plain_v0`, `topk_scores_provenance_v0`, `contrastive_competitor_v0`, and `hard_distractor_contrast_v0`. All 16 tool-call runs succeeded. The main result is nuanced: contrastive structure is not automatically better. For `llm_span_narrow`, `topk_plain_v0` kept the best PFP (`0.0625`) with 9 added gold and 6 added false spans. `hard_distractor_contrast_v0` reduced false spans from 6 to 5 but killed two gold spans and doubled mean PFP to `0.1250`. `topk_scores_provenance_v0` had the highest mean SpanF0.5 (`0.2829`) but increased false spans and latency. Therefore hard-distractor contrast should be routed selectively to filter/no-gold/hard-distractor cases, not used as a universal span-narrow pack. See the [B2 detailed report](b2-contrastive-pack-quality-experiment.md).

## B1C Cross-Model Rich Candidate Rerun

B1C reran B1's `topk_plain_v0` rich-candidate matrix across the updated active LLM roster. Kimi-K2.7-Code tool_call remains the reference configuration: 24/24 schema-valid calls, zero fallback, 9 added gold, 5 added false, mean SpanF0.5 0.2825, and mean PFP 0.0625. GLM-5.2 is viable under `json_schema_strict` (23/24 schema-valid, 7 added gold, 7 added false, mean SpanF0.5 0.2192) but tool_call remains noisy. Qwen3.6-27B broadens 27B dense model coverage, but both output modes hit rate-limit/fallback noise; treat the current Qwen run as plumbing/rate-limit evidence, not quality evidence. See the [B1C detailed report](b1c-cross-model-rich-candidate-rerun.md).

## B3 Request-More-Context Quality Experiment

B3 compared P25 bucket routing against fixed request-more-context treatments using two live P21 pack layouts in each job: `topk_plain_v0` for span narrowing and `hard_distractor_contrast_v0` for filter routing. The first fixed RMC policies did not beat P25. P25 reached 8 added gold / 7 added false, mean SpanF0.5 0.0890, and mean PFP 0.0417. Both LLM-routed RMC variants reached 7 added gold / 8 added false, mean SpanF0.5 0.0820, and mean PFP 0.0833. The local conservative route avoided PFP but collapsed recall. B3 therefore points to interpretable policy search or narrower bucket-specific routing repair rather than fixed global RMC rules. See the [B3 detailed report](b3-rmc-quality-experiment.md).

## B6-lite Interpretable Policy Search

B6-lite runs a bounded rule search over paired `topk_plain_v0` and `hard_distractor_contrast_v0` P21 ephemeral records. On the four-repo Kimi tool-call smoke matrix, it found lower-false-cost hypotheses but not robust policies. `ambiguous_query_weak_only_default_use_p25_action` matched P25's observed added gold with one fewer false span and lower observed PFP, but appeared on the Pareto frontier in only one repo and still used 12 LLM actions. `negative_weak_only_ambiguous_query_use_p25_action_default_use_p25_action` had low false cost and positive net span value but lower gold/SpanF0.5. B6-lite therefore motivates a combined-matrix B6B search with real leave-one-repo-out rather than a default change. See the [B6-lite detailed report](b6-lite-interpretable-policy-search.md).

## B6B Combined-Matrix Interpretable Policy Search

B6B merges paired P21 records from four public repo slices and performs true split-before-search leave-one-repo-out: train the small interpretable grammar on three repo slices, freeze the Pareto policies, then evaluate on the held-out slice. The live run `27689938744` found lower-false-cost hypotheses but still no default policy. `ambiguous_query_weak_only_default_use_p25_action` preserved P25-like held-out gold/SpanF0.5 in aggregate while reducing false spans (7 gold / 5 false vs P25's 7 / 8) and observed PFP (0.0 vs 0.0833). `negative_weak_only_ambiguous_query_use_p25_action_default_use_p25_action` was lower-false (4 gold / 1 false) but loses too much gold for deep-quality use. B6B remains diagnostic-only and needs fresh validation on more repos/models. See the [B6B detailed report](b6b-combined-policy-search.md).

## B6C Frozen-Policy Validation Protocol

B6C freezes the two candidate policies identified by B6B and defines the exact fresh-validation protocol for comparing them against the fixed P25 bucket-routed baseline. It performs no search, rule generation, or winner selection. The frozen policy file is exact-spec/hash checked, and non-self-test runs require a `b6c_fresh_validation_contract` proving records were generated after the freeze and were not retuned from B6C results. The currently committed artifact is a self-test protocol check (`claim_level=self_test_synthetic_protocol_check`), not a completed fresh validation. A live B6C run must produce `claim_level=frozen_policy_fresh_validation` before it can be used as fresh validation evidence. Public reports remain aggregate-only and emit no repo/task/candidate identifiers or raw content. B6C is diagnostic-only, not a promotion gate. See the [B6C detailed report](b6c-frozen-policy-validation.md).

The first live B6C run (`27706742419`) produced `claim_level=frozen_policy_fresh_validation` with the freshness contract valid and no search on the fresh records. `ambiguous_query_weak_only_default_use_p25_action` preserved P25's 8 added gold and mean SpanF0.5 while reducing false spans from 6 to 5, removing observed PFP, and cutting effective LLM actions from 24 to 12. The more conservative frozen policy reached 5 gold / 1 false and positive net span value, but lost too much gold for deep-quality use. This supports a balanced-policy hypothesis, not a default change.

B6E expanded the same frozen-policy validation to 48 comparable tasks (`27717886432`, four public repo slices × 12 round-robin tasks). The main balanced-policy candidate again preserved P25's added gold and mean SpanF0.5 while reducing false spans from 17 to 14, removing observed PFP, and reducing estimated LLM actions from 47 to 31. This strengthens the balanced-policy hypothesis within the same four-repo public universe, but remains single-model and not repo-generalization or a default change.

B6F reused the same frozen-policy validation on a different set of four public repo slices (`27735809672`, 4 × 12 tasks). The main balanced-policy candidate again preserved P25's added gold and mean SpanF0.5 while reducing false spans from 24 to 20, removing observed PFP, and reducing estimated LLM actions from 47 to 31. This is the first repo-generalization smoke supporting the balanced-policy hypothesis, but remains single-model, low-n, and not a default/promotion result.

## B8-lite Medium Matrix Combiner

B8-lite combines the B6E and B6F frozen-policy validation reports into a derived 96-task aggregate over eight public repo slices. It performs no new provider calls, no policy search, and no per-task/per-repo reads. The main balanced-policy candidate matches P25's 21 added gold and weighted mean SpanF0.5 while reducing false spans from 41 to 34, removing observed PFP, and reducing estimated LLM actions from 94 to 62. This strengthens the single-model balanced-policy hypothesis, but remains a derived aggregate rollup, not a new live validation run or default change. See the [B8-lite detailed report](b8-lite-medium-matrix-combiner.md).

## B6D Cross-Adapter Frozen-Policy Validation

B6D tests whether the B6C frozen-policy direction is quality-interpretable under a different model adapter, without changing the frozen policy or searching again. The first live B6D run (`27716082836`) completed successfully but reported `status=not_quality_interpretable`: GLM-5.2 `json_schema_strict` had `schema_valid_rate=0.75` and `infra_failure_rate=0.25`, below the adapter-health threshold. Direction consistency is therefore `not_determinable`, and policy-family quality metrics remain null. This is adapter-health evidence, not a negative quality conclusion about the frozen policy. Output mode is treated as a model-adapter configuration parameter, not an OpenLocus algorithm variable. See the [B6D detailed report](b6d-cross-adapter-frozen-validation.md).

## B9A Adapter Health Repair Screen

B9A screens GLM-5.2 and Qwen3.6-27B adapter profiles under sequential small live runs. It is not a quality leaderboard and treats output mode as a model-adapter configuration parameter. Qwen3.6-27B `json_schema_strict` passed the small health screen (`schema_valid_rate=1.0`, `infra_failure_rate=0.0`) and can be used for cautious low-volume follow-up. GLM-5.2 `json_schema_strict` improved over tool-call behavior but remains below quality-interpretable thresholds (`schema_valid_rate=0.833`, `infra_failure_rate=0.333`). GLM tool-call and Qwen tool-call remain too noisy for critical-path validation. See the [B9A detailed report](b9a-adapter-health-report.md).

## B9B Qwen Low-Volume Quality Follow-up

B9B reran Qwen3.6-27B under its health-passed `json_schema_strict` adapter with sequential low-volume P21 rich-candidate jobs. The adapter remained healthy (`schema_valid_rate=1.0`, `infra_failure_rate=0.0`) and produced quality-interpretable span-narrow signal: 7 added gold / 4 added false, false_per_gold 0.571, mean SpanF0.5 0.2831, mean PFP 0.0625. Qwen should no longer be treated only as plumbing/rate-limit evidence under this adapter profile, but this is still a small single-adapter follow-up, not a default model or output-mode leaderboard result. See the [B9B detailed report](b9b-qwen-low-volume-quality-follow-up.md).

## B9C Qwen Frozen-Policy Validation

B9C validates the B6C frozen balanced policy under Qwen3.6-27B `json_schema_strict`. Run `27744695226` completed successfully with `quality_interpretable=true` and `direction_consistency=consistent_with_kimi`. The balanced frozen policy preserved P25's 6 added gold and mean SpanF0.5 while reducing false spans from 5 to 4, removing observed PFP, and cutting estimated LLM actions from 24 to 12. This is the first secondary-adapter support for the balanced-policy direction, but remains a low-n smoke, not a default/promotion result. See the [B9C detailed report](b9c-qwen-frozen-policy-validation.md).

## B9D DeepSeek / GLM Participation Screen

B9D checks whether DeepSeek and GLM adapters can participate in future experiments without turning adapter noise into the research subject. DeepSeek-V4-Flash and DeepSeek-V4-Pro both completed small sequential screens under `tool_call` and `json_schema_strict` with schema_valid_rate 1.0 and infra_failure_rate 0.0. Flash showed a more recall-oriented span-narrow shape (4 gold / 3 false on 12 tasks), while Pro was more conservative (2 gold / 1 false). GLM-5.2 remains supported but noisy based on B9A/B6D and should stay opt-in/exploratory. This is a participation recommendation, not a model leaderboard. See the [B9D detailed report](b9d-deepseek-glm-participation-screen.md).

## B4/B9 Model-Robust Evidence Conversion

B4/B9 separates `algorithm_spec` (model-independent strategy definitions) from `model_adapter` (model + output-mode health) and re-encodes the live quality cells from B1, B1C, B2 and B3. It is aggregate-only, not a gate, not a precondition-only stage, and does not change `EvidenceCore`. `span_narrow_topk_plain_v0` shows a `low_n_directional_signal` on the two matched Kimi adapter deltas; GLM-5.2 json_schema_strict is secondary observed cross-family validation only because no matched baseline delta is available. Fixed RMC variants (`rmc_hybrid_v0`, `rmc_llm_pack_routed_v0`, `rmc_local_conservative_v0`) are `not_supported`. B9B/B9C later update Qwen from plumbing-only to secondary low-volume adapter support, but B4/B9's original aggregate remains unchanged. See the [B4/B9 detailed report](b4-b9-model-robust-evidence-conversion.md).

## B10 Runtime Feature Audit + Balanced Policy v1 Freeze

B10 freezes the B6C main balanced candidate `ambiguous_query_weak_only_default_use_p25_action` as the algorithm spec `balanced_policy_v1_benchmark_routed` and audits the provenance of every routing feature the spec actually reads. It does not run any model, does not search, does not change the frozen policy, and does not change `EvidenceCore`. This is a **benchmark-routed research algorithm spec only** (`claim_level=benchmark_routed_algorithm_spec_only`), NOT a runtime-feature-only policy, NOT a default change, NOT a promotion candidate.

The audit is explicit: `ambiguous_or_query_noise` is `_ambiguous_like or _query_noise`, where `_ambiguous_like` reads the benchmark public labels `task_bucket`/`task_risk_tags` (benchmark public dependency) and `_query_noise` reads the deterministic runtime feature `route_features.query_noise`. The default action `use_p25_action` delegates to `p25.route_bucket_routed_v0` and therefore inherits the P25 deterministic runtime route_features (`candidate_count`, `candidate_support_exists`). P25 exact/unique short-circuiting is currently driven by bucket labels rather than a `unique_symbol_anchor` route-feature read. `runtime_clean=false` and `runtime_feature_only_mode_supported=false` because the `_ambiguous_like` branch cannot be evaluated without `task_bucket`/`task_risk_tags`; a runtime-feature-only mode would route every task to the default action and never fire the `ambiguous_query_weak_only` rule. Routing uses no score-private fields (`score_private_dependencies_for_routing=[]`); `has_gold`, `score_group`, and `outcome_metrics` are used only for aggregate scoring after actions are chosen. `model_adapter`, `output_mode`, and provider credentials/endpoints/secrets are an excluded adapter layer, not part of the algorithm spec. Public artifacts are aggregate-only and emit no forbidden public keys (`task_id`, `repo_id`, `candidate_id`, `path`, `span`, `snippet`, `prompt`, `response`, `gold_spans`, `provider_key`, `base_url`, `api_key`, `content_sha`). `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`. The next step is `balanced_policy_v1_runtime_shadow`: replace the ambiguous bucket/tag branch with pure runtime features (`query_noise`, `candidate_support_exists`, anchor disagreement) and run an action-agreement replay against this benchmark-routed spec — that runtime-shadow policy is NOT this spec. See the [B10 detailed report](b10-runtime-feature-audit.md).

## B10B Runtime-Shadow Replay (Ambiguous Branch Only)

B10B is the next step after the B10 freeze of `balanced_policy_v1_benchmark_routed`. It does not run any model, does not search, does not tune policy quality, and does not defaultize. It only tests whether a fixed predeclared runtime-feature-only shadow predicate can reproduce the **ambiguous branch** of the frozen benchmark-routed spec's action on the same records. The strengthened evaluator carries a verdict framework (`runtime_shadow_ambiguous_supported` + `support_claim` + `support_claim_reason`), 10 predeclared acceptance gates (including `label_driven_ambiguous_min_denominator: 10` as a HARD gate, not an escape clause), stratified agreement metrics (`target_weak_only_recall`, `target_use_p25_specificity`, `shadow_weak_only_precision`, `label_driven_ambiguous_recall_qn0`), silent-failure checks, a direct Cohen's kappa implementation (no numpy/sklearn), and a 4-partition outcome-equivalence audit on the disagreement subset (audit-only; outcomes never feed back into routing). The leakage guard now mutates `outcome_metrics` in addition to `task_bucket`/`task_risk_tags`/`has_gold`/`score_group`. The current verdict on the synthetic fixture is `runtime_shadow_ambiguous_supported=false`, `support_claim="mechanics_only_synthetic_fixture"`, `replay_source="synthetic_fixture"` — a **mechanics-validated scaffold with empirical validation pending**, not an empirical-support claim. All safety invariants are preserved (`claim_level=ambiguous_branch_runtime_shadow_only`, `full_runtime_clean_policy=false`, `ambiguous_branch_runtime_shadow_only=true`, `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `policy_search_performed=false`, `quality_strategy_tuned=false`, `runtime_calls_by_replay=0`, `model_calls_by_replay=0`). Empirical support requires B10B to run on real CI ephemeral records (`--records <path>`) and pass every predeclared gate; until then B11 should be framed as **exploratory prospective stress test**, not "supported validation". See the [B10B detailed report](b10b-runtime-shadow-replay.md).

## B11 Prospective Blind Validation

B11 is the first prospective validation of the frozen balanced policy `balanced_policy_v1_benchmark_routed` on new repos and tasks generated after the 2026-06-18 policy freeze, with no retuning of policies, thresholds, or success criteria. It compares 4 policies (Local baseline, P25 `p25.route_bucket_routed_v0`, Balanced v1 `balanced_policy_v1_benchmark_routed`, Conservative `rmc_local_conservative_v0`) across 4 model families (`Kimi-K2.7-Code`, `Qwen3.6-27B`, `DeepSeek-V4-Flash`, `DeepSeek-V4-Pro`; GLM-5.2 excluded as noisy). Predeclared success/failure/partial criteria with explicit overall and worst-group thresholds (`Δgold_span`, `ΔSpanF0.5`, `ΔPFP`, `Δfalse_spans`, `ΔLLM_calls`) plus a `RobustUtility` = `min_group(SpanF0.5 - λ*PFP - μ*normalized_cost - ν*normalized_latency)` aggregate are frozen in the preregistration before any live runs. B10B `--records` is integrated to run in CI after each B11 run, giving B10B its first empirical validation. B11 is a prospective stress test, not a promotion step: `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`. The plan, CI workflow definition, and report-aggregator skeleton are autonomous; actual live LLM runs require a user `workflow_dispatch` trigger with `enable_remote_models=true`. See the [B11 detailed report](b11-prospective-blind-validation.md).

### B11 official integrated matrix result (2026-06-18)

The B11 official integrated matrix completed 32/32 runs (two transient `provider_status` failures retried) across 8 public repo slices and 4 model families, totalling 384 records. The aggregate is a **derived aggregate rollup** of the already-downloaded aggregate-only public B11/B10B artifacts (`eval/b11_matrix_combiner.py` → `artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json`); no raw records, paths, prompts, responses, snippets, or private labels were read. Verdict counts: `success 8`, `partial 23`, `failure 1`; aggregate verdict `partial_with_failure`.

Overall weighted means (384 records) — `local_baseline` / `p25` / `balanced_v1` / `conservative`: `gold_span 0.377604 / 0.247396 / 0.244792 / 0.125000`; `false_span 1.203125 / 0.236979 / 0.182292 / 0.236979`; `span_f0_5 0.062197 / 0.064538 / 0.062639 / 0.023611`; `PFP 0.083333 / 0.020833 / 0.000000 / 0.000000`; `model_calls 0.0 / 0.958333 / 0.604167 / 0.000000`. Balanced v1 vs P25 deltas: `Δgold_span -0.002604`, `Δfalse_span -0.054688`, `ΔSpanF0.5 -0.001899`, `ΔPFP -0.020833`, `Δmodel_calls -0.354167` — balanced_v1 preserved near-parity SpanF0.5/gold while reducing false spans, PFP, and model calls on average. Per model family: `deepseek_flash` (partial 6 / success 2), `deepseek_pro` (partial 5 / success 3), `kimi` (partial 5 / success 2 / **failure 1** — a `py_fastapi` slice exceeded `failure_spanf05_delta`), `qwen` (partial 7 / success 1).

B10B ran after every B11 run (32/32 reports); `runtime_shadow_ambiguous_supported=false` on all runs with `support_claim="empirical_replay_support_pending"` (reason `insufficient_label_driven_denominator`; max observed `label_driven_ambiguous_denominator_qn0=3` vs the 10-record hard gate), so the B10B runtime-shadow predicate remains empirical-pending.

**Conclusion**: B11 is **mixed/partial**. The result strengthens the algorithm-candidate signal (balanced_v1 preserves near-parity SpanF0.5/gold vs P25 while reducing false spans, PFP, and model calls on average), but does **not** prove a runtime-clean general algorithm, does **not** promote, does **not** change defaults, and does **not** alter EvidenceCore semantics. The one Kimi failure slice and the B10B denominator-pending predicate are open issues for B12 (mechanism decomposition). Recommended next step: B12.

## B12 Mechanism Decomposition

B12 is the mechanism-decomposition phase that follows B11. It decomposes **why** the frozen balanced policy `balanced_policy_v1_benchmark_routed` (B10) works (if B11 confirms it generalizes) via 5 ablation variants (A full balanced, B deterministic call-reduction control, C ambiguous weak_only only [≡A by construction], D P25 default, E random same-count call-reduction control) and 4 predeclared hypotheses (H1 ambiguous routing, H2 LLM call reduction, H3 P25 fallback sufficiency, H4 model-specific). B12 is replay-only (each P21 record contains per-strategy outcomes, so each variant is computed by selecting the appropriate per-strategy outcome; no live LLM calls in the evaluator). As of the C1 slice (2026-06-19), B12 **now consumes private per-record P21 records** via the shared C1 adapter (`eval/c1_private_records.py`) — the `--input` path is **no longer a stub**; it produces a real aggregate-only report with per-variant replay over the 5 variants, count reporting (`total_records` / `complete_records` / `balanced_branch_count` / `p25_llm_eligible_count` / `actual_call_avoided_count` / `random_selected_count`), and a scientific verdict.

**Taint model + actual-call-avoided definitions.** The C1 adapter uses a three-category taint model: (1) runtime-clean `route_features`; (2) benchmark route labels (`task_bucket`, `task_risk_tags`) — used to analyze frozen benchmark-routed policies but NOT runtime-clean; (3) score/outcome/private fields (`score_group`, per-strategy outcomes, `p31_score_gold`, `p31_candidate_pools`, `p33b_anchor_subtypes`) — allowed only because the file is runner-temp/private. `balanced_branch_set` = records where the balanced v1 `ambiguous_or_query_noise` predicate fires (reads benchmark labels → that is why balanced_v1 is benchmark-routed, NOT runtime-clean). `p25_llm_subset` = records where D/P25 would choose an LLM strategy. `actual_call_avoided_set = balanced_branch_set ∩ p25_llm_subset` — the records where the balanced routing actually avoids an LLM call that D would have made (the B-variant intervention set). E uses one frozen seed (`e_random_seed=20260618`) to hash-select the same count from `p25_llm_subset` (single-seed limitation noted; seed-averaging deferred).

**Revised (C1) H1-H3 criteria** — before any empirical replay: the balanced policy is expected to PRESERVE gold/span vs D approximately (NOT increase), REDUCE false/PFP/model_calls vs D, and OUTPERFORM B/E on false/PFP/RobustUtility enough to support targeted ambiguous routing. A is NOT required to increase gold/span. H4 is `insufficient_data` unless ≥ 2 known model families are present. **H4 insufficient_data does NOT block the H1-H3 mechanism verdict** — the report carries `h4_insufficient_data_blocks_overall_verdict=false` and `h1_h3_verdict_independent_of_h4=true`, so single-model B12 CI slices can evaluate H1-H3 while H4 needs multi-model aggregation.

B12 is mechanism decomposition, **not** a promotion step: `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `policy_search_performed=false`, `quality_strategy_tuned=false`. The public B12 report is **aggregate-only** — no task_id, raw/private repo_id, path, span, candidate_id, content_sha, per-record hash, P31/P33 block, or raw prompt/response/snippet/provider field is emitted (only COUNTS). Aggregate group metrics use only public preregistered repo labels for synthetic/preregistration fixtures or anonymized `public_repo_group_NNN` labels for private `--input` replays. Scientific verdicts (`supported` / `refuted` / `partial` / `insufficient_data`) return exit 0; mechanical/privacy/schema errors return nonzero; a scientific no-result is a valid CI outcome and does NOT fail CI. See the [B12 detailed report](b12-mechanism-decomposition.md).

### C2 B12 CI canary (2026-06-19)

C2 verified the new C1/B12 path on a real CI run: `py_fastapi × Kimi × round_robin_public_buckets × 12 tasks` (run `27816890557`) produced a B12 report with `replay_source="ci_ephemeral_records"`, `total_records=12`, `complete_records=12`, `incomplete_record_count=0`, `balanced_branch_count=4`, `p25_llm_eligible_count=10`, `actual_call_avoided_count=4`, and `random_selected_count=4`. The public report remained aggregate-only and privacy-safe. The canary verdict was `partial`: H1 `refuted`, H2 `refuted`, H3 `supported`, H4 `insufficient_data` (single model family). This is a canary-level mechanism result only, not a full B12 conclusion. The next step is a full B12 matrix over the B11 repo/model cells.

### C2/B12 official matrix aggregate (2026-06-19)

The **C2/B12 official matrix aggregate** combines the 28 analyzable per-run B12 `b12-mechanism-decomposition-report-v0` public aggregate reports into a single derived aggregate (`eval/b12_matrix_combiner.py` → `artifacts/b12_mechanism_decomposition/b12_matrix_aggregate_report.json`, schema `b12-mechanism-matrix-aggregate-report-v0`). It is a bounded aggregate-only rollup: it reads only already-downloaded public B12 reports, performs no provider calls (`new_provider_calls=0`), no policy search (`policy_search_performed=false`), no threshold tuning, and no promotion/default/runtime-clean/EvidenceCore-semantics claim. Coverage: `28/32` cells analyzable; `4` `ts_vite` cells excluded as `coverage_insufficient_no_remote_llm_snippet` (they failed the old P21 privacy gate because they did not exercise remote LLM snippets even at `max_tasks=24`; these are coverage gaps, NOT B12 mechanism failures). Records: `336` total (`12` per cell). Verdict counts: `partial: 28`. Hypothesis status counts: H1 `supported: 3 / refuted: 25`, H2 `supported: 8 / refuted: 20`, H3 `supported: 28`, H4 `insufficient_data: 28` (every cell is a single-model-family slice, so H4 needs multi-model aggregation across cells; H4 insufficient_data does NOT block the H1-H3 verdict by design). Record-weighted A (full balanced) deltas vs D (P25 default): `Δgold_span 0.0`, `ΔSpanF0.5 0.0`, `Δfalse_span -0.029762`, `ΔPFP -0.014881`, `Δmodel_calls -0.333333`; vs E (random call reduction): `Δgold_span -0.044643`, `ΔSpanF0.5 0.001569`, `Δfalse_span -0.592262`, `ΔPFP -0.026786`, `Δmodel_calls 0.0`; vs B (deterministic call reduction): `Δgold_span 0.0`, `ΔSpanF0.5 0.0`, `Δfalse_span -0.130952`, `ΔPFP -0.035714`, `Δmodel_calls 0.0`. Weighted mean robust utility (A): `0.054155`. Replay count totals: `balanced_branch_count=112`, `p25_llm_eligible_count=324`, `actual_call_avoided_count=112`, `random_selected_count=112`. Overall verdict: `partial_with_coverage_exclusions` — NOT a global `supported` verdict, NOT promotion, NOT default change, NOT runtime-clean general algorithm claim, NOT EvidenceCore semantics change. All safety flags: `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `policy_search_performed=false`, `runtime_clean_policy_supported=false`, `new_provider_calls=0`, `candidate_not_fact=true`. Recommended next step: B13 distributionally robust policy search WITH CAUTION (B13 must not be treated as authorized by a B12 supported verdict), or a future B12 matrix rerun that closes the `ts_vite` coverage gap. See the [B12 detailed report](b12-mechanism-decomposition.md).

### B12 public aggregate mechanism screen (2026-06-18)

A bounded **public-aggregate mechanism screen** was added (`eval/b12_public_aggregate_screen.py` → `artifacts/b12_mechanism_decomposition/b12_public_aggregate_screen_report.json`). This is **NOT** a full B12 per-record replay. The explorer/oracle finding is that full B12 replay is impossible from the current public B11 aggregate: it lacks per-record route decisions, ambiguous-subset membership, deterministic call-reduction variant B, random call-reduction variant E, and `weak_candidate_only` per-strategy outcomes. The screen therefore emits **per-hypothesis screen statuses**, never a single global `supported` verdict, and applies the SAME frozen numeric gates (±0.02 approx-equality, 0.05 H4 family-spread) to the aggregate deltas only.

Per-hypothesis screen results from the B11 official matrix aggregate (32 runs / 384 records):

- **H1 (ambiguous routing): `inconclusive_unavailable_ablation_controls`** — the public aggregate has no per-record route decisions, no ambiguous subset, and no variants B/E. The screen does NOT claim H1 support.
- **H2 (LLM call reduction): `reduced_calls_observed_causal_mechanism_inconclusive`** — `Δmodel_calls -0.354167` so reduced calls are observed descriptively, but without variant E (random call reduction) the causal mechanism cannot be attributed. The screen does NOT claim H2 causal support.
- **H3 (P25 fallback sufficiency): `aggregate_primary_parity_supported_consistent_with_h3`** — `Δgold_span -0.002604` and `ΔSpanF0.5 -0.001899` are both within ±0.02, so aggregate primary parity holds (consistent with H3 at the aggregate level). This is **not** a full H3 supported verdict: per-record fallback sufficiency cannot be concluded from aggregate deltas alone.
- **H4 (model-specific): `family_gold_spread_not_supported_model_repo_interaction_inconclusive`** — per-family gold_span delta spread is `0.010417` (deepseek_flash 0.0, deepseek_pro 0.0, kimi -0.010417, qwen 0.0), at or below the 0.05 family-level threshold, so H4 is NOT supported under the predeclared family-level gold-span spread criterion. This is **not** a full H4 refutation: the Kimi `py_fastapi` failure slice means model×repo interaction remains inconclusive without per-record data.

Safety fields preserved verbatim: `aggregate_only_public_artifact=true`, `candidate_not_fact=true`, `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `policy_search_performed=false`, `quality_strategy_tuned=false`, `new_provider_calls=0`. The screen does NOT claim promotion, default change, runtime-clean general algorithm, H1 support, H2 causal support, or full H4 refutation. Recommended next step: future ephemeral-record B12 replay, or B13 robust policy search **with caution** (B13 must not be treated as authorized by a B12 supported verdict). See the [B12 detailed report](b12-mechanism-decomposition.md).

## B13 Distributionally Robust Policy Search

B13 is the distributionally-robust policy-search phase that follows B12. It searches for a policy with 6-10 rules, using only runtime-observable `route_features` (no benchmark-private labels, no score-private fields, no raw model names in `algorithm_spec`), that optimizes worst-group utility or `CVaR_20%`, validated via 3 rotating leave-one-model-family-out rotations. Allowed actions are LLM-free (`weak_only`, `use_p25_action`, `use_local_baseline`); the search method is bounded grid + greedy refinement (pure Python). B13 IS the policy-search *stage* (`stage_is_policy_search=true`), but the shipped skeleton performs NO empirical policy search (`empirical_policy_search_performed=false`); the synthetic-fixture / `--input` stub report sets `policy_search_performed=false`, `policy_found=false`, `rotations_evaluated=false`, `rotations_defined=true`, `rotation_count=3`, `winner_declared=false` so the public artifact cannot be misread as an empirical B13 run. Synthetic / stub reports emit only rotation *definitions* (no per-rotation `passes=true` / `all_rotations_pass=true` / `test_worst_group_utility` / `delta_vs_b10_reference`); the skeleton verdict framework emits only `insufficient_data` (synthetic fixture) or `not_implemented` (ci_ephemeral_records stub) — `success` / `failure` / `partial` are reserved for a future empirical `policy_search_performed=true` path that is NOT present in this skeleton. The `--self-test` is read-only (compares in-memory expected artifacts to on-disk artifacts, fails on drift, does not mutate checked-in artifacts); `--regenerate-artifacts` is the only path that mutates checked-in artifacts. Results are NOT promoted (`promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`); they are research candidates that feed into B14 (uncertainty calibration) and B16 (downstream agent evaluation). The `--input` path is a stub (verdict `not_implemented`); B13 needs P21 records from B11 live runs. Real B13 distributionally robust policy search cannot be done from public aggregates alone: the bounded public-aggregate feasibility / no-go screen at `eval/b13_public_aggregate_feasibility_screen.py` reads the published B11 aggregate + B12 public screen and emits `verdict=no_go_public_aggregate_only` (or `insufficient_data_public_aggregate_only`) under `artifacts/b13_dro_policy_search/`, with `policy_found=false`, `rotations_evaluated=false`, `full_b13_possible_from_public_artifacts=false`; it never selects a rule, never declares a winner, and never claims empirical policy search. B13 is the last "immediate priority" item in the B10-B19 Breakthrough Sprint. See the [B13 detailed report](b13-distributionally-robust-policy-search.md).

## B14 Uncertainty Calibration

B14 is the uncertainty-calibration phase that follows B13. It produces a **model-independent** uncertainty score per record (never calibrated to a specific model name) from three allowed signal families — local candidate signals, model output structure, and cross-model disagreement — and evaluates that score with risk-coverage, selective risk, ECE, and PFP-at-fixed-coverage metrics, with worst-group reporting and rotating leave-one-model-family-out validation. The signal families are restricted: **no** benchmark-private labels (`task_bucket`, `task_risk_tags`), **no** score-private fields (`has_gold`, `score_group`, `outcome_metrics`), and **no** raw model names in `algorithm_spec` (abstract `family_slots` only). Per-record outcomes (was the selected span correct) are the calibration TARGET, never an uncertainty signal feature. Frozen coverage levels are `[0.50, 0.70, 0.90, 0.95, 0.99]`; ECE uses 15 equal-width bins over `[0, 1]`; the split protocol is stratified by (model_family, repo) with `calibration_fraction=0.50` / `test_fraction=0.50` (recalibration on the calibration split only; the test split is held out and reported once). Predeclared success/partial/failure criteria use explicit thresholds on test-split ECE (≤ 0.05), selective risk at coverage=0.90 (≤ 0.10), worst-group selective risk at coverage=0.90 (≤ 0.15), and a 0.02 approx-equality / strictly-greater rotation threshold, plus a `CVaR_20%` worst-group tail average.

B14 IS the uncertainty-calibration *stage* (`stage_is_uncertainty_calibration=true`), but the shipped skeleton performs NO empirical uncertainty calibration (`uncertainty_calibration_performed=false`); the synthetic-fixture / `--input` stub report sets `calibrated_model_claim=false`, `per_record_inputs_available=false`, `uncertainty_score_found=false`, `rotations_evaluated=false`, `rotations_defined=true`, `rotation_count=3`, `winner_declared=false`, `metrics_evaluated=false`, `no_fake_metrics_from_aggregate_means=true` so the public artifact cannot be misread as an empirical B14 calibration. **CRITICAL**: the skeleton MUST NOT compute fake ECE / risk-coverage / selective-risk / PFP-at-coverage metrics from aggregate means; the synthetic fixture validates only metric NAMES and gates (no per-record (uncertainty, outcome) pairs, no computed metric values). Synthetic / stub reports emit only rotation *definitions* (no per-rotation `passes=true` / `test_ece` / `test_selective_risk` / `test_risk_coverage_curve` / `test_pfp_at_fixed_coverage` / `delta_vs_reference`); the skeleton verdict framework emits only `insufficient_data` (synthetic fixture) or `not_implemented` (ci_ephemeral_records stub) — `success` / `failure` / `partial` are reserved for a future empirical `uncertainty_calibration_performed=true` path that is NOT present in this skeleton. The `--self-test` is read-only (compares in-memory expected artifacts to on-disk artifacts, fails on drift, does not mutate checked-in artifacts); `--regenerate-artifacts` is the only path that mutates checked-in artifacts. Results are NOT promoted (`promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`); they are research candidates that feed into B16 (downstream agent evaluation) and future selective-abstention policy work. Real B14 calibration cannot be done from public aggregates alone: the bounded public-aggregate feasibility / no-go screen (`eval/b14_public_aggregate_feasibility_screen.py`) reads the published B11 + B12 + B13 artifacts and emits `verdict=no_go_public_aggregate_only` (or `insufficient_data_public_aggregate_only`) under `artifacts/b14_uncertainty_calibration/`; it never claims empirical calibration, never computes a metric, never selects an uncertainty score, and never declares a winner. The missing inputs are: no per-record uncertainty scores, no per-record outcomes, no paired cross-model outputs, no schema-repair per-call rows, no candidate score distributions/entropy, no calibration/test split, no ECE bins, and no fixed-coverage thresholds. B11 mixed/partial, B12 aggregate-screen only, and B13 no-go are carried forward unchanged. See the [B14 detailed report](b14-uncertainty-calibration.md).


## B15 Context Pack Policy

B15 is the context-pack-policy phase that follows B14. The goal is a **frozen, preregistered PackPolicy** mapping `(role, runtime_state, model_profile)` to a deterministic **atom set** (the pack-layout atoms a context pack should expose), validated against per-record pack-atom flags + per-record outcomes + role + runtime_state + model_profile + group membership from B11/B13 live runs. B15 is a **bounded planning / feasibility phase**, NOT an empirical atom-level ablation. Roles are FROZEN (`span_narrow`, `filter_reject`, `request_more_context`, `source_test_disambiguation`); the atom registry is FROZEN (`signature`, `matched_lines`, `raw_snippet`, `neighbor_context`, `scores`, `provenance`, `hard_distractor`, `same_file_competitor`, `path_kind_flag`); the runtime_state contract is label-free and model-name-free; the model_profile abstraction uses abstract capability slots (`profile_slot_a`..`profile_slot_d`) + capability descriptors only — **NO** raw model names in `algorithm_spec`. The experimental structure is FROZEN into 4 stages: `no_llm_feasibility` → `fractional_factorial_live_atom_screen` (resolution-IV fraction over the atom registry, no full 2^9 factorial) → `freeze_candidate_policy` → `fresh_validation` (stratified by `(model_family, repo, role)` with `atom_screen_fraction=0.50` / `fresh_validation_fraction=0.50`, held out and reported once). Hard gates (FROZEN): `privacy_gate`, `leakage_gate`, `adapter_health_gate`, `randomization_balance_gate`, `denominator_gate` (min 30 per cell), `token_budget_gate`, `promotion_false_gate`. Metric registry (FROZEN, 9 names): `atom_effect_per_atom`, `role_pack_outcome`, `runtime_state_pack_outcome`, `model_profile_pack_outcome`, `worst_group_pack_outcome`, `cvar_20_pack_outcome`, `token_budget_parity`, `denominator_per_atom_role_model`, `randomization_balance_per_arm` — every metric requires per-record (atom_flag, outcome, role, runtime_state, model_profile) tuples; none can be computed from aggregate means.

B15 IS the context-pack-policy *stage* (`stage_is_context_pack_policy=true`), but the shipped skeleton performs NO empirical atom ablation (`atom_ablation_performed=false`) and NO PackPolicy learning (`pack_policy_learned=false`); the synthetic-fixture / `--input` stub report sets `per_record_inputs_available=false`, `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `policy_search_performed=false`, `quality_strategy_tuned=false`, `new_provider_calls=0`, `candidate_policy_frozen=false`, `stages_evaluated=false`, `stages_defined=true`, `stage_count=4`, `winner_declared=false`, `metrics_evaluated=false`, `no_fake_atom_effects_from_aggregate_means=true` so the public artifact cannot be misread as an empirical B15 PackPolicy result. **CRITICAL**: the skeleton MUST NOT compute fake atom-effect / role-pack-outcome / worst-group-pack-outcome metrics from aggregate means; the synthetic fixture validates only metric NAMES and gates (no per-record (atom_flag, outcome) pairs, no computed metric values). Synthetic / stub reports emit only stage *definitions* (no per-stage `passes=true` / `atom_effect_per_atom` / `role_pack_outcome` / `worst_group_pack_outcome`); the skeleton verdict framework emits only `insufficient_data` (synthetic fixture) or `not_implemented` (ci_ephemeral_records stub) — `success` / `failure` / `partial` are reserved for a future empirical `atom_ablation_performed=true` / `pack_policy_learned=true` path that is NOT present in this skeleton. The `--self-test` is read-only (compares in-memory expected artifacts to on-disk artifacts, fails on drift, does not mutate checked-in artifacts); `--regenerate-artifacts` is the only path that mutates checked-in artifacts; `--input` stub requires explicit `--out` and refuses to write the canonical checked-in B15 report. Results are NOT promoted (`promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `pack_policy_learned=false`, `atom_ablation_performed=false`); they are research candidates that feed into B16 (downstream agent evaluation) and future context-pack routing work. Real B15 PackPolicy validation cannot be done from public aggregates alone: the bounded public-aggregate prior / no-go screen (`eval/b15_public_aggregate_prior_screen.py`) reads the published B2 contrastive-pack experiment (existence only), the B14 public-aggregate feasibility report, and — when present — the B4-B9 / P21-G / P49 public aggregates, and emits `verdict=prior_screen_only` (or `no_go_public_aggregate_only` when B2 is missing) under `artifacts/b15_context_pack_policy/`; it never claims empirical PackPolicy learning, never computes an atom-effect metric, never freezes a candidate policy, and never declares a winner. The published B2 contrastive-pack experiment is a single-model, low-N (24 tasks per layout), aggregate-only pack-layout comparison; it is usable ONLY as a `low_n_single_model_aggregate_directional_prior` (`b2_prior_usable=true`, `b2_prior_claim_level=low_n_single_model_aggregate_directional_prior`), NOT as atom-level causality, role-specific PackPolicy, calibrated policy, cross-model robustness, a hard-distractor general rule, a scores/provenance general win, a default change, a promotion, or an EvidenceCore change. The missing inputs are: no per-record pack atom flags, no per-record outcomes, no role-specific paired outputs, no model_profile paired blocks, no randomized atom assignment, no randomization balance stats, no denominator by atom/role/model, and no token-budget matched controls. B14 no-go is carried forward unchanged; it does NOT authorize promotion, default change, PackPolicy promotion, or a runtime-clean general algorithm. See the [B15 detailed report](b15-context-pack-policy.md).

---

## B16 Downstream Coding-Agent Evaluation

B16 is the downstream-coding-agent-evaluation phase that follows B15. The goal is a **frozen, preregistered paired within-task randomized controlled trial (RCT)** that measures whether a candidate retrieval/context variant improves a downstream coding agent (not just retrieval aggregates) on real, paired, isolated-workspace agent runs. B16 is a **bounded planning / feasibility phase**, NOT live downstream agent evaluation. Arms are FROZEN into primary (`control_current_retrieval_v0`, `balanced_v1_retrieval_candidate`), exploratory (`candidate_pack_policy_v0`, only included if a real B15 candidate exists — the B15 skeleton does NOT produce one, so this arm is EXCLUDED by default), and debugging-only (`gold_context_ceiling`, never promoted). Task types are FROZEN (`bug_localization`, `small_code_edit`, `test_selection`, `multi_file_feature`, `refactor_impact`). The paired RCT enforces paired within-task randomization, isolated fresh workspace per run, randomized arm order, same budget/tools/prompt except the retrieval/context variant, and no cross-run memory. Hard gates (FROZEN): `feasibility_gate`, `denominator_gate` (min 30 per (task_type, arm) cell), `leakage_gate`, `operational_parity_gate` (token-budget match tolerance 0.10, latency match tolerance 0.15, same tools/budget/prompt except retrieval variant, isolated fresh workspace, randomized arm order, no cross-run memory), `privacy_gate`, `promotion_false_gate`. Metric registry (FROZEN, 8 names): `solve_rate`, `correct_file_before_first_edit`, `wrong_file_edits`, `tool_calls_before_first_edit`, `context_tokens`, `tests_pass`, `latency`, `cost` — every metric requires per-run paired agent outputs (event logs, patches/diffs, test execution results, solve labels, first-file-before-first-edit events, wrong-file-edit annotations, tool-call/token/latency/cost rows, isolated workspace proof, randomized arm order, task oracle/hidden-test manifest); none can be computed from retrieval aggregates.

B16 IS the downstream-agent-evaluation *stage* (`stage_is_downstream_agent_evaluation=true`), but the shipped skeleton performs NO live downstream agent runs (`downstream_agent_runs_performed=false`), NO patch execution (`patch_execution_performed=false`), NO agent-behavior metrics evaluation (`agent_behavior_metrics_evaluated=false`), and NO solve-rate evaluation (`solve_rate_evaluated=false`); the synthetic-fixture / `--input` stub report sets `per_record_inputs_available=false`, `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `retrieval_variant_promoted=false`, `policy_search_performed=false`, `quality_strategy_tuned=false`, `new_provider_calls=0`, `candidate_retrieval_variant_frozen=false`, `stages_evaluated=false`, `stages_defined=true`, `stage_count=4`, `winner_declared=false`, `metrics_evaluated=false`, `no_fake_downstream_metrics_from_retrieval_aggregates=true` so the public artifact cannot be misread as an empirical B16 downstream agent result. **CRITICAL**: the skeleton MUST NOT compute fake solve-rate / correct-file-before-first-edit / wrong-file-edits / tool-call / token / latency / cost metrics from retrieval aggregates; the synthetic fixture validates only metric NAMES and gates (no per-run paired agent outputs, no computed metric values). Synthetic / stub reports emit only stage *definitions* (no per-stage `passes=true` / `solve_rate` / `correct_file_before_first_edit` / `wrong_file_edits`); the skeleton verdict framework emits only `insufficient_data` (synthetic fixture) or `not_implemented` (ci_ephemeral_records stub) — `success` / `failure` / `partial` are reserved for a future empirical `downstream_agent_runs_performed=true` / `solve_rate_evaluated=true` path that is NOT present in this skeleton. The `--self-test` is read-only (compares in-memory expected artifacts to on-disk artifacts, fails on drift, does not mutate checked-in artifacts); `--regenerate-artifacts` is the only path that mutates checked-in artifacts; `--input` stub requires explicit `--out` and refuses to write ANY path inside `artifacts/b16_downstream_agent_evaluation/`. Results are NOT promoted (`promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `retrieval_variant_promoted=false`, `downstream_agent_runs_performed=false`, `patch_execution_performed=false`, `agent_behavior_metrics_evaluated=false`, `solve_rate_evaluated=false`); they are research candidates only. Real B16 downstream agent evaluation cannot be done from public aggregates alone: the bounded public-aggregate feasibility / no-go screen (`eval/b16_public_aggregate_feasibility_screen.py`) reads the published B11 matrix + B12 + B13 + B14 + B15 public screens and emits `verdict=no_go_public_aggregate_only` (or `insufficient_data_public_aggregate_only`) under `artifacts/b16_downstream_agent_evaluation/`; it never claims downstream agent value, never computes a downstream metric from retrieval aggregates, never freezes a candidate retrieval variant, never promotes a retrieval variant, and never declares a winner. The B10-B15 retrieval/context candidate research is retrieval research; it does NOT prove downstream coding-agent value. Retrieval improvements are NOT downstream agent improvements; B15 PackPolicy is NOT a downstream agent improvement. The missing inputs are: no live paired agent runs, no agent event logs, no patches/diffs, no test execution results, no solve labels, no first-file-before-first-edit events, no wrong-file-edit annotations, no tool-call/token/latency/cost per run, no randomized arm order, no isolated workspace proof, no task oracle/hidden-test manifest, and no operational parity proof. B11 `partial_with_failure` and B12/B13/B14/B15 no-go or screen-only statuses are carried forward unchanged. See the [B16 detailed report](b16-downstream-agent-evaluation.md).

---

## B17 QuIVer Systems Track

B17 is the quiver-systems-track phase that follows B16. The goal is a **frozen, preregistered backend bakeoff** comparing ANN backend candidates on backend systems metrics (latency, memory, build time, update cost, index size) **under a frozen candidate-quality policy** so backend quality cannot be silently relaxed when comparing systems numbers. B17 is a **bounded planning / diagnostic phase**, NOT QuIVer production backend, NOT ANN quality promotion, NOT default change, NOT EvidenceCore semantics change. Candidate backends are FROZEN into reference (`flat_f32_reference`), candidate (`hnsw_candidate`, `bq_topk_f32_rerank_candidate`, `quiver_vamana_prototype` — the QuIVer/Vamana graph backend end goal, **unimplemented**), and optional-store (`tdb_vector_candidate`, store/backend candidate only, NOT an Evidence source, excluded by default). Candidate-set equivalence constraints are FROZEN (`candidate_set_overlap_at_k` ≥ 0.90 at K=[10,50,100], `gold_retention_delta` tolerance 0.05, `primary_false_positive_delta` guard 0.05, `span_f0_5_delta` tolerance 0.05, `citation_validity` = 1.0, `stale_evidencecore_rejection_required`, `no_default_expansion_required`). Hard gates (FROZEN): `quiver_graph_implementation_gate`, `backend_parity_gate`, `candidate_set_equivalence_gate`, `evidencecore_materialization_gate`, `stale_citation_gate`, `privacy_gate`, `promotion_false_gate`. Metric registry (FROZEN, 11 names): `candidate_set_overlap_at_k`, `gold_retention_delta`, `span_f0_5_delta`, `primary_false_positive_delta`, `p50_latency`, `p95_latency`, `hot_memory`, `build_time`, `update_cost`, `index_size`, `recall_tolerance_violation_count` — every metric requires per-backend systems bakeoff inputs (index build records, search latency records, hot memory records, index size records, update cost records, candidate-set-at-K records, gold retention records, span F0.5 records, PFP records, citation validity records, stale rejection records, EvidenceCore rejection records, recall tolerance violation records, randomized run order proof, isolated index workspace proof, shared frozen candidate-quality manifest); none can be computed from the existing R33/R34/R36/R24 diagnostics.

B17 IS the quiver-systems-track *stage* (`stage_is_quiver_systems_track=true`), but the shipped skeleton performs NO ANN backend bakeoff (`ann_backend_bakeoff_performed=false`), NO candidate-set equivalence validation (`candidate_set_equivalence_validated=false`), NO QuIVer/Vamana graph implementation (`quiver_graph_implemented=false`), and NO backend quality promotion (`backend_quality_promoted=false`); the synthetic-fixture / `--input` stub report sets `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `retrieval_policy_changed=false`, `metrics_evaluated=false`, `new_provider_calls=0`, `no_fake_ann_metrics_from_diagnostics=true` so the public artifact cannot be misread as an empirical B17 systems bakeoff result. **CRITICAL**: the skeleton MUST NOT compute fake candidate_set_overlap_at_k / gold_retention_delta / span_f0_5_delta / primary_false_positive_delta / p50_latency / p95_latency / hot_memory / build_time / update_cost / index_size / recall_tolerance_violation_count metrics from the existing R33/R34/R36/R24 diagnostics; the synthetic fixture validates only metric NAMES and gates (no per-backend systems bakeoff inputs, no computed metric values). Synthetic / stub reports emit only stage *definitions* (no per-stage `passes=true` / `candidate_set_overlap_at_k` / `gold_retention_delta` / `p50_latency` / `hot_memory` / `build_time` / `index_size`); the skeleton verdict framework emits only `insufficient_data` (synthetic fixture) or `not_implemented` (ci_ephemeral_records stub) — `success` / `failure` / `partial` are reserved for a future empirical `ann_backend_bakeoff_performed=true` / `candidate_set_equivalence_validated=true` / `quiver_graph_implemented=true` path that is NOT present in this skeleton. The `--self-test` is read-only (compares in-memory expected artifacts to on-disk artifacts, fails on drift, does not mutate checked-in artifacts); `--regenerate-artifacts` is the only path that mutates checked-in artifacts; `--input` stub requires explicit `--out` and refuses to write ANY path inside `artifacts/b17_quiver_systems_track/`. The bounded public-systems diagnostic carry-forward / no-go screen (`eval/b17_public_systems_diagnostic_screen.py`) reads the published R33 readiness + R34/R36 anchor-proto + real-provider P3/P4 quiver diagnostics + optional R24 QuIVer/TDB/dense probe and emits `verdict=no_go_quiver_graph_missing` (or `diagnostic_carry_forward_only`); it never claims QuIVer implementation, never computes an ANN metric from diagnostics, never promotes a backend, never changes retrieval policy, and never declares a winner. The existing R33/R34/R36/R24 diagnostics are **diagnostic-only carry-forward** — they are NOT quality proof and NOT promotion evidence; they do NOT implement a QuIVer/Vamana graph backend, do NOT contain an HNSW run, and do NOT contain a candidate-set equivalence matrix across backends. See [`b17-quiver-systems-track.md`](b17-quiver-systems-track.md).

---

## B18 OOD / Temporal Evaluation

B18 is the ood-temporal-evaluation phase that follows B17. The goal is a **frozen, preregistered OOD / temporal evaluation** of the retrieval / candidate / Evidence pipeline across five FROZEN split axes (`temporal_split`, `repo_split`, `language_split`, `model_family_split`, `adversarial_split`) **under a no-retuning protocol** (no policy search, no quality strategy tuning, no retrieval policy change, no EvidenceCore semantics change, no default change, no promotion) so an in-distribution average cannot be mistaken for OOD / temporal generalization. B18 is a **bounded preregistration + public-aggregate no-go screen phase**, NOT a real OOD / temporal evaluation, NOT a policy search, NOT a quality strategy tuning, NOT a default change, NOT an EvidenceCore semantics change, NOT a promotion. Split axes are FROZEN (`temporal_split`, `repo_split`, `language_split`, `model_family_split`, `adversarial_split`). No-retuning protocol is FROZEN (`no_retuning_protocol=true`, `no_policy_search=true`, `no_quality_strategy_tuning=true`, `no_retrieval_policy_change=true`, `no_evidencecore_semantics_change=true`, `no_default_change=true`, `no_promotion=true`). Hard gates (FROZEN): `per_record_data_gate`, `time_axis_gate`, `commit_chronology_gate`, `no_retuning_gate`, `adversarial_holdout_gate`, `temporal_holdout_gate`, `evidencecore_materialization_gate`, `stale_citation_gate`, `privacy_gate`, `promotion_false_gate`. Metric registry (FROZEN, 13 names): `ood_generalization_gap`, `temporal_holdout_delta`, `repo_holdout_metric`, `language_holdout_metric`, `model_family_holdout_metric`, `adversarial_robustness_score`, `worst_group_metric`, `cvar_tail_metric`, `per_cell_denominator`, `temporal_split_integrity`, `no_retuning_proof_metric`, `citation_validity`, `stale_evidencecore_rejection_rate` — every metric requires per-record OOD / temporal inputs (per-record records, per-record time index, per-record commit chronology, per-record repo / language / model_family axes, per-record task category, per-record adversarial holdout membership, per-record temporal holdout membership, per-record outcome label, per-record citation validity, per-record stale rejection, per-record EvidenceCore rejection, per-record randomized run order proof, per-record no-retuning proof, shared frozen evaluation protocol manifest); none can be computed from the B11 aggregate means or from the R15 / R20 / R26 repo locks.

B18 IS the ood-temporal-evaluation *stage* (`stage_is_ood_temporal_evaluation=true`), but the shipped skeleton performs NO real OOD / temporal evaluation (`ood_temporal_evaluation_performed=false`), NO metrics evaluation (`metrics_evaluated=false`), NO policy search (`policy_search_performed=false`), NO quality strategy tuning (`quality_strategy_tuned=false`), and NO promotion (`promotion_ready=false`); the synthetic-fixture / `--input` stub report sets `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `retrieval_policy_changed=false`, `metrics_evaluated=false`, `new_provider_calls=0`, `no_fake_ood_metrics_from_aggregate_means=true` so the public artifact cannot be misread as an empirical B18 OOD / temporal result. **CRITICAL**: the skeleton MUST NOT compute fake ood_generalization_gap / temporal_holdout_delta / repo_holdout_metric / language_holdout_metric / model_family_holdout_metric / adversarial_robustness_score / worst_group_metric / cvar_tail_metric / per_cell_denominator / temporal_split_integrity / no_retuning_proof_metric / citation_validity / stale_evidencecore_rejection_rate metrics from the existing B11 aggregate means or from the R15 / R20 / R26 repo locks; the B11 aggregate carries public model-family means + repo slice list + sanitized failure slices but NO per-record, per-time-index, per-repo-per-language cell, model_family x repo matrix, adversarial holdout outcome, or temporal holdout outcome, and the R15 / R20 / R26 repo locks are synthetic / static snapshots with no real commit chronology or time axis. Synthetic / stub reports emit only stage *definitions* (no per-stage `passes=true` / `ood_generalization_gap` / `temporal_holdout_delta` / `worst_group_metric` / `cvar_tail_metric` / `per_cell_denominator`); the skeleton verdict framework emits only `insufficient_data` (synthetic fixture) or `not_implemented` (ci_ephemeral_records stub) — `success` / `failure` / `partial` are reserved for a future empirical `ood_temporal_evaluation_performed=true` / `metrics_evaluated=true` path that is NOT present in this skeleton. The `--self-test` is read-only (compares in-memory expected artifacts to on-disk artifacts, fails on drift, does not mutate checked-in artifacts); `--regenerate-artifacts` is the only path that mutates checked-in artifacts; `--input` stub requires explicit `--out` and refuses to write ANY path inside `artifacts/b18_ood_temporal_evaluation/`. The bounded public-aggregate no-go screen (`--public-screen --out <path>`, also run from `--regenerate-artifacts`) reads the published B11 prospective matrix aggregate report plus optional R15 / R20 / R26 repos.lock.jsonl files and dataset manifests and emits `verdict=no_go_public_aggregate_only` (or `public_aggregate_carry_forward_only`); it never claims OOD / temporal evaluation, never computes an OOD / temporal metric from aggregate means, never promotes a retrieval variant, never changes retrieval policy, and never declares a winner. The existing B11 / R15 / R20 / R26 aggregates are **aggregate-only / metadata-only carry-forward** — they are NOT OOD / temporal proof and NOT promotion evidence; they do NOT contain per-record records, a time axis, commit chronology, per-repo-per-language cells, a model_family x repo matrix, adversarial holdout outcomes, or temporal holdout outcomes. See [`b18-ood-temporal-evaluation.md`](b18-ood-temporal-evaluation.md).

---

## B19 Theoretical Synthesis — Model-Robust Selective Evidence Conversion

B19 is the **theoretical synthesis** of the B10-B18 Breakthrough Sprint. It is **synthesis-only**: `is_synthesis_only=true`, `is_new_experiment=false`, `ran_providers=false`, `new_provider_calls=0`, `changed_retrieval_default_evidencecore=false`. It does NOT run any provider, does NOT change retrieval / default / `EvidenceCore`, and does NOT claim promotion. It synthesizes B10 / B10B / B11 / B12 / B13 / B14 / B15 / B16 / B17 / B18 into a single paper-style algorithm report for the candidate algorithm concept **Model-Robust Selective Evidence Conversion** — a model-robust, runtime-clean, evidence-gated policy that selectively converts high-reach / high-false-cost local candidate pools into current-source `EvidenceCore` spans by decoupling recall from admission, routing LLM roles selectively, and optimizing worst-group utility across model adapters. Inputs: query, local candidate pool, runtime-observable uncertainty, model capability profile, latency/cost budget. Outputs/actions: local-only, weak/supporting, LLM span-narrow, LLM filter, abstain, request-more-context, then `EvidenceCore` materialization. Core principles: recall/admission decoupling; LLM role-selective routing; algorithm/model-adapter separation; runtime-observable features only (for a runtime-clean policy); worst-group / cross-model robust optimization; candidate must materialize into current-source `EvidenceCore`. Formal sections: problem statement, algorithm sketch/pseudocode, evidence boundary, policy-learning loop, adapter boundary, evaluation protocol, current empirical evidence, no-go gaps, promotion blockers, next research program.

B19 carries forward ONLY already-published public-aggregate findings and introduces NO new empirical claims: **B10** `balanced_policy_v1_benchmark_routed` was benchmark-routed, not runtime-clean (`runtime_clean=false`); **B10B** mechanics-validated runtime-shadow scaffold + CI integration, empirical support pending (label-driven denominator < 10 in all B11 runs); **B11** official integrated matrix 32/32, 384 records, aggregate verdict `partial_with_failure`, balanced_v1 vs p25 deltas `Δgold_span -0.002604` / `ΔSpanF0.5 -0.001899` / `Δfalse_span -0.054688` / `ΔPFP -0.020833` / `Δmodel_calls -0.354167` — strengthens the algorithm-candidate signal but NO promotion; **B12** public aggregate cannot identify mechanism (needs per-record strategy/action outcomes); **B13** public aggregate cannot run real DRO search (needs per-record group/action outcomes); **B14** cannot calibrate uncertainty from public aggregates (needs per-record/model-output structure); **B15** cannot learn Context Pack Policy from public aggregates (current value is preregistration/prior screen); **B16** downstream agent value unproven (needs fixed agent harness with patch/test outcomes); **B17** QuIVer systems track no-go (QuIVer graph/vector backend missing; systems-only future track); **B18** OOD/temporal no-go from public aggregate (needs per-record temporal/repo/language/model/adversarial axes). The public artifact (`artifacts/b19_theoretical_synthesis/b19_theoretical_synthesis_report.json`, schema `b19-theoretical-synthesis-report-v0`) is aggregate-only, runs a B19-specific forbidden-key scan (clean), embeds a self-hash drift guard, and carries the B11 deltas byte-for-byte. `eval/b19_theoretical_synthesis.py` `--self-test` verifies required sections, all no-promotion flags false, B11 deltas exact, forbidden scan clean, docs links exist, and drift guard matched. No fake metrics; no new claims beyond B10-B18. `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `runtime_clean_policy_supported=false`, `downstream_agent_value_proven=false`, `ood_temporal_supported=false`, `quiver_systems_supported=false`. See the [B19 detailed report](b19-theoretical-synthesis.md).

---

## B10-B19 Bottom Line

The B10-B19 Breakthrough Sprint strengthens the **Model-Robust Selective Evidence Conversion** algorithm-candidate signal but does NOT prove a runtime-clean general algorithm, does NOT promote, does NOT change defaults, and does NOT alter `EvidenceCore` semantics. The strongest current empirical evidence is the B11 official integrated matrix (`partial_with_failure`, 32/32, 384 records): balanced_v1 vs p25 preserves near-parity SpanF0.5 / gold_span while reducing false_span, PFP, and model_calls on average. However, B10 `runtime_clean=false` and B10B `runtime_shadow_ambiguous_supported=false` (label-driven denominator < 10) block the runtime-clean generalization claim, and B12 / B13 / B14 / B15 / B16 / B17 / B18 are all public-aggregate no-go or screen-only because every downstream stage lacks the per-record data it requires. The synthesis is a research candidate, not a promotion. Promotion is a separate, future, evidence-gated decision that requires (1) a runtime-clean B10B predicate passing its 10-record hard gate on real CI ephemeral records, (2) per-record mechanism / DRO / calibration / pack-policy / downstream-agent / QuIVer-systems / OOD-temporal evidence, and (3) a separate promotion preregistration. `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `runtime_clean_policy_supported=false`, `downstream_agent_value_proven=false`, `ood_temporal_supported=false`, `quiver_systems_supported=false`.

---

## C4 External Benchmark Adapters — Schema Readiness v1 (2026-06-20)

C4.1 is the **external benchmark adapter / schema readiness** phase. It is **not** an external benchmark performance evaluation, **not** a benchmark result, **not** a downstream agent value proof, and **not** a promotion or default change. It adds one evaluator (`eval/c4_external_benchmark_adapters.py`) and one canonical aggregate-only public artifact (`artifacts/c4_external_benchmark_adapters/c4_external_benchmark_adapter_report.json`, schema `c4_external_benchmark_adapters.v1`, `claim_level=adapter_schema_readiness_only`). The evaluator implements built-in known source/schema metadata for ContextBench (`Contextbench/ContextBench`; `default/train` 1136, `contextbench_verified/train` 500; license `unknown_dataset_license`, row-level redistribution disabled) and SWE-Explore (`SWE-Explore-Bench/SWE-Explore-Bench`; `default/train` 848; license `cc-by-nc-nd-4.0`, row-level redistribution AND derived-label publication disabled), synthetic in-memory row adapters that separate `public_task` (aggregate-safe metadata) from `private_label` (row-level payload never serialized), line range normalization for synthetic self-test / private in-memory validation only, a strict fail-closed forbidden-output scanner for all public JSON outputs, a bounded HF datasets-server schema smoke via stdlib `urllib` only (no new dependencies), and a deterministic `spec_hash` (`9de6609359aa8de4cfe7ca50b1388ebc51d9ee2f016bb3bc6c34e253da5ef153`) that excludes timestamps/network/raw rows/local paths. Row-level benchmark contents (rows, labels, instance IDs, repo URLs/commits/paths, file paths/spans/line ranges, snippets, problem statements, patches/tests, prompts/responses, provider payloads, content_sha, raw HF payloads, response bodies) were NOT persisted in any public artifact or doc.

Validation: `python3 -m py_compile eval/c4_external_benchmark_adapters.py` PASS; `python3 eval/c4_external_benchmark_adapters.py --self-test` PASS (9 groups: ContextBench adapter separation, SWE-Explore adapter separation, line range normalization, forbidden scan rejects injection, no-claim flags exactly false, spec hash deterministic, aggregate-only report, forbidden scan blocks leak at generation, schema smoke report shape); default canonical artifact generation PASS (`forbidden_scan: pass`); real schema smoke commands for ContextBench (`--benchmark contextbench --schema-smoke --limit 3 --out /tmp/c4_contextbench_schema.json` => `forbidden_scan: pass`, `new_network_calls: 4`) and SWE-Explore (`--benchmark swe_explore --schema-smoke --limit 3 --out /tmp/c4_swe_explore_schema.json` => `forbidden_scan: pass`, `new_network_calls: 3`) PASS. The `/tmp` smoke outputs follow the same aggregate-only boundary as the committed artifact.

All no-claim flags remain false: `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `runtime_clean_general_algorithm_claimed=false`, `downstream_agent_value_proven=false`, `ood_temporal_supported=false`, `quiver_systems_supported=false`. The schema smoke confirms only that public HF datasets-server schema endpoints are reachable and parse; it does NOT confirm benchmark quality, label correctness, or fitness for any downstream evaluation. Synthetic self-test rows confer NO empirical support. See the [C4 detailed report](c4-external-benchmark-adapters.md).

---

## 0. Executive Research Thesis

The most important current finding is not that semantic retrieval is solved. It is that OpenLocus now has an evidence-gated research system for studying semantic retrieval, QuIVer, LLM-derived views, graph signals, and admission guards without weakening the evidence contract.

The research posture is now quality/efficiency first, with necessary safety boundaries rather than context starvation. On public corpora or explicit opt-in remote runs, rich code context is acceptable: raw snippets, path/symbol/signature metadata, neighbor windows, top-k local candidates, and retrieval scores should be available to models when that improves quality and speed.

The invariant remains:

```text
candidate != fact
candidate/supporting channels -> current source read -> content_sha/range validation -> EvidenceCore
```

Within that system, real embedding models now show **candidate/file-level recall signal**, but the L1/L2 large-slice tests also show that dense-only/global dense is unstable at larger scale, with low SpanF0.5 and high primary false-positive risk. P20-LS-A similarly shows that low-context/query-only LLM aliases are not enough. RRF remains the recall base, symbol/regex remain precision anchors, and `query_noise_plus_rrf_agree_min` remains the strongest current guard candidate. Dense, QuIVer, LLM-derived views, and graph signals must remain candidate/supporting/diagnostic layers for now, but P21-G should test cross-model context injection rather than continuing metadata-only model inputs or single-model token sweeps.

---

## 1. Evidence Strength

| Evidence tier | What it supports | What it does not support |
|---|---|---|
| **Strong: EvidenceCore, materialization gates, citation validation, CI privacy gates** | Fact authority is working: current-file validation, `content_sha`, strict line ranges, citation validity, RUN/SCORE separation, secret/private-label exclusion. | Does not prove any retrieval strategy should be default, and should not force low-context model inputs on public/opt-in runs. |
| **Strong for failure discovery: R29 on R26 auto-stress 1100 tasks** | RRF/symbol/guard/dense_mock/graph failure patterns are visible across broad stress buckets. | R26 labels are weak/mined/deterministic; not human promotion evidence. |
| **Moderate: real-provider P8/P9 CI scale-up** | Real embeddings show initial, repeatable file-level recall signal on bounded public repo slices; QuIVer BQ diagnostics are worth continuing. | Samples are small; span quality and default safety are not proven. |
| **Moderate-to-strong negative evidence: L1/L2 large-repo slices** | Dense-only/global dense is unstable on larger slices; all four L2 repos had PFP=`1.0`, and SpanF0.5 remained extremely low. | Still not a full-repo exhaustive benchmark; does not prove rich raw-code embedding views are useless. |
| **Directional: P1-P7 self-tests and bounded runs** | Provider, LLM status, local harness, and initial anchor-seeded hypotheses work mechanically. | Tiny/self-test outcomes can be contradicted by larger public corpus runs. |
| **Not quality evidence: dense_mock, LLM-generated stress, unavailable QuIVer/TDB** | Useful for failure discovery and plumbing. | Must not be used as semantic quality or promotion evidence. |

---

## 2. Main Research Conclusions

### 2.1 RRF is still the recall base

RRF remains the strongest recall channel on R26/R29: FileRecall@1 is about `0.803`, and FileRecall@5 is about `0.923`. This confirms that fusing local lexical/symbol channels improves coverage.

Its main risk is also clear: high primary false-positive rate, about `0.453` in R29. RRF is a strong recall base, but it should not directly become primary admission without guards, anchors, or an admission model.

### 2.2 Symbol and regex are precision anchors

Symbol search remains the precision anchor. In R29 it has SpanF0.5 around `0.291` and primary_false_positive_rate around `0.080`. Its weakness is high abstention and incomplete extraction coverage, not excessive noise. This makes symbol extraction repair a promising recall-safe improvement path.

Regex remains a foundational anchor too, but it needs normalization. User queries should not default to raw regex. The system needs separate modes for literal search, explicit regex search, identifier search, and path search. R39/R40 support continuing validation of `regex_hybrid_normalized`.

### 2.3 `query_noise_plus_rrf_agree_min` is the best current guard candidate

In R29, `query_noise_plus_rrf_agree_min` preserved RRF recall while reducing primary false-positive rate from about `0.453` to about `0.106`, with guard_recall_kill_rate around `0.003`. This is the clearest current guard signal.

It still cannot be promoted. R23 showed many bucket regressions, and R26/R29 are not human-reviewed promotion tiers. It is a strong guard candidate for continued study, not a default strategy.

### 2.4 Real embeddings help file recall but not span evidence yet

P8/P9 CI scale-up showed initial, repeatable file-level recall signal on bounded public corpus slices. For example, the bounded Flask P2 run achieved FileRecall@1=`0.800` and FileRecall@3=`1.000`; in the multilingual bge-m3 smoke, Go/Python were strong, Rust was moderate, and JavaScript Express was weaker.

The later L1/L2 large-slice tests weakened this optimistic signal. At 60 tasks / 1000 records / 2000 files, Django/Kubernetes dropped to roughly `0.25` FileRecall@1, Next.js/Deno were near `0`, all four repos had primary_false_positive_rate=`1.0`, and the best SpanF0.5 was only about `0.022`. Dense retrieval is currently a candidate-support channel, not a primary span-evidence channel.

### 2.5 Bigger embedding models did not dominate in the first slice

P9a compared `BAAI/bge-m3`, `Qwen/Qwen3-Embedding-0.6B`, `Qwen/Qwen3-Embedding-4B`, and `Qwen/Qwen3-Embedding-8B` on the same Flask slice. In this small sample, the largest model did not dominate: bge-m3 and Qwen 0.6B/4B reached FileRecall@1=`1.000`, while 8B reached `0.800`.

This does not prove smaller models are better, but it is enough to avoid assuming the largest model is best without same-task bakeoffs. Future bakeoffs should compare models on the same tasks, corpus, caps, latency, and cost.

### 2.6 Anchor-seeded dense/QuIVer is promising but not safe yet

Early tiny/self-tests made anchor-seeded dense/QuIVer look promising: P4 once showed added_gold=`2` and added_false=`0`. But P8a on a real public Flask slice produced the opposite caution signal: FileRecall@1=`1.000`, but added_gold=`3` and added_false=`15`.

L1 P4 strengthened the block: on `py_django`, the best anchor strategy had added_gold=`0` and added_false=`40`; on `go_kubernetes`, it had added_gold=`5` and added_false=`44`.

This is exactly why the research harness matters: a small optimistic signal was constrained by a more realistic corpus slice. The conclusion is not that anchor-seeding is useless; it is that anchor-seeded dense/QuIVer must remain supporting-only while span targeting and false-span suppression are improved.

### 2.7 QuIVer is still diagnostic, but BQ signals are no longer empty

P3 ran BQ readiness diagnostics on real embeddings. On the Flask slice, BQ_overlap@10=`0.680`, BQ_overlap@50=`0.728`, BQ_vs_f32_MRR=`1.000`, and quiver_fit was marked `promising`. This means the BQ/QuIVer direction is worth continuing.

L1 P3 kept BQ diagnostics non-empty on larger slices: Django was marked `promising`, Kubernetes `mixed`. This remains BQ diagnostic evidence only, not QuIVer graph/ANN quality.

But the QuIVer graph/Vamana backend is not implemented, and no ANN graph quality claim exists yet. QuIVer remains diagnostic/prototype-only.

### 2.8 Graph expansion remains blocked

R25/R29/P6 support the same conclusion: graph is not safe as default expansion. In R29, graph_basic added_gold=`0` and added_false=`437`. Graph is more likely useful as an explainer, rerank feature, impact signal, or test selector than as default recall expansion.

### 2.9 LLM-derived views are useful for stress and hints, not facts

The real LLM provider has run successfully, and P5 generated derived/stress outputs. These outputs must remain `not_evidence=true`: the LLM must not generate Evidence, gold labels, citation verdicts, or promotion verdicts.

The useful role for LLMs is query aliases, symbol tags, intent views, candidate rerank/filter/span narrowing, and failure/stress generation. LLMs can expand the failure surface and help interpret rich candidate context, but they cannot replace EvidenceCore.

P20-LS makes this boundary executable: LS0 validates safety gates, LS1 generates `not_evidence=true` query aliases and evaluates them as candidate/supporting-only retrieval expansion, and LS3 writes only the public stress split by default. The initial offline slice was already a caution signal. P20-LS-A then ran the real LLM provider (`Kimi-K2.7-Code`) on self-test plus 9 real CI corpus runs. Schema/guardrail behavior was acceptable, but low-context/query-only alias quality failed completely: 0/9 real runs passed quality, added_gold_span=`289` vs added_false_span=`8312` (~28.8:1 false:gold), and average fabricated_identifier_rate was ~`0.459`. Therefore, scale-up is blocked for the low-context/query-only alias mode. This is not a verdict on rich-context LLM retrieval; future alias/retrieval research should use source snippets, candidate metadata, symbol/path inventories, and prompt/context matrices.

### 2.10 P21-G should study cross-model context injection effects

The next model phase should stop treating metadata-only remote inputs as the default research posture, but it should also avoid pretending that one model's best token budget is an OpenLocus-wide law. For public corpora and explicit opt-in remote runs, models should receive enough code facts to be useful: raw code snippets, path headers, signatures, symbol bodies, neighboring lines, local retrieval scores, hard distractors, and top-k candidate sets. Necessary boundaries remain: exclude secrets, ignored files, provider keys, and private labels/gold answers; keep EvidenceCore as final fact authority; do not use LLMs as promotion judges.

P21-G should compare context atoms and packs across embedding and LLM model profiles, query buckets, repo types, roles, and layouts. The primary variables are not fixed token caps but injected information: signatures, matched lines, source/test/doc flags, retrieval scores, body windows, neighbor symbols, related tests, hard distractors, candidate uncertainty, and inventory grounding. P21-G1E showed naked dense context atoms remain supporting-only: `pack2_evidence_sketch` had the best model-averaged SpanF0.5 and `atom_signature` the best FileRecall@5, but false spans dominated (`17924` vs `2876`). P21-G2E showed constrained dense has modest supporting value: `dense_atom_signature_rrf_file_constrained` averaged SpanF0.5 `0.163` vs RRF `0.1508`, PFP avg `0.0`, useful in `11/16` runs. Dense remains non-primary. P21-G3L showed LLM rich candidate roles can help but are model/repo specific: `llm_span_narrow` had avg ΔSpanF0.5 `+0.0418`, with strongest signal from Flash/Kimi on `py_flask`; filter/abstain reduced false spans but often killed gold; GLM-5.1 schema degradation blocks scale-up until prompt/schema repair. Every report must measure quality, efficiency, and cross-model generalization: SpanF0.5, added_gold/false, PFP, provider calls, input/output tokens/chars, p50/p95 latency, cost, model-averaged treatment effect, per-model effect, and effect variance.

P21-G3L-R is now the structured-output repair path for LLM roles. The rich-candidate harness supports `prompt_only`, `json_object`, `json_schema_strict`, and `tool_call` output modes, records provider-rejection fallback diagnostics, and allows one schema repair retry without another fallback ladder. The first GLM-focused smoke ran 4 output modes × 2 repos: `tool_call` is the preferred GLM mode so far (avg SpanNarrow Δ `+0.0677`, repair success `3/5`), `prompt_only` should be blocked, `json_object` remains insufficient, and `json_schema_strict` is mixed. A sequential low-concurrency `tool_call` rerun removed provider HTTP 429 noise and improved GLM SpanNarrow avg Δ to `+0.1361`; use GLM `tool_call` for the next bucketed P21-G3L run.

P21-G3B adds public-safe bucket sampling (`task_bucket` and `task_risk_tags`) and confirms that global LLM roles are unsafe across mixed buckets. In the 6-run bucketed smoke, LLM roles reduced PFP but frequently killed gold spans. `span_narrow` remains useful on likely-positive/high-confidence tasks, but it is not a cross-bucket default. `filter` and `abstain` should be routed only to negative/dense-false-positive/ambiguous buckets, not applied globally.

P22/P23 shifts the next phase from channel testing to evidence-seeking policy surfaces. The current freeze has two separate local, no-remote decision surfaces: `r20_positive` for positive candidate reach and `r26_guard` for no-gold guard stress. On the capped R20 positive slice, RRF remains the reach base (`Reach@5=0.975`, `SpanReach@5=0.95`), but symbol has the best local SpanF0.5 (`0.3169`), and `symbol_regex_union` is the best precision/reach experimental baseline candidate for P25/P30. On R26, BM25/RRF still create no-gold false primary (`0.2833`), while symbol/regex/union/guard abstain. This confirms P25/P30 must optimize policy surfaces separately: reach preservation, false-primary suppression, and EvidenceCore materialization are distinct success layers.

### 2.11 P25 bucket-routed LLM role policy evaluator is ready

`eval/p25_bucket_policy.py` is a deterministic, no-remote policy evaluator. The
committed report is a sanitized self-test scaffold (`status=self_test_only`,
`not_quality_evidence=true`), not quality evidence. Real P25 evaluation now
requires ephemeral SCORE-phase records from
`eval/p21_llm_rich_candidate.py --p25-policy-records-out`; those records remain
under runner temp and are not uploaded, while P25 uploads aggregate metrics only.
The `bucket_routed_v0` policy routes by allowlisted public `task_bucket`/
`task_risk_tags`: `llm_span_narrow` for likely-positive/high-confidence buckets,
fixed a-priori `llm_filter`/`llm_abstain_filter` for negative/
dense-false-positive/ambiguous buckets, skips LLM for exact-symbol-plus-unique
anchors, and otherwise falls back to the candidate baseline. Aggregate P21
summaries and non-ephemeral schemas are rejected with
`status=insufficient_task_detail`. This provides a scaffold for future P25/P30
evidence-seeking policy surfaces, not a promotion claim.

The first real P25 remote smoke used this safe P21→P25 ephemeral handoff on six
successful aggregate runs (`Flash/Kimi/GLM × py_flask/js_express`, 18
bucket-sampled tasks each). `bucket_routed_v0` reduced added false spans
`108 -> 28` and mean PFP by about `0.0926`, but also reduced added gold spans
`24 -> 21`; mean SpanF0.5 delta was only slightly positive (`+0.0026`) and
repo/model-dependent. Therefore P25 is useful as a false-primary reducer signal
for P30 Admission V3, not a default policy.

### 2.12 P30 Admission Model V3 scaffold is ready

`eval/p30_admission_model_v3.py` is a deterministic, no-remote admission model
research harness (schema `p30-admission-v3-report-v1`). The committed
self-test artifact is a sanitized synthetic scaffold
(`status=self_test_only`, `not_quality_evidence=true`), not a quality result.
Real P30 evaluation requires the same ephemeral
`p25-policy-records-ephemeral-v1` records produced by
`eval/p21_llm_rich_candidate.py --p25-policy-records-out`; those records stay
under runner temp and are not uploaded, while P30 uploads aggregate metrics
only.

P30 routes only from RUN-phase public/observable features: public
`task_bucket`, `task_risk_tags`, and `route_features`. `score_group`,
`has_gold`, gold spans, private labels, and outcome metrics are used only for
aggregate scoring after actions are chosen. Allowed actions are `abstain`,
`admit_symbol_regex_union`, `admit_rrf_primary`, `admit_llm_span_narrow`,
`apply_llm_filter`, `supporting_only`, and `weak_candidate_only`. The
`admission_v3` scorecard combines explainable monotonic feature scores (query
noise, exact/unique symbol anchor, symbol/regex/local anchors, RRF backed by
anchor, LLM span-narrow validity/within candidate) with hard guards for
negative/ambiguous/dense-false-positive buckets. Dense and graph signals are
allowed only as supporting features; they cannot invent primary evidence.

The evaluator compares `candidate_baseline`, `llm_span_narrow`, `llm_filter`,
`llm_abstain_filter`, `bucket_routed_v0` (reused from P25), and
`admission_v3`. It reports task count, SpanF0.5, PFP, added gold/false spans,
filter gold kill rate, abstain rate, action counts, score bands,
selective risk proxy, mean deltas versus the candidate baseline and
`bucket_routed_v0`, and explicit outcome-fallback counters for actions that do
not have measured outcomes in a given ephemeral record. Public output is
recursively scanned for forbidden keys
(raw query/snippet/prompt/response/gold/gold_spans/private labels/provider
keys). `promotion_ready=false`, `default_should_change=false`,
`evidencecore_semantics_changed=false`, `candidate_not_fact=true`,
`external_calls=0`.

P30 is not a promotion candidate. The next step is to run it against real P25
ephemeral smoke records and compare the scorecard to P25 `bucket_routed_v0`
and the P22/P23 evidence-seeking guard surfaces.

The first real P30 remote smoke completed six successful runs
(`Flash/Kimi/GLM × py_flask/js_express`, 18 bucket-sampled tasks each). It
confirmed that the current `admission_v3` scaffold is too conservative:
baseline produced `27/102` added gold/false spans, P25 `bucket_routed_v0`
produced `19/39`, and P30 `admission_v3` produced `17/41`. P30 matched the mean
PFP reduction (`-0.0833`) but had worse mean SpanF0.5 delta than
`bucket_routed_v0` (`-0.0102` vs `+0.0010`). Non-zero fallback counts show the
current ephemeral handoff lacks measured outcomes/features for the richer local
admission actions. Next: extend P21/P22 handoff with measured
`symbol_regex_union` / `rrf_primary` outcomes and safe route features before
rerunning P30.

P30-H1 implemented that handoff repair. It succeeded as measurement repair but
failed as policy improvement. Six real runs produced zero selected-action
fallback for `admission_v3_h1`, so the comparison is now quality-comparable.
However, P25 `bucket_routed_v0` remained better: `20/37` added gold/false with
mean ΔSpanF0.5 `+0.0020`, versus P30-H1 `18/87` with mean ΔSpanF0.5 `-0.0350`.
The new conclusion is that missing handoff was masking a scorecard problem:
`admit_symbol_regex_union` is too broad and admits many false spans. Next P30-H2
should make local-anchor admission stricter instead of adding more channels.

P30-H2 made local-anchor admission stricter, but this also failed as a quality
repair. It stayed fallback-free and quality-comparable, but produced `15/90`
added gold/false versus H1 `18/87` and P25 `bucket_routed_v0` `16/36`; mean
ΔSpanF0.5 was `-0.0370` for H2 versus `-0.0346` for H1 and `-0.0052` for P25.
The updated diagnosis is that primary-admission breadth was not the only issue:
weak/supporting/filter actions still preserve too much span-level false cost.
P30-H3 now models action-specific span cost and false-span budgets as a
score-phase-only, diagnostic accounting layer. It does not change admission
routes; it derives per-action cost from the existing `bucket_routed_v0`,
`admission_v3_h1`, `admission_v3_h2`, and baseline comparison policies, and emits
a dedicated `artifacts/p30_admission_v3/p30_h3_span_cost_report.json` artifact
with schema `p30-h3-action-span-cost-report-v1`.

The real P30-H3 smoke (6 successful runs, 108 tasks) explains the P30 failure
mode more precisely. Baseline was `27/102` added gold/false spans; P25
`bucket_routed_v0` remained the strongest reference at `19/45`; P30-H1 was
`18/88`; P30-H2 was `15/90`. H3 shows P30-H1/H2 false-span cost is dominated
by primary local-admit actions (`admit_symbol_regex_union`, and H2
`admit_rrf_primary`), while `supporting_only` mainly costs recall by killing
gold rather than adding false spans. Therefore P30-H4 should use explicit
action budgets for primary local-admit actions instead of globally tightening
all non-primary actions.

### 2.13 P31 Candidate Reach Ceiling Study scaffold is ready

`eval/p31_candidate_reach_ceiling.py` is a deterministic, no-remote diagnostic
scaffold (schema `p31-candidate-reach-ceiling-report-v1`). The committed
self-test artifact is sanitized synthetic data (`status=self_test_only`,
`not_quality_evidence=true`), not quality evidence. P31 is SCORE-phase-only:
labels are loaded only after RUN and are used only for aggregate metrics. It
does not influence routing or admission decisions.

P31 measures whether candidate evidence alone reaches the gold label before any
routing or admission. Inputs are the same ephemeral
`p25-policy-records-ephemeral-v1` records used by P25/P30. When records do not
yet carry candidate evidence pools, P31 reports
`candidate_pool_availability=missing_candidate_pool` and
`reach_metrics_available=false`, then computes outcome-only fallback metrics
rather than fabricating reach zeros. When pools are present, it reports
aggregate `GoldFileReach@K`, `GoldSpanReach@K`, `GoldSpanExactReach@K`,
`CandidateAbsentRate@K`, and `FileRightSpanWrongRate@K` for K=1/3/5/10/20, plus
`ModelMissGivenGoldPresent@K` against `candidate_baseline`, action/strategy
diagnostics (`FilterKillGoldRate`, `AdmissionFalsePrimaryRate`,
`AdmissionFalseSpanPerNoGoldTask`), `EvidenceCoreRejectRate` (`not_measured`
when rejection fields are not present), and a K=5 failure funnel with
`funnel_sums_to_positive_tasks=true`.

P31-H1 extends the P21 rich-candidate handoff so ephemeral records now carry
lightweight candidate pools (`p31_candidate_pools`) and private SCORE-phase gold
spans (`p31_score_gold`), tagged with `p31_h1_candidate_reach_handoff=true` and
`p31_h1_schema_version="p31-h1-candidate-reach-handoff-v1"`. Pool items keep only
`rank`, `path`, `start_line`, `end_line`, plus optional `content_sha`, `score`,
and `channels`; no snippets, raw queries, prompts, responses, or provider fields.

P31-H2 adds a strategy-level reach matrix across `candidate_baseline`,
`rrf_primary`, `symbol_regex_union`, `llm_span_narrow`, `llm_filter`, and
`llm_abstain_filter`. It reports reach@K per strategy and, when H1 pools are
present, aggregate reach by public repo and task bucket, unique reach share,
pairwise file/span overlap and Jaccard span, marginal gain in both directions,
and union reach for fixed strategy combinations. Missing strategy pools are
reported as `availability=missing_pool`, not fake zeros.

Public artifacts are aggregate-only: no per-task rows, raw queries, snippets,
prompts, responses, candidate paths/spans, gold spans, private labels, or
provider fields. Safety flags are locked: `promotion_ready=false`,
`default_should_change=false`, `evidencecore_semantics_changed=false`,
`candidate_not_fact=true`, `remote_calls_by_p31=0`,
`score_phase_only_metrics=true`, `aggregate_only_public_artifact=true`.

The real P33-B subtype smoke (6 successful runs, 108 task observations: 36
positive and 72 no-gold) confirms the P33 result at finer granularity: no
observed subtype bucket is primary-safe. `span_overlap` is the best coarse
agreement class (`GoldSpanReach=1.0`, `false_per_gold≈1.78`) but remains
net-negative under a 2x false-span penalty. `symbol_regex_fusion` also has
perfect subtype span reach in this smoke but still costs `24/66` added
gold/false (`false_per_gold=2.75`). `same_file_only` is weaker
(`false_per_gold≈2.18`), and `disagree` / `single_source` buckets are dominated
by false-span cost. RRF backing helps but does not make anchors safe
(`rrf_yes false_per_gold≈4.67`). P33-B subtype buckets should therefore feed
P32/P30-H4 action budgets, not primary admission.


The first real P31-H1 reach smoke completed six successful runs
(`Flash/Kimi/GLM × py_flask/js_express`, 108 total tasks, 48 positive tasks).
H1 handoff was detected in every run and reach metrics were available in every
run. Candidate baseline reached only `24/48` positive tasks at both file and
span level at K=5 (`GoldFileReach@5=0.5000`, `GoldSpanReach@5=0.5000`), while
`FileRightSpanWrongRate@5=0/24`. This points to candidate absence as the first
bottleneck in this smoke, not within-file span localization. P25
`bucket_routed_v0` still had lower false-span cost than P30-H1/H2 on the same
runs (`20/46` added gold/false vs H1 `18/87`, H2 `15/90`), but P31 shows
admission tuning alone cannot recover the missing half of positive tasks.

The P31-H2 strategy reach matrix rerun shows why the next repair should target
anchors, not another LLM role. At K=5, `candidate_baseline` reaches `24/48`
positive spans, `rrf_primary` reaches `21/48`, and `symbol_regex_union` reaches
`42/48`. `symbol_regex_union` contributes `18/48` unique span hits, while
`candidate_baseline + rrf_primary` and `candidate_baseline + llm_span_narrow`
remain at `24/48`. Therefore `symbol_regex_union` is a high-reach candidate
expansion source, but P30-H3 already showed it is unsafe when admitted directly
as primary. The next steps are P33 anchor repair/calibration and P32/P30-H4
action budgets before local-anchor primary admission.

The first real P33 anchor precision smoke confirms that no observed anchor
bucket is primary-safe yet. The strongest calibration cell (`a3_r0_s2`: span
agreement, low-risk, RRF-span-backed) reaches `42/48` positive spans, but has
`false_per_gold≈8.69` and `net_span_value_2x=-786`. `symbol_regex_agree_span`
reaches `9/9` positives in its bucket, but still has `false_per_gold=4.0`;
`symbol_regex_disagree` reaches `27/30` but has `false_per_gold≈13.44`, and
`regex_only` is worse (`false_per_gold=22.5`). Therefore P33 preserves the
P31-H2 conclusion that anchors are the main reach lever, while strengthening
the P30-H3 conclusion that anchor primary admission must be budgeted. P33-B
should now repair/calibrate symbol and regex subtypes; P32/P30-H4 should not
promote any local-anchor bucket without held-out budget validation.

### 2.14 P33 Reach-Preserving Precision Anchor Repair scaffold is ready

`eval/p33_anchor_precision_repair.py` is a deterministic, no-remote diagnostic
scaffold (schema `p33-anchor-precision-repair-report-v1`). It consumes the same
P21/P31-H1 ephemeral records that P31 uses: it needs `p31_candidate_pools`,
`p31_score_gold`, public `task_bucket`/`task_risk_tags`, and pre-SCORE
`route_features`. Labels and gold spans are used only in the SCORE phase for
aggregate metrics. When candidate pools or gold spans are missing, P33 reports
`availability=missing_pool`/`not_measured` rather than fabricating zeros.

P33 defines an anchor taxonomy v1 with buckets such as
`exact_unique_symbol_anchor`, `unique_symbol_anchor`, `symbol_anchor_only`,
`regex_anchor_only`, `symbol_regex_agree_span`/`agree_file`/`disagree`,
`rrf_anchor_agree_span`/`agree_file`/`unbacked`, public buckets
(`positive`/`ambiguous`/`negative`), risk tags (`hard_distractor`,
`dense_false_positive`), query-noise levels, and bounded composites like
`symbol_regex_agree_span_low_risk`, `rrf_span_backed`, and
`negative_or_ambiguous_with_anchor`. For each bucket it reports task counts,
positive/no-gold counts, `GoldFileReach@5`, `GoldSpanReach@5`,
`FileRightSpanWrongRate@5`, span cost aggregates (`added_gold_span`,
`added_false_span`, `false_per_gold`, `gold_per_false`, `net_span_value_1x/2x`),
mean `SpanF0.5` and mean `primary_false_positive_rate`, and a diagnostic class
(`primary_candidate_safe_observed`, `supporting_only_observed`,
`needs_budget_guard`, `blocked_high_false_cost`, or
`insufficient_denominator`).

A 3D calibration matrix over `anchor_strength` (0=none, 1=symbol_or_regex_only,
2=file_agreement, 3=span_agreement, 4=exact_unique_symbol_span_agreement),
`risk_level` (0=low/positive, 1=ambiguous, 2=negative/high risk), and
`rrf_backing_level` (0=none, 1=file-only, 2=span) reports the same aggregate
diagnostics and flags monotonic-sanity violations. A `p33_to_p32_handoff` section
groups budget candidates by diagnostic class, with `frozen_policy=false`.

Public artifacts are aggregate-only: no per-task rows, task IDs, raw queries,
snippets, prompts, responses, route features, candidate paths/spans, gold spans,
private labels, or provider fields. Safety flags are locked:
`promotion_ready=false`, `default_should_change=false`,
`evidencecore_semantics_changed=false`, `candidate_not_fact=true`,
`remote_calls_by_p33=0`, `score_phase_only_metrics=true`,
`aggregate_only_public_artifact=true`.

### 2.15 P33-B Anchor Subtype Calibration scaffold is ready

`eval/p33b_anchor_subtype_calibration.py` is a deterministic, no-remote diagnostic
scaffold (schema `p33b-anchor-subtype-calibration-v1`). It extends the P21
ephemeral handoff with private per-candidate subtype metadata
(`p33b_anchor_subtypes`, schema `p33b-anchor-subtypes-v1`) describing each
`symbol_regex_union` candidate as `symbol_only`, `regex_only`, or
`symbol_regex_fusion`, with agreement classes (`single_source`, `same_file_only`,
`span_overlap`, `disagree`), `rank_bin`, `candidate_count_bin`,
`span_width_bin`, and per-candidate `rrf_backing`. The handoff also adds
`symbol_primary` and `regex_primary` candidate pools for P31 reach studies.

P33-B consumes those ephemeral records, joins private subtype rows to the
`symbol_regex_union` candidates, and uses `p31_score_gold` and strategy outcomes
only in the SCORE phase for aggregate metrics. It reports bounded subtype-bucket
diagnostics: task counts, positive/no-gold counts, `SubtypeGoldFileReach@5`,
`SubtypeGoldSpanReach@5`, `FileRightSpanWrongRate@5`,
`UniqueSubtypeSpanReach@5`, span cost aggregates with coarse task-level
attribution, `delta_vs_candidate_baseline`, and diagnostic classes with minimum
denominator gating. A 3D calibration matrix over `source_strength` (0=regex_only,
1=symbol_only, 2=symbol_regex_fusion), `match_quality` (0=disagree,
1=same_file_only, 2=span_overlap_unbacked, 3=span_overlap_rrf_backed), and
`risk_level` reports the same diagnostics plus monotonic-sanity checks. A
`p33b_to_p32_handoff` groups budget candidates by diagnostic class, with
`frozen_policy=false`.

Public artifacts remain aggregate-only: no per-task rows, task IDs, raw queries,
snippets, prompts, responses, candidate paths/spans, gold spans, private labels,
route features, subtype rows, or provider fields. Safety flags are locked:
`promotion_ready=false`, `default_should_change=false`,
`evidencecore_semantics_changed=false`, `candidate_not_fact=true`,
`remote_calls_by_p33b=0`, `score_phase_only_metrics=true`,
`aggregate_only_public_artifact=true`.

### 2.16 P32 / P30-H4 deterministic budget overlay is ready

`eval/p30_admission_model_v3.py` now implements `admission_v3_h4`, a P32/P30-H4
budget-overlay policy. H4 is deterministic, no-remote, and diagnostic-only. It
reads private P33-B subtype metadata from the P21 ephemeral handoff
(`p33b_anchor_subtypes`, `p33b_anchor_subtypes_schema`) and uses it, together
with RUN-phase public features, to test budgeted demotion. It does not change
Rust/EvidenceCore semantics, the default pipeline strategy, or any production
admission route.

P33-B showed that no subtype is primary-safe: even the best `span_overlap`
bucket has `false_per_gold≈1.78` and negative `net_span_value_2x`, while
`disagree` and `single_source` are dangerous and `same_file_only` is weaker.
Consequently H4 never selects `admit_symbol_regex_union`, `admit_rrf_primary`,
or `admit_llm_span_narrow` from subtype evidence alone. Its actions are limited
to `apply_llm_filter`, `supporting_only`, `weak_candidate_only`, and `abstain`.
Rules are conservative: negative/dense/ambiguous tasks are filtered or
abstained; `span_overlap` in low-risk public buckets becomes `supporting_only`
when RRF-backed and `weak_candidate_only` otherwise; `same_file_only` becomes
`weak_candidate_only` only in clearly positive buckets; `disagree`/
`single_source` are filtered unless the public bucket is strongly positive and
query noise is low. Missing subtype metadata degrades to a `bucket_routed_v0`-
like conservative fallback.

The normalized in-memory task carries the private P31/P33-B handoff fields
(`p31_candidate_pools`, `p31_score_gold`, `p33b_anchor_subtypes`,
`p33b_anchor_subtypes_schema`) for SCORE-phase use, but these keys are never
emitted in public P30 artifacts. Report flags are locked to
`h4_budget_overlay=true`, `promotion_ready=false`,
`default_should_change=false`, and, when P33-B records are present,
`h4_available=true` / `p33b_handoff_detected=true`. H4 reports
`quality_comparable`, `blocked_by_missing_action_outcomes`, and
`selected_action_fallback_rate` like H1/H2, and the real-provider CI gate now
requires H4 to exist and, on `p21_llm_rich` records, to be quality-comparable
with zero selected-action fallback.

The first real P30-H4 remote smoke completed 6 successful runs. It was
quality-comparable and fallback-free, but it was too conservative: H4 produced
`0` added gold spans and `0` added false spans, with mean SpanF0.5 `0.0000`.
P25 `bucket_routed_v0` remains the best reference on the same runs (`27/34`
added gold/false, mean SpanF0.5 `0.0768`). H4 is therefore a safety lower bound
and useful negative result, not a deployable admission policy. The next H4
iteration should test budgeted selective re-admission or `request_more_context`,
not all-demotion.

### 2.17 P32 / P30-H4B selective primary re-admission is ready

`eval/p30_admission_model_v3.py` now also implements `admission_v3_h4b`, a P32/P30-H4B
selective primary re-admission diagnostic. H4B is deterministic, no-remote, and
diagnostic-only. It uses the same private P33-B subtype handoff and RUN-phase
public features as H4, but tests an extremely narrow strict conjunction for
primary-admit actions rather than demoting everything.

The strict gate selects `admit_symbol_regex_union` only when the best subtype is
`symbol_regex_fusion` + `span_overlap` + `rrf_backing`, `local_anchor` and
`symbol_regex_agree_span` are true, `query_noise <= 0.1`, the public bucket/tag is
in a low-risk positive set, and either `exact_unique_symbol_anchor` or
`rrf_anchor_agree_span` holds. If `rrf_backed_by_anchor` and
`rrf_anchor_agree_span` also hold, H4B may optionally select `admit_rrf_primary`
instead. All other tasks are hard-guarded or demoted, including negative/dense/
ambiguous/hallucination/high-noise cases and any best subtype that is
`regex_only`, `same_file_only`, `disagree`, or `single_source`.

Public outputs include `h4b_available`, `h4b_budget_overlay=true`,
`h4b_selective_readmission=true`, `h4b_primary_opportunity_count`, and rule
aggregate counts (`strict_union_re_admit`, `strict_rrf_re_admit`, `hard_guard`,
`missing_handoff`, `demote_span_overlap`, `demote_same_file`,
`filter_dangerous_subtype`). H4B also reports `quality_comparable`,
`selected_action_fallback_rate`, `false_per_gold`, `net_span_value_2x`, and a
span-cost summary from P30-H3 accounting. On synthetic self-test it is
quality-comparable and fallback-free, and fires a small number of strict primary
opportunities. The real H4B smoke completed 6 successful provider runs: H4B is
quality-comparable and fallback-free, and it escapes H4A's all-demotion failure
(`0/0 -> 24/41` added gold/false). It still does not beat P25
`bucket_routed_v0` (`25/30` added gold/false, mean SpanF0.5 `0.0683` vs H4B
`0.0433`), so H4B is a promising research direction but not a promotion
candidate. The next iteration should tighten strict RRF re-admission or use
`request_more_context` before primary admission.

---

## 3. Current Hypotheses

| Hypothesis | Current state | What would confirm it |
|---|---|---|
| RRF should remain the recall base. | Strongly supported by R29, but needs guard. | Stable recall under guard across human-reviewed and stress tiers. |
| Symbol/regex should be precision anchors. | Strongly supported. | Broader symbol repair validation without PFP increase. |
| Dense should remain supporting-only for now. | Current L1/L2 evidence blocks dense-only/global dense as primary/default. | Rich raw-code/snippet views add gold more than false spans with low PFP and acceptable latency/cost. |
| Anchor-seeded dense/QuIVer may be safer than global dense. | Plausible but mixed. | P4-like tests on multiple repos show repeatable false-span suppression. |
| BQ diagnostics may be compatible with current code-embedding distributions. | Diagnostic signal promising on Flask. | Sharded BQ/proto graph beats flat f32 or improves latency without false-span growth. |
| Smaller embedding models may be enough. | Initial P9 supports continued bakeoff. | Same-task model bakeoff across more repos with latency/cost. |
| LLM-derived views can expand failures safely. | Mechanically supported, not quality-proven. | Rich context derived views add gold or stress coverage without inducing primary hallucinations. |
| LLM query aliases can improve anchors without pollution. | Low-context P20-LS-A query aliases are blocked for `Kimi-K2.7-Code`: 0/9 real quality pass, false:gold span ≈28.8:1, avg fabricated identifier rate≈0.459. | A grounded variant succeeds: aliases selected from repo inventories or top-k candidate context, `alias_added_gold > alias_added_false`, no PFP increase, low fabricated identifier rate. |
| Context atoms can generalize across model families. | Planned P21-G hypothesis. | Signature/matched-lines/scores/flags/body-window atoms show positive model-averaged treatment effect with low model variance and no PFP increase. |
| Rich LLM candidate support can improve span targeting. | Planned P21-G role hypothesis. | Rerank/filter/span-narrow over snippet-backed local candidates improves SpanF0.5 and reduces false spans at acceptable latency/cost. |

---

## 4. Contradictions and Negative Results

These negative results are among the most valuable findings because they prevent premature optimism:

1. **P4 tiny optimism weakened by P8a**: tiny self-test had added_false=`0`; the public Flask slice had added_false=`15`.
2. **Dense file recall and span quality diverge**: P8/P9 show good FileRecall but low SpanF0.5.
3. **RRF recall is coupled with false-primary risk**: raw recall is not enough; admission is critical.
4. **Graph expansion is repeatedly net-negative**: graph_basic mostly adds false spans and almost no gold.
5. **Larger embedding models did not win the first bakeoff**: 8B did not dominate 0.6B/4B/bge-m3.
6. **JS Express underperformed Go/Python/Rust**: embedding quality varies across language/framework buckets.
7. **P20-LS low-context alias expansion failed real-provider scale-up**: all guardrails passed, but query-only aliases produced far more false spans than gold spans (8312 vs 289 on real CI runs), with high fabricated identifier rates. This blocks low-context LLM alias scale-up, not rich-context LLM retrieval.

---

## 5. Current Quality and Boundary Policy

The new research priority is quality and efficiency. Boundaries should protect the fact layer and secrets, not starve the model of useful public-code context. All conclusions depend on preserving these necessary boundaries:

- `EvidenceCore` remains the only authoritative fact layer.
- Dense, QuIVer, graph, and LLM-derived outputs remain candidate/supporting/diagnostic, not Evidence.
- Evidence must come from reading current source files and validating `content_sha` plus line ranges.
- RUN phase must not read private labels; SCORE phase reads labels only after run artifacts exist.
- Real providers run only under `workflow_dispatch + enable_remote_models=true + OPENLOCUS_ALLOW_REMOTE=1`.
- Reports and artifacts must not upload provider URLs/keys, private labels, or gold answers. Raw snippets may be sent to providers in explicit public/opt-in rich-context runs, but should not be committed as artifacts unless intentionally documented.
- Unavailable strategies must be reason-only and must not emit fake quality numbers.

Allowed in quality-first public/opt-in remote runs:

- raw code snippets/chunks after secret and ignore filtering;
- path, symbol, signature, doc heading, and neighbor-line context;
- top-k local candidate metadata and retrieval scores;
- prompt/context matrices that trade quality, cost, and latency.

---

## 6. What the Research Has Actually Established

The research has established four things with reasonable confidence:

1. **The fact-layer safety constraints are executable**: EvidenceCore, materialization, and citation validation are implemented across local retrieval, store, graph, dense, and CI runner paths.
2. **Local lexical/symbol/RRF remain the backbone**: real models did not replace RRF/symbol/regex; they made anchors and guards more important.
3. **Real models are useful but context-sensitive**: embeddings have file-level signal, LLMs can expand stress/derived views, and QuIVer BQ deserves continuation; none should directly become facts, but future tests should give models richer code context.
4. **The experiment system can find counterexamples**: the P4 → P8a and P20-LS offline → remote scale-up shifts show that the harness can challenge tiny optimistic or merely schema-safe results with realistic corpus slices.

---

## 7. Stage Summary Index

The detailed phase reports are preserved. This section is an index, not a replacement.

### R0-R13: Local evidence kernel and safety scaffolds

- R0/R1: local evidence kernel, read/scan/search, trace, citation validation.
- R2: regex/BM25/symbol/RRF local bakeoff.
- R3: StoreHit materialization gate and conservative store.
- R4: DerivedIndexView safety scaffold; derived views are not Evidence.
- R5: deterministic graph scaffold; graph output is not direct Evidence.
- R6: deterministic fast-context orchestration scaffold.
- R7-R10: persistent BM25, AST chunking, quality bakeoff, incremental index.
- R11: TDB Level0 adapter probe; metadata/chunks only, no retrieval quality claim.
- R12: real-repo incremental robustness bench.
- R13: provider/dense safety scaffold with mock embeddings and no remote quality claim.

### R14-R29: Benchmark/failure-surface expansion

- R14-R16: scaled benchmark foundation, external multi-repo expansion, multi-method bakeoff.
- R17-R19: query router, guard calibration, large/stress guard generalization.
- R20-R23: auto-wide failure-surface dataset, strategy matrix, failure attribution, guard sweep.
- R24-R25: QuIVer/TDB availability probe, dense_mock/graph ablation; graph/dense default expansion blocked.
- R26: auto-stress-1000 static dataset.
- R28: conservative promotion candidate report; no default change.
- R29: R26 strategy matrix; RRF recall strong, symbol precision anchor, query-noise guard promising, graph/dense blocked.

### R30-R45: Real-model readiness and diagnostic expansion

- R30: freeze R29 baseline.
- R31: real embedding provider smoke and safety gates.
- R32: embedding view bakeoff harness.
- R33: QuIVer BQ readiness diagnostics.
- R34-R36: QuIVer/BQ prototype and anchor-seeded dense/quiver experiments.
- R37-R38: LLM-derived views and stress expansion; not Evidence.
- R39-R40: symbol extraction and regex normalization repair tracks.
- R41-R42: graph role research and admission model v2 rules.
- R43-R45: integrated long-run report; no promotion.

### P1-P9: Real-provider and CI scale-up

- P1: real embedding and LLM smoke, provider access validated.
- P2: bounded real embedding view bakeoff.
- P3: real embedding QuIVer BQ readiness.
- P4: real embedding anchor prototype.
- P5: LLM-derived/stress harness with not-evidence boundary.
- P6: repair/admission replay.
- P7: real-provider summary.
- P8/P9: GitHub Actions public corpus scale-up, model bakeoff, and multilingual smoke.

### P20-P25/P30: LLM scale-up, policy routing, and explainable admission

- P20-LS/P20-LS-A: low-context/query-only LLM aliases safety-passed but quality-failed; direct low-context alias scale-up blocked.
- P21-G: cross-model context-injection phase using context atoms, context packs, candidate metadata, model profiles, roles, layouts, and latency/cost accounting. P21-G1E found useful file/span signal (`pack2_evidence_sketch`, `atom_signature`) but naked dense false spans dominated. P21-G2E found constrained dense has modest supporting value (`dense_atom_signature_rrf_file_constrained`) while dense-only remains diagnostic/non-primary. P21-G3L found LLM span narrowing has promising but model/repo-specific signal; filter/abstain need prompt/bucket routing and GLM needs schema repair.
- P25: bucket-routed LLM role policy evaluator. Deterministic, no-remote, routes by public `task_bucket`/`task_risk_tags`; reduces false primary but also some gold spans; useful as a P30 input, not default.
- P30: Admission Model V3 research harness. Deterministic explainable scorecard with hard guards, routes only from pre-SCORE public features, compares baselines plus `admission_v3`/`admission_v3_h1`/`admission_v3_h2`, reports score bands/selective risk/deltas, action-specific span-cost accounting (P30-H3), and scans public output for forbidden keys. P30-H1 fixed missing outcomes; P30-H2 stricter local-anchor admission still underperforms P25; P30-H3 now provides diagnostic action-cost accounting without changing routes.
- P48: Diagnostic Policy Simulator / Request-More-Context Overlay. Deterministic, SCORE-phase-only route simulator that overlays the P47 span-geometry gate on P25 `bucket_routed_v0` and P30-H4B `admission_v3_h4b`. It counts how many risky candidate-derived primary actions would be replaced by `request_more_context`, reports measured primary cost for existing actions only, and emits geometry-only diagnostics with explicit not-evidence flags. It does not change defaults or EvidenceCore.
- P49: Contrastive Candidate Pack Scaffold. Deterministic, SCORE-phase-only pack-shape diagnostic that builds candidate packs from candidate metadata only (rank, score, channels, subtype axes, path-kind). It reports aggregate pack-build, contrast, provenance-completeness, and SCORE-phase diagnostics per public task bucket and risk tag. It does not call an LLM, does not create evidence, does not admit spans, does not read source files, does not validate content_sha, and does not change defaults or EvidenceCore.
- P52: Metadata-Only Local Verifier Scaffold. Deterministic, SCORE-phase-only feature-availability and candidate-risk-bucket inventory that runs before any source-read or LLM span-narrow phase. It consumes the same ephemeral P25-policy records as P46/P49, classifies candidates into metadata-risk buckets using only public metadata, and reports aggregate availability/checkability/risk diagnostics by pack strategy, public bucket, and risk tag. It does not verify source text, does not read files, does not call an LLM, does not construct prompts, does not validate EvidenceCore, does not produce evidence, does not produce a verifier pass/fail score, and does not prove P51/P53 quality. See `docs/en/p52-metadata-local-verifier-scaffold.md`.
- P52B: Source-Backed Local Verifier Feature Matrix. Deterministic, SCORE-phase-only source-shape feature diagnostics computed from bounded local source reads. It consumes the same ephemeral P25-policy records and the P52A materialization outcome, extracts source-shape heuristics from bounded candidate spans, classifies candidates into source-feature risk buckets, and reports aggregate diagnostics by pack strategy and safe public dimensions. It does not produce evidence, does not produce a verifier pass/fail or local-verifier score, does not admit candidates, does not change defaults, does not prove P51 quality, and does not send source to providers. See `docs/en/p52b-source-backed-local-verifier-feature-matrix.md`.
- P52C: Diagnostic Local Verifier Scoring Simulator. Deterministic, gold-free diagnostic score-bucket simulator over P52B/P52A/P52/P49/P48 features. It computes fixed `p52c_diagnostic_score_v0` score buckets and aggregate retrospective correlations; scores are not Evidence, not a verifier pass/fail, and not an admission/default/promotion claim. See `docs/en/p52c-local-verifier-scoring-simulator.md`.

### C5-A: ContextBench verified retrieval performance smoke

- C5-A: first external-benchmark-shaped retrieval performance smoke. Reads a bounded ContextBench verified subset from HF datasets-server `/rows` (default 5 rows; hard cap 20; stdlib `urllib` only), materializes the referenced repositories at `base_commit` under transient `/tmp` directories via `git clone --filter=blob:none --no-checkout` then `git checkout`, runs OpenLocus `bm25` retrieval (no provider calls), scores against `gold_context` spans via `eval/score.py`, and commits only an aggregate public report. Schema `c5_contextbench_verified_performance_smoke.v1`, `claim_level=external_benchmark_retrieval_performance_smoke_only`, `status=pass|partial|unavailable_with_reason`, `mode=contextbench_verified_retrieval_performance_smoke`, phase `C5-A`. 113/113 self-test checks pass. Safe true flags (true only if actually true): `external_benchmark_rows_read`, `repositories_materialized_transiently`, `openlocus_retrieval_executed`, `score_py_metrics_computed`, `performance_smoke`, `aggregate_only_public_artifact`, `diagnostic_only`. All no-claim / no-runtime-change flags false (`external_benchmark_performance_claimed`, `downstream_agent_value_proven`, `promotion_ready`, `default_should_change`, `runtime_behavior_changed`, `retriever_changed`, `pack_builder_changed`, `backend_changed`, `default_policy_changed`, `evidencecore_semantics_changed`, `provider_calls_made`, `remote_provider_calls_made`). License: `dataset_license_status=unknown_dataset_license`, `row_level_redistribution_allowed=false`, `derived_row_level_publication_allowed=false`, `aggregate_metrics_publication=aggregate_only_smoke`. CI is a separate manual opt-in `workflow_dispatch` with `enable_external_benchmark_network=true`; no provider secrets/vars; uploads aggregate report only. If network smoke cannot complete, artifact is truthful `unavailable_with_reason` with a real failure category (no stale/fake pass). C5-A is NOT a benchmark result, NOT a leaderboard entry, NOT a performance claim, NOT a promotion, NOT a default change, NOT a runtime/retriever/pack/backend/EvidenceCore semantic change, and NOT a downstream agent value claim. See `docs/en/c5-contextbench-verified-performance-smoke.md`.

### C5-B: ContextBench verified retrieval method matrix smoke

- C5-B: bounded multi-method matrix extension of C5-A. Reads a bounded ContextBench verified subset from HF datasets-server `/rows` ONCE (shared across all methods; default 5 rows per method; hard cap 10; stdlib `urllib` only), materializes the referenced repositories at `base_commit` under transient `/tmp` directories via `git clone --filter=blob:none --no-checkout` then `git checkout`, runs OpenLocus retrieval across the requested method matrix (default `bm25,regex,symbol`; allowed `bm25,regex,text,symbol`; fixed `baseline_method=bm25`; no provider calls), scores each method against benchmark label spans via `eval/score.py`, and commits only an aggregate public report with per-method records and aggregate-only deltas vs the fixed `bm25` baseline. Schema `c5b_contextbench_verified_method_matrix_smoke.v1`, `claim_level=external_benchmark_retrieval_method_matrix_smoke_only`, `status=pass|partial|unavailable_with_reason|fail_schema_contract|fail_forbidden_scan`, `mode=contextbench_verified_retrieval_method_matrix_smoke`, phase `C5-B`. 161/161 self-test checks pass. Safe true flags (true only if actually true): `external_benchmark_rows_read`, `repositories_materialized_transiently`, `openlocus_retrieval_executed`, `score_py_metrics_computed`, `method_matrix_smoke`, `aggregate_only_public_artifact`, `diagnostic_only`. All no-claim / no-runtime-change flags false (`external_benchmark_performance_claimed`, `leaderboard_entry_claimed`, `downstream_agent_value_proven`, `promotion_ready`, `default_should_change`, `baseline_is_policy_candidate`, `runtime_behavior_changed`, `retriever_changed`, `pack_builder_changed`, `backend_changed`, `default_policy_changed`, `evidencecore_semantics_changed`, `provider_calls_made`, `remote_provider_calls_made`). License: `dataset_license_status=unknown_dataset_license`, `row_level_redistribution_allowed=false`, `derived_row_level_publication_allowed=false`, `aggregate_metrics_publication=aggregate_only_smoke`. Method metric allowlist: `file_recall@10`, `mrr`, `span_f0.5@10`, `success_rate`. `method_results` is a list of records (NOT a dict keyed by method name). Does NOT emit `winner`, `best_method`, `recommended_default`, or anything implying a policy/default decision. CI is a separate manual opt-in `workflow_dispatch` with `enable_external_benchmark_network=true`; no provider secrets/vars; no provider model env; uploads aggregate report only. If network smoke cannot complete, artifact is truthful `unavailable_with_reason` with a real failure category (no stale/fake pass). C5-B is NOT a benchmark result, NOT a leaderboard entry, NOT a performance claim, NOT a promotion, NOT a default change, NOT a runtime/retriever/pack/backend/EvidenceCore semantic change, and NOT a downstream agent value claim. See `docs/en/c5b-contextbench-verified-method-matrix-smoke.md`.

### C5-C: ContextBench verified retrieval method matrix scale smoke

- C5-C: bounded 20-row method-matrix scale extension of C5-B. Reads a bounded 20-row ContextBench verified subset from HF datasets-server `/rows` ONCE (shared across all 3 methods; default 20 rows per method; hard cap 20; stdlib `urllib` only), materializes the referenced repositories at `base_commit` under transient `/tmp` directories (once per method+row) via `git clone --filter=blob:none --no-checkout` then `git checkout`, runs OpenLocus retrieval across the requested method matrix (default `bm25,regex,symbol`; only `bm25,regex,symbol` allowed in C5-C; `text` is NOT allowed; fixed `baseline_method=bm25`; no provider calls), scores each method against benchmark label spans via `eval/score.py`, and commits only an aggregate public report with per-method records (list, NOT dict keyed by method name), optional per-method `aggregate_runtime_seconds`, aggregate-only deltas vs the fixed `bm25` baseline, and an `input_summary` block. Schema `c5c_contextbench_verified_method_matrix_scale_smoke.v1`, `claim_level=external_benchmark_retrieval_method_matrix_scale_smoke_only`, `status=contextbench_method_matrix_scale_smoke_pass|partial|unavailable_with_reason|fail_forbidden_scan`, `mode=contextbench_verified_bounded_scale_method_matrix`, phase `C5-C`. 179/179 self-test checks pass. Safe true flags (true only if actually true): `retrieval_scale_smoke_performed`, `openlocus_retrieval_executed`, `score_py_metrics_computed`, `aggregate_only_public_artifact`, `diagnostic_only` (C5-C does NOT use C5-B's `method_matrix_smoke` flag or C5-A's `external_benchmark_rows_read`/`repositories_materialized_transiently`/`performance_smoke` flags). All no-claim / no-runtime-change flags false (`external_benchmark_performance_claimed`, `leaderboard_entry_claimed`, `downstream_agent_value_proven`, `promotion_ready`, `default_should_change`, `baseline_is_policy_candidate`, `runtime_behavior_changed`, `retriever_changed`, `pack_builder_changed`, `backend_changed`, `default_policy_changed`, `evidencecore_semantics_changed`, `provider_calls_made`, `remote_provider_calls_made`). License: `dataset_license_status=unknown_dataset_license`, `row_level_redistribution_allowed=false`, `derived_row_level_publication_allowed=false`, `aggregate_metrics_publication=aggregate_only_smoke`. Method metric allowlist: `file_recall@10`, `mrr`, `span_f0.5@10`, `success_rate`. `method_results` is a list of records (NOT a dict keyed by method name). Does NOT emit `winner`, `best_method`, `recommended_default`, or anything implying a policy/default decision. CI is a separate manual opt-in `workflow_dispatch` with `enable_external_benchmark_network=true`; no provider secrets/vars; no provider model env; uploads aggregate report only. If network smoke cannot complete, artifact is truthful `unavailable_with_reason` with a real failure category (no stale/fake pass). C5-C is NOT a benchmark result, NOT a leaderboard entry, NOT a performance claim, NOT a promotion, NOT a default change, NOT a runtime/retriever/pack/backend/EvidenceCore semantic change, and NOT a downstream agent value claim. See `docs/en/c5c-contextbench-method-matrix-scale-smoke.md`.

Manual CI run `27905621090` passed after the C5-C workflow was made fail-closed for network-enabled runs: 20 rows fetched, 3/3 methods successful, bm25 file_recall@10=0.35 / mrr=0.143107 / span_f0.5@10=0.020838 / success_rate=1.0, regex and symbol file_recall@10=0.0; earlier run `27905321437` green-unavailable was treated as fail-open and fixed. These are smoke diagnostics only, not external benchmark performance or default-policy claims.

Key detailed reports:


### C5-F: RepoQA 10-needle method-matrix scale smoke

- C5-F: separate 10-needle scale checkpoint for RepoQA method-matrix retrieval smoke. Reuses C5-E's RepoQA asset/needle/clone/retrieval/score pipeline but preserves C5-E as a completed checkpoint. Schema `c5f_repoqa_method_matrix_scale_smoke.v1`, `claim_level=repoqa_retrieval_method_matrix_scale_smoke_only`, status `repoqa_method_matrix_scale_smoke_pass|partial|unavailable_with_reason|fail_forbidden_scan|fail_schema_contract`, mode `repoqa_bounded_10_needle_method_matrix_scale_smoke`, phase `C5-F`. Default/hard cap 10 Python needles per method; methods `bm25,regex,symbol`; fixed `baseline_method=bm25`; no provider calls; 191/191 self-test checks pass. Manual CI run `27909885489`: 10 needles seen, 3/3 methods successful, forbidden scan pass, provider_calls=0, bm25 file_recall@10=0.5 / mrr=0.369216 / span_f0.5@10=0.020817 / success_rate=1.0, regex/symbol file_recall@10=0.0, aggregate_runtime_seconds bm25=19.018 / regex=18.181 / symbol=28.251. This is smoke-only, not a benchmark/performance/leaderboard/default/method-winner/downstream-value claim.

### C5-E: RepoQA method-matrix retrieval smoke

- C5-E: bounded RepoQA method-matrix retrieval smoke. Extends C5-D from single-method `bm25` to a bounded method matrix over `bm25,regex,symbol`. Downloads the EvalPlus RepoQA release asset `repoqa-2024-06-23.json.gz` from `evalplus/repoqa_release` to in-memory bytes (transient; NEVER written to workspace), decompresses in memory, parses a bounded RepoQA Python needle subset (default 5 needles per method; hard cap 10; NO silent all-language fallback), materializes the referenced repositories at their `commit_sha` under transient `/tmp` directories (once per method+needle) via `git clone --filter=blob:none --no-checkout` then `git checkout`, runs OpenLocus retrieval across the requested method matrix (default `bm25,regex,symbol`; only `bm25,regex,symbol` allowed; `text` NOT allowed; fixed `baseline_method=bm25`; no provider calls), scores each method against `needle.path`/`start_line`/`end_line` via `eval/score.py`, and commits only an aggregate public report with per-method records (list, NOT dict keyed by method name), per-method `aggregate_runtime_seconds`, and aggregate-only deltas vs the fixed `bm25` baseline. Schema `c5e_repoqa_method_matrix_smoke.v1`, `claim_level=repoqa_retrieval_method_matrix_smoke_only`, `status=repoqa_method_matrix_smoke_pass|partial|unavailable_with_reason|fail_forbidden_scan|fail_schema_contract`, `mode=repoqa_bounded_method_matrix_smoke`, phase `C5-E`. 228/228 self-test checks pass. Safe true flags (true only if actually true): `repoqa_method_matrix_smoke_performed`, `asset_downloaded_transiently`, `repoqa_needles_parsed_in_memory`, `repositories_materialized_transiently`, `openlocus_retrieval_executed`, `score_py_metrics_computed`, `aggregate_only_public_artifact`, `diagnostic_only` (C5-E does NOT use C5-D's `repoqa_retrieval_smoke_performed` flag). All no-claim / no-runtime-change flags false (`external_benchmark_performance_claimed`, `leaderboard_entry_claimed`, `downstream_agent_value_proven`, `promotion_ready`, `default_should_change`, `baseline_is_policy_candidate`, `runtime_behavior_changed`, `retriever_changed`, `pack_builder_changed`, `backend_changed`, `default_policy_changed`, `evidencecore_semantics_changed`, `provider_calls_made`, `remote_provider_calls_made`). License: `dataset_license_status=unknown_dataset_license`, `row_level_redistribution_allowed=false`, `derived_row_level_publication_allowed=false`, `aggregate_metrics_publication=aggregate_only_smoke`. Method metric allowlist: `file_recall@10`, `mrr`, `span_f0.5@10`, `success_rate`. `method_results` is a list of records (NOT a dict keyed by method name). Does NOT emit `winner`, `best_method`, `recommended_default`, or anything implying a policy/default decision. CI is a separate manual opt-in `workflow_dispatch` with `enable_external_benchmark_network=true`; no provider secrets/vars; no provider model env; fail-closed like C5-C (network-enabled CI cannot pass with unavailable/no needles; require status in (`repoqa_method_matrix_smoke_pass`, `partial`), `needles_seen > 0`, `methods_successful > 0`, `forbidden_scan.status=pass`); uploads aggregate report only. If network smoke cannot complete, artifact is truthful `unavailable_with_reason` with a real failure category (no stale/fake pass). C5-E is NOT a benchmark result, NOT a leaderboard entry, NOT a performance claim, NOT a promotion, NOT a default change, NOT a runtime/retriever/pack/backend/EvidenceCore semantic change, and NOT a downstream agent value claim. See `docs/en/c5e-repoqa-method-matrix-smoke.md`.

Manual CI run `27907731742` passed for C5-E: 5 RepoQA Python needles per method, 3/3 methods successful, forbidden scan pass, bm25 file_recall@10=0.6 / mrr=0.46 / span_f0.5@10=0.041634 / success_rate=1.0, regex/symbol file_recall@10=0.0, provider_calls=0. These are method-matrix smoke diagnostics only, not method winner/default/performance claims.

### C5-D: RepoQA BM25 retrieval performance smoke

- C5-D: bounded RepoQA BM25 retrieval performance smoke. Downloads the EvalPlus RepoQA release asset `repoqa-2024-06-23.json.gz` from `evalplus/repoqa_release` to in-memory bytes (transient; NEVER written to workspace), decompresses in memory, parses a bounded RepoQA Python needle subset (default 5 needles; hard cap 10; NO silent all-language fallback), materializes the referenced repositories at their `commit_sha` under transient `/tmp` directories via `git clone --filter=blob:none --no-checkout` then `git checkout`, runs OpenLocus `bm25` retrieval (bm25 only; no provider calls), scores against `needle.path`/`start_line`/`end_line` via `eval/score.py`, and commits only an aggregate public report. Schema `c5d_repoqa_retrieval_performance_smoke.v1`, `claim_level=repoqa_retrieval_performance_smoke_only`, `status=repoqa_retrieval_smoke_pass|partial|unavailable_asset_download_failed|unavailable_no_python_needles|unavailable_repo_clone_failed|fail_forbidden_scan|fail_schema_contract`, `mode=repoqa_bounded_bm25_retrieval_smoke`, phase `C5-D`. 219/219 self-test checks pass. Safe true flags (true only if actually true): `repoqa_retrieval_smoke_performed`, `asset_downloaded_transiently`, `repoqa_needles_parsed_in_memory`, `repositories_materialized_transiently`, `openlocus_retrieval_executed`, `score_py_metrics_computed`, `aggregate_only_public_artifact`, `diagnostic_only`. All no-claim / no-runtime-change flags false (`external_benchmark_performance_claimed`, `leaderboard_entry_claimed`, `downstream_agent_value_proven`, `promotion_ready`, `default_should_change`, `runtime_behavior_changed`, `retriever_changed`, `pack_builder_changed`, `backend_changed`, `default_policy_changed`, `evidencecore_semantics_changed`, `provider_calls_made`, `remote_provider_calls_made`). License: `dataset_license_status=unknown_dataset_license`, `row_level_redistribution_allowed=false`, `derived_row_level_publication_allowed=false`, `aggregate_metrics_publication=aggregate_only_smoke`. Metric allowlist: `file_recall@10`, `mrr`, `span_f0.5@10`, `success_rate`. Does NOT emit `winner`, `best_method`, `recommended_default`, or anything implying a policy/default decision. CI is a separate manual opt-in `workflow_dispatch` with `enable_external_benchmark_network=true`; no provider secrets/vars; no provider model env; fail-closed like C5-C (network-enabled CI cannot pass with unavailable/no needles); uploads aggregate report only. If network smoke cannot complete, artifact is truthful `unavailable_*` with a real failure category (no stale/fake pass). C5-D is NOT a benchmark result, NOT a leaderboard entry, NOT a performance claim, NOT a promotion, NOT a default change, NOT a runtime/retriever/pack/backend/EvidenceCore semantic change, and NOT a downstream agent value claim. See `docs/en/c5d-repoqa-bm25-retrieval-smoke.md`.
Manual CI run `27906775008` passed for C5-D: 5 RepoQA Python needles seen/successful, forbidden scan pass, file_recall@10=0.6 / mrr=0.46 / span_f0.5@10=0.041634 / success_rate=1.0, provider_calls=0. These are smoke diagnostics only, not external benchmark performance or default-policy claims.

### BEA-0: Budgeted Evidence Acquisition v0

- BEA-0: first real algorithmic retrieval/acquisition experiment with private per-record SCORE JSONL traces. Reruns fresh multi-method retrieval (bm25/regex/symbol + optional rrf) over bounded real ContextBench verified Python rows (default 10; hard cap 20) + RepoQA Python needles (default 5; hard cap 10), runs the deterministic `bea_v0_budgeted` policy under an evidence budget (default 10; hard cap 20), and computes per-arm aggregate metrics with baseline-vs-treatment deltas vs `bm25_top10` (and `rrf_bm25_regex_symbol_top10` when rrf enabled). Schema `bea0_budgeted_evidence_acquisition.v1`, `claim_level=bea_v0_budgeted_acquisition_smoke_only`, `status=bea_v0_smoke_pass|partial|unavailable_with_reason|fail_forbidden_scan|fail_schema_contract`, `mode=bea_v0_budgeted_acquisition`, phase `BEA-0`. 212/212 self-test checks pass. The `bea_v0_budgeted` policy consumes ONLY runtime-clean candidate features (method source, candidate rank, score/normalized score, rank agreement across methods, duplicate path/span overlap, candidate count, accepted coverage, budget remaining, cheap path extension); verified invariant under synthetic gold/label/row-id/model-family/previous-outcome tainting (policy produces IDENTICAL accepted/action_trace/budget_states because it ignores those fields). Actions: `accept_candidate`, `skip_low_support`, `rerank_by_agreement`, `stop_budget_exhausted`, optional `expand_same_file`. Private per-record SCORE JSONL written ONLY under `/tmp` (or explicitly ignored private path under gitignored `runs/`); private SCORE path NEVER serialized in public artifact/docs/CI. Public artifact records ONLY aggregate SCORE manifest fields (`private_score_records_written`, `private_score_record_count`, `private_score_schema_version`, `private_score_manifest_hash`, `private_score_storage_class`, `private_score_path_publicly_serialized=false`). Safe true flags (true only if actually true): `bea_v0_acquisition_performed`, `multi_method_candidates_collected`, `budgeted_policy_executed`, `private_score_records_written`, `external_benchmark_rows_read`, `repositories_materialized_transiently`, `openlocus_retrieval_executed`, `score_py_metrics_computed`, `aggregate_only_public_artifact`, `diagnostic_only`. All no-claim / no-runtime-change flags false (`external_benchmark_performance_claimed`, `leaderboard_entry_claimed`, `downstream_agent_value_proven`, `calibration_claimed`, `method_winner_claimed`, `promotion_ready`, `default_should_change`, `runtime_behavior_changed`, `retriever_changed`, `pack_builder_changed`, `backend_changed`, `default_policy_changed`, `evidencecore_semantics_changed`, `provider_calls_made`, `remote_provider_calls_made`). License: `dataset_license_status=unknown_dataset_license`, `row_level_redistribution_allowed=false`, `derived_row_level_publication_allowed=false`, `aggregate_metrics_publication=aggregate_only_smoke`. Per-arm metric allowlist: `file_recall@10`, `mrr`, `span_f0.5@10`, `success_rate`, `candidate_count_read`, `evidence_budget_used`, `action_steps`, `latency_seconds`, `quality_per_candidate`. Does NOT emit `winner`, `best_method`, `recommended_default`, `method_winner`, `calibration`, or anything implying a policy/default decision. CI is a separate manual opt-in `workflow_dispatch` with `enable_external_benchmark_network=true`; no provider secrets/vars; no provider model env; fail-closed like C5-C/C5-D/C5-E (network-enabled CI cannot pass with unavailable/no records; require status in (`bea_v0_smoke_pass`, `partial`), `records_successful > 0`, `forbidden_scan.status=pass`, `provider_calls=0`, `private_score_record_count == records_successful`, no `winner`/`best_method`/`recommended_default`/`method_winner`/`calibration` fields anywhere, no BEA-0 private fields anywhere); uploads aggregate report only; never uploads private SCORE JSONL. If network smoke cannot complete, artifact is truthful `unavailable_with_reason` with a real failure category (no stale/fake pass). BEA-0 is NOT a benchmark result, NOT a leaderboard entry, NOT a performance claim, NOT a method-winner claim, NOT a calibration claim, NOT a promotion, NOT a default change, NOT a runtime/retriever/pack/backend/EvidenceCore semantic change, and NOT a downstream agent value claim. See `docs/en/bea0-budgeted-evidence-acquisition.md`.
Manual CI run `27934507148` (2026-06-21) passed for BEA-0 with ContextBench 2 rows + RepoQA 1 needle, budget=5, methods bm25/regex/symbol, rrf baseline enabled: 3 records successful, forbidden scan pass, provider_calls=0, private_score_record_count=3 (matches records_successful), private_score_storage_class=tmp_private, private_score_path_publicly_serialized=false. Treatment `bea_v0_budgeted` preserved file_recall@10 / mrr / success_rate parity with both `bm25_top10` and `rrf_bm25_regex_symbol_top10` while using roughly half the evidence budget (evidence_budget_used=3.333333 vs 6.666667) and improved span_f0.5@10 by +0.027662 and quality_per_candidate by +0.001384 vs `bm25_top10`. These are smoke-level aggregate deltas only, not benchmark performance, method-winner, calibration, default, promotion, runtime/retriever/EvidenceCore, or downstream-agent-value claims.

### BEA-1: Mechanism Ablation Smoke

- BEA-1: mechanism ablation smoke over fresh bounded ContextBench verified Python rows (default 5; hard cap 20) + RepoQA Python needles (default 3; hard cap 10). Reruns fresh multi-method retrieval (bm25/regex/symbol + optional rrf); does NOT bootstrap the BEA-0 aggregate artifact. Runs 5 fixed arms (`bm25_top10`, `bea_v0_budgeted`, `same_budget_bm25_prefix`, `agreement_only_same_budget`, `seeded_random_same_budget`; `rrf_bm25_regex_symbol_top10` when rrf enabled) on every record under a paired denominator rule. Same-budget K exactly: `K = min(len(bea_v0_budgeted.accepted_candidates), available_deduped_candidate_count)`. Arm algorithms exactly as plan: BM25 prefix; agreement-only sorted by (agreement desc, min_rank asc, max_normalized_score desc, stable order); seeded random with fixed public seed `20240621` over stable-ordered deduped universe; no gold/labels/row IDs/provider/model fields in seed or ordering. Schema `bea1_mechanism_ablation.v1`, `claim_level=bea_v0_mechanism_ablation_smoke_only`, `status=bea1_mechanism_ablation_pass|partial|unavailable_with_reason|fail_forbidden_scan|fail_schema_contract`, `mode=bounded_external_retrieval_mechanism_ablation`, phase `BEA-1`. 420/420 self-test checks pass. Public artifact is records-only: `arm_metric_records` (`{arm, metric, value}`), `delta_records` (`{baseline_arm, treatment_arm, metric, delta}` vs fixed `bm25_top10`), `mechanism_contrast_records` (`{contrast, baseline_arm, treatment_arm, metric, delta, record_count}` for `bea_vs_same_budget_bm25`/`bea_vs_agreement_only`/`bea_vs_seeded_random`), aggregate-only `private_score_manifest` block (`records_written`, `record_count`, `schema_version`, `manifest_hash`, `storage_class`, `path_publicly_serialized=false`). Private per-record SCORE JSONL written ONLY under `/tmp`; private SCORE path NEVER serialized. Safe true flags (true only if actually true): `mechanism_ablation_performed`, `bea_v0_acquisition_performed`, `private_score_records_written`, `external_benchmark_rows_read`, `openlocus_retrieval_executed`, `score_py_metrics_computed`, `aggregate_only_public_artifact`, `diagnostic_only`. All no-claim / no-runtime-change flags false (`external_benchmark_performance_claimed`, `leaderboard_entry_claimed`, `downstream_agent_value_proven`, `calibration_claimed`, `method_winner_claimed`, `promotion_ready`, `default_should_change`, `runtime_behavior_changed`, `retriever_changed`, `pack_builder_changed`, `backend_changed`, `default_policy_changed`, `evidencecore_semantics_changed`, `provider_calls_made`, `remote_provider_calls_made`). License: `dataset_license_status=unknown_dataset_license`, `row_level_redistribution_allowed=false`, `derived_row_level_publication_allowed=false`, `aggregate_metrics_publication=aggregate_only_smoke`. Does NOT emit `winner`, `best_method`, `recommended_default`, `method_winner`, `calibration`. CI is a separate manual opt-in `workflow_dispatch` with `enable_external_benchmark_network=true`; no provider secrets/vars; no provider model env; fail-closed (require status in (`bea1_mechanism_ablation_pass`, `partial`), `records_successful >= 3`, every mechanism contrast `record_count >= 3`, `forbidden_scan.status=pass`, `provider_calls=0`, `private_score_manifest` present with `path_publicly_serialized=false` and `record_count == records_successful`, no `winner`/`best_method`/`recommended_default`/`method_winner`/`calibration` fields anywhere, no BEA-1 private fields anywhere); uploads aggregate report only; never uploads private SCORE JSONL. If network smoke cannot complete, artifact is truthful `unavailable_with_reason` with a real failure category. BEA-1 is NOT a benchmark result, NOT a leaderboard entry, NOT a performance claim, NOT a method-winner claim, NOT a calibration claim, NOT a promotion, NOT a default change, NOT a runtime/retriever/pack/backend/EvidenceCore semantic change, and NOT a downstream agent value claim. See `docs/en/bea1-mechanism-ablation.md`.
Manual CI run `27936497544` passed for BEA-1 with ContextBench 5 rows + RepoQA 3 needles, budget=5, methods bm25/regex/symbol, rrf baseline enabled: 8 records successful, `paired_exclusion_count=0`, forbidden scan pass, `provider_calls=0`, `private_score_manifest.record_count=8` (matches records_successful), `private_score_manifest.storage_class=tmp_private`, `private_score_manifest.path_publicly_serialized=false`. Mechanism contrasts (mrr, paired `record_count=8`): `bea_vs_same_budget_bm25` delta(mrr)=0.0 (BEA ties same-budget BM25 prefix); `bea_vs_agreement_only` delta(mrr)=0.0 (BEA ties agreement-only); `bea_vs_seeded_random` delta(mrr)=+0.09375 (BEA beats seeded random). BEA v0 and `agreement_only_same_budget` produce IDENTICAL file_recall@10/mrr/span_f0.5@10/success_rate with the same `evidence_budget_used=3.125`, suggesting BEA v0's gain over a pure agreement-only rank under the same budget is zero on this bounded sample. `seeded_random_same_budget` underperforms both, confirming deterministic agreement-based selection beats random selection under the same budget. These are smoke-level aggregate deltas only, not benchmark performance, method-winner, calibration, default, promotion, runtime/retriever/EvidenceCore, or downstream-agent-value claims.

### BEA-2: Policy v0.2 Diversity/Risk Mechanism Smoke

- BEA-2: policy v0.2 diversity/risk mechanism smoke over fresh heldout ContextBench verified Python rows (offset 40, limit 20) + RepoQA Python needles (offset 20, limit 10). Implements a real algorithmic policy change — BEA v0.2 diversity/risk-aware acquisition — with frozen priority weights (agreement=0.30, bm25_norm=0.20, diversity=0.20, query_path_overlap=0.15, risk_penalty=-0.25, duplication_penalty=-0.30) that are NOT tuned from outcomes. v0.2 is structurally different from v0 and agreement-only: greedy priority-scored selection with diversity/risk/duplication-aware recomputation after each selection. 5 fixed policy arms: `bm25_prefix_same_budget`, `agreement_only_same_budget`, `bea_v0`, `bea_v0_2_diversity_risk`, `seeded_random_same_budget` (optional `rrf_same_budget`). Same-budget K exactly: `K = min(len(bea_v0_2_diversity_risk.accepted_candidates), available_deduped_candidate_count)`. Schema `bea2_policy_v02.v1`, `claim_level=bea_v02_policy_smoke_only`, phase `BEA-2`, 321/321 self-test checks pass. Public artifact is records-only: `benchmark_arm_metric_records` (`{benchmark, arm, metric, value, record_count}`), `delta_records` (v0.2 vs each control arm with v0 as fixed baseline), `mechanism_contrast_records` (paired denominator with `record_count`), `win_tie_loss_records` (win/tie/loss on primary metrics: `file_recall@10`, `mrr`, `span_f0.5@10`, `success_rate`), aggregate `private_score_manifest` block. Private per-record SCORE JSONL (one row per record × policy arm) written ONLY under `/tmp`; private SCORE path NEVER serialized. All no-claim / no-runtime-change flags false. BEA-2 is NOT a benchmark result, NOT a leaderboard entry, NOT a performance claim, NOT a method-winner claim, NOT a calibration claim, NOT a promotion, NOT a default change, NOT a runtime/retriever/pack/backend/EvidenceCore semantic change, and NOT a downstream agent value claim. BEA-2 does NOT mutate BEA-0/BEA-1 semantics. See `docs/en/bea2-policy-v02.md`.
Manual CI run `27938484585` (2026-06-21) passed with ContextBench offset 40 limit 20 + RepoQA offset 20 limit 10, budget=5, methods bm25/regex/symbol, RRF baseline enabled. 30 records successful; `paired_exclusion_count=0`; forbidden scan pass; `provider_calls=0`; `private_score_manifest.record_count=180` (30 records × 6 arms); `private_score_manifest.storage_class=tmp_private`; `private_score_manifest.path_publicly_serialized=false`; `aggregate_runtime_seconds=386.3`. BEA v0.2 vs BEA v0 / same-budget BM25 / agreement-only / RRF: `file_recall@10` delta=+0.033334, `mrr` delta=+0.081667, `span_f0.5@10` delta=-0.012947, `success_rate` delta=+0.033334, `latency_seconds` delta=+8.188547, `evidence_budget_used` delta=0.0. Win/tie/loss (v0.2 vs v0, n=30): file_recall@10 win=3 tie=25 loss=2; mrr win=7 tie=21 loss=2; span_f0.5@10 win=0 tie=28 loss=2; success_rate win=3 tie=25 loss=2. Against seeded random, v0.2 deltas were stronger positive (`file_recall@10` +0.233334, `mrr` +0.326667, `span_f0.5@10` +0.019687, `success_rate` +0.233334). This is a mixed smoke-level mechanism result, not a method-winner/default/performance/calibration claim.

### BEA-3: Anchor/Span/Latency-Aware Policy Smoke

- BEA-3: frozen BEA v0.3 anchor/span/latency-aware policy smoke over fresh heldout ContextBench verified Python rows (offset 60, limit 20) + RepoQA Python needles (offset 30, limit 10). v0.3 reserves `anchor_count=min(2,budget)` slots for BM25/agreement anchors, applies diversity/risk scoring to remaining budget, adds runtime-clean span/latency proxies (tighter line-span bonus, same-file-as-anchor support bonus, risk bucket penalties, weak-support + low-BM25 penalty, fixed marginal-priority early stop after anchors). Frozen weights: anchor=0.35, span_tight=0.15, anchor_file_support=0.10, weak_support_penalty=-0.20, early_stop_margin=0.05 — NOT tuned from outcomes. Required ablations: `v0_3_no_anchor`, `v0_3_no_early_stop`. 9 fixed arms: v0.3, v0.3_no_anchor, v0.3_no_early_stop, v0.2, v0, bm25_prefix, agreement_only, seeded_random, rrf_same_budget (when available). Schema `bea3_anchor_span_latency.v1`, `claim_level=bea_v03_policy_smoke_only`, phase `BEA-3`, 225/225 self-test checks pass. Public artifact is records-only: `benchmark_arm_metric_records`, `delta_records`, `mechanism_contrast_records`, `win_tie_loss_records`, `mechanism_summary_records` (anchor_used_rate, early_stop_rate, mean_budget_used, mean_latency_seconds, mean_span_extent, span_proxy_bucket counts), aggregate `private_score_manifest`. New metric: `quality_per_latency` = span_f0.5@10 / latency_seconds. Latency attribution fix: all arms share candidate-collection latency. Private per-record SCORE JSONL (one row per record × arm, 9 arms) written ONLY under `/tmp`. All no-claim / no-runtime-change flags false. BEA-3 is NOT a benchmark result, NOT a leaderboard entry, NOT a performance claim, NOT a method-winner claim, NOT a calibration claim, NOT a promotion, NOT a default change, NOT a runtime/retriever/pack/backend/EvidenceCore semantic change, and NOT a downstream agent value claim. BEA-3 does NOT mutate BEA-0/BEA-1/BEA-2 semantics. See `docs/en/bea3-anchor-span-latency.md`.
Bounded local run (2026-06-21) with ContextBench offset 60 limit 3 + RepoQA offset 30 limit 2, budget=5, methods bm25/regex/symbol, rrf baseline enabled: 5 records successful, forbidden scan pass, `provider_calls=0`, `private_score_manifest.record_count=45` (5×9 arms), `private_score_storage_class=tmp_private`, `private_score_path_publicly_serialized=false`. Win/tie/loss (v0.3 vs v0.2, n=5): file_recall@10 win=0 tie=5 loss=0; mrr win=0 tie=5 loss=0; span_f0.5@10 win=0 tie=5 loss=0; success_rate win=0 tie=5 loss=0. v0.3 ties v0.2 on all primary metrics on this bounded sample (all candidates were tight-span, low-risk, BM25-backed — the span/latency proxies didn't change the accepted set). Mechanism summary: anchor_used_rate=1.0, early_stop_rate=0.0, mean_budget_used=5.0, mean_span_extent=4.88. This is an honest smoke-level result, not a method-winner or calibration claim.


- `docs/final-research-report.md` — long R0-R29 historical report.
- `docs/research-summary.md` — stage-by-stage status summary.
- `docs/r29-r26-stress-matrix.md` — R29 matrix and failure clusters.
- `docs/r45-promotion-candidate-report.md` — R30-R45 conclusion checkpoint.
- `docs/real-provider-p7-summary.md` — P1-P6 real-provider summary.
- `docs/real-provider-ci-scale-p8-p9.md` — first CI scale-up results.
- `docs/en/real-provider-ci-large-scale.md` — L1/L2 real-provider large-scale results.
- `docs/p20-llm-large-scale.md` — P20-LS-A low-context LLM alias scale-up result.
- `docs/p21-g-cross-model-context-injection.md` — P21-G cross-model context-injection plan.
- `docs/p25-bucket-routed-policy.md` — P25 bucket-routed LLM role policy.
- `docs/p30-admission-model-v3.md` — P30 Admission Model V3 report.
- `docs/p30-admission-model-v3-remote-smoke.md` — first P30 real remote smoke.
- `docs/p30-h1-remote-smoke.md` — P30-H1 enriched handoff real remote smoke.
- `docs/p30-h2-remote-smoke.md` — P30-H2 stricter local-anchor admission real remote smoke.
- `docs/p30-h3-span-cost-accounting.md` — P30-H3 action-specific span-cost accounting (diagnostic-only, score-phase-only, no route change).
- `docs/p30-h3-remote-smoke.md` — P30-H3 real remote smoke action-cost diagnosis.
- `docs/en/p48-diagnostic-policy-simulator.md` — P48 diagnostic policy simulator / request-more-context overlay (not evidence, not admission, not default).
- `docs/en/p49-contrastive-candidate-pack-scaffold.md` — P49 contrastive candidate pack scaffold (not evidence, not admission, not default, metadata-only pack construction).
- `docs/en/p52-metadata-local-verifier-scaffold.md` — P52 metadata-only local verifier scaffold (not evidence, not admission, not default, source/query features unavailable, candidate-risk diagnostics only).
- `docs/en/p52b-source-backed-local-verifier-feature-matrix.md` — P52B source-backed local verifier feature matrix (not evidence, not admission, not default, source-shape heuristic diagnostics only, AST/query features unavailable).
- `docs/en/c5-contextbench-verified-performance-smoke.md` — C5-A ContextBench verified retrieval performance smoke (aggregate-only; external benchmark retrieval smoke; not a benchmark result, not a leaderboard entry, not a performance claim, not a promotion, not a default change, not a downstream agent value claim).
- `docs/en/c5b-contextbench-verified-method-matrix-smoke.md` — C5-B ContextBench verified retrieval method matrix smoke (aggregate-only; multi-method matrix smoke; default bm25,regex,symbol; fixed baseline_method=bm25; per-method records; aggregate-only deltas vs bm25; no winner/best_method/recommended_default; not a benchmark result, not a leaderboard entry, not a performance claim, not a promotion, not a default change, not a downstream agent value claim).
- `docs/en/c5c-contextbench-method-matrix-scale-smoke.md` — C5-C ContextBench verified retrieval method matrix scale smoke (aggregate-only; bounded 20-row method-matrix scale smoke; bm25,regex,symbol only (no text); fixed baseline_method=bm25; per-method records with optional aggregate_runtime_seconds; aggregate-only deltas vs bm25; input_summary block; no winner/best_method/recommended_default; not a benchmark result, not a leaderboard entry, not a performance claim, not a promotion, not a default change, not a downstream agent value claim).
- `docs/en/c5d-repoqa-bm25-retrieval-smoke.md` — C5-D RepoQA BM25 retrieval performance smoke (aggregate-only; bounded RepoQA Python needle subset; transient /tmp asset download + clone + retrieval + score; bm25 only; python only (no silent all-language fallback); no winner/best_method/recommended_default; not a benchmark result, not a leaderboard entry, not a performance claim, not a promotion, not a default change, not a downstream agent value claim).
- `docs/en/c5e-repoqa-method-matrix-smoke.md` — C5-E RepoQA method-matrix retrieval smoke (aggregate-only; bounded RepoQA Python needle subset per method; bm25,regex,symbol only (no text); transient /tmp asset download + clone + retrieval + score; per-method records with aggregate_runtime_seconds; aggregate-only deltas vs bm25; no winner/best_method/recommended_default; not a benchmark result, not a leaderboard entry, not a performance claim, not a promotion, not a default change, not a downstream agent value claim).
- `docs/en/c5f-repoqa-method-matrix-scale-smoke.md` — C5-F RepoQA 10-needle method-matrix scale smoke (aggregate-only; separate C5-F checkpoint; bm25,regex,symbol only; default/hard cap 10 Python needles per method; no provider calls; no winner/best_method/recommended_default; not a benchmark result, not a leaderboard entry, not a performance claim, not a promotion, not a default change, not a downstream agent value claim).
- `docs/en/f1c-cross-benchmark-retrieval-utility.md` — F1-C cross-benchmark retrieval-derived utility smoke (aggregate-only; reruns real bounded external data: ContextBench verified 20-row + RepoQA 10-needle Python; bm25,regex,symbol + empty_retrieval zero baseline; fixed retrieval_utility proxy; cross-benchmark weighted means; 5 fixed counterfactual effects bm25_vs_empty/regex_vs_empty/symbol_vs_empty/regex_vs_bm25/symbol_vs_bm25; ContextBench and RepoQA failure categories kept separate; no provider calls; no winner/best_method/recommended_default/E_S notation; not a benchmark result, not a leaderboard entry, not a performance claim, not a method winner, not a promotion, not a default change, not a downstream agent value claim, not true E/S calibration).
- `docs/en/f1d-cross-benchmark-retrieval-robustness.md` — F1-D cross-benchmark retrieval utility robustness smoke (aggregate-only; reruns real bounded external data: ContextBench verified 20-row + RepoQA 10-needle Python; per-unit metrics intercepted in memory before aggregation; bm25,regex,symbol + empty_retrieval zero baseline; fixed retrieval_utility proxy unchanged from F1-C; cross-benchmark weighted means; paired cross-benchmark bootstrap preserving sample counts; 5 fixed effects x 5 metrics = 25 bootstrap effect records with CI p05/p50/p95 and sign-stability fractions; benchmark_method_means/cross_benchmark_method_means/bootstrap_effect_records/input_summary/bootstrap_summary only; no per-unit metric arrays; no F1-C container names; ContextBench and RepoQA failure categories kept separate; no provider calls; bootstrap replicates default 1000 hard cap 2000 seed 20240621; no winner/best_method/recommended_default/E_S notation; not a benchmark result, not a leaderboard entry, not a performance claim, not a formal confidence interval, not a method winner, not a promotion, not a default change, not a downstream agent value claim, not true E/S calibration).
- `docs/en/d5a1-automated-calibration-feature-table.md` — D5-A1 automated calibration feature table (aggregate-only; machine-reads committed aggregate artifacts: F1-D/F1-C/C5-C/C5-F/B16-E required, D5-A0/B16-D optional if present and claim-safe; fail-closed input validation (schema/status/claim-flags/forbidden_scan); extracts retrieval robustness signals (F1-D bm25_vs_empty/regex_vs_bm25/symbol_vs_bm25 point/CI/sign stability), external benchmark agreement/disagreement (C5-C+C5-F bm25 positive on both, regex/symbol negative on both, method agreement counts), live provider delta (B16-E context_pack_signal/solve_rate_delta/families); computes deterministic calibration feature/bucket records (magnitude buckets, sign stability buckets, live provider delta bucket, family distribution bucket, cross-signal alignment label); readiness buckets ready_for_manual_review/needs_more_live_downstream/retrieval_only_insufficient/conflicting_signals/insufficient_signal; recommended next measurements manual_reference_audit/heldout_benchmark_scale/live_downstream_scale (measurement-only, NOT policy/default/method winner); input_artifact_records/signal_records/calibration_feature_records/readiness_bucket_records/recommended_next_measurement_records only; no per-unit metric arrays, no raw input artifact paths/content, no B16 task text, no winner/best/default/calibrated-model/policy-recommendation fields, no E/S notation; feature extraction, NOT calibration; not a benchmark result, not a leaderboard entry, not a performance claim, not a formal confidence interval, not a method winner, not a promotion, not a default change, not a downstream agent value claim, not true E/S calibration, not a calibrated model claim, not a policy recommendation).
- `docs/en/d5a2-heldout-feature-validation.md` — D5-A2 heldout feature validation smoke (aggregate-only; runs fresh heldout ContextBench rows 21-40 + RepoQA needles 11-20; loads D5-A1 committed artifact as preregistered feature source (fail-closed); methods bm25/regex/symbol only; fixed retrieval_utility proxy unchanged from F1-C/F1-D; 4 retrieval-feature validations (bm25_vs_empty magnitude/sign stability, regex/symbol_vs_bm25 sign stability); validation outcomes retrieval_feature_validation_supported/mixed/not_supported/unavailable; d5a1_input_record/heldout_benchmark_method_records/validation_records/validation_summary_records only; no per-unit metrics, no row/needle IDs, no winner/default/calibration claims; heldout feature validation, NOT calibration, NOT policy/default, NOT method winner, NOT benchmark performance, NOT downstream value, NOT runtime/retriever/pack/backend/default-policy/EvidenceCore change; validates only retrieval-feature stability from D5-A1, NOT live-provider/downstream alignment).
- `docs/en/bea0-budgeted-evidence-acquisition.md` — BEA-0 Budgeted Evidence Acquisition v0 (aggregate-only; first real algorithmic retrieval/acquisition experiment; reruns fresh multi-method retrieval over bounded real ContextBench verified Python rows + RepoQA Python needles; deterministic bea_v0_budgeted policy with action trace + budget states under an evidence budget; private per-record SCORE JSONL traces in /tmp only (never committed, never uploaded; private SCORE path NEVER serialized in public artifact/docs/CI); aggregate-only per-arm metrics + baseline-vs-treatment deltas vs bm25_top10 and rrf_bm25_regex_symbol_top10; runtime-clean policy (no gold/labels/row-IDs/benchmark-labels/previous-outcomes/provider-model-names/private-buckets); actions accept_candidate/skip_low_support/rerank_by_agreement/stop_budget_exhausted + optional expand_same_file; no provider calls; no winner/best_method/recommended_default/method_winner/calibration; not a benchmark result, not a leaderboard entry, not a performance claim, not a method-winner claim, not a calibration claim, not a promotion, not a default change, not a runtime/retriever/pack/backend/EvidenceCore semantic change, not a downstream agent value claim).
- `docs/en/bea1-mechanism-ablation.md` — BEA-1 Mechanism Ablation Smoke (aggregate-only records; mechanism ablation over fresh bounded ContextBench verified Python rows + RepoQA Python needles; 5 fixed arms: bm25_top10, bea_v0_budgeted, same_budget_bm25_prefix, agreement_only_same_budget, seeded_random_same_budget (rrf_bm25_regex_symbol_top10 when enabled); same-budget K exactly = min(len(bea_v0_budgeted.accepted_candidates), available_deduped_candidate_count); paired denominator rule; mechanism_contrast_records with record_count; private per-record SCORE JSONL in /tmp only (never committed, never uploaded; private SCORE path NEVER serialized); runtime-clean same-budget controls (no gold/labels/row-IDs/provider-model fields in seed or ordering); no provider calls; no winner/best_method/recommended_default/method_winner/calibration; not a benchmark result, not a leaderboard entry, not a performance claim, not a method-winner claim, not a calibration claim, not a promotion, not a default change, not a runtime/retriever/pack/backend/EvidenceCore semantic change, not a downstream agent value claim).
- `docs/en/bea2-policy-v02.md` — BEA-2 Policy v0.2 Diversity/Risk Mechanism Smoke (records-only; fresh heldout ContextBench verified Python rows offset 40 limit 20 + RepoQA Python needles offset 20 limit 10; 5 fixed policy arms: bm25_prefix_same_budget, agreement_only_same_budget, bea_v0, bea_v0_2_diversity_risk, seeded_random_same_budget (rrf_same_budget when enabled); BEA v0.2 = frozen-priority-weight diversity/risk-aware greedy selection (agreement + bm25_norm + diversity + query/path overlap - risk penalty - duplication penalty); private per-record SCORE JSONL in /tmp only (one row per record × policy arm; never committed; private SCORE path NEVER serialized); benchmark_arm_metric_records + delta_records + mechanism_contrast_records + win_tie_loss_records; no provider calls; no winner/best_method/recommended_default/method_winner/calibration; not a benchmark result, not a leaderboard entry, not a performance claim, not a method-winner claim, not a calibration claim, not a promotion, not a default change, not a runtime/retriever/pack/backend/EvidenceCore semantic change, not a downstream agent value claim).
- `docs/en/bea3-anchor-span-latency.md` — BEA-3 Anchor/Span/Latency-Aware Policy Smoke (records-only; fresh heldout ContextBench verified Python rows offset 60 limit 20 + RepoQA Python needles offset 30 limit 10; 9 fixed arms: bea_v0_3_anchor_span_latency, bea_v0_3_no_anchor, bea_v0_3_no_early_stop, bea_v0_2_diversity_risk, bea_v0, bm25_prefix_same_budget, agreement_only_same_budget, seeded_random_same_budget (rrf_same_budget when enabled); BEA v0.3 = frozen anchor/span/latency-aware policy (anchor slots + diversity/risk + span tightness + anchor file support + weak-support penalty + marginal early stop); new metric quality_per_latency; new record type mechanism_summary_records; private per-record SCORE JSONL in /tmp only (one row per record × arm; never committed; private SCORE path NEVER serialized); no provider calls; no winner/best_method/recommended_default/method_winner/calibration; not a benchmark result, not a leaderboard entry, not a performance claim, not a method-winner claim, not a calibration claim, not a promotion, not a default change, not a runtime/retriever/pack/backend/EvidenceCore semantic change, not a downstream agent value claim).

---

## 8. Next Research Questions

The next step is not promotion. It is larger, more granular, more reproducible validation:

1. Freeze the L2 task set into a reproducible suite to avoid task-generation drift.
2. Run P21-G context atom screening on public/opt-in corpora: signatures, matched lines, retrieval scores, flags, body windows, neighbors, related tests, and hard distractors.
3. Extend P3/P4 beyond Django/Kubernetes only after false-span analysis.
4. Continue bge-m3 vs Qwen 0.6B/4B/8B bakeoffs on identical task sets, including latency/cost.
5. Feed P5 stress traps into anchored dense/QuIVer validation and measure whether added_gold consistently exceeds added_false.
6. Re-validate symbol repair and regex normalization on R26/R38, focusing on bucket regressions.
7. Add real dense support scores to admission_v2 research, but only as supporting features.
8. Continue QuIVer sharding/prototype work; do not claim QuIVer quality until graph/ANN backend evidence exists.
9. If LLM query aliases are revisited, test only grounded variants: inventory-selected aliases or aliases derived after seeing top-k local candidate snippets.
10. Run P21-G rich LLM candidate support: rerank/filter/span-narrow/abstain/inventory_alias over snippet-backed local candidates, record model-averaged and per-model effects, and report quality, latency, token, and cost trade-offs.
11. P30-H3: add action-specific span-cost accounting and false-span budgets for weak/supporting/filter outcomes before further route tuning.

---

## 9. Current Bottom Line

OpenLocus has established a quality-and-evidence-gated research direction: local lexical/symbol/RRF retrieval is the backbone, while real embeddings, QuIVer, LLM-derived views, and graph signals are valuable only when grounded and validated. L1/L2 shows dense-only/global dense cannot be primary/default, and P20-LS-A shows low-context/query-only LLM aliases cannot be scaled as-is. P22/P23 now frames the next phase as evidence-seeking retrieval policy research: preserve local recall, use precision anchors and guard surfaces to suppress false primary, route dense/LLM roles only where the bucket/candidate surface supports them, and let EvidenceCore remain the only fact authority. P30 provides a deterministic, explainable admission scaffold to compare these policy surfaces.
