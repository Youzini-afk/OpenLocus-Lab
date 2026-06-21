# C5-A ContextBench Verified Retrieval Performance Smoke

Date: 2026-06-21 (C5-A external benchmark retrieval performance smoke
over ContextBench verified subset)

C5-A is the **first external-benchmark-shaped retrieval performance
smoke** in the OpenLocus research track. It reads a bounded ContextBench
verified subset from the HuggingFace datasets-server, materializes the
referenced repository at `base_commit` under a transient `/tmp`
workspace, runs OpenLocus retrieval (initially `bm25`, no provider/model
calls), scores against ContextBench `gold_context` spans via the existing
`eval/score.py` logic, and commits **only an aggregate public report**.

C5-A is explicitly **not** a rigorous benchmark result, **not** a
leaderboard entry, **not** a performance claim, **not** a promotion,
**not** a default/policy change, and **not** a runtime/retriever/pack/
backend/EvidenceCore semantic change.

> **Important claim boundary.** C5-A emits `claim_level =
> external_benchmark_retrieval_performance_smoke_only`. It does NOT claim
> an external benchmark result, NOT a leaderboard entry, NOT a performance
> claim, NOT a promotion, NOT a default change, NOT a runtime/retriever/
> pack/backend change, NOT an EvidenceCore semantic change, and NOT a
> downstream agent value claim. All no-claim / no-runtime-change flags
> are false: `external_benchmark_performance_claimed=false`,
> `downstream_agent_value_proven=false`, `promotion_ready=false`,
> `default_should_change=false`, `runtime_behavior_changed=false`,
> `retriever_changed=false`, `pack_builder_changed=false`,
> `backend_changed=false`, `default_policy_changed=false`,
> `evidencecore_semantics_changed=false`, `provider_calls_made=false`,
> `remote_provider_calls_made=false`.

## Objective

Turn the C4 ContextBench readiness/row-mapping smoke into the first real
external benchmark retrieval performance smoke:

- read a bounded ContextBench verified subset from HuggingFace
  datasets-server `/rows` endpoint;
- keep raw ContextBench rows, queries/problem statements, repo URLs/
  names, base commits, gold paths/spans/contents, generated task/label/
  run JSONL, evidence rows, and cloned source repos **transient only**
  under `/tmp` or CI ephemeral workspace;
- materialize the referenced repository at `base_commit` via
  `git clone --filter=blob:none --no-checkout` then `git checkout`;
- run OpenLocus retrieval (initially `bm25`, no provider/model calls);
- score against ContextBench `gold_context` spans via existing
  `eval/score.py` logic;
- commit only an aggregate public report.

This is empirical performance smoke, not another readiness/control-plane
stage. It is also not a rigorous benchmark claim, promotion, default-
policy change, or downstream-agent value claim.

## D5-A0 -> B16-A -> C5-A relation

```text
D5-A0 automated E/S calibration smoke (retrieval-only aggregate)
-> B16-A minimal deterministic/mock downstream paired-agent empirical run
   (real edit/test loop; deterministic mock agent; paired control/treatment
    arms; synthetic public micro tasks; aggregate-only public artifact;
    no live LLM, no provider/remote calls, no downstream agent value claim)
-> C5-A ContextBench verified retrieval performance smoke
   (real external benchmark retrieval smoke; transient /tmp clone +
    retrieval + score; aggregate-only public artifact; no provider calls;
    no raw rows/queries/repo URLs/commits/gold paths/spans/JSONL/evidence
    rows/cloned repos/stdout/stderr committed)
```

C5-A is NOT C5. The full C5 external-benchmark-evaluation phase remains
a bounded planning / feasibility stage that would require rigorous
benchmark design, larger sample sizes, multiple methods, and statistical
analysis. C5-A only produces the first empirical external-benchmark-
shaped retrieval smoke by running a bounded ContextBench verified subset
through the real OpenLocus retrieval + scoring pipeline.

## Implementation

### Evaluator

`eval/c5_contextbench_verified_performance_smoke.py` exposes an argparse
CLI:

- `--self-test` — no-network synthetic self-test (113 assertion checks).
- `--row-limit` — number of ContextBench verified rows to evaluate;
  default 5, hard cap 20.
- `--method` — OpenLocus retrieval method; default `bm25`; allowed
  `bm25`, `regex`, `text`, `symbol` (no provider calls).
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
  `artifacts/c5_contextbench_verified_performance_smoke/c5_contextbench_verified_performance_smoke_report.json`.

Unknown/private-looking arguments are rejected with a generic `invalid
arguments` message that does not echo private paths or basenames
(`SafeArgumentParser` pattern).

### Runtime flow

1. Self-test must pass before any artifact is written
   (`_refuse_on_self_test_failure`).
2. Resolve OpenLocus binary to an absolute path (release then debug
   fallback). If missing, produce truthful `unavailable_with_reason`
   with `failure_reason_category=retrieval_failed`.
3. Fetch bounded ContextBench verified rows from HF datasets-server
   `/rows` endpoint (paginated; stdlib `urllib` only; bounded timeout).
   Filter in-memory by `language_filter` (categorical bucket only).
4. For each row (bounded to `row_limit`):
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
     (`--method bm25 --cwd <repo_root>`).
   - Run `eval/score.py` and parse aggregate metrics.
5. Aggregate metrics across successful rows (mean of each allowlisted
   numeric metric).
6. Build aggregate-only public report with fail-closed forbidden scan.

### Public artifact identity

The committed artifact at
`artifacts/c5_contextbench_verified_performance_smoke/c5_contextbench_verified_performance_smoke_report.json`
is the public aggregate-only smoke artifact. Identity / boundary fields:

- `schema_version` = `c5_contextbench_verified_performance_smoke.v1`
- `generated_by`, `generated_at`, `claim_level`, `status`, `mode`,
  `phase`
- `status`: `pass` | `partial` | `unavailable_with_reason` |
  `fail_schema_contract` | `fail_forbidden_scan`
- Safe true flags (true only if actually true):
  `external_benchmark_rows_read`, `repositories_materialized_transiently`,
  `openlocus_retrieval_executed`, `score_py_metrics_computed`,
  `performance_smoke`, `aggregate_only_public_artifact`,
  `diagnostic_only`.
- No-claim / no-runtime-change flags (all false):
  `external_benchmark_performance_claimed`,
  `downstream_agent_value_proven`, `promotion_ready`,
  `default_should_change`, `runtime_behavior_changed`,
  `retriever_changed`, `pack_builder_changed`, `backend_changed`,
  `default_policy_changed`, `evidencecore_semantics_changed`,
  `provider_calls_made`, `remote_provider_calls_made`.
- License fields (fixed):
  `dataset_license_status=unknown_dataset_license`,
  `row_level_redistribution_allowed=false`,
  `derived_row_level_publication_allowed=false`,
  `aggregate_metrics_publication=aggregate_only_smoke`.
- `method`, `query_mode`, `language_filter`, `network_mode`,
  `openlocus_binary_source`.
- `row_limit_requested`, `rows_fetched`, `rows_evaluated`,
  `rows_successful`, `rows_failed`, `network_calls`, `provider_calls=0`.
- `failure_reason_category` (only in `unavailable_with_reason` status).
- `failure_category_counts`: fixed enum categories only.
- `metrics`: aggregate metric means/rates/counts from `eval/score.py`,
  filtered to a fixed allowlist only (no dynamic row IDs or paths).
- `framing`: explicit `external_benchmark_performance_claimed=false`,
  `leaderboard_entry_claimed=false`, `promotion_claimed=false`, etc.
- `self_test_passed`.
- `forbidden_scan` summary (fail-closed before writing JSON).

### Aggregate metrics

The `metrics` block contains only allowlisted aggregate metric names
and numeric values from `eval/score.py`. No row-level records, no row
IDs, no paths, no spans, no snippets, no content_sha. Allowlisted
metric names:

- `total_tasks`, `successful`, `success_rate`, `avg_latency_ms`.
- `structural_validity`, `citation_validity`,
  `citation_hash_checked`, `citation_validation_mode`.
- `file_recall@1`, `file_recall@5`, `file_recall@10`,
  `file_precision@5`, `file_precision@10`, `mrr`.
- `line_precision@10`, `line_recall@10`, `span_f0.5@10`.
- `token_waste_ratio@10`, `wrong_span_rate@10`,
  `zero_overlap_evidence_rate@10`.

The `failure_category_counts` block contains only fixed enum category
labels (never row-level values):

- `network_fetch_failed`, `row_parse_failed`,
  `gold_context_parse_failed`, `language_filter_excluded`,
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
- `metrics={}` (no metrics).
- `performance_smoke=false`.
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
- repo URLs, repo names, base commits, repo paths;
- file paths, spans, line ranges, snippets, gold content;
- problem statements / queries (sanitized in-memory only);
- patches, test patches, f2p, p2p;
- generated task/label/run JSONL (transient `/tmp` only);
- OpenLocus evidence rows, snippets, paths, line ranges, content_sha;
- cloned repos/source files (transient `/tmp` only);
- raw command stdout/stderr or stack traces.

The public artifact records only: aggregate metric means/rates/counts
from `eval/score.py` (allowlisted), fixed failure-category counts, fixed
config labels (method, query_mode, language_filter categories only),
row counts, network/provider call counts, and the deterministic
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
- Real performance smoke requires public network access to HF
  datasets-server and GitHub repos. CI is a separate explicit
  `workflow_dispatch` job with `enable_external_benchmark_network=true`
  input. It does NOT run on PR/push by default, uses no provider
  secrets/vars, no `OPENLOCUS` provider env, and uploads only the
  aggregate temp report.
- If `enable_external_benchmark_network` is false, the workflow is a
  no-op with a clear message and exits 0 (self-test + py_compile still
  run; no aggregate report is produced in no-op mode).
- The workflow validates the report's claim boundary flags after the
  smoke: `aggregate_only_public_artifact=true`, `diagnostic_only=true`;
  all no-claim / no-runtime-change flags false; license fields fixed;
  `provider_calls=0`; `forbidden_scan.status=pass`;
  `self_test_passed=true`; `status` in `(pass, partial,
  unavailable_with_reason)` (no stale/fake pass; no
  `fail_schema_contract` / `fail_forbidden_scan`).

## Forbidden scanner (public, fail-closed)

A strict forbidden-output scanner runs fail-closed before writing the
public JSON. Modeled on the B16-A scanner (no contract containers with
field-name tokens; no over-broad container exemption). Rejects forbidden
dict keys (`path`, `span`, `file`, `repo`, `repo_url`, `base_commit`,
`instance_id`, `problem_statement`, `gold_context`, `gold_paths`,
`gold_lines`, `query`, `content_sha`, `snippet`, `patch`, `diff`,
`stdout`, `stderr`, `event_log`, `stack_trace`, `api_key`, `base_url`,
`provider_key`, `secret`, `token`, `credential`, `rows`, `per_run`,
`predictions`, `candidates`, `evidence`, etc.) anywhere, and rejects
value patterns: ANY URL (no URL allowlist — repo URLs must NEVER leak),
32+ char hex digests, 40-char commit SHAs, repo slugs like
`astropy/astropy`, secret-like strings, path-like strings with file
extensions, `/tmp/` workspace path values, `task_N` task-identifier
values, patch/diff markers (`---`, `+++`, `@@`), stack traces
(`Traceback (most recent call last)`), multiline strings, raw JSON
fragments, raw line ranges `12-34`, and the self-test sentinel.

The `failure_category_counts` and `metrics` containers are
schema-key containers whose CHILD KEYS are fixed category labels or
allowlisted metric names (NOT row-level values); the forbidden_key
check is relaxed for those child keys, but the values under them are
still scanned (they must be ints/floats/short strings only).

The scanner runs ONLY against the final public aggregate artifact.
Internal task/label/run JSONL (which contain paths/spans/queries/gold)
are kept in-memory/transient under `/tmp` only, never scanned against
the public contract, and never committed.

## Self-tests

`--self-test` runs 113 deterministic checks across 15 groups (no
network; synthetic rows + synthetic score data):

1. Artifact identity fields (schema, claim, status, mode, phase,
   generated_by).
2. Safe true flags present + correct values (7 flags).
3. No-claim / no-runtime-change false flags (12 flags).
4. License fields (4 fields).
5. Forbidden scanner rejects (25 injection patterns: repo URL, repo
   slug, commit SHA, repo key, repo_url key, base_commit key,
   instance_id key, problem_statement key, gold_context key,
   gold_paths key, gold_lines key, query key, path key, file path
   value, line range value, hex digest value, secret-like value,
   /tmp path value, task_id value, patch marker value, stack trace
   value, sentinel value, multiline value, raw JSON fragment, long
   string, forbidden field name as value).
6. Forbidden scanner allows safe values (method, query_mode,
   language_filter, network_mode, metric value, failure category count).
7. Query sanitizer (first_paragraph / first_sentence / raw; HTML comment
   / code fence / markdown header stripping; length caps; query never
   in public artifact).
8. Gold context parser (extracts paths/lines; rejects invalid JSON /
   missing file / inverted range; gold_paths / gold_lines never in
   public artifact).
9. Score metric allowlist (excludes row_id / path / content_sha;
   includes mrr / file_recall).
10. Failure category counts fixed enum (in-enum keys pass; non-enum
    keys rejected by builder).
11. Row limit cap (default 5; hard cap 20).
12. Unavailable report (truthful; no stale/fake pass; no metrics;
    forbidden scan pass).
13. Fail-closed generation (clean report no raise; leaked report
    raises; self-test failure refuses artifact generation).
14. Public artifact self-scan is clean (skeleton + unavailable).
15. CLI argument surface (`--self-test`, `--row-limit`, `--method`,
    `--query-mode`, `--language-filter`, `--openlocus`, `--out`).

## Validation

```text
python3 -m py_compile eval/c5_contextbench_verified_performance_smoke.py  => PASS
python3 eval/c5_contextbench_verified_performance_smoke.py --self-test  => PASS (113/113 checks)
python3 eval/c5_contextbench_verified_performance_smoke.py \
  --row-limit 5 --method bm25 --query-mode first_paragraph \
  --language-filter python \
  --out artifacts/c5_contextbench_verified_performance_smoke/\
c5_contextbench_verified_performance_smoke_report.json  => PASS
  (status: pass, forbidden_scan: pass, self_test_passed: true,
   mode: contextbench_verified_retrieval_performance_smoke, phase: C5-A,
   method: bm25, query_mode: first_paragraph, language_filter: python,
   rows_fetched: 5, rows_evaluated: 5, rows_successful: 5, rows_failed: 0,
   network_calls: 1, provider_calls: 0,
   external_benchmark_rows_read: true,
   repositories_materialized_transiently: true,
   openlocus_retrieval_executed: true,
   score_py_metrics_computed: true,
   performance_smoke: true,
   aggregate_only_public_artifact: true,
   diagnostic_only: true,
   external_benchmark_performance_claimed: false,
   downstream_agent_value_proven: false,
   promotion_ready: false, default_should_change: false,
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
python3 eval/c5_contextbench_verified_performance_smoke.py \
  --row-limit 5 --method bm25 --query-mode first_paragraph \
  --language-filter python \
  --out artifacts/c5_contextbench_verified_performance_smoke/\
c5_contextbench_verified_performance_smoke_report.json
  => status: pass, forbidden_scan: pass, self_test_passed: true
  => rows_fetched: 5, rows_evaluated: 5, rows_successful: 5, rows_failed: 0
  => network_calls: 1, provider_calls: 0
  => external_benchmark_rows_read: true
  => repositories_materialized_transiently: true
  => openlocus_retrieval_executed: true
  => score_py_metrics_computed: true
  => performance_smoke: true
```

The 5 ContextBench verified rows were fetched transiently from HF
datasets-server, adapted in-memory, the referenced repositories were
cloned at their `base_commit` under transient `/tmp` directories,
OpenLocus `bm25` retrieval was run on each repository, and
`eval/score.py` produced aggregate retrieval metrics. Aggregate metric
means (file recall, MRR, span/line metrics, zero-overlap,
structural/citation validity) were computed across the 5 successful rows
and written to the committed artifact. No raw ContextBench rows,
queries, repo URLs/names, base commits, gold paths/spans/contents,
generated task/label/run JSONL, evidence rows, cloned repos, or
stdout/stderr were committed or uploaded.

If the network smoke cannot complete in a future environment (network/
HF/GitHub failure, clone timeout, retrieval failure, score failure),
the artifact records truthful `unavailable_with_reason` with a real
`failure_reason_category` and the corresponding
`failure_category_counts` increment. No stale/fake pass is ever written.

## Caveats

- C5-A is the public aggregate-only external benchmark retrieval
  performance smoke artifact. It is eval/diagnostic only. It does NOT
  change runtime, retriever, pack, backend, or default policy; it does
  NOT change EvidenceCore semantics. It is NOT a benchmark result, NOT
  a leaderboard entry, NOT a performance claim, NOT a promotion, NOT a
  default change, NOT a runtime-clean general algorithm claim, NOT an
  OOD temporal claim, NOT a QuIVer systems claim, and NOT a downstream
  agent value claim.
- C5-A runs NO provider calls and NO remote provider calls. The only
  network calls are to the public HF datasets-server (to fetch bounded
  ContextBench verified rows) and to public GitHub (to clone the
  referenced repositories at their `base_commit` under transient `/tmp`
  directories). `provider_calls=0`, `provider_calls_made=false`,
  `remote_provider_calls_made=false`.
- C5-A uses a **bounded ContextBench verified subset** (default 5 rows;
  hard cap 20 rows). This is a smoke, not a rigorous benchmark
  evaluation. The aggregate metrics are point estimates over a small
  sample and should NOT be interpreted as a benchmark result, leaderboard
  entry, or performance claim.
- C5-A materializes the referenced repositories at their `base_commit`
  under transient `/tmp` directories. The cloned repos, generated
  task/label/run JSONL, evidence rows, and stdout/stderr stay under
  `/tmp` only and are NEVER committed or uploaded. The committed
  artifact contains ONLY aggregate counts/rates/means.
- C5-A does NOT claim external benchmark performance. The aggregate
  metrics are smoke-level diagnostics, NOT a benchmark result.
  `external_benchmark_performance_claimed=false`.
- C5-A does NOT prove downstream agent value. The retrieval smoke does
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

- C5-A is the first external-benchmark-shaped retrieval performance
  smoke. The full C5 external-benchmark-evaluation phase remains a
  bounded planning / feasibility stage that would require rigorous
  benchmark design, larger sample sizes, multiple methods, and
  statistical analysis.
- No promotion, no default change, no EvidenceCore semantics change, no
  runtime-clean general algorithm claim, no downstream agent value
  claim, no OOD temporal claim, and no QuIVer systems claim follows from
  C5-A.
