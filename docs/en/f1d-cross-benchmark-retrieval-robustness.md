# F1-D Cross-Benchmark Retrieval Utility Robustness Smoke (Public Aggregate-Only Artifact)

## Scope and claim boundary

F1-D extends F1-C from point estimates to **diagnostic paired-bootstrap
confidence/sign-stability estimates**. F1-D **reruns real bounded
external data** over two benchmark-shaped retrieval samples
(ContextBench verified 20-row + RepoQA 10-needle Python), intercepts
per-unit score metrics **before aggregation** (in memory or `/tmp`
only), computes a fixed retrieval-derived utility proxy per
benchmark/method, cross-benchmark weighted means, and paired bootstrap
confidence/sign-stability statistics for five fixed effects over five
metrics. F1-D is **not** a rollup of existing C5 or F1-C aggregate
artifacts: it re-executes the real retrieval+score pipeline and
captures per-unit metrics in memory before they are collapsed by the
C5-C/C5-E aggregation helpers.

F1-D is explicitly **not** a downstream utility claim, **not** true
E/S calibration, **not** an external benchmark performance claim, **not**
a leaderboard entry, **not** a method winner claim, **not** a
promotion/default/runtime/retriever/pack/backend/EvidenceCore semantic
change, **not** a live/provider claim, and **not** a formal external
benchmark confidence interval. It makes NO provider calls and NO remote
provider calls. The bootstrap statistics are diagnostic robustness
estimates, NOT formal benchmark confidence intervals.

- Claim level: `cross_benchmark_retrieval_utility_robustness_smoke_only`.
- Mode: `bounded_contextbench_repoqa_retrieval_robustness`;
  phase `F1-D`.
- Status enum:
  `cross_benchmark_retrieval_robustness_pass` on success (both benchmarks
  pass AND bm25 succeeds on both);
  `partial` if at least one benchmark passes AND bm25 succeeds on at
  least one benchmark;
  `unavailable_with_reason` if none/blocked/network unavailable;
  `fail_forbidden_scan` on scanner failure;
  `fail_schema_contract` on invalid method config / shape.
- F1-D is **eval/diagnostic only**. It is NOT a benchmark result, NOT
  downstream utility, NOT true E/S calibration, NOT an external benchmark
  performance claim, NOT a leaderboard entry, NOT a method winner, NOT
  a formal confidence interval, and NOT a promotion.

### F1-C -> F1-D relation

```text
F1-C cross-benchmark retrieval-derived utility smoke
  (two benchmarks: ContextBench verified 20-row + RepoQA 10-needle
   Python; reruns real bounded external data;
   bm25/regex/symbol + empty_retrieval zero baseline;
   cross-benchmark weighted means;
   5 fixed counterfactual effects;
   aggregate-only public artifact; no provider calls;
   no winner/best/default/E_S notation; point estimates only)
-> F1-D cross-benchmark retrieval utility robustness smoke
   (same two benchmarks; same bounded data;
    per-unit metrics intercepted in memory before aggregation;
    paired cross-benchmark bootstrap preserving sample counts;
    5 fixed effects x 5 metrics = 25 bootstrap effect records;
    bootstrap CI p05/p50/p95 and sign-stability fractions;
    aggregate-only public artifact; no provider calls;
    no per-unit metric arrays; no winner/best/default/E_S notation)
```

## Benchmarks

F1-D reruns real bounded external data for two benchmarks (same
bounded subsets as F1-C):

1. **`contextbench`** — ContextBench verified subset (config
   `contextbench_verified`, split `train`): 20 verified rows, language
   python, query mode `first_paragraph`, methods `bm25,regex,symbol`.
2. **`repoqa`** — RepoQA Python needles: 10 needles, methods
   `bm25,regex,symbol`.

F1-D reruns the real network smoke (transient HF rows + GitHub clones +
RepoQA asset download + retrieval + score into `/tmp`). It does NOT
reuse existing C5-C, C5-E, or F1-C aggregate artifacts; it re-executes
the real retrieval+score pipeline and intercepts per-unit metrics in
memory before aggregation.

## Utility formula (fixed diagnostic proxy; unchanged from F1-C)

F1-D uses the same fixed retrieval-derived utility proxy as F1-C (NOT
downstream solve rate, NOT E/S calibration):

```text
utility = file_hit + 0.25*mrr + 0.5*span_f0.5 - miss_penalty
miss_penalty = 0.25 if file_recall@10 == 0 else 0
```

where `file_hit = file_recall@10` and `span_f0.5 = span_f0.5@10`.

`empty_retrieval` is the explicit zero-context baseline (no retrieval
run required). All metrics and utility are 0 by construction (it is a
synthetic baseline for the utility formula, NOT a retrieval method).

## Cross-benchmark weighted means

For each method, F1-D computes a cross-benchmark weighted mean across
the two benchmarks. Weights are sample counts: ContextBench row count
and RepoQA needle count.

```text
weighted_mean[metric] =
  (contextbench_value * contextbench_sample_count
   + repoqa_value * repoqa_sample_count)
  / (contextbench_sample_count + repoqa_sample_count)
```

`empty_retrieval` has sample_count=0 on both benchmarks; its weighted
mean is 0 by construction.

## Bootstrap effects

F1-D uses five fixed allowlisted effects (records-shaped only):

1. **`bm25_vs_empty`**  — (bm25 - empty_retrieval).
2. **`regex_vs_empty`** — (regex - empty_retrieval).
3. **`symbol_vs_empty`** — (symbol - empty_retrieval).
4. **`regex_vs_bm25`**  — (regex - bm25).
5. **`symbol_vs_bm25`** — (symbol - bm25).

Effects are computed for the cross-benchmark weighted mean of
`retrieval_utility` and each aggregate metric (`file_recall@10`,
`mrr`, `span_f0.5@10`, `success_rate`, `retrieval_utility`).

## Cross-benchmark resampling (preserves sample counts)

Within each bootstrap replicate:

1. ContextBench paired units are resampled **with replacement** to the
   ContextBench sample count (20 rows).
2. RepoQA paired units are resampled **with replacement** to the RepoQA
   needle count (10 needles).
3. For each benchmark, the aggregate metric means and retrieval
   utility are recomputed from the resampled per-unit metrics.
4. The cross-benchmark weighted mean is computed with the original
   sample counts as weights.
5. The effect is (treatment cross-benchmark weighted mean - baseline
   cross-benchmark weighted mean).

For paired effects (`regex_vs_bm25`, `symbol_vs_bm25`), resampling
preserves the treatment-baseline pairing: both are drawn from the same
resampled unit index (paired complete-case analysis).

For `*_vs_empty` effects, the baseline is synthetic zero (all metrics
0, utility 0 by construction); the effect equals the treatment value.

For `retrieval_utility`, the bootstrap recomputes utility from the
resampled aggregate metric means (utility of means), matching F1-C's
aggregate semantics. For `empty_retrieval` baseline, the baseline
utility is 0.0 by construction (NOT utility(0,0,0) which would be
-0.25).

## Public effect record fields

Each bootstrap effect record has exactly these fields:

- `effect_name`: fixed effect label.
- `metric`: fixed metric label.
- `point_estimate`: observed effect on the original data.
- `bootstrap_mean`: mean of bootstrap replicate effects.
- `ci_p05`: 5th percentile of bootstrap replicate effects.
- `ci_p50`: 50th percentile (median) of bootstrap replicate effects.
- `ci_p95`: 95th percentile of bootstrap replicate effects.
- `sign_positive_fraction`: fraction of replicates with effect > 0.
- `sign_negative_fraction`: fraction of replicates with effect < 0.
- `sign_zero_fraction`: fraction of replicates with effect == 0.
- `sample_units`: total paired units across both benchmarks.
- `bootstrap_replicates`: number of bootstrap replicates.
- `bootstrap_seed`: fixed RNG seed.

## Metrics

Aggregate retrieval/score utility proxy metrics (NOT downstream-agent
metrics):

- `file_recall@10`
- `mrr`
- `span_f0.5@10`
- `success_rate`
- `retrieval_utility` (F1-C/F1-D fixed utility proxy)

Allowed method labels: `empty_retrieval`, `bm25`, `regex`, `symbol`.

## Public artifact shape

Records only (aggregate-only; no per-unit metric arrays):

- `benchmark_method_means`: list of fixed records
  `{benchmark, method, sample_count, metrics}`.
- `cross_benchmark_method_means`: list of fixed records
  `{method, contextbench_sample_count, repoqa_sample_count, metrics}`.
  Includes `empty_retrieval` at position 0 (all metrics 0).
- `bootstrap_effect_records`: list of fixed records (fields above).
- `input_summary`: `contextbench_row_limit`, `repoqa_needle_limit`,
  `methods`, `benchmarks`, aggregate counts, `method_labels`,
  `effect_labels`, `metric_labels`, `contextbench_query_mode`,
  `repoqa_query_mode`, `repoqa_gold_target_mode`.
- `bootstrap_summary`: `bootstrap_replicates`, `bootstrap_seed`,
  `effect_count`, `metric_count`, `bootstrap_record_count`,
  `resampling_method`.

Identity / boundary fields:

- `schema_version` = `f1d_cross_benchmark_retrieval_robustness.v1`
- `generated_by`, `generated_at`, `claim_level`, `status`, `mode`,
  `phase`, `methods_requested`, `methods_allowed`, `baseline_method`,
  `network_mode`, `openlocus_binary_source`.
- `contextbench_row_limit_requested`, `repoqa_needle_limit_requested`,
  `contextbench_rows_fetched`, `repoqa_needles_seen`.
- `bootstrap_replicates_requested`, `bootstrap_seed`.
- `methods_count`, `methods_attempted`, `methods_successful`,
  `methods_succeeded`, `methods_failed`.
- Safe true flags (only when actually true):
  `retrieval_utility_robustness_smoke`, `contextbench_rows_read`,
  `repoqa_needles_read`, `openlocus_retrieval_executed`,
  `score_py_metrics_computed`, `bootstrap_computed`,
  `aggregate_only_public_artifact`, `diagnostic_only`.
- Always-false no-claim flags:
  `true_e_s_calibration_claimed`,
  `automated_e_s_full_calibration_claimed`,
  `human_e_s_calibration_claimed`,
  `external_benchmark_performance_claimed`,
  `leaderboard_entry_claimed`, `method_winner_claimed`,
  `baseline_is_policy_candidate`, `downstream_agent_value_proven`,
  `promotion_ready`, `default_should_change`,
  `runtime_behavior_changed`, `retriever_changed`,
  `pack_builder_changed`, `backend_changed`,
  `default_policy_changed`, `evidencecore_semantics_changed`,
  `provider_calls_made`, `remote_provider_calls_made`.
- `contextbench_failure_category_counts`: fixed ContextBench failure
  category counts only (kept SEPARATE from RepoQA).
- `repoqa_failure_category_counts`: fixed RepoQA failure category
  counts only (kept SEPARATE from ContextBench).
- `network_calls`, `provider_calls` (always 0).
- `self_test_passed`.
- `forbidden_scan` summary (fail-closed before writing JSON).
- `framing`: fixed no-claim framing fields
  (including `is_formal_benchmark_confidence_interval: false`).

## CLI

```bash
python3 -m py_compile eval/f1d_cross_benchmark_retrieval_robustness.py
python3 eval/f1d_cross_benchmark_retrieval_robustness.py --self-test
python3 eval/f1d_cross_benchmark_retrieval_robustness.py \
    --contextbench-row-limit 20 --repoqa-needle-limit 10 \
    --methods bm25,regex,symbol --bootstrap-replicates 1000 \
    --out artifacts/f1d_cross_benchmark_retrieval_robustness/\
f1d_cross_benchmark_retrieval_robustness_report.json
# Override openlocus binary and bootstrap seed:
python3 eval/f1d_cross_benchmark_retrieval_robustness.py \
    --contextbench-row-limit 20 --repoqa-needle-limit 10 \
    --methods bm25,regex,symbol \
    --bootstrap-replicates 1000 --bootstrap-seed 20240621 \
    --openlocus target/release/openlocus \
    --out /tmp/f1d_smoke_report.json
```

Default mode: runs a real cross-benchmark network smoke (transient
HF rows + RepoQA asset download + GitHub clones + retrieval + score
into `/tmp`). If network/openlocus is unavailable, it produces a
truthful `unavailable_with_reason` report. No provider calls are ever
made.

CLI arguments: `--self-test`, `--out`, `--contextbench-row-limit`
(default 20, hard cap 20), `--repoqa-needle-limit` (default 10, hard
cap 10), `--methods` (default `bm25,regex,symbol`),
`--bootstrap-replicates` (default 1000, hard cap 2000),
`--bootstrap-seed` (default 20240621), `--openlocus`.
Unknown/private-looking arguments are rejected with a generic
`invalid arguments` message (SafeArgumentParser pattern).

## Reused helpers

F1-D imports F1-C, C5-C, C5-E, C5-A, and C5-D helpers
(backward-compatible; none are modified):

- F1-C utility formula: `f1c._compute_utility`,
  `f1c._extract_method_metrics`, `f1c._filter_metrics`,
  `f1c._compute_utility` (guarantees formula identity).
- F1-C config: `f1c.parse_methods`, `f1c.MethodConfigError`,
  `f1c._validate_contextbench_row_limit`,
  `f1c._validate_repoqa_needle_limit`, F1-C constants
  (METRIC_NAMES, EFFECTS, ALLOWED_METHODS, etc.).
- F1-C scanner: `f1c._scan_f1c` (combines C5-A/C5-C/C5-E scanners and
  F1-C-specific checks); F1-D adds F1-D-specific forbidden keys and
  record-shape checks.
- ContextBench matrix execution: F1-D mirrors the C5-C
  `_run_single_method` loop but captures per-unit metrics in memory
  before aggregation (does NOT call `c5c._run_single_method` which
  collapses per-unit data). Reuses `c5c._public_failure_counts`,
  `c5c.PUBLIC_FAILURE_CATEGORIES`, `c5c.STATUS_PASS`.
- RepoQA matrix execution: F1-D mirrors the C5-E `_run_single_method`
  loop but captures per-unit metrics in memory before aggregation.
  Reuses `c5e.STATUS_PASS`.
- ContextBench primitives: `c5a._fetch_contextbench_rows`,
  `c5a.DEFAULT_QUERY_MODE`, `c5a.DEFAULT_LANGUAGE_FILTER`,
  `c5a._resolve_openlocus_binary`, `c5a._parse_gold_context`,
  `c5a._sanitize_query`, `c5a._clone_and_checkout`,
  `c5a._write_transient_jsonl`, `c5a._run_retrieval_and_score`.
- RepoQA primitives: `c5d._download_asset_to_bytes`,
  `c5d._decompress_asset`, `c5d._parse_repoqa_needles`,
  `c5d._sanitize_needle_description`, `c5d._clone_and_checkout`,
  `c5d._write_transient_jsonl`, `c5d._run_retrieval_and_score`,
  `c5d.ASSET_URL`, `c5d.DEFAULT_LANGUAGE_FILTER`,
  `c5d.FAILURE_CATEGORIES`.
- Scanner primitives: `c5a._RE_URL_VALUE`, `c5a._RE_HEX_DIGEST`,
  `c5a._RE_SECRET_LIKE`, etc.; `c5c._scan_c5c`,
  `c5c.FORBIDDEN_RECOMMENDATION_FIELDS`; `c5e._scan_c5e`.

F1-D report identity is F1-D (`schema_version=f1d_cross_benchmark_retrieval_robustness.v1`,
`claim_level=cross_benchmark_retrieval_utility_robustness_smoke_only`,
`mode=bounded_contextbench_repoqa_retrieval_robustness`, `phase=F1-D`).
F1-D does NOT mutate F1-C result semantics.

## Forbidden scanner (public, fail-closed)

A strict forbidden-output scanner runs fail-closed before writing the
public JSON. It combines:

- The F1-C forbidden scanner (which itself combines C5-A/C5-C/C5-E
  scanners and F1-C-specific forbidden keys, record-shape checks, and
  value-pattern checks).
- F1-D-specific forbidden keys: F1-C record container names
  (`benchmark_results`, `cross_benchmark_method_results`,
  `counterfactual_effects`) — F1-D uses its own container names;
  per-unit metric array keys (`per_row_metrics`, `per_needle_metrics`,
  `row_metrics`, `needle_metrics`, `row_hashes`, `needle_hashes`,
  `per_unit_metrics`, `per_unit_utility`).
- F1-D records-shape check: `benchmark_method_means`,
  `cross_benchmark_method_means`, `bootstrap_effect_records` must be
  lists of records (NOT dict-keyed mirrors).
- F1-D value-pattern check: rejects raw model routing prefixes
  (reused from F1-C).

No `winner` / `best_method` / `recommended_default` fields are emitted.
No E/S calibration notation (`E_primary` / `S_support`) is used.
No per-unit metric arrays, row hashes, or per-row/per-needle data are
committed.

The scanner runs ONLY against the final public aggregate artifact. The
internal task/label/run JSONL and per-unit metrics (which contain
paths/spans/queries/gold) are kept in-memory or under `/tmp` only,
never scanned against the public contract, and never committed.

## Failure categories kept separate

ContextBench and RepoQA failure categories remain separate (do NOT
merge incompatible enums):

- `contextbench_failure_category_counts`: ContextBench categories
  (`network_fetch_failed`, `clone_failed`, `checkout_failed`,
  `label_context_parse_failed`, `row_parse_failed`,
  `retrieval_failed`, `score_failed`, `no_python_rows`, etc.).
- `repoqa_failure_category_counts`: RepoQA categories
  (`asset_download_failed`, `asset_decompress_failed`,
  `asset_parse_failed`, `no_python_needles`, `needle_parse_failed`,
  `repo_clone_failed`, `repo_checkout_failed`, `retrieval_failed`,
  `score_failed`, etc.).

## Self-tests

- Artifact identity fields (schema, claim, status, mode, phase,
  generated_by).
- Safe true flags present; no-claim flags false.
- Methods / effects / metrics / benchmarks are fixed allowlists.
- Records-shaped containers (`benchmark_method_means`,
  `cross_benchmark_method_means`, `bootstrap_effect_records` are
  lists; no dynamic dict mirrors; no F1-C container keys).
- Method parser (rejects unknown/text; dedups; defaults).
- Row/needle limit hard caps (20 / 10).
- Bootstrap replicates hard cap (2000) and default (1000).
- Bootstrap seed default (20240621).
- Utility computation: empty_retrieval -> 0; zero file_recall ->
  miss_penalty 0.25; nonzero file_recall -> no miss_penalty.
- Per-unit aggregation (utility of means != mean of per-unit
  utilities).
- Cross-benchmark weighted means (different metrics; empty_retrieval
  zero).
- Bootstrap computation (point estimate, mean, CIs, sign fractions,
  sample_units, determinism with same seed).
- Bootstrap effect records count = effects * metrics = 5 * 5 = 25.
- Bootstrap effect record fields (exact set).
- Paired unit builder (matched by index; empty baseline; partial
  overlap).
- Percentile helper (single value, empty, p0/p50/p100).
- Failure categories kept separate (ContextBench vs RepoQA enums).
- Scanner rejections: repo URL, commit SHA, repo slug, task_id key,
  query key, winner key, best_method key, E_primary key, raw routing
  prefix value, tmp path, provider key, F1-C container keys, per-unit
  metric array keys, row hashes.
- Scanner allows: method/benchmark/effect/metric names, bootstrap
  fields, benchmark_method_means records, bootstrap_effect_records
  records.
- Scanner rejects dict-keyed mirrors for F1-D containers.
- Fail-closed generation: clean report does not raise; leaked report
  raises SystemExit; winner/ES-notation/per-unit-key leak raises
  SystemExit; self-test failure refuses artifact generation.
- Public artifact self-scan is clean.
- Pass/partial report shapes (benchmark_method_means count;
  cross_benchmark_method_means includes empty_retrieval;
  bootstrap_effect_records count; bootstrap_summary record count
  matches).
- CLI argument surface (including `--bootstrap-replicates`,
  `--bootstrap-seed`).

## Validation

```text
python3 -m py_compile eval/f1d_cross_benchmark_retrieval_robustness.py  => PASS
python3 eval/f1d_cross_benchmark_retrieval_robustness.py --self-test  => PASS (185/185 checks)
python3 eval/f1d_cross_benchmark_retrieval_robustness.py \
  --contextbench-row-limit 20 --repoqa-needle-limit 10 \
  --methods bm25,regex,symbol --bootstrap-replicates 1000 \
  --out artifacts/f1d_cross_benchmark_retrieval_robustness/\
f1d_cross_benchmark_retrieval_robustness_report.json  => PASS
  (status: cross_benchmark_retrieval_robustness_pass,
   forbidden_scan: pass, self_test_passed: true,
   contextbench_rows_fetched: 20, repoqa_needles_seen: 10,
   network_calls: 2, provider_calls: 0,
   bootstrap_record_count: 25,
   retrieval_utility_robustness_smoke: true,
   contextbench_rows_read: true,
   repoqa_needles_read: true,
   openlocus_retrieval_executed: true,
   score_py_metrics_computed: true,
   bootstrap_computed: true,
   downstream_agent_value_proven: false,
   true_e_s_calibration_claimed: false,
   external_benchmark_performance_claimed: false,
   method_winner_claimed: false,
   leaderboard_entry_claimed: false,
   promotion_ready: false,
   default_should_change: false,
   retriever_changed: false,
   pack_builder_changed: false,
   backend_changed: false,
   default_policy_changed: false,
   evidencecore_semantics_changed: false)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

Local real-network run produced the following aggregate metrics and
bootstrap statistics (no row/needle/repo/commit/query/gold/path/span/
snippet/source/JSONL/evidence/stdout/stderr/clone-path/row-id/hash/
per-unit-metric-array/provider/model-routing-prefix/winner/best/
default/recommended fields committed):

```text
status: cross_benchmark_retrieval_robustness_pass
contextbench_rows_fetched: 20
repoqa_needles_seen: 10
network_calls: 2
forbidden_scan: pass
provider_calls: 0
bootstrap_replicates: 1000
bootstrap_seed: 20240621
bootstrap_record_count: 25
contextbench/bm25: file_recall@10=0.35, mrr=0.143107, span_f0.5@10=0.020838, success_rate=1.0, retrieval_utility=0.396196
contextbench/regex: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0, retrieval_utility=-0.25
contextbench/symbol: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0, retrieval_utility=-0.25
repoqa/bm25: file_recall@10=0.5, mrr=0.369216, span_f0.5@10=0.020817, success_rate=1.0, retrieval_utility=0.602712
repoqa/regex: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0, retrieval_utility=-0.25
repoqa/symbol: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0, retrieval_utility=-0.25
cross_benchmark bm25: file_recall@10=0.4, mrr=0.218477, span_f0.5@10=0.020831, success_rate=1.0, retrieval_utility=0.465035
cross_benchmark regex: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0, retrieval_utility=-0.25
cross_benchmark symbol: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0, retrieval_utility=-0.25
bm25_vs_empty [retrieval_utility]: point=+0.465035, mean=+0.463491, ci=[+0.298938, +0.464512, +0.624026], sign+=1.0, sign-=0.0, sign0=0.0
regex_vs_empty [retrieval_utility]: point=-0.25, mean=-0.25, ci=[-0.25, -0.25, -0.25], sign+=0.0, sign-=1.0, sign0=0.0
symbol_vs_empty [retrieval_utility]: point=-0.25, mean=-0.25, ci=[-0.25, -0.25, -0.25], sign+=0.0, sign-=1.0, sign0=0.0
regex_vs_bm25 [retrieval_utility]: point=-0.715035, mean=-0.713491, ci=[-0.874026, -0.714511, -0.548938], sign+=0.0, sign-=1.0, sign0=0.0
symbol_vs_bm25 [retrieval_utility]: point=-0.715035, mean=-0.713491, ci=[-0.874026, -0.714511, -0.548938], sign+=0.0, sign-=1.0, sign0=0.0
bm25_vs_empty [file_recall@10]: point=+0.4, mean=+0.398833, ci=[+0.266667, +0.4, +0.533333], sign+=1.0, sign-=0.0, sign0=0.0
```

The point estimates match F1-C's cross-benchmark weighted-mean deltas
(`bm25_vs_empty` retrieval_utility = +0.465035, `regex_vs_bm25` =
-0.715035), confirming the utility formula and aggregation are
unchanged from F1-C. The bootstrap CIs and sign-stability fractions
extend these point estimates with diagnostic robustness information.

This is a cross-benchmark retrieval utility robustness smoke over tiny
bounded ContextBench + RepoQA subsets. It is not downstream utility,
not a formal external benchmark result, not a formal confidence
interval, not a method winner, and not a default/promotion signal.

## Caveats

- F1-D is the public aggregate-only cross-benchmark retrieval utility
  robustness smoke artifact. It is eval/diagnostic only. It does NOT
  change runtime, retriever, pack, backend, or default policy; it
  does NOT change EvidenceCore semantics. It is NOT a benchmark result,
  NOT downstream utility, NOT true E/S calibration, NOT an external
  benchmark performance claim, NOT a leaderboard entry, NOT a method
  winner, NOT a formal confidence interval, and NOT a promotion.
- F1-D reruns real bounded external data (ContextBench verified 20-row
  + RepoQA 10-needle Python). It does NOT combine existing C5-C, C5-E,
  or F1-C aggregate artifacts; it re-executes the real retrieval+score
  pipeline and intercepts per-unit metrics in memory before aggregation.
- F1-D makes NO provider calls and NO remote provider calls. All
  transient data (rows, needles, queries, gold labels, retrieval
  JSONL, scoring JSONL, repo URLs, commits, paths, spans, candidates,
  stdout/stderr, per-unit metrics) stays in memory or under `/tmp`
  only and is NEVER committed or uploaded.
- Per-unit metrics exist only in memory or `/tmp`; the public artifact
  emits aggregate means and bootstrap statistics only. No per-row or
  per-needle metric arrays are committed.
- F1-D does NOT prove downstream agent value.
  `downstream_agent_value_proven=false`.
- F1-D does NOT claim true E/S calibration.
  `true_e_s_calibration_claimed=false`.
- F1-D does NOT claim external benchmark performance.
  `external_benchmark_performance_claimed=false`.
- F1-D does NOT claim a method winner.
  `method_winner_claimed=false`.
- F1-D does NOT emit winner/best_method/recommended_default fields.
- F1-D does NOT use E/S calibration notation (`E_primary` / `S_support`).
- F1-D does NOT emit F1-C record container names
  (`benchmark_results`, `cross_benchmark_method_results`,
  `counterfactual_effects`); it uses its own container names
  (`benchmark_method_means`, `cross_benchmark_method_means`,
  `bootstrap_effect_records`).
- The utility formula is a fixed diagnostic proxy (unchanged from
  F1-C). It is NOT a downstream solve rate, NOT a calibrated agent
  utility, and NOT a promotion metric. The miss_penalty (0.25 when
  file_recall@10 == 0) can produce negative utility values; this is
  intentional (zero recall with nonzero success_rate is a degenerate
  signal).
- `empty_retrieval` is a synthetic zero-context baseline. No retrieval
  run is performed for it; all metrics and utility are 0 by
  construction (overriding the formula's miss_penalty for the
  zero-recall case, matching F1-C).
- The bootstrap statistics are diagnostic robustness estimates, NOT
  formal external benchmark confidence intervals. They reflect the
  variability of the bounded smoke sample, not the population-level
  uncertainty of a full benchmark evaluation.
  `is_formal_benchmark_confidence_interval=false`.
- Cross-benchmark resampling preserves benchmark sample counts
  (ContextBench 20, RepoQA 10). This is a smoke-level diagnostic, NOT
  a formal meta-analysis.
- The `success_rate` metric is degenerate (always 1.0 for real methods
  that successfully complete retrieval, since per-unit metrics are
  captured only for successful units). The bootstrap correctly
  reflects this (e.g., `regex_vs_bm25` on `success_rate` has
  point=0.0 and sign_zero_fraction=1.0).
- ContextBench and RepoQA failure categories are kept SEPARATE in the
  public artifact; their incompatible enums are NOT merged.
- All no-claim / no-runtime-change flags remain false; diagnostic flags
  (`aggregate_only_public_artifact`, `diagnostic_only`) remain true;
  the smoke-claimed flags (`retrieval_utility_robustness_smoke`,
  `contextbench_rows_read`, `repoqa_needles_read`,
  `openlocus_retrieval_executed`, `score_py_metrics_computed`,
  `bootstrap_computed`) are true ONLY when a real network run actually
  executed.
- No runtime/retriever/pack/model/backend/default-policy files were
  modified. No promotion/default/runtime claims change.
