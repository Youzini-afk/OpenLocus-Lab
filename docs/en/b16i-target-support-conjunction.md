# B16-I Non-Decisive Support / Target-Support Conjunction Live-Provider Smoke (Public Aggregate-Only Artifact)

## Scope and claim boundary

B16-I tests the mechanism exposed by B16-H. B16-H removed the file-choice
confound, but support-only still solved every task because the support cue
was too decisive. B16-I redesigns the live-provider synthetic tasks to
test whether support alone can be made non-decisive: target binding and
support rule were expected to be needed together. Manual CI showed this
conjunction was not observed; support-only remained sufficient.

B16-I has FIVE fixed arms over the same eight synthetic task families
reused from B16-F/B16-G/B16-H for comparability. A live LLM provider
(OpenAI-compatible) is used over synthetic public micro bug tasks; the
model's structured edit action is applied locally; real stdlib tests run;
only aggregate behavior metrics are published.

B16-I is explicitly **not** a downstream agent value proof, **not** a
live-agent generalization proof, **not** an external benchmark result,
**not** a production coding-agent benchmark, **not** a real user task
evaluation, **not** a method winner/default/promotion claim, **not** a
calibration claim, **not** a BEA superiority claim, and **not** a
runtime/retriever/pack/backend/default-policy/EvidenceCore semantic
change. It does NOT publish prompts, responses, provider payloads, base
URLs, API keys, raw model routing prefixes, workspace paths, file paths,
source snippets, patches/diffs, test output, atom compositions, support
rule text, exact answers, chosen file names, raw event logs, or per-run
rows.

- Claim level: `target_support_conjunction_downstream_smoke_only`.
- Mode: `public_aggregate_synthetic_task_family_matrix`; phase `B16-I`.
- Status enum: `target_support_conjunction_smoke_pass` on live success;
  `blocked_remote_not_enabled` / `unavailable_no_local_provider_env`
  when remote opt-in not satisfied; `provider_call_failed` /
  `structured_action_parse_failed` / `paired_run_failed` /
  `fail_forbidden_scan` on failures.
- B16-I is **eval/diagnostic only**. Allowed claim: bounded live-provider
  behavior on synthetic file-choice tasks designed to require
  target-support conjunction. Forbidden: downstream value proof, BEA
  superiority, method/default/winner, benchmark performance, real-user-
  task claim, calibration, promotion, runtime/retriever/pack/backend/
  default-policy/EvidenceCore change.

### B16-H -> B16-I relation

```text
B16-H file-choice atom ablation downstream smoke
  (5 arms: control_sparse, file_choice_target_only,
   file_choice_support_only, file_choice_distractor_plus_support,
   file_choice_target_plus_support;
   8 tasks x 5 arms = 40 live calls;
   CONFOUND REMOVED: agent chooses among per-task safe files;
   but support cue was too decisive: support_only solved 8/8)
-> B16-I non-decisive support / target-support conjunction downstream smoke
   (5 arms: control_sparse, file_choice_target_only,
    file_choice_nondecisive_support_only,
    file_choice_distractor_plus_nondecisive_support,
    file_choice_target_plus_support;
    8 tasks x 5 arms = 40 live calls default;
     support cue intended to be non-decisive: gives formula/invariant/rule
     designed to require target binding; target_plus_support is the
     conjunction arm. CI later showed support-only still solved 8/8.)
```

## Arms

1. **`control_sparse`**: task issue only, minimal context; no atoms.
2. **`file_choice_target_only`**: target file cue + target symbol cue;
   no support module, no support rule. Identifies target file/symbol but
   lacks the rule/value.
3. **`file_choice_nondecisive_support_only`**: support module cue +
   non-decisive support rule (formula/invariant/dependency/config
   relation that still requires target binding); no target file cue, no
   symbol cue. The support atom must NOT contain the exact final answer,
   exact target-file instruction, or target-symbol edit instruction.
4. **`file_choice_distractor_plus_nondecisive_support`**: distractor
   file cue + support module cue + non-decisive support rule; no target
   file; wrong-file binding. Gives rule plus wrong binding.
5. **`file_choice_target_plus_support`**: target file cue + target
   symbol cue + support module cue + non-decisive support rule. This is
   the preregistered conjunction arm — gives both target binding and
   support rule and was intended to be the reliably solving context arm;
   CI showed support-only also solved 8/8.

Primary contrasts:

- `file_choice_target_plus_support` vs `file_choice_target_only`
- `file_choice_target_plus_support` vs
  `file_choice_nondecisive_support_only`
- `file_choice_target_plus_support` vs
  `file_choice_distractor_plus_nondecisive_support`

Secondary contrasts:

- `file_choice_target_only` vs
  `file_choice_nondecisive_support_only`
- each context arm vs `control_sparse`

## Intended non-decisive support cue design

The support atom was designed to give a formula/invariant/dependency/
config relation that should still require target binding to apply. It
does NOT contain:

- the exact final answer (e.g. "Correct value: 42");
- the exact target-file instruction (e.g. "edit target.py");
- the target-symbol edit instruction (e.g. "function foo should return
  42").

Instead, it says things like "the correct return value is derived as
helper_constant * 2 + task_index ... You must determine which file
applies this relation." The target_plus_support arm additionally gives
the target binding (which file + which symbol), making the full cue
decisive by construction. Manual CI showed the support-only cue was still
sufficient despite this design.

## File-choice confound removal (carried over from B16-H)

File choice remains enabled across the per-task safe file set (target
module + distractor module + support/config/cross-file module). The
chosen file is recorded ONLY in private SCORE/event JSONL under `/tmp`.
Only aggregate file-choice rates are exposed publicly.

## Committed artifact and default local run

The committed artifact at
`artifacts/b16i_target_support_conjunction/b16i_target_support_conjunction_report.json`
is the public aggregate-only smoke artifact. The default local no-env
run is truthful: without `--allow-remote` and the required provider
credential/model environment, the evaluator emits `blocked_remote_not_enabled`
or `unavailable_no_local_provider_env` with live-run flags false. It is NOT a
fake pass.

## Private artifacts (under /tmp only; never committed/uploaded)

For every task x arm, B16-I writes:

- **Private SCORE JSONL** (one row per task x arm = 40 rows default):
  atom_composition, chosen_file, score_outcome, latency_ms, tokens,
  provider_calls, failure_reason.
- **Private event JSONL** (one row per task x arm = 40 rows default):
  prompt, response, parsed_action, chosen_file, patch, test_stdout,
  test_stderr, test_returncode, provider_metadata, failure_reason.

Both are written under `/tmp` only (or explicitly ignored private path
under gitignored `runs/`). The private path is NEVER serialized in the
public artifact/docs/CI.

## Public artifact

Aggregate-only records: `arm_results`, `paired_deltas`,
`task_family_results`, `mechanism_summary_records`, `honest_signals`,
private manifests, `forbidden_scan`, no-claim flags. Counts-only
self-test fields: `self_test_checks_total` and
`self_test_checks_passed`. No `self_test_summary` and no
`self_test_checks` list.

Metrics include: solve_rate, tests_pass_rate, patch_apply_rate,
correct_file_before_first_edit_rate, wrong_file_edit_rate,
selected_target_file_rate, selected_distractor_file_rate,
selected_support_file_rate, no_op_rate, invalid_json_rate,
provider_failure_rate, context_tokens_mean, prompt_tokens_total,
completion_tokens_total, latency_seconds_mean, cost_proxy_total.

Mechanism summary records (counts only):

- `target_support_conjunction_required_count`: tasks where
  target_plus_support solved but NEITHER target_only NOR support_only
  solved (conjunction was required).
- `support_only_sufficient_count`: tasks where support_only solved.
- `target_only_sufficient_count`: tasks where target_only solved.
- `distractor_hurts_count`: tasks where distractor_plus_support did NOT
  solve but target_plus_support DID.
- `wrong_file_selection_count`: tasks where any context arm selected a
  non-target file.
- `all_arms_solved_count`: tasks where all 5 arms solved.
- `sparse_solved_count`: tasks where control_sparse solved.

## CLI

```bash
python3 -m py_compile eval/b16i_target_support_conjunction.py
python3 eval/b16i_target_support_conjunction.py --self-test
python3 eval/b16i_target_support_conjunction.py \
    --out artifacts/b16i_target_support_conjunction/\
b16i_target_support_conjunction_report.json
# Live opt-in only if provider credential/model environment is available and safe:
python3 eval/b16i_target_support_conjunction.py \
    --allow-remote --task-count 8 \
    --out artifacts/b16i_target_support_conjunction/\
b16i_target_support_conjunction_report.json
```

## CI pass criterion

CI pass means: live run completed + privacy scan passed + artifact is
honest. CI pass does NOT require the conjunction to hold. Zero or
negative delta on any contrast is a valid empirical result if honestly
recorded.

## Forbidden scanner (public, fail-closed)

Strict forbidden-output scanner runs fail-closed before writing the
public JSON. Rejects forbidden dict keys including `prompt`,
`response`, `chosen_file`, `file_choice`, `support_rule_text`,
`exact_answer`, `atom_composition`, `score_outcome`, `phase_run_id`,
`provider_metadata`, and all path/file/snippet/patch/test/secret
identifiers. Value patterns: ANY URL, 32+ char hex digests, secret-like
strings, path-like strings with file extensions, `/tmp/` workspace path
values, patch/diff markers, stack traces, multiline strings, raw JSON
fragments, raw line ranges, raw model routing prefixes, and the
self-test sentinel.

## Self-tests

306 self-test checks (counts-only public summary; the detailed check
list is NOT published in the public artifact). Covers: artifact identity,
no-claim flags, live-run flag gating, eight task families, workspace
builder, safe file set, pack builder atoms, atom composition, non-
decisive support cue text (no exact answer / no target-file instruction
/ decisive cue does contain the answer), file-choice validator (rejects
evil.py; accepts per-task safe files), chosen-file categorization,
private SCORE/event writers + fake responses, aggregate metrics +
file-choice rates + paired deltas (8 contrasts x 17 metrics) +
mechanism summary (7 records) + honest signals + family results, model
display normalization, env preservation, private manifest hashes,
scanner rejections (including support_rule_text, exact_answer,
chosen_file, file_choice), scanner allows, fail-closed generation,
public artifact self-scan clean, CLI argument surface, remote gating,
five-arm structure.

## Validation

```text
python3 -m py_compile eval/b16i_target_support_conjunction.py  => PASS
python3 eval/b16i_target_support_conjunction.py --self-test  => PASS (306/306 checks)
python3 eval/b16i_target_support_conjunction.py \
  --out artifacts/b16i_target_support_conjunction/\
b16i_target_support_conjunction_report.json               => PASS
  (status: blocked_remote_not_enabled,
   forbidden_scan: pass, self_test_passed: true,
   mode: public_aggregate_synthetic_task_family_matrix, phase: B16-I,
   model_display_category: unavailable,
   live_llm_agent: false, provider_calls_made: false,
   remote_provider_calls_made: false, paired_run_executed: false,
   synthetic_task_family_matrix_used: false,
   target_support_conjunction_executed: false,
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

## Manual CI result

Manual real-provider CI run `27950908481` passed: 8 tasks x 5 arms = 40 live provider calls; forbidden scan pass; private SCORE/event manifests each have `record_count=40` and `path_publicly_serialized=false`; 306/306 self-tests. Results: `control_sparse` solve/test=0.0; `file_choice_target_only` solve/test=0.125 and selected target file rate=1.0; `file_choice_nondecisive_support_only` solve/test=1.0 and selected target file rate=1.0; `file_choice_distractor_plus_nondecisive_support` solve/test=1.0 and selected target file rate=1.0; `file_choice_target_plus_support` solve/test=1.0 and selected target file rate=1.0. Mechanism summary: `target_support_conjunction_required_count=0`, `support_only_sufficient_count=8`, `target_only_sufficient_count=1`, `distractor_hurts_count=0`, `wrong_file_selection_count=0`, `all_arms_solved_count=0`, `sparse_solved_count=0`. Interpretation: the intended non-decisive support cue was still sufficient on this bounded synthetic file-choice slice; target+support did not improve over support-only; target-only solved only 1/8; distractor did not hurt when support was present. This means the target-support conjunction was not observed. This is not a downstream value proof, BEA superiority claim, method-winner/default claim, benchmark/performance claim, or calibration claim.

## Caveats

- B16-I is the public aggregate-only non-decisive support / target-
  support conjunction downstream smoke artifact. It is eval/diagnostic
  only. It does NOT change runtime, retriever, pack, backend, or default
  policy; it does NOT change EvidenceCore semantics.
- B16-I uses a **live LLM provider** (OpenAI-compatible) only when
  `--allow-remote`, the remote opt-in gate, and provider credential/model env are
  all set. The default local no-env path remains truthful
  (`blocked_remote_not_enabled`). It is NOT a fake pass.
- B16-I does NOT prove downstream agent value.
  `downstream_agent_value_proven=false`.
- B16-I does NOT claim BEA superiority.
  `bea_superiority_claimed=false`.
- B16-I does NOT publish prompts, responses, support rule text, exact
  answers, chosen file names, atom compositions, or per-run rows.
- Sufficiency findings are bounded to "on this bounded synthetic
  file-choice slice".
- All no-claim / no-runtime-change flags remain false; diagnostic flags
  remain true; live-run flags are true ONLY when a live run actually
  executed.
