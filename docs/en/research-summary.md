# OpenLocus Research Summary

For the current research-conclusion synthesis, see
[`docs/en/current-research-conclusions.md`](current-research-conclusions.md)
or the index page [`docs/current-research-conclusions.md`](../current-research-conclusions.md).

当前研究结论总报告见
[`docs/zh/current-research-conclusions.md`](../zh/current-research-conclusions.md)，
入口索引见 [`docs/current-research-conclusions.md`](../current-research-conclusions.md)。

This document will be updated after each evidence-gated stage. The detailed
chronological notes below are preserved for traceability; the current high-level
research conclusion is summarized first.

## Historical status update — 2026-06-20 (D4-series rollup / D5-H blocked)

The latest checkpoint is the D4-series harness rollup (`b7c65dd`,
`add D4 harness rollup`). It is a public rollup-only artifact
(`eval/d4_series_rollup.py` ->
`artifacts/d4_series_rollup/d4_series_rollup_report.json`) with
`schema_version=d4_series_rollup.v1`,
`claim_level=d4_series_harness_rollup_only`, and
`status=d5_blocked_no_real_human_manual_labels`.

The C4 external benchmark readiness sequence is complete through C4.5: ContextBench
schema/readiness and verified row-mapping smoke, SWE-Explore row-mapping with a
negative line-budget-shape observation, CORE-Bench source-readiness no-go, and
RepoQA source/schema-contract readiness. These are readiness and boundary results,
not external benchmark performance claims.

The Step 6 / D-series dual-rubric control plane is complete through D4 rollup:

```text
D1 deterministic dual-rubric scaffold
-> D2 public aggregate mappability + private proxy smoke
-> D3 true E/S label protocol preregistration
-> D4a execution gate / dry-run
-> D4b true-label bundle harness
-> D4c annotation packet builder harness
-> D4d human annotation runbook/checklist
-> D4e filled-packet -> D4b bundle converter harness
-> D4f D4b bundle validation / gate-check harness
-> D4-series rollup / D5 blocked status
```

The D-series result is control-plane readiness only. It does **not** collect real
human/manual labels, does **not** convert or validate a real human-label bundle,
does **not** compute calibration/agreement/CI metrics, and does **not** unblock
D5-H / human-reference calibration. This historical D4-rollup state is superseded
for ongoing work by the D5-A0 empirical pivot below: lack of human/manual labels
does not block the automated/programmatic D5-A path.

Current no-claim flags remain false: `promotion_ready=false`,
`default_should_change=false`, `evidencecore_semantics_changed=false`,
`runtime_clean_general_algorithm_claimed=false`, `downstream_agent_value_proven=false`,
`true_e_s_calibration_claimed=false`, and external benchmark performance remains
unclaimed. The active next step is no longer an E1 control-plane preregistration;
it is the D5-A automated empirical path recorded below.

## Current status update — 2026-06-20 (D5-A0 automated E/S calibration smoke)

Following the D4-series rollup, the trajectory was corrected: the
control-plane-only stages stop here, and D5-A0 produces the first empirical,
post-control-plane smoke. The D5-H / human-reference / human-calibrated audit
remains out of scope/unavailable until real human/manual true E/S labels are
collected; the D5-A automated/programmatic empirical path is active and
continues. D5-A0 (`eval/d5a_automated_es_calibration.py` ->
`artifacts/d5a_automated_es_calibration/d5a_automated_es_calibration_report.json`,
schema `d5a_automated_es_calibration.v1`,
`claim_level=automated_e_s_calibration_smoke_only`,
`status=automated_es_calibration_smoke_pass`,
`mode=public_aggregate_r14_retrieval_smoke`, phase `D5-A0`) derives
**automated E labels** and **deterministic S-proxy labels** from the existing
committed r14 sanity span labels (gold spans + hard negatives) over real
OpenLocus retrieval outputs (regex, bm25, symbol, rrf). It invokes
`eval/run_retrieval.py` per method into transient `/tmp/d5a_retrieval_*`
outputs (never committed) and writes ONLY aggregate counts/rates to the
committed artifact. 157/157 self-test checks pass; all four methods succeeded;
3152 candidates labeled total.

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

## Current status update — 2026-06-20 (B16-A minimal mock downstream paired run)

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
**real subprocess tests**, and computes aggregate behavior metrics
(solve_rate, tests_pass_rate, correct_file_before_first_edit_rate,
wrong_file_edits_mean, tool_calls_before_first_edit_mean,
context_tokens_mean, latency_ms_mean, cost_proxy_mean) over paired
control/treatment arms. The treatment pack causally alters the mock
agent's behavior (treatment solve_rate=1.0 vs control solve_rate=0.0).
104/104 self-test checks pass; 24 tasks; 48 total runs.

This is smoke-only. It does NOT claim downstream agent value, does NOT
claim live agent generalization, does NOT claim external benchmark
performance, does NOT claim a real user task, does NOT promote any
candidate, and does NOT change runtime/retriever/pack/backend/
default-policy/EvidenceCore semantics. The per-run event logs,
patches, and test output stay under `/tmp` only and are NEVER committed
or uploaded. The committed artifact is aggregate-only. All no-claim /
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
(`downstream_agent_runs_performed`, `deterministic_mock_agent`,
`synthetic_micro_tasks_used`, `paired_arms_evaluated`,
`real_file_edits_performed`, `real_test_commands_executed`,
`agent_behavior_metrics_evaluated`, `aggregate_only_public_artifact`,
`diagnostic_only`) are the only additional true flags. No runtime/
  retriever/pack/model/backend/default-policy files were modified. See
  the [B16-A detailed report](b16a-minimal-mock-agent-paired-run.md).

## Current status update — 2026-06-21 (B16-B less-separable mock downstream paired stress)

Following B16-A, B16-B extends the deterministic/mock downstream
paired-agent empirical run from deliberately separable micro bugs to a
harder **less-separable multi-cue stress** task family. B16-B
(`eval/b16b_less_separable_mock_paired_run.py` ->
`artifacts/b16b_less_separable_mock_paired_run/b16b_less_separable_mock_paired_run_report.json`,
schema `b16b_less_separable_mock_paired_run.v1`,
`claim_level=deterministic_mock_downstream_paired_stress_only`,
`status=mock_downstream_paired_stress_pass`,
`mode=public_aggregate_synthetic_stress_tasks`, phase `B16-B`)
generates deterministic synthetic public less-separable stress tasks
in code, creates a fresh `/tmp` workspace per task+arm with real
multi-file Python modules (target.py with decoy symbol, distractor.py
with same symbol, support.py with offset constant, test_target.py) +
stdlib tests, runs a **deterministic mock agent** (no live LLM, no
provider calls, no remote calls) that performs **real file edits** and
runs **real subprocess tests**, and computes aggregate behavior metrics
(solve_rate, tests_pass_rate, correct_file_before_first_edit_rate,
wrong_file_edits_mean, tool_calls_before_first_edit_mean,
context_tokens_mean, latency_ms_mean, cost_proxy_mean) over paired
control_sparse/treatment_multi_cue arms. Solving requires combining
four cues (target_file + target_symbol + operation_hint +
support_relation); missing any cue causes a deterministic wrong action.
The treatment multi-cue pack causally alters the mock agent's behavior
(treatment solve_rate=1.0 vs control solve_rate=0.0). 147/147 self-test
checks pass; 24 tasks; 48 total runs. Treatment is perfect by
construction; docs describe this as a harness/stress result, NOT a
live agent result.

This is stress-only. It does NOT claim downstream agent value, does
NOT claim live agent generalization, does NOT claim external benchmark
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
(`downstream_agent_runs_performed`, `deterministic_mock_agent`,
`paired_run_executed`, `real_file_edits_performed`,
`subprocess_tests_executed`, `less_separable_stress_tasks`,
`aggregate_only_public_artifact`, `diagnostic_only`) are the only
additional true flags. No runtime/retriever/pack/model/
backend/default-policy files were modified. See the
[B16-B detailed report](b16b-less-separable-mock-paired-run.md).

## Current status update — 2026-06-21 (B16-C live-provider downstream paired smoke)

Following B16-A/B16-B (deterministic/mock), B16-C produces the first
**live-provider** B16-style downstream-agent empirical run. B16-C
(`eval/b16c_live_provider_paired_smoke.py` + shared
`eval/provider_client.py` ->
`artifacts/b16c_live_provider_paired_smoke/b16c_live_provider_paired_smoke_report.json`,
schema `b16c_live_provider_paired_smoke.v1`,
`claim_level=live_provider_downstream_paired_smoke_only`,
`mode=public_aggregate_synthetic_micro_tasks`, phase `B16-C`) generates
deterministic synthetic public micro bug tasks, creates a fresh `/tmp`
workspace per task+arm, runs a **live LLM agent** (OpenAI-compatible)
only when `--allow-remote` + `OPENLOCUS_ALLOW_REMOTE=1` + provider env
are all set, applies the model's structured edit action locally
(allowlisted `target.py` only; actions `replace_return_value` /
`no_op` only), runs real subprocess tests, and computes aggregate
behavior metrics over paired `control_sparse` /
`treatment_context_pack` arms. Manual CI run `27900913599`
(`real-provider-benchmark`, `stage=b16c_live_provider_paired_smoke`,
`enable_remote_models=true`) completed
`status=live_provider_paired_smoke_pass`; the committed artifact now
mirrors that sanitized aggregate CI report. The run executed 2 synthetic
tasks / 4 live provider calls, 4/4 calls succeeded, invalid_json_count=0,
and the workflow privacy validator passed. Both arms solved both trivial
micro tasks (`control_sparse` solve_rate=1.0;
`treatment_context_pack` solve_rate=1.0), so the treatment-minus-control
solve-rate delta is 0.0. 33/33 provider-client self-test checks pass;
119/119 B16-C self-test checks pass.

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
`evidencecore_semantics_changed=false`). Live-run flags
(`downstream_agent_runs_performed`, `live_llm_agent`,
`provider_calls_made`, `remote_provider_calls_made`,
`paired_run_executed`, `synthetic_micro_tasks_used`,
`real_file_edits_performed`, `real_test_commands_executed`,
`agent_behavior_metrics_evaluated`) are true ONLY when a live run
actually executed; otherwise false. No raw model routing prefix is
emitted; only the normalized `model_display_category` is recorded. No
runtime/retriever/pack/model/backend/default-policy files were
modified. The B16-C upload surface is dedicated to the sanitized
aggregate report only; generic `real-provider` artifacts such as
`plan.json` are excluded from the B16-C artifact upload. See the
[B16-C detailed report](b16c-live-provider-paired-smoke.md).

## Current status update — 2026-06-21 (B16-D less-trivial live-provider downstream paired smoke)

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
support relation required; correct value =
`helper_constant * 2 + task_index`), creates a fresh `/tmp` workspace
per task+arm, runs a **live LLM agent** (OpenAI-compatible) only when
`--allow-remote` + `OPENLOCUS_ALLOW_REMOTE=1` + provider env are all
set, applies the model's structured edit action locally (allowlisted
`target.py` only; actions `replace_return_value` /
`choose_helper_constant` / `no_op`; distractor/support NOT editable),
runs real subprocess tests, and computes aggregate behavior metrics
over paired `control_sparse` / `treatment_context_pack` arms.
Treatment includes target file cue, target symbol cue, support-relation
cue, and exact edit constraint; control lacks the decisive cues. Manual
CI run `27901644438` (`real-provider-benchmark`,
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
false). 138/138 self-test checks pass.

This is smoke-only. It does NOT claim downstream agent value, does NOT
claim live agent generalization, does NOT claim external benchmark
performance, does NOT claim a real user task, does NOT promote any
candidate, and does NOT change runtime/retriever/pack/backend/
default-policy/EvidenceCore semantics. CI pass means live run completed
+ privacy scan passed + artifact is honest; CI pass does NOT require
treatment improvement (zero/negative delta is valid). Per-run prompts,
responses, event logs, patches, and test output stay under `/tmp` only
and are NEVER committed or uploaded. Honest signal fields
(`context_pack_signal_observed`, `treatment_solve_rate_delta`,
`treatment_wrong_file_edits_delta`) are diagnostic smoke outcomes only,
NEVER promotion/default/value claims. All no-claim / no-runtime-change
flags remain false. Live-run flags are true ONLY when a live run
actually executed; otherwise false. No raw model routing prefix is
emitted; only the normalized `model_display_category` is recorded. No
runtime/retriever/pack/model/backend/default-policy files were
modified. The positive treatment delta is a tiny synthetic smoke signal,
not proof of downstream value or generalization. See the
[B16-D detailed report](b16d-less-trivial-live-provider-paired-smoke.md).

## Current status update — 2026-06-21 (B16-E broader live-provider downstream paired smoke)

Following B16-D, B16-E broadens the live-provider paired smoke from one
task family into a heterogeneous synthetic task-family matrix with four
fixed families. B16-E
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
`treatment_context_pack` arms. Manual CI run `27902925812` (`real-provider-benchmark`,
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
188/188 self-test checks pass.

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
a live run actually executed. No raw model routing prefix is emitted;
only the normalized `model_display_category` is recorded. No
runtime/retriever/pack/model/backend/default-policy files were
modified. See the
[B16-E detailed report](b16e-broader-live-provider-paired-smoke.md).

## Current status update — 2026-06-21 (D5-A2 heldout feature validation smoke)

D5-A2 validates whether D5-A1's retrieval-derived feature bucket
reproduces on fresh heldout external retrieval samples. D5-A2
(`eval/d5a2_heldout_feature_validation.py`, reusing C5-A/C5-C/C5-D/C5-E
primitives backward-compatibly; none modified) ->
`artifacts/d5a2_heldout_feature_validation/d5a2_heldout_feature_validation_report.json`,
schema `d5a2_heldout_feature_validation.v1`,
`claim_level=heldout_retrieval_feature_validation_smoke_only`,
`status=heldout_feature_validation_pass|partial|unavailable_with_reason|fail_forbidden_scan|fail_schema_contract`,
`mode=heldout_contextbench_repoqa_feature_validation`, phase `D5-A2`)
loads the D5-A1 committed artifact as the preregistered feature source
(fail-closed on missing/schema-mismatch/unsafe-claim-flags), runs fresh
heldout ContextBench verified Python rows 21-40 (fetch 40, evaluate
slice [20,40)) and RepoQA Python needles 11-20 (parse 20, evaluate
slice [10,20)) with methods bm25/regex/symbol, computes the same fixed
retrieval-derived utility proxy (unchanged from F1-C/F1-D), and checks
4 retrieval-feature validations (bm25_vs_empty magnitude/sign
stability; regex/symbol_vs_bm25 sign stability). Validation outcomes
(fixed allowlist): `retrieval_feature_validation_supported`,
`retrieval_feature_validation_mixed`,
`retrieval_feature_validation_not_supported`,
`unavailable_with_reason`. Records-shaped lists only
(`d5a1_input_record`, `heldout_benchmark_method_records`,
`validation_records`, `validation_summary_records`); no per-unit
metric arrays, no row/needle IDs, no winner/default/calibration claims.
88/88 self-test checks pass. Local heldout run and manual CI run `27915252367` passed: status
`heldout_feature_validation_pass`, forbidden scan pass,
`validation_outcome=retrieval_feature_validation_supported`,
contextbench_rows_fetched=20, repoqa_needles_seen=10,
network_calls=2, provider_calls=0; all 4 D5-A1 retrieval features
reproduce on heldout data (bm25_vs_empty heldout +0.727961 positive
supported; bm25 sign stability heldout file_recall +0.6 positive
supported; regex/symbol_vs_bm25 heldout -0.977961 negative supported).

This is heldout feature validation, NOT calibration. It is NOT
calibration, NOT a calibrated model claim, NOT a policy/default
recommendation, NOT a benchmark result, NOT downstream utility, NOT
true E/S calibration, NOT an external benchmark performance claim, NOT
a leaderboard entry, NOT a method winner, NOT a promotion/default/
runtime/retriever/pack/backend/EvidenceCore semantic change. It
validates only retrieval-feature stability from D5-A1; it does NOT
validate live-provider/downstream alignment. All no-claim /
no-runtime-change flags remain false.
`heldout_feature_validation_executed=true` only when a real heldout run
actually executed. See the
[D5-A2 detailed report](d5a2-heldout-feature-validation.md).

## Current status update — 2026-06-21 (D5-A1 automated calibration feature table)

D5-A1 moves from empirical smokes to **calibration-ready weak-supervision
features** by machine-reading committed aggregate artifacts. D5-A1
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
(magnitude buckets, sign stability buckets, live provider delta bucket,
family distribution bucket, cross-signal alignment label) and
readiness buckets (`ready_for_manual_review`,
`needs_more_live_downstream`, `retrieval_only_insufficient`,
`conflicting_signals`, `insufficient_signal`). Recommended next
measurements are measurement-only (`manual_reference_audit`,
`heldout_benchmark_scale`, `live_downstream_scale`), NOT policy/
default/method winner. Records-shaped lists only
(`input_artifact_records`, `signal_records`,
`calibration_feature_records`, `readiness_bucket_records`,
`recommended_next_measurement_records`); no per-unit metric arrays, no
raw input artifact paths/content, no B16 task text, no
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

## Current status update — 2026-06-21 (F1-D cross-benchmark retrieval utility robustness smoke)

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
`retrieval_utility`) = 25 bootstrap effect records with fields
`effect_name`, `metric`, `point_estimate`, `bootstrap_mean`,
`ci_p05`, `ci_p50`, `ci_p95`, `sign_positive_fraction`,
`sign_negative_fraction`, `sign_zero_fraction`, `sample_units`,
`bootstrap_replicates`, `bootstrap_seed`. Cross-benchmark resampling
preserves benchmark sample counts (ContextBench 20, RepoQA 10);
paired effects preserve treatment-baseline pairing. `empty_retrieval`
is the explicit zero-context baseline (no retrieval run; all
metrics/utility 0). Records-shaped only
(`benchmark_method_means`, `cross_benchmark_method_means`,
`bootstrap_effect_records`, `input_summary`, `bootstrap_summary`);
no per-unit metric arrays; no F1-C container names; no dynamic dict
mirrors; no winner/best/default fields; no E/S calibration notation;
ContextBench and RepoQA failure categories kept separate. Bootstrap
replicates default 1000 (hard cap 2000), fixed seed 20240621.
185/185 self-test checks pass. Local real-network run and manual CI run `27913035117` passed: 20
ContextBench rows fetched, 10 RepoQA needles seen, status
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

## Current status update — 2026-06-21 (F1-C cross-benchmark retrieval-derived utility smoke)

F1-C is the **cross-benchmark** retrieval-derived utility smoke. F1-C
(`eval/f1c_cross_benchmark_retrieval_utility.py`,
reusing C5-C/C5-E/C5-A/C5-D primitives backward-compatibly; none
modified) ->
`artifacts/f1c_cross_benchmark_retrieval_utility/f1c_cross_benchmark_retrieval_utility_report.json`,
schema `f1c_cross_benchmark_retrieval_utility.v1`,
`claim_level=cross_benchmark_retrieval_derived_utility_smoke_only`,
`status=cross_benchmark_retrieval_utility_pass|partial_with_exclusions|unavailable_with_reason|fail_forbidden_scan|fail_schema_contract`,
`mode=bounded_contextbench_repoqa_retrieval_utility`, phase `F1-C`)
**reruns real bounded external data** for two benchmarks
(ContextBench verified 20-row + RepoQA 10-needle Python), computes a
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
separate. 167/167 self-test checks pass. Local real-network run and
manual CI run `27911651758` passed: 20 ContextBench rows fetched, 10
RepoQA needles seen, status
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

## Current status update — 2026-06-21 (F1-B retrieval-derived counterfactual utility smoke)

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
candidate-set utility deltas. Five variants (`baseline_empty_candidate_set`,
`bm25_topk`, `regex_topk`, `symbol_topk`,
`bm25_plus_symbol_topk`) and four effects
(`bm25_candidates_vs_empty`, `regex_candidates_vs_empty`,
`symbol_candidates_vs_empty`, `symbol_added_to_bm25`). Metrics:
`file_recall@10`, `mrr`, `span_f0.5@10`, `success_rate`.
Records-shaped `variant_results`, `counterfactual_effects`,
`method_inputs`. No provider calls. No winner/best/default fields.
No E/S calibration notation. 95/95 self-test checks pass.
Manual CI run `27903995230` passed: 5 rows fetched/successful,
forbidden scan pass, `bm25_topk` file_recall@10=0.4 / mrr=0.225 /
span_f0.5@10=0.015905 / success_rate=1.0, `regex_topk` and
`symbol_topk` file_recall@10=0.0, and `symbol_added_to_bm25` delta=0.0.

This is smoke-only. It is NOT downstream utility, NOT true E/S
calibration, NOT an external benchmark performance claim, NOT a
leaderboard entry, NOT a promotion/default/runtime/retriever/pack/
backend/EvidenceCore semantic change. All no-claim /
no-runtime-change flags remain false. `retrieval_derived_counterfactual_utility_smoke=true`
only when a real network run actually executed. See the
[F1-B detailed report](f1b-retrieval-derived-counterfactual-utility.md).

## Current status update — 2026-06-21 (C5-A ContextBench verified retrieval performance smoke)

Following D5-A0 and B16-A, C5-A produces the first
external-benchmark-shaped retrieval performance smoke. C5-A
(`eval/c5_contextbench_verified_performance_smoke.py` ->
`artifacts/c5_contextbench_verified_performance_smoke/c5_contextbench_verified_performance_smoke_report.json`,
schema `c5_contextbench_verified_performance_smoke.v1`,
`claim_level=external_benchmark_retrieval_performance_smoke_only`,
`status=pass|partial|unavailable_with_reason`,
`mode=contextbench_verified_retrieval_performance_smoke`, phase
`C5-A`) reads a bounded ContextBench verified subset from HF
datasets-server `/rows` (default 5 rows; hard cap 20; stdlib `urllib`
only), parses `gold_context` JSON into transient `gold_paths`/`gold_lines`
(the `content` field is NEVER read or persisted), sanitizes
`problem_statement` into a retrieval query (in-memory only; first
paragraph / first sentence / raw), clones `repo_url` at `base_commit`
under a per-row `TemporaryDirectory` via `git clone --filter=blob:none
--no-checkout` then `git checkout` (bounded timeouts), generates
transient task/label JSONL under a `TemporaryDirectory`, runs OpenLocus
retrieval via `eval/run_retrieval.py` (`--method bm25 --cwd <repo_root>`,
no provider calls), runs `eval/score.py` and parses aggregate metrics,
and writes ONLY aggregate counts/rates/means to the committed artifact.
113/113 self-test checks pass; 5 rows fetched, 5 rows successful, 0
rows failed.

This is smoke-only. It does NOT claim an external benchmark result,
does NOT claim a leaderboard entry, does NOT claim performance, does
NOT claim a promotion, does NOT claim a default change, does NOT claim
a runtime/retriever/pack/backend/EvidenceCore semantic change, and does
NOT claim downstream agent value. The raw ContextBench rows, queries,
repo URLs/names, base commits, gold paths/spans/contents, generated
task/label/run JSONL, evidence rows, cloned repos, and stdout/stderr
stay under `/tmp` only and are NEVER committed or uploaded. The
committed artifact is aggregate-only. All no-claim /
no-runtime-change flags remain false
(`external_benchmark_performance_claimed=false`,
`downstream_agent_value_proven=false`, `promotion_ready=false`,
`default_should_change=false`, `runtime_behavior_changed=false`,
`retriever_changed=false`, `pack_builder_changed=false`,
`backend_changed=false`, `default_policy_changed=false`,
`evidencecore_semantics_changed=false`, `provider_calls_made=false`,
`remote_provider_calls_made=false`). The safe true flags (true only
if actually true: `external_benchmark_rows_read`,
`repositories_materialized_transiently`, `openlocus_retrieval_executed`,
`score_py_metrics_computed`, `performance_smoke`,
`aggregate_only_public_artifact`, `diagnostic_only`) are the only
additional true flags. If the network smoke cannot complete
(network/HF/GitHub failure, clone timeout, retrieval failure, score
failure), the artifact records truthful `unavailable_with_reason` with
a real `failure_reason_category` (no stale/fake pass). No runtime/
retriever/pack/model/backend/default-policy files were modified. See
the [C5-A detailed report](c5-contextbench-verified-performance-smoke.md).

## Current status update — 2026-06-21 (C5-B ContextBench verified retrieval method matrix smoke)

Following C5-A, C5-B produces the bounded multi-method matrix extension of
the first external-benchmark-shaped retrieval performance smoke. C5-B
(`eval/c5b_contextbench_verified_method_matrix_smoke.py` ->
`artifacts/c5b_contextbench_verified_method_matrix/c5b_contextbench_verified_method_matrix_report.json`,
schema `c5b_contextbench_verified_method_matrix_smoke.v1`,
`claim_level=external_benchmark_retrieval_method_matrix_smoke_only`,
`status=pass|partial|unavailable_with_reason|fail_schema_contract|fail_forbidden_scan`,
`mode=contextbench_verified_retrieval_method_matrix_smoke`, phase
`C5-B`) reads a bounded ContextBench verified subset from HF
datasets-server `/rows` ONCE (default 5 rows per method; hard cap 10;
shared across all methods; stdlib `urllib` only), parses `gold_context`
JSON into transient `gold_paths`/`gold_lines` (the `content` field is
NEVER read or persisted), sanitizes `problem_statement` into a retrieval
query (in-memory only; first paragraph / first sentence / raw), clones
`repo_url` at `base_commit` under a per-row `TemporaryDirectory` via
`git clone --filter=blob:none --no-checkout` then `git checkout` (bounded
timeouts), generates transient task/label JSONL under a
`TemporaryDirectory`, runs OpenLocus retrieval via `eval/run_retrieval.py`
across the requested method matrix (default `bm25,regex,symbol`; allowed
`bm25,regex,text,symbol`; fixed `baseline_method=bm25`; `--method <method>
--cwd <repo_root>`, no provider calls), runs `eval/score.py` per method
and parses aggregate metrics, and writes ONLY aggregate per-method
records + aggregate-only deltas vs the fixed `bm25` baseline to the
committed artifact. 161/161 self-test checks pass; 5 rows fetched (shared
across methods), 3 methods requested (bm25, regex, symbol), 3 methods
successful, 0 methods failed.

This is smoke-only. It does NOT claim an external benchmark result,
does NOT claim a leaderboard entry, does NOT claim performance, does
NOT claim a promotion, does NOT claim a default change, does NOT claim
a runtime/retriever/pack/backend/EvidenceCore semantic change, and does
NOT claim downstream agent value. It does NOT emit `winner`,
`best_method`, `recommended_default`, or anything implying a policy/
default decision. `baseline_method` is fixed to `bm25`,
`baseline_is_policy_candidate=false`, and `default_should_change=false`.
The raw ContextBench rows, queries, repo URLs/names, base commits, gold
paths/spans/contents, generated task/label/run JSONL, evidence rows,
cloned repos, per-row metrics, row-level hashes, and stdout/stderr stay
under `/tmp` only and are NEVER committed or uploaded. The committed
artifact is aggregate-only. All no-claim / no-runtime-change flags
remain false (`external_benchmark_performance_claimed=false`,
`leaderboard_entry_claimed=false`,
`downstream_agent_value_proven=false`, `promotion_ready=false`,
`default_should_change=false`, `baseline_is_policy_candidate=false`,
`runtime_behavior_changed=false`, `retriever_changed=false`,
`pack_builder_changed=false`, `backend_changed=false`,
`default_policy_changed=false`, `evidencecore_semantics_changed=false`,
`provider_calls_made=false`, `remote_provider_calls_made=false`). The
safe true flags (true only if actually true:
`external_benchmark_rows_read`, `repositories_materialized_transiently`,
`openlocus_retrieval_executed`, `score_py_metrics_computed`,
`method_matrix_smoke`, `aggregate_only_public_artifact`,
`diagnostic_only`) are the only additional true flags. If the network
smoke cannot complete (network/HF/GitHub failure, clone timeout,
retrieval failure, score failure), the artifact records truthful
`unavailable_with_reason` with a real `failure_reason_category` (no
stale/fake pass). Earlier C5-C CI run `27905321437` was treated as a fail-open bug
because it uploaded green `unavailable_with_reason`; the workflow now
fails network-enabled unavailable reports. No runtime/retriever/pack/model/backend/default-policy
files were modified. See
the [C5-B detailed report](c5b-contextbench-verified-method-matrix-smoke.md).

## Current status update — 2026-06-21 (C5-C ContextBench verified method matrix scale smoke)

Following D5-A0, B16-A, C5-A, and C5-B, C5-C produces the first
external-benchmark-shaped retrieval method matrix scale smoke. C5-C
(`eval/c5c_contextbench_verified_method_matrix_scale_smoke.py` ->
`artifacts/c5c_contextbench_verified_method_matrix_scale/c5c_contextbench_verified_method_matrix_scale_report.json`,
schema `c5c_contextbench_verified_method_matrix_scale_smoke.v1`,
`claim_level=external_benchmark_retrieval_method_matrix_scale_smoke_only`,
`status=contextbench_method_matrix_scale_smoke_pass|partial|unavailable_with_reason|fail_forbidden_scan`,
`mode=contextbench_verified_bounded_scale_method_matrix`, phase
`C5-C`) scales C5-B up from a 5-row method matrix to a bounded 20-row
method-matrix scale smoke. It reads a bounded 20-row ContextBench
verified subset from HF datasets-server `/rows` ONCE (shared across all
3 methods; hard cap 20; stdlib `urllib` only), materializes the
referenced repositories at `base_commit` under transient `/tmp`
directories (once per method+row) via `git clone --filter=blob:none
--no-checkout` then `git checkout`, runs OpenLocus retrieval across the
requested method matrix (default `bm25,regex,symbol`; only
`bm25,regex,symbol` allowed in C5-C; `text` is NOT allowed; fixed
`baseline_method=bm25`; no provider calls), scores each method against
benchmark label spans via `eval/score.py`, and commits only an aggregate
public report with per-method records (list, NOT dict keyed by method
name), optional per-method `aggregate_runtime_seconds`, aggregate-only
deltas vs the fixed `bm25` baseline, and an `input_summary` block.
179/179 self-test checks pass. Manual CI run `27905621090` passed after
the workflow was made fail-closed for network-enabled runs: 20 rows
fetched, 3/3 methods successful, 0 methods failed; bm25 produced
file_recall@10=0.35, mrr=0.143107, span_f0.5@10=0.020838,
success_rate=1.0; regex and symbol produced file_recall@10=0.0 and
mrr=0.0 on this bounded smoke.

This is smoke-only. It does NOT claim an external benchmark result,
does NOT claim a leaderboard entry, does NOT claim performance, does
NOT claim a promotion, does NOT claim a default change, does NOT claim
a runtime/retriever/pack/backend/EvidenceCore semantic change, and does
NOT claim downstream agent value. It does NOT emit `winner`,
`best_method`, `recommended_default`, or anything implying a policy/
default decision. The raw ContextBench rows, queries, repo URLs/names,
base commits, gold paths/spans/contents, generated task/label/run
JSONL, evidence rows, cloned repos, and stdout/stderr stay under `/tmp`
only and are NEVER committed or uploaded. The committed artifact is
aggregate-only. All no-claim / no-runtime-change flags remain false
(`external_benchmark_performance_claimed=false`,
`leaderboard_entry_claimed=false`,
`downstream_agent_value_proven=false`, `promotion_ready=false`,
`default_should_change=false`, `baseline_is_policy_candidate=false`,
`runtime_behavior_changed=false`, `retriever_changed=false`,
`pack_builder_changed=false`, `backend_changed=false`,
`default_policy_changed=false`, `evidencecore_semantics_changed=false`,
`provider_calls_made=false`, `remote_provider_calls_made=false`). The
safe true flags (true only if actually true:
`retrieval_scale_smoke_performed`, `openlocus_retrieval_executed`,
`score_py_metrics_computed`, `aggregate_only_public_artifact`,
`diagnostic_only`) are the only additional true flags. If the network
smoke cannot complete (network/HF/GitHub failure, clone timeout,
retrieval failure, score failure), the artifact records truthful
`unavailable_with_reason` with a real `failure_reason_category` (no
stale/fake pass). No runtime/retriever/pack/model/backend/default-policy
files were modified. See
the [C5-C detailed report](c5c-contextbench-method-matrix-scale-smoke.md).

## Current status update — 2026-06-21 (C5-D RepoQA BM25 retrieval performance smoke)

Following D5-A0, B16-A, C5-A, C5-B, and C5-C, C5-D produces the first
RepoQA-shaped retrieval performance smoke. C5-D
(`eval/c5d_repoqa_bm25_retrieval_smoke.py` ->
`artifacts/c5d_repoqa_bm25_retrieval_smoke/c5d_repoqa_bm25_retrieval_smoke_report.json`,
schema `c5d_repoqa_retrieval_performance_smoke.v1`,
`claim_level=repoqa_retrieval_performance_smoke_only`,
`status=repoqa_retrieval_smoke_pass|partial|unavailable_asset_download_failed|unavailable_no_python_needles|unavailable_repo_clone_failed|fail_forbidden_scan|fail_schema_contract`,
`mode=repoqa_bounded_bm25_retrieval_smoke`, phase `C5-D`) downloads
the EvalPlus RepoQA release asset `repoqa-2024-06-23.json.gz` from
`evalplus/repoqa_release` to in-memory bytes (transient; NEVER written
to the workspace), decompresses it in memory, parses a bounded RepoQA
Python needle subset (default 5 needles; hard cap 10; NO silent
all-language fallback), materializes the referenced repositories at
their `commit_sha` under transient `/tmp` directories via
`git clone --filter=blob:none --no-checkout` then `git checkout`, runs
OpenLocus `bm25` retrieval (bm25 only; no provider calls), scores
against `needle.path`/`start_line`/`end_line` via `eval/score.py`, and
commits only an aggregate public report. 219/219 self-test checks
pass; 5 needles seen, 5 needles successful, 0 needles failed.
Manual CI run `27906775008` passed with the same aggregate metrics; the
committed artifact now mirrors that sanitized CI report: file_recall@10=0.6,
mrr=0.46, span_f0.5@10=0.041634, success_rate=1.0, forbidden scan pass,
and provider_calls=0.

This is smoke-only. It does NOT claim an external benchmark result,
does NOT claim a leaderboard entry, does NOT claim performance, does
NOT claim a promotion, does NOT claim a default change, does NOT claim
a runtime/retriever/pack/backend/EvidenceCore semantic change, and does
NOT claim downstream agent value. It does NOT emit `winner`,
`best_method`, `recommended_default`, or anything implying a policy/
default decision. The release asset, raw repo records, repo names/URLs,
commit SHAs, entrypoint paths, topics, content, dependency, needle
names/descriptions/paths/start/end lines, generated task/label/run
JSONL, evidence rows, cloned repos, and stdout/stderr stay under `/tmp`
or in-memory only and are NEVER committed or uploaded. The committed
artifact is aggregate-only. All no-claim / no-runtime-change flags
remain false (`external_benchmark_performance_claimed=false`,
`leaderboard_entry_claimed=false`,
`downstream_agent_value_proven=false`, `promotion_ready=false`,
`default_should_change=false`, `runtime_behavior_changed=false`,
`retriever_changed=false`, `pack_builder_changed=false`,
`backend_changed=false`, `default_policy_changed=false`,
`evidencecore_semantics_changed=false`, `provider_calls_made=false`,
`remote_provider_calls_made=false`). The safe true flags (true only if
actually true: `repoqa_retrieval_smoke_performed`,
`asset_downloaded_transiently`, `repoqa_needles_parsed_in_memory`,
`repositories_materialized_transiently`, `openlocus_retrieval_executed`,
`score_py_metrics_computed`, `aggregate_only_public_artifact`,
`diagnostic_only`) are the only additional true flags. If the network
smoke cannot complete (asset download failure, no Python needles, repo
clone failure, retrieval failure, score failure), the artifact records
truthful `unavailable_*` with a real `failure_reason_category` (no
stale/fake pass). No runtime/retriever/pack/model/backend/default-policy
files were modified. See
the [C5-D detailed report](c5d-repoqa-bm25-retrieval-smoke.md).


## Current status update — 2026-06-21 (C5-E RepoQA method-matrix retrieval smoke)

Following D5-A0, B16-A, C5-A, C5-B, C5-C, and C5-D, C5-E produces the
first RepoQA-shaped retrieval method-matrix smoke. C5-E
(`eval/c5e_repoqa_method_matrix_smoke.py` ->
`artifacts/c5e_repoqa_method_matrix_smoke/c5e_repoqa_method_matrix_smoke_report.json`,
schema `c5e_repoqa_method_matrix_smoke.v1`,
`claim_level=repoqa_retrieval_method_matrix_smoke_only`,
`status=repoqa_method_matrix_smoke_pass|partial|unavailable_with_reason|fail_forbidden_scan|fail_schema_contract`,
`mode=repoqa_bounded_method_matrix_smoke`, phase `C5-E`) extends C5-D
from single-method `bm25` to a bounded method matrix over
`bm25,regex,symbol`. It downloads the EvalPlus RepoQA release asset
`repoqa-2024-06-23.json.gz` to in-memory bytes (transient; NEVER written
to workspace), parses a bounded RepoQA Python needle subset (default 5
needles per method; hard cap 10; NO silent all-language fallback),
materializes the referenced repositories at their `commit_sha` under
transient `/tmp` directories (once per method+needle), runs OpenLocus
retrieval across the requested method matrix (default
`bm25,regex,symbol`; only `bm25,regex,symbol` allowed; `text` NOT
allowed; fixed `baseline_method=bm25`; no provider calls), scores each
method against `needle.path`/`start_line`/`end_line` via
`eval/score.py`, and commits only an aggregate public report with
per-method records (list, NOT dict keyed by method name), per-method
`aggregate_runtime_seconds`, and aggregate-only deltas vs the fixed
`bm25` baseline. 228/228 self-test checks pass; 5 needles seen, 3/3
methods successful, 0 methods failed.
Manual CI run `27907731742` passed with the same aggregate metrics; the
committed artifact now mirrors that sanitized CI report. CI runtimes were
bm25=9.416s, regex=6.969s, symbol=11.436s; provider_calls=0 and
forbidden_scan=pass.

This is smoke-only. It does NOT claim an external benchmark result,
does NOT claim a leaderboard entry, does NOT claim performance, does
NOT claim a promotion, does NOT claim a default change, does NOT claim
a runtime/retriever/pack/backend/EvidenceCore semantic change, and does
NOT claim downstream agent value. It does NOT emit `winner`,
`best_method`, `recommended_default`, or anything implying a policy/
default decision. The release asset, raw repo records, repo names/URLs,
commit SHAs, entrypoint paths, topics, content, dependency, needle
names/descriptions/paths/start/end lines, generated task/label/run
JSONL, evidence rows, cloned repos, and stdout/stderr stay under `/tmp`
or in-memory only and are NEVER committed or uploaded. The committed
artifact is aggregate-only. All no-claim / no-runtime-change flags
remain false. The safe true flags (true only if actually true:
`repoqa_method_matrix_smoke_performed`, `asset_downloaded_transiently`,
`repoqa_needles_parsed_in_memory`,
`repositories_materialized_transiently`, `openlocus_retrieval_executed`,
`score_py_metrics_computed`, `aggregate_only_public_artifact`,
`diagnostic_only`) are the only additional true flags. If the network
smoke cannot complete, the artifact records truthful
`unavailable_with_reason` with a real `failure_reason_category` (no
stale/fake pass). No runtime/retriever/pack/model/backend/default-policy
files were modified. See
the [C5-E detailed report](c5e-repoqa-method-matrix-smoke.md).

## Current status update — 2026-06-21 (C5-F RepoQA 10-needle method-matrix scale smoke)

C5-F scales C5-E from 5 RepoQA Python needles per method to 10 needles per method while keeping C5-E unchanged. C5-F (`eval/c5f_repoqa_method_matrix_scale_smoke.py` -> `artifacts/c5f_repoqa_method_matrix_scale/c5f_repoqa_method_matrix_scale_report.json`, schema `c5f_repoqa_method_matrix_scale_smoke.v1`, `claim_level=repoqa_retrieval_method_matrix_scale_smoke_only`, `status=repoqa_method_matrix_scale_smoke_pass|partial|unavailable_with_reason|fail_forbidden_scan|fail_schema_contract`, `mode=repoqa_bounded_10_needle_method_matrix_scale_smoke`, phase `C5-F`) runs the RepoQA method matrix over `bm25,regex,symbol`, default/hard-cap 10 Python needles per method, fixed `baseline_method=bm25`, no provider calls, aggregate-only records and deltas. 191/191 self-test checks pass; manual CI run `27909885489` saw 10 needles, 3/3 methods successful, forbidden scan pass, and provider_calls=0. Aggregate metrics: bm25 file_recall@10=0.5 / mrr=0.369216 / span_f0.5@10=0.020817 / success_rate=1.0; regex and symbol file_recall@10=0.0 / mrr=0.0 / span_f0.5@10=0.0 / success_rate=1.0.

This is smoke-only. It does NOT claim an external benchmark result, leaderboard entry, performance, promotion, default change, method winner, runtime/retriever/pack/backend/EvidenceCore semantic change, or downstream agent value. It emits no `winner`, `best_method`, `recommended_default`, or policy/default recommendation fields. Raw RepoQA row/repo/needle values and generated files remain transient. See the [C5-F detailed report](c5f-repoqa-method-matrix-scale-smoke.md).

## Current status update — 2026-06-21 (F1 counterfactual evidence utility smoke)

Following D5-A0, B16-A, and C5-A, F1 produces the first counterfactual
evidence utility smoke. F1
(`eval/f1_counterfactual_evidence_utility_smoke.py` ->
`artifacts/f1_counterfactual_evidence_utility/f1_counterfactual_evidence_utility_report.json`,
schema `f1_counterfactual_evidence_utility_smoke.v1`,
`claim_level=counterfactual_evidence_utility_smoke_only`,
`status=counterfactual_evidence_utility_smoke_pass`,
`mode=public_aggregate_synthetic_micro_tasks`, phase `F1`) generates
deterministic synthetic public micro bug tasks in code, creates a fresh
`/tmp` workspace per task+variant with real tiny Python modules + stdlib
tests, runs a **deterministic mock agent** (no live LLM, no provider
calls, no remote calls) that performs **real file edits** and runs
**real subprocess tests** under **six counterfactual context variants**
(`base_no_context`, `primary_only`, `support_only`,
`primary_plus_support`, `distractor_only`, `primary_plus_distractor`),
computes aggregate behavior metrics per variant, and computes
**five marginal utility deltas** from aggregate variant metrics
(`primary_context_vs_base`, `support_context_vs_base`,
`distractor_context_vs_base`, `support_added_to_primary`,
`distractor_added_to_primary`). The deltas are causal-shaped (variant
vs variant) and use utility-specific names that deliberately avoid
`E_primary` / `S_support` field-name shape. A `theory_mapping` block
records that `primary_context_vs_base` corresponds to an E-utility smoke
proxy and `support_added_to_primary` / `distractor_added_to_primary`
correspond to S-conditional utility smoke proxies, but F1 is explicitly
NOT true E/S calibration (`true_e_s_calibration_claimed=false`,
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
backend/default-policy files were modified. See
the [F1 detailed report](f1-counterfactual-evidence-utility.md).

## Current status update — 2026-06-20 (C4.1 external benchmark adapter / schema readiness)

C4.1 is a **bounded external benchmark adapter / schema readiness** phase,
NOT an external benchmark performance evaluation, NOT a benchmark result,
and NOT a promotion or default change. It adds one evaluator
(`eval/c4_external_benchmark_adapters.py`) and one canonical aggregate-only
public artifact
(`artifacts/c4_external_benchmark_adapters/c4_external_benchmark_adapter_report.json`,
schema `c4_external_benchmark_adapters.v1`,
`claim_level=adapter_schema_readiness_only`). The evaluator implements built-in
known source/schema metadata for ContextBench (`Contextbench/ContextBench`;
`default/train` 1136, `contextbench_verified/train` 500; license
`unknown_dataset_license`, row-level redistribution disabled) and SWE-Explore
(`SWE-Explore-Bench/SWE-Explore-Bench`; `default/train` 848; license
`cc-by-nc-nd-4.0`, row-level redistribution AND derived-label publication
disabled), synthetic in-memory row adapters separating `public_task` from
`private_label` (row-level payload never serialized), line range normalization
for synthetic self-test / private in-memory validation only, a strict
fail-closed forbidden-output scanner for all public JSON outputs, a bounded HF
datasets-server schema smoke via stdlib `urllib` only (no new dependencies), and
a deterministic `spec_hash`
(`9de6609359aa8de4cfe7ca50b1388ebc51d9ee2f016bb3bc6c34e253da5ef153`). Row-level
benchmark contents were NOT persisted in any public artifact or doc.

Validation: `python3 -m py_compile eval/c4_external_benchmark_adapters.py` PASS;
`python3 eval/c4_external_benchmark_adapters.py --self-test` PASS (9 groups);
default canonical artifact generation PASS (`forbidden_scan: pass`); real schema
smoke for ContextBench (`forbidden_scan: pass`, `new_network_calls: 4`) and
SWE-Explore (`forbidden_scan: pass`, `new_network_calls: 3`) PASS. The `/tmp`
smoke outputs follow the same aggregate-only boundary as the committed artifact.

All no-claim flags remain false: `promotion_ready=false`,
`default_should_change=false`, `evidencecore_semantics_changed=false`,
`runtime_clean_general_algorithm_claimed=false`,
`downstream_agent_value_proven=false`, `ood_temporal_supported=false`,
`quiver_systems_supported=false`. The schema smoke confirms only that public HF
datasets-server schema endpoints are reachable and parse; it does NOT confirm
benchmark quality, label correctness, or fitness for any downstream evaluation.
Synthetic self-test rows confer NO empirical support. See
[`docs/en/c4-external-benchmark-adapters.md`](c4-external-benchmark-adapters.md).
The prior 2026-06-16 status (Candidate-to-Evidence Conversion phase, P25
bucket_routed_v0 reference policy, B19 Model-Robust Selective Evidence
Conversion synthesis candidate) is preserved below unchanged.

## Current status update — 2026-06-16

OpenLocus is now in the **Candidate-to-Evidence Conversion** phase. The current
research question is no longer which retrieval channel is globally strongest;
it is how to convert high-reach, high-false-cost candidate pools into low
false-cost, citation-valid Evidence without weakening `EvidenceCore`.

The latest completed chain is:

```text
P46 reach/cost map
-> P47 request_more_context geometry diagnostic
-> P50 fixed-suite / anti-overfit gate
-> P48 request_more_context overlay simulator
-> P49 contrastive candidate pack scaffold
-> P52 metadata-only local verifier scaffold
-> P52A source materialization prerequisite
-> P52B source-backed local verifier feature matrix
-> P51 deterministic LLM span-narrow scaffold
-> P52C diagnostic local-verifier scoring simulator
-> P51-B LLM opt-in contract / dry-run payload validator
-> P57 generalization gate
-> P58 source-backed verifier calibration
-> P59 contrastive pack coverage & counterfactual study
-> P60 RMC policy v2 v0 comparison matrix
-> P61 pre-spend gate v0
-> P51-C0 live LLM micro-run planner / explicit opt-in gate
-> P62 generalization matrix aggregator v0
-> P63 cross-run slice collector / matrix runner v0
```

Key current conclusions:

```text
P25 bucket_routed_v0 remains the strongest reference policy.
symbol_regex_union remains the main candidate-reach lever, not a primary admission rule.
request_more_context is now a first-class diagnostic action, not Evidence.
P52A/P52B establish bounded local source materialization and source-shape diagnostics.
P52C adds fixed gold-free diagnostic score buckets, not verifier pass/fail.
P51/P51-B define future LLM span-narrow/filter entry points, but still no live LLM calls.
P57 adds a deterministic aggregate-only generalization-readiness gate after P51-B.
P58 adds aggregate source-backed verifier calibration as deterministic planning-hint buckets; it is not a verifier pass/fail, not admission, not Evidence, and not default/promotion/live readiness.
P59 adds a deterministic pre-spend diagnostic that rebuilds P49 packs and measures whether they contain the prerequisite contrastive information a later LLM role would need; it is not a quality evaluator, not admission, not Evidence, and not default/promotion/live readiness.
P60 adds a deterministic RMC policy comparison matrix that selects only the next diagnostic action; it reports aggregate routing counts and SCORE-phase gold-reach/false-cost diagnostics, but is not evidence, not admission, and does not select a winner or recommend a default.
P61 adds a deterministic aggregate-only pre-spend readiness gate that reports whether a future P51-C live LLM micro-run is worth considering; it is not authorization, not Evidence, and not default/promotion/live readiness.
P62 adds a deterministic aggregate-only generalization matrix aggregator that combines sanitized multi-slice aggregate report sets; it deduplicates identical signatures internally, publishes only counts, and is not quality evidence, not repo/dataset identity proof, and not default/promotion/live readiness.
P63 adds a deterministic offline aggregate-only cross-run slice collector and orchestrator that validates local artifact directories and runs P62 -> P57 -> P61; it does not fetch artifacts, call providers, or expose identities, and is not a fetcher, not quality evidence, not provider spend authorization, not repo/dataset diversity proof, and not default/promotion/live readiness.
P59B repairs the P59 hard-distractor/actionability precondition with a gold-free metadata_hard_distractor_proxy_v1; it does not relax P61 and does not use labels to construct packs.
P51-B now includes an explicit redaction-policy precondition, allowing P61 to distinguish "redaction is required and satisfied" from "redaction is missing" without constructing prompts or payloads.
promotion_ready=false and default_should_change=false.
EvidenceCore semantics are unchanged.
```

Recent validation completed after P52C/P51-B/P61:

```text
local deterministic regression: passed
p61 self_test: passed
p62 self_test: passed
p63 self_test: passed
p21_llm_rich self_test CI: 27601393249 green
p21_llm_rich ci_smoke CI: 27601488191 green
p21_llm_rich ci_smoke repo_id=js_express: 27601639934 green
```

Real cross-run P63 dry-run progression:

```text
initial manual P63 cross-run collection over four ci_smoke max_tasks=6 round_robin_public_buckets runs:
  py_flask      27637929480 green
  js_express    27637930877 green
  go_gin        27637932300 green
  rust_ripgrep  27637933749 green

P63 accepted sanitized slice dirs: 4/4
P62 distinct eligible slices: 4
P57 status: diagnostic_matrix_complete
P57 observed task aggregate: 24 tasks, positive=9, no_gold=15
P61 status: blocked_missing_actionability
P61 blocker: P59 actionability bucket = blocked_missing_hard_distractor

after P59B hard-distractor proxy repair and P51-B redaction-precondition repair,
manual P63 cross-run collection over four fresh ci_smoke max_tasks=6 round_robin_public_buckets runs:
  py_flask      27643271948 green
  js_express    27643273360 green
  go_gin        27643274763 green
  rust_ripgrep  27643276402 green

P63 accepted sanitized slice dirs: 4/4
P62 distinct eligible slices: 4
P57 status: diagnostic_matrix_complete
P61 status: micro_run_preconditions_met
P61 reason: all_required_preconditions_present
P51-B redaction policy status: required_defined_satisfied
```

Breakthrough Sprint B1 live LLM rich-candidate run:

```text
matrix:
  repos: py_flask, js_express, go_gin, rust_ripgrep
  tasks: 6 per repo, 24 total per output mode
  model: Kimi-K2.7-Code
  stage: p21_llm_rich

tool_call runs:
  py_flask      27674929320 green
  js_express    27674930653 green
  go_gin        27674932153 green
  rust_ripgrep  27674933629 green

json_schema_strict runs:
  py_flask      27675200878 green
  js_express    27675202356 green
  go_gin        27675203807 green
  rust_ripgrep  27675205460 green
```

The strongest B1 result is `llm_span_narrow` in tool-call mode: over 24 tasks it
increased added gold from 8 to 9, reduced added false spans from 43 to 5,
improved mean SpanF0.5 from 0.1099 to 0.2849, and reduced mean primary false
positive rate from 0.1250 to 0.0625. The same model under `json_schema_strict`
was schema-stable but slower and left more false spans (`8` vs `5` for
`llm_span_narrow`). This is the first post-gate live quality result showing that
rich candidate LLM span narrowing can convert high-noise candidate pools into
substantially lower-false-cost spans. It is not Evidence, not promotion, and not
a default change. See [`b1-live-llm-rich-candidate-run.md`](b1-live-llm-rich-candidate-run.md).

The first matrix proved that P62 -> P57 -> P61 could move beyond the single-slice
`insufficient_matrix` condition and exposed a concrete P59 hard-distractor
blocker. P59B repaired that blocker with a gold-free metadata hard-distractor
proxy, and the subsequent matrix reached `micro_run_preconditions_met`. This
still **does not** authorize live LLM spend: it is only a precondition signal.
Opening P51-C remains a separate explicit workflow/human decision with its own
provider-spend controls, prompt/payload privacy gates, and small micro-run plan.

The validation covered the deterministic P52C/P51-B/P61/P62 self-tests, docs i18n mirror,
workflow Python heredoc compilation, diff checks, artifact privacy gates,
self-test no-source-root behavior, default `ci_smoke` source-backed behavior, and
a small `js_express` cross-repo slice. It did **not** run the full nightly/weekly
matrix, full repo-language generalization, or a live P51-C LLM opt-in call.

Current detailed reports added in this phase:

- [`p61-pre-spend-gate.md`](p61-pre-spend-gate.md)
- [`p62-generalization-matrix-aggregator.md`](p62-generalization-matrix-aggregator.md)
- [`p63-cross-run-slice-collector.md`](p63-cross-run-slice-collector.md)
- [`p60-rmc-policy-v2.md`](p60-rmc-policy-v2.md)
- [`p59-contrastive-pack-coverage-counterfactual.md`](p59-contrastive-pack-coverage-counterfactual.md)
- [`p58-source-backed-verifier-calibration.md`](p58-source-backed-verifier-calibration.md)
- [`p59-contrastive-pack-coverage-counterfactual.md`](p59-contrastive-pack-coverage-counterfactual.md)

Recommended next step: proceed to B2/B3, not more precondition scaffolding. B2
should compare contrastive pack variants with real LLM quality metrics, and B3
should test request_more_context as a quality-improving strategy using the B1
span-narrow/filter signal. B1 is positive but small; it justifies targeted
expansion, not promotion/default changes.

Breakthrough Sprint B2 contrastive-pack quality experiment:

```text
layouts:
  topk_plain_v0
  topk_scores_provenance_v0
  contrastive_competitor_v0
  hard_distractor_contrast_v0

matrix:
  4 repos x 6 tasks x 4 layouts = 96 live tasks
  model: Kimi-K2.7-Code
  output: tool_call
```

B2 showed that contrastive structure is not automatically better. For
`llm_span_narrow`, `topk_plain_v0` kept the best PFP (`0.0625`) and full gold
retention (`9` added gold, `6` added false). `hard_distractor_contrast_v0`
reduced false spans from `6` to `5`, but killed two gold spans and doubled mean
PFP to `0.1250`. `topk_scores_provenance_v0` had the highest mean SpanF0.5
(`0.2829`) but increased false spans and latency. The immediate conclusion is to
route contrastive/hard-distractor packs selectively to filter/no-gold/hard-
distractor buckets, not to use them as a universal span-narrow pack. See
[`b2-contrastive-pack-quality-experiment.md`](b2-contrastive-pack-quality-experiment.md).

Breakthrough Sprint B1C cross-model rerun:

```text
matrix:
  4 repos x 6 tasks x topk_plain_v0
  Kimi-K2.7-Code tool_call
  Qwen3.6-27B tool_call + json_schema_strict
  GLM-5.2 tool_call + json_schema_strict
```

Kimi tool_call remains the primary reference: 24/24 schema-valid calls, zero
fallbacks, 9 added gold, 5 added false, mean SpanF0.5 0.2825, mean PFP 0.0625.
GLM-5.2 is viable under `json_schema_strict` (23/24 schema-valid, 7 added gold,
7 added false, mean SpanF0.5 0.2192) but tool_call remains noisy. Qwen3.6-27B
adds 27B dense model coverage, but both output modes hit rate-limit/fallback
noise, so this run is plumbing/rate-limit evidence rather than quality evidence.
See [`b1c-cross-model-rich-candidate-rerun.md`](b1c-cross-model-rich-candidate-rerun.md).

Breakthrough Sprint B3 request-more-context quality experiment:

```text
matrix:
  4 repos x 6 tasks
  model: Kimi-K2.7-Code
  output: tool_call
  treatments: P25, RMC-local, RMC-LLM, RMC-hybrid
```

B3 was a high-value negative result. Fixed RMC routing did not beat P25. P25
over the plain pack reached 8 added gold / 7 added false, mean SpanF0.5 0.0890,
and mean PFP 0.0417. Both `rmc_llm_pack_routed_v0` and `rmc_hybrid_v0` reached 7
added gold / 8 added false, mean SpanF0.5 0.0820, and mean PFP 0.0833.
`rmc_local_conservative_v0` avoided PFP but collapsed recall (4 gold / 18 false,
mean SpanF0.5 0.0226). The algorithmic conclusion is that RMC needs searched or
bucket-specific routing; fixed rules are too crude. See
[`b3-rmc-quality-experiment.md`](b3-rmc-quality-experiment.md).

Breakthrough Sprint B6-lite interpretable policy search:

```text
matrix:
  4 repos x 6 tasks
  model: Kimi-K2.7-Code
  stage: b6_lite_policy_search
```

B6-lite searched a small rule grammar over paired plain/hard-distractor P21
records. It found lower-false-cost hypotheses, but not robust policies. The best
aggregate searched candidate with P25-like gold was
`ambiguous_query_weak_only_default_use_p25_action` (8 gold / 6 false / PFP 0.0),
but it appeared on the frontier in only one repo and still used 12 LLM actions.
The conservative
`negative_weak_only_ambiguous_query_use_p25_action_default_use_p25_action`
achieved 5 gold / 2 false and positive net span value, but lower SpanF0.5. B6
therefore supports a B6B combined-matrix search with proper leave-one-repo-out;
it does not justify a default change. See
[`b6-lite-interpretable-policy-search.md`](b6-lite-interpretable-policy-search.md).

B6B combined-matrix policy search:

```text
run: 27689938744 green
matrix: 4 public repo slices x 6 tasks
claim: leave_one_repo_diagnostic_only
```

B6B trained the same small interpretable grammar on three repo slices and scored
the frozen policies on the held-out slice, then aggregated only public counts.
It found two lower-false-cost families worth follow-up. The strongest P25-like
candidate, `ambiguous_query_weak_only_default_use_p25_action`, preserved P25's
held-out added gold/SpanF0.5 in aggregate while reducing false spans (7 gold / 5
false vs P25's 7 / 8) and PFP (0.0 vs 0.0833). The conservative
`negative_weak_only_ambiguous_query_use_p25_action_default_use_p25_action`
reduced false further (4 gold / 1 false) but lost too much gold for deep-quality
use. Neither is a default; both require a fresh validation run on more repos and
model-robust checks. See
[`b6b-combined-policy-search.md`](b6b-combined-policy-search.md).

B6C frozen-policy fresh validation:

```text
run: 27706742419 green
matrix: 4 public repo slices x 6 tasks
model: Kimi-K2.7-Code tool_call
claim: frozen_policy_fresh_validation
search_performed: false
```

B6C froze the two B6B candidate policies before evaluation and validated them on
fresh paired records. The main policy candidate,
`ambiguous_query_weak_only_default_use_p25_action`, preserved P25's added gold
and mean SpanF0.5 while reducing false spans (8 gold / 5 false vs P25's 8 / 6),
removing observed PFP, and halving effective LLM actions (12 vs 24). The
conservative candidate reached 5 gold / 1 false with positive net span value but
lost too much gold for the deep-quality path. B6C supports a balanced-policy
hypothesis, not a default change. See
[`b6c-frozen-policy-validation.md`](b6c-frozen-policy-validation.md).

B6E expanded frozen-policy validation reused the same evaluator and frozen policy
spec on a larger fresh task matrix:

```text
run: 27717886432 green
matrix: 4 public repo slices x 12 tasks = 48 comparable tasks
model: Kimi-K2.7-Code tool_call
claim: frozen_policy_fresh_validation
search_performed: false
```

The main balanced-policy candidate again preserved P25's added gold and mean
SpanF0.5 while reducing false spans (13 gold / 14 false vs P25's 13 / 17),
removing observed PFP, and reducing estimated LLM actions (31 vs 47). This
strengthens the B6C balanced-policy hypothesis within the same four-repo public
universe. It is not repo-generalization, not cross-model validation, and not a
default change.

B6F repo-generalization smoke reused the same frozen policy spec on a different
set of four public repo slices:

```text
run: 27735809672 green
matrix: 4 new public repo slices x 12 tasks = 48 comparable tasks
model: Kimi-K2.7-Code tool_call
claim: frozen_policy_fresh_validation
search_performed: false
```

The main balanced-policy candidate again preserved P25's added gold and mean
SpanF0.5 while reducing false spans (8 gold / 20 false vs P25's 8 / 24),
removing observed PFP, and reducing estimated LLM actions (31 vs 47). This is the
first repo-generalization smoke supporting the balanced-policy hypothesis. It is
still single-model and low-n.

B8-lite medium-matrix aggregate rollup:

```text
sources: B6E 27717886432 + B6F 27735809672
scope: 8 public repo slices, 96 comparable tasks
new provider calls: 0
policy search performed: false
```

The derived rollup keeps the frozen-policy trend intact: the main balanced
candidate matches P25's added gold and weighted mean SpanF0.5 while reducing
false spans from 41 to 34, eliminating observed PFP, and reducing estimated LLM
actions from 94 to 62. This strengthens the balanced-policy candidate, but it is
a derived single-model aggregate, not a new live validation run or default
change. See [`b8-lite-medium-matrix-combiner.md`](b8-lite-medium-matrix-combiner.md).

B6D cross-adapter frozen-policy validation:

```text
run: 27716082836 green
adapter: GLM-5.2 json_schema_strict
status: not_quality_interpretable
schema_valid_rate: 0.75
infra_failure_rate: 0.25
direction_consistency: not_determinable
```

B6D completed successfully as a workflow and aggregate-report path, but it did
not produce quality-interpretable cross-adapter evidence. The GLM adapter health
was below threshold, so policy-family quality metrics remain null and no claim is
made about whether the B6C frozen policy transfers to GLM. Output mode is treated
as an adapter/profile configuration, not as a universal algorithm variable. See
[`b6d-cross-adapter-frozen-validation.md`](b6d-cross-adapter-frozen-validation.md).

B9A adapter-health screen:

```text
matrix:
  GLM-5.2 and Qwen3.6-27B
  tool_call and json_schema_strict adapter profiles
  2 public repo slices per adapter profile
  max_tasks=6, sequentially triggered jobs
```

B9A is not a quality leaderboard. It treats output mode as a model-adapter
configuration parameter and reports only adapter health. Qwen3.6-27B
`json_schema_strict` passed the small health screen (`schema_valid_rate=1.0`,
`infra_failure_rate=0.0`) and is a candidate for cautious low-volume follow-up.
GLM-5.2 `json_schema_strict` improved over tool-call behavior but remained below
quality-interpretable thresholds (`schema_valid_rate=0.833`,
`infra_failure_rate=0.333`). GLM tool-call and Qwen tool-call remain too noisy
for critical-path validation. See [`b9a-adapter-health-report.md`](b9a-adapter-health-report.md).

B9B Qwen low-volume quality follow-up:

```text
model: Qwen3.6-27B
adapter: json_schema_strict
matrix: 4 public repo slices x 6 tasks
execution: sequential jobs
schema_valid_rate: 1.0
infra_failure_rate: 0.0
```

Qwen json_schema_strict produced quality-interpretable live rich-candidate
results under the low-volume sequential discipline. `llm_span_narrow` reached 7
added gold / 4 added false, false_per_gold 0.571, mean SpanF0.5 0.2831, and mean
PFP 0.0625. This promotes Qwen from plumbing-only to a secondary
quality-interpretable adapter candidate for cautious low-volume follow-up, but it
is not a default model or output-mode leaderboard result. See
[`b9b-qwen-low-volume-quality-follow-up.md`](b9b-qwen-low-volume-quality-follow-up.md).

B9C Qwen frozen-policy validation:

```text
run: 27744695226 green
adapter: Qwen3.6-27B json_schema_strict
status: ok
quality_interpretable: true
direction_consistency: consistent_with_kimi
```

B9C reused the B6C frozen balanced policy under the health-stable Qwen adapter.
The balanced policy preserved P25's added gold and mean SpanF0.5 while reducing
false spans from 5 to 4, removing observed PFP, and cutting estimated LLM actions
from 24 to 12. This is a low-n smoke, but it is the first secondary-adapter
support for the balanced-policy direction. See
[`b9c-qwen-frozen-policy-validation.md`](b9c-qwen-frozen-policy-validation.md).

B9D DeepSeek/GLM participation screen:

```text
DeepSeek-V4-Flash tool_call/json_schema_strict:
  schema_valid_rate=1.0, infra_failure_rate=0.0
  span_narrow: 4 gold / 3 false on 12 tasks

DeepSeek-V4-Pro tool_call/json_schema_strict:
  schema_valid_rate=1.0, infra_failure_rate=0.0
  span_narrow: 2 gold / 1 false on 12 tasks

GLM-5.2:
  still noisy from B9A/B6D; keep opt-in exploratory only
```

B9D is not a model leaderboard. It gives participation recommendations:
DeepSeek Flash/Pro are healthy enough for future exploratory involvement, GLM
remains supported but not critical-path, Qwen json_schema_strict remains the best
current secondary validation adapter, and Kimi tool_call remains the primary
reference. See [`b9d-deepseek-glm-participation-screen.md`](b9d-deepseek-glm-participation-screen.md).

B4/B9 model-robust evidence conversion digest:

```text
inputs:
  B1, B1C, B2, B3 live aggregate quality cells
outputs:
  algorithm_spec vs model_adapter separation
  matched-baseline treatment deltas where available
  low-n claim levels, not universal algorithm claims
```

B4/B9 deliberately prevents the Kimi result from becoming the OpenLocus
algorithm. `span_narrow_topk_plain_v0` is only a `low_n_directional_signal` on
the two matched Kimi adapter deltas; GLM-5.2 json_schema_strict is secondary
observed cross-family validation because no matched baseline delta is available.
B9B/B9C later upgrade Qwen json_schema_strict to secondary low-volume support,
but the original B4/B9 aggregate remains unchanged. Fixed RMC variants remain
`not_supported`. See
[`b4-b9-model-robust-evidence-conversion.md`](b4-b9-model-robust-evidence-conversion.md).

B10 runtime feature audit + balanced policy v1 freeze:

```text
algorithm_spec_id: balanced_policy_v1_benchmark_routed
claim_level: benchmark_routed_algorithm_spec_only
source frozen candidate: ambiguous_query_weak_only_default_use_p25_action
frozen spec hash matched: true
runtime_clean: false
runtime_feature_only_mode_supported: false
promotion_ready: false
default_should_change: false
evidencecore_semantics_changed: false
model_adapter / output_mode / provider credentials: excluded adapter layer
```

B10 freezes the B6C main balanced candidate as the algorithm spec
`balanced_policy_v1_benchmark_routed` and audits the provenance of every routing
feature the spec reads. `ambiguous_or_query_noise` is `_ambiguous_like or
_query_noise`: `_ambiguous_like` reads benchmark public labels
`task_bucket`/`task_risk_tags`, `_query_noise` reads the deterministic runtime
feature `route_features.query_noise`. The default `use_p25_action` delegates to
`p25.route_bucket_routed_v0` and inherits P25 route_features
(`candidate_count`, `candidate_support_exists`). P25 exact/unique short-circuiting
is currently driven by bucket labels rather than a runtime `unique_symbol_anchor`
route-feature read.
`runtime_clean=false` because the `_ambiguous_like` branch needs
`task_bucket`/`task_risk_tags`, so a runtime-feature-only mode would never fire
the `ambiguous_query_weak_only` rule. Routing uses no score-private fields
(`score_private_dependencies_for_routing=[]`); `has_gold`/`score_group`/
`outcome_metrics` are aggregate-scoring only. This is a benchmark-routed
research algorithm spec only — not a runtime-feature-only policy, not a default
change, not a promotion. The next step is `balanced_policy_v1_runtime_shadow`:
replace the ambiguous bucket/tag branch with pure runtime features
(`query_noise`, `candidate_support_exists`, anchor disagreement) and run an
action-agreement replay against this spec. See
[`b10-runtime-feature-audit.md`](b10-runtime-feature-audit.md).

B10B runtime-shadow replay (ambiguous branch only):

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
replay_source: synthetic_fixture
runtime_shadow_ambiguous_supported: false
support_claim: mechanics_only_synthetic_fixture
support_claim_reason: synthetic_fixture_only
```

B10B is the next step after the B10 freeze. It does not run any model, does not
search, does not tune policy quality, and does not defaultize. It only tests
whether a fixed predeclared runtime-feature-only shadow predicate can
reproduce the **ambiguous branch** of the frozen
`balanced_policy_v1_benchmark_routed` action on the same records. The shadow
predicate reads only runtime `route_features` (`query_noise`,
`candidate_support_exists`, `local_anchor`, `rrf_backed_by_anchor`) and never
reads `task_bucket`/`task_risk_tags`/`has_gold`/`score_group`/outcome metrics;
`runtime_shadow_ambiguous = query_noise OR (candidate_support_exists AND
anchor_disagreement_proxy)` where `anchor_disagreement_proxy = local_anchor
AND NOT rrf_backed_by_anchor`. If any required runtime feature is missing, the
record is marked missing and the shadow action is NOT silently defaulted to
false; if all records are missing features, the status is
`insufficient_runtime_features`. The strengthened evaluator also carries: 10
predeclared acceptance gates (including
`label_driven_ambiguous_min_denominator: 10` as a HARD gate, not an escape
clause), stratified agreement metrics (`target_weak_only_recall`,
`target_use_p25_specificity`, `shadow_weak_only_precision`,
`label_driven_ambiguous_recall_qn0`, `query_noise_only_recall_qn1`),
silent-failure checks (`all_shadow_ambiguous`, `all_shadow_non_ambiguous`,
`base_rate_only_suspected`, `no_silent_failure`), a direct Cohen's kappa
implementation (no numpy/sklearn), a 4-partition outcome-equivalence audit on
the disagreement subset (`outcome_audit`, audit-only — outcomes never feed
back into routing), a verdict framework
(`runtime_shadow_ambiguous_supported` + `support_claim` +
`support_claim_reason`), a `replay_source` parameter
(`synthetic_fixture` vs `ci_ephemeral_records`), and a CLI `--records <path>`
mode for CI integration. The leakage guard now mutates `outcome_metrics` in
addition to `task_bucket`/`task_risk_tags`/`has_gold`/`score_group`. The
public report is aggregate-only and emits no forbidden public keys or raw
path/digest/provider strings. **B10B does NOT prove a runtime-clean balanced
policy** and the current verdict on the synthetic fixture is
`runtime_shadow_ambiguous_supported=false`,
`support_claim="mechanics_only_synthetic_fixture"`,
`replay_source="synthetic_fixture"` — i.e. a **mechanics-validated scaffold
with empirical validation pending**, not an empirical-support claim. The
default `use_p25_action` still delegates to P25 benchmark-routed behavior, so
this is ambiguous-branch runtime-shadow only. B11 should be framed as
**exploratory prospective stress test**, not "supported validation", until
B10B runs on real CI ephemeral records and passes every predeclared gate. See
[`b10b-runtime-shadow-replay.md`](b10b-runtime-shadow-replay.md).

B11 prospective blind validation:

```text
algorithm_spec_id: balanced_policy_v1_benchmark_routed (frozen, B10)
claim_level: prospective_validation_preregistration
new_repos_new_tasks_after_freeze: true
retuning_after_live_runs: false (forbidden by preregistration)
promotion_ready: false
default_should_change: false
evidencecore_semantics_changed: false
policy_search_performed: false
quality_strategy_tuned: false
live_llm_runs_require_workflow_dispatch: true
```

B11 is the first true **prospective** validation of the frozen balanced policy
`balanced_policy_v1_benchmark_routed`. Prior validation (B6C/B6E/B6F/B8-lite/B9C)
shared the same task generation and research universe; B11 uses new repos and
tasks generated after the 2026-06-18 policy freeze, with no retuning of policies,
thresholds, or success criteria. The preregistration freezes artifacts (the B10
spec, the B10B shadow predicate, `rmc_local_conservative_v0`,
`p25.route_bucket_routed_v0`, the B10B 10 gates and verdict framework) and all
success/failure/partial criteria **before** any live runs; any post-hoc analysis
must be labeled exploratory.

Scope is split into a minimum viable first round (8 repos, 5 languages, ~120
tasks, 4 models, 4-6 hours CI per model family) and a full round if promising
(12-16 repos, 300-500 tasks). The minimum viable 8 repos are `py_fastapi`,
`py_pytest`, `ts_vite`, `ts_hono`, `go_chi`, `go_prometheus`, `rust_deno`,
`java_spring_petclinic` — all new, none used in B6B/B6C/B6E/B6F/B8-lite.

B11 covers 4 model families: Kimi (`Kimi-K2.7-Code`, `tool_call`, reference),
Qwen (`Qwen3.6-27B`, `json_schema_strict`, secondary), DeepSeek Flash
(`DeepSeek-V4-Flash`, `json_schema_strict`, recall), and DeepSeek Pro
(`DeepSeek-V4-Pro`, `json_schema_strict`, conservative). GLM-5.2 is excluded
as noisy per B9A/B6D. Output mode is a model-adapter configuration parameter,
not an OpenLocus algorithm variable. 4 policies are compared: Local baseline
(no LLM), P25 `p25.route_bucket_routed_v0`, Balanced v1
`balanced_policy_v1_benchmark_routed`, and Conservative
`rmc_local_conservative_v0`.

Predeclared success/failure/partial criteria use explicit overall and worst-group
thresholds on `Δgold_span`, `ΔSpanF0.5`, `ΔPFP`, `Δfalse_spans`, and `ΔLLM_calls`
(Balanced v1 vs P25), plus a `RobustUtility` =
`min_group(SpanF0.5 - λ*PFP - μ*normalized_cost - ν*normalized_latency)` aggregate
with `λ=1.0`, `μ=0.1`, `ν=0.1`. B10B integration: B10B `--records` runs in CI
after each B11 run (already wired in commit `2cbdd0c`), giving B10B its first
empirical validation (`replay_source="ci_ephemeral_records"`). B11 is a
prospective stress test, not a promotion step: even on success,
`promotion_ready=false`. The plan, CI workflow definition, and report-aggregator
skeleton are autonomous; actual live LLM runs require a user
`workflow_dispatch` trigger with `enable_remote_models=true`. See
[`b11-prospective-blind-validation.md`](b11-prospective-blind-validation.md).

B11 official integrated matrix result (2026-06-18):

```text
algorithm_spec_id: balanced_policy_v1_benchmark_routed (frozen, B10)
claim_level: derived_aggregate_of_b11_prospective_validation_reports
matrix_status: 32/32 runs complete (two transient provider_status retried)
record_count_total: 384
verdict_counts: {success: 8, partial: 23, failure: 1}
aggregate_verdict: partial_with_failure
promotion_ready: false
default_should_change: false
evidencecore_semantics_changed: false
policy_search_performed: false
quality_strategy_tuned: false
new_provider_calls_by_combiner: 0
aggregate_only_public_artifact: true
```

The B11 official integrated matrix completed 32/32 runs across the 8 public
repo slices (`py_fastapi`, `py_pytest`, `ts_vite`, `ts_hono`, `go_chi`,
`go_prometheus`, `rust_deno`, `java_spring_petclinic`) and 4 model families
(`kimi`, `qwen`, `deepseek_flash`, `deepseek_pro`). Two transient
`provider_status` failures were retried; the aggregate rolls up only the
already-downloaded aggregate-only public B11/B10B artifacts (no raw records,
paths, prompts, responses, snippets, or private labels read).

Overall weighted means across 384 records
(`local_baseline` / `p25` / `balanced_v1` / `conservative`):

```text
gold_span   : 0.377604 / 0.247396 / 0.244792 / 0.125000
false_span  : 1.203125 / 0.236979 / 0.182292 / 0.236979
span_f0_5   : 0.062197 / 0.064538 / 0.062639 / 0.023611
PFP         : 0.083333 / 0.020833 / 0.000000 / 0.000000
model_calls : 0.0      / 0.958333 / 0.604167 / 0.000000
```

Balanced v1 vs P25 deltas (overall): `Δgold_span -0.002604`,
`Δfalse_span -0.054688`, `ΔSpanF0.5 -0.001899`, `ΔPFP -0.020833`,
`Δmodel_calls -0.354167`. I.e. balanced_v1 preserved near-parity
`SpanF0.5`/`gold_span` vs P25 while reducing false spans, PFP, and model
calls. Per model family (balanced_v1 vs P25, record-weighted over 96 records
each): `deepseek_flash` partial 6 / success 2 (`Δfalse_span -0.052083`,
`ΔPFP -0.010417`), `deepseek_pro` partial 5 / success 3 (`Δfalse_span
-0.083333`, `ΔPFP -0.031250`), `kimi` partial 5 / success 2 / failure 1
(`Δgold_span -0.010417`, `ΔSpanF0.5 -0.007595`, `Δfalse_span -0.072917`,
`ΔPFP -0.031250`), `qwen` partial 7 / success 1 (`Δfalse_span -0.010417`,
`ΔPFP -0.010417`). The single failure was a Kimi `py_fastapi` slice whose
`failure_spanf05_delta` threshold was exceeded. B10B runtime-shadow replay
ran after every B11 run (32/32 reports); `runtime_shadow_ambiguous_supported`
was `false` on all runs with
`support_claim="empirical_replay_support_pending"` and reason
`insufficient_label_driven_denominator` (max observed
`label_driven_ambiguous_denominator_qn0=3` vs the 10-record hard gate), so
the B10B predicate remains empirical-pending and is NOT a runtime-clean
general algorithm claim.

Framing: B11 is **mixed/partial**. The result strengthens the
algorithm-candidate signal (balanced_v1 preserves near-parity SpanF0.5/gold
while reducing false spans, PFP, and model calls on average) but does NOT
prove a runtime-clean general algorithm. No promotion, no default change, no
EvidenceCore semantics change. Recommended next step: B12 mechanism
decomposition to identify which conditions drive the Kimi failure and the
mixed partials. Aggregate artifact:
`artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json`
(generated by `eval/b11_matrix_combiner.py`). See
[`b11-prospective-blind-validation.md`](b11-prospective-blind-validation.md).

B12 mechanism decomposition:

```text
algorithm_spec_id: b12_mechanism_decomposition_v0
claim_level: mechanism_decomposition_v0
replay_only: true (no live LLM calls inside evaluator)
promotion_ready: false
default_should_change: false
evidencecore_semantics_changed: false
policy_search_performed: false
quality_strategy_tuned: false
```

B12 is the **mechanism decomposition** phase that follows B11. The goal is to
understand **WHY** the frozen balanced policy
`balanced_policy_v1_benchmark_routed` (B10) works (if B11 confirms it
generalizes), via 5 ablation variants and 4 predeclared hypotheses. The 5
ablation variants are: **A** (full balanced; `ambiguous→weak_only, else P25`),
**B** (deterministic LLM reduction; P25 for all but skip LLM for ambiguous
tasks), **C** (ambiguous weak_only only; ≡A by construction since the balanced
policy has only one routing rule), **D** (P25 default only; baseline), and
**E** (random LLM reduction; P25 for all but randomly skip the same number of
LLM calls as A). The 4 hypotheses are: **H1** (ambiguous routing — gains come
from the `ambiguous→weak_only` rule), **H2** (LLM call reduction — gains come
from any LLM-call reduction), **H3** (P25 fallback sufficiency — the routing
rule doesn't help), **H4** (model-specific — effect sizes vary across model
families). The A≡C equivalence is declared explicitly up-front (not a post-hoc
discovery): the balanced policy has only one routing rule, so A and C produce
identical per-record outcomes, and Variant C is collapsed into A in every
hypothesis test.

B12 is replay-only: each P21 record contains per-strategy outcomes, so each
ablation variant is computed by selecting the appropriate per-strategy outcome
from existing records. No live LLM calls are made by the B12 evaluator. If P21
records are not available, B12 needs new live ablation runs
(`workflow_dispatch` + `enable_remote_models=true`). Predeclared
support/refute criteria use explicit thresholds on `gold_span` and
`span_f0_5` deltas: "≈" means within ±0.02, ">" means strictly greater than
0.02; H4 uses a worst-case model-family spread threshold of 0.05 on the
`A - D` `gold_span` delta. The B12 verdict framework emits one of
`supported`/`refuted`/`partial`/`insufficient_data`/`not_implemented`. After the
C1 private-record adapter landed, the B12 evaluator's `--input` path is real:
it consumes CI-private P21 payloads through `eval/c1_private_records.py`,
normalizes runtime features / benchmark route labels / SCORE-phase outcome
fields, and emits an aggregate-only public report. It still makes no live LLM
calls and does not expose task IDs, raw repo IDs, paths, spans, content hashes,
prompts, responses, snippets, provider URLs, or provider keys. B12 is mechanism
decomposition, **not** a promotion step: `promotion_ready=false`,
`default_should_change=false`, `evidencecore_semantics_changed=false`. See
[`b12-mechanism-decomposition.md`](b12-mechanism-decomposition.md).

C2 B12 CI canary (2026-06-19): after the C1 shared private-record adapter
landed, a real CI canary (`py_fastapi × Kimi × round_robin_public_buckets × 12
tasks`, run `27816890557`) verified that B12 consumes private P21 per-record
records and emits only an aggregate public report. The B12 report used
`replay_source="ci_ephemeral_records"` with `12/12` complete records,
`balanced_branch_count=4`, `p25_llm_eligible_count=10`,
`actual_call_avoided_count=4`, and `random_selected_count=4`. Canary verdict:
`partial` (H1 `refuted`, H2 `refuted`, H3 `supported`, H4 `insufficient_data`
because this is a single-model-family slice). This is canary-level evidence
only; the full B12 matrix over B11 repo/model cells remains the next step.

C2/B12 official matrix aggregate (2026-06-19):

```text
schema_version: b12-mechanism-matrix-aggregate-report-v0
claim_level: derived_aggregate_of_b12_mechanism_decomposition_reports
aggregate_only_public_artifact: true
promotion_ready: false
default_should_change: false
evidencecore_semantics_changed: false
policy_search_performed: false
runtime_clean_policy_supported: false
new_provider_calls: 0
candidate_not_fact: true
cell_count_target: 32
analyzable_cell_count: 28
excluded_cell_count: 4
aggregate_verdict: partial_with_coverage_exclusions
```

The **C2/B12 official matrix aggregate** combines the 28 analyzable per-run
`b12-mechanism-decomposition-report-v0` public aggregate reports (one per
included repo×model cell) into a single derived aggregate
(`eval/b12_matrix_combiner.py` →
`artifacts/b12_mechanism_decomposition/b12_matrix_aggregate_report.json`). It
is bounded: it reads only already-downloaded aggregate-only public B12
reports, performs no provider calls, no policy search, and no threshold
tuning. Coverage: `28/32` cells analyzable, `4` `ts_vite` cells excluded as
`coverage_insufficient_no_remote_llm_snippet` (they did not exercise remote
LLM snippets even at `max_tasks=24`; these are coverage gaps, NOT B12
mechanism failures). Records: `336` total (`12` per cell). Verdict counts:
`partial: 28`. Hypothesis status counts: H1 `supported: 3 / refuted: 25`, H2
`supported: 8 / refuted: 20`, H3 `supported: 28`, H4 `insufficient_data: 28`
(every cell is a single-model-family slice, so H4 needs multi-model
aggregation across cells; H4 insufficient_data does NOT block the H1-H3
verdict). Record-weighted A (full balanced) deltas vs D (P25 default):
`Δgold_span 0.0`, `ΔSpanF0.5 0.0`, `Δfalse_span -0.029762`,
`ΔPFP -0.014881`, `Δmodel_calls -0.333333`; vs E (random call reduction):
`Δgold_span -0.044643`, `ΔSpanF0.5 0.001569`, `Δfalse_span -0.592262`,
`ΔPFP -0.026786`, `Δmodel_calls 0.0`; vs B (deterministic call reduction):
`Δgold_span 0.0`, `ΔSpanF0.5 0.0`, `Δfalse_span -0.130952`,
`ΔPFP -0.035714`, `Δmodel_calls 0.0`. Weighted mean robust utility (A):
`0.054155`. Replay count totals: `balanced_branch_count=112`,
`p25_llm_eligible_count=324`, `actual_call_avoided_count=112`,
`random_selected_count=112`. Overall verdict:
`partial_with_coverage_exclusions` — NOT a global `supported` verdict, NOT a
promotion, NOT a default change, NOT a runtime-clean general algorithm claim.
See [`b12-mechanism-decomposition.md`](b12-mechanism-decomposition.md).

B12 public aggregate mechanism screen (2026-06-18):

```text
schema_version: b12-public-aggregate-mechanism-screen-v0
claim_level: bounded_public_aggregate_mechanism_screen_of_b11_aggregate
is_full_b12_mechanism_decomposition: false
full_b12_possible_from_public_artifact: false
per_hypothesis_status_only_no_global_supported_verdict: true
aggregate_only_public_artifact: true
promotion_ready: false
default_should_change: false
evidencecore_semantics_changed: false
policy_search_performed: false
quality_strategy_tuned: false
new_provider_calls: 0
```

A bounded **public-aggregate mechanism screen** was added
(`eval/b12_public_aggregate_screen.py` →
`artifacts/b12_mechanism_decomposition/b12_public_aggregate_screen_report.json`).
This is **NOT** a full B12 per-record replay. The explorer/oracle finding is
that full B12 replay is impossible from the current public B11 aggregate:
it lacks per-record route decisions, ambiguous-subset membership,
deterministic call-reduction variant B, random call-reduction variant E, and
`weak_candidate_only` per-strategy outcomes. The screen therefore emits
**per-hypothesis screen statuses**, never a single global `supported` verdict,
and applies the SAME frozen numeric gates (±0.02 approx-equality, 0.05 H4
family-spread) to the B11 aggregate deltas only. It reads only the already-
published B11 aggregate report; no raw records, paths, prompts, responses,
snippets, or private labels are read or emitted.

Per-hypothesis screen results from the B11 official matrix aggregate (32 runs
/ 384 records): **H1** `inconclusive_unavailable_ablation_controls` (no
per-record route decisions, no ambiguous subset, no variants B/E; does NOT
claim H1 support). **H2** `reduced_calls_observed_causal_mechanism_inconclusive`
(`Δmodel_calls -0.354167` so reduced calls are observed descriptively, but
without variant E the causal mechanism cannot be attributed; does NOT claim
H2 causal support). **H3** `aggregate_primary_parity_supported_consistent_with_h3`
(`Δgold_span -0.002604` and `ΔSpanF0.5 -0.001899` both within ±0.02; consistent
with H3 at the aggregate level but NOT a full H3 supported verdict — per-record
fallback sufficiency cannot be concluded from aggregate deltas alone). **H4**
`family_gold_spread_not_supported_model_repo_interaction_inconclusive`
(per-family gold_span delta spread `0.010417` — deepseek_flash 0.0,
deepseek_pro 0.0, kimi -0.010417, qwen 0.0 — at or below the 0.05 family-level
threshold, so H4 is NOT supported under the predeclared family-level gold-span
spread criterion; NOT a full H4 refutation because the Kimi `py_fastapi`
failure slice leaves model×repo interaction inconclusive without per-record
data). Recommended next step: future ephemeral-record B12 replay, or B13 robust
policy search **with caution** (B13 must not be treated as authorized by a B12
supported verdict). See
[`b12-mechanism-decomposition.md`](b12-mechanism-decomposition.md).

B13 distributionally robust policy search:

```text
algorithm_spec_id: b13_dro_policy_search_v0
claim_level: distributionally_robust_policy_search_v0
replay_and_search_only: true (no live LLM calls inside evaluator)
promotion_ready: false
default_should_change: false
evidencecore_semantics_changed: false
stage_is_policy_search: true (B13 stage IS policy search)
empirical_policy_search_performed: false (skeleton performs no empirical search)
policy_search_performed: false (synthetic/stub report; use stage_is_policy_search
                               =true to mark the stage)
quality_strategy_tuned: false
algorithm_spec_has_no_model_names: true (B13 special invariant)
```

B13 is the **distributionally robust policy search** phase that follows B12.
The goal is to find a policy with 6-10 rules, using only runtime-observable
features, that optimizes **worst-group utility** (not the average) or
`CVaR_20%`, validated via rotating leave-one-model-family-out. The rule
grammar is restricted to `route_features` only
(`query_noise`, `candidate_support_exists`, `local_anchor`,
`rrf_backed_by_anchor`, `candidate_count`, `symbol_regex_agree_file`,
`symbol_regex_agree_span`, `rrf_anchor_agree_file`, `rrf_anchor_agree_span`,
`dense_support_present`): **NO** benchmark-private labels (`task_bucket`,
`task_risk_tags`), **NO** score-private fields (`has_gold`, `score_group`,
`outcome_metrics`), and **NO** raw model names in `algorithm_spec` (B13 uses
`model_profile` capabilities like `supports_reliable_span_narrow`,
`cost_class`, `latency_class`; the spec emits abstract `family_slots`
`family_a`/`family_b`/`family_c`/`family_d` instead of "Kimi"/"Qwen"/
"DeepSeek"). Allowed actions are LLM-free: `weak_only`, `use_p25_action`,
`use_local_baseline`. The optimization objective is
`RobustUtility = SpanF0.5 - λ*PFP - μ*normalized_cost - ν*normalized_latency`
with `λ=1.0`, `μ=0.1`, `ν=0.1`, and `CVaR α=0.20`. The search method is bounded
grid + greedy refinement (pure Python; no numpy/sklearn/scipy), capped at
`MAX_RULES=10` and `MAX_SEARCH_ITERATIONS=1000`. Validation uses 3 rotating
leave-one-model-family-out rotations (`loo_family_a`, `loo_family_b`,
`loo_family_c_and_d`); all 3 must pass (worst-group `RobustUtility` within
±0.02 of B10's or strictly better). B13 IS the policy-search *stage*
(`stage_is_policy_search=true`), but the shipped skeleton performs NO
empirical policy search (`empirical_policy_search_performed=false`) and the
synthetic / stub report sets `policy_search_performed=false`,
`policy_found=false`, `rotations_evaluated=false`, `rotations_defined=true`,
`rotation_count=3`, `winner_declared=false` so the public artifact cannot
be misread as an empirical B13 run; synthetic / stub reports emit only
rotation *definitions* (no per-rotation `passes=true` /
`test_worst_group_utility` / `delta_vs_b10_reference`), and the skeleton
verdict framework emits only `insufficient_data` (synthetic fixture) or
`not_implemented` (ci_ephemeral_records stub) — `success` / `failure` /
`partial` are reserved for a future empirical `policy_search_performed=true`
path that is NOT present in this skeleton. The `--self-test` is read-only
(compares in-memory expected artifacts to on-disk artifacts, fails on drift;
does not mutate checked-in artifacts); `--regenerate-artifacts` is the only path that mutates checked-in artifacts. B13
needs P21
records from B11 live runs (4 model families × 8 repos); the `--input` path
is a stub (verdict `not_implemented`; real search deferred). The bounded
public-aggregate feasibility / no-go screen
(`eval/b13_public_aggregate_feasibility_screen.py`) reads the published B11
aggregate + B12 public screen and emits
`verdict=no_go_public_aggregate_only` (or
`insufficient_data_public_aggregate_only`) under
`artifacts/b13_dro_policy_search/`; it never claims empirical policy search,
never selects a rule, never declares a winner. B13 results feed
into B14 (uncertainty calibration) and B16 (downstream agent evaluation) as
research candidates only. B13 is the last "immediate priority" item in the
B10-B19 Breakthrough Sprint; the remaining items (B14-B19) are second priority
or parallel tracks. See
[`b13-distributionally-robust-policy-search.md`](b13-distributionally-robust-policy-search.md).

B14 uncertainty calibration:

```text
algorithm_spec_id: b14_uncertainty_calibration_v0
claim_level: uncertainty_calibration_v0
replay_and_calibration_only: true (no live LLM calls inside evaluator)
promotion_ready: false
default_should_change: false
evidencecore_semantics_changed: false
stage_is_uncertainty_calibration: true (B14 stage IS uncertainty calibration)
uncertainty_calibration_performed: false (skeleton performs no empirical calibration)
calibrated_model_claim: false (no model is claimed to be calibrated)
per_record_inputs_available: false (skeleton; no real per-record inputs)
policy_search_performed: false
quality_strategy_tuned: false
metrics_evaluated: false (skeleton; no fake metric values from aggregate means)
no_fake_metrics_from_aggregate_means: true
algorithm_spec_has_no_model_names: true (B14 special invariant)
```

B14 is the **uncertainty calibration** phase that follows B13. The goal is
**model-independent uncertainty calibration** for the balanced-policy
candidate: produce an uncertainty score per record (never calibrated to a
specific model name) from local candidate signals, model output structure,
and cross-model disagreement, then evaluate that score with risk-coverage,
selective risk, ECE, and PFP-at-fixed-coverage metrics, with worst-group
reporting and rotating leave-one-model-family-out validation. The signal
families are restricted to **NO** benchmark-private labels (`task_bucket`,
`task_risk_tags`), **NO** score-private fields (`has_gold`, `score_group`,
`outcome_metrics`), and **NO** raw model names in `algorithm_spec` (B14 uses
abstract `family_slots` `family_a`/`family_b`/`family_c`/`family_d`). The
frozen coverage levels are `[0.50, 0.70, 0.90, 0.95, 0.99]`; the ECE bin
definition is 15 equal-width bins over `[0, 1]`; the split protocol is
stratified by (model_family, repo) with `calibration_fraction=0.50` /
`test_fraction=0.50` (recalibration on the calibration split only; the test
split is held out and reported once). Predeclared success/partial/failure
criteria use explicit thresholds on ECE on the test split (≤ 0.05),
selective risk at coverage=0.90 (≤ 0.10), worst-group selective risk at
coverage=0.90 (≤ 0.15), and a 0.02 approx-equality / strictly-greater
rotation threshold, plus a `CVaR_20%` worst-group tail average. B14 IS the
uncertainty-calibration *stage*
(`stage_is_uncertainty_calibration=true`), but the shipped skeleton performs
NO empirical uncertainty calibration
(`uncertainty_calibration_performed=false`); the synthetic / stub report
sets `calibrated_model_claim=false`, `per_record_inputs_available=false`,
`uncertainty_score_found=false`, `rotations_evaluated=false`,
`rotations_defined=true`, `rotation_count=3`, `winner_declared=false`,
`metrics_evaluated=false`, `no_fake_metrics_from_aggregate_means=true` so
the public artifact cannot be misread as an empirical B14 calibration.
**CRITICAL**: the skeleton MUST NOT compute fake ECE / risk-coverage /
selective-risk / PFP-at-coverage metrics from aggregate means; the
synthetic fixture validates only metric NAMES and gates (no per-record
(uncertainty, outcome) pairs, no computed metric values). Synthetic / stub
reports emit only rotation *definitions* (no per-rotation `passes=true` /
`test_ece` / `test_selective_risk` / `test_risk_coverage_curve` /
`test_pfp_at_fixed_coverage` / `delta_vs_reference`); the skeleton verdict
framework emits only `insufficient_data` (synthetic fixture) or
`not_implemented` (ci_ephemeral_records stub) — `success` / `failure` /
`partial` are reserved for a future empirical
`uncertainty_calibration_performed=true` path that is NOT present in this
skeleton. The `--self-test` is read-only (compares in-memory expected
artifacts to on-disk artifacts, fails on drift, does not mutate checked-in artifacts);
`--regenerate-artifacts` is the only path that mutates checked-in artifacts. The bounded
public-aggregate feasibility / no-go screen
(`eval/b14_public_aggregate_feasibility_screen.py`) reads the published B11
aggregate + B12 public screen + B13 public feasibility and emits
`verdict=no_go_public_aggregate_only` (or
`insufficient_data_public_aggregate_only`) under
`artifacts/b14_uncertainty_calibration/`; it never claims empirical
calibration, never computes a metric, never selects an uncertainty score,
and never declares a winner. Real B14 calibration cannot be done from
public aggregates alone: it requires per-record uncertainty scores,
per-record binary outcomes, paired cross-model outputs, schema-repair
per-call rows, and candidate score distributions, none of which are present
in current public artifacts. B14 results feed into B16 (downstream agent
evaluation) and future selective-abstention policy work as research
candidates only. See
[`b14-uncertainty-calibration.md`](b14-uncertainty-calibration.md).

B15 context pack policy:

```text
algorithm_spec_id: b15_context_pack_policy_v0
claim_level: context_pack_policy_v0
replay_and_validation_only: true (no live LLM calls inside evaluator)
promotion_ready: false
default_should_change: false
evidencecore_semantics_changed: false
stage_is_context_pack_policy: true (B15 stage IS context pack policy)
pack_policy_learned: false (skeleton performs no PackPolicy learning)
atom_ablation_performed: false (skeleton performs no empirical atom ablation)
per_record_inputs_available: false (skeleton; no real per-record inputs)
policy_search_performed: false
quality_strategy_tuned: false
new_provider_calls: 0
candidate_policy_frozen: false
stages_evaluated: false
stages_defined: true
stage_count: 4
winner_declared: false
metrics_evaluated: false (skeleton; no fake atom-effect values from aggregate means)
no_fake_atom_effects_from_aggregate_means: true
algorithm_spec_has_no_model_names: true (B15 special invariant)
```

B15 is the **context pack policy** phase that follows B14. The goal is a
**frozen, preregistered PackPolicy** mapping
`(role, runtime_state, model_profile)` to a deterministic **atom set**
(the pack-layout atoms a context pack should expose), validated
against per-record pack-atom flags + per-record outcomes + role +
runtime_state + model_profile + group membership from B11/B13 live
runs. B15 is a **bounded planning / feasibility phase**, NOT an
empirical atom-level ablation. Roles are FROZEN (`span_narrow`,
`filter_reject`, `request_more_context`, `source_test_disambiguation`);
the atom registry is FROZEN (`signature`, `matched_lines`,
`raw_snippet`, `neighbor_context`, `scores`, `provenance`,
`hard_distractor`, `same_file_competitor`, `path_kind_flag`); the
runtime_state contract is label-free and model-name-free; the
model_profile abstraction uses abstract capability slots
(`profile_slot_a`..`profile_slot_d`) + capability descriptors only —
**NO** raw model names in `algorithm_spec` (B15 uses abstract
`abstract_profile_slots`, never `kimi`/`qwen`/`deepseek`/`glm`). The
experimental structure is FROZEN into 4 stages: `no_llm_feasibility` →
`fractional_factorial_live_atom_screen` (resolution-IV fraction over
the atom registry, no full 2^9 factorial) → `freeze_candidate_policy`
→ `fresh_validation` (stratified by `(model_family, repo, role)` with
`atom_screen_fraction=0.50` / `fresh_validation_fraction=0.50`, held
out and reported once). Hard gates (FROZEN): `privacy_gate`,
`leakage_gate`, `adapter_health_gate`,
`randomization_balance_gate`, `denominator_gate` (min 30 per cell),
`token_budget_gate`, `promotion_false_gate`. Metric registry (FROZEN,
9 names): `atom_effect_per_atom`, `role_pack_outcome`,
`runtime_state_pack_outcome`, `model_profile_pack_outcome`,
`worst_group_pack_outcome`, `cvar_20_pack_outcome`,
`token_budget_parity`, `denominator_per_atom_role_model`,
`randomization_balance_per_arm` — every metric requires per-record
(atom_flag, outcome, role, runtime_state, model_profile) tuples;
none can be computed from aggregate means. Predeclared
success/partial/failure criteria use explicit thresholds on
fresh-validation-split per-role pack-outcome improvement (≥ 0.02),
worst-group pack-outcome regression (≤ 0.15), denominator
(≥ 30 per cell), randomization balance (≤ 0.05 imbalance),
token-budget match tolerance (0.10), plus a `CVaR_20%` worst-group
tail average. B15 IS the context-pack-policy *stage*
(`stage_is_context_pack_policy=true`), but the shipped skeleton
performs NO empirical PackPolicy learning (`pack_policy_learned=false`)
and NO empirical atom ablation (`atom_ablation_performed=false`); the
synthetic / stub report sets `per_record_inputs_available=false`,
`candidate_policy_frozen=false`, `stages_evaluated=false`,
`stages_defined=true`, `stage_count=4`, `winner_declared=false`,
`metrics_evaluated=false`, `no_fake_atom_effects_from_aggregate_means=true`
so the public artifact cannot be misread as an empirical B15
PackPolicy result. **CRITICAL**: the skeleton MUST NOT compute fake
atom-effect / role-pack-outcome / worst-group-pack-outcome metrics
from aggregate means; the synthetic fixture validates only metric
NAMES and gates (no per-record (atom_flag, outcome) pairs, no
computed metric values). Synthetic / stub reports emit only stage
*definitions* (no per-stage `passes=true` /
`atom_effect_per_atom` / `role_pack_outcome` /
`worst_group_pack_outcome`); the skeleton verdict framework emits
only `insufficient_data` (synthetic fixture) or `not_implemented`
(ci_ephemeral_records stub) — `success` / `failure` / `partial` are
reserved for a future empirical `atom_ablation_performed=true` /
`pack_policy_learned=true` path that is NOT present in this
skeleton. The `--self-test` is read-only (compares in-memory expected
artifacts to on-disk artifacts, fails on drift, does not mutate
checked-in artifacts); `--regenerate-artifacts` is the only path that
mutates checked-in artifacts; `--input` stub requires explicit
`--out` and refuses to write the canonical checked-in B15 report. The
bounded public-aggregate prior / no-go screen
(`eval/b15_public_aggregate_prior_screen.py`) reads the published B2
contrastive-pack experiment (existence only), the B14 public-
aggregate feasibility report, and — when present — the B4-B9 / P21-G /
P49 public aggregates, and emits
`verdict=prior_screen_only` (or `no_go_public_aggregate_only` when B2
is missing) under `artifacts/b15_context_pack_policy/`; it never
claims empirical PackPolicy learning, never computes an atom-effect
metric, never freezes a candidate policy, and never declares a winner.
The published B2 contrastive-pack experiment is a single-model,
low-N (24 tasks per layout), aggregate-only pack-layout comparison;
it is usable ONLY as a
`low_n_single_model_aggregate_directional_prior`
(`b2_prior_usable=true`,
`b2_prior_claim_level=low_n_single_model_aggregate_directional_prior`),
NOT as atom-level causality, role-specific PackPolicy, calibrated
policy, cross-model robustness, a hard-distractor general rule, a
scores/provenance general win, a default change, a promotion, or an
EvidenceCore change. Real B15 PackPolicy validation cannot be done
from public aggregates alone: it requires per-record pack atom flags,
per-record outcomes, role-specific paired outputs, model_profile
paired blocks, group membership, randomized atom assignment,
randomization balance stats, denominator-by-atom/role/model cells,
and token-budget-matched controls, none of which are present in
current public artifacts. B15 results feed into B16 (downstream agent
evaluation) and future context-pack routing work as research
candidates only. See
[`b15-context-pack-policy.md`](b15-context-pack-policy.md).

B16 downstream coding-agent evaluation:

```text
algorithm_spec_id: b16_downstream_agent_evaluation_v0
claim_level: downstream_agent_evaluation_v0
replay_and_validation_only: true (no live LLM calls and no live downstream agent runs inside evaluator)
promotion_ready: false
default_should_change: false
evidencecore_semantics_changed: false
retrieval_variant_promoted: false
stage_is_downstream_agent_evaluation: true (B16 stage IS downstream agent evaluation)
downstream_agent_runs_performed: false (skeleton performs no live agent runs)
patch_execution_performed: false (skeleton performs no patch execution)
agent_behavior_metrics_evaluated: false (skeleton evaluates no agent behavior metrics)
solve_rate_evaluated: false (skeleton evaluates no solve rate)
per_record_inputs_available: false (skeleton; no real per-run inputs)
policy_search_performed: false
quality_strategy_tuned: false
new_provider_calls: 0
candidate_retrieval_variant_frozen: false
stages_evaluated: false
stages_defined: true
stage_count: 4
winner_declared: false
metrics_evaluated: false (skeleton; no fake solve-rate or downstream metrics from retrieval aggregates)
no_fake_downstream_metrics_from_retrieval_aggregates: true
```

B16 is the **downstream coding-agent evaluation** phase that follows
B15. The goal is a **frozen, preregistered paired within-task
randomized controlled trial** that measures whether a candidate
retrieval/context variant improves a downstream coding agent (not
just retrieval aggregates) on real, paired, isolated-workspace agent
runs. B16 is a **bounded planning / feasibility phase**, NOT live
downstream agent evaluation. Arms are FROZEN into primary
(`control_current_retrieval_v0`, `balanced_v1_retrieval_candidate`),
exploratory (`candidate_pack_policy_v0`, only included if a real B15
candidate exists — the B15 skeleton does NOT produce one, so this arm
is EXCLUDED by default), and debugging-only (`gold_context_ceiling`,
never promoted). Task types are FROZEN (`bug_localization`,
`small_code_edit`, `test_selection`, `multi_file_feature`,
`refactor_impact`). The paired RCT enforces paired within-task
randomization, isolated fresh workspace per run, randomized arm
order, same budget/tools/prompt except the retrieval/context variant,
and no cross-run memory. Hard gates (FROZEN): `feasibility_gate`,
`denominator_gate` (min 30 per (task_type, arm) cell),
`leakage_gate`, `operational_parity_gate` (token-budget match
tolerance 0.10, latency match tolerance 0.15, same tools/budget/prompt
except retrieval variant, isolated fresh workspace, randomized arm
order, no cross-run memory), `privacy_gate`, `promotion_false_gate`.
Metric registry (FROZEN, 8 names): `solve_rate`,
`correct_file_before_first_edit`, `wrong_file_edits`,
`tool_calls_before_first_edit`, `context_tokens`, `tests_pass`,
`latency`, `cost` — every metric requires per-run paired agent
outputs (event logs, patches/diffs, test execution results, solve
labels, first-file-before-first-edit events, wrong-file-edit
annotations, tool-call/token/latency/cost rows, isolated workspace
proof, randomized arm order, task oracle/hidden-test manifest); none
can be computed from retrieval aggregates. Predeclared
success/partial/failure criteria use explicit thresholds on
fresh-validation-split solve-rate improvement (≥ 0.02),
correct-file-before-first-edit improvement (≥ 0.02),
wrong-file-edits regression (≤ 0.15), denominator (≥ 30 per cell),
randomization balance (≤ 0.05 imbalance), operational parity
(token-budget 0.10, latency 0.15), cost reported per arm, plus a
`CVaR_20%` worst-group tail average. B16 IS the downstream-agent-
evaluation *stage*
(`stage_is_downstream_agent_evaluation=true`), but the shipped
skeleton performs NO live downstream agent runs
(`downstream_agent_runs_performed=false`), NO patch execution
(`patch_execution_performed=false`), NO agent-behavior metrics
evaluation (`agent_behavior_metrics_evaluated=false`), and NO
solve-rate evaluation (`solve_rate_evaluated=false`); the
synthetic / stub report sets `per_record_inputs_available=false`,
`candidate_retrieval_variant_frozen=false`,
`stages_evaluated=false`, `stages_defined=true`, `stage_count=4`,
`winner_declared=false`, `metrics_evaluated=false`,
`no_fake_downstream_metrics_from_retrieval_aggregates=true` so the
public artifact cannot be misread as an empirical B16 downstream
agent result. **CRITICAL**: the skeleton MUST NOT compute fake
solve-rate / correct-file-before-first-edit / wrong-file-edits /
tool-call / token / latency / cost metrics from retrieval aggregates;
the synthetic fixture validates only metric NAMES and gates (no
per-run paired agent outputs, no computed metric values). Synthetic
/ stub reports emit only stage *definitions* (no per-stage
`passes=true` / `solve_rate` / `correct_file_before_first_edit` /
`wrong_file_edits`); the skeleton verdict framework emits only
`insufficient_data` (synthetic fixture) or `not_implemented`
(ci_ephemeral_records stub) — `success` / `failure` / `partial` are
reserved for a future empirical
`downstream_agent_runs_performed=true` /
`solve_rate_evaluated=true` path that is NOT present in this
skeleton. The `--self-test` is read-only (compares in-memory expected
artifacts to on-disk artifacts, fails on drift, does not mutate
checked-in artifacts); `--regenerate-artifacts` is the only path that
mutates checked-in artifacts; `--input` stub requires explicit
`--out` and refuses to write ANY path inside
`artifacts/b16_downstream_agent_evaluation/`. The bounded
public-aggregate feasibility / no-go screen
(`eval/b16_public_aggregate_feasibility_screen.py`) reads the
published B11 matrix + B12 + B13 + B14 + B15 public screens and
emits `verdict=no_go_public_aggregate_only` (or
`insufficient_data_public_aggregate_only`) under
`artifacts/b16_downstream_agent_evaluation/`; it never claims
downstream agent value, never computes a downstream metric from
retrieval aggregates, never freezes a candidate retrieval variant,
never promotes a retrieval variant, and never declares a winner.
The B10-B15 retrieval/context candidate research is retrieval
research; it does NOT prove downstream coding-agent value. Retrieval
improvements are NOT downstream agent improvements; B15 PackPolicy
is NOT a downstream agent improvement. Real B16 downstream agent
evaluation cannot be done from public aggregates alone: it requires
paired live downstream agent runs, per-run agent event logs,
per-run patches/diffs, per-run test execution results, per-run solve
labels, per-run first-file-before-first-edit events, per-run
 wrong-file-edit annotations, per-run tool-call/token/latency/cost
 rows, per-run isolated fresh workspace proof, per-run randomized arm
 order, and a task oracle/hidden-test manifest, none of which are
 present in current public artifacts. B11 `partial_with_failure` and
 B12/B13/B14/B15 no-go or screen-only statuses are carried forward
 unchanged. See
 [`b16-downstream-agent-evaluation.md`](b16-downstream-agent-evaluation.md).

B17 QuIVer systems track:

```text
algorithm_spec_id: b17_quiver_systems_track_v0
claim_level: quiver_systems_track_v0
replay_and_validation_only: true (no live LLM calls and no live ANN backend bakeoff inside evaluator)
promotion_ready: false
default_should_change: false
evidencecore_semantics_changed: false
retrieval_policy_changed: false
backend_quality_promoted: false
stage_is_quiver_systems_track: true (B17 stage IS quiver systems track)
quiver_graph_implemented: false (skeleton performs no QuIVer or Vamana graph implementation)
ann_backend_bakeoff_performed: false (skeleton performs no ANN backend bakeoff)
candidate_set_equivalence_validated: false (skeleton validates no candidate-set equivalence)
metrics_evaluated: false (skeleton; no fake ANN metrics from diagnostics)
new_provider_calls: 0
all_stages_pass: false
stages_evaluated: false
stages_defined: true
stage_count: 4
winner_declared: false
no_fake_ann_metrics_from_diagnostics: true
```

B17 is the **QuIVer systems track** phase that follows B16. The goal
is a **frozen, preregistered backend bakeoff** comparing ANN backend
candidates on backend systems metrics (latency, memory, build time,
update cost, index size) **under a frozen candidate-quality policy**
so backend quality cannot be silently relaxed when comparing systems
numbers. B17 is a **bounded planning / diagnostic phase**, NOT
QuIVer production backend, NOT ANN quality promotion, NOT default
change, NOT EvidenceCore semantics change. Candidate backends are
FROZEN into reference (`flat_f32_reference`), candidate
(`hnsw_candidate`, `bq_topk_f32_rerank_candidate`,
`quiver_vamana_prototype` — the QuIVer/Vamana graph backend end goal,
**unimplemented**), and optional-store
(`tdb_vector_candidate`, store/backend candidate only, NOT an
Evidence source, excluded by default). Candidate-set equivalence
constraints are FROZEN (`candidate_set_overlap_at_k` ≥ 0.90 at
K=[10,50,100], `gold_retention_delta` tolerance 0.05,
`primary_false_positive_delta` guard 0.05, `span_f0_5_delta`
tolerance 0.05, `citation_validity` = 1.0,
`stale_evidencecore_rejection_required`,
`no_default_expansion_required`). Hard gates (FROZEN):
`quiver_graph_implementation_gate`, `backend_parity_gate`,
`candidate_set_equivalence_gate`,
`evidencecore_materialization_gate`, `stale_citation_gate`,
`privacy_gate`, `promotion_false_gate`. Metric registry (FROZEN, 11
names): `candidate_set_overlap_at_k`, `gold_retention_delta`,
`span_f0_5_delta`, `primary_false_positive_delta`, `p50_latency`,
`p95_latency`, `hot_memory`, `build_time`, `update_cost`,
`index_size`, `recall_tolerance_violation_count` — every metric
requires per-backend systems bakeoff inputs (index build records,
search latency records, hot memory records, index size records,
update cost records, candidate-set-at-K records, gold retention
records, span F0.5 records, PFP records, citation validity records,
stale rejection records, EvidenceCore rejection records, recall
tolerance violation records, randomized run order proof, isolated
index workspace proof, shared frozen candidate-quality manifest);
none can be computed from the existing R33/R34/R36/R24 diagnostics.
B17 IS the quiver-systems-track *stage*
(`stage_is_quiver_systems_track=true`), but the shipped skeleton
performs NO ANN backend bakeoff
(`ann_backend_bakeoff_performed=false`), NO candidate-set
equivalence validation
(`candidate_set_equivalence_validated=false`), NO QuIVer/Vamana
graph implementation (`quiver_graph_implemented=false`), and NO
backend quality promotion (`backend_quality_promoted=false`); the
synthetic-fixture / `--input` stub report sets
`promotion_ready=false`, `default_should_change=false`,
`evidencecore_semantics_changed=false`,
`retrieval_policy_changed=false`, `metrics_evaluated=false`,
`new_provider_calls=0`, `no_fake_ann_metrics_from_diagnostics=true`
so the public artifact cannot be misread as an empirical B17 systems
bakeoff result. **CRITICAL**: the skeleton MUST NOT compute fake
candidate_set_overlap_at_k / gold_retention_delta / span_f0_5_delta
/ primary_false_positive_delta / p50_latency / p95_latency /
hot_memory / build_time / update_cost / index_size /
recall_tolerance_violation_count metrics from the existing
R33/R34/R36/R24 diagnostics; the synthetic fixture validates only
metric NAMES and gates (no per-backend systems bakeoff inputs, no
computed metric values). Synthetic / stub reports emit only stage
*definitions* (no per-stage `passes=true` / `candidate_set_overlap_at_k`
/ `gold_retention_delta` / `p50_latency` / `hot_memory` /
`build_time` / `index_size`); the skeleton verdict framework emits
only `insufficient_data` (synthetic fixture) or `not_implemented`
(ci_ephemeral_records stub) — `success` / `failure` / `partial` are
reserved for a future empirical
`ann_backend_bakeoff_performed=true` /
`candidate_set_equivalence_validated=true` /
`quiver_graph_implemented=true` path that is NOT present in this
skeleton. The `--self-test` is read-only (compares in-memory expected
artifacts to on-disk artifacts, fails on drift, does not mutate
checked-in artifacts); `--regenerate-artifacts` is the only path
that mutates checked-in artifacts; `--input` stub requires explicit
`--out` and refuses to write ANY path inside
`artifacts/b17_quiver_systems_track/`. The bounded public-systems
diagnostic carry-forward / no-go screen
(`eval/b17_public_systems_diagnostic_screen.py`) reads the published
R33 readiness + R34/R36 anchor-proto + real-provider P3/P4 quiver
diagnostics + optional R24 QuIVer/TDB/dense probe and emits
`verdict=no_go_quiver_graph_missing` (or
`diagnostic_carry_forward_only`) under
`artifacts/b17_quiver_systems_track/`; it never claims QuIVer
implementation, never computes an ANN metric from diagnostics, never
promotes a backend, never changes retrieval policy, and never
declares a winner. The existing R33/R34/R36/R24 diagnostics are
**diagnostic-only carry-forward** — they are NOT quality proof and
NOT promotion evidence; they do NOT implement a QuIVer/Vamana graph
backend, do NOT contain an HNSW run, and do NOT contain a
candidate-set equivalence matrix across backends. See
[`b17-quiver-systems-track.md`](b17-quiver-systems-track.md).

 B18 OOD / temporal evaluation:

 ```text
 algorithm_spec_id: b18_ood_temporal_evaluation_v0
 claim_level: ood_temporal_evaluation_v0
 replay_and_validation_only: true (no live LLM calls and no live OOD or temporal evaluation inside evaluator)
 promotion_ready: false
 default_should_change: false
 evidencecore_semantics_changed: false
 retrieval_policy_changed: false
 backend_quality_promoted: false
 stage_is_ood_temporal_evaluation: true (B18 stage IS OOD and temporal evaluation)
 ood_temporal_evaluation_performed: false (skeleton performs no OOD or temporal evaluation)
 metrics_evaluated: false (skeleton; no fake OOD or temporal metrics from aggregate means)
 policy_search_performed: false (no-retuning protocol)
 quality_strategy_tuned: false (no-retuning protocol)
 real_ood_temporal_supported: false
 new_provider_calls: 0
 all_axes_pass: false
 axes_evaluated: false
 axes_defined: true
 axis_count: 5
 winner_declared: false
 no_fake_ood_metrics_from_aggregate_means: true
 ```

 B18 is the **OOD (out-of-distribution) / temporal evaluation** phase
 that follows B17. The goal is a **frozen, preregistered OOD /
 temporal evaluation** of the retrieval / candidate / Evidence
 pipeline across five FROZEN split axes — `temporal_split`,
 `repo_split`, `language_split`, `model_family_split`,
 `adversarial_split` — **under a no-retuning protocol** (no policy
 search, no quality strategy tuning, no retrieval policy change, no
 EvidenceCore semantics change, no default change, no promotion) so
 an in-distribution average cannot be mistaken for OOD / temporal
 generalization. B18 is a **bounded preregistration + public-
 aggregate no-go screen phase**, NOT a real OOD / temporal
 evaluation, NOT a policy search, NOT a quality strategy tuning, NOT
 a default change, NOT an EvidenceCore semantics change, NOT a
 promotion. Split axes are FROZEN (`temporal_split`,
 `repo_split`, `language_split`, `model_family_split`,
 `adversarial_split`). No-retuning protocol is FROZEN
 (`no_retuning_protocol=true`, `no_policy_search=true`,
 `no_quality_strategy_tuning=true`, `no_retrieval_policy_change=true`,
 `no_evidencecore_semantics_change=true`, `no_default_change=true`,
 `no_promotion=true`). Hard gates (FROZEN): `per_record_data_gate`,
 `time_axis_gate`, `commit_chronology_gate`, `no_retuning_gate`,
 `adversarial_holdout_gate`, `temporal_holdout_gate`,
 `evidencecore_materialization_gate`, `stale_citation_gate`,
 `privacy_gate`, `promotion_false_gate`. Metric registry (FROZEN, 13
 names): `ood_generalization_gap`, `temporal_holdout_delta`,
 `repo_holdout_metric`, `language_holdout_metric`,
 `model_family_holdout_metric`, `adversarial_robustness_score`,
 `worst_group_metric`, `cvar_tail_metric`, `per_cell_denominator`,
 `temporal_split_integrity`, `no_retuning_proof_metric`,
 `citation_validity`, `stale_evidencecore_rejection_rate` — every
 metric requires per-record OOD / temporal inputs (per-record
 records, per-record time index, per-record commit chronology,
 per-record repo / language / model_family axes, per-record task
 category, per-record adversarial holdout membership, per-record
 temporal holdout membership, per-record outcome label, per-record
 citation validity, per-record stale rejection, per-record
 EvidenceCore rejection, per-record randomized run order proof,
 per-record no-retuning proof, shared frozen evaluation protocol
 manifest); none can be computed from the B11 aggregate means or
 from the R15 / R20 / R26 repo locks. B18 IS the ood-temporal-
 evaluation *stage* (`stage_is_ood_temporal_evaluation=true`), but
 the shipped skeleton performs NO real OOD / temporal evaluation
 (`ood_temporal_evaluation_performed=false`), NO metrics evaluation
 (`metrics_evaluated=false`), NO policy search
 (`policy_search_performed=false`), NO quality strategy tuning
 (`quality_strategy_tuned=false`), and NO promotion
 (`promotion_ready=false`); the synthetic-fixture / `--input` stub
 report sets `promotion_ready=false`, `default_should_change=false`,
 `evidencecore_semantics_changed=false`,
 `retrieval_policy_changed=false`, `metrics_evaluated=false`,
 `new_provider_calls=0`, `no_fake_ood_metrics_from_aggregate_means=true`
 so the public artifact cannot be misread as an empirical B18 OOD /
 temporal result. **CRITICAL**: the skeleton MUST NOT compute fake
 ood_generalization_gap / temporal_holdout_delta /
 repo_holdout_metric / language_holdout_metric /
 model_family_holdout_metric / adversarial_robustness_score /
 worst_group_metric / cvar_tail_metric / per_cell_denominator /
 temporal_split_integrity / no_retuning_proof_metric /
 citation_validity / stale_evidencecore_rejection_rate metrics from
 the existing B11 aggregate means or from the R15 / R20 / R26 repo
 locks; the B11 aggregate carries public model-family means + repo
 slice list + sanitized failure slices but NO per-record, per-time-
 index, per-repo-per-language cell, model_family x repo matrix,
 adversarial holdout outcome, or temporal holdout outcome, and the
 R15 / R20 / R26 repo locks are synthetic / static snapshots with no
 real commit chronology or time axis. Synthetic / stub reports emit
 only stage *definitions* (no per-stage `passes=true` /
 `ood_generalization_gap` / `temporal_holdout_delta` /
 `worst_group_metric` / `cvar_tail_metric` / `per_cell_denominator`);
 the skeleton verdict framework emits only `insufficient_data`
 (synthetic fixture) or `not_implemented` (ci_ephemeral_records
 stub) — `success` / `failure` / `partial` are reserved for a future
 empirical `ood_temporal_evaluation_performed=true` /
 `metrics_evaluated=true` path that is NOT present in this skeleton.
 The `--self-test` is read-only (compares in-memory expected
 artifacts to on-disk artifacts, fails on drift, does not mutate
 checked-in artifacts); `--regenerate-artifacts` is the only path
 that mutates checked-in artifacts; `--input` stub requires explicit
 `--out` and refuses to write ANY path inside
 `artifacts/b18_ood_temporal_evaluation/`. The bounded public-
 aggregate no-go screen (`--public-screen --out <path>`, also run
 from `--regenerate-artifacts`) reads the published B11 prospective
 matrix aggregate report plus optional R15 / R20 / R26 repos.lock.jsonl
 files and dataset manifests and emits `verdict=no_go_public_aggregate_only`
 (or `public_aggregate_carry_forward_only`) under
 `artifacts/b18_ood_temporal_evaluation/`; it never claims OOD /
 temporal evaluation, never computes an OOD / temporal metric from
 aggregate means, never promotes a retrieval variant, never changes
 retrieval policy, and never declares a winner. The existing B11 /
 R15 / R20 / R26 aggregates are **aggregate-only / metadata-only
 carry-forward** — they are NOT OOD / temporal proof and NOT
 promotion evidence; they do NOT contain per-record records, a time
 axis, commit chronology, per-repo-per-language cells, a
 model_family x repo matrix, adversarial holdout outcomes, or
 temporal holdout outcomes. See
 [`b18-ood-temporal-evaluation.md`](b18-ood-temporal-evaluation.md).

B19 theoretical synthesis (Model-Robust Selective Evidence Conversion):

```text
algorithm_concept: Model-Robust Selective Evidence Conversion
schema_version: b19-theoretical-synthesis-report-v0
claim_level: theoretical_synthesis_of_b10_through_b18
is_synthesis_only: true
is_new_experiment: false
ran_providers: false
new_provider_calls: 0
changed_retrieval_default_evidencecore: false
aggregate_only_public_artifact: true
synthesized_stages: B10, B10B, B11, B12, B13, B14, B15, B16, B17, B18
promotion_ready: false
default_should_change: false
evidencecore_semantics_changed: false
runtime_clean_policy_supported: false
downstream_agent_value_proven: false
ood_temporal_supported: false
quiver_systems_supported: false
forbidden_public_scan_clean: true
report_drift_guarded: true
```

B19 is the **theoretical synthesis** of the B10-B18 Breakthrough Sprint. It
is **synthesis-only**: it does NOT run any provider, does NOT change
retrieval / default / EvidenceCore, and does NOT claim promotion. It
synthesizes B10 / B10B / B11 / B12 / B13 / B14 / B15 / B16 / B17 / B18
into a single paper-style algorithm report for the candidate algorithm
concept **Model-Robust Selective Evidence Conversion** — a model-robust,
runtime-clean, evidence-gated policy that selectively converts high-
reach / high-false-cost local candidate pools into current-source
`EvidenceCore` spans by decoupling recall from admission, routing LLM
roles selectively, and optimizing worst-group utility across model
adapters.

Inputs: query, local candidate pool, runtime-observable uncertainty,
model capability profile, latency/cost budget. Outputs/actions:
local-only, weak/supporting, LLM span-narrow, LLM filter, abstain,
request-more-context, then `EvidenceCore` materialization. Core
principles: recall/admission decoupling; LLM role-selective routing;
algorithm/model-adapter separation; runtime-observable features only
(for a runtime-clean policy); worst-group / cross-model robust
optimization; candidate must materialize into current-source
`EvidenceCore`. Formal sections cover problem statement, algorithm
sketch/pseudocode, evidence boundary, policy-learning loop, adapter
boundary, evaluation protocol, current empirical evidence, no-go gaps,
promotion blockers, and next research program.

Carried forward verbatim (NO new claims beyond B10-B18):

- **B10** — `balanced_policy_v1_benchmark_routed` was benchmark-routed,
  not runtime-clean (`runtime_clean=false`).
- **B10B** — mechanics-validated runtime-shadow scaffold + CI
  integration; empirical support pending (label-driven denominator < 10
  in all B11 runs).
- **B11** — official integrated matrix 32/32, 384 records, aggregate
  verdict `partial_with_failure`; balanced_v1 vs p25 deltas:
  `Δgold_span -0.002604`, `ΔSpanF0.5 -0.001899`, `Δfalse_span -0.054688`,
  `ΔPFP -0.020833`, `Δmodel_calls -0.354167`. Strengthens algorithm-
  candidate signal but NO promotion.
- **B12** — public aggregate cannot identify mechanism; needs per-record
  strategy/action outcomes.
- **B13** — public aggregate cannot run real DRO search; needs per-record
  group/action outcomes.
- **B14** — cannot calibrate uncertainty from public aggregates; needs
  per-record/model-output structure.
- **B15** — cannot learn Context Pack Policy from public aggregates;
  current value is preregistration/prior screen.
- **B16** — downstream agent value unproven; needs fixed agent harness
  with patch/test outcomes.
- **B17** — QuIVer systems track no-go: QuIVer graph/vector backend
  missing; systems-only future track.
- **B18** — OOD/temporal no-go from public aggregate; needs per-record
  temporal/repo/language/model/adversarial axes.

The B19 public artifact
(`artifacts/b19_theoretical_synthesis/b19_theoretical_synthesis_report.json`,
schema `b19-theoretical-synthesis-report-v0`) is aggregate-only, runs a
B19-specific forbidden-key scan (clean), embeds a self-hash drift guard,
and carries the B11 deltas byte-for-byte. `eval/b19_theoretical_synthesis.py`
`--self-test` verifies required sections, all no-promotion flags false,
B11 deltas exact, forbidden scan clean, docs links exist, and drift
guard matched. No fake metrics; no new claims beyond B10-B18. See
[`b19-theoretical-synthesis.md`](b19-theoretical-synthesis.md).

---

## Current status update — 2026-06-13

The research program has moved beyond the original local-only benchmark stages
into controlled real-provider CI experiments. The current conclusion is not a
promotion decision; it is a sharper research boundary:

```text
RRF remains the recall base.
symbol/regex remain precision anchors.
query_noise_plus_rrf_agree_min remains the strongest guard candidate.
real dense embeddings have candidate/file-level signal but are unstable as global dense.
P20-LS-A blocks low-context/query-only LLM aliases, not rich-context LLM retrieval.
P21-G should prioritize cross-model context injection effects, richer code context, quality, latency, and cost.
Dense/QuIVer/LLM-derived/graph remain supporting/diagnostic/candidate only.
P32/P30-H4 anchor-subtype budget overlay is now wired into P30; it tests demotion, not primary promotion.
P32/P30-H4B selective primary re-admission is now wired into P30; it tests an extremely narrow strict gate and keeps almost all tasks non-primary.
promotion_ready=false and current_default_should_change=false.
```

Most important recent finding: **L1/L2 and P20-LS-A exposed the weakness of
under-contextualized model retrieval**. L1/L2 showed dense-only/global dense risk
with `BAAI/bge-m3` and the conservative `path_plus_symbol` view at
`60 tasks / 1000 records / 2000 files`: four large-repo slices all had
`primary_false_positive_rate=1.0`, very low `SpanF0.5`, and unstable file recall.
P20-LS-A showed the same pattern for low-context/query-only LLM aliases: schema
and guardrails passed, but quality failed. This blocks dense-only/global dense
and low-context aliases from primary/default use, and shifts the next phase to
P21-G: context atoms, context packs, model profiles, roles, layouts, richer
snippets/candidate metadata, and explicit latency/cost accounting.

Current detailed conclusion reports:

- [`docs/zh/current-research-conclusions.md`](../zh/current-research-conclusions.md) /
  [`docs/en/current-research-conclusions.md`](current-research-conclusions.md)
- [`docs/zh/real-provider-ci-large-scale.md`](../zh/real-provider-ci-large-scale.md) /
  [`docs/en/real-provider-ci-large-scale.md`](real-provider-ci-large-scale.md)
- [`p20-llm-large-scale.md`](p20-llm-large-scale.md)
- [`p21-g-cross-model-context-injection.md`](p21-g-cross-model-context-injection.md)
- [`real-provider-ci-scale-p8-p9.md`](real-provider-ci-scale-p8-p9.md)
- [`real-provider-p7-summary.md`](real-provider-p7-summary.md)

Next research direction: freeze the L2 suite, attribute false positives, then
run P21-G cross-model context-injection experiments on public/opt-in corpora:
context atom screening, context pack ladders, LLM rerank/filter/span-narrow over
local candidates, inventory-grounded aliases, and prompt/context/layout matrices. Continue excluding
secrets, ignored files, provider keys, and private labels/gold answers, but do
not let context minimization dominate quality.

## P25 Bucket-Routed LLM Role Policy (2026-06-14)

A deterministic P25 policy evaluator (`eval/p25_bucket_policy.py`) is now
available. The committed report is a sanitized synthetic self-test scaffold
(`status=self_test_only`, `not_quality_evidence=true`), not a quality result.
Real P25 evaluation now requires ephemeral SCORE-phase records produced by
`eval/p21_llm_rich_candidate.py --p25-policy-records-out`; those records stay
under runner temp and are not uploaded, while P25 uploads aggregate metrics
only. The evaluator compares five policies: `candidate_baseline`,
`global_span_narrow`, `global_filter`, `global_abstain_filter`, and
`bucket_routed_v0`. The bucket-routed policy routes `llm_span_narrow` to
likely-positive/high-confidence buckets, routes `llm_filter`/`llm_abstain_filter`
to negative/dense-false-positive/ambiguous buckets using a fixed a-priori
negative strategy, skips LLM calls when an exact-symbol-plus-unique-anchor signal
is available, and falls back to the candidate baseline otherwise. Aggregate P21
summaries and non-ephemeral schemas are rejected with
`status=insufficient_task_detail`; no policy is promotion-ready or default-ready. See
[`docs/p25-bucket-routed-policy.md`](p25-bucket-routed-policy.md).

The first real P25 remote smoke then ran six successful aggregate policy runs
(`Flash/Kimi/GLM × py_flask/js_express`, 18 bucket-sampled tasks each) via the
safe P21→P25 ephemeral SCORE handoff. `bucket_routed_v0` strongly reduced false
spans (`108 -> 28`) and mean PFP (`-0.0926`), while losing some gold spans
(`24 -> 21`). Mean SpanF0.5 delta was only slightly positive (`+0.0026`) and
repo/model-dependent. This makes P25 useful as a false-primary reducer component
for P30 Admission V3, not a default/promotion candidate. Remote summary:
[`docs/p25-bucket-routed-policy-remote-smoke.md`](p25-bucket-routed-policy-remote-smoke.md).

## P30 Admission Model V3 (2026-06-14)

P30 adds a deterministic explainable admission model evaluator
(`eval/p30_admission_model_v3.py`) as a research-only follow-on to P25.
The committed artifact is a sanitized synthetic self-test scaffold
(`status=self_test_only`, `not_quality_evidence=true`) and is not a quality
result. P30 consumes the same ephemeral `p25-policy-records-ephemeral-v1`
records produced by `eval/p21_llm_rich_candidate.py --p25-policy-records-out`,
rejects aggregate summaries and non-ephemeral schemas, and routes only from
RUN-phase public/observable features (`task_bucket`, `task_risk_tags`,
`route_features`). Labels, gold, `score_group`, and outcome metrics are used
only for aggregate scoring after actions are chosen.

Allowed admission actions are: `abstain`, `admit_symbol_regex_union`,
`admit_rrf_primary`, `admit_llm_span_narrow`, `apply_llm_filter`,
`supporting_only`, and `weak_candidate_only`. The `admission_v3` scorecard
uses monotonic feature scores and hard guards around query noise,
exact/unique symbol anchors, symbol/regex/local anchors, RRF-backed-by-anchor
signals, LLM span-narrow validity/within-candidate, and negative/ambiguous/
dense-false-positive buckets. Dense and graph signals are allowed only as
supporting features; they cannot invent primary evidence.

The evaluator compares `candidate_baseline`, `llm_span_narrow`, `llm_filter`,
`llm_abstain_filter`, `bucket_routed_v0` (reused from P25), and
`admission_v3`. Aggregates include task count, SpanF0.5, PFP, added gold/false
spans, filter gold kill rate, abstain rate, action counts, score bands,
selective risk proxy, deltas versus the candidate baseline and
`bucket_routed_v0`, and explicit outcome-fallback counters for actions that do
not have measured outcomes in a given ephemeral record. Public output is
recursively scanned for forbidden keys
(raw query/snippet/prompt/response/gold/gold_spans/private label/provider key
fields). `promotion_ready=false`, `default_should_change=false`,
`evidencecore_semantics_changed=false`, `candidate_not_fact=true`,
`external_calls=0`.

P30 is intentionally not a promotion candidate. The next validation step is to
run the evaluator against real P25 ephemeral smoke records and compare the
scorecard to P25 `bucket_routed_v0` and the P22/P23 evidence-seeking guard
surfaces. See [`docs/p30-admission-model-v3.md`](p30-admission-model-v3.md).

The first real P30 remote smoke ran six successful workflow runs
(`Flash/Kimi/GLM × py_flask/js_express`, 18 bucket-sampled tasks each). On this
smoke, `admission_v3` matched `bucket_routed_v0`'s mean PFP reduction versus
baseline (`-0.0833`) but was more conservative and lower quality: baseline
`27/102` gold/false, `bucket_routed_v0` `19/39`, and `admission_v3` `17/41`.
Mean SpanF0.5 delta was `+0.0010` for `bucket_routed_v0` versus `-0.0102` for
`admission_v3`. Non-zero fallback counts show the current ephemeral handoff does
not yet provide enough measured local-anchor outcomes/features for P30's richer
admission actions. Conclusion: no promotion; extend the handoff with measured
`symbol_regex_union` / `rrf_primary` outcomes and safe route features before
rerunning P30. Remote report:
[`docs/p30-admission-model-v3-remote-smoke.md`](p30-admission-model-v3-remote-smoke.md).

P30-H1 repaired that handoff: P21 now writes ephemeral measured outcomes for
`symbol_regex_union`, `rrf_primary`, `supporting_only`, and `weak_candidate_only`,
and only pre-SCORE safe route features; P30 reports `admission_v3_h1` as the same
scorecard evaluated over enriched handoff records. Six real runs confirmed H1
fixed measurement fallback (`missing_action_outcome_count=0` for H1), but it did
not improve quality. P25 `bucket_routed_v0` remained stronger (`20/37`
gold/false, mean ΔSpanF0.5 `+0.0020`) than `admission_v3_h1` (`18/87`, mean
ΔSpanF0.5 `-0.0350`). The bottleneck moved from missing handoff to scorecard
quality: `symbol_regex_union` admission is too broad and needs stricter
agreement/bucket guards. Report: [`docs/p30-h1-remote-smoke.md`](p30-h1-remote-smoke.md).

P30-H2 tightened local-anchor admission (`symbol_regex_union` requires exact
unique symbol or span agreement; `rrf_primary` requires RRF/anchor span agreement;
file-only agreement is downgraded). Six real runs showed H2 remained
quality-comparable and fallback-free, but did not improve quality: P25
`bucket_routed_v0` was `16/36` gold/false with mean ΔSpanF0.5 `-0.0052`, H1 was
`18/87` with `-0.0346`, and H2 was `15/90` with `-0.0370`. The bottleneck is no
longer only primary admission breadth: weak/supporting/filter actions still carry
span-level false cost. Next P30 work should add action-specific span-cost budgets
and non-primary cost accounting before further route tuning. Report:
[`docs/p30-h2-remote-smoke.md`](p30-h2-remote-smoke.md).

P30-H3 implemented action-specific span-cost accounting as a score-phase-only,
diagnostic follow-on. It does not introduce a new admission route or policy; it
derives per-action cost from existing policies (`bucket_routed_v0`,
`admission_v3_h1`, `admission_v3_h2`, and baseline comparison policies). H3
reports, per action, selected count/rate, added gold/false spans, false/gold and
gold/false ratios, net span value at 1x and 2x weighting, deltas versus baseline,
mean ΔSpanF0.5 and mean ΔPFP, gold-kill rate and false-reduction rate, and
budget-violation flags. Policy-level summaries include primary/non-primary/
unclassified false-span cost, budget violation count/rate/reasons, and worst
actions by false cost and gold kill. The dedicated artifact is
`artifacts/p30_admission_v3/p30_h3_span_cost_report.json` with schema
`p30-h3-action-span-cost-report-v1`, and the doc is
[`docs/p30-h3-span-cost-accounting.md`](p30-h3-span-cost-accounting.md).
`promotion_ready=false`, `default_should_change=false`, `diagnostic_only=true`,
`score_phase_only_accounting=true`.

The first real P30-H3 smoke completed 6 successful runs (108 tasks). Baseline
was `27/102` added gold/false spans; P25 `bucket_routed_v0` remained the
strongest reference at `19/45`; P30-H1 was `18/88`; P30-H2 was `15/90`. H3
shows P30-H1/H2 false-span cost is dominated by primary local-admit actions,
especially `admit_symbol_regex_union` and H2 `admit_rrf_primary`; `supporting_only`
mostly costs recall by killing gold rather than adding false spans. See
[`p30-h3-remote-smoke.md`](p30-h3-remote-smoke.md).

## P31 Candidate Reach Ceiling Study (2026-06-14)

P31 (`eval/p31_candidate_reach_ceiling.py`) is a deterministic, no-remote,
diagnostic-only follow-on that measures how often candidate evidence alone
reaches the gold label before any routing or admission decision. It is
SCORE-phase-only: labels are loaded only after RUN and are used only for
aggregate metrics.

Inputs are the same ephemeral `p25-policy-records-ephemeral-v1` records used by
P25/P30. P31-H1 extends the P21 rich-candidate handoff so ephemeral records now
carry lightweight candidate pools (`p31_candidate_pools`) and private SCORE-phase
gold spans (`p31_score_gold`), marked with
`p31_h1_candidate_reach_handoff=true` and schema
`p31-h1-candidate-reach-handoff-v1`. Pool items keep only `rank`, `path`,
`start_line`, `end_line`, and optional `content_sha`, `score`, and `channels`;
no snippets, raw queries, prompts, responses, or provider fields. When H1 pools
are absent, P31 computes outcome-only fallback metrics and reports
`candidate_pool_availability=missing_candidate_pool` with
`reach_metrics_available=false`, rather than fabricating zeros. When pools and
gold spans are present, it reports `GoldFileReach@K`, `GoldSpanReach@K`,
`GoldSpanExactReach@K`, `CandidateAbsentRate@K`, and
`FileRightSpanWrongRate@K` for K=1/3/5/10/20.

P31-H2 adds the strategy reach matrix: per-strategy reach across
`candidate_baseline`, `rrf_primary`, `symbol_regex_union`, `llm_span_narrow`,
`llm_filter`, and `llm_abstain_filter`. It also reports reach by public repo and
task bucket, unique reach share, pairwise file/span overlap and Jaccard span,
marginal gain in both directions, and union reach for fixed strategy
combinations. A strategy with missing candidate pool is reported as
`availability=missing_pool`, not zero.

Additional aggregate diagnostics: `ModelMissGivenGoldPresent@K` compares
strategies (`llm_span_narrow`, `llm_filter`, `llm_abstain_filter`,
`symbol_regex_union`, `rrf_primary`, `bucket_routed_v0`, `admission_v3` and H1/H2)
against `candidate_baseline`; `FilterKillGoldRate`,
`AdmissionFalsePrimaryRate`, and `AdmissionFalseSpanPerNoGoldTask` are derived
from available per-action/per-strategy outcome fields; `EvidenceCoreRejectRate`
is reported as `not_measured` if no rejection fields exist. A K=5 aggregate
failure funnel is emitted with `funnel_sums_to_positive_tasks=true`.

Public artifacts are aggregate-only: no per-task rows, raw queries, snippets,
prompts, responses, candidate paths/spans, gold spans, private labels, or
provider fields. Safety flags are locked: `promotion_ready=false`,
`default_should_change=false`, `evidencecore_semantics_changed=false`,
`candidate_not_fact=true`, `remote_calls_by_p31=0`,
`score_phase_only_metrics=true`, `aggregate_only_public_artifact=true`. Report:
[`docs/p31-candidate-reach-ceiling.md`](p31-candidate-reach-ceiling.md).


The first real P31-H1 reach smoke completed six successful runs. H1 handoff and
reach metrics were available in all runs. At K=5, candidate baseline reached
`24/48` positive tasks at both file and span level (`0.5000`), with
`FileRightSpanWrongRate@5=0/24`. This indicates candidate absence is the first
bottleneck on this smoke. P25 `bucket_routed_v0` remained the better false-span
reference on the same runs (`20/46` added gold/false) compared with P30-H1
(`18/87`) and P30-H2 (`15/90`). See
[`p31-h1-remote-smoke.md`](p31-h1-remote-smoke.md).

The real P31-H2 strategy reach matrix shows `symbol_regex_union` is the main
candidate-reach lever: at K=5, `candidate_baseline` reaches `24/48` spans,
`rrf_primary` reaches `21/48`, and `symbol_regex_union` reaches `42/48`, with
`18/48` unique span hits. Combining `candidate_baseline` with `rrf_primary` or
`llm_span_narrow` stays at `24/48`; combining with `symbol_regex_union` reaches
`42/48`. This makes P33 anchor repair/calibration the next candidate-generation
priority, while P32/P30-H4 must budget `symbol_regex_union` before primary
admission. See
[`p31-h2-strategy-reach-remote-smoke.md`](p31-h2-strategy-reach-remote-smoke.md).

The first real P33 anchor precision smoke completed six successful runs. It
found no primary-safe observed anchor bucket. The strongest calibration cell
(`a3_r0_s2`: span agreement, low-risk, RRF-span-backed) keeps the P31-H2 reach
ceiling (`42/48` positive spans) but has high false cost (`false_per_gold≈8.69`,
`net_span_value_2x=-786`). `symbol_regex_agree_span` is high-reach but still
costly (`9/9` positive span reach, `false_per_gold=4.0`); `symbol_regex_disagree`
and `regex_only` are worse. See
[`p33-anchor-precision-repair-remote-smoke.md`](p33-anchor-precision-repair-remote-smoke.md).

## P33 Reach-Preserving Precision Anchor Repair (2026-06-14)

P33 (`eval/p33_anchor_precision_repair.py`) is a deterministic, no-remote,
diagnostic-only follow-on to P31. It studies how pre-SCORE anchor signals
(symbol, regex, RRF anchor agreement, query noise, public bucket, risk tags)
correlate with candidate reach and span cost. It consumes the same ephemeral
`p25-policy-records-ephemeral-v1` records as P31, including `p31_candidate_pools`,
`p31_score_gold`, and `route_features`. Labels are loaded only after RUN and
used only for aggregate SCORE-phase metrics.

The anchor taxonomy v1 includes primitive anchor buckets (`exact_unique_symbol`,
`unique_symbol`, `symbol_only`, `regex_only`, `symbol_regex_agree_span/file`,
`symbol_regex_disagree`, `rrf_agree_span/file`, `rrf_unbacked`), public bucket
and tag buckets, query-noise levels, and bounded composites. Each bucket reports
task counts, reach@5, span cost (added gold/false, false/gold, net value),
mean SpanF0.5, mean primary false-positive rate, and a diagnostic class. A 3D
calibration matrix over anchor_strength/risk_level/rrf_backing_level is also
emitted: anchor strength encodes none/symbol_or_regex_only/file_agreement/
span_agreement/exact_unique_symbol_span_agreement; the backing axis encodes none/
file-only/span RRF backing rather than dense/graph support. It includes
monotonic-sanity checks and a `p33_to_p32_handoff` of budget candidates
(`frozen_policy=false`). Missing pools are reported as `availability=missing_pool`
or `not_measured`, not zero.

Public artifacts are aggregate-only: no per-task rows, task IDs, queries,
snippets, prompts, responses, route features, candidate paths/spans, gold spans,
private labels, or provider fields. Safety flags are locked:
`promotion_ready=false`, `default_should_change=false`,
`evidencecore_semantics_changed=false`, `candidate_not_fact=true`,
`remote_calls_by_p33=0`, `score_phase_only_metrics=true`,
`aggregate_only_public_artifact=true`. Report: `docs/p33-anchor-precision-repair.md`.

## P33-B Anchor Subtype Calibration (2026-06-15)

P33-B adds per-candidate anchor subtype metadata to the P21 ephemeral handoff
(`p33b_anchor_subtypes`, schema `p33b-anchor-subtypes-v1`) so we can measure
whether the source class (`symbol_only`, `regex_only`, `symbol_regex_fusion`),
agreement class (`single_source`, `same_file_only`, `span_overlap`, `disagree`),
and RRF-backing status carry different reach/cost profiles inside the
`symbol_regex_union` expansion used by P31-H2. The handoff also carries
`symbol_primary` and `regex_primary` pools for P31 reach studies.

`eval/p33b_anchor_subtype_calibration.py` is deterministic and no-remote. It
joins subtype rows to union candidates in the SCORE phase, reports bounded
subtype-bucket diagnostics (GoldFile/SpanReach@5, FRSW, unique span reach,
span cost with coarse task-level attribution, delta vs candidate_baseline), and
a 3D calibration matrix over source_strength, match_quality, and risk_level with
monotonic sanity checks. Missing subtype handoff causes `availability` to report
the empty/missing reason instead of fake zeros. A `p33b_to_p32_handoff` groups
budget candidates by diagnostic class with `frozen_policy=false`.

Public artifacts are aggregate-only and explicitly forbid per-task rows, task
IDs, candidate paths/spans, subtype rows, route features, labels, and provider
fields. Safety flags are locked: `promotion_ready=false`,
`default_should_change=false`, `evidencecore_semantics_changed=false`,
`candidate_not_fact=true`, `remote_calls_by_p33b=0`,
`score_phase_only_metrics=true`, `aggregate_only_public_artifact=true`.
Report: `docs/p33b-anchor-subtype-calibration.md`.

The real P33-B subtype smoke completed 6 successful runs (108 task observations,
36 positive, 72 no-gold). It confirms that finer subtype splits still do not
produce a primary-safe bucket. `span_overlap` is the best coarse agreement class
(`false_per_gold≈1.78`, `GoldSpanReach=1.0`) but remains net-negative under a 2x
false-span penalty; `symbol_regex_fusion` is high-reach but costs `24/66` added
gold/false; `disagree` and `single_source` are dominated by false-span cost.
These subtype buckets should feed P32/P30-H4 budgets, not primary admission.
See [`p33b-anchor-subtype-remote-smoke.md`](p33b-anchor-subtype-remote-smoke.md).

## P32 / P30-H4 Budget Overlay (2026-06-15)

`eval/p30_admission_model_v3.py` now includes the `admission_v3_h4` policy, a P32/P30-H4 deterministic budget overlay. H4 consumes only RUN-phase public features (`task_bucket`, `task_risk_tags`, `route_features`) and the private P33-B subtype handoff (`p33b_anchor_subtypes`, `p33b_anchor_subtypes_schema`). It uses P33-B conclusions to test budgeted demotion, not primary promotion.

Routing rules are conservative: negative/dense/ambiguous tasks are filtered or abstained; `span_overlap` in low-risk public buckets becomes `supporting_only` when RRF-backed and `weak_candidate_only` otherwise; `same_file_only` becomes `weak_candidate_only` only in clearly positive buckets; `disagree`/`single_source` are filtered unless the public bucket is strongly positive and query noise is low. Exact/unique-symbol signals are treated as budget-diagnostic non-primary. Missing subtype metadata degrades to a `bucket_routed_v0`-like conservative fallback. H4 never selects `admit_symbol_regex_union`, `admit_rrf_primary`, or `admit_llm_span_narrow` from subtype evidence alone.

Private handoff fields are copied into the normalized in-memory task but are never emitted into public P30 artifacts. Report flags are locked: `h4_budget_overlay=true`, `promotion_ready=false`, `default_should_change=false`, and, when P33-B records are present, `h4_available=true` / `p33b_handoff_detected=true`. H4 reports `quality_comparable`, `blocked_by_missing_action_outcomes`, and `selected_action_fallback_rate` like H1/H2, and the real-provider CI gate requires H4 to exist and, on `p21_llm_rich` records, to be quality-comparable with zero selected-action fallback. See [`p32-p30-h4-budget-overlay.md`](p32-p30-h4-budget-overlay.md).

The real P30-H4 remote smoke completed 6 successful runs and showed the all-demotion overlay is too conservative: H4 was quality-comparable and fallback-free but produced `0/0` added gold/false spans and mean SpanF0.5 `0.0000`. P25 `bucket_routed_v0` remained the best reference on the same runs (`27/34` added gold/false, mean SpanF0.5 `0.0768`). H4 should therefore evolve toward budgeted selective re-admission or `request_more_context` variants rather than all-demotion. See [`p32-p30-h4-remote-smoke.md`](p32-p30-h4-remote-smoke.md).

## P32 / P30-H4B Selective Re-Admission (2026-06-15)

`eval/p30_admission_model_v3.py` now includes the `admission_v3_h4b` policy, a P32/P30-H4B selective primary re-admission diagnostic. H4B consumes the same RUN-phase public features and private P33-B subtype handoff as H4, but uses an extremely narrow strict conjunction to test whether a tiny subset of tasks can safely be re-admitted as primary. Almost all tasks are hard-guarded or demoted.

The strict gate allows `admit_symbol_regex_union` only when the best subtype is `symbol_regex_fusion` + `span_overlap` + `rrf_backing`, `local_anchor` and `symbol_regex_agree_span` are true, `query_noise <= 0.1`, the public bucket/tag is in a low-risk positive set, and either `exact_unique_symbol_anchor` or `rrf_anchor_agree_span` holds. If `rrf_backed_by_anchor` and `rrf_anchor_agree_span` also hold, H4B may optionally select `admit_rrf_primary`. All negative/dense/ambiguous/hallucination/high-noise cases, missing handoffs, and best subtypes that are `regex_only`, `same_file_only`, `disagree`, or `single_source` are routed to `apply_llm_filter`, `supporting_only`, or `weak_candidate_only`.

Public outputs include `h4b_available`, `h4b_budget_overlay=true`, `h4b_selective_readmission=true`, `h4b_primary_opportunity_count`, per-policy `rule_counts`, `false_per_gold`, `net_span_value_2x`, a `span_cost_summary`, and H1/H2-style quality comparability. On synthetic self-test H4B is quality-comparable and fallback-free, with a small number of strict primary opportunities. The real H4B smoke validates the selective re-admission direction but does not close the gap to P25: H4B recovers from H4A all-demotion (`0/0 -> 24/41` added gold/false) while P25 remains better (`25/30`, mean SpanF0.5 `0.0683` vs H4B `0.0433`). See [`p32-p30-h4b-selective-readmission.md`](p32-p30-h4b-selective-readmission.md) and [`p32-p30-h4b-remote-smoke.md`](p32-p30-h4b-remote-smoke.md).

## Stage status

| Stage | Status | Summary |
|---|---|---|
| R0 Research Harness | Passed initial gate | EvidenceCore/EvidenceMeta, trace JSONL, citation validation, and smoke eval harness are implemented. |
| R1 Local Evidence Kernel | Passed initial gate | Local read, repo scan, line-based regex/text search, policy basics, path safety, and context-lite file output are implemented without remote dependencies. |
| R2 Retrieval Method Bakeoff | Passed oracle review | BM25 (Tantivy), simple symbol search, and RRF fusion added. BM25 uses line-scoring, stale-hash skip, no-overlap skip. Symbol uses boundary delimiters. RRF merges wider metadata into narrower survivors. Eval harness reports file/line/span metrics and citation validity; Rust CLI validator provides hash/excerpt-backed citation validation. |
| R3 Level0 Storage Scaffold | Passed Level0 conformance | Store traits + StoreHit materialization gate + ConservativeChunkStore + TDB Level0 placeholder. Materialization rejects empty sha / stale / invalid hits, produces citation-valid Evidence from single file read (TOCTOU-safe). |
| R4 Level0 Derived Safety | Passed oracle review | DerivedIndexView model + deterministic rule generator + policy/citation/freshness gates + JSONL store. data_level hard-gated ≤1. Secret-like tokens filtered. High-risk kinds disabled. View IDs include policy_mode/generator_version. Stale mutation detected. JSONL parse errors surfaced. No quality claim. |
| R5 Level0 Graph Scaffold | Passed oracle review | GraphEdge carries source_content_sha/source_language. Materialization via StoreHit → openlocus_store::materialize_evidence (not hand-built). Invalid ranges rejected (not clamped). build_graph validates paths/sha, builds safe_records only. Depth=1 only. Channel::Graph. Citation-valid evidence. Not a precise semantic/call graph. |
| R6 Level0 Fast Context | Passed oracle review | 4-turn deterministic loop (lexical → symbol → graph → RRF fusion). EvidencePack-compatible output with trace_id. ActionRecord per-channel replay. Token budget (chars/4). Unknown channel gate. Final citation validation drops invalid. Orchestration scaffold only, not learned agent. |
| R7 Persistent BM25 Index + Warm SLO | Passed Level0 smoke (after oracle review gates) | Persistent Tantivy index at .openlocus/index/tantivy/ with mandatory manifest at .openlocus/index/manifest.json. schema_version=r7-bm25-v1. Search/open refuse if manifest is missing or policy_hash/schema mismatches. validate_path on every hit before file read. Empty content_sha → skip. Strict range (1≤start≤end≤total_lines, no clamp). build_index filters unsafe paths. PersistentBm25Index keeps the Index/searcher open and is reused by bench warm. Warm open=1ms, query p50=1ms. Bench invalid_citations uses real citation validation (hash/range/excerpt/freshness). 32/32 safety checks passed. Level0 implementation notes only; not a general performance claim. |
| R8 AST Chunking + Symbol Extraction | Passed Level0 smoke (40/40 checks) | Tree-sitter AST-bounded chunking and symbol extraction as experimental opt-in (--chunk-strategy ast). AST symbol Evidence uses Channel::TreeSitter, narrow header spans, current-file verification. Fallback to line windows for unsupported languages/parse errors. Manifest schema r8-bm25-v2 with chunk_strategy and ast_stats. R7 manifests loadable. Line remains default. |
| R9 AST vs Line Quality Bakeoff | Safety checks passed (16/16); quality gate false (FileRecall@5 regression) | eval/ast_quality_bakeoff.py compares persistent BM25 line vs ast on R2 fixture. Latest run: AST improves SpanF0.5@10 (+0.025), FileRecall@1 (+0.143), token_waste (−0.022), wrong_span_rate (−0.087), but regresses FileRecall@5 (−0.071). Citation_validity and structural_validity 1.0 for both. Latency is comparable/noisy in this tiny CLI benchmark. AST remains experimental/opt-in; line remains default. Negative result on gate is valid; fixture is small and self-referential. |
| R10 Incremental Index + Dirty Summary + Synthetic SLO | Passed Level0 smoke (37→48 incremental checks + synthetic SLO) | Dirty summary (dirty_index) computes manifest-vs-current scan: clean, requires_update, requires_rebuild, added/modified/deleted files with counts. Added detection uses ALL manifest paths (indexed+skipped); skipped→nonempty is modified not added. File-level update (update_index) via --dirty or --path: delete-by-term + re-add, commit once, manifest file write uses tmp+rename (not single transaction with Tantivy commit). Safety gates: missing manifest, policy/schema/strategy mismatch → refuse update (load failures also caught). Context-lite writes dirty-summary.json file. eval/incremental_index_smoke.py 48 safety checks. eval/synthetic_slo_bench.py: 1000-file synthetic repo, build_ms, dirty p50, persistent_cli_search p95, one-file update p50 (true modification each iteration), 0 invalid citations. Level0 synthetic only; not a general performance claim. TDB deferred to R11. |
| R11 TDB Level0 Adapter Probe | Passed Level0 smoke (11/11 adapter checks; 29/29 total store tests with --features tdb) | Feature-gated TriviumDB 0.7.0 adapter behind `tdb` Cargo feature. TdbChunkStore opens Database<f32> with dim=1, stores chunk metadata as JSON payloads (schema `tdb_chunk_v1`). Build discipline copies ConservativeChunkStore: validate_path, TOCTOU-safe sha, skip stale/traversal/empty. Capabilities honest: metadata+chunks only, no lexical/vector/graph. Marker-based purge safety. Materialization via StoreHit → materialize_evidence(). Default build unchanged; TDB is NOT a default dependency. Placeholder preserved. Level0 probe only; no retrieval quality claim. |
| R12 Real-Repo Incremental Robustness Bench | Passed hard safety checks (149/149); latency and catastrophic growth guard are report-only | eval/real_repo_incremental_bench.py tests R10 incremental update on temp copy of OpenLocus repo. Per-run unique markers avoid self-contamination. Positive gates require path+marker conjunction in cited excerpt (not disjunction). Branch delete/rename-old markers are proven indexed before removal. Latency compare uses twin repo copies with same mutation. Growth catastrophic guard (max(3×rebuild, rebuild+64MiB)); observed 20-cycle growth ~1.10×; does not prove long-term bounded growth. sys.exit(1) on safety failure only; latency/growth gates report-only. |
| R13 Remote Embedding / LLM-Derived Indexing Safety Scaffold | Passed Level0 safety (45/45 checks) | New crate `openlocus-provider` with EmbeddingProvider trait, MockEmbeddingProvider (deterministic blake3-based vectors, dimensions=32), DisabledEmbeddingProvider. Policy gate: remote denied by default, data_level ≤1 AND ≤metadata.max_data_level, secret scanning blocks SECRET/TOKEN/PASSWORD/API_KEY/sk_/ghp_/AKIA. Dense JSONL store at .openlocus/embeddings/vectors.jsonl stores EmbeddingRecord (vectors present, no raw text). Audit JSONL at .openlocus/audit/embeddings.jsonl (no raw text/vector/query). CLI uses query_sha/query_len (no raw query). Search produces StoreHits → materialize_evidence(Channel::Dense). Short file ranges: end_line=min(total_lines,8). Audit events: query_embed/allow/block/provider_unavailable (not cache_hit). CLI: provider status/audit, dense build/search/purge. 45/45 safety checks. Integration/safety only; not real semantic retrieval. |
| R14 Scaled Evidence Benchmark Foundation | Safety foundation passed (0 critical leakage; fail-closed architecture) | Scaled benchmark program with S/M/L/X tiers. R14-S: 4 logical repo groups from one OpenLocus workspace snapshot, 48 tasks, 48 labels, 47 hard negatives. Fail-closed safety: runner/scorer isolation (run=public tasks only, score=labels only), isolated temp roots per repo group, isolated `.openlocus/policy.toml` from repo lock, unknown repo_id refusal, citation validity must be 1.0 with Rust hash/range validation, runtime canary retrieval, repo lock content manifest re-verification (normalized SHA-256 per file sorted). Span-overlap hard_negative_hit_rate@10 + negative_nonempty_rate@10. eval/r14_generate_dataset.py, eval/r14_benchmark.py (strict RUN/SCORE phases), eval/r14_leakage_check.py (8 static checks, 0 critical), eval/r14_smoke.py (HARD FAIL, no best-effort). R14-S is a safety foundation, not a quality conclusion. R14-M partial. R14-L/X not populated (running --tier L/X fails). Graph precision is future feature track. |
| R15 External Multi-Repo Benchmark Expansion | Safety foundation passed (112/112 smoke checks) | 9 independent external repos across 5 languages, 166 medium tasks, 270 hard negatives. Regex FileRecall@1=0.852, BM25=0.548 on R15-M. BM25 negative_nonempty_rate@10=0.645. Mined benchmark expansion, not quality conclusion. |
| R16 Multi-Method Quality Bakeoff | All safety gates passed across R14-S/R15-M/R15-stress | Cross-matrix bakeoff of regex/bm25/symbol/rrf. RRF wins R15-M recall (0.933/0.993/0.959) but inherits BM25 negative false positives (0.645/0.684). Symbol best span precision (0.310 SpanF0.5, 0.052 hard_neg, 0.000 neg_nonempty). No method promoted to default. Lexical/symbol/RRF only; no provider/dense/LLM claims. |
| R17 Query Intent Router / Negative Guard | All source safety gates passed; citation inherited from validated predictions | Eval-layer router/guard experiment. query_only_router_v0 eliminates R15-M negative_nonempty (0.645→0.000) with acceptable recall regression (FileRecall@1 -0.037). rrf_guarded_by_symbol_regex eliminates R15-M negative_nonempty with zero recall regression. R15-stress negative_nonempty reduces but not eliminated (0.158/0.474). No Rust core changes. No LLM/dense claims. |
| R18 Threshold/Guard Calibration Sweep | All source safety gates passed; citation inherited from validated predictions; baseline consistency checked | Eval-layer calibration sweep over 46 strategies with 8 thresholds. Train-selected `rrf_guarded_by_symbol_regex` preserves RRF recall on R15-M/holdout and drops medium negative_nonempty to 0.000, but remains weak on stress (0.474 vs symbol 0.105). Separate query-noise+agreement strategies reach stress 0.000 as observations, not promotions. Pareto frontier computed. No core changes. No LLM/dense claims. |
| R19 Large/Stress Guard Generalization | All source safety gates passed; citation inherited from validated predictions; baseline consistency checked | Eval-layer generalization validation on R15-L (294 weak/mined tasks) and R15-stress. rrf_guarded_by_symbol_regex generalizes to R15-L (recall preserved, neg_nonempty 0.917→0.042) but fails stress (0.474 vs symbol 0.105). query_noise_plus_rrf_agree_min_0.0 stress-zero observation repeated (0.000). R15-L labels are weak/mined; generalization smoke only, not promotion evidence. promotion_ready=false always. No core changes. No LLM/dense claims. |
| R20 Auto-Wide Retrieval Failure-Surface Benchmark | Static validation passed (14/14 checks, 0 critical errors) | Generated/mined/weak failure-surface dataset for retrieval failure discovery, NOT promotion evidence. 741 tasks across 25 categories and 9 R15 repos. Public tasks contain only task_id/repo_id/query/public_version/source_tier. Private labels carry all judgement fields (query_category, expected_behavior, oracle_type, risk_tags, gold_spans, hard_distractors, must_not_primary, etc.). label_quality: mined_high_confidence/mined/weak only (no human_reviewed). Static validator enforces schema, enum, coverage, anti-leakage, manifest SHA, overlap constraints. No runner/scorer matrix yet. R21 will use it. Dataset + static validator only; no Rust core changes. |
| R21 Auto-Wide Strategy Matrix | 0 critical safety issues; citation_validity=1.0 all 10 strategies; promotion_ready=false | Eval-layer strategy matrix across 10 strategies on R20 auto-wide failure-surface dataset (741 tasks, 9 repos, 25 categories). All strategies have non-zero no_gold_nonempty_rate (0.167-0.495). BM25/RRF are no-gold-heavy (both 0.495). Symbol precision-best but abstains most (0.517). rrf_guarded_by_symbol kills 22.8% recall. query_noise_plus_rrf_agree_min best R21 guard balance (no_gold_nonempty_rate 0.221, FileRecall@1 0.693 preserved). Composite/guard strategies built from base predictions and also Rust citation-validated before cleanup; no labels in RUN. R20 labels weak/mined; not promotion evidence. No Rust core changes. No LLM/dense claims. |
| R22/R27 Failure Attribution | 13 failure clusters computed; 206 bucket regressions; promotion_ready=false | Analysis-only score phase: consumes R21 artifacts + R20 labels, produces failure clusters + expanded metrics. RRF_INHERITED_BM25_FALSE_POSITIVE=110, GUARD_RECALL_KILL=67 (symbol guard), SYMBOL_EXTRACTION_MISS=91, REGEX_NORMALIZATION_BUG=1, BENCHMARK_ORACLE_SUSPECT=62. Unrun strategies (dense/TDB/graph/AST) count=0 with recommended_next_tests. EVIDENCECORE_REJECTION metric_unavailable. 206 bucket regressions; promotion_blocked_by_bucket_regression=true. No retrieval re-run. No Rust core changes. No LLM/dense claims. |
| R23 Guard Parameter Sweep | 51 strategies swept; all blocked by bucket regression; promotion_ready=false | Eval-layer guard parameter sweep consuming R21 artifacts + R20 labels; does NOT change Rust core. 51 strategies across 8 dimensions (query_noise_threshold, rrf_score_threshold, regex/symbol/regex_or_symbol_agreement, top1_top2_gap_threshold, identifier_density_threshold, candidate_channel_count_threshold) plus 15 combined strategies. R21 artifacts manifest is verified fail-closed for every recorded path, sha256, byte count, and JSONL line count. All 51 strategies have bucket regressions. Combined query_noise_1+regex_or_symbol_agree is best R23 guard balance (no_gold_nonempty_rate 0.221 vs RRF 0.495, FileRecall@1 0.693 preserved, zero guard_recall_kill). Agreement guards reduce false positives without recall cost (0.279 no_gold_nonempty at zero kill). RRF score threshold >0.02 causes sharp recall cliff. Gap threshold kills too much recall even at 0.005. No strategy eliminates false positives without unacceptable recall loss. Curves: risk_coverage, recall_vs_negative, recall_vs_false_primary, precision_vs_abstain. 6877 total bucket regressions. promotion_ready=false. not_promotion_evidence=true. No LLM/dense claims. |
| R24 QuIVer/TDB/Dense Probe | Availability + mock dense candidate-channel probe; quiver_implemented=false; promotion_ready=false | NOT a QuIVer bakeoff. QuIVer is not implemented (scan confirms no impl in Rust crates; quiver_implemented=false). TDB is a feature-gated metadata/chunk store placeholder (available=false in default build). Dense mock is available as candidate-channel safety/quality-smoke (not semantic quality). Dense real is unavailable. R24 runs dense mock build/search on R20 auto-wide tasks in isolated repo roots, preserves embeddings/audit between build/search, validates citations fail-closed, and scores against R20 labels. Dense mock produced 5,264 citation-valid candidates but poor/noisy behavior (FileRecall@1 0.024, MRR 0.073, primary_false_positive_rate 0.878) plus 99 explicit candidate rejections. Canary hardening is non-vacuous: 8 non-empty dense stores checked, path/query canaries returned evidence, raw canary/query leakage=0. dense_mock_plus_rrf confirms dense contribution but increases noise (primary_false_positive_rate 0.923, hard_distractor_hit_rate 0.215). QuIVer diagnostic fields report unavailable/not_measured with reason quiver_not_implemented; no numeric 0 output as quality result. tdb_stale_leak_count is not_applicable. No Rust core changes. No LLM/dense real/QuIVer quality claims. remote_calls=0. |
| R25 Graph+Dense Ablation | Net-negative for both graph_basic and dense_mock; default expansion blocked; promotion_ready=false | Eval-layer ablation of graph_basic and dense_mock on R20 auto-wide (741 tasks). graph_basic: net-negative (0 gold, 435 false spans → blocked). dense_mock: net-negative (2 gold, 20,273 false → blocked). rrf_plus_graph dilutes RRF (FileRecall@1 0.693→0.497). rrf_plus_dense_mock also dilutes (0.693→0.134). graph_pollution_ratio=0.0. Citation validity remains 1.0: graph/dense/composites are revalidated in R25; no_graph inherits R21 validation after R25 verifies the R21 artifact manifest before baseline use. R25 source-leak canary is regex-only with seeded self-test, not a dense-path canary. QuIVer/TDB unavailable/not_measured. No Rust core changes. No LLM/dense real/QuIVer quality claims. remote_calls=0. |
| R26 Auto-Stress-1000 | Static validation passed (19/19 checks, 0 critical errors); NOT promotion evidence | Weak/mined/deterministic stress dataset for retrieval failure discovery. 1100 tasks across exact target counts for 10 stress categories and 9 R20 repos. Uses the same external repo set as R20 and derives some queries from existing R20 tasks/labels where useful. Public tasks contain only test_id/repo_id/query/public_version/source; category/risk/judgement fields live only in private labels. Private labels carry all judgement fields. No canary tokens. Deterministic seed 42. Validator fail-closes on exact category counts, public/private schema separation, task/label query consistency, span path/range validity, SHA-256 artifact checks, and repo content manifest SHA lock recomputation. Runner/scorer matrix now provided by R29. Designed to maximize failure discovery; NOT promotion evidence. Negative/abstain cases dominate (60%). No Rust core changes. No LLM/dense claims. |
| R28 Promotion Candidate Report | promotion_ready=false; current default should not change | Conservative synthesis of R21/R23/R24/R25/R26 reports over the R20/R26 failure-surface datasets. RRF remains best recall channel, symbol remains precision anchor, query_noise_plus_rrf_agree_min is promising but not stable enough due to R23 bucket regressions and unrun R26 retrieval matrix, graph/dense expansions are blocked by R25 added_false_span > added_gold_span, QuIVer/TDB have no independent quality evidence, dense_mock is noise/safety probe only. Default recommendation: no_change_current_evidence_gated_local_retrieval. Next required tests: run R26 strategy matrix, add human-verified labels, implement real embedding/QuIVer only after runner gates exist. |
| R29 R26 Auto-Stress Strategy Matrix | promotion_ready=false; not_promotion_evidence=true; failure-surface only | Eval-layer strategy matrix across 16 strategies (4 base + 6 composite/guard + 6 graph/dense/composite) on R26 auto-stress (1100 tasks, 10 stress categories, 9 repos). Strict RUN/SCORE separation: run phase loads only public tasks + repo lock, never labels; score phase loads labels only. R26 provenance validated before run. Citation validity must be 1.0 for all strategies. 14 required failure clusters computed. Span contribution analysis for graph/dense/composites vs fresh RRF baseline. Bucket regressions across source_category/expected_behavior/oracle_type/repo_id/risk_tags. Private field scan on all JSONL artifacts. 5 unavailable strategies report reason only (no fake numeric quality). dense_mock is candidate-channel safety smoke, not semantic quality. QuIVer not implemented. No Rust core changes. No LLM/dense real/QuIVer quality claims. remote_calls=0. |
| R30 Baseline Freeze | Completed; no promotion | Frozen R29/R26 stress matrix as the comparison baseline. When raw R29 runtime artifacts were absent from checkout, R30 explicitly used committed R29 docs/manifests and recorded missing artifact status rather than fabricating original predictions. Subsequent experiments report `delta_vs_r29_*` fields against this frozen baseline. |
| R31 Real Embedding Provider Smoke | Completed; safety gates first | Implemented OpenAI-compatible real embedding provider plumbing, remote-default-deny gates, audit/no-raw-text policy, provider request headers, optional `dimensions` field support, and local mock plus real-provider smoke. Real provider access was validated, but R31 made no quality claim. |
| R32 Embedding View Bakeoff Harness | Completed; supporting-only | Added view bakeoff harness for multiple embedding views with RUN/SCORE separation. Default is local/mock; real remote runs are explicit/manual and currently remote-safe `path_plus_symbol` only. Reports FileRecall, SpanF0.5, PFP, citation validity, provider calls, and `delta_vs_r29_baseline`. Dense output remains candidate/supporting-only. |
| R33 QuIVer Readiness Diagnostics | Completed; diagnostic-only | Added BQ2/sign-magnitude diagnostics over real embeddings: BQ overlap, BQ-vs-f32 MRR, sign entropy, angular gap, centroid/shard variance. QuIVer graph/Vamana is still not implemented; R33 emits diagnostic evidence only, no ANN quality claim. |
| R34-R36 QuIVer/BQ + Anchor Prototype | Completed; no default expansion | Added offline/real-provider prototype comparisons: flat f32, BQ top-k + f32 rerank, source/test split, per-view/language ideas, and regex/symbol anchor variants. Early tiny results were optimistic, but public corpus and L1 slice runs showed added_false often exceeds added_gold. QuIVer/dense remain supporting-only. |
| R37-R38 LLM-Derived Views + Stress | Completed; not Evidence | Real LLM provider smoke succeeded. LLM output is used only for derived views/stress/failure discovery with `not_evidence=true`; it does not generate Evidence, gold labels, citation verdicts, or promotion verdicts. Private labels are not uploaded in CI. |
| R39-R40 Symbol/Regex Repair Bakeoff | Completed; needs larger validation | Offline repair bakeoff showed `regex_hybrid_normalized` and symbol extraction repair are promising recall-safe directions. They still need fixed-suite validation for bucket regressions before any default-path consideration. |
| R41-R42 Graph Role + Admission v2 | Completed; research-only | Reframed graph as supporting/rerank/explainer, not default expansion. Added admission_v2 rule research with actions like admit_primary/admit_supporting/weak_candidate/abstain, but no learned/default admission change. |
| R43-R45 Integrated Long-Run Report | Completed; promotion_ready=false | Consolidated R30-R42 outputs into real-model matrix summary, failure clusters, and promotion candidate report. Conclusion: RRF recall base, symbol precision anchor, query-noise guard best current candidate, dense/QuIVer/LLM-derived/graph all non-default. |
| P1-P7 Real Provider Bring-up | Completed; real providers usable | Ran real embedding and LLM smoke locally/CI with gitignored `.env.local` and GitHub `production` environment. SiliconFlow embedding and OpenAI-compatible LLM access were validated. P2/P3/P4/P5/P6/P7 produced first real-provider summaries; no provider URL/key committed. |
| P8/P9 Real-Provider CI Scale-Up | Completed; first public CI slices | Added `real-provider-benchmark.yml` manual workflow with `environment: production`, guarded secrets, input validation, and no private label upload. Ran small public corpus, model bakeoff (`bge-m3`, Qwen 0.6B/4B/8B), and multilingual smoke. Result: file-level signal exists, but SpanF0.5 remains low and model size did not dominate in first slices. |
| L1/L2 Real-Provider Large-Repo Slices | Completed; strong dense-only/global-dense block | Ran controlled large-repo slices across Django, Kubernetes, Next.js, and Deno. L1 showed file-recall variability and P4 false-span growth. L2 (`60 tasks / 1000 records / 2000 files`) had PFP=1.0 on all four repos, very low SpanF0.5, and unstable FileRecall. Conclusion: dense-only/global dense must remain supporting/candidate-only; next phase should freeze L2, attribute false positives, and test constrained dense. |
| P10-P14 Constrained Dense Research | Planned | Proposed next phase: freeze `real_provider_l2_v1`, attribute L2 false positives, simulate constrained candidate pools locally, run small remote constrained variants, then rerun fixed L2 only if added_gold exceeds added_false and PFP drops. No EvidenceCore changes and no promotion. |
| P20-LS LLM Large-Scale Eval Harness | P20-LS-A completed; low-context alias blocked | Bounded eval-only harness (`eval/p20_llm_large_scale.py`) for LLM-derived query aliases and stress-label generation. Remote runs require `workflow_dispatch + enable_remote_models=true + OPENLOCUS_ALLOW_REMOTE=1`. P20-LS-A ran `Kimi-K2.7-Code` on self-test plus 9 real CI corpus runs (220 real provider calls). All LS0/LS1 safety gates passed, no raw source/private labels/prompts uploaded, but 0/9 real runs passed quality: added_gold_span=289 vs added_false_span=8312 (~28.8:1 false:gold), avg fabricated_identifier_rate≈0.459. Narrow decision: stop scaling low-context/query-only LLM aliases. This is not a verdict on rich-context LLM retrieval; it motivates context-grounded rerank/filter/span-narrow experiments. No EvidenceCore changes; promotion_ready=false; default_should_change=false. |
| P21-G Cross-Model Context Injection Research | P21-G3L-R GLM tool_call confirmed under low concurrency | Research pivot from minimal-context baselines to cross-model context-injection effects. P21-G1E found rich embedding views have file/span signal but naked dense false spans dominate. P21-G2E found constrained dense (`dense_atom_signature_rrf_file_constrained`) has modest supporting value but dense remains non-primary. P21-G3L found LLM span narrowing has promising but model/repo-specific signal; filter/abstain often kill gold. P21-G3L-R added provider-level output modes (`prompt_only`, `json_object`, `json_schema_strict`, `tool_call`), fallback diagnostics, and one no-fallback schema repair retry. GLM 4-mode comparison found `tool_call` best (avg SpanNarrow Δ +0.0677), `prompt_only` blocked, `json_object` insufficient, `json_schema_strict` mixed. A sequential low-concurrency `tool_call` rerun removed 429 noise and improved GLM SpanNarrow avg Δ to +0.1361 across py_flask/js_express. Next: bucketed GLM/Kimi/Flash `span_narrow` with `tool_call` for GLM; filter/abstain remain non-default. EvidenceCore remains final authority. |
| P21-G3B Bucketed LLM Role Study | Bucketed smoke completed; global LLM roles blocked | Public task generation now exposes safe `task_bucket/task_risk_tags` and P21 runners support `round_robin_public_buckets`, so RUN can sample mixed buckets without labels/gold. First true bucketed LLM role smoke ran 6 runs (Flash/Kimi/GLM × py_flask/js_express, 18 tasks each, provider concurrency ≤6). Bucket coverage now includes abstain/weak/no_gold/ambiguous/dense_false_positive buckets. Result: all LLM roles reduce PFP materially, but often by killing gold spans; global `span_narrow` is positive on py_flask but negative on js_express mixed buckets; `filter`/`abstain` are useful as false-positive reducers only in specific buckets, not as defaults. Next: build a rule-based policy that routes `span_narrow` only to likely-positive/high-confidence tasks and `filter/abstain` only to negative/dense_false_positive/ambiguous buckets. |
| P22/P23 Evidence-Seeking Policy Surface | Decision surfaces frozen; bottlenecks decomposed | P22/P23 moves from channel bakeoffs to strategy-surface analysis. It freezes two capped local surfaces with hashes and no remote/model calls: `r20_positive` (120 positive tasks across 9 repos) and `r26_guard` (120 no-gold stress tasks across 9 repos). R20 shows RRF is still the reach base (`Reach@5=0.975`, `SpanReach@5=0.95`) but symbol has best local SpanF0.5 (`0.3169`) and `symbol_regex_union` is the best precision/reach experimental baseline candidate for P25/P30. R26 shows BM25/RRF create noisy false primary (`NoGoldFP=0.2833`) while symbol/regex/union/guard abstain, so guard stress must be evaluated separately from positive reach. Reports: `docs/p22-p23-policy-surface.md`, per-surface docs/artifacts under `docs/` and `artifacts/p22_p23/`. |
| P25 Bucket-Routed LLM Role Policy evaluator | Self-test scaffold ready; real evaluation requires ephemeral P21/P25 handoff | `eval/p25_bucket_policy.py` is deterministic and no-remote. It routes by public `task_bucket`/`task_risk_tags` and compares candidate_baseline, global span/filter/abstain, and bucket_routed_v0. Aggregate summaries/non-ephemeral schemas are rejected. First real smoke reduced false spans but also some gold spans; useful as P30 false-primary reducer, not default. Report: `docs/p25-bucket-routed-policy.md`. |
| P30 Admission Model V3 | Self-test scaffold ready; real evaluation requires ephemeral P21/P25 handoff | `eval/p30_admission_model_v3.py` is deterministic, explainable, no-remote. Routes only from public task_bucket/task_risk_tags/route_features; allowed actions are abstain/admit_symbol_regex_union/admit_rrf_primary/admit_llm_span_narrow/apply_llm_filter/supporting_only/weak_candidate_only. Compares baselines plus admission_v3, reports score bands/selective_risk/deltas, and recursively scans public output for forbidden keys. Not promotion-ready; next step compare to P25 real smoke and P22/P23 guards. Report: `docs/p30-admission-model-v3.md`. |
| P31 Candidate Reach Ceiling Study | Scaffold ready; diagnostic-only, SCORE-phase-only | `eval/p31_candidate_reach_ceiling.py` measures whether candidate evidence alone reaches the gold label at K=1/3/5/10/20 before any routing or admission. It is deterministic, no-remote, and aggregate-only: no per-task rows, raw queries, snippets, prompts, responses, gold spans, private labels, or provider fields. Inputs are ephemeral P25/P30 records; records without candidate evidence pools fall back to outcome-only metrics with `candidate_pool_availability=missing_candidate_pool` and `reach_metrics_available=false`. Reports `GoldFileReach@K`, `GoldSpanReach@K`, `GoldSpanExactReach@K`, `CandidateAbsentRate@K`, `FileRightSpanWrongRate@K`, `ModelMissGivenGoldPresent@K`, `FilterKillGoldRate`, `AdmissionFalsePrimaryRate`, `AdmissionFalseSpanPerNoGoldTask`, and a K=5 failure funnel. `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `candidate_not_fact=true`, `remote_calls_by_p31=0`. Report: `docs/p31-candidate-reach-ceiling.md`. |
| P33 Reach-Preserving Precision Anchor Anchor Repair | Scaffold ready; diagnostic-only, SCORE-phase-only | `eval/p33_anchor_precision_repair.py` studies how pre-SCORE anchor signals correlate with reach and span cost. It consumes ephemeral P21/P31-H1 records and aggregates an anchor taxonomy v1, a 3D calibration matrix, and budget-candidate handoff to P32. Public output is aggregate-only, no per-task rows, route features, or private fields. `promotion_ready=false`, `default_should_change=false`, `candidate_not_fact=true`, `remote_calls_by_p33=0`. Report: `docs/p33-anchor-precision-repair.md`. |
| P33-B Anchor Subtype Calibration | Scaffold ready; diagnostic-only, SCORE-phase-only | `eval/p33b_anchor_subtype_calibration.py` consumes the P21/P31-H1 ephemeral handoff extended with per-candidate `p33b_anchor_subtypes` for `symbol_only`/`regex_only`/`symbol_regex_fusion` source classes, agreement classes, rank/size/width bins, and per-candidate `rrf_backing`. It reports subtype-bucket diagnostics, unique subtype span reach, a 3D calibration matrix over source strength / match quality / risk level, and a `p33b_to_p32_handoff` of budget candidates. Public output is aggregate-only, no subtype rows, candidate paths/spans, or private fields. `promotion_ready=false`, `default_should_change=false`, `remote_calls_by_p33b=0`. Report: `docs/p33b-anchor-subtype-calibration.md`. |
| P58 Source-Backed Verifier Calibration | Self-test scaffold ready; aggregate-only planning hints | `eval/p58_source_backed_verifier_calibration.py` is deterministic, no-remote, and consumes only aggregate upstream JSON (P48, P52C, P51B, P57, optional P52B/P52A/P49). It emits coarse planning/action-hint buckets (`request_more_context`, `local_verifier_priority`, `p51c_eligibility`) and is not a verifier, admission, Evidence, or default/promotion/live-readiness signal. `promotion_ready=false`, `default_should_change=false`, `candidate_not_fact=true`, `remote_calls_by_p58=0`. Report: `docs/p58-source-backed-verifier-calibration.md`. |

## R0/R1 initial findings

- Evidence precision matters immediately: the first regex implementation returned over-wide line ranges for distant matches in one file. This would have harmed token waste and Span F0.5. The fix moved R1 regex/text search to one narrow Evidence per matching line.
- Citation validation must validate more than hashes. Range validity and excerpt consistency are needed to catch incorrect spans.
- Path safety is part of evidence safety. Symlink escape protection is required before treating read output as verified current evidence.
- The current local baseline is intentionally boring: no dense, graph, TDB, or LLM indexing has been added yet. This keeps R0/R1 suitable as the control group for later bakeoffs.

## R2 findings

- **BM25 substantially improves file-level recall on the current self-referential fixture**: 0.39 vs 0.21 at k=1, 0.86 vs 0.36 at k=5.
- **Symbol search is high-precision but narrow**: only activates for definition-style queries, but when it fires, line precision is the highest of all methods (0.39) and wrong_span_rate is 0.0.
- **RRF fusion approaches BM25-level recall** while incorporating symbol precision, achieving 0.82 FileRecall@5 and 0.057 SpanF0.5@10 on the current fixture.
- **All methods produce structurally citation-valid evidence in the Python scorer**; aggregated current R2 output was also validated by the Rust CLI citation validator with `0` invalid citations (hash/range/excerpt checked).
- **Token waste is high** (~0.92) because evidence spans are often near-but-not-on narrow gold spans.
- **CLI end-to-end latency** (not warm-index): regex ~13ms, BM25 ~113ms, symbol ~161ms, RRF ~272ms.

## R3 findings

- **Materialization gate is essential and works**: empty sha rejected, stale hits rejected, invalid ranges rejected, TOCTOU-safe (sha + excerpt from same bytes), produced Evidence is citation-valid.
- **TOCTOU safety matters**: reading file bytes once and deriving both sha and excerpt from that single read prevents a modification between reads from producing inconsistent evidence.
- **ConservativeChunkStore validates paths and skips bad records**: traversal paths rejected, stale content_sha skipped, empty files produce no invalid chunks.
- **TDB placeholder provides clean Level0 surface**: returns available=false, success=false with descriptive errors, never panics.
- **This is a Level0 storage scaffold**, not a full storage bakeoff or TDB comparison.

## R4 findings

- **Safety scaffold works**: all gates are functional and block by default. High-risk kinds blocked, data_level hard-gated at ≤1 for Level0, experimental opt-in required, no remote calls.
- **Deterministic view IDs include policy_mode and generator_version**: same source/kind/generator/data_level/policy_mode/generator_version always produces the same ID; change in any produces different ID.
- **No raw full code at data_level ≤ 1**: derived text contains only metadata (line range, language, first identifier). Prevents accidental exposure in derived artifacts.
- **Secret-like tokens are aggressively filtered**: identifiers containing SECRET/TOKEN/PASSWORD/API_KEY/PRIVATE_KEY, or with prefixes sk_/ghp_/AKIA, or long high-entropy mixed strings are not emitted in tags or aliases.
- **JSONL parse errors are surfaced** (not silently skipped): `derived validate` reports parse_errors count.
- **Stale mutation is detected**: building views, modifying a source file, then validating correctly reports stale views.
- **DerivedIndexView is NOT Evidence**: cannot bypass StoreHit/materialize_evidence gate. Any future derived search must materialize source evidence.
- **This is a Level0 safety scaffold only. No quality claim about derived view relevance or usefulness.**

## R5 findings

- **StoreHit materialization gate is essential**: graph edges are converted to StoreHit and delegated to `openlocus_store::materialize_evidence()`. This ensures consistency with all other materialization paths and prevents hand-built Evidence from bypassing validation.
- **GraphEdge carries build-time sha and language**: source_content_sha and source_language allow the materializer to detect stale edges and reject invalid ranges (not clamp them).
- **build_graph validates paths and current sha**: safe_records with validated path and current sha are used for all edge builders (imports, tests, configures). Stale and path-unsafe records are counted and skipped, producing no edges.
- **Simple line-based import parsing works for Rust/Python repos**: mod/use, import/from lines are easy to parse and resolve against the path_set.
- **Config edges are noisy but bounded**: Cargo.toml/package.json link broadly to nearby source files in the fixture. This favors recall but can create many false positives; no general precision/recall claim is made.
- **Depth=1 only; depth>1 returns clear error**: not silently expanded.
- **graph inspect wraps output with artifact marker**: `artifact="graph_edges_not_evidence"` makes it clear these are not citation-valid Evidence.
- **This is a Level0 deterministic scaffold only. Not a precise call graph, type graph, or dependency graph.**

## R6 findings

- **4-turn deterministic loop works as orchestration scaffold**: lexical → symbol → graph → RRF fusion produces multi-channel evidence without any LLM planner.
- **Symbol turn is conditionally activated**: skipped when query lacks identifier-like tokens, avoiding wasted computation.
- **Token budget enforced**: `--budget N` uses chars/4 approximation; evidence trimmed from bottom if cumulative tokens exceed budget. `--max-evidence` is separate count cap.
- **Unknown channel gate**: channels outside regex/text/bm25/symbol/graph are rejected with clear error.
- **Final citation validation**: evidence filtered through `is_citation_valid` before output; invalid dropped and counted in `diagnostics.invalid_citations_dropped`.
- **EvidencePack-compatible output**: `pack` field with trace_id, budget_used. `evidence` field preserved for direct access.
- **ActionRecord per-channel replay**: each turn/channel recorded with query, result_count, latency_ms, optional error. Written to `.openlocus/traces/fast-context-<trace_id>.json`.
- **Confidence derived from top RRF score**: low confidence (<0.1) triggers a missing_question.
- **Orchestration scaffold only, not learned agent.** No adaptive re-querying, no feedback loops, no LLM planning.

## R7 findings

- **Persistent Tantivy BM25 index with manifest works**: build creates .openlocus/index/tantivy/ + .openlocus/index/manifest.json. status/validate/search/purge CLI commands all functional.
- **Manifest and policy gates enforced**: search_persistent_bm25 and PersistentBm25Index::open require the manifest and check manifest policy_hash/schema against current Policy/schema; refuse search if manifest is missing or mismatched. validate_index reports policy_hash_matches=false. Eval confirms: policy change after build → search refuses, validate detects mismatch; manifest deletion → search refuses.
- **Stale/deleted hits are skipped, not emitted**: search_persistent_bm25 re-reads every hit's current file, computes content_sha, and skips mismatches. No stale VerifiedCurrent evidence is ever produced.
- **Empty content_sha bypass prevented**: Hits with empty index_content_sha are skipped (invalid_hits_skipped++), cannot bypass stale check.
- **validate_path on every Tantivy hit**: Before reading a file from a Tantivy hit's path, validate_path is called. Invalid paths → skip. build_index also filters unsafe FileRecord paths.
- **Strict range validation, no clamping**: Chunk ranges must satisfy 1 ≤ start ≤ end ≤ total_lines. Invalid ranges → skip (invalid_hits_skipped++), not clamped.
- **Manifest enables fast staleness detection**: status_index quickly checks all indexed files' current sha against manifest entries. validate_index reports specific stale/deleted/path_unsafe files.
- **Policy exclusion works end-to-end**: .env and *.pem files are excluded by scan_repo, never indexed, and never appear in persistent search output.
- **Warm benchmark is honest**: PersistentBm25Index::open opens the Index/searcher once; same handle reused for all queries with no per-query Index::open. index_open_ms measures open cost only (1ms). index_build_ms reported separately if build was needed. invalid_citations uses real citation validation (hash/range/excerpt/freshness check), not just range.
- **Warm query latency**: On the current small self-referential workspace snapshot, warm queries take 1-2ms per query after index is opened. Open cost is 1ms.
- **Safety is preserved**: Every persistent search hit is re-verified against the current filesystem. The Tantivy stored body is never used as the final excerpt.
- **Purge is safe**: Only deletes known R7 artifact paths under .openlocus/index/. Canonicalizes paths and refuses to delete if index_dir escapes repo root.
- **This is a Level0 implementation only. No incremental update; build is always full rebuild. Warm SLO numbers are from a small self-referential codebase; not a general performance claim. R7 Level0 passed only after oracle review gates.**

## R8 findings

- **Tree-sitter AST-bounded chunking is functional as an experimental scaffold**: `openlocus-ast` crate parses Rust, Python, JavaScript, and TypeScript using Tree-sitter 0.25.x. AST chunk boundaries align with logical code structures (functions, classes, structs, etc.) rather than arbitrary line windows. Oversized nodes are split into line windows; gaps are covered by fallback line windows; no overlapping chunks.
- **AST symbol extraction produces narrow, citation-valid Evidence**: `extract_ast_symbols` extracts definition nodes with header/signature spans (max 10 lines, usually signature/header only rather than full bodies). Symbol names are extracted from Tree-sitter node fields. AST symbol Evidence uses Channel::TreeSitter and is verified against the current filesystem (hash/excerpt/freshness).
- **Fallback is correct**: Unsupported languages (e.g., Go) fall back to line-window chunking. Parse errors also fall back to line windows. No data loss. Fallback stats are visible in manifest ast_stats.
- **Opt-in, not default**: `--chunk-strategy ast` is experimental; line-window remains the default. No quality claim about AST chunking superiority until eval computes it.
- **Manifest schema r8-bm25-v2**: Includes chunk_strategy and ast_stats fields. R7 manifests (r7-bm25-v1) still loadable with default chunk_strategy=line_window_v1. Unrecognized schema versions refuse with rebuild instruction.
- **Schema/strategy mismatch refusal**: search/validate/status refuse if manifest chunk_strategy is unrecognized. R7 manifests without chunk_strategy are loaded as line_window_v1 for compatibility; R8-written manifests always include chunk_strategy. No silent search of unverifiable strategy.
- **CLI symbol search modes**: `openlocus search symbol <name> --mode regex|ast|auto`. Default auto: AST first for supported files, regex fallback for unsupported/no results. Regex mode preserves existing behavior.
- **R7 persistent smoke still passes**: Default line build continues to work with all 32 safety checks passing.
- **AST smoke eval passes 40/40 checks**: Including AST build/status/validate/search, parser-error visibility, stale mutation, narrow AST symbol header, symbol search modes, citation validation, schema mismatch, policy exclusion, default line build compatibility.
- **This is a Level0 experimental scaffold. AST chunking quality lift is NOT proven. Tree-sitter parser edge cases may exist. AST symbol extraction does not handle all symbol patterns (re-exports, aliased imports). No incremental update for AST index.**

## R9 findings

- **AST vs line persistent BM25 bakeoff completed on R2 fixture (28 tasks)**: `eval/ast_quality_bakeoff.py` runs both strategies through purge/build/search/score and produces a combined report with delta, quality gate, and safety checks.
- **AST improves SpanF0.5@10 (+0.025, latest run ~63% relative)** and FileRecall@1 (+0.143, 36% relative): AST-bounded chunks align better with logical code structures, producing more targeted evidence spans and better top-1 file retrieval.
- **AST regresses FileRecall@5 (−0.071 in the latest run)**: More granular AST chunks can dilute BM25 scores across multiple chunks per file, reducing the chance that any single chunk ranks a file into top-5. This is the quality gate failure.
- **AST reduces token waste (−0.022) and wrong_span_rate (−0.087 in the latest run)**: Narrower evidence spans waste fewer tokens and overlap gold spans more often.
- **Quality gate is false** (FileRecall@5 regression). **Safety checks all pass** (16/16). Citation_validity and structural_validity are 1.0 for both strategies.
- **Latency is comparable** (ratio ~1.0). Both strategies have similar per-query latency on this fixture.
- **AST remains experimental/opt-in; line remains default.** The fixture is too small and self-referential to generalise. A larger, diverse codebase eval would be needed for a definitive quality comparison.
- **Negative result is valid**: the bakeoff correctly captures a real trade-off between span precision (AST better) and broad file recall at k>1 (line more conservative).

## R10 findings

- **Incremental update works correctly**: dirty_index detects added/modified/deleted files; update_index applies batch changes (delete-by-term + re-add + commit + manifest file write via tmp+rename). Post-update status shows clean. 48/48 incremental smoke checks passed.
- **Dirty summary is accurate and safe**: distinguishes requires_update (file changes) from requires_rebuild (policy/schema/strategy mismatch or corrupt manifest). Policy-excluded added files do not dirty. Skipped entries (empty files, read errors) with unchanged sha are clean; skipped→nonempty is reported as modified (not added). Status never says clean if validate would fail.
- **Safety gates enforced on update**: missing manifest, policy hash mismatch, schema mismatch, and unrecognized chunk strategy all refuse update with clear error messages requiring rebuild. Manifest load failures are also caught gracefully.
- **Tantivy delete-by-term prevents duplicate docs**: `Term::from_field_text(path_field, path)` correctly removes all chunks for a path before re-adding. Deletes are tombstones until merge (documented, not a bug).
- **Context-lite dirty summary written to file**: R10 writes actual dirty index status to `.openlocus/context/dirty-summary.json`. The `ContextLitePack.dirty_summary` struct field remains `None` (the file is the surface, not the struct field).
- **Synthetic SLO benchmark (1000 files)**: latest run build_ms=147, dirty_status p50≈44ms/p95≈48ms, persistent_cli_search p95≈15ms, bench_warm open-once query p95=0ms, one-file update p50≈115ms/p95≈117ms (true modification each iteration), 0 invalid citations. Level0 synthetic only; not a general performance claim. `persistent_cli_search` is CLI-measured; `bench_warm` is the Rust CLI's internal open-once query timing over a synthetic dataset.
- **TDB deferred to R11**: R10 focused on incremental index; TDB moves to R11.
- **Not a single transaction**: Tantivy commit and manifest file write are separate; a crash between may leave a safe but inconsistent state requiring rebuild or re-update.

## R11 findings

- **TriviumDB 0.7.0 compiles and works as an optional dependency**: Feature-gated behind `tdb = ["dep:triviumdb"]`. Default build does not compile TDB. `cargo test --workspace` passes without TDB. `cargo test -p openlocus-store --features tdb` passes with 29/29 tests.
- **TdbChunkStore is a Level0 adapter probe**: Opens `Database<f32>` with `dim=1`, stores chunk metadata as JSON payloads (schema `tdb_chunk_v1`). The `[0.0]` vector is a smoke probe, NOT vector quality. Capabilities honestly report metadata+chunks only, no lexical/vector/graph.
- **Build discipline preserved**: validate_path, TOCTOU-safe sha, skip stale/traversal/empty — same as ConservativeChunkStore.
- **Marker-based purge safety**: Adapter writes an `.openlocus_marker` file; purge verifies marker before deletion and refuses without it.
- **Materialization conformance enforced**: TDB chunk records → StoreHit → materialize_evidence(). Stale, empty-sha, and invalid-range hits correctly rejected.
- **No default dependency on TDB**: TDB is NOT a default backend. It does not replace Tantivy persistent BM25 or the conservative store. Placeholder preserved.
- **No retrieval quality claim**: This is a Level0 wiring/persistence probe. No comparison against Tantivy BM25 or conservative store quality.

## R12 findings

- **Real-repo incremental update passes this Level0 sample**: On a temp copy of the OpenLocus repository (mixed Rust, Python, TypeScript, Markdown), incremental update correctly handles sampled modify, add, delete, rename, policy-excluded, and batch workloads. No stale VerifiedCurrent evidence produced.
- **All hard safety checks pass**: 149/149 hard safety checks pass (dirty detection, update success, clean after update, validate valid, collected marker-search citations invalid_count=0, no stale VerifiedCurrent for deleted/old paths).
- **Per-run unique markers avoid self-contamination**: Fixed markers appeared in copied docs/scripts causing false positives. Per-run suffixes (8-hex chars) and pre-build assert prevent this.
- **Positive gates use path+marker conjunction**: `evidence_has_path_and_marker` requires both path fragment AND marker in the cited excerpt of the same evidence item. Previous disjunction (path OR marker) could pass from unrelated evidence.
- **Citation validity maintained for collected marker-search evidence**: total_invalid_citations=0 across all workloads. Collected evidence validated through `openlocus citations validate` with validator returncode==0.
- **Latency comparison uses twin repo copies**: Both update and rebuild start from same state with same mutation applied. Incremental update ~42% faster on this sample. Gate is report-only; does not cause exit failure.
- **Growth is a catastrophic guard, not bounded proof**: 20 cycles observed growth ~1.11×; catastrophic guard passed (max(3×rebuild, rebuild+64MiB)). Does not prove long-term bounded growth.
- **Level0 one real-repo sample only**: OpenLocus temp copy is one data point. Not a general performance or robustness claim.

## Historical verification snapshot

This snapshot is preserved from the earlier local-first stages. It is not the
latest complete real-provider CI status; see the current-status section and the
L1/L2 reports above for recent remote-provider runs.

```text
Rust tests: 243 passed (193 existing + 50 new in openlocus-provider); 29 passed (store with --features tdb)
fmt: clean
clippy: clean with -D warnings (default and --features tdb)
CLI commands: read, scan, search regex/text/bm25/symbol, retrieve, fast-context, citations validate, context-lite, store status/build/purge, derived build/validate/inspect/purge, graph build/inspect, impact, tests, index build/status/dirty/validate/update/purge, search bm25 --index persistent (policy gate enforced), search symbol --mode regex|ast|auto, index build --chunk-strategy line|ast, bench warm (honest: open-once + real citation validation), provider status/audit, dense build/search/purge, version
Eval: regex/bm25/symbol/rrf on fixtures/r2.jsonl; storage_level0_smoke; derived_level0_safety (13/13 checks passed); graph_level0_smoke (11/11 checks passed); fast_context_level0_smoke (14/14 checks passed); persistent_index_smoke (32/32 checks passed, incl. policy/manifest gates + strict validation + honest bench); ast_chunking_smoke (40/40 checks passed); ast_quality_bakeoff (16/16 safety checks passed, quality_gate_passed=false due to FileRecall@5 regression); incremental_index_smoke (48/48 checks passed, incl. dirty summary + skipped empty file + file-level update + policy/schema/strategy gates + citation validation); synthetic_slo_bench (1000 files, build_ms, dirty p50/p95, persistent_cli_search p95, bench_warm open-once query p95, one-file update p50/p95, 0 invalid citations, Level0 synthetic only); real_repo_incremental_bench (modify/add/delete/rename/policy_exclude/batch/latency_compare/growth_cycles on OpenLocus temp copy, total_invalid_citations=0, no stale VerifiedCurrent violations, Level0 one real-repo sample only); provider_dense_safety (45/45 checks passed, incl. remote/outbound defaults, experimental gate, vector/audit no raw text, secret blocking, stale rejection, disabled/unknown provider audit events, query_sha not raw query, short file range, citation validity)
Structural validity: 1.0 across all methods
Citation validity: Python scorer reports 1.0 across methods (`path_range_only` unless Python blake3 is installed); Rust CLI citation validator confirmed current aggregated R2 evidence has `0` invalid citations with hash/range/excerpt checks
Remote dependency: none
TDB dependency: optional only (behind `tdb` feature; not in default build)
LLM dependency: none (rule extractor only)
Graph: deterministic, local-only, depth=1 only
Fast-context: 4-turn deterministic loop, EvidencePack output, ActionRecord replay, token budget, unknown channel gate, final citation validation, no LLM, remote_calls=0
Persistent index: r8-bm25-v2, mandatory manifest + policy gate enforced, validate_path per hit, empty sha skip, strict range no clamp, chunk_strategy line|ast, ast_stats in manifest, warm open=1ms p50=1ms, 32/32 R7 safety checks + 40/40 R8 AST safety checks + 48/48 R10 incremental safety checks
Incremental update: dirty summary (added/modified/deleted), skipped entries tracked (not falsely added), file-level update (--dirty, --path), manifest file write via tmp+rename (not single transaction with Tantivy commit), Tantivy delete-by-term, policy/schema/strategy mismatch + load failure refusal
TDB adapter: Level0 probe, feature-gated, dim=1 smoke, metadata+chunks only, marker-based purge, materialization conformance, no default dependency, no retrieval quality claim
Real-repo bench: Level0 one real-repo sample (OpenLocus temp copy), per-run unique markers avoid self-contamination, cited-excerpt path+marker conjunction gates, branch old/delete markers proven indexed before removal, sampled modify/add/delete/rename/policy_exclude/batch workloads pass, latency_compare uses twin repos (report-only gate), growth_cycles catastrophic guard (observed 20-cycle ~1.10×, does not prove long-term bounded), total_invalid_citations=0, citations_validator_ok=true, no stale VerifiedCurrent violations, sys.exit(1) on safety failure only
Provider/dense scaffold: MockEmbeddingProvider deterministic blake3 vectors dim=32, gate enforces data_level≤1 AND data_level≤metadata.max_data_level, secret scanning blocks SECRET/TOKEN/PASSWORD/API_KEY/sk_/ghp_/AKIA, audit uses query_embed/allow/block/provider_unavailable (not cache_hit), CLI uses query_sha/query_len (no raw query), short file end_line=min(total_lines,8), vector store has vectors but no raw text, audit has no raw text/vector/query, 45/45 safety checks, integration/safety only — not real semantic retrieval
R14 benchmark foundation: 4 logical repo groups from one OpenLocus workspace snapshot, 48 tasks (sanity), 48 labels, 47 hard negatives; fail-closed safety (runner/scorer isolation, isolated temp roots, isolated policy.toml from repo lock, unknown repo_id refusal, citation validity=1.0 via Rust validator, runtime canary retrieval, repo lock manifest re-verification); span-overlap hard_negative_hit_rate@10 + negative_nonempty_rate@10; R14-S is safety foundation, not quality conclusion; graph precision is future feature track
R15 external multi-repo expansion: 9 independent external repos (fast-context-mcp, grok2api, infinite-canvas, gemini-web2api, windsurf2api, kiro2, triviumdb, smartsearch, codex2api) across 5 languages (Rust, Python, Go, JS, TS); 166 medium tasks, 270 hard negatives; multi-language symbol extraction; absolute source paths; isolated roots with repo_id-specific allowlist source-file copying (no whole-repo copy, no symlinks/artifacts); runtime `.openlocus` traces cleaned/audited between queries; strict Rust citation validation before cleanup; exact/single repo_id-prefix scoring path matching; regex FileRecall@1=0.852, BM25 FileRecall@1=0.548; BM25 negative_nonempty_rate@10=0.645; 112/112 smoke checks passed; mined benchmark expansion, not quality conclusion
R16 multi-method quality bakeoff: cross-matrix bakeoff of regex/bm25/symbol/rrf across R14-S/R15-M/R15-stress; all safety gates passed (safety_passed=true, citation_validity=1.0, citation_hash_checked=true, canary_retrieval.passed=true); RRF wins R15-M recall (FileRecall@1 0.933, @5/10 0.993, MRR 0.959) but inherits BM25 negative_nonempty false positives (0.645 R15-M, 0.684 stress); symbol best span precision (0.310 SpanF0.5, 0.052 hard_neg, 0.000 neg_nonempty on R15-M); no method promoted to universal default; lexical/symbol/RRF only; no provider/dense/LLM claims; no remote calls
R17 query intent router / negative guard: eval-layer experiment; does NOT change Rust core; query_only_router_v0 eliminates R15-M negative_nonempty (0.645→0.000) with acceptable recall regression (FileRecall@1 0.904 vs 0.941); rrf_guarded_by_symbol_regex eliminates R15-M negative_nonempty with zero recall regression; R15-stress negative_nonempty reduces but not eliminated (0.158/0.474); citation safety inherited from validated source predictions; baseline prediction/report consistency checked; no LLM/dense claims; remote_calls=0
R18 threshold/guard calibration sweep: eval-layer sweep over 46 strategies with 8 thresholds on R15-M and R15-stress; train-selected rrf_guarded_by_symbol_regex preserves RRF recall on R15-M/holdout and drops medium negative_nonempty to 0.000, but remains weak on stress (0.474 vs symbol 0.105); separate query_noise_plus_rrf_agree_min strategies reach stress 0.000 as observations, not promotions; Pareto frontier computed; no core changes; no LLM/dense claims; remote_calls=0
R19 large/stress guard generalization: eval-layer generalization validation on R15-L (294 weak/mined tasks) and R15-stress; rrf_guarded_by_symbol_regex generalizes to R15-L (recall preserved, neg_nonempty 0.917→0.042) but fails stress (0.474 vs symbol 0.105); query_noise_plus_rrf_agree_min_0.0 stress-zero observation repeated (0.000); R15-L labels are weak/mined; generalization smoke only, not promotion evidence; promotion_ready=false always; no core changes; no LLM/dense claims; remote_calls=0
R25 graph+dense ablation: eval-layer ablation of graph_basic and dense_mock on R20 auto-wide (741 tasks); graph_basic net-negative (0 gold, 435 false spans → blocked); dense_mock net-negative (2 gold, 20,273 false → blocked); rrf_plus_graph dilutes RRF (FileRecall@1 0.693→0.497); rrf_plus_dense_mock dilutes (0.693→0.134); graph_pollution_ratio=0.0; citation validity remains 1.0 with graph/dense/composites revalidated and no_graph inherited from R21 after manifest verification; source-leak canary is regex-only with seeded self-test, not dense-path canary; QuIVer/TDB unavailable/not_measured; no Rust core changes; no LLM/dense real/QuIVer quality claims; remote_calls=0; promotion_ready=false
R26 auto-stress-1000: weak/mined/deterministic stress dataset for retrieval failure discovery; 1100 tasks across exact target counts for 10 stress categories (negative_nonexistent 150, ambiguous_vague 150, hard_distractor 200, semantic_trap 150, same_name_symbol 100, frontend_backend_confusion 75, test_source_confusion 75, generated_vendor_trap 50, stale_index_like 50, dense_quiver_specific_trap 100); 9 R20 repos; same external repo set as R20 plus some R20 task/label-derived queries; deterministic seed 42; no canary tokens; public tasks contain only test_id/repo_id/query/public_version/source; private labels carry category/risk/judgement fields; 19/19 fail-closed static validation checks passed including task/label query consistency, span path/range validity, and repo content manifest SHA lock recomputation; NOT promotion evidence; negative/abstain cases dominate (60%); no runner/scorer matrix yet; no Rust core changes; no LLM/dense claims; remote_calls=0

R28 promotion candidate report: conservative synthesis of R21/R23/R24/R25/R26 reports over R20/R26 failure-surface datasets with promotion_ready=false; current default should not change; best_recall_channel=rrf; best_precision_anchor=symbol; best_dense_candidate=none_available_for_default; quiver_recommendation=hold; graph/dense default expansion blocked; key blockers are R20 weak/mined labels, R26 deterministic/metamorphic/mined/stress labels with no retrieval matrix, R23 guard bucket regressions, QuIVer not implemented, dense real unavailable, and no broad human-verified stress tier
```

## R13 findings

- **Safe scaffold works**: All 45 safety checks pass. Remote is denied by default. Experimental opt-in is required. Secret scanning blocks token-like inputs. Audit contains no raw text or vectors. Vector store contains embedding vectors but no raw text/code snippet.
- **Mock provider is deterministic and normalized**: Same inputs always produce the same unit-length vector via blake3 hash. Different inputs produce different vectors. No network dependency.
- **Materialization gate is essential**: Dense search produces StoreHits which must be materialized through `materialize_evidence()`. Stale hits (content_sha mismatch) are correctly rejected.
- **Metadata-only views prevent code leakage**: Dense store builds views from path/language/basename/path-tokens only. No code snippets at data_level=0. Vector store and audit log do not contain raw code text.
- **Short file ranges are valid**: end_line=min(total_lines, 8) ensures materialize_evidence can verify ranges. Short files produce valid evidence.
- **Query text never leaks**: CLI JSON uses query_sha/query_len. Trace events use query_sha. Audit never stores raw query text. Blocked secret queries do not appear in traces.
- **Audit events use accurate names**: `query_embed` for query embedding, `allow`/`block`/`provider_unavailable` for decisions. Not `cache_hit` (no real cache behavior in R13). Cache key builder/stability only; no cache-hit behavior yet.
- **This is a safety scaffold only. No real semantic quality claim.** Mock vectors are deterministic blake3-based and do not capture semantic similarity. Dense mock search is integration/safety only.

## R14 findings

- **Scaled benchmark program established with fail-closed safety**: R14 defines S/M/L/X tiers. R14-S is populated with 4 logical repo groups from one OpenLocus workspace snapshot, 48 tasks, 48 labels, 47 hard negatives. Runner/scorer are strictly isolated. Citation validity must be 1.0.
- **Anti-leakage design is strictly enforced**: Public tasks contain no gold paths/lines. Labels are in separate private files with canary tokens. Path-component matching prevents false positives (e.g., 'openlocus-retrieval' does not match 'eval/'). Runtime canary retrieval is executed inside isolated benchmark roots.
- **Hard negatives are first-class with span-overlap metrics**: 47 hard negatives in R14-S. `hard_negative_hit_rate@10` requires span overlap unless a hard negative is explicitly file-level. `negative_nonempty_rate@10` measures false positive rate on negative tasks.
- **Citation validity is fail-closed, not a soft gate**: validity must be 1.0. No path-only fallback. Every citation must be hash+range+path valid.
- **Repo lock content manifest is verified by recomputation**: Normalized SHA-256 per file sorted. Mismatch = CRITICAL fail closed.
- **R14-S is a safety foundation, not a quality conclusion**: Validates the pipeline is fail-closed. Does not support quality claims.
- **Previous R14 graph precision is a future feature track**: Not the current R14 definition.
- **R14-M is partial; R14-L/X are not populated**: M uses the same 4 logical repo groups (target is 8+ independent repo groups/repositories). L/X require additional repos. Running --tier L or --tier X will fail with clear message.

## R15 findings

- **External multi-repo benchmark works with fail-closed safety**: 9 independent external repos across 5 languages (Rust, Python, Go, JavaScript, TypeScript), 166 medium-tier tasks, 270 hard negatives. Isolated roots allowlist-copy only manifest/source files under repo_id-specific folders; symlinks/artifacts are not copied. Unknown repo_id fail-closed. Canary retrieval zero hits.
- **Regex outperforms BM25 on exact-symbol queries**: FileRecall@1 is 0.852 (regex) vs 0.548 (bm25) on R15-M. This is because many tasks target exact symbol names where regex matches precisely. BM25 has high negative_nonempty_rate@10 (0.645 vs 0.000 for regex).
- **Hard negative hit rate is non-trivial (~0.23-0.29)**: Structurally plausible but incorrect results are common, as expected with mined hard negatives from the same repo. Hard-negative/gold span overlap is statically blocked.
- **Multi-language symbol extraction is functional but heuristic**: Rust/Python/Go/JS/TS regex-based patterns work for common cases. May miss unusual patterns (Go methods, Python decorators, JS arrows).
- **Anti-leakage holds across external repos**: 0 critical leakage issues. Absolute source path verification. Multi-language manifest verification. Task/label/manifest consistency checks. Canary tokens planted and runtime canary retrieval returns zero hits.
- **This is a mined benchmark expansion, not a quality conclusion.** Labels are mined with varying confidence; not human-verified. External local repos are workspace snapshots; not modified.

## R16 findings

- **Cross-matrix quality bakeoff across R14-S/R15-M/R15-stress**: eval/r16_quality_bakeoff.py runs all three matrices with four methods (regex, BM25, symbol, RRF), verifies safety gates, and produces aggregate report. All safety gates passed; citation_validity=1.0 across all methods/matrices; citation hash checked; canary retrieval passed; no remote calls.
- **RRF wins R15-M recall/MRR** (FileRecall@1 0.933, @5/10 0.993, MRR 0.959) but inherits BM25 negative false positive behavior (negative_nonempty@10 0.645 on R15-M, 0.684 on stress). Not safe as default for precision-sensitive tasks without negative gating or query intent routing.
- **Symbol has best span precision/hard-negative profile on R15-M** (SpanF0.5 0.310, hard_negative_hit_rate 0.052, negative_nonempty 0.000) but lower recall than RRF. Ideal as precision anchor, not sole retriever.
- **Regex strong on mined exact-symbol external tasks** (R15-M FileRecall@1 0.852, negative_nonempty 0.000) but reflects task distribution and exact-string bias, not a general natural-language conclusion.
- **BM25 strong in R14-S but weak and false-positive-heavy in R15-M/stress**: Needs query intent routing or threshold/negative guard.
- **No method promoted to universal default from R16**: Next research should be query intent router / negative guard / method fusion policy, not raw channel addition.
- **This is a lexical/symbol/RRF quality bakeoff. No provider/dense/LLM quality claims are made.**

## R17 findings

- **rrf_guarded_by_symbol_regex eliminates R15-M negative_nonempty with zero recall/MRR regression**: A simple evidence-presence guard that only returns RRF evidence when symbol or regex also found evidence perfectly filters R15-M negative tasks. This is the strongest result for a negative guard on R15-M.
- **query_only_router_v0 eliminates R15-M negative_nonempty with acceptable recall regression**: FileRecall@1 drops from 0.941 to 0.904 (delta -0.037), MRR from 0.963 to 0.918 (delta -0.044). SpanF0.5 improves from 0.253 to 0.315. The router uses noise marker detection, compound snake_case fabrication detection, and vague multi-word query detection.
- **R15-stress negative_nonempty reduces but is not eliminated**: query_only_router_v0 drops from 0.684 to 0.158; rrf_guarded drops to 0.474. Common-word queries where regex still returns false positives prevent full elimination.
- **task_type_assisted_router is an upper-bound reference**: Uses benchmark metadata (task_type) not available at runtime. Achieves 0.258 on R15-M and 0.316 on R15-stress.
- **No core default promotion**: R15-stress negative_nonempty remains above 0 for all strategies. Both R15-M and R15-stress negative_nonempty must improve without unacceptable recall/MRR regression before any core default change.
- **Eval-layer research only; does NOT change Rust core. No LLM/dense claims.**

## R18 findings

- **Train-selected candidate is useful but not stress-safe**: `rrf_guarded_by_symbol_regex` preserves RRF FileRecall@1/MRR on full R15-M (0.941/0.963) and holdout (0.844/0.900), while reducing medium negative_nonempty to 0.000. Stress remains weak: 0.474 negative_nonempty versus symbol 0.105.
- **The query noise guard is the key differentiator for stress**: rrf_guarded_by_symbol_regex alone leaves stress at 0.474 because regex returns false positives for common-word stress queries. The query noise guard identifies these as vague/noise and routes to empty.
- **Stress-zero strategies are observations, not promotions**: `query_noise_plus_rrf_agree_min` variants reach 0.000 stress negative_nonempty on the 19-task stress set, but this is too small and mined to justify default promotion.
- **Threshold sweep reveals sharp recall cliff at 0.05**: Most RRF top scores are either very high or very low; thresholds above 0.03 reject nearly all evidence.
- **Pareto frontier on R15-M shows recall vs hard-negative trade-off**: symbol (0.052 hard_neg, 0.807 recall) vs rrf_guarded (0.259 hard_neg, 0.941 recall) vs query_only_router_v0 (0.237 hard_neg, 0.904 recall).
- **No core default promotion in R18**: Threshold/guard choices are calibrated on mined R15 data and require larger/human-verified validation before promotion.
- **Eval-layer calibration only; does NOT change Rust core. No LLM/dense claims.**

## R19 findings

- **rrf_guarded_by_symbol_regex generalizes to R15-L**: FileRecall@1 preserved (0.911 vs RRF 0.911), negative_nonempty drops from 0.917 to 0.042. R15-L labels are weak/mined; generalization smoke only.
- **rrf_guarded fails stress**: Stress negative_nonempty is 0.474, above symbol baseline 0.105. The selected candidate does NOT improve stress beyond symbol. Query noise guard is needed.
- **query_noise_plus_rrf_agree_min_0.0 stress-zero observation repeated**: Achieves 0.000 stress negative_nonempty and 0.000 R15-L negative_nonempty. R15-L FileRecall@1 is 0.904 (delta -0.007 vs RRF). Observation, not promotion.
- **R15-L labels are weak/mined (270 mined, 24 weak)**: Generalization smoke only, not promotion evidence. R15-stress has only 19 tasks.
- **No core default promotion from R19**: promotion_ready is always false. Requires human-verified labels and larger stress dataset.
- **Eval-layer generalization validation only; does NOT change Rust core. No LLM/dense claims.**

## R20 findings

- **Failure-surface dataset generation works**: 741 tasks across 25 required categories and 9 R15 repos, with deterministic generation from fixed seed=42.
- **Public/private separation is clean**: Public tasks contain only task_id, repo_id, query, public_version, source_tier. No gold/expected/oracle/risk/judgement fields leak. All judgement fields are in separate private labels.
- **Category coverage is complete**: All 25 required categories have >= 5 tasks. positive_exact_symbol (180) and positive_regex_anchor (90) dominate due to per-repo symbol extraction.
- **Label quality distribution**: mined_high_confidence: 315, mined: 168, weak: 258. No human_reviewed (forbidden in R20).
- **Expected behavior distribution**: primary_evidence: 374, abstain: 177, weak_candidates: 90, no_primary: 45, supporting_only: 55.
- **Oracle type distribution**: deterministic: 438, stress: 148, mined: 110, metamorphic: 36, differential: 9.
- **Static validation passes all 14 check categories**: no private field leaks, task/label ID bijection, enum validity, required label schema, gold_span consistency, overlap constraints, span path/range validation, manifest SHA verification, coverage minimums, dataset manifest flags.
- **Metamorphic/stress categories** (dirty_overlay, deleted_file, renamed_file, branch_switch_like) encode expected behavior for R21/R26 but do NOT mutate source in R20.
- **R20 labels are failure-surface oracle/probe labels, not EvidenceCore.**
- **R20 is a failure-surface dataset, NOT promotion evidence.** No runner/scorer matrix exists yet; R21 will use this data.
- **Dataset + static validator only; no Rust core changes.**

## R22/R27 findings

- **Failure attribution is analysis-only**: Consumes R21 artifacts and R20 labels without re-running retrieval. 13 failure clusters computed from cross-strategy comparison heuristics.
- **RRF_INHERITED_BM25_FALSE_POSITIVE is the largest actionable cluster (110 tasks)**: BM25 and RRF both return false primary evidence on no-gold tasks. RRF inherits BM25's broad lexical matching without a negative gate.
- **GUARD_RECALL_KILL affects 67 positive tasks**: rrf_guarded_by_symbol kills recall when symbol returns empty on natural-language/vague queries but RRF finds gold. Per-guard: symbol=67 kills, regex=0, symbol_regex=0, query_noise=0.
- **SYMBOL_EXTRACTION_MISS affects 91 positive tasks**: Regex/RRF find gold but heuristic symbol extraction misses due to non-standard definition patterns.
- **REGEX_NORMALIZATION_BUG affects 1 task**: Curly braces in route-style queries cause Rust regex parse errors.
- **62 BENCHMARK_ORACLE_SUSPECT tasks**: Weak-quality labels where strategies strongly disagree with the oracle, suggesting label (not strategy) error.
- **Unrun strategy clusters have count=0**: Dense, TDB/QuIVer, graph, AST strategies not evaluated in R21. No fabricated data. recommended_next_tests provided for each.
- **EVIDENCECORE_REJECTION clusters have metric_unavailable=true**: R21 shows rate=0.0 for all strategies; no rejection data to analyze.
- **206 bucket regressions detected**: Multiple strategies exceed thresholds in specific buckets. promotion_blocked_by_bucket_regression=true.
- **promotion_ready=false. not_promotion_evidence=true. No Rust core changes. No LLM/dense claims.**

## R23 findings

- **Guard parameter sweep is analysis-only**: Consumes R21 artifacts and R20 labels without re-running retrieval. 51 strategies across 8 guard parameter dimensions plus 15 combined strategies.
- **All 51 strategies have bucket regressions**: Every guard strategy has at least one bucket where recall gap vs RRF >0.15, no_gold_nonempty_rate >0.3, primary_false_positive_rate >0.3, or guard_recall_kill_rate >0.1.
- **Combined query_noise + agreement is the best R23 guard balance**: query_noise_1_plus_regex_or_symbol_agree achieves no_gold_nonempty_rate 0.221 (vs RRF 0.495) with FileRecall@1 0.693 preserved and zero guard_recall_kill.
- **Agreement guards reduce false positives without recall cost**: regex_or_symbol_agreement_required reduces no_gold_nonempty_rate from 0.495 to 0.279 with zero guard_recall_kill and preserved FileRecall@1.
- **RRF score threshold above 0.02 causes sharp recall cliff**: Most RRF top scores are concentrated near 0.03-0.06.
- **top1_top2_gap threshold kills too much recall**: Even gap=0.005 causes >50% guard_recall_kill_rate.
- **Symbol agreement alone kills 22.8% recall**: Confirms R22 finding.
- **No strategy eliminates no_gold_nonempty_rate to zero without unacceptable recall loss**: Strategies achieving near-zero false positives do so by abstaining on >99% of queries.
- **Curves computed**: risk_coverage_curve, recall_vs_negative_curve, recall_vs_false_primary_curve, precision_vs_abstain_curve.
- **6877 total bucket regressions across 51 strategies**: Expected given R20 label diversity and now includes bucket-level guard_recall_kill regressions.
- **promotion_ready=false. not_promotion_evidence=true. No Rust core changes. No LLM/dense claims.**

## R24 findings

- **QuIVer is not implemented**: Scan of all Rust crates, Cargo.toml files, and source code confirms no QuIVer implementation exists outside eval/docs placeholders. quiver_implemented=false. All R24.1 diagnostic fields (BQ_overlap, quiver recall, quiver precision, quiver MRR, quiver F0.5) report unavailable/not_measured with reason quiver_not_implemented and explicit next_required_tests. No numeric 0 is output as a quality result.
- **TDB is a placeholder in default build**: `openlocus store status tdb --json` returns available=false, success=false, mode=placeholder. TDB is a feature-gated metadata/chunk store, not an ANN/QuIVer backend. tdb_stale_leak_count is not_applicable.
- **Dense mock is available as a candidate-channel safety smoke**: mock and disabled providers are available; real provider is unavailable. Dense mock uses deterministic blake3-based vectors that do NOT capture semantic similarity.
- **Dense mock produces real, materialized candidates but mostly exposes noise**: full run produced 5,264 dense_mock candidates, all Rust citation-valid. Quality is poor as expected for non-semantic mock vectors: FileRecall@1 0.024, MRR 0.073, SpanF0.5 ~0.000, token_waste 0.850, primary_false_positive_rate 0.878.
- **Dense CLI rejection and canary behavior are explicit**: full run recorded 99 candidate rejections (`candidate_rejection_rate` 0.134). Canary hardening checked 8 non-empty dense stores, skipped 1 empty store, returned 66 path-canary evidence items and 132 query-canary evidence items, with raw canary/query leakage 0.
- **Dense mock + RRF fusion amplifies noise**: fusion confirms dense contribution (642 tasks, 5,264 dense spans retained) but increases false-primary/noise: FileRecall@1 0.134, MRR 0.451, token_waste 0.928, primary_false_positive_rate 0.923, hard_distractor_hit_rate 0.215. This is a failure-surface probe, not a recommended strategy.
- **Citation validity is enforced**: Dense evidence and dense+RRF fusion evidence both pass Rust citation validation (hash+range+path) before cleanup. dense_mock citation_total=5,264; fusion citation_total=13,149; invalid=0.
- **R24 is NOT a QuIVer bakeoff**: It is an availability + mock dense candidate-channel probe + TDB placeholder status check. QuIVer remains future work.
- **No Rust core changes. No LLM/dense real/QuIVer quality claims. remote_calls=0.**

## R25 findings

- **graph_basic is net-negative on R20 auto-wide**: Added 0 gold spans and 435 false spans. Depth=1 graph impact from top path (derived via symbol→regex fallback) introduces evidence from related files that are not in gold, without recovering any gold spans RRF missed. Default expansion blocked by added_false_span > added_gold_span rule.
- **dense_mock is net-negative as expected**: Added 2 gold spans and 20,273 false spans. Non-semantic blake3-based mock vectors produce massive noise. The 2 gold hits are likely coincidental proximity. Default expansion blocked.
- **rrf_plus_graph dilutes RRF quality**: FileRecall@1 drops from 0.693 to 0.497. Graph evidence competes with RRF evidence in RRF score calculation, pushing relevant RRF hits down in ranking.
- **rrf_plus_dense_mock also dilutes RRF quality**: FileRecall@1 drops from 0.693 to 0.134. Dense mock evidence floods the RRF pool with irrelevant candidates.
- **Graph pollution is zero**: No graph evidence returned on forbidden paths (graph_pollution_ratio=0.000).
- **Graph has low token waste when it fires** (0.310 vs 0.779 baseline) but mostly abstains (0.785 abstain rate).
- **Graph path derivation stats**: symbol=358/741 (48.3%), regex=156/741 (21.1%), none=227/741 (30.6%). Impact returns empty evidence for 355/514 tasks with a top path (no graph edges found).
- **Combined strategies show additive noise**: rrf_plus_dense_mock_plus_graph accumulates both graph (435) and dense (20,273) false spans (20,695 total).
- **Citation validity remains 1.0**: graph_basic, dense_mock, and composite strategies are revalidated in R25 with Rust hash/range/path citation validation. no_graph inherits R21 validation after R25 verifies the R21 artifact manifest before baseline use.
- **QuIVer/TDB honestly reported as unavailable/not_measured**: No numeric zero quality results for QuIVer. TDB not applicable.
- **R25 is an eval-layer ablation study; does NOT change Rust core. No LLM/dense real/QuIVer quality claims. remote_calls=0. promotion_ready=false. not_promotion_evidence=true.**

## R29 findings

- **16-strategy matrix on R26 auto-stress (1100 tasks) is a failure-surface probe**: eval/r29_r26_stress_matrix.py runs base (regex/bm25/symbol/rrf), composite/guard (bm25_regex, bm25_symbol, rrf_guarded_by_symbol/regex/symbol_regex, query_noise_plus_rrf_agree_min), and R24/R25-style (dense_mock, dense_mock_plus_rrf, graph_basic, rrf_plus_graph, rrf_plus_dense_mock, rrf_plus_dense_mock_plus_graph) strategies. Strictly separated RUN/SCORE phases. R26 provenance validated before run. Citation validity must be 1.0 for all strategies. 14 required failure clusters computed. Span contribution analysis for graph/dense/composites vs fresh RRF baseline. Bucket regressions across source_category/expected_behavior/oracle_type/repo_id/risk_tags.
- **5 unavailable strategies report reason only**: dense_real_if_available (not_configured_or_policy_disabled), tdb_quiver_if_available (quiver_not_implemented), tdb_quiver_plus_rrf (quiver_not_implemented), tdb_quiver_guarded_by_symbol_regex (quiver_not_implemented), fast_context_if_available (fast_context_is_4turn_orchestration_scaffold_not_standalone_matrix_strategy). No fake numeric quality.
- **No skip-run**: Fresh run always required. Canary/citation validation cannot be bypassed.
- **Private field scan enforced**: Prediction/evidence/rejection/trace JSONL must not include source_category, risk_public, intent_guess, risk_tags, oracle_type, expected_behavior, gold_spans, hard_distractors, must_not_primary, why_this_is_hard, which_strategy_it_targets.
- **R26 labels are weak/mined/deterministic/stress**: Not human-verified. This is failure-surface only, not promotion evidence.
- **dense_mock is candidate-channel safety smoke, not semantic quality**: Mock vectors are deterministic blake3-based and do not capture semantic similarity.
- **graph_basic is deterministic depth=1**: Not precise call/type graph.
- **QuIVer not implemented; TDB unavailable**: No fabricated numeric quality.
- **promotion_ready=false. not_promotion_evidence=true. No Rust core changes. No LLM/dense real/QuIVer quality claims. remote_calls=0.**
- **Full R29 run completed with safety gates passed**: 1100 tasks, 16 implemented strategies, 64 artifact files verified, artifact private-field/canary scans clean, all implemented strategies have citation_validity=1.0.
- **RRF remains strongest recall but unsafe alone**: FileRecall@1=0.803, FileRecall@5=0.923, MRR=0.858, primary_false_positive_rate=0.453.
- **`query_noise_plus_rrf_agree_min` stress result is promising but still not promotion**: FileRecall@1=0.803, FileRecall@5=0.923, primary_false_positive_rate=0.106, guard_recall_kill_rate=0.003. R23 bucket-regression evidence still blocks promotion.
- **Symbol remains the precision anchor**: SpanF0.5=0.291, primary_false_positive_rate=0.080, token_waste=0.247, but abstain_rate=0.671.
- **Dense mock and dense+RRF are net-negative failure surfaces**: dense_mock primary_false_positive_rate=0.874; dense_mock_plus_rrf/rrf_plus_dense_mock primary_false_positive_rate=0.906.
- **Graph remains default-blocked**: graph_basic added_gold_span=0 and added_false_span=437; all graph/dense expansion variants are blocked by added_false_span > added_gold_span.
- **Failure clusters surfaced at scale**: DENSE_MOCK_NOISE=577, RRF_INHERITED_BM25_FALSE_POSITIVE=299, DENSE_SEMANTIC_TRAP_FALSE_POSITIVE=219, GRAPH_ADDS_NO_GOLD=90, GUARD_RECALL_KILL=62. Bucket regressions total=448.

## BEA-0 findings

- **BEA-0 is the first real algorithmic retrieval/acquisition experiment**:
  reruns fresh multi-method retrieval (bm25/regex/symbol + optional rrf)
  over fresh bounded ContextBench verified Python rows (default 10; hard
  cap 20) and RepoQA Python needles (default 5; hard cap 10), runs a
  deterministic `bea_v0_budgeted` policy under an evidence budget (default
  10; hard cap 20), and computes per-arm aggregate metrics with
  baseline-vs-treatment deltas vs `bm25_top10` (and
  `rrf_bm25_regex_symbol_top10` when rrf enabled). Not replay, not
  aggregate validation — real fresh retrieval + acquisition loop.
- **BEA v0 policy is runtime-clean and deterministic**: consumes only
  method source, candidate rank, score/normalized score, rank agreement
  across methods, duplicate path/span overlap, candidate count, accepted
  coverage, budget remaining, cheap path extension. Verified invariant under
  synthetic gold/label/row-id/model-family/previous-outcome tainting
  (policy produces IDENTICAL accepted/action_trace/budget_states because it
  ignores those fields). Initial actions: `accept_candidate`,
  `skip_low_support`, `rerank_by_agreement`, `stop_budget_exhausted`;
  optional `expand_same_file` for deferred same-file candidates under budget.
- **Private per-record SCORE JSONL preserved in /tmp**: every evaluated
  record gets a private SCORE row with phase_run_id, benchmark, private
  record id, runtime query feature summary, candidate list (method, rank,
  score, normalized_score, path, span, content_sha, extension, agreement),
  action trace, budget states, accepted/final candidates, score outcome
  (per-arm metrics), latency_ms, cost_usd=0.0, tokens=0, provider_calls=0,
  failure_reason. Private SCORE path NEVER serialized in public artifact,
  docs, or CI artifacts. Public artifact records ONLY aggregate SCORE
  manifest fields (records_written, record_count, schema_version,
  manifest_hash, storage_class, path_publicly_serialized=false).
- **Manual CI run `27934507148` (2026-06-21)**: ContextBench 2 rows + RepoQA 1
  needle, budget=5, methods bm25/regex/symbol, rrf baseline required and enabled. All 3
  records successful. Treatment `bea_v0_budgeted` preserved file_recall@10
  / mrr / success_rate parity with both baselines while using roughly half
  the evidence budget (`evidence_budget_used=3.33` vs `6.67`) and improved
  `span_f0.5@10` by `+0.028` and `quality_per_candidate` by `+0.0014`.
  3 private per-record SCORE rows written to
  `/tmp/bea0_private_score_<pid>_<ts>/bea0.private.jsonl`.
- **Strict claim boundary**: BEA-0 emits `claim_level =
  bea_v0_budgeted_acquisition_smoke_only`. NOT a benchmark result, NOT a
  leaderboard entry, NOT a performance claim, NOT a method-winner claim,
  NOT a calibration claim, NOT a promotion, NOT a default change, NOT a
  runtime/retriever/pack/backend/EvidenceCore semantic change, NOT a
  downstream agent value claim. Does NOT emit `winner`, `best_method`,
  `recommended_default`, `method_winner`, `calibration`. All no-claim /
  no-runtime-change flags false; `aggregate_only_public_artifact=true`,
  `diagnostic_only=true`, `provider_calls=0`.
- **212/212 self-test checks pass**: 26 groups covering identity fields,
  safe true flags, no-claim false flags, license fields, private SCORE
  manifest aggregate-only fields, row/needle/budget hard caps, method
  validation, path extension helper, BEA v0 policy mechanics (accepts
  nonempty; first accept is high-agreement; skips low_support; budget
  states track budget_remaining; respects budget cap), runtime-clean
  invariance under tainting, per-arm metrics + deltas, aggregate means,
  arm metric allowlist filtering, failure category counts enum,
  unavailable statuses, scanner rejects BEA-0-specific forbidden keys
  (private_score_path, action_trace, budget_states, accepted_candidates,
  final_candidates, candidate_list, score_outcome, etc.) and value
  patterns (repo URL/slug/commit SHA/file path/tmp path/multiline), scanner
  allows safe values (schema_version, methods, budget, arm_metric_records,
  delta_records, private_score_manifest_hash, failure_category), fail-closed
  generation (clean report no raise; private_score_path raises;
  action_trace raises; accepted_candidates raises; winner raises;
  best_method raises; self-test failure refuses artifact generation),
  CLI surface, private SCORE writer round-trip, aggregate runtime seconds
  present, no winner/best_method/recommended_default/method_winner/
  calibration anywhere.
- **CI is manual opt-in `workflow_dispatch`** with
  `enable_external_benchmark_network=true`. Network disabled by default.
  Fail-closed when enabled: require status in (`bea_v0_smoke_pass`,
  `partial`), `records_successful > 0`, `forbidden_scan.status=pass`,
  `provider_calls=0`, `private_score_record_count == records_successful`,
  no `winner`/`best_method`/`recommended_default`/`method_winner`/
  `calibration` fields anywhere, no BEA-0 private fields
  (`private_score_path`, `action_trace`, `budget_states`,
  `accepted_candidates`, `final_candidates`, `candidate_list`,
  `score_outcome`, etc.) anywhere. Uploads only aggregate public report;
  never uploads private SCORE JSONL.
- **BEA-0 is NOT C3**: C3 was replay-only and selected among precomputed
  P21 outcomes; BEA-0 actually reruns retrieval and acquires evidence
  under a budget, with private per-record SCORE traces. C3 -> BEA-0 is the
  pivot from replay-only to real acquisition.

## BEA-1 findings

- **BEA-1 is the first mechanism ablation smoke**: reruns fresh
  multi-method retrieval (bm25/regex/symbol + optional rrf) over bounded
  real ContextBench verified Python rows (default 5; hard cap 20) and
  RepoQA Python needles (default 3; hard cap 10), runs 5 fixed arms
  (`bm25_top10`, `bea_v0_budgeted`, `same_budget_bm25_prefix`,
  `agreement_only_same_budget`, `seeded_random_same_budget`; plus
  `rrf_bm25_regex_symbol_top10` when rrf enabled), and computes per-arm
  metric records, baseline-vs-treatment delta records, and mechanism
  contrast records on the paired denominator. NOT aggregate validation;
  real fresh retrieval + 3 same-budget controls + mechanism contrasts.
- **Same-budget K exactly per plan**:
  `K = min(len(bea_v0_budgeted.accepted_candidates), available_deduped_candidate_count)`.
  If BEA accepts zero candidates for a record, same-budget controls also
  select zero. Public artifacts never serialize accepted candidates or
  candidate lists.
- **Same-budget controls are runtime-clean and deterministic**:
  `same_budget_bm25_prefix` takes the first K BM25 candidates after
  dedupe; `agreement_only_same_budget` sorts the same deduped universe as
  BEA by (agreement desc, min_rank asc, max_normalized_score desc, stable
  order); `seeded_random_same_budget` uses fixed public seed `20240621`
  over the stable-ordered deduped universe. No gold/labels/row IDs/
  provider/model fields in seed or ordering. Verified invariant under
  synthetic gold/label/row-id tainting.
- **Paired denominator rule**: mechanism contrasts only include records
  where both baseline and treatment arms have valid metrics for the same
  record. Every `mechanism_contrast_records` row includes `record_count`
  so deltas are interpretable. Public artifacts do not serialize per-record
  inclusion masks.
- **Manual CI run `27936497544` (2026-06-21)**: ContextBench 5 rows + RepoQA 3
  needles, budget=5, methods bm25/regex/symbol, rrf baseline required and enabled.
  All 8 records successful; `paired_exclusion_count=0`. BEA v0 ties
  `same_budget_bm25_prefix` and `agreement_only_same_budget` on
  file_recall@10/mrr/span_f0.5@10/success_rate with the same
  `evidence_budget_used=3.125`; BEA v0 beats `seeded_random_same_budget`
  by `delta(mrr)=+0.09375`. 8 private per-record SCORE rows written to
  `/tmp/bea0_private_score_<pid>_<ts>/bea1.private.jsonl`.
- **Strict claim boundary**: BEA-1 emits `claim_level =
  bea_v0_mechanism_ablation_smoke_only`. NOT a benchmark result, NOT a
  leaderboard entry, NOT a performance claim, NOT a method-winner claim,
  NOT a calibration claim, NOT a promotion, NOT a default change, NOT a
  runtime/retriever/pack/backend/EvidenceCore semantic change, NOT a
  downstream agent value claim. Does NOT emit `winner`, `best_method`,
  `recommended_default`, `method_winner`, `calibration`. All no-claim /
  no-runtime-change flags false; `aggregate_only_public_artifact=true`,
  `diagnostic_only=true`, `provider_calls=0`.
- **420/420 self-test checks pass**: 28 groups covering identity fields,
  safe true flags, no-claim false flags, license fields, private SCORE
  manifest aggregate-only fields, row/needle/budget hard caps, method
  validation, same-budget K exactly, three same-budget control arm
  algorithms, runtime-clean invariance, arm_metric_records fixed shape,
  delta_records fixed shape, mechanism_contrast_records fixed shape +
  record_count, failure category counts enum, unavailable statuses,
  scanner rejects BEA-0 + BEA-1 forbidden keys and value patterns,
  scanner allows safe values, fail-closed generation, CLI surface,
  private SCORE writer round-trip, paired denominator rule, aggregate
  runtime seconds present, no winner/best_method/recommended_default/
  method_winner/calibration anywhere, fixed arms present, scanner rejects
  BEA-1-specific claim-boundary keys (calibration, method_winner, etc.).
- **CI is manual opt-in `workflow_dispatch`** with
  `enable_external_benchmark_network=true`. Network disabled by default.
  Fail-closed when enabled: require status in (`bea1_mechanism_ablation_pass`,
  `partial`), `records_successful >= 3`, every mechanism contrast
  `record_count >= 3`, `forbidden_scan.status=pass`, `provider_calls=0`,
  `private_score_manifest` present with `path_publicly_serialized=false`
  and `record_count == records_successful`, no
  `winner`/`best_method`/`recommended_default`/`method_winner`/`calibration`
  fields anywhere, no BEA-1 private fields anywhere. Uploads only
  aggregate public report; never uploads private SCORE JSONL.
- **BEA-1 is NOT BEA-0**: BEA-0 measured BEA v0 vs `bm25_top10` (and
  `rrf_bm25_regex_symbol_top10` when enabled); BEA-1 measures BEA v0 vs
  three same-budget controls that isolate whether BEA-0's gains (if any)
  come from multi-source agreement / sequential budgeted evidence
  acquisition rather than merely reading fewer candidates. BEA-1 does
  NOT bootstrap the BEA-0 aggregate artifact; it reruns fresh external
  retrieval.

## BEA-2 findings

- **BEA-2 is the policy v0.2 diversity/risk mechanism smoke**: implements a
  real algorithmic policy change (BEA v0.2) with frozen priority weights
  (agreement=0.30, bm25_norm=0.20, diversity=0.20, query_path_overlap=0.15,
  risk_penalty=-0.25, duplication_penalty=-0.30) over fresh heldout
  ContextBench verified Python rows (offset 40) + RepoQA Python needles
  (offset 20). v0.2 is structurally different from v0 and agreement-only:
  greedy priority-scored selection with diversity/risk/duplication-aware
  recomputation after each selection.
- **Manual CI run `27938484585` (2026-06-21)**: Manual CI run `27938484585` (2026-06-21) passed with ContextBench offset 40 limit 20 + RepoQA offset 20 limit 10, budget=5, methods bm25/regex/symbol, RRF baseline enabled. 30 records successful; `paired_exclusion_count=0`; forbidden scan pass; `provider_calls=0`; `private_score_manifest.record_count=180` (30 records × 6 arms); `private_score_manifest.storage_class=tmp_private`; `private_score_manifest.path_publicly_serialized=false`; `aggregate_runtime_seconds=386.3`. BEA v0.2 vs BEA v0 / same-budget BM25 / agreement-only / RRF: `file_recall@10` delta=+0.033334, `mrr` delta=+0.081667, `span_f0.5@10` delta=-0.012947, `success_rate` delta=+0.033334, `latency_seconds` delta=+8.188547, `evidence_budget_used` delta=0.0. Win/tie/loss (v0.2 vs v0, n=30): file_recall@10 win=3 tie=25 loss=2; mrr win=7 tie=21 loss=2; span_f0.5@10 win=0 tie=28 loss=2; success_rate win=3 tie=25 loss=2. Against seeded random, v0.2 deltas were stronger positive (`file_recall@10` +0.233334, `mrr` +0.326667, `span_f0.5@10` +0.019687, `success_rate` +0.233334). This is a mixed smoke-level mechanism result, not a method-winner/default/performance/calibration claim.
- **321/321 self-test checks pass**: 31 groups covering identity, safe-true /
  no-claim flags, license, private SCORE manifest, heldout offset/limit hard
  caps, budget caps, method validation, v0.2 policy mechanics (accepts
  nonempty; respects budget; differs from v0; priority components present;
  runtime-clean invariance), risk_bucket/diversity/query_overlap helpers,
  same-budget K, same-budget control arms, benchmark_arm_metric_records
  fixed shape, delta_records, mechanism_contrast_records, win_tie_loss_records,
  failure category enum, unavailable statuses, scanner reject/allow, fail-closed
  generation, CLI surface, private SCORE writer round-trip, paired denominator,
  aggregate runtime, no winner/calibration anywhere, fixed arms, frozen
  priority weights.
- **Strict claim boundary**: `claim_level=bea_v02_policy_smoke_only`. NOT
  benchmark/leaderboard/performance/method-winner/calibration/promotion/
  default/runtime/EvidenceCore/downstream-value. `provider_calls=0`.
- **BEA-2 does NOT mutate BEA-0/BEA-1**: standalone phase, standalone
  evaluator, standalone artifact. BEA-0/BEA-1 semantics unchanged.

## BEA-3 findings

- **BEA-3 implements a frozen BEA v0.3 anchor/span/latency-aware policy**:
  reserves anchor slots for BM25/agreement anchors, applies diversity/risk
  scoring to remaining budget, adds runtime-clean span/latency proxies
  (tighter line-span bonus, same-file-as-anchor support, risk penalties,
  weak-support penalty, marginal-priority early stop). Frozen weights NOT
  tuned from outcomes. Ablations: v0_3_no_anchor, v0_3_no_early_stop.
- **Manual CI run `27942492278` (2026-06-21)**: 30 records (ContextBench 20 + RepoQA 10), budget=5, 9 arms, 270 private SCORE rows. v0.3 vs v0.2: file_recall@10 delta=0.0, mrr delta=0.0, span_f0.5@10 delta=+0.00217, success_rate delta=0.0, latency_seconds delta=+0.001098, quality_per_latency delta=+0.000292. Win/tie/loss vs v0.2: file/MRR/success all 0/30/0, span 1/29/0. v0.3 is effectively tied with v0.2, with only a tiny span/quality-per-latency signal.
- **225/225 self-test checks pass**: 30 groups.
- **Strict claim boundary**: `claim_level=bea_v03_policy_smoke_only`.
  NOT benchmark/leaderboard/performance/method-winner/calibration/promotion/
  default/runtime/EvidenceCore/downstream-value. `provider_calls=0`.
- **BEA-3 does NOT mutate BEA-0/BEA-1/BEA-2**: standalone phase, evaluator,
  artifact.
- **New metric**: `quality_per_latency` = span_f0.5@10 / latency_seconds.
- **New record type**: `mechanism_summary_records` (anchor_used_rate,
  early_stop_rate, mean_budget_used, mean_latency_seconds,
  mean_span_extent, span_proxy_bucket counts).
- **Latency attribution fix**: all arms share candidate-collection latency
  (fair attribution); v0.3 also gets incremental policy time.

## BEA-4 findings

- **BEA-4 is the external scale smoke for the frozen BEA v0.3 policy**:
  manual CI run `27957586271` completed green on a larger fresh external slice
  (ContextBench verified Python rows offset 80 limit 80 + RepoQA Python needles
  offset 40 limit 40) with 7 fixed arms (no ablations; v0.3 + v0.2 + v0 +
  bm25_prefix + agreement_only + rrf + seeded_random). v0.3 algorithm/weights
  are frozen exactly as BEA-3 (`algorithm_changed_during_bea4=false`,
  `weights_tuned_during_bea4=false` — binding).
- **Scale result**: 120 records successful (ContextBench 80 + RepoQA 40),
  `private_score_manifest.record_count=840` (120×7 arms), `network_calls=3`,
  `provider_calls=0`, forbidden scan pass, aggregate runtime 864.538s.
- **BEA v0.3 metrics**: ContextBench file_recall@10=0.225, mrr=0.151875,
  span_f0.5@10=0.013607, success_rate=0.225; RepoQA file_recall@10=0.575,
  mrr=0.402917, span_f0.5@10=0.044761, success_rate=0.575.
- **Deltas are mixed**: vs BEA v0.2, v0.3 ties file_recall/MRR/success,
  slightly lowers span (-0.000075), and adds tiny latency (+0.000831s).
  vs BEA v0 / same-budget BM25 / agreement-only / RRF, v0.3 improves
  file_recall by +0.108334, MRR by +0.076945, span by +0.001333, and
  success by +0.108334; vs seeded random it improves file_recall by +0.175,
  MRR by +0.139028, span by +0.020195, and success by +0.175. Latency and
  quality-per-latency trade-offs remain mixed, especially vs RRF.
- **Public artifact is records-only**: `benchmark_arm_metric_records`,
  `delta_records`, `win_tie_loss_records`, `worst_slice_records` (70 aggregate
  records with 7 fixed bucket labels), `mechanism_summary_records`, and
  aggregate-only `private_score_manifest`. No row IDs, repos, paths, commits,
  queries, labels, candidate lists, gold/source snippets, or private SCORE paths.
- **Strict claim boundary**: `claim_level=bea_v03_external_scale_smoke_only`.
  NOT benchmark/leaderboard/performance/method-winner/calibration/promotion/
  default/runtime/EvidenceCore/downstream-value. `provider_calls=0`.
- **BEA-4 does NOT mutate BEA-0/BEA-1/BEA-2/BEA-3**: standalone phase,
  evaluator, artifact. v0.3 frozen.

## BEA-5 findings

- **BEA-5 is complete as a fixed-protocol No-Go / near-miss**: final CI run
  `28003522632` failed closed with `records_successful=119`, one short of
  the predeclared 120-record quota. A local exact-protocol rerun reproduced
  the aggregate artifact.
- **Fixed protocol**: success-quota scan over the full available Python frame
  excluding BEA-2/3/4 windows; raw caps ContextBench 480 and RepoQA 240;
  minimums ContextBench >= 40, RepoQA >= 20; fixed budget 5; fixed methods
  `bm25,regex,symbol`; RRF same-budget required.
- **Aggregate yield**: `records_attempted_total=186`, `records_successful=119`,
  `records_excluded=67`, `contextbench_successful=82`, `repoqa_successful=37`,
  `quota_reached=false`, `failure_category_counts.retrieval_failed=67`,
  `rrf_required_but_missing=0`.
- **Private traces**: `private_score_manifest.record_count=833` (119×7 arms)
  and `private_attempt_manifest.record_count=186`; both are `/tmp` private,
  path not publicly serialized.
- **119-record metric signal**: v0.3 ties v0.2 on file_recall@10, MRR, and
  success_rate; v0.3 vs v0.2 has `span_f0.5@10 +0.004953` and
  `quality_per_latency +0.002853`. v0.3 beats BM25/agreement/RRF on
  file_recall/MRR/success by +0.184874/+0.164566/+0.184874, but has latency
  costs and remains non-passing because the quota missed by one record.
- **Interpretation**: BEA-5 is not a pass and not a benchmark/performance
  claim. It becomes failure-decomposition input for BEA-4/5, not a reason to
  tune v0.31 weights or keep changing sampling.
- **Strict claim boundary**: `claim_level=
  bea_v03_frozen_policy_robustness_smoke_only`. NOT benchmark/leaderboard/
  performance/method-winner/calibration/promotion/default/runtime/EvidenceCore
  /downstream-value. `provider_calls=0`.
- **BEA-5 does NOT mutate BEA-0/BEA-1/BEA-2/BEA-3/BEA-4**: standalone
  phase, evaluator, artifact. v0.3 frozen.

## B16-F findings

- **B16-F is the first downstream live-provider paired smoke that compares
  a BEA v0.3-derived context pack against a same-budget BM25 context-pack
  control** (and a sparse control) on bounded synthetic coding tasks. Three
  arms: `control_sparse`, `bm25_same_budget_context_pack`,
  `bea_v03_context_pack`. Primary contrast: BEA vs same-budget BM25.
  Secondary: BEA vs sparse, BM25 vs sparse. Eight fixed task families.
  Default 8 tasks x 3 arms = 24 live provider calls.
- **BEA v0.3 context pack selector uses ONLY runtime-clean candidate
  features** (method source, rank, score/normalized score, agreement count,
  span extent, path). NEVER reads gold paths, `correct_value`, task_family
  decisive cue, or any private answer. Verified via gold-tainting invariant
  in self-test (tainting `correct_value` does NOT change BEA selection).
- **Private SCORE JSONL + private event JSONL written under `/tmp` only**
  (one row per task x arm = 24 rows each default). Private SCORE carries
  candidate_features, bea_action_trace, bea_budget_trace,
  selected_candidates, score_outcome. Private event carries prompt,
  response, parsed_action, patch, test_stdout/stderr, provider_metadata.
  Public artifact includes only aggregate manifests with record counts,
  schema versions, `storage_class=tmp_private`,
  `path_publicly_serialized=false`, manifest hashes.
- **352/352 self-test checks pass**. Local no-env path truthfully
  `blocked_remote_not_enabled` (NOT a fake pass).
- **Strict claim boundary**: `claim_level=
  bea_derived_context_pack_downstream_paired_smoke_only`. NOT benchmark/
  leaderboard/performance/method-winner/calibration/promotion/default/
  runtime/EvidenceCore/downstream-value. CI pass does NOT require BEA
  improvement; zero/negative delta is valid.
- **Manual real-provider CI run `27945253824` passed**: 8 tasks x 3 arms = 24 live provider calls. Sparse control solved 2/8 (`solve_rate=0.25`, `tests_pass_rate=0.25`, `latency_seconds_mean=13.4355`); same-budget BM25 context pack solved 8/8 (`solve_rate=1.0`, `tests_pass_rate=1.0`, `latency_seconds_mean=1.1885`); BEA v0.3 context pack also solved 8/8 (`solve_rate=1.0`, `tests_pass_rate=1.0`, `latency_seconds_mean=1.579`). Primary BEA-vs-BM25 solve/test deltas are 0.0; BEA has +0.3905s mean latency and +161 prompt tokens. Both context arms beat sparse by +0.75 solve/test. `context_pack_signal_observed=false` for the primary contrast.
- **B16-F does NOT mutate BEA-0/BEA-1/BEA-2/BEA-3**: standalone phase,
  evaluator, artifact. The CI result is smoke-only and does not prove downstream value or method superiority.
- **Public artifact is aggregate-only**: `arm_results` (per-arm metrics),
  `paired_deltas` (3 contrasts), `task_family_results`, `family_signal_summary`,
  `honest_signals`, `private_score_manifest`, `private_event_manifest`,
  `forbidden_scan`, no-claim flags. No raw prompts/responses/patches/paths/
  snippets/candidate features/BEA action traces/pack composition/per-run
  rows.
- **Workflow stage `b16f_bea_derived_context_pack_paired_smoke`** added to
  `real-provider-benchmark.yml` (manual `workflow_dispatch` only;
  `enable_remote_models=false` default; dedicated sanitized upload;
  generic upload excluded; plan.json deleted; fail-closed on missing arms,
  zero provider_calls, missing paired_deltas, private manifest count
  mismatch, forbidden_scan fail).

## B16-G findings

- **B16-G explains B16-F's downstream tie via a live-provider atom
  ablation**. Five fixed arms: `control_sparse`, `target_only`,
  `support_only`, `distractor_plus_support`, `target_plus_support`.
  Eight fixed task families (reused from B16-F for comparability).
  Default 8 tasks x 5 arms = 40 live provider calls.
- **Atom composition per arm is deterministic and private** (written
  only to private SCORE JSONL under /tmp). Atoms: `target_file_cue`,
  `target_symbol_cue`, `support_module_cue`, `decisive_cue`,
  `distractor_file_cue`. `target_plus_support` carries all four target/
  support/decisive atoms; `distractor_plus_support` carries distractor
  + support + decisive (wrong-file cue); `target_only` carries target
  file + symbol only; `support_only` carries support + decisive only.
- **Primary contrasts**: `target_plus_support` vs
  `distractor_plus_support`; `target_plus_support` vs `support_only`;
  `target_only` vs `support_only`. **Secondary contrasts**: each
  context arm vs `control_sparse`. 7 contrasts x 13 metrics = 91
  paired delta records.
- **Mechanism summary records** (counts only):
  `support_atom_sufficient_count` (tasks where support_only solved),
  `target_atom_required_count` (tasks where target_only solved but
  support_only did NOT), `distractor_hurts_count` (tasks where
  distractor_plus_support did NOT solve but target_plus_support DID),
  `all_arms_solved_count`, `sparse_solved_count`.
- **221/221 self-test checks pass**. Local no-env path truthfully
  `blocked_remote_not_enabled` (NOT a fake pass). Self-test summary is
  counts-only in the public artifact (no detailed check list).
- **Strict claim boundary**: `claim_level=
  context_pack_atom_ablation_downstream_smoke_only`. NOT benchmark/
  leaderboard/performance/method-winner/calibration/promotion/default/
  runtime/EvidenceCore/downstream-value/BEA-superiority. CI pass does
  NOT require any atom to win; zero/negative delta is valid.
  `bea_superiority_claimed=false`.
- **Manual real-provider CI run `27947247773` passed**: 8 tasks x 5 arms
  = 40 live provider calls; forbidden scan pass; private SCORE/event manifests
  each record_count=40 with `path_publicly_serialized=false`; 221/221 self-test
  checks. Result: `control_sparse` solve/test=0.0, `target_only` solve/test=0.0,
  `support_only` solve/test=1.0, `distractor_plus_support` solve/test=1.0,
  `target_plus_support` solve/test=1.0.
- **Mechanism interpretation**: decisive support was sufficient on this bounded
  synthetic live-provider slice (`support_atom_sufficient_count=8`); target-only
  context was not sufficient (`target_atom_required_count=0`); distractor did
  not hurt when decisive support was present (`distractor_hurts_count=0`). This
  explains B16-F's BEA-vs-BM25 tie without claiming BEA superiority or
  downstream value proof.
- **B16-G does NOT mutate B16-F**: standalone phase, evaluator, artifact.
- **Public artifact is aggregate-only**: `arm_results`, `paired_deltas`,
  `task_family_results`, `mechanism_summary_records`, `honest_signals`,
  `private_score_manifest`, `private_event_manifest`, `forbidden_scan`,
  no-claim flags. No raw prompts/responses/patches/paths/snippets/atom
  compositions/candidate traces/per-run rows.
- **Workflow stage `b16g_context_pack_atom_ablation`** added to
  `real-provider-benchmark.yml` (manual `workflow_dispatch` only;
  `enable_remote_models=false` default; dedicated sanitized upload;
  generic upload excluded; plan.json deleted; fail-closed on missing
  arms, zero provider_calls, missing primary contrast, missing
  paired_deltas, private manifest count mismatch, forbidden_scan fail,
  bea_superiority_claimed not false).

## B16-H findings

- **B16-H resolves the main B16-G confound via a live-provider file-choice
  atom ablation**. B16-G's structured action schema and prompt forced
  edits to `target.py`, so `support_only` solving 8/8 did not prove the
  support atom alone can guide file choice. B16-H removes that confound:
  the prompt no longer says "only use target.py"; there is no global
  `ALLOWED_EDIT_FILES = {target.py}` set; the validator accepts only the
  per-task safe file set (target + distractor + support/config/cross-file
  module); arbitrary paths are never accepted; the chosen file is
  recorded ONLY in private SCORE/event JSONL under `/tmp`; only aggregate
  file-choice rates are exposed publicly.
- **Five fixed arms**: `control_sparse`, `file_choice_target_only`,
  `file_choice_support_only`, `file_choice_distractor_plus_support`,
  `file_choice_target_plus_support`. Eight fixed task families (reused
  from B16-F/B16-G). Default 8 tasks x 5 arms = 40 live provider calls.
- **Primary contrasts**: `file_choice_target_plus_support` vs
  `file_choice_support_only`; `file_choice_target_plus_support` vs
  `file_choice_distractor_plus_support`; `file_choice_target_only` vs
  `file_choice_support_only`. **Secondary contrasts**: each context arm
  vs `control_sparse`. 7 contrasts x 17 metrics = 119 paired delta
  records.
- **File-choice aggregate metrics** (NEVER actual filenames):
  `selected_target_file_rate`, `selected_distractor_file_rate`,
  `selected_support_file_rate`, `wrong_file_edit_rate`,
  `correct_file_before_first_edit_rate`.
- **Mechanism summary records** (counts only, all carry the
  "with_file_choice" qualifier because the confound has been removed):
  `support_only_sufficient_with_file_choice_count`,
  `target_atom_required_with_file_choice_count`,
  `distractor_hurts_with_file_choice_count`,
  `wrong_file_selection_count`,
  `all_arms_solved_count`, `sparse_solved_count`.
- **266/266 self-test checks pass**. Local no-env path truthfully
  `blocked_remote_not_enabled` (NOT a fake pass). Self-test summary is
  counts-only in the public artifact.
- **Strict claim boundary**: `claim_level=
  file_choice_atom_ablation_downstream_smoke_only`. NOT benchmark/
  leaderboard/performance/method-winner/calibration/promotion/default/
  runtime/EvidenceCore/downstream-value/BEA-superiority. CI pass does
  NOT require any atom to win; zero/negative delta is valid.
  `bea_superiority_claimed=false`. Docs say "on this bounded synthetic
  file-choice slice" for any sufficiency finding.
- **B16-H live result**: Manual real-provider CI run `27949115076` passed: 8 tasks x 5 arms = 40 live provider calls; forbidden scan pass; private SCORE/event manifests each have `record_count=40` and `path_publicly_serialized=false`; 266/266 self-tests. Results: `control_sparse` solve/test=0.0; `file_choice_target_only` solve/test=0.0 but selected target file rate=1.0; `file_choice_support_only` solve/test=1.0 and selected target file rate=1.0; `file_choice_distractor_plus_support` solve/test=1.0 and selected target file rate=1.0; `file_choice_target_plus_support` solve/test=1.0 and selected target file rate=1.0. Mechanism summary: `support_only_sufficient_with_file_choice_count=8`, `target_atom_required_with_file_choice_count=0`, `distractor_hurts_with_file_choice_count=0`, `wrong_file_selection_count=0`, `all_arms_solved_count=0`, `sparse_solved_count=0`. Interpretation: on this bounded synthetic file-choice slice, the decisive support cue was still sufficient to guide file choice; target-only context was insufficient; distractor did not hurt when decisive support was present. This is not a downstream value proof, BEA superiority claim, method-winner/default claim, benchmark/performance claim, or calibration claim.
- **Public artifact is aggregate-only**: `arm_results` (with file-choice
  rates), `paired_deltas`, `task_family_results`,
  `mechanism_summary_records`, `honest_signals`,
  `private_score_manifest`, `private_event_manifest`, `forbidden_scan`,
  no-claim flags. No raw prompts/responses/patches/paths/snippets/atom
  compositions/chosen file names/candidate traces/per-run rows.
  `input_summary.file_choice_confound_removed=true`.
- **Workflow stage `b16h_file_choice_atom_ablation`** added to
  `real-provider-benchmark.yml` (manual `workflow_dispatch` only;
  `enable_remote_models=false` default; dedicated sanitized upload;
  generic upload excluded; plan.json deleted; fail-closed on missing
  arms, zero provider_calls, missing primary contrasts, missing
  wrong-file/file-choice metrics, private manifest count mismatch,
  forbidden_scan fail,   `file_choice_confound_removed` not true,
  `bea_superiority_claimed` not false).

## B16-I findings

- **B16-I tests the mechanism exposed by B16-H**. B16-H removed the
  file-choice confound, but support-only still solved every task because
  the support cue was too decisive. B16-I redesigns the tasks to test
  whether support alone can be made non-decisive: target binding and
  support rule were expected to be needed together.
- **Five fixed arms**: `control_sparse`, `file_choice_target_only`,
  `file_choice_nondecisive_support_only`,
  `file_choice_distractor_plus_nondecisive_support`,
  `file_choice_target_plus_support`. Eight fixed task families (reused
  from B16-F/B16-G/B16-H). Default 8 tasks x 5 arms = 40 live provider
  calls.
- **Intended non-decisive support cue**: gives formula/invariant/
  dependency/config relation that was designed to still require target
  binding. It does NOT contain the exact final answer, exact target-file
  instruction, or target-symbol edit instruction. Run `27950908481`
  showed this design did not make support-only non-decisive: support-only
  still solved 8/8.
- **Primary contrasts**: `file_choice_target_plus_support` vs
  `file_choice_target_only`; vs
  `file_choice_nondecisive_support_only`; vs
  `file_choice_distractor_plus_nondecisive_support`. **Secondary**:
  `file_choice_target_only` vs
  `file_choice_nondecisive_support_only`; each context arm vs
  `control_sparse`. 8 contrasts x 17 metrics = 136 paired delta records.
- **Mechanism summary records** (7 counts):
  `target_support_conjunction_required_count` (tps solved but NEITHER
  target_only NOR support_only solved),
  `support_only_sufficient_count`, `target_only_sufficient_count`,
  `distractor_hurts_count`, `wrong_file_selection_count`,
  `all_arms_solved_count`, `sparse_solved_count`.
- **306/306 self-test checks pass**. Local no-env path truthfully
  `blocked_remote_not_enabled` (NOT a fake pass). Counts-only self-test
  fields (`self_test_checks_total`, `self_test_checks_passed`); NO
  `self_test_summary` or `self_test_checks` list published.
- **Strict claim boundary**: `claim_level=
  target_support_conjunction_downstream_smoke_only`. NOT benchmark/
  leaderboard/performance/method-winner/calibration/promotion/default/
  runtime/EvidenceCore/downstream-value/BEA-superiority. CI pass does
  NOT require the conjunction to hold. `bea_superiority_claimed=false`.
- **B16-I live result**: Manual real-provider CI run `27950908481` passed: 8 tasks x 5 arms = 40 live provider calls; forbidden scan pass; private SCORE/event manifests each have `record_count=40` and `path_publicly_serialized=false`; 306/306 self-tests. Results: `control_sparse` solve/test=0.0; `file_choice_target_only` solve/test=0.125 and selected target file rate=1.0; `file_choice_nondecisive_support_only` solve/test=1.0 and selected target file rate=1.0; `file_choice_distractor_plus_nondecisive_support` solve/test=1.0 and selected target file rate=1.0; `file_choice_target_plus_support` solve/test=1.0 and selected target file rate=1.0. Mechanism summary: `target_support_conjunction_required_count=0`, `support_only_sufficient_count=8`, `target_only_sufficient_count=1`, `distractor_hurts_count=0`, `wrong_file_selection_count=0`, `all_arms_solved_count=0`, `sparse_solved_count=0`. Interpretation: the intended non-decisive support cue was still sufficient on this bounded synthetic file-choice slice; target+support did not improve over support-only; target-only solved only 1/8; distractor did not hurt when support was present. This means the target-support conjunction was not observed. This is not a downstream value proof, BEA superiority claim, method-winner/default claim, benchmark/performance claim, or calibration claim.
- **B16-I does NOT mutate B16-F/B16-G/B16-H**: standalone phase,
  evaluator, artifact.
- **Workflow stage `b16i_target_support_conjunction`** added to
  `real-provider-benchmark.yml` (manual `workflow_dispatch` only;
  `enable_remote_models=false` default; dedicated sanitized upload;
  generic upload excluded; plan.json deleted; fail-closed on missing
  arms, zero provider_calls, missing primary contrasts, missing
  wrong-file/file-choice metrics, private manifest count mismatch,
  `support_cue_nondecisive` not true, `bea_superiority_claimed` not
  false, forbidden_scan fail).

## B16-J findings

- **B16-J is the LAST B16 atom-redesign attempt**. It fixes the B16-I failure by using role-neutral candidate filenames and full-prompt leakage self-tests; target/distractor roles stay private and public artifacts stay aggregate-only.
- **Five fixed arms**: `control_sparse`, `ambiguous_target_only`, `ambiguous_support_only`, `ambiguous_distractor_plus_support`, `ambiguous_target_plus_support`. Eight fixed task families; default 8 tasks x 5 arms = 40 live provider calls.
- **329/329 self-test checks pass**. Local no-env path truthfully `blocked_remote_not_enabled`. Counts-only self-test fields (`self_test_checks_total`, `self_test_checks_passed`).
- **B16-J live result**: Manual real-provider CI run `27953321504` passed: 8 tasks x 5 arms = 40 live provider calls; forbidden scan pass; private SCORE/event manifests each have `record_count=40` and `path_publicly_serialized=false`; 329/329 self-tests. Results: `control_sparse` solve/test=0.0, selected_target_file_rate=0.125, wrong_file_edit_rate=0.875; `ambiguous_target_only` solve/test=0.0, selected_target_file_rate=1.0; `ambiguous_support_only` solve/test=0.25, selected_target_file_rate=0.25, selected_distractor_file_rate=0.625, wrong_file_edit_rate=0.75; `ambiguous_distractor_plus_support` solve/test=0.625, selected_target_file_rate=0.625, selected_distractor_file_rate=0.375; `ambiguous_target_plus_support` solve/test=1.0, selected_target_file_rate=1.0, wrong_file_edit_rate=0.0. Primary deltas for `ambiguous_target_plus_support`: vs `ambiguous_support_only` solve/test delta=+0.75, wrong_file_edit_rate delta=-0.75, selected_target_file_rate delta=+0.75; vs `ambiguous_target_only` solve/test delta=+1.0; vs `ambiguous_distractor_plus_support` solve/test delta=+0.375, wrong_file_edit_rate delta=-0.375. Mechanism summary: `target_support_conjunction_required_count=6`, `support_only_sufficient_count=2`, `target_only_sufficient_count=0`, `distractor_hurts_count=3`, `ambiguous_support_wrong_binding_count=6`, `wrong_file_selection_count=6`, `all_arms_solved_count=0`, `sparse_solved_count=0`. Interpretation: after role-neutral filenames and full-prompt leakage tests, B16-J finally isolated a bounded target+support conjunction signal on this synthetic slice; support-only was no longer sufficient on most tasks (2/8), target-only solved 0/8, and adding target binding to ambiguous support solved 8/8. This is still a smoke-level synthetic live-provider mechanism result, not downstream value proof, BEA superiority, method-winner/default, benchmark/performance, calibration, promotion, or runtime/EvidenceCore change.
- **Stop rule outcome**: B16-J isolated a bounded conjunction signal, so do not run B16-K; move next to external BEA scale / broader real benchmark work.
- **Strict claim boundary**: `claim_level=ambiguous_support_conjunction_downstream_smoke_only`. NOT downstream value/BEA superiority/method winner/default/benchmark/calibration/promotion/runtime/EvidenceCore claim. `bea_superiority_claimed=false`.

## BEA-FD1 findings

- **BEA-FD1 replays both exact BEA-4/5 protocols via subprocess**: BEA-4
  (CI 27957586271, expected 120/840) and BEA-5 (CI 28003522632, expected
  119/833). Parses private SCORE JSONL files, classifies v0.3 outcomes into
  12 fixed categories, publishes records-only aggregate decomposition tables.
  Fixed protocol: no budget/methods CLI inputs.
- **174/174 self-test checks pass**.
- **Public artifact records-only** with natural keys per oracle guidance:
  (source_phase, benchmark, category, category_availability), etc.
- **Metric loss**: quality = max(0, baseline-treatment); latency = max(0,
  treatment-baseline). Records include loss_sum/loss_mean/delta_mean.
- **Available categories**: gold_file_absent, correct_file_wrong_span,
  too_many_anchor_slots, early_stop_too_early, budget_spent_on_low_marginal_gain,
  latency_without_quality_gain. **Unavailable**: redundant_same_file_candidates
  (missing_trace), risk_penalty_removed_gold (missing_trace),
  missing_support_candidate/support_selected_without_target/target_selected_without_support
  (no_support_label).
- **Manual BEA-FD1 CI run `28011901294` passed**: status `bea_fd1_decomposition_pass`, records_decomposed=239, private decomposition rows=86040, forbidden_scan=pass. Aggregate tables expose category counts, metric-loss, win/tie/loss, benchmark buckets, and candidate-source buckets without private rows. Dominant available categories are low marginal gain / latency cost, gold-file absence, and correct-file/wrong-span; support-target categories remain unavailable until private SCORE has role labels.
- **Strict claim boundary**: `claim_level=bea_fd1_failure_decomposition_smoke_only`.
  NOT benchmark/leaderboard/performance/method-winner/calibration/promotion/
  default/runtime/EvidenceCore/downstream-value. `provider_calls=0`.
## BEA-v0.4-P1 findings

- **BEA-v0.4-P1 setwise role-proxy smoke implemented**: eval-local
  deterministic role-proxy setwise selection policy
  (`setwise_complementarity_v0_4_p1`) compared against BEA v0.3 and
  same-budget controls on a fresh small external smoke slice. P1 smoke
  evidence only, NOT v0.4 proof/winner/default/calibration.
- **269/269 self-test checks pass**.
- **Required arms (6; RRF cheap + stable)**: `bm25_prefix_same_budget`,
  `bea_v0_3_anchor_span_latency`, `role_proxy_only_same_budget`,
  `setwise_complementarity_v0_4_p1`, `seeded_random_same_budget`,
  `rrf_same_budget`. Treatment: `setwise_complementarity_v0_4_p1`.
- **Role-proxy fixed enum (deterministic, runtime-clean)**:
  `target_proxy`, `support_proxy`, `unknown`. No gold/private labels.
  Signals: method agreement, BM25/RRF/regex/symbol source, query/path
  token overlap, AST/path role heuristics, span tightness, same-file/
  cross-file relation, source diversity.
- **v0.4 P1 setwise selection rules (frozen, no post-hoc tuning)**:
  at least one target_proxy if available; prefer support_proxy from a
  different file/symbol family; penalize repeated same-file selections;
  reward novelty/source diversity/span tightness. Frozen weights:
  target=0.40, support_cross_file=0.20, source_diversity=0.15,
  span_tight=0.10, novelty=0.10, dup_file_penalty=-0.35,
  weak_support_penalty=-0.15.
- **Fresh small external smoke protocol (success-quota)**:
  records_successful>=30, contextbench_successful>=20,
  repoqa_successful>=10. Mandatory excluded windows BEA-2/3/4
  (ContextBench [40,160), RepoQA [20,80)). BEA-5 overlap disclosed not
  excluded. This is P1 smoke evidence, not fresh disjoint validation.
- **Hard gates**: role_proxy_assignment_rate>=0.70,
  target_proxy_available_rate>=0.50, support_proxy_available_rate>=0.30,
  unknown_only_record_rate<=0.30, setwise_selection_diff_rate_vs_v03>=0.25,
  mean_duplicate_file_count_v04<=v03,
  mean_candidate_source_diversity_v04>=v03, quality safety
  (file_recall/mrr within 0.05, span within 0.02, latency within 1.25x),
  at least one directional improvement.
- **Public artifact records-only** with natural keys:
  `source_run_records`, `arm_metric_records`, `arm_delta_records`,
  `role_proxy_summary_records`, `setwise_behavior_records`,
  `failure_family_records`, `win_tie_loss_records`,
  `availability_records`, aggregate-only
  `private_score_manifest`/`private_decision_manifest`/
  `private_role_proxy_manifest`, `hard_gate_records`, `failure_category_count_records`, `forbidden_scan`.
- **Statuses**: `bea_v04_p1_smoke_pass`, `partial_directional_signal`,
  `no_go_proxy_unavailable`, `no_go_no_selection_change`,
  `no_go_quality_regression`, `unavailable_with_reason`,
  `offline_counterfactual_replay`, `fail_forbidden_scan`,
  `fail_schema_contract`.
- **Default no-network artifact truthfully `unavailable_with_reason`**:
  provider_calls=0, forbidden_scan=pass, self_test_checks_total=269,
  self_test_checks_passed=269, empty record tables.
- **Strict claim boundary**: `claim_level=bea_v04_p1_setwise_role_proxy_smoke_only`.
  NOT benchmark/leaderboard/performance/method-winner/calibration/promotion/
  default/runtime/EvidenceCore/downstream-value. NOT v0.4 proof. NOT the
  full v0.4 matrix. `provider_calls=0`.
- **Manual CI run `28017063082` passed fail-closed and produced a P1 No-Go / weak negative**: status `no_go_proxy_unavailable`, records_successful=38 (ContextBench 20, RepoQA 18), attempted=46, excluded=8, private SCORE rows=228, decision rows=190, role-proxy rows=760. The current role proxies assigned every candidate but produced target_proxy_available_rate=0.0 and setwise_selection_diff_rate_vs_v03=0.105263 (<0.25). Quality did not catastrophically regress versus v0.3, but did not improve: file_recall@10 and MRR deltas are 0.0, span_f0.5@10 delta=-0.003036, latency delta=+0.001686s, quality_per_latency delta=-0.000809. Do not advance this target-role proxy design to a full v0.4 matrix without improving target-role features.

## BEA-v0.4-P2 findings

- **BEA-v0.4-P2 target-role proxy repair smoke completed**: local checkpoint
  `d59492f`, manual CI run `28020331024`.
- **Result is a valid P2 No-Go, not a v0.4 proof**: status
  `no_go_target_proxy_still_unavailable`, records_successful=38
  (ContextBench 20, RepoQA 18), attempted=46, excluded=8,
  forbidden_scan=pass, self-test 335/335, private SCORE rows=228,
  decision rows=190, role-proxy rows=760, target-feature rows=760.
- **Target-role repair worked but did not make setwise selection useful**:
  target_proxy_available_rate improved from 0.0 to 1.0 and
  target_proxy_selected_rate_p2=1.0, but support_proxy_available_rate_p2=0.0.
  P2-vs-P1 selection difference remained 0.0; P2-vs-v0.3 selection
  difference remained 0.105263 (<0.25).
- **Quality safety held, but no algorithmic advance**: versus v0.3,
  file_recall@10 and MRR deltas are 0.0, span_f0.5@10 delta=-0.003036,
  latency delta=+0.001789s, quality_per_latency delta=-0.000857. Do not
  advance to the full v0.4 matrix until a support/complementarity proxy
  produces nonzero support availability and materially changes selection.


## BEA-v0.4-P3 findings

- **BEA-v0.4-P3 support/complementarity proxy repair smoke completed**: local checkpoint `7f58f66`, manual CI run `28022595796`.
- **Result is a valid final role-proxy No-Go, not a v0.4 proof**: status `no_go_support_proxy_degenerate`, records_successful=38 (ContextBench 20, RepoQA 18), attempted=46, excluded=8, forbidden_scan=pass, self-test 400/400, private SCORE rows=266, decision rows=190, role-proxy rows=760, support-feature rows=760, pair-feature rows=38.
- **Support/complementarity repair over-corrected**: target and support availability/selection all reached 1.0, and target-support pairs reached 1.0, but support was degenerate: support_proxy_available_rate_p3=1.0 (above <=0.90 gate) and mean_support_candidates_per_record_p3=18.289474 (above <=8.0 gate).
- **Selection changed but quality regressed**: P3 selection differed from v0.3/P2/P1 at 0.5/0.394737/0.394737, but versus v0.3 file_recall@10 delta=-0.052632, MRR delta=-0.155263, span_f0.5@10 delta=-0.003531, latency +0.001730s, quality_per_latency 0.015992 vs 0.016856.
- **Role-proxy stop rule triggered**: do not run legacy role-proxy P4/P5, do not enter the full v0.4 matrix from this role-proxy design, and do not tune v0.31/v0.32. Next algorithm work should pivot to direct FD1-objective setwise acquisition.

## BEA-FD2-A findings

- **BEA-FD2-A direct FD1-objective setwise smoke completed**: local checkpoint `709b0cb`, manual CI run `28025382422`.
- **Result is a bounded No-Go, not a v0.4 advance**: status `no_go_no_fd1_loss_reduction`, records_successful=38 (ContextBench 20, RepoQA 18), attempted=46, excluded=8, forbidden_scan=pass, self-test 373/373.
- **Selection changed strongly but the objective failed**: FD1-weighted selection differed from v0.3 at 0.710526 and from coverage-only at 0.684211, so the treatment was not a no-op.
- **Composite loss and quality regressed**: composite FD1 loss worsened to 0.756181 versus v0.3 0.397802 and coverage-only 0.748783; file_recall@10 fell to 0.684211 versus v0.3 0.763158, and MRR fell to 0.516228 versus v0.3 0.569737. Span and latency gates passed, but FD1-loss and quality gates failed.
- **Decision**: do not run FD2-B from this objective, do not tune v0.31/v0.32 weights, and do not resurrect role proxies. The direct FD1-weighted objective must be treated as a failed algorithm hypothesis on this bounded frame.

## BEA-FD2-A1 findings

- **BEA-FD2-A1 failure attribution replay completed**: local checkpoint `67a6d61`, manual CI run `28027342996`.
- **Replay matched and attribution passed**: status `bea_fd2a1_attribution_replay_pass`, records_attributed=38, records_regressed=38, private trace counts exact (190/190/190/950/1), forbidden_scan=pass, self-test 404/404.
- **Dominant mechanism**: `latency_category_non_actionable_or_dominating` fired on 38/38 regressed records. Secondary mechanisms were much smaller: redundancy_overcorrection 4/38, gold_file_displacement 3/38, aggregate_weight_category_collision 3/38.
- **Candidate availability is not the blocker**: `candidate_availability_limit=0/38`; better candidates existed above budget and 2×budget for 38/38 records.
- **Decision**: FD2-A failed because its objective optimized a latency-loss category that was not actionable by the candidate-level proxy. Next objective work must remove/decouple non-actionable latency pressure and protect file-recall/gold-file utility; do not run FD2-B from FD2-A, do not revive role proxies, and do not tune v0.31/v0.32 weights.

## BEA-v1-P1 findings

- **BEA-v1-P1 Actionability Audit completed**: local checkpoint `6e661f1`, CI fix commits `b63db2a` and `9c72ae2`, manual CI run `28076434237`.
- **Audit replay passed but v1-A was rejected**: the workflow regenerated the FD1 private decomposition under `/tmp`, validated the FD1 replay artifact, parsed 86040 private decomposition rows, and recovered 239 composite `(source_phase, private_record_id)` groups. Public artifact status is `no_go_retrieval_availability_limit`, not pass.
- **Actionability result**: all 12 FD1 failure categories were mapped over 6 action layers (72 cells). `latency_without_quality_gain` is explicitly non-actionable by candidate selection and belongs to `non_actionable_accounting`, preserving the FD2-A1 lesson.
- **File-selector ceiling result**: `gold_file_absent` denominator=119, but the private lower-bound recoverable count is only 1. Lower-bound rate=0.004184 (<0.05 gate), unrecoverable candidate-unavailable lower-bound count=118, retrieval-availability rate=0.991597. The public upper bound remains 119/239=0.497908 but is not sufficient to authorize v1-A.
- **Decision**: do not start BEA-v1-A coverage-preserving selector on this FD1 evidence. The next BEA v1 work should target candidate availability / retrieval expansion evidence (or collect trace fields needed for span/stopping ceilings) before selector-only optimization.

## BEA-v1-P2 findings

- **BEA-v1-P2 Candidate Availability / Retrieval Reach Smoke completed**: local checkpoint `2940750`, retrieval flag fix `d0daee7`, runtime-safe retrieval hardening `d4de762`, manual CI run `28093864524`.
- **Status**: `no_go_retrieval_reach_latency_or_pool_cost`. The workflow regenerated FD1 private decomposition under `/tmp`, validated the replay, ran 4 retrieval-reach arms over the 119-record `gold_file_absent` denominator, wrote 476 private reach rows, and published aggregate-only tables.
- **Availability result**: baseline current pool reached 32/119 files. Depth-only expansion reached 59/119 (+27, availability lift 0.226891) within cost thresholds; query-anchor reached 60/119 (+28) but exceeded cost; combined depth+query reached 81/119 (+49) but mean pool 202.38 (10.13×) and latency 7.025s (3.89×) exceeded safety gates.
- **Decision**: candidate availability is empirically improvable, so the v1-P1 pure retrieval-unavailable story is refined. However, naive broad expansion is not acceptable. Do not start BEA-v1-A selector from the combined arm. The next BEA v1 step should be a constrained retrieval policy that preserves depth-only reach gains while bounding pool/latency, with latency outside candidate relevance scoring.

## BEA-v1-P3 findings

- **BEA-v1-P3 Constrained Retrieval Policy Smoke completed**: local checkpoint `6801e2b`, manual CI run `28102428194`.
- **Status**: `no_go_p3_cost_exceeded`. The workflow regenerated FD1 private decomposition under `/tmp`, validated replay, ran 3 retrieval-policy arms over the 119-record file-miss denominator, wrote 357 private policy rows, and published aggregate-only tables.
- **Mechanism result**: P3 retained almost all P2 depth-only reach (58/119 vs 59/119; +26 newly reachable vs +27) while reducing mean pool from 68.18 to 41.50 (2.08× baseline vs 3.41× for P2 depth). Efficiency improved to 1.208122 newly reachable per added candidate, above P2 depth-only and combined.
- **No-Go reason**: latency safety failed. P3 mean latency was 3.645s, 2.17× baseline, above the 2.0× gate. This indicates the next bottleneck is retrieval-action scheduling latency, not candidate relevance scoring.
- **Decision**: do not promote this scheduler to v1-A input. If BEA v1 continues, isolate latency overhead from sequential/repeated retrieval actions and test a latency-aware action scheduler at the retrieval-action layer, still keeping latency outside candidate relevance scoring.

## BEA-v1-P4 findings

- **BEA-v1-P4 Latency-Aware Retrieval Action Scheduler Smoke completed**: local checkpoint `87a266a`, diagnostic upload patch `3ffeb23`, manual CI run `28118888584`.
- **Status**: `bea_v1_p4_latency_aware_retrieval_scheduler_pass`. The workflow regenerated FD1 private decomposition under `/tmp`, validated replay, ran 4 fixed P4 arms over the 119-record file-miss denominator, wrote 476 private scheduler rows, and published aggregate-only tables.
- **Mechanism result**: baseline reached 32/119. P2 depth reached 59/119 (+27) with 3.41× pool and 1.18× latency. P3 reference reached 58/119 (+26) with 2.17× latency. P4 reached 56/119 (+24), preserving >=75% of P2 depth gain, with pool 2.056×, latency 1.750×, and 19.38% lower latency than P3. Hard-cap violations were 0 and action count was reduced on 119/119 records.
- **Decision**: P4 validates the retrieval-action scheduling layer as a runtime-clean candidate-availability lever. It still is not a default-policy, method-winner, benchmark-performance, or runtime-promotion claim; selector relevance remains unresolved (mean first-gold rank 25.625; 48 records above budget). Next work should be reviewed as a bounded follow-on from this scheduler pass, not as broad retrieval expansion or latency-in-relevance scoring.

## BEA-v1-P4H findings

- **BEA-v1-P4H Disjoint Scheduler Validation completed as denominator No-Go**: local checkpoint `dee1ce1`, full-frame scan fix `0dfeb27`, manual CI run `28132121958`.
- **Status**: `no_go_p4h_insufficient_denominator`. The workflow regenerated FD1 private decomposition under `/tmp`, validated the 239 / 86040 replay, and ran the raw external full-frame disjoint denominator scan. It produced a valid aggregate artifact, but the heldout denominator reached only 73/80, so scheduler arms were not executed.
- **Denominator result**: exact FD1 private raw-key exclusion removed 239 prior BEA-4/5 records. The scan fetched 266 ContextBench and 100 RepoQA rows, excluded 162 ContextBench + 77 RepoQA exact prior rows, attempted 104 ContextBench + 23 RepoQA candidate rows, and found 61 ContextBench + 12 RepoQA baseline file-miss records. `raw_scan_attempted_records=127`, `raw_scan_yield_file_miss_records=73`, `private_scheduler_rows=0`, and `retrieval_policy_executed=false`.
- **Decision**: P4H does not validate P4 on a disjoint heldout denominator and does not authorize P5 selector/reranker work, BEA-v1-A, runtime promotion, or broad retrieval expansion. P4 remains a bounded same-frame scheduler pass; the immediate blocker is insufficient disjoint heldout file-miss denominator under the current ContextBench/RepoQA frame.

## BEA-v1-P4I findings

- **BEA-v1-P4I Disjoint Denominator Reservoir Audit completed as reservoir No-Go**: local checkpoint `a834733`, manual CI run `28137455572`.
- **Status**: `no_go_disjoint_denominator_reservoir_insufficient`. P4I scanned the full supported ContextBench/RepoQA Python frame with only the baseline/current candidate-pool diagnostic arm. It did not run P2/P3/P4 scheduler arms, selector/reranker logic, retrieval expansion, or provider calls.
- **Reservoir result**: the audit fetched 366 raw rows, excluded 239 exact BEA-4/5 prior raw keys from FD1 private replay, attempted 127 non-prior candidate rows, observed 54 baseline-reached rows, and found only 73 FD1-excluded file-miss reservoir records. `reservoir_upper_bound_count=73`, `qualified_denominator_reservoir_count=0`, and `p4h_overlap_resolved=false` because P4H exact selected keys are not committed.
- **Decision**: P4H's denominator blocker is confirmed as a source/reservoir limitation in the currently supported ContextBench/RepoQA Python frame, not just a fixed-tail sampling error. Do not enter frozen P4H rerun, P5 selector/reranker, BEA-v1-A, runtime promotion, method-winner claims, or broad retrieval expansion from P4I.

## BEA-v1-P4J findings

- **BEA-v1-P4J Cross-Source File-Miss Reservoir Unlock Audit completed as unqualified No-Go**: local checkpoint `18671d8`, diagnostic/fail-closed patch `18126f4`, manual CI run `28146407493`.
- **Status**: `no_go_cross_source_reservoir_unqualified`. P4J scanned only already-supported cross-source frames with the baseline/current candidate-pool replay diagnostic arm: ContextBench `contextbench_verified/train` with `language_filter=all` and RepoQA non-Python asset languages. It did not run scheduler arms, selector/reranker logic, provider calls, frozen P4 rerun, P5, or BEA-v1-A.
- **Reservoir result**: P4J found a large FD1-excluded upper-bound file-miss reservoir: `denominator_count=333`, `reservoir_upper_bound_count=333`, `cross_source_non_python_reservoir_count=272`, `cross_source_python_reservoir_count=61`. It fetched 780 rows, attempted 618 rows, excluded 162 exact FD1 BEA-4/5 prior raw keys, selected 333 file-miss records, and wrote 618 private reservoir scan rows under `/tmp` only.
- **Unqualified reason**: `qualified_cross_source_reservoir_count=0` and `p4h_p4i_overlap_resolved=false`, because P4H/P4I exact selected keys remain unavailable/aggregate-only. The 333-record count is an upper bound, not a locked all-prior-disjoint denominator.
- **Decision**: P4J proves the current-source Python-frame reservoir shortage is not the whole source story, but it still does not authorize locked-P4 validation, frozen P4 rerun, P5 selector/reranker, BEA-v1-A, runtime promotion, method-winner claims, or broad retrieval expansion. Any next phase must first resolve/lock exact P4H/P4I overlap or define a new strictly bounded source-audit contract; it cannot treat the 333 upper-bound reservoir as ready.

## BEA-v1-P4K findings

- **BEA-v1-P4K Exact Overlap Resolution & Locked Reservoir Audit completed as locked-reservoir-ready for design only**: local checkpoint `c6b7fc9`, manual CI run `28151914531`.
- **Status**: `cross_source_locked_reservoir_ready_for_locked_p4_validation_design`. P4K reran the exact reconstruction audit under `/tmp`, reconstructed P4H `73/73`, P4I `73/73`, and P4J `333/333` with the committed split `61` Python + `272` non-Python.
- **Overlap result**: P4J's 61 Python rows overlapped P4H/P4I; the post-overlap locked cross-source reservoir is `272/80`, entirely non-Python (`non_python_locked_reservoir_count=272`, `python_locked_reservoir_count=0`).
- **Boundary**: This resolves P4J's unqualified-reservoir blocker and authorizes only the design of a later locked-denominator P4 validation phase. P4K itself did not run scheduler arms; the separate P4L phase later executed the locked scheduler validation. P4K does not authorize frozen P4 rerun, P5 selector/reranker, BEA-v1-A, runtime promotion, method-winner claims, or broad retrieval expansion.

## BEA-v1-P4L findings

- **BEA-v1-P4L Locked Non-Python P4 Scheduler Validation completed as scheduler-validation pass**: local checkpoint `5922826`, denominator-drift classifier fix `251ae2b`, P4 treatment hard-cap gate fix `6034b3d`, heartbeat workflow patch `e98839b`, manual CI run `28184096209`.
- **Status**: `bea_v1_p4l_locked_non_python_scheduler_validation_pass`. P4L reconstructed the full P4J/P4K split exactly (`333/61/272`), locked the non-Python denominator at `272`, executed the four frozen scheduler arms, and wrote 1088 private arm-outcome rows under `/tmp` only.
- **Scheduler result**: baseline current pool reached `0/272`; P2 depth-only reference reached `55/272`; P3 constrained reference reached `55/272`; frozen P4 latency-aware scheduler reached `52/272`. P4 retained `0.945455` of the P2 gain, had `p4_vs_p3_latency_ratio=0.656763`, `p4_latency_reduction_vs_p3=0.343237`, `p4_pool_growth_ratio=2.176782`, and zero P4-treatment hard-cap violations. P2 had 3 hard-cap violations, but these are reference diagnostics only.
- **Boundary**: P4L validates the frozen P4 retrieval-action scheduler on the locked non-Python denominator. It does not authorize P5 selector/reranker, BEA-v1-A selector work, runtime/default promotion, method-winner claims, broad retrieval expansion, frozen P4 reruns, or any future locked-P4 promotion/default step.

## BEA-v1-N1 findings

- **BEA-v1-N1 Frozen P4 + Span-Refiner Smoke completed as rank-blocked No-Go**: local checkpoint `c77f8d1`, diagnostics patch `9c6cd41`, openlocus binary fix `c51d20b`, full-file refiner checkpoint `e04b2fa`, rank-aware D1 checkpoint `6b152d2`, auxiliary line-lookup fix `0ddc2e8`, manual CI run `28245155237`.
- **Status**: `no_go_n1_inadequate_top10_actionable_denominator`. N1 replayed FD1 private decomposition, reconstructed the frozen P4L/P4K denominator, and validated D0 scheduler preservation over the locked 272-record non-Python denominator: baseline `0`, P2 `55`, P3 `55`, P4 `52`, P4 treatment hard-cap `0`.
- **Span result**: D1 total / pool span-opportunity denominator was adequate at `40`, but D1 top-10 actionable was `0` and D1 rank-blocked was `40`. The full-file same-file refiner improved 8/40 local gold-file spans and regressed 0/40, but those records were all outside top-10; since N1 forbids evidence reorder, canonical `SpanF0.5@10` cannot be used to claim span improvement.
- **Decision**: N1 does not validate a span-only repair. The next bounded BEA-v1 work should investigate rank/pack actionability for moving gold-file evidence into the actionable top-10 pack, while preserving the no-P5/no-BEA-v1-A/no-default-promotion boundary until separately authorized.

## BEA-v1-N2 findings

- **BEA-v1-N2 Rank/Pack Actionability Decomposition completed as decomposition pass**: local checkpoint `e4c4d54`, stability checkpoint `e1406a5`, candidate-order classification fix `7c90213`, D0 latency display fix `a5b519b`, empirical CI source `28272769423`.
- **Artifact provenance**: the public artifact uses the validated CI `28272769423` result and applies a local records-only correction of one non-gating D0 latency display field (`p4_p3_latency_ratio_observed=0.662177`) from the closed N1 artifact. Later reruns `28275921872` and `28277110197` produced no contradictory N2 evidence because they failed before a valid N2 artifact.
- **Status**: `n2_rank_pack_actionability_decomposition_pass`. D2 reconstructed exactly (`40/40`) and all rows were classified (`40/40`). First gold-file rank bucket was `rank_21_50=40/40`; top-20 recovery was `0/40`, top-50/top-100 recovery `40/40`, unique-file top-10 recovery `0/40`, evidence materializable `40/40`, hard-cap violations `0`, and public scanner `pass`.
- **Mechanism**: primary blocker was `extra_depth_append_blocked=40/40`. The N1 span bottleneck is therefore a rank/pack actionability problem where the gold file is consistently available in the deeper pool but not appended/merged into the actionable pack.
- **Decision**: N2 authorizes only extra-depth merge-order design. It does not authorize implementation, P5, BEA-v1-A, selector/reranker execution, runtime/default promotion, method-winner claims, broad retrieval expansion, downstream-value claims, or frozen P4 rerun.

## BEA-v1-N3 findings

- **BEA-v1-N3 Extra-Depth Merge-Order Design Simulation completed as inconclusive design result**: local checkpoint `76ebd32`, manual CI `28278662782`, status `n3_merge_order_design_inconclusive`.
- **Result**: D3 reconstructed exactly (`40/40`) and scanner passed. Frozen P4 order recovered `0/40`; fixed interleave recovered `8/40`; early extra-depth quota 3 recovered `10/40`; bounded promotion after primary prefix 4/3 recovered `10/40`. Best recovery rate was `0.25`, below the predeclared `0.50` pass gate. The best arms preserved top-10 retention (`0.975`), materialized recovered evidence (`1.0`), and had hard-cap violations `0`, but recovery did not cross.
- **Decision**: these simple bounded merge-order designs do not solve the N2 rank/pack blocker. N3 does not authorize implementation, P5, BEA-v1-A, selector/reranker execution, runtime/default promotion, method-winner claims, broad retrieval expansion, downstream-value claims, or frozen P4 rerun.

## BEA-v1-P0-1 trace-gap audit findings

- **BEA-v1-P0-1 Trace Gap Audit completed as a scanner-validated trace-surface phase**: status `trace_gap_audit_pass`, self-test `5/5`, forbidden scan `pass`.
- **Result**: the audit reads committed FD1, P1, FD2-A1, P4L, N2, and N3 artifacts and publishes sanitized per-gap records for all 12 FD1 categories. Trace availability is `sanitized_available=3`, `private_only_needs_public_export=3`, `missing_label=3`, `missing_trace=2`, and `aggregate_only_insufficient_for_deep_research=1`.
- **Decision**: next work should close the data surface, not implement a policy. Authorized follow-ups are actionability-matrix refresh, sanitized scheduler dataset export, support-link labeling inputs, and redundancy/risk/stop trace preservation. P0-1 does not authorize P5, BEA-v1-A, selector/reranker execution, runtime promotion, broad retrieval expansion, method-winner claims, or downstream-value claims.

## BEA-v1-P0-2 actionability-matrix refresh findings

- **BEA-v1-P0-2 Actionability Matrix Refresh completed as a records-only join**: status `actionability_matrix_refresh_pass`, self-test `6/6`, forbidden scan `pass`, refreshed cells `72/72`, causal P1 cell classes unchanged.
- **Result**: readiness summary is `ready_sanitized_trace=10`, `blocked_private_export=11`, `blocked_missing_label=18`, `blocked_missing_trace=12`, `blocked_aggregate_only=3`, and `not_applicable_by_layer=18`.
- **Decision**: P0-2 confirms that the next BEA-v1 phase should export or design trace inputs before any new policy experiment. It authorizes scheduler dataset export and support/redundancy/risk/stop trace-surface work only; it does not authorize P5, BEA-v1-A, selector/reranker execution, implementation, runtime promotion, broad retrieval expansion, method-winner claims, or downstream-value claims.
