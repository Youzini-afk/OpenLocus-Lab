# C5-D RepoQA BM25 Retrieval Performance Smoke

Date: 2026-06-21 (C5-D RepoQA bounded retrieval performance smoke over
the EvalPlus RepoQA/SNF release asset `repoqa-2024-06-23.json.gz`)

C5-D is the **first RepoQA-shaped retrieval performance smoke** in the
OpenLocus research track. It downloads the EvalPlus RepoQA release
asset `repoqa-2024-06-23.json.gz` from `evalplus/repoqa_release` to
`/tmp` only, decompresses it in memory, parses a bounded Python needle
subset, clones the referenced repositories at their `commit_sha` under
transient `/tmp` directories, runs OpenLocus `bm25` retrieval (no
provider/model calls), scores against needle path/line ranges via the
existing `eval/score.py` logic, and commits **only an aggregate public
report**.

C5-D is explicitly **not** a benchmark result, **not** a leaderboard
entry, **not** a performance claim, **not** a promotion, **not** a
default/policy change, and **not** a runtime/retriever/pack/backend/
EvidenceCore semantic change. It does NOT emit `winner`,
`best_method`, `recommended_default`, or anything implying a policy/
default decision.

> **Important claim boundary.** C5-D emits `claim_level =
> repoqa_retrieval_performance_smoke_only`. It does NOT claim an external
> benchmark result, NOT a leaderboard entry, NOT a performance claim, NOT
> a promotion, NOT a default change, NOT a runtime/retriever/pack/backend
> change, NOT an EvidenceCore semantic change, and NOT a downstream agent
> value claim. All no-claim / no-runtime-change flags are false:
> `external_benchmark_performance_claimed=false`,
> `leaderboard_entry_claimed=false`,
> `downstream_agent_value_proven=false`, `promotion_ready=false`,
> `default_should_change=false`, `runtime_behavior_changed=false`,
> `retriever_changed=false`, `pack_builder_changed=false`,
> `backend_changed=false`, `default_policy_changed=false`,
> `evidencecore_semantics_changed=false`, `provider_calls_made=false`,
> `remote_provider_calls_made=false`.

## Objective

Run the first real RepoQA retrieval performance smoke without creating
another readiness-only stage. Use the known EvalPlus RepoQA release
asset, parse a small bounded Python needle set in memory, clone
referenced repos transiently, run OpenLocus `bm25`, score against needle
path/line ranges with `eval/score.py`, and publish only aggregate
metrics.

### Why RepoQA, not SWE-Explore

- SWE-Explore C4.3 row-map smoke found no usable line-budget/retrieval
  label shape in preview rows: no line-level labels, no file maps, no
  line ranges.
- SWE-Explore also lacks a natural query and public clone URL in the
  observed preview shape, and its license boundary is more restrictive.
- RepoQA has a known release asset and natural retrieval structure:
  `needle.description` is the query, `needle.path` + start/end lines are
  the gold target.

## C5-A -> C5-B -> C5-C -> C5-D relation

```text
C5-A ContextBench verified retrieval performance smoke
  (single-method; bm25 default; bounded 5-row ContextBench verified
   subset; transient /tmp clone + retrieval + score; aggregate-only
   public artifact; no provider calls)
-> C5-B ContextBench verified retrieval method matrix smoke
   (multi-method matrix; default bm25,regex,symbol; 5-row per method;
    fixed baseline_method=bm25; per-method aggregate records;
    aggregate-only deltas vs bm25; aggregate-only public artifact;
    no provider calls; no winner/best_method/recommended_default)
-> C5-C ContextBench verified retrieval method matrix scale smoke
   (multi-method matrix; bm25,regex,symbol only; bounded 20-row per
    method; per-method aggregate records with optional
    aggregate_runtime_seconds; input_summary block; aggregate-only
    public artifact; no provider calls; no winner/best_method/
    recommended_default; status pass enum
    contextbench_method_matrix_scale_smoke_pass)
-> C5-D RepoQA BM25 retrieval performance smoke
   (single-method bm25 only; bounded 5-needle RepoQA Python subset;
    transient /tmp asset download + clone + retrieval + score;
    aggregate-only public artifact; no provider calls; no
    winner/best_method/recommended_default; status pass enum
    repoqa_retrieval_smoke_pass)
```

C5-D is NOT C5. The full C5 external-benchmark-evaluation phase
remains a bounded planning / feasibility stage that would require
rigorous benchmark design, larger sample sizes, multiple methods, and
statistical analysis. C5-D only produces the first empirical RepoQA-
shaped retrieval smoke by running a bounded RepoQA Python needle subset
through the real OpenLocus retrieval + scoring pipeline.

## Implementation

### Evaluator

`eval/c5d_repoqa_bm25_retrieval_smoke.py` exposes an argparse CLI:

- `--self-test` — no-network synthetic self-test (219 assertion checks).
- `--needle-limit` — number of RepoQA Python needles to evaluate;
  default 5, hard cap 10.
- `--language-filter` — language filter category; default `python`;
  only `python` allowed (C5-D does NOT silently fall back to all
  languages).
- `--method` — OpenLocus retrieval method; default `bm25`; only `bm25`
  allowed.
- `--openlocus` — optional OpenLocus binary path (default
  `target/release/openlocus` then `target/debug/openlocus` fallback;
  resolved to an absolute path because `run_retrieval.py` runs with
  `--cwd <repo_root>`).
- `--out` — output artifact JSON path; default
  `artifacts/c5d_repoqa_bm25_retrieval_smoke/c5d_repoqa_bm25_retrieval_smoke_report.json`.

Unknown/private-looking arguments are rejected with a generic `invalid
arguments` message that does not echo private paths or basenames
(`SafeArgumentParser` pattern).

### Runtime flow

1. Self-test must pass before any artifact is written
   (`_refuse_on_self_test_failure`).
2. Resolve OpenLocus binary to an absolute path (release then debug
   fallback). If missing, produce truthful
   `unavailable_repo_clone_failed` report.
3. Download the `repoqa-2024-06-23.json.gz` release asset to in-memory
   bytes (transient; NEVER written to the workspace or committed).
4. Decompress + parse the asset in memory (transient; NEVER written to
   the workspace or committed).
5. Parse RepoQA needles in memory: filter by `language_filter=python`
   (categorical bucket only; NO silent all-language fallback); each
   needle is a transient in-memory dict with `repo_url`, `commit_sha`,
   `needle_path`, `needle_start_line`, `needle_end_line`,
   `needle_description`. If zero Python needles are found, status is
   `unavailable_no_python_needles`.
6. For each needle (bounded to `needle_limit`):
   - Sanitize `needle_description` into a retrieval query (in-memory
     only; extract the `Purpose` section's first sentence; strip
     markdown bold/italic; cap length).
   - Clone `repo_url` at `commit_sha` under a per-needle
     `TemporaryDirectory` via `git clone --filter=blob:none
     --no-checkout` then `git checkout` (bounded timeouts).
   - Generate transient task/label JSONL under a `TemporaryDirectory`.
   - Run OpenLocus retrieval via `eval/run_retrieval.py`
     (`--method bm25 --cwd <repo_root>`).
   - Run `eval/score.py` and parse aggregate metrics.
7. Aggregate metrics across successful needles (mean of each allowlisted
   numeric metric).
8. Build aggregate-only public report with fail-closed forbidden scan.

### Public artifact identity

The committed artifact at
`artifacts/c5d_repoqa_bm25_retrieval_smoke/c5d_repoqa_bm25_retrieval_smoke_report.json`
is the public aggregate-only smoke artifact. Identity / boundary fields:

- `schema_version` = `c5d_repoqa_retrieval_performance_smoke.v1`
- `generated_by`, `generated_at`, `claim_level`, `status`, `mode`,
  `phase`
- `benchmark` = `repoqa`
- `dataset_release` = `repoqa-2024-06-23`
- `language_filter` = `python`
- `method` = `bm25`
- `query_mode` = `needle_description`
- `gold_target_mode` = `needle_path_line_range`
- `status`: `repoqa_retrieval_smoke_pass` | `partial` |
  `unavailable_asset_download_failed` |
  `unavailable_no_python_needles` |
  `unavailable_repo_clone_failed` | `fail_forbidden_scan` |
  `fail_schema_contract`
- Safe true flags (true only if actually true):
  `repoqa_retrieval_smoke_performed`, `asset_downloaded_transiently`,
  `repoqa_needles_parsed_in_memory`,
  `repositories_materialized_transiently`,
  `openlocus_retrieval_executed`, `score_py_metrics_computed`,
  `aggregate_only_public_artifact`, `diagnostic_only`.
- No-claim / no-runtime-change flags (all false):
  `external_benchmark_performance_claimed`,
  `leaderboard_entry_claimed`, `downstream_agent_value_proven`,
  `promotion_ready`, `default_should_change`,
  `runtime_behavior_changed`, `retriever_changed`,
  `pack_builder_changed`, `backend_changed`,
  `default_policy_changed`, `evidencecore_semantics_changed`,
  `provider_calls_made`, `remote_provider_calls_made`.
- License fields (fixed):
  `dataset_license_status=unknown_dataset_license`,
  `row_level_redistribution_allowed=false`,
  `derived_row_level_publication_allowed=false`,
  `aggregate_metrics_publication=aggregate_only_smoke`.
- `needle_limit_requested`, `needles_seen`, `needles_evaluated`,
  `needles_successful`, `needles_failed`, `network_calls`,
  `provider_calls=0`, `aggregate_runtime_seconds`.
- `aggregate_metrics`: only allowlisted metric names (`file_recall@10`,
  `mrr`, `span_f0.5@10`, `success_rate`).
- `failure_category_counts`: fixed enum categories only.
- `failure_reason_category` (only in unavailable statuses).
- `framing`: explicit `external_benchmark_performance_claimed=false`,
  `leaderboard_entry_claimed=false`, `promotion_claimed=false`, etc.
- `self_test_passed`.
- `forbidden_scan` summary (fail-closed before writing JSON).

### Aggregate metrics

The `aggregate_metrics` block contains only allowlisted aggregate metric
names and numeric values from `eval/score.py`. No row-level records, no
needle IDs, no repo names, no commit SHAs, no paths, no spans, no
snippets, no content_sha. Allowlisted metric names:

- `file_recall@10`, `mrr`, `span_f0.5@10`, `success_rate`.

The `failure_category_counts` block contains only fixed enum category
labels (never row-level values):

- `asset_download_failed`, `asset_decompress_failed`,
  `asset_parse_failed`, `no_python_needles`,
  `needle_parse_failed`, `language_filter_excluded`,
  `repo_clone_failed`, `repo_checkout_failed`,
  `task_jsonl_write_failed`, `label_jsonl_write_failed`,
  `retrieval_failed`, `score_failed`, `needle_limit_capped`,
  `scanner_self_test_failed`, `forbidden_leak_blocked`,
  `unexpected_exception`.

### Unavailable statuses

If the network smoke cannot complete (asset download failure,
decompress failure, parse failure, no Python needles, repo clone
failure, retrieval failure, score failure, etc.), the artifact records
truthful `unavailable_*` with a real `failure_reason_category` and the
corresponding `failure_category_counts` increment. No stale/fake pass is
ever written. The unavailable statuses are:

- `unavailable_asset_download_failed`: asset download or decompress or
  parse failed.
- `unavailable_no_python_needles`: zero Python needles found (NO silent
  all-language fallback).
- `unavailable_repo_clone_failed`: repo clone/checkout or retrieval or
  score failed.

In unavailable mode, `aggregate_metrics={}`,
`repoqa_retrieval_smoke_performed=false`,
`aggregate_only_public_artifact=true` and `diagnostic_only=true` remain
true.

## Privacy / license boundary

Public artifacts and docs remain aggregate-only. The following were
NOT persisted in any public artifact or doc:

- the `repoqa-2024-06-23.json.gz` release asset (downloaded to `/tmp`
  only, decompressed in memory, NEVER committed or uploaded);
- raw repo records, repo names/URLs, commit SHAs, entrypoint paths,
  topics, content, dependency, functions;
- needle names, descriptions, paths, start/end lines, start/end bytes,
  global_* fields, code_ratio;
- generated task/label/run JSONL (transient `/tmp` only);
- OpenLocus evidence rows, snippets, paths, line ranges, content_sha;
- cloned repos/source files (transient `/tmp` only);
- raw command stdout/stderr or stack traces;
- per-needle metrics or per-needle failure records;
- needle IDs / row IDs / hashes of row-level values.

The public artifact records only: aggregate metric means/rates/counts
from `eval/score.py` (allowlisted), fixed failure-category counts, fixed
config labels (`benchmark`, `dataset_release`, `language_filter`,
`method`, `query_mode`, `gold_target_mode`), needle counts, network/
provider call counts, and the deterministic `generated_by` path.

RepoQA dataset license is unknown
(`unknown_dataset_license`); row-level redistribution is disabled
(`row_level_redistribution_allowed=false`) and derived row-level
publication is disabled
(`derived_row_level_publication_allowed=false`). Aggregate metrics
publication is allowed as aggregate-only smoke
(`aggregate_metrics_publication=aggregate_only_smoke`).

## Network / CI policy

- Default no-network self-test passes without GitHub/network.
- Real smoke requires public network access to GitHub (asset download +
  repo clones). CI is a separate explicit `workflow_dispatch` job with
  `enable_external_benchmark_network=true` input. It does NOT run on
  PR/push by default, uses no provider secrets/vars, no provider model
  env, and uploads only the aggregate temp report.
- If `enable_external_benchmark_network` is false, the workflow is a
  no-op with a clear message and exits 0 (self-test + py_compile still
  run; no aggregate report is produced in no-op mode).
- The workflow validates the report's claim boundary flags after the
  smoke (fail-closed like C5-C: network-enabled CI cannot pass with
  unavailable/no needles): `aggregate_only_public_artifact=true`,
  `diagnostic_only=true`; all no-claim / no-runtime-change flags false;
  license fields fixed; `provider_calls=0`;
  `forbidden_scan.status=pass`; `self_test_passed=true`; `status` in
  `(repoqa_retrieval_smoke_pass, partial)`; `needles_seen > 0`;
  `needles_successful > 0`.

## Forbidden scanner (public, fail-closed)

A strict forbidden-output scanner runs fail-closed before writing the
public JSON. Reuses C5-A forbidden scanner primitives for raw key/value
leak detection, and ADDS C5-D-specific checks:

- Rejects RepoQA-specific forbidden dict keys (`repo`, `commit_sha`,
  `entrypoint_path`, `topic`, `content`, `dependency`, `needles`,
  `needle`, `needle_name`, `needle_path`, `needle_description`,
  `needle_id`, `name`, `start_line`, `end_line`, `start_byte`,
  `end_byte`, `global_start_line`, `global_end_line`,
  `global_start_byte`, `global_end_byte`, `code_ratio`, `path`,
  `description`, `row`, `repo_name`, `repo_slug`, `repo_url`,
  `base_commit`, `instance_id`, `task_id`, `query`, `query_text`,
  `problem_statement`, `gold`, `gold_path`, `gold_span`, `gold_snippet`,
  `gold_paths`, `gold_lines`, `gold_context`, `snippet`, `snippets`,
  `content_sha`, `stdout`, `stderr`, `stdout_text`, `stderr_text`,
  `evidence`, `evidence_row`, `evidence_rows`, `retrieved_path`,
  `retrieved_paths`, `retrieved_snippet`, `cloned_repo_path`,
  `cloned_repo`, `per_row_metrics`, `row_metrics`,
  `per_needle_metrics`, `needle_metrics`, `patch`, `diff`, etc.)
  anywhere.
- Rejects recommendation / policy fields anywhere: `winner`,
  `best_method`, `recommended_default`, `recommended_method`,
  `preferred_method`, `default_method`, `policy_decision`, `decision`,
  `ranking`, `rank`.
- Rejects value patterns: ANY URL (no URL allowlist — repo URLs must
  NEVER leak), 32+ char hex digests, 40-char commit SHAs, repo slugs
  like `psf/black`, secret-like strings, path-like strings with file
  extensions, `/tmp/` workspace path values, `task_N`/`needle_N`
  task-identifier values, patch/diff markers (`---`, `+++`, `@@`),
  stack traces, multiline strings, raw JSON fragments, raw line
  ranges `585-639`, and the self-test sentinel.

The `failure_category_counts` and `aggregate_metrics` containers are
schema-key containers whose CHILD KEYS are fixed category labels or
allowlisted metric names (NOT row-level values); the forbidden_key
check is relaxed for those child keys, but the values under them are
still scanned (they must be ints/floats/short strings only).

The scanner runs ONLY against the final public aggregate artifact.
Internal task/label/run JSONL (which contain paths/spans/queries/gold)
are kept in-memory/transient under `/tmp` only, never scanned against
the public contract, and never committed.

## Self-tests

`--self-test` runs 219 deterministic checks across 23 groups (no
network; synthetic gzip fixture + synthetic score data):

1. Artifact identity fields (schema, claim, status, mode, phase,
   generated_by, benchmark, dataset_release, query_mode,
   gold_target_mode; status pass when self-test passed).
2. Safe true flags present + correct values (8 flags).
3. No-claim / no-runtime-change false flags (13 flags).
4. License fields (4 fields).
5. Needle limit hard cap 10 (default 5; cap 10; passes through at 5;
   rejects 0).
6. Method allowlist (bm25 only).
7. Language filter (python only, no silent all-language fallback:
   parsing with python filter on an asset with no python needles
   returns `unavailable_no_python_needles`, NOT a fallback to all
   languages).
8. gzip JSON fixture parse in memory (pass; has python key).
9. Needle extraction validates fields (repo_url, commit_sha,
   needle_path, line range, description).
10. Malformed needles map to fixed failure categories (no repo, no
    commit_sha, no path, inverted range, no description).
11. Needle limit cap (15 needles capped at 10; below available no cap).
12. Query sanitizer (extracts Purpose; strips markdown bold; capped at
    300; fallback when no Purpose).
13. Score metric allowlist (excludes row_id/path/content_sha/
    avg_latency_ms; includes file_recall/mrr; allowlist subset of
    C5-A).
14. Synthetic score aggregation (has file_recall/success_rate;
    success_rate recomputed; empty when no needles).
15. Failure category counts fixed enum (in-enum keys pass; non-enum
    keys rejected by builder).
16. Unavailable statuses (asset_download_failed, no_python_needles,
    repo_clone_failed; each has correct status enum, no smoke flag, no
    metrics, no perf claim, scan pass).
17. Scanner rejects forbidden content (60+ forbidden keys including
    RepoQA-specific repo/commit_sha/entrypoint_path/topic/content/
    dependency/needles/needle/needle_name/needle_path/
    needle_description/start_line/end_line/start_byte/end_byte/
    global_*/code_ratio/path/description; 10 recommendation fields;
    repo URL value; repo slug value; commit SHA value; file path
    value; line range value; hex digest value; /tmp path value;
    multiline value; raw JSON fragment).
18. Scanner allows safe values (benchmark, dataset_release, method,
    language_filter, query_mode, gold_target_mode, network_mode,
    aggregate_metrics, failure_category_count).
19. Fail-closed generation (clean report no raise; leaked repo raises;
    best_method raises; winner raises; recommended_default raises;
    commit_sha raises; needle_description raises; self-test failure
    refuses artifact generation).
20. Public artifact self-scan is clean (skeleton + unavailable).
21. CLI argument surface (`--self-test`, `--needle-limit`,
    `--language-filter`, `--method`, `--openlocus`, `--out`).
22. Aggregate runtime seconds present (pass report has numeric;
    unavailable has null).
23. No winner/best_method/recommended_default anywhere (10 fields).

## Validation

```text
python3 -m py_compile eval/c5d_repoqa_bm25_retrieval_smoke.py  => PASS
python3 eval/c5d_repoqa_bm25_retrieval_smoke.py --self-test  => PASS (219/219 checks)
python3 eval/c5d_repoqa_bm25_retrieval_smoke.py \
  --needle-limit 5 --language-filter python --method bm25 \
  --out artifacts/c5d_repoqa_bm25_retrieval_smoke/\
c5d_repoqa_bm25_retrieval_smoke_report.json  => PASS
  (status: repoqa_retrieval_smoke_pass,
   forbidden_scan: pass, self_test_passed: true,
   mode: repoqa_bounded_bm25_retrieval_smoke, phase: C5-D,
   method: bm25, language_filter: python,
   query_mode: needle_description, gold_target_mode: needle_path_line_range,
   needles_seen: 5, needles_evaluated: 5, needles_successful: 5, needles_failed: 0,
   network_calls: 1, provider_calls: 0,
   repoqa_retrieval_smoke_performed: true,
   asset_downloaded_transiently: true,
   repoqa_needles_parsed_in_memory: true,
   repositories_materialized_transiently: true,
   openlocus_retrieval_executed: true,
   score_py_metrics_computed: true,
   aggregate_only_public_artifact: true,
   diagnostic_only: true,
   external_benchmark_performance_claimed: false,
   leaderboard_entry_claimed: false,
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

Manual CI run `27906775008` (`c5-repoqa-bm25-retrieval-smoke`,
`enable_external_benchmark_network=true`, `needle_limit=5`,
`language_filter=python`, `method=bm25`) completed successfully. The
committed artifact now mirrors that sanitized aggregate CI report. The
workflow validator was fail-closed: network-enabled CI required
`repoqa_retrieval_smoke_pass` or `partial`, `needles_seen > 0`,
`needles_successful > 0`, and `forbidden_scan.status=pass` before upload.

```text
python3 eval/c5d_repoqa_bm25_retrieval_smoke.py \
  --needle-limit 5 --language-filter python --method bm25 \
  --out artifacts/c5d_repoqa_bm25_retrieval_smoke/\
c5d_repoqa_bm25_retrieval_smoke_report.json
  => status: repoqa_retrieval_smoke_pass,
     forbidden_scan: pass, self_test_passed: true
  => needles_seen: 5, needles_evaluated: 5, needles_successful: 5, needles_failed: 0
  => network_calls: 1, provider_calls: 0
  => repoqa_retrieval_smoke_performed: true
  => asset_downloaded_transiently: true
  => repoqa_needles_parsed_in_memory: true
  => repositories_materialized_transiently: true
  => openlocus_retrieval_executed: true
  => score_py_metrics_computed: true
  => aggregate_metrics: file_recall@10=0.6, mrr=0.46,
     span_f0.5@10=0.041634, success_rate=1.0
  => aggregate_runtime_seconds: 4.025
```

The `repoqa-2024-06-23.json.gz` release asset was downloaded to
in-memory bytes (transient; NEVER written to the workspace), the 5
RepoQA Python needles were parsed in memory, the referenced
repositories were cloned at their `commit_sha` under transient `/tmp`
directories, OpenLocus `bm25` retrieval was run on each repository,
and `eval/score.py` produced aggregate retrieval metrics. Aggregate
metric means were computed across the 5 successful needles and written
to the committed artifact. No raw repo records, repo names/URLs, commit
SHAs, entrypoint paths, topics, content, dependency, needle names/
descriptions/paths/start/end lines, generated task/label/run JSONL,
evidence rows, cloned repos, or stdout/stderr were committed or
uploaded.

If the network smoke cannot complete in a future environment (asset
download failure, decompress failure, parse failure, no Python needles,
repo clone failure, retrieval failure, score failure), the artifact
records truthful `unavailable_*` with a real `failure_reason_category`
and the corresponding `failure_category_counts` increment. No stale/fake
pass is ever written.

## Caveats

- C5-D is the public aggregate-only RepoQA BM25 retrieval performance
  smoke artifact. It is eval/diagnostic only. It does NOT change
  runtime, retriever, pack, backend, or default policy; it does NOT
  change EvidenceCore semantics. It is NOT a benchmark result, NOT a
  leaderboard entry, NOT a performance claim, NOT a promotion, NOT a
  default change, NOT a runtime-clean general algorithm claim, NOT an
  OOD temporal claim, NOT a QuIVer systems claim, and NOT a downstream
  agent value claim.
- C5-D does NOT emit `winner`, `best_method`, `recommended_default`, or
  anything implying a policy/default decision.
- C5-D runs NO provider calls and NO remote provider calls. The only
  network calls are to public GitHub (to download the
  `repoqa-2024-06-23.json.gz` release asset and to clone the referenced
  repositories at their `commit_sha` under transient `/tmp` directories).
  `provider_calls=0`, `provider_calls_made=false`,
  `remote_provider_calls_made=false`.
- C5-D uses a **bounded RepoQA Python needle subset** (default 5
  needles; hard cap 10). This is a smoke, not a rigorous benchmark
  evaluation. The aggregate metrics are point estimates over a bounded
  sample and should NOT be interpreted as a benchmark result,
  leaderboard entry, or performance claim.
- C5-D downloads the `repoqa-2024-06-23.json.gz` release asset to
  in-memory bytes (transient; NEVER written to the workspace or
  committed) and decompresses it in memory. The cloned repos, generated
  task/label/run JSONL, evidence rows, and stdout/stderr stay under
  `/tmp` only and are NEVER committed or uploaded. The committed
  artifact contains ONLY aggregate counts/rates/means.
- C5-D does NOT silently fall back from Python to all languages. If
  `language_filter=python` and zero Python needles are found, the
  artifact is truthful `unavailable_no_python_needles`.
- C5-D does NOT claim external benchmark performance. The aggregate
  metrics are smoke-level diagnostics, NOT a benchmark result.
  `external_benchmark_performance_claimed=false`.
- C5-D does NOT prove downstream agent value. The retrieval smoke does
  not exercise any downstream agent. `downstream_agent_value_proven=false`.
- RepoQA dataset license is unknown
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

- C5-D is the first RepoQA-shaped retrieval performance smoke. The full
  C5 external-benchmark-evaluation phase remains a bounded planning /
  feasibility stage that would require rigorous benchmark design, larger
  sample sizes, multiple methods, and statistical analysis.
- No promotion, no default change, no EvidenceCore semantics change, no
  runtime-clean general algorithm claim, no downstream agent value
  claim, no OOD temporal claim, and no QuIVer systems claim follows from
  C5-D.
