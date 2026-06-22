# BEA-0 Budgeted Evidence Acquisition v0

Date: 2026-06-21 (BEA-0 budgeted evidence acquisition v0 over fresh bounded
ContextBench verified Python rows + RepoQA Python needles, with private
per-record SCORE JSONL traces in `/tmp` and aggregate-only public artifact)

BEA-0 is the **first real algorithmic retrieval/acquisition experiment** in
the OpenLocus research track that pairs a deterministic budgeted acquisition
policy with private per-record SCORE JSONL traces and publishes only
aggregate baseline-vs-treatment delta_records. It reruns fresh retrieval over bounded
real ContextBench verified Python rows + RepoQA Python needles, collects
multi-method candidates (`bm25`/`regex`/`symbol`, optional `rrf`), runs the
deterministic `bea_v0_budgeted` policy under an evidence budget, and computes
per-arm aggregate retrieval/acquisition metrics with baseline-vs-treatment
delta_records vs `bm25_top10` (and `rrf_bm25_regex_symbol_top10` when rrf is
enabled).

BEA-0 is explicitly **not** a benchmark result, **not** a leaderboard entry,
**not** a performance claim, **not** a method-winner claim, **not** a
calibration claim, **not** a promotion, **not** a default/policy change, and
**not** a runtime/retriever/pack/backend/EvidenceCore semantic change. It does
NOT emit `winner`, `best_method`, `recommended_default`, `method_winner`, or
anything implying a policy/default decision.

> **Important claim boundary.** BEA-0 emits `claim_level =
> bea_v0_budgeted_acquisition_smoke_only`. It does NOT claim an external
> benchmark result, NOT a leaderboard entry, NOT a performance claim, NOT a
> method-winner claim, NOT a calibration claim, NOT a promotion, NOT a
> default change, NOT a runtime/retriever/pack/backend change, NOT an
> EvidenceCore semantic change, and NOT a downstream agent value claim. All
> no-claim / no-runtime-change flags are false:
> `external_benchmark_performance_claimed=false`,
> `leaderboard_entry_claimed=false`,
> `downstream_agent_value_proven=false`, `calibration_claimed=false`,
> `method_winner_claimed=false`, `promotion_ready=false`,
> `default_should_change=false`, `runtime_behavior_changed=false`,
> `retriever_changed=false`, `pack_builder_changed=false`,
> `backend_changed=false`, `default_policy_changed=false`,
> `evidencecore_semantics_changed=false`, `provider_calls_made=false`,
> `remote_provider_calls_made=false`.

## Objective

Pivot from readiness/control-plane/aggregate-validation work to a real
algorithmic retrieval/acquisition experiment with private per-record SCORE
traces. BEA-0 implements and runs a deterministic budgeted acquisition policy
over fresh external benchmark data, preserves private per-record SCORE JSONL
in `/tmp` (never committed, never uploaded), and publishes only aggregate
baseline-vs-treatment delta_records.

### Why this is a real acquisition experiment, not aggregate validation

- Reruns fresh multi-method retrieval (`bm25`/`regex`/`symbol` + optional
  `rrf`) over fresh ContextBench verified Python rows + RepoQA Python
  needles via `eval/run_retrieval.py:run_query()`.
- Builds a per-record candidate list (method source, rank, score, normalized
  score, path, span, content_sha, extension).
- Runs a deterministic `bea_v0_budgeted` policy that consumes ONLY
  runtime-clean candidate features (no gold labels, no row IDs, no benchmark
  labels, no previous outcomes, no provider/model names, no private route
  buckets) and produces an action trace + accepted/final candidate list
  under an evidence budget.
- Computes per-arm metric records using `eval/score.py` functions on synthetic
  in-memory prediction records (one per arm per record).
- Writes a private per-record SCORE JSONL row to `/tmp` (or an explicitly
  ignored private path) with full per-record detail.
- Publishes only aggregate per-arm metric records + baseline-vs-treatment delta_records.

## C3 -> BEA-0 relation

```text
C3 Budgeted Evidence Acquisition v0 (replay-only)
  (replay-only policy experiment over the C1 private-records adapter;
   selects among precomputed P21 per-strategy outcomes; no fresh
   retrieval; no acquisition loop; diagnostic-rank-only; no winner)
-> BEA-0 Budgeted Evidence Acquisition v0 (real acquisition loop)
   (real algorithmic retrieval/acquisition experiment; reruns fresh
    multi-method retrieval over bounded real ContextBench verified Python
    rows + RepoQA Python needles; deterministic bea_v0_budgeted policy
    with action trace + budget states; private per-record SCORE JSONL
    in /tmp; aggregate-only public artifact with baseline-vs-treatment
    delta_records; no provider calls; no winner/method_winner/default/calibration
    claim)
```

BEA-0 is NOT C3. C3 was replay-only and selected among precomputed P21
outcomes; BEA-0 actually reruns retrieval and acquires evidence under a
budget, with private per-record SCORE traces.

## Implementation

### Evaluator

`eval/bea0_budgeted_evidence_acquisition.py` exposes an argparse CLI:

- `--self-test` — no-network synthetic self-test (212 assertion checks).
- `--contextbench-row-limit` — number of ContextBench verified Python rows
  to evaluate; default 10, hard cap 20.
- `--repoqa-needle-limit` — number of RepoQA Python needles to evaluate;
  default 5, hard cap 10.
- `--budget` — evidence budget for the `bea_v0_budgeted` policy; default
  10, hard cap 20.
- `--methods` — comma-separated retrieval methods; default
  `bm25,regex,symbol`; allowed `bm25,regex,symbol`; `bm25` is required
  (the treatment's primary rank feature).
- `--enable-rrf-baseline` — optional flag to enable the
  `rrf_bm25_regex_symbol_top10` baseline arm (default disabled; do not
  block on rrf).
- `--enable-external-benchmark-network` — allow real HuggingFace + GitHub
  network access for ContextBench row fetch + RepoQA asset download +
  repo clones (default false; no provider secrets/vars).
- `--openlocus` — optional OpenLocus binary path (default
  `target/release/openlocus` then `target/debug/openlocus` fallback;
  resolved to an absolute path because `run_retrieval.py` runs with
  `--cwd <repo_root>`).
- `--out` — output artifact JSON path; default
  `artifacts/bea0_budgeted_evidence_acquisition/bea0_budgeted_evidence_acquisition_report.json`.
- `--private-score-dir` — explicit private SCORE JSONL directory (default
  fresh `/tmp/bea0_private_score_<pid>_<ts>`; must be under `/tmp` or the
  gitignored `runs/` directory).

Unknown/private-looking arguments are rejected with a generic `invalid
arguments` message that does not echo private paths or basenames
(`SafeArgumentParser` pattern).

### BEA v0 budgeted policy (runtime-clean, deterministic)

The treatment policy `bea_v0_budgeted` consumes ONLY runtime-clean
candidate features available before scoring:

- method source (`bm25` / `regex` / `symbol`);
- candidate rank within method;
- score or normalized score if available (normalized within each method's
  evidence list: max score -> 1.0);
- rank agreement across methods (how many distinct methods returned the
  same `(path, start_line, end_line)` span);
- duplicate path/span overlap (within and across methods);
- candidate count;
- accepted file/path coverage so far;
- budget remaining;
- cheap path kind/file extension metadata.

It MUST NOT use gold files/lines/labels, row IDs, benchmark-specific answer
hints, previous outcome on the same record, provider/model names, or private
route buckets. The evaluator verifies routing invariance: candidate policies
produce IDENTICAL accepted/action_trace/budget_states when synthetic
gold/label/row-id/model-family/previous-outcome fields are added to the
candidate list (because the policy ignores them).

Algorithm:

1. Compute per-span agreement: how many distinct methods returned the same
   `(path, start_line, end_line)` span. Build a per-span summary with max
   normalized_score, min rank, agreement count, method set.
2. Sort the deduplicated span list by:
   (a) agreement count DESC (multi-method agreement first);
   (b) min rank across methods ASC (lower rank = earlier in any method);
   (c) max normalized_score DESC (higher score wins ties).
3. Iterate the sorted list with a budget of `budget` accepted candidates.
   For each candidate:
   - If budget exhausted: emit `stop_budget_exhausted` and break.
   - If span has `agreement==1` AND `min_rank>5` AND
     `max_norm_score<0.01`: emit `skip_low_support` (skip without
     accepting).
   - If span has `agreement>=2` AND path already in `accepted_paths`:
     emit `rerank_by_agreement` and defer (push to a deferred pool).
   - Else: emit `accept_candidate` and append to accepted; mark path.
4. After the main pass, if budget remains, process deferred
   `rerank_by_agreement` candidates as `expand_same_file` actions
   (retain an additional same-file candidate under budget).

Initial actions: `accept_candidate`, `skip_low_support`,
`rerank_by_agreement`, `stop_budget_exhausted`. Optional if easy:
`expand_same_file` (retain an additional same-file candidate under budget).

### Runtime flow

1. Self-test must pass before any artifact is written
   (`_refuse_on_self_test_failure`).
2. Resolve OpenLocus binary to an absolute path (release then debug
   fallback). If missing, produce truthful `unavailable_with_reason`
   report.
3. Resolve private SCORE JSONL directory (fresh `/tmp/bea0_private_score_*`
   by default; explicit `--private-score-dir` must be under `/tmp` or the
   gitignored `runs/` directory).
4. If `--enable-external-benchmark-network` is false, write a truthful
   `unavailable_with_reason` report with
   `failure_reason_category=contextbench_fetch_failed` and exit 0
   (self-test + py_compile still run; no aggregate report is produced in
   no-op mode beyond the unavailable artifact).
5. ContextBench arm: fetch bounded Python rows from HF datasets-server
   `/rows` (default 10 rows; hard cap 20; stdlib `urllib` only). For each
   row: parse `gold_context` (transient), sanitize `problem_statement`
   into a retrieval query (transient), clone repo at `base_commit` under
   a per-row `TemporaryDirectory`, run multi-method retrieval via
   `eval/run_retrieval.py:run_query()`, run baselines + treatment,
   compute per-arm metric records, write private SCORE row to `/tmp`.
6. RepoQA arm: download `repoqa-2024-06-23.json.gz` to in-memory bytes
   (transient), decompress in memory, parse bounded Python needles
   (default 5; hard cap 10; NO silent all-language fallback). For each
   needle: sanitize `needle_description` (transient), clone repo at
   `commit_sha` under a per-needle `TemporaryDirectory`, run multi-method
   retrieval, run baselines + treatment, compute per-arm metric records, write
   private SCORE row to `/tmp`.
7. Aggregate per-arm metric records across successful records (mean of each
   allowlisted numeric metric). Compute baseline-vs-treatment delta_records.
8. Build aggregate-only public report with fail-closed forbidden scan.
9. Fail-closed: `provider_calls` must be 0; private SCORE record count
   must match `records_successful` when network was enabled and at least
   one record succeeded; forbidden scan must pass.

### Public artifact identity

The committed artifact at
`artifacts/bea0_budgeted_evidence_acquisition/bea0_budgeted_evidence_acquisition_report.json`
is the public aggregate-only smoke artifact. Identity / boundary fields:

- `schema_version` = `bea0_budgeted_evidence_acquisition.v1`
- `generated_by`, `generated_at`, `claim_level`, `status`, `mode`, `phase`
- `methods` = list of retrieval methods used
- `budget` = evidence budget
- `enable_rrf_baseline` = bool
- `baseline_arms` = `[bm25_top10]` (or
  `[bm25_top10, rrf_bm25_regex_symbol_top10]` when rrf enabled)
- `treatment_arm` = `bea_v0_budgeted`
- `status`: `bea_v0_smoke_pass` | `partial` | `unavailable_with_reason` |
  `fail_forbidden_scan` | `fail_schema_contract`
- Safe true flags (true only if actually true):
  `bea_v0_acquisition_performed`, `multi_method_candidates_collected`,
  `budgeted_policy_executed`, `private_score_records_written`,
  `external_benchmark_rows_read`, `repositories_materialized_transiently`,
  `openlocus_retrieval_executed`, `score_py_metrics_computed`,
  `aggregate_only_public_artifact`, `diagnostic_only`.
- No-claim / no-runtime-change flags (all false):
  `external_benchmark_performance_claimed`,
  `leaderboard_entry_claimed`, `downstream_agent_value_proven`,
  `calibration_claimed`, `method_winner_claimed`, `promotion_ready`,
  `default_should_change`, `runtime_behavior_changed`, `retriever_changed`,
  `pack_builder_changed`, `backend_changed`, `default_policy_changed`,
  `evidencecore_semantics_changed`, `provider_calls_made`,
  `remote_provider_calls_made`.
- License fields (fixed):
  `dataset_license_status=unknown_dataset_license`,
  `row_level_redistribution_allowed=false`,
  `derived_row_level_publication_allowed=false`,
  `aggregate_metrics_publication=aggregate_only_smoke`.
- `contextbench_row_limit_requested`, `repoqa_needle_limit_requested`,
  `records_evaluated`, `records_successful`, `records_failed`,
  `network_calls`, `provider_calls=0`, `aggregate_runtime_seconds`.
- `arm_metric_records`: per-arm aggregate metrics, allowlisted only.
- `delta_records`: per-arm baseline-vs-treatment delta_records, allowlisted only.
- Private SCORE manifest (aggregate-only; no path serialized):
  `private_score_records_written` (true only if rows actually written),
  `private_score_record_count`, `private_score_schema_version`,
  `private_score_manifest_hash` (sha256 of the in-memory manifest schema,
  never of the row contents), `private_score_storage_class` (`tmp_private`
  or `ignored_private`), `private_score_path_publicly_serialized=false`.
- `failure_category_counts`: fixed enum categories only.
- `failure_reason_category` (only in unavailable status).
- `framing`: explicit `external_benchmark_performance_claimed=false`,
  `leaderboard_entry_claimed=false`, `promotion_claimed=false`,
  `calibration_claimed=false`, `method_winner_claimed=false`, etc.
- `self_test_passed`.
- `forbidden_scan` summary (fail-closed before writing JSON).

### Per-arm aggregate metrics

The `arm_metric_records` block contains one entry per arm
(`bm25_top10`, `bea_v0_budgeted`, optionally `rrf_bm25_regex_symbol_top10`).
Each entry has only allowlisted metric names:

- `file_recall@10`, `mrr`, `span_f0.5@10`, `success_rate` (from
  `eval/score.py` functions on synthetic in-memory prediction records).
- `candidate_count_read` (total candidates collected for the arm).
- `evidence_budget_used` (candidates actually retained by the arm).
- `action_steps` (action trace length; for baselines, equals evidence
  count).
- `latency_seconds` (per-record mean latency for the arm).
- `quality_per_candidate` (`span_f0.5@10 / candidate_count_read`).

### Baseline-vs-treatment delta_records

The `delta_records` block contains per-metric delta_records (treatment - baseline) for:

- `bea_v0_budgeted` vs `bm25_top10` (always present when treatment ran).
- `rrf_bm25_regex_symbol_top10` vs `bm25_top10` (only when rrf baseline
  enabled).

A valid outcome may be improvement, same quality with less budget, no-delta,
or quality loss with a causal action-trace failure mode. The artifact is
honest about whichever occurs.

### Unavailable statuses

If the network smoke cannot complete (ContextBench fetch failure, RepoQA
asset download failure, parse failure, no Python rows/needles, repo clone
failure, retrieval failure, private SCORE write failure, etc.), the artifact
records truthful `unavailable_with_reason` with a real
`failure_reason_category` and the corresponding `failure_category_counts`
increment. No stale/fake pass is ever written.

In unavailable mode, `arm_metric_records=[]`, `delta_records=[]`,
`bea_v0_acquisition_performed=false`, `aggregate_only_public_artifact=true`
and `diagnostic_only=true` remain true.

## Privacy / license boundary

Public artifacts and docs remain aggregate-only. The following were NOT
persisted in any public artifact or doc:

- the `repoqa-2024-06-23.json.gz` release asset (downloaded to `/tmp`
  only, decompressed in memory, NEVER committed or uploaded);
- raw ContextBench rows / RepoQA needles, queries/problem statements,
  repo URLs/names, base commits / commit SHAs, gold paths/spans/contents;
- generated task/label/run JSONL (transient `/tmp` only);
- OpenLocus evidence rows, snippets, paths, line ranges, content_sha;
- cloned repos/source files (transient `/tmp` only);
- raw command stdout/stderr or stack traces;
- per-record metrics or per-record failure records;
- row IDs / needle IDs / hashes of row-level values;
- private per-record SCORE JSONL rows (written ONLY under `/tmp` or an
  explicitly ignored private path; the private SCORE path is NEVER
  serialized in the public artifact, docs, or CI artifacts).

The public artifact records only: aggregate per-arm metric
means/rates/counts from `eval/score.py` + deterministic budgeted acquisition
policy accounting (allowlisted), baseline-vs-treatment delta_records (allowlisted),
fixed failure-category counts, fixed config labels (`methods`, `budget`,
`baseline_arms`, `treatment_arm`), record counts, network/provider call
counts, private SCORE manifest aggregate-only fields
(`private_score_records_written`, `private_score_record_count`,
`private_score_schema_version`, `private_score_manifest_hash`,
`private_score_storage_class`, `private_score_path_publicly_serialized=false`),
and the deterministic `generated_by` path.

ContextBench + RepoQA dataset licenses are unknown
(`unknown_dataset_license`); row-level redistribution is disabled
(`row_level_redistribution_allowed=false`) and derived row-level
publication is disabled
(`derived_row_level_publication_allowed=false`). Aggregate metrics
publication is allowed as aggregate-only smoke
(`aggregate_metrics_publication=aggregate_only_smoke`).

## Network / CI policy

- Default no-network self-test passes without HuggingFace/GitHub.
- Real acquisition requires public network access to HF datasets-server
  and GitHub (asset download + repo clones). CI is a separate explicit
  `workflow_dispatch` job with
  `enable_external_benchmark_network=true`. It does NOT run on PR/push
  by default, uses no provider secrets/vars, no provider model env, and
  uploads only the aggregate report. The private SCORE JSONL is NEVER
  uploaded.
- If `enable_external_benchmark_network` is false, the workflow is a
  no-op with a clear message and exits 0 (self-test + py_compile still
  run; an unavailable aggregate artifact is produced).
- The workflow validates the report's claim boundary flags after the
  smoke (fail-closed: network-enabled CI cannot pass with unavailable/no
  records; require status in (`bea_v0_smoke_pass`, `partial`),
  `records_successful > 0`, `forbidden_scan.status=pass`,
  `provider_calls=0`, `private_score_record_count == records_successful`,
  no `winner`/`best_method`/`recommended_default`/`method_winner`/`calibration`
  fields anywhere).

## Forbidden scanner (public, fail-closed)

A strict forbidden-output scanner runs fail-closed before writing the public
JSON. Reuses C5-A/C5-D forbidden scanner primitives for raw key/value leak
detection, and ADDS BEA-0-specific checks:

- Rejects BEA-0-specific forbidden dict keys (`private_score_path`,
  `score_path`, `private_score_file`, `private_record_id`,
  `private_record_hash`, `action_trace`, `action_steps_trace`,
  `budget_state`, `budget_states`, `accepted_candidates`,
  `final_candidates`, `candidate_list`, `candidates`, `score_outcome`,
  `per_record_metrics`, `runtime_query_features`,
  `query_feature_summary`, `query_features`, `benchmark_row_id`,
  `benchmark_record_id`, `benchmark_label`, `phase_run_id`, `run_id`,
  `task_id`, `row_id`, `needle_id`, `instance_id`, `provider_name`,
  `model_name`, `model_family`, `provider_payload`, `private_bucket`,
  `route_bucket`, `task_bucket`) anywhere.
- Rejects recommendation / policy fields anywhere: `winner`,
  `best_method`, `recommended_default`, `recommended_method`,
  `preferred_method`, `default_method`, `policy_decision`, `decision`,
  `ranking`, `rank`.
- Rejects value patterns: ANY URL (no URL allowlist — repo URLs must
  NEVER leak), 32+ char hex digests (except under safe value paths like
  `private_score_manifest_hash`), 40-char commit SHAs, repo slugs like
  `psf/black`, secret-like strings, path-like strings with file
  extensions, `/tmp/` workspace path values, `task_N`/`needle_N`
  task-identifier values, patch/diff markers (`---`, `+++`, `@@`),
  stack traces, multiline strings, raw JSON fragments, raw line ranges
  `585-639`, and the self-test sentinel.

The `failure_category_counts`, `aggregate_metrics`, `arm_metric_records`, and
`delta_records` containers are schema-key containers whose CHILD KEYS are fixed
category labels or allowlisted metric/arm names (NOT row-level values);
the forbidden_key check is relaxed for those child keys, but the values
under them are still scanned (they must be ints/floats/short strings
only).

The scanner runs ONLY against the final public aggregate artifact.
Internal task/label/run JSONL, the private SCORE JSONL, and the
per-record candidate lists / action traces / budget states / accepted
candidates (which contain paths/spans/queries/gold) are kept
in-memory/transient under `/tmp` only, never scanned against the public
contract, and never committed.

## Self-tests

`--self-test` runs 212 deterministic checks across 26 groups (no network;
synthetic candidates + synthetic gold record + synthetic metrics):

1. Artifact identity fields (schema, claim, status, mode, phase,
   generated_by, treatment_arm, baseline_arms).
2. Safe true flags present + correct values (10 flags).
3. No-claim / no-runtime-change false flags (15 flags).
4. License fields (4 fields).
5. Private SCORE manifest aggregate-only fields (records_written,
   record_count, schema_version, storage_class,
   path_not_publicly_serialized, manifest_hash is sha256 hex, 14
   forbidden private keys absent).
6. Row/needle limit hard caps (ContextBench default 10 / cap 20; RepoQA
   default 5 / cap 10; rejects 0).
7. Budget hard cap (default 10; cap 20; caps at 20; rejects 0).
8. Method validation (default; dedup preserves order; requires bm25;
   rejects dense; rejects empty).
9. Path extension helper (py, rs, none, lowercase).
10. BEA v0 budgeted policy mechanics (accepts nonempty; first accept is
    high-agreement; has accept_candidate action; skips low_support;
    budget states nonempty; budget_remaining decreasing).
11. Policy respects budget cap (budget=3, budget=1, budget=0, empty
    candidates).
12. Policy runtime-clean invariance (accepted list + action trace
    identical when synthetic gold/label/row-id/model-family/
    previous-outcome fields are added to candidates).
13. Per-arm metric records + delta_records (bm25 file_recall/mrr/success_rate = 1.0;
    empty evidence = 0; delta_records positive).
14. Aggregate means (file_recall=1.0; candidate_count_read=4; empty=0).
15. Arm metric allowlist filtering (excludes path/row_id/content_sha/arm;
    includes mrr).
16. Failure category counts fixed enum (in-enum keys pass; non-enum keys
    rejected by builder).
17. Unavailable report (status, failure_reason_category, no smoke flag,
    no perf claim, empty arm_metric_records/delta_records, no private_score_path,
    scan pass).
18. Scanner rejects forbidden content (BEA-0-specific forbidden keys;
    repo URL/slug/commit SHA/file path/tmp path/multiline values).
19. Scanner allows safe values (schema_version, methods, budget,
    arm_metric_records, delta_records, private_score_manifest_hash, failure_category).
20. Fail-closed generation (clean report no raise; private_score_path
    raises; action_trace raises; accepted_candidates raises; winner
    raises; best_method raises; self-test failure refuses artifact
    generation).
21. Public artifact self-scan is clean (skeleton + unavailable).
22. CLI argument surface (`--self-test`, `--contextbench-row-limit`,
    `--repoqa-needle-limit`, `--budget`, `--methods`, `--openlocus`,
    `--out`, `--private-score-dir`, `--enable-rrf-baseline`).
23. Private SCORE writer round-trip (two rows; parse as JSON;
    path-leak detected by scanner).
24. Arm metric allowlist subset (all 9 allowlisted keys present in
    filtered output).
25. Aggregate runtime seconds present (pass report has numeric;
    unavailable omits).
26. No winner/best_method/recommended_default/method_winner/calibration
    anywhere (5 fields).

## Validation

```text
python3 -m py_compile eval/bea0_budgeted_evidence_acquisition.py  => PASS
python3 eval/bea0_budgeted_evidence_acquisition.py --self-test  => PASS (212/212 checks)
python3 eval/bea0_budgeted_evidence_acquisition.py \
  --contextbench-row-limit 2 --repoqa-needle-limit 1 \
  --budget 5 --methods bm25,regex,symbol \
  --enable-rrf-baseline --enable-external-benchmark-network \
  --openlocus target/debug/openlocus \
  --out artifacts/bea0_budgeted_evidence_acquisition/\
bea0_budgeted_evidence_acquisition_report.json  => PASS
  (status: bea_v0_smoke_pass,
   forbidden_scan: pass, self_test_passed: true,
   mode: bea_v0_budgeted_acquisition, phase: BEA-0,
   methods: bm25,regex,symbol, budget: 5,
   enable_rrf_baseline: true,
   baseline_arms: [bm25_top10, rrf_bm25_regex_symbol_top10],
   treatment_arm: bea_v0_budgeted,
   records_evaluated: 3, records_successful: 3, records_failed: 0,
   network_calls: 2, provider_calls: 0,
   bea_v0_acquisition_performed: true,
   multi_method_candidates_collected: true,
   budgeted_policy_executed: true,
   private_score_records_written: true,
   private_score_record_count: 3,
   private_score_schema_version: bea0_private_score.v1,
   private_score_storage_class: tmp_private,
   private_score_path_publicly_serialized: false,
   external_benchmark_rows_read: true,
   repositories_materialized_transiently: true,
   openlocus_retrieval_executed: true,
   score_py_metrics_computed: true,
   aggregate_only_public_artifact: true,
   diagnostic_only: true,
   external_benchmark_performance_claimed: false,
   leaderboard_entry_claimed: false,
   downstream_agent_value_proven: false,
   calibration_claimed: false, method_winner_claimed: false,
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

## Real bounded local run result (2026-06-21)

Bounded local run with `--contextbench-row-limit 2
--repoqa-needle-limit 1 --budget 5 --methods bm25,regex,symbol
--enable-rrf-baseline --enable-external-benchmark-network
--openlocus target/debug/openlocus` completed successfully. The committed
artifact mirrors that sanitized aggregate report.

```text
python3 eval/bea0_budgeted_evidence_acquisition.py \
  --contextbench-row-limit 2 --repoqa-needle-limit 1 \
  --budget 5 --methods bm25,regex,symbol \
  --enable-rrf-baseline --enable-external-benchmark-network \
  --openlocus target/debug/openlocus
  => status: bea_v0_smoke_pass,
     forbidden_scan: pass, self_test_passed: true
  => records_evaluated: 3, records_successful: 3, records_failed: 0
  => network_calls: 2, provider_calls: 0
  => bea_v0_acquisition_performed: true
  => multi_method_candidates_collected: true
  => budgeted_policy_executed: true
  => private_score_records_written: true
  => private_score_record_count: 3
  => private_score_storage_class: tmp_private
  => private_score_path_publicly_serialized: false
  => arm_metric_records arm=bm25_top10:    file_recall@10=0.666667, mrr=0.666667,
     span_f0.5@10=0.059187, success_rate=0.666667,
     candidate_count_read=13.333333, evidence_budget_used=6.666667,
     action_steps=6.666667, latency_seconds=0.467,
     quality_per_candidate=0.002959
  => arm_metric_records arm=rrf_bm25_regex_symbol_top10:
     file_recall@10=0.666667, mrr=0.666667, span_f0.5@10=0.059187,
     success_rate=0.666667, candidate_count_read=13.333333,
     evidence_budget_used=6.666667, action_steps=6.666667,
     latency_seconds=1.219, quality_per_candidate=0.002959
  => arm_metric_records arm=bea_v0_budgeted: file_recall@10=0.666667,
     mrr=0.666667, span_f0.5@10=0.086849, success_rate=0.666667,
     candidate_count_read=13.333333, evidence_budget_used=3.333333,
     action_steps=4.0, latency_seconds=3.640497,
     quality_per_candidate=0.004343
  => delta_records treatment_arm=bea_v0_budgeted (vs bm25_top10):
     file_recall@10=0.0, mrr=0.0, span_f0.5@10=+0.027662,
     success_rate=0.0, evidence_budget_used=-3.333334,
     action_steps=-2.666667, quality_per_candidate=+0.001384,
     latency_seconds=+3.173497, candidate_count_read=0.0
  => aggregate_runtime_seconds: 19.641
```

The bounded local run reran fresh retrieval over 2 ContextBench verified
Python rows + 1 RepoQA Python needle, collected multi-method candidates
(bm25/regex/symbol) plus the optional rrf baseline, ran the deterministic
`bea_v0_budgeted` policy under budget=5, wrote 3 private per-record SCORE
JSONL rows to `/tmp/bea0_private_score_<pid>_<ts>/bea0.private.jsonl`
(transient; NEVER committed or uploaded), and committed only aggregate
per-arm metric records + baseline-vs-treatment delta_records. The treatment preserved
file_recall@10 / mrr / success_rate parity with `bm25_top10` and
`rrf_bm25_regex_symbol_top10` while using roughly half the evidence
budget (`evidence_budget_used=3.33` vs `6.67`) and improved
`span_f0.5@10` by `+0.028` and `quality_per_candidate` by `+0.0014`.
This is an honest smoke-level aggregate delta over a bounded sample, not a
benchmark result, leaderboard entry, performance claim, method-winner claim,
calibration claim, promotion, default change, runtime/retriever/pack/
backend/EvidenceCore semantic change, or downstream agent value claim.

If the network smoke cannot complete in a future environment (ContextBench
fetch failure, RepoQA asset download failure, parse failure, no Python
rows/needles, repo clone failure, retrieval failure, private SCORE write
failure), the artifact records truthful `unavailable_with_reason` with a
real `failure_reason_category` and the corresponding
`failure_category_counts` increment. No stale/fake pass is ever written.

## Caveats

- BEA-0 is the public aggregate-only budgeted evidence acquisition v0 smoke
  artifact. It is eval/diagnostic only. It does NOT change runtime,
  retriever, pack, backend, or default policy; it does NOT change
  EvidenceCore semantics. It is NOT a benchmark result, NOT a leaderboard
  entry, NOT a performance claim, NOT a method-winner claim, NOT a
  calibration claim, NOT a promotion, NOT a default change, NOT a
  runtime-clean general algorithm claim, and NOT a downstream agent value
  claim.
- BEA-0 does NOT emit `winner`, `best_method`, `recommended_default`,
  `method_winner`, `calibration`, or anything implying a policy/default
  decision.
- BEA-0 runs NO provider calls and NO remote provider calls. The only
  network calls are to public HuggingFace datasets-server and GitHub (to
  download the RepoQA release asset and to clone the referenced
  repositories at their commit SHA under transient `/tmp` directories).
  `provider_calls=0`, `provider_calls_made=false`,
  `remote_provider_calls_made=false`.
- BEA-0 uses a **bounded ContextBench verified Python subset** (default 10
  rows; hard cap 20) and a **bounded RepoQA Python needle subset**
  (default 5 needles; hard cap 10). This is a smoke, not a rigorous
  benchmark evaluation. The aggregate metrics are point estimates over a
  bounded sample and should NOT be interpreted as a benchmark result,
  leaderboard entry, performance claim, method-winner claim, or
  calibration.
- BEA-0 writes private per-record SCORE JSONL ONLY under `/tmp` (or an
  explicitly ignored private path under the gitignored `runs/` directory).
  The private SCORE path is NEVER serialized in the public artifact, docs,
  or CI artifacts. The public artifact records ONLY aggregate SCORE
  manifest fields (`private_score_records_written`,
  `private_score_record_count`, `private_score_schema_version`,
  `private_score_manifest_hash`, `private_score_storage_class`,
  `private_score_path_publicly_serialized=false`).
- BEA-0 does NOT silently fall back from Python to all languages. If
  `language_filter=python` and zero Python rows/needles are found, the
  artifact is truthful `unavailable_with_reason` with a real failure
  category.
- BEA-0 does NOT claim external benchmark performance. The aggregate
  metrics are smoke-level diagnostics, NOT a benchmark result.
  `external_benchmark_performance_claimed=false`.
- BEA-0 does NOT claim a method winner. The treatment is a deterministic
  budgeted acquisition policy with an honest baseline-vs-treatment
  delta; the delta may be positive, zero, or negative.
  `method_winner_claimed=false`.
- BEA-0 does NOT prove downstream agent value. The acquisition smoke does
  not exercise any downstream agent. `downstream_agent_value_proven=false`.
- ContextBench + RepoQA dataset licenses are unknown
  (`unknown_dataset_license`); row-level redistribution is disabled
  (`row_level_redistribution_allowed=false`) and derived row-level
  publication is disabled
  (`derived_row_level_publication_allowed=false`). Aggregate metrics
  publication is allowed as aggregate-only smoke
  (`aggregate_metrics_publication=aggregate_only_smoke`).
- All no-claim / no-runtime-change flags remain false; diagnostic flags
  (`aggregate_only_public_artifact`, `diagnostic_only`) remain true. No
  runtime/retriever/pack/model/backend/default-policy files were modified;
  no promotion/default/runtime claims change. EvidenceCore semantics are
  unchanged.

## Next steps

- BEA-0 is the first real algorithmic retrieval/acquisition experiment
  with private per-record SCORE traces. A full BEA-1 / BEA-2 phase would
  require larger sample sizes, multiple budget settings, statistical
  analysis, and richer policy features (e.g. score calibration, anchor
  agreement, span-overlap geometry).
- No promotion, no default change, no EvidenceCore semantics change, no
  runtime-clean general algorithm claim, no method-winner claim, no
  calibration claim, no downstream agent value claim follows from BEA-0.
