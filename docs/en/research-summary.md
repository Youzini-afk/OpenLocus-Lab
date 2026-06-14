# OpenLocus Research Summary

For the current research-conclusion synthesis, see
[`docs/en/current-research-conclusions.md`](current-research-conclusions.md)
or the index page [`docs/current-research-conclusions.md`](../current-research-conclusions.md).

当前研究结论总报告见
[`docs/zh/current-research-conclusions.md`](../zh/current-research-conclusions.md)，
入口索引见 [`docs/current-research-conclusions.md`](../current-research-conclusions.md)。

This document will be updated after each evidence-gated stage. The detailed
chronological notes below are preserved for traceability; the current high-level
research conclusion is summarized first.

## Current status update — 2026-06-13

The research program has moved beyond the original local-only benchmark stages
into controlled real-provider CI experiments. The current conclusion is not a
promotion decision; it is a sharper research boundary:

```text
RRF remains the recall base.
symbol/regex remain precision anchors.
query_noise_plus_rrf_agree_min remains the strongest guard candidate.
real dense embeddings have candidate/file-level signal but are unstable as global dense.
P20-LS-A blocks low-context/query-only LLM aliases, not rich-context LLM retrieval.
P21-G should prioritize cross-model context injection effects, richer code context, quality, latency, and cost.
Dense/QuIVer/LLM-derived/graph remain supporting/diagnostic/candidate only.
promotion_ready=false and current_default_should_change=false.
```

Most important recent finding: **L1/L2 and P20-LS-A exposed the weakness of
under-contextualized model retrieval**. L1/L2 showed dense-only/global dense risk
with `BAAI/bge-m3` and the conservative `path_plus_symbol` view at
`60 tasks / 1000 records / 2000 files`: four large-repo slices all had
`primary_false_positive_rate=1.0`, very low `SpanF0.5`, and unstable file recall.
P20-LS-A showed the same pattern for low-context/query-only LLM aliases: schema
and guardrails passed, but quality failed. This blocks dense-only/global dense
and low-context aliases from primary/default use, and shifts the next phase to
P21-G: context atoms, context packs, model profiles, roles, layouts, richer
snippets/candidate metadata, and explicit latency/cost accounting.

Current detailed conclusion reports:

- [`docs/zh/current-research-conclusions.md`](../zh/current-research-conclusions.md) /
  [`docs/en/current-research-conclusions.md`](current-research-conclusions.md)
- [`docs/zh/real-provider-ci-large-scale.md`](../zh/real-provider-ci-large-scale.md) /
  [`docs/en/real-provider-ci-large-scale.md`](real-provider-ci-large-scale.md)
- [`p20-llm-large-scale.md`](p20-llm-large-scale.md)
- [`p21-g-cross-model-context-injection.md`](p21-g-cross-model-context-injection.md)
- [`real-provider-ci-scale-p8-p9.md`](real-provider-ci-scale-p8-p9.md)
- [`real-provider-p7-summary.md`](real-provider-p7-summary.md)

Next research direction: freeze the L2 suite, attribute false positives, then
run P21-G cross-model context-injection experiments on public/opt-in corpora:
context atom screening, context pack ladders, LLM rerank/filter/span-narrow over
local candidates, inventory-grounded aliases, and prompt/context/layout matrices. Continue excluding
secrets, ignored files, provider keys, and private labels/gold answers, but do
not let context minimization dominate quality.

## P25 Bucket-Routed LLM Role Policy (2026-06-14)

A deterministic P25 policy evaluator (`eval/p25_bucket_policy.py`) is now
available. The committed report is a sanitized synthetic self-test scaffold
(`status=self_test_only`, `not_quality_evidence=true`), not a quality result.
Real P25 evaluation now requires ephemeral SCORE-phase records produced by
`eval/p21_llm_rich_candidate.py --p25-policy-records-out`; those records stay
under runner temp and are not uploaded, while P25 uploads aggregate metrics
only. The evaluator compares five policies: `candidate_baseline`,
`global_span_narrow`, `global_filter`, `global_abstain_filter`, and
`bucket_routed_v0`. The bucket-routed policy routes `llm_span_narrow` to
likely-positive/high-confidence buckets, routes `llm_filter`/`llm_abstain_filter`
to negative/dense-false-positive/ambiguous buckets using a fixed a-priori
negative strategy, skips LLM calls when an exact-symbol-plus-unique-anchor signal
is available, and falls back to the candidate baseline otherwise. Aggregate P21
summaries and non-ephemeral schemas are rejected with
`status=insufficient_task_detail`; no policy is promotion-ready or default-ready. See
[`docs/p25-bucket-routed-policy.md`](p25-bucket-routed-policy.md).

The first real P25 remote smoke then ran six successful aggregate policy runs
(`Flash/Kimi/GLM × py_flask/js_express`, 18 bucket-sampled tasks each) via the
safe P21→P25 ephemeral SCORE handoff. `bucket_routed_v0` strongly reduced false
spans (`108 -> 28`) and mean PFP (`-0.0926`), while losing some gold spans
(`24 -> 21`). Mean SpanF0.5 delta was only slightly positive (`+0.0026`) and
repo/model-dependent. This makes P25 useful as a false-primary reducer component
for P30 Admission V3, not a default/promotion candidate. Remote summary:
[`docs/p25-bucket-routed-policy-remote-smoke.md`](p25-bucket-routed-policy-remote-smoke.md).

## P30 Admission Model V3 (2026-06-14)

P30 adds a deterministic explainable admission model evaluator
(`eval/p30_admission_model_v3.py`) as a research-only follow-on to P25.
The committed artifact is a sanitized synthetic self-test scaffold
(`status=self_test_only`, `not_quality_evidence=true`) and is not a quality
result. P30 consumes the same ephemeral `p25-policy-records-ephemeral-v1`
records produced by `eval/p21_llm_rich_candidate.py --p25-policy-records-out`,
rejects aggregate summaries and non-ephemeral schemas, and routes only from
RUN-phase public/observable features (`task_bucket`, `task_risk_tags`,
`route_features`). Labels, gold, `score_group`, and outcome metrics are used
only for aggregate scoring after actions are chosen.

Allowed admission actions are: `abstain`, `admit_symbol_regex_union`,
`admit_rrf_primary`, `admit_llm_span_narrow`, `apply_llm_filter`,
`supporting_only`, and `weak_candidate_only`. The `admission_v3` scorecard
uses monotonic feature scores and hard guards around query noise,
exact/unique symbol anchors, symbol/regex/local anchors, RRF-backed-by-anchor
signals, LLM span-narrow validity/within-candidate, and negative/ambiguous/
dense-false-positive buckets. Dense and graph signals are allowed only as
supporting features; they cannot invent primary evidence.

The evaluator compares `candidate_baseline`, `llm_span_narrow`, `llm_filter`,
`llm_abstain_filter`, `bucket_routed_v0` (reused from P25), and
`admission_v3`. Aggregates include task count, SpanF0.5, PFP, added gold/false
spans, filter gold kill rate, abstain rate, action counts, score bands,
selective risk proxy, deltas versus the candidate baseline and
`bucket_routed_v0`, and explicit outcome-fallback counters for actions that do
not have measured outcomes in a given ephemeral record. Public output is
recursively scanned for forbidden keys
(raw query/snippet/prompt/response/gold/gold_spans/private label/provider key
fields). `promotion_ready=false`, `default_should_change=false`,
`evidencecore_semantics_changed=false`, `candidate_not_fact=true`,
`external_calls=0`.

P30 is intentionally not a promotion candidate. The next validation step is to
run the evaluator against real P25 ephemeral smoke records and compare the
scorecard to P25 `bucket_routed_v0` and the P22/P23 evidence-seeking guard
surfaces. See [`docs/p30-admission-model-v3.md`](p30-admission-model-v3.md).

The first real P30 remote smoke ran six successful workflow runs
(`Flash/Kimi/GLM × py_flask/js_express`, 18 bucket-sampled tasks each). On this
smoke, `admission_v3` matched `bucket_routed_v0`'s mean PFP reduction versus
baseline (`-0.0833`) but was more conservative and lower quality: baseline
`27/102` gold/false, `bucket_routed_v0` `19/39`, and `admission_v3` `17/41`.
Mean SpanF0.5 delta was `+0.0010` for `bucket_routed_v0` versus `-0.0102` for
`admission_v3`. Non-zero fallback counts show the current ephemeral handoff does
not yet provide enough measured local-anchor outcomes/features for P30's richer
admission actions. Conclusion: no promotion; extend the handoff with measured
`symbol_regex_union` / `rrf_primary` outcomes and safe route features before
rerunning P30. Remote report:
[`docs/p30-admission-model-v3-remote-smoke.md`](p30-admission-model-v3-remote-smoke.md).

P30-H1 repaired that handoff: P21 now writes ephemeral measured outcomes for
`symbol_regex_union`, `rrf_primary`, `supporting_only`, and `weak_candidate_only`,
and only pre-SCORE safe route features; P30 reports `admission_v3_h1` as the same
scorecard evaluated over enriched handoff records. Six real runs confirmed H1
fixed measurement fallback (`missing_action_outcome_count=0` for H1), but it did
not improve quality. P25 `bucket_routed_v0` remained stronger (`20/37`
gold/false, mean ΔSpanF0.5 `+0.0020`) than `admission_v3_h1` (`18/87`, mean
ΔSpanF0.5 `-0.0350`). The bottleneck moved from missing handoff to scorecard
quality: `symbol_regex_union` admission is too broad and needs stricter
agreement/bucket guards. Report: [`docs/p30-h1-remote-smoke.md`](p30-h1-remote-smoke.md).

P30-H2 tightened local-anchor admission (`symbol_regex_union` requires exact
unique symbol or span agreement; `rrf_primary` requires RRF/anchor span agreement;
file-only agreement is downgraded). Six real runs showed H2 remained
quality-comparable and fallback-free, but did not improve quality: P25
`bucket_routed_v0` was `16/36` gold/false with mean ΔSpanF0.5 `-0.0052`, H1 was
`18/87` with `-0.0346`, and H2 was `15/90` with `-0.0370`. The bottleneck is no
longer only primary admission breadth: weak/supporting/filter actions still carry
span-level false cost. Next P30 work should add action-specific span-cost budgets
and non-primary cost accounting before further route tuning. Report:
[`docs/p30-h2-remote-smoke.md`](p30-h2-remote-smoke.md).

P30-H3 implemented action-specific span-cost accounting as a score-phase-only,
diagnostic follow-on. It does not introduce a new admission route or policy; it
derives per-action cost from existing policies (`bucket_routed_v0`,
`admission_v3_h1`, `admission_v3_h2`, and baseline comparison policies). H3
reports, per action, selected count/rate, added gold/false spans, false/gold and
gold/false ratios, net span value at 1x and 2x weighting, deltas versus baseline,
mean ΔSpanF0.5 and mean ΔPFP, gold-kill rate and false-reduction rate, and
budget-violation flags. Policy-level summaries include primary/non-primary/
unclassified false-span cost, budget violation count/rate/reasons, and worst
actions by false cost and gold kill. The dedicated artifact is
`artifacts/p30_admission_v3/p30_h3_span_cost_report.json` with schema
`p30-h3-action-span-cost-report-v1`, and the doc is
[`docs/p30-h3-span-cost-accounting.md`](p30-h3-span-cost-accounting.md).
`promotion_ready=false`, `default_should_change=false`, `diagnostic_only=true`,
`score_phase_only_accounting=true`.

The first real P30-H3 smoke completed 6 successful runs (108 tasks). Baseline
was `27/102` added gold/false spans; P25 `bucket_routed_v0` remained the
strongest reference at `19/45`; P30-H1 was `18/88`; P30-H2 was `15/90`. H3
shows P30-H1/H2 false-span cost is dominated by primary local-admit actions,
especially `admit_symbol_regex_union` and H2 `admit_rrf_primary`; `supporting_only`
mostly costs recall by killing gold rather than adding false spans. See
[`p30-h3-remote-smoke.md`](p30-h3-remote-smoke.md).

## P31 Candidate Reach Ceiling Study (2026-06-14)

P31 (`eval/p31_candidate_reach_ceiling.py`) is a deterministic, no-remote,
diagnostic-only follow-on that measures how often candidate evidence alone
reaches the gold label before any routing or admission decision. It is
SCORE-phase-only: labels are loaded only after RUN and are used only for
aggregate metrics.

Inputs are the same ephemeral `p25-policy-records-ephemeral-v1` records used by
P25/P30. P31-H1 extends the P21 rich-candidate handoff so ephemeral records now
carry lightweight candidate pools (`p31_candidate_pools`) and private SCORE-phase
gold spans (`p31_score_gold`), marked with
`p31_h1_candidate_reach_handoff=true` and schema
`p31-h1-candidate-reach-handoff-v1`. Pool items keep only `rank`, `path`,
`start_line`, `end_line`, and optional `content_sha`, `score`, and `channels`;
no snippets, raw queries, prompts, responses, or provider fields. When H1 pools
are absent, P31 computes outcome-only fallback metrics and reports
`candidate_pool_availability=missing_candidate_pool` with
`reach_metrics_available=false`, rather than fabricating zeros. When pools and
gold spans are present, it reports `GoldFileReach@K`, `GoldSpanReach@K`,
`GoldSpanExactReach@K`, `CandidateAbsentRate@K`, and
`FileRightSpanWrongRate@K` for K=1/3/5/10/20.

Additional aggregate diagnostics: `ModelMissGivenGoldPresent@K` compares
strategies (`llm_span_narrow`, `llm_filter`, `llm_abstain_filter`,
`symbol_regex_union`, `rrf_primary`, `bucket_routed_v0`, `admission_v3` and H1/H2)
against `candidate_baseline`; `FilterKillGoldRate`,
`AdmissionFalsePrimaryRate`, and `AdmissionFalseSpanPerNoGoldTask` are derived
from available per-action/per-strategy outcome fields; `EvidenceCoreRejectRate`
is reported as `not_measured` if no rejection fields exist. A K=5 aggregate
failure funnel is emitted with `funnel_sums_to_positive_tasks=true`.

Public artifacts are aggregate-only: no per-task rows, raw queries, snippets,
prompts, responses, candidate paths/spans, gold spans, private labels, or
provider fields. Safety flags are locked: `promotion_ready=false`,
`default_should_change=false`, `evidencecore_semantics_changed=false`,
`candidate_not_fact=true`, `remote_calls_by_p31=0`,
`score_phase_only_metrics=true`, `aggregate_only_public_artifact=true`. Report:
[`docs/p31-candidate-reach-ceiling.md`](p31-candidate-reach-ceiling.md).

## Stage status

| Stage | Status | Summary |
|---|---|---|
| R0 Research Harness | Passed initial gate | EvidenceCore/EvidenceMeta, trace JSONL, citation validation, and smoke eval harness are implemented. |
| R1 Local Evidence Kernel | Passed initial gate | Local read, repo scan, line-based regex/text search, policy basics, path safety, and context-lite file output are implemented without remote dependencies. |
| R2 Retrieval Method Bakeoff | Passed oracle review | BM25 (Tantivy), simple symbol search, and RRF fusion added. BM25 uses line-scoring, stale-hash skip, no-overlap skip. Symbol uses boundary delimiters. RRF merges wider metadata into narrower survivors. Eval harness reports file/line/span metrics and citation validity; Rust CLI validator provides hash/excerpt-backed citation validation. |
| R3 Level0 Storage Scaffold | Passed Level0 conformance | Store traits + StoreHit materialization gate + ConservativeChunkStore + TDB Level0 placeholder. Materialization rejects empty sha / stale / invalid hits, produces citation-valid Evidence from single file read (TOCTOU-safe). |
| R4 Level0 Derived Safety | Passed oracle review | DerivedIndexView model + deterministic rule generator + policy/citation/freshness gates + JSONL store. data_level hard-gated ≤1. Secret-like tokens filtered. High-risk kinds disabled. View IDs include policy_mode/generator_version. Stale mutation detected. JSONL parse errors surfaced. No quality claim. |
| R5 Level0 Graph Scaffold | Passed oracle review | GraphEdge carries source_content_sha/source_language. Materialization via StoreHit → openlocus_store::materialize_evidence (not hand-built). Invalid ranges rejected (not clamped). build_graph validates paths/sha, builds safe_records only. Depth=1 only. Channel::Graph. Citation-valid evidence. Not a precise semantic/call graph. |
| R6 Level0 Fast Context | Passed oracle review | 4-turn deterministic loop (lexical → symbol → graph → RRF fusion). EvidencePack-compatible output with trace_id. ActionRecord per-channel replay. Token budget (chars/4). Unknown channel gate. Final citation validation drops invalid. Orchestration scaffold only, not learned agent. |
| R7 Persistent BM25 Index + Warm SLO | Passed Level0 smoke (after oracle review gates) | Persistent Tantivy index at .openlocus/index/tantivy/ with mandatory manifest at .openlocus/index/manifest.json. schema_version=r7-bm25-v1. Search/open refuse if manifest is missing or policy_hash/schema mismatches. validate_path on every hit before file read. Empty content_sha → skip. Strict range (1≤start≤end≤total_lines, no clamp). build_index filters unsafe paths. PersistentBm25Index keeps the Index/searcher open and is reused by bench warm. Warm open=1ms, query p50=1ms. Bench invalid_citations uses real citation validation (hash/range/excerpt/freshness). 32/32 safety checks passed. Level0 implementation notes only; not a general performance claim. |
| R8 AST Chunking + Symbol Extraction | Passed Level0 smoke (40/40 checks) | Tree-sitter AST-bounded chunking and symbol extraction as experimental opt-in (--chunk-strategy ast). AST symbol Evidence uses Channel::TreeSitter, narrow header spans, current-file verification. Fallback to line windows for unsupported languages/parse errors. Manifest schema r8-bm25-v2 with chunk_strategy and ast_stats. R7 manifests loadable. Line remains default. |
| R9 AST vs Line Quality Bakeoff | Safety checks passed (16/16); quality gate false (FileRecall@5 regression) | eval/ast_quality_bakeoff.py compares persistent BM25 line vs ast on R2 fixture. Latest run: AST improves SpanF0.5@10 (+0.025), FileRecall@1 (+0.143), token_waste (−0.022), wrong_span_rate (−0.087), but regresses FileRecall@5 (−0.071). Citation_validity and structural_validity 1.0 for both. Latency is comparable/noisy in this tiny CLI benchmark. AST remains experimental/opt-in; line remains default. Negative result on gate is valid; fixture is small and self-referential. |
| R10 Incremental Index + Dirty Summary + Synthetic SLO | Passed Level0 smoke (37→48 incremental checks + synthetic SLO) | Dirty summary (dirty_index) computes manifest-vs-current scan: clean, requires_update, requires_rebuild, added/modified/deleted files with counts. Added detection uses ALL manifest paths (indexed+skipped); skipped→nonempty is modified not added. File-level update (update_index) via --dirty or --path: delete-by-term + re-add, commit once, manifest file write uses tmp+rename (not single transaction with Tantivy commit). Safety gates: missing manifest, policy/schema/strategy mismatch → refuse update (load failures also caught). Context-lite writes dirty-summary.json file. eval/incremental_index_smoke.py 48 safety checks. eval/synthetic_slo_bench.py: 1000-file synthetic repo, build_ms, dirty p50, persistent_cli_search p95, one-file update p50 (true modification each iteration), 0 invalid citations. Level0 synthetic only; not a general performance claim. TDB deferred to R11. |
| R11 TDB Level0 Adapter Probe | Passed Level0 smoke (11/11 adapter checks; 29/29 total store tests with --features tdb) | Feature-gated TriviumDB 0.7.0 adapter behind `tdb` Cargo feature. TdbChunkStore opens Database<f32> with dim=1, stores chunk metadata as JSON payloads (schema `tdb_chunk_v1`). Build discipline copies ConservativeChunkStore: validate_path, TOCTOU-safe sha, skip stale/traversal/empty. Capabilities honest: metadata+chunks only, no lexical/vector/graph. Marker-based purge safety. Materialization via StoreHit → materialize_evidence(). Default build unchanged; TDB is NOT a default dependency. Placeholder preserved. Level0 probe only; no retrieval quality claim. |
| R12 Real-Repo Incremental Robustness Bench | Passed hard safety checks (149/149); latency and catastrophic growth guard are report-only | eval/real_repo_incremental_bench.py tests R10 incremental update on temp copy of OpenLocus repo. Per-run unique markers avoid self-contamination. Positive gates require path+marker conjunction in cited excerpt (not disjunction). Branch delete/rename-old markers are proven indexed before removal. Latency compare uses twin repo copies with same mutation. Growth catastrophic guard (max(3×rebuild, rebuild+64MiB)); observed 20-cycle growth ~1.10×; does not prove long-term bounded growth. sys.exit(1) on safety failure only; latency/growth gates report-only. |
| R13 Remote Embedding / LLM-Derived Indexing Safety Scaffold | Passed Level0 safety (45/45 checks) | New crate `openlocus-provider` with EmbeddingProvider trait, MockEmbeddingProvider (deterministic blake3-based vectors, dimensions=32), DisabledEmbeddingProvider. Policy gate: remote denied by default, data_level ≤1 AND ≤metadata.max_data_level, secret scanning blocks SECRET/TOKEN/PASSWORD/API_KEY/sk_/ghp_/AKIA. Dense JSONL store at .openlocus/embeddings/vectors.jsonl stores EmbeddingRecord (vectors present, no raw text). Audit JSONL at .openlocus/audit/embeddings.jsonl (no raw text/vector/query). CLI uses query_sha/query_len (no raw query). Search produces StoreHits → materialize_evidence(Channel::Dense). Short file ranges: end_line=min(total_lines,8). Audit events: query_embed/allow/block/provider_unavailable (not cache_hit). CLI: provider status/audit, dense build/search/purge. 45/45 safety checks. Integration/safety only; not real semantic retrieval. |
| R14 Scaled Evidence Benchmark Foundation | Safety foundation passed (0 critical leakage; fail-closed architecture) | Scaled benchmark program with S/M/L/X tiers. R14-S: 4 logical repo groups from one OpenLocus workspace snapshot, 48 tasks, 48 labels, 47 hard negatives. Fail-closed safety: runner/scorer isolation (run=public tasks only, score=labels only), isolated temp roots per repo group, isolated `.openlocus/policy.toml` from repo lock, unknown repo_id refusal, citation validity must be 1.0 with Rust hash/range validation, runtime canary retrieval, repo lock content manifest re-verification (normalized SHA-256 per file sorted). Span-overlap hard_negative_hit_rate@10 + negative_nonempty_rate@10. eval/r14_generate_dataset.py, eval/r14_benchmark.py (strict RUN/SCORE phases), eval/r14_leakage_check.py (8 static checks, 0 critical), eval/r14_smoke.py (HARD FAIL, no best-effort). R14-S is a safety foundation, not a quality conclusion. R14-M partial. R14-L/X not populated (running --tier L/X fails). Graph precision is future feature track. |
| R15 External Multi-Repo Benchmark Expansion | Safety foundation passed (112/112 smoke checks) | 9 independent external repos across 5 languages, 166 medium tasks, 270 hard negatives. Regex FileRecall@1=0.852, BM25=0.548 on R15-M. BM25 negative_nonempty_rate@10=0.645. Mined benchmark expansion, not quality conclusion. |
| R16 Multi-Method Quality Bakeoff | All safety gates passed across R14-S/R15-M/R15-stress | Cross-matrix bakeoff of regex/bm25/symbol/rrf. RRF wins R15-M recall (0.933/0.993/0.959) but inherits BM25 negative false positives (0.645/0.684). Symbol best span precision (0.310 SpanF0.5, 0.052 hard_neg, 0.000 neg_nonempty). No method promoted to default. Lexical/symbol/RRF only; no provider/dense/LLM claims. |
| R17 Query Intent Router / Negative Guard | All source safety gates passed; citation inherited from validated predictions | Eval-layer router/guard experiment. query_only_router_v0 eliminates R15-M negative_nonempty (0.645→0.000) with acceptable recall regression (FileRecall@1 -0.037). rrf_guarded_by_symbol_regex eliminates R15-M negative_nonempty with zero recall regression. R15-stress negative_nonempty reduces but not eliminated (0.158/0.474). No Rust core changes. No LLM/dense claims. |
| R18 Threshold/Guard Calibration Sweep | All source safety gates passed; citation inherited from validated predictions; baseline consistency checked | Eval-layer calibration sweep over 46 strategies with 8 thresholds. Train-selected `rrf_guarded_by_symbol_regex` preserves RRF recall on R15-M/holdout and drops medium negative_nonempty to 0.000, but remains weak on stress (0.474 vs symbol 0.105). Separate query-noise+agreement strategies reach stress 0.000 as observations, not promotions. Pareto frontier computed. No core changes. No LLM/dense claims. |
| R19 Large/Stress Guard Generalization | All source safety gates passed; citation inherited from validated predictions; baseline consistency checked | Eval-layer generalization validation on R15-L (294 weak/mined tasks) and R15-stress. rrf_guarded_by_symbol_regex generalizes to R15-L (recall preserved, neg_nonempty 0.917→0.042) but fails stress (0.474 vs symbol 0.105). query_noise_plus_rrf_agree_min_0.0 stress-zero observation repeated (0.000). R15-L labels are weak/mined; generalization smoke only, not promotion evidence. promotion_ready=false always. No core changes. No LLM/dense claims. |
| R20 Auto-Wide Retrieval Failure-Surface Benchmark | Static validation passed (14/14 checks, 0 critical errors) | Generated/mined/weak failure-surface dataset for retrieval failure discovery, NOT promotion evidence. 741 tasks across 25 categories and 9 R15 repos. Public tasks contain only task_id/repo_id/query/public_version/source_tier. Private labels carry all judgement fields (query_category, expected_behavior, oracle_type, risk_tags, gold_spans, hard_distractors, must_not_primary, etc.). label_quality: mined_high_confidence/mined/weak only (no human_reviewed). Static validator enforces schema, enum, coverage, anti-leakage, manifest SHA, overlap constraints. No runner/scorer matrix yet. R21 will use it. Dataset + static validator only; no Rust core changes. |
| R21 Auto-Wide Strategy Matrix | 0 critical safety issues; citation_validity=1.0 all 10 strategies; promotion_ready=false | Eval-layer strategy matrix across 10 strategies on R20 auto-wide failure-surface dataset (741 tasks, 9 repos, 25 categories). All strategies have non-zero no_gold_nonempty_rate (0.167-0.495). BM25/RRF are no-gold-heavy (both 0.495). Symbol precision-best but abstains most (0.517). rrf_guarded_by_symbol kills 22.8% recall. query_noise_plus_rrf_agree_min best R21 guard balance (no_gold_nonempty_rate 0.221, FileRecall@1 0.693 preserved). Composite/guard strategies built from base predictions and also Rust citation-validated before cleanup; no labels in RUN. R20 labels weak/mined; not promotion evidence. No Rust core changes. No LLM/dense claims. |
| R22/R27 Failure Attribution | 13 failure clusters computed; 206 bucket regressions; promotion_ready=false | Analysis-only score phase: consumes R21 artifacts + R20 labels, produces failure clusters + expanded metrics. RRF_INHERITED_BM25_FALSE_POSITIVE=110, GUARD_RECALL_KILL=67 (symbol guard), SYMBOL_EXTRACTION_MISS=91, REGEX_NORMALIZATION_BUG=1, BENCHMARK_ORACLE_SUSPECT=62. Unrun strategies (dense/TDB/graph/AST) count=0 with recommended_next_tests. EVIDENCECORE_REJECTION metric_unavailable. 206 bucket regressions; promotion_blocked_by_bucket_regression=true. No retrieval re-run. No Rust core changes. No LLM/dense claims. |
| R23 Guard Parameter Sweep | 51 strategies swept; all blocked by bucket regression; promotion_ready=false | Eval-layer guard parameter sweep consuming R21 artifacts + R20 labels; does NOT change Rust core. 51 strategies across 8 dimensions (query_noise_threshold, rrf_score_threshold, regex/symbol/regex_or_symbol_agreement, top1_top2_gap_threshold, identifier_density_threshold, candidate_channel_count_threshold) plus 15 combined strategies. R21 artifacts manifest is verified fail-closed for every recorded path, sha256, byte count, and JSONL line count. All 51 strategies have bucket regressions. Combined query_noise_1+regex_or_symbol_agree is best R23 guard balance (no_gold_nonempty_rate 0.221 vs RRF 0.495, FileRecall@1 0.693 preserved, zero guard_recall_kill). Agreement guards reduce false positives without recall cost (0.279 no_gold_nonempty at zero kill). RRF score threshold >0.02 causes sharp recall cliff. Gap threshold kills too much recall even at 0.005. No strategy eliminates false positives without unacceptable recall loss. Curves: risk_coverage, recall_vs_negative, recall_vs_false_primary, precision_vs_abstain. 6877 total bucket regressions. promotion_ready=false. not_promotion_evidence=true. No LLM/dense claims. |
| R24 QuIVer/TDB/Dense Probe | Availability + mock dense candidate-channel probe; quiver_implemented=false; promotion_ready=false | NOT a QuIVer bakeoff. QuIVer is not implemented (scan confirms no impl in Rust crates; quiver_implemented=false). TDB is a feature-gated metadata/chunk store placeholder (available=false in default build). Dense mock is available as candidate-channel safety/quality-smoke (not semantic quality). Dense real is unavailable. R24 runs dense mock build/search on R20 auto-wide tasks in isolated repo roots, preserves embeddings/audit between build/search, validates citations fail-closed, and scores against R20 labels. Dense mock produced 5,264 citation-valid candidates but poor/noisy behavior (FileRecall@1 0.024, MRR 0.073, primary_false_positive_rate 0.878) plus 99 explicit candidate rejections. Canary hardening is non-vacuous: 8 non-empty dense stores checked, path/query canaries returned evidence, raw canary/query leakage=0. dense_mock_plus_rrf confirms dense contribution but increases noise (primary_false_positive_rate 0.923, hard_distractor_hit_rate 0.215). QuIVer diagnostic fields report unavailable/not_measured with reason quiver_not_implemented; no numeric 0 output as quality result. tdb_stale_leak_count is not_applicable. No Rust core changes. No LLM/dense real/QuIVer quality claims. remote_calls=0. |
| R25 Graph+Dense Ablation | Net-negative for both graph_basic and dense_mock; default expansion blocked; promotion_ready=false | Eval-layer ablation of graph_basic and dense_mock on R20 auto-wide (741 tasks). graph_basic: net-negative (0 gold, 435 false spans → blocked). dense_mock: net-negative (2 gold, 20,273 false → blocked). rrf_plus_graph dilutes RRF (FileRecall@1 0.693→0.497). rrf_plus_dense_mock also dilutes (0.693→0.134). graph_pollution_ratio=0.0. Citation validity remains 1.0: graph/dense/composites are revalidated in R25; no_graph inherits R21 validation after R25 verifies the R21 artifact manifest before baseline use. R25 source-leak canary is regex-only with seeded self-test, not a dense-path canary. QuIVer/TDB unavailable/not_measured. No Rust core changes. No LLM/dense real/QuIVer quality claims. remote_calls=0. |
| R26 Auto-Stress-1000 | Static validation passed (19/19 checks, 0 critical errors); NOT promotion evidence | Weak/mined/deterministic stress dataset for retrieval failure discovery. 1100 tasks across exact target counts for 10 stress categories and 9 R20 repos. Uses the same external repo set as R20 and derives some queries from existing R20 tasks/labels where useful. Public tasks contain only test_id/repo_id/query/public_version/source; category/risk/judgement fields live only in private labels. Private labels carry all judgement fields. No canary tokens. Deterministic seed 42. Validator fail-closes on exact category counts, public/private schema separation, task/label query consistency, span path/range validity, SHA-256 artifact checks, and repo content manifest SHA lock recomputation. Runner/scorer matrix now provided by R29. Designed to maximize failure discovery; NOT promotion evidence. Negative/abstain cases dominate (60%). No Rust core changes. No LLM/dense claims. |
| R28 Promotion Candidate Report | promotion_ready=false; current default should not change | Conservative synthesis of R21/R23/R24/R25/R26 reports over the R20/R26 failure-surface datasets. RRF remains best recall channel, symbol remains precision anchor, query_noise_plus_rrf_agree_min is promising but not stable enough due to R23 bucket regressions and unrun R26 retrieval matrix, graph/dense expansions are blocked by R25 added_false_span > added_gold_span, QuIVer/TDB have no independent quality evidence, dense_mock is noise/safety probe only. Default recommendation: no_change_current_evidence_gated_local_retrieval. Next required tests: run R26 strategy matrix, add human-verified labels, implement real embedding/QuIVer only after runner gates exist. |
| R29 R26 Auto-Stress Strategy Matrix | promotion_ready=false; not_promotion_evidence=true; failure-surface only | Eval-layer strategy matrix across 16 strategies (4 base + 6 composite/guard + 6 graph/dense/composite) on R26 auto-stress (1100 tasks, 10 stress categories, 9 repos). Strict RUN/SCORE separation: run phase loads only public tasks + repo lock, never labels; score phase loads labels only. R26 provenance validated before run. Citation validity must be 1.0 for all strategies. 14 required failure clusters computed. Span contribution analysis for graph/dense/composites vs fresh RRF baseline. Bucket regressions across source_category/expected_behavior/oracle_type/repo_id/risk_tags. Private field scan on all JSONL artifacts. 5 unavailable strategies report reason only (no fake numeric quality). dense_mock is candidate-channel safety smoke, not semantic quality. QuIVer not implemented. No Rust core changes. No LLM/dense real/QuIVer quality claims. remote_calls=0. |
| R30 Baseline Freeze | Completed; no promotion | Frozen R29/R26 stress matrix as the comparison baseline. When raw R29 runtime artifacts were absent from checkout, R30 explicitly used committed R29 docs/manifests and recorded missing artifact status rather than fabricating original predictions. Subsequent experiments report `delta_vs_r29_*` fields against this frozen baseline. |
| R31 Real Embedding Provider Smoke | Completed; safety gates first | Implemented OpenAI-compatible real embedding provider plumbing, remote-default-deny gates, audit/no-raw-text policy, provider request headers, optional `dimensions` field support, and local mock plus real-provider smoke. Real provider access was validated, but R31 made no quality claim. |
| R32 Embedding View Bakeoff Harness | Completed; supporting-only | Added view bakeoff harness for multiple embedding views with RUN/SCORE separation. Default is local/mock; real remote runs are explicit/manual and currently remote-safe `path_plus_symbol` only. Reports FileRecall, SpanF0.5, PFP, citation validity, provider calls, and `delta_vs_r29_baseline`. Dense output remains candidate/supporting-only. |
| R33 QuIVer Readiness Diagnostics | Completed; diagnostic-only | Added BQ2/sign-magnitude diagnostics over real embeddings: BQ overlap, BQ-vs-f32 MRR, sign entropy, angular gap, centroid/shard variance. QuIVer graph/Vamana is still not implemented; R33 emits diagnostic evidence only, no ANN quality claim. |
| R34-R36 QuIVer/BQ + Anchor Prototype | Completed; no default expansion | Added offline/real-provider prototype comparisons: flat f32, BQ top-k + f32 rerank, source/test split, per-view/language ideas, and regex/symbol anchor variants. Early tiny results were optimistic, but public corpus and L1 slice runs showed added_false often exceeds added_gold. QuIVer/dense remain supporting-only. |
| R37-R38 LLM-Derived Views + Stress | Completed; not Evidence | Real LLM provider smoke succeeded. LLM output is used only for derived views/stress/failure discovery with `not_evidence=true`; it does not generate Evidence, gold labels, citation verdicts, or promotion verdicts. Private labels are not uploaded in CI. |
| R39-R40 Symbol/Regex Repair Bakeoff | Completed; needs larger validation | Offline repair bakeoff showed `regex_hybrid_normalized` and symbol extraction repair are promising recall-safe directions. They still need fixed-suite validation for bucket regressions before any default-path consideration. |
| R41-R42 Graph Role + Admission v2 | Completed; research-only | Reframed graph as supporting/rerank/explainer, not default expansion. Added admission_v2 rule research with actions like admit_primary/admit_supporting/weak_candidate/abstain, but no learned/default admission change. |
| R43-R45 Integrated Long-Run Report | Completed; promotion_ready=false | Consolidated R30-R42 outputs into real-model matrix summary, failure clusters, and promotion candidate report. Conclusion: RRF recall base, symbol precision anchor, query-noise guard best current candidate, dense/QuIVer/LLM-derived/graph all non-default. |
| P1-P7 Real Provider Bring-up | Completed; real providers usable | Ran real embedding and LLM smoke locally/CI with gitignored `.env.local` and GitHub `production` environment. SiliconFlow embedding and OpenAI-compatible LLM access were validated. P2/P3/P4/P5/P6/P7 produced first real-provider summaries; no provider URL/key committed. |
| P8/P9 Real-Provider CI Scale-Up | Completed; first public CI slices | Added `real-provider-benchmark.yml` manual workflow with `environment: production`, guarded secrets, input validation, and no private label upload. Ran small public corpus, model bakeoff (`bge-m3`, Qwen 0.6B/4B/8B), and multilingual smoke. Result: file-level signal exists, but SpanF0.5 remains low and model size did not dominate in first slices. |
| L1/L2 Real-Provider Large-Repo Slices | Completed; strong dense-only/global-dense block | Ran controlled large-repo slices across Django, Kubernetes, Next.js, and Deno. L1 showed file-recall variability and P4 false-span growth. L2 (`60 tasks / 1000 records / 2000 files`) had PFP=1.0 on all four repos, very low SpanF0.5, and unstable FileRecall. Conclusion: dense-only/global dense must remain supporting/candidate-only; next phase should freeze L2, attribute false positives, and test constrained dense. |
| P10-P14 Constrained Dense Research | Planned | Proposed next phase: freeze `real_provider_l2_v1`, attribute L2 false positives, simulate constrained candidate pools locally, run small remote constrained variants, then rerun fixed L2 only if added_gold exceeds added_false and PFP drops. No EvidenceCore changes and no promotion. |
| P20-LS LLM Large-Scale Eval Harness | P20-LS-A completed; low-context alias blocked | Bounded eval-only harness (`eval/p20_llm_large_scale.py`) for LLM-derived query aliases and stress-label generation. Remote runs require `workflow_dispatch + enable_remote_models=true + OPENLOCUS_ALLOW_REMOTE=1`. P20-LS-A ran `[mk]Kimi-K2.7-Code` on self-test plus 9 real CI corpus runs (220 real provider calls). All LS0/LS1 safety gates passed, no raw source/private labels/prompts uploaded, but 0/9 real runs passed quality: added_gold_span=289 vs added_false_span=8312 (~28.8:1 false:gold), avg fabricated_identifier_rate≈0.459. Narrow decision: stop scaling low-context/query-only LLM aliases. This is not a verdict on rich-context LLM retrieval; it motivates context-grounded rerank/filter/span-narrow experiments. No EvidenceCore changes; promotion_ready=false; default_should_change=false. |
| P21-G Cross-Model Context Injection Research | P21-G3L-R GLM tool_call confirmed under low concurrency | Research pivot from minimal-context baselines to cross-model context-injection effects. P21-G1E found rich embedding views have file/span signal but naked dense false spans dominate. P21-G2E found constrained dense (`dense_atom_signature_rrf_file_constrained`) has modest supporting value but dense remains non-primary. P21-G3L found LLM span narrowing has promising but model/repo-specific signal; filter/abstain often kill gold. P21-G3L-R added provider-level output modes (`prompt_only`, `json_object`, `json_schema_strict`, `tool_call`), fallback diagnostics, and one no-fallback schema repair retry. GLM 4-mode comparison found `tool_call` best (avg SpanNarrow Δ +0.0677), `prompt_only` blocked, `json_object` insufficient, `json_schema_strict` mixed. A sequential low-concurrency `tool_call` rerun removed 429 noise and improved GLM SpanNarrow avg Δ to +0.1361 across py_flask/js_express. Next: bucketed GLM/Kimi/Flash `span_narrow` with `tool_call` for GLM; filter/abstain remain non-default. EvidenceCore remains final authority. |
| P21-G3B Bucketed LLM Role Study | Bucketed smoke completed; global LLM roles blocked | Public task generation now exposes safe `task_bucket/task_risk_tags` and P21 runners support `round_robin_public_buckets`, so RUN can sample mixed buckets without labels/gold. First true bucketed LLM role smoke ran 6 runs (Flash/Kimi/GLM × py_flask/js_express, 18 tasks each, provider concurrency ≤6). Bucket coverage now includes abstain/weak/no_gold/ambiguous/dense_false_positive buckets. Result: all LLM roles reduce PFP materially, but often by killing gold spans; global `span_narrow` is positive on py_flask but negative on js_express mixed buckets; `filter`/`abstain` are useful as false-positive reducers only in specific buckets, not as defaults. Next: build a rule-based policy that routes `span_narrow` only to likely-positive/high-confidence tasks and `filter/abstain` only to negative/dense_false_positive/ambiguous buckets. |
| P22/P23 Evidence-Seeking Policy Surface | Decision surfaces frozen; bottlenecks decomposed | P22/P23 moves from channel bakeoffs to strategy-surface analysis. It freezes two capped local surfaces with hashes and no remote/model calls: `r20_positive` (120 positive tasks across 9 repos) and `r26_guard` (120 no-gold stress tasks across 9 repos). R20 shows RRF is still the reach base (`Reach@5=0.975`, `SpanReach@5=0.95`) but symbol has best local SpanF0.5 (`0.3169`) and `symbol_regex_union` is the best precision/reach experimental baseline candidate for P25/P30. R26 shows BM25/RRF create noisy false primary (`NoGoldFP=0.2833`) while symbol/regex/union/guard abstain, so guard stress must be evaluated separately from positive reach. Reports: `docs/p22-p23-policy-surface.md`, per-surface docs/artifacts under `docs/` and `artifacts/p22_p23/`. |
| P25 Bucket-Routed LLM Role Policy evaluator | Self-test scaffold ready; real evaluation requires ephemeral P21/P25 handoff | `eval/p25_bucket_policy.py` is deterministic and no-remote. It routes by public `task_bucket`/`task_risk_tags` and compares candidate_baseline, global span/filter/abstain, and bucket_routed_v0. Aggregate summaries/non-ephemeral schemas are rejected. First real smoke reduced false spans but also some gold spans; useful as P30 false-primary reducer, not default. Report: `docs/p25-bucket-routed-policy.md`. |
| P30 Admission Model V3 | Self-test scaffold ready; real evaluation requires ephemeral P21/P25 handoff | `eval/p30_admission_model_v3.py` is deterministic, explainable, no-remote. Routes only from public task_bucket/task_risk_tags/route_features; allowed actions are abstain/admit_symbol_regex_union/admit_rrf_primary/admit_llm_span_narrow/apply_llm_filter/supporting_only/weak_candidate_only. Compares baselines plus admission_v3, reports score bands/selective_risk/deltas, and recursively scans public output for forbidden keys. Not promotion-ready; next step compare to P25 real smoke and P22/P23 guards. Report: `docs/p30-admission-model-v3.md`. |
| P31 Candidate Reach Ceiling Study | Scaffold ready; diagnostic-only, SCORE-phase-only | `eval/p31_candidate_reach_ceiling.py` measures whether candidate evidence alone reaches the gold label at K=1/3/5/10/20 before any routing or admission. It is deterministic, no-remote, and aggregate-only: no per-task rows, raw queries, snippets, prompts, responses, gold spans, private labels, or provider fields. Inputs are ephemeral P25/P30 records; records without candidate evidence pools fall back to outcome-only metrics with `candidate_pool_availability=missing_candidate_pool` and `reach_metrics_available=false`. Reports `GoldFileReach@K`, `GoldSpanReach@K`, `GoldSpanExactReach@K`, `CandidateAbsentRate@K`, `FileRightSpanWrongRate@K`, `ModelMissGivenGoldPresent@K`, `FilterKillGoldRate`, `AdmissionFalsePrimaryRate`, `AdmissionFalseSpanPerNoGoldTask`, and a K=5 failure funnel. `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `candidate_not_fact=true`, `remote_calls_by_p31=0`. Report: `docs/p31-candidate-reach-ceiling.md`. |

## R0/R1 initial findings

- Evidence precision matters immediately: the first regex implementation returned over-wide line ranges for distant matches in one file. This would have harmed token waste and Span F0.5. The fix moved R1 regex/text search to one narrow Evidence per matching line.
- Citation validation must validate more than hashes. Range validity and excerpt consistency are needed to catch incorrect spans.
- Path safety is part of evidence safety. Symlink escape protection is required before treating read output as verified current evidence.
- The current local baseline is intentionally boring: no dense, graph, TDB, or LLM indexing has been added yet. This keeps R0/R1 suitable as the control group for later bakeoffs.

## R2 findings

- **BM25 substantially improves file-level recall on the current self-referential fixture**: 0.39 vs 0.21 at k=1, 0.86 vs 0.36 at k=5.
- **Symbol search is high-precision but narrow**: only activates for definition-style queries, but when it fires, line precision is the highest of all methods (0.39) and wrong_span_rate is 0.0.
- **RRF fusion approaches BM25-level recall** while incorporating symbol precision, achieving 0.82 FileRecall@5 and 0.057 SpanF0.5@10 on the current fixture.
- **All methods produce structurally citation-valid evidence in the Python scorer**; aggregated current R2 output was also validated by the Rust CLI citation validator with `0` invalid citations (hash/range/excerpt checked).
- **Token waste is high** (~0.92) because evidence spans are often near-but-not-on narrow gold spans.
- **CLI end-to-end latency** (not warm-index): regex ~13ms, BM25 ~113ms, symbol ~161ms, RRF ~272ms.

## R3 findings

- **Materialization gate is essential and works**: empty sha rejected, stale hits rejected, invalid ranges rejected, TOCTOU-safe (sha + excerpt from same bytes), produced Evidence is citation-valid.
- **TOCTOU safety matters**: reading file bytes once and deriving both sha and excerpt from that single read prevents a modification between reads from producing inconsistent evidence.
- **ConservativeChunkStore validates paths and skips bad records**: traversal paths rejected, stale content_sha skipped, empty files produce no invalid chunks.
- **TDB placeholder provides clean Level0 surface**: returns available=false, success=false with descriptive errors, never panics.
- **This is a Level0 storage scaffold**, not a full storage bakeoff or TDB comparison.

## R4 findings

- **Safety scaffold works**: all gates are functional and block by default. High-risk kinds blocked, data_level hard-gated at ≤1 for Level0, experimental opt-in required, no remote calls.
- **Deterministic view IDs include policy_mode and generator_version**: same source/kind/generator/data_level/policy_mode/generator_version always produces the same ID; change in any produces different ID.
- **No raw full code at data_level ≤ 1**: derived text contains only metadata (line range, language, first identifier). Prevents accidental exposure in derived artifacts.
- **Secret-like tokens are aggressively filtered**: identifiers containing SECRET/TOKEN/PASSWORD/API_KEY/PRIVATE_KEY, or with prefixes sk_/ghp_/AKIA, or long high-entropy mixed strings are not emitted in tags or aliases.
- **JSONL parse errors are surfaced** (not silently skipped): `derived validate` reports parse_errors count.
- **Stale mutation is detected**: building views, modifying a source file, then validating correctly reports stale views.
- **DerivedIndexView is NOT Evidence**: cannot bypass StoreHit/materialize_evidence gate. Any future derived search must materialize source evidence.
- **This is a Level0 safety scaffold only. No quality claim about derived view relevance or usefulness.**

## R5 findings

- **StoreHit materialization gate is essential**: graph edges are converted to StoreHit and delegated to `openlocus_store::materialize_evidence()`. This ensures consistency with all other materialization paths and prevents hand-built Evidence from bypassing validation.
- **GraphEdge carries build-time sha and language**: source_content_sha and source_language allow the materializer to detect stale edges and reject invalid ranges (not clamp them).
- **build_graph validates paths and current sha**: safe_records with validated path and current sha are used for all edge builders (imports, tests, configures). Stale and path-unsafe records are counted and skipped, producing no edges.
- **Simple line-based import parsing works for Rust/Python repos**: mod/use, import/from lines are easy to parse and resolve against the path_set.
- **Config edges are noisy but bounded**: Cargo.toml/package.json link broadly to nearby source files in the fixture. This favors recall but can create many false positives; no general precision/recall claim is made.
- **Depth=1 only; depth>1 returns clear error**: not silently expanded.
- **graph inspect wraps output with artifact marker**: `artifact="graph_edges_not_evidence"` makes it clear these are not citation-valid Evidence.
- **This is a Level0 deterministic scaffold only. Not a precise call graph, type graph, or dependency graph.**

## R6 findings

- **4-turn deterministic loop works as orchestration scaffold**: lexical → symbol → graph → RRF fusion produces multi-channel evidence without any LLM planner.
- **Symbol turn is conditionally activated**: skipped when query lacks identifier-like tokens, avoiding wasted computation.
- **Token budget enforced**: `--budget N` uses chars/4 approximation; evidence trimmed from bottom if cumulative tokens exceed budget. `--max-evidence` is separate count cap.
- **Unknown channel gate**: channels outside regex/text/bm25/symbol/graph are rejected with clear error.
- **Final citation validation**: evidence filtered through `is_citation_valid` before output; invalid dropped and counted in `diagnostics.invalid_citations_dropped`.
- **EvidencePack-compatible output**: `pack` field with trace_id, budget_used. `evidence` field preserved for direct access.
- **ActionRecord per-channel replay**: each turn/channel recorded with query, result_count, latency_ms, optional error. Written to `.openlocus/traces/fast-context-<trace_id>.json`.
- **Confidence derived from top RRF score**: low confidence (<0.1) triggers a missing_question.
- **Orchestration scaffold only, not learned agent.** No adaptive re-querying, no feedback loops, no LLM planning.

## R7 findings

- **Persistent Tantivy BM25 index with manifest works**: build creates .openlocus/index/tantivy/ + .openlocus/index/manifest.json. status/validate/search/purge CLI commands all functional.
- **Manifest and policy gates enforced**: search_persistent_bm25 and PersistentBm25Index::open require the manifest and check manifest policy_hash/schema against current Policy/schema; refuse search if manifest is missing or mismatched. validate_index reports policy_hash_matches=false. Eval confirms: policy change after build → search refuses, validate detects mismatch; manifest deletion → search refuses.
- **Stale/deleted hits are skipped, not emitted**: search_persistent_bm25 re-reads every hit's current file, computes content_sha, and skips mismatches. No stale VerifiedCurrent evidence is ever produced.
- **Empty content_sha bypass prevented**: Hits with empty index_content_sha are skipped (invalid_hits_skipped++), cannot bypass stale check.
- **validate_path on every Tantivy hit**: Before reading a file from a Tantivy hit's path, validate_path is called. Invalid paths → skip. build_index also filters unsafe FileRecord paths.
- **Strict range validation, no clamping**: Chunk ranges must satisfy 1 ≤ start ≤ end ≤ total_lines. Invalid ranges → skip (invalid_hits_skipped++), not clamped.
- **Manifest enables fast staleness detection**: status_index quickly checks all indexed files' current sha against manifest entries. validate_index reports specific stale/deleted/path_unsafe files.
- **Policy exclusion works end-to-end**: .env and *.pem files are excluded by scan_repo, never indexed, and never appear in persistent search output.
- **Warm benchmark is honest**: PersistentBm25Index::open opens the Index/searcher once; same handle reused for all queries with no per-query Index::open. index_open_ms measures open cost only (1ms). index_build_ms reported separately if build was needed. invalid_citations uses real citation validation (hash/range/excerpt/freshness check), not just range.
- **Warm query latency**: On the current small self-referential workspace snapshot, warm queries take 1-2ms per query after index is opened. Open cost is 1ms.
- **Safety is preserved**: Every persistent search hit is re-verified against the current filesystem. The Tantivy stored body is never used as the final excerpt.
- **Purge is safe**: Only deletes known R7 artifact paths under .openlocus/index/. Canonicalizes paths and refuses to delete if index_dir escapes repo root.
- **This is a Level0 implementation only. No incremental update; build is always full rebuild. Warm SLO numbers are from a small self-referential codebase; not a general performance claim. R7 Level0 passed only after oracle review gates.**

## R8 findings

- **Tree-sitter AST-bounded chunking is functional as an experimental scaffold**: `openlocus-ast` crate parses Rust, Python, JavaScript, and TypeScript using Tree-sitter 0.25.x. AST chunk boundaries align with logical code structures (functions, classes, structs, etc.) rather than arbitrary line windows. Oversized nodes are split into line windows; gaps are covered by fallback line windows; no overlapping chunks.
- **AST symbol extraction produces narrow, citation-valid Evidence**: `extract_ast_symbols` extracts definition nodes with header/signature spans (max 10 lines, usually signature/header only rather than full bodies). Symbol names are extracted from Tree-sitter node fields. AST symbol Evidence uses Channel::TreeSitter and is verified against the current filesystem (hash/excerpt/freshness).
- **Fallback is correct**: Unsupported languages (e.g., Go) fall back to line-window chunking. Parse errors also fall back to line windows. No data loss. Fallback stats are visible in manifest ast_stats.
- **Opt-in, not default**: `--chunk-strategy ast` is experimental; line-window remains the default. No quality claim about AST chunking superiority until eval computes it.
- **Manifest schema r8-bm25-v2**: Includes chunk_strategy and ast_stats fields. R7 manifests (r7-bm25-v1) still loadable with default chunk_strategy=line_window_v1. Unrecognized schema versions refuse with rebuild instruction.
- **Schema/strategy mismatch refusal**: search/validate/status refuse if manifest chunk_strategy is unrecognized. R7 manifests without chunk_strategy are loaded as line_window_v1 for compatibility; R8-written manifests always include chunk_strategy. No silent search of unverifiable strategy.
- **CLI symbol search modes**: `openlocus search symbol <name> --mode regex|ast|auto`. Default auto: AST first for supported files, regex fallback for unsupported/no results. Regex mode preserves existing behavior.
- **R7 persistent smoke still passes**: Default line build continues to work with all 32 safety checks passing.
- **AST smoke eval passes 40/40 checks**: Including AST build/status/validate/search, parser-error visibility, stale mutation, narrow AST symbol header, symbol search modes, citation validation, schema mismatch, policy exclusion, default line build compatibility.
- **This is a Level0 experimental scaffold. AST chunking quality lift is NOT proven. Tree-sitter parser edge cases may exist. AST symbol extraction does not handle all symbol patterns (re-exports, aliased imports). No incremental update for AST index.**

## R9 findings

- **AST vs line persistent BM25 bakeoff completed on R2 fixture (28 tasks)**: `eval/ast_quality_bakeoff.py` runs both strategies through purge/build/search/score and produces a combined report with delta, quality gate, and safety checks.
- **AST improves SpanF0.5@10 (+0.025, latest run ~63% relative)** and FileRecall@1 (+0.143, 36% relative): AST-bounded chunks align better with logical code structures, producing more targeted evidence spans and better top-1 file retrieval.
- **AST regresses FileRecall@5 (−0.071 in the latest run)**: More granular AST chunks can dilute BM25 scores across multiple chunks per file, reducing the chance that any single chunk ranks a file into top-5. This is the quality gate failure.
- **AST reduces token waste (−0.022) and wrong_span_rate (−0.087 in the latest run)**: Narrower evidence spans waste fewer tokens and overlap gold spans more often.
- **Quality gate is false** (FileRecall@5 regression). **Safety checks all pass** (16/16). Citation_validity and structural_validity are 1.0 for both strategies.
- **Latency is comparable** (ratio ~1.0). Both strategies have similar per-query latency on this fixture.
- **AST remains experimental/opt-in; line remains default.** The fixture is too small and self-referential to generalise. A larger, diverse codebase eval would be needed for a definitive quality comparison.
- **Negative result is valid**: the bakeoff correctly captures a real trade-off between span precision (AST better) and broad file recall at k>1 (line more conservative).

## R10 findings

- **Incremental update works correctly**: dirty_index detects added/modified/deleted files; update_index applies batch changes (delete-by-term + re-add + commit + manifest file write via tmp+rename). Post-update status shows clean. 48/48 incremental smoke checks passed.
- **Dirty summary is accurate and safe**: distinguishes requires_update (file changes) from requires_rebuild (policy/schema/strategy mismatch or corrupt manifest). Policy-excluded added files do not dirty. Skipped entries (empty files, read errors) with unchanged sha are clean; skipped→nonempty is reported as modified (not added). Status never says clean if validate would fail.
- **Safety gates enforced on update**: missing manifest, policy hash mismatch, schema mismatch, and unrecognized chunk strategy all refuse update with clear error messages requiring rebuild. Manifest load failures are also caught gracefully.
- **Tantivy delete-by-term prevents duplicate docs**: `Term::from_field_text(path_field, path)` correctly removes all chunks for a path before re-adding. Deletes are tombstones until merge (documented, not a bug).
- **Context-lite dirty summary written to file**: R10 writes actual dirty index status to `.openlocus/context/dirty-summary.json`. The `ContextLitePack.dirty_summary` struct field remains `None` (the file is the surface, not the struct field).
- **Synthetic SLO benchmark (1000 files)**: latest run build_ms=147, dirty_status p50≈44ms/p95≈48ms, persistent_cli_search p95≈15ms, bench_warm open-once query p95=0ms, one-file update p50≈115ms/p95≈117ms (true modification each iteration), 0 invalid citations. Level0 synthetic only; not a general performance claim. `persistent_cli_search` is CLI-measured; `bench_warm` is the Rust CLI's internal open-once query timing over a synthetic dataset.
- **TDB deferred to R11**: R10 focused on incremental index; TDB moves to R11.
- **Not a single transaction**: Tantivy commit and manifest file write are separate; a crash between may leave a safe but inconsistent state requiring rebuild or re-update.

## R11 findings

- **TriviumDB 0.7.0 compiles and works as an optional dependency**: Feature-gated behind `tdb = ["dep:triviumdb"]`. Default build does not compile TDB. `cargo test --workspace` passes without TDB. `cargo test -p openlocus-store --features tdb` passes with 29/29 tests.
- **TdbChunkStore is a Level0 adapter probe**: Opens `Database<f32>` with `dim=1`, stores chunk metadata as JSON payloads (schema `tdb_chunk_v1`). The `[0.0]` vector is a smoke probe, NOT vector quality. Capabilities honestly report metadata+chunks only, no lexical/vector/graph.
- **Build discipline preserved**: validate_path, TOCTOU-safe sha, skip stale/traversal/empty — same as ConservativeChunkStore.
- **Marker-based purge safety**: Adapter writes an `.openlocus_marker` file; purge verifies marker before deletion and refuses without it.
- **Materialization conformance enforced**: TDB chunk records → StoreHit → materialize_evidence(). Stale, empty-sha, and invalid-range hits correctly rejected.
- **No default dependency on TDB**: TDB is NOT a default backend. It does not replace Tantivy persistent BM25 or the conservative store. Placeholder preserved.
- **No retrieval quality claim**: This is a Level0 wiring/persistence probe. No comparison against Tantivy BM25 or conservative store quality.

## R12 findings

- **Real-repo incremental update passes this Level0 sample**: On a temp copy of the OpenLocus repository (mixed Rust, Python, TypeScript, Markdown), incremental update correctly handles sampled modify, add, delete, rename, policy-excluded, and batch workloads. No stale VerifiedCurrent evidence produced.
- **All hard safety checks pass**: 149/149 hard safety checks pass (dirty detection, update success, clean after update, validate valid, collected marker-search citations invalid_count=0, no stale VerifiedCurrent for deleted/old paths).
- **Per-run unique markers avoid self-contamination**: Fixed markers appeared in copied docs/scripts causing false positives. Per-run suffixes (8-hex chars) and pre-build assert prevent this.
- **Positive gates use path+marker conjunction**: `evidence_has_path_and_marker` requires both path fragment AND marker in the cited excerpt of the same evidence item. Previous disjunction (path OR marker) could pass from unrelated evidence.
- **Citation validity maintained for collected marker-search evidence**: total_invalid_citations=0 across all workloads. Collected evidence validated through `openlocus citations validate` with validator returncode==0.
- **Latency comparison uses twin repo copies**: Both update and rebuild start from same state with same mutation applied. Incremental update ~42% faster on this sample. Gate is report-only; does not cause exit failure.
- **Growth is a catastrophic guard, not bounded proof**: 20 cycles observed growth ~1.11×; catastrophic guard passed (max(3×rebuild, rebuild+64MiB)). Does not prove long-term bounded growth.
- **Level0 one real-repo sample only**: OpenLocus temp copy is one data point. Not a general performance or robustness claim.

## Historical verification snapshot

This snapshot is preserved from the earlier local-first stages. It is not the
latest complete real-provider CI status; see the current-status section and the
L1/L2 reports above for recent remote-provider runs.

```text
Rust tests: 243 passed (193 existing + 50 new in openlocus-provider); 29 passed (store with --features tdb)
fmt: clean
clippy: clean with -D warnings (default and --features tdb)
CLI commands: read, scan, search regex/text/bm25/symbol, retrieve, fast-context, citations validate, context-lite, store status/build/purge, derived build/validate/inspect/purge, graph build/inspect, impact, tests, index build/status/dirty/validate/update/purge, search bm25 --index persistent (policy gate enforced), search symbol --mode regex|ast|auto, index build --chunk-strategy line|ast, bench warm (honest: open-once + real citation validation), provider status/audit, dense build/search/purge, version
Eval: regex/bm25/symbol/rrf on fixtures/r2.jsonl; storage_level0_smoke; derived_level0_safety (13/13 checks passed); graph_level0_smoke (11/11 checks passed); fast_context_level0_smoke (14/14 checks passed); persistent_index_smoke (32/32 checks passed, incl. policy/manifest gates + strict validation + honest bench); ast_chunking_smoke (40/40 checks passed); ast_quality_bakeoff (16/16 safety checks passed, quality_gate_passed=false due to FileRecall@5 regression); incremental_index_smoke (48/48 checks passed, incl. dirty summary + skipped empty file + file-level update + policy/schema/strategy gates + citation validation); synthetic_slo_bench (1000 files, build_ms, dirty p50/p95, persistent_cli_search p95, bench_warm open-once query p95, one-file update p50/p95, 0 invalid citations, Level0 synthetic only); real_repo_incremental_bench (modify/add/delete/rename/policy_exclude/batch/latency_compare/growth_cycles on OpenLocus temp copy, total_invalid_citations=0, no stale VerifiedCurrent violations, Level0 one real-repo sample only); provider_dense_safety (45/45 checks passed, incl. remote/outbound defaults, experimental gate, vector/audit no raw text, secret blocking, stale rejection, disabled/unknown provider audit events, query_sha not raw query, short file range, citation validity)
Structural validity: 1.0 across all methods
Citation validity: Python scorer reports 1.0 across methods (`path_range_only` unless Python blake3 is installed); Rust CLI citation validator confirmed current aggregated R2 evidence has `0` invalid citations with hash/range/excerpt checks
Remote dependency: none
TDB dependency: optional only (behind `tdb` feature; not in default build)
LLM dependency: none (rule extractor only)
Graph: deterministic, local-only, depth=1 only
Fast-context: 4-turn deterministic loop, EvidencePack output, ActionRecord replay, token budget, unknown channel gate, final citation validation, no LLM, remote_calls=0
Persistent index: r8-bm25-v2, mandatory manifest + policy gate enforced, validate_path per hit, empty sha skip, strict range no clamp, chunk_strategy line|ast, ast_stats in manifest, warm open=1ms p50=1ms, 32/32 R7 safety checks + 40/40 R8 AST safety checks + 48/48 R10 incremental safety checks
Incremental update: dirty summary (added/modified/deleted), skipped entries tracked (not falsely added), file-level update (--dirty, --path), manifest file write via tmp+rename (not single transaction with Tantivy commit), Tantivy delete-by-term, policy/schema/strategy mismatch + load failure refusal
TDB adapter: Level0 probe, feature-gated, dim=1 smoke, metadata+chunks only, marker-based purge, materialization conformance, no default dependency, no retrieval quality claim
Real-repo bench: Level0 one real-repo sample (OpenLocus temp copy), per-run unique markers avoid self-contamination, cited-excerpt path+marker conjunction gates, branch old/delete markers proven indexed before removal, sampled modify/add/delete/rename/policy_exclude/batch workloads pass, latency_compare uses twin repos (report-only gate), growth_cycles catastrophic guard (observed 20-cycle ~1.10×, does not prove long-term bounded), total_invalid_citations=0, citations_validator_ok=true, no stale VerifiedCurrent violations, sys.exit(1) on safety failure only
Provider/dense scaffold: MockEmbeddingProvider deterministic blake3 vectors dim=32, gate enforces data_level≤1 AND data_level≤metadata.max_data_level, secret scanning blocks SECRET/TOKEN/PASSWORD/API_KEY/sk_/ghp_/AKIA, audit uses query_embed/allow/block/provider_unavailable (not cache_hit), CLI uses query_sha/query_len (no raw query), short file end_line=min(total_lines,8), vector store has vectors but no raw text, audit has no raw text/vector/query, 45/45 safety checks, integration/safety only — not real semantic retrieval
R14 benchmark foundation: 4 logical repo groups from one OpenLocus workspace snapshot, 48 tasks (sanity), 48 labels, 47 hard negatives; fail-closed safety (runner/scorer isolation, isolated temp roots, isolated policy.toml from repo lock, unknown repo_id refusal, citation validity=1.0 via Rust validator, runtime canary retrieval, repo lock manifest re-verification); span-overlap hard_negative_hit_rate@10 + negative_nonempty_rate@10; R14-S is safety foundation, not quality conclusion; graph precision is future feature track
R15 external multi-repo expansion: 9 independent external repos (fast-context-mcp, grok2api, infinite-canvas, gemini-web2api, windsurf2api, kiro2, triviumdb, smartsearch, codex2api) across 5 languages (Rust, Python, Go, JS, TS); 166 medium tasks, 270 hard negatives; multi-language symbol extraction; absolute source paths; isolated roots with repo_id-specific allowlist source-file copying (no whole-repo copy, no symlinks/artifacts); runtime `.openlocus` traces cleaned/audited between queries; strict Rust citation validation before cleanup; exact/single repo_id-prefix scoring path matching; regex FileRecall@1=0.852, BM25 FileRecall@1=0.548; BM25 negative_nonempty_rate@10=0.645; 112/112 smoke checks passed; mined benchmark expansion, not quality conclusion
R16 multi-method quality bakeoff: cross-matrix bakeoff of regex/bm25/symbol/rrf across R14-S/R15-M/R15-stress; all safety gates passed (safety_passed=true, citation_validity=1.0, citation_hash_checked=true, canary_retrieval.passed=true); RRF wins R15-M recall (FileRecall@1 0.933, @5/10 0.993, MRR 0.959) but inherits BM25 negative_nonempty false positives (0.645 R15-M, 0.684 stress); symbol best span precision (0.310 SpanF0.5, 0.052 hard_neg, 0.000 neg_nonempty on R15-M); no method promoted to universal default; lexical/symbol/RRF only; no provider/dense/LLM claims; no remote calls
R17 query intent router / negative guard: eval-layer experiment; does NOT change Rust core; query_only_router_v0 eliminates R15-M negative_nonempty (0.645→0.000) with acceptable recall regression (FileRecall@1 0.904 vs 0.941); rrf_guarded_by_symbol_regex eliminates R15-M negative_nonempty with zero recall regression; R15-stress negative_nonempty reduces but not eliminated (0.158/0.474); citation safety inherited from validated source predictions; baseline prediction/report consistency checked; no LLM/dense claims; remote_calls=0
R18 threshold/guard calibration sweep: eval-layer sweep over 46 strategies with 8 thresholds on R15-M and R15-stress; train-selected rrf_guarded_by_symbol_regex preserves RRF recall on R15-M/holdout and drops medium negative_nonempty to 0.000, but remains weak on stress (0.474 vs symbol 0.105); separate query_noise_plus_rrf_agree_min strategies reach stress 0.000 as observations, not promotions; Pareto frontier computed; no core changes; no LLM/dense claims; remote_calls=0
R19 large/stress guard generalization: eval-layer generalization validation on R15-L (294 weak/mined tasks) and R15-stress; rrf_guarded_by_symbol_regex generalizes to R15-L (recall preserved, neg_nonempty 0.917→0.042) but fails stress (0.474 vs symbol 0.105); query_noise_plus_rrf_agree_min_0.0 stress-zero observation repeated (0.000); R15-L labels are weak/mined; generalization smoke only, not promotion evidence; promotion_ready=false always; no core changes; no LLM/dense claims; remote_calls=0
R25 graph+dense ablation: eval-layer ablation of graph_basic and dense_mock on R20 auto-wide (741 tasks); graph_basic net-negative (0 gold, 435 false spans → blocked); dense_mock net-negative (2 gold, 20,273 false → blocked); rrf_plus_graph dilutes RRF (FileRecall@1 0.693→0.497); rrf_plus_dense_mock dilutes (0.693→0.134); graph_pollution_ratio=0.0; citation validity remains 1.0 with graph/dense/composites revalidated and no_graph inherited from R21 after manifest verification; source-leak canary is regex-only with seeded self-test, not dense-path canary; QuIVer/TDB unavailable/not_measured; no Rust core changes; no LLM/dense real/QuIVer quality claims; remote_calls=0; promotion_ready=false
R26 auto-stress-1000: weak/mined/deterministic stress dataset for retrieval failure discovery; 1100 tasks across exact target counts for 10 stress categories (negative_nonexistent 150, ambiguous_vague 150, hard_distractor 200, semantic_trap 150, same_name_symbol 100, frontend_backend_confusion 75, test_source_confusion 75, generated_vendor_trap 50, stale_index_like 50, dense_quiver_specific_trap 100); 9 R20 repos; same external repo set as R20 plus some R20 task/label-derived queries; deterministic seed 42; no canary tokens; public tasks contain only test_id/repo_id/query/public_version/source; private labels carry category/risk/judgement fields; 19/19 fail-closed static validation checks passed including task/label query consistency, span path/range validity, and repo content manifest SHA lock recomputation; NOT promotion evidence; negative/abstain cases dominate (60%); no runner/scorer matrix yet; no Rust core changes; no LLM/dense claims; remote_calls=0

R28 promotion candidate report: conservative synthesis of R21/R23/R24/R25/R26 reports over R20/R26 failure-surface datasets with promotion_ready=false; current default should not change; best_recall_channel=rrf; best_precision_anchor=symbol; best_dense_candidate=none_available_for_default; quiver_recommendation=hold; graph/dense default expansion blocked; key blockers are R20 weak/mined labels, R26 deterministic/metamorphic/mined/stress labels with no retrieval matrix, R23 guard bucket regressions, QuIVer not implemented, dense real unavailable, and no broad human-verified stress tier
```

## R13 findings

- **Safe scaffold works**: All 45 safety checks pass. Remote is denied by default. Experimental opt-in is required. Secret scanning blocks token-like inputs. Audit contains no raw text or vectors. Vector store contains embedding vectors but no raw text/code snippet.
- **Mock provider is deterministic and normalized**: Same inputs always produce the same unit-length vector via blake3 hash. Different inputs produce different vectors. No network dependency.
- **Materialization gate is essential**: Dense search produces StoreHits which must be materialized through `materialize_evidence()`. Stale hits (content_sha mismatch) are correctly rejected.
- **Metadata-only views prevent code leakage**: Dense store builds views from path/language/basename/path-tokens only. No code snippets at data_level=0. Vector store and audit log do not contain raw code text.
- **Short file ranges are valid**: end_line=min(total_lines, 8) ensures materialize_evidence can verify ranges. Short files produce valid evidence.
- **Query text never leaks**: CLI JSON uses query_sha/query_len. Trace events use query_sha. Audit never stores raw query text. Blocked secret queries do not appear in traces.
- **Audit events use accurate names**: `query_embed` for query embedding, `allow`/`block`/`provider_unavailable` for decisions. Not `cache_hit` (no real cache behavior in R13). Cache key builder/stability only; no cache-hit behavior yet.
- **This is a safety scaffold only. No real semantic quality claim.** Mock vectors are deterministic blake3-based and do not capture semantic similarity. Dense mock search is integration/safety only.

## R14 findings

- **Scaled benchmark program established with fail-closed safety**: R14 defines S/M/L/X tiers. R14-S is populated with 4 logical repo groups from one OpenLocus workspace snapshot, 48 tasks, 48 labels, 47 hard negatives. Runner/scorer are strictly isolated. Citation validity must be 1.0.
- **Anti-leakage design is strictly enforced**: Public tasks contain no gold paths/lines. Labels are in separate private files with canary tokens. Path-component matching prevents false positives (e.g., 'openlocus-retrieval' does not match 'eval/'). Runtime canary retrieval is executed inside isolated benchmark roots.
- **Hard negatives are first-class with span-overlap metrics**: 47 hard negatives in R14-S. `hard_negative_hit_rate@10` requires span overlap unless a hard negative is explicitly file-level. `negative_nonempty_rate@10` measures false positive rate on negative tasks.
- **Citation validity is fail-closed, not a soft gate**: validity must be 1.0. No path-only fallback. Every citation must be hash+range+path valid.
- **Repo lock content manifest is verified by recomputation**: Normalized SHA-256 per file sorted. Mismatch = CRITICAL fail closed.
- **R14-S is a safety foundation, not a quality conclusion**: Validates the pipeline is fail-closed. Does not support quality claims.
- **Previous R14 graph precision is a future feature track**: Not the current R14 definition.
- **R14-M is partial; R14-L/X are not populated**: M uses the same 4 logical repo groups (target is 8+ independent repo groups/repositories). L/X require additional repos. Running --tier L or --tier X will fail with clear message.

## R15 findings

- **External multi-repo benchmark works with fail-closed safety**: 9 independent external repos across 5 languages (Rust, Python, Go, JavaScript, TypeScript), 166 medium-tier tasks, 270 hard negatives. Isolated roots allowlist-copy only manifest/source files under repo_id-specific folders; symlinks/artifacts are not copied. Unknown repo_id fail-closed. Canary retrieval zero hits.
- **Regex outperforms BM25 on exact-symbol queries**: FileRecall@1 is 0.852 (regex) vs 0.548 (bm25) on R15-M. This is because many tasks target exact symbol names where regex matches precisely. BM25 has high negative_nonempty_rate@10 (0.645 vs 0.000 for regex).
- **Hard negative hit rate is non-trivial (~0.23-0.29)**: Structurally plausible but incorrect results are common, as expected with mined hard negatives from the same repo. Hard-negative/gold span overlap is statically blocked.
- **Multi-language symbol extraction is functional but heuristic**: Rust/Python/Go/JS/TS regex-based patterns work for common cases. May miss unusual patterns (Go methods, Python decorators, JS arrows).
- **Anti-leakage holds across external repos**: 0 critical leakage issues. Absolute source path verification. Multi-language manifest verification. Task/label/manifest consistency checks. Canary tokens planted and runtime canary retrieval returns zero hits.
- **This is a mined benchmark expansion, not a quality conclusion.** Labels are mined with varying confidence; not human-verified. External local repos are workspace snapshots; not modified.

## R16 findings

- **Cross-matrix quality bakeoff across R14-S/R15-M/R15-stress**: eval/r16_quality_bakeoff.py runs all three matrices with four methods (regex, BM25, symbol, RRF), verifies safety gates, and produces aggregate report. All safety gates passed; citation_validity=1.0 across all methods/matrices; citation hash checked; canary retrieval passed; no remote calls.
- **RRF wins R15-M recall/MRR** (FileRecall@1 0.933, @5/10 0.993, MRR 0.959) but inherits BM25 negative false positive behavior (negative_nonempty@10 0.645 on R15-M, 0.684 on stress). Not safe as default for precision-sensitive tasks without negative gating or query intent routing.
- **Symbol has best span precision/hard-negative profile on R15-M** (SpanF0.5 0.310, hard_negative_hit_rate 0.052, negative_nonempty 0.000) but lower recall than RRF. Ideal as precision anchor, not sole retriever.
- **Regex strong on mined exact-symbol external tasks** (R15-M FileRecall@1 0.852, negative_nonempty 0.000) but reflects task distribution and exact-string bias, not a general natural-language conclusion.
- **BM25 strong in R14-S but weak and false-positive-heavy in R15-M/stress**: Needs query intent routing or threshold/negative guard.
- **No method promoted to universal default from R16**: Next research should be query intent router / negative guard / method fusion policy, not raw channel addition.
- **This is a lexical/symbol/RRF quality bakeoff. No provider/dense/LLM quality claims are made.**

## R17 findings

- **rrf_guarded_by_symbol_regex eliminates R15-M negative_nonempty with zero recall/MRR regression**: A simple evidence-presence guard that only returns RRF evidence when symbol or regex also found evidence perfectly filters R15-M negative tasks. This is the strongest result for a negative guard on R15-M.
- **query_only_router_v0 eliminates R15-M negative_nonempty with acceptable recall regression**: FileRecall@1 drops from 0.941 to 0.904 (delta -0.037), MRR from 0.963 to 0.918 (delta -0.044). SpanF0.5 improves from 0.253 to 0.315. The router uses noise marker detection, compound snake_case fabrication detection, and vague multi-word query detection.
- **R15-stress negative_nonempty reduces but is not eliminated**: query_only_router_v0 drops from 0.684 to 0.158; rrf_guarded drops to 0.474. Common-word queries where regex still returns false positives prevent full elimination.
- **task_type_assisted_router is an upper-bound reference**: Uses benchmark metadata (task_type) not available at runtime. Achieves 0.258 on R15-M and 0.316 on R15-stress.
- **No core default promotion**: R15-stress negative_nonempty remains above 0 for all strategies. Both R15-M and R15-stress negative_nonempty must improve without unacceptable recall/MRR regression before any core default change.
- **Eval-layer research only; does NOT change Rust core. No LLM/dense claims.**

## R18 findings

- **Train-selected candidate is useful but not stress-safe**: `rrf_guarded_by_symbol_regex` preserves RRF FileRecall@1/MRR on full R15-M (0.941/0.963) and holdout (0.844/0.900), while reducing medium negative_nonempty to 0.000. Stress remains weak: 0.474 negative_nonempty versus symbol 0.105.
- **The query noise guard is the key differentiator for stress**: rrf_guarded_by_symbol_regex alone leaves stress at 0.474 because regex returns false positives for common-word stress queries. The query noise guard identifies these as vague/noise and routes to empty.
- **Stress-zero strategies are observations, not promotions**: `query_noise_plus_rrf_agree_min` variants reach 0.000 stress negative_nonempty on the 19-task stress set, but this is too small and mined to justify default promotion.
- **Threshold sweep reveals sharp recall cliff at 0.05**: Most RRF top scores are either very high or very low; thresholds above 0.03 reject nearly all evidence.
- **Pareto frontier on R15-M shows recall vs hard-negative trade-off**: symbol (0.052 hard_neg, 0.807 recall) vs rrf_guarded (0.259 hard_neg, 0.941 recall) vs query_only_router_v0 (0.237 hard_neg, 0.904 recall).
- **No core default promotion in R18**: Threshold/guard choices are calibrated on mined R15 data and require larger/human-verified validation before promotion.
- **Eval-layer calibration only; does NOT change Rust core. No LLM/dense claims.**

## R19 findings

- **rrf_guarded_by_symbol_regex generalizes to R15-L**: FileRecall@1 preserved (0.911 vs RRF 0.911), negative_nonempty drops from 0.917 to 0.042. R15-L labels are weak/mined; generalization smoke only.
- **rrf_guarded fails stress**: Stress negative_nonempty is 0.474, above symbol baseline 0.105. The selected candidate does NOT improve stress beyond symbol. Query noise guard is needed.
- **query_noise_plus_rrf_agree_min_0.0 stress-zero observation repeated**: Achieves 0.000 stress negative_nonempty and 0.000 R15-L negative_nonempty. R15-L FileRecall@1 is 0.904 (delta -0.007 vs RRF). Observation, not promotion.
- **R15-L labels are weak/mined (270 mined, 24 weak)**: Generalization smoke only, not promotion evidence. R15-stress has only 19 tasks.
- **No core default promotion from R19**: promotion_ready is always false. Requires human-verified labels and larger stress dataset.
- **Eval-layer generalization validation only; does NOT change Rust core. No LLM/dense claims.**

## R20 findings

- **Failure-surface dataset generation works**: 741 tasks across 25 required categories and 9 R15 repos, with deterministic generation from fixed seed=42.
- **Public/private separation is clean**: Public tasks contain only task_id, repo_id, query, public_version, source_tier. No gold/expected/oracle/risk/judgement fields leak. All judgement fields are in separate private labels.
- **Category coverage is complete**: All 25 required categories have >= 5 tasks. positive_exact_symbol (180) and positive_regex_anchor (90) dominate due to per-repo symbol extraction.
- **Label quality distribution**: mined_high_confidence: 315, mined: 168, weak: 258. No human_reviewed (forbidden in R20).
- **Expected behavior distribution**: primary_evidence: 374, abstain: 177, weak_candidates: 90, no_primary: 45, supporting_only: 55.
- **Oracle type distribution**: deterministic: 438, stress: 148, mined: 110, metamorphic: 36, differential: 9.
- **Static validation passes all 14 check categories**: no private field leaks, task/label ID bijection, enum validity, required label schema, gold_span consistency, overlap constraints, span path/range validation, manifest SHA verification, coverage minimums, dataset manifest flags.
- **Metamorphic/stress categories** (dirty_overlay, deleted_file, renamed_file, branch_switch_like) encode expected behavior for R21/R26 but do NOT mutate source in R20.
- **R20 labels are failure-surface oracle/probe labels, not EvidenceCore.**
- **R20 is a failure-surface dataset, NOT promotion evidence.** No runner/scorer matrix exists yet; R21 will use this data.
- **Dataset + static validator only; no Rust core changes.**

## R22/R27 findings

- **Failure attribution is analysis-only**: Consumes R21 artifacts and R20 labels without re-running retrieval. 13 failure clusters computed from cross-strategy comparison heuristics.
- **RRF_INHERITED_BM25_FALSE_POSITIVE is the largest actionable cluster (110 tasks)**: BM25 and RRF both return false primary evidence on no-gold tasks. RRF inherits BM25's broad lexical matching without a negative gate.
- **GUARD_RECALL_KILL affects 67 positive tasks**: rrf_guarded_by_symbol kills recall when symbol returns empty on natural-language/vague queries but RRF finds gold. Per-guard: symbol=67 kills, regex=0, symbol_regex=0, query_noise=0.
- **SYMBOL_EXTRACTION_MISS affects 91 positive tasks**: Regex/RRF find gold but heuristic symbol extraction misses due to non-standard definition patterns.
- **REGEX_NORMALIZATION_BUG affects 1 task**: Curly braces in route-style queries cause Rust regex parse errors.
- **62 BENCHMARK_ORACLE_SUSPECT tasks**: Weak-quality labels where strategies strongly disagree with the oracle, suggesting label (not strategy) error.
- **Unrun strategy clusters have count=0**: Dense, TDB/QuIVer, graph, AST strategies not evaluated in R21. No fabricated data. recommended_next_tests provided for each.
- **EVIDENCECORE_REJECTION clusters have metric_unavailable=true**: R21 shows rate=0.0 for all strategies; no rejection data to analyze.
- **206 bucket regressions detected**: Multiple strategies exceed thresholds in specific buckets. promotion_blocked_by_bucket_regression=true.
- **promotion_ready=false. not_promotion_evidence=true. No Rust core changes. No LLM/dense claims.**

## R23 findings

- **Guard parameter sweep is analysis-only**: Consumes R21 artifacts and R20 labels without re-running retrieval. 51 strategies across 8 guard parameter dimensions plus 15 combined strategies.
- **All 51 strategies have bucket regressions**: Every guard strategy has at least one bucket where recall gap vs RRF >0.15, no_gold_nonempty_rate >0.3, primary_false_positive_rate >0.3, or guard_recall_kill_rate >0.1.
- **Combined query_noise + agreement is the best R23 guard balance**: query_noise_1_plus_regex_or_symbol_agree achieves no_gold_nonempty_rate 0.221 (vs RRF 0.495) with FileRecall@1 0.693 preserved and zero guard_recall_kill.
- **Agreement guards reduce false positives without recall cost**: regex_or_symbol_agreement_required reduces no_gold_nonempty_rate from 0.495 to 0.279 with zero guard_recall_kill and preserved FileRecall@1.
- **RRF score threshold above 0.02 causes sharp recall cliff**: Most RRF top scores are concentrated near 0.03-0.06.
- **top1_top2_gap threshold kills too much recall**: Even gap=0.005 causes >50% guard_recall_kill_rate.
- **Symbol agreement alone kills 22.8% recall**: Confirms R22 finding.
- **No strategy eliminates no_gold_nonempty_rate to zero without unacceptable recall loss**: Strategies achieving near-zero false positives do so by abstaining on >99% of queries.
- **Curves computed**: risk_coverage_curve, recall_vs_negative_curve, recall_vs_false_primary_curve, precision_vs_abstain_curve.
- **6877 total bucket regressions across 51 strategies**: Expected given R20 label diversity and now includes bucket-level guard_recall_kill regressions.
- **promotion_ready=false. not_promotion_evidence=true. No Rust core changes. No LLM/dense claims.**

## R24 findings

- **QuIVer is not implemented**: Scan of all Rust crates, Cargo.toml files, and source code confirms no QuIVer implementation exists outside eval/docs placeholders. quiver_implemented=false. All R24.1 diagnostic fields (BQ_overlap, quiver recall, quiver precision, quiver MRR, quiver F0.5) report unavailable/not_measured with reason quiver_not_implemented and explicit next_required_tests. No numeric 0 is output as a quality result.
- **TDB is a placeholder in default build**: `openlocus store status tdb --json` returns available=false, success=false, mode=placeholder. TDB is a feature-gated metadata/chunk store, not an ANN/QuIVer backend. tdb_stale_leak_count is not_applicable.
- **Dense mock is available as a candidate-channel safety smoke**: mock and disabled providers are available; real provider is unavailable. Dense mock uses deterministic blake3-based vectors that do NOT capture semantic similarity.
- **Dense mock produces real, materialized candidates but mostly exposes noise**: full run produced 5,264 dense_mock candidates, all Rust citation-valid. Quality is poor as expected for non-semantic mock vectors: FileRecall@1 0.024, MRR 0.073, SpanF0.5 ~0.000, token_waste 0.850, primary_false_positive_rate 0.878.
- **Dense CLI rejection and canary behavior are explicit**: full run recorded 99 candidate rejections (`candidate_rejection_rate` 0.134). Canary hardening checked 8 non-empty dense stores, skipped 1 empty store, returned 66 path-canary evidence items and 132 query-canary evidence items, with raw canary/query leakage 0.
- **Dense mock + RRF fusion amplifies noise**: fusion confirms dense contribution (642 tasks, 5,264 dense spans retained) but increases false-primary/noise: FileRecall@1 0.134, MRR 0.451, token_waste 0.928, primary_false_positive_rate 0.923, hard_distractor_hit_rate 0.215. This is a failure-surface probe, not a recommended strategy.
- **Citation validity is enforced**: Dense evidence and dense+RRF fusion evidence both pass Rust citation validation (hash+range+path) before cleanup. dense_mock citation_total=5,264; fusion citation_total=13,149; invalid=0.
- **R24 is NOT a QuIVer bakeoff**: It is an availability + mock dense candidate-channel probe + TDB placeholder status check. QuIVer remains future work.
- **No Rust core changes. No LLM/dense real/QuIVer quality claims. remote_calls=0.**

## R25 findings

- **graph_basic is net-negative on R20 auto-wide**: Added 0 gold spans and 435 false spans. Depth=1 graph impact from top path (derived via symbol→regex fallback) introduces evidence from related files that are not in gold, without recovering any gold spans RRF missed. Default expansion blocked by added_false_span > added_gold_span rule.
- **dense_mock is net-negative as expected**: Added 2 gold spans and 20,273 false spans. Non-semantic blake3-based mock vectors produce massive noise. The 2 gold hits are likely coincidental proximity. Default expansion blocked.
- **rrf_plus_graph dilutes RRF quality**: FileRecall@1 drops from 0.693 to 0.497. Graph evidence competes with RRF evidence in RRF score calculation, pushing relevant RRF hits down in ranking.
- **rrf_plus_dense_mock also dilutes RRF quality**: FileRecall@1 drops from 0.693 to 0.134. Dense mock evidence floods the RRF pool with irrelevant candidates.
- **Graph pollution is zero**: No graph evidence returned on forbidden paths (graph_pollution_ratio=0.000).
- **Graph has low token waste when it fires** (0.310 vs 0.779 baseline) but mostly abstains (0.785 abstain rate).
- **Graph path derivation stats**: symbol=358/741 (48.3%), regex=156/741 (21.1%), none=227/741 (30.6%). Impact returns empty evidence for 355/514 tasks with a top path (no graph edges found).
- **Combined strategies show additive noise**: rrf_plus_dense_mock_plus_graph accumulates both graph (435) and dense (20,273) false spans (20,695 total).
- **Citation validity remains 1.0**: graph_basic, dense_mock, and composite strategies are revalidated in R25 with Rust hash/range/path citation validation. no_graph inherits R21 validation after R25 verifies the R21 artifact manifest before baseline use.
- **QuIVer/TDB honestly reported as unavailable/not_measured**: No numeric zero quality results for QuIVer. TDB not applicable.
- **R25 is an eval-layer ablation study; does NOT change Rust core. No LLM/dense real/QuIVer quality claims. remote_calls=0. promotion_ready=false. not_promotion_evidence=true.**

## R29 findings

- **16-strategy matrix on R26 auto-stress (1100 tasks) is a failure-surface probe**: eval/r29_r26_stress_matrix.py runs base (regex/bm25/symbol/rrf), composite/guard (bm25_regex, bm25_symbol, rrf_guarded_by_symbol/regex/symbol_regex, query_noise_plus_rrf_agree_min), and R24/R25-style (dense_mock, dense_mock_plus_rrf, graph_basic, rrf_plus_graph, rrf_plus_dense_mock, rrf_plus_dense_mock_plus_graph) strategies. Strictly separated RUN/SCORE phases. R26 provenance validated before run. Citation validity must be 1.0 for all strategies. 14 required failure clusters computed. Span contribution analysis for graph/dense/composites vs fresh RRF baseline. Bucket regressions across source_category/expected_behavior/oracle_type/repo_id/risk_tags.
- **5 unavailable strategies report reason only**: dense_real_if_available (not_configured_or_policy_disabled), tdb_quiver_if_available (quiver_not_implemented), tdb_quiver_plus_rrf (quiver_not_implemented), tdb_quiver_guarded_by_symbol_regex (quiver_not_implemented), fast_context_if_available (fast_context_is_4turn_orchestration_scaffold_not_standalone_matrix_strategy). No fake numeric quality.
- **No skip-run**: Fresh run always required. Canary/citation validation cannot be bypassed.
- **Private field scan enforced**: Prediction/evidence/rejection/trace JSONL must not include source_category, risk_public, intent_guess, risk_tags, oracle_type, expected_behavior, gold_spans, hard_distractors, must_not_primary, why_this_is_hard, which_strategy_it_targets.
- **R26 labels are weak/mined/deterministic/stress**: Not human-verified. This is failure-surface only, not promotion evidence.
- **dense_mock is candidate-channel safety smoke, not semantic quality**: Mock vectors are deterministic blake3-based and do not capture semantic similarity.
- **graph_basic is deterministic depth=1**: Not precise call/type graph.
- **QuIVer not implemented; TDB unavailable**: No fabricated numeric quality.
- **promotion_ready=false. not_promotion_evidence=true. No Rust core changes. No LLM/dense real/QuIVer quality claims. remote_calls=0.**
- **Full R29 run completed with safety gates passed**: 1100 tasks, 16 implemented strategies, 64 artifact files verified, artifact private-field/canary scans clean, all implemented strategies have citation_validity=1.0.
- **RRF remains strongest recall but unsafe alone**: FileRecall@1=0.803, FileRecall@5=0.923, MRR=0.858, primary_false_positive_rate=0.453.
- **`query_noise_plus_rrf_agree_min` stress result is promising but still not promotion**: FileRecall@1=0.803, FileRecall@5=0.923, primary_false_positive_rate=0.106, guard_recall_kill_rate=0.003. R23 bucket-regression evidence still blocks promotion.
- **Symbol remains the precision anchor**: SpanF0.5=0.291, primary_false_positive_rate=0.080, token_waste=0.247, but abstain_rate=0.671.
- **Dense mock and dense+RRF are net-negative failure surfaces**: dense_mock primary_false_positive_rate=0.874; dense_mock_plus_rrf/rrf_plus_dense_mock primary_false_positive_rate=0.906.
- **Graph remains default-blocked**: graph_basic added_gold_span=0 and added_false_span=437; all graph/dense expansion variants are blocked by added_false_span > added_gold_span.
- **Failure clusters surfaced at scale**: DENSE_MOCK_NOISE=577, RRF_INHERITED_BM25_FALSE_POSITIVE=299, DENSE_SEMANTIC_TRAP_FALSE_POSITIVE=219, GRAPH_ADDS_NO_GOLD=90, GUARD_RECALL_KILL=62. Bucket regressions total=448.
