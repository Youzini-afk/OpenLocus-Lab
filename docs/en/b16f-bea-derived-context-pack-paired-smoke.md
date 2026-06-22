# B16-F BEA-Derived Context Pack Live-Provider Paired Smoke (Public Aggregate-Only Artifact)

## Scope and claim boundary

B16-F is the first downstream live-provider paired smoke that compares a
**BEA v0.3-derived context pack** against a **same-budget BM25
context-pack control** (and a sparse control) on bounded synthetic
coding tasks. The primary contrast is BEA v0.3 context pack vs same-budget
BM25 context pack; secondary contrasts are BEA vs sparse and BM25 vs
sparse.

B16-F uses eight fixed allowlisted task families. For each synthetic
workspace, B16-F constructs runtime-clean candidate features (method
source, rank, score/normalized score, agreement count, span extent).
BM25 selects the same-budget BM25 prefix; BEA applies a frozen v0.3-style
policy using ONLY runtime-available features. The BEA selector NEVER
reads gold paths/lines/labels, task answers, `correct_value`, or
per-task outcomes. A live LLM provider (OpenAI-compatible) is used over
synthetic public micro bug tasks; the model's structured edit action is
applied locally; real stdlib tests run; only aggregate behavior metrics
are published.

B16-F is explicitly **not** a downstream agent value proof, **not** a
live-agent generalization proof, **not** an external benchmark result,
**not** a production coding-agent benchmark, **not** a real user task
evaluation, **not** a method winner/default/promotion claim, **not** a
calibration claim, and **not** a runtime/retriever/pack/backend/default-
policy/EvidenceCore semantic change. It does NOT publish prompts,
responses, provider payloads, base URLs, API keys, raw model routing
prefixes, workspace paths, file paths, source snippets, patches/diffs,
test output, raw event logs, candidate features, BEA/BM25 action traces,
pack composition, or per-run rows.

- Claim level: `bea_derived_context_pack_downstream_paired_smoke_only`.
- Mode: `public_aggregate_synthetic_task_family_matrix`; phase `B16-F`.
- Status enum: `bea_derived_context_pack_paired_smoke_pass` on live
  success; `blocked_remote_not_enabled` /
  `unavailable_no_local_provider_env` when remote opt-in not satisfied;
  `provider_call_failed` / `structured_action_parse_failed` /
  `paired_run_failed` / `fail_forbidden_scan` on failures.
- B16-F is **eval/diagnostic only**. It is NOT a benchmark result, NOT
  a downstream agent value claim, NOT a runtime-clean general algorithm
  claim, NOT an OOD temporal claim, NOT a QuIVer systems claim, and NOT
  a method winner/calibration/promotion/default/runtime/EvidenceCore
  claim.

### BEA-3 -> B16-F relation

```text
BEA-3 anchor/span/latency-aware retrieval policy smoke
  (retrieval-side only; 30 records x 9 arms; v0.3 tied v0.2 on
   file/MRR/success with a tiny span/quality-per-latency signal)
-> B16-F BEA-derived context pack downstream paired smoke
   (downstream live-provider; 8 synthetic tasks x 3 arms = 24 live
    calls default; BEA v0.3 context pack vs same-budget BM25 context
    pack vs sparse control; same aggregate-only safety model; CI pass
    does NOT require BEA improvement)
```

B16-F addresses the deep-research directive's gap: BEA retrieval-side
metrics are not enough; BEA must be tested against live coding-agent
behavior. B16-F only produces a downstream live-provider paired smoke
by running a tiny paired live LLM agent on a synthetic public
task-family matrix with BEA-derived vs same-budget BM25 context packs.

## Arms

B16-F runs THREE paired arms with the same budget/tool constraints;
only the context pack differs:

1. **`control_sparse`**: task issue only, minimal context; NO target
   file cue; NO decisive cue; candidate_count=0; small token budget.
   The agent cannot determine the correct value/operation without the
   decisive cue.
2. **`bm25_same_budget_context_pack`**: same-budget BM25 prefix pack.
   Same budget K as the BEA arm. Includes target file cue + symbol cue
   + decisive cue ONLY IF the BM25 prefix happens to include target.py
   and support/config/cross_file.py. By design, the deterministic
   candidate features make BM25 prefix exclude target.py (lower BM25
   score) while including distractor.py (highest BM25 score) and
   support.py (second-highest). The BM25 pack thus supplies the
   distractor (wrong file) + support but NOT the target file cue.
3. **`bea_v03_context_pack`**: frozen BEA v0.3 anchor/span/latency
   selected pack. Same budget K as BM25. BEA v0.3 uses agreement
   anchors (target.py has agreement=3 across bm25/regex/symbol) and
   span tightness to select target.py + support.py. The BEA pack thus
   supplies the target file cue + symbol cue + decisive cue.

Primary public paired delta: BEA minus same-budget BM25. Secondary
deltas: BEA minus sparse and BM25 minus sparse.

## Committed artifact and default local run

The committed artifact at
`artifacts/b16f_bea_derived_context_pack_paired_smoke/b16f_bea_derived_context_pack_paired_smoke_report.json`
is the public aggregate-only smoke artifact. The default local no-env
run is truthful: without `--allow-remote` and the required provider credential/model environment,
the evaluator emits `blocked_remote_not_enabled` or
`unavailable_no_local_provider_env` with live-run flags false. It is NOT a fake
pass.

Manual real-provider CI run `27945253824` passed. The committed artifact now mirrors the sanitized aggregate report from that run: 8 synthetic tasks x 3 arms = 24 live provider calls, `model_display_category=Kimi-K2.7-Code`, forbidden scan pass, 352/352 self-test checks, `private_score_manifest.record_count=24`, `private_event_manifest.record_count=24`, both manifests `storage_class=tmp_private` and `path_publicly_serialized=false`. Sparse control solved 2/8 (`solve_rate=0.25`, `tests_pass_rate=0.25`, `latency_seconds_mean=13.4355`); same-budget BM25 context pack solved 8/8 (`solve_rate=1.0`, `tests_pass_rate=1.0`, `latency_seconds_mean=1.1885`); BEA v0.3 context pack also solved 8/8 (`solve_rate=1.0`, `tests_pass_rate=1.0`, `latency_seconds_mean=1.579`). Primary BEA-vs-BM25 deltas: solve/test/wrong-file/edit-validity deltas 0.0, `latency_seconds_mean` delta +0.3905, prompt tokens +161, completion tokens +47. Secondary deltas vs sparse: both context arms +0.75 solve/test. Interpretation: B16-F shows context-pack benefit over sparse on this bounded synthetic live-provider slice, but BEA v0.3 does not improve over same-budget BM25; `context_pack_signal_observed=false` for the primary contrast. This is a downstream live-provider smoke result, not downstream value proof, not a method-winner/default/performance/calibration claim.

## Heterogeneous synthetic public task-family matrix design

B16-F generates deterministic synthetic public micro bug tasks across
eight fixed allowlisted task families (default 8 tasks; `--task-count`
range 4-12, hard cap 12; default 24 live calls = 8 x 3 arms; max 36
live calls). Tasks cycle through the eight families so the matrix is
balanced.

### Task families

Each family has a different decisive cue that the BEA pack supplies via
the support/config/cross_file module being included as an anchor:

1. **`same_symbol_support_relation`** — target/distractor share a symbol
   and a support relation determines the correct edit. Correct value =
   `helper_constant * 2 + task_index`.
2. **`operation_ambiguity`** — target symbol may be inferable but the
   operation is ambiguous (increment vs multiply). Correct operation is
   multiply; correct value = `base_value * 2`.
3. **`boundary_condition`** — correct edit depends on inclusive/exclusive
   boundary behavior. Correct value = `limit_value - 1`.
4. **`helper_dependency_choice`** — multiple helpers exist; correct edit
   requires choosing the right helper relation. Correct value =
   `helper_b * 3` (not `helper_a * 2`).
5. **`config_or_test_mismatch`** — target.py uses a wrong config value;
   correct value = `config_value` from `config.py` (not `support.py`).
6. **`distractor_file`** — distractor.py has the same symbol but wrong
   value; target.py is the correct file. Correct value =
   `helper_constant + 5`.
7. **`nearby_wrong_function`** — target.py has two functions; the bug
   is in one, the nearby one has a similar name. Correct value =
   `helper_constant * 2`.
8. **`cross_file_symbol`** — correct value = helper from another module
   (`cross_file.py`). Correct value = `cross_value + 1`.

### Multi-file workspace

For each task and arm, B16-F creates a fresh `/tmp` workspace with four
real Python files: `target.py` (buggy function), `distractor.py`
(same-named decoy), `support.py`/`config.py`/`cross_file.py` (helper
constant), and `test_target.py` (imports target AND support; asserts
the correct family-specific relation). The harness actually edits files
and runs subprocess tests.

## Runtime-clean candidate features and BEA v0.3 policy

For each synthetic task, B16-F generates 6 deterministic runtime-clean
candidate features. Each candidate carries: path, method, rank, score,
normalized_score, methods set, agreement count, start_line, end_line,
span_extent. No gold paths, `correct_value`, task_family decisive cue,
or any private answer is present in candidate features.

Design: `target.py` has agreement=3 (all methods return it), MEDIUM BM25
score (intentionally lower than support), tight span.
`distractor.py` has agreement=1 (bm25 only), HIGH BM25 score, tight
span. `support.py`/`config.py`/`cross_file.py` has agreement=2
(bm25+symbol), second-highest BM25 score, tight span. This makes:

- **BEA v0.3** (budget=2): picks `target.py` (agreement=3, anchor
  anchor-eligible) + `support.py` (agreement=2, anchor-eligible, new
  file). The BEA pack includes target + support → target file cue +
  decisive cue.
- **BM25 same-budget prefix** (K=2): picks `distractor.py` (highest BM25
  score) + `support.py` (second-highest). The BM25 pack excludes
  `target.py` → no target file cue. The LLM may edit `distractor.py`
  (wrong file) or fail to determine the correct value.
- **Sparse control**: no candidates, no cues.

The BEA v0.3 frozen policy uses: agreement (weight 0.30), bm25_norm
(0.20), diversity (0.20), query/path overlap (0.15), span tightness
(0.15), anchor file support (0.10), anchor boost (0.35 for anchor slots),
risk penalty (-0.25), weak-support penalty (-0.20), duplication penalty
(-0.30), marginal-priority early stop (threshold 0.05). All weights are
frozen constants, NOT tuned from outcomes. Anchor count = min(2, budget).

### BEA runtime-clean invariant

The BEA selector consumes ONLY runtime-clean candidate features. It
NEVER reads gold paths, `correct_value`, task_family decisive cue, or
any private answer. Tainting `correct_value` with a wrong value does NOT
change BEA selection because the policy ignores that field entirely.
This invariant is verified in the self-test.

## Live provider constraints

- Exact provider credential/model env names live in workflow/config wiring, not research prose.
- Remote calls are made ONLY when `--allow-remote`, the remote opt-in gate,
  the workflow-dispatch gate when required, and provider credential/model
  configuration are all present.
- No raw base URL, API key, prompt, response, source snippet,
  patch/diff, stdout/stderr, workspace path, candidate features, BEA
  action trace, pack composition, or provider payload in
  artifact/docs.
- The live LLM prompt may include a tiny synthetic/public source snippet
  (the buggy target module + the support module) and a family-specific
  decisive cue only when the treatment pack carries it. Prompts are
  NEVER persisted (only written to private event JSONL under `/tmp`).
- The structured edit action schema is allowlisted: action must be
  `replace_return_value`, `choose_helper_constant`, or `no_op`; file
  must be `target.py`; no arbitrary paths, no shell. Distractor and
  support files are NOT editable.
- Usage diagnostics may include aggregate prompt/completion/total
  token counts if the provider returns `usage`; otherwise marked
  unavailable.
- Cost is `cost_proxy` only (always 0.0); no live price inference.
- Research docs/artifacts record normalized model display names without
  routing prefix (e.g. `Kimi-K2.7-Code`, not the raw routing prefix)
  except when documenting exact workflow/env allowlists.

## Private artifacts (under /tmp only; never committed/uploaded)

For every task x arm, B16-F writes:

- **Private SCORE JSONL** (one row per task x arm = 24 rows default):
  candidate_features (paths, scores, ranks, methods, agreement, spans),
  bea_action_trace, bea_budget_trace, bea_stop_reason,
  selected_candidates (pack composition), score_outcome (per-arm
  metrics), latency_ms, tokens, provider_calls, failure_reason.
- **Private event JSONL** (one row per task x arm = 24 rows default):
  prompt, response, parsed_action, patch, test_stdout, test_stderr,
  test_returncode, provider_metadata, failure_reason.

Both are written under `/tmp` only (or explicitly ignored private path
under gitignored `runs/`). The private path is NEVER serialized in the
public artifact/docs/CI.

## CLI

```bash
python3 -m py_compile eval/b16f_bea_derived_context_pack_paired_smoke.py
python3 eval/b16f_bea_derived_context_pack_paired_smoke.py --self-test
python3 eval/b16f_bea_derived_context_pack_paired_smoke.py \
    --out artifacts/b16f_bea_derived_context_pack_paired_smoke/\
b16f_bea_derived_context_pack_paired_smoke_report.json
# Live opt-in only if provider credential/model environment is available and safe:
python3 eval/b16f_bea_derived_context_pack_paired_smoke.py \
    --allow-remote --task-count 8 \
    --out artifacts/b16f_bea_derived_context_pack_paired_smoke/\
b16f_bea_derived_context_pack_paired_smoke_report.json
```

Default mode (without `--allow-remote` or without provider credential/model env):
writes a truthful `unavailable_no_local_provider_env` or
`blocked_remote_not_enabled` aggregate report if `--out` is supplied;
no provider calls; live-run flags false except
`aggregate_only_public_artifact=true` and `diagnostic_only=true`.

CLI arguments: `--self-test`, `--out`, `--allow-remote`,
`--require-workflow-dispatch`, `--task-count`, `--private-score-dir`,
`--private-event-dir`. Unknown/private-looking arguments are rejected
with a generic `invalid arguments` message that does not echo private
paths or basenames (SafeArgumentParser pattern).

`--self-test` runs no-network self-tests with fake provider responses;
covers remote gating, env preservation, missing env unavailable path,
provider diagnostics redaction, candidate generator (runtime-clean;
no gold fields), BEA v0.3 policy (accepts target+support; ignores gold
tainting), BM25 same-budget prefix (excludes target), pack builder
(control lacks cues; BEA has cues; BM25 lacks target cue), fake valid
edit apply/test for all eight families, invalid JSON count, fixed
provider error category, action path/action restrictions (including
distractor/support file rejection), all eight task families,
treatment/control decisive-cue differences, private SCORE/event
writers (rows written under /tmp; valid JSON; private fields present),
records-shaped family matrix, scanner forbidden keys/values (including
BEA-private keys: candidate_features, selected_candidates,
bea_action_trace, bea_budget_trace, score_outcome), no-claim flags,
and fail-closed scanner behavior.

## Provider client helper

B16-F reuses `eval/provider_client.py` from B16-C/D/E (unchanged). It is
a minimal OpenAI-compatible chat helper that returns a safe
`ProviderCallResult` object exposing ONLY aggregate counts (calls
attempted/succeeded/failed, invalid_json, timeout, latency, numeric
provider `usage` if present, a fixed failure-category enum token, HTTP
status). Raw prompts, messages, responses, base URLs, API keys, and
provider payloads are NEVER returned in public diagnostics.

## Artifact identity (default committed artifact)

The committed artifact at
`artifacts/b16f_bea_derived_context_pack_paired_smoke/b16f_bea_derived_context_pack_paired_smoke_report.json`
is the public aggregate-only smoke artifact. Identity / boundary
fields:

- `schema_version` = `b16f_bea_derived_context_pack_paired_smoke.v1`
- `generated_by`, `generated_at`, `claim_level`, `status`, `mode`,
  `phase`, `model_display_category` (normalized; no routing prefix).
- Safe true flags (only on live run; exactly these, all true):
  `downstream_agent_runs_performed`, `live_llm_agent`,
  `provider_calls_made`, `remote_provider_calls_made`,
  `paired_run_executed`, `synthetic_task_family_matrix_used`,
  `real_file_edits_performed`, `real_test_commands_executed`,
  `agent_behavior_metrics_evaluated`,
  `bea_v03_context_pack_executed`,
  `bm25_same_budget_context_pack_executed`,
  `private_score_records_written`,
  `private_event_records_written`,
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
  `method_winner_claimed`, `calibration_claimed`.
- `input_summary`: `synthetic_task_count`, `run_count_per_arm`,
  `total_runs`, `arms` (`[control_sparse,
  bm25_same_budget_context_pack, bea_v03_context_pack]`),
  `task_families` (the eight allowlisted family names),
  `paired_design` (`true`), `workspace_isolation`
  (`fresh_tmp_per_task_arm`), `transient_workspace_outputs_only`
  (`true`), `designed_causal_subset` (`true`),
  `task_family_matrix` (`true`), `primary_contrast`
  (`bea_v03_context_pack_vs_bm25_same_budget_context_pack`).
- `arm_results`: list of fixed records
  `{arm, metrics, provider_summary, failure_category_counts}`.
  Metrics: `run_count`, `solve_rate`, `tests_pass_rate`,
  `patch_apply_rate`, `invalid_json_rate`, `no_op_rate`,
  `provider_failure_rate`, `context_tokens_mean`,
  `prompt_tokens_total`, `completion_tokens_total`,
  `latency_seconds_mean`, `cost_proxy_total`,
  `correct_file_before_first_edit_rate`, `wrong_file_edit_rate`.
- `paired_deltas`: list of fixed records
  `{baseline_arm, treatment_arm, metric, delta}`. Three contrasts:
  BEA vs BM25 (primary), BEA vs sparse (secondary), BM25 vs sparse
  (secondary).
- `task_family_results`: list of fixed records
  `{task_family, arm, run_count, solve_rate, tests_pass_rate,
  correct_file_before_first_edit_rate, wrong_file_edit_rate}`.
  Only allowlisted family names appear. No task IDs.
- `family_signal_summary`: aggregate counts only for the PRIMARY
  contrast (BEA vs BM25): `families_evaluated`,
  `families_with_positive_solve_delta`,
  `families_with_zero_solve_delta`,
  `families_with_negative_solve_delta`.
- `honest_signals`: `context_pack_signal_observed` (bool),
  `primary_solve_rate_delta` (number),
  `primary_tests_pass_rate_delta` (number),
  `primary_wrong_file_edit_rate_delta` (number),
  `families_evaluated` (int), `families_with_positive_solve_delta`
  (int), `families_with_zero_solve_delta` (int),
  `families_with_negative_solve_delta` (int). These are diagnostic
  smoke outcomes only, NEVER promotion/default/value claims.
- `private_score_manifest`: aggregate-only
  `{records_written, record_count, schema_version, manifest_hash,
  storage_class, path_publicly_serialized=false}`.
- `private_event_manifest`: aggregate-only
  `{records_written, record_count, schema_version, manifest_hash,
  storage_class, path_publicly_serialized=false}`.
- `self_test_checks_total`, `self_test_checks_passed`, and `self_test_passed`
  counts only (individual self-test names are not published in the public
  artifact to avoid scanner/audit noise).
- `forbidden_scan` summary (fail-closed before writing JSON).

## CI pass criterion

CI pass means:

```text
live run completed + privacy scan passed + artifact is honest
```

CI pass does NOT require BEA improvement. Zero or negative BEA-vs-BM25
delta is a valid empirical result if honestly recorded. All three arms
solving or all three failing is a valid empirical result. Some families
may show positive BEA-vs-BM25 delta while others show zero or negative;
all are valid empirical outcomes.

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
`model_id`, `candidate_features`, `selected_candidates`,
`bea_action_trace`, `bea_budget_trace`, `bea_stop_reason`,
`score_outcome`, `accepted_candidates`, `action_trace`,
`budget_trace`, `phase_run_id`, `provider_metadata`, etc.) and value
patterns: ANY URL (no URL allowlist), 32+ char hex digests, secret-like
strings, path-like strings with file extensions, `/tmp/` workspace path
values, `task_N` task-identifier values, patch/diff markers, stack
traces, multiline strings, raw JSON fragments, raw line ranges, raw
model routing prefixes, and the self-test sentinel.

The scanner runs ONLY against the final public aggregate artifact. The
internal per-run event logs and SCORE rows (which contain paths/patches/
test stdout/stderr/candidate features/BEA action traces) are kept
under `/tmp` only, never scanned against the public contract, and
never committed.

## Self-tests

- Artifact identity fields (schema, claim, status enum, mode, phase,
  generated_by, primary_contrast, arms count=3, families count=8,
  default task count=8, max live calls=36).
- Always-false no-claim flags (all 14 false).
- Live-run flag gating (unavailable report: live-run flags false; live
  report: live-run flags true).
- Eight task families generation (all eight present; balanced for 8
  tasks; family-specific deterministic correct values).
- Multi-file workspace per family (target/distractor/support/test;
  same-symbol distractor; test fails before fix).
- Candidate generator (6 candidates; target agreement=3; distractor
  agreement=1; support agreement=2; distractor BM25 > target BM25; no
  gold fields).
- BEA v0.3 policy (accepts 2 candidates; accepts target as anchor;
  accepts support; does NOT accept distractor first; action/budget
  trace nonempty; stop reason set; mechanism summary present; selection
  invariant under gold tainting).
- BM25 same-budget prefix (count matches K; includes distractor;
  excludes target).
- Pack builder (control lacks all cues; BEA has target/symbol/decisive
  cues; BM25 lacks target file cue; same budget K matches; BEA richer
  than control).
- Decisive cue text per family (non-empty; no raw routing prefix).
- Fake valid BEA response per family (correct file edit; no wrong file;
  tests pass; solve=true; provider call succeeded; task_family/arm
  recorded).
- Fake invalid JSON response (parse failure): no edit; tests fail; no
  raw response in run result.
- Private SCORE/event writers (9 rows each written under /tmp; valid
  JSON; private fields present: candidate_features,
  selected_candidates, score_outcome, prompt, response, test_stdout).
- Edit action restrictions: disallowed file rejected; disallowed
  action rejected; distractor.py rejected; support.py rejected;
  missing symbol rejected; non-int new_return_value rejected;
  non-object rejected; valid action accepted;
  `choose_helper_constant` accepted; `no_op` accepted.
- Aggregate metrics + paired deltas (3 contrasts x N metrics;
  primary contrast present; primary solve_rate delta positive on BEA
  solves / BM25 fails; secondary contrasts present) + family results
  (all eight families; three arms per family) + family signal summary
  + honest signals (context_pack_signal_observed true on positive
  delta; false on zero delta).
- Model display normalization (strips routing prefix; empty returns
  `unavailable`; strips unsafe chars).
- Env preservation self-test (probe restores env; no-network probes
  do not clear live provider gate/env state).
- Private manifest hashes stable (SCORE and event manifest hashes are
  stable and distinct).
- Scanner rejections: workspace path, file path, source snippet,
  patch marker, test output, task_id key, raw event log, stack trace,
  content_sha key, hex digest, provider auth field, endpoint URL
  field, raw routing prefix, URL value, prompt key, response key,
  messages key, provider_payload key, candidate_features key,
  selected_candidates key, bea_action_trace key, bea_budget_trace key,
  score_outcome key, sentinel canary.
- Scanner allows: arm names, task family names, paired_deltas records,
  family results records, model display category, honest signal
  fields, private_score_manifest, private_event_manifest, failure
  category token, primary_contrast.
- Fail-closed generation: clean public report does not raise; leaked
  public report raises SystemExit; self-test failure refuses artifact
  generation.
- Public artifact self-scan is clean (no forbidden key anywhere).
- CLI argument surface: `--self-test`, `--out`, `--allow-remote`,
  `--require-workflow-dispatch`, `--task-count`, `--private-score-dir`,
  `--private-event-dir` are the only options (plus `-h`/`--help`);
  default task count is in range.
- Remote gating: blocked when `allow_remote=False`; unavailable when
  env missing.
- Three-arm structure: control first, BM25 second, BEA third; default
  total runs = 24.

## Validation

```text
python3 -m py_compile eval/b16f_bea_derived_context_pack_paired_smoke.py  => PASS
python3 eval/b16f_bea_derived_context_pack_paired_smoke.py --self-test  => PASS (352/352 checks)
python3 eval/b16f_bea_derived_context_pack_paired_smoke.py \
  --out artifacts/b16f_bea_derived_context_pack_paired_smoke/\
b16f_bea_derived_context_pack_paired_smoke_report.json               => PASS
  (status: blocked_remote_not_enabled,
   forbidden_scan: pass, self_test_passed: true,
   mode: public_aggregate_synthetic_task_family_matrix, phase: B16-F,
   model_display_category: unavailable,
   live_llm_agent: false, provider_calls_made: false,
   remote_provider_calls_made: false, paired_run_executed: false,
   synthetic_task_family_matrix_used: false,
   bea_v03_context_pack_executed: false,
   bm25_same_budget_context_pack_executed: false,
   private_score_records_written: false,
   private_event_records_written: false,
   downstream_agent_value_proven: false, promotion_ready: false,
   default_should_change: false, retriever_changed: false,
   pack_builder_changed: false, backend_changed: false,
   default_policy_changed: false, evidencecore_semantics_changed: false,
   runtime_behavior_changed: false,
   external_benchmark_performance_claimed: false,
   live_agent_generalization_claimed: false, real_user_task_claimed: false,
   method_winner_claimed: false, calibration_claimed: false)
python3 scripts/validate_docs_i18n.py                                  => PASS
git diff --check                                                       => PASS
```

The local no-env validation path is truthful and blocked/unavailable. The
manual CI result above is the committed result checkpoint for B16-F.

## Manual CI result

Manual real-provider CI run `27945253824` passed. The committed artifact now mirrors the sanitized aggregate report from that run: 8 synthetic tasks x 3 arms = 24 live provider calls, `model_display_category=Kimi-K2.7-Code`, forbidden scan pass, 352/352 self-test checks, `private_score_manifest.record_count=24`, `private_event_manifest.record_count=24`, both manifests `storage_class=tmp_private` and `path_publicly_serialized=false`. Sparse control solved 2/8 (`solve_rate=0.25`, `tests_pass_rate=0.25`, `latency_seconds_mean=13.4355`); same-budget BM25 context pack solved 8/8 (`solve_rate=1.0`, `tests_pass_rate=1.0`, `latency_seconds_mean=1.1885`); BEA v0.3 context pack also solved 8/8 (`solve_rate=1.0`, `tests_pass_rate=1.0`, `latency_seconds_mean=1.579`). Primary BEA-vs-BM25 deltas: solve/test/wrong-file/edit-validity deltas 0.0, `latency_seconds_mean` delta +0.3905, prompt tokens +161, completion tokens +47. Secondary deltas vs sparse: both context arms +0.75 solve/test. Interpretation: B16-F shows context-pack benefit over sparse on this bounded synthetic live-provider slice, but BEA v0.3 does not improve over same-budget BM25; `context_pack_signal_observed=false` for the primary contrast. This is a downstream live-provider smoke result, not downstream value proof, not a method-winner/default/performance/calibration claim.

## Caveats

- B16-F is the public aggregate-only BEA-derived context pack
  downstream paired smoke artifact. It is eval/diagnostic only. It does
  NOT change runtime, retriever, pack, backend, or default policy; it
  does NOT change EvidenceCore semantics. It is NOT a benchmark
  result, NOT a downstream agent value claim, NOT a runtime-clean
  general algorithm claim, NOT an OOD temporal claim, NOT a QuIVer
  systems claim, NOT a method winner claim, NOT a calibration claim,
  and NOT a promotion/default/runtime/EvidenceCore change.
- B16-F uses a **live LLM provider** (OpenAI-compatible) only when
  `--allow-remote` + remote opt-in gate + provider credential/model env are
  all set. The default local no-env path remains truthful
  (`blocked_remote_not_enabled`). It is NOT a fake pass.
- B16-F does NOT prove downstream agent value.
  `downstream_agent_value_proven=false`.
- B16-F does NOT claim live agent generalization.
  `live_agent_generalization_claimed=false`.
- B16-F does NOT publish prompts, responses, provider payloads, base
  URLs, API keys, raw model routing prefixes, workspace paths, file
  paths, source snippets, patches/diffs, test output, candidate
  features, BEA action traces, pack composition, raw event logs, or
  per-run rows. The per-run event logs, prompts, responses, candidate
  features, BEA action traces, and test output stay under `/tmp` only
  and are NEVER committed or uploaded.
- The BEA v0.3 context pack selector uses ONLY runtime-clean candidate
  features. It NEVER reads gold paths, `correct_value`, task_family
  decisive cues, or any private answer. This is verified in the
  self-test via the gold-tainting invariant.
- The committed artifact contains ONLY aggregate counts/rates/means in
  records-shaped containers. No raw model routing prefix is emitted;
  only the normalized `model_display_category` is recorded.
- `honest_signals` and `family_signal_summary` are diagnostic smoke
  outcomes only, NEVER promotion/default/value claims. Zero or
  negative BEA-vs-BM25 delta is a valid empirical result. Some families
  may show positive delta while others show zero or negative; all are
  valid empirical outcomes.
- All no-claim / no-runtime-change flags remain false; diagnostic
  flags (`aggregate_only_public_artifact`, `diagnostic_only`) remain
  true; the live-run flags are true ONLY when a live run actually
  executed.
- No runtime/retriever/pack/model/backend/default-policy files were
  modified. No promotion/default/runtime claims change.
