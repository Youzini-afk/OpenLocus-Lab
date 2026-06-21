# C5-E RepoQA Method-Matrix Retrieval Smoke

Date: 2026-06-21 (C5-E RepoQA bounded retrieval method-matrix smoke
over the EvalPlus RepoQA/SNF release asset
`repoqa-2024-06-23.json.gz`, extending C5-D single-method RepoQA
`bm25` smoke into a bounded multi-method matrix smoke over
`bm25,regex,symbol`)

C5-E is the **bounded multi-method matrix extension** of the C5-D
RepoQA retrieval performance smoke. It downloads the EvalPlus RepoQA
release asset `repoqa-2024-06-23.json.gz` from `evalplus/repoqa_release`
to in-memory bytes (transient; NEVER written to workspace), decompresses
it in memory, parses a bounded RepoQA Python needle subset, materializes
the referenced repositories at their `commit_sha` under transient `/tmp`
directories (once per method+needle), runs OpenLocus retrieval across
the requested method matrix (default `bm25,regex,symbol`; only
`bm25,regex,symbol` allowed; fixed `baseline_method=bm25`; no provider
calls), scores each method against `needle.path`/`start_line`/
`end_line` via the existing `eval/score.py` logic, and commits **only an
aggregate public report** with per-method aggregate metrics (records,
NOT dynamic method-key dicts), aggregate-only deltas vs the fixed
`bm25` baseline, and per-method `aggregate_runtime_seconds`.

C5-E is explicitly **not** a benchmark result, **not** a leaderboard
entry, **not** a performance claim, **not** a promotion, **not** a
default/policy change, and **not** a runtime/retriever/pack/backend/
EvidenceCore semantic change. It does NOT emit `winner`, `best_method`,
`recommended_default`, or anything implying a policy/default decision.

> **Important claim boundary.** C5-E emits `claim_level =
> repoqa_retrieval_method_matrix_smoke_only`. It does NOT claim an
> external benchmark result, NOT a leaderboard entry, NOT a performance
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

Extend C5-D from single-method RepoQA `bm25` to a bounded RepoQA method
matrix over `bm25,regex,symbol`. This is empirical external-benchmark-
shaped retrieval work: download the EvalPlus RepoQA release asset
transiently, parse Python needles in memory, transiently clone
referenced repositories, run OpenLocus retrieval per method, score with
`eval/score.py`, and publish only aggregate metrics.

## C5-A -> C5-B -> C5-C -> C5-D -> C5-E relation

```text
C5-A ContextBench verified retrieval performance smoke (single-method)
-> C5-B ContextBench verified method matrix smoke (5-row, 3 methods)
-> C5-C ContextBench verified method matrix scale smoke (20-row, 3 methods)
-> C5-D RepoQA BM25 retrieval performance smoke (single-method bm25)
-> C5-E RepoQA method-matrix retrieval smoke
   (multi-method matrix; bm25,regex,symbol only (no text);
    bounded 5-needle RepoQA Python subset per method;
    transient /tmp asset download + clone + retrieval + score;
    per-method aggregate records with aggregate_runtime_seconds;
    aggregate-only deltas vs bm25; aggregate-only public artifact;
    no provider calls; no winner/best_method/recommended_default;
    status pass enum repoqa_method_matrix_smoke_pass)
```

C5-E is NOT C5. The full C5 external-benchmark-evaluation phase remains
a bounded planning / feasibility stage. C5-E only produces the first
empirical RepoQA-shaped retrieval method matrix smoke by running a
bounded RepoQA Python needle subset through the real OpenLocus
retrieval + scoring pipeline across the requested method matrix.

## Implementation

### Evaluator

`eval/c5e_repoqa_method_matrix_smoke.py` exposes an argparse CLI:

- `--self-test` — no-network synthetic self-test (228 assertion checks).
- `--needle-limit` — number of RepoQA Python needles to evaluate per
  method; default 5, hard cap 10.
- `--methods` — comma-separated OpenLocus retrieval methods; default
  `bm25,regex,symbol`; only `bm25,regex,symbol` allowed (the `text`
  method is NOT allowed in C5-E); unknown methods are rejected;
  duplicates are deduplicated deterministically.
- `--language-filter` — language filter category; default `python`; only
  `python` allowed (C5-E does NOT silently fall back to all languages).
- `--openlocus` — optional OpenLocus binary path (default
  `target/release/openlocus` then `target/debug/openlocus` fallback;
  resolved to an absolute path).
- `--out` — output artifact JSON path; default
  `artifacts/c5e_repoqa_method_matrix_smoke/c5e_repoqa_method_matrix_smoke_report.json`.

Unknown/private-looking arguments are rejected with a generic `invalid
arguments` message that does not echo private paths or basenames
(`SafeArgumentParser` pattern).

### Runtime flow

1. Self-test must pass before any artifact is written.
2. Parse methods (raises `MethodConfigError` on invalid config; produces
   a `fail_schema_contract` report on failure).
3. Resolve OpenLocus binary to an absolute path. If missing, produce
   truthful `unavailable_with_reason` report.
4. Download the `repoqa-2024-06-23.json.gz` release asset to in-memory
   bytes (transient; NEVER written to workspace).
5. Decompress + parse the asset in memory.
6. Parse RepoQA needles in memory: filter by `language_filter=python`
   (NO silent all-language fallback).
7. For each method (`bm25,regex,symbol`), for each needle: clone repo
   at `commit_sha` under a per-method+needle `TemporaryDirectory`;
   generate transient task/label JSONL; run OpenLocus retrieval via
   `eval/run_retrieval.py`; run `eval/score.py`.
8. Aggregate metrics across successful needles per method.
9. Compute aggregate deltas vs the fixed `bm25` baseline.
10. Build aggregate-only public report with fail-closed forbidden scan.

### Public artifact identity

- `schema_version` = `c5e_repoqa_method_matrix_smoke.v1`
- `claim_level` = `repoqa_retrieval_method_matrix_smoke_only`
- `status`: `repoqa_method_matrix_smoke_pass` | `partial` |
  `unavailable_with_reason` | `fail_forbidden_scan` |
  `fail_schema_contract`
- `mode` = `repoqa_bounded_method_matrix_smoke`; `phase` = `C5-E`
- `benchmark` = `repoqa`; `dataset_release` = `repoqa-2024-06-23`
- `baseline_method` = `bm25`; `baseline_is_policy_candidate` = `false`
- Safe true flags: `repoqa_method_matrix_smoke_performed`,
  `asset_downloaded_transiently`, `repoqa_needles_parsed_in_memory`,
  `repositories_materialized_transiently`, `openlocus_retrieval_executed`,
  `score_py_metrics_computed`, `aggregate_only_public_artifact`,
  `diagnostic_only`.
- No-claim / no-runtime-change flags (all false): see claim boundary
  above.
- `method_results`: list of records (NOT dict keyed by method name)
  with `method`, `status`, `needles_evaluated`, `needles_successful`,
  `needles_failed`, `metrics` (allowlisted), `failure_category_counts`,
  `aggregate_runtime_seconds`.
- `smoke_metric_deltas_vs_baseline`: fixed records with
  `baseline_method=bm25`, `method`, `metric` (allowlisted), `delta`.
- License fields fixed: `dataset_license_status=unknown_dataset_license`,
  `row_level_redistribution_allowed=false`,
  `derived_row_level_publication_allowed=false`,
  `aggregate_metrics_publication=aggregate_only_smoke`.

### Aggregate metrics

Allowlisted metric names per method: `file_recall@10`, `mrr`,
`span_f0.5@10`, `success_rate`.

### Unavailable mode

If the network smoke cannot complete, the artifact records truthful
`unavailable_with_reason` with a real `failure_reason_category`. No
stale/fake pass. `method_results` is a list of per-method records each
with `status=unavailable_with_reason`, `metrics={}`, zero needle
counts; `smoke_metric_deltas_vs_baseline=[]`.

## Privacy / license boundary

The release asset is downloaded to in-memory bytes (transient; NEVER
written to workspace or committed). Raw repo records, repo names/URLs,
commit SHAs, entrypoint paths, topics, content, dependency, needle
names/descriptions/paths/start/end lines, generated task/label/run
JSONL, evidence rows, cloned repos, and stdout/stderr stay under `/tmp`
or in-memory only and are NEVER committed or uploaded.

RepoQA dataset license is unknown
(`unknown_dataset_license`); row-level redistribution is disabled and
derived row-level publication is disabled. Aggregate metrics
publication is allowed as aggregate-only smoke
(`aggregate_metrics_publication=aggregate_only_smoke`).

## Network / CI policy

- Default no-network self-test passes without GitHub/network.
- Real smoke requires public network access to GitHub (asset download +
  repo clones). CI is a separate explicit `workflow_dispatch` job with
  `enable_external_benchmark_network=true`. It does NOT run on PR/push
  by default, uses no provider secrets/vars, no provider model env,
  and uploads only the
  aggregate report.
- If `enable_external_benchmark_network` is false, the workflow is a
  no-op with a clear message and exits 0.
- Fail-closed like C5-C: network-enabled CI cannot pass with
  unavailable/no needles; require `status` in
  `(repoqa_method_matrix_smoke_pass, partial)`, `needles_seen > 0`,
  `methods_successful > 0`, `forbidden_scan.status=pass`.

## Forbidden scanner (public, fail-closed)

Reuses C5-D forbidden scanner primitives + C5-E-specific checks:
rejects `method_results` as dict keyed by method name; rejects
recommendation/policy fields (`winner`, `best_method`,
`recommended_default`, etc.) anywhere; rejects RepoQA-specific
forbidden keys (repo, commit_sha, entrypoint_path, topic, content,
dependency, needles, needle, needle_name, needle_path,
needle_description, start_line, end_line, start_byte, end_byte,
global_*, code_ratio, path, description, etc.) anywhere; rejects value
patterns (URLs, hex digests, commit SHAs, repo slugs, /tmp paths,
etc.).

## Self-tests

`--self-test` runs 228 deterministic checks across 20 groups (no
network; synthetic data).

## Validation

```text
python3 -m py_compile eval/c5e_repoqa_method_matrix_smoke.py  => PASS
python3 eval/c5e_repoqa_method_matrix_smoke.py --self-test  => PASS (228/228 checks)
python3 eval/c5e_repoqa_method_matrix_smoke.py \
  --needle-limit 5 --language-filter python --methods bm25,regex,symbol \
  --out artifacts/c5e_repoqa_method_matrix_smoke/\
c5e_repoqa_method_matrix_smoke_report.json  => PASS
  (status: repoqa_method_matrix_smoke_pass,
   forbidden_scan: pass, self_test_passed: true,
   mode: repoqa_bounded_method_matrix_smoke, phase: C5-E,
   methods: [bm25, regex, symbol], methods_successful: 3, methods_failed: 0,
   needles_seen: 5, network_calls: 1, provider_calls: 0,
   repoqa_method_matrix_smoke_performed: true,
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
python3 eval/c5e_repoqa_method_matrix_smoke.py \
  --needle-limit 5 --language-filter python --methods bm25,regex,symbol \
  --out artifacts/c5e_repoqa_method_matrix_smoke/\
c5e_repoqa_method_matrix_smoke_report.json
  => status: repoqa_method_matrix_smoke_pass,
     forbidden_scan: pass, self_test_passed: true
  => needles_seen: 5, methods_successful: 3, methods_failed: 0
  => network_calls: 1, provider_calls: 0
  => repoqa_method_matrix_smoke_performed: true
  => method_results:
     bm25: file_recall@10=0.6, mrr=0.46, span_f0.5@10=0.041634, success_rate=1.0, runtime=3.977s
     regex: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0, runtime=2.721s
     symbol: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0, runtime=7.076s
  => smoke_metric_deltas_vs_baseline: 8 records (regex×4 + symbol×4)
```

## Caveats

- C5-E is the public aggregate-only RepoQA retrieval method-matrix
  smoke artifact. It is eval/diagnostic only. It does NOT change
  runtime, retriever, pack, backend, or default policy; it does NOT
  change EvidenceCore semantics. It is NOT a benchmark result, NOT a
  leaderboard entry, NOT a performance claim, NOT a promotion, NOT a
  default change, NOT a runtime-clean general algorithm claim, NOT an
  OOD temporal claim, NOT a QuIVer systems claim, and NOT a downstream
  agent value claim.
- C5-E does NOT emit `winner`, `best_method`, `recommended_default`, or
  anything implying a policy/default decision.
- C5-E runs NO provider calls and NO remote provider calls.
- C5-E uses a **bounded RepoQA Python needle subset** (default 5 needles
  per method; hard cap 10). This is a smoke, not a rigorous benchmark.
- C5-E does NOT silently fall back from Python to all languages.
- All no-claim / no-runtime-change flags remain false; diagnostic flags
  remain true. No runtime/retriever/pack/model/backend/default-policy
  files were modified; no promotion/default/runtime claims change.
