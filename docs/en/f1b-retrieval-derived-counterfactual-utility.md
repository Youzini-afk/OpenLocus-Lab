# F1-B Retrieval-Derived Counterfactual Utility Smoke (Public Aggregate-Only Artifact)

## Scope and claim boundary

F1-B moves F1 from purely synthetic context variants to
**retrieval-derived** counterfactual utility: it uses real ContextBench
verified rows, transient public repo clones, real OpenLocus retrieval
outputs, and `eval/score.py` metrics to estimate the aggregate marginal
utility of candidate-set variants. This is empirical work, not a
control-plane artifact.

F1-B is explicitly **not** a downstream utility claim, **not** true E/S
calibration, **not** an external benchmark performance claim, **not** a
leaderboard entry, **not** a promotion/default/runtime/retriever/pack/
backend/EvidenceCore semantic change, and **not** a live/provider claim.
It makes NO provider calls and NO remote provider calls.

- Claim level: `retrieval_derived_counterfactual_utility_smoke_only`.
- Mode: `public_aggregate_contextbench_retrieval_counterfactual`;
  phase `F1-B`.
- Status enum:
  `retrieval_derived_counterfactual_utility_smoke_pass` on success;
  `partial` if some but not all variants succeed;
  `unavailable_with_reason` if none/blocked/network unavailable;
  `fail_forbidden_scan` on scanner failure.
- F1-B is **eval/diagnostic only**. It is NOT a benchmark result, NOT
  downstream utility, NOT true E/S calibration, NOT an external benchmark
  performance claim, NOT a leaderboard entry, and NOT a promotion.

### F1 -> F1-B relation

```text
F1 counterfactual evidence utility smoke (synthetic/mock tasks)
-> F1-B retrieval-derived counterfactual utility smoke
   (real ContextBench verified rows; transient /tmp clones;
    real OpenLocus retrieval; eval/score.py metrics;
    candidate-set variants derived from real retrieval;
    aggregate-only public artifact; no provider calls)
```

## Candidate-set variants

F1-B uses five fixed allowlisted candidate-set variants (records-shaped
only; no dynamic dict mirrors):

1. **`baseline_empty_candidate_set`** — empty candidate set (no
   retrieval). All metrics are zero by construction.
2. **`bm25_topk`** — BM25 retrieval candidates.
3. **`regex_topk`** — regex retrieval candidates.
4. **`symbol_topk`** — symbol retrieval candidates.
5. **`bm25_plus_symbol_topk`** — BM25 + symbol union candidates
   (approximate aggregation via max of per-method metrics).

### Deferred variant

`bm25_plus_distractor_topk` is **deferred**. A safe implementation would
require per-candidate identity tracking (which candidate came from which
method, and which is a distractor), which risks candidate identity
leakage in the public artifact. It is omitted from F1-B and documented
as deferred to a future phase that can safely track candidate provenance
without leaking per-candidate rows.

## Counterfactual effects

F1-B uses four fixed allowlisted counterfactual effects (records-shaped
only; one metric per fixed record):

1. **`bm25_candidates_vs_empty`** — (bm25_topk - baseline_empty).
2. **`regex_candidates_vs_empty`** — (regex_topk - baseline_empty).
3. **`symbol_candidates_vs_empty`** — (symbol_topk - baseline_empty).
4. **`symbol_added_to_bm25`** — (bm25_plus_symbol_topk - bm25_topk).

### Deferred effect

`distractor_added_to_bm25` is **deferred** (same reason as the deferred
variant above).

## Metrics

Aggregate retrieval/score utility metrics (NOT downstream-agent
metrics):

- `file_recall@10`
- `mrr`
- `span_f0.5@10`
- `success_rate`

## CLI

```bash
python3 -m py_compile eval/f1b_retrieval_derived_counterfactual_utility_smoke.py
python3 eval/f1b_retrieval_derived_counterfactual_utility_smoke.py --self-test
python3 eval/f1b_retrieval_derived_counterfactual_utility_smoke.py \
    --out artifacts/f1b_retrieval_derived_counterfactual_utility/\
f1b_retrieval_derived_counterfactual_utility_report.json
# Override row limit and methods:
python3 eval/f1b_retrieval_derived_counterfactual_utility_smoke.py \
    --row-limit 5 --methods bm25,regex,symbol \
    --out /tmp/f1b_smoke_report.json
```

Default mode: runs a real network smoke (transient HF rows + GitHub
clones + retrieval + score into `/tmp`). If network/openlocus is
unavailable, it produces a truthful `unavailable_with_reason` report.
No provider calls are ever made.

CLI arguments: `--self-test`, `--out`, `--row-limit` (default 5, hard
cap 10), `--methods` (default `bm25,regex,symbol`), `--query-mode`
(default `first_paragraph`), `--language-filter` (default `python`),
`--openlocus`. Unknown/private-looking arguments are rejected with a
generic `invalid arguments` message (SafeArgumentParser pattern).

## Reused helpers

F1-B imports C5-A helpers (backward-compatible; C5-A is NOT modified):

- `c5_contextbench_verified_performance_smoke._fetch_contextbench_rows`
- `c5_contextbench_verified_performance_smoke._sanitize_query`
- `c5_contextbench_verified_performance_smoke._parse_gold_context`
- `c5_contextbench_verified_performance_smoke._write_transient_jsonl`
- `c5_contextbench_verified_performance_smoke._resolve_openlocus_binary`
- `c5_contextbench_verified_performance_smoke._clone_and_checkout`
- `c5_contextbench_verified_performance_smoke._run_retrieval_and_score`
- `c5_contextbench_verified_performance_smoke._filter_score_metrics`

## Artifact identity (default committed artifact)

The committed artifact at
`artifacts/f1b_retrieval_derived_counterfactual_utility/f1b_retrieval_derived_counterfactual_utility_report.json`
is the public aggregate-only smoke artifact. Identity / boundary fields:

- `schema_version` = `f1b_retrieval_derived_counterfactual_utility_smoke.v1`
- `generated_by`, `generated_at`, `claim_level`, `status`, `mode`,
  `phase`, `methods`, `query_mode`, `language_filter`,
  `network_mode`, `openlocus_binary_source`.
- Safe true flags (only when actually true):
  `retrieval_derived_counterfactual_utility_smoke`,
  `external_benchmark_rows_read`, `openlocus_retrieval_executed`,
  `score_py_metrics_computed`, `aggregate_only_public_artifact`,
  `diagnostic_only`.
- Always-false no-claim flags:
  `true_e_s_calibration_claimed`,
  `automated_e_s_full_calibration_claimed`,
  `human_e_s_calibration_claimed`,
  `downstream_agent_value_proven`, `live_llm_agent`,
  `provider_calls_made`, `remote_provider_calls_made`,
  `external_benchmark_performance_claimed`,
  `leaderboard_entry_claimed`, `promotion_ready`,
  `default_should_change`, `runtime_behavior_changed`,
  `retriever_changed`, `pack_builder_changed`, `backend_changed`,
  `default_policy_changed`, `evidencecore_semantics_changed`.
- `variant_results`: list of fixed records
  `{variant, row_count, file_recall@10, mrr, span_f0.5@10,
  success_rate, failure_category_counts}`.
- `counterfactual_effects`: list of fixed records
  `{baseline_variant, treatment_variant, effect_name, metric, delta}`.
- `method_inputs`: list of fixed records `{method, row_count}`.
- `input_summary`: `row_limit_requested`, `methods`, `query_mode`,
  `language_filter`, `variants`, `effects`, `metrics`, aggregate row
  counts.
- `failure_category_counts`: fixed category counts only.
- `self_test_passed`.
- `forbidden_scan` summary (fail-closed before writing JSON).
- `framing`: fixed no-claim framing fields.

## Forbidden scanner (public, fail-closed)

A strict forbidden-output scanner runs fail-closed before writing the
public JSON. Rejects forbidden dict keys anywhere (`task_id`,
`repo_url`, `base_commit`, `query`, `gold`, `gold_paths`, `gold_lines`,
`gold_context`, `path`, `file`, `snippet`, `code`, `patch`, `diff`,
`stdout`, `stderr`, `content_sha`, `candidate`, `evidence`, `winner`,
`best`, `recommended_default`, `api_key`, `base_url`, `provider_key`,
`secret`, `token`, `model_id_raw`, `E_primary`, `S_support`, etc.) and
value patterns: ANY URL (no URL allowlist), 32+ char hex digests, 40-char
commit SHAs, secret-like strings, path-like strings with file extensions,
`/tmp/` workspace paths, `task_N` task-identifier values, repo slugs,
patch/diff markers, stack traces, multiline strings, raw JSON fragments,
raw line ranges, raw model routing prefixes, and the self-test sentinel.

No `winner` / `best` / `recommended_default` fields are emitted. No
E/S calibration notation (`E_primary` / `S_support`) is used.

The scanner runs ONLY against the final public aggregate artifact. The
internal task/label/run JSONL (which contain paths/spans/queries/gold)
are kept in-memory or under `/tmp` only, never scanned against the
public contract, and never committed.

## Self-tests

- Artifact identity fields (schema, claim, status, mode, phase,
  generated_by).
- Safe true flags present; no-claim flags false.
- Variants and effects are fixed allowlists.
- Records-shaped containers (`variant_results`, `counterfactual_effects`,
  `method_inputs` are lists; no dynamic dict mirrors).
- Variant metric extraction (empty candidate set -> zero; synthetic
  score metrics extracted; missing metric -> 0.0).
- Variant aggregation (row count; mean computation).
- Counterfactual effects computation (records-shaped; delta correct for
  bm25_vs_empty and symbol_added_to_bm25).
- Scanner rejections: repo URL, file path, commit SHA, repo slug,
  task_id key, query key, gold key, content_sha key, candidate key,
  evidence key, winner key, best key, recommended_default key, raw
  routing prefix, URL value, tmp path, stdout key, provider key,
  sentinel canary.
- Scanner allows: variant names, effect names, metric names, method
  names, variant_results records, counterfactual_effects records,
  failure category token.
- Fail-closed generation: clean report does not raise; leaked report
  raises SystemExit; self-test failure refuses artifact generation.
- Public artifact self-scan is clean (no forbidden key anywhere).
- CLI argument surface.

## Validation

```text
python3 -m py_compile eval/f1b_retrieval_derived_counterfactual_utility_smoke.py  => PASS
python3 eval/f1b_retrieval_derived_counterfactual_utility_smoke.py --self-test  => PASS (95/95 checks)
python3 eval/f1b_retrieval_derived_counterfactual_utility_smoke.py \
  --out artifacts/f1b_retrieval_derived_counterfactual_utility/\
f1b_retrieval_derived_counterfactual_utility_report.json  => PASS
  (status: retrieval_derived_counterfactual_utility_smoke_pass,
   forbidden_scan: pass, self_test_passed: true,
   rows_fetched: 5, rows_successful: 5,
   retrieval_derived_counterfactual_utility_smoke: true,
   external_benchmark_rows_read: true,
   openlocus_retrieval_executed: true,
   score_py_metrics_computed: true,
   downstream_agent_value_proven: false,
   true_e_s_calibration_claimed: false,
   external_benchmark_performance_claimed: false,
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

Manual CI run `27903995230`
(`f1b-retrieval-derived-utility-smoke.yml`,
`enable_external_benchmark_network=true`) also passed. The uploaded
aggregate report matched the committed artifact surface and passed the
same no-claim/scanner checks:

```text
status: retrieval_derived_counterfactual_utility_smoke_pass
rows_fetched: 5
rows_successful: 5
methods: bm25,regex,symbol
forbidden_scan: pass
baseline_empty_candidate_set: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=0.0
bm25_topk: file_recall@10=0.4, mrr=0.225, span_f0.5@10=0.015905, success_rate=1.0
regex_topk: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0
symbol_topk: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0
bm25_plus_symbol_topk: file_recall@10=0.4, mrr=0.225, span_f0.5@10=0.015905, success_rate=1.0
bm25_candidates_vs_empty: file_recall@10 delta=+0.4, mrr delta=+0.225, success_rate delta=+1.0
symbol_added_to_bm25: file_recall@10 delta=0.0, mrr delta=0.0, success_rate delta=0.0
```

This is a retrieval-derived candidate-set utility smoke over a tiny
ContextBench subset. It is not downstream utility, not a formal external
benchmark result, and not a default/promotion signal.

## Caveats

- F1-B is the public aggregate-only retrieval-derived counterfactual
  utility smoke artifact. It is eval/diagnostic only. It does NOT
  change runtime, retriever, pack, backend, or default policy; it
  does NOT change EvidenceCore semantics. It is NOT a benchmark result,
  NOT downstream utility, NOT true E/S calibration, NOT an external
  benchmark performance claim, NOT a leaderboard entry, and NOT a
  promotion.
- F1-B makes NO provider calls and NO remote provider calls. It uses
  real ContextBench verified rows, transient GitHub clones, real
  OpenLocus retrieval, and `eval/score.py` metrics. All transient data
  (rows, queries, gold labels, retrieval JSONL, scoring JSONL, repo
  URLs, commits, paths, spans, candidates, stdout/stderr) stays in
  memory or under `/tmp` only and is NEVER committed or uploaded.
- F1-B does NOT prove downstream agent value.
  `downstream_agent_value_proven=false`.
- F1-B does NOT claim true E/S calibration.
  `true_e_s_calibration_claimed=false`.
- F1-B does NOT claim external benchmark performance.
  `external_benchmark_performance_claimed=false`.
- F1-B does NOT emit winner/best/recommended-default fields.
- F1-B does NOT use E/S calibration notation (`E_primary` / `S_support`).
- `bm25_plus_distractor_topk` variant and `distractor_added_to_bm25`
  effect are **deferred** (safe implementation requires per-candidate
  identity tracking which risks leakage; deferred to a future phase).
- The `bm25_plus_symbol_topk` variant uses an approximate aggregation
  (max of per-method metrics) rather than a true union candidate set.
  This is a smoke-level approximation, NOT a precise union metric.
- All no-claim / no-runtime-change flags remain false; diagnostic flags
  (`aggregate_only_public_artifact`, `diagnostic_only`) remain true;
  the smoke-claimed flags (`retrieval_derived_counterfactual_utility_smoke`,
  `external_benchmark_rows_read`, `openlocus_retrieval_executed`,
  `score_py_metrics_computed`) are true ONLY when a real network run
  actually executed.
- No runtime/retriever/pack/model/backend/default-policy files were
  modified. No promotion/default/runtime claims change.
