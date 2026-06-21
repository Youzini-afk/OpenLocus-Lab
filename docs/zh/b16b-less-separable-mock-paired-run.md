# B16-B Less-Separable Mock 下游 Paired-Agent 压力测试（公共仅 aggregate artifact）

> 中文译本待补充。以下为英文原文，避免内容丢失。

## English source / 英文原文

# B16-B Less-Separable Mock Downstream Paired-Agent Stress (Public Aggregate-Only Artifact)

## Scope and claim boundary

B16-B extends B16-A from deliberately separable synthetic micro bugs
to a harder **less-separable deterministic/mock downstream paired-agent
stress** run. It remains empirical: real temporary workspaces, real
file edits, real subprocess tests, aggregate
solve/correct-file/wrong-file/tool-call/context/latency/cost-proxy
metrics. The new work reduces the artificial separability of B16-A
without jumping yet to live-provider agent execution.

B16-B is explicitly **not** a live LLM downstream agent run, **not** a
downstream agent value claim, **not** an external benchmark performance
claim, **not** a live agent generalization claim, **not** a real user
task claim, **not** a promotion, **not** a default/policy change, and
**not** a runtime/retriever/pack/backend/EvidenceCore semantic change.

B16-B **does not** claim downstream agent value, **does not** promote
any candidate, **does not** change runtime/retriever/pack/backend/
default-policy/EvidenceCore semantics, **does not** claim live agent
generalization, **does not** claim external benchmark performance, and
**does not** claim a real user task. The committed artifact is
aggregate-only: no task IDs, workspace paths, file paths, source
snippets, patches/diffs, test output, raw event logs, per-run rows,
private IDs, or provider/model info beyond the deterministic mock
identity. It emits NO `winner`, `best_arm`, `recommended_default`,
`preferred_policy`, or `promotion` recommendation fields.

- Claim level: `deterministic_mock_downstream_paired_stress_only`.
- Status: `mock_downstream_paired_stress_pass` on success; mode
  `public_aggregate_synthetic_stress_tasks`; phase `B16-B`.
- B16-B is **eval/diagnostic only**. It is NOT a benchmark result, NOT
  a live downstream agent value claim, NOT a runtime-clean general
  algorithm claim, NOT an OOD temporal claim, and NOT a QuIVer systems
  claim.

### B16-A -> B16-B relation

```text
B16-A minimal deterministic/mock downstream paired-agent empirical run
   (deliberately separable micro tasks; single separable token;
    control=wrong-cue/no-cue; treatment=target_file cue;
    treatment solve_rate=1.0 vs control solve_rate=0.0)
-> B16-B less-separable deterministic/mock downstream paired-agent stress
   (multi-cue tasks: target_file + target_symbol + operation_hint +
    support_relation; within-file symbol ambiguity (decoy) +
    cross-file symbol ambiguity (distractor) + support offset;
    control_sparse=symbol+operation but NO file cue and NO support cue;
    treatment_multi_cue=full multi-cue pack;
    treatment solve_rate=1.0 vs control solve_rate=0.0;
    real file edits + real subprocess tests; aggregate-only public artifact;
    no live LLM, no provider/remote calls, no downstream agent value claim)
```

B16-B is NOT B16. The full B16 downstream-coding-agent-evaluation
phase remains a bounded planning / feasibility stage that requires live
paired agent runs with real provider calls. B16-B only produces a
harder deterministic/mock stress of the downstream-agent metric/artifact
pipeline. It does NOT unlock B16 live agent value,
default/policy/public-release, or any promotion claim.

### Why not live provider for B16-B

Explorer recon found reusable OpenAI-compatible helpers in P20/P21/R32
and production GitHub environment variables, but no shared
downstream-agent event log, tool-call/cost/token tracking helper, or
live agent loop. A live-provider B16 would therefore be a larger B16-C
change requiring provider-client/event-log design and privacy review.
B16-B should first stress the downstream-agent metric/artifact pipeline
under harder deterministic conditions.

## Synthetic public less-separable stress task design

B16-B generates deterministic synthetic public less-separable stress
task specs in code (default 24 tasks; configurable via `--task-count`
in the range 4-32). Each task spec describes a tiny multi-file Python
workspace where solving requires combining multiple cues
(`target_file` + `target_symbol` + `operation_hint` +
`support_relation`) instead of one separable token:

- `target.py`: defines `target_symbol` (buggy) AND a `decoy_symbol`
  with a similar name (also buggy) -> within-file symbol ambiguity.
- `distractor.py`: defines the SAME `target_symbol` (buggy) ->
  cross-file symbol ambiguity (target.py vs distractor.py).
- `support.py`: defines `SUPPORT_OFFSET` constant -> the correct
  return value is `correct_value + support_offset`; support is useful
  for interpretation but is NOT the edit target.
- `test_target.py`: stdlib test that imports `support.SUPPORT_OFFSET`
  and `target.target_symbol`, asserts the correct combined value;
  exits 0 on success, 1 on failure.

The fix requires combining four cues:

1. `target_file` cue to pick target.py (not distractor.py);
2. `target_symbol` cue to pick the right symbol in target.py (not
   the decoy);
3. `operation_hint` cue to apply the replace-return-value operation;
4. `support_relation` cue to apply the support offset.

Missing any cue causes a deterministic wrong action. For each task and
arm, B16-B creates a fresh `/tmp` workspace containing all four files.
All workspace files are real Python files written to disk under
`/tmp`. The harness actually edits files and runs subprocess tests.

## Paired arm design

B16-B runs paired `control_sparse` / `treatment_multi_cue` arms with
the same budget/tool constraints; only the context pack differs.

- **control_sparse arm**: partial pack with `target_symbol` +
  `operation_hint` but NO `target_file` and NO `support_relation`.
  The deterministic mock agent cannot disambiguate the cross-file
  symbol name (target.py and distractor.py both define
  `target_symbol`) and lacks the support offset, so it edits the wrong
  file (distractor.py) with the wrong value (no offset) -> tests fail.
- **treatment_multi_cue arm**: full multi-cue pack with `target_file`
  + `target_symbol` + `operation_hint` + `support_relation`. The
  deterministic mock agent edits the correct target file, picks the
  correct symbol, applies the correct operation, and uses the support
  offset -> tests pass.

The treatment pack **causally alters** the deterministic mock agent's
behavior. Treatment is perfect by construction; docs therefore
describe this as a **harness/stress** result, NOT a live agent result.
This is a causal pack-effect stress, not a live agent value claim.

## Deterministic mock agent

The mock agent is fully deterministic and multi-cue-dependent:

1. **File selection**: if the pack has a `target_file` cue -> edit
   target.py (correct file). Otherwise, perform a deterministic
   lexicographic symbol search across `.py` files; `distractor.py`
   sorts before `target.py`, so the agent picks the distractor (wrong
   file) when no file cue is given.
2. **Symbol selection**: if the pack has a `target_symbol` cue ->
   edit that symbol (if it exists in the chosen file). Otherwise,
   pick the lexicographically-first `def` symbol in the file
   (deterministic but possibly the decoy).
3. **Operation application**: if the pack has an `operation_hint` cue
   -> apply the replace-return-value operation. If
   `support_relation` is present and the operation hint references
   `support_offset`, use `correct_value + support_offset` as the new
   return value. Otherwise, use `correct_value` without offset (tests
   will fail).
4. **Test execution**: after the edit (or no-op), the agent runs the
   real subprocess test command
   (`python3 <workspace>/test_target.py`) and records the pass/fail
   result.

The per-run **event log** (with file paths, edit content, test
stdout/stderr) is kept in-memory only and NEVER written to the public
artifact. Only aggregate metrics are returned.

## CLI

```bash
python3 -m py_compile eval/b16b_less_separable_mock_paired_run.py
python3 eval/b16b_less_separable_mock_paired_run.py --self-test
python3 eval/b16b_less_separable_mock_paired_run.py \
    --out artifacts/b16b_less_separable_mock_paired_run/\
b16b_less_separable_mock_paired_run_report.json
# Override the deterministic task count (range 4-32):
python3 eval/b16b_less_separable_mock_paired_run.py \
    --task-count 12 \
    --out /tmp/b16b_stress_report.json
```

Default mode: writes the committed public aggregate-only artifact
(default out path if `--out` omitted). The default mode generates
deterministic synthetic public less-separable stress tasks, creates a
fresh `/tmp` workspace per task+arm, runs the deterministic mock agent
(real file edits + real subprocess tests), computes aggregate behavior
metrics, and writes ONLY the public aggregate artifact. Raw event
logs/patches/test output stay under `/tmp` and are never committed or
uploaded.

CLI arguments: `--self-test`, `--out`, `--task-count`. Unknown/
private-looking arguments are rejected with a generic `invalid
arguments` message that does not echo private paths or basenames
(SafeArgumentParser pattern).

### Guard requirements

1. Default mode generates deterministic synthetic public
   less-separable stress tasks in code (no external dataset required).
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
   content hashes, no secrets, no model/provider env values.
6. Strict fail-closed forbidden scanner runs immediately before writing
   the JSON artifact (`_enforce_no_forbidden`).
7. Self-test failure refuses successful artifact generation
   (`_refuse_on_self_test_failure`).

## Artifact identity (default committed artifact)

The committed artifact at
`artifacts/b16b_less_separable_mock_paired_run/b16b_less_separable_mock_paired_run_report.json`
is the public aggregate-only stress artifact. Identity / boundary
fields:

- `schema_version` = `b16b_less_separable_mock_paired_run.v1`
- `generated_by`, `generated_at`, `claim_level`, `status`, `mode`,
  `phase`
- Safe true flags (exactly these, all true):
  `downstream_agent_runs_performed`, `deterministic_mock_agent`,
  `paired_run_executed`, `real_file_edits_performed`,
  `subprocess_tests_executed`, `less_separable_stress_tasks`,
  `aggregate_only_public_artifact`, `diagnostic_only`.
- No-claim / no-runtime-change flags (all false):
  `live_llm_agent`, `provider_calls_made`,
  `remote_provider_calls_made`, `downstream_agent_value_proven`,
  `live_agent_generalization_claimed`, `promotion_ready`,
  `default_should_change`, `runtime_behavior_changed`,
  `retriever_changed`, `pack_builder_changed`, `backend_changed`,
  `default_policy_changed`, `evidencecore_semantics_changed`,
  `external_benchmark_performance_claimed`.
- `input_summary`: `synthetic_task_count`, `run_count_per_arm`,
  `total_runs`, `arms` (`[control_sparse, treatment_multi_cue]`),
  `paired_design` (`true`), `workspace_isolation`
  (`fresh_tmp_per_task_arm`), `transient_workspace_outputs_only`
  (`true`), `multi_cue_design` (`true`), `less_separable_tasks`
  (`true`).
- `arm_results`: list-of-records (fixed arm allowlist), each with
  `arm`, `metrics`, and `outcome_category_counts`.
- `paired_deltas`: list-of-records, one metric per record, each with
  fixed keys `baseline_arm`, `treatment_arm`, `metric`, and `delta`.
  Deltas are treatment-minus-control for all rate/mean metrics
  (excluding `run_count`).
- No top-level dynamic arm-key mirrors are emitted: there is no
  `arm_metrics`, no top-level `outcome_category_counts`, and no legacy
  `deltas_treatment_minus_control` field.
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
(excluding `run_count`).

## Forbidden scanner (public, fail-closed)

A strict forbidden-output scanner runs fail-closed before writing the
public JSON. Rejects forbidden dict keys (`task_id`, `workspace_path`,
`file`, `target_file`, `target_module`, `support_module`,
`distractor_module`, `test_module`, `path`, `content_sha`, `snippet`,
`code`, `patch`, `diff`, `test_output`, `stdout`, `stderr`,
`event_log`, `stack_trace`, `api_key`, `base_url`, `provider_key`,
`secret`, `token`, `model_name`, `provider_env`, `rows`, `per_run`,
`winner`, `best_arm`, `recommended_default`, `preferred_policy`,
`promotion`, etc.) anywhere, and rejects value patterns: ANY URL, 32+
char hex digests, secret-like strings, path-like strings with file
extensions, `/tmp/` workspace path values, `task_N` task-identifier
values, patch/diff markers, stack traces, multiline strings, raw JSON
fragments, raw line ranges, model-name-like strings, provider-env-like
strings, and the self-test sentinel.

The scanner runs ONLY against the final public aggregate artifact. The
internal per-run event logs are kept in-memory only, never scanned
against the public contract, and never committed.

## Self-tests

- Artifact identity fields (schema, claim, status, mode, phase,
  generated_by).
- Safe true flags (all 8 true); no-claim / no-runtime-change false
  flags (all 14 false).
- No recommendation fields present.
- Synthetic task generation: deterministic count, symbols, correct
  values, buggy values, support offsets, expected values, decoy
  symbols, less-separable multi-cue structure.
- Pack builder: control has symbol+operation but lacks file and support
  cues; treatment has all four cues; treatment is richer; packs differ;
  treatment operation_hint references support_offset.
- Real workspace creation: all files exist; target has decoy symbol;
  distractor has same symbol; support has offset constant.
- Real test subprocess: test fails before the fix.
- Mock agent behavior: treatment edits correct file, tests pass,
  solve=true, real file edit with offset, outcome=solved; control
  edits wrong file, tests fail, solve=false, distractor edited,
  outcome=wrong_file_targeted.
- Mock action dependence on multi-cue pack.
- Workspace isolation.
- Aggregate metrics math.
- Outcome category counts.
- Deltas computation.
- Forbidden scanner rejects: workspace path, file path, support file
  path, source snippet, patch marker, test output, stderr, task_id
  key/value, raw event log, stack trace, content_sha key, hex digest,
  provider auth/endpoint/env, model name, recommendation fields,
  sentinel, URL, forbidden field name as value, line range.
- Forbidden scanner allows: arm names, metric values, workspace
  isolation token, outcome category names, multi_cue_design token,
  less_separable token.
- Fail-closed generation.
- Public artifact self-scan clean; no per-run rows; arm_results
  list-of-records; paired_deltas list-of-records with fixed shape; no
  top-level dict mirrors / no legacy delta field.
- CLI argument surface.
- Both arms run same task count; total runs equals task count times
  arms.

## Validation

```text
python3 -m py_compile eval/b16b_less_separable_mock_paired_run.py    => PASS
python3 eval/b16b_less_separable_mock_paired_run.py --self-test      => PASS (147/147 checks)
python3 eval/b16b_less_separable_mock_paired_run.py \
  --out artifacts/b16b_less_separable_mock_paired_run/\
b16b_less_separable_mock_paired_run_report.json                     => PASS
  (status: mock_downstream_paired_stress_pass,
    forbidden_scan: pass, self_test_passed: true,
    mode: public_aggregate_synthetic_stress_tasks, phase: B16-B,
    synthetic_task_count: 24, total_runs: 48,
    control_sparse: solve_rate=0.0, tests_pass_rate=0.0,
      correct_file_before_first_edit_rate=0.0,
      wrong_file_edits_mean=1.0,
    treatment_multi_cue: solve_rate=1.0, tests_pass_rate=1.0,
      correct_file_before_first_edit_rate=1.0,
      wrong_file_edits_mean=0.0,
    paired_deltas records: solve_rate=+1.0,
      wrong_file_edits_mean=-1.0,
    live_llm_agent: false, provider_calls_made: false,
    remote_provider_calls_made: false,
    downstream_agent_value_proven: false,
    promotion_ready: false,
    default_should_change: false,
    retriever_changed: false, pack_builder_changed: false,
    backend_changed: false, default_policy_changed: false,
    evidencecore_semantics_changed: false,
    runtime_behavior_changed: false,
    external_benchmark_performance_claimed: false,
    live_agent_generalization_claimed: false)
python3 scripts/validate_docs_i18n.py                           => PASS
git diff --check                                               => PASS
```

## Caveats

- B16-B is the public aggregate-only less-separable mock downstream
  paired stress artifact. It is eval/diagnostic only. It does NOT
  change runtime, retriever, pack, backend, or default policy; it
  does NOT change EvidenceCore semantics. It is NOT a benchmark result,
  NOT a live downstream agent value claim, NOT a runtime-clean general
  algorithm claim, NOT an OOD temporal claim, and NOT a QuIVer systems
  claim.
- B16-B uses a **deterministic mock agent** (no live LLM, no provider
  calls, no remote calls). The mock agent's behavior is multi-cue
  pack-dependent by design. This is a causal pack-effect stress, NOT a
  live agent value claim. Treatment is perfect by construction; docs
  describe this as a harness/stress result, NOT a live agent result.
- B16-B generates **deterministic synthetic public less-separable
  stress tasks** in code. These are NOT real user tasks and are NOT
  external benchmark tasks.
- B16-B performs **real file edits** and **real subprocess tests**
  (stdlib Python) in fresh `/tmp` workspaces per task+arm. The per-run
  event logs, patches, and test output stay under `/tmp` only and are
  NEVER committed or uploaded.
- B16-B does NOT prove downstream agent value.
  `downstream_agent_value_proven=false`.
- B16-B does NOT claim live agent generalization.
  `live_agent_generalization_claimed=false`.
- B16-B emits NO `winner`, `best_arm`, `recommended_default`,
  `preferred_policy`, or `promotion` recommendation field.
- All no-claim / no-runtime-change flags remain false; diagnostic
  flags remain true; the deterministic-mock-stress-run flags are the
  only additional true flags.
- No runtime/retriever/pack/model/backend/default-policy files were
  modified. No promotion/default/runtime claims change.
