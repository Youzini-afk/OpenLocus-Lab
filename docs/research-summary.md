# OpenLocus Research Summary

This document will be updated after each evidence-gated stage.

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

## Verification snapshot

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
