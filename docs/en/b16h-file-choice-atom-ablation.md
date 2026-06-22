# B16-H File-Choice Atom Ablation Live-Provider Smoke (Public Aggregate-Only Artifact)

## Scope and claim boundary

B16-H resolves the main B16-G confound: B16-G's structured action schema
and prompt forced edits to `target.py`, so `support_only` solving 8/8 did
not prove the support atom alone can guide file choice. B16-H removes
that confound while keeping safe structured actions and private traces.

B16-H removes the file-choice confound:

* the prompt no longer says "only use target.py";
* there is no global `ALLOWED_EDIT_FILES = {target.py}` set;
* the validator accepts only the per-task safe file set: target module,
  distractor module, and the support/config/cross-file module when
  present;
* arbitrary paths are never accepted;
* the chosen file is recorded ONLY in private event/SCORE JSONL under
  `/tmp`;
* only aggregate file-choice rates (selected_target_file_rate,
  selected_distractor_file_rate, selected_support_file_rate) are
  exposed publicly. No actual filenames are published.

B16-H uses eight fixed allowlisted task families (reused from B16-F/B16-G
for comparability). A live LLM provider (OpenAI-compatible) is used over
synthetic public micro bug tasks; the model's structured edit action is
applied locally; real stdlib tests run; only aggregate behavior metrics
are published.

B16-H is explicitly **not** a downstream agent value proof, **not** a
live-agent generalization proof, **not** an external benchmark result,
**not** a production coding-agent benchmark, **not** a real user task
evaluation, **not** a method winner/default/promotion claim, **not** a
calibration claim, **not** a BEA superiority claim, and **not** a
runtime/retriever/pack/backend/default-policy/EvidenceCore semantic
change. It does NOT publish prompts, responses, provider payloads, base
URLs, API keys, raw model routing prefixes, workspace paths, file paths,
source snippets, patches/diffs, test output, atom compositions, chosen
file names, raw event logs, or per-run rows.

- Claim level: `file_choice_atom_ablation_downstream_smoke_only`.
- Mode: `public_aggregate_synthetic_task_family_matrix`; phase `B16-H`.
- Status enum: `file_choice_atom_ablation_smoke_pass` on live success;
  `blocked_remote_not_enabled` / `unavailable_no_local_provider_env`
  when remote opt-in not satisfied; `provider_call_failed` /
  `structured_action_parse_failed` / `paired_run_failed` /
  `fail_forbidden_scan` on failures.
- B16-H is **eval/diagnostic only**. It is NOT a benchmark result, NOT a
  downstream agent value claim, NOT a runtime-clean general algorithm
  claim, NOT an OOD temporal claim, NOT a QuIVer systems claim, NOT a
  method winner/calibration/promotion/default/runtime/EvidenceCore
  claim, and NOT a BEA superiority claim.
- Docs say "on this bounded synthetic file-choice slice" for any
  sufficiency finding.

### B16-G -> B16-H relation

```text
B16-G context-pack atom ablation downstream smoke
  (5 arms: control_sparse, target_only, support_only,
   distractor_plus_support, target_plus_support;
   8 tasks x 5 arms = 40 live calls;
   CONFOUND: prompt/validator forced file=target.py, so
   support_only solving 8/8 did not prove the support atom alone can
   guide file choice)
-> B16-H file-choice atom ablation downstream smoke
   (5 arms: control_sparse, file_choice_target_only,
    file_choice_support_only, file_choice_distractor_plus_support,
    file_choice_target_plus_support;
    8 tasks x 5 arms = 40 live calls default;
    CONFOUND REMOVED: agent chooses among per-task safe files;
    chosen file recorded only in private traces; public artifact only
    aggregate file-choice rates; CI pass does NOT require any atom to
    win)
```

## Arms

B16-H runs FIVE fixed arms with the same budget/tool constraints; only
the atom composition differs (same as B16-G but with `file_choice_`
prefix to mark the confound removal):

1. **`control_sparse`**: task issue only, minimal context; no atoms.
2. **`file_choice_target_only`**: target file cue + target symbol cue;
   no support module, no decisive cue.
3. **`file_choice_support_only`**: support module cue + decisive cue; no
   target file cue, no symbol cue.
4. **`file_choice_distractor_plus_support`**: distractor file cue +
   support module cue + decisive cue; no target file; wrong-file cue.
5. **`file_choice_target_plus_support`**: target file cue + target
   symbol cue + support module cue + decisive cue (full pack).

Primary contrasts:

- `file_choice_target_plus_support` vs `file_choice_support_only`
- `file_choice_target_plus_support` vs
  `file_choice_distractor_plus_support`
- `file_choice_target_only` vs `file_choice_support_only`

Secondary contrasts: each context arm vs `control_sparse`.

## File-choice confound removal (key harness change)

Unlike B16-G (which forced `ALLOWED_EDIT_FILES = {target.py}` and the
prompt said "only use target.py"), B16-H:

- Computes the per-task safe file set via `_safe_edit_files(task)`:
  target module + distractor module + support/config/cross-file module.
- The prompt lists the per-task safe file set and lets the agent CHOOSE
  which file to edit. It does NOT say "only use target.py".
- The validator checks the file against the per-task safe file set, not
  a global set. The agent may edit distractor.py or the support module
  (which will not solve the task).
- The chosen file is recorded ONLY in private SCORE/event JSONL under
  `/tmp` (as `chosen_file`).
- The public artifact exposes only aggregate file-choice rates:
  `selected_target_file_rate`, `selected_distractor_file_rate`,
  `selected_support_file_rate`. No actual filenames are published.

This is the file-choice confound removal. B16-H can now determine
whether the support atom alone is sufficient to guide file choice (not
just sufficient to solve when the file is forced).

## Committed artifact and default local run

The committed artifact at
`artifacts/b16h_file_choice_atom_ablation/b16h_file_choice_atom_ablation_report.json`
is the public aggregate-only smoke artifact. The default local no-env
run is truthful: without `--allow-remote` and the required provider credential/model environment,
the evaluator emits `blocked_remote_not_enabled` or
`unavailable_no_local_provider_env` with live-run flags false. It is NOT a fake
pass.

Manual real-provider CI run `27949115076` passed: 8 tasks x 5 arms = 40 live provider calls; forbidden scan pass; private SCORE/event manifests each have `record_count=40` and `path_publicly_serialized=false`; 266/266 self-tests. Results: `control_sparse` solve/test=0.0; `file_choice_target_only` solve/test=0.0 but selected target file rate=1.0; `file_choice_support_only` solve/test=1.0 and selected target file rate=1.0; `file_choice_distractor_plus_support` solve/test=1.0 and selected target file rate=1.0; `file_choice_target_plus_support` solve/test=1.0 and selected target file rate=1.0. Mechanism summary: `support_only_sufficient_with_file_choice_count=8`, `target_atom_required_with_file_choice_count=0`, `distractor_hurts_with_file_choice_count=0`, `wrong_file_selection_count=0`, `all_arms_solved_count=0`, `sparse_solved_count=0`. Interpretation: on this bounded synthetic file-choice slice, the decisive support cue was still sufficient to guide file choice; target-only context was insufficient; distractor did not hurt when decisive support was present. This is not a downstream value proof, BEA superiority claim, method-winner/default claim, benchmark/performance claim, or calibration claim.


## Aggregate metrics

Public artifact includes records-only aggregates:

- `arm_results` (per-arm metrics)
- `paired_deltas` (7 contrasts: 3 primary + 4 secondary)
- `task_family_results`
- `mechanism_summary_records`
- `private_score_manifest`
- `private_event_manifest`
- `forbidden_scan`

Metrics include: solve_rate, tests_pass_rate, patch_apply_rate,
correct_file_before_first_edit_rate, wrong_file_edit_rate,
selected_target_file_rate, selected_distractor_file_rate,
selected_support_file_rate, no_op_rate, invalid_json_rate,
provider_failure_rate, context_tokens_mean, prompt_tokens_total,
completion_tokens_total, latency_seconds_mean, cost_proxy_total.

Mechanism summary records (counts only):

- `support_only_sufficient_with_file_choice_count`: tasks where
  `file_choice_support_only` solved (support atom alone sufficient even
  when the agent must choose the file).
- `target_atom_required_with_file_choice_count`: tasks where
  `file_choice_target_only` solved but `file_choice_support_only` did
  NOT (target atom was necessary for file choice).
- `distractor_hurts_with_file_choice_count`: tasks where
  `file_choice_distractor_plus_support` did NOT solve but
  `file_choice_target_plus_support` DID (distractor cue caused failure
  under file choice).
- `wrong_file_selection_count`: tasks where the agent selected a
  non-target file (distractor or support) across all context arms.
- `all_arms_solved_count`: tasks where all 5 arms solved.
- `sparse_solved_count`: tasks where control_sparse solved.

## Private artifacts (under /tmp only; never committed/uploaded)

For every task x arm, B16-H writes:

- **Private SCORE JSONL** (one row per task x arm = 40 rows default):
  atom_composition, chosen_file, score_outcome (per-arm metrics),
  latency_ms, tokens, provider_calls, failure_reason.
- **Private event JSONL** (one row per task x arm = 40 rows default):
  prompt, response, parsed_action, chosen_file, patch, test_stdout,
  test_stderr, test_returncode, provider_metadata, failure_reason.

Both are written under `/tmp` only (or explicitly ignored private path
under gitignored `runs/`). The private path is NEVER serialized in the
public artifact/docs/CI.

## CLI

```bash
python3 -m py_compile eval/b16h_file_choice_atom_ablation.py
python3 eval/b16h_file_choice_atom_ablation.py --self-test
python3 eval/b16h_file_choice_atom_ablation.py \
    --out artifacts/b16h_file_choice_atom_ablation/\
b16h_file_choice_atom_ablation_report.json
# Live opt-in only if provider credential/model environment is available and safe:
python3 eval/b16h_file_choice_atom_ablation.py \
    --allow-remote --task-count 8 \
    --out artifacts/b16h_file_choice_atom_ablation/\
b16h_file_choice_atom_ablation_report.json
```

Default mode (without `--allow-remote` or without provider credential/model env):
writes a truthful `unavailable_no_local_provider_env` or
`blocked_remote_not_enabled` aggregate report if `--out` is supplied;
no provider calls; live-run flags false except
`aggregate_only_public_artifact=true` and `diagnostic_only=true`.

CLI arguments: `--self-test`, `--out`, `--allow-remote`,
`--require-workflow-dispatch`, `--task-count`, `--private-score-dir`,
`--private-event-dir`. Unknown/private-looking arguments are rejected
with a generic `invalid arguments` message (SafeArgumentParser pattern).

## Provider client helper

B16-H reuses `eval/provider_client.py` from B16-C/D/E/F/G (unchanged).
Minimal OpenAI-compatible chat helper returning a safe
`ProviderCallResult` with ONLY aggregate counts. Raw prompts,
messages, responses, base URLs, API keys, and provider payloads are
NEVER returned in public diagnostics.

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
`chosen_file`, `file_choice`, `candidate_features`,
`selected_candidates`, etc.) and value patterns: ANY URL (no URL
allowlist), 32+ char hex digests, secret-like strings, path-like
strings with file extensions (including `target.py`, `distractor.py`),
`/tmp/` workspace path values, `task_N` task-identifier values,
patch/diff markers, stack traces, multiline strings, raw JSON fragments,
raw line ranges, raw model routing prefixes, and the self-test sentinel.

The scanner runs ONLY against the final public aggregate artifact. The
internal per-run event logs and SCORE rows (which contain paths/patches/
test stdout/stderr/atom compositions/chosen file) are kept under `/tmp`
only, never scanned against the public contract, and never committed.

## Self-tests

B16-H keeps the self-test focused (counts-only public summary; the
detailed check list is NOT published in the public artifact). The
self-test covers:

- Artifact identity fields (schema, claim, status enum, mode, phase,
  generated_by, arms count=5, families count=8, default task count=8,
  max live calls=60, primary/secondary contrast counts,
  `file_choice_confound_removed` flag, NO global
  `ALLOWED_EDIT_FILES` set).
- Always-false no-claim flags (all 15 false including
  `bea_superiority_claimed`).
- Live-run flag gating.
- Eight task families generation (all eight present; balanced for 8
  tasks).
- Multi-file workspace per family + safe file set (target + distractor +
  support all in safe set).
- Pack builder atoms per arm.
- Atom composition private list.
- File-choice validator (rejects `evil.py`; accepts `target.py`,
  `distractor.py`, `support.py`, `config.py` for config family,
  `cross_file.py` for cross_file family; rejects disallowed action;
  accepts `no_op`).
- Chosen-file categorization (target/distractor/support/none).
- Private SCORE/event writers + fake responses (tps solve chose target;
  so wrong chose distractor; control no_op; invalid JSON; 4 rows each;
  valid JSON; private fields present: atom_composition, chosen_file,
  score_outcome, prompt, response).
- Aggregate metrics + file-choice rates (selected_target_file_rate,
  selected_distractor_file_rate, selected_support_file_rate all
  present) + paired deltas (7 contrasts x 17 metrics; all 3 primary
  contrasts present) + mechanism summary (6 records:
  support_only_sufficient_with_file_choice_count,
  target_atom_required_with_file_choice_count,
  distractor_hurts_with_file_choice_count,
  wrong_file_selection_count, all_arms_solved_count,
  sparse_solved_count) + honest signals + family results.
- Model display normalization.
- Env preservation self-test.
- Private manifest hashes stable and distinct.
- Scanner rejections (including `chosen_file`, `file_choice`,
  `target.py`/`distractor.py` value leakage).
- Scanner allows (arm names, paired_deltas, mechanism_records, model
  display category, private manifests, file-choice rates,
  honest signals).
- Fail-closed generation.
- Public artifact self-scan is clean (no forbidden key anywhere,
  including `chosen_file` and `file_choice`).
- CLI argument surface.
- Remote gating.
- Five-arm structure; default total runs = 40.

## Manual CI result

Manual real-provider CI run `27949115076` passed: 8 tasks x 5 arms = 40 live provider calls; forbidden scan pass; private SCORE/event manifests each have `record_count=40` and `path_publicly_serialized=false`; 266/266 self-tests. Results: `control_sparse` solve/test=0.0; `file_choice_target_only` solve/test=0.0 but selected target file rate=1.0; `file_choice_support_only` solve/test=1.0 and selected target file rate=1.0; `file_choice_distractor_plus_support` solve/test=1.0 and selected target file rate=1.0; `file_choice_target_plus_support` solve/test=1.0 and selected target file rate=1.0. Mechanism summary: `support_only_sufficient_with_file_choice_count=8`, `target_atom_required_with_file_choice_count=0`, `distractor_hurts_with_file_choice_count=0`, `wrong_file_selection_count=0`, `all_arms_solved_count=0`, `sparse_solved_count=0`. Interpretation: on this bounded synthetic file-choice slice, the decisive support cue was still sufficient to guide file choice; target-only context was insufficient; distractor did not hurt when decisive support was present. This is not a downstream value proof, BEA superiority claim, method-winner/default claim, benchmark/performance claim, or calibration claim.

## Validation

```text
python3 -m py_compile eval/b16h_file_choice_atom_ablation.py  => PASS
python3 eval/b16h_file_choice_atom_ablation.py --self-test  => PASS (266/266 checks)
python3 eval/b16h_file_choice_atom_ablation.py \
  --out artifacts/b16h_file_choice_atom_ablation/\
b16h_file_choice_atom_ablation_report.json               => PASS
  (status: blocked_remote_not_enabled,
   forbidden_scan: pass, self_test_passed: true,
   mode: public_aggregate_synthetic_task_family_matrix, phase: B16-H,
   model_display_category: unavailable,
   live_llm_agent: false, provider_calls_made: false,
   remote_provider_calls_made: false, paired_run_executed: false,
   synthetic_task_family_matrix_used: false,
   file_choice_atom_ablation_executed: false,
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

- B16-H is the public aggregate-only file-choice atom ablation
  downstream smoke artifact. It is eval/diagnostic only. It does NOT
  change runtime, retriever, pack, backend, or default policy; it does
  NOT change EvidenceCore semantics. It is NOT a benchmark result, NOT
  a downstream agent value claim, NOT a runtime-clean general algorithm
  claim, NOT an OOD temporal claim, NOT a QuIVer systems claim, NOT a
  method winner claim, NOT a calibration claim, NOT a BEA superiority
  claim, and NOT a promotion/default/runtime/EvidenceCore change.
- B16-H uses a **live LLM provider** (OpenAI-compatible) only when
  `--allow-remote`, the remote opt-in gate, and provider credential/model env are
  all set. The default local no-env path remains truthful
  (`blocked_remote_not_enabled`). It is NOT a fake pass.
- B16-H does NOT prove downstream agent value.
  `downstream_agent_value_proven=false`.
- B16-H does NOT claim live agent generalization.
  `live_agent_generalization_claimed=false`.
- B16-H does NOT claim BEA superiority.
  `bea_superiority_claimed=false`. B16-H explains atoms under file
  choice; it does NOT claim BEA improves agents or should be default.
- B16-H does NOT publish prompts, responses, provider payloads, base
  URLs, API keys, raw model routing prefixes, workspace paths, file
  paths, source snippets, patches/diffs, test output, atom
  compositions, chosen file names, raw event logs, or per-run rows.
- The sufficiency finding wording is bounded: "on this bounded
  synthetic file-choice slice". Any `support_only_sufficient` count
  applies only to this bounded synthetic file-choice slice, not to
  general downstream agent value.
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
