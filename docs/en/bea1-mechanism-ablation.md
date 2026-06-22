# BEA-1 Mechanism Ablation Smoke

Date: 2026-06-21 (BEA-1 mechanism ablation smoke over fresh bounded
ContextBench verified Python rows + RepoQA Python needles, with private
per-record SCORE JSONL traces in `/tmp` and aggregate-only public records)

BEA-1 is the **mechanism ablation** follow-up to BEA-0. It reruns fresh
bounded external ContextBench verified Python rows + RepoQA Python needles,
runs the BEA-0 ``bea_v0_budgeted`` policy plus three same-budget controls
(``same_budget_bm25_prefix``, ``agreement_only_same_budget``,
``seeded_random_same_budget``), and the existing baselines
(``bm25_top10``, ``rrf_bm25_regex_symbol_top10`` when enabled), on the same
records under a paired denominator rule. The public artifact is
records-shaped aggregate only: per-arm metric records, baseline-vs-treatment
delta records, mechanism contrast records, and aggregate private SCORE
manifest.

BEA-1 is explicitly **not** a benchmark result, **not** a leaderboard entry,
**not** a performance claim, **not** a method-winner claim, **not** a
calibration claim, **not** a promotion, **not** a default/policy change, and
**not** a runtime/retriever/pack/backend/EvidenceCore semantic change. It
does NOT emit `winner`, `best_method`, `recommended_default`,
`method_winner`, `calibration`, or anything implying a policy/default
decision.

> **Important claim boundary.** BEA-1 emits `claim_level =
> bea_v0_mechanism_ablation_smoke_only`. It does NOT claim an external
> benchmark result, NOT a leaderboard entry, NOT a performance claim, NOT
> a method-winner claim, NOT a calibration claim, NOT a promotion, NOT a
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

Turn BEA-0 into a small real mechanism ablation. Rerun bounded external
ContextBench + RepoQA retrieval, preserve private per-record SCORE JSONL
under `/tmp`, and compare BEA v0 against mechanism-specific controls on the
same records. Public output remains records-shaped aggregate only.

### Why this is a real mechanism ablation, not aggregate validation

- Reruns fresh multi-method retrieval (`bm25`/`regex`/`symbol` + optional
  `rrf`) over fresh ContextBench verified Python rows + RepoQA Python
  needles via `eval/run_retrieval.py:run_query()` (fresh external run; does
  NOT bootstrap the BEA-0 aggregate artifact).
- Runs 5 fixed arms (`bm25_top10`, `bea_v0_budgeted`,
  `same_budget_bm25_prefix`, `agreement_only_same_budget`,
  `seeded_random_same_budget`; `rrf_bm25_regex_symbol_top10` when rrf is
  enabled) on every record, plus mechanism contrasts on the paired
  denominator.
- Same-budget controls use `K = len(bea_v0_budgeted.accepted_candidates)`
  capped by available deduped candidates, so BEA-0 vs controls differ ONLY
  in the acquisition mechanism, not in budget.
- Writes a private per-record SCORE JSONL row to `/tmp` (or an explicitly
  ignored private path) with full per-record detail including same-budget
  control arm evidence and the per-record same-budget K.
- Publishes only aggregate per-arm metric records + baseline-vs-treatment
  delta records + mechanism contrast records + aggregate private SCORE
  manifest.

## BEA-0 -> BEA-1 relation

```text
BEA-0 Budgeted Evidence Acquisition v0 (single treatment)
  (real algorithmic retrieval/acquisition experiment; reruns fresh
   multi-method retrieval over bounded real ContextBench verified Python
   rows + RepoQA Python needles; deterministic bea_v0_budgeted policy
   with action trace + budget states; private per-record SCORE JSONL
   in /tmp; aggregate-only public artifact with baseline-vs-treatment
   deltas; no provider calls; no winner/method_winner/default/calibration
   claim)
-> BEA-1 Mechanism Ablation Smoke (mechanism contrasts)
   (real mechanism ablation; same fresh external run shape as BEA-0 but
    adds three same-budget controls: same_budget_bm25_prefix,
    agreement_only_same_budget, seeded_random_same_budget; paired
    denominator rule; mechanism contrast records; private per-record
    SCORE JSONL in /tmp with same-budget K + control arm evidence;
    records-shaped aggregate-only public artifact; no provider calls;
    no winner/method_winner/default/calibration claim)
```

BEA-1 is NOT BEA-0. BEA-0 measured BEA v0 vs `bm25_top10` (and
`rrf_bm25_regex_symbol_top10` when enabled); BEA-1 measures BEA v0 vs three
same-budget controls that isolate whether BEA-0's gains (if any) come from
multi-source agreement / sequential budgeted evidence acquisition rather
than merely reading fewer candidates.

## Implementation

### Evaluator

`eval/bea1_mechanism_ablation.py` exposes an argparse CLI:

- `--self-test` — no-network synthetic self-test (420 assertion checks).
- `--contextbench-row-limit` — number of ContextBench verified Python rows
  to evaluate; default 5, hard cap 20.
- `--repoqa-needle-limit` — number of RepoQA Python needles to evaluate;
  default 3, hard cap 10.
- `--budget` — evidence budget for the `bea_v0_budgeted` policy and
  same-budget controls; default 5, hard cap 20.
- `--methods` — comma-separated retrieval methods; default
  `bm25,regex,symbol`; allowed `bm25,regex,symbol`; `bm25` is required.
- `--enable-rrf-baseline` — optional flag to enable the
  `rrf_bm25_regex_symbol_top10` baseline arm (default disabled; do not
  block on rrf).
- `--enable-external-benchmark-network` — allow real HuggingFace + GitHub
  network access (default false; no provider secrets/vars).
- `--openlocus` — optional OpenLocus binary path (default
  `target/release/openlocus` then `target/debug/openlocus` fallback).
- `--out` — output artifact JSON path; default
  `artifacts/bea1_mechanism_ablation/bea1_mechanism_ablation_report.json`.
- `--private-score-dir` — explicit private SCORE JSONL directory (default
  fresh `/tmp/bea0_private_score_<pid>_<ts>`; must be under `/tmp` or the
  gitignored `runs/` directory).

Unknown/private-looking arguments are rejected with a generic `invalid
arguments` message (`SafeArgumentParser` pattern).

### Fixed arms (no dynamic arm names)

- `bm25_top10`: normal BM25 top-10 baseline; first 10 BM25 candidates after
  dedupe; no budget matching.
- `rrf_bm25_regex_symbol_top10`: multi-method RRF baseline when enabled;
  first 10 RRF candidates over bm25/regex/symbol after dedupe.
- `bea_v0_budgeted`: BEA-0 deterministic policy with runtime-clean features
  only; may accept/skip/rerank/stop and records private action trace only
  in SCORE.
- `same_budget_bm25_prefix`: first `K` BM25 candidates after dedupe; no
  agreement reranking, no BEA sequential coverage/defer/expand rules.
- `agreement_only_same_budget`: same deduped candidate universe as BEA;
  sort by agreement desc, min_rank asc, max_normalized_score desc, stable
  candidate order; take first `K`; no BEA sequential coverage/defer/expand
  rules.
- `seeded_random_same_budget`: deterministic PRNG with fixed public seed
  `20240621`; sample `K` from the same deduped candidate universe after
  stable ordering; no gold/labels/row IDs/provider/model fields in seed or
  ordering.

These arms answer whether BEA-0 gains come from multi-source agreement /
sequential budgeted evidence acquisition rather than merely reading fewer
candidates.

### Same-budget definition

Same-budget controls use a per-record candidate count `K` defined exactly
as:

```text
K = len(bea_v0_budgeted.accepted_candidates)
K = min(K, available_deduped_candidate_count)
```

If BEA accepts zero candidates for a record, same-budget controls also
select zero and the record is marked unusable for mechanism contrasts unless
all fixed arms have valid zero-candidate metrics. Public artifacts never
serialize accepted candidates or candidate lists; only aggregate arm/
contrast records are public.

### Paired denominator rule

Mechanism contrasts are paired. A contrast only includes records where both
baseline and treatment arms have valid metrics for the same record. If any
fixed mechanism arm fails for a record, either:

- exclude that record from every mechanism contrast and increment
  `paired_exclusion_count` (and the
  `record_excluded_from_paired_denominator` failure category); or
- mark the run `partial` if exclusions prevent the minimum paired count.

Every public `mechanism_contrast_records` row must include `record_count`
so deltas are interpretable. Public artifacts do not serialize per-record
inclusion masks.

### Runtime flow

1. Self-test must pass before any artifact is written
   (`_refuse_on_self_test_failure`).
2. Resolve OpenLocus binary to an absolute path (release then debug
   fallback). If missing, produce truthful `unavailable_with_reason` report.
3. Resolve private SCORE JSONL directory (fresh `/tmp/bea0_private_score_*`
   by default; explicit `--private-score-dir` must be under `/tmp` or the
   gitignored `runs/` directory).
4. If `--enable-external-benchmark-network` is false, write a truthful
   `unavailable_with_reason` report with
   `failure_reason_category=contextbench_fetch_failed` and exit 0
   (self-test + py_compile still run; an unavailable aggregate artifact is
   produced in no-op mode).
5. ContextBench arm: fetch bounded Python rows from HF datasets-server
   `/rows` (default 5 rows; hard cap 20). For each row: parse
   `gold_context` (transient), sanitize `problem_statement` (transient),
   clone repo at `base_commit` under a per-row `TemporaryDirectory`, run
   multi-method retrieval, run all fixed arms, compute per-arm metrics,
   write private SCORE row to `/tmp`.
6. RepoQA arm: download `repoqa-2024-06-23.json.gz` to in-memory bytes
   (transient), decompress in memory, parse bounded Python needles
   (default 3; hard cap 10; NO silent all-language fallback). For each
   needle: sanitize `needle_description` (transient), clone repo at
   `commit_sha` under a per-needle `TemporaryDirectory`, run multi-method
   retrieval, run all fixed arms, compute per-arm metrics, write private
   SCORE row to `/tmp`.
7. Aggregate per-arm metrics across successful records (mean of each
   allowlisted numeric metric). Compute baseline-vs-treatment deltas
   (each treatment arm vs the fixed `bm25_top10` baseline). Compute
   mechanism contrast records on the paired denominator (BEA v0 vs each
   same-budget control).
8. Build aggregate-only public report with fail-closed forbidden scan.
9. Fail-closed: `provider_calls` must be 0; private SCORE record count
   must match `records_successful` when network was enabled and at least
   one record succeeded; forbidden scan must pass.

### Public artifact identity

The committed artifact at
`artifacts/bea1_mechanism_ablation/bea1_mechanism_ablation_report.json`
is the public aggregate-only smoke artifact. Identity / boundary fields:

- `schema_version` = `bea1_mechanism_ablation.v1`
- `generated_by`, `generated_at`, `claim_level`, `status`, `mode`, `phase`
- `methods` = list of retrieval methods used
- `budget` = evidence budget
- `enable_rrf_baseline` = bool
- `fixed_arms` = list of fixed arm IDs (no dynamic arm names)
- `baseline_arm` = `bm25_top10` (fixed)
- `treatment_arm` = `bea_v0_budgeted` (fixed)
- `seeded_random_seed` = `20240621` (fixed public constant)
- `status`: `bea1_mechanism_ablation_pass` | `partial` |
  `unavailable_with_reason` | `fail_forbidden_scan` |
  `fail_schema_contract`
- Safe true flags (true only if actually true):
  `mechanism_ablation_performed`, `bea_v0_acquisition_performed`,
  `private_score_records_written`, `external_benchmark_rows_read`,
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
  `paired_exclusion_count`, `network_calls`, `provider_calls=0`,
  `aggregate_runtime_seconds`.
- `arm_metric_records`: list of fixed-shape `{arm, metric, value}` records
  (one per arm/metric).
- `delta_records`: list of fixed-shape
  `{baseline_arm, treatment_arm, metric, delta}` records (each treatment
  arm vs `bm25_top10`).
- `mechanism_contrast_records`: list of fixed-shape
  `{contrast, baseline_arm, treatment_arm, metric, delta, record_count}`
  records (BEA v0 vs each same-budget control on the paired denominator).
- `private_score_manifest`: aggregate-only manifest block with
  `records_written`, `record_count`, `schema_version`, `manifest_hash`,
  `storage_class`, `path_publicly_serialized=false`. The private SCORE
  path is NEVER serialized.
- `failure_category_counts`: fixed enum categories only.
- `failure_reason_category` (only in unavailable status).
- `framing`: explicit `external_benchmark_performance_claimed=false`,
  `leaderboard_entry_claimed=false`, `promotion_claimed=false`,
  `calibration_claimed=false`, `method_winner_claimed=false`, etc.
- `self_test_passed`.
- `forbidden_scan` summary (fail-closed before writing JSON).

### Per-arm metric records

The `arm_metric_records` block contains one fixed-shape record per arm/
metric: `{arm, metric, value}`. Allowed metrics: `file_recall@10`, `mrr`,
`span_f0.5@10`, `success_rate`, `candidate_count_read`,
`evidence_budget_used`, `action_steps`, `latency_seconds`,
`quality_per_candidate`. No dynamic arm dicts.

### Delta records

The `delta_records` block contains one fixed-shape record per treatment/
metric: `{baseline_arm, treatment_arm, metric, delta}`. Each treatment arm
(`bea_v0_budgeted`, `same_budget_bm25_prefix`,
`agreement_only_same_budget`, `seeded_random_same_budget`, and
`rrf_bm25_regex_symbol_top10` when enabled) is compared vs the fixed
`bm25_top10` baseline.

### Mechanism contrast records

The `mechanism_contrast_records` block contains fixed-shape records:
`{contrast, baseline_arm, treatment_arm, metric, delta, record_count}`.
Fixed contrast IDs:

- `bea_vs_same_budget_bm25`: `bea_v0_budgeted` vs
  `same_budget_bm25_prefix`.
- `bea_vs_agreement_only`: `bea_v0_budgeted` vs
  `agreement_only_same_budget`.
- `bea_vs_seeded_random`: `bea_v0_budgeted` vs
  `seeded_random_same_budget`.

A contrast only includes records where both arms have valid metrics for
the same record (paired denominator rule). Every record includes
`record_count` so deltas are interpretable.

### Unavailable statuses

If the network smoke cannot complete (ContextBench fetch failure, RepoQA
asset download failure, parse failure, no Python rows/needles, repo clone
failure, retrieval failure, private SCORE write failure, etc.), the
artifact records truthful `unavailable_with_reason` with a real
`failure_reason_category` and the corresponding `failure_category_counts`
increment. No stale/fake pass is ever written.

In unavailable mode, `arm_metric_records=[]`, `delta_records=[]`,
`mechanism_contrast_records=[]`,
`mechanism_ablation_performed=false`,
`aggregate_only_public_artifact=true` and `diagnostic_only=true` remain
true.

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
  serialized in the public artifact, docs, or CI artifacts);
- action traces, budget states, accepted candidates, final candidates,
  candidate lists, score outcomes (private per-record fields, kept
  transient under `/tmp` only).

The public artifact records only: aggregate per-arm metric records,
baseline-vs-treatment delta records, mechanism contrast records (with
`record_count`), aggregate private SCORE manifest (records_written,
record_count, schema_version, manifest_hash, storage_class,
path_publicly_serialized=false), fixed failure-category counts, fixed
config labels (`methods`, `budget`, `fixed_arms`, `baseline_arm`,
`treatment_arm`, `seeded_random_seed`), record counts, paired exclusion
count, network/provider call counts, and the deterministic `generated_by`
path.

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
  and GitHub. CI is a separate explicit `workflow_dispatch` job with
  `enable_external_benchmark_network=true`. It does NOT run on PR/push
  by default, uses no provider secrets/vars, no provider model env, and
  uploads only the aggregate report. The private SCORE JSONL is NEVER
  uploaded.
- If `enable_external_benchmark_network` is false, the workflow is a
  no-op with a clear message and exits 0 (self-test + py_compile still
  run; an unavailable aggregate artifact is produced).
- The workflow validates the report's claim boundary flags after the
  smoke (fail-closed: network-enabled CI cannot pass with unavailable/no
  records): require status in (`bea1_mechanism_ablation_pass`, `partial`),
  `records_successful >= 3`, every mechanism contrast has
  `record_count >= 3`, `forbidden_scan.status=pass`, `provider_calls=0`,
  private SCORE manifest present with `path_publicly_serialized=false`,
  no `winner`/`best_method`/`recommended_default`/`method_winner`/
  `calibration` fields anywhere, no BEA-1 private fields anywhere.

## Forbidden scanner (public, fail-closed)

A strict forbidden-output scanner runs fail-closed before writing the public
JSON. Reuses BEA-0/C5-A/C5-D forbidden scanner primitives for raw key/value
leak detection, and ADDS BEA-1-specific claim-boundary forbidden keys
(`calibration`, `method_winner`, `best_method`, `recommended_default`,
`winner`, `leaderboard`, `promotion`, etc.) anywhere. BEA-1 also relaxes
false positives for the nested `private_score_manifest.manifest_hash`
sha256 hex string (legitimate aggregate manifest hash; safe to publish).

The `failure_category_counts`, `arm_metric_records`, `delta_records`,
`mechanism_contrast_records`, and `private_score_manifest` containers are
schema-key containers whose CHILD KEYS are fixed category labels or
allowlisted metric/arm names; the forbidden_key check is relaxed for those
child keys, but the values under them are still scanned.

The scanner runs ONLY against the final public aggregate artifact.
Internal task/label/run JSONL, the private SCORE JSONL, and the per-record
candidate lists / action traces / budget states / accepted candidates /
same-budget control arm evidence (which contain paths/spans/queries/gold)
are kept in-memory/transient under `/tmp` only, never scanned against the
public contract, and never committed.

## Self-tests

`--self-test` runs 420 deterministic checks across 28 groups (no network;
synthetic candidates + synthetic gold record + synthetic metrics):

1. Artifact identity fields (schema, claim, status, mode, phase,
   generated_by, treatment_arm, baseline_arm, seeded_random_seed).
2. Safe true flags present + correct values (8 flags).
3. No-claim / no-runtime-change false flags (15 flags).
4. License fields (4 fields).
5. Private SCORE manifest aggregate-only fields (manifest present,
   records_written, record_count, schema_version, storage_class,
   path_not_publicly_serialized, manifest_hash is sha256 hex, 14
   forbidden private keys absent).
6. Row/needle/budget hard caps (ContextBench default 5 / cap 20; RepoQA
   default 3 / cap 10; budget default 5 / cap 20; rejects 0).
7. Method validation (default; requires bm25; rejects dense).
8. Same-budget K exactly per plan (min of bea_accepted and deduped;
   zero when bea accepts zero; zero when no deduped; zero when both zero).
9. same_budget_bm25_prefix arm (returns K; zero when K=0; first path is
   path1).
10. agreement_only_same_budget arm (returns K; zero when K=0; first is
    high-agreement span).
11. seeded_random_same_budget arm (returns K; zero when K=0;
    deterministic; K=3 deterministic; returns all when K exceeds deduped).
12. seeded_random + agreement_only runtime-clean invariance under
    gold/label/row-id tainting.
13. arm_metric_records fixed shape (each record has exactly {arm, metric,
    value}; metric allowlisted; value numeric; arm fixed).
14. delta_records fixed shape (each record has exactly {baseline_arm,
    treatment_arm, metric, delta}; baseline_arm=bm25_top10; metric
    allowlisted; delta numeric).
15. mechanism_contrast_records fixed shape + record_count (each record
    has exactly {contrast, baseline_arm, treatment_arm, metric, delta,
    record_count}; contrast fixed; treatment_arm=bea_v0_budgeted;
    record_count positive; delta numeric).
16. Failure category counts fixed enum (in-enum keys pass; non-enum keys
    rejected by builder).
17. Unavailable report (status, failure_reason_category, no smoke flag,
    no perf claim, empty arm_metric_records/delta_records/
    mechanism_contrast_records, private_score_manifest present with
    path_publicly_serialized=false, scan pass).
18. Scanner rejects forbidden content (BEA-0-specific forbidden keys;
    repo URL/slug/commit SHA/file path/tmp path/multiline values).
19. Scanner allows safe values (schema_version, methods, budget,
    arm_metric_records, delta_records, mechanism_contrast_records,
    private_score_manifest, failure_category).
20. Fail-closed generation (clean report no raise; private_score_path
    raises; action_trace raises; accepted_candidates raises; winner
    raises; best_method raises; calibration raises; self-test failure
    refuses artifact generation).
21. Public artifact self-scan is clean (skeleton + unavailable).
22. CLI argument surface (`--self-test`, `--contextbench-row-limit`,
    `--repoqa-needle-limit`, `--budget`, `--methods`, `--openlocus`,
    `--out`, `--private-score-dir`, `--enable-rrf-baseline`,
    `--enable-external-benchmark-network`).
23. Private SCORE writer round-trip (two rows; parse as JSON;
    path-leak detected by scanner).
24. Paired denominator rule (records missing one arm are excluded from
    contrasts involving that arm; record_count reflects paired
    denominator).
25. Aggregate runtime seconds present (pass report has numeric;
    unavailable omits).
26. No winner/best_method/recommended_default/method_winner/calibration
    anywhere (5 fields).
27. Fixed arms present in fixed_arms list (5 arms when rrf disabled;
    rrf excluded when disabled).
28. Scanner rejects BEA-1-specific forbidden keys (calibration,
    method_winner, best_method, recommended_default, winner, etc.).

## Validation

```text
python3 -m py_compile eval/bea1_mechanism_ablation.py  => PASS
python3 eval/bea1_mechanism_ablation.py --self-test  => PASS (420/420 checks)
python3 eval/bea1_mechanism_ablation.py \
  --enable-external-benchmark-network \
  --contextbench-row-limit 5 --repoqa-needle-limit 3 \
  --budget 5 --methods bm25,regex,symbol --enable-rrf-baseline \
  --out artifacts/bea1_mechanism_ablation/\
bea1_mechanism_ablation_report.json  => PASS
  (status: bea1_mechanism_ablation_pass,
   forbidden_scan: pass, self_test_passed: true,
   mode: bounded_external_retrieval_mechanism_ablation, phase: BEA-1,
   methods: bm25,regex,symbol, budget: 5,
   enable_rrf_baseline: true,
   fixed_arms: [bm25_top10, bea_v0_budgeted, same_budget_bm25_prefix,
                agreement_only_same_budget, seeded_random_same_budget,
                rrf_bm25_regex_symbol_top10],
   baseline_arm: bm25_top10, treatment_arm: bea_v0_budgeted,
   seeded_random_seed: 20240621,
   records_evaluated: 8, records_successful: 8, records_failed: 0,
   paired_exclusion_count: 0,
   network_calls: 2, provider_calls: 0,
   mechanism_ablation_performed: true,
   bea_v0_acquisition_performed: true,
   private_score_records_written: true,
   private_score_manifest.record_count: 8,
   private_score_manifest.storage_class: tmp_private,
   private_score_manifest.path_publicly_serialized: false,
   external_benchmark_rows_read: true,
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

Bounded local run with `--enable-external-benchmark-network
--contextbench-row-limit 5 --repoqa-needle-limit 3 --budget 5 --methods
bm25,regex,symbol --enable-rrf-baseline` completed successfully. The
committed artifact mirrors that sanitized aggregate report.

```text
python3 eval/bea1_mechanism_ablation.py \
  --enable-external-benchmark-network \
  --contextbench-row-limit 5 --repoqa-needle-limit 3 \
  --budget 5 --methods bm25,regex,symbol --enable-rrf-baseline \
  --out artifacts/bea1_mechanism_ablation/\
bea1_mechanism_ablation_report.json
  => status: bea1_mechanism_ablation_pass,
     forbidden_scan: pass, self_test_passed: true
  => records_evaluated: 8, records_successful: 8, records_failed: 0
  => paired_exclusion_count: 0
  => network_calls: 2, provider_calls: 0
  => mechanism_ablation_performed: true
  => bea_v0_acquisition_performed: true
  => private_score_records_written: true
  => private_score_manifest.record_count: 8
  => private_score_manifest.storage_class: tmp_private
  => private_score_manifest.path_publicly_serialized: false
  => aggregate_runtime_seconds: 49.73

  arm_metric_records (means across 8 records):
    bm25_top10:                    file_recall@10=0.5,    mrr=0.296875,
                                    span_f0.5@10=0.035962, success_rate=0.5,
                                    candidate_count_read=12.5, evidence_budget_used=6.25,
                                    action_steps=6.25, latency_seconds=0.447125,
                                    quality_per_candidate=0.001798
    rrf_bm25_regex_symbol_top10:   file_recall@10=0.5,    mrr=0.296875,
                                    span_f0.5@10=0.035962, success_rate=0.5,
                                    candidate_count_read=12.5, evidence_budget_used=6.25,
                                    action_steps=6.25, latency_seconds=1.249875,
                                    quality_per_candidate=0.001798
    bea_v0_budgeted:               file_recall@10=0.375, mrr=0.28125,
                                    span_f0.5@10=0.057174, success_rate=0.375,
                                    candidate_count_read=12.5, evidence_budget_used=3.125,
                                    action_steps=3.75, latency_seconds=3.74384,
                                    quality_per_candidate=0.002859
    same_budget_bm25_prefix:       file_recall@10=0.375, mrr=0.28125,
                                    span_f0.5@10=0.057174, success_rate=0.375,
                                    candidate_count_read=12.5, evidence_budget_used=3.125,
                                    action_steps=3.125, latency_seconds=0.0,
                                    quality_per_candidate=0.002859
    agreement_only_same_budget:    file_recall@10=0.375, mrr=0.28125,
                                    span_f0.5@10=0.057174, success_rate=0.375,
                                    candidate_count_read=12.5, evidence_budget_used=3.125,
                                    action_steps=3.125, latency_seconds=0.0,
                                    quality_per_candidate=0.002859
    seeded_random_same_budget:     file_recall@10=0.25,  mrr=0.1875,
                                    span_f0.5@10=0.020161, success_rate=0.25,
                                    candidate_count_read=12.5, evidence_budget_used=3.125,
                                    action_steps=3.125, latency_seconds=0.0,
                                    quality_per_candidate=0.001008

  mechanism_contrast_records (mrr, paired record_count=8):
    bea_vs_same_budget_bm25:   delta(mrr)=0.0     (bea ties same-budget BM25 prefix)
    bea_vs_agreement_only:    delta(mrr)=0.0     (bea ties agreement-only)
    bea_vs_seeded_random:     delta(mrr)=+0.09375 (bea beats seeded random)
```

The bounded local run reran fresh retrieval over 5 ContextBench verified
Python rows + 3 RepoQA Python needles, collected multi-method candidates
(bm25/regex/symbol) plus the optional rrf baseline, ran the deterministic
`bea_v0_budgeted` policy under budget=5 plus three same-budget controls,
wrote 8 private per-record SCORE JSONL rows to
`/tmp/bea0_private_score_<pid>_<ts>/bea1.private.jsonl` (transient; NEVER
committed or uploaded), and committed only aggregate per-arm metric
records + baseline-vs-treatment delta records + mechanism contrast records
(with `record_count=8`).

Key mechanism ablation findings (smoke-level, NOT benchmark/calibration/
method-winner claims):

- BEA v0 and `agreement_only_same_budget` produce IDENTICAL
  file_recall@10 / mrr / span_f0.5@10 / success_rate on the paired
  denominator, with the same `evidence_budget_used=3.125`. This suggests
  BEA v0's gain (if any) over a pure agreement-only rank under the same
  budget is zero on this bounded sample; BEA v0's sequential
  coverage/defer/expand rules did not change the accepted set vs the
  simpler agreement-only sort.
- BEA v0 and `same_budget_bm25_prefix` also produce IDENTICAL
  file_recall@10 / mrr / span_f0.5@10 / success_rate, suggesting BEA v0's
  agreement-based reranking did not differ from BM25-prefix selection on
  this bounded sample (the high-agreement spans were also the top BM25
  spans).
- `seeded_random_same_budget` underperforms both BEA v0 and the
  agreement-only control by `delta(mrr)=+0.09375` in BEA v0's favor,
  confirming that deterministic agreement-based selection beats random
  selection under the same budget on this bounded sample.

These are honest smoke-level aggregate deltas over a bounded sample, not
benchmark results, leaderboard entries, performance claims, method-winner
claims, calibration claims, promotions, default changes, runtime/retriever/
pack/backend/EvidenceCore semantic changes, or downstream agent value
claims.

If the network smoke cannot complete in a future environment (ContextBench
fetch failure, RepoQA asset download failure, parse failure, no Python
rows/needles, repo clone failure, retrieval failure, private SCORE write
failure), the artifact records truthful `unavailable_with_reason` with a
real `failure_reason_category` and the corresponding
`failure_category_counts` increment. No stale/fake pass is ever written.

## Caveats

- BEA-1 is the public aggregate-only mechanism ablation smoke artifact.
  It is eval/diagnostic only. It does NOT change runtime, retriever, pack,
  backend, or default policy; it does NOT change EvidenceCore semantics.
  It is NOT a benchmark result, NOT a leaderboard entry, NOT a performance
  claim, NOT a method-winner claim, NOT a calibration claim, NOT a
  promotion, NOT a default change, NOT a runtime-clean general algorithm
  claim, and NOT a downstream agent value claim.
- BEA-1 does NOT emit `winner`, `best_method`, `recommended_default`,
  `method_winner`, `calibration`, or anything implying a policy/default
  decision.
- BEA-1 runs NO provider calls and NO remote provider calls.
  `provider_calls=0`, `provider_calls_made=false`,
  `remote_provider_calls_made=false`.
- BEA-1 uses a **bounded ContextBench verified Python subset** (default 5
  rows; hard cap 20) and a **bounded RepoQA Python needle subset**
  (default 3 needles; hard cap 10). This is a smoke, not a rigorous
  benchmark evaluation. The aggregate metrics are point estimates over a
  bounded sample and should NOT be interpreted as a benchmark result,
  leaderboard entry, performance claim, method-winner claim, or
  calibration.
- BEA-1 writes private per-record SCORE JSONL ONLY under `/tmp` (or an
  explicitly ignored private path under the gitignored `runs/` directory).
  The private SCORE path is NEVER serialized in the public artifact, docs,
  or CI artifacts. The public artifact records ONLY aggregate SCORE
  manifest fields (`records_written`, `record_count`, `schema_version`,
  `manifest_hash`, `storage_class`, `path_publicly_serialized=false`).
- BEA-1 does NOT silently fall back from Python to all languages. If
  `language_filter=python` and zero Python rows/needles are found, the
  artifact is truthful `unavailable_with_reason` with a real failure
  category.
- BEA-1 does NOT claim external benchmark performance. The aggregate
  metrics are smoke-level diagnostics, NOT a benchmark result.
  `external_benchmark_performance_claimed=false`.
- BEA-1 does NOT claim a method winner. The mechanism contrasts are
  honest baseline-vs-treatment deltas; the delta may be positive, zero, or
  negative. `method_winner_claimed=false`.
- BEA-1 does NOT prove downstream agent value. The mechanism ablation
  smoke does not exercise any downstream agent.
  `downstream_agent_value_proven=false`.
- BEA-1 does NOT bootstrap the BEA-0 aggregate artifact. It reruns fresh
  external retrieval; the BEA-0 artifact is not read or relied upon.
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

- BEA-1 is the first mechanism ablation smoke. A full BEA-2 / BEA-3 phase
  would require larger sample sizes, multiple budget settings,
  statistical analysis, score calibration, and richer policy features
  (e.g. anchor agreement, span-overlap geometry).
- No promotion, no default change, no EvidenceCore semantics change, no
  runtime-clean general algorithm claim, no method-winner claim, no
  calibration claim, no downstream agent value claim follows from BEA-1.
