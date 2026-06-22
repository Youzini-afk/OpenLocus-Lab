# B16-G Context-Pack Atom Ablation Live-Provider Smoke (Public Aggregate-Only Artifact)

## Scope and claim boundary

B16-G explains B16-F's downstream tie: context packs beat sparse, but BEA
v0.3 did not beat same-budget BM25. B16-G runs a live-provider atom
ablation to identify whether the target-file cue, the decisive support
cue, the distractor cue, or their combination drive solves on bounded
synthetic coding tasks.

B16-G uses eight fixed allowlisted task families. For each synthetic
workspace, B16-G constructs deterministic atom compositions per arm.
The atom composition (which source snippets and cues are included in
the prompt) is recorded only in private SCORE/event JSONL under `/tmp`.
A live LLM provider (OpenAI-compatible) is used over synthetic public
micro bug tasks; the model's structured edit action is applied locally;
real stdlib tests run; only aggregate behavior metrics are published.

B16-G is explicitly **not** a downstream agent value proof, **not** a
live-agent generalization proof, **not** an external benchmark result,
**not** a production coding-agent benchmark, **not** a real user task
evaluation, **not** a method winner/default/promotion claim, **not** a
calibration claim, **not** a BEA superiority claim, and **not** a
runtime/retriever/pack/backend/default-policy/EvidenceCore semantic
change. It does NOT publish prompts, responses, provider payloads, base
URLs, API keys, raw model routing prefixes, workspace paths, file paths,
source snippets, patches/diffs, test output, atom compositions, raw
event logs, or per-run rows.

- Claim level: `context_pack_atom_ablation_downstream_smoke_only`.
- Mode: `public_aggregate_synthetic_task_family_matrix`; phase `B16-G`.
- Status enum: `context_pack_atom_ablation_smoke_pass` on live
  success; `blocked_remote_not_enabled` /
  `unavailable_no_local_provider_env` when remote opt-in not satisfied;
  `provider_call_failed` / `structured_action_parse_failed` /
  `paired_run_failed` / `fail_forbidden_scan` on failures.
- B16-G is **eval/diagnostic only**. It is NOT a benchmark result, NOT
  a downstream agent value claim, NOT a runtime-clean general algorithm
  claim, NOT an OOD temporal claim, NOT a QuIVer systems claim, NOT a
  method winner/calibration/promotion/default/runtime/EvidenceCore
  claim, and NOT a BEA superiority claim.

### B16-F -> B16-G relation

```text
B16-F BEA-derived context pack downstream paired smoke
  (3 arms: control_sparse, bm25_same_budget_context_pack,
   bea_v03_context_pack; 8 tasks x 3 arms = 24 live calls;
   context packs beat sparse, but BEA tied same-budget BM25)
-> B16-G context-pack atom ablation downstream smoke
   (5 arms: control_sparse, target_only, support_only,
    distractor_plus_support, target_plus_support;
    8 tasks x 5 arms = 40 live calls default;
    explains which atoms drive solves; same aggregate-only safety
    model; CI pass does NOT require any atom to win)
```

B16-G addresses the deep-research directive's gap: B16-F showed context
packs help over sparse but BEA did not improve over same-budget BM25.
B16-G decomposes the context pack into atoms to explain which atoms
(target file cue, support module cue, decisive cue, distractor cue)
drive the solve signal.

## Arms

B16-G runs FIVE fixed arms with the same budget/tool constraints; only
the atom composition differs:

1. **`control_sparse`**: task issue only, minimal context; no atoms.
   The agent cannot determine the correct value/operation without any
   cues.
2. **`target_only`**: target file cue + target symbol cue (target.py
   source + symbol name). NO support module, NO decisive cue. Tests
   whether the target file cue alone is sufficient.
3. **`support_only`**: support module cue + decisive cue
   (support/config/cross_file source + family-specific decisive
   relation). NO target file cue, NO symbol cue. Tests whether the
   support relation alone is sufficient.
4. **`distractor_plus_support`**: distractor file cue + support module
   cue + decisive cue (distractor.py + support source + decisive
   relation). NO target file cue, NO symbol cue. The distractor is the
   wrong file; tests whether the agent edits distractor.py (wrong file)
   when the distractor cue is present instead of the target cue.
5. **`target_plus_support`**: target file cue + target symbol cue +
   support module cue + decisive cue (target.py + support source +
   decisive relation). This is the "full pack" arm; tests whether the
   full pack solves.

Primary contrasts:

- `target_plus_support` vs `distractor_plus_support` (target file cue
  matters when support is present).
- `target_plus_support` vs `support_only` (target file cue matters on
  top of support).
- `target_only` vs `support_only` (which atom alone is sufficient).

Secondary contrasts: each context arm vs `control_sparse`.

## Committed artifact and default local run

The committed artifact at
`artifacts/b16g_context_pack_atom_ablation/b16g_context_pack_atom_ablation_report.json`
is the public aggregate-only smoke artifact. The default local no-env
run is truthful: without `--allow-remote` and the required provider env,
the evaluator emits `blocked_remote_not_enabled` (or
`unavailable_no_local_provider_env` when `OPENLOCUS_ALLOW_REMOTE=1` but
provider env is missing) with live-run flags false. It is NOT a fake
pass.

Manual real-provider CI run (when executed via
`real-provider-benchmark.yml` stage
`b16g_context_pack_atom_ablation` with `enable_remote_models=true`,
`task_count=8`) produces 40 live provider calls (8 tasks x 5 arms). The
committed artifact will be updated to mirror the sanitized aggregate
report from the first successful manual CI run.

## Heterogeneous synthetic public task-family matrix design

B16-G reuses the eight fixed allowlisted task families from B16-F for
comparability (default 8 tasks; `--task-count` range 4-12, hard cap 12;
default 40 live calls = 8 x 5 arms; max 60 live calls). Tasks cycle
through the eight families so the matrix is balanced.

### Task families

The same eight families as B16-F: `same_symbol_support_relation`,
`operation_ambiguity`, `boundary_condition`,
`helper_dependency_choice`, `config_or_test_mismatch`,
`distractor_file`, `nearby_wrong_function`, `cross_file_symbol`. Each
family has a different decisive cue that the support module carries.

### Multi-file workspace

For each task and arm, B16-G creates a fresh `/tmp` workspace with four
real Python files: `target.py` (buggy function), `distractor.py`
(same-named decoy), `support.py`/`config.py`/`cross_file.py` (helper
constant), and `test_target.py` (imports target AND support; asserts
the correct family-specific relation). The harness actually edits files
and runs subprocess tests.

## Atom pack builder

Each arm gets a deterministic set of atoms (source snippets and cues
included in the prompt). The atom composition is private (written only
to private SCORE/event JSONL under `/tmp`). The public pack descriptor
carries only booleans/counts/token estimates.

Atom semantics:

- `target_file_cue`: prompt includes target.py source + "edit target.py".
- `target_symbol_cue`: prompt includes the exact symbol name.
- `support_module_cue`: prompt includes support/config/cross_file source.
- `decisive_cue`: prompt includes the family-specific decisive relation.
- `distractor_file_cue`: prompt includes distractor.py source (wrong
  file).

Arm composition:

- `control_sparse`: none.
- `target_only`: target_file_cue + target_symbol_cue (NO support, NO
  decisive).
- `support_only`: support_module_cue + decisive_cue (NO target
  file/symbol).
- `distractor_plus_support`: distractor_file_cue + support_module_cue +
  decisive_cue (NO target file; wrong-file cue).
- `target_plus_support`: target_file_cue + target_symbol_cue +
  support_module_cue + decisive_cue (full pack).

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
  patch/diff, stdout/stderr, workspace path, atom composition, or
  provider payload in artifact/docs.
- The live LLM prompt may include tiny synthetic/public source snippets
  (target.py / distractor.py / support module) and a family-specific
  decisive cue only when the pack carries it. Prompts are NEVER
  persisted (only written to private event JSONL under `/tmp`).
- The structured edit action schema is allowlisted: action must be
  `replace_return_value`, `choose_helper_constant`, or `no_op`; file
  must be `target.py`; no arbitrary paths, no shell. Distractor and
  support files are NOT editable.
- Usage diagnostics may include aggregate prompt/completion/total
  token counts if the provider returns `usage`; otherwise marked
  unavailable.
- Cost is `cost_proxy` only (always 0.0); no live price inference.
- Research docs/artifacts record normalized model display names without
  routing prefix (e.g. `Kimi-K2.7-Code`, not the raw routing prefix).

## Private artifacts (under /tmp only; never committed/uploaded)

For every task x arm, B16-G writes:

- **Private SCORE JSONL** (one row per task x arm = 40 rows default):
  atom_composition, score_outcome (per-arm metrics), latency_ms,
  tokens, provider_calls, failure_reason.
- **Private event JSONL** (one row per task x arm = 40 rows default):
  prompt, response, parsed_action, patch, test_stdout, test_stderr,
  test_returncode, provider_metadata, failure_reason.

Both are written under `/tmp` only (or explicitly ignored private path
under gitignored `runs/`). The private path is NEVER serialized in the
public artifact/docs/CI.

## CLI

```bash
python3 -m py_compile eval/b16g_context_pack_atom_ablation.py
python3 eval/b16g_context_pack_atom_ablation.py --self-test
python3 eval/b16g_context_pack_atom_ablation.py \
    --out artifacts/b16g_context_pack_atom_ablation/\
b16g_context_pack_atom_ablation_report.json
# Live opt-in (only if provider env is available and safe):
OPENLOCUS_ALLOW_REMOTE=1 OPENLOCUS_LLM_WORKFLOW_DISPATCH=1 \
    python3 eval/b16g_context_pack_atom_ablation.py \
    --allow-remote --task-count 8 \
    --out artifacts/b16g_context_pack_atom_ablation/\
b16g_context_pack_atom_ablation_report.json
```

Default mode (without `--allow-remote` or without provider env):
writes a truthful `unavailable_no_local_provider_env` or
`blocked_remote_not_enabled` aggregate report if `--out` is supplied;
no provider calls; live-run flags false except
`aggregate_only_public_artifact=true` and `diagnostic_only=true`.

CLI arguments: `--self-test`, `--out`, `--allow-remote`,
`--require-workflow-dispatch`, `--task-count`, `--private-score-dir`,
`--private-event-dir`. Unknown/private-looking arguments are rejected
with a generic `invalid arguments` message that does not echo private
paths or basenames (SafeArgumentParser pattern).

## Provider client helper

B16-G reuses `eval/provider_client.py` from B16-C/D/E/F (unchanged). It
is a minimal OpenAI-compatible chat helper that returns a safe
`ProviderCallResult` object exposing ONLY aggregate counts (calls
attempted/succeeded/failed, invalid_json, timeout, latency, numeric
provider `usage` if present, a fixed failure-category enum token, HTTP
status). Raw prompts, messages, responses, base URLs, API keys, and
provider payloads are NEVER returned in public diagnostics.

## Artifact identity (default committed artifact)

The committed artifact at
`artifacts/b16g_context_pack_atom_ablation/b16g_context_pack_atom_ablation_report.json`
is the public aggregate-only smoke artifact. Identity / boundary
fields:

- `schema_version` = `b16g_context_pack_atom_ablation.v1`
- `generated_by`, `generated_at`, `claim_level`, `status`, `mode`,
  `phase`, `model_display_category` (normalized; no routing prefix).
- Safe true flags (only on live run; exactly these, all true):
  `downstream_agent_runs_performed`, `live_llm_agent`,
  `provider_calls_made`, `remote_provider_calls_made`,
  `paired_run_executed`, `synthetic_task_family_matrix_used`,
  `real_file_edits_performed`, `real_test_commands_executed`,
  `agent_behavior_metrics_evaluated`, `atom_ablation_executed`,
  `private_score_records_written`, `private_event_records_written`,
  `aggregate_only_public_artifact`, `diagnostic_only`.
- On unavailable/blocked status, live-run flags are false except
  `aggregate_only_public_artifact=true` and `diagnostic_only=true`.
- Always-false no-claim flags:
  `downstream_agent_value_proven`,
  `live_agent_generalization_claimed`, `promotion_ready`,
  `default_should_change`,
  `external_benchmark_performance_claimed`, `real_user_task_claimed`,
  `runtime_behavior_changed`, `retriever_changed`,
  `pack_builder_changed`, `backend_changed`,
  `default_policy_changed`, `evidencecore_semantics_changed`,
  `method_winner_claimed`, `calibration_claimed`,
  `bea_superiority_claimed`.
- `input_summary`: `synthetic_task_count`, `run_count_per_arm`,
  `total_runs`, `arms` (`[control_sparse, target_only, support_only,
  distractor_plus_support, target_plus_support]`),
  `task_families` (the eight allowlisted family names),
  `paired_design` (`true`), `workspace_isolation`
  (`fresh_tmp_per_task_arm`), `transient_workspace_outputs_only`
  (`true`), `designed_causal_subset` (`true`),
  `task_family_matrix` (`true`), `primary_contrasts` (3 contrasts),
  `secondary_contrasts` (4 contrasts).
- `arm_results`: list of fixed records
  `{arm, metrics, provider_summary, failure_category_counts}`.
  Metrics: `run_count`, `solve_rate`, `tests_pass_rate`,
  `patch_apply_rate`, `correct_file_before_first_edit_rate`,
  `wrong_file_edit_rate`, `no_op_rate`, `invalid_json_rate`,
  `provider_failure_rate`, `context_tokens_mean`,
  `prompt_tokens_total`, `completion_tokens_total`,
  `latency_seconds_mean`, `cost_proxy_total`.
- `paired_deltas`: list of fixed records
  `{baseline_arm, treatment_arm, metric, delta}`. 7 contrasts (3
  primary + 4 secondary) x 13 metrics.
- `task_family_results`: list of fixed records
  `{task_family, arm, run_count, solve_rate, tests_pass_rate}`.
  Only allowlisted family names appear. No task IDs.
- `mechanism_summary_records`: aggregate counts only:
  `support_atom_sufficient_count` (tasks where support_only solved),
  `target_atom_required_count` (tasks where target_only solved but
  support_only did NOT), `distractor_hurts_count` (tasks where
  distractor_plus_support did NOT solve but target_plus_support DID),
  `all_arms_solved_count`, `sparse_solved_count`.
- `honest_signals`: `target_file_signal_observed` (bool),
  `support_atom_signal_observed` (bool),
  `support_atom_sufficient_count` (int), `target_atom_required_count`
  (int), `distractor_hurts_count` (int), `all_arms_solved_count`
  (int), `sparse_solved_count` (int), per-arm solve rates. These are
  diagnostic smoke outcomes only, NEVER promotion/default/value/BEA-
  superiority claims.
- `private_score_manifest`: aggregate-only
  `{records_written, record_count, schema_version, manifest_hash,
  storage_class, path_publicly_serialized=false}`.
- `private_event_manifest`: aggregate-only
  `{records_written, record_count, schema_version, manifest_hash,
  storage_class, path_publicly_serialized=false}`.
- `self_test_checks_total`, `self_test_checks_passed`, and
  `self_test_passed` (counts only; no detailed check list).
- `forbidden_scan` summary (fail-closed before writing JSON).

## CI pass criterion

CI pass means:

```text
live run completed + privacy scan passed + artifact is honest
```

CI pass does NOT require any atom to win. Zero or negative delta on any
contrast is a valid empirical result if honestly recorded. All five arms
solving or all five failing is a valid empirical result.

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
`model_id`, `atom_composition`, `atom_trace`, `action_trace`,
`score_outcome`, `phase_run_id`, `provider_metadata`,
`candidate_features`, `selected_candidates`, etc.) and value patterns:
ANY URL (no URL allowlist), 32+ char hex digests, secret-like strings,
path-like strings with file extensions, `/tmp/` workspace path values,
`task_N` task-identifier values, patch/diff markers, stack traces,
multiline strings, raw JSON fragments, raw line ranges, raw model
routing prefixes, and the self-test sentinel.

The scanner runs ONLY against the final public aggregate artifact. The
internal per-run event logs and SCORE rows (which contain paths/patches/
test stdout/stderr/atom compositions) are kept under `/tmp` only, never
scanned against the public contract, and never committed.

## Self-tests

B16-G keeps the self-test focused (counts-only public summary; the
detailed check list is NOT published in the public artifact). The
self-test covers:

- Artifact identity fields (schema, claim, status enum, mode, phase,
  generated_by, arms count=5, families count=8, default task count=8,
  max live calls=60, primary/secondary contrast counts).
- Always-false no-claim flags (all 15 false including
  `bea_superiority_claimed`).
- Live-run flag gating.
- Eight task families generation (all eight present; balanced for 8
  tasks).
- Multi-file workspace per family (target/distractor/support/test;
  test fails before fix).
- Pack builder atoms per arm (control has no atoms; target_only has
  target+symbol; support_only has support+decisive;
  distractor_plus_support has distractor+support+decisive;
  target_plus_support has all four atoms).
- Atom composition private list (correct atom counts and names per
  arm).
- Private SCORE/event writers + fake responses (tps solve; dps wrong
  value; control no_op; invalid JSON; 4 rows each written under /tmp;
  valid JSON; private fields present: atom_composition, score_outcome,
  prompt, response).
- Edit action restrictions (disallowed file/action rejected;
  distractor.py rejected; no_op accepted).
- Aggregate metrics + paired deltas (7 contrasts x 13 metrics;
  primary contrast present; primary solve_rate delta positive) +
  mechanism summary (5 records: support_atom_sufficient_count,
  target_atom_required_count, distractor_hurts_count,
  all_arms_solved_count, sparse_solved_count) + honest signals +
  family results (all eight families; five arms per family).
- Model display normalization (strips routing prefix; empty returns
  `unavailable`; strips unsafe chars).
- Env preservation self-test (probe restores env; no-network probes
  do not clear live provider env).
- Private manifest hashes stable (SCORE and event manifest hashes are
  stable and distinct).
- Scanner rejections (workspace path, file path, source snippet, patch
  marker, prompt/response keys, atom_composition key, score_outcome
  key, phase_run_id key, provider_metadata key, raw routing prefix,
  URL value, sentinel canary).
- Scanner allows (arm names, task family names, paired_deltas,
  mechanism_records, model display category, private manifests,
  honest signals).
- Fail-closed generation (clean public report does not raise; leaked
  report raises SystemExit; self-test failure refuses artifact
  generation).
- Public artifact self-scan is clean.
- CLI argument surface.
- Remote gating.
- Five-arm structure (control first, target_only second, support_only
  third, distractor_plus_support fourth, target_plus_support fifth;
  default total runs = 40).

## Validation

```text
python3 -m py_compile eval/b16g_context_pack_atom_ablation.py  => PASS
python3 eval/b16g_context_pack_atom_ablation.py --self-test  => PASS (221/221 checks)
python3 eval/b16g_context_pack_atom_ablation.py \
  --out artifacts/b16g_context_pack_atom_ablation/\
b16g_context_pack_atom_ablation_report.json               => PASS
  (status: blocked_remote_not_enabled,
   forbidden_scan: pass, self_test_passed: true,
   mode: public_aggregate_synthetic_task_family_matrix, phase: B16-G,
   model_display_category: unavailable,
   live_llm_agent: false, provider_calls_made: false,
   remote_provider_calls_made: false, paired_run_executed: false,
   synthetic_task_family_matrix_used: false,
   atom_ablation_executed: false,
   private_score_records_written: false,
   private_event_records_written: false,
   downstream_agent_value_proven: false, promotion_ready: false,
   default_should_change: false, retriever_changed: false,
   pack_builder_changed: false, backend_changed: false,
   default_policy_changed: false, evidencecore_semantics_changed: false,
   runtime_behavior_changed: false,
   external_benchmark_performance_claimed: false,
   live_agent_generalization_claimed: false, real_user_task_claimed: false,
   method_winner_claimed: false, calibration_claimed: false,
   bea_superiority_claimed: false)
python3 scripts/validate_docs_i18n.py                                  => PASS
git diff --check                                                       => PASS
```

The local no-env validation path is truthful and blocked/unavailable.

## Caveats

- B16-G is the public aggregate-only context-pack atom ablation
  downstream smoke artifact. It is eval/diagnostic only. It does NOT
  change runtime, retriever, pack, backend, or default policy; it does
  NOT change EvidenceCore semantics. It is NOT a benchmark result, NOT
  a downstream agent value claim, NOT a runtime-clean general algorithm
  claim, NOT an OOD temporal claim, NOT a QuIVer systems claim, NOT a
  method winner claim, NOT a calibration claim, NOT a BEA superiority
  claim, and NOT a promotion/default/runtime/EvidenceCore change.
- B16-G uses a **live LLM provider** (OpenAI-compatible) only when
  `--allow-remote` + `OPENLOCUS_ALLOW_REMOTE=1` + provider env are
  all set. The default local no-env path remains truthful
  (`blocked_remote_not_enabled`). It is NOT a fake pass.
- B16-G does NOT prove downstream agent value.
  `downstream_agent_value_proven=false`.
- B16-G does NOT claim live agent generalization.
  `live_agent_generalization_claimed=false`.
- B16-G does NOT claim BEA superiority.
  `bea_superiority_claimed=false`. B16-G explains atoms; it does NOT
  claim BEA improves agents or should be default.
- B16-G does NOT publish prompts, responses, provider payloads, base
  URLs, API keys, raw model routing prefixes, workspace paths, file
  paths, source snippets, patches/diffs, test output, atom
  compositions, raw event logs, or per-run rows. The per-run event
  logs, prompts, responses, atom compositions, and test output stay
  under `/tmp` only and are NEVER committed or uploaded.
- `honest_signals` and `mechanism_summary_records` are diagnostic
  smoke outcomes only, NEVER promotion/default/value/BEA-superiority
  claims. Zero or negative delta on any contrast is a valid empirical
  result.
- All no-claim / no-runtime-change flags remain false; diagnostic
  flags (`aggregate_only_public_artifact`, `diagnostic_only`) remain
  true; the live-run flags are true ONLY when a live run actually
  executed.
- No runtime/retriever/pack/model/backend/default-policy files were
  modified. No promotion/default/runtime claims change.
