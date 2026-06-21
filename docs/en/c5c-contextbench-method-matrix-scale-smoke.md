# C5-C ContextBench Verified Retrieval Method Matrix Scale Smoke

Date: 2026-06-21 (C5-C external benchmark retrieval method matrix scale
smoke over ContextBench verified subset, scaling C5-B 5-row method
matrix smoke up to a bounded 20-row method-matrix scale smoke)

C5-C is the **bounded 20-row method-matrix scale extension** of the C5-B
external-benchmark-shaped retrieval method matrix smoke. It reads a
bounded 20-row ContextBench verified subset from the HuggingFace
datasets-server ONCE, materializes the referenced repository at
`base_commit` under a transient `/tmp` workspace, and runs OpenLocus
retrieval across the requested method matrix (default
`bm25,regex,symbol`; only `bm25,regex,symbol` allowed in C5-C; fixed
`baseline_method=bm25`), scoring each method against benchmark label
spans via the existing `eval/score.py` logic. It commits
**only an aggregate public report** with per-method aggregate metrics
(records, NOT dynamic method-key dicts), aggregate-only deltas vs the
fixed `bm25` baseline, and an `input_summary` block.

C5-C is explicitly **not** a rigorous benchmark result, **not** a
leaderboard entry, **not** a performance claim, **not** a promotion,
**not** a default/policy change, and **not** a runtime/retriever/pack/
backend/EvidenceCore semantic change. It does NOT emit `winner`,
`best_method`, `recommended_default`, or anything implying a policy/
default decision. `baseline_is_policy_candidate=false` and
`default_should_change=false` are fixed.

> **Important claim boundary.** C5-C emits `claim_level =
> external_benchmark_retrieval_method_matrix_scale_smoke_only`. It does
> NOT claim an external benchmark result, NOT a leaderboard entry, NOT
> a performance claim, NOT a promotion, NOT a default change, NOT a
> runtime/retriever/pack/backend change, NOT an EvidenceCore semantic
> change, and NOT a downstream agent value claim. All no-claim /
> no-runtime-change flags are false:
> `external_benchmark_performance_claimed=false`,
> `leaderboard_entry_claimed=false`,
> `downstream_agent_value_proven=false`, `promotion_ready=false`,
> `default_should_change=false`, `baseline_is_policy_candidate=false`,
> `runtime_behavior_changed=false`, `retriever_changed=false`,
> `pack_builder_changed=false`, `backend_changed=false`,
> `default_policy_changed=false`, `evidencecore_semantics_changed=false`,
> `provider_calls_made=false`, `remote_provider_calls_made=false`.

## Objective

Scale the C5-B single-method ContextBench verified retrieval method
matrix smoke (5 rows) up to a bounded 20-row method-matrix scale smoke:

- read a bounded 20-row ContextBench verified subset from HuggingFace
  datasets-server `/rows` endpoint ONCE (shared across all methods);
- keep raw ContextBench rows, queries/problem statements, repo URLs/
  names, base commits, gold paths/spans/contents, generated task/label/
  run JSONL, evidence rows, and cloned source repos **transient only**
  under `/tmp` or CI ephemeral workspace;
- materialize the referenced repository at `base_commit` via
  `git clone --filter=blob:none --no-checkout` then `git checkout`;
- run OpenLocus retrieval across the requested method matrix
  (default `bm25,regex,symbol`; only `bm25,regex,symbol` allowed in
  C5-C; fixed `baseline_method=bm25`; no provider/model calls);
- score each method against benchmark label spans via existing
  `eval/score.py` logic;
- commit only an aggregate public report with per-method records,
  aggregate-only deltas vs the fixed `bm25` baseline, and an
  `input_summary` block.

This is empirical method-matrix scale smoke, not another readiness/
control-plane stage. It is also not a rigorous benchmark claim,
promotion, default-policy change, leaderboard entry, or downstream-agent
value claim.

## C5-A -> C5-B -> C5-C relation

```text
C5-A ContextBench verified retrieval performance smoke
  (single-method; bm25 default; bounded 5-row ContextBench verified
   subset; transient /tmp clone + retrieval + score; aggregate-only
   public artifact; no provider calls; no raw rows/queries/repo URLs/
   commits/gold paths/spans/JSONL/evidence rows/cloned repos/stdout/
   stderr committed)
-> C5-B ContextBench verified retrieval method matrix smoke
   (multi-method matrix; default bm25,regex,symbol; allowed
    bm25,regex,text,symbol; 5-row per method; fixed baseline_method=bm25;
    shared row fetch across methods; per-method aggregate records;
    aggregate-only deltas vs bm25; aggregate-only public artifact;
    no provider calls; no winner/best_method/recommended_default)
-> C5-C ContextBench verified retrieval method matrix scale smoke
   (multi-method matrix; bm25,regex,symbol ONLY (no text);
    bounded 20-row per method; fixed baseline_method=bm25;
    shared row fetch across methods; per-method aggregate records with
    optional aggregate_runtime_seconds; aggregate-only deltas vs bm25;
    input_summary block; aggregate-only public artifact;
    no provider calls; no winner/best_method/recommended_default;
    status pass enum contextbench_method_matrix_scale_smoke_pass)
```

C5-C is NOT C5. The full C5 external-benchmark-evaluation phase remains
a bounded planning / feasibility stage that would require rigorous
benchmark design, larger sample sizes, multiple methods, and statistical
analysis. C5-C only produces the first empirical external-benchmark-
shaped retrieval method matrix scale smoke by running a bounded 20-row
ContextBench verified subset through the real OpenLocus retrieval +
scoring pipeline across the requested method matrix.

## Implementation

### Evaluator

`eval/c5c_contextbench_verified_method_matrix_scale_smoke.py` exposes
an argparse CLI:

- `--self-test` — no-network synthetic self-test (179 assertion checks).
- `--row-limit` — number of ContextBench verified rows to evaluate per
  method; default 20, hard cap 20 (C5-C is the bounded scale smoke: it
  uses the full ContextBench verified preview budget in one run).
- `--methods` — comma-separated OpenLocus retrieval methods; default
  `bm25,regex,symbol`; only `bm25,regex,symbol` allowed in C5-C (the
  `text` method is NOT allowed in C5-C, unlike C5-B which allows it);
  unknown methods are rejected; duplicates are deduplicated
  deterministically (first-seen order preserved).
- `--query-mode` — query sanitizer mode; default `first_paragraph`;
  allowed `first_paragraph`, `first_sentence`, `raw`.
- `--language-filter` — language filter category; default `python`;
  allowed `python`, `all` (categorical bucket only — never the raw row
  value beyond in-memory scope).
- `--openlocus` — optional OpenLocus binary path (default
  `target/release/openlocus` then `target/debug/openlocus` fallback;
  resolved to an absolute path because `run_retrieval.py` runs with
  `--cwd <repo_root>`).
- `--out` — output artifact JSON path; default
  `artifacts/c5c_contextbench_verified_method_matrix_scale/c5c_contextbench_verified_method_matrix_scale_report.json`.

Unknown/private-looking arguments are rejected with a generic `invalid
arguments` message that does not echo private paths or basenames
(`SafeArgumentParser` pattern).

### Runtime flow

1. Self-test must pass before any artifact is written
   (`_refuse_on_self_test_failure`).
2. Parse methods (raises `MethodConfigError` on invalid config; produces
   an `unavailable_with_reason` report on failure).
3. Resolve OpenLocus binary to an absolute path (release then debug
   fallback). If missing, produce truthful `unavailable_with_reason`
   with `failure_reason_category=retrieval_failed`.
4. Fetch bounded 20-row ContextBench verified rows from HF datasets-server
   `/rows` endpoint ONCE (paginated; stdlib `urllib` only; bounded
   timeout). Filter in-memory by `language_filter` (categorical bucket
   only). This single fetch is shared across all methods.
5. For each method (bounded to `bm25,regex,symbol`):
   - For each row (bounded to 20):
     - Parse benchmark label context JSON into transient `gold_paths` /
       `gold_lines` for `eval/score.py` (the label `content` field is
       read or persisted).
     - Sanitize `problem_statement` into a retrieval query (in-memory
       only; first paragraph / first sentence / raw; strip HTML comments,
       HTML tags, markdown headers, code fences; cap length).
     - Clone `repo_url` at `base_commit` under a per-row
       `TemporaryDirectory` via `git clone --filter=blob:none
       --no-checkout` then `git checkout` (bounded timeouts).
     - Generate transient task/label JSONL under a
       `TemporaryDirectory`.
     - Run OpenLocus retrieval via `eval/run_retrieval.py`
       (`--method <method> --cwd <repo_root>`).
     - Run `eval/score.py` and parse aggregate metrics.
   - Aggregate metrics across successful rows (mean of each allowlisted
     numeric metric).
   - Record `aggregate_runtime_seconds` (wall-clock time for the
     method's full run).
6. Compute aggregate deltas vs the fixed `bm25` baseline.
7. Build aggregate-only public report with fail-closed forbidden scan.

### Public artifact identity

The committed artifact at
`artifacts/c5c_contextbench_verified_method_matrix_scale/c5c_contextbench_verified_method_matrix_scale_report.json`
is the public aggregate-only scale-smoke artifact. Identity / boundary
fields:

- `schema_version` = `c5c_contextbench_verified_method_matrix_scale_smoke.v1`
- `generated_by`, `generated_at`, `claim_level`, `status`, `mode`,
  `phase`
- `status`: `contextbench_method_matrix_scale_smoke_pass` | `partial` |
  `unavailable_with_reason` | `fail_forbidden_scan`
- Safe true flags (true only if actually true):
  `retrieval_scale_smoke_performed`, `openlocus_retrieval_executed`,
  `score_py_metrics_computed`, `aggregate_only_public_artifact`,
  `diagnostic_only`. (C5-C does NOT use C5-B's `method_matrix_smoke`
  flag or C5-A's `external_benchmark_rows_read`/
  `repositories_materialized_transiently`/`performance_smoke` flags.)
- No-claim / no-runtime-change flags (all false):
  `external_benchmark_performance_claimed`,
  `leaderboard_entry_claimed`, `downstream_agent_value_proven`,
  `promotion_ready`, `default_should_change`,
  `baseline_is_policy_candidate`, `runtime_behavior_changed`,
  `retriever_changed`, `pack_builder_changed`, `backend_changed`,
  `default_policy_changed`, `evidencecore_semantics_changed`,
  `provider_calls_made`, `remote_provider_calls_made`.
- License fields (fixed):
  `dataset_license_status=unknown_dataset_license`,
  `row_level_redistribution_allowed=false`,
  `derived_row_level_publication_allowed=false`,
  `aggregate_metrics_publication=aggregate_only_smoke`.
- `methods_requested`, `methods_allowed`, `baseline_method`,
  `query_mode`, `language_filter`, `network_mode`,
  `openlocus_binary_source`.
- `row_limit_requested`, `rows_fetched`, `methods_count`,
  `methods_attempted`, `methods_successful`, `methods_succeeded`,
  `methods_failed`, `network_calls`, `provider_calls=0`.
- `input_summary`: `row_limit`, `methods`, `query_mode`,
  `language_filter`, `rows_fetched`, `rows_evaluated`,
  `rows_successful`, `rows_failed` (aggregate counts only).
- `failure_reason_category` (only in `unavailable_with_reason` status).
- `failure_category_counts`: fixed enum categories only.
- `method_results`: fixed records (list of dicts, NOT a dict keyed by
  method name) with `method`, `status`, `rows_evaluated`,
  `rows_successful`, `rows_failed`, `metrics` (allowlisted only),
  `failure_category_counts`, and optional `aggregate_runtime_seconds`.
- `smoke_metric_deltas_vs_baseline`: fixed records with
  `baseline_method=bm25`, `method`, `metric` (allowlisted), `delta`.
- `framing`: explicit `external_benchmark_performance_claimed=false`,
  `leaderboard_entry_claimed=false`, `promotion_claimed=false`, etc.
- `self_test_passed`.
- `forbidden_scan` summary (fail-closed before writing JSON).

### Aggregate metrics

The `metrics` block in each method result record contains only
allowlisted aggregate metric names and numeric values from
`eval/score.py`. No row-level records, no row IDs, no paths, no spans,
no snippets, no content_sha. Allowlisted metric names:

- `file_recall@10`, `mrr`, `span_f0.5@10`, `success_rate`.

The `failure_category_counts` block contains only fixed enum category
labels (never row-level values):

- `network_fetch_failed`, `row_parse_failed`,
  `label_context_parse_failed`, `language_filter_excluded`,
  `clone_failed`, `checkout_failed`, `task_jsonl_write_failed`,
  `label_jsonl_write_failed`, `retrieval_failed`, `score_failed`,
  `no_python_rows`, `row_limit_capped`, `scanner_self_test_failed`,
  `forbidden_leak_blocked`, `unexpected_exception`.

### Unavailable mode

If the network smoke cannot complete (network/HF/GitHub failure, clone
timeout, retrieval failure, score failure, etc.), the artifact records
truthful `unavailable_with_reason` with a real `failure_reason_category`
and the corresponding `failure_category_counts` increment. No stale/
fake pass is ever written. In unavailable mode:

- `status=unavailable_with_reason`.
- `method_results` is a list of per-method records, each with
  `status=unavailable_with_reason`, `metrics={}`, and zero row counts.
- `smoke_metric_deltas_vs_baseline=[]` (no deltas).
- `retrieval_scale_smoke_performed=false`.
- `openlocus_retrieval_executed=false`.
- `score_py_metrics_computed=false`.
- `aggregate_only_public_artifact=true` and `diagnostic_only=true`
  remain true.

## Privacy / license boundary

Public artifacts and docs remain aggregate-only. The following were
NOT persisted in any public artifact or doc:

- raw ContextBench rows and gold labels;
- row-level task instance values, instance IDs, original_inst_id;
- repo URLs, repo names, base commits, repo paths;
- file paths, spans, line ranges, snippets, gold content;
- problem statements / queries (sanitized in-memory only);
- patches, test patches, f2p, p2p;
- generated task/label/run JSONL (transient `/tmp` only);
- OpenLocus evidence rows, snippets, paths, line ranges, content_sha;
- cloned repos/source files (transient `/tmp` only);
- raw command stdout/stderr or stack traces;
- per-row metrics or per-row failure records;
- row/repo/candidate hashes.

The public artifact records only: aggregate metric means/rates/counts
from `eval/score.py` (allowlisted), fixed failure-category counts, fixed
config labels (method, query_mode, language_filter categories only),
row counts, network/provider call counts, optional per-method
aggregate runtime seconds, and the deterministic `generated_by` path.

ContextBench dataset license is unknown
(`unknown_dataset_license`); row-level redistribution is disabled
(`row_level_redistribution_allowed=false`) and derived row-level
publication is disabled
(`derived_row_level_publication_allowed=false`). Aggregate metrics
publication is allowed as aggregate-only smoke
(`aggregate_metrics_publication=aggregate_only_smoke`).

## Network / CI policy

- Default no-network self-test passes without HuggingFace/GitHub.
- Real scale smoke requires public network access to HF
  datasets-server and GitHub repos. CI is a separate explicit
  `workflow_dispatch` job with `enable_external_benchmark_network=true`
  input. It does NOT run on PR/push by default, uses no provider
  secrets/vars, no `OPENLOCUS_LLM`/`OPENLOCUS_EMBEDDING` env, and
  uploads only the aggregate temp report.
- If `enable_external_benchmark_network` is false, the workflow is a
  no-op with a clear message and exits 0 (self-test + py_compile still
  run; no aggregate report is produced in no-op mode).
- The workflow validates the report's claim boundary flags after the
  smoke: `aggregate_only_public_artifact=true`, `diagnostic_only=true`;
  all no-claim / no-runtime-change flags false; license fields fixed;
  `provider_calls=0`; `forbidden_scan.status=pass`;
  `self_test_passed=true`; `status` in
  `(contextbench_method_matrix_scale_smoke_pass, partial,
  unavailable_with_reason)` (no stale/fake pass; no
  `fail_forbidden_scan`).

## Forbidden scanner (public, fail-closed)

A strict forbidden-output scanner runs fail-closed before writing the
public JSON. Reuses C5-A forbidden scanner primitives for raw key/value
leak detection, and ADDS C5-C-specific checks:

- Rejects forbidden dict keys (`path`, `span`, `file`, `repo`,
  `repo_url`, `base_commit`, `instance_id`, `problem_statement`,
  benchmark label-context keys, `gold_paths`, `gold_lines`, `query`, `content_sha`,
  `snippet`, `patch`, `diff`, `stdout`, `stderr`, `event_log`,
  `stack_trace`, `api_key`, `base_url`, `provider_key`, `secret`,
  `token`, `credential`, `rows`, `per_run`, `predictions`, `candidates`,
  `evidence`, `row`, `repo_name`, `repo_slug`, `query_text`, `gold`,
  `gold_path`, `gold_span`, `gold_snippet`, `stdout_text`,
  `stderr_text`, `evidence_row`, `evidence_rows`, `retrieved_path`,
  `retrieved_paths`, `retrieved_snippet`, `cloned_repo_path`,
  `cloned_repo`, `per_row_metrics`, `row_metrics`, etc.) anywhere.
- Rejects recommendation / policy fields anywhere: `winner`,
  `best_method`, `recommended_default`, `recommended_method`,
  `preferred_method`, `default_method`, `policy_decision`, `decision`,
  `ranking`, `rank`.
- Rejects value patterns: ANY URL (no URL allowlist — repo URLs must
  NEVER leak), 32+ char hex digests, 40-char commit SHAs, repo slugs
  like `astropy/astropy`, secret-like strings, path-like strings with
  file extensions, `/tmp/` workspace path values, `task_N`
  task-identifier values, patch/diff markers (`---`, `+++`, `@@`),
  stack traces, multiline strings, raw JSON fragments, raw line
  ranges `12-34`, and the self-test sentinel.
- Rejects `method_results` as a dict keyed by method name (must be a
  list of records); rejects records with missing/non-allowlisted
  `method`; rejects `text` as a method (C5-C allows only
  `bm25,regex,symbol`).

The `failure_category_counts`, `metrics`, and
`smoke_metric_deltas_vs_baseline` containers are schema-key containers
whose CHILD KEYS are fixed category labels or allowlisted metric names
(NOT row-level values); the forbidden_key check is relaxed for those
child keys, but the values under them are still scanned (they must be
ints/floats/short strings only).

The scanner runs ONLY against the final public aggregate artifact.
Internal task/label/run JSONL (which contain paths/spans/queries/gold)
are kept in-memory/transient under `/tmp` only, never scanned against
the public contract, and never committed.

## Self-tests

`--self-test` runs 179 deterministic checks across 19 groups (no
network; synthetic rows + synthetic score data):

1. Method parser (rejects unknown; dedups duplicates; default exactly
   bm25,regex,symbol; skips empty tokens; rejects `text` method in
   C5-C).
2. Hard cap row_limit=20 (default 20; cap 20; passes through at 5 and
   20; rejects 0).
3. Method result records (reject unknown method; reject `text` method;
   accept allowlisted method; reject non-allowlisted metric; allowlist
   subset of C5-A; accept `aggregate_runtime_seconds`; reject
   non-numeric runtime; reject unexpected keys).
4. Deltas only for allowlisted metrics and baseline bm25 (excludes
   baseline method; only allowlisted metrics; baseline is bm25; value
   correctness; empty when baseline missing; validator rejects
   baseline method / non-numeric / non-allowlisted metric).
5. No best_method / recommendation fields (scanner rejects all 10
   recommendation fields; clean report missing all of them;
   `baseline_is_policy_candidate=false`; `default_should_change=false`).
6. Scanner rejects dynamic method key not in allowlist (dict shape;
   non-dict record; missing method; non-allowlisted method; `text`
   method; accepts clean list).
7. Scanner rejects row/repo/query/gold/path/span/snippet/content_sha/
   stdout/stderr keys (45 forbidden keys); rejects repo URL value;
   rejects repo slug value; rejects commit SHA value.
8. Status semantics (all pass => `contextbench_method_matrix_scale_smoke_pass`;
   mixed => `partial`; none => `unavailable_with_reason`; empty =>
   `unavailable_with_reason`; pass enum is the distinct string).
9. Generation fails if scanner fails (clean report no raise; leaked
   repo raises; `best_method` raises; `winner` raises;
   `recommended_default` raises; `method_results` dict raises;
   self-test failure refuses artifact generation).
10. Artifact identity fields (schema, claim, status, mode, phase,
    generated_by; status pass when self-test passed).
11. Safe true flags present + correct values (5 flags; no C5-B
    `method_matrix_smoke` flag; no C5-A `external_benchmark_rows_read`
    flag).
12. No-claim / no-runtime-change false flags (14 flags).
13. License fields (4 fields).
14. Unavailable report (truthful; no stale/fake pass; no deltas;
    forbidden scan pass; all method_results unavailable; has
    input_summary).
15. Public artifact self-scan is clean (skeleton + unavailable).
16. CLI argument surface (`--self-test`, `--row-limit`, `--methods`,
    `--query-mode`, `--language-filter`, `--openlocus`, `--out`).
17. `ALLOWED_METHODS` exactly `bm25,regex,symbol`; excludes `text`.
18. `input_summary` shape (has row_limit, methods, query_mode,
    language_filter, aggregate counts).
19. `aggregate_runtime_seconds` in method result records (present;
    numeric; scanner accepts).

## Validation

```text
python3 -m py_compile eval/c5c_contextbench_verified_method_matrix_scale_smoke.py  => PASS
python3 eval/c5c_contextbench_verified_method_matrix_scale_smoke.py --self-test  => PASS (179/179 checks)
python3 eval/c5c_contextbench_verified_method_matrix_scale_smoke.py \
  --row-limit 20 --methods bm25,regex,symbol \
  --query-mode first_paragraph --language-filter python \
  --out artifacts/c5c_contextbench_verified_method_matrix_scale/\
c5c_contextbench_verified_method_matrix_scale_report.json  => PASS
  (status: contextbench_method_matrix_scale_smoke_pass,
   forbidden_scan: pass, self_test_passed: true,
   mode: contextbench_verified_bounded_scale_method_matrix, phase: C5-C,
   methods: [bm25, regex, symbol], methods_successful: 3, methods_failed: 0,
   rows_fetched: 20, rows_evaluated: 20, rows_successful: 20, rows_failed: 0,
   network_calls: 1, provider_calls: 0,
   retrieval_scale_smoke_performed: true,
   openlocus_retrieval_executed: true,
   score_py_metrics_computed: true,
   aggregate_only_public_artifact: true,
   diagnostic_only: true,
   external_benchmark_performance_claimed: false,
   leaderboard_entry_claimed: false,
   downstream_agent_value_proven: false,
   promotion_ready: false, default_should_change: false,
   baseline_is_policy_candidate: false,
   runtime_behavior_changed: false, retriever_changed: false,
   pack_builder_changed: false, backend_changed: false,
   default_policy_changed: false, evidencecore_semantics_changed: false,
   provider_calls_made: false, remote_provider_calls_made: false,
   dataset_license_status: unknown_dataset_license,
   row_level_redistribution_allowed: false,
   derived_row_level_publication_allowed: false,
   aggregate_metrics_publication: aggregate_only_smoke)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

## Real smoke result (2026-06-21)

```text
python3 eval/c5c_contextbench_verified_method_matrix_scale_smoke.py \
  --row-limit 20 --methods bm25,regex,symbol \
  --query-mode first_paragraph --language-filter python \
  --out artifacts/c5c_contextbench_verified_method_matrix_scale/\
c5c_contextbench_verified_method_matrix_scale_report.json
  => status: contextbench_method_matrix_scale_smoke_pass,
     forbidden_scan: pass, self_test_passed: true
  => rows_fetched: 20, rows_evaluated: 20, rows_successful: 20, rows_failed: 0
  => methods: [bm25, regex, symbol], methods_successful: 3, methods_failed: 0
  => network_calls: 1, provider_calls: 0
  => retrieval_scale_smoke_performed: true
  => openlocus_retrieval_executed: true
  => score_py_metrics_computed: true
```

The 20 ContextBench verified rows were fetched transiently from HF
datasets-server ONCE (shared across all 3 methods), adapted in-memory,
the referenced repositories were cloned at their `base_commit` under
transient `/tmp` directories (once per method+row), OpenLocus retrieval
was run on each repository for each method (`bm25`, `regex`, `symbol`),
and `eval/score.py` produced aggregate retrieval metrics per method.
Aggregate metric means were computed across the 20 successful rows per
method and written to the committed artifact. No raw ContextBench rows,
queries, repo URLs/names, base commits, gold paths/spans/contents,
generated task/label/run JSONL, evidence rows, cloned repos, or
stdout/stderr were committed or uploaded.

If the network smoke cannot complete in a future environment (network/
HF/GitHub failure, clone timeout, retrieval failure, score failure),
the artifact records truthful `unavailable_with_reason` with a real
`failure_reason_category` and the corresponding
`failure_category_counts` increment. No stale/fake pass is ever written.

## Caveats

- C5-C is the public aggregate-only external benchmark retrieval method
  matrix scale smoke artifact. It is eval/diagnostic only. It does NOT
  change runtime, retriever, pack, backend, or default policy; it does
  NOT change EvidenceCore semantics. It is NOT a benchmark result, NOT
  a leaderboard entry, NOT a performance claim, NOT a promotion, NOT a
  default change, NOT a runtime-clean general algorithm claim, NOT an
  OOD temporal claim, NOT a QuIVer systems claim, and NOT a downstream
  agent value claim.
- C5-C runs NO provider calls and NO remote provider calls. The only
  network calls are to the public HF datasets-server (to fetch bounded
  ContextBench verified rows ONCE, shared across all methods) and to
  public GitHub (to clone the referenced repositories at their
  `base_commit` under transient `/tmp` directories, once per method+row).
  `provider_calls=0`, `provider_calls_made=false`,
  `remote_provider_calls_made=false`.
- C5-C uses a **bounded 20-row ContextBench verified subset** (default
  20 rows per method; hard cap 20). This is a scale smoke, not a
  rigorous benchmark evaluation. The aggregate metrics are point
  estimates over a bounded sample and should NOT be interpreted as a
  benchmark result, leaderboard entry, or performance claim.
- C5-C materializes the referenced repositories at their `base_commit`
  under transient `/tmp` directories, once per method+row (because
  each method runs against the same rows but in isolated workspaces).
  The cloned repos, generated task/label/run JSONL, evidence rows, and
  stdout/stderr stay under `/tmp` only and are NEVER committed or
  uploaded. The committed artifact contains ONLY aggregate counts/
  rates/means and optional per-method aggregate runtime seconds.
- C5-C does NOT claim external benchmark performance. The aggregate
  metrics are smoke-level diagnostics, NOT a benchmark result.
  `external_benchmark_performance_claimed=false`.
- C5-C does NOT emit `winner`, `best_method`, `recommended_default`,
  or anything implying a policy/default decision.
  `baseline_is_policy_candidate=false`, `default_should_change=false`.
- C5-C does NOT prove downstream agent value. The retrieval smoke does
  not exercise any downstream agent. `downstream_agent_value_proven=false`.
- ContextBench dataset license is unknown
  (`unknown_dataset_license`); row-level redistribution is disabled
  (`row_level_redistribution_allowed=false`) and derived row-level
  publication is disabled
  (`derived_row_level_publication_allowed=false`). Aggregate metrics
  publication is allowed as aggregate-only smoke
  (`aggregate_metrics_publication=aggregate_only_smoke`).
- All no-claim / no-runtime-change flags remain false; diagnostic flags
  (`aggregate_only_public_artifact`, `diagnostic_only`) remain true.
  No runtime/retriever/pack/model/backend/default-policy files were
  modified; no promotion/default/runtime claims change.

## Next steps

- C5-C is the bounded 20-row external-benchmark-shaped retrieval method
  matrix scale smoke. The full C5 external-benchmark-evaluation phase
  remains a bounded planning / feasibility stage that would require
  rigorous benchmark design, larger sample sizes, multiple methods, and
  statistical analysis.
- No promotion, no default change, no EvidenceCore semantics change, no
  runtime-clean general algorithm claim, no downstream agent value
  claim, no OOD temporal claim, and no QuIVer systems claim follows from
  C5-C.
