# B16-A Minimal Mock Downstream Paired Run (Public Aggregate-Only Artifact)

## Scope and claim boundary

B16-A is the **first B16-style downstream-agent empirical run that is
not control-plane-only**. It executes a real edit/test loop on tiny
synthetic Python workspaces under transient `/tmp` directories and
produces behavior metrics. The agent is a **deterministic mock agent**
(no live LLM, no provider calls, no remote calls) whose behavior
depends on the provided context pack.

B16-A is explicitly **not** a live LLM downstream agent run, **not** a
downstream agent value claim, **not** an external benchmark performance
claim, **not** a live agent generalization claim, **not** a real user
task claim, **not** a promotion, **not** a default/policy change, and
**not** a runtime/retriever/pack/backend/EvidenceCore semantic change.

B16-A **does not** claim downstream agent value, **does not** promote
any candidate, **does not** change runtime/retriever/pack/backend/
default-policy/EvidenceCore semantics, **does not** claim live agent
generalization, **does not** claim external benchmark performance, and
**does not** claim a real user task. The committed artifact is
aggregate-only: no task IDs, workspace paths, file paths, source
snippets, patches/diffs, test output, raw event logs, per-run rows,
private IDs, or provider/model info beyond the deterministic mock
identity.

- Claim level: `deterministic_mock_downstream_paired_smoke_only`.
- Status: `mock_downstream_paired_smoke_pass` on success; mode
  `public_aggregate_synthetic_micro_tasks`; phase `B16-A`.
- B16-A is **eval/diagnostic only**. It is NOT a benchmark result, NOT
  a live downstream agent value claim, NOT a runtime-clean general
  algorithm claim, NOT an OOD temporal claim, and NOT a QuIVer systems
  claim.

### D5-A0 -> B16-A relation

```text
D5-A0 automated E/S calibration smoke (retrieval-only aggregate)
-> B16-A minimal deterministic/mock downstream paired-agent empirical run
   (real edit/test loop; deterministic mock agent; paired control/treatment
    arms; synthetic public micro tasks; aggregate-only public artifact;
    no live LLM, no provider/remote calls, no downstream agent value claim)
```

B16-A is NOT B16. The full B16 downstream-coding-agent-evaluation
phase remains a bounded planning / feasibility stage that requires live
paired agent runs with real provider calls. B16-A only produces the
first empirical downstream-agent-shaped smoke by running a
deterministic mock agent on synthetic public micro tasks. It does NOT
unlock B16 live agent value, default/policy/public-release, or any
promotion claim.

## Synthetic public micro bug task design

B16-A generates deterministic synthetic public micro bug task specs in
code (default 24 tasks; configurable via `--task-count` in the range
4-32). Each task spec describes a tiny Python module with a one-line
bug (returns the wrong value) and a stdlib test that asserts the
correct value. The fix is a deterministic one-line return-value
replacement.

For each task and arm, B16-A creates a fresh `/tmp` workspace containing:

- `target.py`: a tiny module with a one-line bug (returns wrong value).
- `distractor.py`: a wrong-file distractor with a similar-looking
  symbol (the mock agent may edit this if given a wrong cue).
- `test_target.py`: a stdlib test that imports `target` and asserts the
  correct value; exits 0 on success, 1 on failure.

All workspace files are real Python files written to disk under
`/tmp`. The harness actually edits files and runs subprocess tests.

## Paired arm design

B16-A runs paired control/treatment arms with the same budget/tool
constraints; only the context pack differs.

- **control arm**: bare/wrong-cue pack. For a designed subset
  (even-index tasks) the control pack carries a **wrong-cue file**
  pointing at the distractor; for the rest it carries **no file cue**
  at all. The deterministic mock agent therefore edits the wrong file
  (or does nothing) and tests fail.
- **treatment arm**: richer/evidence pack with the **target file**,
  **target symbol**, and **operation hint** cues. The deterministic
  mock agent edits the correct target file and tests pass.

The treatment pack **causally alters** the deterministic mock agent's
behavior for the designed subset. This is a causal pack-effect smoke,
not a live agent value claim.

## Deterministic mock agent

The mock agent is fully deterministic and pack-dependent:

1. If the pack has a `target_file` cue -> edit that file with the
   correct fix (tests will pass).
2. Elif the pack has a `wrong_cue_file` cue -> edit the wrong file
   (tests will still fail; `wrong_file_edits=1`).
3. Else -> do nothing (tests fail; no edit).

After the edit (or no-op), the agent runs the real subprocess test
command (`python3 <workspace>/test_target.py`) and records the
pass/fail result. The per-run **event log** (with file paths, edit
content, test stdout/stderr) is kept in-memory only and NEVER written
to the public artifact. Only aggregate metrics are returned.

## CLI

```bash
python3 -m py_compile eval/b16a_minimal_mock_agent_paired_run.py
python3 eval/b16a_minimal_mock_agent_paired_run.py --self-test
python3 eval/b16a_minimal_mock_agent_paired_run.py \
    --out artifacts/b16a_minimal_mock_agent_paired_run/\
b16a_minimal_mock_agent_paired_run_report.json
# Override the deterministic task count (range 4-32):
python3 eval/b16a_minimal_mock_agent_paired_run.py \
    --task-count 12 \
    --out /tmp/b16a_smoke_report.json
```

Default mode: writes the committed public aggregate-only artifact
(default out path if `--out` omitted). The default mode generates
deterministic synthetic public micro bug tasks, creates a fresh
`/tmp` workspace per task+arm, runs the deterministic mock agent (real
file edits + real subprocess tests), computes aggregate behavior
metrics, and writes ONLY the public aggregate artifact. Raw event
logs/patches/test output stay under `/tmp` and are never committed or
uploaded.

CLI arguments: `--self-test`, `--out`, `--task-count`. Unknown/
private-looking arguments are rejected with a generic `invalid
arguments` message that does not echo private paths or basenames
(SafeArgumentParser pattern).

`--self-test` runs a real `/tmp` workspace edit/test loop with no
external provider required; it covers real file edits, real test
subprocess execution, arm pack difference, mock action dependence on
pack cues, aggregate math, scanner rejections (path, snippet, patch,
test output, task_id, event log, stack trace, content_sha, provider
auth/endpoint, secret sentinel, URL, line range), no-claim flag
invariants, fail-closed generation, and CLI argument surface.

### Guard requirements

1. Default mode generates deterministic synthetic public micro bug
   tasks in code (no external dataset required).
2. Each task+arm gets a fresh `/tmp` workspace; no shared state across
   arms or tasks.
3. The mock agent performs real file edits and runs real subprocess
   tests (stdlib Python).
4. The per-run event log (paths, patches, test output) stays under
   `/tmp` only and is never committed or uploaded
   (`transient_workspace_outputs_only=true`).
5. The committed artifact contains ONLY aggregate counts/rates/means;
   no per-run rows, no paths, no file paths, no source snippets, no
   patches/diffs, no test output, no event logs, no task IDs, no
   content hashes, no secrets.
6. Strict fail-closed forbidden scanner runs immediately before writing
   the JSON artifact (`_enforce_no_forbidden`).
7. Self-test failure refuses successful artifact generation
   (`_refuse_on_self_test_failure`).

## Artifact identity (default committed artifact)

The committed artifact at
`artifacts/b16a_minimal_mock_agent_paired_run/b16a_minimal_mock_agent_paired_run_report.json`
is the public aggregate-only smoke artifact. Identity / boundary
fields:

- `schema_version` = `b16a_minimal_mock_agent_paired_run.v1`
- `generated_by`, `generated_at`, `claim_level`, `status`, `mode`,
  `phase`
- Safe true flags (exactly these, all true):
  `downstream_agent_runs_performed`, `deterministic_mock_agent`,
  `synthetic_micro_tasks_used`, `paired_arms_evaluated`,
  `real_file_edits_performed`, `real_test_commands_executed`,
  `agent_behavior_metrics_evaluated`, `aggregate_only_public_artifact`,
  `diagnostic_only`.
- No-claim / no-runtime-change flags (all false):
  `live_llm_agent`, `provider_calls_made`, `remote_calls_made`,
  `downstream_agent_value_proven`, `promotion_ready`,
  `default_should_change`, `runtime_behavior_changed`,
  `retriever_changed`, `pack_builder_changed`, `backend_changed`,
  `default_policy_changed`, `evidencecore_semantics_changed`,
  `external_benchmark_performance_claimed`,
  `live_agent_generalization_claimed`, `real_user_task_claimed`.
- `input_summary`: `synthetic_task_count`, `run_count_per_arm`,
  `total_runs`, `arms` (`[control, treatment]`), `paired_design`
  (`true`), `workspace_isolation` (`fresh_tmp_per_task_arm`),
  `transient_workspace_outputs_only` (`true`),
  `designed_causal_subset` (`true`).
- `arm_metrics`: per-arm dict (`control`, `treatment`) with
  `run_count`, `solve_rate`, `tests_pass_rate`,
  `correct_file_before_first_edit_rate`, `wrong_file_edits_mean`,
  `tool_calls_before_first_edit_mean`, `context_tokens_mean`,
  `latency_ms_mean`, `cost_proxy_mean`. No per-run rows, no paths, no
  patches, no test output.
- `deltas_treatment_minus_control`: treatment-minus-control deltas for
  all rate/mean metrics (excluding `run_count`, which is identical by
  paired design).
- `self_test_summary` + `self_test_checks` + `self_test_passed`.
- `forbidden_scan` summary (fail-closed before writing JSON).

## Aggregate metrics

Per-arm aggregate metrics (no per-run rows):

- `run_count`: number of runs in the arm (= synthetic task count).
- `solve_rate`: fraction of runs where tests pass AND the correct
  file was edited before/at the first edit.
- `tests_pass_rate`: fraction of runs where tests pass after the
  agent action.
- `correct_file_before_first_edit_rate`: fraction of runs where the
  first edit was on the correct target file.
- `wrong_file_edits_mean`: mean count of wrong-file edits per run.
- `tool_calls_before_first_edit_mean`: mean tool calls before the
  first edit.
- `context_tokens_mean`: mean deterministic context-token count
  (control pack is smaller; treatment pack is richer).
- `latency_ms_mean`: mean real wall-clock latency of the test
  subprocess in milliseconds.
- `cost_proxy_mean`: mean cost proxy (always 0.0 for the deterministic
  mock agent; no provider calls).

Treatment-minus-control deltas are emitted for all rate/mean metrics
(excluding `run_count`). Exact synthetic task/run counts are
acceptable because these are synthetic public tasks.

## Forbidden scanner (public, fail-closed)

A strict forbidden-output scanner runs fail-closed before writing the
public JSON. Rejects forbidden dict keys (`task_id`, `task_index`,
`workspace_path`, `workspace`, `file`, `filename`, `filepath`,
`target_file`, `wrong_cue_file`, `target_module`, `distractor_module`,
`test_module`, `path`, `span`, `start_line`, `end_line`,
`content_sha`, `content_hash`, `snippet`, `code`, `source_code`,
`patch`, `diff`, `test_output`, `test_log`, `test_stdout`,
`test_stderr`, `stdout`, `stderr`, `event_log`, `events`, `log`,
`trace`, `raw_event`, `stack_trace`, `traceback`, `api_key`,
`base_url`, `provider_key`, `secret`, `token`, `credential`,
`rows`, `per_run`, `predictions`, `candidates`, etc.) anywhere, and
rejects value patterns: ANY URL (no URL allowlist), 32+ char hex
digests, secret-like strings (api_key/base_url/provider_key/secret/
password/credential), path-like strings with file extensions,
`/tmp/` workspace path values, `task_N` task-identifier values,
patch/diff markers (`---`, `+++`, `@@`), stack traces (`Traceback (most
recent call last)`), multiline strings, raw JSON fragments, raw line
ranges `12-34`, and the self-test sentinel.

The scanner runs ONLY against the final public aggregate artifact. The
internal per-run event logs (which contain paths/patches/test stdout/
stderr) are kept in-memory only, never scanned against the public
contract, and never committed.

## Self-tests

- Artifact identity fields (schema, claim, status, mode, phase,
  generated_by).
- Safe true flags (all 9 true); no-claim / no-runtime-change false
  flags (all 15 false).
- Synthetic task generation: deterministic count, symbols, correct
  values, buggy values.
- Pack builder: control even-index has wrong-cue file; control
  odd-index has no file cue; treatment has target file/symbol/
  operation hint cues; treatment pack is richer than control;
  control pack lacks target file cue.
- Real workspace creation: target/distractor/test files exist on disk.
- Real test subprocess: test fails before the fix (bug present).
- Mock agent behavior (pack-dependent): treatment edits correct file,
  no wrong-file edits, tests pass, solve=true, real file edit applied;
  control wrong-cue edits wrong file, wrong_file_edits=1, tests fail,
  solve=false, distractor file actually edited; control no-cue does
  nothing, tests fail, solve=false.
- Mock action dependence on pack cues: target_file cue drives correct
  file edit; wrong_cue_file drives wrong file edit; treatment solve
  rate higher than control.
- Aggregate metrics math: run_count, solve_rate, tests_pass_rate,
  correct_file_rate, wrong_file_edits_mean, tool_calls_mean,
  cost_proxy_mean=0.
- Deltas computation: solve_rate delta positive, wrong_file_edits_mean
  delta negative, run_count excluded from deltas.
- Forbidden scanner rejects: workspace path, file path, source
  snippet, patch marker, test output, task_id key, task_id value,
  raw event log, stack trace, content_sha key, hex digest value,
  provider auth field, endpoint URL field, sentinel canary, URL value,
  forbidden field name as value, line range value.
- Forbidden scanner allows: arm names (control/treatment), metric
  values, workspace isolation token.
- Fail-closed generation: clean public report does not raise; leaked
  public report raises SystemExit; self-test failure refuses artifact
  generation; failed self-test does not carry success status.
- Public artifact self-scan is clean (no forbidden key anywhere).
- CLI argument surface: `--self-test`, `--out`, `--task-count` are the
  only options (plus `-h`/`--help`); default task count is in range.

## Validation

```text
python3 -m py_compile eval/b16a_minimal_mock_agent_paired_run.py    => PASS
python3 eval/b16a_minimal_mock_agent_paired_run.py --self-test      => PASS (104/104 checks)
python3 eval/b16a_minimal_mock_agent_paired_run.py \
  --out artifacts/b16a_minimal_mock_agent_paired_run/\
b16a_minimal_mock_agent_paired_run_report.json                     => PASS
  (status: mock_downstream_paired_smoke_pass,
   forbidden_scan: pass, self_test_passed: true,
   mode: public_aggregate_synthetic_micro_tasks, phase: B16-A,
   synthetic_task_count: 24, total_runs: 48,
   control: solve_rate=0.0, tests_pass_rate=0.0,
     correct_file_before_first_edit_rate=0.0,
     wrong_file_edits_mean=0.5,
   treatment: solve_rate=1.0, tests_pass_rate=1.0,
     correct_file_before_first_edit_rate=1.0,
     wrong_file_edits_mean=0.0,
   deltas_treatment_minus_control: solve_rate=+1.0,
     wrong_file_edits_mean=-0.5,
   live_llm_agent: false, provider_calls_made: false,
   remote_calls_made: false,
   downstream_agent_value_proven: false,
   promotion_ready: false,
   default_should_change: false,
   retriever_changed: false,
   pack_builder_changed: false,
   backend_changed: false,
   default_policy_changed: false,
   evidencecore_semantics_changed: false,
   runtime_behavior_changed: false,
   external_benchmark_performance_claimed: false,
   live_agent_generalization_claimed: false,
   real_user_task_claimed: false)
python3 scripts/validate_docs_i18n.py                           => PASS
git diff --check                                               => PASS
```

## Caveats

- B16-A is the public aggregate-only minimal mock downstream paired
  smoke artifact. It is eval/diagnostic only. It does NOT change
  runtime, retriever, pack, backend, or default policy; it does NOT
  change EvidenceCore semantics. It is NOT a benchmark result, NOT a
  live downstream agent value claim, NOT a runtime-clean general
  algorithm claim, NOT an OOD temporal claim, and NOT a QuIVer systems
  claim.
- B16-A uses a **deterministic mock agent** (no live LLM, no provider
  calls, no remote calls). The mock agent's behavior is pack-dependent
  by design: the treatment pack includes the target file/symbol/
  operation cue, while the control pack lacks the target cue or
  carries a wrong-cue file. This is a causal pack-effect smoke, NOT a
  live agent value claim.
- B16-A generates **deterministic synthetic public micro bug tasks**
  in code. These are NOT real user tasks and are NOT external
  benchmark tasks. The exact task/run counts are acceptable because
  these are synthetic public tasks.
- B16-A performs **real file edits** and **real subprocess tests**
  (stdlib Python) in fresh `/tmp` workspaces per task+arm. The
  per-run event logs, patches, and test output stay under `/tmp` only
  and are NEVER committed or uploaded. The committed artifact contains
  ONLY aggregate counts/rates/means.
- B16-A does NOT prove downstream agent value. The treatment-vs-control
  delta is a deterministic mock artifact of the designed pack cues,
  NOT evidence that the treatment pack improves a live downstream
  agent. `downstream_agent_value_proven=false`.
- B16-A does NOT claim live agent generalization. The deterministic
  mock agent generalizes trivially to the synthetic task family by
  construction; this is NOT a live agent generalization claim.
  `live_agent_generalization_claimed=false`.
- All no-claim / no-runtime-change flags remain false; diagnostic
  flags (`aggregate_only_public_artifact`, `diagnostic_only`) remain
  true; the deterministic-mock-run flags
  (`downstream_agent_runs_performed`, `deterministic_mock_agent`,
  `synthetic_micro_tasks_used`, `paired_arms_evaluated`,
  `real_file_edits_performed`, `real_test_commands_executed`,
  `agent_behavior_metrics_evaluated`) are the only additional true
  flags.
- No runtime/retriever/pack/model/backend/default-policy files were
  modified. No promotion/default/runtime claims change.
