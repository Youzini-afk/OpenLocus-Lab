# F1-C Cross-Benchmark Retrieval-Derived Utility Smoke (Public Aggregate-Only Artifact)

## Scope and claim boundary

F1-C is the **cross-benchmark** retrieval-derived utility smoke. It
**reruns real bounded external data** over two benchmark-shaped
retrieval samples (ContextBench verified 20-row + RepoQA 10-needle
Python), then computes a fixed retrieval-derived utility proxy per
benchmark/method, cross-benchmark weighted means, and counterfactual
effects. F1-C is **not** a rollup of existing C5 aggregate JSON
artifacts: it calls the real C5-C ContextBench matrix runner and the
real C5-E RepoQA matrix runner, materializes transient `/tmp` clones,
runs real OpenLocus retrieval, and runs `eval/score.py`.

F1-C is explicitly **not** a downstream utility claim, **not** true
E/S calibration, **not** an external benchmark performance claim, **not**
a leaderboard entry, **not** a method winner claim, **not** a
promotion/default/runtime/retriever/pack/backend/EvidenceCore semantic
change, and **not** a live/provider claim. It makes NO provider calls
and NO remote provider calls.

- Claim level: `cross_benchmark_retrieval_derived_utility_smoke_only`.
- Mode: `bounded_contextbench_repoqa_retrieval_utility`;
  phase `F1-C`.
- Status enum:
  `cross_benchmark_retrieval_utility_pass` on success (both benchmarks
  pass AND bm25 succeeds on both);
  `partial_with_exclusions` if at least one benchmark passes AND bm25
  succeeds on at least one benchmark;
  `unavailable_with_reason` if none/blocked/network unavailable;
  `fail_forbidden_scan` on scanner failure;
  `fail_schema_contract` on invalid method config / shape.
- F1-C is **eval/diagnostic only**. It is NOT a benchmark result, NOT
  downstream utility, NOT true E/S calibration, NOT an external benchmark
  performance claim, NOT a leaderboard entry, NOT a method winner, and
  NOT a promotion.

### F1-B -> F1-C relation

```text
F1-B retrieval-derived counterfactual utility smoke
  (single benchmark: ContextBench verified 5-row;
   5 candidate-set variants; 4 effects; bm25/regex/symbol;
   no provider calls)
-> F1-C cross-benchmark retrieval-derived utility smoke
   (two benchmarks: ContextBench verified 20-row + RepoQA 10-needle
    Python; reruns real bounded external data;
    bm25/regex/symbol + empty_retrieval zero baseline;
    cross-benchmark weighted means;
    5 fixed counterfactual effects;
    aggregate-only public artifact; no provider calls;
    no winner/best/default/E_S notation)
```

## Benchmarks

F1-C reruns real bounded external data for two benchmarks:

1. **`contextbench`** — ContextBench verified subset (config
   `contextbench_verified`, split `train`): 20 verified rows, language
   python, query mode `first_paragraph`, methods `bm25,regex,symbol`.
   Reuses C5-C matrix execution primitives
   (`eval/c5c_contextbench_verified_method_matrix_scale_smoke.py`).
2. **`repoqa`** — RepoQA Python needles: 10 needles, methods
   `bm25,regex,symbol`. Reuses C5-E matrix execution primitives
   (`eval/c5e_repoqa_method_matrix_smoke.py`).

F1-C reruns the real network smoke (transient HF rows + GitHub clones +
RepoQA asset download + retrieval + score into `/tmp`). It does NOT
reuse existing C5-C or C5-E aggregate artifacts; it re-executes the
real retrieval+score pipeline.

## Utility formula (fixed diagnostic proxy)

F1-C uses a fixed retrieval-derived utility proxy per benchmark/method
(NOT downstream solve rate, NOT E/S calibration):

```text
utility = file_hit + 0.25*mrr + 0.5*span_f0.5 - miss_penalty
miss_penalty = 0.25 if file_recall@10 == 0 else 0
```

where `file_hit = file_recall@10` and `span_f0.5 = span_f0.5@10`.

`empty_retrieval` is the explicit zero-context baseline (no retrieval
run required). All metrics and utility are 0 by construction (it is a
synthetic baseline for the utility formula, NOT a retrieval method).

## Cross-benchmark weighted means

For each method, F1-C computes a cross-benchmark weighted mean across
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

## Counterfactual effects

F1-C uses five fixed allowlisted counterfactual effects (records-shaped
only; one metric per fixed record):

1. **`bm25_vs_empty`**  — (bm25 - empty_retrieval).
2. **`regex_vs_empty`** — (regex - empty_retrieval).
3. **`symbol_vs_empty`** — (symbol - empty_retrieval).
4. **`regex_vs_bm25`**  — (regex - bm25).
5. **`symbol_vs_bm25`** — (symbol - bm25).

Effects are computed for the cross-benchmark weighted mean of
`retrieval_utility` and each aggregate metric (`file_recall@10`,
`mrr`, `span_f0.5@10`, `success_rate`, `retrieval_utility`).

## Metrics

Aggregate retrieval/score utility proxy metrics (NOT downstream-agent
metrics):

- `file_recall@10`
- `mrr`
- `span_f0.5@10`
- `success_rate`
- `retrieval_utility` (F1-C fixed utility proxy)

Allowed method labels: `empty_retrieval`, `bm25`, `regex`, `symbol`.

## CLI

```bash
python3 -m py_compile eval/f1c_cross_benchmark_retrieval_utility.py
python3 eval/f1c_cross_benchmark_retrieval_utility.py --self-test
python3 eval/f1c_cross_benchmark_retrieval_utility.py \
    --contextbench-row-limit 20 --repoqa-needle-limit 10 \
    --methods bm25,regex,symbol \
    --out artifacts/f1c_cross_benchmark_retrieval_utility/\
f1c_cross_benchmark_retrieval_utility_report.json
# Override openlocus binary:
python3 eval/f1c_cross_benchmark_retrieval_utility.py \
    --contextbench-row-limit 20 --repoqa-needle-limit 10 \
    --methods bm25,regex,symbol \
    --openlocus target/release/openlocus \
    --out /tmp/f1c_smoke_report.json
```

Default mode: runs a real cross-benchmark network smoke (transient
HF rows + RepoQA asset download + GitHub clones + retrieval + score
into `/tmp`). If network/openlocus is unavailable, it produces a
truthful `unavailable_with_reason` report. No provider calls are ever
made.

CLI arguments: `--self-test`, `--out`, `--contextbench-row-limit`
(default 20, hard cap 20), `--repoqa-needle-limit` (default 10, hard
cap 10), `--methods` (default `bm25,regex,symbol`), `--openlocus`.
Unknown/private-looking arguments are rejected with a generic
`invalid arguments` message (SafeArgumentParser pattern).

## Reused helpers

F1-C imports C5-C, C5-E, C5-A, and C5-D helpers (backward-compatible;
none are modified):

- ContextBench matrix execution: `c5c._run_single_method`,
  `c5c._public_failure_counts`, `c5c.PUBLIC_FAILURE_CATEGORIES`,
  `c5c.STATUS_PASS` (for status mirror only).
- RepoQA matrix execution: `c5e._run_single_method`,
  `c5e.STATUS_PASS` (for status mirror only).
- ContextBench primitives: `c5a._fetch_contextbench_rows`,
  `c5a.DEFAULT_QUERY_MODE`, `c5a.DEFAULT_LANGUAGE_FILTER`,
  `c5a._resolve_openlocus_binary`.
- RepoQA primitives: `c5d._download_asset_to_bytes`,
  `c5d._decompress_asset`, `c5d._parse_repoqa_needles`,
  `c5d.ASSET_URL`, `c5d.DEFAULT_LANGUAGE_FILTER`, `c5d.FAILURE_CATEGORIES`.
- Scanner primitives: `c5a._RE_URL_VALUE`, `c5a._RE_HEX_DIGEST`,
  `c5a._RE_SECRET_LIKE`, etc.; `c5c._scan_c5c`, `c5c.FORBIDDEN_RECOMMENDATION_FIELDS`;
  `c5e._scan_c5e`.

F1-C report identity is F1-C (`schema_version=f1c_cross_benchmark_retrieval_utility.v1`,
`claim_level=cross_benchmark_retrieval_derived_utility_smoke_only`,
`mode=bounded_contextbench_repoqa_retrieval_utility`, `phase=F1-C`).
F1-C normalizes upstream component statuses into F1-C component buckets:
`pass`, `partial`, or `unavailable`. Upstream C5-C/C5-E/C5-F status
enums are NOT emitted in the public artifact, including inside
`benchmark_results.status`.

## Artifact identity (default committed artifact)

The committed artifact at
`artifacts/f1c_cross_benchmark_retrieval_utility/f1c_cross_benchmark_retrieval_utility_report.json`
is the public aggregate-only smoke artifact. Identity / boundary fields:

- `schema_version` = `f1c_cross_benchmark_retrieval_utility.v1`
- `generated_by`, `generated_at`, `claim_level`, `status`, `mode`,
  `phase`, `methods_requested`, `methods_allowed`, `baseline_method`,
  `network_mode`, `openlocus_binary_source`.
- `contextbench_row_limit_requested`, `repoqa_needle_limit_requested`,
  `contextbench_rows_fetched`, `repoqa_needles_seen`.
- `methods_count`, `methods_attempted`, `methods_successful`,
  `methods_succeeded`, `methods_failed`.
- Safe true flags (only when actually true):
  `retrieval_derived_counterfactual_utility_smoke`,
  `contextbench_rows_read`, `repoqa_needles_read`,
  `openlocus_retrieval_executed`, `score_py_metrics_computed`,
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
- `benchmark_results`: list of fixed records
  `{benchmark, method, status, rows_evaluated|needles_evaluated,
  rows_successful|needles_successful, rows_failed|needles_failed,
  metrics, failure_category_counts}`.
- `cross_benchmark_method_results`: list of fixed records
  `{method, contextbench_sample_count, repoqa_sample_count, metrics}`.
  Includes `empty_retrieval` at position 0 (all metrics 0).
- `counterfactual_effects`: list of fixed records
  `{effect_name, baseline_method, treatment_method, metric, delta}`.
- `input_summary`: `contextbench_row_limit`, `repoqa_needle_limit`,
  `methods`, `benchmarks`, aggregate counts, `method_labels`,
  `effect_labels`, `metric_labels`, `contextbench_query_mode`,
  `repoqa_query_mode`, `repoqa_gold_target_mode`.
- `contextbench_failure_category_counts`: fixed ContextBench failure
  category counts only (kept SEPARATE from RepoQA).
- `repoqa_failure_category_counts`: fixed RepoQA failure category
  counts only (kept SEPARATE from ContextBench).
- `network_calls`, `provider_calls` (always 0).
- `self_test_passed`.
- `forbidden_scan` summary (fail-closed before writing JSON).
- `framing`: fixed no-claim framing fields.

## Forbidden scanner (public, fail-closed)

A strict forbidden-output scanner runs fail-closed before writing the
public JSON. It combines:

- C5-A forbidden scanner primitives (raw key/value leak detection).
- C5-C-specific forbidden keys (extra ContextBench row keys,
  recommendation fields, dynamic dict-keyed method_results rejection).
- C5-E-specific forbidden keys (RepoQA-shaped row/needle/repo/commit
  keys).
- F1-C-specific forbidden keys: `winner`, `best`, `best_method`,
  `best_variant`, `recommended_default`, `preferred_variant`,
  `preferred_method`, `best_arm`, `best_family`,
  `E_primary`, `S_support`, `e_score`, `s_score`, `model_id_raw`,
  `routing_prefix`.
- F1-C records-shape check: `benchmark_results`,
  `cross_benchmark_method_results`, `counterfactual_effects` must be
  lists of records (NOT dict-keyed mirrors).
- F1-C value-pattern check: rejects raw model routing prefixes.

No `winner` / `best_method` / `recommended_default` fields are emitted.
No E/S calibration notation (`E_primary` / `S_support`) is used.

The scanner runs ONLY against the final public aggregate artifact. The
internal task/label/run JSONL (which contain paths/spans/queries/gold)
are kept in-memory or under `/tmp` only, never scanned against the
public contract, and never committed.

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
- Records-shaped containers (`benchmark_results`,
  `cross_benchmark_method_results`, `counterfactual_effects` are
  lists; no dynamic dict mirrors).
- Method parser (rejects unknown/text; dedups; defaults).
- Row/needle limit hard caps (20 / 10).
- Utility computation: empty_retrieval -> 0; zero file_recall ->
  miss_penalty 0.25; nonzero file_recall -> no miss_penalty.
- Cross-benchmark weighted means (equal metrics; different metrics;
  empty_retrieval zero).
- Counterfactual effects (records-shaped; bm25_vs_empty and
  regex_vs_bm25 utility deltas correct).
- Failure categories kept separate (ContextBench vs RepoQA enums).
- Scanner rejections: repo URL, file path, commit SHA, repo slug,
  task_id key, query key, gold key, content_sha key, candidate key,
  evidence key, winner key, best_method key, recommended_default key,
  E_primary key, S_support key, model_id_raw key, routing_prefix
  key, raw routing prefix value, URL value, tmp path, stdout key,
  provider key, secret canary, repo key, commit_sha key, needle_path
  key, needle_description key.
- Scanner allows: method/benchmark/effect/metric names, query mode
  labels (`first_paragraph`, `needle_description`,
  `needle_path_line_range`), benchmark_results records,
  cross_benchmark_method_results records, counterfactual_effects
  records.
- Scanner rejects dict-keyed mirrors for benchmark_results /
  cross_benchmark_method_results / counterfactual_effects.
- Fail-closed generation: clean report does not raise; leaked report
  raises SystemExit; winner/ES-notation leak raises SystemExit;
  self-test failure refuses artifact generation.
- Public artifact self-scan is clean.
- Pass/partial report shapes (benchmark_results count;
  cross_benchmark_method_results includes empty_retrieval;
  counterfactual_effects count).
- CLI argument surface.

## Validation

```text
python3 -m py_compile eval/f1c_cross_benchmark_retrieval_utility.py  => PASS
python3 eval/f1c_cross_benchmark_retrieval_utility.py --self-test  => PASS (167/167 checks)
python3 eval/f1c_cross_benchmark_retrieval_utility.py \
  --contextbench-row-limit 20 --repoqa-needle-limit 10 \
  --methods bm25,regex,symbol \
  --out artifacts/f1c_cross_benchmark_retrieval_utility/\
f1c_cross_benchmark_retrieval_utility_report.json  => PASS
  (status: cross_benchmark_retrieval_utility_pass,
   forbidden_scan: pass, self_test_passed: true,
   contextbench_rows_fetched: 20, repoqa_needles_seen: 10,
   network_calls: 2, provider_calls: 0,
   retrieval_derived_counterfactual_utility_smoke: true,
   contextbench_rows_read: true,
   repoqa_needles_read: true,
   openlocus_retrieval_executed: true,
   score_py_metrics_computed: true,
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

Local real-network run and manual CI run `27911651758` produced the following aggregate metrics
(no row/needle/repo/commit/query/gold/path/span/snippet/source/
JSONL/evidence/stdout/stderr/clone-path/row-id/hash/provider/
model-routing-prefix/winner/best/default/recommended fields
committed):

```text
status: cross_benchmark_retrieval_utility_pass
contextbench_rows_fetched: 20
repoqa_needles_seen: 10
network_calls: 2
forbidden_scan: pass
provider_calls: 0
contextbench/bm25: file_recall@10=0.35, mrr=0.143107, span_f0.5@10=0.020838, success_rate=1.0, retrieval_utility=0.396196
contextbench/regex: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0, retrieval_utility=-0.25
contextbench/symbol: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0, retrieval_utility=-0.25
repoqa/bm25: file_recall@10=0.5, mrr=0.369216, span_f0.5@10=0.020817, success_rate=1.0, retrieval_utility=0.602712
repoqa/regex: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0, retrieval_utility=-0.25
repoqa/symbol: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0, retrieval_utility=-0.25
cross_benchmark bm25: file_recall@10=0.4, mrr=0.218477, span_f0.5@10=0.020831, success_rate=1.0, retrieval_utility=0.465035
cross_benchmark regex: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0, retrieval_utility=-0.25
cross_benchmark symbol: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0, retrieval_utility=-0.25
bm25_vs_empty [retrieval_utility]: delta=+0.465035
regex_vs_empty [retrieval_utility]: delta=-0.25
symbol_vs_empty [retrieval_utility]: delta=-0.25
regex_vs_bm25 [retrieval_utility]: delta=-0.715035
symbol_vs_bm25 [retrieval_utility]: delta=-0.715035
```

This is a cross-benchmark retrieval-derived utility smoke over tiny
bounded ContextBench + RepoQA subsets. It is not downstream utility,
not a formal external benchmark result, not a method winner, and not a
default/promotion signal.

## Caveats

- F1-C is the public aggregate-only cross-benchmark retrieval-derived
  utility smoke artifact. It is eval/diagnostic only. It does NOT
  change runtime, retriever, pack, backend, or default policy; it
  does NOT change EvidenceCore semantics. It is NOT a benchmark result,
  NOT downstream utility, NOT true E/S calibration, NOT an external
  benchmark performance claim, NOT a leaderboard entry, NOT a method
  winner, and NOT a promotion.
- F1-C reruns real bounded external data (ContextBench verified 20-row
  + RepoQA 10-needle Python). It does NOT combine existing C5-C or
  C5-E aggregate artifacts; it re-executes the real retrieval+score
  pipeline.
- F1-C makes NO provider calls and NO remote provider calls. All
  transient data (rows, needles, queries, gold labels, retrieval
  JSONL, scoring JSONL, repo URLs, commits, paths, spans, candidates,
  stdout/stderr) stays in memory or under `/tmp` only and is NEVER
  committed or uploaded.
- F1-C does NOT prove downstream agent value.
  `downstream_agent_value_proven=false`.
- F1-C does NOT claim true E/S calibration.
  `true_e_s_calibration_claimed=false`.
- F1-C does NOT claim external benchmark performance.
  `external_benchmark_performance_claimed=false`.
- F1-C does NOT claim a method winner.
  `method_winner_claimed=false`.
- F1-C does NOT emit winner/best_method/recommended_default fields.
- F1-C does NOT use E/S calibration notation (`E_primary` / `S_support`).
- The utility formula is a fixed diagnostic proxy. It is NOT a
  downstream solve rate, NOT a calibrated agent utility, and NOT a
  promotion metric. The miss_penalty (0.25 when file_recall@10 == 0)
  can produce negative utility values; this is intentional (zero
  recall with nonzero success_rate is a degenerate signal).
- `empty_retrieval` is a synthetic zero-context baseline. No
  retrieval run is performed for it; all metrics and utility are 0
  by construction.
- Cross-benchmark weighted means use sample counts as weights
  (ContextBench row count, RepoQA needle count). This is a
  smoke-level aggregation; it is NOT a formal meta-analysis.
- ContextBench and RepoQA failure categories are kept SEPARATE in the
  public artifact (`contextbench_failure_category_counts` and
  `repoqa_failure_category_counts`); their incompatible enums are NOT
  merged.
- All no-claim / no-runtime-change flags remain false; diagnostic flags
  (`aggregate_only_public_artifact`, `diagnostic_only`) remain true;
  the smoke-claimed flags (`retrieval_derived_counterfactual_utility_smoke`,
  `contextbench_rows_read`, `repoqa_needles_read`,
  `openlocus_retrieval_executed`, `score_py_metrics_computed`) are
  true ONLY when a real network run actually executed.
- No runtime/retriever/pack/model/backend/default-policy files were
  modified. No promotion/default/runtime claims change.
