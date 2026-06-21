# F1 Counterfactual Evidence Utility Smoke (Public Aggregate-Only Artifact)

## Scope and claim boundary

F1 is the **first counterfactual evidence utility smoke** in the
OpenLocus research track. It tests the deep-research idea that
evidence/support should be measured as **marginal causal utility for a
coding-agent trajectory**, not only as subjective relevance. F1 executes
a real edit/test loop on tiny synthetic Python workspaces under
transient `/tmp` directories across **six counterfactual context
variants** and computes **five marginal utility deltas** from aggregate
per-variant metrics.

F1 is explicitly **not** a live LLM downstream agent run, **not** a
downstream agent value claim, **not** an external benchmark performance
claim, **not** a live agent generalization claim, **not** a real user
task claim, **not** a true E/S calibration claim, **not** a promotion,
**not** a default/policy change, and **not** a runtime/retriever/pack/
backend/EvidenceCore semantic change.

The agent is a **deterministic mock agent** (no live LLM, no provider
calls, no remote calls) whose behavior depends on the provided context
pack. The committed artifact is aggregate-only: no task IDs, workspace
paths, file paths, source snippets, patches/diffs, test output, raw
event logs, per-run rows, private IDs, or provider/model info beyond the
deterministic mock identity.

- Claim level: `counterfactual_evidence_utility_smoke_only`.
- Status: `counterfactual_evidence_utility_smoke_pass` on success; mode
  `public_aggregate_synthetic_micro_tasks`; phase `F1`.
- F1 is **eval/diagnostic only**. It is NOT a benchmark result, NOT a
  live downstream agent value claim, NOT a true E/S calibration claim,
  NOT a runtime-clean general algorithm claim, NOT an OOD temporal
  claim, and NOT a QuIVer systems claim.

### D5-A0 -> B16-A -> C5-A -> F1 relation

```text
D5-A0 automated E/S calibration smoke (retrieval-only aggregate)
-> B16-A minimal deterministic/mock downstream paired-agent empirical run
   (real edit/test loop; deterministic mock agent; paired control/treatment
    arms; synthetic public micro tasks; aggregate-only public artifact;
    no live LLM, no provider/remote calls, no downstream agent value claim)
-> C5-A ContextBench verified retrieval performance smoke
   (external-benchmark-shaped retrieval smoke; bounded ContextBench
    verified subset; transient /tmp clone + retrieval + score;
    aggregate-only public artifact; no provider calls; no external
    benchmark performance claim)
-> F1 counterfactual evidence utility smoke
   (six counterfactual context variants; deterministic mock agent;
    real edit/test loop; five marginal utility deltas computed from
    aggregate variant metrics; aggregate-only public artifact;
    no live LLM, no provider/remote calls; not true E/S calibration)
```

F1 is NOT a real E/S calibration. It is a deterministic/mock causal
smoke that computes marginal utility deltas across counterfactual
context variants. The deltas are causal-shaped (variant vs variant),
but the agent is deterministic, the tasks are synthetic, and the
contexts are hand-designed. `true_e_s_calibration_claimed=false`,
`automated_e_s_full_calibration_claimed=false`,
`human_e_s_calibration_claimed=false`.

## Synthetic public micro bug task design

F1 generates deterministic synthetic public micro bug task specs in
code (default 24 tasks; configurable via `--task-count` in the range
4-100). Each task spec describes a tiny Python module with a one-line
bug (returns the wrong value) and a stdlib test that asserts the
correct value. The fix is a deterministic one-line return-value
replacement.

For each task and variant, F1 creates a fresh `/tmp` workspace
containing:

- `target.py`: a tiny module with a one-line bug (returns wrong value).
  The mock agent edits this file when a primary cue is present.
- `support.py`: a helper module containing a supporting symbol that is
  NOT the target symbol. Editing this file does not affect the test
  outcome (the test only imports `target`).
- `distractor.py`: a wrong-file distractor with a similar-looking
  symbol (the mock agent may edit this if given a wrong cue).
- `test_target.py`: a stdlib test that imports `target` and asserts the
  correct value; exits 0 on success, 1 on failure.

All workspace files are real Python files written to disk under
`/tmp`. The harness actually edits files and runs subprocess tests.
These file names and paths are NEVER emitted to the public artifact.

## Six counterfactual context variants

F1 runs **six counterfactual context variants** per task. Only the
context pack differs across variants; the budget/tool constraints and
the deterministic mock agent are the same.

1. **`base_no_context`**: no file cue at all. The deterministic mock
   agent does nothing -> tests fail. solve_rate=0.0,
   wrong_file_edits=0, tool_calls=0, context_tokens=8.
2. **`primary_only`**: primary target/symbol/operation cue. The
   deterministic mock agent edits the correct target file -> tests
   pass. solve_rate=1.0, wrong_file_edits=0, tool_calls=1,
   context_tokens=24.
3. **`support_only`**: support cue only (no primary). The deterministic
   mock agent edits `support.py` (wrong file; the test only imports
   `target`) -> tests fail. solve_rate=0.0, wrong_file_edits=1,
   tool_calls=1, context_tokens=20.
4. **`primary_plus_support`**: primary + support cue. The deterministic
   mock agent inspects support (1 tool call, no edit), then edits
   `target.py` correctly -> tests pass; richer context than primary.
   solve_rate=1.0, wrong_file_edits=0, tool_calls=2, context_tokens=40.
5. **`distractor_only`**: wrong cue only. The deterministic mock agent
   edits `distractor.py` (wrong file) -> tests fail;
   `wrong_file_edits` increases. solve_rate=0.0, wrong_file_edits=1,
   tool_calls=1, context_tokens=16.
6. **`primary_plus_distractor`**: primary + distractor cue. The
   deterministic mock agent inspects distractor (1 tool call, no
   edit), then edits `target.py` correctly, then also edits
   `distractor.py` (after the correct first edit; tests still pass
   because target is fixed) -> tests pass; worse
   `wrong_file_edits` / `tool_calls` / `context_tokens` than primary.
   solve_rate=1.0, wrong_file_edits=1, tool_calls=2, context_tokens=32.

The `primary_plus_distractor` variant is the sixth variant (the oracle
plan listed five; F1 adds the sixth to enable a clean conditional
distractor utility delta `distractor_added_to_primary`). The docs and
the artifact `input_summary.variant_count=6` state this explicitly.

## Five marginal utility effects

F1 computes **five marginal utility effects** from aggregate variant
metrics. Effect names are deliberately utility-specific and do NOT use
`E_primary` / `S_support` field names that would resemble real E/S
calibration:

- **`primary_context_vs_base`** = `primary_only` - `base_no_context`
- **`support_context_vs_base`** = `support_only` - `base_no_context`
- **`distractor_context_vs_base`** = `distractor_only` - `base_no_context`
- **`support_added_to_primary`** = `primary_plus_support` - `primary_only`
- **`distractor_added_to_primary`** = `primary_plus_distractor` - `primary_only`

Each effect emits deltas for every rate/mean metric (excluding
`run_count`, which is identical across variants by paired design):
`solve_rate_delta`, `tests_pass_rate_delta`,
`correct_file_before_first_edit_rate_delta`,
`wrong_file_edits_mean_delta`,
`tool_calls_before_first_edit_mean_delta`,
`context_tokens_mean_delta`, `latency_ms_mean_delta`,
`cost_proxy_mean_delta`.

Expected marginal effects over the deterministic synthetic task family
(solve_rate / wrong_file_edits_mean / tool_calls_before_first_edit_mean
/ context_tokens_mean deltas):

```text
primary_context_vs_base:    solve +1.0, wrong   +0.0, tools +1.0, ctx +16.0
support_context_vs_base:    solve  0.0, wrong   +1.0, tools +1.0, ctx +12.0
distractor_context_vs_base: solve  0.0, wrong   +1.0, tools +1.0, ctx  +8.0
support_added_to_primary:   solve  0.0, wrong   +0.0, tools +1.0, ctx +16.0
distractor_added_to_primary:solve  0.0, wrong   +1.0, tools +1.0, ctx  +8.0
```

Interpretation:

- The **primary context** is the only context variant with a positive
  solve_rate delta over base. It causally changes the mock agent's
  behavior from no-op to a correct target edit.
- The **support context alone** does not solve (it edits the wrong
  file), but it still incurs a wrong-file edit and tool calls. Its
  marginal utility over base is negative on cost metrics.
- The **distractor context alone** does not solve and incurs a
  wrong-file edit and tool calls. Its marginal utility over base is
  negative on cost metrics.
- Adding **support to primary** does not change correctness (still
  solves) but increases tool calls and context tokens (cost-side
  marginal change, no correctness benefit on this synthetic family).
- Adding **distractor to primary** does not change correctness (still
  solves, because primary wins) but increases wrong-file edits, tool
  calls, and context tokens (negative conditional distractor utility
  on cost metrics).

This is a synthetic causal design, not a general claim about all
retrieval support candidates.

## Theory mapping (NOT true E/S calibration)

The artifact carries a `theory_mapping` block that records how the
marginal effects correspond to E-utility and S-conditional utility
smoke proxies:

- `primary_context_vs_base` -> `e_utility_smoke_proxy`
- `support_context_vs_base` -> `e_utility_smoke_proxy_support_variant`
- `distractor_context_vs_base` -> `e_utility_smoke_proxy_distractor_variant`
- `support_added_to_primary` -> `s_conditional_utility_smoke_proxy`
- `distractor_added_to_primary` -> `s_conditional_distractor_utility_smoke_proxy`

However F1 is explicitly NOT true E/S calibration:
`true_e_s_calibration_claimed=false`,
`automated_e_s_full_calibration_claimed=false`,
`human_e_s_calibration_claimed=false`. The theory mapping is a
naming/interpretation aid only; the marginal deltas are computed from
deterministic mock aggregate metrics over synthetic tasks, not from
real human/manual E/S labels and not from real E/S rubric scoring.

## Deterministic mock agent

The mock agent is fully deterministic and pack-dependent:

1. If the pack has a `target_file` cue (primary cue present):
   - If `support_file` is also present: inspect support (1 tool call,
     no edit), then edit `target.py` correctly.
   - If `wrong_cue_file` is also present: inspect distractor (1 tool
     call, no edit), then edit `target.py` correctly, then also edit
     `distractor.py` (wrong file edit AFTER the correct first edit;
     tests still pass because `target.py` is fixed).
   - Else: edit `target.py` correctly.
2. Elif the pack has a `support_file` cue (no primary): edit `support.py`
   (wrong file); tests still fail.
3. Elif the pack has a `wrong_cue_file` cue (no primary): edit
   `distractor.py` (wrong file); tests fail.
4. Else -> do nothing (tests fail; no edit).

After the edit (or no-op), the agent runs the real subprocess test
command (`python3 <workspace>/test_target.py`) and records the
pass/fail result. The per-run **event log** (with file paths, edit
content, test stdout/stderr) is kept in-memory only and NEVER written
to the public artifact. Only aggregate metrics are returned.

## CLI

```bash
python3 -m py_compile eval/f1_counterfactual_evidence_utility_smoke.py
python3 eval/f1_counterfactual_evidence_utility_smoke.py --self-test
python3 eval/f1_counterfactual_evidence_utility_smoke.py \
    --out artifacts/f1_counterfactual_evidence_utility/\
f1_counterfactual_evidence_utility_report.json
# Override the deterministic task count (range 4-100):
python3 eval/f1_counterfactual_evidence_utility_smoke.py \
    --task-count 48 \
    --out /tmp/f1_smoke_report.json
```

Default mode: writes the committed public aggregate-only artifact
(default out path if `--out` omitted). The default mode generates
deterministic synthetic public micro bug tasks, creates a fresh
`/tmp` workspace per task+variant, runs the deterministic mock agent
(real file edits + real subprocess tests), computes aggregate behavior
metrics and marginal utility deltas, and writes ONLY the public
aggregate artifact. Raw event logs/patches/test output stay under
`/tmp` and are never committed or uploaded.

CLI arguments: `--self-test`, `--out`, `--task-count`. Unknown/
private-looking arguments are rejected with a generic `invalid
arguments` message that does not echo private paths or basenames
(SafeArgumentParser pattern).

`--self-test` runs a real `/tmp` workspace edit/test loop with no
external provider required; it covers real file edits, real test
subprocess execution, all six variant pack designs, mock action
dependence on pack cues, aggregate math, all five marginal-effect
computations, theory-mapping invariants, scanner rejections (path,
snippet, patch, test output, task_id, event log, stack trace,
content_sha, provider auth/endpoint, secret sentinel, URL, line range,
multiline, raw JSON), no-claim flag invariants, fail-closed generation,
and CLI argument surface.

### Guard requirements

1. Default mode generates deterministic synthetic public micro bug
   tasks in code (no external dataset required).
2. Each task+variant gets a fresh `/tmp` workspace; no shared state
   across variants or tasks.
3. The mock agent performs real file edits and runs real subprocess
   tests (stdlib Python).
4. The per-run event log (paths, patches, test output) stays under
   `/tmp` only and is never committed or uploaded
   (`transient_workspace_outputs_only=true`).
5. The committed artifact contains ONLY aggregate counts/rates/means
   and aggregate marginal deltas; no per-run rows, no paths, no file
   paths, no source snippets, no patches/diffs, no test output, no
   event logs, no task IDs, no content hashes, no secrets, no context
   pack contents.
6. Strict fail-closed forbidden scanner runs immediately before writing
   the JSON artifact (`_enforce_no_forbidden`).
7. Self-test failure refuses successful artifact generation
   (`_refuse_on_self_test_failure`).

## Artifact identity (default committed artifact)

The committed artifact at
`artifacts/f1_counterfactual_evidence_utility/f1_counterfactual_evidence_utility_report.json`
is the public aggregate-only smoke artifact. Identity / boundary
fields:

- `schema_version` = `f1_counterfactual_evidence_utility_smoke.v1`
- `generated_by`, `generated_at`, `claim_level`, `status`, `mode`,
  `phase`
- Safe true flags (exactly these, all true):
  `counterfactual_context_variants_executed`, `deterministic_mock_agent`,
  `real_file_edits_performed`, `subprocess_tests_executed`,
  `marginal_utility_metrics_computed`,
  `aggregate_only_public_artifact`, `diagnostic_only`.
- No-claim / no-runtime-change flags (all false):
  `live_llm_agent`, `provider_calls_made`,
  `remote_provider_calls_made`, `downstream_agent_value_proven`,
  `live_agent_generalization_claimed`, `real_user_task_claimed`,
  `true_e_s_calibration_claimed`,
  `automated_e_s_full_calibration_claimed`,
  `human_e_s_calibration_claimed`,
  `external_benchmark_performance_claimed`, `promotion_ready`,
  `default_should_change`, `runtime_behavior_changed`,
  `retriever_changed`, `pack_builder_changed`, `backend_changed`,
  `default_policy_changed`, `evidencecore_semantics_changed`.
- `input_summary`: `synthetic_task_count`, `run_count_per_variant`,
  `total_runs`, `variants` (the six fixed variant labels),
  `variant_count` (6), `effects` (the five fixed effect labels),
  `effect_count` (5), `counterfactual_design` (`true`),
  `workspace_isolation` (`fresh_tmp_per_task_variant`),
  `transient_workspace_outputs_only` (`true`).
- `variant_metrics`: per-variant dict (six variants) with
  `run_count`, `solve_rate`, `tests_pass_rate`,
  `correct_file_before_first_edit_rate`, `wrong_file_edits_mean`,
  `tool_calls_before_first_edit_mean`, `context_tokens_mean`,
  `latency_ms_mean`, `cost_proxy_mean`. No per-run rows, no paths, no
  patches, no test output.
- `marginal_effects`: per-effect dict (five effects) with
  `<metric>_delta` for every rate/mean metric (excluding `run_count`).
- `theory_mapping`: maps effects to E-utility / S-conditional utility
  smoke proxy labels; carries `true_e_s_calibration_claimed=false`,
  `automated_e_s_full_calibration_claimed=false`,
  `human_e_s_calibration_claimed=false`.
- `self_test_summary` + `self_test_checks` + `self_test_passed`.
- `forbidden_scan` summary (fail-closed before writing JSON).

## Aggregate metrics

Per-variant aggregate metrics (no per-run rows):

- `run_count`: number of runs in the variant (= synthetic task count).
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
  (base pack is smallest; primary+support pack is richest).
- `latency_ms_mean`: mean real wall-clock latency of the test
  subprocess in milliseconds.
- `cost_proxy_mean`: mean cost proxy (always 0.0 for the deterministic
  mock agent; no provider calls).

Marginal-effect deltas are emitted for all rate/mean metrics
(excluding `run_count`). Exact synthetic task/run counts are
acceptable because these are synthetic public tasks.

## Forbidden scanner (public, fail-closed)

A strict forbidden-output scanner runs fail-closed before writing the
public JSON. Rejects forbidden dict keys (`task_id`, `task_index`,
`workspace_path`, `workspace`, `file`, `filename`, `filepath`,
`target_file`, `wrong_cue_file`, `support_file`, `target_module`,
`support_module`, `distractor_module`, `test_module`, `path`, `span`,
`start_line`, `end_line`, `content_sha`, `content_hash`, `snippet`,
`code`, `source_code`, `patch`, `diff`, `test_output`, `test_log`,
`test_stdout`, `test_stderr`, `stdout`, `stderr`, `event_log`,
`events`, `log`, `trace`, `raw_event`, `stack_trace`, `traceback`,
`api_key`, `base_url`, `provider_key`, `secret`, `token`,
`credential`, `rows`, `per_run`, `predictions`, `candidates`,
`content`, `source`, `text`, `body`, etc.) anywhere, and rejects
value patterns: ANY URL (no URL allowlist), 32+ char hex digests,
secret-like strings (api_key/base_url/provider_key/secret/password/
credential), path-like strings with file extensions, `/tmp/`
workspace path values, `task_N` task-identifier values, patch/diff
markers (`---`, `+++`, `@@`), stack traces (`Traceback (most recent
call last)`), multiline strings, raw JSON fragments, raw line ranges
`12-34`, and the self-test sentinel.

The scanner runs ONLY against the final public aggregate artifact. The
internal per-run event logs (which contain paths/patches/test stdout/
stderr) are kept in-memory only, never scanned against the public
contract, and never committed.

## Self-tests

- Artifact identity fields (schema, claim, status, mode, phase,
  generated_by).
- Safe true flags (all 7 true); no-claim / no-runtime-change false
  flags (all 18 false).
- Synthetic task generation: deterministic count, symbols, correct
  values, buggy values.
- Pack builder: base has no file cue; primary has target file/symbol/
  operation cue; support has support_file cue only; primary_plus_support
  has both target and support; distractor has wrong_cue_file only;
  primary_plus_distractor has both target and wrong_cue; primary+support
  and primary+distractor are richer than primary; variant_count=6;
  effect_count=5.
- Real workspace creation: target/support/distractor/test files exist
  on disk.
- Real test subprocess: test fails before the fix (bug present).
- Mock agent behavior per variant: base no-op tests fail; primary
  edits correct file tests pass solve; support edits wrong file tests
  fail; primary_plus_support inspects support edits correct file tests
  pass with 2 tool calls; distractor edits wrong file tests fail with
  wrong_edits>base; primary_plus_distractor inspects distractor edits
  correct file then edits distractor tests pass with wrong_edits>primary.
- Mock action dependence on pack cues: target_file cue drives correct
  file edit; wrong_cue_file drives wrong file edit; primary solve rate
  higher than base; support_only and distractor_only do not solve but
  edit wrong file; primary_plus_distractor still solves.
- Aggregate metrics math: run_count, solve_rate, tests_pass_rate,
  correct_file_rate, wrong_file_edits_mean, tool_calls_mean,
  cost_proxy_mean=0.
- Marginal effects: primary_context_vs_base solve_rate_delta positive;
  support_context_vs_base and distractor_context_vs_base solve_rate
  delta zero with wrong_file_edits_delta positive;
  support_added_to_primary solve_rate_delta zero with tool_calls and
  context_tokens delta positive; distractor_added_to_primary
  solve_rate_delta zero with wrong_file_edits, tool_calls, and
  context_tokens delta positive; run_count not present in deltas.
- Theory mapping: marks E-utility proxy, S-conditional proxy,
  S-conditional distractor proxy; true/automated/human E/S calibration
  claimed all false.
- Forbidden scanner rejects: workspace path, file path (target.py,
  support.py, distractor.py, test_target.py), source snippet, context
  text, patch marker, test output, task_id key, task_id value, raw
  event log, stack trace, content_sha key, hex digest value, provider
  auth field, endpoint URL field, sentinel canary, URL value,
  forbidden field name as value, line range value, multiline value,
  raw JSON fragment.
- Forbidden scanner allows: variant names (all six), effect names (all
  five), metric values, delta metric values, workspace isolation token,
  theory-mapping proxy token.
- Fail-closed generation: clean public report does not raise; leaked
  public report raises SystemExit; self-test failure refuses artifact
  generation; failed self-test does not carry success status.
- Public artifact self-scan is clean (no forbidden key anywhere).
- CLI argument surface: `--self-test`, `--out`, `--task-count` are the
  only options (plus `-h`/`--help`); default task count is in range.

## Validation

```text
python3 -m py_compile eval/f1_counterfactual_evidence_utility_smoke.py  => PASS
python3 eval/f1_counterfactual_evidence_utility_smoke.py --self-test  => PASS (162/162 checks)
python3 eval/f1_counterfactual_evidence_utility_smoke.py \
  --out artifacts/f1_counterfactual_evidence_utility/\
f1_counterfactual_evidence_utility_report.json  => PASS
  (status: counterfactual_evidence_utility_smoke_pass,
   forbidden_scan: pass, self_test_passed: true,
   mode: public_aggregate_synthetic_micro_tasks, phase: F1,
   variant_count: 6, effect_count: 5,
   synthetic_task_count: 24, total_runs: 144,
   base_no_context: solve_rate=0.0, tests_pass_rate=0.0,
     wrong_file_edits_mean=0.0, tool_calls_before_first_edit_mean=0.0,
     context_tokens_mean=8.0,
   primary_only: solve_rate=1.0, tests_pass_rate=1.0,
     wrong_file_edits_mean=0.0, tool_calls_before_first_edit_mean=1.0,
     context_tokens_mean=24.0,
   support_only: solve_rate=0.0, tests_pass_rate=0.0,
     wrong_file_edits_mean=1.0, tool_calls_before_first_edit_mean=1.0,
     context_tokens_mean=20.0,
   primary_plus_support: solve_rate=1.0, tests_pass_rate=1.0,
     wrong_file_edits_mean=0.0, tool_calls_before_first_edit_mean=2.0,
     context_tokens_mean=40.0,
   distractor_only: solve_rate=0.0, tests_pass_rate=0.0,
     wrong_file_edits_mean=1.0, tool_calls_before_first_edit_mean=1.0,
     context_tokens_mean=16.0,
   primary_plus_distractor: solve_rate=1.0, tests_pass_rate=1.0,
     wrong_file_edits_mean=1.0, tool_calls_before_first_edit_mean=2.0,
     context_tokens_mean=32.0,
   marginal_effects:
     primary_context_vs_base: solve_rate_delta=+1.0,
       wrong_file_edits_mean_delta=+0.0,
       tool_calls_before_first_edit_mean_delta=+1.0,
       context_tokens_mean_delta=+16.0,
     support_context_vs_base: solve_rate_delta=+0.0,
       wrong_file_edits_mean_delta=+1.0,
       tool_calls_before_first_edit_mean_delta=+1.0,
       context_tokens_mean_delta=+12.0,
     distractor_context_vs_base: solve_rate_delta=+0.0,
       wrong_file_edits_mean_delta=+1.0,
       tool_calls_before_first_edit_mean_delta=+1.0,
       context_tokens_mean_delta=+8.0,
     support_added_to_primary: solve_rate_delta=+0.0,
       wrong_file_edits_mean_delta=+0.0,
       tool_calls_before_first_edit_mean_delta=+1.0,
       context_tokens_mean_delta=+16.0,
     distractor_added_to_primary: solve_rate_delta=+0.0,
       wrong_file_edits_mean_delta=+1.0,
       tool_calls_before_first_edit_mean_delta=+1.0,
       context_tokens_mean_delta=+8.0,
   live_llm_agent: false, provider_calls_made: false,
   remote_provider_calls_made: false,
   downstream_agent_value_proven: false,
   true_e_s_calibration_claimed: false,
   automated_e_s_full_calibration_claimed: false,
   human_e_s_calibration_claimed: false,
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
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

## Caveats

- F1 is the public aggregate-only counterfactual evidence utility smoke
  artifact. It is eval/diagnostic only. It does NOT change runtime,
  retriever, pack, backend, or default policy; it does NOT change
  EvidenceCore semantics. It is NOT a benchmark result, NOT a live
  downstream agent value claim, NOT a true E/S calibration claim, NOT a
  runtime-clean general algorithm claim, NOT an OOD temporal claim, and
  NOT a QuIVer systems claim.
- F1 uses a **deterministic mock agent** (no live LLM, no provider
  calls, no remote calls). The mock agent's behavior is pack-dependent
  by design: the primary pack includes the target file/symbol/operation
  cue, the support pack carries a support cue, and the distractor pack
  carries a wrong-cue file. This is a causal pack-effect smoke, NOT a
  live agent value claim.
- F1 generates **deterministic synthetic public micro bug tasks** in
  code. These are NOT real user tasks and are NOT external benchmark
  tasks. The exact task/run counts are acceptable because these are
  synthetic public tasks.
- F1 performs **real file edits** and **real subprocess tests** (stdlib
  Python) in fresh `/tmp` workspaces per task+variant. The per-run
  event logs, patches, and test output stay under `/tmp` only and are
  NEVER committed or uploaded. The committed artifact contains ONLY
  aggregate counts/rates/means and aggregate marginal-effect deltas.
- F1 does NOT prove downstream agent value. The marginal-effect deltas
  are deterministic mock artifacts of the designed pack cues, NOT
  evidence that any context variant improves a live downstream agent.
  `downstream_agent_value_proven=false`.
- F1 does NOT claim live agent generalization. The deterministic mock
  agent generalizes trivially to the synthetic task family by
  construction; this is NOT a live agent generalization claim.
  `live_agent_generalization_claimed=false`.
- F1 is NOT true E/S calibration. The theory mapping labels are
  naming/interpretation aids only; the marginal deltas are computed
  from deterministic mock aggregate metrics over synthetic tasks, not
  from real human/manual E/S labels and not from real E/S rubric
  scoring. `true_e_s_calibration_claimed=false`,
  `automated_e_s_full_calibration_claimed=false`,
  `human_e_s_calibration_claimed=false`.
- All no-claim / no-runtime-change flags remain false; diagnostic
  flags (`aggregate_only_public_artifact`, `diagnostic_only`) remain
  true; the deterministic-mock-run flags
  (`counterfactual_context_variants_executed`,
  `deterministic_mock_agent`, `real_file_edits_performed`,
  `subprocess_tests_executed`, `marginal_utility_metrics_computed`) are
  the only additional true flags.
- No runtime/retriever/pack/model/backend/default-policy files were
  modified. No promotion/default/runtime claims change.
