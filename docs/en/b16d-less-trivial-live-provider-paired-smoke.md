# B16-D Less-Trivial Live-Provider Downstream Paired Smoke (Public Aggregate-Only Artifact)

## Scope and claim boundary

B16-D is a **harder follow-up to B16-C**. The synthetic public task
family is **less trivial**: multi-file, same/similar symbol names in
target and distractor files, and a **support relation** needed to
determine the correct value/operation. A live LLM provider
(OpenAI-compatible) is used over synthetic public micro bug tasks; the
model's structured edit action is applied locally; real stdlib tests
run; only aggregate behavior metrics are published.

B16-D is explicitly **not** a downstream agent value proof, **not** a
live-agent generalization proof, **not** an external benchmark result,
**not** a production coding-agent benchmark, **not** a real user task
evaluation, and **not** a promotion/default-policy/runtime/retriever/
pack/backend/EvidenceCore semantic change. It does NOT publish prompts,
responses, provider payloads, base URLs, API keys, raw model routing
prefixes, workspace paths, file paths, source snippets, patches/diffs,
test output, raw event logs, or per-run rows.

- Claim level: `less_trivial_live_provider_downstream_paired_smoke_only`.
- Mode: `public_aggregate_synthetic_less_trivial_tasks`; phase `B16-D`.
- Status enum: `live_provider_less_trivial_paired_smoke_pass` on live
  success; `blocked_remote_not_enabled` /
  `unavailable_no_local_provider_env` when remote opt-in not satisfied;
  `provider_call_failed` / `structured_action_parse_failed` /
  `paired_run_failed` / `fail_forbidden_scan` on failures.
- B16-D is **eval/diagnostic only**. It is NOT a benchmark result, NOT
  a downstream agent value claim, NOT a runtime-clean general algorithm
  claim, NOT an OOD temporal claim, and NOT a QuIVer systems claim.

### B16-C -> B16-D relation

```text
B16-C live-provider downstream paired smoke (both arms saturated;
  solve_rate=1.0, delta=0.0)
-> B16-D less-trivial live-provider downstream paired smoke
   (multi-file; same-symbol distractor; support relation required;
    control lacks decisive cue; treatment includes target file cue,
    target symbol cue, support-relation cue, exact edit constraint;
    same aggregate-only safety model; CI pass does NOT require
    treatment improvement)
```

B16-D is NOT B16. The full B16 downstream-coding-agent evaluation phase
remains a bounded planning / feasibility stage. B16-D only produces a
harder live-provider downstream smoke by running a tiny paired live LLM
agent on synthetic public less-trivial micro tasks.

## Committed artifact vs manual CI live-provider result

The **committed artifact** at
`artifacts/b16d_less_trivial_live_provider_paired_smoke/b16d_less_trivial_live_provider_paired_smoke_report.json`
is a **truthful local report**. If a local provider env is not available
(the default state), it carries status `blocked_remote_not_enabled` or
`unavailable_no_local_provider_env` with all live-run flags false
(except `aggregate_only_public_artifact=true` and
`diagnostic_only=true`). A live
`live_provider_less_trivial_paired_smoke_pass` artifact is produced
ONLY by an explicit local opt-in run (`--allow-remote` +
`OPENLOCUS_ALLOW_REMOTE=1` + provider env) or by the manual CI
`real-provider-benchmark` workflow with
`stage=b16d_less_trivial_live_provider_paired_smoke` and
`enable_remote_models=true`.

**Manual CI live-provider run: pending.** As of this commit, no manual
CI `real-provider-benchmark` run for
`b16d_less_trivial_live_provider_paired_smoke` has been triggered yet.
When it is triggered, the CI report will be uploaded as
`artifacts/real_provider_ci/b16d_less_trivial_live_provider_paired_smoke_report.json`
and the docs will be updated to reflect the CI run result.

## Less-trivial synthetic public micro bug task design

B16-D generates deterministic synthetic public less-trivial micro bug
task specs in code (default 4; `--task-count` range 2-8, hard cap 8).
Each task spec is **multi-file**:

- `target.py`: contains the buggy function (same symbol name as the
  distractor to make the task less-trivial).
- `distractor.py`: contains a same-named symbol (decoy).
- `support.py`: defines a helper constant whose value determines the
  correct return value (**support relation**).
- `test_target.py`: imports `target` AND `support`; asserts the
  correct relation. The test only passes if `target` uses the support
  relation correctly.

The correct fix requires the agent to read the support relation
(helper constant value) and apply it to the target. The deterministic
correct value formula is:

```text
helper_constant = 10 + task_index * 7
correct_value   = helper_constant * 2 + task_index
```

A control pack that lacks the support-relation cue cannot determine
the correct value; a treatment pack includes the target file cue,
target symbol cue, support-relation cue (helper constant name + value
+ relation), and the exact edit constraint.

For each task and arm, B16-D creates a fresh `/tmp` workspace with the
four real Python files. The harness actually edits files and runs
subprocess tests.

## Paired arm design

B16-D runs paired `control_sparse` vs `treatment_context_pack` arms
with the same budget/tool constraints; only the context pack differs.

- **control_sparse**: minimal description; NO target file cue; NO
  support-relation cue; small token budget. The agent cannot determine
  the correct value without the support relation.
- **treatment_context_pack**: target file cue, target symbol cue,
  support-relation cue (helper constant name + value + relation), and
  exact edit constraint; larger token budget.

The treatment pack is designed to give the live LLM the decisive cues
needed to determine the correct value via the support relation. This is
a causal pack-effect smoke, NOT a live agent value claim.

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
- The live LLM prompt may include a tiny synthetic/public source snippet
  (the buggy target module + the support module) and a
  support-relation cue only when the treatment pack carries it.
  Prompts are NEVER persisted.
- The structured edit action schema is allowlisted: action must be
  `replace_return_value`, `choose_helper_constant`, or `no_op`; file
  must be `target.py`; no arbitrary paths, no shell. Distractor and
  support files are NOT editable.
- Usage diagnostics may include aggregate prompt/completion/total
  token counts if the provider returns `usage`; otherwise marked
  unavailable.
- Cost is `cost_proxy` only (always 0.0); no live price inference.
- Research docs/artifacts record normalized model display names without
  provider routing prefixes (for example, `Kimi-K2.7-Code`) except
  when documenting exact workflow/env allowlists.

## CLI

```bash
python3 -m py_compile eval/b16d_less_trivial_live_provider_paired_smoke.py
python3 eval/b16d_less_trivial_live_provider_paired_smoke.py --self-test
python3 eval/b16d_less_trivial_live_provider_paired_smoke.py \
    --out artifacts/b16d_less_trivial_live_provider_paired_smoke/\
b16d_less_trivial_live_provider_paired_smoke_report.json
# Live opt-in (only if provider env is available and safe):
OPENLOCUS_ALLOW_REMOTE=1 OPENLOCUS_LLM_WORKFLOW_DISPATCH=1 \
    python3 eval/b16d_less_trivial_live_provider_paired_smoke.py \
    --allow-remote --task-count 4 \
    --out artifacts/b16d_less_trivial_live_provider_paired_smoke/\
b16d_less_trivial_live_provider_paired_smoke_report.json
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
redaction, fake valid edit apply/test (using the support relation),
invalid JSON count, fixed provider error category, action path/action
restrictions (including distractor/support file rejection), same-symbol
distractor task existence, control-lacks-decisive-cue vs
treatment-includes-it, records-shaped aggregate artifact, honest signal
fields, scanner forbidden keys/values, no-claim flags, and fail-closed
scanner behavior.

## Provider client helper

B16-D reuses `eval/provider_client.py` from B16-C (unchanged). It is a
minimal OpenAI-compatible chat helper that returns a safe
`ProviderCallResult` object exposing ONLY aggregate counts (calls
attempted/succeeded/failed, invalid_json, timeout, latency, numeric
provider `usage` if present, a fixed failure-category enum token, HTTP
status). Raw prompts, messages, responses, base URLs, API keys, and
provider payloads are NEVER returned in public diagnostics.

## Artifact identity (default committed artifact)

The committed artifact at
`artifacts/b16d_less_trivial_live_provider_paired_smoke/b16d_less_trivial_live_provider_paired_smoke_report.json`
is the public aggregate-only smoke artifact. Identity / boundary
fields:

- `schema_version` = `b16d_less_trivial_live_provider_paired_smoke.v1`
- `generated_by`, `generated_at`, `claim_level`, `status`, `mode`,
  `phase`, `model_display_category` (normalized; no provider routing
  prefix).
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
  (`true`), `designed_causal_subset` (`true`),
  `less_trivial_multi_file_tasks` (`true`),
  `support_relation_required` (`true`).
- `arm_results`: list of fixed records
  `{arm, metrics, provider_summary, failure_category_counts}`.
- `paired_deltas`: list of fixed records
  `{baseline_arm, treatment_arm, metric, delta}`.
- `honest_signals`: `context_pack_signal_observed` (bool),
  `treatment_solve_rate_delta` (number),
  `treatment_wrong_file_edits_delta` (number). These are diagnostic
  smoke outcomes only, NEVER promotion/default/value claims.
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

## CI pass criterion

CI pass means:

```text
live run completed + privacy scan passed + artifact is honest
```

CI pass does NOT require treatment improvement. Zero or negative
treatment delta is a valid empirical result if honestly recorded.
Both arms solving or both arms failing is a valid empirical result.

## Forbidden scanner (public, fail-closed)

A strict forbidden-output scanner runs fail-closed before writing the
public JSON. Rejects forbidden dict keys anywhere (`prompt`,
`prompts`, `message`, `messages`, `response`, `responses`,
`raw_response`, `request`, `request_body`, `provider_payload`,
`url`, `base_url`, `endpoint`, `api_key`, `token`, `secret`,
`authorization`, `bearer`, `workspace`, `workspace_path`, `path`,
`file`, `target_file`, `target_module`, `distractor_module`,
`support_module`, `test_module`, `snippet`, `code`, `source`,
`patch`, `diff`, `test_output`, `stdout`, `stderr`, `event_log`,
`stack_trace`, `content_sha`, `task_id`, `per_run`, `model_id_raw`,
`model_id`, etc.) and value patterns: ANY URL (no URL allowlist),
32+ char hex digests, secret-like strings, path-like strings with file
extensions, `/tmp/` workspace path values, `task_N` task-identifier
values, patch/diff markers, stack traces, multiline strings, raw JSON
fragments, raw line ranges, raw model routing prefixes, and the
self-test sentinel.

The scanner runs ONLY against the final public aggregate artifact. The
internal per-run event logs (which contain paths/patches/test
stdout/stderr) are kept in-memory only, never scanned against the
public contract, and never committed.

## Self-tests

- Artifact identity fields (schema, claim, status enum, mode, phase,
  generated_by).
- Always-false no-claim flags (all 12 false).
- Live-run flag gating (unavailable report: live-run flags false; live
  report: live-run flags true).
- Less-trivial synthetic task generation (deterministic count, symbols,
  helper constants, correct values using the support relation).
- Multi-file workspace + same-symbol distractor (target and distractor
  share the same symbol; support module defines the helper constant).
- Pack builder (control lacks target file cue AND support-relation
  cue; treatment includes target file cue, symbol cue,
  support-relation cue, exact edit constraint; treatment richer than
  control).
- Real workspace + real edit + real test (fake valid provider
  response using the support relation): test fails before fix; fake
  valid edit applies correct file using the support relation; tests
  pass; solve=true; real file edit applied; provider call summary
  reflects success.
- Fake invalid JSON response (parse failure): no edit; tests fail; no
  raw response in run result.
- Edit action restrictions: disallowed file rejected; disallowed
  action rejected; distractor.py rejected; support.py rejected;
  missing symbol rejected; non-int new_return_value rejected;
  non-object rejected; valid action accepted;
  `choose_helper_constant` accepted; `no_op` accepted.
- Aggregate metrics + deltas (records-shaped; excludes run_count).
- Honest signal fields (`context_pack_signal_observed`,
  `treatment_solve_rate_delta`, `treatment_wrong_file_edits_delta`);
  zero delta -> `context_pack_signal_observed=False`.
- Model display normalization (strips provider routing prefix; empty returns
  `unavailable`; strips unsafe chars).
- Scanner rejections: workspace path, file path, source snippet,
  patch marker, test output, task_id key, raw event log, stack trace,
  content_sha key, hex digest, provider auth field, endpoint URL
  field, raw model routing prefix, URL value, prompt key, response
  key, messages key, provider_payload key, sentinel canary.
- Scanner allows: arm names, metric records, model display category,
  honest signal field, failure category token.
- Fail-closed generation: clean public report does not raise; leaked
  public report raises SystemExit; self-test failure refuses artifact
  generation.
- Public artifact self-scan is clean (no forbidden key anywhere).
- CLI argument surface: `--self-test`, `--out`, `--allow-remote`,
  `--require-workflow-dispatch`, `--task-count` are the only options
  (plus `-h`/`--help`); default task count is in range.
- Remote gating: blocked when `allow_remote=False`; unavailable when
  env missing; `provider_client._check_remote_enabled` enum tokens.

## Validation

```text
python3 -m py_compile eval/b16d_less_trivial_live_provider_paired_smoke.py  => PASS
python3 eval/b16d_less_trivial_live_provider_paired_smoke.py --self-test  => PASS (138/138 checks)
python3 eval/b16d_less_trivial_live_provider_paired_smoke.py \
  --out artifacts/b16d_less_trivial_live_provider_paired_smoke/\
b16d_less_trivial_live_provider_paired_smoke_report.json               => PASS
  (status: blocked_remote_not_enabled,
   forbidden_scan: pass, self_test_passed: true,
   mode: public_aggregate_synthetic_less_trivial_tasks, phase: B16-D,
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

The committed artifact is the truthful local unavailable/blocked
report because no local provider env is available. A live
`live_provider_less_trivial_paired_smoke_pass` artifact requires an
explicit local opt-in run or the manual CI `real-provider-benchmark`
workflow with
`stage=b16d_less_trivial_live_provider_paired_smoke` and
`enable_remote_models=true`. **Manual CI live-provider run: pending.**

## Caveats

- B16-D is the public aggregate-only less-trivial live-provider
  downstream paired smoke artifact. It is eval/diagnostic only. It
  does NOT change runtime, retriever, pack, backend, or default
  policy; it does NOT change EvidenceCore semantics. It is NOT a
  benchmark result, NOT a downstream agent value claim, NOT a
  runtime-clean general algorithm claim, NOT an OOD temporal claim,
  and NOT a QuIVer systems claim.
- B16-D uses a **live LLM provider** (OpenAI-compatible) only when
  `--allow-remote` + `OPENLOCUS_ALLOW_REMOTE=1` + provider env are
  all set. The committed artifact is truthful: if no local provider
  env is available, it carries status `blocked_remote_not_enabled` /
  `unavailable_no_local_provider_env` with live-run flags false. It
  is NOT a fake pass.
- B16-D does NOT prove downstream agent value.
  `downstream_agent_value_proven=false`.
- B16-D does NOT claim live agent generalization.
  `live_agent_generalization_claimed=false`.
- B16-D does NOT publish prompts, responses, provider payloads, base
  URLs, API keys, raw model routing prefixes, workspace paths, file
  paths, source snippets, patches/diffs, test output, raw event logs,
  or per-run rows. The per-run event logs, prompts, responses, and
  test output stay under `/tmp` only and are NEVER committed or
  uploaded.
- The committed artifact contains ONLY aggregate counts/rates/means in
  records-shaped containers. No raw model routing prefix is emitted;
  only the normalized `model_display_category` is recorded.
- `honest_signals` (`context_pack_signal_observed`,
  `treatment_solve_rate_delta`, `treatment_wrong_file_edits_delta`)
  are diagnostic smoke outcomes only, NEVER promotion/default/value
  claims. Zero or negative treatment delta is a valid empirical
  result.
- All no-claim / no-runtime-change flags remain false; diagnostic
  flags (`aggregate_only_public_artifact`, `diagnostic_only`) remain
  true; the live-run flags are true ONLY when a live run actually
  executed.
- No runtime/retriever/pack/model/backend/default-policy files were
  modified. No promotion/default/runtime claims change.
