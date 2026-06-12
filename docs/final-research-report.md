# OpenLocus R0-R20 Research Report

Date: 2026-06-12
Repository: `https://github.com/Youzini-afk/OpenLocus-Lab.git`
Scope: continuous evidence-gated research implementation from the initial design into a working local retrieval kernel prototype, now including the R20 auto-wide retrieval failure-surface benchmark milestone.

## Executive summary

OpenLocus now has a working Rust prototype that validates the core design direction: **all agent-facing code facts must be evidence-backed, citation-checkable, and freshness-aware**.

The implementation completed twenty evidence-gated checkpoints:

| Commit | Stage | Result |
|---|---|---|
| `9779e9f` | R0/R1 local evidence kernel | `EvidenceCore`, local read/search/scan, trace JSONL, citation validation, context-lite. |
| `6d8a274` | R2 retrieval bakeoff | Regex/text, Tantivy BM25, heuristic symbol search, RRF fusion, metrics harness. |
| `f488d08` | R3 storage scaffold | Store traits, StoreHit materialization gate, ConservativeChunkStore, TDB placeholder. |
| `925ed38` | R4 derived indexing safety | `DerivedIndexView`, deterministic rule generator, policy/freshness gates, JSONL store. |
| `83ae02e` | R5 graph scaffold | Deterministic depth=1 graph, StoreHit materialization, impact/test-selection smoke. |
| `fb7104e` | R6 fast context prototype | 4-turn deterministic context orchestration with EvidencePack-compatible output. |
| `43135ed` | R7 persistent BM25 index | Persistent Tantivy index with mandatory manifest/policy gates, safe hit validation, and warm benchmark. |
| R8 checkpoint | R8 AST chunking/symbols | Tree-sitter AST-bounded chunking and AST symbol search as explicit experimental modes. |
| R9 checkpoint | R9 AST quality bakeoff | Persistent BM25 quality comparison: line vs ast on R2 fixture. AST improves span precision but regresses FileRecall@5. |
| R10 checkpoint | R10 incremental index + dirty summary + synthetic SLO | Dirty summary (manifest-vs-current scan), file-level incremental update, context-lite dirty integration, synthetic 1000-file SLO benchmark. 48/48 incremental smoke checks passed. |
| R11 checkpoint | R11 TDB Level0 adapter probe | Feature-gated TriviumDB 0.7.0 adapter behind `tdb` Cargo feature. TdbChunkStore with dim=1 smoke probe, metadata+chunks only, marker-based purge, materialization conformance. 11/11 adapter checks passed. No default dependency. No retrieval quality claim. |
| R12 checkpoint | R12 real-repo incremental robustness benchmark | eval/real_repo_incremental_bench.py on temp copy of OpenLocus repo. modify/add/delete/rename/policy_exclude/batch workloads pass 149/149 hard safety checks. total_invalid_citations=0. No stale VerifiedCurrent violations. Growth catastrophic guard passed (not bounded proof). Latency measured as report-only. Level0 one real-repo sample only. |
| R13 checkpoint | R13 remote embedding / LLM-derived indexing safety scaffold | New `openlocus-provider` crate with EmbeddingProvider trait, MockEmbeddingProvider (deterministic blake3 vectors, dim=32), DisabledEmbeddingProvider. Policy gate: remote denied by default, data_level ≤1 and ≤provider max, secret scanning. Dense JSONL store contains vectors but no raw text/code. Audit JSONL contains no raw text/vector/query. Search → StoreHit → materialize_evidence(Channel::Dense). CLI: provider status/audit, dense build/search/purge; dense output uses query_sha/query_len. 45/45 safety checks passed. Mock quality only; not real semantic retrieval. |
| R14 checkpoint | R14 Scaled Evidence Benchmark Foundation | Scaled benchmark program with S/M/L/X tiers. Fail-closed safety: runner/scorer isolation, isolated temp roots per repo group, isolated `.openlocus/policy.toml` from repo lock, unknown repo_id refusal, citation validity must be 1.0 via Rust validator, runtime canary retrieval, repo lock content manifest re-verification (normalized SHA-256 per file sorted). R14-S: 4 logical repo groups from one OpenLocus workspace snapshot, 48 tasks, 48 labels, 47 hard negatives. Span-overlap hard_negative_hit_rate@10 + negative_nonempty_rate@10. 8 leakage checks, 0 critical. R14-M partial. R14-L/X not populated. Safety foundation, not quality conclusion. |
| R15 checkpoint | R15 External Multi-Repo Benchmark Expansion | 9 independent external repos across 5 languages (Rust/Python/Go/JS/TS), 166 medium-tier tasks, 270 hard negatives. Multi-language symbol extraction with regex-based patterns. Isolated roots allowlist-copy only manifest/source files under repo_id-specific folders; symlinks and artifacts are not copied. Runtime `.openlocus` traces are cleaned after each query/citation validation and audited as hard-gate artifacts. Rust citation validator runs before cleanup (`citation_hash_checked=true`). Scoring accepts exact or single `repo_id/` prefix paths only. Regex FileRecall@1=0.852, BM25=0.548 on R15-M. BM25 negative_nonempty_rate@10=0.645. 112/112 smoke checks passed. 0 critical leakage issues. Mined benchmark expansion, not quality conclusion. |
| R16 checkpoint | R16 Multi-Method Quality Bakeoff | Cross-matrix bakeoff of regex/bm25/symbol/rrf across R14-S/R15-M/R15-stress. All safety gates passed (citation_validity=1.0, citation_hash_checked=true, canary_retrieval.passed=true). RRF wins R15-M recall (FileRecall@1 0.933, @5/10 0.993, MRR 0.959) but inherits BM25 negative_nonempty false positives (0.645 R15-M, 0.684 stress). Symbol best span precision (0.310 SpanF0.5, 0.052 hard_neg, 0.000 neg_nonempty on R15-M). No method promoted to universal default. Lexical/symbol/RRF only; no provider/dense/LLM claims. No remote calls. |
| R17 checkpoint | R17 Query Intent Router / Negative Guard Experiment | Eval-layer router/guard experiment; does NOT change Rust core. query_only_router_v0 eliminates R15-M negative_nonempty (0.645→0.000) with acceptable recall regression (FileRecall@1 0.904 vs 0.941, delta -0.037). rrf_guarded_by_symbol_regex eliminates R15-M negative_nonempty with zero recall regression. R15-stress negative_nonempty reduces but not eliminated (0.158/0.474). Citation safety inherited from validated source predictions. No LLM/dense claims. remote_calls=0. |
| R18 checkpoint | R18 Threshold/Guard Calibration Sweep | Eval-layer calibration sweep over 46 strategies with 8 thresholds on R15-M and R15-stress; does NOT change Rust core. Train-selected candidate `rrf_guarded_by_symbol_regex` preserves RRF recall on R15-M/holdout and drops medium negative_nonempty to 0.000, but remains weak on R15-stress (0.474, worse than symbol 0.105). Separate `query_noise_plus_rrf_agree_min` strategies reach 0.000 stress negative_nonempty but are observations, not promotion candidates. Pareto frontier computed. No core default promotion. No LLM/dense claims. remote_calls=0. |
| R19 checkpoint | R19 Large/Stress Guard Generalization Validation | Eval-layer generalization validation on R15-L (294 weak/mined tasks) and R15-stress; does NOT change Rust core. rrf_guarded_by_symbol_regex generalizes to R15-L (FileRecall@1 preserved at 0.911, negative_nonempty drops from 0.917 to 0.042) but fails stress (0.474 vs symbol 0.105). query_noise_plus_rrf_agree_min_0.0 stress-zero observation repeated (0.000 on both R15-L and R15-stress). R15-L labels are weak/mined (270 mined, 24 weak); generalization smoke only, not promotion evidence. promotion_ready=false always. No LLM/dense claims. remote_calls=0. |
| R20 checkpoint | R20 Auto-Wide Retrieval Failure-Surface Benchmark (Dataset + Static Validator) | Generated/mined/weak failure-surface dataset for retrieval failure discovery, NOT promotion evidence. 741 tasks across 25 required categories and 9 R15 repos. Public tasks contain only task_id/repo_id/query/public_version/source_tier. Private labels carry all judgement fields (query_category, expected_behavior, oracle_type, risk_tags, gold_spans, hard_distractors, must_not_primary, etc.). label_quality: mined_high_confidence/mined/weak only (no human_reviewed). Static validator enforces schema, enum, coverage, anti-leakage, manifest SHA, overlap constraints. 14/14 validation checks passed, 0 critical errors. R20 labels are failure-surface oracle/probe labels, not EvidenceCore. No runner/scorer matrix yet. R21 will use it. Dataset + static validator only; no Rust core changes. |

Final verification snapshot:

```text
Rust tests: 243 passed (193 existing + 50 new in openlocus-provider)
fmt: clean
clippy: clean with -D warnings
Remote dependency: none
LLM dependency: none
TDB dependency: optional only (behind `tdb` feature; not in default build)
Safety evals: storage, derived, graph, fast-context, persistent-index, AST-chunking all passing their Level0 gates; AST quality bakeoff safety checks 16/16 passed; incremental index smoke 48/48 checks passed; synthetic SLO bench 0 invalid citations; TDB adapter probe 11/11 checks passed; real-repo incremental bench 149/149 hard safety checks passed; provider dense safety 45/45 checks passed; R18 calibration sweep all source safety gates passed, baseline consistency checked
```

The most important research outcome is not that retrieval quality is solved. It is that the project now has a **safe experimental harness** where BM25, graph, TDB, LLM-derived views, dense embeddings, and future planners can be tested without weakening the EvidenceCore contract.

## Research methodology

We followed the agreed continuous research loop:

```text
Hypothesis -> Prototype -> Bakeoff / Safety Eval -> Review -> Fix blockers -> Push -> Next stage
```

No stage was promoted just because it ran. Each stage was reviewed against the design constraints:

- do not mutate `EvidenceCore` for research features;
- keep all authoritative facts tied to `path + line_range + content_sha`;
- prefer narrow spans over broad summaries;
- validate current file state before declaring evidence `VerifiedCurrent`;
- keep remote/LLM/TDB features outside the core until gates prove safety and value;
- record caveats rather than overclaim quality.

Several early implementations were deliberately corrected before commit: regex span widening, BM25 `*` fallback, graph hand-built evidence, R6 weak final citation validation, and R4 data-level/policy gaps. These corrections are strong evidence that the gate discipline is useful.

## Implemented architecture

Current workspace structure:

```text
crates/openlocus-core       EvidenceCore, EvidenceMeta, EvidencePack, Policy, trace types
crates/openlocus-repo       path safety, read, scan, content hashing
crates/openlocus-retrieval  regex/text search, BM25, symbol search, RRF fusion
crates/openlocus-ast        Tree-sitter AST chunk and symbol extraction scaffold
crates/openlocus-index      persistent Tantivy BM25 index, manifest, warm benchmark handle
crates/openlocus-store      Store traits, StoreHit materialization, conservative store, TDB placeholder
crates/openlocus-derived    DerivedIndexView safety scaffold
crates/openlocus-graph      deterministic graph scaffold + graph materialization
crates/openlocus-context    Fast Context Level0 rule loop
crates/openlocus-provider   EmbeddingProvider trait, MockEmbeddingProvider, DisabledEmbeddingProvider, policy gate, secret scanner, dense JSONL store, embedding audit
crates/openlocus-cli        user-facing CLI
eval/                       retrieval/storage/derived/graph/fast-context/persistent-index/AST/provider-dense smoke and scoring scripts
docs/                       research log, summary, agent guide, final report
```

Representative commands:

```bash
openlocus read <path[:start-end]> --json
openlocus scan --json
openlocus search regex <pattern> --json
openlocus search bm25 <query> --json
openlocus search bm25 <query> --index persistent --json
openlocus search symbol <name> --mode regex|ast|auto --json
openlocus retrieve <query> --channels regex,bm25,symbol --json
openlocus citations validate <file.json> --json
openlocus store status conservative --json
openlocus derived build all --experimental --json
openlocus graph build --json
openlocus impact <path> --json
openlocus tests --path <path> --json
openlocus fast-context <query> --json
openlocus index build --chunk-strategy line|ast --json
openlocus index status --json
openlocus index dirty --json
openlocus index validate --json
openlocus index update --dirty --json
openlocus index update --path <path> --json
openlocus index purge --json
openlocus bench warm --dataset fixtures/r2.jsonl --iterations 3 --json
openlocus provider status --json
openlocus provider audit --limit 20 --json
openlocus dense build --provider mock --experimental --json
openlocus dense search <query> --provider mock --limit 10 --json
openlocus dense purge --json
```

## Stage results

### R0/R1 — local evidence kernel

Goal: establish a trustworthy local evidence contract before adding semantic retrieval.

Implemented:

- `EvidenceCore`: stable minimal contract (`path`, `start_line`, `end_line`, `content_sha`, `score`, `why`, `channels`).
- Optional `EvidenceMeta`: freshness, language, excerpt, score parts, symbol metadata.
- Path validation with absolute path rejection, `..` rejection, and symlink escape protection.
- `read`, `scan`, regex/text search, command trace JSONL, context-lite files.
- Citation validation for single evidence, arrays, and `{ evidence: [...] }` objects.

Key finding:

- Evidence precision problems appear immediately. The first regex implementation returned over-wide spans for multiple distant matches; this would have harmed token waste and Span F0.5. It was fixed to return one narrow evidence span per matching line.

Status: passed initial local-only gate.

### R2 — retrieval method bakeoff

Goal: compare local retrieval channels without dense, graph, TDB, or LLM indexing.

Implemented:

- Tantivy BM25 over bounded line chunks.
- Line-level query-token scoring and no-overlap skip.
- Stale hash checks for BM25 hits.
- Heuristic symbol search for Rust/Python/TS/JS/Go-style definitions.
- RRF fusion that merges same spans and keeps narrower overlapping spans.
- Evaluation metrics: FileRecall, MRR, LinePrecision/Recall, SpanF0.5, token waste, wrong-span rate, structural validity, and citation validity. The Python scorer verifies path/range and verifies BLAKE3 hashes when optional Python `blake3` is installed; the Rust CLI validator performs hash/range/excerpt-backed citation validation.

Current self-referential fixture results:

| Metric | regex | bm25 | symbol | rrf |
|---|---:|---:|---:|---:|
| FileRecall@1 | 0.21 | 0.39 | 0.39 | 0.39 |
| FileRecall@5 | 0.36 | 0.86 | 0.39 | 0.82 |
| FileRecall@10 | 0.50 | 0.86 | 0.39 | 0.82 |
| MRR | 0.29 | 0.58 | 0.39 | 0.56 |
| SpanF0.5@10 | 0.035 | 0.043 | 0.064 | 0.057 |
| Python scorer citation validity | 1.0 | 1.0 | 1.0 | 1.0 |

The current aggregated R2 evidence output was additionally validated with the Rust CLI citation validator with `0` invalid citations, using hash/range/excerpt checks.

Key finding:

- BM25 improves file-level recall on this fixture, but line/span precision remains weak. The next quality bottleneck is chunking/query rewriting/span targeting, not just adding more recall channels.

Status: passed oracle review as a local retrieval baseline, not a general benchmark claim.

### R3 — storage scaffold and TDB test surface

Goal: introduce backend abstraction without allowing storage to become an evidence authority.

Implemented:

- Store traits and capability reporting.
- `StoreHit -> materialize_evidence()` gate.
- Conservative in-memory chunk store.
- TDB placeholder backend: explicit unavailable/unsupported status, no hidden dependency.
- Storage smoke eval.

Key safety property:

```text
Store backends never directly produce authoritative Evidence.
They produce StoreHit candidates, which must be materialized against the current filesystem.
```

Materialization gate rejects:

- empty `content_sha`;
- path traversal / symlink escape;
- stale hashes;
- invalid ranges;
- inconsistent TOCTOU reads.

TDB conclusion:

- TDB is in the test surface, but only as `Level0 placeholder` for now. A real adapter should be optional, feature-gated, and judged by the same conformance tests before it can become an optional backend.

Status: passed Level0 conformance.

### R4 — LLM-derived indexing safety scaffold

Goal: explore LLM indexing shape without connecting any real LLM or remote provider.

Implemented:

- `DerivedIndexView` model.
- Deterministic rule generator for low-risk view kinds: `chunk_summary`, `symbol_tags`, `query_aliases`.
- Policy/data-level gate: Level0 hard-gates `data_level <= 1`.
- High-risk kinds (`candidate_edge`, `bug_symptom_hint`) blocked by default.
- Source citation/freshness validation.
- JSONL store with parse error reporting and purge.
- Secret-like token filtering for obvious patterns.
- Derived safety eval with stale mutation, policy-excluded files, corrupt JSONL, and no-remote checks.

Key boundary:

```text
DerivedIndexView is not Evidence.
It may become a future query hint, but it cannot prove a code fact.
```

Status: passed oracle review as Level0 safety scaffold. No real LLM integration and no retrieval quality claim.

### R5 — deterministic graph scaffold

Goal: add graph/test/impact plumbing without pretending to have a precise call graph.

Implemented:

- Deterministic graph edge kinds: imports, tests, configures.
- Depth=1 only; depth>1 blocked.
- GraphEdge carries build-time `source_content_sha` and `source_language`.
- Graph materialization uses `StoreHit -> openlocus_store::materialize_evidence()`.
- Invalid ranges rejected, not clamped.
- `graph inspect` labels raw output as `graph_edges_not_evidence`.
- `impact` and `tests` commands return materialized evidence and skipped counts.
- Synthetic graph smoke eval with true citation validation.

Key finding:

- Graph plumbing is useful, but config edges are noisy and import resolution is heuristic. This is safe graph infrastructure, not a semantic graph quality win yet.

Status: passed oracle review as Level0 deterministic graph scaffold.

### R6 — Fast Context Level0 rule prototype

Goal: prototype agent-facing context assembly without an LLM planner.

Implemented:

- 4-turn deterministic loop:
  1. lexical regex/text/BM25;
  2. symbol search if identifier-like query;
  3. graph expansion from top file candidates;
  4. RRF fusion, validation, budget trimming.
- EvidencePack-compatible output with `trace_id`.
- Per-turn/per-channel `ActionRecord` replay trace.
- Trace file written to `.openlocus/traces/fast-context-<trace_id>.json`.
- Token budget using chars/4 approximation plus `--max-evidence` count cap.
- Unknown channel gate.
- Final in-process citation validation: path safety, current file hash, range bounds, excerpt match, and `VerifiedCurrent` freshness.
- Fast-context smoke eval with pack shape, replayable actions, unknown-channel block, token budget, no remote, true citation validation.

Status: passed oracle review as Level0 rule orchestration scaffold. It is not a learned agent and makes no general quality claim.

### R7 — persistent BM25 index and warm benchmark

Goal: separate persistent local index performance from per-query cold build cost while preserving evidence safety.

Implemented:

- `openlocus-index` crate with persistent Tantivy index under `.openlocus/index/tantivy/`.
- Mandatory manifest at `.openlocus/index/manifest.json` with schema version `r7-bm25-v1`, policy hash, file/chunk counts, and per-file content hashes.
- `openlocus index build/status/validate/purge` CLI commands.
- `openlocus search bm25 <query> --index persistent --json` as explicit opt-in; default BM25 remains temporary index behavior.
- `PersistentBm25Index::open(repo_root, policy)` reusable handle used by `openlocus bench warm`.
- Warm benchmark reports `index_open_ms`, `index_build_ms`, p50/p95/max query latency, stale hits skipped, and invalid citations.
- `eval/persistent_index_smoke.py` with 32 Level0 safety checks.

Critical gates added after oracle review:

- persistent search/open refuse if manifest is missing;
- persistent search/open refuse if manifest policy hash or schema version mismatches current policy/schema;
- every Tantivy hit path is validated with `validate_path` before file read;
- empty stored `content_sha` is skipped;
- stored chunk ranges are strictly validated and never clamped;
- `bench warm` opens the Index/searcher once and reuses the same handle for every query;
- benchmark `invalid_citations` checks hash/range/excerpt/freshness, not only line range.

Current small-repo measurement:

```text
Repo scale: small self-referential workspace snapshot
index_open_ms: 1
warm_query_p50_ms: 1
warm_query_p95_ms: 2
warm_query_max_ms: 2
invalid_citations: 0
stale_hits_skipped: 0
persistent_index_smoke: 32/32 checks passed
```

Status: passed Level0 smoke and oracle safety gates. This is a small self-referential benchmark, not a general performance claim.

### R8 — AST-bounded chunking and AST symbol extraction

Goal: test whether Tree-sitter chunk boundaries can improve future span precision without changing EvidenceCore or weakening R7 persistent-index safety.

Implemented:

- `openlocus-ast` crate using Tree-sitter 0.25.x grammars for Rust, Python, JavaScript, and TypeScript.
- `extract_ast_chunks(path, language, source, max_lines)` returns AST-bounded chunks plus fallback line windows; unsupported languages and parse errors fall back to line windows.
- `extract_ast_symbols(path, language, source)` returns narrow header/signature spans; parse errors and unsupported languages return empty AST symbols so callers can use regex fallback.
- Persistent index manifest schema advanced to `r8-bm25-v2`, with `chunk_strategy` and optional `ast_stats`.
- `openlocus index build --chunk-strategy line|ast --json`; line remains default, AST is explicit/experimental.
- `openlocus search symbol <name> --mode regex|ast|auto --json`; regex mode preserves old behavior, auto tries AST then regex fallback.
- `eval/ast_chunking_smoke.py` with 40 Level0 safety checks.

Critical gates:

- AST chunks/symbols are candidates only; final Evidence still comes from current file hash/range/excerpt/freshness validation.
- AST symbol output is narrow header/signature evidence, not full function bodies by default.
- Parser-error files fall back instead of producing AST-bounded evidence from error trees.
- Policy-excluded files are not parsed/indexed/searched.
- Default line-window build/search remains available and R7 persistent smoke still passes.

Status: passed Level0 smoke (`40/40`) and full Rust tests (`176`). AST quality lift is **not proven** yet; this is an experimental scaffold.

### R9 — AST vs line persistent BM25 quality bakeoff

Goal: measure whether AST-bounded chunking improves persistent BM25 retrieval quality compared to default line-window chunking.

Implemented:

- `eval/ast_quality_bakeoff.py`: Reproducible bakeoff script that runs both strategies (purge/build/search/score) on the R2 fixture and produces a combined JSON report with metrics, delta, quality gate, and safety checks.
- Directly reuses `eval/score.py` functions (file_recall_at_k, mrr, span_f_beta_at_k, token_waste_ratio_at_k, citation_validity, etc.) instead of duplicating scoring logic.
- Predictions written as JSONL compatible with `eval/score.py` format.
- Quality gate: citation_validity==1.0 and success_rate==1.0 for both; AST FileRecall@5 ≥ line; AST SpanF0.5@10 ≥ line; token_waste not worse; latency ratio ≤ 1.25.
- Safety checks: build succeeds, validate valid, status strategy matches, emitted evidence nonempty, citation validator invalid_count=0, search stats counters present/nonnegative, strategy explicit.
- Gate and safety are reported separately. Negative results are valid; script does not exit failure on quality gate false.

R2 fixture results (28 tasks, persistent BM25):

| Metric | line | ast | delta |
|---|---:|---:|---:|
| FileRecall@1 | 0.393 | 0.536 | +0.143 |
| FileRecall@5 | 0.821 | 0.750 | −0.071 |
| FileRecall@10 | 0.821 | 0.821 | 0.000 |
| MRR | 0.548 | 0.624 | +0.076 |
| SpanF0.5@10 | 0.039 | 0.064 | +0.025 |
| token_waste_ratio@10 | 0.961 | 0.940 | −0.022 |
| wrong_span_rate@10 | 0.776 | 0.689 | −0.087 |
| citation_validity | 1.0 | 1.0 | 0.0 |
| avg_latency_ms | ~10.4 | ~9.1 | noisy/comparable |
| latency_ratio | — | ~1.0 | — |

Quality gate: **false** (AST FileRecall@5 < line).  
Safety checks: **16/16 passed**.

Key finding:

- AST improves span precision (SpanF0.5@10 ~+63% relative, token_waste −2.2pp, wrong_span_rate −8.7pp) and top-1 recall (+36% relative), but regresses FileRecall@5 (−7.1pp in the latest run) due to chunk-score dilution: more granular AST chunks scatter a file's BM25 signal, reducing the chance that any single chunk ranks the file into top-5.
- This is a real trade-off, not a bug. The fixture is too small and self-referential to generalise.
- **AST remains experimental/opt-in; line remains default.** A larger, diverse codebase eval would be needed for a definitive quality comparison.

Status: safety checks all pass; quality gate is false due to FileRecall@5 regression. This is a valid negative result on a small self-referential fixture.

### R10 — incremental index, dirty summary, and synthetic SLO

Goal: add persistent index dirty summary, file-level incremental update, context-lite dirty integration, and synthetic SLO benchmark without implementing TDB/daemon/watcher or LLM/dense.

Implemented:

 - `dirty_index(repo_root, policy, current_records)`: Manifest-vs-current scan returning `DirtyResult` with clean, requires_update, requires_rebuild, added/modified/deleted files and counts, policy_hash_matches, schema_matches, chunk_strategy. Added detection uses ALL manifest paths (indexed+skipped). Skipped entries with unchanged sha remain clean; skipped→nonempty is reported as modified (not added).
 - `update_index(repo_root, policy, current_records, dirty, path)`: File-level incremental update via `--dirty` (batch) or `--path` (single file). Safety gates: missing manifest, policy/schema/strategy mismatch, manifest load failure → refuse update. Tantivy delete-by-term + re-add, commit once, manifest file write via tmp+rename (not a single transaction with Tantivy commit; crash between may require rebuild or re-update).
 - CLI: `openlocus index dirty --json`, `openlocus index update --dirty --json`, `openlocus index update --path <path> --json`.
 - Context-lite writes dirty-summary.json file with actual dirty index status; `ContextLitePack.dirty_summary` struct field remains `None` (file is the surface).
 - `eval/incremental_index_smoke.py`: 48 safety checks covering build/clean, modify/update/search/clean, add/update/search/clean, delete/update/search/clean, rename simulation, policy-excluded no dirty, policy mismatch refuses update, missing manifest refuses update, skipped empty file clean/promotion, schema/strategy mismatch refuses update, citations invalid_count=0.
 - `eval/synthetic_slo_bench.py`: Deterministic 1000-file synthetic repo, measures build_ms, dirty status latency, persistent_cli_search p95, bench-warm open-once query p95, and one-file update latency (true modification each iteration). 0 invalid citations.

Critical gates:

- Missing manifest → error (requires rebuild); no silent fallback.
- Policy hash/schema/strategy mismatch → refuse update, require rebuild.
- Manifest load failure (corrupt JSON, unknown schema/strategy) → refuse update gracefully, require rebuild.
- Tantivy delete-by-term before add prevents duplicate old+new docs.
- Manifest file write uses tmp+rename to prevent partial writes; but this is not a single transaction with Tantivy commit (crash between may require rebuild or re-update).
- Chunk strategy from manifest is respected; no strategy mixing.
- Tantivy deletes are tombstones until merge (documented, not a bug).
- Added detection uses ALL manifest paths (indexed+skipped); skipped entries with unchanged sha do not appear as added.

Incremental smoke: 48/48 checks passed.

Synthetic SLO (1000 files, seed=42, dev profile):

```text
build_ms: 147
dirty_status_latency p50: 44ms, p95: 48ms
persistent_cli_search_latency p50: 13ms, p95: 14ms
bench_warm open-once query latency p50: 0ms, p95: 0ms, max: 1ms
one_file_update_latency p50: 115ms, p95: 117ms (true modification each iteration)
total_invalid_citations: 0
```

Note: Level0 synthetic-only measurements. Not a general performance claim. `persistent_cli_search_latency_ms` measures CLI search (each call opens index fresh). `bench_warm` reports the Rust CLI's internal open-once query latency over a synthetic dataset.

Key finding:

- Incremental update works correctly and safely: dirty summary accurately identifies changes (skipped entries with unchanged sha remain clean; skipped→nonempty reported as modified, not added), update applies batch changes (Tantivy commit + manifest file write via tmp+rename, not a single transaction), post-update status is clean, and persistent search returns only current content.
- TDB is deferred to R11; R10 focuses on incremental index infrastructure.

Status: passed Level0 smoke (48/48 incremental checks + synthetic SLO).

### R11 — TriviumDB/TDB feature-gated Level0 adapter probe

Goal: implement a real TriviumDB adapter behind a Cargo feature flag, proving the StoreBackend / ChunkStore trait hierarchy can be wired to a live TDB instance. If TDB was not compilable, fall back to a negative feasibility report.

Implemented:

- **Cargo feature**: `tdb = ["dep:triviumdb"]` in `openlocus-store/Cargo.toml`. `triviumdb = { version = "=0.7.0", optional = true }`. Default build does NOT enable the feature.
- **TdbChunkStore** (`crates/openlocus-store/src/tdb_adapter.rs`): Behind `#[cfg(feature = "tdb")]`.
  - Opens `Database<f32>` with `dim=1` and stores chunk metadata as JSON payloads with schema `openlocus_schema=tdb_chunk_v1`.
  - The `[0.0]` vector is a smoke probe only — NOT vector quality. Capabilities honestly report vector=false.
  - Build discipline copies ConservativeChunkStore: `validate_path`, read current bytes once, sha from same bytes, skip stale/traversal/empty.
  - Marker file (`.openlocus_marker`) written alongside `.tdb` for adapter ownership identification.
  - Purge only deletes the adapter-owned TDB artifact set (`.tdb` plus known sidecars) after verifying the marker. Refuses without valid marker.
  - Ingest only from `scan_repo` filtered records; never walks filesystem.
  - TDB hits must go through `StoreHit → materialize_evidence()`.
- **Placeholder preserved**: `TdbPlaceholderStore` unchanged.

R11 Level0 adapter probe results:

| Check | Result |
|---|---|
| `cargo test --workspace` (default, no tdb) | ✅ 193 passed |
| `cargo test -p openlocus-store --features tdb` | ✅ 28 passed |
| `cargo fmt --all -- --check` | ✅ clean |
| `cargo clippy --workspace -- -D warnings` | ✅ clean |
| `cargo clippy -p openlocus-store --features tdb -- -D warnings` | ✅ clean |
| TDB adapter health available when open | ✅ |
| TDB adapter build from records | ✅ |
| TDB adapter capabilities conservative | ✅ metadata+chunks only |
| TDB adapter skips stale records | ✅ |
| TDB adapter skips empty files | ✅ |
| TDB adapter skips traversal records | ✅ |
| TDB adapter purge marker-owned only | ✅ deletes `.tdb` + known sidecars + marker |
| TDB adapter purge refuses without marker | ✅ |
| TDB adapter materialization conformance | ✅ VerifiedCurrent |
| TDB adapter materialization rejects stale | ✅ StaleHit |
| TDB adapter materialization rejects empty sha | ✅ |
| TDB adapter materialization rejects invalid range | ✅ |
| Default build unchanged | ✅ no TDB dependency |
| Placeholder unchanged | ✅ |
| EvidenceCore unchanged | ✅ |

Key finding:

- TriviumDB 0.7.0 compiles from crates.io and works as an optional dependency. The feature-gated adapter correctly wires TDB into the StoreBackend/ChunkStore trait hierarchy with honest capability reporting. Materialization conformance is enforced.
- This is a Level0 adapter probe only. No retrieval quality comparison against Tantivy BM25 or conservative store. The dim=1 vector is a smoke probe. TDB is NOT a default dependency.

Status: passed Level0 smoke (11/11 adapter checks; 29/29 total store tests with --features tdb).

### R12 — real-repo incremental robustness benchmark

Goal: test R10 incremental index on a real repository copy (OpenLocus) with modify/add/delete/rename/policy-exclude/batch workloads, latency comparison, and growth cycling. Do not change Rust core, default CLI/search/retrieve, or introduce watcher/daemon/TDB changes.

Implemented:

- `eval/real_repo_incremental_bench.py` with `report_kind=real_repo_incremental_bench`.
- Source repo defaults to current working directory; copies to temp repo (excluding `target`, `.git`, `.openlocus`, `runs`, `node_modules`, `dist`, `__pycache__`, etc.), creates empty `.git/` and `.openlocus/policy.toml`.
- All workload file mutations occur only in temp repo; original source files are never modified. `--out` writes report to caller workspace.
- **Per-run unique markers** (8-hex-char suffix) avoid self-contamination from copied docs/scripts. Pre-build assert confirms markers absent.
- All search uses `openlocus search bm25 <query> --index persistent --json`. Search returncode must be 0 for positive gates.
- Collected marker-search evidence is validated via `openlocus citations validate` with `invalid_count=0` and validator returncode==0.
- **Positive gates use path+marker conjunction**: `evidence_has_path_and_marker` requires both path fragment AND marker in the cited excerpt. Previous disjunction could pass from unrelated evidence.
- **Empty evidence is not a pass**: Where a marker must be found, `len(evidence) > 0` required.
- Eight workloads: modify_one, add_one, delete_one, rename_one, policy_exclude, branch_like_batch, latency_compare, growth_cycles.
- **Latency compare uses twin repo copies**: Both update and rebuild start from same state with same mutation. Gate is report-only; false does not cause exit failure.
- **Growth catastrophic guard**: `final_after_updates_size ≤ max(3 × post_full_rebuild_size, post_full_rebuild_size + 64MiB)`. Observed 20-cycle growth ratio reported. Does not prove long-term bounded growth.
- `sys.exit(1)` on safety failure only; latency/growth gate failures are report-only.

R12 benchmark results (OpenLocus temp copy):

| Check | Result |
|---|---|
| Baseline build succeeds, file/chunk count >0 | ✅ |
| Baseline dirty clean after build | ✅ |
| Baseline validate valid | ✅ |
| modify_one: dirty detects modified | ✅ |
| modify_one: update succeeds, new marker found at path+marker, old gone | ✅ |
| modify_one: clean + valid after update | ✅ |
| add_one: dirty detects added, search finds marker at path+marker | ✅ |
| add_one: clean + valid after update | ✅ |
| delete_one: dirty detects deleted, no VerifiedCurrent for deleted | ✅ |
| delete_one: clean + valid after update | ✅ |
| rename_one: dirty detects added+deleted, old gone, new found at path+marker | ✅ |
| rename_one: clean + valid after update | ✅ |
| policy_exclude: dirty stays clean, no evidence from excluded path | ✅ |
| branch_batch: add target found at path+marker | ✅ |
| branch_batch: rename-new target found at path+marker | ✅ |
| branch_batch: delete/rename-old markers were indexed before removal | ✅ |
| branch_batch: deleted path no VerifiedCurrent | ✅ |
| branch_batch: rename-old path no VerifiedCurrent | ✅ |
| branch_batch: clean + valid after update | ✅ |
| growth_cycles: all cycles dirty→update→clean→valid | ✅ |
| growth_cycles: catastrophic guard passed (observed ~1.11×) | ✅ |
| total_invalid_citations | 0 |
| stale_verified_current_violations | [] |

Key finding:

- Real-repo incremental update passes this Level0 temp-copy workload: no stale VerifiedCurrent evidence, correct dirty detection for sampled workload types, valid collected marker-search citations, catastrophic growth guard passed.
- Per-run unique markers avoid self-contamination from copied docs/scripts. Pre-build assert confirms markers absent.
- Positive gates require path+marker conjunction; empty evidence is not a pass for positive assertions.
- Latency comparison uses twin repo copies (same mutation, same starting state); incremental update ~42% faster on this sample. Gate is report-only.
- Growth catastrophic guard passed (20 cycles observed growth ~1.11×). Does not prove long-term bounded growth.
- This is one real-repo sample (OpenLocus temp copy). Not a general performance or robustness claim. Different repos, hardware, and workloads may produce different results.
- Collected marker-search evidence validated; not "all evidence in repo".

Status: 149/149 hard safety checks passed; latency/growth gates measured honestly (report-only). Level0 one real-repo sample only.

### R17 — query intent router / negative guard experiment

Goal: test whether query-only routing heuristics and negative guards can reduce negative_nonempty false positives (inherited by RRF from BM25) while preserving recall. Eval-layer research only; does NOT change Rust core.

Implemented:

- `eval/r17_router_guard_experiment.py`: Loads existing R15 predictions, applies three synthetic routing strategies without invoking OpenLocus again, scores with R15-compatible metrics.
- **query_only_router_v0**: Routes based only on query text. Heuristics: negative/noise marker detection, compound snake_case noise, vague multi-word queries, exact identifier detection, identifier token detection, default RRF for recall.
- **rrf_guarded_by_symbol_regex**: Choose RRF only if either symbol or regex has evidence; otherwise empty.
- **task_type_assisted_router_upper_bound**: Uses task_type as upper-bound reference (not production router).

R17 results:

- **rrf_guarded_by_symbol_regex eliminates R15-M negative_nonempty (0.645→0.000) with zero recall/MRR regression**: The guard only returns RRF evidence when symbol or regex also found evidence, and positive tasks always have at least one of those.
- **query_only_router_v0 eliminates R15-M negative_nonempty (0.645→0.000) with acceptable recall regression**: FileRecall@1 drops from 0.941 to 0.904 (delta -0.037), MRR from 0.963 to 0.918 (delta -0.044). SpanF0.5 improves from 0.253 to 0.315.
- **R15-stress negative_nonempty reduces but is not eliminated**: query_only_router_v0 drops from 0.684 to 0.158; rrf_guarded drops to 0.474.

Status: Eval-layer research only; does NOT change Rust core. No LLM/dense claims.

### R18 — threshold/guard calibration sweep

Goal: systematically sweep threshold and guard configurations over R15 benchmark predictions to find Pareto-optimal strategies that reduce negative_nonempty while preserving recall. Uses deterministic repo-holdout split for R15-M. Eval-layer research only; does NOT change Rust core.

Implemented:

- `eval/r18_calibration_sweep.py`: Schema version r18-v1. Imports R17 helpers. 46 strategies across 8 thresholds (0.0, 0.005, 0.01, 0.015, 0.02, 0.03, 0.05, 0.08).
- **Strategy family**: Baselines (regex, bm25, symbol, rrf), R17 fixed references (query_only_router_v0, rrf_guarded_by_symbol_regex), and sweep configs:
  - rrf_score_min_{t}: use RRF if top RRF score >= t else empty
  - rrf_score_min_{t}_regex_or_symbol: use RRF if score >= t and (regex_has or symbol_has)
  - rrf_score_min_{t}_symbol: use RRF if score >= t and symbol_has
  - query_noise_plus_rrf_score_min_{t}: if noise/vague query then empty else RRF if score >= t
  - query_noise_plus_rrf_agree_min_{t}: if noise/vague query then empty else RRF if score >= t and (regex_has or symbol_has)
- **Repo-holdout split**: Deterministic by sorted repo_id: first 6 train, last 3 holdout.
- **Candidate selection**: From train only. Eligible if train negative_nonempty<=0.05 and train FileRecall@1 >= (RRF_train - 0.05). Among eligible, maximize train MRR, minimize token_waste.
- **Pareto frontier**: Full R15-M over maximize FileRecall@1, SpanF0.5@10; minimize negative_nonempty_rate@10, hard_negative_hit_rate@10.

R18 results:

- **rrf_guarded_by_symbol_regex is the train-selected calibration candidate**: It preserves RRF FileRecall@1/MRR on full R15-M (0.941/0.963) and holdout (0.844/0.900) while reducing medium negative_nonempty to 0.000. It is not stress-safe: R15-stress negative_nonempty remains 0.474, above symbol's 0.105.
- **query_noise_plus_rrf_agree_min is a stress-zero observation, not a promotion**: Several thresholds reach 0.000 negative_nonempty on both R15-M and the 19-task stress set. This suggests combining query noise heuristics with regex/symbol agreement is promising, but the stress sample is too small and mined to justify promotion.
- **Threshold sweep reveals sharp recall cliff at 0.05**: Most RRF top scores are either very high or very low; thresholds above 0.03 reject nearly all evidence.
- **Pareto frontier shows recall vs hard-negative trade-off**: symbol (0.052 hard_neg, 0.807 recall) vs rrf_guarded (0.259 hard_neg, 0.941 recall) vs query_only_router_v0 (0.237 hard_neg, 0.904 recall).
- **No core default promotion in R18**: This is eval-layer calibration. Requires larger/human-verified validation before promotion.

Status: Eval-layer calibration only; does NOT change Rust core. No LLM/dense claims.

## Cross-stage findings

### 1. EvidenceCore stayed stable

R0-R11 did not require changing the core evidence contract. R12 also did not change it. Research features were added around it:

- storage uses StoreHit candidates;
- derived indexing uses DerivedIndexView;
- graph uses GraphEdge candidates and materialization;
- fast-context outputs EvidencePack-compatible wrappers.
- persistent BM25 uses Tantivy hits plus mandatory manifest/policy gates, then materializes from the current filesystem before output.
- AST chunking/symbol extraction only changes candidate boundaries; it still materializes final Evidence from current filesystem validation.
- Incremental update uses Tantivy delete-by-term + re-add with the same materialization path; no new evidence bypass.
- TDB adapter uses chunk metadata in JSON payloads with dim=1 smoke probe; materialization still goes through StoreHit.
- Real-repo benchmark uses temp copy of OpenLocus; all evidence still goes through the same materialization and citation validation path.

This validates the original “small and hard” contract design.

### 2. Materialization is the central safety boundary

The largest issues found during review were attempts to produce evidence without going through the materialization gate. R3 fixed this for store hits, R5 fixed it for graph edges, and R6 now performs final validation before output.

The rule should remain permanent:

```text
Candidates are not facts.
Only current-source materialized Evidence can be a fact.
```

### 3. Evaluation caught real mistakes early

The eval/review loop caught:

- over-wide regex spans;
- BM25 parse fallback returning all docs;
- stale BM25 hits;
- graph evidence hand-built without hash binding;
- R4 derived views with insufficient data-level/policy coverage;
- R6 weak final citation validation.

This supports continuing with evidence-gated development rather than feature-first implementation.

### 4. Retrieval quality is still mostly unsolved at span level

BM25 and RRF improved file recall on the current fixture, but SpanF0.5 is still low and token waste is high. More recall channels alone will not solve this. The next quality work should focus on:

- Tree-sitter chunking;
- function/class-level span boundaries;
- query expansion and intent classification;
- better gold datasets;
- persistent warm indexes for fair latency measurement.

### 5. LLM indexing is worth testing, but only through derived views

The R4 scaffold proves a safe route for future LLM-derived indexing:

```text
source span + content_sha + provider/model/prompt/policy provenance
-> DerivedIndexView
-> optional query hint / rerank feature
-> source materialization before final evidence
```

The next LLM step should be a quality bakeoff on low-risk view kinds (`chunk_summary`, `symbol_tags`, `query_aliases`) with provider policy and audit logging, not free-form repository summaries.

### 6. TDB entered as an adapter, not as the data model

The storage scaffold kept TDB in scope while avoiding premature commitment. R11 implemented the first real TDB adapter behind a feature flag, running the same conformance/materialization tests. It did not redefine EvidenceCore or become a default dependency. The adapter is a Level0 probe with honest capability reporting (metadata+chunks only, no lexical/vector/graph quality).

## Current caveats

This prototype is intentionally not production-ready.

- Default BM25 still builds a temporary index per query unless `--index persistent` is explicitly selected.
- Persistent Tantivy is implemented at Level0 with incremental update (R10); updates are file-level via --dirty or --path. No daemon/watch mode yet.
- Incremental update chunk count is approximate after update; full rebuild produces exact counts.
- Tantivy deletes are tombstones until merge; periodic full rebuild recommended for frequently-updated repos.
- Tantivy commit and manifest file write are not a single transaction; crash between may leave a safe but inconsistent state requiring rebuild or re-update.
- Dirty summary re-scans all indexed files (O(n)); filesystem watchers or mtime caching needed for very large repos.
- Skipped entries (empty files, read errors, path_unsafe) are tracked in manifest; they do not appear as "added" on subsequent dirty scans if sha is unchanged.
- ConservativeChunkStore is in-memory and ephemeral.
- TDB is a feature-gated Level0 adapter probe; not a default dependency. Real TriviumDB code is linked only when `--features tdb` is enabled.
- LLM indexing is a deterministic safety scaffold only; no real model/provider is used.
- AST chunking/symbol extraction is experimental; R9 bakeoff shows span precision improvement but FileRecall@5 regression on the small fixture. AST remains opt-in.
- Graph parsing is heuristic and line-based; no LSP/SCIP graph yet.
- Config graph edges are noisy.
- Fast Context is fixed-rule orchestration, not adaptive planning.
- Token budget uses chars/4 approximation, not a tokenizer.
- Policy globbing is simple and needs a mature matcher before broad use.
- Warm-index SLO now has Level0 synthetic measurement and real-repo measurement; larger and more diverse repo behavior is still unknown.
- R12 real-repo benchmark uses one repo (OpenLocus temp copy) with per-run unique alphanumeric markers; not a general performance claim. Growth catastrophic guard passed (observed 20-cycle ~1.11×); does not prove long-term bounded growth.
- R18 calibration sweep is on mined R15 data; not human-verified. Repo-holdout is small (9 repos, 3 holdout). R15-stress has only 19 tasks; metric estimates are noisy.
- R18 includes strategies that eliminate both R15-M and R15-stress negative_nonempty, but those are stress-zero observations on a small mined stress set, not default-promotion evidence. The train-selected candidate still leaves R15-stress negative_nonempty at 0.474.
- No core default promotion from R18; threshold/guard choices require larger/human-verified validation before promotion.

## Recommended next research stages

### R11 — real TDB adapter behind feature flag ✅ DONE

Priority: medium-high. **Completed in R11.**

Implemented TDB adapter behind `tdb` feature flag. TdbChunkStore with dim=1 smoke probe, metadata+chunks only, marker-based purge, materialization conformance. 11/11 adapter checks passed. No default dependency. No retrieval quality claim.

Gate:

- conformance tests pass ✅;
- corruption/purge/rebuild behavior understood ✅ (marker-based purge, refuses without marker);
- quality/latency/resource comparison against conservative track — deferred to future R13+ bakeoff.

### R12 — real-repo incremental robustness benchmark ✅ DONE

Priority: high. **Completed in R12.**

R10 proved a Level0 synthetic incremental loop. R12 tested one real repository sample with modify/add/delete/rename/policy-exclude/batch workloads:

- `eval/real_repo_incremental_bench.py` on temp copy of OpenLocus;
- all sampled workloads pass hard safety gates (no stale VerifiedCurrent, correct dirty detection, valid collected marker-search citations);
- per-run unique markers avoid self-contamination;
- positive gates require path+marker conjunction (not disjunction);
- latency compare uses twin repo copies (same mutation, report-only gate);
- growth catastrophic guard (observed 20-cycle ~1.11×; does not prove long-term bounded growth);
- sys.exit(1) on safety failure only; latency/growth gates report-only;
- total_invalid_citations=0;
- Level0 one real-repo sample only; not general performance claim.

Gate:

- no stale VerifiedCurrent evidence ✅;
- update path remains faster than full rebuild for small edits — measured honestly via twin repos (report-only gate);
- dirty status remains honest under adds/deletes/renames/excludes ✅;
- collected marker-search evidence validated; not "all evidence in repo".

### R13 — remote embedding and LLM-derived indexing safety scaffold

Goal: add a safe scaffold for future dense/semantic embedding and LLM-derived indexing experiments, without connecting to any real remote service.

Implemented:

- New crate `openlocus-provider` with `EmbeddingProvider` trait, `MockEmbeddingProvider` (deterministic blake3-based vectors, dimensions=32, no network), `DisabledEmbeddingProvider`.
- `ProviderLocality` enum: Disabled, Mock, Local, Remote.
- `ProviderMetadata` with provider_id, model_id, dimensions, locality, max_data_level, outbound_possible.
- `EmbedInput` with data_level, policy_mode, purpose; text field skipped in serialization.
- `EmbeddingRecord` stored in JSONL: path, range, source_content_sha, language, text_sha, vector (no raw text; vectors present for search).
- `EmbeddingAuditEvent` written as JSONL: timestamp, event, provider_id, model_id, locality, purpose, path, line_range, data_level, view_kind, bytes_selected, text_sha, secret_scan, policy_decision, cache_key, outbound_attempted, reason (no raw text, vector, or query text in audit).
- Policy gate (`gate_embed_input`): Remote requires policy.remote.allow + allow_embedding + provider in allowed list + data_level gate. Mock/Local: data_level ≤ 1 AND data_level ≤ metadata.max_data_level. Secret gate blocks SECRET/TOKEN/PASSWORD/API_KEY/PRIVATE_KEY/sk_/ghp_/AKIA and high-entropy strings.
- Cache key: `emb1:` + blake3 hex from canonical string with schema_version + provider_id + model_id + dimensions + view_kind + text_sha + source_content_sha + policy_mode + data_level. Cache key builder/stability only; no cache-hit behavior yet.
- Dense JSONL store (`JsonlEmbeddingStore`) at `.openlocus/embeddings/vectors.jsonl`: build from FileRecords with metadata-only views (path/language/basename/path-tokens, no code snippets at data_level=0); build uses real line counts: end_line=min(total_lines, 8) for valid ranges; cosine similarity search; StoreHit → `materialize_evidence(Channel::Dense)`.
- Audit writer at `.openlocus/audit/embeddings.jsonl`. Audit events use accurate names: `allow`, `block`, `query_embed`, `provider_unavailable` (not `cache_hit` unless real cache).
- CLI uses query_sha/query_len instead of raw query text in JSON output and trace events.
- CLI: `provider status --json`, `provider audit --limit N --json`, `dense build --provider mock --experimental --json`, `dense search <query> --provider mock --limit N --json`, `dense purge --json`.
- Disabled/unknown provider: audit event written with policy_decision=deny, event=provider_unavailable.
- Eval: `eval/provider_dense_safety.py` with 45 safety checks.

R13 implemented the safety scaffold for dense/LLM-derived indexing:

- All 45 safety checks pass: remote_default=false, outbound_default=false, experimental gate, audit contains no raw text/vector/query, vector store contains vectors but no raw text/code snippet, stale hit rejection, secret blocking, disabled/unknown provider graceful degradation with audit events, missing store graceful error, citation validity, short file range correctness, CLI JSON uses query_sha not raw query, audit event naming correct (no cache_hit), cache key stability (unit tests).
- Mock provider vectors are deterministic and normalized; no network dependency.
- Dense search produces StoreHits → materialize_evidence(Channel::Dense); stale hits correctly rejected.
- No real semantic quality claim. Mock vectors are blake3-based; they do not capture semantic similarity. Dense mock search is integration/safety only.

Gate:

- audit contains no raw text/vector/query; vector store contains embedding vectors but no raw text/code snippet ✅;
- remote denied by default ✅;
- experimental opt-in required ✅;
- secret scanning blocks token-like inputs ✅;
- graceful degradation when provider unavailable (with audit event) ✅;
- 45/45 safety checks passed ✅;
- mock quality only — not a real semantic retrieval claim.

### R14 — Scaled Evidence Benchmark Foundation ✅ DONE

Priority: high. **Completed in R14. Safety foundation passed.**

R14 establishes a scaled benchmark program for evaluating OpenLocus retrieval quality across repository groups and task types, structured as S/M/L/X tiers with increasing scale and label quality requirements. **This is a safety foundation, not a quality conclusion.** The current S/M data uses logical repo groups from one OpenLocus workspace snapshot; independent external repositories are a follow-up expansion.

Implemented:

- `fixtures/r14/` directory structure: README, taxonomy/annotation guide (fake path examples only), dataset_manifest.json, repos.lock.jsonl, tasks/{sanity,medium,large,stress}.jsonl, labels/{sanity,medium,large,stress}.jsonl, labels/_canary.json, expected_failures/known_issues.md.
- R14-S: 4 logical repo groups from one OpenLocus workspace snapshot, 48 tasks, 48 labels, 47 hard negatives. Label quality: 8 human_reviewed, 37 mined_high_confidence, 3 mined. **Populated=True, Evaluable=True.**
- R14-M: same 4 logical repo groups as S, 36 tasks, 36 labels, 31 hard negatives. **Populated=True, Partial=True.** Full M requires 8+ independent repo groups/repositories.
- R14-L: 10 placeholder tasks with weak labels. **Populated=False, Evaluable=False.** Requires additional repos.
- R14-X: Not populated. Running --tier X fails with clear message. **Populated=False.**
- `eval/r14_generate_dataset.py`: Generates/refreshes R14 data with normalized content manifest SHA (sha256 per file sorted). Glob-style policy excludes. Avoids label leakage.
- `eval/r14_benchmark.py`: Strictly separated RUN phase (public tasks only, no labels) and SCORE phase (labels only, no CLI). Isolated temp roots per repo group with `.openlocus/policy.toml` written from repo lock. Unknown repo_id fail-closed. Rust citation validation must be 1.0 (no path-only fallback). Forbidden path prefix/component detection. Span-overlap hard_negative_hit_rate@10. negative_nonempty_rate@10. Repo lock content manifest re-verification.
- `eval/r14_leakage_check.py`: 8 static checks: task gold leakage, query-gold overlap, labels not in indexed root (path-component matching), glob-style policy excludes, label file isolation, canary placement, repo lock manifest verification, predictions forbidden path scan. Runtime canary retrieval is enforced by `r14_benchmark.py`. 0 critical issues on R14-S.
- `eval/r14_smoke.py`: HARD FAIL smoke test. No best-effort. All checks must pass. Includes runtime canary retrieval, citation validity=1.0 with hash checked by Rust validator, forbidden path checks, isolated runner/scorer verification.

Key safety properties (fail-closed):

- Runner never loads labels/gold. Scorer never calls CLI. Strict phase separation.
- Isolated temp roots per repo group: only declared source paths are exposed. No fixtures/eval/docs/runs/target artifacts.
- Each isolated root writes `.openlocus/policy.toml` from the repo lock; unknown `repo_id` refuses to run instead of falling back to the full workspace.
- Citation validity must be 1.0 (fail-closed) via Rust citation validator. No path-only fallback.
- Repo lock content manifest is recomputed and verified (normalized SHA-256 per file sorted). Mismatch = CRITICAL.
- Policy excludes are glob-style patterns (fixtures/**, eval/**, etc) and are written into isolated roots.
- Canary tokens planted in labels; runtime retrieval against them must return 0 results.
- Predictions with forbidden path prefixes/components are CRITICAL failures.
- Hard negatives use span-overlap matching unless explicitly file-level.
- Negative task metrics: negative_nonempty_rate@10 (false positive rate).
- Label quality is explicit (human_reviewed / mined_high_confidence / mined / weak).
- R14-L/X not populated: running --tier L/X fails with clear message.

Gate:

- benchmark pipeline works end-to-end with fail-closed safety ✅;
- anti-leakage checks pass (0 critical issues, 8 checks) ✅;
- runner/scorer isolation enforced ✅;
- isolated temp roots per repo group ✅;
- citation validity is fail-closed (must be 1.0) ✅;
- repo lock content manifest re-verified ✅;
- glob-style policy excludes written into isolated roots ✅;
- runtime canary retrieval returns zero hits ✅;
- hard negatives are span-overlap first-class data ✅;
- negative task metrics present ✅;
- R14-L/X fail gracefully with clear messages ✅;
- R14-S is a safety foundation, not a quality conclusion ✅;
- graph precision is a future feature track ✅.

**Note**: The previous R14 roadmap item was "graph precision upgrade." This R14 redefines the stage as the scaled benchmark foundation. Graph precision is now tracked as a separate future feature.

### R15 — external multi-repo benchmark expansion ✅ DONE

Priority: high. **Completed in R15. Safety foundation passed.**

R15 extends the R14 benchmark foundation with real local multi-repo data from 9 independent external git repositories. It covers Rust, Python, Go, TypeScript, and JavaScript source code with multi-language symbol extraction.

Implemented:

- **9 external repos resolved** (all exist with sufficient source files):
  - fast-context-mcp (JS/.mjs), grok2api (Python), infinite-canvas (Go/TS/TSX), gemini-web2api (Python), windsurf2api (JS), kiro2 (Rust/TS/TSX), triviumdb (Rust), smartsearch (Python/JS), codex2api (Go/TS/TSX)
- **fixtures/r15/ directory**: README, dataset_manifest.json, repos.lock.jsonl, tasks/{medium,large,stress}.jsonl, labels/{medium,large,stress}.jsonl, taxonomy/annotation_guide.md, expected_failures/known_issues.md, safety_checks.json
- **R15-M**: 9 repos, 166 tasks, 166 labels, 270 hard negatives. Label quality: 135 mined_high_confidence + 9 mined + 10 human_reviewed + 12 weak. Populated=True.
- **R15-L**: 9 repos, 294 tasks, 294 labels, 270 hard negatives. Label quality: 270 mined + 24 weak. Populated=True.
- **R15-stress**: 9 repos, 19 tasks, 19 labels, 0 hard negatives. Label quality: 3 human_reviewed + 16 weak. Populated=True (partial).
- **eval/r15_generate_dataset.py**: Multi-language source scanning (.rs .py .ts .tsx .js .jsx .go .mjs). Regex-based symbol extraction for Rust/Python/Go/JS/TS. Normalized manifest SHA across all source extensions. Skip node_modules/target/.git/dist/build/.venv/etc.
- **eval/r15_benchmark.py**: Extends R14 benchmark for absolute repo source roots. Creates isolated roots by allowlist-copying only manifest/source files under repo_id-specific folders; symlinks and artifacts are skipped. Unknown repo_id fail-closed. Runtime `.openlocus` traces are removed after every query/citation validation and audited before/after each method. Rust citation validator runs before isolated-root cleanup and must report 1.0 validity. Scoring accepts exact paths or a single `repo_id/` prefix, not arbitrary suffixes. Same fail-closed safety gates.
- **eval/r15_leakage_check.py**: Static checks include exact 9-repo lock integrity, absolute source path verification, multi-language manifest verification, task/label/manifest consistency, hard-negative non-overlap, source_repo_kind in labels, canary placement, and forbidden artifact path checks. 0 critical issues.
- **eval/r15_smoke.py**: 112/112 HARD FAIL smoke checks passed. Fixture validation, leakage check, benchmark (regex, bm25), Rust citation hash gate, canary verification, multi-language coverage.

R15-M baseline metrics:

| Metric | regex | bm25 |
|---|---|---|
| file_recall@1 | 0.852 | 0.548 |
| file_recall@5 | 0.956 | 0.719 |
| file_recall@10 | 0.970 | 0.741 |
| mrr | 0.889 | 0.623 |
| span_f0.5@10 | 0.263 | 0.188 |
| hard_negative_hit_rate@10 | 0.289 | 0.230 |
| negative_nonempty_rate@10 | 0.000 | 0.645 |

Gate:

- 9 independent external repos across 5 languages ✅
- 166 medium-tier tasks, 270 hard negatives ✅
- fail-closed safety (0 critical leakage, canary zero hits) ✅
- isolated roots with repo_id-specific folders and allowlisted source-file copying ✅
- unknown repo_id fail-closed ✅
- exact or single `repo_id/` prefix path matching for scoring ✅
- Rust citation hash/range validation before isolated-root cleanup ✅
- multi-language manifest verification ✅
- 112/112 smoke checks passed ✅
- mined benchmark expansion, not quality conclusion ✅

### R16 — multi-method quality bakeoff ✅ DONE

Priority: high. **Completed in R16. All safety gates passed.**

R16 runs a cross-matrix quality bakeoff across R14-S, R15-M, and R15-stress using all four lexical/symbol/RRF methods (regex, BM25, symbol, RRF). It produces aggregate JSON and markdown reports with winners per metric and safety verification.

Implemented:

- **eval/r16_quality_bakeoff.py**: CLI args `--openlocus`, `--workspace`, `--out`, `--skip-run`. Runs three benchmark matrices via subprocess. Verifies safety_passed, citation_validity=1.0 for each method with evidence, citation_hash_checked true or citation_not_applicable true, canary_retrieval.passed where present. Produces aggregate JSON (schema_version r16-v1) with runs metadata, method tables, winners per metric, safety_checks, conclusions. Produces markdown report. Hard fails on any safety gate or runner failure. No provider/dense/LLM claims.
- **docs/r16-quality-bakeoff.md**: Stable report with current results and caveats.

R16 bakeoff results:

R14-S: BM25 dominates recall/MRR; symbol wins span precision (0.199 SpanF0.5, 0.043 hard_neg); all methods 0.000 negative_nonempty.

R15-M: RRF wins recall (FileRecall@1 0.933, @5/10 0.993, MRR 0.959) but inherits BM25 negative_nonempty false positives (0.645); symbol wins span precision (0.310 SpanF0.5, 0.052 hard_neg, 0.000 neg_nonempty).

R15-stress: Symbol has lowest false-positive rate (0.105 negative_nonempty); BM25/RRF worst (0.684).

Key conclusions:

1. RRF wins recall but inherits BM25 false-positive behavior; not safe as default without negative gating or query intent routing.
2. Symbol best span precision/hard-negative profile; ideal as precision anchor, not sole retriever.
3. Regex strong on exact-symbol tasks but reflects task distribution bias.
4. BM25 strong in R14-S but weak/false-positive-heavy in R15-M/stress.
5. No method promoted to universal default; next research should be query intent router / negative guard / method fusion policy.

Safety facts:

- All three matrices: safety_passed=true
- All methods: citation_validity=1.0, citation_hash_checked=true
- canary_retrieval.passed=true where present
- No remote calls; lexical/symbol/RRF only

Gate:

- safety_passed=true across all matrices ✅
- citation_validity=1.0 for all methods ✅
- citation_hash_checked=true ✅
- canary_retrieval.passed=true ✅
- no remote calls ✅
- no provider/dense/LLM claims ✅

## Final conclusion

The current implementation successfully converts the research design into a working, reviewable prototype. The project now has:

- a stable evidence contract;
- local read/search/retrieve primitives;
- file-backed citation validation;
- retrieval method bakeoff harness;
- storage, derived-index, graph, persistent-index, and fast-context safety scaffolds;
- AST vs line quality bakeoff with measurable span precision improvement;
- incremental index with dirty summary and file-level update;
- feature-gated TriviumDB Level0 adapter probe;
- real-repo incremental robustness benchmark (modify/add/delete/rename/policy-exclude/batch/latency/growth);
- provider/embedding safety scaffold with mock provider, policy gate, secret scanning, dense JSONL store, and embedding audit (45/45 safety checks passed);
- **scaled evidence benchmark safety foundation (R14) with S/M/L/X tiers, fail-closed runner/scorer isolation, isolated temp roots, citation validity=1.0 via Rust validator, repo-lock policy files, runtime canary retrieval, repo lock manifest re-verification, span-overlap hard negatives, negative task metrics, and explicit label quality tracking**;
- **external multi-repo benchmark expansion (R15) with 9 independent external repos across 5 languages (Rust/Python/Go/JS/TS), 166 medium-tier tasks, 270 hard negatives, multi-language symbol extraction, absolute source paths, isolated roots with repo_id-specific allowlist source-file copying, strict Rust citation validation, exact/single-prefix scoring path matching, 112/112 smoke checks passed, mined benchmark expansion not quality conclusion**;
- **multi-method quality bakeoff (R16) across R14-S/R15-M/R15-stress with regex/bm25/symbol/rrf, all safety gates passed, RRF wins recall but inherits BM25 false positives, symbol best span precision, no method promoted to universal default, lexical/symbol/RRF only, no provider/dense/LLM claims**;
- **large/stress guard generalization validation (R19) on R15-L (294 weak/mined tasks) and R15-stress, rrf_guarded_by_symbol_regex generalizes to R15-L (recall preserved, neg_nonempty 0.917→0.042) but fails stress (0.474 vs symbol 0.105), query_noise_plus_rrf_agree_min_0.0 stress-zero observation repeated, R15-L labels are weak/mined so generalization smoke only, promotion_ready=false always, no core changes, no LLM/dense claims**;
- pushed checkpoints for each stage.

The next phase should not rush into a full LLM/dense/TDB system. The safest path is to continue testing incremental robustness on more real repositories (R12 completed one OpenLocus temp-copy sample), then extend TDB to meaningful search quality (R11 adapter probe complete), plug in real embedding providers behind the existing policy gate (R13 scaffold ready), and run bakeoffs against the conservative baseline.

### Recommended next stages

- **R14+ graph precision**: Add Tree-sitter/LSP/SCIP-like graph adapters behind the same graph model. Keep heuristic graph as baseline. Gate: impact/test-selection fixture improvement; depth>1 opt-in; graph results still materialize through StoreHit. This is a future feature track, not the current R14 definition.
- **R15+ fast-context quality bakeoff**: Compare `openlocus fast-context` against `retrieve` over larger task sets. Add ablations: no graph, no symbol, BM25 only, derived hints, dense hints. Gate: no citation regressions; budget violations=0; FileRecall/MRR/SpanF0.5 improve or stay within allowed regression.
- **R17 query intent router / negative guard** ✅ DONE: Eval-layer experiment. query_only_router_v0 eliminates R15-M negative_nonempty (0.645→0.000) with acceptable recall regression. rrf_guarded_by_symbol_regex eliminates R15-M negative_nonempty with zero regression. R15-stress not fully solved (0.158/0.474). No Rust core changes. Next: learning/calibrating intent classifier or score thresholds, still evidence-gated.
- **R19 large/stress guard generalization validation** ✅ DONE: Eval-layer validation on R15-L and R15-stress. rrf_guarded_by_symbol_regex generalizes to R15-L but fails stress. query_noise_plus_rrf_agree_min_0.0 stress-zero observation repeated. R15-L labels are weak/mined; generalization smoke only. No promotion. No core changes. Next: human-verified labels and larger stress dataset needed before any default change.
- **R18 real remote embedding after policy review**: Integrate real embedding providers (e.g. OpenAI, local ONNX) behind the R13 policy gate. Requires policy review, API key management, and cost tracking. Gate: quality gain measured in eval; no policy regression; graceful degradation when provider unavailable; audit trail complete.
- **R14-M/L/X expansion**: Expand the benchmark to additional repositories (8+ for M, 16+ for L, 32+ for X). Add human-reviewed labels for critical tasks. Run full method comparison across tiers.
