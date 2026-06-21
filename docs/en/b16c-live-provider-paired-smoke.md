# B16-C Live-Provider Downstream Paired Smoke (Public Aggregate-Only Artifact)

## Scope and claim boundary

B16-C is the **first B16-style downstream-agent empirical run that uses
a live LLM provider** (OpenAI-compatible) over synthetic public micro
bug tasks. It applies the model's structured edit action locally, runs
real stdlib tests, and publishes only aggregate behavior metrics.

B16-C is explicitly **not** a downstream agent value proof, **not** a
live-agent generalization proof, **not** a production coding-agent
benchmark, **not** a real user task evaluation, **not** an external
benchmark evaluation, and **not** a promotion/default-policy/runtime/
retriever/pack/backend/EvidenceCore semantic change. It does NOT
publish prompts, responses, provider payloads, base URLs, API keys,
raw model routing prefixes, workspace paths, file paths, source
snippets, patches/diffs, test output, raw event logs, or per-run rows.

- Claim level: `live_provider_downstream_paired_smoke_only`.
- Mode: `public_aggregate_synthetic_micro_tasks`; phase `B16-C`.
- Status enum: `live_provider_paired_smoke_pass` on live success;
  `unavailable_no_local_provider_env` when no local provider env;
  `blocked_remote_not_enabled` when remote opt-in not satisfied;
  `provider_call_failed` when provider calls failed;
  `structured_action_parse_failed` when structured action parse
  failed; `paired_run_failed` when paired run could not complete;
  `fail_forbidden_scan` on scanner failure.
- B16-C is **eval/diagnostic only**. It is NOT a benchmark result,
  NOT a downstream agent value claim, NOT a runtime-clean general
  algorithm claim, NOT an OOD temporal claim, and NOT a QuIVer systems
  claim.

### B16-A / B16-B -> B16-C relation

```text
B16-A minimal deterministic/mock downstream paired run (no live LLM)
-> B16-B less-separable deterministic/mock paired stress (no live LLM)
-> B16-C live-provider downstream paired smoke (live LLM, real provider)
   (synthetic public micro tasks; fresh /tmp workspace per task+arm;
    real file edits + real subprocess tests; live LLM provider only
    when --allow-remote + OPENLOCUS_ALLOW_REMOTE=1 + env;
    no raw prompt/response/payload committed)
```

B16-C is NOT B16. The full B16 downstream-coding-agent evaluation phase
remains a bounded planning / feasibility stage that requires live
paired agent runs over real benchmark tasks. B16-C only produces the
first live-provider downstream smoke by running a tiny paired live LLM
agent on synthetic public micro tasks.

## Committed artifact and manual CI live-provider result

The **committed artifact** at
`artifacts/b16c_live_provider_paired_smoke/b16c_live_provider_paired_smoke_report.json`
now mirrors the sanitized aggregate report from manual CI run
`27900913599` (`real-provider-benchmark`, stage
`b16c_live_provider_paired_smoke`, `enable_remote_models=true`). The
run completed `live_provider_paired_smoke_pass`, passed the workflow
privacy validator, and uploaded only the dedicated B16-C aggregate
report. The generic `real-provider` artifact upload is explicitly
disabled for B16-C so `plan.json` and other stage artifacts are not
part of the B16-C upload surface.

The default local no-env run is still truthful: without `--allow-remote`
and the required provider env, the evaluator emits
`unavailable_no_local_provider_env` or `blocked_remote_not_enabled` with
live-run flags false. A live pass is produced ONLY by an explicit local
opt-in run (`--allow-remote` + `OPENLOCUS_ALLOW_REMOTE=1` + provider
env) or by the manual CI workflow described above.

Manual CI run `27900913599` summary:

```text
status: live_provider_paired_smoke_pass
model_display_category: Kimi-K2.7-Code
synthetic_task_count: 2
total_runs: 4
provider calls: 4 attempted / 4 succeeded / 0 failed
invalid_json_count: 0
forbidden_scan: pass
control_sparse: solve_rate=1.0, tests_pass_rate=1.0, wrong_file_edits_mean=0.0
treatment_context_pack: solve_rate=1.0, tests_pass_rate=1.0, wrong_file_edits_mean=0.0
treatment-minus-control solve_rate delta: 0.0
treatment-minus-control context_tokens_mean delta: +32.0
```

This is a live-provider execution smoke and a provider/plumbing success.
It is NOT a downstream value proof: the tiny synthetic task family was
trivial for both arms in this run.

## Synthetic public micro bug task design

B16-C generates deterministic synthetic public micro bug task specs in
code (default 2 tasks; `--task-count` range 2-8, hard cap 8). Each task
spec describes a tiny Python module with a one-line bug (returns the
wrong value) and a stdlib test that asserts the correct value. The fix
is a deterministic one-line return-value replacement.

For each task and arm, B16-C creates a fresh `/tmp` workspace
containing `target.py` (buggy), `distractor.py` (wrong-file
distractor), and `test_target.py` (stdlib test). All workspace files
are real Python files written to disk under `/tmp`. The harness
actually edits files and runs subprocess tests.

## Paired arm design

B16-C runs paired `control_sparse` vs `treatment_context_pack` arms
with the same budget/tool constraints; only the context pack differs.

- **control_sparse**: minimal description; no target file cue; small
  token budget.
- **treatment_context_pack**: richer evidence pack with target file
  cue, symbol cue, and a compact file summary; larger token budget.

The treatment pack is designed to give the live LLM more context about
the target file/symbol. This is a causal pack-effect smoke, NOT a
live agent value claim.

## Live LLM provider constraints

- Env vars:
  - `OPENLOCUS_LLM_BASE_URL`
  - `OPENLOCUS_LLM_API_KEY`
  - `OPENLOCUS_LLM_MODEL`
  - `OPENLOCUS_ALLOW_REMOTE=1`
  - `OPENLOCUS_LLM_WORKFLOW_DISPATCH=1` for CI/manual workflow runs
    when `--require-workflow-dispatch` is set.
- Remote calls are made ONLY when `--allow-remote` AND
  `OPENLOCUS_ALLOW_REMOTE=1` AND (when
  `--require-workflow-dispatch`) `OPENLOCUS_LLM_WORKFLOW_DISPATCH=1`
  AND all of `OPENLOCUS_LLM_BASE_URL` /
  `OPENLOCUS_LLM_API_KEY` / `OPENLOCUS_LLM_MODEL` are set.
- No raw base URL, API key, prompt, response, source snippet,
  patch/diff, stdout/stderr, workspace path, or provider payload in
  artifact/docs.
- The live LLM prompt may include a tiny synthetic/public source
  snippet (the buggy target module) and a compact file summary only
  when the treatment pack carries it. Prompts are NEVER persisted.
- The structured edit action schema is allowlisted: action must be
  `replace_return_value` or `no_op`; file must be `target.py`; no
  arbitrary paths, no shell.
- Usage diagnostics may include aggregate prompt/completion/total
  token counts if the provider returns `usage`; otherwise marked
  unavailable.
- Cost is `cost_proxy` only (always 0.0); no live price inference.
- Research docs/artifacts record normalized model display names
  without provider routing prefixes (for example, `Kimi-K2.7-Code`)
  except when documenting exact workflow/env allowlists.

## CLI

```bash
python3 -m py_compile eval/provider_client.py eval/b16c_live_provider_paired_smoke.py
python3 eval/provider_client.py --self-test
python3 eval/b16c_live_provider_paired_smoke.py --self-test
python3 eval/b16c_live_provider_paired_smoke.py \
    --out artifacts/b16c_live_provider_paired_smoke/\
b16c_live_provider_paired_smoke_report.json
# Live opt-in (only if provider env is available and safe):
OPENLOCUS_ALLOW_REMOTE=1 OPENLOCUS_LLM_WORKFLOW_DISPATCH=1 \
    python3 eval/b16c_live_provider_paired_smoke.py \
    --allow-remote --task-count 2 \
    --out artifacts/b16c_live_provider_paired_smoke/\
b16c_live_provider_paired_smoke_report.json
```

Default mode (without `--allow-remote` or without provider env):
writes a truthful `unavailable_no_local_provider_env` or
`blocked_remote_not_enabled` aggregate report if `--out` is supplied;
no provider calls; live-run flags false except
`aggregate_only_public_artifact=true` and `diagnostic_only=true`.

CLI arguments: `--self-test`, `--out`, `--allow-remote`,
`--require-workflow-dispatch`, `--task-count`. Unknown/private-looking
arguments are rejected with a generic `invalid arguments` message that
does not echo private paths or basenames (SafeArgumentParser pattern).

`--self-test` runs no-network self-tests with fake provider responses;
covers remote gating, missing env unavailable path, provider diagnostics
redaction, fake valid edit apply/test, invalid JSON count, fixed
provider error category, action path/action restrictions, real
edit+test execution, scanner forbidden keys/values, no-claim flags,
and fail-closed scanner behavior.

## Provider client helper

`eval/provider_client.py` is a minimal OpenAI-compatible chat helper
shared by B16-C. It returns a safe `ProviderCallResult` object exposing
ONLY aggregate counts (calls attempted/succeeded/failed,
invalid_json, timeout, latency, numeric provider `usage` if present, a
fixed failure-category enum token, HTTP status). Raw prompts,
messages, responses, base URLs, API keys, and provider payloads are
NEVER returned in public diagnostics. Safe failure categories are a
fixed enum; raw exception text is suppressed.

## Artifact identity (default committed artifact)

The committed artifact at
`artifacts/b16c_live_provider_paired_smoke/b16c_live_provider_paired_smoke_report.json`
is the public aggregate-only smoke artifact. Identity / boundary
fields:

- `schema_version` = `b16c_live_provider_paired_smoke.v1`
- `generated_by`, `generated_at`, `claim_level`, `status`, `mode`,
  `phase`, `model_display_category` (normalized; no provider routing prefix).
- Safe true flags (only on live run; exactly these, all true):
  `downstream_agent_runs_performed`, `live_llm_agent`,
  `provider_calls_made`, `remote_provider_calls_made`,
  `paired_run_executed`, `synthetic_micro_tasks_used`,
  `real_file_edits_performed`, `real_test_commands_executed`,
  `agent_behavior_metrics_evaluated`,
  `aggregate_only_public_artifact`, `diagnostic_only`.
- On unavailable/blocked status, live-run flags are false except
  `aggregate_only_public_artifact=true` and `diagnostic_only=true`
  (and `synthetic_micro_tasks_used=false` because no run).
- Always-false no-claim flags:
  `downstream_agent_value_proven`,
  `live_agent_generalization_claimed`, `promotion_ready`,
  `default_should_change`,
  `external_benchmark_performance_claimed`, `real_user_task_claimed`,
  `runtime_behavior_changed`, `retriever_changed`,
  `pack_builder_changed`, `backend_changed`,
  `default_policy_changed`, `evidencecore_semantics_changed`.
- `input_summary`: `synthetic_task_count`, `run_count_per_arm`,
  `total_runs`, `arms` (`[control_sparse, treatment_context_pack]`),
  `paired_design` (`true`), `workspace_isolation`
  (`fresh_tmp_per_task_arm`), `transient_workspace_outputs_only`
  (`true`), `designed_causal_subset` (`true`).
- `arm_results`: list of fixed records
  `{arm, metrics, provider_summary, failure_category_counts}`.
- `paired_deltas`: list of fixed records
  `{baseline_arm, treatment_arm, metric, delta}`.
- `self_test_summary` + `self_test_checks` + `self_test_passed`.
- `forbidden_scan` summary (fail-closed before writing JSON).

## Aggregate metrics

Per-arm aggregate metrics (records-shaped; no per-run rows):

- `run_count`, `solve_rate`, `tests_pass_rate`,
  `correct_file_before_first_edit_rate`, `wrong_file_edits_mean`,
  `tool_calls_before_first_edit_mean`, `context_tokens_mean`,
  `latency_ms_mean`, `cost_proxy_mean` (always 0.0).

`provider_summary` (per-arm aggregate): `calls_attempted`,
`calls_succeeded`, `calls_failed`, `invalid_json_count`,
`timeout_count`, `failure_category_counts` (fixed enum tokens only),
`usage_available`, `prompt_tokens_total`, `completion_tokens_total`,
`total_tokens_total`, `latency_ms_total`.

`paired_deltas`: treatment-minus-control deltas as fixed records
`{baseline_arm, treatment_arm, metric, delta}` (excluding `run_count`,
which is identical by paired design).

## Forbidden scanner (public, fail-closed)

A strict forbidden-output scanner runs fail-closed before writing the
public JSON. Rejects forbidden dict keys anywhere (`prompt`,
`prompts`, `message`, `messages`, `response`, `responses`,
`raw_response`, `request`, `request_body`, `provider_payload`,
`url`, `base_url`, `endpoint`, `api_key`, `token`, `secret`,
`authorization`, `bearer`, `workspace`, `workspace_path`, `path`,
`file`, `target_file`, `target_module`, `distractor_module`,
`test_module`, `snippet`, `code`, `source`, `patch`, `diff`,
`test_output`, `stdout`, `stderr`, `event_log`, `stack_trace`,
`content_sha`, `task_id`, `per_run`, `model_id_raw`, `model_id`,
etc.) and value patterns: ANY URL (no URL allowlist), 32+ char hex
digests, secret-like strings, path-like strings with file extensions,
`/tmp/` workspace path values, `task_N` task-identifier values,
patch/diff markers, stack traces, multiline strings, raw JSON
fragments, raw line ranges, raw model routing prefixes, and
the self-test sentinel.

The scanner runs ONLY against the final public aggregate artifact.
The internal per-run event logs (which contain paths/patches/test
stdout/stderr) are kept in-memory only, never scanned against the
public contract, and never committed.

## Self-tests

- Artifact identity fields (schema, claim, status enum, mode, phase,
  generated_by).
- Always-false no-claim flags (all 12 false).
- Live-run flag gating (unavailable report: live-run flags false;
  live report: live-run flags true).
- Synthetic task generation (deterministic count, symbols, correct
  values).
- Pack builder (control_sparse vs treatment_context_pack difference;
  treatment richer than control).
- Real workspace + real edit + real test (fake valid provider
  response): test fails before fix; fake valid edit applies correct
  file; tests pass; solve=true; real file edit applied; provider call
  summary reflects success.
- Fake invalid JSON response (parse failure): no edit; tests fail; no
  raw response in run result.
- Edit action restrictions: disallowed file rejected; disallowed
  action rejected; missing symbol rejected; non-int new_return_value
  rejected; non-object rejected; valid action accepted; no_op action
  accepted.
- Aggregate metrics + deltas (records-shaped; excludes run_count).
- Model display normalization (strips provider routing prefix; empty returns
  `unavailable`; strips unsafe chars).
- Scanner rejections: workspace path, file path, source snippet,
  patch marker, test output, task_id key, raw event log, stack
  trace, content_sha key, hex digest, provider auth field, endpoint
  URL field, raw model routing prefix, URL value, prompt key,
  response key, messages key, provider_payload key, sentinel canary.
- Scanner allows: arm names, metric records, model display category,
  failure category token.
- Fail-closed generation: clean public report does not raise; leaked
  public report raises SystemExit; self-test failure refuses artifact
  generation.
- Public artifact self-scan is clean (no forbidden key anywhere).
- CLI argument surface: `--self-test`, `--out`, `--allow-remote`,
  `--require-workflow-dispatch`, `--task-count` are the only options
  (plus `-h`/`--help`); default task count is in range.
- Remote gating: blocked when `allow_remote=False`; unavailable when
  env missing; `provider_client._check_remote_enabled` enum tokens.
- Env restoration regression: self-tests restore provider env exactly so
  the live CI gate is not cleared before the provider call.

## Validation

```text
python3 -m py_compile eval/provider_client.py eval/b16c_live_provider_paired_smoke.py  => PASS
python3 eval/provider_client.py --self-test                            => PASS (33/33 checks)
python3 eval/b16c_live_provider_paired_smoke.py --self-test            => PASS (119/119 checks)
python3 eval/b16c_live_provider_paired_smoke.py \
  --out artifacts/b16c_live_provider_paired_smoke/\
b16c_live_provider_paired_smoke_report.json                           => PASS
  (status: blocked_remote_not_enabled,
   forbidden_scan: pass, self_test_passed: true,
   mode: public_aggregate_synthetic_micro_tasks, phase: B16-C,
   model_display_category: unavailable,
   live_llm_agent: false, provider_calls_made: false,
   remote_provider_calls_made: false, paired_run_executed: false,
   downstream_agent_value_proven: false, promotion_ready: false,
   default_should_change: false, retriever_changed: false,
   pack_builder_changed: false, backend_changed: false,
   default_policy_changed: false, evidencecore_semantics_changed: false,
   runtime_behavior_changed: false,
   external_benchmark_performance_claimed: false,
   live_agent_generalization_claimed: false, real_user_task_claimed: false)
python3 scripts/validate_docs_i18n.py                                  => PASS
git diff --check                                                       => PASS
```

The local no-env validation path is truthful and blocked/unavailable.
After manual CI run `27900913599`, the committed artifact mirrors the
sanitized aggregate `live_provider_paired_smoke_pass` report from that
run. The live CI report passed privacy validation and contains no raw
prompt/response/provider payload/base URL/API key/workspace path/patch/
diff/stdout/stderr/per-run rows.

## Caveats

- B16-C is the public aggregate-only live-provider downstream paired
  smoke artifact. It is eval/diagnostic only. It does NOT change
  runtime, retriever, pack, backend, or default policy; it does NOT
  change EvidenceCore semantics. It is NOT a benchmark result, NOT a
  downstream agent value claim, NOT a runtime-clean general algorithm
  claim, NOT an OOD temporal claim, and NOT a QuIVer systems claim.
- B16-C uses a **live LLM provider** (OpenAI-compatible) only when
  `--allow-remote` + `OPENLOCUS_ALLOW_REMOTE=1` + provider env are
  all set. The default local no-env path remains truthful
  (`blocked_remote_not_enabled` / `unavailable_no_local_provider_env`),
  while the committed artifact mirrors the successful sanitized manual
  CI live-provider run `27900913599`. It is NOT a fake pass.
- B16-C does NOT prove downstream agent value. The treatment-vs-control
  delta (when a live run completes) is a smoke signal, NOT evidence
  that the treatment pack improves a live downstream agent.
  `downstream_agent_value_proven=false`.
- B16-C does NOT claim live agent generalization. The tiny synthetic
  public micro task family is trivial by construction; this is NOT a
  live agent generalization claim.
  `live_agent_generalization_claimed=false`.
- B16-C does NOT publish prompts, responses, provider payloads, base
  URLs, API keys, raw model routing prefixes, workspace paths, file
  paths, source snippets, patches/diffs, test output, raw event logs,
  or per-run rows. The per-run event logs, prompts, responses, and
  test output stay under `/tmp` only and are NEVER committed or
  uploaded.
- The committed artifact contains ONLY aggregate counts/rates/means
  in records-shaped containers. No raw model routing prefix is
  emitted; only the normalized `model_display_category` is recorded.
- All no-claim / no-runtime-change flags remain false; diagnostic
  flags (`aggregate_only_public_artifact`, `diagnostic_only`) remain
  true; the live-run flags are true ONLY when a live run actually
  executed.
- No runtime/retriever/pack/model/backend/default-policy files were
  modified. No promotion/default/runtime claims change.
