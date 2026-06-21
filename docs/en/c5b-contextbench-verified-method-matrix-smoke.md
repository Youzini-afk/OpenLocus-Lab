# C5-B ContextBench Verified Retrieval Method Matrix Smoke

Date: 2026-06-21 (C5-B external benchmark retrieval method matrix smoke
over ContextBench verified subset, extending C5-A single-method smoke
into a bounded multi-method matrix smoke)

C5-B is the **bounded multi-method matrix extension** of the C5-A
external-benchmark-shaped retrieval performance smoke. It reads a bounded
ContextBench verified subset from the HuggingFace datasets-server ONCE,
materializes the referenced repository at `base_commit` under a transient
`/tmp` workspace, and runs OpenLocus retrieval across the requested method
matrix (default `bm25,regex,symbol`; allowed `bm25,regex,text,symbol`;
fixed `baseline_method=bm25`), scoring each method against ContextBench
`gold_context` spans via the existing `eval/score.py` logic. It commits
**only an aggregate public report** with per-method aggregate metrics
(records, NOT dynamic method-key dicts) and aggregate-only deltas vs the
fixed `bm25` baseline.

C5-B is explicitly **not** a rigorous benchmark result, **not** a
leaderboard entry, **not** a performance claim, **not** a promotion,
**not** a default/policy change, and **not** a runtime/retriever/pack/
backend/EvidenceCore semantic change. It does NOT emit `winner`,
`best_method`, `recommended_default`, or anything implying a policy/default
decision. `baseline_is_policy_candidate=false` and
`default_should_change=false` are fixed.

> **Important claim boundary.** C5-B emits `claim_level =
> external_benchmark_retrieval_method_matrix_smoke_only`. It does NOT claim
> an external benchmark result, NOT a leaderboard entry, NOT a performance
> claim, NOT a promotion, NOT a default change, NOT a runtime/retriever/
> pack/backend change, NOT an EvidenceCore semantic change, and NOT a
> downstream agent value claim. All no-claim / no-runtime-change flags
> are false: `external_benchmark_performance_claimed=false`,
> `leaderboard_entry_claimed=false`,
> `downstream_agent_value_proven=false`, `promotion_ready=false`,
> `default_should_change=false`, `baseline_is_policy_candidate=false`,
> `runtime_behavior_changed=false`, `retriever_changed=false`,
> `pack_builder_changed=false`, `backend_changed=false`,
> `default_policy_changed=false`, `evidencecore_semantics_changed=false`,
> `provider_calls_made=false`, `remote_provider_calls_made=false`.

## Objective

Extend the C5-A single-method ContextBench verified retrieval performance
smoke into a bounded multi-method matrix smoke:

- read a bounded ContextBench verified subset from HuggingFace
  datasets-server `/rows` endpoint ONCE (shared across all methods);
- keep raw ContextBench rows, queries/problem statements, repo URLs/
  names, base commits, gold paths/spans/contents, generated task/label/
  run JSONL, evidence rows, and cloned source repos **transient only**
  under `/tmp` or CI ephemeral workspace;
- materialize the referenced repository at `base_commit` via
  `git clone --filter=blob:none --no-checkout` then `git checkout`;
- run OpenLocus retrieval across the requested method matrix
  (default `bm25,regex,symbol`; allowed `bm25,regex,text,symbol`;
  fixed `baseline_method=bm25`; no provider/model calls);
- score each method against ContextBench `gold_context` spans via existing
  `eval/score.py` logic;
- commit only an aggregate public report with per-method records and
  aggregate-only deltas vs the fixed `bm25` baseline.

This is empirical method-matrix smoke, not another readiness/control-plane
stage. It is also not a rigorous benchmark claim, promotion, default-policy
change, leaderboard entry, or downstream-agent value claim.

## C5-A -> C5-B relation

```text
C5-A ContextBench verified retrieval performance smoke
  (single-method; bm25 default; bounded ContextBench verified subset;
   transient /tmp clone + retrieval + score; aggregate-only public
   artifact; no provider calls; no raw rows/queries/repo URLs/commits/
   gold paths/spans/JSONL/evidence rows/cloned repos/stdout/stderr
   committed)
-> C5-B ContextBench verified retrieval method matrix smoke
   (multi-method matrix; default bm25,regex,symbol; allowed
    bm25,regex,text,symbol; fixed baseline_method=bm25;
    shared row fetch across methods; per-method aggregate records;
    aggregate-only deltas vs bm25; aggregate-only public artifact;
    no provider calls; no winner/best_method/recommended_default)
```

C5-B is NOT C5. The full C5 external-benchmark-evaluation phase remains a
bounded planning / feasibility stage that would require rigorous benchmark
design, larger sample sizes, multiple methods, and statistical analysis.
C5-B only produces the first empirical external-benchmark-shaped retrieval
method matrix smoke by running a bounded ContextBench verified subset
through the real OpenLocus retrieval + scoring pipeline across the
requested method matrix.

## Implementation

### Evaluator

`eval/c5b_contextbench_verified_method_matrix_smoke.py` exposes an
argparse CLI:

- `--self-test` — no-network synthetic self-test (154 assertion checks).
- `--row-limit` — number of ContextBench verified rows to evaluate per
  method; default 5, hard cap 10 (C5-B is stricter than C5-A because each
  row is evaluated across multiple methods).
- `--methods` — comma-separated OpenLocus retrieval methods; default
  `bm25,regex,symbol`; allowed `bm25,regex,text,symbol`; unknown methods
  are rejected; duplicates are deduplicated deterministically
  (first-seen order preserved).
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
  `artifacts/c5b_contextbench_verified_method_matrix/c5b_contextbench_verified_method_matrix_report.json`.

Unknown/private-looking arguments are rejected with a generic `invalid
arguments` message that does not echo private paths or basenames
(`SafeArgumentParser` pattern).

### Reuse of C5-A helpers

C5-B is a standalone script that imports C5-A as a helper module
(`import c5_contextbench_verified_performance_smoke as c5a`). It reuses
the C5-A primitives that are explicitly safe to share:

- Row fetch: `c5a._fetch_contextbench_rows` (paginated HF datasets-server
  `/rows` access; stdlib `urllib` only; bounded timeout).
- Query sanitizer: `c5a._sanitize_query` (in-memory only; first
  paragraph / first sentence / raw; strip HTML comments, HTML tags,
  markdown headers, code fences; cap length).
- Gold context parser: `c5a._parse_gold_context` (transient
  `gold_paths`/`gold_lines`; the `content` field is NEVER read or
  persisted).
- Clone + checkout: `c5a._clone_and_checkout` (per-row
  `TemporaryDirectory`; `git clone --filter=blob:none --no-checkout`
  then `git checkout`; bounded timeouts).
- Transient JSONL writers: `c5a._write_transient_jsonl` (under
  `TemporaryDirectory` only).
- Retrieval + score runner: `c5a._run_retrieval_and_score`
  (`eval/run_retrieval.py` then `eval/score.py`; aggregate JSON only).
- OpenLocus binary resolution: `c5a._resolve_openlocus_binary`
  (release then debug fallback; absolute path).
- Failure categories: `c5a.FAILURE_CATEGORIES` (fixed enum).
- Score metric allowlist: `c5a.SCORE_METRIC_ALLOWLIST` (C5-B's
  `METHOD_METRIC_ALLOWLIST` is a strict subset).
- Scanner primitives: `c5a._scan_forbidden` (raw key/value leak
  detection), `c5a._refuse_on_self_test_failure`,
  `c5a._now_iso`, `c5a._write_json`, `c5a._check`.
- Query modes / language filters: `c5a.ALLOWED_QUERY_MODES`,
  `c5a.DEFAULT_QUERY_MODE`, `c5a.ALLOWED_LANGUAGE_FILTERS`,
  `c5a.DEFAULT_LANGUAGE_FILTER`.
- License fields: `c5a.LICENSE_FIELDS`.

### C5-B-owned schema / claim fields

C5-B owns its own schema, claim fields, method-matrix aggregation,
method allowlist validation, and matrix self-tests:

- `SCHEMA_VERSION = "c5b_contextbench_verified_method_matrix_smoke.v1"`
- `GENERATED_BY = "eval/c5b_contextbench_verified_method_matrix_smoke.py"`
- `CLAIM_LEVEL = "external_benchmark_retrieval_method_matrix_smoke_only"`
- `MODE = "contextbench_verified_retrieval_method_matrix_smoke"`
- `PHASE = "C5-B"`
- `ALLOWED_METHODS = ("bm25", "regex", "text", "symbol")`
- `DEFAULT_METHODS = ("bm25", "regex", "symbol")`
- `BASELINE_METHOD = "bm25"`
- `DELTA_METRIC_ALLOWLIST = ("file_recall@10", "mrr", "span_f0.5@10",
  "success_rate")` (strict subset of `c5a.SCORE_METRIC_ALLOWLIST`).
- `METHOD_METRIC_ALLOWLIST = DELTA_METRIC_ALLOWLIST` (per-method
  metrics are limited to the same allowlist).
- `FORBIDDEN_RECOMMENDATION_FIELDS = {"winner", "best_method",
  "recommended_default", "recommended_method", "preferred_method",
  "default_method", "policy_decision", "decision", "ranking", "rank"}`
  (these keys must NEVER appear anywhere in the public artifact).

### Runtime flow

1. Self-test must pass before any artifact is written
   (`c5a._refuse_on_self_test_failure`).
2. Parse `--methods` (C5-B-owned `parse_methods`): empty/None -> default
   `["bm25", "regex", "symbol"]`; each token must be in
   `ALLOWED_METHODS`; duplicates are deduplicated deterministically
   (first-seen order preserved); empty tokens are skipped. On invalid
   config, produce `fail_schema_contract` report.
3. Validate `--row-limit` (C5-B hard cap 10).
4. Resolve OpenLocus binary to an absolute path (release then debug
   fallback). If missing, produce truthful `unavailable_with_reason`
   with `failure_reason_category=retrieval_failed`.
5. Fetch bounded ContextBench verified rows from HF datasets-server
   `/rows` endpoint ONCE (shared across all methods; paginated; stdlib
   `urllib` only; bounded timeout). Filter in-memory by
   `language_filter` (categorical bucket only).
6. For each method in the requested method matrix:
   - For each row (bounded to `row_limit`):
     - Parse `gold_context` JSON into transient `gold_paths` /
       `gold_lines` for `eval/score.py` (the `content` field is NEVER
       read or persisted).
     - Sanitize `problem_statement` into a retrieval query (in-memory
       only; first paragraph / first sentence / raw; strip HTML comments,
       HTML tags, markdown headers, code fences; cap length).
     - Clone `repo_url` at `base_commit` under a per-row
       `TemporaryDirectory` via `git clone --filter=blob:none
       --no-checkout` then `git checkout` (bounded timeouts).
     - Generate transient task/label JSONL under a `TemporaryDirectory`.
     - Run OpenLocus retrieval via `eval/run_retrieval.py`
       (`--method <method> --cwd <repo_root>`).
     - Run `eval/score.py` and parse aggregate metrics.
   - Aggregate metrics across successful rows for this method
     (mean of each allowlisted numeric metric; `success_rate` recomputed
     from `rows_successful / rows_evaluated`).
   - Build a method result record (list element, NOT a dict key).
7. Compute aggregate deltas vs the fixed `baseline_method=bm25`
   (delta = method_metric - baseline_metric; only for
   `DELTA_METRIC_ALLOWLIST` metrics; baseline excluded from the deltas
   list; empty list if baseline missing — no fake zero).
8. Compute overall status from method results (`pass` if all methods
   succeed, `partial` if mixed, `unavailable_with_reason` if none).
9. Build aggregate-only public report with fail-closed C5-B forbidden
   scan.

### Public artifact identity

The committed artifact at
`artifacts/c5b_contextbench_verified_method_matrix/c5b_contextbench_verified_method_matrix_report.json`
is the public aggregate-only smoke artifact. Identity / boundary fields:

- `schema_version` = `c5b_contextbench_verified_method_matrix_smoke.v1`
- `generated_by`, `generated_at`, `claim_level`, `status`, `mode`,
  `phase`
- `status`: `pass` | `partial` | `unavailable_with_reason` |
  `fail_schema_contract` | `fail_forbidden_scan`
- `methods_requested`, `methods_allowed`, `baseline_method`,
  `query_mode`, `language_filter`, `network_mode`,
  `openlocus_binary_source`.
- `row_limit_requested`, `rows_fetched`, `methods_count`,
  `methods_attempted`, `methods_successful`, `methods_succeeded`,
  `methods_failed`, `network_calls`,
  `provider_calls=0`.
- `method_results`: list of records (NOT a dict keyed by method name):
  ```json
  {"method":"bm25","status":"pass","rows_evaluated":5,
   "rows_successful":5,"rows_failed":0,"metrics":{...},
   "failure_category_counts":{...}}
  ```
- `smoke_metric_deltas_vs_baseline`: list of records, one metric per
  record (only for methods other than the baseline; only for
  `DELTA_METRIC_ALLOWLIST` metrics):
  ```json
  {"baseline_method":"bm25","method":"regex",
   "metric":"mrr","delta":-0.075}
  ```
- `failure_reason_category` (only in `unavailable_with_reason` /
  `fail_schema_contract` status).
- `failure_category_counts`: fixed enum categories only (aggregated
  across methods).
- Safe true flags (true only if actually true):
  `external_benchmark_rows_read`, `repositories_materialized_transiently`,
  `openlocus_retrieval_executed`, `score_py_metrics_computed`,
  `method_matrix_smoke`, `aggregate_only_public_artifact`,
  `diagnostic_only`.
- No-claim / no-runtime-change flags (all false):
  `external_benchmark_performance_claimed`,
  `leaderboard_entry_claimed`,
  `downstream_agent_value_proven`, `promotion_ready`,
  `default_should_change`, `baseline_is_policy_candidate`,
  `runtime_behavior_changed`, `retriever_changed`, `pack_builder_changed`,
  `backend_changed`, `default_policy_changed`,
  `evidencecore_semantics_changed`, `provider_calls_made`,
  `remote_provider_calls_made`.
- License fields (fixed):
  `dataset_license_status=unknown_dataset_license`,
  `row_level_redistribution_allowed=false`,
  `derived_row_level_publication_allowed=false`,
  `aggregate_metrics_publication=aggregate_only_smoke`.
- `framing`: explicit `external_benchmark_performance_claimed=false`,
  `leaderboard_entry_claimed=false`, `promotion_claimed=false`, etc.
- `self_test_passed`.
- `forbidden_scan` summary (fail-closed before writing JSON).

### Aggregate metrics

The `metrics` block in each method result record contains only
allowlisted aggregate metric names and numeric values from
`eval/score.py`. No row-level records, no row IDs, no paths, no spans,
no snippets, no content_sha. Allowlisted metric names (C5-B strict subset
of the C5-A `SCORE_METRIC_ALLOWLIST`):

- `file_recall@10`, `mrr`, `span_f0.5@10`, `success_rate`.

The `smoke_metric_deltas_vs_baseline` records contain one allowlisted
metric per record, computed as `method_metric - baseline_metric` for each
method other than the baseline. The baseline method itself is excluded
from the deltas list (a method is not compared against itself). If the
baseline method is missing or has no metrics, no deltas are emitted (an
empty list, NOT a fake zero).

The `failure_category_counts` block (both at the top level and per
method result record) contains only fixed enum category labels (never
row-level values):

- `network_fetch_failed`, `row_parse_failed`,
  `gold_context_parse_failed`, `language_filter_excluded`,
  `clone_failed`, `checkout_failed`, `task_jsonl_write_failed`,
  `label_jsonl_write_failed`, `retrieval_failed`, `score_failed`,
  `no_python_rows`, `row_limit_capped`, `scanner_self_test_failed`,
  `forbidden_leak_blocked`, `unexpected_exception`.

### Status semantics

- `pass`: all requested methods have at least one successful evaluated
  row and the scanner passes.
- `partial`: at least one method succeeds and at least one method
  fails/unavailable.
- `unavailable_with_reason`: no method completes retrieval+scoring.
- `fail_schema_contract`: invalid method config, unexpected metric key,
  unsafe artifact structure.
- `fail_forbidden_scan`: scanner failure.

### Unavailable mode

If the network smoke cannot complete (network/HF/GitHub failure, clone
timeout, retrieval failure, score failure, etc.), the artifact records
truthful `unavailable_with_reason` with a real `failure_reason_category`
and the corresponding `failure_category_counts` increment. No stale/
fake pass is ever written. In unavailable mode:

- `status=unavailable_with_reason`.
- `method_results` is a list of records, one per requested method, each
  with `status=unavailable_with_reason` and empty `metrics={}`.
- `smoke_metric_deltas_vs_baseline=[]` (no deltas).
- `method_matrix_smoke=false`.
- `openlocus_retrieval_executed=false`.
- `score_py_metrics_computed=false`.
- `repositories_materialized_transiently=false`.
- `external_benchmark_rows_read=true` only if rows were actually
  fetched before the failure.
- `aggregate_only_public_artifact=true` and `diagnostic_only=true`
  remain true.

## Privacy / license boundary

Public artifacts and docs remain aggregate-only. The following were
NOT persisted in any public artifact or doc:

- raw ContextBench rows and gold labels;
- row-level task instance values, instance IDs, original_inst_id;
- repo URLs, repo names, base commits, repo paths, cloned repo paths;
- file paths, spans, line ranges, snippets, gold content;
- problem statements / queries (sanitized in-memory only);
- patches, test patches, f2p, p2p;
- generated task/label/run JSONL (transient `/tmp` only);
- OpenLocus evidence rows, snippets, paths, line ranges, content_sha;
- retrieved paths/snippets/content_sha;
- per-row metrics, row-level hashes;
- raw logs, stdout, stderr;
- cloned repos/source files (transient `/tmp` only).

The public artifact records only: aggregate metric means/rates/counts
from `eval/score.py` (allowlisted), aggregate-only deltas vs the fixed
`bm25` baseline (allowlisted), fixed failure-category counts, fixed
config labels (methods_requested/methods_allowed categories, method
result method names, query_mode, language_filter categories only), row
counts, network/provider call counts, and the deterministic
`generated_by` path.

ContextBench dataset license is unknown
(`unknown_dataset_license`); row-level redistribution is disabled
(`row_level_redistribution_allowed=false`) and derived row-level
publication is disabled
(`derived_row_level_publication_allowed=false`). Aggregate metrics
publication is allowed as aggregate-only smoke
(`aggregate_metrics_publication=aggregate_only_smoke`).

## Network / CI policy

- Default no-network self-test passes without HuggingFace/GitHub.
- Real matrix smoke requires public network access to HF
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
  all no-claim / no-runtime-change flags false; `baseline_is_policy_candidate=false`,
  `default_should_change=false`, `leaderboard_entry_claimed=false`;
  license fields fixed; `provider_calls=0`;
  `forbidden_scan.status=pass`; `self_test_passed=true`; `status` in
  `(pass, partial, unavailable_with_reason)` (no stale/fake pass; no
  `fail_schema_contract` / `fail_forbidden_scan`); no `winner`,
  `best_method`, or `recommended_default` field present.

## Forbidden scanner (public, fail-closed)

C5-B reuses the C5-A forbidden scanner primitives for raw key/value leak
detection (URLs, hex digests, repo slugs, /tmp paths, patch markers,
stack traces, secrets, etc.), and ADDS C5-B-specific checks:

- Rejects `method_results` if it is a dict keyed by method name (C5-B
  requires a list of records, NOT a dict). A dict shape would leak
  method names as dynamic dict keys.
- Rejects each method result record whose `method` value is not in
  `ALLOWED_METHODS` (defensive against tampering to spoof a non-
  allowlisted method).
- Rejects `FORBIDDEN_RECOMMENDATION_FIELDS` keys anywhere (`winner`,
  `best_method`, `recommended_default`, `recommended_method`,
  `preferred_method`, `default_method`, `policy_decision`, `decision`,
  `ranking`, `rank`).
- Rejects C5-B-specific extra forbidden keys anywhere: `row`,
  `rows_data`, `raw_row`, `raw_rows`, `repo_name`, `repo_slug`,
  `query_text`, `gold`, `gold_path`, `gold_span`, `gold_snippet`,
  `snippet`, `snippets`, `content_sha`, `stdout`, `stderr`,
  `stdout_text`, `stderr_text`, `evidence_row`, `evidence_rows`,
  `retrieved_path`, `retrieved_paths`, `retrieved_snippet`,
  `cloned_repo_path`, `cloned_repo`, `per_row_metrics`, `row_metrics`.

The C5-B scanner also filters out a single C5-A false positive: the
method-name string `"text"` appearing as a value under
`methods_allowed` / `methods_requested` is flagged by the C5-A scanner as
`forbidden_field_name_value` (because `text` is a forbidden CONTENT/KEY
name in C5-A's contract). In C5-B, `text` is also a legitimate OpenLocus
retrieval method name, so it may appear as a value under
`methods_allowed` / `methods_requested`. The C5-B scanner filters out
that single false positive (only for `forbidden_field_name_value`
violations on C5-B-specific safe value paths); all other C5-A
violations are preserved.

The `failure_category_counts`, `metrics`, and `smoke_metric_deltas_vs_baseline`
containers are C5-B schema-key containers whose CHILD KEYS are fixed
category labels or allowlisted metric names (NOT row-level values); the
forbidden_key check is relaxed for those child keys, but the values
under them are still scanned.

The scanner runs ONLY against the final public aggregate artifact.
Internal task/label/run JSONL (which contain paths/spans/queries/gold)
are kept in-memory/transient under `/tmp` only, never scanned against
the public contract, and never committed.

## Self-tests

`--self-test` runs 154 deterministic checks across 18 groups (no
network; synthetic rows + synthetic score data):

1. Method parser (rejects unknown methods; deduplicates duplicates
   deterministically; default `bm25,regex,symbol`; skips empty tokens;
   preserves first-seen order).
2. Hard cap `row_limit=10` enforced (default 5; hard cap 10; rejects
   zero; caps above 10; passes through at 5).
3. Method result records require allowlisted method values (rejects
   unknown method; rejects non-allowlisted metric key; accepts
   allowlisted method; method metric allowlist is a subset of C5-A
   score allowlist).
4. Deltas only for allowlisted metrics and baseline `bm25` (excludes
   baseline method; only for `DELTA_METRIC_ALLOWLIST` metrics;
   baseline method is `bm25`; delta value correctness for regex mrr;
   empty when baseline missing; delta validator rejects baseline
   method; rejects non-numeric).
5. No `best_method` / recommendation fields (scanner rejects each
   forbidden recommendation field key; clean report missing each field;
   `baseline_is_policy_candidate=false`; `default_should_change=false`).
6. Scanner rejects dynamic method key not in allowlist if dict shape
   exists (rejects `method_results` as dict; rejects non-dict record;
   rejects missing method; rejects non-allowlisted method; accepts clean
   list-of-records).
7. Scanner rejects row/repo/query/gold/path/span/snippet/content_sha/
   stdout/stderr keys (35 forbidden key injections).
8. Status semantics (all success -> pass; mixed -> partial; none ->
   unavailable; empty -> unavailable).
9. Generation fails if scanner fails (clean report no raise; leaked
   report raises; `best_method` raises; `method_results` dict raises;
   self-test failure refuses artifact generation).
10. Artifact identity fields (schema, claim, status, mode, phase,
    generated_by).
11. Safe true flags present + correct values (7 flags).
12. No-claim / no-runtime-change false flags (14 flags).
13. License fields (4 fields).
14. Unavailable report (truthful; no stale/fake pass; no deltas; all
    method results unavailable; forbidden scan pass).
15. Public artifact self-scan is clean (clean + unavailable).
16. CLI argument surface (`--self-test`, `--row-limit`, `--methods`,
    `--query-mode`, `--language-filter`, `--openlocus`, `--out`).
17. Schema contract failure (`fail_schema_contract` status; no
    method_results; forbidden scan pass).
18. `ALLOWED_METHODS` exactly `bm25,regex,text,symbol`.

## Validation

```text
python3 -m py_compile eval/c5b_contextbench_verified_method_matrix_smoke.py  => PASS
python3 eval/c5b_contextbench_verified_method_matrix_smoke.py --self-test  => PASS (161/161 checks)
cargo build --locked --release -p openlocus-cli  => PASS
python3 eval/c5b_contextbench_verified_method_matrix_smoke.py \
  --row-limit 5 --methods bm25,regex,symbol \
  --query-mode first_paragraph --language-filter python \
  --openlocus target/release/openlocus \
  --out artifacts/c5b_contextbench_verified_method_matrix/\
c5b_contextbench_verified_method_matrix_report.json  => PASS
  (status: pass, forbidden_scan: pass, self_test_passed: true,
   mode: contextbench_verified_retrieval_method_matrix_smoke, phase: C5-B,
   methods: [bm25, regex, symbol], methods_attempted: 3,
   methods_successful: 3, methods_succeeded: 3, methods_failed: 0,
   rows_fetched: 5, network_calls: 1, provider_calls: 0,
   baseline_method: bm25, baseline_is_policy_candidate: false,
   default_should_change: false,
   external_benchmark_rows_read: true,
   repositories_materialized_transiently: true,
   openlocus_retrieval_executed: true,
   score_py_metrics_computed: true,
   method_matrix_smoke: true,
   aggregate_only_public_artifact: true,
   diagnostic_only: true,
   external_benchmark_performance_claimed: false,
   leaderboard_entry_claimed: false,
   downstream_agent_value_proven: false, promotion_ready: false,
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
python3 eval/c5b_contextbench_verified_method_matrix_smoke.py \
  --row-limit 5 --methods bm25,regex,symbol \
  --query-mode first_paragraph --language-filter python \
  --openlocus target/release/openlocus \
  --out artifacts/c5b_contextbench_verified_method_matrix/\
c5b_contextbench_verified_method_matrix_report.json
  => status: pass, forbidden_scan: pass, self_test_passed: true
  => rows_fetched: 5, methods: [bm25, regex, symbol]
  => methods_attempted: 3, methods_successful: 3, methods_succeeded: 3,
     methods_failed: 0
  => network_calls: 1, provider_calls: 0
  => baseline_method: bm25
  => external_benchmark_rows_read: true
  => repositories_materialized_transiently: true
  => openlocus_retrieval_executed: true
  => score_py_metrics_computed: true
  => method_matrix_smoke: true
```

The 5 ContextBench verified rows were fetched transiently ONCE from HF
datasets-server (shared across all 3 methods), adapted in-memory, the
referenced repositories were cloned at their `base_commit` under
transient `/tmp` directories, OpenLocus `bm25`, `regex`, and `symbol`
retrieval were run on each repository, and `eval/score.py` produced
aggregate retrieval metrics per method. Aggregate metric means (file
recall@10, MRR, span F0.5@10, success_rate) were computed across the 5
successful rows per method and written to the committed artifact as
per-method records. Aggregate-only deltas vs the fixed `bm25` baseline
were computed for `regex` and `symbol`. No raw ContextBench rows,
queries, repo URLs/names, base commits, gold paths/spans/contents,
generated task/label/run JSONL, evidence rows, cloned repos, or
stdout/stderr were committed or uploaded.

If the network smoke cannot complete in a future environment (network/
HF/GitHub failure, clone timeout, retrieval failure, score failure),
the artifact records truthful `unavailable_with_reason` with a real
`failure_reason_category` and the corresponding
`failure_category_counts` increment. No stale/fake pass is ever written.

## Caveats

- C5-B is the public aggregate-only external benchmark retrieval method
  matrix smoke artifact. It is eval/diagnostic only. It does NOT
  change runtime, retriever, pack, backend, or default policy; it does
  NOT change EvidenceCore semantics. It is NOT a benchmark result, NOT a
  leaderboard entry, NOT a performance claim, NOT a promotion, NOT a
  default change, NOT a runtime-clean general algorithm claim, NOT an
  OOD temporal claim, NOT a QuIVer systems claim, and NOT a downstream
  agent value claim.
- C5-B does NOT emit `winner`, `best_method`, `recommended_default`, or
  anything implying a policy/default decision. The fixed
  `baseline_method` is `bm25`, `baseline_is_policy_candidate=false`, and
  `default_should_change=false`.
- C5-B runs NO provider calls and NO remote provider calls. The only
  network calls are to the public HF datasets-server (to fetch bounded
  ContextBench verified rows ONCE, shared across methods) and to
  public GitHub (to clone the referenced repositories at their
  `base_commit` under transient `/tmp` directories per method).
  `provider_calls=0`, `provider_calls_made=false`,
  `remote_provider_calls_made=false`.
- C5-B uses a **bounded ContextBench verified subset** (default 5 rows;
  hard cap 10 rows; per method). This is a smoke, not a rigorous
  benchmark evaluation. The aggregate metrics are point estimates over a
  small sample and should NOT be interpreted as a benchmark result,
  leaderboard entry, performance claim, or method recommendation.
- C5-B materializes the referenced repositories at their `base_commit`
  under transient `/tmp` directories. The cloned repos, generated
  task/label/run JSONL, evidence rows, and stdout/stderr stay under
  `/tmp` only and are NEVER committed or uploaded. The committed
  artifact contains ONLY aggregate counts/rates/means and aggregate-only
  deltas.
- C5-B does NOT claim external benchmark performance. The aggregate
  metrics are smoke-level diagnostics, NOT a benchmark result.
  `external_benchmark_performance_claimed=false`.
- C5-B does NOT prove downstream agent value. The retrieval matrix smoke
  does not exercise any downstream agent.
  `downstream_agent_value_proven=false`.
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

- C5-B is the first external-benchmark-shaped retrieval method matrix
  smoke, extending C5-A's single-method smoke. The full C5
  external-benchmark-evaluation phase remains a bounded planning /
  feasibility stage that would require rigorous benchmark design,
  larger sample sizes, multiple methods, and statistical analysis.
- No promotion, no default change, no EvidenceCore semantics change, no
  runtime-clean general algorithm claim, no downstream agent value
  claim, no OOD temporal claim, and no QuIVer systems claim follows from
  C5-B.
