# OpenLocus Research Log

## 2026-06-11 — R0/R1 bootstrap

### Objective

Start an evidence-gated implementation that can validate the core contract before adding dense, graph, TDB, or LLM indexing experiments.

### Current hypothesis

The first useful milestone is not semantic retrieval. It is a trustworthy local evidence kernel with traceability, citation validation, and file-backed context-lite.

### Stage gates

- R0 passes when every returned result is traceable as `EvidenceCore` and citation validation can verify path/range/hash.
- R1 passes when read, repo scan, regex search, and context-lite work without remote dependencies.

### Implementation notes

- Initialized a Rust workspace with separate crates for core contracts, repo IO, retrieval, and CLI.
- Implemented `EvidenceCore` as the stable output contract: `path`, `start_line`, `end_line`, `content_sha`, `score`, `why`, `channels`.
- Kept `EvidenceMeta` optional so policy/freshness/excerpt/language metadata can evolve without breaking core evidence.
- Implemented local-only policy defaults and basic `.openlocus/policy.toml` loading.
- Implemented trace JSONL output under `.openlocus/traces/` for command-level observability.
- Implemented file reads with range parsing and symlink escape protection.
- Implemented repo scanning with default ignores, policy include/exclude, and gitignore control.
- Implemented line-based regex/text search. A review caught an early over-wide span design; it was corrected so each matched line returns a narrow Evidence span.
- Implemented citation validation for single Evidence, Evidence arrays, and `{ evidence: [...] }` packs, including range/hash/excerpt checks.
- Implemented context-lite file creation as an initial file-backed session fact surface.

### Review findings resolved

- **Search span precision**: fixed broad first-match-to-last-match spans; regex/text search now returns per-line evidence.
- **Citation validation**: now validates path, range, current file hash, and excerpt consistency.
- **Path safety**: existing targets are canonicalized to prevent symlink escapes outside the repo.
- **Freshness correctness**: search evidence hashes the bytes actually read for the match, avoiding stale scan-record hashes.
- **Policy basics**: scan include/exclude and `include_gitignored` now affect scan behavior.

### Verification

```text
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
cargo build --workspace
openlocus read README.md:1-3 --json
openlocus citations validate /tmp/openlocus-evidence.json --json
openlocus search regex OpenLocus --json
openlocus citations validate /tmp/openlocus-search.json --json
openlocus context-lite --write-files --json
python3 eval/run_retrieval.py --dataset fixtures/smoke.jsonl --out runs/smoke-rg.jsonl --openlocus target/debug/openlocus
python3 eval/score.py --pred runs/smoke-rg.jsonl
```

All Rust checks passed. CLI smoke eval returned success rate `1.0`.

### Caveats carried forward

- Regex search is intentionally line-based in R1; multiline regex spanning line boundaries is not supported yet.
- Context-lite currently writes minimal placeholder files; deeper dirty/test/diagnostics ingestion belongs in a later hardening pass.
- Policy globbing is intentionally simple and should be replaced with a mature matcher before broad user-facing use.
- Trace events are command-level and not yet full replayable retrieval trajectories.

---

## 2026-06-11 — R2 Retrieval Method Bakeoff

### Objective

Add local-only, evaluable, EvidenceCore-compatible BM25/symbol/RRF retrieval methods. Do not implement dense, TDB, LLM, or graph indexing yet.

### Hypothesis

BM25 over bounded line chunks with line tightening will outperform plain regex for file-level recall while maintaining narrow evidence spans. Symbol search will provide high-precision single-line hits for definition queries. RRF fusion of regex + BM25 + symbol will achieve the best combined file recall and MRR.

### Implementation notes

- **BM25 search** (`bm25_search.rs`): Builds an in-temp Tantivy index over bounded line chunks (max 30 lines). Schema: path, language, content_sha (STRING|STORED), start_line, end_line (u64 STORED), content (TEXT|STORED). Returns Evidence tightened to the best-matching line ±2 context, capped at 7 lines. content_sha recomputed from current file bytes. Channel::Bm25, meta.score_parts.bm25, meta.freshness = verified_current. Query parser safe fallback on parse errors.
- **BM25 span selection**: Each chunk hit is line-scored by query token overlap (not chunk center). If no line has any query token overlap, the hit is skipped (precision-biased). The best-scoring line becomes the center, ±2 context, capped at 7 lines.
- **BM25 stale check**: Index-time content_sha from Tantivy stored fields is compared to current file hash. Mismatch → skip hit. Line range strictly guarded: 1 ≤ start ≤ end ≤ total_lines.
- **Symbol search** (`symbol_search.rs`): Simple heuristic regex-based symbol extraction for Rust/Python/TS/JS/Go. Returns narrow single-line Evidence around the signature/head. Uses Channel::Regex with why="simple_symbol: {name}". Fills meta.symbol with name + kind. Language-aware pattern filtering prevents cross-language false matches. Word-boundary delimiters prevent partial matches (e.g. "User" won't match "UserProfile").
- **RRF fusion** (`rrf.rs`): Combines evidence from multiple channels using Reciprocal Rank Fusion (k=60). Exact same (path, start_line, end_line) → merge why/score/channels. Overlapping spans on same path → keep narrower, discard wider. The wider's why, channels, and RRF score are merged into the narrower survivor (no span widening). Tie-break: score desc, path asc, start_line asc, end_line asc. RRF only changes ranking/score, never widens spans.
- **CLI**: Added `search bm25 <query>`, `search symbol <query>`, `retrieve <query> --channels regex,bm25,symbol --max-results N`. All new commands append trace events.
- **Eval**: Updated `run_retrieval.py` to accept `--method regex|text|bm25|symbol|rrf`, `--channels` for RRF. Updated `score.py` with structural_validity + citation_validity, FileRecall@1/5/10, FilePrecision@5/10, MRR, LinePrecision@10, LineRecall@10, SpanF0.5@10, token_waste_ratio@10, wrong_span_rate@10 (gold-file-only), zero_overlap_evidence_rate@10 (all evidence). Python scorer verifies path/range and verifies BLAKE3 hashes when optional Python `blake3` is installed; Rust CLI validator is used for hash/excerpt-backed citation checks. Added `fixtures/r2.jsonl` with 28 tasks, gold spans refreshed to current codebase.

### R2 eval results (after oracle review fixes)

| Metric | regex | bm25 | symbol | rrf |
|---|---|---|---|---|
| file_recall@1 | 0.21 | **0.39** | **0.39** | **0.39** |
| file_recall@5 | 0.36 | **0.86** | 0.39 | 0.82 |
| file_recall@10 | 0.50 | **0.86** | 0.39 | 0.82 |
| mrr | 0.29 | **0.58** | 0.39 | 0.56 |
| line_precision@10 | 0.06 | 0.04 | **0.39** | 0.06 |
| line_recall@10 | 0.01 | **0.04** | 0.01 | 0.04 |
| span_f0.5@10 | 0.04 | 0.04 | **0.06** | 0.06 |
| structural_validity | **1.0** | **1.0** | **1.0** | **1.0** |
| citation_validity | **1.0** | **1.0** | **1.0** | **1.0** |
| wrong_span_rate@10 | 0.77 | 0.80 | **0.0** | 0.76 |
| zero_overlap@10 | 0.92 | 0.95 | **0.0** | 0.93 |
| avg_latency_ms† | 18 | 145 | 272 | 421 |

† CLI end-to-end latency including index build (BM25/RRF) or file scan (symbol). Not a warm-index benchmark.

### Key findings

1. BM25 substantially improves file-level recall on the current self-referential fixture (0.39 vs 0.21 at k=1, 0.86 vs 0.36 at k=5). This is an early local-only bakeoff result, not a general benchmark claim.
2. Symbol search has the highest line precision (0.39) and zero wrong spans when it fires, but only activates for definition-style queries on known languages.
3. RRF fusion approaches BM25-level file recall (0.82 at k=5) while incorporating symbol precision, achieving 0.057 SpanF0.5@10 in this fixture.
4. All methods produce structurally citation-valid evidence in the Python scorer. Current aggregated R2 output was also validated by `openlocus citations validate` with `0` invalid citations (hash/range/excerpt checked).
5. Token waste ratio remains high (~0.92) — evidence spans are narrow but often miss gold lines. Query-token line scoring fixed chunk-center anchoring, but chunking/query expansion/gold-span calibration need further refinement.
6. BM25 stale check and no-overlap skip are effective: no stale or center-only hits appear in the output.
7. Symbol boundary delimiters prevent partial matches (verified: "User" does not match "UserProfile").

### Oracle review fixes applied

- **BM25 span selection**: Replaced chunk-center anchoring with line-level query token overlap scoring. Hits with no token overlap are skipped (precision-biased).
- **BM25 stale check**: Index-time content_sha compared to current file hash. Mismatch → skip. Strict line range guard added.
- **BM25 query fallback**: Removed `*` all-doc fallback; parse failures now degrade to sanitized query or empty results.
- **Symbol boundary**: Added `(?:[^a-zA-Z0-9_]|$)` delimiter after symbol name in all patterns. Prevents partial matches.
- **RRF overlap dedup**: Wider span's why/channels/score are now merged into the narrower survivor. Deterministic tie-break: score desc, path asc, start_line asc, end_line asc.
- **Eval citation validity**: Split into `structural_validity` (no I/O) and `citation_validity` (path/range by default; hash check when optional Python `blake3` is installed). Added `--repo-root`. For hash/excerpt-backed validation, use `openlocus citations validate`.
- **Eval metrics**: Added `zero_overlap_evidence_rate@10` (all evidence, not just gold-file). `wrong_span_rate@10` now only counts evidence on gold files. Added `--channels` to `run_retrieval.py`.
- **Fixtures**: Refreshed gold spans to current codebase actual line numbers.

### Caveats carried forward

- BM25 builds a fresh Tantivy index per query; not suitable for large repos without persistent indexing.
- Symbol search is heuristic-only; real TreeSitter or SCIP would improve recall.
- Line-level metrics are low because gold spans target specific code regions; the eval is more meaningful for file-level metrics at this stage.
- BM25 CLI end-to-end latency includes index build; a persistent index would reduce this significantly.
- The Rust `regex` crate does not support lookahead; symbol boundary uses consuming match `(?:[^a-zA-Z0-9_]|$)` instead.

---

## 2026-06-11 — R3 Level0 Storage Scaffold/Conformance

### Objective

Add Store traits + StoreHit materialization gate + conservative storage surface + TDB Level 0 test surface. Do not implement dense/LLM/graph quality or make TDB a default dependency. This is a Level0 storage scaffold, not a full storage bakeoff or TDB comparison.

### Hypothesis

A storage abstraction layer with materialization gating (StoreHit → filesystem Evidence) will enable safe backend substitution. The conservative in-memory chunk store should pass conformance tests. TDB can be represented as a placeholder that correctly reports unavailability rather than being silently missing.

### Implementation notes

- **Store crate** (`openlocus-store`): New workspace crate with types (SnapshotId, ChunkKind, ChunkKey, ChunkRecord, StoreSource, StoreDebug, StoreHit, StoreCapabilities, StoreHealth, StoreError) and traits (StoreBackend, ChunkStore, LexicalStore, VectorStore, GraphStore).
- **Materialization gate** (`materialize_evidence`): Critical gate that converts StoreHit → Evidence by: (0) reject empty content_sha, (1) validate_path (symlink protection), (2) read file bytes once; compute content_sha from same bytes (TOCTOU-safe), (3) reject stale hits (sha mismatch), (4) decode same bytes for line content; validate range (1 ≤ start ≤ end ≤ total_lines), (5) build excerpt from decoded content, (6) return Evidence with freshness=VerifiedCurrent. Store backends never directly output authoritative Evidence.
- **ConservativeChunkStore**: In-memory ephemeral implementation (mode=ephemeral_in_memory, persistent=false) with metadata=true, chunks=true, lexical=false, vector=false, graph=false. Build validates paths via validate_path, skips stale records (content_sha mismatch), skips empty files (no start=1,end=0 invalid chunks), computes content_sha from same bytes used for line splitting. Does not walk filesystem itself.
- **TdbPlaceholderStore**: Level 0 test surface implementing StoreBackend with available=false, success=false, mode=placeholder, and all capabilities false. Returns clear error messages ("feature 'tdb' is not enabled"). Does not add triviumdb as a dependency.
- **CLI**: Added `openlocus store status/build/purge conservative|tdb --json`. JSON output includes mode, persistent, and success fields. All commands append trace events.
- **Eval**: Added `eval/storage_bakeoff.py` with report_kind="storage_level0_smoke". Uses positional backend syntax.

### R3 Level0 conformance results

| Check | Result |
|---|---|
| Conservative build from scan_repo | ✅ chunks, files, valid ranges |
| Conservative capabilities explicit | ✅ metadata+chunks only |
| Conservative skips stale records | ✅ test passes |
| Conservative skips empty files (no invalid chunks) | ✅ test passes |
| Conservative skips traversal records | ✅ test passes |
| Conservative purge | ✅ clears all data |
| TDB status returns available=false, success=false | ✅ |
| TDB build returns error, not panic | ✅ |
| TDB purge returns error, not panic | ✅ |
| Materialize rejects empty content_sha | ✅ test passes |
| Materialize rejects stale hit | ✅ test passes |
| Materialize rejects invalid range | ✅ test passes |
| Materialize produces citation-valid Evidence | ✅ test passes |
| Materialize TOCTOU-safe (sha + excerpt from same read) | ✅ test passes |
| Ingest only from scan_repo records | ✅ store never walks filesystem |
| Unknown backend returns error | ✅ |

### Key findings

1. The materialization gate is essential and works correctly: empty sha rejected, stale hits rejected, invalid ranges rejected, and produced Evidence is citation-valid (verified_current freshness, correct content_sha, excerpt from current file).
2. TOCTOU safety matters: reading file bytes once and deriving both sha and excerpt from that single read prevents a file modification between sha computation and excerpt extraction from producing inconsistent evidence.
3. ConservativeChunkStore validates paths and skips stale/invalid records: traversal paths are rejected, stale content_sha records are skipped, empty files produce no invalid chunks.
4. TDB placeholder provides a clean Level 0 test surface: CLI commands return JSON with available=false, success=false, and descriptive errors rather than panicking or silently failing.
5. All ingest comes from scan_repo filtered records; stores never walk the filesystem. Policy filtering is automatically respected.

### Caveats carried forward

- ConservativeChunkStore is in-memory ephemeral only; data does not persist across CLI invocations. A persistent index (e.g. sidecar file) would be needed for production use.
- TDB placeholder does not exercise any actual TriviumDB code; it only validates the API shape. When a real adapter is needed, it should be behind a feature flag with an optional dependency.
- VectorStore and GraphStore traits are defined but not implemented; they are placeholders for R4+ experimentation.
- The store does not yet integrate with BM25 search; BM25 still builds a fresh Tantivy index per query.
- This is a Level0 storage scaffold, not a full storage bakeoff or TDB comparison. No real storage-backed retrieval quality comparison is claimed.

---

## 2026-06-11 — R4 LLM Indexing Research Candidate Level0 Safety Scaffold

### Objective

Add DerivedIndexView model + deterministic rule/mock generator + policy/citation/freshness gates + JSONL store + CLI/eval. No real LLM, no quality claim. This is a Level0 safety scaffold: prove the gates work before connecting any remote service.

### Hypothesis

A derived index view system with strict safety gates (no-LLM-required generator, policy-gated kinds, data_level bounds, source validation, experimental opt-in) can be implemented and verified without any remote calls. The safety gates should block all high-risk operations by default.

### Implementation notes

- **Derived crate** (`openlocus-derived`): New workspace crate with model (DerivedIndexView, DerivedViewKind, DerivedSource, DerivedGeneratorKind, DerivedProvenance, DerivedValidation), generator (deterministic rule extractor for L1 kinds), validation (path/content_sha/range/kind/data_level checks), and JSONL store.
- **Key constraint**: DerivedIndexView is NOT Evidence. It cannot bypass StoreHit/materialize_evidence. If derived search is ever implemented, it must materialize source evidence.
- **Generator**: Deterministic rule-based extractor for chunk_summary, symbol_tags, query_aliases. No full raw code snippets at data_level ≤ 1 (only metadata + first identifier per chunk). Identifier extraction via simple heuristics; query alias splitting via camelCase/snake_case decomposition.
- **Validation**: validate_derived_view checks path safety (via validate_path), source content_sha matches current file, range valid, kind allowed, data_level allowed. No remote calls.
- **Store**: JsonlDerivedViewStore writes to `.openlocus/derived/views.jsonl` with audit log at `.openlocus/derived/audit.jsonl`. Supports upsert (replaces by view_id), list, purge.
- **View ID**: Deterministic hash of (source_path, source_sha, kind, generator, data_level, policy_mode, generator_version). Same inputs always produce the same ID. Source, policy, or generator-version changes produce different IDs.
- **High-risk kinds**: candidate_edge and bug_symptom_hint are disabled by default (is_high_risk() = true). Generator skips them entirely.
- **CLI**: `openlocus derived build/validate/inspect/purge`. Build requires `--experimental`. All commands output JSON with remote_calls=0, data_level, policy_mode.
- **Eval**: `eval/derived_safety.py` with report_kind="derived_level0_safety".

### R4 Level0 safety results (after oracle review fixes)

| Safety Check | Result |
|---|---|
| Build without --experimental blocked | ✅ clear error JSON |
| Build with --experimental succeeds | ✅ views generated |
| Build with --max-data-level 2 blocked | ✅ Level0 hard gate |
| remote_calls always 0 | ✅ |
| candidate_edge blocked | ✅ blocked_kind=1, generated=0 |
| bug_symptom_hint blocked | ✅ blocked_kind=1, generated=0 |
| data_level ≤ 1 enforced | ✅ Level0 hard gate |
| No raw full code in derived text at data_level=1 | ✅ test passes |
| Secret-like tokens filtered (SECRET_KEY, API_TOKEN, sk_, ghp_, AKIA) | ✅ test passes |
| View ID deterministic | ✅ test passes |
| View ID changes on source change | ✅ test passes |
| View ID changes on policy_mode change | ✅ test passes |
| View ID changes on generator_version change | ✅ test passes |
| Validate detects stale views | ✅ test passes |
| Validate detects blocked kind | ✅ test passes |
| Validate detects blocked data_level | ✅ test passes |
| Validate detects path_unsafe | ✅ test passes |
| Validate detects invalid range | ✅ test passes |
| Validate surfaces parse_errors | ✅ corrupt JSONL test passes |
| Stale mutation detected (modify file → validate → stale>0) | ✅ eval passes |
| Policy-excluded paths absent (.env, *.pem) | ✅ eval passes |
| Purge removes views and audit files | ✅ eval passes |

### Key findings

1. The safety scaffold works: all gates are functional and block by default. High-risk kinds are blocked, data_level is hard-gated at ≤1 for Level0, experimental opt-in is required, and no remote calls are made.
2. Deterministic view IDs include policy_mode and generator_version: the same source/kind/generator/data_level/policy_mode/generator_version always produces the same ID, and a change in any of these produces a different ID.
3. At data_level ≤ 1, derived text contains only metadata (line range, language, first identifier) — no full raw code snippets. This prevents accidental exposure of sensitive code in derived artifacts.
4. Secret-like tokens are aggressively filtered: identifiers containing SECRET/TOKEN/PASSWORD/API_KEY/PRIVATE_KEY, or with prefixes sk_/ghp_/AKIA, or long high-entropy mixed-case strings are not emitted in tags or aliases.
5. JSONL parse errors are surfaced (not silently skipped): `derived validate` reports parse_errors count; safety eval fails if parse_errors > 0.
6. Stale mutation is detected: building views, modifying a source file, then validating correctly reports stale views.
7. The rule-based generator is intentionally simple: identifier extraction, camelCase/snake_case splitting. It is not a replacement for real LLM-based indexing; it proves the pipeline shape works.

### Caveats carried forward

- This is a Level0 safety scaffold only. No quality claim about derived view relevance or usefulness.
- The rule-based generator produces coarse metadata; real LLM indexing would produce richer summaries and aliases.
- DerivedIndexView is not Evidence and cannot be used as such. Any future derived search must materialize source evidence through the store gate.
- The JSONL store does not scale for large repos; it reads/writes the full file on each operation.
- candidate_edge and bug_symptom_hint are defined but never generated; they serve as API surface for future high-risk experiments.
- No real LLM adapter exists. The MockLlm generator kind is defined but not implemented.
- Derived views are not integrated with the RRF retrieval pipeline; this is a future optimization.
- The secrets/ directory is not in the default exclude list; only .env* and **/*.pem are excluded by default.

## 2026-06-11 — R5 Semantic Graph Level0 Deterministic Scaffold

### Objective

Implement a local-only, deterministic, depth=1 semantic graph scaffold. No LSP/SCIP/LLM. Graph candidates cannot directly substitute for Evidence; must be materialized through StoreHit → `openlocus_store::materialize_evidence()`.

### Implementation

1. **openlocus-graph crate**: Types (GraphNode, GraphEdge with source_content_sha/source_language, EdgeKind, GraphBuildResult, GraphCapabilities), builder, and materializer.
2. **Edge kinds**:
   - imports: parse Rust `mod/use`, TS/JS `import ... from`, Python `import/from`, Go `import` lines. Resolution uses path_set and basename_index.
   - tests: path/name heuristic (tests/ dir, *_test.*, *.test.*, test_*) linking to source files with matching basename.
   - configures: config files (Cargo.toml, package.json, etc.) to nearby source files (bounded max 50).
3. **Safe record construction**: `build_graph` validates paths and current sha, creates safe_records, and builds import/test/config edges only from safe/current records. Stale and path-unsafe records are counted and skipped.
4. **Materialization via StoreHit**: `materialize_graph_evidence()` converts GraphEdge to StoreHit and delegates to `openlocus_store::materialize_evidence(repo_root, &hit, Channel::Graph)`. Invalid ranges are rejected (not clamped). Graph-specific why/score_parts are added post-materialization without changing span/hash.
5. **Depth gate**: depth>1 returns error, not silently expanded.
6. **CLI**: `graph build`, `graph inspect` (with artifact="graph_edges_not_evidence" marker), `impact <path> --depth N` (with skipped count), `tests select --path P` (with skipped count).

### Oracle review fixes

- GraphEdge now carries source_content_sha and source_language at build time.
- materialize_graph_evidence converts to StoreHit and calls openlocus_store::materialize_evidence (not hand-building Evidence). Invalid ranges rejected (not clamped).
- build_graph builds safe_records/path_set/sha map from validated current records only; test/config edges built from safe_records only.
- graph inspect wraps output with artifact="graph_edges_not_evidence" marker.
- tests command includes skipped count.
- eval/graph_smoke.py uses synthetic temp fixture repo, includes import/test/config examples, true citation validation via `openlocus citations validate`, policy-excluded file checks, depth-2 blocking.

### R5 Level0 results (after oracle review)

| Check | Result |
|---|---|
| Graph build succeeds | ✅ |
| Edges > 0 (imports + configures + tests) | ✅ |
| Inspect has artifact marker | ✅ |
| Impact returns citation-valid evidence | ✅ verified via citations validate |
| Depth=2 blocked | ✅ clear error JSON |
| Tests select works | ✅ with skipped count |
| Stale check active (skipped_stale field) | ✅ |
| Policy excluded (.env, .pem) absent from edges | ✅ |
| StoreHit materialization gate | ✅ edges → StoreHit → materialize_evidence |

### Key findings

1. Simple line-based import parsing is surprisingly effective for Rust and Python repos. The path_set resolution approach (look for candidate files in same directory or by basename) avoids needing a full module resolver.
2. Config edges dominate because each config file links to all nearby source files. This is noisy but safe for Level0.
3. Test heuristics work for common patterns (*_test.rs, *.test.ts, tests/ dir) but don't handle inline tests or less common naming conventions.
4. Materialization via StoreHit gate is essential: graph edges carry build-time sha, and `materialize_evidence` rejects stale/invalid hits. This means graph-derived evidence is always citation-valid.
5. Graph is rebuilt on each command (not persisted). Stale records are caught at build time.

### 限制

- This is a Level0 deterministic scaffold only. Not a precise call graph, type graph, or dependency graph.
- Import parsing is line-based heuristic, not a full parser. It will miss multi-line imports and macro-generated code.
- Go import resolution is not implemented (requires module path mapping).
- Test heuristic only links by filename/path convention, not by analyzing test content.
- Config edges are noisy (many false positives). A future version should be more targeted.
- Graph is rebuilt on each command (not persisted). For large repos, this needs caching.
- Stale detection works at build time only (graph rebuilt per command). A persistent graph would need materialization-time stale checks, which the StoreHit gate already provides.
- Graph edges are not integrated with the RRF retrieval pipeline; this is a future optimization.

## 2026-06-11 — R6 Fast Context Level0 Rule Prototype

### Objective

Implement a 4-turn deterministic fast-context loop using existing regex/bm25/symbol/graph channels, returning citation-valid EvidencePack. No LLM planner, no remote calls. Budget cap enforced. Graph depth=1 only.

### Implementation

1. **openlocus-context crate**: FastContextPlan, TurnResult, TurnKind, FastContextResult, ActionRecord, FastContextDiagnostics types.
2. **4-turn loop**:
   - Turn 1 (Lexical): regex/text search, optionally BM25. Broad discovery.
   - Turn 2 (Symbol): if query has identifier-like tokens (camelCase, snake_case), run symbol search.
   - Turn 3 (Graph): get top file candidates from turns 1-2, build graph, get impact edges, materialize as Evidence via StoreHit.
   - Turn 4 (Fusion): RRF combine all channel evidence, dedup/narrow, apply token budget cap, compute confidence, generate missing_questions.
3. **Token budget**: `--budget N` means approximate max tokens (chars/4). Evidence trimmed from bottom if cumulative tokens exceed budget. `--max-evidence` still supported as count cap.
4. **ActionRecord**: per-channel, per-turn replayable actions with turn, channel, query, result_count, skipped, latency_ms, error. Written to `.openlocus/traces/fast-context-<trace_id>.json`.
5. **Unknown channel gate**: channels outside `regex,text,bm25,symbol,graph` are rejected with success=false/error.
6. **Final validation**: before output, evidence is filtered through `is_citation_valid` using safe path validation, current file hash comparison, line-range bounds, excerpt matching, and `VerifiedCurrent` freshness. Invalid citations are dropped and counted in `diagnostics.invalid_citations_dropped`.
7. **EvidencePack-compatible output**: `pack` field in result is a full EvidencePack with trace_id, budget_used. `evidence` field preserved for direct access.
8. **Disabled channels tracked**: if a channel fails or is not applicable, it's recorded in disabled_channels.

### Oracle review fixes

- Output now includes `pack` (EvidencePack-compatible) and `trace_id`.
- ActionRecord per turn/channel for replay. Trace file written to `.openlocus/traces/fast-context-<trace_id>.json`.
- `--budget` is now token budget (chars/4), not evidence count. `--max-evidence` is count cap. `tokens_estimated` is meaningful >0 when evidence exists.
- Unknown channels rejected with success=false/error JSON.
- Final validation drops invalid citations, counted in `diagnostics.invalid_citations_dropped`.
- Graph turn benefits are fixture-observed only, not a general quality claim.

### R6 Level0 results (after oracle review)

| Check | Result |
|---|---|
| Fast-context succeeds | ✅ |
| EvidencePack-compatible output | ✅ pack with trace_id |
| trace_id non-empty and matching | ✅ |
| Actions replayable | ✅ 4 actions with channel/query |
| Unknown channel blocked | ✅ error with valid channels list |
| Token budget respected | ✅ budget=50 → 3 evidence, 38 tokens |
| tokens_estimated meaningful | ✅ >0 when evidence exists |
| Citation validation (all evidence) | ✅ 100% valid |
| remote_calls = 0 | ✅ |
| Turns ≤ 4 | ✅ exactly 4 |
| Diagnostics present | ✅ invalid_citations_dropped=0 |
| No raw derived/graph edges in output | ✅ |

### Key findings

1. The 4-turn deterministic loop is a simple orchestration scaffold. It runs each channel in sequence and fuses results at the end.
2. Symbol search (Turn 2) is skipped when the query lacks identifier-like tokens, avoiding wasted computation and noise.
3. Token budget (chars/4) is a reasonable approximation. Budget=50 tokens trimmed from 20 to 3 evidence in testing.
4. All evidence is citation-valid by construction: regex/bm25/symbol search produces VerifiedCurrent evidence; graph evidence goes through StoreHit materialization. Final validation catches any that slip through.
5. The loop is deterministic: same query + same repo always produces same results.
6. Confidence is derived from the top evidence's RRF score. Low confidence (<0.1) triggers a missing_question.
7. ActionRecord enables replay/debugging of each step in the loop.

### Caveats

- This is a Level0 orchestration scaffold only, not a learned agent. No adaptive re-querying, no feedback loops, no LLM planning.
- Turn ordering is fixed (lexical → symbol → graph → fusion). A smarter planner could reorder or skip turns.
- Token estimation is chars/4, not a real tokenizer. Actual token counts may differ by 20-50%.
- Graph is rebuilt every fast-context invocation (not persisted).
- The "missing_questions" are rule-generated, not LLM-generated.
- No channel-specific error recovery beyond marking disabled_channels.
- Graph turn adds contextual evidence in fixtures; no general quality claim about graph benefit.

---

## 2026-06-11 — R7 Persistent Local Tantivy BM25 Index + Warm SLO Benchmark

### Objective

Add persistent Tantivy BM25 index with manifest tracking, CLI commands, warm SLO benchmark, and eval safety smoke. Do not change EvidenceCore contract. Do not connect TDB/LLM/dense/daemon. Persistent index requires explicit flag/command; temp BM25 path remains default.

### Hypothesis

A persistent Tantivy BM25 index with per-file content_sha tracking in a manifest will enable warm-query SLO measurement and will correctly skip stale/deleted hits without producing invalid evidence. The manifest enables fast staleness detection without re-reading all indexed content.

### Implementation notes

- **openlocus-index crate** (`crates/openlocus-index`): New workspace crate with manifest module and persistent index module.
- **Manifest** (`manifest.rs`): Schema version `r7-bm25-v1`, stored at `.openlocus/index/manifest.json`. Contains file_count, chunk_count, policy_hash (blake3 of canonical TOML serialization), and per-file entries (path, content_sha, size_bytes, language, status=indexed|skipped, skipped_reason). Manifest load/save/exists.
- **Persistent index** (`persistent.rs`): Tantivy index at `.openlocus/index/tantivy/`.
  - `build_index(repo_root, records, policy)`: Full rebuild, writes Tantivy index + manifest. Removes existing index before rebuild. Uses same chunking logic as temp BM25 (max 30 lines per chunk, same schema fields). **Filters unsafe FileRecord paths via validate_path before indexing** (path_unsafe records are skipped with reason).
  - `status_index(repo_root, policy)`: Returns exists, schema_version, file_count, chunk_count, policy_hash_matches, requires_rebuild, stale_files_fast (quick sha comparison of all indexed files).
  - `validate_index(repo_root, policy)`: Full validation of manifest entries against filesystem. Returns valid, stale_files, deleted_files, policy_hash_matches, path_unsafe_files. **Policy hash mismatch → valid=false.**
  - `purge_index(repo_root)`: Safe deletion of R7 artifacts only (manifest + tantivy dir). Canonicalizes paths and refuses to delete if index_dir escapes repo root.
  - `search_persistent_bm25(repo_root, query, max_results, policy)`: **Manifest/policy gate**: requires `.openlocus/index/manifest.json`, checks manifest policy_hash matches current Policy, and checks schema version; refuses search (bail) if missing/mismatched. **validate_path** on every Tantivy hit path before reading file. **Empty index_content_sha** → skip (cannot bypass stale check). **Strict chunk range validation**: 1 ≤ start ≤ end ≤ total_lines; invalid range → skip, no clamping. Opens existing Tantivy index, searches, then re-reads current file for every hit. Computes content_sha from current bytes, compares to index-time sha (stale → skip). Performs line-level query token scoring. Returns Evidence + SearchStats (query_ms, materialize_ms, stale_hits_skipped, invalid_hits_skipped).
  - `PersistentBm25Index::open(repo_root, policy)`: Requires manifest, opens the Tantivy Index/searcher once, validates policy hash + schema version. Returns a reusable handle with a `search()` method that does not reopen the Index per query. Used by bench warm to open once and loop queries.
- **CLI**:
  - `openlocus index build --json`: Build persistent index from scanned files.
  - `openlocus index status --json`: Quick status check.
  - `openlocus index validate --json`: Full validation against filesystem.
  - `openlocus index purge --json`: Safe deletion of R7 artifacts.
  - `openlocus search bm25 <query> --index temp|persistent --json`: Default is temp (existing per-query behavior). `--index persistent` uses pre-built index. **Policy gate enforced**: if manifest policy hash ≠ current policy, search returns an error.
  - `openlocus bench warm --dataset fixtures/r2.jsonl --iterations 3 --json`: Opens persistent index once via PersistentBm25Index handle, loops queries using the same reader/searcher. Reports index_build_ms (if built), index_open_ms (open cost only), queries, iterations, warm_query_p50_ms, warm_query_p95_ms, warm_query_max_ms, invalid_citations (real citation validation: hash/range/excerpt/freshness), stale_hits_skipped, notes.
- **Eval**: `eval/persistent_index_smoke.py` with 32 safety checks covering build/status/validate/search/stale_mutation/deleted_file/policy_excluded/policy_change_detection/manifest_missing_refusal/bench_warm/purge.
- **Safety gates (oracle review)**:
  1. **Manifest + policy gate**: search_persistent_bm25 and PersistentBm25Index::open require the manifest, check manifest policy_hash against current Policy, and refuse search if missing/mismatched.
  2. **Path validation**: validate_path on every Tantivy hit path; build_index filters unsafe FileRecord paths.
  3. **Empty content_sha**: skipped (cannot verify stale check).
  4. **Strict range**: 1 ≤ start ≤ end ≤ total_lines; no clamping.
  5. **Warm benchmark honesty**: PersistentBm25Index opens the Index/searcher once and reuses the same handle for all queries; no per-query Index::open; index_open_ms measures open cost only; index_build_ms reported separately if build was needed; invalid_citations uses real citation validation (hash/range/excerpt/freshness).

### R7 Level0 results

| Check | Result |
|---|---|
| Build succeeds and writes manifest | ✅ |
| Build filters unsafe paths via validate_path | ✅ |
| Status returns exists=true, schema matches, no rebuild needed | ✅ |
| Validate returns valid=true on fresh index | ✅ |
| Search persistent returns VerifiedCurrent evidence | ✅ |
| Search stale_hits_skipped=0, invalid_hits_skipped=0 on fresh index | ✅ |
| Policy gate: search refuses with policy hash mismatch | ✅ |
| Policy gate: validate detects policy hash mismatch | ✅ |
| Empty content_sha → skip (cannot bypass stale check) | ✅ |
| Strict range validation: 1 ≤ start ≤ end ≤ total_lines, no clamping | ✅ |
| validate_path on every Tantivy hit path before reading file | ✅ |
| Stale mutation: modified file → no VerifiedCurrent evidence for stale hit | ✅ |
| Stale mutation: stale_hits_skipped > 0 or zero results | ✅ |
| Validate detects stale files after mutation | ✅ |
| Deleted file: search produces no evidence for deleted file | ✅ |
| Policy excluded files (.env, .pem) absent from persistent output | ✅ |
| Policy change after build: search refuses | ✅ |
| Policy change after build: validate detects mismatch | ✅ |
| Manifest missing: search refuses instead of trusting Tantivy dir alone | ✅ |
| Bench warm succeeds with p50/p95/max latency | ✅ |
| Bench warm invalid_citations=0 (real citation validation) | ✅ |
| Purge removes manifest and tantivy dir | ✅ |
| Temp BM25 still works as default | ✅ |

### Warm SLO benchmark results (on current codebase)

```json
{
  "index_build_ms": null,
  "index_open_ms": 1,
  "queries": 28,
  "iterations": 3,
  "warm_query_p50_ms": 1,
  "warm_query_p95_ms": 2,
  "warm_query_max_ms": 2,
  "invalid_citations": 0,
  "stale_hits_skipped": 0
}
```

Note: These are implementation notes and initial SLO measurements on a small self-referential fixture. They are not a general performance claim. The `index_open_ms` measures the cost of opening an already-built Tantivy index and validating the manifest policy/schema gates — this is the actual warm-start cost. The `index_build_ms` is reported separately if the index needed to be built; it is null here because the index already existed. The warm_query_p50_ms reflects search-only cost after the index handle is opened once. The `invalid_citations` count uses real citation validation (hash/range/excerpt/freshness checks), not just range checks.

### Key findings

1. **Manifest-based staleness detection works**: After building an index, modifying a file, and running `search persistent`, the stale hit is correctly skipped (stale_hits_skipped > 0). No stale VerifiedCurrent evidence is emitted.
2. **Deleted file safety**: After deleting a file, searching the persistent index produces no evidence for the deleted file. The read failure is counted as invalid_hits_skipped.
3. **Policy exclusion works**: Files matching policy exclude patterns (.env, *.pem) are not scanned and not indexed, so they never appear in persistent search output.
4. **Validate detects staleness**: After modifying a file, `index validate` correctly reports the file as stale and marks the index as invalid.
5. **Warm query latency is fast on the current fixture**: On the current small self-referential workspace snapshot, warm queries take 1-2ms per query after index is opened (1ms open cost). The PersistentBm25Index handle opens once and reuses the same Index/searcher for all queries.
6. **Safety is preserved**: Every persistent search hit is re-verified against the current filesystem. The Tantivy stored body is never used as the final excerpt; the excerpt is always built from the current file content.
7. **Manifest and policy gates work**: Changing the policy after building the index causes search to refuse (error) and validate to report policy_hash_matches=false. Deleting the manifest also causes persistent search to refuse instead of trusting the Tantivy directory alone. This prevents querying unverifiable or stale-policy indexes.
8. **Strict validation prevents bypass**: Empty content_sha hits are skipped (cannot verify stale check). Chunk ranges are strictly validated (1 ≤ start ≤ end ≤ total_lines) with no clamping — invalid ranges are skipped.

### Caveats carried forward

- This is a Level0 persistent index implementation. Incremental update added in R10; the index still becomes stale when files change until `index update --dirty` is run.
- The manifest stores per-file content_sha at build time; it does not track per-chunk sha. If a file changes, all chunks from that file are considered stale (conservative).
- Warm SLO numbers are from a small self-referential codebase snapshot. Performance on larger repos may differ significantly.
- Persistent index does not integrate with RRF or fast-context pipelines yet; it is accessible only via `search bm25 --index persistent`.
- No daemon/watch mode; index becomes stale when files change and must be manually rebuilt.
- The index is stored under `.openlocus/index/` which may grow large for big repos. No size limit or rotation is implemented.
- Tantivy index is not encrypted; content is stored in the Tantivy segment files under `.openlocus/index/tantivy/`.
- R7 Level0 passed only after oracle review gates (policy hash, validate_path, empty sha, strict range, honest warm benchmark).

## 2026-06-11 — R8 AST-bounded chunking + AST symbol extraction (experimental)

### Objective

Add Tree-sitter-based AST chunking and symbol extraction as an experimental, opt-in alternative to line-window chunking. AST mode changes candidate chunk/symbol boundaries; final Evidence still requires current-filesystem path/range/hash/excerpt/freshness verification. Line-window chunking remains the default.

### Current hypothesis

AST-bounded chunks should improve retrieval precision by aligning chunk boundaries with logical code structures (functions, classes, structs, etc.) rather than arbitrary line windows. However, the quality lift is not yet proven by eval; this is an experimental scaffold.

### Stage gates

- R8 passes when AST build/search/validate/status work correctly, AST symbol search returns tree_sitter-channel Evidence, stale mutation is detected, fallback (unsupported language, parse error) is correct, and R7 persistent smoke still passes.
- AST mode is opt-in (`--chunk-strategy ast`); line remains default.
- No quality claim unless eval computes it.

### Implementation notes

- New crate `openlocus-ast` with Tree-sitter 0.25.x + language grammars (Rust, Python, JavaScript, TypeScript).
- `extract_ast_chunks(path, language, source, max_lines)`: Parses source with Tree-sitter for supported languages, extracts definition nodes (fn/struct/enum/trait/impl/mod/type/macro for Rust; function_definition/class_definition/decorated_definition for Python; function/class/method/lexical/variable/export for JS/TS plus interface/type/enum for TS). Oversized nodes split into line windows. Gaps covered by fallback line windows. No overlapping chunks. Strict 1-based line ranges. Unsupported language or parse error → fallback line windows.
- `extract_ast_symbols(path, language, source)`: Extracts narrow header/signature spans (max 10 lines, usually signature/header only rather than full bodies) for definitions. Uses Tree-sitter node field "name" for symbol extraction, with special handling for decorated Python definitions. Unsupported/parse error → empty symbols + fallback status; callers use regex fallback.
- Manifest schema version changed to `r8-bm25-v2`. R7 manifests (`r7-bm25-v1`) still loadable with default chunk_strategy=line_window_v1. Unrecognized schema versions refuse with rebuild instruction.
- `ChunkStrategy` enum: `LineWindowV1` (default), `AstV1` (experimental). Stored in manifest.
- `AstManifestStats` in manifest: supported_files, fallback_files, parser_error_files, ast_chunks, fallback_chunks.
- CLI: `openlocus index build --chunk-strategy line|ast` (default line). `openlocus search symbol <name> --mode regex|ast|auto` (default auto: AST first for supported files, regex fallback).
- Search/validate/status refuse if manifest chunk_strategy is unrecognized. R7 manifests without chunk_strategy are loaded as line_window_v1 for compatibility; R8-written manifests always include chunk_strategy. No silent search of unverifiable strategy.
- AST symbol Evidence uses Channel::TreeSitter, narrow span, current-file hash/excerpt/freshness validation. Regex symbol Evidence uses Channel::Regex (unchanged).
- `eval/ast_chunking_smoke.py`: 40 safety checks covering AST build/status/validate/search, parser-error visibility, stale mutation, narrow AST symbol header, symbol search modes, citation validation, schema mismatch, policy exclusion, default line build compatibility.

### R8 AST chunking safety checks

| Check | Result |
|---|---|
| Line build succeeds (default strategy) | ✅ |
| Line build has chunk_strategy=line | ✅ |
| Line build has no ast_stats | ✅ |
| AST build succeeds | ✅ |
| AST build has chunk_strategy=ast | ✅ |
| AST build has ast_stats | ✅ |
| AST stats: supported_files > 0 | ✅ |
| AST stats: ast_chunks > 0 | ✅ |
| AST stats: parser_error_files visible | ✅ |
| AST status: chunk_strategy=ast | ✅ |
| AST status: has ast_stats | ✅ |
| AST status: no rebuild needed | ✅ |
| AST validate: valid | ✅ |
| AST validate: chunk_strategy=ast | ✅ |
| AST search persistent: returns evidence | ✅ |
| AST search: all freshness verified_current | ✅ |
| Stale mutation: no verified_current evidence for stale file | ✅ |
| Stale mutation: stale_hits_skipped > 0 | ✅ |
| Validate detects stale after mutation | ✅ |
| AST symbol search: returns results | ✅ |
| AST symbol: uses tree_sitter channel | ✅ |
| AST symbol: header/signature span, not full body | ✅ |
| Regex symbol search: returns results | ✅ |
| Auto symbol search: returns results | ✅ |
| Policy excluded files absent | ✅ |
| Citation validation: valid | ✅ |
| Citation validation: invalid_count=0 | ✅ |
| Bad schema version: search refuses | ✅ |
| Line build after AST: succeeds | ✅ |
| Line build after AST: strategy=line | ✅ |

### Key findings

1. **AST chunking is functional as an experimental scaffold**: Tree-sitter parsing works for Rust, Python, JavaScript, and TypeScript. Chunk boundaries align with logical code structures.
2. **Fallback is correct**: Unsupported languages fall back to line-window chunking. Parse errors also fall back. No data loss.
3. **Oversized node splitting works**: Functions exceeding max_lines are split into line windows with kind=fallback_line_window.
4. **Gap filling ensures complete coverage**: No gaps or overlaps between chunks.
5. **AST symbol extraction produces narrow, citation-valid Evidence**: Symbols use Channel::TreeSitter, narrow header/signature spans (max 10 lines, usually signature/header only rather than full bodies), and are verified against the current filesystem.
6. **R7 persistent smoke still passes**: Default line build continues to work. Schema version is backward-compatible (R7 manifests loadable).
7. **Quality lift is NOT proven**: This is an experimental scaffold. No comparative eval has been run to measure retrieval quality improvement from AST chunking vs line-window chunking.

### Caveats

- AST mode is experimental and opt-in. Line-window chunking remains the default and recommended strategy.
- Tree-sitter parsers may have edge cases or version-specific behavior. The quality of chunking depends on the grammar quality.
- AST symbol extraction does not handle all possible symbol patterns (e.g., re-exports, aliased imports, nested definitions). Regex fallback covers many of these.
- The `auto` mode for symbol search tries AST first for supported files and falls back to regex if no results. This may miss cases where regex finds results that AST does not.
- No incremental update for AST index in this R8 iteration; R10 adds incremental update for both line and ast strategies.
- Manifest schema version `r8-bm25-v2` is not compatible with `r7-bm25-v1` for search purposes (older schemas load but may require rebuild for search).
- AST chunking adds Tree-sitter as a dependency, increasing binary size and compile time.

## 2026-06-11 — R9 AST vs Line Persistent BM25 Quality Bakeoff

### Objective

Evaluate `index build --chunk-strategy line` vs `--chunk-strategy ast` persistent BM25 retrieval quality on the R2 self-referential fixture. Produce a reproducible script and research log. Do not change EvidenceCore, default behaviour, or implement incremental indexing.

### Hypothesis

AST-bounded chunks should improve span-level precision/recall (SpanF0.5@10) by aligning chunk boundaries with logical code structures, but the effect may be small or negative on this small self-referential fixture. File-level recall may not improve because AST chunking changes span boundaries, not file-level ranking.

### R9 bakeoff results (persistent BM25 on fixtures/r2.jsonl, 28 tasks)

| Metric | line | ast | delta |
|---|---:|---:|---:|
| FileRecall@1 | 0.393 | 0.536 | +0.143 |
| FileRecall@5 | 0.821 | 0.750 | −0.071 |
| FileRecall@10 | 0.821 | 0.821 | 0.000 |
| MRR | 0.548 | 0.624 | +0.076 |
| SpanF0.5@10 | 0.039 | 0.064 | +0.025 |
| token_waste_ratio@10 | 0.961 | 0.940 | −0.022 |
| wrong_span_rate@10 | 0.776 | 0.689 | −0.087 |
| zero_overlap_evidence_rate@10 | 0.950 | 0.913 | −0.038 |
| citation_validity | 1.0 | 1.0 | 0.0 |
| structural_validity | 1.0 | 1.0 | 0.0 |
| success_rate | 1.0 | 1.0 | 0.0 |
| avg_latency_ms | ~10.4 | ~9.1 | noisy/comparable |
| latency_ratio | — | ~1.0 | noisy |

### Quality gate

| Gate condition | Result |
|---|---|
| Both citation_validity == 1.0 | ✅ |
| Both success_rate == 1.0 | ✅ |
| AST FileRecall@5 ≥ line | ❌ (0.750 < 0.821) |
| AST SpanF0.5@10 ≥ line | ✅ (0.064 > 0.039) |
| AST token_waste not worse | ✅ (0.940 < 0.961) |
| Latency ratio ≤ 1.25 | ✅ (comparable; latest run ~0.88) |
| **Overall quality_gate_passed** | **false** (FileRecall@5 regression) |

### Safety checks

| Safety check | Result |
|---|---|
| Line build succeeds | ✅ |
| AST build succeeds | ✅ |
| Line validate valid | ✅ |
| AST validate valid | ✅ |
| Line status strategy=line | ✅ |
| AST status strategy=ast | ✅ |
| Evidence nonempty (both) | ✅ |
| Citation validator invalid_count=0 (both) | ✅ |
| Search stats counters present/nonnegative (both) | ✅ |
| Build strategy explicit (both) | ✅ |
| **All safety checks passed** | **true** |

### Key findings

1. **AST improves SpanF0.5@10 by +0.025** (0.039 → 0.064, ~63% relative in the latest run). AST-bounded chunks align better with logical code structures, producing evidence spans that overlap gold lines more often. This is the strongest positive signal for AST chunking.
2. **AST improves FileRecall@1 by +0.143** (0.393 → 0.536, +36% relative). The finer-grained AST chunks appear to help top-1 file retrieval, likely because more specific chunks match queries more precisely at the top rank.
3. **AST regresses FileRecall@5 by −0.071** (0.821 → 0.750 in the latest run). This is the quality gate failure. AST chunking produces more, smaller chunks (e.g., 15 chunks vs 5 for a 5-file repo), which can dilute BM25 scores for some files, causing them to rank outside top-5. This is a real trade-off: finer chunks help precision at k=1 but may hurt recall at higher k because the same file's chunks compete with each other.
4. **AST reduces token_waste_ratio@10 by −0.022** (0.961 → 0.940 in the latest run). Narrower, more targeted evidence spans waste fewer tokens on irrelevant lines. The improvement is modest on this fixture.
5. **AST reduces wrong_span_rate@10 by −0.087** (0.776 → 0.689 in the latest run). AST-bounded evidence on gold files is more likely to overlap gold spans, reducing the rate of evidence that hits the right file but the wrong location.
6. **Latency is comparable/noisy** (latest ratio ~0.88). Both strategies have similar per-query latency in this tiny CLI benchmark; this is not a general performance claim.
7. **Citation validity and structural validity are perfect for both strategies** (1.0). AST chunking does not compromise evidence safety.
8. **Quality gate is false** due to FileRecall@5 regression. This is a negative result on the gate but not on safety. The gate correctly captures the trade-off.

### Interpretation

**AST remains experimental/opt-in. Line remains default.**

The R9 bakeoff shows a mixed picture: AST improves span precision (SpanF0.5, token waste, wrong_span_rate) and top-1 recall (FileRecall@1, MRR), but regresses FileRecall@5. On this small self-referential fixture, the trade-off is real but the magnitude is small. The regression at FileRecall@5 likely reflects chunk-score dilution: more granular AST chunks can scatter a file's BM25 signal across many smaller chunks, reducing the chance that any single chunk ranks the file into the top-5.

Whether this trade-off is acceptable depends on the use case: for top-1 precision and span quality, AST is preferable; for broad file discovery at k=5+, line chunking is more conservative. The fixture is too small and self-referential to generalise these findings. A larger, diverse codebase eval would be needed to determine whether AST chunking provides a consistent quality improvement.

### Caveats

- Fixture is R2 small self-referential (28 tasks, ~20 source files). Results are not generalisable.
- FileRecall@5 regression may be an artifact of chunk granularity on small repos; larger repos may not exhibit the same trade-off.
- No incremental indexing in this R9 bakeoff; R10 adds incremental update.
- The bakeoff only tests persistent BM25; temp BM25, RRF, and fast-context are not compared here.
- token_waste_ratio remains high (~0.94) for both strategies. The bottleneck is query-evidence alignment, not chunking strategy.
- Python citation validation uses path_range_only mode (no blake3 Python package installed); Rust CLI citation validator confirmed invalid_count=0 for both strategies.
- AST mode is experimental and opt-in. Line-window chunking remains the default and recommended strategy.

## 2026-06-11 — R10 Incremental Index + Dirty Summary + Synthetic SLO

### Objective

Add persistent index dirty summary, file-level incremental update, context-lite dirty integration, and synthetic SLO benchmark. Do not implement TDB/daemon/watcher. Do not add LLM/dense. EvidenceCore unchanged.

### Current hypothesis

A manifest-vs-filesystem dirty summary enables incremental index updates that avoid full rebuilds for small changes. File-level update with Tantivy delete-by-term + re-add should correctly maintain the index without producing duplicate or stale evidence. Policy/schema/strategy mismatches must refuse update, requiring rebuild instead. Note: the Tantivy commit and manifest file write are not a single transaction; failure between them may leave a safe but inconsistent state requiring rebuild or re-update.

### Implementation notes

- **Dirty summary** (`dirty_index`): Computes manifest-vs-current scan returning `DirtyResult` with:
  - `clean`: bool (true if no changes and policy/schema match)
  - `requires_update`: bool (true if added/modified/deleted files, no rebuild needed)
  - `requires_rebuild`: bool (true if policy/schema/strategy mismatch or no index)
  - `added_files`, `modified_files`, `deleted_files`: arrays of path strings
  - `added_count`, `modified_count`, `deleted_count`: u64 counts
  - `policy_hash_matches`, `schema_matches`: bool flags
  - `chunk_strategy`: from manifest
  - Discovers policy-included added files not in manifest; policy-excluded added files do not dirty.
  - Status must not say clean if validate would fail.

- **File-level update** (`update_index`): CLI: `openlocus index update --dirty --json` and/or `openlocus index update --path <path> --json`.
  - If index/manifest missing → error (requires rebuild).
  - If policy hash/schema/strategy mismatch → refuse update, require rebuild.
  - For `--dirty`: compute added/modified/deleted from dirty summary, then:
    - Delete old Tantivy docs by path using `Term::from_field_text(path_field, path)`.
    - For added/modified policy-included files: validate_path, read current file, compute sha, chunk according to manifest chunk_strategy, add docs.
    - For deleted files: delete docs by path, remove manifest entry.
    - Commit once after batch.
    - Write manifest file using tmp+rename (not a single transaction with Tantivy commit; failure between may require rebuild/update).
  - Added detection uses ALL manifest paths (indexed + skipped), not just indexed. Skipped entries with unchanged sha remain clean; skipped→nonempty is reported as modified (not added).
  - For `--path`: update only that policy-included path. If file exists add/update; if missing delete from index. Validate path safety.
  - Returns `UpdateResult` with `added_count`, `modified_count`, `deleted_count`, `commit_ms`, `manifest_written`, `post_status_clean`.
  - Tantivy deletes are tombstones until merge; documented, not a bug.
  - Prevents duplicate old+new docs by delete_term(path) before add.
  - Chunk according to manifest chunk_strategy; does not mix strategies.

- **Context-lite integration**: R10 populates dirty-summary.json with actual dirty index status (clean, requires_update, requires_rebuild, added/modified/deleted counts and files) instead of the R1 empty placeholder. If index doesn't exist, reports requires_rebuild=true.

- **CLI commands**:
  - `openlocus index dirty --json`: Show dirty summary.
  - `openlocus index update --dirty --json`: Update all dirty files.
  - `openlocus index update --path <path> --json`: Update single file.

- **Eval scripts**:
  - `eval/incremental_index_smoke.py`: 48 safety checks covering build/clean, modify/update/search/clean, add/update/search/clean, delete/update/search/clean, rename simulation, policy-excluded no dirty, policy mismatch refuses update, missing manifest refuses update, skipped empty file clean/promotion, schema/strategy mismatch refuses update, citations invalid_count=0.
  - `eval/synthetic_slo_bench.py`: Deterministic 1000-file synthetic repo (mix .rs/.py/.ts/.md/.txt), measures build_ms, dirty status latency, persistent_cli_search p95, bench_warm open-once query p95, and one-file update latency (true modification each iteration). Validates no invalid citations. Level0 synthetic only; no broad performance claims.

### R10 incremental index smoke results (48/48 checks passed)

| Check | Result |
|---|---|
| Build succeeds, file_count > 0 | ✅ |
| Dirty clean after build | ✅ |
| Dirty: no requires_update/rebuild after build | ✅ |
| Dirty: policy_hash_matches + schema_matches | ✅ |
| Modify file → dirty detects modified | ✅ |
| Search before update: no stale VerifiedCurrent | ✅ |
| Update dirty: modifies file, manifest written | ✅ |
| Search after update: finds new content | ✅ |
| Dirty clean after update | ✅ |
| Add new file → dirty detects added | ✅ |
| Update dirty: adds file | ✅ |
| Search finds added file | ✅ |
| Dirty clean after add update | ✅ |
| Delete file → dirty detects deleted | ✅ |
| Update dirty: deletes file | ✅ |
| Search: no evidence for deleted file | ✅ |
| Dirty clean after delete update | ✅ |
| Rename: old gone, new found | ✅ |
| Policy-excluded added file does not dirty | ✅ |
| Policy hash mismatch refuses update | ✅ |
| Missing manifest refuses update | ✅ |
| Citations: invalid_count=0 | ✅ |
| Purge after smoke succeeds | ✅ |

### R10 synthetic SLO benchmark results (1000 files, seed=42)

```json
{
  "build_ms": 147,
  "build_file_count": 1000,
  "build_chunk_count": 1072,
  "dirty_status_latency_ms": {"p50": 44, "p95": 48, "max": 48},
  "dirty_clean": true,
  "persistent_cli_search_latency_ms": {"p50": 13, "p95": 14, "max": 15},
  "bench_warm": {"index_open_ms": 5, "queries": 10, "iterations": 3, "warm_query_p50_ms": 0, "warm_query_p95_ms": 0, "warm_query_max_ms": 1, "invalid_citations": 0},
  "total_invalid_citations": 0,
  "one_file_update_latency_ms": {"p50": 115, "p95": 117, "max": 126},
  "update_success": true,
  "update_modified_count_ok": true,
  "all_safety_checks_passed": true
}
```

Note: These are Level0 synthetic-only measurements on a deterministic 1000-file fixture. They are not a general performance claim. Actual performance on real-world repos will vary with file sizes, content diversity, and hardware. `persistent_cli_search_latency_ms` measures CLI search (each call opens index fresh); `bench_warm` reports the Rust CLI's internal open-once query latency over a synthetic dataset. The dirty_status_latency includes a full file rescan which is bounded by the number of indexed files; for very large repos this would need optimization (e.g., filesystem watchers, mtimes). One-file update latency reflects a true modification (different content each iteration), not a no-op.

### Key findings

1. **Incremental update works correctly**: Modified, added, and deleted files are properly detected, updated in the Tantivy index, and the manifest is written using tmp+rename. Post-update status shows clean.
2. **Dirty summary is accurate**: It correctly identifies added/modified/deleted files, distinguishes requires_update from requires_rebuild, and does not report policy-excluded files as dirty.
3. **Safety gates are enforced**: Policy hash mismatch and missing manifest refuse update with clear error messages. Schema and strategy mismatches also refuse update.
4. **Search-after-update correctness**: After updating modified files, persistent search returns only new content (verified_current freshness). After deleting files, no evidence appears. After adding files, new files are discoverable.
5. **Tantivy delete-by-term works**: Using `Term::from_field_text(path_field, path)` correctly removes all chunks for a given path before re-adding, preventing duplicate old+new docs.
6. **Manifest file write uses tmp+rename**: This prevents partial manifest writes. However, the Tantivy commit and manifest write are not a single transaction; a crash between them may leave a safe but inconsistent state (Tantivy committed but manifest stale), requiring a rebuild or re-update.
7. **One-file update latency is reasonable for synthetic small edits**: ~115ms p50 for a true single-file update in a 1000-file repo (dev profile, unoptimized). This includes scan + dirty computation + Tantivy write + manifest write.
8. **Dirty status latency scales with file count**: ~44ms p50 for 1000 files in dev build. For very large repos, filesystem watchers or mtime-based optimization would be needed.
9. **Context-lite dirty summary is now written to file**: R10 replaces the R1 empty placeholder by writing actual dirty counts and status information to `.openlocus/context/dirty-summary.json`. The `ContextLitePack.dirty_summary` struct field remains `None` (the file is the authoritative source, not the struct field).

### Caveats

- This is a Level0 incremental index implementation. Not a daemon/watcher; index becomes stale when files change and must be manually updated via `index update --dirty` or `--path`.
- Tantivy deletes are tombstones until merge. For repos with frequent updates, periodic full rebuild or explicit merge may be needed to reclaim space.
- Chunk count in manifest after update is approximate (old_count + new_chunks - estimated_deleted_chunks). A full rebuild produces exact counts.
- Dirty summary re-scans all indexed files to compare content_sha. For very large repos, this is O(n) in indexed file count. A filesystem watcher or mtime cache would be needed for sub-second dirty detection.
- The update does not handle branch switches or concurrent modifications; a rebuild is recommended after significant changes.
- AST strategy update uses the same `compute_chunks` helper as build; it respects the manifest's chunk_strategy and does not mix strategies.
- The Tantivy commit and manifest file write are not a single transaction. If the process crashes between them, the index may be in a safe but inconsistent state (Tantivy committed, manifest stale). A rebuild or re-update resolves this.
- Skipped entries (empty files, read errors, path_unsafe) are tracked in the manifest; they do not appear as "added" on subsequent dirty scans if sha is unchanged. A skipped→nonempty transition is reported as "modified" and the update promotes it to "indexed".
- R7/R8/R9 smoke tests still pass after R10 changes.
- TDB moves to a later research stage (was R10 in original roadmap, now deferred to R11).

---

## 2026-06-11 — R11 TriviumDB/TDB Feature-Gated Level0 Adapter Probe

### Objective

Implement a feature-gated TriviumDB (TDB) adapter behind a `tdb` Cargo feature, proving the StoreBackend / ChunkStore trait hierarchy can be wired to a real TDB instance. This is a Level0 adapter probe for metadata/chunk persistence only — not a retrieval quality claim. If the TDB crate was not compilable or its API was unsuitable, the fallback was a negative feasibility report.

### Current hypothesis

TriviumDB 0.7.0 (from crates.io) can be used as an optional dependency behind a Cargo feature flag to store chunk metadata as JSON payloads in TDB nodes with dim=1 dummy vectors. The adapter should pass the same build discipline as ConservativeChunkStore (validate_path, TOCTOU-safe sha, skip stale/traversal/empty) and honestly report capabilities (metadata+chunks only, no lexical/vector/graph claims). TDB hits must go through StoreHit → materialize_evidence(); they cannot directly become Evidence.

### Implementation notes

- **Cargo feature**: Added `[features] default = []` and `tdb = ["dep:triviumdb"]` to `crates/openlocus-store/Cargo.toml`. Added `triviumdb = { version = "=0.7.0", optional = true }`. Workspace/default build does NOT enable the feature; `cargo test --workspace` does not compile or require TriviumDB.
- **TdbChunkStore** (`crates/openlocus-store/src/tdb_adapter.rs`): Behind `#[cfg(feature = "tdb")]`.
  - Opens a `Database<f32>` with `dim=1` and stores chunk metadata as JSON payloads with schema `openlocus_schema=tdb_chunk_v1`.
  - The vector `[0.0]` is a smoke probe only — this is NOT vector quality. Documentation explicitly states this.
  - Payload schema: `openlocus_schema`, `path`, `start_line`, `end_line`, `content_sha`, `language`, `kind`.
  - Build discipline copies ConservativeChunkStore: `validate_path`, read current bytes once, sha from same bytes, skip stale/traversal/empty invalid chunks; line chunks OK.
  - Uses `db.insert(&[0.0f32], payload)` with auto-assigned NodeIds. In-memory `ChunkRecord` list maintained for conformance.
  - Capabilities: metadata=true, chunks=true, lexical=false, vector=false, graph=false.
  - Marker file (`.openlocus_marker`) written alongside the `.tdb` file to identify adapter-owned data.
  - Purge only deletes the adapter-owned TDB artifact set (`.tdb` plus known sidecars) after verifying the marker. Refuses purge if marker is missing or mismatched.
  - Ingest only from `scan_repo` filtered records; never walks filesystem itself.
  - If adapter exposes hits, they must be converted to `StoreHit` and go through `materialize_evidence()`.
- **Module registration**: `#[cfg(feature = "tdb")] pub mod tdb_adapter;` in `lib.rs`.
- **Placeholder preserved**: `TdbPlaceholderStore` (always available) unchanged — it still reports `available=false` when the `tdb` feature is not enabled.

### R11 Level0 adapter probe results

| Check | Result |
|---|---|
| `cargo test --workspace` (default, no tdb) | ✅ 193 passed |
| `cargo test -p openlocus-store --features tdb` | ✅ 28 passed (18 existing + 10 new adapter) |
| `cargo fmt --all -- --check` | ✅ clean |
| `cargo clippy --workspace --all-targets -- -D warnings` | ✅ clean |
| `cargo clippy -p openlocus-store --features tdb -- -D warnings` | ✅ clean |
| TDB adapter health available when open | ✅ |
| TDB adapter build from records | ✅ chunks, files, valid ranges |
| TDB adapter capabilities conservative | ✅ metadata+chunks only, no lexical/vector/graph |
| TDB adapter skips stale records | ✅ test passes |
| TDB adapter skips empty files (no invalid chunks) | ✅ test passes |
| TDB adapter skips traversal records | ✅ test passes |
| TDB adapter purge marker-owned only | ✅ deletes .tdb + known sidecars + marker |
| TDB adapter purge refuses without marker | ✅ error with marker/refused |
| TDB adapter materialization conformance | ✅ StoreHit → materialize_evidence → VerifiedCurrent |
| TDB adapter materialization rejects stale | ✅ StaleHit |
| TDB adapter materialization rejects empty sha | ✅ error |
| TDB adapter materialization rejects invalid range | ✅ error |
| Default build unchanged | ✅ no TDB dependency in default |
| Placeholder unchanged | ✅ TdbPlaceholderStore preserved |
| EvidenceCore unchanged | ✅ |
| No default dependency on triviumdb | ✅ optional only |

### Key findings

1. **TriviumDB 0.7.0 compiles and works**: The crate from crates.io compiles with the workspace's Rust edition (2024) and toolchain. `Database::open(path, dim=1)` creates/opens a database; `db.insert(&[0.0f32], payload)` inserts nodes with JSON payloads; `db.flush()` persists to disk.
2. **Feature-gated adapter works correctly**: The `tdb` feature flag cleanly gates the adapter. Default builds do not compile or require TriviumDB. The adapter module is only included when the feature is enabled.
3. **Build discipline is preserved**: The TDB adapter follows the same ConservativeChunkStore discipline — validate_path, TOCTOU-safe sha computation, stale/traversal/empty skipping. This ensures consistent behavior across store backends.
4. **dim=1 is a smoke probe, not vector quality**: The adapter explicitly does not claim vector search capability. The `[0.0]` vector is used solely to satisfy TDB's API requirement. Capabilities honestly report vector=false.
5. **Marker-based purge is safe**: The adapter writes a marker file alongside the `.tdb` file. Purge verifies the marker before deletion and refuses to delete paths without a valid marker. This prevents accidental deletion of arbitrary files.
6. **Materialization conformance is enforced**: TDB chunk records are converted to StoreHit and must go through `materialize_evidence()`. Stale, empty-sha, and invalid-range hits are correctly rejected.
7. **TDB is NOT a default backend**: The adapter is feature-gated and opt-in. TDB does not replace Tantivy persistent BM25 or the conservative store. The placeholder store continues to report unavailability when the feature is not enabled.
8. **This is a Level0 adapter probe**: No retrieval quality claim is made. The adapter proves wiring and persistence; it does not provide meaningful lexical, vector, or graph search through TDB.

### Caveats

- This is a Level0 adapter probe only. No retrieval quality comparison against Tantivy BM25 or conservative store.
- The TDB adapter uses auto-assigned NodeIds (via `db.insert()`). The `insert_with_id` API exists but requires predetermined IDs; this is a possible future enhancement for deterministic chunk IDs.
- The TDB adapter does not implement `LexicalStore`, `VectorStore`, or `GraphStore`. It only provides `StoreBackend` + `ChunkStore`.
- TDB file locking prevents multiple processes from opening the same database simultaneously (by design in TriviumDB).
- Chunk insert and flush failures now fail the Level0 build instead of silently claiming persistence success.
- No CLI integration for TDB adapter in this R11 iteration. The adapter is only usable programmatically.
- TDB is not integrated with the RRF retrieval pipeline or fast-context orchestration.
- The `TdbPlaceholderStore` still exists and reports `available=false` regardless of whether the `tdb` feature is enabled. A future iteration could make the placeholder aware of the feature flag.
- Warm/persistent query benchmark not yet run against the TDB adapter (not meaningful until search is implemented).

---

## 2026-06-11 — R12 Real-Repo Incremental Robustness Benchmark

### Objective

Add a real-repo sample benchmark using a safe temporary copy of the current OpenLocus repository to test R10 incremental index's real-scenario robustness. Do not change Rust core, default CLI/search/retrieve, and do not introduce watcher/daemon/TDB changes.

### Current hypothesis

R10 proved incremental update works on a synthetic 1000-file repo. A real repo with mixed file types, larger files, and real code patterns should also pass all safety gates (no stale VerifiedCurrent evidence, correct dirty detection, valid citations). Incremental update should be faster than full rebuild for small edits on a real repo.

### Implementation notes

- **New eval script**: `eval/real_repo_incremental_bench.py` with `report_kind=real_repo_incremental_bench`.
- **Source repo**: defaults to current working directory; copies to temp repo excluding `target`, `.git`, `.openlocus`, `runs`, `node_modules`, `dist`, `__pycache__`, etc. Creates empty `.git/` and `.openlocus/policy.toml` in temp repo.
- **All workload file mutations only in temp repo**: original source files are never modified. `--out` writes report to caller workspace.
- **Per-run unique markers**: Each run generates a random 8-hex-char suffix (e.g. `a3f7b2c1`). All markers are concatenated with this suffix (e.g. `r12addalphaa3f7b2c1`). Before baseline build, `assert_markers_absent` scans the temp repo to confirm no marker self-contamination from copied docs/scripts.
- **All search**: `openlocus search bm25 <query> --index persistent --json`. Search returncode must be 0 for positive gates.
- **Collected marker-search evidence validation**: `openlocus citations validate <file> --json` with `invalid_count=0` and validator returncode==0.
- **Positive gates use path+marker conjunction**: `evidence_has_path_and_marker` requires BOTH the target relative path AND the marker in the cited excerpt. Disjunction (path OR marker) is not used for positive assertions.
- **Empty evidence is not a pass for positive gates**: Where a marker must be found, `len(evidence) > 0` is required.
- **`sys.exit(1)` on safety failure**: `all_safety_checks_passed` false exits with code 1. Latency/growth gate false does NOT cause exit failure.
- **Latency comparison uses twin repo copies**: For each iteration, two fresh copies of the source repo are made. Same mutation is applied to both; one gets `update --dirty`, the other gets `build`. This ensures fair comparison of the same final state.
- **Growth gate renamed to catastrophic guard**: `growth_catastrophic_guard_passed` (not "bounded proof"). Observed 20-cycle growth ratio reported separately. The catastrophic bound (max(3×rebuild, rebuild+64MiB)) is a backstop, not proof of long-term bounded growth.
- **Branch-like batch checks are specific**: At least one add target path+marker AND one rename-new target path+marker must be found. At least one deleted path and one rename-old path must have no VerifiedCurrent evidence.

### Script CLI

```bash
python3 eval/real_repo_incremental_bench.py \
  --openlocus target/debug/openlocus \
  --source /workspace/OpenLocus/OpenLocus \
  --out runs/real-repo-incremental-bench.json \
  --iterations 3 \
  --growth-cycles 20
```

Optional `--keep-temp` to preserve temp repo after benchmark.

### Workloads

A. **modify_one**: Append per-run marker to existing file; dirty detects modified; search old marker has no VerifiedCurrent for modified path; update; new marker found at path with marker in evidence (path AND marker); old marker gone; clean + valid + citations invalid_count=0.

B. **add_one**: Add `r12_bench/r12_add_target_{sfx}.rs` with per-run marker; dirty detects added; update; search finds marker at path with marker in evidence; clean + valid + citations invalid_count=0.

C. **delete_one**: Delete `r12_bench/r12_delete_target_{sfx}.rs`; dirty detects deleted; update; search marker no VerifiedCurrent for deleted path; clean + valid + citations invalid_count=0.

D. **rename_one**: Rename `r12_rename_old_{sfx}.rs` → `r12_rename_new_{sfx}.rs` + change marker; dirty detects added+deleted; update; old gone (no VerifiedCurrent for old path); new found at new path with marker (path AND marker); clean + valid + citations invalid_count=0.

E. **policy_exclude**: Add `.env.r12bench{sfx}` with marker; dirty stays clean; no evidence from excluded path (path-aware check).

F. **branch_like_batch**: Batch add 5 + delete 3 + rename 3; old delete/rename markers are first proven indexed; dirty covers categories; update; add target 0 found at path+marker; rename-new target 0 found at path+marker; deleted path 0 no VerifiedCurrent; rename-old path 0 no VerifiedCurrent; clean + valid + citations invalid_count=0.

G. **latency_compare**: Twin repo copies per iteration; same mutation applied; compare `update --dirty` vs `build` for modify_one and batch. Gate: p50 update < p50 rebuild. If false, report only; does not cause exit failure.

H. **growth_cycles**: N cycles of modify same file + update. Each cycle: dirty detects modified, update succeeds, dirty clean, validate valid. Catastrophic guard: `final_after_updates_size <= max(3 * post_full_rebuild_size, post_full_rebuild_size + 64MiB)`. Observed growth ratio reported. This is a catastrophic guard, not proof of long-term bounded growth.

### R12 results (after per-run marker + safety gate fixes)

| Check | Result |
|---|---|
| Baseline markers absent pre-build (no self-contamination) | ✅ |
| Baseline build succeeds, file/chunk count >0 | ✅ |
| Baseline dirty clean after build | ✅ |
| Baseline validate valid | ✅ |
| modify_one: dirty detects modified | ✅ |
| modify_one: update succeeds | ✅ |
| modify_one: new marker found at path+marker | ✅ |
| modify_one: old marker gone (no VerifiedCurrent for path) | ✅ |
| modify_one: clean + valid after update | ✅ |
| add_one: dirty detects added | ✅ |
| add_one: search finds marker at path+marker | ✅ |
| add_one: clean + valid after update | ✅ |
| delete_one: dirty detects deleted | ✅ |
| delete_one: no VerifiedCurrent for deleted path | ✅ |
| delete_one: clean + valid after update | ✅ |
| rename_one: dirty detects added + deleted | ✅ |
| rename_one: old gone, new found at path+marker | ✅ |
| rename_one: clean + valid after update | ✅ |
| policy_exclude: dirty stays clean | ✅ |
| policy_exclude: no evidence from excluded path | ✅ |
| branch_batch: add target 0 found at path+marker | ✅ |
| branch_batch: rename-new target 0 found at path+marker | ✅ |
| branch_batch: deleted/rename-old markers indexed before removal | ✅ |
| branch_batch: deleted path 0 no VerifiedCurrent | ✅ |
| branch_batch: rename-old path 0 no VerifiedCurrent | ✅ |
| branch_batch: clean + valid after update | ✅ |
| growth_cycles: all cycles dirty→update→clean→valid | ✅ |
| growth_cycles: catastrophic guard passed | ✅ |
| total_invalid_citations | 0 |
| stale_verified_current_violations | [] |

### Latency compare (twin repo copies, same mutation)

| Scenario | Update p50 (ms) | Rebuild p50 (ms) | Update faster? |
|---|---|---|---|
| modify_one | 96.2 | 165.8 | ✅ yes |
| branch_like_batch | 99.7 | 169.4 | ✅ yes |

Incremental update is ~42% faster than full rebuild for both single-file and batch modifications on this real-repo sample (75 files, 804 chunks, dev profile). Latency gate is report-only; false does not cause exit failure.

### Growth result

| Metric | Value |
|---|---|
| Size after 20 update cycles | ~905 KB |
| Size after full rebuild | ~823 KB |
| Observed growth ratio | 1.11 |
| Catastrophic guard (≤ max(3×rebuild, rebuild+64MiB)) | ✅ passed |

20 cycles observed growth ~1.11×; catastrophic guard passed. Does not prove long-term bounded growth.

### Safety checks

149/149 hard safety checks passed. Script exits with code 1 if any hard safety check fails; latency/growth gate failures are report-only.

### Key findings

1. **Real-repo incremental update passes this Level0 sample**: On a temp copy of the OpenLocus repository (mixed Rust, Python, TypeScript, Markdown files), incremental update correctly handles sampled modify, add, delete, rename, policy-excluded, and batch workloads. No stale VerifiedCurrent evidence is produced.
2. **Citation validity is maintained for collected marker-search evidence**: Evidence validated through `openlocus citations validate` has `invalid_count=0` and validator returncode==0.
3. **Per-run unique markers avoid self-contamination**: Fixed markers appeared in copied docs/scripts, causing false positives. Per-run suffixes (8-hex chars) and pre-build assert prevent this.
4. **Positive gates use path+marker conjunction**: Previous `evidence_has_path_or_marker` (disjunction) could pass from unrelated evidence. New `evidence_has_path_and_marker` requires both path and marker in the cited excerpt of the same evidence item.
5. **Empty evidence is not a pass for positive gates**: Previous code could pass add/rename checks with empty evidence returning `invalid_citations=0`. Now requires `len(evidence) > 0`.
6. **Latency comparison uses twin repo copies**: Previous code compared update on a dirty repo vs rebuild on a clean repo (unfair). Now both start from the same state with the same mutation applied.
7. **Growth gate is honestly named as catastrophic guard**: 20 cycles observed growth ~1.11×; catastrophic guard passed. This does not prove long-term bounded growth.
8. **This is one real-repo sample (OpenLocus temp copy)**: Not a general performance claim. Different repos, hardware, and workloads may produce different results.

### Caveats

- This is a Level0 real-repo sample benchmark using one repo (OpenLocus temp copy). Not a general performance or robustness claim.
- Per-run unique markers avoid self-contamination but are not representative of real search queries.
- The temp repo excludes `.git` history; real repos with large git histories may behave differently in scan time.
- Tantivy deletes are tombstones until merge; index size after many updates may be larger than a fresh rebuild. The catastrophic guard bounds extreme growth but does not prove bounded growth.
- The latency comparison uses CLI wall-clock time which includes process startup overhead. Internal Rust timing would be more precise.
- No concurrent access testing; single-process only.
- No crash/recovery testing between Tantivy commit and manifest write.
- Branch-like batch does not actually switch git branches; it simulates the file-level effects of a branch switch.
- Collected marker-search evidence is validated; this is not "all evidence in repo" — only evidence from workload-specific marker searches.

## 2026-06-11 — R13 Remote Embedding / LLM-Derived Indexing Bakeoff Safety Scaffold

### Objective

Add a safe scaffold for future dense/semantic embedding and LLM-derived indexing experiments, without connecting to any real remote service, reading API keys, downloading models, or adding reqwest/async-openai/fastembed/ANN DB dependencies.

### Design constraints

- No real remote calls, no API key reads, no model downloads.
- Default build is fully local; EvidenceCore is unchanged.
- Dense/mock/derived hints produce candidate StoreHits only; final Evidence must go through `openlocus_store::materialize_evidence(repo_root, hit, Channel::Dense)`.
- Audit never stores raw snippet text or vectors; vector store stores path/range/source_content_sha/language/vector but not raw text/code snippet.
- CLI/trace/audit never store raw query text; use query_sha + query_len instead.
- Quality claims limited to mock integration; no real semantic gain claimed.

### Implementation

1. **New crate `openlocus-provider`** with modules:
   - `model.rs`: `ProviderLocality`, `ProviderMetadata`, `EmbedInput`, `EmbeddingRecord`, `EmbeddingAuditEvent`, `ProviderDecision`.
   - `provider.rs`: `EmbeddingProvider` trait, `DisabledEmbeddingProvider`, `create_provider()`.
   - `mock.rs`: `MockEmbeddingProvider` — deterministic vector from blake3(provider_id/model_id/text_sha/index), normalized, dimensions=32, no network.
   - `gate.rs`: `gate_embed_input()` — Remote requires policy.remote.allow + allow_embedding + provider in allowed list + data_level gate. Mock/Local: data_level ≤ 1 AND data_level ≤ metadata.max_data_level. Secret gate blocks SECRET/TOKEN/PASSWORD/API_KEY/PRIVATE_KEY/sk_/ghp_/AKIA and high-entropy strings.
   - `cache.rs`: Domain-separated stable cache key with `emb1:` prefix + blake3 hex. Cache key builder/stability only; no cache-hit behavior yet.
   - `audit.rs`: JSONL audit writer at `.openlocus/audit/embeddings.jsonl`; no raw text/vector in audit events. Audit events use accurate names: `allow`, `block`, `query_embed`, `provider_unavailable` (not `cache_hit` unless real cache).
   - `dense_store.rs`: `JsonlEmbeddingStore` at `.openlocus/embeddings/vectors.jsonl`. Build from FileRecords with metadata-only views (`path:<path> language:<language> basename:<stem> words:<path tokens>`, no code snippet). Build uses real line counts: end_line=min(total_lines, 8), so short files get valid ranges. Cosine similarity search. Store `EmbeddingRecord` (no raw text; vector present for search).

2. **CLI additions**:
   - `openlocus provider status --json`: reports remote_default=false, outbound_default=false, supported providers [mock, disabled].
   - `openlocus provider audit --limit N --json`: reads audit JSONL, outputs events (no raw text).
   - `openlocus dense build --provider mock --experimental --json`: requires --experimental; builds vector store from metadata-only views.
   - `openlocus dense search <query> --provider mock --limit N --json`: embeds query, searches by cosine, materializes StoreHits via `materialize_evidence(Channel::Dense)`. CLI JSON uses query_sha/query_len instead of raw query text.
   - `openlocus dense purge --json`: removes vector store.

3. **Eval script** `eval/provider_dense_safety.py`: 45 safety checks covering remote/outbound defaults, experimental gate, vector/audit no raw text, secret blocking, stale hit rejection, disabled/unknown provider graceful degradation, missing store graceful error, cache key stability, short file range correctness, query SHA not raw query, audit event naming, trace no raw query/secret.

### Verification

```text
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
python3 eval/provider_dense_safety.py --openlocus target/debug/openlocus --out runs/provider-dense-safety.json
```

### Safety checks

45/45 safety checks passed:
- remote_default=false, outbound_default=false
- build without --experimental fails
- build with --experimental --provider mock succeeds with remote_calls=0
- vectors.jsonl exists, contains no raw code marker, no "text" field, valid ranges
- audit JSONL exists, has events, no raw marker, no "vector" field, no "text" field, no "cache_hit" event
- dense search returns citation-valid Evidence (Channel::Dense, freshness=verified_current)
- stale hit after file modification is skipped (materialize rejects stale SHA)
- disabled/unknown provider degrades gracefully (no panic, success=false), audit event written
- secret-like query text (sk_ prefix) is blocked; no raw secret in CLI JSON/audit/traces
- CLI JSON uses query_sha/query_len, not raw query field
- short file range is correct (end_line=min(total_lines, 8))
- missing store returns graceful error
- audit_raw_text_leak=false, remote_calls=0, citation_invalid_count=0

### Key findings

1. **Safe scaffold works**: All gates are functional. Remote is denied by default. Experimental opt-in is required. Secret scanning blocks token-like inputs. Audit contains no raw text or vectors. Vector store contains embedding vectors but no raw text/code snippet.
2. **Mock provider is deterministic and normalized**: Same inputs always produce the same unit-length vector. Different inputs produce different vectors. No network dependency.
3. **Materialization gate is essential**: Dense search produces StoreHits which must be materialized through `materialize_evidence()`. Stale hits (content_sha mismatch) are correctly rejected.
4. **Metadata-only views prevent code leakage**: The dense store builds views from path/language/basename/path-tokens only. No code snippets are included at data_level=0. The vector store and audit log do not contain raw code text.
5. **Short file ranges are now valid**: end_line=min(total_lines, 8) ensures materialize_evidence can verify ranges. Short files produce valid evidence.
6. **Query text never leaks**: CLI JSON uses query_sha/query_len. Trace events use query_sha. Audit never stores raw query text. Blocked secret queries do not appear in traces.
7. **Audit events use accurate names**: `query_embed` for query embedding, `allow`/`block`/`provider_unavailable` for decisions. Not `cache_hit` (no real cache behavior in R13).
8. **This is a safety scaffold only. No real semantic quality claim.** Mock vectors are deterministic blake3-based and do not capture semantic similarity. Dense mock search is integration/safety only.

### Caveats

- Mock provider vectors are deterministic but not semantically meaningful. Quality claims are limited to mock integration.
- The dense store builds one record per file (metadata view only). Future work could add chunk-level views with real embeddings.
- No real remote provider is implemented. The gate infrastructure is in place for future R14+ integration.
- Cache is not yet used for deduplication (build always recomputes). Cache key stability is verified by unit tests. Cache key builder/stability only; no cache-hit behavior yet.
- No ANN index; cosine search is linear scan over all records. Not suitable for large corpus.
- Dense mock search is integration/safety only; not a real semantic retrieval claim.

## 2026-06-12 — R14 Scaled Evidence Benchmark Foundation

### Objective

Establish a scaled benchmark program for evaluating OpenLocus retrieval quality across repository groups and task types, structured as S/M/L/X tiers with increasing scale and label quality requirements. This is a benchmark *foundation*, not a quality conclusion. The current S/M data uses logical repo groups from one OpenLocus workspace snapshot; independent external repositories are a follow-up expansion. The goal is to have a reproducible, anti-leakage evaluation pipeline that can run locally and produce meaningful file-level and span-level metrics with hard negatives as a first-class indicator.

### Design constraints

- Do not change EvidenceCore, Cargo license, or introduce remote dependencies.
- Public tasks contain no gold paths/lines; labels are private and separate.
- Hard negatives are first-class data, not optional.
- Citation validity/freshness/lock validation is a fail-closed safety gate (must be 1.0).
- No dense/LLM/graph quality claims.
- R14-S must be locally runnable; M/L/X define target structures for future expansion.
- Runner/scorer must be strictly isolated: runner never loads labels, scorer never calls CLI.
- Isolated benchmark root per repo: temp root with only declared source paths.
- Repo lock content manifest must be recomputed and verified (normalized SHA-256 per file sorted).
- Benchmark runner writes isolated `.openlocus/policy.toml` from repo lock glob-style excludes (fixtures/**, eval/**, etc).
- Canary tokens in labels must never appear in indexed/retrieved content; runtime canary retrieval runs inside isolated roots.
- Predictions with forbidden path prefixes/components are CRITICAL failures.
- Unknown `repo_id` is CRITICAL; runner refuses to fall back to the full workspace.

### Implementation notes

- **fixtures/r14/ directory**: README, taxonomy/annotation guide, dataset_manifest.json, repos.lock.jsonl, tasks/{sanity,medium,large,stress}.jsonl, labels/{sanity,medium,large,stress}.jsonl, labels/_canary.json, expected_failures/known_issues.md.
- **Data schema**: Public tasks have `task_id`, `query`, `task_type`, `method_hint`, `repo_id` — no gold. Labels have `task_id`, `gold_spans`, `hard_negatives`, `label_quality`. Repo lock has `repo_id`, `source`, `commit`, `content_manifest_sha`, `content_manifest_algorithm`, `policy/excludes` (glob-style), `language/tier` metadata.
- **R14-S data**: 4 logical repo groups from one OpenLocus workspace snapshot, 48 tasks, 48 labels, 47 hard negatives. Label quality: 8 human_reviewed, 37 mined_high_confidence, 3 mined. Populated=True.
- **R14-M data**: same 4 logical repo groups as S, 36 tasks, 36 labels, 31 hard negatives. Partial=True. Full M requires 8+ independent repo groups/repositories.
- **R14-L data**: 10 placeholder tasks with weak labels. Populated=False. Requires additional repos beyond current workspace.
- **R14-X data**: Not populated. Requires external repo sources. Running --tier X will fail.
- **eval/r14_generate_dataset.py**: Generates/refreshes R14 data with normalized content manifest SHA (sha256 per file sorted). Glob-style policy excludes. Avoids label leakage.
- **eval/r14_benchmark.py**: Strictly separated RUN phase (public tasks only, no labels) and SCORE phase (labels only, no CLI). Isolated temp roots per repo group with `.openlocus/policy.toml` written from repo lock. Unknown repo_id fail-closed. Failed-closed Rust citation validation (must be 1.0). Forbidden path prefix/component detection. Negative task metrics (negative_nonempty_rate@10). Span-overlap hard negative hit rate. Repo lock content manifest re-verification.
- **eval/r14_leakage_check.py**: static checks: task gold leakage, query-gold overlap, labels not in indexed root (path-component matching), glob-style policy excludes, label file isolation, canary placement, repo lock manifest verification, predictions forbidden path scan. Runtime canary retrieval is enforced by `r14_benchmark.py`.
- **eval/r14_smoke.py**: HARD FAIL smoke test. No best-effort. All checks must pass. Includes runtime canary retrieval, citation validity=1.0 with hash checked by Rust validator, forbidden path checks, isolated runner/scorer verification.

### R14-S foundation data

| Metric | Value |
|---|---|
| Repo groups | 4 logical groups from one OpenLocus workspace snapshot (openlocus-core, openlocus-retrieval, openlocus-store, openlocus-cli) |
| Tasks (sanity) | 48 |
| Labels (sanity) | 48 |
| Hard negatives (sanity) | 47 |
| Label quality | 8 human_reviewed, 37 mined_high_confidence, 3 mined |
| Task types | exact_symbol, implementation_search, config_policy, negative, stress, cross_repo |
| Anti-leakage | Public tasks have no gold; labels are private; runtime canary retrieval; isolated roots with repo-lock policy excludes |
| Citation gate | Fail-closed (validity must be 1.0) |
| Run time estimate | <5 min local |

### Current tier status

| Tier | Repo groups | Tasks | Labels | Hard Negatives | Populated | Evaluable |
|---|---|---|---|---|---|---|
| R14-S | 4 | 48 | 48 | 47 | True | True |
| R14-M | 4 | 36 | 36 | 31 | True (partial) | True |
| R14-L | 0 | 10 (placeholder) | 10 (weak) | 0 | False | False |
| R14-X | 0 | 0 | 0 | 0 | False | False |

### Key findings

1. **Benchmark pipeline works end-to-end with fail-closed safety**: Runner/scorer isolation, isolated temp roots, citation validity must be 1.0, forbidden path detection, unknown repo_id refusal, repo-lock policy files, and runtime canary retrieval are enforced.
2. **Anti-leakage design is strictly enforced**: Public tasks contain no gold information. Labels are in a separate directory with canary tokens. The leakage check catches gold path/line exposure, query-gold overlap, and forbidden prediction paths. 8 checks, 0 critical issues.
3. **Hard negatives are first-class with span-overlap metrics**: 47 hard negatives in R14-S. `hard_negative_hit_rate@10` requires line overlap unless a hard negative is explicitly file-level. `negative_nonempty_rate@10` measures false positive rate on negative tasks.
4. **Citation validity is fail-closed**: validity must be 1.0. Every citation must be hash+range+path valid. No path-only fallback.
5. **Repo lock content manifest is verified**: Normalized SHA-256 per file sorted. Mismatch = CRITICAL fail closed. Generator and benchmark use the same algorithm.
6. **Mined labels are usable but not human-verified**: `mined_high_confidence` labels are structurally sound but may have imprecise line ranges. Explicit `label_quality` field.
7. **R14-S is a safety foundation, not a quality conclusion**: Validates the pipeline is fail-closed. Does not support quality claims.
8. **R14-L/X are not populated**: Running --tier L or --tier X will fail with clear message. Structure is defined but data requires additional independent repos.
9. **Previous R14 graph precision is a future feature track**: Not the current R14 definition.

### Caveats

- This is a benchmark *safety foundation*. R14-S validates the pipeline is fail-closed; it does not support quality conclusions about retrieval methods.
- Mined labels are not human-verified. `mined_high_confidence` labels have structurally-sound spans but may be imprecise at line-level.
- R14-M is partial (4 logical repo groups; target is 8+ independent repo groups/repositories). R14-L/X are not populated.
- The current repo-group set is self-referential (OpenLocus codebase). External repos are required for generalizability.
- Stress and negative tasks have limited gold spans. Stress tasks have weak labels; negative tasks have empty gold.
- Hard negative hit rate depends on method quality; a high rate indicates the method is returning plausible but incorrect results.
- Citation validity as a safety gate catches structural issues but does not measure retrieval relevance.
- Runtime canary retrieval currently covers isolated R14-S benchmark roots; broader artifact-canary stress across future external repositories remains follow-up work.
- The benchmark does not claim dense/LLM/graph quality improvements. Those are future feature tracks.

## 2026-06-12 — R15 External Multi-Repo Benchmark Expansion

### Objective

Extend the R14 benchmark foundation with real local multi-repo benchmark data from independent external git repositories under `/workspace`. R15 adds 9 independent external repos covering Rust, Python, Go, TypeScript, and JavaScript, generating Medium/Large/Stress tier data with multi-language symbol extraction. This is a mined benchmark expansion, not a final quality conclusion. External local repos are workspace snapshots and are not modified.

### Design constraints

- Do not break R14 scripts or data; R15 is an independent checkpoint
- Do not modify external repos; only read and allowlist-copy manifest/source files into isolated roots
- Do not index /workspace root directly; must use repo lock declared source roots
- Runner/scorer isolation: runner never loads labels, scorer never calls CLI
- Isolated roots: allowlist-copy only declared source files under repo_id-specific folders; symlinks/artifacts are not copied
- Unknown repo_id fail-closed; no fallback to full workspace
- Citation validator hash-checks evidence in isolated root
- Path matching: scoring accepts exact paths or a single `repo_id/` prefix only, not arbitrary suffixes
- Repo lock uses `local_absolute_path` source with absolute paths; isolated root preserves relative paths
- Multi-language manifest: normalized SHA-256 across .rs .py .ts .tsx .js .jsx .go .mjs
- Skip directories: node_modules/target/.git/dist/build/.venv/__pycache__/.next/.nuxt/runs/fixtures/eval/docs/.openlocus
- Public tasks contain no gold path/line/hard_negatives/label_quality
- Labels include source_repo_kind: external_local
- Citation validity must be 1.0 (fail-closed)
- Runtime canary retrieval must return zero hits

### Implementation notes

- **fixtures/r15/ directory**: README.md, dataset_manifest.json, repos.lock.jsonl, tasks/{medium,large,stress}.jsonl, labels/{medium,large,stress}.jsonl, labels/_canary.json, taxonomy/annotation_guide.md, expected_failures/known_issues.md, safety_checks.json.
- **9 external repos resolved** (all exist and have sufficient source files):
  - fast-context-mcp (JS/.mjs, 5 files, 2361 lines)
  - grok2api (Python, 157 files, 29676 lines)
  - infinite-canvas (Go/TS/TSX, 110 files, 14100 lines)
  - gemini-web2api (Python, 9 files, 1330 lines)
  - windsurf2api (JS, 143 files, 36127 lines)
  - kiro2 (Rust/TS/TSX, 114 files, 33908 lines)
  - triviumdb (Rust, 117 files, 45947 lines)
  - smartsearch (Python/JS, 69 files, 22393 lines)
  - codex2api (Go/TS/TSX, 239 files, 114692 lines)
- **eval/r15_generate_dataset.py**: Multi-language source scanning with regex-based symbol extraction for Rust/Python/Go/JS/TS. Generates normalized manifest SHA across all source extensions. Creates 8-20 tasks per repo (definition/symbol, implementation_search, config/import, negative, stress). Public tasks have no gold. Labels have gold_spans, hard_negatives, label_quality, source_repo_kind.
- **eval/r15_benchmark.py**: Extends R14 benchmark for absolute repo source roots and multi-language manifest. Creates isolated roots by allowlist-copying only declared source files under repo_id-specific folders. Unknown repo_id fail-closed. Runtime `.openlocus` traces are removed after every query/citation validation and audited before/after each method. Rust citation validator runs before isolated-root cleanup and must report 1.0 validity. Scoring accepts exact paths or a single `repo_id/` prefix only. Same fail-closed safety gates.
- **eval/r15_leakage_check.py**: Extended from R14 with static checks including exact 9-repo lock integrity, duplicate repo_id/source path detection, absolute source path verification, multi-language manifest verification, task/label/manifest consistency, hard-negative non-overlap, and source_repo_kind in labels.
- **eval/r15_smoke.py**: HARD FAIL smoke test. Fixture validation, leakage check, small matrix benchmark (regex, bm25), Rust citation hash gate, canary verification, multi-language coverage check. 112/112 checks passed.

### R15-M baseline results (166 tasks, 9 repos)

| Metric | regex | bm25 |
|---|---|---|
| file_recall@1 | 0.852 | 0.548 |
| file_recall@5 | 0.956 | 0.719 |
| file_recall@10 | 0.970 | 0.741 |
| mrr | 0.889 | 0.623 |
| span_f0.5@10 | 0.263 | 0.188 |
| hard_negative_hit_rate@10 | 0.289 | 0.230 |
| negative_nonempty_rate@10 | 0.000 | 0.645 |
| success_rate | 1.0 | 1.0 |

Safety: passed. Canary: 36 checked, 0 hits, 0 failures. Citation hash checked.

### R15 data scale

| Tier | Repos | Tasks | Labels | Hard Negatives | Label Quality |
|------|-------|-------|--------|----------------|---------------|
| R15-M | 9 | 166 | 166 | 270 | mined_high_confidence (135) + mined (9) + human_reviewed (10) + weak (12) |
| R15-L | 9 | 294 | 294 | 270 | mined (270) + weak (24) |
| R15-stress | 9 | 19 | 19 | 0 | human_reviewed (3) + weak (16) |

### Key findings

1. **Multi-repo benchmark pipeline works end-to-end**: 9 independent external repos across 5 languages (Rust, Python, Go, JavaScript, TypeScript) with 166 medium-tier tasks, 270 hard negatives. Fail-closed safety enforced.
2. **Regex search outperforms BM25 on this multi-repo fixture**: FileRecall@1 is 0.852 (regex) vs 0.548 (bm25). This is likely because many tasks target exact symbol names which regex matches precisely, while BM25's tokenization may dilute short queries.
3. **BM25 has high false positive rate on negative tasks**: negative_nonempty_rate@10 is 0.645 (bm25) vs 0.000 (regex). BM25 returns results for many negative queries, while regex returns empty for non-matching exact strings.
4. **Hard negative hit rate is non-trivial**: ~0.23-0.29 for both methods. This indicates that structurally plausible but incorrect results are common, which is expected with mined hard negatives from the same repo.
5. **Span-level precision is improved vs R14-S baseline**: SpanF0.5@10 is 0.263 (regex) vs R14-S's lower sanity baseline. This improvement is likely due to better symbol extraction and more precise gold spans from multi-language definitions.
6. **Anti-leakage design holds across repos**: 0 critical leakage issues, canary retrieval returns zero hits, no gold in public tasks.
7. **Multi-language symbol extraction is functional but heuristic**: Rust/Python/Go/JS/TS patterns work for common cases but may miss or misidentify symbols in unusual patterns.
8. **This is a mined benchmark expansion, not a quality conclusion.** Labels are mined with varying confidence; not human-verified.

### Caveats

- This is a mined benchmark expansion, not a quality conclusion.
- Mined labels are not human-verified. `mined_high_confidence` labels have structurally-sound spans but may be imprecise at line-level.
- External local repos are workspace snapshots; they are not modified but their content may change over time, which would invalidate the manifest SHA.
- Multi-language support is best-effort. OpenLocus CLI may only support specific file types. If the CLI does not index `.mjs` or `.go` files, tasks targeting those types will return empty results.
- Symbol extraction is regex-based heuristic. It may miss or misidentify symbols, especially for unusual patterns (Go methods with receivers, Python decorators, JS arrow functions).
- Hard negatives are mined, not curated. They are structurally plausible but may not always be the best distractors.
- Hard-negative overlap with gold spans is statically blocked, but distractor quality still requires human review.
- The benchmark does not claim dense/LLM/graph quality improvements.
- Baseline metrics (regex outperforming BM25 on exact-symbol tasks) are specific to this fixture and should not be generalized.
- smartsearch has 2102 Python files but only 69 are indexed after excluding node_modules, __pycache__, etc. Most files are in excluded directories.

## 2026-06-12 — R16 Multi-Method Quality Bakeoff

### Objective

Run a cross-matrix quality bakeoff across R14-S, R15-M, and R15-stress using all four lexical/symbol/RRF methods (regex, BM25, symbol, RRF). Produce aggregate report with winners, safety verification, and conclusions. No provider/dense/LLM claims.

### Implementation notes

- **eval/r16_quality_bakeoff.py**: CLI args `--openlocus`, `--workspace`, `--out`, `--skip-run`. Runs three benchmark matrices via subprocess: R14-S, R15-M, R15-stress. Loads JSON reports, verifies safety_passed, citation_validity=1.0 for each method with evidence, citation_hash_checked true or citation_not_applicable true, canary_retrieval.passed where present. Produces aggregate JSON (schema_version r16-v1) with runs metadata, method tables, winners per metric, safety_checks, conclusions. Produces markdown report alongside output. Hard fails (exit nonzero) if any safety gate fails or any runner command fails. No provider/dense/LLM claims.

### R16 bakeoff results

**R14-S Matrix:**

| Metric | regex | bm25 | symbol | rrf |
|---|---|---|---|---|
| FileRecall@1 | 0.457 | **0.696** | 0.674 | 0.543 |
| FileRecall@5 | 0.587 | **0.870** | 0.717 | **0.870** |
| FileRecall@10 | 0.630 | **0.870** | 0.717 | **0.870** |
| MRR | 0.518 | **0.770** | 0.684 | 0.661 |
| SpanF0.5@10 | 0.068 | 0.064 | **0.199** | 0.084 |
| hard_negative@10 | 0.152 | 0.196 | **0.043** | 0.152 |
| negative_nonempty@10 | **0.000** | **0.000** | **0.000** | **0.000** |

**R15-M Matrix:**

| Metric | regex | bm25 | symbol | rrf |
|---|---|---|---|---|
| FileRecall@1 | 0.852 | 0.548 | 0.807 | **0.933** |
| FileRecall@5 | 0.956 | 0.719 | 0.830 | **0.993** |
| FileRecall@10 | 0.970 | 0.741 | 0.844 | **0.993** |
| MRR | 0.889 | 0.623 | 0.820 | **0.959** |
| SpanF0.5@10 | 0.263 | 0.188 | **0.310** | 0.253 |
| hard_negative@10 | 0.289 | 0.230 | **0.052** | 0.259 |
| negative_nonempty@10 | **0.000** | 0.645 | **0.000** | 0.645 |

**R15-stress Matrix (negative tasks only):**

| Metric | regex | bm25 | symbol | rrf |
|---|---|---|---|---|
| negative_nonempty@10 | 0.474 | 0.684 | **0.105** | 0.684 |

### Safety facts

- All three matrices: safety_passed=true
- All methods across all matrices: citation_validity=1.0
- Citation hash checked in R14/R15 reports via Rust validator
- canary_retrieval.passed=true where present
- No remote calls

### Conclusions

1. **RRF wins R15-M recall/MRR** (FileRecall@1 0.933, @5/10 0.993, MRR 0.959) but inherits BM25 negative false positive behavior (negative_nonempty@10 0.645 on R15-M and 0.684 on stress), so it is not safe as default for precision-sensitive tasks without negative gating or query intent routing.
2. **Symbol has best span precision/hard-negative profile on R15-M** (SpanF0.5 0.310, hard_negative_hit_rate 0.052, negative_nonempty 0.000) but lower recall than RRF, so it is ideal as precision anchor, not sole retriever.
3. **Regex is surprisingly strong on mined exact-symbol external tasks** (R15-M FileRecall@1 0.852, negative_nonempty 0.000), but this reflects task distribution and exact-string bias; not a general natural-language conclusion.
4. **BM25 strong in R14-S but weak and false-positive-heavy in R15-M/stress**; needs query intent routing or threshold/negative guard.
5. **No promotion of any method to universal default from R16**; next research should be query intent router / negative guard / method fusion policy, not raw channel addition.

### Caveats

- R16 is a multi-method quality bakeoff; not a universal quality conclusion.
- Mined labels are not human-verified.
- No provider/dense/LLM quality claims.
- RRF negative_nonempty_rate reflects BM25 false-positive inheritance.
- R14-S uses self-referential OpenLocus workspace data; not generalizable.

---

## 2026-06-12 — R17 Query Intent Router / Negative Guard Experiment

### Objective

Test whether query-only routing heuristics and negative guards can reduce negative_nonempty false positives (inherited by RRF from BM25) while preserving recall. Eval-layer research only; does NOT change Rust core.

### Current hypothesis

RRF wins recall but inherits BM25 negative false positives (R15-M negative_nonempty@10=0.645, R15-stress=0.684). A query-only router that suppresses evidence for noise/vague/fabricated queries, combined with a symbol/regex evidence guard for RRF, should materially reduce negative_nonempty without unacceptable recall regression.

### Implementation notes

- **eval/r17_router_guard_experiment.py**: Loads existing R15 predictions, applies three synthetic routing strategies without invoking OpenLocus again, scores with R15-compatible metrics, produces JSON (schema_version r17-v1) and markdown output.
- **Strategies**:
  1. **query_only_router_v0**: Routes based only on query text, no labels, no task_type. Heuristics: negative/noise marker detection (FIXME_bogus, TODO_nonexistent, etc.), compound snake_case noise detection (quantum_entanglement_solver, blockchain_consensus_protocol), vague multi-word query detection (all common words like "error handling", "data processing"), exact identifier detection (prefer symbol then regex), identifier token detection (prefer regex then symbol), default RRF for recall.
  2. **task_type_assisted_router_upper_bound**: Uses public task_type as an upper-bound reference (not production router). mutation_negative/query_noise/negative → empty; provider_ish → empty; stress → symbol if evidence else empty; exact_symbol/implementation_search → symbol if evidence else regex else rrf; config_import → regex if evidence else rrf.
  3. **rrf_guarded_by_symbol_regex**: Choose RRF only if either symbol or regex has evidence; otherwise empty. Tests whether symbol/regex evidence presence is a sufficient guard against RRF/BM25 false positives.
- **Scoring**: Reuses R15-compatible metrics (FileRecall@1/5/10, MRR, SpanF0.5@10, token_waste@10, hard_negative_hit_rate@10, negative_nonempty_rate@10, success_rate). Exact or single repo_id prefix path matching only.
- **Citation safety**: Inherited from source validated predictions. Records citation_inherited_from_validated_methods=true. Does NOT claim new citation validation.
- **Safety gates**: Hard fail if source report safety_passed is not true, expected methods are missing, citation_validity < 1.0, citation_hash_checked not true (or citation_not_applicable), canary_retrieval.passed not true, or prediction JSONL metrics do not match the source report baseline metrics.

### R17 results

**R15-M Strategy Metrics:**

| Metric | regex | bm25 | symbol | rrf | query_only_router_v0 | task_type_assisted | rrf_guarded |
|---|---|---|---|---|---|---|---|
| file_recall@1 | 0.852 | 0.541 | 0.807 | 0.941 | 0.904 | 0.904 | 0.941 |
| file_recall@5 | 0.956 | 0.719 | 0.830 | 0.993 | 0.941 | 0.926 | 0.993 |
| file_recall@10 | 0.970 | 0.741 | 0.844 | 0.993 | 0.948 | 0.941 | 0.993 |
| mrr | 0.889 | 0.619 | 0.820 | 0.963 | 0.918 | 0.916 | 0.963 |
| span_f0.5@10 | 0.263 | 0.188 | 0.310 | 0.253 | 0.315 | 0.380 | 0.253 |
| token_waste@10 | 0.677 | 0.639 | 0.204 | 0.695 | 0.539 | 0.264 | 0.695 |
| hard_negative@10 | 0.289 | 0.230 | 0.052 | 0.259 | 0.237 | 0.074 | 0.259 |
| negative_nonempty@10 | 0.000 | 0.645 | 0.000 | 0.645 | 0.000 | 0.258 | 0.000 |

**R15-stress Strategy Metrics (negative tasks only):**

| Metric | regex | bm25 | symbol | rrf | query_only_router_v0 | task_type_assisted | rrf_guarded |
|---|---|---|---|---|---|---|---|
| negative_nonempty@10 | 0.474 | 0.684 | 0.105 | 0.684 | 0.158 | 0.316 | 0.474 |

**Per-Strategy Route Counts:**

- query_only_router_v0: symbol=43, regex=91, empty=48, rrf=3
- task_type_assisted: symbol=123, regex=18, rrf=8, empty=36
- rrf_guarded: rrf=144, empty=41

**Key Deltas vs RRF (R15-M):**

- query_only_router_v0 vs RRF: negative_nonempty -0.645, FileRecall@1 -0.037, MRR -0.044, SpanF0.5 +0.062
- rrf_guarded_by_symbol_regex vs RRF: negative_nonempty -0.645, all other metrics +0.000 (identical recall/MRR/SpanF0.5)

### Key findings

1. **rrf_guarded_by_symbol_regex eliminates R15-M negative_nonempty (0.645 → 0.000) with zero recall/MRR regression**: Because the guard only returns RRF evidence when symbol or regex also found evidence, and positive tasks always have at least one of those, the guard perfectly filters negative tasks on R15-M. This is the strongest result: a simple evidence-presence guard is sufficient for R15-M negatives.
2. **query_only_router_v0 also eliminates R15-M negative_nonempty (0.645 → 0.000) with acceptable recall regression**: FileRecall@1 drops from 0.941 to 0.904 (delta -0.037), MRR from 0.963 to 0.918 (delta -0.044). SpanF0.5 improves from 0.253 to 0.315 (+0.062). The router correctly identifies negative tasks (vague queries, fabricated identifiers) and routes them to empty.
3. **On R15-stress, both strategies reduce but don't eliminate negative_nonempty**: query_only_router_v0 drops from 0.684 to 0.158; rrf_guarded drops to 0.474. The stress tier includes common-word queries where regex still returns false positives, and the symbol/regex guard lets those through.
4. **task_type_assisted_router is an upper bound**: It achieves 0.258 on R15-M (not zero because some config_import tasks have legitimate evidence) and 0.316 on R15-stress. It uses task_type as benchmark metadata, not runtime information.
5. **No core default promotion**: While R15-M negative_nonempty reaches 0.000 with two strategies, R15-stress negative_nonempty remains above 0 for all strategies. The bar for core default promotion requires BOTH R15-M and R15-stress negative_nonempty improvement without unacceptable recall/MRR regression.
6. **Next steps**: Learning/calibrating intent classifier or adding score thresholds, but still evidence-gated. No LLM or dense model claims.

### Caveats

- R17 is an eval-layer router/guard experiment; does NOT change Rust core.
- query_only_router uses heuristic rules only; not a learned classifier.
- task_type_assisted_router uses benchmark metadata (task_type) that is not runtime-available; it is an upper-bound reference.
- Citation safety is inherited from validated source predictions; no new citation validation is claimed.
- Mined labels are not human-verified; line ranges may be imprecise.
- Negative tasks in R15-stress have weak or human_reviewed labels only.
- No provider/dense/LLM quality claims are made.
- Routing decisions are deterministic and reproducible from the same inputs.
- The compound_snake_case_noise detector uses a fixed set of domain keywords; real fabricated identifiers could evade it.

## 2026-06-12 — R18 Threshold/Guard Calibration Sweep

### Objective

Sweep threshold and guard configurations over R15 benchmark predictions to find Pareto-optimal strategies that reduce negative_nonempty while preserving recall. Uses deterministic repo-holdout split for R15-M. Eval-layer research only; does NOT change Rust core.

### Current hypothesis

R17 showed that query_only_router_v0 and rrf_guarded_by_symbol_regex both eliminate R15-M negative_nonempty (0.645→0.000), but R15-stress negative_nonempty remains above 0. R18 tests whether systematic threshold/guard sweeps over public query + prediction features can produce a calibrated strategy with better stress performance while maintaining R15-M recall.

### Implementation notes

- **eval/r18_calibration_sweep.py**: Schema version r18-v1. Imports R17 helpers (load_jsonl, score_predictions, verify_safety_gates, check_baseline_prediction_consistency, query feature heuristics) via sys.path resolution.
- **Safety gates**: Hard fail on source report safety_passed, canary_retrieval, expected methods, citation_validity=1.0, citation_hash_checked, baseline prediction/report consistency. Route phase must happen before labels are loaded; enforced by code structure.
- **Public features only for routing**: query string, repo_id, evidence counts per method, top/max score per method, top evidence channels/why, R17 query-only heuristics (negative/noise/vague/exact identifier). Labels/gold loaded only after all routing decisions.
- **Strategy family**: Baselines (regex, bm25, symbol, rrf), R17 fixed references (query_only_router_v0, rrf_guarded_by_symbol_regex), and sweep configs over thresholds [0.0, 0.005, 0.01, 0.015, 0.02, 0.03, 0.05, 0.08]:
  - rrf_score_min_{t}: use RRF if top RRF score >= t else empty
  - rrf_score_min_{t}_regex_or_symbol: use RRF if score >= t and (regex_has or symbol_has)
  - rrf_score_min_{t}_symbol: use RRF if score >= t and symbol_has
  - query_noise_plus_rrf_score_min_{t}: if noise/vague query then empty else RRF if score >= t
  - query_noise_plus_rrf_agree_min_{t}: if noise/vague query then empty else RRF if score >= t and (regex_has or symbol_has)
- **Scoring**: R15-compatible metrics on full R15-M, train R15-M, holdout R15-M, and R15-stress.
- **Repo-holdout split**: Deterministic by sorted repo_id: first 6 train (codex2api, fast-context-mcp, gemini-web2api, grok2api, infinite-canvas, kiro2), last 3 holdout (smartsearch, triviumdb, windsurf2api).
- **Candidate selection**: From train only. Eligible if train negative_nonempty<=0.05 and train FileRecall@1 >= (RRF_train - 0.05). Among eligible, maximize train MRR, minimize token_waste. If no eligible, fallback with no_candidate_met_constraints.
- **Pareto frontier**: Full R15-M over dimensions: maximize FileRecall@1, SpanF0.5@10; minimize negative_nonempty_rate@10, hard_negative_hit_rate@10.
- **Output**: JSON (schema_version r18-v1), markdown, and docs/r18-calibration-sweep.md.

### R18 results

**Selected candidate**: rrf_guarded_by_symbol_regex (eligible count: 15)

**Full R15-M Strategy Metrics (baselines + R17 + selected):**

| Metric | regex | bm25 | symbol | rrf | query_only_router_v0 | rrf_guarded | selected |
|---|---|---|---|---|---|---|---|
| file_recall@1 | 0.852 | 0.541 | 0.807 | 0.941 | 0.904 | 0.941 | 0.941 |
| mrr | 0.889 | 0.619 | 0.820 | 0.963 | 0.918 | 0.963 | 0.963 |
| span_f0.5@10 | 0.263 | 0.188 | 0.310 | 0.253 | 0.315 | 0.253 | 0.253 |
| negative_nonempty@10 | 0.000 | 0.645 | 0.000 | 0.645 | 0.000 | 0.000 | 0.000 |

**Key Sweep Finding — query_noise_plus_rrf_agree_min (full R15-M):**

| Threshold | neg_nonempty | FileRecall@1 | MRR | stress_neg_nonempty |
|---|---|---|---|---|
| 0.000 | 0.000 | 0.941 | 0.961 | 0.000 |
| 0.005 | 0.000 | 0.941 | 0.961 | 0.000 |
| 0.010 | 0.000 | 0.941 | 0.961 | 0.000 |
| 0.015 | 0.000 | 0.941 | 0.961 | 0.000 |
| 0.020 | 0.000 | 0.933 | 0.955 | 0.000 |
| 0.030 | 0.000 | 0.933 | 0.955 | 0.000 |
| 0.050 | 0.000 | 0.015 | 0.015 | 0.000 |
| 0.080 | 0.000 | 0.000 | 0.000 | 0.000 |

**Holdout R15-M (rrf_guarded_by_symbol_regex vs RRF):**

| Metric | RRF | rrf_guarded | Delta |
|---|---|---|---|
| file_recall@1 | 0.844 | 0.844 | +0.000 |
| mrr | 0.900 | 0.900 | +0.000 |
| negative_nonempty@10 | 0.700 | 0.000 | -0.700 |

**R15-stress (selected strategies):**

| Strategy | negative_nonempty@10 |
|---|---|
| rrf | 0.684 |
| symbol | 0.105 |
| query_only_router_v0 | 0.158 |
| rrf_guarded_by_symbol_regex | 0.474 |
| query_noise_plus_rrf_agree_min_0.0 | 0.000 |
| query_noise_plus_rrf_agree_min_0.015 | 0.000 |

**Pareto frontier (Full R15-M, key entries):**

| Strategy | FileRecall@1 | SpanF0.5@10 | neg_nonempty | hard_neg |
|---|---|---|---|---|
| rrf_guarded_by_symbol_regex | 0.941 | 0.253 | 0.000 | 0.259 |
| query_only_router_v0 | 0.904 | 0.315 | 0.000 | 0.237 |
| symbol | 0.807 | 0.310 | 0.000 | 0.052 |

### Key findings

1. **Train-selected candidate is useful but not stress-safe**: `rrf_guarded_by_symbol_regex` preserves RRF FileRecall@1/MRR on full R15-M (0.941/0.963) and holdout (0.844/0.900), while reducing medium negative_nonempty to 0.000. R15-stress remains weak at 0.474 negative_nonempty, above symbol's 0.105.
2. **The query noise guard is the key differentiator for stress**: rrf_guarded_by_symbol_regex alone leaves stress at 0.474 because regex returns false positives for common-word stress queries. The query noise guard identifies these as vague/noise and routes to empty, achieving 0.000 on stress.
3. **rrf_guarded_by_symbol_regex remains the selected candidate by MRR**: On train, it has MRR 0.994 vs query_noise_plus_rrf_agree_min_0.0 MRR 0.961. The candidate selection rule (maximize MRR among eligible) favors the simpler guard.
4. **Threshold sweep reveals sharp recall cliff at 0.05**: RRF top scores rarely fall between 0.03 and 0.05; most are either very high (>0.05) or very low (<0.02). Thresholds above 0.03 reject nearly all evidence, making them useless in practice.
5. **Stress-zero strategies are observations, not promotions**: `query_noise_plus_rrf_agree_min` variants reach 0.000 stress negative_nonempty on the 19-task stress set, but this is too small and mined to justify default promotion.
6. **R15-stress remains the critical failure surface for non-query-noise strategies**: Without the query noise guard, stress negative_nonempty stays above symbol baseline. With it, the stress surface is addressed but only through heuristic classification of query intent.
7. **Pareto frontier shows trade-off between recall and hard-negative precision**: symbol has lowest hard_negative (0.052) but lower recall; rrf_guarded has highest recall but higher hard_negative (0.259); query_only_router_v0 is a middle ground.
8. **No core default promotion in R18**: This is eval-layer calibration. Threshold/guard choices are calibrated on mined R15 data and require larger/human-verified validation before promotion.

### Caveats

- R18 is an eval-layer calibration sweep; does NOT change Rust core.
- Calibration is on mined R15 data; not human-verified.
- Repo-holdout split is deterministic but small (9 repos, 3 holdout); not a substitute for cross-dataset validation.
- R15-stress has only 19 tasks; metric estimates are noisy.
- Sweep thresholds are hand-chosen; exhaustive search would be exponential.
- Pareto frontier depends on chosen dimensions; different dimensions may yield different frontiers.
- No core default promotion unless both R15-M and R15-stress negative_nonempty improve without unacceptable recall/MRR regression.
- Citation safety is inherited from validated source predictions; no new citation validation is claimed.
- No LLM/dense/provider claims are made.
- Routing decisions are deterministic and reproducible from the same inputs.

---

## 2026-06-12 — R19 Large/Stress Guard Generalization Validation

### Objective

Validate whether R18 train-selected guard strategies generalize to R15-L (294 weak/mined tasks) and R15-stress. R15-L labels are mostly weak/mined; used only for generalization smoke, not as promotion evidence. Does NOT change Rust core.

### Current hypothesis

The R18 train-selected `rrf_guarded_by_symbol_regex` should preserve recall and reduce negative_nonempty on R15-L, similar to its R15-M behavior. The `query_noise_plus_rrf_agree_min` stress-zero observation should repeat on R15-stress. However, R15-L labels are weak/mined, so any "improvement" is a generalization smoke test, not promotion evidence.

### Implementation notes

- **eval/r19_large_guard_validation.py**: Schema version r19-v1. Imports R17 and R18 helpers. Runs R15 benchmark for L and stress tiers with R19-owned report/prediction artifacts.
- **R19-owned prediction artifacts**: Generic `r15-large-{method}-predictions.jsonl` and `r15-stress-{method}-predictions.jsonl` are copied to `r19-r15-large-{method}-predictions.jsonl` and `r19-r15-stress-{method}-predictions.jsonl` immediately after benchmark run. Provenance includes sha256/bytes/jsonl_lines. --skip-run requires R19-owned predictions only.
- **Safety gates**: source report safety_passed, canary_retrieval passed, expected methods present, citation_validity=1.0, citation_hash_checked or citation_not_applicable true, baseline prediction/report consistency hard gate (imported from R17). Labels loaded only after all route predictions generated.
- **Strategy set (9 total)**:
  - Baselines: regex, bm25, symbol, rrf
  - query_only_router_v0 (R17 fixed reference)
  - rrf_guarded_by_symbol_regex (R18 train-selected candidate)
  - query_noise_plus_rrf_agree_min_0.0 (R18 stress-zero observation)
  - query_noise_plus_rrf_agree_min_0.02
  - query_noise_plus_rrf_score_min_0.02
- **Scoring**: FileRecall@1/5/10, MRR, SpanF0.5@10, token_waste@10, hard_negative_hit_rate@10, negative_nonempty_rate@10, success_rate. Label quality counts for large/stress with explicit caveat.
- **Generalization assessment fields**: selected_candidate_large_ok, selected_candidate_stress_ok, stress_zero_observation_repeated, promotion_ready (always false).

### R19 results

#### R15-L strategy metrics (294 tasks, labels: 270 mined, 24 weak)

| Strategy | FileRecall@1 | MRR | SpanF0.5@10 | neg_nonempty@10 |
|---|---:|---:|---:|---:|
| regex | 0.848 | 0.884 | 0.270 | 0.042 |
| bm25 | 0.456 | 0.532 | 0.156 | 0.917 |
| symbol | 0.822 | 0.838 | 0.360 | 0.000 |
| rrf | 0.911 | 0.949 | 0.264 | 0.917 |
| query_only_router_v0 | 0.885 | 0.902 | 0.319 | 0.333 |
| rrf_guarded_by_symbol_regex | 0.911 | 0.949 | 0.264 | 0.042 |
| query_noise_plus_rrf_agree_min_0.0 | 0.900 | 0.938 | 0.264 | 0.000 |
| query_noise_plus_rrf_agree_min_0.02 | 0.896 | 0.933 | 0.263 | 0.000 |
| query_noise_plus_rrf_score_min_0.02 | 0.896 | 0.933 | 0.263 | 0.000 |

#### R15-stress strategy metrics (19 tasks, labels: 3 human_reviewed, 16 weak)

| Strategy | neg_nonempty@10 |
|---|---:|
| regex | 0.474 |
| bm25 | 0.684 |
| symbol | 0.105 |
| rrf | 0.684 |
| query_only_router_v0 | 0.158 |
| rrf_guarded_by_symbol_regex | 0.474 |
| query_noise_plus_rrf_agree_min_0.0 | 0.000 |
| query_noise_plus_rrf_agree_min_0.02 | 0.000 |
| query_noise_plus_rrf_score_min_0.02 | 0.000 |

#### Generalization assessment

| Field | Value |
|---|---|
| selected_candidate_large_ok | True |
| selected_candidate_stress_ok | False |
| stress_zero_observation_repeated | True |
| promotion_ready | False |

### Key findings

1. **rrf_guarded_by_symbol_regex generalizes to R15-L**: FileRecall@1 is preserved (0.911 vs RRF 0.911, delta +0.000), negative_nonempty drops from 0.917 to 0.042. However, R15-L labels are weak/mined; this is generalization smoke only, not promotion evidence.
2. **rrf_guarded_by_symbol_regex does NOT improve stress beyond symbol**: Stress negative_nonempty is 0.474, above symbol's 0.105. The selected candidate fails the stress test, consistent with R18 findings. Query noise guard is needed for stress improvement.
3. **query_noise_plus_rrf_agree_min_0.0 stress-zero observation repeats**: Achieves 0.000 stress negative_nonempty and 0.000 R15-L negative_nonempty. On R15-L, FileRecall@1 is 0.904 (delta -0.007 vs RRF). This is an observation, not promotion evidence.
4. **R15-L labels are weak/mined (270 mined, 24 weak)**: Any metric improvement or regression is generalization smoke only. These labels cannot serve as promotion evidence.
5. **R15-stress has only 19 tasks (3 human_reviewed, 16 weak)**: Metric estimates are very noisy. The stress-zero result is a pattern observation on a small sample, not a reliable measurement.
6. **No core default promotion from R19**: promotion_ready is always false. Requires human-verified labels and larger stress dataset.

### Caveats

- R19 is an eval-layer generalization validation; does NOT change Rust core.
- R15-L labels are mostly weak/mined; used for generalization smoke only, not as promotion evidence.
- R15-stress has only 19 tasks; metric estimates are very noisy.
- Guard strategies were calibrated on R15-M in R18; R15-L generalization is a smoke test, not a validation.
- Citation safety is inherited from validated source predictions; no new citation validation is claimed.
- No LLM/dense/provider claims are made.
- Routing decisions are deterministic and reproducible from the same inputs.
- promotion_ready is always false in R19; requires human-verified labels and larger stress dataset.

---

## 2026-06-12 — R20 Auto-Wide Retrieval Failure-Surface Benchmark (Dataset + Static Validator)

### Objective

Generate a failure-discovery benchmark dataset and static validation artifacts from R15 repos.lock.jsonl and local source paths. R20 labels are failure-surface oracle/probe labels, NOT EvidenceCore or promotion evidence. No Rust core changes, no strategy matrix, no promotion, no provider/QuIVer.

### Design constraints

- **Candidate is not fact.** R20 labels are failure-surface oracle/probe labels, not EvidenceCore.
- **Public tasks** contain ONLY: `task_id`, `repo_id`, `query`, `public_version`, `source_tier`. No gold/expected/oracle/risk/judgement fields.
- **Private labels** carry all judgement fields: `query_category`, `intent_guess`, `risk_tags`, `oracle_type`, `expected_behavior`, `label_quality`, `gold_spans`, `hard_distractors`, `must_not_primary`, `why_this_is_hard`, `which_strategy_it_targets`, `caveat`.
- **expected_behavior** enum: `primary_evidence` | `supporting_only` | `weak_candidates` | `abstain` | `no_primary`
- **oracle_type** enum: `deterministic` | `mined` | `differential` | `metamorphic` | `stress`
- **label_quality**: `mined_high_confidence` | `mined` | `weak` (NO `human_reviewed`)
- **R20 is failure discovery + static validation, NOT promotion evidence.**
- No Rust core changes, no strategy matrix, no promotion, no provider/QuIVer.

### Implementation notes

- **eval/r20_generate_auto_wide.py**: Deterministic generator (seed=42) that:
  - Reuses R15 repos.lock.jsonl and local source paths
  - Extracts symbols/config/routes/imports/tests/files from source text via regex heuristics
  - Generates 25 required query_category types across all 9 R15 repos
  - Produces public tasks (minimal fields) and private labels (all judgement fields)
  - Validates gold_spans / must_not_primary / hard_distractors overlap
  - Sorts outputs by task_id for determinism
  - Fills minimum coverage gaps with synthetic weak probes

- **eval/r20_static_validate.py**: Static validator enforcing:
  1. No private fields in public tasks
  2. Task/label ID bijection, no duplicates, no unknown repo_ids
  3. Enum validity (expected_behavior, oracle_type, label_quality)
  4. `primary_evidence` must have gold_spans; `abstain`/`no_primary` must not
  5. `must_not_primary` must not overlap `gold_spans`
  6. `hard_distractors` must not overlap `gold_spans`
  7. Gold span paths/ranges must exist in locked source and be in bounds
  8. Repo lock content_manifest_sha must match recomputed SHA
  9. `label_quality` must not be `human_reviewed`
  10. All 25 required categories present with >= 5 tasks each
  11. >= 9 repos, >= 300 total tasks, >= 15 per repo
  12. `dataset_manifest` flags: `not_promotion_evidence=true`, `core_changes=false`, `remote_calls=0`, `dense_or_llm_claims=false`

- **fixtures/r20_auto_wide/**: Dataset directory with:
  - `dataset_manifest.json`, `repos.lock.jsonl`
  - `tasks/auto_wide.jsonl` (public tasks)
  - `labels/auto_wide.jsonl` (private labels)
  - `safety_checks.json`, `coverage_report.json`, `README.md`

### R20 generation results

| Metric | Value |
|---|---|
| Repos | 9 |
| Tasks | 741 |
| Labels | 741 |
| Categories | 25 (all >= 5 tasks) |
| Per-repo minimum | 72 |
| Label quality distribution | mined_high_confidence: 315, mined: 168, weak: 258 |
| Expected behavior distribution | primary_evidence: 374, abstain: 177, weak_candidates: 90, no_primary: 45, supporting_only: 55 |
| Oracle type distribution | deterministic: 438, stress: 148, mined: 110, metamorphic: 36, differential: 9 |

### R20 static validation results

| Check | Result |
|---|---|
| No private fields in public tasks | ✅ |
| Task/label ID bijection | ✅ |
| No duplicate IDs | ✅ |
| No unknown repo_ids | ✅ |
| Enum validity (expected_behavior, oracle_type, label_quality) | ✅ |
| primary_evidence has gold_spans | ✅ |
| abstain/no_primary has empty gold_spans | ✅ |
| must_not_primary no gold overlap | ✅ |
| hard_distractors no gold overlap | ✅ |
| Gold span paths exist in locked source | ✅ |
| Gold span ranges in bounds | ✅ |
| Repo lock content_manifest_sha verified | ✅ |
| label_quality != human_reviewed | ✅ |
| All 25 categories >= 5 tasks | ✅ |
| >= 9 repos | ✅ |
| >= 300 total tasks | ✅ |
| >= 15 tasks per repo | ✅ |
| not_promotion_evidence=true | ✅ |
| core_changes=false | ✅ |
| remote_calls=0 | ✅ |
| dense_or_llm_claims=false | ✅ |

**All 14 validation categories passed. 0 critical errors, 0 warnings.**

### Oracle review: fail-closed validator fixes

The initial validator was fail-open on several critical paths. The following
fixes were applied after oracle review:

1. **Public task extra fields → ERROR** (was warning): Any field not in
   `PUBLIC_TASK_FIELDS` in a public task is now a hard error, not a warning.
   This prevents leaking judgement fields through unexpected public fields.

2. **Source path inaccessible → ERROR** (was warning): If a repo's source path
   is not accessible, both the file cache build and the manifest SHA
   verification now emit errors instead of warnings. Inaccessible source means
   the dataset cannot be verified — this must fail, not warn.

3. **Label required-field schema hard validation** (was missing): All 14
   required label fields (`task_id`, `repo_id`, `query_category`, `intent_guess`,
   `risk_tags`, `oracle_type`, `expected_behavior`, `label_quality`,
   `gold_spans`, `hard_distractors`, `must_not_primary`, `why_this_is_hard`,
   `which_strategy_it_targets`, `caveat`) must be present with correct types
   (str/list). Non-caveat string fields must be non-empty.

4. **hard_distractors / must_not_primary path/range validation** (was missing):
   Both `hard_distractors` and `must_not_primary` spans now have their
   paths verified against locked source and their line ranges checked for
   bounds, same as `gold_spans`.

5. **Per-repo coverage iterates ALL repos in repo_lock** (was only repos with
   tasks): If a repo appears in `repo_lock` but has zero tasks, this is now
   a hard failure (0 < 15). Previously, only repos that appeared in task
   data were checked, meaning an empty repo would silently pass.

Post-fix validation: 741 tasks, 741 labels, 9 repos, 25 categories, 0 errors,
0 warnings. All injection tests (extra public field, inaccessible source,
missing label fields, out-of-bounds distractor, empty repo) correctly fail.

### Key findings

1. **Failure-surface dataset generation works**: 741 tasks across 25 categories and 9 repos, with deterministic generation from fixed seed.
2. **Public/private separation is clean**: No private/leak fields appear in public tasks. All judgement fields are in separate private labels.
3. **Category coverage is complete**: All 25 required categories have >= 5 tasks. Some categories (positive_exact_symbol, positive_regex_anchor) have many more due to per-repo symbol extraction.
4. **Metamorphic/stress categories encode expected behavior without source mutation**: dirty_overlay, deleted_file, renamed_file, branch_switch_like are probes for R21/R26 that encode what should happen but do not mutate source in R20.
5. **Static validation catches schema/safety violations**: The validator enforces enum validity, gold_span consistency, overlap constraints, manifest SHA verification, and coverage minimums.
6. **R20 labels are failure-surface oracle/probe labels, not EvidenceCore.**

### Caveats

- **R20 is a failure-surface dataset, NOT promotion evidence.** No runner/scorer matrix exists yet.
- **Labels are mined/weak, not human-verified.** `human_reviewed` is forbidden.
- **Metamorphic/stress categories** (dirty_overlay, deleted_file, renamed_file, branch_switch_like) encode expected behavior for R21/R26 but do NOT mutate source in R20.
- **generated_vendor_trap** may be synthetic if repos lack vendor/generated files.
- **dense_semantic_trap / proper_name_api_config_regression** target semantic false positives around provider/api/config names.
- **No Rust core changes in R20.** Dataset and validator only.
- **R21 will use this dataset** for retrieval failure-surface analysis with actual runner/scorer.

## 2026-06-12 — R21 Auto-Wide Strategy Matrix

### Objective

Run a strategy matrix across 10 retrieval strategies on the R20 auto-wide failure-surface dataset (741 tasks, 9 repos, 25 categories). Evaluate failure surfaces: where strategies fail, what types of queries cause false positives, and which guard patterns reduce negatives without killing recall. NOT promotion evidence.

### Architecture

Strictly separated RUN and SCORE phases (same as R15/R17/R18/R19):

- **Phase 1 (RUN)**: loads only public tasks + repo lock. Creates isolated benchmark roots by allowlist-copying source files under repo_id-specific folders. Runs base methods (regex, bm25, symbol, rrf) via openlocus CLI. Builds composite/guard strategies from base predictions. Never reads labels.
- **Phase 2 (SCORE)**: loads predictions + labels. Computes metrics. Never invokes CLI.

Safety:
- Runner never loads private labels/gold
- Retrieval runs inside isolated temp roots (no fixtures/eval/docs/runs)
- Repo lock content manifest re-verified (normalized hash)
- Citation validation runs BEFORE isolated root cleanup
- Predictions with forbidden prefixes are critical failures
- Composite/guard strategies built from base predictions only; no CLI, no labels
- R20 labels weak/mined; promotion_ready=false, not_promotion_evidence=true

### Implemented strategies (10)

1. regex — `openlocus search regex`
2. bm25 — `openlocus search bm25`
3. symbol — `openlocus search symbol`
4. rrf — `openlocus retrieve` (RRF fusion)
5. bm25_regex — RRF fuse bm25+regex predictions
6. bm25_symbol — RRF fuse bm25+symbol predictions
7. rrf_guarded_by_symbol — RRF only if symbol has evidence
8. rrf_guarded_by_regex — RRF only if regex has evidence
9. rrf_guarded_by_symbol_regex — RRF only if symbol OR regex has evidence
10. query_noise_plus_rrf_agree_min — R17 noise guard + RRF agree (threshold=0.0)

### Unavailable strategies (10)

ast_chunk_bm25, ast_chunk_rrf, graph_basic, graph_rrf, dense_mock, dense_real_if_available, tdb_quiver_if_available, tdb_quiver_plus_rrf, tdb_quiver_guarded_by_symbol_regex, fast_context_if_available — each with documented reason.

### Key findings

1. **All strategies have non-zero no-gold false positives**: Even guards that suppress RRF false positives still return evidence on 16.7-49.5% of no-gold tasks. No strategy eliminates false positives entirely on the auto-wide failure-surface dataset.

2. **BM25/RRF are no-gold-heavy**: BM25 `no_gold_nonempty_rate=0.495`, RRF `0.495`. These methods are recall-strong but precision-weak on no-answer/abstain tasks.

3. **Symbol is precision-best but abstains most**: symbol `no_gold_nonempty_rate=0.167` (lowest among base methods) but `abstain_rate=0.517` (highest). When symbol fires, it's precise; when it doesn't, there's no fallback.

4. **rrf_guarded_by_symbol kills recall**: guard_recall_kill_rate=0.228 — the guard eliminates 23% of RRF's recall hits. The symbol-availability gate is too strict for the auto-wide query distribution.

5. **query_noise_plus_rrf_agree_min is the best R21 guard balance**: `no_gold_nonempty_rate=0.221` (vs RRF 0.495) with `FileRecall@1=0.693` preserved (same as raw RRF).

6. **Regex parse failures**: Tasks with regex metacharacters (e.g., `/models/{model_id}`) fail for regex/rrf methods.

7. **R20 label quality limits conclusions**: 258/741 labels are "weak", 315 "mined_high_confidence", 168 "mined". No human_reviewed labels.

### Metrics (741 tasks, 9 repos)

| Strategy | FileRecall@1 | MRR | no_gold_nonempty_rate | abstain_rate |
|----------|-------------|-----|-----------------------|-------------|
| regex | 0.524 | 0.583 | 0.279 | 0.306 |
| bm25 | 0.388 | 0.455 | 0.495 | 0.366 |
| symbol | 0.575 | 0.585 | 0.167 | 0.517 |
| rrf | 0.693 | 0.753 | 0.495 | 0.182 |
| bm25_regex | 0.612 | 0.671 | 0.495 | 0.182 |
| bm25_symbol | 0.551 | 0.643 | 0.495 | 0.224 |
| rrf_guarded_by_symbol | 0.561 | 0.598 | 0.167 | 0.517 |
| rrf_guarded_by_regex | 0.693 | 0.753 | 0.279 | 0.306 |
| rrf_guarded_by_symbol_regex | 0.693 | 0.753 | 0.279 | 0.306 |
| query_noise_plus_rrf_agree_min | 0.693 | 0.753 | 0.221 | 0.350 |

All 10 strategies: citation_validity=1.0. Composite/guard strategies are built from validated base predictions and also Rust citation-validated before isolated root cleanup.

### Caveats

- **R21 is a failure-discovery matrix, NOT promotion evidence.** promotion_ready=false. not_promotion_evidence=true.
- R20 labels are weak/mined (no human_reviewed); metrics are probes, not evidence.
- No LLM, dense, graph, TDB, or fast-context strategies are included.
- Latency for composite strategies is 0ms (built from existing predictions, no CLI).
- One task (r20aw-0625) fails regex parse due to `{model_id}` metacharacters.
- No Rust core changes in R21. Eval-layer research only.

---

## 2026-06-12 — R22/R27 Failure Attribution

### Objective

Consume R21 artifacts and R20 labels to produce automatic failure clusters and expanded metrics. Do NOT re-run retrieval. Do NOT change Rust core. This is analysis-only score phase.

### Hypothesis

Systematic cross-strategy comparison of R21 predictions against R20 labels will reveal structured failure patterns (inherited false positives, guard recall kills, symbol extraction misses, regex normalization bugs, benchmark oracle suspects) that are not visible from per-strategy metrics alone. Unrun strategy clusters (dense, TDB, graph, AST) should have count=0 with recommended tests, not fabricated data.

### Implementation notes

- **eval/r22_r27_failure_attribution.py**: Analysis-only score-phase script. Loads R21 predictions (JSONL), R21 report (JSON), R20 labels (private JSONL). Never invokes openlocus CLI. Computes 13 failure clusters and expanded per-strategy metrics.
- **13 required cluster keys**: RRF_INHERITED_BM25_FALSE_POSITIVE, GUARD_RECALL_KILL, SYMBOL_EXTRACTION_MISS, REGEX_NORMALIZATION_BUG, AST_SPAN_BOUNDARY_BAD, DENSE_SEMANTIC_TRAP, TDB_QUIVER_SEMANTIC_TRAP, TDB_STALE_REJECTED, TDB_STALE_LEAK, GRAPH_POLLUTION, EVIDENCECORE_REJECTION_EXPECTED, EVIDENCECORE_REJECTION_UNEXPECTED, BENCHMARK_ORACLE_SUSPECT.
- **Each cluster**: count, affected_strategies, unaffected_strategies, representative_examples (<=5), suspected_cause, recommended_next_tests.
- **Unrun clusters**: count=0 with suspected_cause explaining why not measured and recommended_next_tests for future experiments.
- **Path matching**: R20 labels use relative paths (e.g., `src/core.mjs`); R21 predictions use `repo_id/path` format. Matching uses suffix comparison.
- **Expanded metrics**: Per strategy: FileRecall@1/3/5, MRR, SpanF0.5, SpanPrecision, SpanRecall, token_waste, no_gold_nonempty_rate, primary_false_positive_rate, must_not_primary_violation_rate, abstain_rate, weak_candidate_rate, hard_distractor_hit_rate, guard_recall_kill_rate (if available), citation_validity.
- **Bucket regressions**: Flag promotion_blocked_by_bucket_regression when strategy has high no_gold_nonempty (>0.3) or recall gap >0.15 vs RRF in bucket or guard kills >0.1 in bucket.
- **Safety**: promotion_ready=false, not_promotion_evidence=true, source_report_sha, labels_sha, artifact_manifest_sha verified, no labels in run phase, runs artifacts gitignored, no promotion claims, no dense/LLM/QuIVer quality claims.

### R22/R27 failure attribution results

| Cluster | Count | Key finding |
|---------|-------|-------------|
| RRF_INHERITED_BM25_FALSE_POSITIVE | 110 | BM25 and RRF both return false primary evidence on no-gold tasks |
| GUARD_RECALL_KILL | 67 | rrf_guarded_by_symbol kills recall on positive tasks (per_guard: symbol=67, regex=0, symbol_regex=0, query_noise=0) |
| SYMBOL_EXTRACTION_MISS | 91 | Regex/RRF find gold but symbol search misses |
| REGEX_NORMALIZATION_BUG | 1 | Curly braces in route queries cause Rust regex parse errors |
| AST_SPAN_BOUNDARY_BAD | 0 | Not run; AST chunking experimental |
| DENSE_SEMANTIC_TRAP | 0 | Not run; no real embedding provider |
| TDB_QUIVER_SEMANTIC_TRAP | 0 | Not run; TDB behind feature gate |
| TDB_STALE_REJECTED | 0 | Not run; TDB not evaluated |
| TDB_STALE_LEAK | 0 | Not run; TDB not evaluated |
| GRAPH_POLLUTION | 0 | Not run; graph not in R21 matrix |
| EVIDENCECORE_REJECTION_EXPECTED | 0 | metric_unavailable; R21 rate=0.0 for all strategies |
| EVIDENCECORE_REJECTION_UNEXPECTED | 0 | metric_unavailable; no unexpected rejections |
| BENCHMARK_ORACLE_SUSPECT | 62 | Weak labels where strategies strongly disagree with oracle |

Bucket regressions: 206 detected. promotion_blocked_by_bucket_regression: true.

### Key findings

1. **RRF inherits BM25 false positives on 110 no-gold tasks**: The largest actionable cluster. BM25's broad lexical matching produces false primary hits that RRF propagates.
2. **Symbol guard kills recall on 67 positive tasks**: rrf_guarded_by_symbol has the highest per_guard kill count (67). rrf_guarded_by_regex and rrf_guarded_by_symbol_regex have 0 kills because regex always returns evidence on these tasks.
3. **Symbol extraction misses 91 positive tasks**: Heuristic regex-based symbol extraction fails for non-standard patterns where regex/RRF succeed.
4. **62 weak labels are suspect**: On 62/258 weak-quality labels, strategies strongly disagree with the oracle, suggesting label error rather than strategy failure.
5. **Unrun strategy clusters have count=0 by design**: No data is fabricated for dense, TDB, graph, or AST strategies.
6. **206 bucket regressions**: Multiple strategies exceed thresholds for no_gold_nonempty (>0.3), recall gap vs RRF (>0.15), or guard kills (>0.1) in specific query_category/risk_tags/repo/language/expected_behavior buckets.

### Caveats

- R20 labels are weak/mined (no human_reviewed). Failure attribution may reflect label quality rather than strategy quality.
- This is analysis-only; no retrieval was re-run.
- Unrun cluster counts are 0 by construction, not negative results.
- Path matching uses suffix comparison; may produce false matches on very short paths.
- No Rust core changes. Eval-layer research only.
- promotion_ready=false. not_promotion_evidence=true.

## 2026-06-12 — R23 Guard Parameter Sweep

### Objective

Eval-layer guard parameter sweep consuming R21 artifacts and R20 labels. Sweep over 8 guard parameter dimensions (query_noise_threshold, rrf_score_threshold, regex_agreement_required, symbol_agreement_required, regex_or_symbol_agreement_required, top1_top2_gap_threshold, identifier_density_threshold, candidate_channel_count_threshold) plus 15 combined strategies. Does NOT re-run retrieval, does NOT change Rust core.

### Hypothesis

Systematic parameter sweep across guard dimensions will reveal Pareto-optimal operating points for the recall-vs-false-positive trade-off. Combined strategies (query noise + agreement + score threshold) should outperform single-dimension guards.

### Implementation notes

- **eval/r23_guard_sweep.py**: Analysis-only score phase. Loads R21 predictions (rrf, regex, symbol) + R20 labels + R21 report. Never invokes openlocus CLI. Labels only in score phase.
- **Guard semantics**: Based on raw RRF evidence; if guard condition fails then abstain. Agreement based on regex/symbol predictions evidence presence. Score threshold based on RRF top score. Gap threshold based on top1-top2 score gap. Identifier density from query parsing. Candidate channel count from top evidence channels union estimate.
- **51 strategies**: 7 query_noise_threshold values, 10 rrf_score_threshold values, 3 boolean agreement strategies, 7 top1_top2_gap_threshold values, 4 identifier_density_threshold values, 5 candidate_channel_count_threshold values, plus 15 combined strategies.
- **Output**: runs/r23-guard-sweep.json with strategies, curves (risk_coverage, recall_vs_negative, recall_vs_false_primary, precision_vs_abstain), bucket_summary, observations.
- **Bucket regression**: recall gap vs RRF >0.15, no_gold_nonempty_rate >0.3, primary_false_positive_rate >0.3, guard_recall_kill_rate >0.1.
- **Safety**: promotion_ready=false, not_promotion_evidence=true, no promotion claims, no dense/LLM/QuIVer claims, labels only in score phase, R21 artifact manifest verified fail-closed for every recorded path/sha256/byte-count/jsonl-line-count.

### R23 guard sweep results (51 strategies, 741 tasks)

| Strategy | FileRecall@1 | no_gold_nonempty | pfp | abstain | guard_kill | blocked |
|---|---|---|---|---|---|---|
| rrf_raw (baseline) | 0.693 | 0.495 | 0.495 | 0.182 | N/A | false |
| query_noise_threshold_1 | 0.693 | 0.437 | 0.437 | 0.225 | 0.000 | true |
| regex_or_symbol_agreement | 0.693 | 0.279 | 0.279 | 0.306 | 0.000 | true |
| query_noise_1+regex_or_symbol_agree | 0.693 | 0.221 | 0.221 | 0.350 | 0.000 | true |
| symbol_agreement | 0.561 | 0.167 | 0.167 | 0.517 | 0.228 | true |
| rrf_score_threshold_0.02 | 0.602 | 0.198 | 0.198 | 0.456 | 0.151 | true |
| rrf_score_threshold_0.04 | 0.329 | 0.018 | 0.018 | 0.804 | 0.571 | true |
| top1_top2_gap_0.005 | 0.372 | 0.036 | 0.036 | 0.746 | 0.528 | true |
| ident_1+regex_or_symbol_agree | 0.610 | 0.207 | 0.207 | 0.470 | 0.120 | true |

### Key findings

1. **All 51 strategies have bucket regressions**: Every guard strategy has at least one bucket where recall gap, no_gold_nonempty_rate, primary_false_positive_rate, or guard_recall_kill_rate exceeds the regression threshold.
2. **Query noise guard is effective but insufficient alone**: query_noise_threshold_1 preserves FileRecall@1 (0.693) with zero guard_recall_kill, but no_gold_nonempty_rate remains at 0.437.
3. **Agreement guards reduce false positives without recall cost**: regex_or_symbol_agreement_required reduces no_gold_nonempty_rate from 0.495 to 0.279 with zero guard_recall_kill.
4. **Combined query_noise + agreement is the best R23 guard balance**: query_noise_1_plus_regex_or_symbol_agree achieves no_gold_nonempty_rate 0.221 with FileRecall@1 0.693 and zero guard_recall_kill.
5. **RRF score threshold above 0.02 causes sharp recall cliff**: Most RRF top scores are concentrated near 0.03-0.06; thresholds above 0.02 reject substantial recall.
6. **top1_top2_gap threshold kills too much recall**: Gap thresholds even at 0.005 cause >50% guard_recall_kill_rate.
7. **Symbol agreement alone kills 22.8% recall**: Confirms R22 finding that rrf_guarded_by_symbol is too aggressive.
8. **No strategy eliminates no_gold_nonempty_rate to zero without unacceptable recall cost**: Strategies achieving near-zero false positives do so by abstaining on >99% of queries.

### Safety

- promotion_ready=false, not_promotion_evidence=true always
- No promotion claims, no dense/LLM/QuIVer quality claims
- Labels only in score phase; never used for routing
- R21 artifacts manifest verified fail-closed for path/sha256/byte-count/jsonl-line-count
- Analysis-only no CLI
- R20 labels weak/mined; not promotion evidence

### Caveats

- R20 labels are weak/mined (258 weak, 315 mined_high_confidence, 168 mined); not promotion evidence
- Guard parameter sweep is analysis-only; no Rust core changes
- Bucket regression thresholds (0.15 recall gap, 0.3 no_gold, 0.3 pfp, 0.1 kill) are heuristic
- All strategies blocked by bucket regression; expected given R20 label diversity
- Combined strategies are observations, not promotions
- query_noise_score is deterministic/heuristic; not learned from data

---

## 2026-06-12 — R24 QuIVer/TDB/Dense Probe

### Objective

Probe QuIVer/TDB/dense availability and run dense_mock as a candidate-channel safety/quality smoke on the R20 auto-wide failure-surface dataset. NOT a QuIVer bakeoff. QuIVer is not implemented and must be reported unavailable; no fabricated QuIVer quality data is produced. TDB is a feature-gated metadata/chunk store, not an ANN/QuIVer backend. Dense real is unavailable; dense_mock is candidate-channel safety/quality-smoke (not semantic quality).

### Core principles

1. QuIVer is not implemented -> report unavailable, not run. No numeric 0 as quality result.
2. TDB is NOT ANN/QuIVer -> feature-gated metadata/chunk store. Probe placeholder only.
3. dense_real unavailable; dense_mock is candidate-channel safety/quality-smoke (not semantic quality).

### Implementation notes

- **eval/r24_quiver_tdb_probe.py**: Strictly separated RUN and SCORE phases.
  - Phase 1 (RUN): Availability checks + dense mock candidate-channel probe. Loads only public tasks + repo lock. Creates isolated benchmark roots by allowlist-copying source files. Runs dense build/search via openlocus CLI. Never reads labels.
  - Phase 2 (SCORE): Loads predictions + labels. Computes metrics. Never invokes openlocus CLI.
- **Availability checks** (fail-closed evidence):
  - QuIVer implementation scan: no files/deps/symbols for QuIVer except eval/docs placeholders. Report unavailable, not run.
  - TDB default status via `openlocus store status tdb --json`: available=false, success=false. No retrieval quality claimed.
  - Dense provider status: mock and disabled available; real provider unavailable.
- **Dense mock candidate-channel probe**:
  - Uses R20 repo lock source paths. Builds isolated temp roots by allowlist-copying source files under repo_id/ and .openlocus/policy.toml.
  - For each repo, runs `openlocus dense build --provider mock --experimental --json` once.
  - For R20 tasks, runs `openlocus dense search --provider mock --limit 10 --json <query>` in that repo isolated root.
  - Preserves `.openlocus/embeddings` and `.openlocus/audit` between build/search; only transient traces/context are cleaned during the run.
  - Produces R24-owned artifacts in runs/: dense_mock predictions/evidence/rejections/trace plus dense_mock_plus_rrf predictions/evidence/rejections/trace, and manifest json. Does NOT commit runs.
  - Validates dense evidence through `openlocus citations validate --json` before cleanup. citation_validity must be 1.0 if evidence exists.
  - Scans .openlocus/embeddings and audit for canary tokens and query leaks. A non-secret dense path canary runs after dense build and fails closed if it cannot traverse the vector store and return evidence for non-empty stores. `success=false` task searches are recorded as candidate rejections, not process failures, when CLI exits cleanly with a block/no-hit reason.
  - Scores dense_mock using R20 labels: FileRecall@1/3/5, MRR, SpanF0.5, SpanPrecision, SpanRecall, token_waste, no_gold_nonempty_rate, primary_false_positive_rate, must_not_primary_violation_rate, abstain_rate, weak_candidate_rate, hard_distractor_hit_rate. Bucket metrics for query_category, risk_tags, expected_behavior, repo_id, language. Dense semantic trap/proper_name/config/API buckets separately summarized.
- **Optional fusion**: dense_mock_plus_rrf by RRF-fusing dense_mock with R21 rrf predictions, only if dense evidence citation-valid and no synthetic invalid channels. Score separately and report dense candidate contribution.
- **TDB stale/materialization smoke**: Default build TDB is unavailable placeholder. `store status tdb` confirms. Does not enable feature. Reports tdb_feature_probe_not_run with reason. tdb_stale_leak_count is not_applicable.
- **QuIVer diagnostic fields**: R24.1 fields (BQ_overlap, quiver recall, etc.) set status unavailable/not_measured with reason quiver_not_implemented and next_required_tests. Does NOT output numeric 0 as quality result.

### Safety gates

- Labels not loaded until after dense run complete
- Citation validator pass for dense artifacts
- Artifact manifest path/sha/bytes/lines verified
- Dense mock must produce non-empty materialized candidates; otherwise R24 fails as a vacuous candidate-channel probe
- Non-secret dense path canary must return evidence for non-empty dense stores; raw canary/query text must not appear in stdout/stderr or artifacts
- Canary/no label leakage: public tasks only in run phase; labels only score
- No promotion/dense real/QuIVer quality claims
- Runs artifacts gitignored
- Private field scan: no gold_spans/expected_behavior/query_category in R24 artifacts
- Canary token scan: no canary tokens in R24 artifacts

### Key findings

1. **QuIVer is not implemented**: Scan of all Rust crates, Cargo.toml files, and source code confirms no QuIVer implementation exists outside eval/docs placeholders. quiver_implemented=false.
2. **TDB is a placeholder in default build**: `openlocus store status tdb --json` returns available=false, success=false, mode=placeholder. TDB is a feature-gated metadata/chunk store, not an ANN/QuIVer backend.
3. **Dense mock is available as a candidate-channel safety smoke**: mock and disabled providers are available; real provider is unavailable. Dense mock uses deterministic blake3-based vectors that do NOT capture semantic similarity.
4. **Dense mock produces real, materialized candidates but mostly finds failure surfaces**: full run produced 5,264 dense_mock candidates, all Rust citation-valid. Quality is poor as expected for non-semantic mock vectors: FileRecall@1 0.024, MRR 0.073, SpanF0.5 ~0.000, token_waste 0.850, primary_false_positive_rate 0.878.
5. **Dense CLI rejections are now explicit**: full run recorded 99 candidate rejections (`candidate_rejection_rate` 0.134), mostly expected block/no-hit outcomes surfaced explicitly rather than hidden as empty successes.
6. **Canary hardening is non-vacuous**: 8 non-empty dense stores checked, 1 empty store skipped, path canary returned 66 evidence items, query canaries returned 132 evidence items, and raw canary/query leakage count was 0.
7. **Dense mock + RRF fusion is a noise-amplification probe, not a recommendation**: full run confirms dense contribution (642 tasks with dense candidates; 5,264 dense spans retained in fusion), but fusion increases false-primary/noise: FileRecall@1 0.134, MRR 0.451, token_waste 0.928, primary_false_positive_rate 0.923, hard_distractor_hit_rate 0.215.
8. **Citation validity is enforced**: dense_mock evidence and dense_mock_plus_rrf evidence both pass Rust citation validation (hash+range+path) before cleanup. dense_mock citation_total=5,264; fusion citation_total=13,149; invalid=0.
9. **QuIVer diagnostic fields are properly unavailable**: All R24.1 fields report unavailable/not_measured with reason quiver_not_implemented and explicit next_required_tests. No numeric 0 is output as a quality result.

### Caveats

- This is an availability + mock dense candidate-channel probe, NOT a QuIVer bakeoff
- QuIVer remains future work
- Dense mock scores are NOT semantic quality metrics
- TDB is a metadata/chunk store, not an ANN/QuIVer backend
- Dense real provider is unavailable
- R20 labels are weak/mined; not promotion evidence
- promotion_ready=false always
- No Rust core changes

---

## 2026-06-12 — R25 Graph+Dense Ablation

### Objective

Eval-layer ablation study measuring the contribution of graph_basic and dense_mock strategies — individually and in combination with R21 RRF — on the R20 auto-wide failure-surface dataset (741 tasks, 9 repos, 25 categories). Does NOT change Rust core or EvidenceCore.

### Core principles

1. dense_mock is non-semantic (deterministic blake3 vectors do NOT capture semantic similarity)
2. QuIVer is not implemented (unavailable/not_measured; no numeric zero as quality result)
3. TDB is a feature-gated placeholder (not applicable for this ablation)
4. R20 labels are weak/mined (258 weak, 315 mined_high_confidence, 168 mined; no human_reviewed)

### Implementation notes

- **eval/r25_graph_dense_ablation.py**: Strictly separated RUN and SCORE phases.
  - Phase 1 (RUN): Loads only public tasks + repo lock + R21 rrf predictions. Creates isolated benchmark roots by allowlist-copying source files. Runs graph_basic (derive top path via symbol→regex fallback, then impact) and dense_mock (build + search) via openlocus CLI in isolated roots. Builds composite strategies (rrf_plus_graph, rrf_plus_dense_mock, rrf_plus_dense_mock_plus_graph) by RRF-fusing base predictions. Never reads labels.
  - Phase 2 (SCORE): Loads all strategy predictions + R20 labels. Computes metrics. Never invokes openlocus CLI.
- **6 strategies**: no_graph (R21 rrf baseline), graph_basic, rrf_plus_graph, dense_mock, rrf_plus_dense_mock, rrf_plus_dense_mock_plus_graph.
- **New ablation metrics**: added_gold_span, added_false_span, graph_pollution_ratio, graph_token_waste_delta, dense_added_gold_span, dense_added_false_span, combined_added_gold_span, combined_added_false_span.
- **Rule**: If added_false_span > added_gold_span, default expansion is blocked.
- **QuIVer/TDB**: Explicit unavailable/not_measured; no numeric zero quality output.
- **Safety gates**: Labels not loaded until after run; R21 artifact manifest path/sha/bytes/jsonl line count verified fail-closed before using RRF baseline; citation validator hash/range/path for graph/dense/composite strategies (no_graph inherits R21 validation after manifest verification); artifact manifest verified; scans for private fields/canary tokens; promotion_ready=false, not_promotion_evidence=true, remote_calls=0.
- **Bug fix**: `_extract_evidence_from_search_result()` helper added because search commands return JSON array (wrapped as `result["items"]` by `run_cli`), while impact/retrieve return `result["evidence"]`.
- **Bug fix**: `INIMPLEMENTED_STRATEGIES` → `IMPLEMENTED_STRATEGIES` typo.

### R25 ablation results (741 tasks, 9 repos)

#### Retrieval quality

| Metric | no_graph | graph_basic | rrf_plus_graph | dense_mock | rrf_plus_dense_mock | rrf_plus_dense_mock_plus_graph |
|--------|---------:|------------:|---------------:|-----------:|--------------------:|-------------------------------:|
| FileRecall@1 | 0.693 | 0.003 | 0.497 | 0.024 | 0.134 | 0.112 |
| FileRecall@3 | 0.791 | 0.013 | 0.762 | 0.110 | 0.719 | 0.698 |
| FileRecall@5 | 0.829 | 0.013 | 0.791 | 0.152 | 0.781 | 0.767 |
| MRR | 0.753 | 0.008 | 0.641 | 0.073 | 0.451 | 0.405 |
| SpanF0.5 | 0.185 | 0.000 | 0.172 | 0.000 | 0.077 | 0.068 |
| token_waste | 0.779 | 0.310 | 0.800 | 0.850 | 0.928 | 0.938 |
| no_gold_nonempty | 0.495 | 0.072 | 0.495 | 0.878 | 0.923 | 0.923 |
| abstain_rate | 0.182 | 0.785 | 0.182 | 0.134 | 0.034 | 0.034 |
| citation_validity | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |

#### Ablation metrics

| Metric | graph | dense | rrf_plus_graph | rrf_plus_dense | combined |
|--------|------:|------:|---------------:|---------------:|---------:|
| added_gold_span | 0 | 2 | 0 | 2 | 2 |
| added_false_span | 435 | 20,273 | 435 | 20,273 | 20,695 |
| default_expansion_blocked | true | true | true | true | true |

#### Graph-specific metrics

| Metric | Value |
|--------|-------|
| Path derivation: symbol | 358/741 (48.3%) |
| Path derivation: regex | 156/741 (21.1%) |
| Path derivation: none | 2222/2241 (30.6%) |
| Impact failures (no top path) | 227 |
| Impact no evidence (top path found but impact empty) | 355 |
| graph_pollution_ratio | 0.000 |
| graph_token_waste_delta | -0.469 |

### Key findings

1. **graph_basic produces net-negative contribution**: Added 0 gold spans and 435 false spans. Default expansion blocked.
2. **dense_mock is net-negative as expected**: Added 2 gold spans and 20,273 false spans. Non-semantic mock vectors produce massive noise. Default expansion blocked.
3. **rrf_plus_graph dilutes RRF quality**: FileRecall@1 drops from 0.693 to 0.497 because graph evidence competes with RRF evidence in the RRF score calculation.
4. **rrf_plus_dense_mock also dilutes RRF quality**: FileRecall@1 drops from 0.693 to 0.134. Dense mock evidence floods the RRF pool with irrelevant candidates.
5. **Graph pollution is zero**: No graph evidence was returned on forbidden paths. graph_pollution_ratio=0.000.
6. **Graph has low token waste when it fires**: graph_basic token_waste=0.310 vs no_graph=0.779, but this is because graph_basic mostly abstains (0.785 abstain rate).
7. **Citation validity remains 1.0**: graph_basic, dense_mock, and composite strategies are revalidated in R25 with Rust hash/range/path citation validation. no_graph inherits R21 validation after R25 verifies the R21 artifact manifest before baseline use.
8. **QuIVer/TDB are honestly reported as unavailable/not_measured**: No numeric zero quality results for QuIVer. TDB is not applicable for this ablation.
9. **Canary scope is source-leak only**: R25 uses a regex canary over isolated copied source before dense build. A seeded self-test proves regex hits are detectable, then 36 leakage checks produce 0 hits and 0 failures. It does not claim a dense-path canary; R24 owns dense-path canary hardening.

### Safety

- All safety checks passed
- Labels not loaded until after run complete (strict RUN/SCORE phase separation)
- Citation validator hash/range/path for every strategy with evidence
- Artifact manifest path/sha/bytes/line count verified
- Artifact scans for private fields: 0 issues
- Artifact scans for canary tokens: 0 issues
- promotion_ready=false, not_promotion_evidence=true, remote_calls=0
- R20 labels weak/mined caveat recorded

### Caveats

- R20 labels are weak/mined (no human_reviewed); not promotion evidence
- dense_mock is non-semantic; no real embedding quality claim
- Graph impact is depth=1 only; deeper impact not tested
- Graph path derivation uses symbol→regex fallback; not LSP/SCIP
- Impact returns empty evidence for 355/514 tasks with top path (no graph edges found)
- graph_basic abstains on 78.5% of tasks (no path or no impact)
- Combined strategies show additive noise: graph + dense false spans accumulate
- Runs artifacts are gitignored; report not committed
- No Rust core changes

---

## 2026-06-12 — R26 Auto-Stress-1000

### Objective

Generate a large-scale stress dataset with >= 1000 cases targeting specific failure categories, using the same external repo set as R20 and deriving some queries from existing R20 tasks/labels where useful. Data generation/static validation only; no Rust core changes, no retrieval strategy promotion.

### Hypothesis

A targeted stress dataset with precise category composition will maximize failure discovery across retrieval strategies. Specifically: negative/abstain-heavy cases will expose hallucination and false-positive vulnerabilities; hard-distractor and same-name cases will test precision under confusion; semantic-trap and dense_quiver cases will test dense/infrastructure naming confusion; stale-index cases will test freshness detection.

### Implementation notes

- Created `eval/r26_generate_auto_stress.py` — generates 1100 stress cases from the same external repo set as R20 and some R20 derivative labels using deterministic seed 42.
- Created `eval/r26_validate_auto_stress.py` — fail-closed static validator with 19 checks.
- Created `fixtures/r26_auto_stress/` with tasks, labels, manifest, repos.lock, safety_checks, summary.
- Public tasks contain only: test_id, repo_id, query, public_version, source. No category/risk/judgement fields leak.
- Private labels carry all judgement fields: source_category, risk_public, intent_guess, risk_tags, oracle_type, expected_behavior, gold_spans, hard_distractors, must_not_primary, why_this_is_hard, which_strategy_it_targets.
- 10 stress categories with exact target composition: negative_nonexistent 150, ambiguous_vague 150, hard_distractor 200, semantic_trap 150, same_name_symbol 100, frontend_backend_confusion 75, test_source_confusion 75, generated_vendor_trap 50, stale_index_like 50, dense_quiver_specific_trap 100.
- Uses the same external repo set as R20 and derives some queries from existing R20 tasks/labels where useful (hard_distractor, same_name_symbol, frontend_backend_confusion, test_source_confusion, generated_vendor_trap, stale_index_like categories use R20 label queries as seeds).
- No canary tokens anywhere.
- Deterministic seed 42.

### Validation results

- 19/19 fail-closed static validation checks passed, including exact category target counts, public/private schema separation, SHA-256 artifact checks, and repo content manifest SHA lock recomputation
- 0 critical errors
- 0 warnings
- Tasks: 1100, Labels: 1100, Repos: 9, Categories: 10
- All categories meet minimum count (10)
- All repos meet minimum count (50)
- No canary tokens found
- No private fields in public tasks
- Label-public task query/repo consistency verified
- Span path/range validity verified against locked source files
- Deterministic SHA256 checksums verified
- dataset_manifest flags correct

### Caveats

- **R26 is weak/mined/deterministic stress, NOT promotion evidence.** It is designed to maximize failure discovery, not demonstrate quality.
- **Labels are mined/weak/deterministic, not human-verified.** `human_reviewed` is forbidden.
- **Negative/abstain cases dominate** (590/1100 abstain + 70/1100 no_primary = 60%). This is intentional.
- **Derivation from R20 is shallow.** R26 reuses R20 repo sources and some R20 label queries as seeds, but does NOT inherit R20 gold spans or oracle judgments.
- **semantic_trap and dense_quiver_specific_trap categories contain queries about ML/AI/vector infrastructure that these repos do NOT implement.** These test false-positive resistance, not retrieval quality.
- **stale_index_like cases are metamorphic probes.** They reference code that may not exist in the current snapshot.
- **No runner/scorer matrix exists for R26.** R26 is a static dataset with a static validator.
- **R26 labels are stress failure-surface labels, not EvidenceCore.**
- No Rust core changes

## 2026-06-12 — R28 Promotion Candidate Report

### Objective

Synthesize R21/R23/R24/R25/R26 reports over the R20/R26 failure-surface datasets into a conservative `promotion_candidate_report` that answers whether defaults should change, whether guard/dense/graph/QuIVer are promotion-ready, and which evidence gaps block promotion.

### Implementation

- Added `eval/r28_promotion_candidate_report.py`.
- Reads already validated artifacts only: R21 auto-wide strategy matrix, R23 guard sweep, R24 dense/QuIVer/TDB probe, R25 graph+dense ablation, and R26 auto-stress static validation.
- Produces `artifacts/r28_promotion_candidate/r28-promotion-candidate-report.json` and `docs/zh/r28-promotion-candidate-report.md`.
- No retrieval CLI invocation.
- No core changes.
- remote_calls=0.

### Findings

- `promotion_ready=false`.
- Current default should not change.
- `best_recall_channel=rrf`, but RRF still has high false-primary/no-gold risk on R20 auto-wide.
- `best_precision_anchor=symbol`.
- `query_noise_plus_rrf_agree_min` is promising but not stable enough: R21 shows useful risk reduction without recall kill, but R23 finds bucket regressions for all 51 swept strategies and R26 has not been run through a retrieval runner/scorer matrix yet.
- QuIVer/TDB have no independent quality evidence. QuIVer is not implemented; TDB is not an ANN/search backend in default build.
- Dense mock is safety/noise probe only, not semantic quality. R24/R25 show high false-primary/noise.
- Graph default expansion is blocked: R25 graph added 0 gold spans and 435 false spans.
- Dense default expansion is blocked: R25 dense added 2 gold spans and 20,273 false spans.

### Blocking evidence gaps

- R26 auto-stress has static validation only; no retrieval runner/scorer matrix yet. (Resolved by R29.)
- R20 labels are weak/mined and R26 oracle types are deterministic/metamorphic/mined/stress; neither is human-verified promotion evidence.
- R23 guard sweep shows bucket regressions across all swept strategies.
- QuIVer is unavailable, so there is no BQ/ANN compatibility or quality evidence.
- Dense real provider is unavailable.
- Graph/dense expansions are net-negative in R25.

### Recommendation

Keep all new channels as candidate/supporting/research-only. Next work should run R26 through the strategy matrix and add human-verified labels for high-risk buckets before any default policy change.

## 2026-06-12 — R29 R26 Auto-Stress Strategy Matrix

### Objective

Run R26's 1100 public stress tasks through a 16-strategy matrix to maximize failure discovery, NOT promotion. Must be fresh run; no skip-run support.

### Current hypothesis

A comprehensive strategy matrix across base (regex/bm25/symbol/rrf), composite/guard, and R24/R25-style (dense_mock, graph_basic, composites) strategies on R26's stress dataset will reveal systematic failure surfaces. R26's 10 stress categories (negative_nonexistent, ambiguous_vague, hard_distractor, semantic_trap, same_name_symbol, frontend_backend_confusion, test_source_confusion, generated_vendor_trap, stale_index_like, dense_quiver_specific_trap) are specifically designed to expose retrieval failures.

### Implementation notes

- **eval/r29_r26_stress_matrix.py**: Strictly separated RUN and SCORE phases.
  - RUN phase: loads only public tasks + repo lock + R26 safety/manifest. Creates isolated benchmark roots by allowlist-copying source files. Runs base methods via openlocus CLI. Builds composite/guard strategies from base predictions. Runs dense_mock build/search and graph_basic. Never reads labels. Validates all citations while isolated roots exist. Writes all run artifacts before loading labels.
  - SCORE phase: loads predictions + labels. Computes metrics, failure clusters, span contributions, bucket regressions. Never invokes CLI.
- **16 implemented strategies**: regex, bm25, symbol, rrf, bm25_regex, bm25_symbol, rrf_guarded_by_symbol, rrf_guarded_by_regex, rrf_guarded_by_symbol_regex, query_noise_plus_rrf_agree_min, dense_mock, dense_mock_plus_rrf, graph_basic, rrf_plus_graph, rrf_plus_dense_mock, rrf_plus_dense_mock_plus_graph.
- **5 unavailable strategies**: dense_real_if_available (not_configured_or_policy_disabled), tdb_quiver_if_available (quiver_not_implemented), tdb_quiver_plus_rrf (quiver_not_implemented), tdb_quiver_guarded_by_symbol_regex (quiver_not_implemented), fast_context_if_available (fast_context_is_4turn_orchestration_scaffold_not_standalone_matrix_strategy). No fake numeric quality.
- **Citation validation**: Every implemented strategy's evidence validated via `openlocus citations validate` while isolated roots exist. Composite/fusion evidence revalidated. No synthetic EvidenceCore channels (no "RRF" channel added). If any citation invalid, exit non-zero.
- **Isolation**: Allowlisted source files copied from R26 repos.lock into isolated temp roots. No docs/eval/fixtures/runs/.git. Symlinks disallowed. `.openlocus/policy.toml` in isolated root. Runtime traces cleaned between queries; dense embeddings preserved after build.
- **R26 provenance validation**: run phase validates safety_checks.passed=true, task_count=1100, not_promotion_evidence=true, core_changes=false, remote_calls=0, dense_or_llm_claims=false, and tasks SHA. Declared label count is recorded but label file content/SHA validation is deferred to score phase after run artifacts/citations/manifest are written.
- **14 required failure clusters**: RRF_INHERITED_BM25_FALSE_POSITIVE, GUARD_RECALL_KILL, SYMBOL_EXTRACTION_MISS, REGEX_NORMALIZATION_BUG, DENSE_MOCK_NOISE, DENSE_SEMANTIC_TRAP_FALSE_POSITIVE, GRAPH_NEIGHBOR_FALSE_POSITIVE, GRAPH_ADDS_NO_GOLD, HARD_DISTRACTOR_CONFUSION, NEGATIVE_NONEXISTENT_FALSE_PRIMARY, STALE_INDEX_LIKE_FALSE_PRIMARY, TEST_SOURCE_CONFUSION, FRONTEND_BACKEND_CONFUSION, BENCHMARK_ORACLE_SUSPECT.
- **Span contribution analysis**: graph/dense/composites vs fresh RRF baseline; added_gold_span, added_false_span, tasks_with_additions, default_expansion_blocked.
- **Bucket regressions**: per source_category, expected_behavior, oracle_type, repo_id, risk_tags. Regression types: recall drop, false-primary increase, no-gold-nonempty increase, must-not-primary increase, abstain spike on primary_evidence.
- **Private field scan**: prediction/evidence/rejection/trace JSONL must not include: source_category, risk_public, intent_guess, risk_tags, oracle_type, expected_behavior, gold_spans, hard_distractors, must_not_primary, why_this_is_hard, which_strategy_it_targets.
- **Report fields**: schema_version="r29-v1", promotion_ready=false, not_promotion_evidence=true, core_changes=false, remote_calls=0, labels_loaded_after_run=true, run_phase_public_only=true, score_phase_labels_only=true, r26_source_artifacts_validated=true, r26_label_artifacts_validated_after_run=true, citation_validity_all_strategies=1.0, quiver_implemented=false, dense_mock_is_semantic_quality=false, artifact_manifest_verified=true.
- **No skip-run**: Fresh run always required.

### Full-run results

- Full R29 completed on 1100 R26 tasks across 16 implemented strategies.
- Safety gates: ALL PASSED. Artifact manifest verified (64 files). Artifact private-field scan and canary scan clean. Citation validity is 1.0 for every implemented strategy.
- RRF remains the best recall channel but unsafe alone: FileRecall@1=0.803, FileRecall@5=0.923, MRR=0.858, primary_false_positive_rate=0.453.
- `query_noise_plus_rrf_agree_min` reduces false-primary while preserving RRF recall on R26: FileRecall@1=0.803, FileRecall@5=0.923, primary_false_positive_rate=0.106, guard_recall_kill_rate=0.003. This is still not promotion evidence because R23 showed bucket regressions and R26 labels are not human-verified.
- Symbol remains the precision anchor: SpanF0.5=0.291, primary_false_positive_rate=0.080, token_waste=0.247, abstain_rate=0.671.
- Dense mock is a high-noise failure probe: dense_mock primary_false_positive_rate=0.874; dense_mock_plus_rrf and rrf_plus_dense_mock primary_false_positive_rate=0.906.
- Graph remains default-blocked: graph_basic added_gold_span=0, added_false_span=437.
- All graph/dense expansion variants are blocked by `added_false_span > added_gold_span`.
- Failure clusters: DENSE_MOCK_NOISE=577, RRF_INHERITED_BM25_FALSE_POSITIVE=299, DENSE_SEMANTIC_TRAP_FALSE_POSITIVE=219, GRAPH_ADDS_NO_GOLD=90, SYMBOL_EXTRACTION_MISS=63, GUARD_RECALL_KILL=62, FRONTEND_BACKEND_CONFUSION=57, HARD_DISTRACTOR_CONFUSION=43, NEGATIVE_NONEXISTENT_FALSE_PRIMARY=41, TEST_SOURCE_CONFUSION=41, REGEX_NORMALIZATION_BUG=36, GRAPH_NEIGHBOR_FALSE_POSITIVE=26.
- Bucket regressions total=448 across bm25, bm25_regex, bm25_symbol, dense_mock, dense_mock_plus_rrf, graph_basic, regex, rrf_guarded_by_symbol, rrf_plus_dense_mock, rrf_plus_dense_mock_plus_graph, symbol.

### Caveats

- No promotion, no default change, failure-surface only.
- R26 labels are weak/mined/deterministic/stress; not human-verified.
- dense_mock is candidate-channel safety smoke, not semantic quality.
- graph_basic is deterministic depth=1, not precise call/type graph.
- QuIVer/TDB unavailable; no fabricated numeric quality.
- Fresh run only; no skip-run support.

## 2026-06-18 — B10B Runtime-Shadow Replay（仅 ambiguous 分支）

### Objective

B10B 是 B10 冻结 `balanced_policy_v1_benchmark_routed` 之后的下一步。它通过仅
action-agreement replay 验证一个预先声明的、仅依赖 runtime feature 的 shadow predicate，
该 predicate 在同批记录上近似冻结 benchmark-routed spec 的 ambiguous 分支。没有新的模型
runs、没有新的 default policy、没有 policy search、没有调参、没有 promotion。目标是测试
仅靠 runtime `route_features`（`query_noise`、`candidate_support_exists`、
`local_anchor`、`rrf_backed_by_anchor`）能否 shadow 当前由 benchmark 公开标签
（`task_bucket`/`task_risk_tags`）驱动的 ambiguous 分支。

### Implementation notes

- 并行侦察：@explorer 映射了 16-key `route_features` 空间，识别出 4 个干净的 shadow
  features（`query_noise`、`candidate_support_exists`、`local_anchor`、
  `rrf_backed_by_anchor`）；@librarian 确认方法论为 “offline shadow-policy conformance
  replay”（不是完整 OPE —— 无 propensities、无 counterfactual 加权）；@oracle 战略评审在原
  实现中发现了 4 个 blocker。
- @fixer 强化了 evaluator（1163 → 约 1820 行）：在 leakage mutation 测试中加入
  `outcome_metrics`、predeclared acceptance gates（10 个 gate）、分层 agreement metrics
  （`target_weak_only_recall`、`target_use_p25_specificity`、`shadow_weak_only_precision`、
  `label_driven_ambiguous_recall_qn0`、`query_noise_only_recall_qn1`）、silent-failure
  检查（`all_shadow_ambiguous`、`all_shadow_non_ambiguous`、`base_rate_only_suspected`、
  `no_silent_failure`）、Cohen's kappa（直接实现，不依赖 numpy/sklearn）、不一致子集上的
  outcome-equivalence 审计（4 个分区）、verdict 框架
  （`runtime_shadow_ambiguous_supported` + `support_claim` + `support_claim_reason`）、
  `replay_source` 参数（`synthetic_fixture` vs `ci_ephemeral_records`），以及用于 CI 集成
  的 CLI `--records` 选项。
- @oracle 最终评审发现 1 个遗留问题：denominator 被当作 escape clause（OR）而非 hard gate
  （AND）处理。@fixer 已修复：`label_driven_ambiguous_min_denominator=10` 现为 HARD gate；
  denominator 不足时 verdict 为 `False`，
  `support_claim="empirical_replay_support_pending"`，
  `support_claim_reason="insufficient_label_driven_denominator"`。
- 最终 spec sha256：
  `c201eb709dc0112c2bb91db33917c6d20ea48582924821a2bda7950709e754ba`。
- 10 项 self-test 检查全部 PASS。

### Findings

- B10B 现已是 mechanics-validated scaffold：evaluator、leakage guard、verdict 框架，以及
  全部 10 个 predeclared gate 均工作正确。
- 在 synthetic fixture 上的当前 verdict：
  `runtime_shadow_ambiguous_supported=false`、
  `support_claim="mechanics_only_synthetic_fixture"`、
  `support_claim_reason="synthetic_fixture_only"`、
  `replay_source="synthetic_fixture"`。
- 磁盘上不存在真实 CI ephemeral 记录（P21 ephemeral 记录写入 `$RUNNER_TEMP` 且不提交；
  P21 public JSON 在 B2 隐私修复后仅聚合）。
- 因此 B10B 暂时无法做出任何 empirical support claim。empirical validation 需要或为
  CI 集成（在清理前对 `$RUNNER_TEMP/p25-policy-records-ephemeral-v1/*.json` 运行
  `--records`），或为 B11 prospective runs。

### Caveats

- B10B 仅是 ambiguous 分支 runtime-shadow；**不**证明 runtime-clean balanced policy。
- 默认 `use_p25_action` 仍委托给 P25 benchmark-routed 行为。
- 无 live LLM 调用（`runtime_calls_by_replay=0`、`model_calls_by_replay=0`）。
- 无 default 变更、无 promotion、无 `EvidenceCore` 语义变更。
- B11 应被 framing 为 “exploratory prospective stress test”，**不是** “supported
  validation”，直到 B10B 在真实 CI 记录上运行并通过 predeclared gate。
- shadow predicate 已 FROZEN；B11 期间不调参。任何 predicate 变更都应启动新的冻结
  spec/version。

## 2026-06-18 — B10B Runtime-Shadow Replay CI Integration

### Objective

将 B10B 集成到 CI workflow 中，使其针对真实 P21 ephemeral records 运行，从而在下次 P21 CI run 时把 mechanics-validated scaffold 转变为 empirically-validated 的 scaffold。

### Implementation notes

- 使 `eval/b10b_runtime_shadow_replay.py --records` 既能接受 JSON 数组（legacy），也能接受 P21 payload 对象（带 `records` 字段）。格式由 top-level type 检测。
- 新增 `_extract_outcome_metrics(record, target_action_value)` helper，从 P21 per-strategy dicts 解析 outcome_audit 数据：target=weak_only 时取 `weak_candidate_only`，target=use_p25_action 时取 `candidate_baseline`。仅提取四个 `OUTCOME_AUDIT_NUMERIC_FIELDS`（`added_gold_span`、`added_false_span`、`span_f0_5`、`primary_false_positive_rate`）到一个新的 in-memory dict 中。Record 永不被 mutate。Shadow predicate 仍绝不读取 outcome_metrics（仅审计）。
- 新增 `--out <path>` CLI 选项用于 CI 输出路径。
- 在 `.github/workflows/real-provider-benchmark.yml`（P21-G3L step，在 P62 之后、`rm -f "$P25_RECORDS"` cleanup 之前）新增 CI step：`if [[ -f "$P25_RECORDS" ]]; then python3 eval/b10b_runtime_shadow_replay.py --records "$P25_RECORDS" --out artifacts/real_provider_ci/b10b_runtime_shadow_replay_report.json; fi`。Verdict=False 是合法结果（不是 CI failure）；只有 file/parse 错误才 fail。
- Spec hash 不变：`c201eb709dc0112c2bb91db33917c6d20ea48582924821a2bda7950709e754ba`（无 spec 变更；outcome 提取仅用于审计）。
- 本地 P21 payload fixture 测试通过：`replay_source="ci_ephemeral_records"`、`outcome_audit_status="ok"`，跨全部 4 个分区共 4 条记录，verdict=False 且带 `insufficient_label_driven_denominator`（小样本下预期如此）。
- Self-test 仍通过（10 项检查）。

### Findings

- B10B 现已接入 CI。下次 P21 CI run（通过 workflow_dispatch + enable_remote_models=true 触发）将产出真实 empirical B10B 数据。
- 若 B10B 在真实记录上通过全部 10 个 predeclared gate，则从 “mechanics-validated scaffold” 升级为 “empirically-supported”。
- 若 B10B 未通过 gate，B11 prospective validation 仍继续（B10B 仅是 ambiguous-branch shadow；B11 测试 benchmark-routed policy）。

### Caveats

- B10B CI 集成初始为 non-blocking（verdict=False 是合法结果）。
- 真实 empirical validation 需要下次 P21 CI run，需要 workflow_dispatch + enable_remote_models=true。
- B10B 本身不产生新的 live LLM calls（仅 replay）。

## 2026-06-18 — B11 Prospective Blind Validation Planning

### Objective

起草 B11 preregistration plan：在 2026-06-18 policy freeze 之后生成的新 repos/tasks 上，对冻结的 balanced policy `balanced_policy_v1_benchmark_routed` 进行 prospective validation，不对 policies、thresholds 或 success criteria 做任何 retuning。

### Implementation notes

- 并行侦察：@explorer 识别出已在 B6B/B6C/B6E/B6F/B8-lite 中使用的 8 个 repos（`py_flask`、`js_express`、`go_gin`、`rust_ripgrep`、`go_cobra`、`py_httpx`、`js_axios`、`rust_mdbook`），并从 `eval/ci_repos/openlocus-ci-repos-v1.yaml` 映射出可用的新 repos。@librarian 研究了 prospective validation 方法论（preregistration、worst-group metrics、CVaR、leave-one-out、live LLM eval 最佳实践）。@oracle strategic plan 返回为空（改用自行分析）。
- 为 minimum viable B11 选定 8 个新 repos：`py_fastapi`、`py_pytest`、`ts_vite`、`ts_hono`、`go_chi`、`go_prometheus`、`rust_deno`、`java_spring_petclinic`（5 种 languages：Python、TypeScript、Go、Rust、Java）。
- 从 `eval/p21_model_profiles.json` 确认 4 个 model families：Kimi-K2.7-Code（tool_call，reference）、Qwen3.6-27B（json_schema_strict，secondary）、DeepSeek-V4-Flash（json_schema_strict，recall）、DeepSeek-V4-Pro（json_schema_strict，conservative）。GLM-5.2 被排除（按 B9A/B6D 噪声大）。
- 确认 4 个 policies：Local baseline（无 LLM）、P25 `bucket_routed_v0`、Balanced v1 `balanced_policy_v1_benchmark_routed`、Conservative `rmc_local_conservative_v0`。
- Predeclared success/failure/partial criteria 带有显式 thresholds（Δgold_span、ΔSpanF0.5、ΔPFP、Δfalse_spans、ΔLLM_calls；overall + worst-group）。
- 定义 RobustUtility = min_group(SpanF0.5 - λ*PFP - μ*normalized_cost - ν*normalized_latency)，参数 λ=1.0、μ=0.1、ν=0.1。
- B10B integration：B10B --records 在每次 B11 run 之后于 CI 中运行（已通过 commit 2cbdd0c 集成），给 B10B 带来首次 empirical validation。
- 在 `docs/en/b11-prospective-blind-validation.md` 写入 B11 preregistration plan（325 行）。

### Findings

- B11 plan 已在任何 prospective live runs 之前冻结。live runs 开始后不再 retune policies、thresholds 或 success criteria。
- B11 被 framing 为 “exploratory prospective stress test”（按 @oracle B10B review）：B10B 尚未在真实 CI 记录上运行，因此 runtime-shadow predicate 未受到 empirical support。B11 测试的是 benchmark-routed balanced policy，不是 runtime-shadow predicate。
- Minimum viable B11（8 repos、~120 tasks、4 models）可自主完成基础设施搭建；live runs 需要 workflow_dispatch + enable_remote_models=true。

### Caveats

- B11 plan 是 preregistration；任何 post-hoc analysis 必须标注为 exploratory。
- Live LLM runs 需要用户 workflow_dispatch 触发。
- B11 **不**证明 promotion readiness；`promotion_ready=false`、`default_should_change=false`、`evidencecore_semantics_changed=false`。
- B11 evaluator skeleton（`eval/b11_prospective_validation.py`）与 CI workflow stage 是后续步骤（单独任务）。

## 2026-06-18 — B12 Mechanism Decomposition Planning

### Objective
起草 B12 preregistration plan：通过 5 个 ablation variants（A-E）和 4 个 hypotheses（H1-H4）进行 mechanism decomposition，以理解 balanced policy 为何有效。

### Implementation notes
- 定义 5 个 ablation variants：A（full balanced）、B（deterministic LLM reduction）、C（ambiguous weak_only only，≡A）、D（P25 default）、E（random LLM reduction）。
- 定义 4 个 hypotheses：H1（ambiguous routing）、H2（LLM call reduction）、H3（P25 fallback sufficiency）、H4（model-specific）。
- 方法论：replay-based（若 P21 records 可用）或 live ablation runs。
- B12 evaluator skeleton 位于 `eval/b12_mechanism_decomposition.py`（约 900 行，10 个 self-test checks，spec sha256 稳定）。
- --input 为 stub（verdict=not_implemented）；完整 ablation 计算延后。

### Findings
- B12 plan 已在任何 ablation runs 之前冻结。
- 若 P21 records 可用（来自 B11 live runs 或 CI ephemeral），B12 可作为 replay 完成。
- A≡C（两者均为 "ambiguous→weak_only, else P25"），因为 balanced policy 只有一条 routing rule。

### Caveats
- B12 ablation runs（若需要）需要 workflow_dispatch + enable_remote_models=true。
- B12 **不**证明 promotion；`promotion_ready=false`、`default_should_change=false`。


## 2026-06-18 — B13 Distributionally Robust Policy Search Planning

### Objective
起草 B13 preregistration plan：distributionally robust policy search，优化 worst-group utility（而非平均值），仅使用 runtime-observable features，并通过 rotating leave-one-model-family-out 验证。

### Implementation notes
- Rule grammar：6-10 条 rules，每条仅使用 runtime route_features（query_noise、candidate_support_exists、local_anchor、rrf_backed_by_anchor、candidate_count 等）。无 benchmark-private labels、无 score-private fields、algorithm_spec 中无 model names。
- Optimization objective：maximize worst-group utility OR CVaR_20%。RobustUtility = SpanF0.5 - λ*PFP - μ*normalized_cost - ν*normalized_latency（λ=1.0、μ=0.1、ν=0.1）。
- Validation：rotating leave-one-model-family-out（Kimi+Qwen→DeepSeek、Kimi+DeepSeek→Qwen、Qwen+DeepSeek→Kimi）。全部 3 个 rotations 必须通过。
- B13 evaluator skeleton 位于 `eval/b13_dro_policy_search.py`（约 2300 行，9 个只读 self-test checks，spec sha256 稳定）。`--self-test` 为只读（将内存中期望 artifacts 与 on-disk artifacts 比对，drift 即失败，不修改 checked-in artifacts）；`--regenerate-artifacts` 为唯一会修改 checked-in artifacts 的路径。
- --input 为 stub（verdict=not_implemented）；完整 search 延后。
- Special invariant：`algorithm_spec_has_no_model_names=true`（验证 spec 中无 model names）。
- skeleton verdict 框架仅发出 `insufficient_data`（synthetic fixture）或 `not_implemented`（ci_ephemeral_records stub）；`success` / `failure` / `partial` 保留给未来 `policy_search_performed=true` 的 empirical 路径，该路径在当前 skeleton 中**不**存在。
- synthetic / stub 报告仅发出 rotation *定义*（`rotations_defined=true`、`rotation_count=3`、`rotations_evaluated=false`）；它们**从不**发出 per-rotation 的 `passes=true` / `all_rotations_pass=true` / `test_worst_group_utility` / `delta_vs_b10_reference` 仿佛是 empirical 的。顶层 `policy_found=false`、`rotations_evaluated=false`、`winner_declared=false` 始终存在。

### Findings
- B13 plan 已在任何 search runs 之前冻结。
- B13 需要 B11 live runs 的 P21 records（4 model families × 8 repos）。
- B13 是 policy-search stage（`stage_is_policy_search=true`），但当前 skeleton
  **不**执行 empirical policy search（`empirical_policy_search_performed=false`）；
  synthetic / stub 报告设置 `policy_search_performed=false`、
  `policy_found=false`、`rotations_evaluated=false`、`winner_declared=false`，使该公共 artifact
  不会被误读为 empirical B13 run。**不**发出 empirical per-rotation
  passes / utilities / deltas。结果**不**被 promoted
  （`promotion_ready=false`、`default_should_change=false`）。
- B13 是 B10-B19 Breakthrough Sprint 中最后一个 "immediate priority" item。

### Caveats
- B13 search 需要 P21 records（来自 B11 live runs 或 CI ephemeral）。
- B13 **不**证明 promotion；结果仅是 research candidates。
- B13 之后，剩余 items（B14-B19）为 second priority 或 parallel tracks。

## 2026-06-18 — B13 Public-Aggregate Feasibility / No-Go Screen

### Objective

在 explorer/oracle 发现仅凭公共 aggregates 无法进行真实 B13 之后，针对
B13 从已发布的 B11 aggregate 与 B12 public-aggregate screen 产生一个 bounded
的 public-aggregate **feasibility / no-go screen**（**不是**真实 B13
distributionally robust policy search）。

### Implementation notes

- 新增 screen 脚本 `eval/b13_public_aggregate_feasibility_screen.py`（纯
  Python；复用 `b6_lite_interpretable_policy_search._walk_forbidden` 做公共输出
  的 forbidden-key 扫描；`--self-test` 合成 fixture 模式 + 输入校验阻断检查 +
  insufficient-data 分支检查 + forbidden 扫描检查）。
- 新增 aggregate artifact
  `artifacts/b13_dro_policy_search/b13_public_aggregate_feasibility_report.json`
  （schema `b13-public-aggregate-feasibility-screen-v0`）。
- 该 screen 仅读取 `artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json`
  与 `artifacts/b12_mechanism_decomposition/b12_public_aggregate_screen_report.json`
  （已发布的公共 aggregates）；不读取任何 raw records、paths、prompts、
  responses、snippets 或 private labels。
- 加固 B13 skeleton 的 claim fields：`eval/b13_dro_policy_search.py` 现在区分
  `stage_is_policy_search=true`（B13 stage 即 policy search）与
  `empirical_policy_search_performed=false`（skeleton 不执行 empirical search）；
  synthetic / stub 报告设置 `policy_search_performed=false`、
  `policy_found=false`、`rotations_evaluated=false`、`winner_declared=false`，使公共 artifact 不会
  被误读为 empirical B13 search。synthetic / stub 报告仅发出 rotation *定义*
  （`rotations_defined=true`、`rotation_count=3`、`rotations_evaluated=false`）；
  它们**从不**发出 per-rotation 的 `passes=true` /
  `all_rotations_pass=true` / `test_worst_group_utility` /
  `delta_vs_b10_reference` 仿佛是 empirical 的。skeleton verdict 框架仅发出
  `insufficient_data`（synthetic fixture）或 `not_implemented`
  （ci_ephemeral_records stub）；`success` / `failure` / `partial` 保留给未来
  `policy_search_performed=true` 的 empirical 路径，该路径在当前 skeleton 中**不**存在。
  `--self-test` 为只读（将内存中期望 artifacts 与 on-disk artifacts 比对，drift
  即失败，不修改 checked-in artifacts）；`--regenerate-artifacts` 为唯一会修改 checked-in artifacts 的路径。
  `verify_algorithm_spec`、`verify_report`、`_print_summary` 与
  `run_self_test` 已同步更新。

### Findings

- 公共 aggregate screen 的 B13 verdict：`no_go_public_aggregate_only`
  （B11 有 384 条记录；公共 aggregate 足以产生 feasibility 读取，但仅凭公共
  aggregates 无法进行真实 B13 search）。
- `empirical_policy_search_performed=false`、`policy_search_performed=false`、
  `policy_found=false`、`rotations_evaluated=false`、
  `full_b13_possible_from_public_artifacts=false`。
- 阻断真实 B13 的 missing inputs：
  `no_per_record_route_features_in_public_artifact`、
  `no_per_record_action_eligibility_in_public_artifact`、
  `no_per_strategy_outcomes_in_public_artifact`、
  `no_weak_candidate_only_public_outcomes_in_public_artifact`、
  `no_group_membership_for_train_test_rotations_in_public_artifact`、
  `no_held_out_family_evaluation_in_public_artifact`、
  `no_candidate_rule_coverage_in_public_artifact`。
- B11 mixed/partial verdict（`partial_with_failure`）与 B12 public-aggregate
  screen statuses 原样 carry forward；它们**不**授权 promotion、default
  change 或 runtime-clean general algorithm。
- 已发布固定策略（P25 / balanced_v1）的 descriptive overall-mean penalty index 以
  `descriptive_fixed_strategy_proxy_not_policy_search=true` 标注包含；它是严格
  descriptive 的，**不是** B13 RobustUtility、**不是** worst-group/CVaR/rotation-
  validated，**不**可用于 policy selection 或 strategy ranking；从不选择新 rule，
  从不声明 winner。

### Caveats

- 该 screen **不是**真实 B13 distributionally robust policy search。它**不**
  声称 empirical policy search，**不**选择 rule，**不**声明 winner。
- 无 promotion、无 default change、无 runtime-clean general algorithm claim、
  无 EvidenceCore semantics 变化（`promotion_ready=false`、
  `default_should_change=false`、`evidencecore_semantics_changed=false`、
  `policy_search_performed=false`、`quality_strategy_tuned=false`、
  `new_provider_calls=0`）。
- 建议下一步：future ephemeral-record B13 replay（唯一能进行 empirical
  distributionally robust policy search 的路径），或先做 ephemeral-record B12
  replay 以因果分解 balanced policy。公共 aggregate 不足以做任一。

## 2026-06-18 — B11 Official Integrated Matrix 聚合报告

### Objective

基于已下载的 aggregate-only public B11/B10B artifacts，对完成的 B11 official integrated matrix 生成有界的、仅聚合的 rollup，不读取任何 raw records、paths、prompts、responses、snippets 或 private labels。

### Implementation notes

- 输入：`/tmp/b11_official_integrated_artifacts` 下 32 个 run 目录，每个含 `artifacts/real_provider_ci/b11_prospective_validation_report.json` 与 `b10b_runtime_shadow_replay_report.json`。矩阵在重试两次 transient `provider_status` 失败后完成 32/32。
- 新增 combiner 脚本 `eval/b11_matrix_combiner.py`（纯 Python；复用 `b6_lite_interpretable_policy_search._walk_forbidden` 做公共输出的 forbidden-key 扫描；`--self-test` 合成 fixture 模式 + 空输入阻断检查）。
- 新增聚合 artifact `artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json`（schema `b11-prospective-matrix-aggregate-report-v0`）。
- combiner 拒绝任何不是 public B11 repo slice + public model 显示名 + run-id 三元组的 run 目录名；只发布 sanitized counts、public repo slice ID（`py_fastapi`、`py_pytest`、`ts_vite`、`ts_hono`、`go_chi`、`go_prometheus`、`rust_deno`、`java_spring_petclinic`）、public model-family 名（`kimi`、`qwen`、`deepseek_flash`、`deepseek_pro`）、weighted means、deltas 与 verdict 计数。不发布 run ID。

### Findings

- 32 runs，384 条记录。Verdict 计数：success 8、partial 23、failure 1。
- 384 条记录的 overall weighted means（`local_baseline` / `p25` / `balanced_v1` / `conservative`）：`gold_span 0.377604 / 0.247396 / 0.244792 / 0.125000`；`false_span 1.203125 / 0.236979 / 0.182292 / 0.236979`；`span_f0_5 0.062197 / 0.064538 / 0.062639 / 0.023611`；`PFP 0.083333 / 0.020833 / 0.0 / 0.0`；`model_calls 0.0 / 0.958333 / 0.604167 / 0.0`。
- balanced_v1 相对 P25 的 deltas：`Δgold_span -0.002604`、`Δfalse_span -0.054688`、`ΔSpanF0.5 -0.001899`、`ΔPFP -0.020833`、`Δmodel_calls -0.354167`。balanced_v1 平均上保持与 P25 近乎一致的 SpanF0.5/gold，同时减少 false spans、PFP 与 model calls。
- 按 model family（balanced_v1 vs P25，每个 96 条记录）：`deepseek_flash` partial 6 / success 2；`deepseek_pro` partial 5 / success 3；`kimi` partial 5 / success 2 / failure 1（一个 `py_fastapi` slice 超出 `failure_spanf05_delta`）；`qwen` partial 7 / success 1。
- B10B：32/32 报告，所有 run `runtime_shadow_ambiguous_supported=false`，`support_claim="empirical_replay_support_pending"`（原因 `insufficient_label_driven_denominator`；最大 `label_driven_ambiguous_denominator_qn0=3`，远低于 10 条记录的 hard gate）。B10B runtime-shadow predicate 仍为 empirical-pending。

### Caveats

- B11 为 mixed/partial。该结果加强了 algorithm-candidate 信号，但**并未**证明 runtime-clean 的 general algorithm。
- 无 promotion、无 default change、无 EvidenceCore semantics 变化（`promotion_ready=false`、`default_should_change=false`、`evidencecore_semantics_changed=false`、`policy_search_performed=false`、`quality_strategy_tuned=false`、`new_provider_calls=0`）。
- Kimi `py_fastapi` 失败 slice 与 B10B denominator-pending predicate 是 B12（mechanism decomposition）需要解决的开放问题。
- 仅聚合；combiner 未读取任何 raw records、paths、prompts、responses、snippets 或 private labels。

## 2026-06-18 — B12 Public Aggregate Mechanism Screen

### Objective

在 explorer/oracle 发现从当前 public artifacts 无法完成 full B12 replay 之后，基于已发布的 B11 aggregate 报告，对 H1-H4 生成一个有界的 public-aggregate **mechanism screen**（**不是**完整的 B12 per-record replay）。

### Implementation notes

- 新增 screen 脚本 `eval/b12_public_aggregate_screen.py`（纯 Python；复用 `b6_lite_interpretable_policy_search._walk_forbidden` 做公共输出的 forbidden-key 扫描；`--self-test` 合成 fixture 模式 + 输入校验阻断检查 + H3 parity-break 检查 + H4 spread-supported 分支检查）。
- 新增聚合 artifact `artifacts/b12_mechanism_decomposition/b12_public_aggregate_screen_report.json`（schema `b12-public-aggregate-mechanism-screen-v0`）。
- 该 screen 只读取 `artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json`（已发布的 B11 aggregate）；不读取或发布任何 raw records、paths、prompts、responses、snippets 或 private labels。
- 该 screen 应用**相同的**冻结数值门槛（±0.02 approx-equality on `gold_span`/`span_f0_5`；0.05 H4 model-family spread threshold），但仅作用于 aggregate deltas，因为 per-record ablation deltas 在 public 中不可用。
- 发出**逐 hypothesis 的 screen status**，从不发出单一全局 `supported` verdict；原样保留所有 safety fields（`aggregate_only_public_artifact=true`、`candidate_not_fact=true`、`promotion_ready=false`、`default_should_change=false`、`evidencecore_semantics_changed=false`、`policy_search_performed=false`、`quality_strategy_tuned=false`、`new_provider_calls=0`）。

### Findings

- H1 ambiguous routing：`inconclusive_unavailable_ablation_controls` —— public aggregate 缺少 per-record route decisions、ambiguous subset、variants B/E；**不**声称 H1 support。
- H2 LLM call reduction：`reduced_calls_observed_causal_mechanism_inconclusive` —— `Δmodel_calls -0.354167`，描述性观察到 reduced calls，但缺少 variant E 无法归因 causal mechanism；**不**声称 H2 causal support。
- H3 P25 fallback sufficiency：`aggregate_primary_parity_supported_consistent_with_h3` —— `Δgold_span -0.002604` 与 `ΔSpanF0.5 -0.001899` 均在 ±0.02 内；与 H3 在 aggregate primary-parity 层面一致，但**不是**完整的 H3 supported verdict（从 aggregate deltas 无法得出 per-record fallback sufficiency 结论）。
- H4 model-specific：`family_gold_spread_not_supported_model_repo_interaction_inconclusive` —— per-family gold_span delta spread `0.010417`（deepseek_flash 0.0、deepseek_pro 0.0、kimi -0.010417、qwen 0.0）at or below 0.05 family-level threshold；在 predeclared family-level gold-span spread criterion 下 **not supported**；**不是**完整的 H4 refutation，因为 Kimi `py_fastapi` failure slice 在无 per-record 数据时使 model×repo interaction 仍 inconclusive。

### Testability gaps（为何 full B12 从 public artifact 不可行）

- `no_per_record_route_decisions_in_public_artifact` —— 只发布 policy-level route-decision counts；per-record ambiguous vs P25 decisions 缺失。
- `no_ambiguous_subset_membership_in_public_artifact` —— public aggregate 不标识哪些 records 落入 ambiguous subset，因此 variants B/C/E 无法通过 subset selection 重建。
- `no_deterministic_call_reduction_variant_B_in_public_artifact` —— variant B 不是 B11 matrix 中发布的 policy，因此 H1 A>B 与 H2 routing-vs-reduction 比较无法进行。
- `no_random_call_reduction_variant_E_in_public_artifact` —— variant E 未发布；缺少 E 无法评估 H2 A≈E criterion。
- `no_weak_candidate_only_outcomes_in_public_artifact` —— `weak_candidate_only` per-strategy outcomes 不在 public aggregate 中，因此 routing-rule 贡献无法被隔离。

### Caveats

- 该 screen **不是**完整的 B12 mechanism decomposition。它**不**声称 H1 support，**不**声称 H2 causal support，**不**声称 full H4 refutation（仅 family-level gold-span spread criterion not supported），且**不**声称 H3 fully supported（仅 aggregate primary parity）。
- 无 promotion、无 default change、无 runtime-clean general algorithm claim、无 EvidenceCore semantics 变化（`promotion_ready=false`、`default_should_change=false`、`evidencecore_semantics_changed=false`、`policy_search_performed=false`、`quality_strategy_tuned=false`、`new_provider_calls=0`）。
- 建议下一步：future ephemeral-record B12 replay（首选），或 B13 distributionally robust policy search 谨慎进行。B13 不得被视为由 B12 supported verdict 授权。

## 2026-06-18 — B14 Uncertainty Calibration 规划 + Public-Aggregate Feasibility / No-Go Screen

### Objective

新增 B14 uncertainty-calibration 的 **preregistration + evaluator skeleton + public-aggregate feasibility / no-go screen**。这是一个有界的规划 / 可行性阶段，**不是** empirical calibration。真实 B14（model-independent uncertainty calibration，使用 local candidate signals、model output structure、cross-model disagreement；指标 risk-coverage、selective risk、ECE、PFP at fixed coverage；worst-group 报告；rotating leave-one-model-family-out）需要 per-record uncertainty scores + per-record outcomes + paired model outputs，这些在当前公共 artifacts 中不可用。

### Implementation notes

- 新增 preregistration 文档 `docs/en/b14-uncertainty-calibration.md` 与 `docs/zh/b14-uncertainty-calibration.md`（冻结的 signal families、forbidden labels、required per-record inputs、split/calibration/test protocol、coverage levels、ECE target definition、worst-group reporting、privacy/publication gates、success/partial/failure criteria）。明确指出当前公共 artifacts（B11 aggregate、B12 public screen、B13 public feasibility）不足。
- 新增 evaluator skeleton `eval/b14_uncertainty_calibration.py`（纯 Python；镜像 B13 freeze 风格）：frozen `build_algorithm_spec` + `build_report`；只读 `--self-test`（仅 synthetic fixture mechanics，将内存中期望 artifacts 与 on-disk artifacts 比对，drift 即失败，不写入）；`--regenerate-artifacts` 显式 mutating 路径；`--input` stub 返回 `not_implemented` / `insufficient_data`（**不是** empirical calibration）。Safety fields 原样保留：stub/synthetic 下 `uncertainty_calibration_performed=false`、`calibrated_model_claim=false`、`per_record_inputs_available=false`；`promotion_ready=false`、`default_should_change=false`、`evidencecore_semantics_changed=false`、`policy_search_performed=false`、`quality_strategy_tuned=false`、`new_provider_calls=0`。skeleton **绝不可**从 aggregate means 计算伪造的 ECE / risk-coverage / selective-risk / PFP-at-coverage 指标；synthetic fixture 仅验证 metric NAMES 与 gates（`metrics_evaluated=false`、`no_fake_metrics_from_aggregate_means=true`）。
- 新增聚合 artifacts `artifacts/b14_uncertainty_calibration/b14_uncertainty_calibration.algorithm.json`（schema `b14-uncertainty-calibration-spec-v0`）与 `b14_uncertainty_calibration_report.json`（schema `b14-uncertainty-calibration-report-v0`），由 `--regenerate-artifacts` 生成。
- 新增 bounded public-aggregate feasibility screen `eval/b14_public_aggregate_feasibility_screen.py`（纯 Python；复用 `b6_lite_interpretable_policy_search._walk_forbidden` 做公共输出的 forbidden-key 扫描；`--self-test` 合成 fixture 模式 + 输入校验阻断检查 + insufficient-data 分支检查 + forbidden 扫描检查）。它只读取 `artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json`、`artifacts/b12_mechanism_decomposition/b12_public_aggregate_screen_report.json` 与 `artifacts/b13_dro_policy_search/b13_public_aggregate_feasibility_report.json`（已发布的公共聚合）；不读取或发布任何 raw records、paths、prompts、responses、snippets 或 private labels。
- 新增聚合 artifact `artifacts/b14_uncertainty_calibration/b14_public_aggregate_feasibility_report.json`（schema `b14-public-aggregate-feasibility-screen-v0`）。

### Findings

- B14 verdict from the public aggregate screen：`no_go_public_aggregate_only`（B11 有 384 条记录；public aggregate 足以产生 feasibility read，但仅凭公共 aggregates 无法进行真实 B14 calibration）。
- `uncertainty_calibration_performed=false`、`calibrated_model_claim=false`、`per_record_inputs_available=false`、`uncertainty_score_found=false`、`rotations_evaluated=false`、`metrics_evaluated=false`、`no_fake_metrics_from_aggregate_means=true`、`full_b14_possible_from_public_artifacts=false`。
- 阻塞真实 B14 的 missing inputs：`no_per_record_uncertainty_scores_in_public_artifact`、`no_per_record_outcomes_in_public_artifact`、`no_paired_cross_model_outputs_in_public_artifact`、`no_schema_repair_per_call_rows_in_public_artifact`、`no_candidate_score_distributions_or_entropy_in_public_artifact`、`no_calibration_test_split_in_public_artifact`、`no_ece_bins_in_public_artifact`、`no_fixed_coverage_thresholds_applicable_in_public_artifact`。
- B11 mixed/partial verdict（`partial_with_failure`）、B12 public-aggregate screen statuses 与 B13 no-go 原样 carry forward；它们**不**授权 promotion、default change、calibrated-model claim 或 runtime-clean general algorithm。
- skeleton self-test verdict `insufficient_data`（synthetic fixture；无 per-record (uncertainty, outcome) pairs；无 metric values 被计算）；`--input` stub verdict `not_implemented`。

### Caveats

- 该 screen **不是**真实 B14 uncertainty calibration。它**不**计算 ECE / risk-coverage / selective risk / PFP-at-coverage，**不**声称 empirical calibration，**不**选择 uncertainty score，**不**声明 winner。
- 无 promotion、无 default change、无 calibrated-model claim、无 runtime-clean general algorithm claim、无 EvidenceCore semantics 变化（`promotion_ready=false`、`default_should_change=false`、`evidencecore_semantics_changed=false`、`uncertainty_calibration_performed=false`、`calibrated_model_claim=false`、`per_record_inputs_available=false`、`policy_search_performed=false`、`quality_strategy_tuned=false`、`new_provider_calls=0`）。
- 建议下一步：future ephemeral-record B14 calibration（唯一可执行 empirical uncertainty calibration 的路径），或先 ephemeral-record B13 replay 以授权 candidate policy。仅凭公共 aggregate 无法实现任一。


## 2026-06-18 — B15 Context Pack Policy Preregistration + Evaluator Skeleton + Public-Aggregate Prior / No-Go Screen

### Objective

Add the B15 context-pack-policy **preregistration + evaluator skeleton + public-aggregate prior / no-go screen**. This is a bounded planning / feasibility phase, NOT empirical atom-level ablation. Real B15 (frozen, preregistered PackPolicy mapping `(role, runtime_state, model_profile)` to a deterministic atom set; validated against per-record pack atom flags + per-record outcomes + role + runtime_state + model_profile + group membership; metric registry atom_effect_per_atom / role_pack_outcome / runtime_state_pack_outcome / model_profile_pack_outcome / worst_group_pack_outcome / cvar_20_pack_outcome / token_budget_parity / denominator_per_atom_role_model / randomization_balance_per_arm; worst-group reporting; rotating fresh-validation split stratified by `(model_family, repo, role)`) requires per-record pack atom flags + per-record outcomes + role-specific paired outputs + runtime_state + model_profile paired blocks + group membership + randomized atom assignment + balance stats + denominator-by-atom/role/model cells + token-budget-matched controls, which are unavailable in any current public artifact.

### Implementation notes

- New preregistration docs `docs/en/b15-context-pack-policy.md` and `docs/zh/b15-context-pack-policy.md` (frozen roles, atom registry, runtime_state contract, model_profile abstraction, forbidden labels/outcomes/raw model names, metric registry, hard gates, experimental structure, success/partial/failure criteria). Explicit that current public artifacts (B2 pack experiment, B14 public feasibility, B4-B9, P21-G, P49) are insufficient; B2 usable ONLY as `low_n_single_model_aggregate_directional_prior`.
- New evaluator skeleton `eval/b15_context_pack_policy.py` (pure Python; mirrors B13/B14 freeze style): frozen `build_algorithm_spec` + `build_report`; read-only `--self-test` (synthetic fixture mechanics only, compares in-memory expected artifacts to on-disk artifacts and fails on drift, does not mutate checked-in artifacts); `--regenerate-artifacts` is the explicit checked-in-artifact mutating path; `--input` stub requires explicit `--out`, refuses to write the checked-in B15 report, and returns `not_implemented` / `insufficient_data` (NOT empirical PackPolicy validation). Safety fields preserved verbatim: `pack_policy_learned=false`, `atom_ablation_performed=false`, `per_record_inputs_available=false` for stub/synthetic; `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `policy_search_performed=false`, `quality_strategy_tuned=false`, `new_provider_calls=0`. The skeleton MUST NOT compute fake atom-effect / role-pack-outcome / worst-group-pack-outcome metrics from aggregate means; the synthetic fixture validates only metric NAMES and gates (`metrics_evaluated=false`, `no_fake_atom_effects_from_aggregate_means=true`).
- New aggregate artifacts `artifacts/b15_context_pack_policy/b15_context_pack_policy.algorithm.json` (schema `b15-context-pack-policy-spec-v0`) and `b15_context_pack_policy_report.json` (schema `b15-context-pack-policy-report-v0`), generated by `--regenerate-artifacts`.
- New bounded public-aggregate prior / no-go screen `eval/b15_public_aggregate_prior_screen.py` (pure Python; reuses `b6_lite_interpretable_policy_search._walk_forbidden` for the public-output forbidden-key scan; `--self-test` synthetic-fixture mode + input-validation block checks + no-B2-doc branch check + optional-inputs-unavailable check + forbidden scan check). It reads only the published B2 contrastive-pack experiment doc (existence only; does NOT parse private per-task detail), the B14 public-aggregate feasibility report, and — when present — the B4-B9 / P21-G embedding-context / P49 contrastive-pack-scaffold public aggregate reports; no raw records, paths, prompts, responses, snippets, or private labels are read or emitted.
- New aggregate artifact `artifacts/b15_context_pack_policy/b15_public_aggregate_prior_screen_report.json` (schema `b15-public-aggregate-prior-screen-v0`).

### Findings

- B15 verdict from the public aggregate prior screen: `prior_screen_only` (B2 doc exists; usable ONLY as `low_n_single_model_aggregate_directional_prior`; real B15 PackPolicy validation is not possible from public aggregates alone).
- `pack_policy_learned=false`, `atom_ablation_performed=false`, `per_record_inputs_available=false`, `candidate_policy_frozen=false`, `stages_evaluated=false`, `metrics_evaluated=false`, `no_fake_atom_effects_from_aggregate_means=true`, `full_b15_possible_from_public_artifacts=false`.
- `b2_prior_usable=true`, `b2_prior_claim_level=low_n_single_model_aggregate_directional_prior`.
- `atom_level_inference_possible=false`, `role_specific_policy_possible=false`, `calibration_possible=false`, `new_live_runs_required=true`.
- Missing inputs that block real B15 from the public artifacts: `no_per_record_pack_atom_flags_in_public_artifact`, `no_per_record_outcomes_in_public_artifact`, `no_role_specific_paired_outputs_in_public_artifact`, `no_model_profile_paired_blocks_in_public_artifact`, `no_randomized_atom_assignment_in_public_artifact`, `no_randomization_balance_stats_in_public_artifact`, `no_denominator_by_atom_role_model_in_public_artifact`, `no_token_budget_matched_controls_in_public_artifact`, `no_fresh_validation_split_in_public_artifact`.
- B14 no-go carried forward unchanged; B2 prior carried forward ONLY as a weak directional hint; they do NOT authorize promotion, default change, PackPolicy promotion, atom-level causality, role-specific PackPolicy, calibrated policy, cross-model robustness, a hard-distractor general rule, a scores/provenance general win, or a runtime-clean general algorithm.
- Skeleton self-test verdict `insufficient_data` (synthetic fixture; no per-record (atom_flag, outcome) pairs; no metric values computed); `--input` stub verdict `not_implemented`.

### Caveats

- The screen is NOT real B15 PackPolicy validation. It does NOT compute atom-effect / role-pack-outcome / worst-group-pack-outcome metrics, does NOT claim empirical PackPolicy learning, does NOT freeze a candidate policy, does NOT declare a winner.
- No promotion, no default change, no PackPolicy promotion, no atom-level causality, no role-specific PackPolicy, no calibrated policy, no cross-model robustness, no hard-distractor general rule, no scores/provenance general win, no EvidenceCore semantics change (`promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `pack_policy_learned=false`, `atom_ablation_performed=false`, `per_record_inputs_available=false`, `policy_search_performed=false`, `quality_strategy_tuned=false`, `new_provider_calls=0`).
- B2 is usable ONLY as `low_n_single_model_aggregate_directional_prior`; it is NOT atom-level causality, role-specific PackPolicy, calibrated policy, cross-model robustness, a hard-distractor general rule, a scores/provenance general win, a default change, a promotion, or an EvidenceCore change.
- Recommended next step: future ephemeral-record B15 PackPolicy validation (the only path that can perform empirical PackPolicy validation), or first ephemeral-record B14 calibration to authorize a candidate uncertainty score. The public aggregate alone is insufficient for either.

## 2026-06-18 — B16 Downstream Coding-Agent Evaluation Preregistration + Evaluator Skeleton + Public-Aggregate Feasibility / No-Go Screen

### Objective

Add the B16 downstream coding-agent evaluation **preregistration + evaluator skeleton + public-aggregate feasibility / no-go screen**. This is a bounded planning / feasibility phase, NOT live downstream agent evaluation. Real B16 (frozen, preregistered paired within-task randomized controlled trial measuring whether a candidate retrieval/context variant improves a downstream coding agent on paired live agent runs with isolated fresh workspace, randomized arm order, same budget/tools/prompt except the retrieval variant, and no cross-run memory; metrics solve_rate, correct_file_before_first_edit, wrong_file_edits, tool_calls_before_first_edit, context_tokens, tests_pass, latency, cost; worst-group reporting; rotating fresh-validation split stratified by `(task_type, repo, model_family)`) requires paired live downstream agent runs + per-run agent event logs + per-run patches/diffs + per-run test execution results + per-run solve labels + per-run first-file-before-first-edit events + per-run wrong-file-edit annotations + per-run tool-call/token/latency/cost rows + per-run isolated workspace proof + per-run randomized arm order + a task oracle/hidden-test manifest, which are unavailable in any current public artifact. The B10-B15 retrieval/context candidate research is retrieval research; it does NOT prove downstream coding-agent value.

### Implementation notes

- New preregistration docs `docs/en/b16-downstream-agent-evaluation.md` and `docs/zh/b16-downstream-agent-evaluation.md` (frozen arms, task types, paired within-task randomization, metric registry, hard gates, experimental structure, success/partial/failure criteria). Explicit that current public artifacts (B11 matrix, B12/B13/B14/B15 public screens) are insufficient; retrieval improvements are NOT downstream agent improvements; B15 PackPolicy is NOT a downstream agent improvement.
- New evaluator skeleton `eval/b16_downstream_agent_evaluation.py` (pure Python; mirrors B13/B14/B15 freeze style): frozen `build_algorithm_spec` + `build_report`; read-only `--self-test` (synthetic fixture mechanics only, compares in-memory expected artifacts to on-disk artifacts and fails on drift, does not mutate checked-in artifacts); `--regenerate-artifacts` is the explicit checked-in-artifact mutating path; `--input` stub requires explicit `--out`, refuses to write ANY path inside `artifacts/b16_downstream_agent_evaluation/`, and returns `not_implemented` / `insufficient_data` (NOT empirical downstream agent evaluation). Safety fields preserved verbatim: `downstream_agent_runs_performed=false`, `patch_execution_performed=false`, `agent_behavior_metrics_evaluated=false`, `solve_rate_evaluated=false`, `per_record_inputs_available=false` for stub/synthetic; `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `retrieval_variant_promoted=false`, `policy_search_performed=false`, `quality_strategy_tuned=false`, `new_provider_calls=0`. The skeleton MUST NOT compute fake solve-rate / correct-file-before-first-edit / wrong-file-edits / tool-call / token / latency / cost metrics from retrieval aggregates; the synthetic fixture validates only metric NAMES and gates (`metrics_evaluated=false`, `no_fake_downstream_metrics_from_retrieval_aggregates=true`).
- New aggregate artifacts `artifacts/b16_downstream_agent_evaluation/b16_downstream_agent_evaluation.algorithm.json` (schema `b16-downstream-agent-evaluation-spec-v0`) and `b16_downstream_agent_evaluation_report.json` (schema `b16-downstream-agent-evaluation-report-v0`), generated by `--regenerate-artifacts`.
- New bounded public-aggregate feasibility / no-go screen `eval/b16_public_aggregate_feasibility_screen.py` (pure Python; reuses `b6_lite_interpretable_policy_search._walk_forbidden` for the public-output forbidden-key scan; `--self-test` synthetic-fixture mode + input-validation block checks + integrity fail-closed check + insufficient-data branch check + forbidden scan check). It reads only `artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json`, `artifacts/b12_mechanism_decomposition/b12_public_aggregate_screen_report.json`, `artifacts/b13_dro_policy_search/b13_public_aggregate_feasibility_report.json`, `artifacts/b14_uncertainty_calibration/b14_public_aggregate_feasibility_report.json`, and `artifacts/b15_context_pack_policy/b15_public_aggregate_prior_screen_report.json` (already-published public aggregates); no raw records, paths, prompts, responses, snippets, diffs, patches, test results, solve labels, agent event logs, or private labels are read or emitted.
- New aggregate artifact `artifacts/b16_downstream_agent_evaluation/b16_public_aggregate_feasibility_report.json` (schema `b16-public-aggregate-feasibility-screen-v0`).

### Findings

- B16 verdict from the public aggregate feasibility screen: `no_go_public_aggregate_only` (B11 has 384 records; the public aggregate is sufficient to produce a feasibility read, but real B16 downstream agent evaluation is not possible from public aggregates alone).
- `downstream_agent_runs_performed=false`, `patch_execution_performed=false`, `agent_behavior_metrics_evaluated=false`, `solve_rate_evaluated=false`, `per_record_inputs_available=false`, `candidate_retrieval_variant_frozen=false`, `stages_evaluated=false`, `metrics_evaluated=false`, `no_fake_downstream_metrics_from_retrieval_aggregates=true`, `full_b16_possible_from_public_artifacts=false`, `retrieval_variant_promoted=false`.
- Missing inputs that block real B16 from the public artifacts: `no_live_paired_agent_runs_in_public_artifact`, `no_agent_event_logs_in_public_artifact`, `no_patches_or_diffs_in_public_artifact`, `no_test_execution_results_in_public_artifact`, `no_solve_labels_in_public_artifact`, `no_first_file_before_first_edit_event_in_public_artifact`, `no_wrong_file_edit_annotations_in_public_artifact`, `no_tool_calls_tokens_latency_cost_per_run_in_public_artifact`, `no_randomized_arm_order_in_public_artifact`, `no_isolated_workspace_proof_in_public_artifact`, `no_task_oracle_or_hidden_test_manifest_in_public_artifact`, `no_operational_parity_proof_in_public_artifact`.
- B11 `partial_with_failure` and B12/B13/B14/B15 no-go or screen-only statuses carried forward unchanged; they do NOT authorize promotion, default change, retrieval-variant promotion, downstream agent value, or a runtime-clean general algorithm.
- Skeleton self-test verdict `insufficient_data` (synthetic fixture; no per-run paired agent outputs; no metric values computed); `--input` stub verdict `not_implemented`.

### Caveats

- The screen is NOT real B16 downstream agent evaluation. It does NOT compute solve-rate / correct-file-before-first-edit / wrong-file-edits / tool-call / token / latency / cost metrics, does NOT claim downstream agent value, does NOT freeze a candidate retrieval variant, does NOT promote a retrieval variant, does NOT declare a winner.
- No promotion, no default change, no retrieval-variant promotion, no EvidenceCore semantics change, no downstream agent runs, no patch execution, no agent behavior metrics, no solve rate (`promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `retrieval_variant_promoted=false`, `downstream_agent_runs_performed=false`, `patch_execution_performed=false`, `agent_behavior_metrics_evaluated=false`, `solve_rate_evaluated=false`, `per_record_inputs_available=false`, `policy_search_performed=false`, `quality_strategy_tuned=false`, `new_provider_calls=0`).
- Retrieval improvements are NOT downstream agent improvements; B15 PackPolicy is NOT a downstream agent improvement. The B10-B15 retrieval/context candidate research does NOT prove downstream coding-agent value.
- Recommended next step: future ephemeral-record B16 downstream agent evaluation (the only path that can perform empirical downstream agent evaluation), or first ephemeral-record B15 PackPolicy validation to authorize a candidate context-pack policy. The public aggregate alone is insufficient for either.

## 2026-06-18 — B17 QuIVer Systems Track Preregistration + Evaluator Skeleton + Public-Systems Diagnostic Carry-Forward / No-Go Screen

### Objective

Add the B17 QuIVer systems track **preregistration + evaluator skeleton + public-systems diagnostic carry-forward / no-go screen**. This is a bounded planning / diagnostic phase, NOT QuIVer production backend, NOT ANN quality promotion, NOT default change, NOT EvidenceCore semantics change. Real B17 (frozen, preregistered backend bakeoff comparing ANN backend candidates on backend systems metrics — latency, memory, build time, update cost, index size — under a frozen candidate-quality policy with candidate-set equivalence constraints: overlap@K vs reference, gold_retention_delta tolerance, primary_false_positive_delta guard, SpanF0.5_delta tolerance, citation_validity=1.0, stale/EvidenceCore rejection, no default expansion; metrics candidate_set_overlap_at_k, gold_retention_delta, span_f0_5_delta, primary_false_positive_delta, p50_latency, p95_latency, hot_memory, build_time, update_cost, index_size, recall_tolerance_violation_count; worst-group reporting; rotating fresh-validation split stratified by `(repo, model_family, language)`) requires per-backend systems bakeoff inputs + per-backend index build records + per-backend search latency records + per-backend hot memory records + per-backend index size records + per-backend update cost records + per-backend candidate-set-at-K records + per-backend gold retention records + per-backend span F0.5 records + per-backend PFP records + per-backend citation validity records + per-backend stale rejection records + per-backend EvidenceCore rejection records + per-backend recall tolerance violation records + per-backend randomized run order proof + per-backend isolated index workspace proof + a shared frozen candidate-quality manifest, which are unavailable in any current public artifact. The existing R33/R34/R36/R24 diagnostics are diagnostic-only carry-forward, not quality proof and not promotion evidence; they do NOT implement a QuIVer/Vamana graph backend, do NOT contain an HNSW run, and do NOT contain a candidate-set equivalence matrix across backends.

### Implementation notes

- New preregistration docs `docs/en/b17-quiver-systems-track.md` and `docs/zh/b17-quiver-systems-track.md` (frozen candidate backends, candidate-set equivalence constraints, metric registry, hard gates, experimental structure, success/partial/failure criteria). Explicit that the existing R33/R34/R36/R24 diagnostics are diagnostic-only carry-forward — not promotion evidence, not quality proof; they do NOT implement a QuIVer/Vamana graph backend, do NOT contain an HNSW run, and do NOT contain a candidate-set equivalence matrix across backends.
- New evaluator skeleton `eval/b17_quiver_systems_track.py` (pure Python; mirrors B13/B14/B15/B16 freeze style): frozen `build_algorithm_spec` + `build_report`; read-only `--self-test` (synthetic fixture mechanics only, compares in-memory expected artifacts to on-disk artifacts and fails on drift, does not mutate checked-in artifacts); `--regenerate-artifacts` is the explicit checked-in-artifact mutating path; `--input` stub requires explicit `--out`, refuses to write ANY path inside `artifacts/b17_quiver_systems_track/`, and returns `not_implemented` / `insufficient_data` (NOT empirical QuIVer systems bakeoff). Safety fields preserved verbatim: `stage_is_quiver_systems_track=true`, `quiver_graph_implemented=false`, `ann_backend_bakeoff_performed=false`, `candidate_set_equivalence_validated=false`, `backend_quality_promoted=false`, `retrieval_policy_changed=false`, `metrics_evaluated=false` for stub/synthetic; `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `new_provider_calls=0`. The skeleton MUST NOT compute fake candidate_set_overlap_at_k / gold_retention_delta / span_f0_5_delta / primary_false_positive_delta / p50_latency / p95_latency / hot_memory / build_time / update_cost / index_size / recall_tolerance_violation_count metrics from the existing R33/R34/R36/R24 diagnostics; the synthetic fixture validates only metric NAMES and gates (`metrics_evaluated=false`, `no_fake_ann_metrics_from_diagnostics=true`).
- New aggregate artifacts `artifacts/b17_quiver_systems_track/b17_quiver_systems_track.algorithm.json` (schema `b17-quiver-systems-track-spec-v0`) and `b17_quiver_systems_track_report.json` (schema `b17-quiver-systems-track-report-v0`), generated by `--regenerate-artifacts`.
- New bounded public-systems diagnostic carry-forward / no-go screen `eval/b17_public_systems_diagnostic_screen.py` (pure Python; reuses `b6_lite_interpretable_policy_search._walk_forbidden` for the public-output forbidden-key scan; `--self-test` synthetic-fixture mode + optional-artifacts-absent branch + no-artifacts-at-all branch + input-validation block checks + forbidden scan check). It reads only `artifacts/r33/quiver_readiness.json`, `artifacts/r34_r36/quiver_anchor_proto.json`, `artifacts/real_provider/p3_real_quiver_readiness.json`, `artifacts/real_provider/p4_real_quiver_anchor_proto.json`, and the optional `runs/r24-quiver-tdb-probe.json` (already-published public diagnostics); each guard is optional and absent artifacts are reported as `not_present` rather than failing. No raw records, paths, prompts, responses, snippets, diffs, patches, test results, solve labels, backend event logs, index build records, search latency records, hot memory records, index size records, or private labels are read or emitted.
- New aggregate artifact `artifacts/b17_quiver_systems_track/b17_public_systems_diagnostic_screen_report.json` (schema `b17-public-systems-diagnostic-screen-v0`).

### Findings

- B17 verdict from the public-systems diagnostic carry-forward screen: `no_go_quiver_graph_missing` (every present public diagnostic reports `quiver_graph_implemented=false`; the B17 QuIVer systems track cannot proceed without a QuIVer or Vamana graph backend implementation).
- `stage_is_quiver_systems_track=true`, `quiver_graph_implemented=false`, `ann_backend_bakeoff_performed=false`, `candidate_set_equivalence_validated=false`, `backend_quality_promoted=false`, `retrieval_policy_changed=false`, `metrics_evaluated=false`, `no_fake_ann_metrics_from_diagnostics=true`, `full_b17_systems_bakeoff_possible_from_public_artifacts=false`, `new_provider_calls=0`.
- Missing inputs that block real B17 from the public diagnostics: `no_quiver_or_vamana_graph_backend_implementation`, `no_hnsw_backend_run`, `no_candidate_set_equivalence_matrix_across_backends`, `no_update_cost_benchmark`, `no_build_time_index_size_benchmark`, `no_stale_citation_cross_backend_validation`, `no_shared_frozen_candidate_quality_manifest`, `no_large_repo_repeatable_systems_matrix`.
- R33 `quiver_graph_implemented=false`, `quiver_quality_metrics_emitted=false`; R34/R36 `quiver_mode=diagnostic_only`; real-provider P3/P4 diagnostic-only; R24 QuIVer/TDB/dense probe `promotion_ready=false` — all carried forward unchanged as pre-B17 signals only, NOT promotion, NOT quality proof.
- Skeleton self-test verdict `insufficient_data` (synthetic fixture; no per-backend systems bakeoff inputs; no metric values computed); `--input` stub verdict `not_implemented`.

### Caveats

- The screen is NOT real B17 QuIVer systems bakeoff. It does NOT compute candidate_set_overlap_at_k / gold_retention_delta / span_f0_5_delta / primary_false_positive_delta / p50_latency / p95_latency / hot_memory / build_time / update_cost / index_size / recall_tolerance_violation_count metrics, does NOT claim QuIVer implementation, does NOT claim ANN quality, does NOT promote a backend, does NOT change retrieval policy, does NOT declare a winner.
- No promotion, no default change, no retrieval-policy change, no backend quality promotion, no QuIVer graph implementation, no EvidenceCore semantics change, no ANN backend bakeoff, no candidate-set equivalence validation, no metrics evaluated (`promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `retrieval_policy_changed=false`, `backend_quality_promoted=false`, `quiver_graph_implemented=false`, `ann_backend_bakeoff_performed=false`, `candidate_set_equivalence_validated=false`, `metrics_evaluated=false`, `new_provider_calls=0`).
- The existing R33/R34/R36/R24 diagnostics are diagnostic-only carry-forward — they are NOT quality proof and NOT promotion evidence; they do NOT implement a QuIVer/Vamana graph backend, do NOT contain an HNSW run, and do NOT contain a candidate-set equivalence matrix across backends.
- Recommended next step: future QuIVer or Vamana graph backend implementation + a shared frozen candidate-quality manifest, then run a B17 systems bakeoff with per-backend systems inputs and candidate-set equivalence matrix versus a reference backend. The public diagnostics alone are insufficient.

## 2026-06-19 — B18 OOD / Temporal Evaluation Preregistration + Evaluator Skeleton + Public-Aggregate No-Go Screen

### Objective

Add the B18 OOD / temporal evaluation **preregistration + evaluator skeleton + bounded public-aggregate no-go screen**。这是一个 bounded preregistration / no-go 阶段，**不是** 真正的 OOD / temporal evaluation，**不是** policy search，**不是** quality strategy tuning，**不是** default change，**不是** EvidenceCore semantics change，**不是** promotion。真实 B18（frozen、preregistered 的 OOD / temporal evaluation，跨五个 FROZEN split axes——`temporal_split`、`repo_split`、`language_split`、`model_family_split`、`adversarial_split`——在 no-retuning protocol 下，metrics 包括 ood_generalization_gap、temporal_holdout_delta、repo_holdout_metric、language_holdout_metric、model_family_holdout_metric、adversarial_robustness_score、worst_group_metric、cvar_tail_metric、per_cell_denominator、temporal_split_integrity、no_retuning_proof_metric、citation_validity、stale_evidencecore_rejection_rate；worst-group reporting；rotating fresh-validation split stratified by `(repo, language, model_family, time)`）需要 per-record OOD / temporal inputs + per-record records + per-record time index + per-record commit chronology + per-record repo / language / model_family axes + per-record task category + per-record adversarial holdout membership + per-record temporal holdout membership + per-record outcome label + per-record citation validity + per-record stale rejection + per-record EvidenceCore rejection + per-record randomized run order proof + per-record no-retuning proof + shared frozen evaluation protocol manifest，这些在任何当前 public artifact 中都不可得。现有 B11 / R15 / R20 / R26 aggregates 是 aggregate-only / metadata-only carry-forward，不是 OOD / temporal proof，也不是 promotion evidence；它们**不**包含 per-record records、time axis、commit chronology、per-repo-per-language cells、model_family x repo matrix、adversarial holdout outcomes 或 temporal holdout outcomes；R15 / R20 / R26 repo locks 是 synthetic / static snapshots，无真实 commit chronology 或 time axis。

### Implementation notes

- 新 preregistration docs `docs/en/b18-ood-temporal-evaluation.md` 与 `docs/zh/b18-ood-temporal-evaluation.md`（frozen split axes、no-retuning protocol、metric registry、hard gates、experimental structure、success/partial/failure criteria）。明确现有 B11 / R15 / R20 / R26 aggregates 是 aggregate-only / metadata-only carry-forward —— 不是 promotion evidence，不是 OOD / temporal proof；它们**不**包含 per-record records、time axis、commit chronology、per-repo-per-language cells、model_family x repo matrix、adversarial holdout outcomes 或 temporal holdout outcomes。
- 新 evaluator skeleton `eval/b18_ood_temporal_evaluation.py`（pure Python；mirror B13/B14/B15/B16/B17 freeze style）：frozen `build_algorithm_spec` + `build_report`；read-only `--self-test`（synthetic fixture mechanics only，将 in-memory expected artifacts 与 on-disk artifacts 比对，drift 即失败，不修改 checked-in artifacts）；`--regenerate-artifacts` 为显式修改 checked-in artifacts 的路径（同时写入 canonical public no-go screen report）；`--public-screen --out <path>` 从当前 public artifacts 运行 bounded public-aggregate no-go screen 并写入显式 `--out` 路径（若 `--out` 缺失，canonical public screen artifact 仅在从 `--regenerate-artifacts` 调用时才被写入；否则非 self-test 调用要求 `--out`）；`--input` stub 要求显式 `--out`，拒绝写入 `artifacts/b18_ood_temporal_evaluation/` 内的任何路径，并返回 `not_implemented` / `insufficient_data`（**非** empirical OOD / temporal evaluation）。Safety fields 保持原样：`stage_is_ood_temporal_evaluation=true`、`ood_temporal_evaluation_performed=false`、`metrics_evaluated=false`、`policy_search_performed=false`、`quality_strategy_tuned=false`、`real_ood_temporal_supported=false`、`retrieval_policy_changed=false`；`promotion_ready=false`、`default_should_change=false`、`evidencecore_semantics_changed=false`、`new_provider_calls=0`。Skeleton **绝不可**从 B11 aggregate means 或 R15 / R20 / R26 repo locks 计算伪造的 ood_generalization_gap / temporal_holdout_delta / repo_holdout_metric / language_holdout_metric / model_family_holdout_metric / adversarial_robustness_score / worst_group_metric / cvar_tail_metric / per_cell_denominator / temporal_split_integrity / no_retuning_proof_metric / citation_validity / stale_evidencecore_rejection_rate 指标；synthetic fixture 仅验证 metric NAMES 与 gates（`metrics_evaluated=false`、`no_fake_ood_metrics_from_aggregate_means=true`）。
- 新 aggregate artifacts `artifacts/b18_ood_temporal_evaluation/b18_ood_temporal_evaluation.algorithm.json`（schema `b18-ood-temporal-evaluation-spec-v0`）、`b18_ood_temporal_evaluation_report.json`（schema `b18-ood-temporal-evaluation-report-v0`）与 `b18_public_ood_temporal_screen_report.json`（schema `b18-public-ood-temporal-screen-v0`），由 `--regenerate-artifacts` 生成。
- 新 bounded public-aggregate no-go screen 集成进 `eval/b18_ood_temporal_evaluation.py`（`--public-screen` mode + `screen_public` 函数；复用 `b6_lite_interpretable_policy_search._walk_forbidden` 作为共享的 public-output forbidden-key scan，加上 B18 evaluator 自身更严格的 `_recursive_key_scan`；`--self-test` 包含 `public_screen_no_go` 与 `public_screen_optional_artifacts_absent` checks）。它仅读取 `artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json`、`fixtures/r15/repos.lock.jsonl`、`fixtures/r20_auto_wide/repos.lock.jsonl`、`fixtures/r26_auto_stress/repos.lock.jsonl`、`fixtures/r20_auto_wide/dataset_manifest.json` 与 `fixtures/r26_auto_stress/dataset_manifest.json`（已发布的 public aggregates / metadata）；每个 guard 是可选的，缺失的 artifacts 被报告为 `not_present` 而非失败。不读取或发出 raw records、paths、prompts、responses、snippets、diffs、patches、test results、solve labels、agent event logs、per-record records、time indices、commit chronology、outcome labels、content SHAs 或 private labels。

### Findings

- B18 public-aggregate no-go screen verdict：`no_go_public_aggregate_only`（每个存在的 public artifact 是 aggregate-only 或 synthetic static snapshot；均不含 per-record records、time axis、commit chronology、per-repo-per-language cells、model_family x repo matrix、adversarial holdout outcomes 或 temporal holdout outcomes）。
- `stage_is_ood_temporal_evaluation=true`、`ood_temporal_evaluation_performed=false`、`metrics_evaluated=false`、`policy_search_performed=false`、`quality_strategy_tuned=false`、`real_ood_temporal_supported=false`、`retrieval_policy_changed=false`、`no_fake_ood_metrics_from_aggregate_means=true`、`full_b18_ood_temporal_evaluation_possible_from_public_artifacts=false`、`new_provider_calls=0`。
- 从 public aggregates 阻塞真实 B18 的 missing inputs：`no_per_record_records`、`no_time_axis`、`no_commit_chronology`、`no_per_repo_per_language_cells_in_public_b11`、`no_model_family_x_repo_matrix`、`no_adversarial_holdout_outcomes`、`no_temporal_holdout_outcomes`。
- B11 aggregate `promotion_ready=false`、`aggregate_only_public_artifact=true`；R15 / R20 / R26 repo locks 是 synthetic static snapshots（单一 static snapshot commit label，无 chronological ordering）—— 均作为 pre-B18 signals 不变 carry forward，**非** promotion，**非** OOD / temporal proof。
- Skeleton self-test verdict `insufficient_data`（synthetic fixture；无 per-record OOD / temporal inputs；无 metric values computed）；`--input` stub verdict `not_implemented`。

### Caveats

- 该 screen **不**是真实 B18 OOD / temporal evaluation。它**不**计算 ood_generalization_gap / temporal_holdout_delta / repo_holdout_metric / language_holdout_metric / model_family_holdout_metric / adversarial_robustness_score / worst_group_metric / cvar_tail_metric / per_cell_denominator / temporal_split_integrity / no_retuning_proof_metric / citation_validity / stale_evidencecore_rejection_rate 指标，**不**声称 OOD / temporal evaluation，**不**声称 generalization，**不** promote retrieval variant，**不**修改 retrieval policy，**不**声明 winner。
- No promotion、no default change、no retrieval-policy change、no backend quality promotion、no OOD / temporal evaluation、no policy search、no quality strategy tuning、no EvidenceCore semantics change、no metrics evaluated（`promotion_ready=false`、`default_should_change=false`、`evidencecore_semantics_changed=false`、`retrieval_policy_changed=false`、`backend_quality_promoted=false`、`stage_is_ood_temporal_evaluation=true`、`ood_temporal_evaluation_performed=false`、`metrics_evaluated=false`、`policy_search_performed=false`、`quality_strategy_tuned=false`、`real_ood_temporal_supported=false`、`new_provider_calls=0`）。
- 现有 B11 / R15 / R20 / R26 aggregates 是 aggregate-only / metadata-only carry-forward —— 它们**不**是 OOD / temporal proof，**不**是 promotion evidence；它们**不**包含 per-record records、time axis、commit chronology、per-repo-per-language cells、model_family x repo matrix、adversarial holdout outcomes 或 temporal holdout outcomes；R15 / R20 / R26 repo locks 是 synthetic / static snapshots，无真实 commit chronology 或 time axis。
- Recommended next step：未来带真实 time axis 与 commit chronology per repo 的 prospective per-record data collection，加上 per-repo / per-language / per-model-family cells 与 adversarial 和 temporal holdout memberships，在 frozen no-retuning protocol 下，然后运行 B18 OOD / temporal evaluation。仅靠 public aggregates 是不够的。

## 2026-06-19 — B19 理论综合（Model-Robust Selective Evidence Conversion）

### Objective

撰写 B10-B18 Breakthrough Sprint 的 **理论综合**，作为候选算法概念 **Model-Robust Selective Evidence Conversion** 的论文式算法报告。这是 synthesis-only：**不**运行 provider，**不**修改 retrieval / default / `EvidenceCore`，**不**声明 promotion。综合 B10 / B10B / B11 / B12 / B13 / B14 / B15 / B16 / B17 / B18；在 B10-B18 之外**不**引入任何新 metrics 与新 claim。

### Implementation notes

- 新综合文档 `docs/en/b19-theoretical-synthesis.md` 与 `docs/zh/b19-theoretical-synthesis.md`（算法概念；输入；输出/动作；核心原则；问题陈述；算法草稿/伪代码；证据边界；策略学习循环；adapter 边界；评估协议；综合证据 B10-B18；当前 empirical 证据；no-go gaps；promotion blockers；下一步研究计划；结论）。明确 B19 是 synthesis-only，所有 no-promotion 标志均为 false。
- 新 evaluator `eval/b19_theoretical_synthesis.py`（pure Python）：frozen `build_report`；只读 `--self-test`（将内存中期望报告与 on-disk artifact 比对，drift 即失败，**不**修改 checked-in artifacts）；`--regenerate-artifacts` 是**唯一**修改 checked-in artifacts 的路径（重写 canonical report 并重跑 self-test）；`--input` 是一个 `not_implemented` stub，因为 B19 是 synthesis-only（要求 `--out`，拒绝写入 `artifacts/b19_theoretical_synthesis/` 内的任何路径）。
- 新 aggregate artifact `artifacts/b19_theoretical_synthesis/b19_theoretical_synthesis_report.json`（schema `b19-theoretical-synthesis-report-v0`，claim level `theoretical_synthesis_of_b10_through_b18`），由 `--regenerate-artifacts` 生成。
- B19 专用的 forbidden scan 复用共享的 `b6_lite_interpretable_policy_search.FORBIDDEN_PUBLIC_KEYS` 集合与一个 digest-like value 检查（`[A-Fa-f0-9]{32,}`），但**不**应用共享 helper 的 `>256 chars = long_string` 规则，因为综合本身就是有意为之的长 prose。报告自身的 `report_content_sha256` drift-guard self-hash 按键名白名单豁免。
- drift guard（`report_content_sha256`）作为 SHA-256 嵌入，覆盖报告内容的 canonical sorted-keys JSON（排除 `generated_at` 与 `report_content_sha256` 自身）。self-test 重新计算并断言相等。

### Findings

- B19 verdict：synthesis-only；B10-B18 的 evidence boundary 原样 carry forward。唯一逐字 carry forward 的 empirical 数字是 B11 official integrated matrix deltas（balanced_v1 vs p25）：`Δgold_span -0.002604`、`ΔSpanF0.5 -0.001899`、`Δfalse_span -0.054688`、`ΔPFP -0.020833`、`Δmodel_calls -0.354167`。self-test 逐字节断言它们与 `artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json` 一致。
- 所有 no-promotion 标志为 false：`promotion_ready=false`、`default_should_change=false`、`evidencecore_semantics_changed=false`、`runtime_clean_policy_supported=false`、`downstream_agent_value_proven=false`、`ood_temporal_supported=false`、`quiver_systems_supported=false`、`is_new_experiment=false`、`ran_providers=false`、`changed_retrieval_default_evidencecore=false`。
- Safety invariants 保持：`aggregate_only_public_artifact=true`、`candidate_not_fact=true`、`not_evidence=true`、`llm_output_not_evidence=true`、`new_provider_calls=0`、`forbidden_public_scan_clean=true`、`report_drift_guarded=true`、`docs_links_exist=true`、`synthesized_source_artifacts_pinned=true`、`no_fake_metrics_beyond_b10_b18=true`。
- self-test 验证：所有 10 个 required formal sections 存在且非空；所有 no-promotion flags 字面为 False；B11 deltas 存在且精确（与源 artifact 交叉核对）；所有 10 个 synthesized source artifacts 在磁盘上存在；B19 docs links 存在（en + zh）；forbidden public scan 干净；report content hash drift guard 匹配。

### Caveats

- B19 **不**是新实验，**不**是 promotion，**不**是 default change，**不**是 `EvidenceCore` semantics change，**不**是 runtime-clean policy claim，**不**是 downstream-agent value claim，**不**是 OOD/temporal claim，**不**是 QuIVer systems claim。
- 本综合原样 carry forward B12 / B13 / B14 / B15 / B16 / B17 / B18 的 no-go / screen-only / prior-screen 状态。B11 `partial_with_failure` 原样 carry forward。B10 `runtime_clean=false` 与 B10B `runtime_shadow_ambiguous_supported=false` 原样 carry forward。
- 公共 artifact 中无 raw records / paths / spans / snippets / prompts / responses / gold labels / `content_sha` / provider keys / api keys。drift-guard self-hash 是唯一的 digest-like value，按键名白名单豁免。
- Recommended next step：B19 next-research-program 列表（runtime-clean B10B predicate、per-record mechanism / DRO / calibration / pack-policy / downstream-agent / QuIVer / OOD-temporal 数据收集），然后是一个单独的 promotion preregistration。综合本身**绝不**授权 promotion。

## 2026-06-19 — C2 B12 CI Canary with Private P21 Records

### Objective

用真实 GitHub CI run 验证新的 C1 private-record adapter 与 B12 real `--input` replay path，而不是只依赖 synthetic fixtures。目标是证明 B12 能消费 runner-temp private P21 records，同时只发出 aggregate-only public report，并保持 public/private boundary。

### Implementation notes

- 首先尝试了一个 `3`-task prefix canary（run `27816674482`）；它被现有 P21 privacy gate 拒绝，因为该 sample 没有 exercise remote LLM snippets。这是 canary coverage failure，不是 B12 replay failure。
- 随后用 `round_robin_public_buckets` 与 `max_tasks=12` 重跑（run `27816890557`），成功 exercise provider path，并通过 P21 privacy gate、B10B、B11 与 B12 report upload flow。
- 新增 aggregate-only artifact `artifacts/c2_b12_canary/c2_b12_canary_report.json`，只汇总 public counts、verdicts、deltas 与 safety flags。不提交 private records、task IDs、raw repo IDs、paths、spans、content hashes、prompts、responses、snippets、provider URLs 或 provider keys。

### Findings

- B12 report 使用 `replay_source="ci_ephemeral_records"`，并通过 `eval/c1_private_records.py` 消费真实 private P21 records。
- Counts：`total_records=12`、`complete_records=12`、`incomplete_record_count=0`、`missing_required_outcome_count=0`、`balanced_branch_count=4`、`p25_llm_eligible_count=10`、`actual_call_avoided_count=4`、`random_selected_count=4`。
- Canary verdict：`partial`。H1 `refuted`、H2 `refuted`、H3 `supported`、H4 `insufficient_data`（single model family；按设计 H4 不阻断 H1-H3 verdict）。
- Canary 上 A vs D deltas：`gold_span 0.0`、`SpanF0.5 0.0`、`false_span 0.0`、`PFP 0.0`、`model_calls -0.333333`。A vs E false-span delta 为 `-0.083334`。

### Caveats

- 这只是 canary-level result：一个 repo、一个 model family、12 records。它**不**证明 B12 mechanism 全局成立，也**不** promotion、**不** default-change、**不**使 balanced_v1 runtime-clean。
- 下一步是对 B11 repo/model cells 跑完整 B12 matrix，然后聚合 B12 reports，再做机制 claim。

## 2026-06-19 — C2/B12 Official Matrix Aggregate Combiner

### Objective

实现 C2/B12 official matrix aggregate combiner：一个有界的 derived aggregate
rollup，把一次已完成的 C2/B12 official integrated matrix run 产生的 per-run
`b12-mechanism-decomposition-report-v0` 公共 aggregate 报告合并为一份
aggregate-only public artifact。它是 aggregate-only；**不**运行 providers、**不**运行
policy search、**不** promotion、**不**修改 defaults、**不**修改 `EvidenceCore` 语义。

### Implementation notes

- 新增 evaluator `eval/b12_matrix_combiner.py`（纯 Python）。CLI：`--self-test`
  （synthetic 3-cell + 1-exclusion fixture，校验 schema/safety/weighted means/
  forbidden scan/verdict）；`--artifacts-dir <path>`（递归发现其下的
  `b12_mechanism_decomposition_report.json`，从 `real-provider-p21_llm_rich-<run_id>`
  路径组件解析 run_id）；可选 `--manifest <path>`（强制 `included`/`excluded` 计数，
  并把每个已发现报告的 run_id 对账到 manifest 的 included cell）；`--out <path>` 默认
  `artifacts/b12_mechanism_decomposition/b12_matrix_aggregate_report.json`。
- 输出 schema：`b12-mechanism-matrix-aggregate-report-v0`。Aggregate-only public：**无**
  run IDs、task IDs、raw repo IDs、paths/spans/content_sha/prompts/responses/snippets/
  provider URLs/keys。公共 repo slice IDs 与 model-family 名仅作为 manifest 中的 slice IDs
  再发布，绝不作为 run IDs。
- 逐输入校验：schema version `b12-mechanism-decomposition-report-v0`、
  `aggregate_only_public_artifact=true`、`promotion_ready=false`、
  `default_should_change=false`、`evidencecore_semantics_changed=false`、
  `replay_source == ci_ephemeral_records`、无 forbidden public keys/values
  （复用 `b6_lite_interpretable_policy_search._walk_forbidden`）、included cell 的
  `complete_records > 0` 且 `incomplete_record_count == 0`。
- 在 28 个 analyzable cells 上聚合：`cell_count_target=32`、`analyzable_cell_count=28`、
  `excluded_cell_count=4`；`record_count_total`；`coverage_exclusions`（按公共 repo slice +
  model family + reason，无 run ids）；基于 per-run B12 verdict 的 `verdict_counts`；
  H1/H2/H3/H4 的 `hypothesis_status_counts`；对 `gold_span`、`span_f0_5`、`false_span`、
  `primary_false_positive_rate`、`model_calls` 计算相对 D/E/B 的 record-weighted 均值 delta
  （以 `complete_records` 为权重），外加 A 的 record-weighted 均值 robust utility；
  `replay_count_totals` 覆盖 `balanced_branch_count`、`p25_llm_eligible_count`、
  `actual_call_avoided_count`、`random_selected_count`；保守的 `mechanism_summary`。

### Findings — run reconciliation

- 目标 matrix：32 cells（8 个公共 repo slice × 4 个公共 model family）。
- Analyzable：28 cells（8 个 repo slice 中 7 个 slice 的全部 4 个 model family ——
  `py_fastapi`、`py_pytest`、`ts_hono`、`go_chi`、`go_prometheus`、`rust_deno`、
  `java_spring_petclinic`）。
- Excluded：4 cells，全部为 `ts_vite` × {kimi, qwen, deepseek_flash, deepseek_pro}，
  `status=coverage_insufficient_no_remote_llm_snippet`。这些 cells 即使 `max_tasks=24`
  也未 exercise remote LLM snippets，故被旧 P21 privacy gate 拒绝。它们被视为
  coverage-insufficient，**不**视为 B12 mechanism failure。
- Matrix run 期间出现 transient Cargo failures，已成功重试（两次 `ts_hono × deepseek_pro`
  与 `java_spring_petclinic × deepseek_flash` 重试成功，`source=
  retry_success_replacing_transient_failure`）。**未**基于这些重试做任何 promotion、
  default 或 runtime-clean 声明。

### Findings — 生成 aggregate 的关键指标

- `record_count_total=336`（每 cell 12 条 complete records）。
- `verdict_counts={"partial": 28}`。
- `hypothesis_status_counts`：H1 `supported: 3 / refuted: 25`；H2
  `supported: 8 / refuted: 20`；H3 `supported: 28`；H4 `insufficient_data: 28`
  （每个 cell 都是 single-model-family slice，故 H4 需跨 cell 的 multi-model
  aggregation；按设计 H4 insufficient_data **不**阻断 H1-H3 verdict）。
- Record-weighted A（full balanced）deltas vs D（P25 default）：`Δgold_span 0.0`、
  `ΔSpanF0.5 0.0`、`Δfalse_span -0.029762`、`ΔPFP -0.014881`、`Δmodel_calls -0.333333`；
  vs E（random call reduction）：`Δgold_span -0.044643`、`ΔSpanF0.5 0.001569`、
  `Δfalse_span -0.592262`、`ΔPFP -0.026786`、`Δmodel_calls 0.0`；vs B（deterministic
  call reduction）：`Δgold_span 0.0`、`ΔSpanF0.5 0.0`、`Δfalse_span -0.130952`、
  `ΔPFP -0.035714`、`Δmodel_calls 0.0`。
- `weighted_mean_robust_utility_a = 0.054155`。
- `replay_count_totals`：`balanced_branch_count=112`、`p25_llm_eligible_count=324`、
  `actual_call_avoided_count=112`、`random_selected_count=112`。
- `aggregate_verdict = partial_with_coverage_exclusions`。

### Caveats

- 这是 per-cell B12 报告的 aggregate，**不**是 promotion step、**不**是 default change、
  **不**是 runtime-clean general algorithm claim、**不**是 `EvidenceCore` semantics change。
  `promotion_ready=false`、`default_should_change=false`、
  `evidencecore_semantics_changed=false`、`policy_search_performed=false`、
  `runtime_clean_policy_supported=false`、`new_provider_calls=0`、`candidate_not_fact=true`。
- 4 个 `ts_vite` 排除是覆盖缺口（无 remote LLM snippets），**不**是 B12 mechanism failure。
  机制 claim 仅限定在 28 个 analyzable cells 上。
- 按策略从不发出全局 `supported` verdict：存在覆盖排除时 verdict 为
  `partial_with_coverage_exclusions`；即使 32/32 也仍为 `partial`（不过度声称 H1/H2/H3）。
- H2 因果归因受限于每 cell 单一冻结 E seed（`e_random_seed=20260618`）；seed-averaging
  暂缓。
- 建议下一步：B13 distributionally robust policy search **需谨慎**（B13 绝不可被当作被
  B12 supported verdict 授权），或未来重跑 B12 matrix 以闭合 `ts_vite` 覆盖缺口。

## 2026-06-19 — C3 Budgeted Evidence Acquisition v0（Replay Evaluator）

### Objective

将 C3 Budgeted Evidence Acquisition v0 实现为基于 C1 私有记录适配器的真实
replay policy 实验，而非 skeleton。C3 把一个冻结的、可解释的候选策略集合
（每个策略只是一个 runtime-clean `route_features` 字典的纯函数）replay 到
P21 的 per-strategy outcomes 上，计算 budgeted evidence utility，并在
common-complete 分母下将候选策略与 P25 和 balanced_v1 两个 baseline 比较。

### Implementation

- 新 evaluator `eval/c3_budgeted_evidence_acquisition.py`（纯 Python；使用
  `eval/c1_private_records.py`）。模式：`--self-test`（仅 synthetic fixture，
  无 empirical claim）、`--regenerate-artifacts`（canonical synthetic spec +
  self-test 报告）、`--input <path>`（真实 aggregate-only replay 报告；
  `replay_source="ci_ephemeral_records"`）。
- 新冻结 algorithm spec
  `artifacts/c3_budgeted_evidence_acquisition/c3_budgeted_evidence_acquisition.algorithm.json`
  （确定性、稳定 sha256
  `9c1b0842e030c95d1e54cd2bfe97b0bdf39335560172de8e25d3677ff8e5e8d2`）。
- 新 synthetic self-test 报告
  `artifacts/c3_budgeted_evidence_acquisition/c3_budgeted_evidence_acquisition_report.json`。
- 新文档 `docs/en/c3-budgeted-evidence-acquisition.md` 和
  `docs/zh/c3-budgeted-evidence-acquisition.md`。
- CI workflow 集成于 `.github/workflows/real-provider-benchmark.yml`：在 B12
  消费 `$P25_RECORDS` 之后、`rm -f "$P25_RECORDS"` 之前，C3 运行
  `python3 eval/c3_budgeted_evidence_acquisition.py --input "$P25_RECORDS"
  --out artifacts/real_provider_ci/c3_budgeted_evidence_acquisition_report.json`。
  per-cell C3 只输出充分统计信息且不声明 winner。

### Frozen design（不从 outcome 调参）

- 允许的 runtime features（冻结 allowlist，共 10 个）：`query_noise`、
  `candidate_support_exists`、`local_anchor`、`rrf_backed_by_anchor`、
  `candidate_count`、`symbol_regex_agree_file`、`symbol_regex_agree_span`、
  `rrf_anchor_agree_file`、`rrf_anchor_agree_span`、`dense_support_present`。
  缺失 feature 视为 false / 0；只输出 aggregate `feature_presence_counts`
  （raw `route_features` 字典是 forbidden public key）。
- 允许的 candidate actions（冻结）：`candidate_baseline`、
  `weak_candidate_only`、`llm_span_narrow`、`llm_filter`、
  `llm_abstain_filter`。P25 和 balanced_v1 **不**是 candidate actions；它们
  只作 baseline，标记 `runtime_clean_candidate_policy=false`、
  `benchmark_label_taint=true`。
- 冻结候选策略集合（6 个，可解释，**不**从 outcome 派生）：`local_only`、
  `weak_on_noise_else_local`、`span_narrow_on_anchor_else_local`、
  `filter_on_noise_else_span_narrow_on_anchor_else_local`、
  `abstain_filter_on_disagreement_else_span_narrow_on_anchor_else_local`、
  `weak_on_disagreement_span_on_anchor_else_local`。
- Objective 常量：`lambda=1.0`、`mu=1.0`、`cost_weight=0.1`。
  `utility = span_f0_5 - lambda*added_false_span -
  mu*primary_false_positive_rate - cost_weight*model_calls`。
- 覆盖：所有候选策略和 baseline 使用 common-complete 分母；若任一所选 action
  outcome 缺失则排除该记录。`complete_records==0` =>
  `status=coverage_insufficient`。per-cell 报告**不**声明 winner：
  `winner_declared=false`、`cell_diagnostic_rank_only=true`、
  `candidate_selection_deferred_to_matrix_combiner=true`。

### Runtime-clean 硬规则

候选策略**只**接收投影后的 `route_features` 字典，**绝不**接收
`PrivateRecord`，**绝不**读取 `task_bucket` / `task_risk_tags` / `has_gold`
/ `score_group` / `outcomes` / `task_id` / `repo_id` / `model_family` /
`language` / 私有 hash。evaluator 通过**真实的 PrivateRecord 字段 scrub 测试**
验证 routing invariance（scrubbed 副本中每个非 `route_features` 字段被替换为
保证与原始值不同的 sentinel/permuted 值），并暴露
`selected_actions_invariant_under_private_field_permutation=true` 和
`runtime_clean_policy_inputs_only=true`。

### Safety invariants

- `empirical_algorithm_experiment_performed=true` 和
  `policy_search_or_enumeration_performed=true` 仅在真实记录的 `--input`
  下为 true（synthetic self-test 两者皆 false）。
- `replay_only=true`、`remote_calls_by_c3=0`、`model_calls_by_replay=0`、
  `promotion_ready=false`、`default_should_change=false`、
  `evidencecore_semantics_changed=false`、
  `aggregate_only_public_artifact=true`。
- Forbidden public keys 扫描拒绝 `task_id` / `repo_id` / `run_id` /
  `private_record_hash` / `route_features` / `outcomes` / `p31_score_gold` /
  `p31_candidate_pools` / `p33b_anchor_subtypes` / `task_risk_tags` / `path`
  / `span` / `content_sha` / `query` / `raw_query` / `snippet` / `prompt`
  / `response` / `provider_key` / `api_key` / `base_url` / `score_group`
  / `has_gold` / `strategy_results` / `source_ordinal` / `candidate_id` /
  `record_hash` / `test_id` / `private_label` / `private_labels` / `label`
  / `labels` / `gold_spans` / `hash` / `digest` / `task_bucket`。扫描对 key 名
  为精确匹配，因此安全的 metric 名如 `added_false_span` /
  `primary_false_positive_rate` / `added_gold_span` 仍然允许。aggregate
  `model_family` / `language` 计数允许；v0 省略 `task_bucket` 计数。

### Self-test

`python3 eval/c3_budgeted_evidence_acquisition.py --self-test` 通过（11 项
检查：forbidden 扫描、spec hash 稳定、action/feature allowlist 冻结、
objective 常量冻结、runtime-clean invariance（真实 PrivateRecord 字段 scrub
测试）、P25/balanced 非 candidate policy、synthetic-fixture mechanics、
synthetic C1 payload 的 `--input` 完整模式、missing-outcome =>
`coverage_insufficient`、无 per-cell winner、磁盘 artifact 与内存构建一致
（drift 检测）、docs 路径存在）。self-test 严格只读，**绝不**修改 checked-in
artifact；使用 `--regenerate-artifacts` 更新 canonical artifact。

### Caveats

- C3 是 budgeted replay policy 实验，**不**是 promotion step、**不**是
  default change、**不**是 `EvidenceCore` 语义变更、**不**是 runtime-clean
  general algorithm 证明。`promotion_ready=false`、
  `default_should_change=false`、`evidencecore_semantics_changed=false`。
- per-cell C3 **不**声明 winner；候选选择推迟到 matrix combiner。诊断 rank
  仅为排序，不是 claim。
- synthetic self-test fixture 不赋予任何 empirical support；只有真实 P21
  记录的 `--input` 才设置 `empirical_algorithm_experiment_performed=true`。
- 冻结候选策略集合是枚举，不是调参搜索；不从 outcomes 调参阈值或策略。

## 2026-06-19 — C3 Budgeted Evidence Acquisition Matrix Combiner

### 目标

为 C3 官方 matrix 构建 committed aggregate-only combiner，仿照
`eval/b12_matrix_combiner.py`，但限定于 C3 budgeted evidence acquisition 的
per-cell 报告。将 28 个可分析 per-cell `c3-budgeted-evidence-acquisition-report-v0`
artifact 加上 4 个 `ts_vite` coverage exclusion 合并为单个派生 aggregate，输出仅
diagnostic-rank，**不**声明 winner/selection/promotion/default。

### 实现

- 新 combiner `eval/c3_matrix_combiner.py`（纯 Python；导入
  `eval/b6_lite_interpretable_policy_search.py` 以复用 `_walk_forbidden`
  公开输出扫描）。模式：`--self-test`（合成 2-cell + 1-exclusion fixture，无
  私有记录），以及真实 combine（`--artifacts-dir` + `--manifest` + `--out`）。
- 输入：per-run artifact 位于
  `<run_id>/real-provider-p21_llm_rich-<run_id>/artifacts/real_provider_ci/c3_budgeted_evidence_acquisition_report.json`，
  以及 32 个规划 cell 的扁平 manifest（4 个 `ts_vite` cell 为
  `status=planned_exclusion_coverage_insufficient` 且 `run_id=null`，作为 coverage
  exclusion 计入；28 个 cell 有真实 run_id）。
- 新 artifact
  `artifacts/c3_budgeted_evidence_acquisition/c3_matrix_aggregate_report.json`
  （canonical C3 matrix aggregate；`generated_by=c3_matrix_combiner`、
  `schema_version=c3-budgeted-evidence-acquisition-matrix-report-v0`、
  `claim_level=budgeted_matrix_aggregate_public_v0`）。
- 更新文档 `docs/en/c3-budgeted-evidence-acquisition.md` 与
  `docs/zh/c3-budgeted-evidence-acquisition.md`，新增“Matrix combiner”章节。

### per-cell 校验（每个 included 报告都强制执行）

每个 included C3 per-cell 报告都校验：
`schema_version=c3-budgeted-evidence-acquisition-report-v0`、
`generated_by=c3_budgeted_evidence_acquisition`、
`replay_source=ci_ephemeral_records`、
`empirical_algorithm_experiment_performed=true`、`winner_declared=false`、
`cell_diagnostic_rank_only=true`、
`candidate_selection_deferred_to_matrix_combiner=true`、
`runtime_clean_policy_inputs_only=true`、
`selected_actions_invariant_under_private_field_permutation=true`、
`promotion_ready/default_should_change/evidencecore_semantics_changed=false`、
`remote_calls_by_c3=0`、`model_calls_by_replay=0`、
`aggregate_only_public_artifact=true`、per-cell safety invariant
`forbidden_public_keys_scanned=true` 与
`no_raw_path_digest_provider_strings=true`、`complete_records>0`、
`incomplete_record_count==0`，以及与 C3 spec 逐字节匹配的冻结
`candidate_policy_ids` / `action_set`。共享 `_walk_forbidden` 扫描在每个输入上
重跑。任何预期的 included run 若缺失报告则硬失败，除非 manifest 标记其为
coverage-insufficient。

### 汇总机制

- `planned_cells=32`、`included_cells=28`、`coverage_excluded_cells=4`、
  `total_records` / `complete_records` = 336 / 336（跨 cell 求和）。
- `per_candidate_policy`：对 6 个冻结候选策略 id，按 `complete_records` 加权的每个
  安全 metric（`span_f0_5`、`added_gold_span`、`added_false_span`、
  `primary_false_positive_rate`、`model_calls`、`utility`）的均值，以及 sum 汇总。
- `baseline_aggregates`（`p25`、`balanced_v1`，同样加权）。
- `deltas_vs_p25` 与 `deltas_vs_balanced_v1`：per-cell per-policy delta 的记录
  加权均值。
- `diagnostic_rank_only_global`：候选策略按 aggregate mean `utility` 降序排序；
  `winner_declared=false`、
  `candidate_selection_deferred_to_future_preregistered_matrix=true`、每个策略
  `candidate_selected=false`。仅排序——无 winner、无 freeze、无选择。
- `runtime_feature_coverage`：跨 cell 的 `feature_presence_counts` 求和。
- `coverage_exclusion_summary` / `coverage_exclusion_reason_counts`：按
  `(repo_slice_id, model_family, reason)` 计数；无 run ID。
- `artifact_manifest_summary`：仅计数（无 sha256 摘要，以避免在公开
  forbidden-value 扫描中出现 hash 形态的值）。

### 官方 matrix 结果（28 可分析 + 4 排除）

- `status=matrix_aggregate_ok_with_exclusions`。
- `diagnostic_rank_only_global[0]=weak_on_disagreement_span_on_anchor_else_local`
  （mean `utility=-0.167791`、mean `model_calls=0.511905`）；其后：
  `abstain_filter_on_disagreement_else_span_narrow_on_anchor_else_local`
  （`utility=-0.199933`）、`span_narrow_on_anchor_else_local`
  （`utility=-0.268981`）、`filter_on_noise_else_span_narrow_on_anchor_else_local`
  （`utility=-0.270171`）、`weak_on_noise_else_local`（`utility=-1.578684`）、
  `local_only`（`utility=-1.638208`）。**未声明任何 winner。**
- baselines：`p25` mean `utility=-0.227093`（mean `model_calls=0.964286`）；
  `balanced_v1` mean `utility=-0.146141`（mean `model_calls=0.630953`）。
- diagnostic 排名第一相对 `p25` 的 delta：
  `weak_on_disagreement_span_on_anchor_else_local`
  （`Δutility=+0.059303`、`Δmodel_calls=-0.452381`）。
- `runtime_feature_coverage`：`local_anchor=280`、
  `rrf_backed_by_anchor=172`、`rrf_anchor_agree_file=172`、
  `rrf_anchor_agree_span=172`、`candidate_count=123`、
  `candidate_support_exists=123`、`dense_support_present=123`、
  `symbol_regex_agree_file=56`、`symbol_regex_agree_span=56`、`query_noise=28`。

### 安全不变量（matrix aggregate）

- `aggregate_only_public_artifact=true`、`promotion_ready=false`、
  `default_should_change=false`、`evidencecore_semantics_changed=false`、
  `runtime_clean_candidate_evaluated=true`、`winner_declared=false`、
  所有策略 `candidate_selected=false`、
  `candidate_selection_deferred_to_future_preregistered_matrix=true`、
  `remote_calls_by_combiner=0`、`model_calls_by_combiner=0`、
  `no_run_ids_emitted=true`、`no_task_ids_in_artifact=true`、
  `no_paths_spans_hashes_snippets_prompts_responses=true`、
  `no_forbidden_public_keys=true`、
  `no_raw_path_digest_provider_strings=true`。最终输出上运行共享
  `_walk_forbidden` 扫描（`integrity.forbidden_public_key_scan_clean=true`）。

### self-test

`python3 eval/c3_matrix_combiner.py --self-test` 通过（5 项：含加权均值/delta/
baseline 汇总 + diagnostic rank + coverage exclusion 计数 + no-winner/
no-selection 的 happy path；forbidden-key 注入拒绝；缺失报告硬失败；无 manifest
真实路径 fail-closed；空输入阻断）。self-test 严格只读且仅用合成 fixture；不赋予
任何 empirical support。

### 注意事项

- C3 matrix aggregate **仅 diagnostic-rank**。它**不**是 promotion 步骤、**不**是
  default 变更、**不**是 `EvidenceCore` 语义变更、**不**是 runtime-clean 通用算法
  证明、**不**是候选选择。
- `diagnostic_rank_only_global` 仅为排序；排名第一的策略**并不**是被选中的策略。
  选择推迟到未来的 preregistered matrix。
- 4 个 `ts_vite` coverage exclusion
  （`coverage_insufficient_no_remote_llm_snippet`）仍是未闭合的 coverage 缺口；
  它们**不**是 C3 机制失败。
- 公开 repo slice ID 与 model family 名以 `repo_slice_id` / `model_family` 发布
  （与 B11/B12 一致），而非 raw `repo_id`；coverage exclusion 不含 run ID。

## 2026-06-20 — C4 外部 Benchmark Adapter —— Schema 就绪 v1

### 目标

为 ContextBench 与 SWE-Explore 实现一个真实（非 skeleton-only）的外部
benchmark adapter / schema 就绪层，产出一份 aggregate-only 公共 artifact，记录
adapter/schema 就绪状态而不持久化任何行级 benchmark 内容。C4.1 **不是**外部
benchmark 性能评估，**不是** benchmark 结果，也**不是** promotion 或默认策略
变更。

### 实现

- 新增 evaluator `eval/c4_external_benchmark_adapters.py`，提供 argparse CLI：
  `--self-test`、`--benchmark {contextbench,swe_explore,all}`、
  `--schema-smoke`、`--limit`（默认 3，硬上限 10）、`--out`。默认调用从内置
  已知 source/schema 元数据加合成 self-test 状态生成 canonical aggregate 报告，
  无网络。
- Canonical aggregate-only artifact
  `artifacts/c4_external_benchmark_adapters/c4_external_benchmark_adapter_report.json`
  （schema `c4_external_benchmark_adapters.v1`、
  `claim_level=adapter_schema_readiness_only`）。
- ContextBench 规格：dataset_id `Contextbench/ContextBench`；configs
  `default/train` 1136、`contextbench_verified/train` 500；仅 schema 字段名
  `instance_id`、`original_inst_id`、`repo`、`repo_url`、`language`、
  `base_commit`、`gold_context`、`patch`、`test_patch`、`problem_statement`、
  `f2p`、`p2p`、`source`；license `unknown_dataset_license`；行级再分发禁用。
- SWE-Explore 规格：dataset_id `SWE-Explore-Bench/SWE-Explore-Bench`；config
  `default/train` 848；仅 schema 字段名 `instance_id`、`repo_path`、`repo_dir`、
  `ground_truth`、`read_step_info`、`meta`、`dataset`；私有类别包含
  `ground_truth.*`、`read_step_info.*`、repo 路径、file maps、line ranges；
  license `cc-by-nc-nd-4.0`；行级再分发与派生 label 发布均禁用。
- 合成内存行 adapter（`adapt_contextbench_row`、`adapt_swe_explore_row`）将
  `public_task`（aggregate-safe 元数据：存在性布尔、字段计数、仅类别桶）与
  `private_label`（行级 payload，永不序列化）分离。两者均不会以行级值序列化
  到公共 artifact。
- Line range 归一化（`normalize_line_range`）接受 list/tuple/dict/`"S-E"`/
  `"S:E"` 形式；拒绝 `start > end`、`start < 1`、非整型、布尔值。仅用于合成
  self-test / 私有内存校验。
- 严格 fail-closed forbidden scanner（`_scan_forbidden`）禁止任何位置作为
  dict key 出现的敏感 key 名，并禁止 URL/hex-digest/secret-like/path-like/
  multiline/long-string 值；允许仅 schema 字段名列表出现在显式容器
  （`field_names_schema_only`、`private_field_categories_detected`）下；将已知
  安全的 provenance 值路径（`spec_hash`、`generated_by`、`dataset_id`、
  `schema_version`、`claim_level`）加入 allowlist。artifact 仅记录
  `forbidden_scan: {status: "pass"}` 加 category/path 计数 —— 从不记录泄漏值。
- 仅通过 stdlib `urllib`（无新依赖）的有界 HF datasets-server schema smoke，
  显式有界超时，以 `/splits` 作为 `/first-rows` 尝试的 source of truth。对
  `/first-rows`，仅解析 features/schema 与行计数/截断布尔；原始行仅保留在本地，
  永不返回或写入。网络/HF 失败时，产生状态 `unavailable` 或 `partial`，并附带
  sanitized reason category/status code —— 无原始响应体。
- 确定性 `spec_hash`（排除时间戳/网络/原始行/本地路径的 canonical spec JSON 的
  SHA-256）：
  `9de6609359aa8de4cfe7ca50b1388ebc51d9ee2f016bb3bc6c34e253da5ef153`。

### 结果

```text
python3 -m py_compile eval/c4_external_benchmark_adapters.py   => PASS
python3 eval/c4_external_benchmark_adapters.py --self-test     => PASS（9 组）
python3 eval/c4_external_benchmark_adapters.py \
  --out artifacts/c4_external_benchmark_adapters/\
c4_external_benchmark_adapter_report.json                     => PASS（forbidden_scan: pass）
python3 eval/c4_external_benchmark_adapters.py \
  --benchmark contextbench --schema-smoke --limit 3 \
  --out /tmp/c4_contextbench_schema.json                       => PASS
  (forbidden_scan: pass, new_network_calls: 4, first_rows_status: pass,
   row_level_data_returned: false)
python3 eval/c4_external_benchmark_adapters.py \
  --benchmark swe_explore --schema-smoke --limit 3 \
  --out /tmp/c4_swe_explore_schema.json                        => PASS
  (forbidden_scan: pass, new_network_calls: 3, first_rows_status: pass,
   row_level_data_returned: false)
```

Self-test 组（9）：ContextBench adapter 分离、SWE-Explore adapter 分离、line
range 归一化、forbidden scan 拒绝注入、no-claim 标志全为 false、spec hash 确
定性、aggregate-only 报告、forbidden scan 在生成时阻断泄漏、schema smoke 报告
形态。

### 注意事项

- C4.1 仅是 adapter/schema 就绪。它**不**校验行级语义、label 或下游 agent 价值。
  schema smoke 仅确认公共 HF datasets-server schema 端点可达且可解析；它**不**确
  认 benchmark 质量、label 正确性或对任何下游评估的适用性。
- ContextBench 数据集 license 未知，即使代码仓库为 Apache-2.0；行级再分发被禁用。
- SWE-Explore HF 数据集 license 为 `cc-by-nc-nd-4.0`；行级再分发与派生 label
  发布均被禁用。
- 合成 self-test 行不提供任何经验支持。
- 所有 no-claim 标志保持 false：`promotion_ready=false`、
  `default_should_change=false`、`evidencecore_semantics_changed=false`、
  `runtime_clean_general_algorithm_claimed=false`、
  `downstream_agent_value_proven=false`、`ood_temporal_supported=false`、
  `quiver_systems_supported=false`。C4.1 不产生 promotion、不产生默认策略变更、
  不产生 EvidenceCore 语义变更、不产生 runtime-clean 通用算法声明、不产生下游
  agent 价值声明、不产生 OOD 时间声明，也不产生 QuIVer systems 声明。

## 2026-06-20 — C4.2 ContextBench Verified Subset Row-Mapping Smoke

### 目标

新增一个针对 ContextBench verified subset
（`contextbench_verified/train`）的有界**真实 row-mapping smoke**：读取真实 HF
datasets-server `/first-rows` 预览行，在函数作用域内通过现有
`adapt_contextbench_row` adapter 适配每一行，在内存中校验
`public_task` / `private_label` 分离，并输出 aggregate-only artifact。真实行
仅存在于函数作用域/内存；不持久化任何原始行、样本行、行值、行级 hash、path、
span、line range、snippet、problem statement、patch/test、prompt/response、
provider payload、content_sha 或原始 HF payload。C4.2 仅是 adapter/row-mapping
就绪，**不**是 benchmark performance/result。

### 实现

- `eval/c4_external_benchmark_adapters.py` 新增 CLI 标志：
  `--row-map-smoke`（与 `--self-test` 和 `--schema-smoke` 互斥）、
  `--row-limit`（默认 10，硬上限 20）、`--config`（默认
  `contextbench_verified`；仅支持该 config）、`--split`（默认 `train`）。
  未设置 `--out` 时默认为 C4.2 artifact 路径，从而不覆盖 C4.1 canonical 报告。
- `_extract_first_rows` 在函数作用域内将 datasets-server `/first-rows` payload
  解析为 (rows, field_names, truncated)。原始行仅返回给调用方用于立即在作用域内
  适配与丢弃。
- `_build_row_map_summary` 遍历有界行，对每行调用
  `adapt_contextbench_row(row)`，断言 public task 无私有 attr，按字段名计数非空
  field presence、public-task presence 布尔、私有字段类别 presence 与固定失败
  类别。不输出任何行级值、hash、path、span 或 snippet。
- `_row_map_smoke_contextbench_verified` 调用 `_http_get_json()` 获取真实
  `/first-rows` 端点，提取行，限制为 `row_limit`，适配，立即丢弃原始行 + payload，
  构建 aggregate 摘要，并运行 fail-closed forbidden scan。网络/HF 失败时，输出
  sanitized `unavailable` 状态并附带 `endpoint_unavailable` 失败类别 —— 无原始
  响应体。
- forbidden scanner 扩展 `SCHEMA_KEY_CONTAINER_KEYS` allowlist
  （`field_presence_counts`、`public_task_presence_counts`、
  `private_field_presence_counts`、`failure_category_counts`），使计数容器可使
  用仅 schema 字段名字符串作为计数桶 key。scanner 仍禁止公共输出中任何位置的行级
  值、path、span、hash、URL 与 secret。
- 新增无网络 self-test `_self_test_row_map_smoke_aggregate_only`：用 sentinel
  私有值（`SECRET_REPO_SENTINEL`、`SECRET_PATCH_SENTINEL` 等）构建合成行，运行
  aggregator，断言报告 JSON 中不包含任何 sentinel、forbidden scan 通过、注入的
  `"12-34"` line range 被拒绝。新增 `_self_test_row_map_smoke_no_rows_unavailable`
  校验零行时为 `unavailable` 状态并附带 `no_rows_returned` 失败类别。

### 结果

```text
python3 -m py_compile eval/c4_external_benchmark_adapters.py   => PASS
python3 eval/c4_external_benchmark_adapters.py --self-test     => PASS（12 组）
python3 eval/c4_external_benchmark_adapters.py \
  --row-map-smoke --benchmark contextbench \
  --config contextbench_verified --split train --row-limit 10 \
  --out /tmp/c4_contextbench_row_map.json                       => PASS
  (rows_seen: 10, rows_mapped: 10, rows_failed: 0, status: pass,
   forbidden_scan: pass, private_label_isolation_verified: true)
python3 eval/c4_external_benchmark_adapters.py \
  --row-map-smoke --benchmark contextbench \
  --config contextbench_verified --split train --row-limit 10 \
  --out artifacts/c4_external_benchmark_adapters/\
c4_contextbench_verified_row_mapping_report.json              => PASS
  (rows_seen: 10, rows_mapped: 10, rows_failed: 0, status: pass,
   forbidden_scan: pass, private_label_isolation_verified: true,
   adapter_assertions_passed: true,
   raw_rows_persisted: false, row_level_values_emitted: false,
   row_level_hashes_emitted: false, raw_response_stored: false)
```

所有 13 个 schema 字段名在全部 10 行中非空；所有 5 个 public-task presence
布尔在全部 10 行中为 True；所有 12 个私有字段类别在全部 10 行中非空。未持久化
任何行级值、hash、path、span、snippet、problem statement、patch/test、
prompt/response、provider payload、content_sha 或原始 HF payload。

### 注意事项

- C4.2 仅是 adapter/row-mapping 就绪。它**不**校验行级语义、label 或下游 agent
  价值。row-map smoke 仅确认 adapter 边界成立（public task 无私有 attr；private
  label 仅在内存中保留私有值）；它**不**确认 benchmark 质量、label 正确性或对任
  何下游评估的适用性。
- ContextBench 数据集 license 未知；行级再分发被禁用。
- 所有 no-claim 标志保持 false：`promotion_ready=false`、
  `default_should_change=false`、`evidencecore_semantics_changed=false`、
  `runtime_clean_general_algorithm_claimed=false`、
  `downstream_agent_value_proven=false`、`ood_temporal_supported=false`、
  `quiver_systems_supported=false`。C4.2 不产生 promotion、不产生默认策略变更、
  不产生 EvidenceCore 语义变更、不产生 runtime-clean 通用算法声明、不产生下游
  agent 价值声明、不产生 OOD 时间声明，也不产生 QuIVer systems 声明。

## 2026-06-20 — C4.3 SWE-Explore Row-Mapping / Line-Budget Aggregate Smoke

### 目标

新增一个针对 SWE-Explore（`default/train`）的有界**真实 row-mapping /
line-budget shape observation smoke**：读取真实 HF datasets-server
`/first-rows` 预览行，在函数作用域内通过现有 `adapt_swe_explore_row` adapter
适配每一行，在内存中校验 `public_task` / `private_label` 分离，并输出含
line-budget shape observation 计数/布尔的 aggregate-only artifact。真实行仅存
在于函数作用域/内存；不持久化任何原始行、样本行、行值、行级 hash、文件路径/
文件名、line range/span/region、patch/test_patch/code snippet、modified/core
文件名、meta 原始内容、label/派生 label、provider payload、content_sha 或原始
HF payload。C4.3 仅是 adapter/row-mapping 就绪，**不**是 benchmark
performance/result。

### 实现

- 扩展 `eval/c4_external_benchmark_adapters.py`，新增 SWE-Explore row-map 常量：
  `SWE_ROW_MAP_SCHEMA_VERSION`（`c4_swe_explore_row_mapping.v1`）、
  `SWE_ROW_MAP_DEFAULT_OUT`、`SWE_ROW_MAP_ALLOWED_CONFIGS={"default"}`、
  `SWE_ROW_MAP_MODE`、`_SWE_PUBLIC_TASK_PRESENCE_KEYS`、
  `_SWE_PRIVATE_LABEL_FIELDS`（14 个类别，含嵌套 `ground_truth_patch`、
  `ground_truth_modified_files`、`read_step_info_file_maps` 等）、
  `_SWE_LINE_BUDGET_READINESS_KEYS`。在 `ROW_MAP_FAILURE_CATEGORIES` 中添加
  `line_budget_shape_error`。在 `SCHEMA_KEY_CONTAINER_KEYS` 中添加
  `line_budget_readiness`。
- 新增函数：`_swe_gt_has`、`_swe_rsi_has`（嵌套 presence 检查）、
  `_swe_row_has_line_ranges`、`_swe_row_has_region_like`（仅 shape 布尔，从不
  是值）、`_build_swe_row_map_summary`（遍历有界行，调用
  `adapt_swe_explore_row`，断言 public task 无私有 attr，计数 field/public-task/
  private-field presence、line-budget readiness 计数/布尔、固定失败类别）、
  `_row_map_smoke_swe_explore`（真实 HF `/first-rows` 调用，提取行，限制，适配，
  丢弃原始，构建摘要，fail-closed forbidden scan，网络失败时 sanitized
  `unavailable`）、`build_swe_row_map_smoke_report`。
- CLI 扩展：`--row-map-smoke` 现按 `--benchmark` 分发（`contextbench` → C4.2；
  `swe_explore` → C4.3）。row-map smoke 拒绝 `--benchmark all`。`--config` 默认
  按 benchmark 区分（contextbench 为 `contextbench_verified`；swe_explore 为
  `default`）。`--out` 默认按 benchmark 区分。现有 ContextBench C4.2 命令不变。
- 新增无网络 self-test：`_self_test_swe_row_map_smoke_aggregate_only`（sentinel
  私有值 `SECRET_REPO_PATH_SENTINEL`、`SECRET_PATCH_SENTINEL`、文件路径、line
  range、instance ID、read_step_info；断言报告 JSON 中无 sentinel、forbidden
  scan 通过、注入的 `"12-34"` 被拒绝）、
  `_self_test_swe_row_map_line_budget_only_counts`（已知合成 line-range/file-
  list 结构给出正确 aggregate 计数，但 JSON 中无 path/range 字符串）、
  `_self_test_swe_row_map_isolation_failure_fail_closed`（坏的 SWE public task
  暴露 `repo_path`/`ground_truth`；断言 `fail_schema_contract`、rows_mapped=0、
  rows_failed>=1、safety bools false、`private_field_leak>=1`、sentinels 不输
  出）。self-test 现有 15 组。

### 结果

```text
python3 -m py_compile eval/c4_external_benchmark_adapters.py   => PASS
python3 eval/c4_external_benchmark_adapters.py --self-test     => PASS（15 组）
python3 eval/c4_external_benchmark_adapters.py \
  --row-map-smoke --benchmark contextbench \
  --config contextbench_verified --split train --row-limit 10 \
  --out /tmp/c4_contextbench_row_map.json                       => PASS（回归）
python3 eval/c4_external_benchmark_adapters.py \
  --row-map-smoke --benchmark swe_explore \
  --config default --split train --row-limit 10 \
  --out /tmp/c4_swe_row_map.json                                => PASS
  (rows_seen: 10, rows_mapped: 10, rows_failed: 0, status: pass,
   forbidden_scan: pass, private_label_isolation_verified: true,
   adapter_assertions_passed: true)
python3 eval/c4_external_benchmark_adapters.py \
  --row-map-smoke --benchmark swe_explore \
  --config default --split train --row-limit 10 \
  --out artifacts/c4_external_benchmark_adapters/\
c4_swe_explore_row_mapping_report.json                       => PASS
  (rows_seen: 10, rows_mapped: 10, rows_failed: 0, status: pass,
   forbidden_scan: pass, private_label_isolation_verified: true,
   adapter_assertions_passed: true,
   raw_rows_persisted: false, row_level_values_emitted: false,
   row_level_hashes_emitted: false, raw_response_stored: false,
   derived_labels_published: false)
```

所有 7 个 SWE schema 字段名在全部 10 行中非空；所有 5 个 public-task presence
布尔在全部 10 行中为 True。嵌套私有类别（`ground_truth_patch`、
`ground_truth_modified_files` 等）在真实 HF `default/train` 预览行中被观察到
为缺失 —— 这是准确的 schema 观察，不是错误。artifact 记录
`budget_evaluation_shape_supported=false`，所以 C4.3 是 row-mapping/privacy
boundary smoke 加一个负向 line-budget shape observation，不是正向 line-budget
readiness 证据。未持久化任何行级值、hash、文件路径、line range、span、snippet、
patch/test、meta 原始内容、label、provider payload、content_sha 或原始 HF payload。

### 注意事项

- C4.3 是 adapter/row-mapping readiness 加一个负向 line-budget shape observation
  （`budget_evaluation_shape_supported=false`）。它**不**校验
  行级语义、label 或下游 agent 价值。row-map smoke 仅确认 adapter 边界成立
  （public task 无私有 attr；private label 仅在内存中保留私有值）；它**不**确认
  benchmark 质量、label 正确性或对任何下游评估的适用性。不做任何性能声明。
- SWE-Explore HF 数据集 license 为 `cc-by-nc-nd-4.0`；行级再分发与派生 label
  发布均被禁用。
- 所有 no-claim 标志保持 false：`promotion_ready=false`、
  `default_should_change=false`、`evidencecore_semantics_changed=false`、
  `runtime_clean_general_algorithm_claimed=false`、
  `downstream_agent_value_proven=false`、`ood_temporal_supported=false`、
  `quiver_systems_supported=false`。C4.3 不产生 promotion、不产生默认策略变更、
  不产生 EvidenceCore 语义变更、不产生 runtime-clean 通用算法声明、不产生下游
  agent 价值声明、不产生 OOD 时间声明，也不产生 QuIVer systems 声明。

## 2026-06-20 — C4.4 CORE-Bench Source Readiness / No-Go

### 目标

为 CORE-Bench（arXiv:2606.11864v1 —— "CORE-Bench: A Comprehensive Benchmark
for Code Retrieval in the Era of Agentic Coding"）产出一份 **source-readiness
no-go** artifact。实际 HF 数据集文件/schema 不可用，因此 C4.4 **不**声称 adapter
支持或 schema 就绪；它仅记录论文与 HF placeholder 已确认但数据集不可用。旧的
`siegelz/core-bench` 科学复现 benchmark 被显式消歧为错误目标。

### 实现

- 新增独立脚本 `eval/c4_core_bench_source_readiness.py`（纯 Python stdlib）。
  CLI：`--self-test`（无网络）、`--source-readiness`（默认模式，构建报告）、
  `--offline`（无网络 probe）、`--out`。
- 仅通过 stdlib `urllib` 的有界网络 probe（超时 10s）：HF dataset API、HF
  tree API、datasets-server `/is-valid`、`/splits`、`/first-rows`。不存储原始
  响应体；仅解析 aggregate 元数据与状态类别。
- 严格的 source-readiness 专用 forbidden scanner：允许官方 source-level URL
  （arXiv/HF placeholder/DOI），但禁止行级 URL、path、span、snippet、raw
  payload、content_sha、line range。placeholder repo 文件名
  （`.gitattributes`、`README.md`）仅在 `placeholder_repo_files_observed` 下
  允许。注入的 `src/foo.py`、`12-34`、`patch`、`content_sha`、多行 snippet 均
  被 scanner 拒绝。
- self-test（5 组，无网络）：错误目标消歧拒绝 `siegelz/core-bench`；offline
  no-go 报告构建状态非 pass/support；forbidden scan 拒绝 path/range/snippet/
  content_sha 注入；source URL 允许；报告 aggregate-only。

### 结果

```text
python3 -m py_compile eval/c4_core_bench_source_readiness.py   => PASS
python3 eval/c4_core_bench_source_readiness.py --self-test     => PASS（5 组）
python3 eval/c4_core_bench_source_readiness.py \
  --out artifacts/c4_external_benchmark_adapters/\
c4_core_bench_source_readiness_report.json                    => PASS
  (status: blocked_dataset_placeholder_empty,
   source_confirmation_status: paper_and_placeholder_confirmed_dataset_unavailable,
   forbidden_scan: pass, new_network_calls: 5)
```

已确认的外部发现：HF 数据集 repo `zhangfw123/CORE-Bench` 为 public、非 gated、
MIT-tagged；当前仅包含 `.gitattributes` 和 `README.md`（`sibling_count=2`）；
datasets-server `/is-valid` 返回 false；`/splits` 与 `/first-rows` 不可用。论文
aggregate facts（来自 arXiv Table 1）：3 个 level（code understanding 172,961
queries；issue-to-edit localization 5,061 queries / 632 repos / 52,712 qrels；
broader context retrieval 2,580 queries / 97 repos / 106,479 qrels）；共
180,602 queries；106,479 broader-context labels。

### 注意事项

- C4.4 仅是 source-readiness no-go。它**不**声称 adapter 支持或 schema 就绪。
  CORE-Bench HF 数据集当前为 placeholder（仅 `.gitattributes` + `README.md`）；
  实际数据集文件/schema 不可用。
- 所有 no-claim 标志保持 false：`promotion_ready=false`、
  `default_should_change=false`、`evidencecore_semantics_changed=false`、
  `runtime_clean_general_algorithm_claimed=false`、
  `downstream_agent_value_proven=false`、`ood_temporal_supported=false`、
  `quiver_systems_supported=false`。`adapter_support_claimed=false`、
  `schema_readiness_claimed=false`、`schema_smoke_passed=false`、
  `row_level_redistribution_allowed=false`、
  `derived_label_publication_allowed=false`。C4.4 不产生
  promotion、不产生默认策略变更、不产生 EvidenceCore 语义变更、不产生
  runtime-clean 通用算法声明、不产生下游 agent 价值声明、不产生 OOD 时间声明，
  也不产生 QuIVer systems 声明。

---

## 2026-06-20 — C4.5 RepoQA Source / Schema-Contract Readiness (Adapter Deferred)

### Objective

Produce a **source/schema-contract readiness with adapter deferred**
artifact for the EvalPlus **RepoQA** benchmark (task: Searching Needle
Function / SNF; arXiv:2406.06025; OpenReview `hK9YSrFuGf`). The official
schema contract is known from source/docs/loader, but full adapter/row-map
benchmark support is deferred pending a conscious
derived-qrels/version/license decision. C4.5 does NOT claim adapter
support, schema readiness, public row schema readiness, row-map smoke
pass, or benchmark result. No RepoQA entry is added to
`eval/c4_external_benchmark_adapters.py`.

### Implementation

- New standalone script `eval/c4_repoqa_source_readiness.py` (pure
  Python stdlib only). CLI: `--self-test` (no network, 9 groups),
  `--source-readiness` (default mode, builds report), `--offline` (no
  network probes), `--out`.
- Bounded network probes via stdlib `urllib` (timeout 10s): GitHub code
  repo API, GitHub release repo API, GitHub release API (tag
  `2024-06-23`) for asset metadata (name/size/content_type only; asset
  body NOT downloaded or decompressed), and HEAD/GET status probes for
  arXiv abs, homepage, OpenReview URLs. No raw response bodies are
  stored; only aggregate metadata and status categories are parsed.
- Strict source/schema-contract-specific forbidden scanner: allows
  official source-level URLs (arXiv/OpenReview/homepage/GitHub/GitHub-API/
  release-asset URLs) but forbids row-level URLs, paths, spans, snippets,
  raw payloads, content hashes, descriptions, questions, answers, raw
  JSON fragments, and line/byte ranges. Schema contract field names
  (`repo`, `content`, `needles`, `path`, `start_line`, `description`,
  etc.) are allowed ONLY as exact approved contract strings from
  `APPROVED_CONTRACT_STRINGS` inside explicit schema-contract containers
  (`repo_record_contract_fields`, `needle_contract_fields`,
  `task_record_contract_fields`, `model_output_contract_fields`,
  `adapter_derived_private_field_categories`,
  `schema_contract_field_names`); they are NEVER allowed as dict keys
  (the forbidden dict-key check is NOT relaxed inside schema-contract
  containers). Dict objects are forbidden inside schema-contract
  containers (row-like objects). Unapproved strings inside schema-contract
  containers are rejected. Injected `pytorch/pytorch`, `/src/main.py`,
  40-char commit SHA, `12-34` line range, multiline snippet,
  `{"repo":...}` raw JSON fragment, 64-char content hash, unapproved
  function name `compute_loss`, path-like `src/main.py`, and dict
  row-like object `[{"repo": "pytorch/pytorch"}]` all fail the scanner.
  Release asset metadata (name/size/tag) is allowed but content
  samples/digests are forbidden. Scanner is fail-closed before writing JSON.
- Self-test (9 groups, no network): wrong-target disambiguation; offline
  report shape (deferred status, not pass/support); schema-contract
  allowlist vs row-key leak; schema container strict pass/fail (approved
  strings pass; unapproved function/path values, dict row-like objects,
  and forbidden dict keys inside schema containers all fail); leak
  injection rejections (repo/function names, path, commit SHA, line/byte
  range, description/question/answer, snippet, raw JSON fragment, content
  hash/provider payload); release metadata allowed but content
  sample/digest forbidden; source URLs allowed; report aggregate-only;
  fail-closed generation.

### Findings

```text
python3 -m py_compile eval/c4_repoqa_source_readiness.py   => PASS
python3 eval/c4_repoqa_source_readiness.py --self-test     => PASS (9 groups)
python3 eval/c4_repoqa_source_readiness.py --offline \
  --out /tmp/c4_repoqa_offline.json                         => PASS
  (status: source_confirmed_schema_contract_ready_adapter_deferred,
   source_confirmation_status: offline_static_findings_only,
   forbidden_scan: pass, new_network_calls: 0)
python3 eval/c4_repoqa_source_readiness.py \
  --out artifacts/c4_external_benchmark_adapters/\
c4_repoqa_source_readiness_report.json                     => PASS
  (status: source_confirmed_schema_contract_ready_adapter_deferred,
   source_confirmation_status: sources_confirmed_via_probe,
   forbidden_scan: pass, new_network_calls: 6)
```

Confirmed external findings: code repo `evalplus/repoqa` and release repo
`evalplus/repoqa_release` are public Apache-2.0; current loader default
release tag `2024-06-23` with monolithic asset
`repoqa-2024-06-23.json.gz` (NOT downloaded or decompressed); paper
aggregate facts: 5 languages x 10 repos x 10 needles = 500 tasks over 50
repositories; version skew noted (paper 5 langs vs current loader 6 langs
with Go added). Official schema contract known from source/docs/loader:
repo record fields (`repo`, `commit_sha`, `entrypoint_path`, `topic`,
`content`, `dependency`, `needles`) and needle fields (`path`, `name`,
`start_byte`, `end_byte`, `start_line`, `end_line`, `description`).

### Caveats

- C4.5 is source/schema-contract readiness with adapter deferred. It
  does NOT claim adapter support, schema readiness, public row schema
  readiness, row-map smoke pass, or benchmark result. The official schema
  contract is known from source/docs/loader, but the monolithic JSON.gz
  is NOT downloaded or decompressed; no row-level data is read or
  persisted.
- All no-claim flags remain false: `promotion_ready=false`,
  `default_should_change=false`, `evidencecore_semantics_changed=false`,
  `runtime_clean_general_algorithm_claimed=false`,
  `downstream_agent_value_proven=false`, `ood_temporal_supported=false`,
  `quiver_systems_supported=false`. `adapter_support_claimed=false`,
  `schema_readiness_claimed=false`,
  `public_row_schema_readiness_claimed=false`,
  `schema_contract_readiness_claimed=true`,
  `row_map_smoke_attempted=false`, `row_map_smoke_passed=false`,
  `benchmark_result_claimed=false`,
  `release_asset_downloaded=false`,
  `release_asset_decompressed=false`,
  `release_asset_body_read=false`,
  `monolithic_json_rows_read=false`,
  `row_level_redistribution_allowed=false`,
  `derived_label_publication_allowed=false`. No promotion, no default
  change, no EvidenceCore semantics change, no runtime-clean general
  algorithm claim, no downstream agent value claim, no OOD temporal claim,
  and no QuIVer systems claim follows from C4.5.

## 2026-06-20 — D1 双评分相关性评测层脚手架

### 目标

产出**仅评测层脚手架**的双评分相关性诊断，将候选相关性拆分为
E-score（语义 / 直接作答证据）与 S-score（依赖 / 支撑结构证据）。
D1 **不得**改变检索器排序、pack 构建、模型调用、后端存储、默认
策略或 EvidenceCore 语义。它仅使用确定性合成 / 来源回溯 fixture；
真实 P21/private records 推迟到后续 D2 校准阶段。

### 实现

- 新增脚本 `eval/d1_dual_rubric_relevance.py`（纯 Python 标准库）。
  CLI：默认生成聚合报告至
  `artifacts/d1_dual_rubric_relevance/d1_dual_rubric_relevance_report.json`；
  `--self-test`（46 项检查，无 I/O）；`--out`。
- 声明级别 `eval_layer_rubric_scaffold_only`；rubric 版本
  `d1_dual_rubric_v0`。E-score（semantic direct match + answer-bearing
  span，范围 0..2）与 S-score（import + dependency-link + caller
  support，范围 0..3）为确定性小整数信号，非模型调用。
- 阈值 `E_HIGH >= 2`、`S_HIGH >= 2`，当 E 或 S `>= 1` 时为弱。
- 分类顺序 fail-closed：(1) 无效引用 / 来源-哈希过期 / 未引用 /
  显式无证据 -> `abstained`；(2) E 高且引用有效 ->
  `primary_evidence`；(3) S 高且 E 低于 high -> `dependency_support`；
  (4) 弱非零 E 或 S -> `weak_candidates`；(5) 否则 -> `abstained`。
  E 高优先于 S 高；E 高但引用无效者弃决。引用有效性是先于 E/S 桶
  分配触发的弃决门（依据 oracle 评审）。
- 规范桶 `primary_evidence`、`dependency_support`、`weak_candidates`、
  `abstained`；旧别名 `dependency_support -> supporting_only`、
  `abstained -> abstain`。
- 严格的禁止输出扫描器（写入 JSON 前 fail-closed）：拒绝禁止的
  字典键（path/span/line_range/start_line/end_line/content_sha/
  snippet/excerpt/candidate_text/query/task_id/repo_id/repo/label/
  qrels/gold/prompt/response 等）与禁止的取值模式（URL、32/40/64 字符
  十六进制摘要、类密钥串、类路径 `src/foo.py`、多行串、原始 JSON
  片段、原始行范围 `12-34`）；仅当非行级时允许通用聚合 reason_code
  串。自测包含禁止扫描注入与 fail-closed 生成。
- 仅聚合的公开产物字段：schema_version、generated_by、generated_at、
  claim_level、rubric_version、thresholds、classification_order、
  bucket_names、legacy_bucket_aliases、fixture_count、candidate_count、
  bucket_counts、e_score_band_counts、s_score_band_counts、
  reason_code_counts、self_test_checks、self_test_passed、
  forbidden_scan，以及扁平的 no-claim/安全标志。
- 既有 mode-only dirty 文件（`eval/ci_clone_and_lock_repo.py`、
  `eval/ci_make_repo_matrix.py`、
  `eval/p59_contrastive_pack_coverage_counterfactual.py`）**未被**触碰。

### 结果

```text
python3 -m py_compile eval/d1_dual_rubric_relevance.py   => PASS
python3 eval/d1_dual_rubric_relevance.py --self-test     => PASS (46/46 checks)
python3 eval/d1_dual_rubric_relevance.py \
  --out artifacts/d1_dual_rubric_relevance/\
d1_dual_rubric_relevance_report.json                     => PASS
  (status: scaffold_only_self_test_passed,
   forbidden_scan: pass, self_test_passed: true,
   fixture_count: 10, candidate_count: 10,
   bucket_counts: {primary_evidence: 2, dependency_support: 1,
     weak_candidates: 2, abstained: 5},
   e_score_band_counts: {none: 3, weak: 1, high: 6},
   s_score_band_counts: {none: 7, weak: 1, high: 2})
python3 scripts/validate_docs_i18n.py                     => PASS
```

10 个合成 fixture 的确定性聚合计数：bucket_counts
`primary_evidence=2, dependency_support=1, weak_candidates=2,
abstained=5`；E 分段 `none=3, weak=1, high=6`；S 分段 `none=7,
weak=1, high=2`；reason-code 计数合计 10。干净报告的 forbidden 扫描
通过且零违规。

### 注意事项

- D1 仅评测/诊断脚手架。它**不**改变运行时、检索器、pack、模型、
  后端或默认策略；它**不**改变 EvidenceCore 语义。它**不是**基准
  结果、**不是**下游 agent 价值声明、**不是** runtime-clean 通用
  算法声明、**不是** OOD 时间维度声明，**也不是** QuIVer 系统声明。
- 所有 no-claim 标志保持为 false：`promotion_ready=false`、
  `default_should_change=false`、`evidencecore_semantics_changed=false`、
  `runtime_clean_general_algorithm_claimed=false`、
  `downstream_agent_value_proven=false`、`ood_temporal_supported=false`、
  `quiver_systems_supported=false`；`runtime_behavior_changed=false`、
  `retriever_changed=false`、`pack_builder_changed=false`、
  `model_calls_changed=false`、`backend_changed=false`、
  `default_policy_changed=false`；`candidate_text_emitted=false`、
  `paths_or_spans_emitted=false`、`content_sha_emitted=false`、
  `raw_private_records_read=false`、`raw_private_records_persisted=false`、
  `row_level_hashes_emitted=false`、`per_candidate_rows_emitted=false`。
  `aggregate_only_public_artifact=true`、`diagnostic_only=true`、
  `not_evidence=true`。
- 读取真实 P21/private records 推迟到后续 D2 校准阶段；D1 fixture
  仅合成 / 来源回溯。

## 2026-06-20 — D2 双评分聚合校准（代理可映射性）

### 目标

产出 D1 之后有界的**代理**（proxy）聚合校准。D2 回答：现有本地
record/outcome 形状能否被映射到 `proxy_e_score` / `proxy_s_score`
聚合分段，而不暴露私有行或改变运行时行为？D2 **不得**声称真实 E/S
相关性已校准。它**不得**修改检索器排序、pack 构建、模型调用、后端
存储、默认策略或 EvidenceCore 语义。

### 实现

- 新增脚本 `eval/d2_dual_rubric_aggregate_calibration.py`（纯 Python
  标准库；仅在 D2b opt-in 路径中惰性导入 `c1_private_records`）。
  两种严格分离的模式：
  - **D2a（默认，已提交）**：公开聚合可映射性清单。仅读取已提交的
    C3/B12 公开聚合产物（通用标签 `c3_public_aggregate`、
    `b12_public_aggregate`；不序列化文件系统路径）。**不**读取
    private records。声明级别
    `public_aggregate_mappability_only`；状态
    `public_aggregate_mappability_only`；模式 `public_inventory`；
    `proxy_calibration_claimed=false`；
    `true_e_s_calibration_claimed=false`；
    `private_records_read=false`。
  - **D2b（可选，未提交，仅 /tmp）**：显式本地/私有代理校准冒烟。
    需要 `--allow-private-records --input <path> --limit N --out
    /tmp/...`。使用 C1 适配器
    （`c1_private_records.load_private_records`）瞬态读取 private
    records。绝不序列化输入路径/基名/大小/mtime。声明级别
    `dual_rubric_proxy_calibration_smoke_only`；
    `proxy_calibration_claimed=true`（冒烟已运行），但
    `true_e_s_calibration_claimed=false`（代理，非真实 E/S）。仅在该显式
    本地/私有模式下记录 `raw_private_records_read=true`，同时
    `raw_private_records_persisted=false` 仍保持为 false。
- 全程使用代理术语：`proxy_e_score`（范围 0..3，来自
  `span_f0_5 > 0.5`、`added_gold_span > 0`、
  `primary_false_positive_rate < 0.3`，取自 `candidate_baseline`
  outcome）、`proxy_s_score`（范围 0..5，来自
  `candidate_support_exists`、`local_anchor`、
  `rrf_backed_by_anchor`、`symbol_regex_agree`、
  `dense_support_present` route features）、`proxy_e_band` /
  `proxy_s_band`（none/weak/high）、`proxy_bucket`
  （`proxy_primary_evidence` / `proxy_dependency_support` /
  `proxy_weak_candidates` / `proxy_abstained` /
  `proxy_unmappable`）。
- 缺失代理字段变为 `proxy_unmappable`，**非**负面证据。
- 阈值 `PROXY_E_HIGH >= 2`、`PROXY_S_HIGH >= 2`，`>= 1` 时为弱。
  分类顺序 fail-closed：(1) 缺失字段 -> `proxy_unmappable`；
  (2) 代理 E 高 -> `proxy_primary_evidence`；(3) 代理 S 高且 E 低于
  high -> `proxy_dependency_support`；(4) 弱非零 ->
  `proxy_weak_candidates`；(5) 否则 -> `proxy_abstained`。代理 E 高
  优先于代理 S 高。
- 小单元抑制（`k_min`，默认 5）用于私有聚合交叉表（代理 E x S
  分段）。计数 < `k_min` 的单元被省略；
  `small_cells_suppressed=true`；`suppressed_cell_count` 报告被抑制
  单元数量（非个别计数）。
- 严格的禁止输出扫描器（写入 JSON 前 fail-closed）：拒绝禁止的
  字典键（path/span/line_range/content_sha/snippet/candidate_text/
  query/task_id/repo_id/repo/label/qrels/gold/prompt/response/
  private_record_hash/p31_score_gold 等）与禁止的取值模式（URL、
  32/40/64 字符十六进制摘要、类密钥串、类路径 `src/foo.py` 和
  `/private/foo.jsonl`、多行串、原始 JSON 片段、原始行范围
  `12-34`）。78 项自测检查，包含禁止扫描注入、fail-closed 生成、
  小单元抑制、缺失字段映射、路径序列化守卫与 CLI 参数守卫。
- CLI 守卫：`--input` 不带 `--allow-private-records` 非零退出（退出码
  2）；`--allow-private-records` 不带 `--input` 非零退出（退出码
  2）。D2b 输出仅写入 `/tmp` 且**绝不**提交。
- 既有 mode-only dirty 文件（`eval/ci_clone_and_lock_repo.py`、
  `eval/ci_make_repo_matrix.py`、
  `eval/p59_contrastive_pack_coverage_counterfactual.py`）**未被**
  触碰。D1/C1/C3/B12 模块被 import/read 但**未被**修改。

### 结果

```text
python3 -m py_compile eval/d2_dual_rubric_aggregate_calibration.py   => PASS
python3 eval/d2_dual_rubric_aggregate_calibration.py --self-test     => PASS (78/78 项检查)
python3 eval/d2_dual_rubric_aggregate_calibration.py \
  --out artifacts/d2_dual_rubric_aggregate_calibration/\
d2_dual_rubric_aggregate_calibration_report.json                     => PASS
  (status: public_aggregate_mappability_only,
   forbidden_scan: pass, self_test_passed: true,
   proxy_calibration_claimed: false,
   true_e_s_calibration_claimed: false,
   private_records_read: false,
   public_aggregates_have_candidate_level_proxy_fields: false,
   private_input_required_for_proxy_calibration: true,
   artifact_classes_checked: [c3_public_aggregate, b12_public_aggregate],
   public_artifact_status_counts: {present: 2, absent: 0})
# CLI 守卫：--input /private/foo.jsonl 不带 --allow-private-records
#   => PASS（退出码 2，路径未泄露到错误消息中）
# CLI 守卫：--allow-private-records 不带 --input
#   => PASS（退出码 2）
# CLI 守卫：D2b 不带显式 /tmp --out
#   => PASS（退出码 2，路径未泄露到错误消息中）
# CLI 守卫：D2b 使用 committed artifact --out
#   => PASS（退出码 2，路径未泄露到错误消息中）
# CLI 守卫：malformed private input 加载错误
#   => PASS（退出码 2，路径/基名被抑制）
# D2b 冒烟（--allow-private-records --input /tmp/... --out /tmp/...）
#   => PASS（仅 /tmp，未提交；forbidden_scan: pass，
#      private_record_count: 6, small_cells_suppressed: true,
#      proxy_bucket_counts: {proxy_primary_evidence: 4,
#        proxy_dependency_support: 2, proxy_abstained: 0,
#        proxy_weak_candidates: 0, proxy_unmappable: 0},
#      产物中无输入路径/基名/大小/mtime，
#      产物中无 task_id/repo_id）
python3 scripts/validate_docs_i18n.py                                 => PASS
git diff --check                                                      => PASS
```

D2a 默认产物确认公开 C3/B12 聚合**不**包含候选级代理字段（按构造
仅聚合）；代理校准需要私有输入。D2b 冒烟对 6 条合成 C1 private
records（P21 v1 payload）产生代理桶计数：
`proxy_primary_evidence=4`（`has_gold=true` 的记录，代理 E 高）、
`proxy_dependency_support=2`（`has_gold=false` 的记录，代理 E 弱、
代理 S 高）。小单元抑制（k_min=3）省略了稀疏交叉表单元。产物中未
泄露输入路径、基名、task_id 或 repo_id。

### 注意事项

- D2 仅评测/诊断。它**不**改变运行时、检索器、pack、模型、后端或
  默认策略；它**不**改变 EvidenceCore 语义。它**不是**基准结果、
  **不是**下游 agent 价值声明、**不是** runtime-clean 通用算法声明、
  **不是** OOD 时间维度声明，**也不是** QuIVer 系统声明。
- 代理分数**不是**真实 E/S 校准，**不是**改进的检索，**不是**下游
  agent 价值，**不是**基准结果，**不是**默认变更。
- D2a（默认）仅公开聚合可映射性，**非**代理校准。它**不**读取
  private records。
- D2b（可选）仅是私有代理校准冒烟。其输出仅写入 `/tmp` 且**绝不**
  提交。它**不**声称真实 E/S 校准。仅在该显式本地/私有模式下记录
  `raw_private_records_read=true`，同时 `raw_private_records_persisted=false`
  仍保持为 false。
- 所有 no-claim 标志保持为 false：`promotion_ready=false`、
  `default_should_change=false`、`evidencecore_semantics_changed=false`、
  `runtime_clean_general_algorithm_claimed=false`、
  `downstream_agent_value_proven=false`、`ood_temporal_supported=false`、
  `quiver_systems_supported=false`；`runtime_behavior_changed=false`、
  `retriever_changed=false`、`pack_builder_changed=false`、
  `model_calls_changed=false`、`backend_changed=false`、
  `default_policy_changed=false`；`candidate_text_emitted=false`、
  `paths_or_spans_emitted=false`、`content_sha_emitted=false`、
  已提交 D2a 中 `raw_private_records_read=false`（仅显式 `/tmp` D2b
  冒烟中为 `true`）、`raw_private_records_persisted=false`、
  `row_level_hashes_emitted=false`、`per_candidate_rows_emitted=false`。
  `aggregate_only_public_artifact=true`、`diagnostic_only=true`、
  `not_evidence=true`。
- 缺失代理字段变为 `proxy_unmappable`，**非**负面证据。
- 小单元抑制（`k_min`）省略稀疏交叉表单元；被抑制的单元计数绝不
  输出。

## 2026-06-20 — D3 双评分标签协议预注册（仅协议）

### 目标

将未来真实 E-score / S-score 标签采集与校准协议作为**仅协议**产物
预注册。D3 是 D1（确定性双评分相关性脚手架）与 D2（代理可映射性）
之间、以及稍后 D4 本地/私有真实 E/S 校准运行之间的桥梁。D3 **不**
采集标签、**不**读取 private records、**不**计算校准指标、**不**衡量
inter-rater agreement、**不**声称真实 E/S 校准、**不**声称代理校准、
**不**采集 model-assisted 标签，也**不**改变运行时行为、检索器、
pack、模型、后端、默认策略或 EvidenceCore 语义。

### 实现

- 新增脚本 `eval/d3_dual_rubric_preregistration.py`（纯 Python 标准库；
  无外部导入，无 private-record loader）。仅协议；不采集标签、不读取
  private records、不计算校准指标。
  - 声明级别 `dual_rubric_label_protocol_preregistration_only`；评分
    版本 `d3_true_dual_rubric_label_protocol_v1`；状态
    `protocol_ready_no_labels_collected`；模式 `protocol_only`。
  - CLI 仅接受 `--self-test` 与 `--out`。**没有** `--input`，**没有**
    `--allow-private-records`；自测强制此约束。
  - 标签协议 false 标志（全为 false）：`labels_collected`、
    `private_records_read`、`raw_private_records_read`、
    `private_records_persisted`、`true_e_s_calibration_claimed`、
    `proxy_calibration_claimed`、`model_assisted_labels_collected`、
    `inter_rater_agreement_measured`、`calibration_metrics_computed`。
  - No-claim / no-runtime-change 标志（全为 false）：`promotion_ready`、
    `default_should_change`、`downstream_agent_value_proven`、
    `runtime_behavior_changed`、`retriever_changed`、`pack_builder_changed`、
    `model_calls_changed`、`backend_changed`、`default_policy_changed`、
    `evidencecore_semantics_changed`、
    `runtime_clean_general_algorithm_claimed`、`ood_temporal_supported`、
    `quiver_systems_supported`。
  - 诊断标志（全为 true）：`aggregate_only_public_artifact`、
    `diagnostic_only`、`not_evidence`。
- 产物章节（全部仅类别，仅聚合/协议）：
  - `sampling_frame_protocol`：`eligible_record_sources` =
    `["local_private_p21_records", "local_private_d2b_proxy_smoke_candidates"]`；
    `sampling_axes` = `["proxy_bucket", "proxy_e_band", "proxy_s_band",
    "abstain_or_unmappable_status"]`；`stratification_required=true`；
    `max_records_per_batch_local_only=50`；
    `raw_record_material_private_only=true`。
  - `annotation_rubric`：`e_score_levels` E0/E1/E2；`s_score_levels`
    S0/S1/S2；`definitions`（abstention gate、E/S 序数刻度）；
    `bucket_mapping`（`primary_evidence`、`dependency_support`、
    `weak_candidates`、`abstained`）；`abstract_examples` 仅来自批准
    枚举（`direct_definition_of_requested_symbol`、
    `caller_import_relation_without_answer_bearing_text`、
    `same_module_but_insufficient_evidence`）。
  - `future_execution_gates`：`explicit_private_opt_in_required=true`；
    `local_output_path_required=true`；
    `output_location_category="tmp_only_local_private"`；
    `no_committed_raw_labels=true`；`k_min=5`；`min_total_labels=50`；
    `inter_rater_agreement_required=true`；
    `agreement_metrics_aggregate_only=["cohens_kappa",
    "krippendorff_alpha"]`；`confidence_intervals_required=true`。
  - `public_release_thresholds`：`min_total_n=50`；`k_min_per_cell=5`；
    `small_cell_policy="suppress_or_merge_to_other"`；
    `confidence_intervals_required=true`；
    `per_row_raw_label_outputs=false`。
  - `privacy_contract`：`no_task_ids`/`no_repo_ids_or_names`/
    `no_file_paths`/`no_spans_or_line_ranges`/`no_snippets_or_excerpts`/
    `no_content_hashes`/`no_prompts_or_responses`/`no_model_outputs`/
    `no_private_labels`/`no_raw_annotation_rows`/`no_per_row_hashes`/
    `no_local_filesystem_paths` 均为 true；`forbidden_field_categories`
    列出禁止字段名。
  - `phase_graph`：D1..D6 仅作为类别字符串（无执行数据）。
  - `forbidden_scan` 摘要（写入 JSON 前 fail-closed）。
- 禁止扫描器（fail-closed）：拒绝禁止的字典键（task_id、repo_id、
  repo、path、span、line_range、start_line、end_line、content_sha、
  snippet、excerpt、candidate_text、query、prompt、response、
  model_output、label、raw_label、annotation_row、per_row_hash 等）
  出现在任意位置；拒绝取值模式 —— 任何 URL（无 URL 白名单）、
  32/40/64 字符十六进制摘要、类密钥串、类路径 `src/foo.py` 和
  `/private/foo.jsonl`、多行串、原始 JSON 片段、原始行范围 `12-34`。
  允许安全协议字符串（`local_private_p21_records`、`proxy_bucket`、
  `E0` 等）。
- 自测（8 组，96 项检查）：(1) 无私有读取/无 input CLI；(2) 不采集标签/
  不计算校准指标/不衡量 agreement；(3) no-claim 标志为 false；(4) 协议
  完整性（必需章节/字段）；(5) 禁止扫描器拒绝敏感键/值；(6) 仅抽象
  示例（批准枚举；未批准的具体/类路径示例校验失败且被扫描器拒绝）；
  (7) 扫描器泄露时 fail-closed 生成；(8) 自测失败时拒绝成功生成产物。
- 新增文档：`docs/en/d3-dual-rubric-preregistration.md`、
  `docs/zh/d3-dual-rubric-preregistration.md`（i18n 镜像）。
- 既有 mode-only dirty 文件（`eval/ci_clone_and_lock_repo.py`、
  `eval/ci_make_repo_matrix.py`、
  `eval/p59_contrastive_pack_coverage_counterfactual.py`）**未被**
  触碰。无 runtime/retriever/pack/model/backend/default 文件被修改。
  未读取 private records。`current-research-conclusions` **未**更新
  （D3 仅协议，结论无变化）。

### 结果

```text
python3 -m py_compile eval/d3_dual_rubric_preregistration.py           => PASS
python3 eval/d3_dual_rubric_preregistration.py --self-test            => PASS (96/96 项检查)
python3 eval/d3_dual_rubric_preregistration.py \
  --out artifacts/d3_dual_rubric_preregistration/\
d3_dual_rubric_preregistration_report.json                            => PASS
  (status: protocol_ready_no_labels_collected,
   forbidden_scan: pass, self_test_passed: true,
   labels_collected: false, private_records_read: false,
   raw_private_records_read: false, private_records_persisted: false,
   true_e_s_calibration_claimed: false, proxy_calibration_claimed: false,
   model_assisted_labels_collected: false,
   inter_rater_agreement_measured: false,
   calibration_metrics_computed: false,
   mode: protocol_only,
   rubric_version: d3_true_dual_rubric_label_protocol_v1)
python3 scripts/validate_docs_i18n.py                                  => PASS
git diff --check                                                       => PASS
```

D3 预注册双评分标签协议，包含全部必需章节（sampling frame、annotation
rubric E0/E1/E2 与 S0/S1/S2、future D4 gates、public release
thresholds、privacy contract、phase graph）。未采集标签、未读取
private records、未计算校准指标、未衡量 inter-rater agreement。禁止
扫描器对已提交产物 fail-closed 通过。

### 注意事项

- D3 是仅协议预注册。它仅评测/诊断。它**不**改变运行时、检索器、
  pack、模型、后端或默认策略；它**不**改变 EvidenceCore 语义。它
  **不是**基准结果、**不是**下游 agent 价值声明、**不是**
  runtime-clean 通用算法声明、**不是** OOD 时间维度声明，**也不是**
  QuIVer 系统声明。
- D3 **不**采集标签、**不**读取 private records、**不**计算校准
  指标、**不**衡量 inter-rater agreement、**不**声称真实 E/S 校准、
  **不**声称代理校准、**不**采集 model-assisted 标签。
- D4 是**可能**执行本地/私有真实 E/S 校准的第一个阶段，且仅当全部
  `future_execution_gates` 满足时。D3 不自动 gate 或触发 D4。
- 所有 no-claim / no-runtime-change 标志保持为 false；诊断标志
  （`aggregate_only_public_artifact`、`diagnostic_only`、`not_evidence`）
  保持为 true。
- 任何示例均为批准的抽象类别字符串；不输出具体 repo/path/snippet
  内容。
- 既有 mode-only dirty 文件（`eval/ci_clone_and_lock_repo.py`、
  `eval/ci_make_repo_matrix.py`、
  `eval/p59_contrastive_pack_coverage_counterfactual.py`）**未被**
  触碰。

## 2026-06-20 — D4a 双评分执行门 / 试运行（仅公开门产物）

### 目标

将 D4a 实现为**执行门 / 试运行**公开产物。D4a 校验未来本地/私有真实
E-score / S-score 标签校准（D4b）运行前所需的控制平面。D4a 是 D3
（仅预注册标签协议）之后的试运行衔接。D4a **不**采集真实标签、默认
**不**读取私有标签 bundle、**不**计算真实校准指标、**不**衡量
inter-rater agreement、**不**声称真实/代理校准，也**不**改变运行时
行为、检索器、pack、模型、后端、默认策略或 EvidenceCore 语义。

### 实现

- 新脚本 `eval/d4_dual_rubric_execution_gate.py`（纯 Python stdlib；无
  外部导入、无 private-record loader）。默认公开门试运行；私有试运行
  是显式的仅 `/tmp` 夹具。
  - 声明级别 `dual_rubric_execution_gate_dry_run_only`；评分版本
    `d3_true_dual_rubric_label_protocol_v1`（D3 协议已校验）；状态
    `execution_gate_ready_no_labels_collected`；模式
    `public_gate_dry_run`；阶段 `D4a`；下一阶段
    `D4b_local_private_label_collection_smoke`。
  - CLI：`--self-test`、`--out`、`--allow-private-labels`、`--input`。
    默认模式（无私有参数）写入已提交公开门产物（若省略 `--out` 则用
    默认输出路径）。
  - 默认 false 标志（全为 false）：`labels_collected`、
    `private_label_bundle_read`、`private_label_bundle_persisted`、
    `private_records_read`、`raw_private_records_read`、
    `raw_labels_persisted`、`raw_label_rows_emitted`、
    `private_output_path_emitted`、`private_input_path_emitted`、
    `private_output_committed`、`calibration_metrics_computed`、
    `inter_rater_agreement_measured`、`agreement_metrics_computed`、
    `confidence_intervals_computed`、`true_e_s_calibration_claimed`、
    `proxy_calibration_claimed`、`public_release_gate_passed`、
    `real_label_bundle_gate_passed`。
  - 执行控制标志（仅已校验的试运行控制为 true）：
    `execution_controls_validated`、`private_cli_guard_validated`、
    `tmp_output_guard_validated`、`validate_before_read_guard_validated`、
    `sanitized_error_guard_validated`、
    `small_cell_suppression_gate_validated`、`min_total_n_gate_validated`、
    `agreement_required_gate_validated`、`confidence_interval_gate_validated`。
  - D3 协议校验：`d3_protocol_checked=true`、`d3_protocol_version=
    d3_true_dual_rubric_label_protocol_v1`、`d3_required_gates_present=
    true`。
  - no-claim / no-runtime-change 标志（全为 false）；诊断标志（全为
    true）：`aggregate_only_public_artifact`、`diagnostic_only`、
    `not_evidence`。
- 私有试运行模式（不提交；仅 `/tmp`）：必须恰好为
  `--allow-private-labels --input <path> --out /tmp/...`。在打开输入**前**
  校验 CLI/输出守卫（validate-before-read 经由记录每次 loader/exists
  调用的可注入 probe 证明）。接受已消毒的仅聚合私有标签-bundle 形状
  JSON（计数与布尔，非原始行）。任何加载/解析/schema/隐私失败返回固定
  消毒错误：`error: failed to load private labels (schema/privacy/parse
  error; details suppressed)`。成功 stdout **不**打印确切的 `/tmp` 输出
  路径。私有输出 JSON 仅含门 pass/fail 布尔、固定阈值、固定门类别名与
  已消毒标志——无输入/输出路径、basename、原始标签、rater ID、
  annotation 行、行 hash 或确切真实私有样本量。
- 门逻辑（合成、内存内；常量来自 D3）：`k_min=5`、
  `min_total_labels=50`、`agreement_required=true`、
  `confidence_intervals_required=true`。基于合成摘要的自测：min-N 低于
  50 fail；small cell 低于 5 fail/suppress；缺第二 rater / agreement
  不可用 fail；缺 CI fail；全部条件 pass。
- 禁止扫描器（写任何 JSON 前 fail-closed）：拒绝禁止的 dict 键
  （`task_id`、`repo_id`、`repo`、`path`、`span`、`line_range`、
  `start_line`、`end_line`、`content_sha`、`snippet`、`candidate_text`、
  `query`、`prompt`、`response`、`model_output`、`label`、`raw_label`、
  `annotation_row`、`rater_id`、`annotator_id`、`disagreement_example`、
  `per_row_hash` 等）于任何位置；拒绝值模式——任何 URL（无 URL
  allowlist）、32/40/64 字符 hex 摘要、类 secret 字符串、类路径
  `src/foo.py` 与 `/private/foo.jsonl`、多行字符串、原始 JSON 片段、
  原始行范围 `12-34`，以及自测 sentinel `SECRET_LABEL_SENTINEL`。允许
  安全的门/协议字符串（`primary_evidence`、`k_min`、`D4a`、
  `d3_true_dual_rubric_label_protocol_v1` 等）。
- 自测（12 组、153 项检查）：(1) 默认 false/true 标志；(2) 产物身份
  字段；(3) D3 协议常量/门已校验；(4) 门逻辑（min-N、small-cell、
  agreement、CI、pass）；(5) CLI 守卫矩阵（纯、无路径/basename 泄露）；
  (6) validate-before-read probe（无效输出 / 已提交输出 / 非 `/tmp` 输出
  时无输入访问）；(7) 敏感 basename + `SECRET_LABEL_SENTINEL` 的消毒
  错误（无泄露）；(8) 私有试运行成功路径（序列化产物中无路径/basename/
  原始标签/输出路径/确切私有样本量）；(9) 禁止扫描器拒绝敏感键/值并
  fail-closed；(10) 扫描器泄露时 fail-closed 生成；(11) 自测失败时拒绝
  成功生成产物；(12) CLI 选项面（恰好为所需选项）。
- 新文档：`docs/en/d4-dual-rubric-execution-gate.md`、
  `docs/zh/d4-dual-rubric-execution-gate.md`（i18n 镜像）。
- 未修改 runtime/retriever/pack/model/backend/default-policy 文件。默认
  提交产物未读取 private records 或私有标签。`current-research-conclusions`
  **未**更新（D4a 是门/试运行；结论无变化）。

### 结果

```text
python3 -m py_compile eval/d4_dual_rubric_execution_gate.py    => PASS
python3 eval/d4_dual_rubric_execution_gate.py --self-test      => PASS (153/153 项检查)
python3 eval/d4_dual_rubric_execution_gate.py \
  --out artifacts/d4_dual_rubric_execution_gate/\
d4_dual_rubric_execution_gate_report.json                     => PASS
  (status: execution_gate_ready_no_labels_collected,
   forbidden_scan: pass, self_test_passed: true,
   labels_collected: false, private_label_bundle_read: false,
   private_output_committed: false,
   calibration_metrics_computed: false,
   true_e_s_calibration_claimed: false, proxy_calibration_claimed: false,
   public_release_gate_passed: false,
   execution_controls_validated: true,
   mode: public_gate_dry_run, phase: D4a,
   next_phase: D4b_local_private_label_collection_smoke,
   rubric_version: d3_true_dual_rubric_label_protocol_v1)
/tmp 私有试运行 smoke（合成 bundle）                            => PASS
  (输出/stdout/stderr 中无输入/输出路径、basename、原始标签、
   sentinel 或确切私有样本量)
CLI 守卫矩阵（缺 allow/input/out、已提交输出、非 /tmp 输出）    => PASS (全部 exit 2)
python3 scripts/validate_docs_i18n.py                          => PASS
git diff --check                                                => PASS
```

D4a 校验执行门控制平面：D3 协议常量（k_min=5、min_total_labels=50、
agreement/CI 必需）、合成门逻辑（min-N/small-cell/agreement/CI）、
CLI/隐私守卫（私有 opt-in、仅 `/tmp` 输出、validate-before-read）、
fail-closed 禁止扫描与消毒错误处理。默认提交产物不采集标签、不读取私有
bundle、不计算校准指标、不衡量 inter-rater agreement、不声称真实/代理
校准，也不通过任何发布门。基于合成聚合 bundle 的 `/tmp` 私有试运行
smoke 通过全部门，且输出/stdout/stderr 中无路径/basename/原始标签/
sentinel/输出路径泄露。

### 注意事项

- D4a 仅执行门 / 试运行公开产物。它仅评测/诊断。它**不**改变运行时、
  检索器、pack、模型、后端或默认策略；它**不**改变 EvidenceCore 语义。
  它**不是**基准结果、**不是**下游 agent 价值声明、**不是**
  runtime-clean 通用算法声明、**不是** OOD 时间维度声明，也**不是**
  QuIVer 系统声明。
- D4a **不是** D4b。默认提交产物**不**采集标签、**不**读取私有标签
  bundle、**不**计算校准指标、**不**衡量 inter-rater agreement、**不**
  声称真实/代理校准，也**不**通过任何公开发布门。执行控制标志仅对已
  校验的试运行控制为 true，**并非**任何真实校准。
- 私有试运行模式仅 `/tmp` 且**绝不**提交。它仅校验一个本地/私有标签-
  bundle 形状 JSON 的结构/门；它**不**计算或声称真实校准指标。
- 所有 no-claim / no-runtime-change 标志保持为 false；诊断标志
  （`aggregate_only_public_artifact`、`diagnostic_only`、`not_evidence`）
  保持为 true。
- D4b 真实标签采集/校准仍为独立的未来 gated 阶段；D4a 不自动 gate 或
  触发 D4b。
- 未修改 runtime/retriever/pack/model/backend/default-policy 文件。

## 2026-06-20 — D4b 双评分真实标签 Smoke 测试夹具（公开夹具 / 无标签产物）

### 目标

将 D4b 实现为**真实标签 smoke 测试夹具**公开产物。D4b 冻结本地/私有真实
E-score / S-score 标签 bundle 的输入契约，并强化执行控制。**默认提交的产物
是公开夹具 / 无标签产物**，而非真实真实标签 smoke 结果。D4b **不**伪造标签、
**不**接受代理/合成/LLM 标签作为真实标签、默认**不**读取私有真实标签
bundle、**不**计算真实校准指标、**不**衡量 inter-rater agreement、**不**
声称真实/代理校准，也**不**改变运行时行为、检索器、pack、模型、后端、
默认策略或 EvidenceCore 语义。`local_private_true_label_smoke_executed`
仅在真实本地私有运行（人工/手动标签且显式 opt-in）时可为 true；默认提交
产物保持 blocked/no-labels。

### 实现

- 新脚本 `eval/d4b_dual_rubric_true_label_smoke.py`（纯 Python stdlib；无
  外部导入、无 private-record loader）。默认公开夹具/无标签；私有 smoke
  是显式的仅 `/tmp` 夹具。
  - 声明级别 `true_label_bundle_execution_harness_only`；评分版本
    `d3_true_dual_rubric_label_protocol_v1`（D3 协议已校验）；状态
    `blocked_no_true_label_bundle_available`；模式
    `public_harness_no_labels`；阶段 `D4b`。
  - CLI：`--self-test`、`--out`、`--allow-private-labels`、`--input`、
    `--synthetic-harness-test`（默认 false）。默认模式（无私有参数）写入
    已提交公开夹具/无标签产物（若省略 `--out` 则用默认输出路径）。
  - 默认 false 标志（全为 false）：`labels_collected`、
    `true_label_bundle_read`、`true_label_bundle_validated`、
    `true_label_bundle_persisted`、
    `local_private_true_label_smoke_executed`、
    `calibration_metrics_computed`、`inter_rater_agreement_measured`、
    `confidence_intervals_computed`、`true_e_s_calibration_claimed`、
    `public_release_gate_passed`、`real_label_bundle_gate_passed`、
    `raw_label_rows_emitted`、`private_input_path_emitted`、
    `private_output_path_emitted`、`private_output_committed`、
    `exact_private_counts_emitted`、`synthetic_labels_accepted_as_true`、
    `proxy_labels_accepted_as_true`、`llm_labels_accepted_as_true`、
    `model_assisted_labels_allowed`。
  - 夹具/控制标志（恰好五个，全为 true）：
    `private_execution_harness_available`、`private_cli_guard_validated`、
    `tmp_output_resolved_guard_validated`、`sanitized_error_guard_validated`、
    `bundle_schema_contract_defined`。默认提交产物中无门校验/校准声明标志
    为 true。
  - 私有真实标签 bundle 契约（`d4b_true_label_bundle_v1`）：`label_source`
    对真实运行必须恰为 `human_manual_true_e_s`；`proxy`/`synthetic`/
    `llm`/`model_assisted` 作为真实标签被拒绝。`rater_count` int >= 2；
    `agreement_available` 与 `confidence_intervals_available` 为布尔；
    `labels` 为对象列表，仅含键 `e_score`（E0/E1/E2）、`s_score`
    （S0/S1/S2）、`bucket`（primary_evidence/dependency_support/
    weak_candidates/abstained）、`citation_valid`、`rater_pair_present`、
    `adjudicated`（布尔）。ID/路径/snippet/rater ID/原始行元数据/未知键被
    拒绝（fail-closed）而非支持并剥离。
  - 强解析 `/tmp` 守卫：解析 `/tmp`；在读取私有输入前解析输出父目录；拒绝
    父 symlink 逃逸 `/tmp`（`/tmp/link_to_repo/out.json`）；拒绝已存在输出
    文件 symlink；拒绝解析后逃逸 `/tmp` 的目标；读取前拒绝已提交产物路径
    与非 `/tmp` 输出。所有输出守卫在输入被打开或 stat 前运行
    （validate-before-read）。
  - 私有输出仅 `/tmp` 且绝不提交。无 label 行、ID、路径、basename、原始
    E/S 行、rater ID、annotation 行、行 hash、prompts/responses/model
    outputs，或确切私有计数。仅 band：`label_count_band`
    （`min_n_met`/`below_min_n`）、`bucket_count_bands`
    （`k_met`/`below_k`/`suppressed`），以及 min-N/k/second-rater/
    agreement/CI 门布尔。因 bundle **输入**契约使用 `labels` 键，任何
    **输出**不得输出 `labels` 键（禁止扫描器拒绝它）。
  - 私有输出含 `input_attestation_required=true`。合成/内存夹具自测设
    `synthetic_harness_test=true` 且
    `local_private_true_label_smoke_executed=false`（即使 bundle 为
    human-manual 形状）。真实本地私有运行（无 synthetic 标志、
    `label_source=human_manual_true_e_s`、有效 schema）可设
    `local_private_true_label_smoke_executed=true` 仅本地（绝不提交）。
  - 任何私有真实标签 bundle load/parse/schema/privacy 失败的固定消毒
    错误：
    `error: failed to load private true labels (schema/privacy/parse
    error; details suppressed)`（无原始异常、输入/输出路径或 basename、
    原始 JSON 或标签文本）。

### 校验结果

```text
python3 -m py_compile eval/d4b_dual_rubric_true_label_smoke.py    => PASS
python3 eval/d4b_dual_rubric_true_label_smoke.py --self-test      => PASS (206/206 项检查)
python3 eval/d4b_dual_rubric_true_label_smoke.py \
  --out artifacts/d4b_dual_rubric_true_label_smoke/\
d4b_dual_rubric_true_label_smoke_report.json                     => PASS
  (status: blocked_no_true_label_bundle_available,
   forbidden_scan: pass, self_test_passed: true,
   labels_collected: false, true_label_bundle_read: false,
   true_label_bundle_validated: false,
   local_private_true_label_smoke_executed: false,
   private_output_committed: false,
   calibration_metrics_computed: false,
   true_e_s_calibration_claimed: false,
   synthetic_labels_accepted_as_true: false,
   proxy_labels_accepted_as_true: false,
   llm_labels_accepted_as_true: false,
   model_assisted_labels_allowed: false,
   public_release_gate_passed: false,
   real_label_bundle_gate_passed: false,
   private_execution_harness_available: true,
   private_cli_guard_validated: true,
   tmp_output_resolved_guard_validated: true,
   sanitized_error_guard_validated: true,
   bundle_schema_contract_defined: true,
   mode: public_harness_no_labels, phase: D4b)
/tmp 私有 smoke（合成 human-manual 形状 bundle）                 => PASS
  (synthetic_harness_test=true,
   local_private_true_label_smoke_executed=false,
   输出/stdout/stderr 中无输入/输出路径、basename、原始标签、
   sentinel、确切计数或 labels 键)
/tmp 私有 smoke（基于合成 fixture 的真实模式 flag-path 测试）      => PASS
  (synthetic_harness_test=false,
   local_private_true_label_smoke_executed=true 仅本地，
   true_label_bundle_read=true, true_label_bundle_validated=true,
   不提交)
CLI 守卫矩阵（缺 allow/input/out、已提交输出、非 /tmp 输出、
  synthetic 无 allow）                                              => PASS (全部 exit 2)
解析 /tmp symlink 逃逸守卫（父 symlink、
  已存在输出文件 symlink）                                         => PASS (exit 2)
消毒错误（proxy/synthetic/llm 源、畸形 bundle、
  不存在的输入）                                                   => PASS (exit 2，无泄露)
python3 scripts/validate_docs_i18n.py                            => PASS
git diff --check                                                 => PASS
```

D4b 冻结真实标签 bundle 输入契约（`d4b_true_label_bundle_v1`、
`label_source=human_manual_true_e_s`、rater_count>=2、六键 label 对象），
并强化执行控制：CLI/隐私守卫、强解析 `/tmp` symlink 逃逸守卫、
validate-before-read、fail-closed 禁止扫描与消毒错误。默认提交产物为
blocked/no-labels：不采集标签、不读取真实标签 bundle、不校验任何 bundle
为真实标签、不计算校准指标、不衡量 inter-rater agreement、不声称真实/代理
校准，也不通过任何发布门。基于合成 human-manual 形状 bundle 的 `/tmp` smoke
通过全部门，且 `synthetic_harness_test=true`、
`local_private_true_label_smoke_executed=false`，输出/stdout/stderr 中无
路径/basename/原始标签/sentinel/确切计数/labels 键泄露。proxy/synthetic/
LLM 源作为真实标签被拒绝。基于合成 fixture 的真实模式 `/tmp` flag-path 测试
在本地输出中设置 `local_private_true_label_smoke_executed=true`、
`true_label_bundle_read=true` 和 `true_label_bundle_validated=true`（绝不提交）；
这只测试私有模式 truth flags，**不是**真实人工标签存在的公开证据。

### 注意事项

- D4b 仅真实标签 smoke 测试夹具公开产物。它仅评测/诊断。它**不**改变
  运行时、检索器、pack、模型、后端或默认策略；它**不**改变 EvidenceCore
  语义。它**不是**基准结果、**不是**下游 agent 价值声明、**不是**
  runtime-clean 通用算法声明、**不是** OOD 时间维度声明，也**不是**
  QuIVer 系统声明。
- D4b 默认是 blocked / 无标签。默认提交产物**不**采集标签、**不**读取
  真实标签 bundle、**不**校验任何 bundle 为真实标签、**不**计算校准指标、
  **不**衡量 inter-rater agreement、**不**声称真实/代理校准，也**不**
  通过任何公开发布/真实 bundle 门。夹具/控制标志仅对已校验的夹具/控制
  为 true，**并非**任何真实校准。
- 合成/代理/LLM 标签**不**被接受为真实标签。它们仅可出现在自测与可选的
  私有模式夹具测试中，且 `local_private_true_label_smoke_executed=false`。
- 私有 smoke 模式仅 `/tmp` 且**绝不**提交。它仅校验一个本地/私有真实
  标签-bundle 形状 JSON 的结构/门；它**不**计算或声称真实校准指标。真实
  本地私有运行可设 `local_private_true_label_smoke_executed=true` 仅本地，
  并在该本地输出中如实记录 `true_label_bundle_read=true` 和
  `true_label_bundle_validated=true`。本次校验使用合成 fixture 测试该 flag
  path；它不是真实人工标签存在的公开证据。
- 所有 no-claim / no-runtime-change 标志保持为 false；诊断标志
  （`aggregate_only_public_artifact`、`diagnostic_only`、`not_evidence`）
  保持为 true；五个夹具/控制标志是仅有的 true 控制标志。
- 未修改 runtime/retriever/pack/model/backend/default-policy 文件。
  `current-research-conclusions` **未**更新（D4b 是夹具/blocked 产物；
  结论无变化）。

## 2026-06-20 — D4c 标注 Packet 构建夹具（公开夹具 / 无 Packet 产物）

### 目标

将 D4c 实现为**标注 packet 构建夹具**公开产物。D4c 通过构建带空标签
槽的本地/私有标注 packet，将私有源记录桥接到未来的人工标注。**默认提交
的产物是公开夹具 / 无 packet 产物**，而非真实 packet 构建结果。D4c
**不**采集标签、**不**填充标签槽、**不**创建 D4b 真实标签 bundle、
**不**运行 packet->bundle 转换器、**不**计算校准指标、**不**进行
model/LLM 标注、默认**不**读取私有源记录、**不**输出 provider payload/
API key/secret/model output，也**不**改变运行时行为、检索器、pack、
模型、后端、默认策略或 EvidenceCore 语义。与 D4b 不同，D4c 私有 packet
输出**可**有意含敏感上下文（路径/snippet/content_sha/query/candidate
文本）用于人工标注，但**仅**在 `/tmp` 下且**绝不**提交；公开产物保持无
packet。

### 实现

- 新脚本 `eval/d4c_annotation_packet_builder.py`（纯 Python stdlib；无
  外部导入）。默认公开夹具/无 packet；私有 packet 构建是显式的仅
  `/tmp` 夹具。
  - 声明级别 `annotation_packet_builder_harness_only`；状态
    `blocked_no_private_source_records_available_or_no_packets_built`；
    模式 `public_harness_no_packets`；阶段 `D4c`；D4b bundle schema
    target `d4b_true_label_bundle_v1`。
  - CLI：`--self-test`、`--out`、`--allow-private-source-records`、
    `--input`（无 synthetic 标志；私有模式总是从任意有效输入构建
    packet）。默认模式（无私有参数）写入已提交公开夹具/无 packet 产物。
  - 默认 false 标志（全为 false）：`private_source_records_read`、
    `private_source_records_persisted`、`annotation_packets_built`、
    `annotation_packets_persisted`、`private_packet_output_written`、
    `packet_output_path_emitted`、`private_input_path_emitted`、
    `packet_ids_emitted`、`task_ids_emitted`、`repo_ids_emitted`、
    `paths_or_spans_emitted`、`snippets_emitted`、`content_sha_emitted`、
    `query_text_emitted`、`candidate_text_emitted`、
    `private_packet_output_contains_sensitive_context`、
    `private_packet_schema_validated`、`private_packet_labels_filled`、
    `labels_collected`、`true_label_bundle_created`、
    `d4b_true_label_bundle_validated`、`d4b_bundle_converter_run`、
    `calibration_metrics_computed`、`model_or_llm_labeling_performed`、
    `provider_payloads_emitted`、`annotation_instructions_emitted`、
    `true_e_s_calibration_claimed`、`public_release_gate_passed`。
  - 夹具/控制标志（恰好六个，全为 true）：
    `private_packet_builder_harness_available`、
    `private_cli_guard_validated`、`tmp_output_resolved_guard_validated`、
    `sanitized_error_guard_validated`、`packet_schema_contract_defined`、
    `d4b_mapping_contract_defined`。默认提交产物中无 packet 构建/标签/
    bundle/校准声明标志为 true。
  - 公开契约：`private_source_record_schema_contract`
    （category-only；schema `d4c_private_source_records_v1`、
    `private_only=true`、`may_contain_sensitive_context=true`）；
    `packet_schema_contract`（schema `d4c_annotation_packet_v1`、
    `private_only=true`、`may_contain_sensitive_context=true`、
    `required_label_slots=[e_score,s_score,bucket,citation_valid,
    rater_pair_present,adjudicated]`、`target_bundle_schema=
    d4b_true_label_bundle_v1`）；`d4b_mapping_contract`
    （`target_bundle_schema=d4b_true_label_bundle_v1`、同
    `packet_label_slots`、
    `packet_to_bundle_requires_manual_transcription_or_local_converter=true`、
    `converter_not_run=true`、`true_label_bundle_created=false`）。
  - 私有源记录契约（`d4c_private_source_records_v1`）：records 列表；
    每条记录恰好需要 `private_record_ref`、`candidate_ref`、
    `query_text`、`candidate_text`、`candidate_bucket_hint`、
    `evidence`；每个 evidence 条目恰好需要 `path`、`start_line`、
    `end_line`、`content_sha`、`snippet`；`candidate_bucket_hint` 属于
    `primary_evidence`/`dependency_support`/`weak_candidates`/
    `abstained`/`unknown`；`start_line`/`end_line` 正整数且
    `start_line <= end_line`；`content_sha` 为 32/40/64 位十六进制。
    未知键（`provider_payload`、`api_key`、`secret`、`model_output`、
    `prompt_response`、labels/label 行）被 fail-closed 拒绝。
  - 强解析 `/tmp` 守卫：解析 `/tmp`；在读取私有输入前解析输出父目录；
    拒绝父 symlink 逃逸 `/tmp`；拒绝已存在输出文件 symlink；拒绝解析后
    逃逸 `/tmp` 的目标；读取前拒绝已提交产物路径与非 `/tmp` 输出。所有
    输出守卫在输入被打开或 stat 前运行（validate-before-read）。
  - 两套扫描器：(1) 公开产物扫描器（严格、fail-closed、带精确契约字符串
    白名单——只有批准的 schema ID 与批准的 label-slot 字段名 token 可出现
    在契约容器内；实现符号或私有文本等任意字符串即使在契约容器内也会被
    拒绝；字段名作为键在任何位置被禁止，作为值在契约外被禁止）；
    (2) 私有 packet 守卫（不同——仅允许
    在 `/tmp` 私有 packet 中出现路径/snippet/content_sha/query/candidate
    文本/标注说明/空标签槽，强制 packet schema、空标签槽、无已填充
    E0/E1/E2/S0/S1/S2 值、无 D4b bundle、无转换器、无校准、无 model
    标注，拒绝 provider secret/API key/provider payload/model output）。
    公开扫描器未被削弱以让私有 packet 通过。
  - 私有 packet 输出仅 `/tmp` 且绝不提交。它含敏感上下文（本地 packet
    ref、query/candidate 文本、evidence path/span/snippet/content_sha、
    标注说明、空标签槽）及安全标志 `private_packet_output=true`、
    `public_artifact=false`、`do_not_commit=true`、
    `labels_filled_by_builder=false`、`d4b_bundle_created=false`、
    `d4b_bundle_converter_run=false`、`true_label_bundle_created=false`、
    `calibration_metrics_computed=false`、
    `model_or_llm_labeling_performed=false`。它绝不在元数据/stdout/stderr
    中回显输入/输出路径或 basename，也不创建 D4b bundle 或标签/校准声明。
  - 任何私有源记录 load/parse/schema/privacy 失败的固定消毒错误：
    `error: failed to load private source records (schema/privacy/parse
    error; details suppressed)`（无原始异常、输入/输出路径或 basename、
    原始 JSON 或私有文本）。

### 校验结果

```text
python3 -m py_compile eval/d4c_annotation_packet_builder.py    => PASS
python3 eval/d4c_annotation_packet_builder.py --self-test      => PASS (238/238 项检查)
python3 eval/d4c_annotation_packet_builder.py \
  --out artifacts/d4c_annotation_packet_builder/\
d4c_annotation_packet_builder_report.json                     => PASS
  (status: blocked_no_private_source_records_available_or_no_packets_built,
   forbidden_scan: pass, self_test_passed: true,
   private_source_records_read: false,
   annotation_packets_built: false,
   private_packet_output_written: false,
   private_packet_output_contains_sensitive_context: false,
   labels_collected: false,
   true_label_bundle_created: false,
   d4b_bundle_converter_run: false,
   calibration_metrics_computed: false,
   model_or_llm_labeling_performed: false,
   provider_payloads_emitted: false,
   public_release_gate_passed: false,
   private_packet_builder_harness_available: true,
   private_cli_guard_validated: true,
   tmp_output_resolved_guard_validated: true,
   sanitized_error_guard_validated: true,
   packet_schema_contract_defined: true,
   d4b_mapping_contract_defined: true,
   mode: public_harness_no_packets, phase: D4c,
   d4b_bundle_schema_target: d4b_true_label_bundle_v1)
/tmp 私有 packet 构建（合成源记录）                                => PASS
  (annotation_packets_built=true,
   private_packet_output_contains_sensitive_context=true,
   private_packet_guard: pass, 标签槽全为 null,
   敏感上下文（path/snippet/content_sha/query_text/
   candidate_text/annotation_instructions/packet_ref）存在于
   /tmp 输出但不在公开产物中,
   元数据/stdout/stderr 中无输入/输出路径或 basename,
   无 provider secret、无 D4b bundle、无转换器、无校准、无
   model 标注、不提交)
CLI 守卫矩阵（input 无 allow、allow 无 input、无显式 out、
  已提交输出、非 /tmp 输出）                                       => PASS (全部 exit 2)
解析 /tmp symlink 逃逸守卫（父 symlink、
  已存在输出文件 symlink）                                         => PASS (exit 2)
畸形私有输入消毒错误                                               => PASS (exit 2，无泄露)
python3 scripts/validate_docs_i18n.py                            => PASS
git diff --check                                                 => PASS
```

D4c 冻结标注 packet 构建夹具契约（`d4c_private_source_records_v1` /
`d4c_annotation_packet_v1` 输入、六个空标签槽、
`d4b_true_label_bundle_v1` 目标）并强化执行控制：CLI/隐私守卫、强解析
`/tmp` symlink 逃逸守卫、validate-before-read、分离的公开扫描器（带精确契约
字符串白名单）与私有 packet 守卫、fail-closed 禁止扫描与消毒错误。默认提交
产物为 blocked/no-packets：不读取私有源记录、不构建 packet、不填充标签、
不创建 D4b bundle、不运行转换器、不计算校准、不进行 model/LLM 标注，
也不通过任何发布门。基于合成源记录的 `/tmp` packet 构建写出了含敏感上下
文的 packet（`private_packet_output_contains_sensitive_context=true`、
`annotation_packets_built=true`），标签槽为空、无已填充 E/S 值、无
D4b bundle、无转换器、无校准、无 model 标注、无 provider secret，且
输出/stdout/stderr 中无输入/输出路径或 basename 泄露——而公开产物保持
无 packet。源输入中的 provider payload/API key/secret/model output/
prompt_response/labels 被 fail-closed 拒绝。

### 注意事项

- D4c 仅标注 packet 构建夹具公开产物。它仅评测/诊断。它**不**改变
  运行时、检索器、pack、模型、后端或默认策略；它**不**改变
  EvidenceCore 语义。它**不是**基准结果、**不是**下游 agent 价值
  声明、**不是** runtime-clean 通用算法声明、**不是** OOD 时间维度
  声明，也**不是** QuIVer 系统声明。
- D4c 默认是 blocked / 无 packet。默认提交产物**不**读取私有源记录、
  **不**构建 packet、**不**持久化 packet、**不**填充标签、**不**
  创建 D4b bundle、**不**运行转换器、**不**计算校准、**不**进行
  model/LLM 标注，也**不**通过任何公开发布门。夹具/控制标志仅对已
  校验的夹具/控制为 true，**并非**任何真实 packet 构建或标签声明。
- D4c **不是**标签采集、**不是** D4b 真实标签 bundle 创建、**不是**
  校准、**不是**发布就绪。它为人工 rater 构建带空标签槽的 packet；
  它不运行 packet->bundle 转换器。
- 私有 packet 构建模式仅 `/tmp` 且**绝不**提交。与 D4b 不同，D4c 私有
  packet 输出**可**有意含人工标注所需的敏感上下文（本地 packet ref、
  query/candidate 文本、evidence path/span/snippet/content_sha、标注
  说明、空标签槽），但**仅**在 `/tmp` 下。默认公开产物绝不读取私有
  记录且不含任何 packet/私有内容。
- 所有 no-claim / no-runtime-change 标志保持为 false；诊断标志
  （`aggregate_only_public_artifact`、`diagnostic_only`、
  `not_evidence`）保持为 true；六个夹具/控制标志是仅有的 true 控制
  标志。
- 未修改 runtime/retriever/pack/model/backend/default-policy 文件。
  `current-research-conclusions` **未**更新（D4c 是夹具/blocked 产物；
  结论无变化）。

## 2026-06-20 — D4d 人工标注 Runbook / Checklist 协议（公开纯协议 artifact）

### Objective

实现 D4d 为**人工标注 runbook / checklist 协议**公开 artifact。D4d 在任何
D4e 转换器或 D5 聚合发布候选之前，冻结未来人工标注者应如何标注 D4c 标注包（填写
双评分卡 E/S 槽位）。默认提交的 artifact 是**公开纯协议 runbook**，不是标签采
集，不是数据包构建，不是已填充数据包，不是 D4b bundle，不是转换器运行，也不是
校准。D4d **不**读取私有数据包、**不**读取私有数据包输出、**不**读取私有源记
录、**不**生成/持久化标注包、**不**招募/识别标注者、**不**发出标注者 ID、**不**
采集标签、**不**创建已填充数据包、**不**创建 D4b 真值 bundle、**不**运行转换
器、**不**校验 D4b bundle、**不**计算校准、**不**度量标注者间一致性、**不**计
算置信区间、**不**通过任何发布门、**不解锁** D5、**不**声明真 E/S 校准、**不**
执行模型/LLM 标注、**不**允许模型辅助标签、**不**发出私有路径/代码片段或
包/任务/仓库 ID/内容哈希/查询/候选文本，且**不**改变运行时行为、retriever、
pack、model、backend、默认策略或 EvidenceCore 语义。D4d 没有私有模式，没有
`--input`，也不读取私有数据包/源记录。

### Implementation

- 新脚本 `eval/d4d_human_annotation_runbook.py`（纯 Python stdlib；无
  外部导入）。仅公开纯协议 runbook artifact；没有私有模式，也没有 `--input`。
  - 声明级别 `human_annotation_runbook_protocol_only`；状态
    `protocol_ready_no_raters_no_labels_no_packets`；模式
    `public_runbook_protocol_only`；阶段 `D4d`；D3 评分卡版本
    `d3_true_dual_rubric_label_protocol_v1`；D4c 数据包 schema 目标
    `d4c_annotation_packet_v1`；D4b bundle schema 目标
    `d4b_true_label_bundle_v1`。
  - CLI：`--self-test`、`--out`（仅此两个）。**没有** `--input`，**没有**
    `--allow-private-source-records`；D4d 是纯协议，从不读取私有数据包或源记
    录。默认模式写入已提交的公开纯协议 runbook artifact。未知或类似私有输入的
    参数会以通用 `invalid arguments` 消息拒绝，不回显私有路径或 basename。
  - 默认 false 标志（全为 false）：`private_packets_read`、
    `private_packet_output_read`、`private_source_records_read`、
    `annotation_packets_generated`、`annotation_packets_persisted`、
    `raters_recruited`、`raters_identified`、`rater_ids_emitted`、
    `labels_collected`、`filled_packets_created`、
    `d4b_true_label_bundle_created`、`d4b_bundle_converter_run`、
    `d4b_true_label_bundle_validated`、`calibration_metrics_computed`、
    `inter_rater_agreement_measured`、`confidence_intervals_computed`、
    `public_release_gate_passed`、`d5_unblocked`、
    `true_e_s_calibration_claimed`、`model_or_llm_labeling_performed`、
    `model_assisted_labels_allowed`、`private_paths_or_snippets_emitted`、
    `packet_ids_emitted`、`task_ids_emitted`、`repo_ids_emitted`、
    `content_sha_emitted`、`query_or_candidate_text_emitted`。
  - 无声明 / 无运行时变更标志（全为 false）：
    `runtime_behavior_changed`、`retriever_changed`、`pack_builder_changed`、
    `model_calls_changed`、`backend_changed`、`default_policy_changed`、
    `evidencecore_semantics_changed`、`promotion_ready`、
    `default_should_change`、`downstream_agent_value_proven`、
    `runtime_clean_general_algorithm_claimed`、`ood_temporal_supported`、
    `quiver_systems_supported`。
  - 协议 true 标志（共十五个，全为 true）：
    `runbook_protocol_defined`、`checklist_schema_defined`、
    `rater_independence_required`、`d3_rubric_required`、
    `d4c_packet_schema_referenced`、`d4b_bundle_schema_referenced`、
    `local_only_storage_required`、`no_llm_labeling_required`、
    `adjudication_policy_defined`、`disagreement_handling_defined`、
    `min_n_gate_referenced`、`k_min_gate_referenced`、
    `agreement_gate_referenced`、`ci_gate_referenced`、
    `aggregate_only_public_release_required`。默认提交产物中无任何数据包构
    建/标签/bundle/校准/一致性/置信区间/发布/D5 解锁声明标志为 true。
  - 公开契约：`runbook_protocol_contract`（七个纯类别章节 — preconditions、
    rater_setup、labeling_rules、prohibited_labeling_sources、
    local_storage_privacy、adjudication、release_gates — 每个带经批准的抽象
    类别 token checklist）；`rubric_contract`（`d3_rubric_version`、
    `e_score_levels=[E0,E1,E2]`、`s_score_levels=[S0,S1,S2]`、
    `bucket_names=[primary_evidence,dependency_support,weak_candidates,
    abstained]`、`required_label_slots=[e_score,s_score,bucket,
    citation_valid,rater_pair_present,adjudicated]`）；
    `label_slot_contract`（六个槽位、`target_packet_schema=
    d4c_annotation_packet_v1`、`target_bundle_schema=
    d4b_true_label_bundle_v1`、`no_filled_packets_created=true`）；
    `release_gate_contract`（`gate_names=[min_total_labels,k_min,
    agreement_metric,confidence_intervals,small_cell_suppression]`、
    `min_total_labels=50`、`k_min=5`、`min_rater_count=2`、
    `agreement_required=true`、`confidence_intervals_required=true`、
    `small_cell_suppression_required=true`、
    `aggregate_only_public_release_required=true`、
    `d5_blocked_until_all_gates_pass=true`、
    `public_release_gate_passed=false`）；
    `prohibited_labeling_sources_contract`（`prohibited_sources`：
    无 LLM/模型标签、无代理标签作为真值、无模型名称规则、无基准私有桶作为运
    行时策略、无下游价值声明；`model_or_llm_labeling_performed=false`、
    `model_assisted_labels_allowed=false`）；`rater_setup_contract`
    （`min_rater_count=2`、`rater_independence_required=true`、
    `rater_independence_rules`、`local_rater_mapping_private_only=true`、
    `rater_ids_emitted=false`、`raters_recruited=false`、
    `raters_identified=false`）。
  - runbook 内容是纯类别且抽象的：没有数据包示例、代码片段、路径、任务 ID、
    仓库名、标注者 ID/姓名、URL 或私有示例。
  - 严格公开扫描器（故障关闭，带精确契约字符串白名单）。契约容器
    （`checklist`、`e_score_levels`、`s_score_levels`、`bucket_names`、
    `required_label_slots`、`gate_names`、`prohibited_sources`、
    `rater_independence_rules`）仅允许经批准的 schema 标识符、E/S 等级、
    桶名、标签槽位字段名、门名和经批准的抽象 runbook 类别 token。任意短字
    符串（如 `compute_loss` 或私有文本）即使在契约容器内**也会被拒绝**（无
    过宽容器豁免）；敏感字段名（`content_sha`、`query_text`、
    `packet_ref`）即使在契约容器内也被拒绝。字段名在任何位置作为键、在契约
    外作为值，均被拒绝。拒绝禁止的 dict 键，并拒绝值模式：任何 URL（无 URL
    白名单）、32/40/64 字符十六进制摘要、类密钥字符串、类路径字符串、多行
    字符串、原始 JSON 片段、原始行范围以及自测 sentinel。
  - 若自测失败或扫描器发现泄漏，生成拒绝成功（写 JSON 前立即故障关闭
    `_enforce_no_forbidden` + `_refuse_on_self_test_failure`）。

### Validation results

```text
python3 -m py_compile eval/d4d_human_annotation_runbook.py    => PASS
python3 eval/d4d_human_annotation_runbook.py --self-test      => PASS (274/274 checks)
python3 eval/d4d_human_annotation_runbook.py \
  --out artifacts/d4d_human_annotation_runbook/\
d4d_human_annotation_runbook_report.json                     => PASS
  (status: protocol_ready_no_raters_no_labels_no_packets,
   forbidden_scan: pass, self_test_passed: true,
   private_packets_read: false,
   annotation_packets_generated: false,
   labels_collected: false,
   filled_packets_created: false,
   d4b_true_label_bundle_created: false,
   d4b_bundle_converter_run: false,
   calibration_metrics_computed: false,
   inter_rater_agreement_measured: false,
   confidence_intervals_computed: false,
   model_or_llm_labeling_performed: false,
   model_assisted_labels_allowed: false,
   raters_recruited: false, raters_identified: false,
   rater_ids_emitted: false,
   public_release_gate_passed: false, d5_unblocked: false,
   runbook_protocol_defined: true,
   checklist_schema_defined: true,
   rater_independence_required: true,
   d3_rubric_required: true,
   d4c_packet_schema_referenced: true,
   d4b_bundle_schema_referenced: true,
   local_only_storage_required: true,
   no_llm_labeling_required: true,
   adjudication_policy_defined: true,
   disagreement_handling_defined: true,
   min_n_gate_referenced: true,
   k_min_gate_referenced: true,
   agreement_gate_referenced: true,
   ci_gate_referenced: true,
   aggregate_only_public_release_required: true,
   mode: public_runbook_protocol_only, phase: D4d,
   d3_rubric_version: d3_true_dual_rubric_label_protocol_v1,
   d4c_packet_schema_target: d4c_annotation_packet_v1,
   d4b_bundle_schema_target: d4b_true_label_bundle_v1)
python3 scripts/validate_docs_i18n.py                           => PASS
git diff --check                                               => PASS
```

D4d 冻结 D4e（包->bundle 转换器，未来）将使用的人工标注 runbook/checklist 协
议，并强化执行控制：纯协议 CLI（无 `--input`、无私有模式，且未知私有输入参数不
回显路径/basename）、带精确契约字符串白
名单的严格故障关闭公开扫描器（无过宽容器豁免——未批准字符串和敏感字段名即使在契
约容器内也被拒绝），以及在扫描器泄漏或自测失败时拒绝成功的故障关闭生成。默认提
交产物是纯协议：不读取私有数据包，不生成数据包，不招募/识别标注者，不采集标签，
不创建已填充数据包，不创建 D4b bundle，不运行转换器，不计算校准，不度量一致性/
置信区间，不执行模型/LLM 标注，也不通过任何发布门。D5 保持锁定。runbook 内容是
纯类别且抽象的；公开 artifact 中没有数据包示例、代码片段、路径、ID、标注者姓名
或 URL。

### Caveats

- D4d 仅是人工标注 runbook / checklist 协议公开 artifact。它仅评测/诊断。它
  **不**改变运行时、retriever、pack、model、backend 或默认策略；也**不**改变
  EvidenceCore 语义。它不是基准测试结果，不是下游 agent 价值声明，不是
  runtime-clean 通用算法声明，不是 OOD 时间性声明，也不是 QuIVer 系统声明。
- D4d 默认是纯协议。默认提交产物**不**读取任何私有数据包，**不**生成任何数据
  包，**不**招募/识别任何标注者，**不**采集任何标签，**不**创建任何已填充数据
  包，**不**创建任何 D4b bundle，**不**运行任何转换器，**不**计算任何校准，**不**
  度量任何一致性/置信区间，**不**执行任何模型/LLM 标注，也**不**通过任何公开发
  布门。D5 保持锁定。协议 true 标志仅对已定义的协议控制为 true，而非任何真实的
  标签采集或 bundle 声明。
- D4d **不是**标签采集，**不是**数据包生成，**不是**已填充数据包创建，**不是**
  D4b 真值 bundle 创建，**不是**转换器，**不是**校准，**不是**一致性度量，也**不
  是** D5 解锁。它冻结为 D4e 做准备的人工标注 runbook/checklist。
- D4d 没有私有模式，没有 `--input`，也不读取私有数据包/源记录。与 D4c 不同，没
  有可选私有构建器。runbook 内容是纯类别且抽象的；公开 artifact 中没有数据包示
  例、代码片段、路径、ID、标注者姓名或 URL。
- 所有无声明 / 无运行时变更标志保持 false；诊断标志
  （`aggregate_only_public_artifact`、`diagnostic_only`、`not_evidence`）保持
  true；协议 true 标志是唯一为 true 的控制标志。
- 未修改 runtime/retriever/pack/model/backend/default-policy 文件。
  `current-research-conclusions` **未**更新（D4d 是纯协议 artifact；结论无变
  化）。

## 2026-06-20 — D4e 已填充 Packet -> D4b Bundle 转换器夹具（公开夹具 / 无转换产物）

### Objective

实现 D4e 为**已填充 packet -> D4b 真值 bundle 转换器夹具**公开 artifact。D4e
在任何真实人工标签存在之前，强化 D4d 人工标注与 D4b bundle 校验之间的转换控制
平面。默认提交的 artifact 是**公开夹具 / 无转换产物**，不是真实的已填充
packet -> D4b bundle 转换运行，不是校准，不是一致性/置信区间计算，也不解锁
D5。D4e **不**默认读取私有已填充 packet，**不**默认转换，**不**默认写入或提
交 D4b bundle，**不**接受 D4c 源上下文字段，**不**接受模型/代理/LLM 标签作
为人工/手工标签，**不**在任何提交产物中发出包引用/任务 ID/仓库 ID/路径/跨度/
代码片段/内容哈希/查询/候选文本/标注者 ID，**不**计算校准/标注者间一致性/置
信区间，**不**通过任何公开发布门，**不解锁** D5，**不**声明真 E/S 校准，**不**
执行模型/LLM 标注，且**不**改变运行时行为、retriever、pack、model、backend、
默认策略或 EvidenceCore 语义。

### Implementation

- 新脚本 `eval/d4e_filled_packet_converter.py`（纯 Python stdlib；无外部导
  入）。仅公开夹具 / 无转换 artifact；私有转换器是可选的，仅写入 `/tmp` 输出
  （永不提交）。
  - 声明级别
    `filled_packet_to_d4b_bundle_converter_harness_only`；状态
    `blocked_no_filled_packets_available_or_no_conversion_run`；模式
    `public_harness_no_filled_packets_no_conversion`；阶段 `D4e`；D4c 数据包
    schema 源 `d4c_annotation_packet_v1`；D4d runbook 协议
    `d4d_human_annotation_runbook.v1`；D4b bundle schema 目标
    `d4b_true_label_bundle_v1`。
  - CLI：`--self-test`、`--out`、`--allow-private-filled-packets`、
    `--input-filled-packets`、`--synthetic-harness-test`。未知或类似私有输入
    的参数会以通用 `invalid arguments` 消息拒绝，不回显私有路径或 basename
    （SafeArgumentParser 模式）。
  - 默认 false 标志（全为 false）：
    `private_filled_packets_read`、`filled_packets_validated`、
    `filled_packets_persisted`、`conversion_run`、
    `d4b_true_label_bundle_created`、
    `d4b_true_label_bundle_written`、
    `d4b_true_label_bundle_validated`、`labels_collected`、
    `labels_converted`、`raw_label_rows_emitted`、
    `packet_ids_emitted`、`task_ids_emitted`、`repo_ids_emitted`、
    `paths_or_spans_emitted`、`snippets_emitted`、
    `content_sha_emitted`、`query_or_candidate_text_emitted`、
    `rater_ids_emitted`、`private_input_path_emitted`、
    `private_output_path_emitted`、`exact_private_counts_emitted`、
    `calibration_metrics_computed`、
    `inter_rater_agreement_measured`、
    `confidence_intervals_computed`、
    `public_release_gate_passed`、`d5_unblocked`、
    `true_e_s_calibration_claimed`、
    `model_or_llm_labeling_performed`、
    `model_assisted_labels_allowed`。
  - 无声明 / 无运行时变更标志（全为 false）：
    `runtime_behavior_changed`、`retriever_changed`、
    `pack_builder_changed`、`model_calls_changed`、`backend_changed`、
    `default_policy_changed`、`evidencecore_semantics_changed`、
    `promotion_ready`、`default_should_change`、
    `downstream_agent_value_proven`、
    `runtime_clean_general_algorithm_claimed`、
    `ood_temporal_supported`、`quiver_systems_supported`。
  - 夹具/控制 true 标志（共八个，全为 true）：
    `converter_harness_available`、`private_cli_guard_validated`、
    `tmp_output_resolved_guard_validated`、
    `sanitized_error_guard_validated`、
    `filled_packet_schema_contract_defined`、
    `d4d_attestation_required`、
    `d4b_bundle_schema_contract_defined`、
    `d4b_mapping_contract_defined`。默认提交产物中无任何读取/转换/bundle/标
    签/校准/D5 声明标志为 true。
  - attestation 作用域被显式区分，避免矛盾的 shorthand：
    `default_public_mode_input_attestation_evaluated=false`，因为默认公开模式
    不读取输入；`private_conversion_d4d_attestation_required=true`，因为私有
    filled-packet 转换必须带 D4d attestation。
  - 公开契约：`filled_packet_schema_contract`（`schema`、
    `source_packet_schema_ref`、`private_only=true`、
    `may_contain_filled_label_slots=true`、`required_label_slots`、
    `required_attestation_fields`、
    `rejects_source_context_fields=true`）；`d4d_runbook_contract`
    （`protocol`、`required_attestation_fields`、
    `attestation_must_be_all_true=true`、
    `no_llm_or_model_labels_required=true`、
    `no_proxy_labels_as_true_labels_required=true`、
    `local_only_storage_required=true`）；`d4b_bundle_schema_contract`
    （`schema`、`required_label_source`、`bundle_allowed_keys`、
    `label_object_allowed_keys`、`e_score_levels=[E0,E1,E2]`、
    `s_score_levels=[S0,S1,S2]`、
    `bucket_names=[primary_evidence,dependency_support,weak_candidates,
    abstained]`、`rejects_unknown_keys=true`、
    `rejects_packet_refs_paths_snippets_raters=true`）；
    `d4b_mapping_contract`（`target_bundle_schema`、
    `packet_label_slots`、`source_packet_schema_ref`、
    `runbook_protocol`、
    `packet_to_bundle_requires_human_or_local_converter=true`、
    `converter_not_run_by_default=true`、
    `d4b_true_label_bundle_created=false`）；`converter_harness_info`
    （`available=true`、`opt_in_required=true`、
    `output_location=tmp_only_local_private`、`committed=false`、
    `converts_filled_packets_to_d4b_bundle=true`、
    `rejects_source_context_fields=true`、
    `rejects_model_proxy_llm_labels=true`、
    `claims_calibration=false`）。
  - 私有已填充 packet 输入契约：最小纯标签批次，带 D4d attestation。允许的
    批次键：`schema`、`source_packet_schema`、`d4d_runbook_attestation`、
    `packets`。允许的 attestation 键：`protocol`、
    `two_independent_human_raters`、`independent_before_adjudication`、
    `no_llm_or_model_labels`、`no_proxy_labels_as_true_labels`、
    `local_only_storage`（全为 true；协议必须恰为
    `d4d_human_annotation_runbook.v1`）。允许的 packet 键：
    `packet_ref`、`label_slots`。允许的标签槽位键：`e_score`、
    `s_score`、`bucket`、`citation_valid`、`rater_pair_present`、
    `adjudicated`。拒绝路径/跨度/代码片段/内容哈希、查询/候选文本、任务/仓库
    ID、标注者 ID/姓名、提示/响应/模型输出/提供者 payload/API 密钥以及源上下文
    字段（D4e 仅消费已填充标签和 attestation）。
  - 私有 D4b bundle 输出契约：schema 恰为
    `d4b_true_label_bundle_v1`，label_source 恰为
    `human_manual_true_e_s`，`rater_count=2`、
    `agreement_available=true`、
    `confidence_intervals_available=false`，真实的合成/真实标志。对于
    `--synthetic-harness-test`：`synthetic_harness_test=true`、
    `synthetic_labels_converted_for_harness_only=true`、
    `local_private_conversion_executed=false`、
    `real_human_labels_converted=false`。对于真实本地私有运行（非合成标志、
    D4d attestation 通过、无模型/代理标签、schema 通过、/tmp 守卫通过）：
    `synthetic_harness_test=false`、
    `synthetic_labels_converted_for_harness_only=false`、
    `local_private_conversion_executed=true`、
    `real_human_labels_converted=true`。私有输出不得包含包引用、任务/仓库
    ID、路径/跨度、代码片段、content_sha、查询/候选文本、标注者 ID、提供者
    payload、API 密钥、模型输出、精确输入/输出路径或 basename。
  - 严格公开扫描器（故障关闭，带精确契约字符串白名单）。契约容器
    （`filled_packet_schema_contract`、`d4d_runbook_contract`、
    `d4b_bundle_schema_contract`、`d4b_mapping_contract`）仅允许经批准的
    schema/协议标识符、E/S 等级、桶名、标签槽位字段名、attestation 字段名、
    human-manual label source 标识符和经批准的 D4b bundle 字段名 token。任意
    短字符串（如 `compute_loss` 或私有文本）即使在契约容器内**也会被拒绝**（无
    过宽容器豁免）；敏感字段名（`content_sha`、`query_text`、
    `packet_ref`、`source_packet_schema`、`d4d_runbook_attestation`、
    `packets`）即使在契约容器内也被拒绝。字段名在任何位置作为键、在契约外作
    为值，均被拒绝。拒绝禁止的 dict 键，并拒绝值模式：任何 URL（无 URL 白名
    单）、32/40/64 字符十六进制摘要、类密钥字符串、类路径字符串、多行字符
    串、原始 JSON 片段、原始行范围以及自测 sentinel。
  - 私有 D4b bundle 输出守卫（与公开扫描器**不同**）：允许标签字段和 E/S 值
    （bundle 是真实的 D4b bundle，可在本地包含标签）；拒绝路径/代码片段/
    content_sha/查询/候选文本、最终 D4b bundle 中的包引用、标注者 ID、提供者
    payload/API 密钥/模型输出；校验 schema 恰为
    `d4b_true_label_bundle_v1`、label_source 恰为
    `human_manual_true_e_s`、真实的合成/真实标志，且输出元数据中无精确输入/
    输出路径或 basename。
  - 解析后的 `/tmp` 输出守卫（强，仅在 OUTPUT 上做文件系统访问）：父目录符号
    链接逃逸被拒绝；已存在的输出文件符号链接被拒绝；解析后的目标必须保持在
    `/tmp` 下。在打开或 stat 输入之前校验（读取前校验）。
  - CLI 守卫矩阵（纯词法，无文件系统）：
    `--input-filled-packets` 不带 `--allow-private-filled-packets` 退出码
    2；`--allow-private-filled-packets` 不带 `--input-filled-packets` 退出
    码 2；私有模式要求显式 `--out`；提交产物路径在读取前被拒绝；非 `/tmp` 输
    出在读取前被拒绝；`--synthetic-harness-test` 不带
    `--allow-private-filled-packets` 退出码 2；路径遍历
    （`/tmp/../etc/...`）被拒绝。
  - 仅清洗错误：任何私有加载/解析/schema/隐私失败返回固定消息
    `error: failed to load private filled packets (schema/privacy/parse error; details suppressed)`；
    永不暴露输入路径、basename、原始 JSON 或标签文本。未知/类似私有输入的参
    数以通用 `invalid arguments` 消息拒绝（不回显值）。
  - 若自测失败或扫描器发现泄漏，生成拒绝成功（写 JSON 前立即故障关闭
    `_enforce_no_forbidden` + `_refuse_on_self_test_failure`）。

### Validation results

```text
python3 -m py_compile eval/d4e_filled_packet_converter.py    => PASS
python3 eval/d4e_filled_packet_converter.py --self-test      => PASS (307/307 checks)
python3 eval/d4e_filled_packet_converter.py \
  --out artifacts/d4e_filled_packet_converter/\
d4e_filled_packet_converter_report.json                     => PASS
  (status: blocked_no_filled_packets_available_or_no_conversion_run,
   forbidden_scan: pass, self_test_passed: true,
   private_filled_packets_read: false,
   conversion_run: false,
   d4b_true_label_bundle_created: false,
   d4b_true_label_bundle_written: false,
   labels_converted: false,
   d5_unblocked: false,
   converter_harness_available: true,
   private_cli_guard_validated: true,
   tmp_output_resolved_guard_validated: true,
   sanitized_error_guard_validated: true,
   filled_packet_schema_contract_defined: true,
   d4d_attestation_required: true,
   d4b_bundle_schema_contract_defined: true,
   d4b_mapping_contract_defined: true,
   mode: public_harness_no_filled_packets_no_conversion, phase: D4e,
   d4c_packet_schema_source: d4c_annotation_packet_v1,
   d4d_runbook_protocol: d4d_human_annotation_runbook.v1,
   d4b_bundle_schema_target: d4b_true_label_bundle_v1)
python3 scripts/validate_docs_i18n.py                           => PASS
git diff --check                                               => PASS
```

D4e 在任何真实人工标签存在之前，强化 D4d 人工标注与 D4b bundle 校验之间的转
换控制平面：私有转换器夹具，带 SafeArgumentParser CLI（未知私有输入参数不回
显值）、带精确契约字符串白名单的严格故障关闭公开扫描器（无过宽容器豁免——未
批准字符串和敏感字段名即使在契约容器内也被拒绝）、与公开扫描器不同的私有
D4b bundle 输出守卫（允许标签字段/E/S 值；拒绝路径/代码片段/引用/标注者
ID/密钥/模型输出；校验 schema、label_source 和真实的合成/真实标志）、解析后
的 `/tmp` 输出守卫（父目录符号链接逃逸、已存在输出符号链接、解析后目标逃逸
均被拒绝）、读取前校验顺序，以及在扫描器泄漏或自测失败时拒绝成功的故障关闭
生成。默认提交产物是夹具 / 无转换产物：不读取私有已填充 packet，不运行转换，
不创建/写入/校验 D4b bundle，不采集/转换标签，不计算校准/一致性/置信区间，
不执行模型/LLM 标注，也不通过任何公开发布门。D5 保持锁定。在合成夹具上的
real-mode flag-path 测试（在本地设置
`local_private_conversion_executed=true` 和
`real_human_labels_converted=true`）仅是 flag-path 测试，**不**是真实标签存
在的证据。

### Caveats

- D4e 仅是已填充 packet -> D4b bundle 转换器夹具公开 artifact。它是
  eval/诊断专用。它**不**改变运行时、retriever、pack、model、backend 或默
  认策略；也**不**改变 EvidenceCore 语义。它不是基准测试结果，不是下游
  agent 价值声明，不是 runtime-clean 通用算法声明，不是 OOD 时间性声明，
  也不是 QuIVer 系统声明。
- D4e 默认是带阻塞公开产物的夹具。默认提交产物**不**读取任何私有已填充
  packet，**不**运行任何转换，**不**创建/写入/校验任何 D4b bundle，**不**采
  集/转换任何标签，**不**计算任何校准/一致性/置信区间，**不**执行任何模型/LLM
  标注，也**不**通过任何公开发布门。D5 保持锁定。夹具/控制 true 标志仅对已
  校验的夹具/控制为 true，而非任何真实标签转换或 bundle 声明。
- D4e **不是**提交输出中的真实标签转换，**不是**校准，**不是**一致性/置信区
  间计算，也**不**解锁 D5。它在任何真实人工标签存在之前，强化 D4d 人工标注
  与 D4b bundle 校验之间的转换控制平面。
- D4e 有私有转换器模式（可选，不提交）。私有输出仅写入 `/tmp` 且永不提交。
  在合成夹具上的 real-mode flag-path 测试（在本地设置
  `local_private_conversion_executed=true` 和
  `real_human_labels_converted=true`）仅是 flag-path 测试，**不**是真实标签
  存在的证据。真实人工标签尚未采集；D5 保持锁定。
- 转换器仅消费已填充的标签槽位和 D4d attestation；它拒绝 D4c 源上下文字段
  （路径、跨度、代码片段、content_sha、查询文本、候选文本、packet 源上下文）。
  D4d attestation 必须恰为 `d4d_human_annotation_runbook.v1`，且所有六个
  必需标志为 true（两名独立人工标注者、裁决前独立、无 LLM/模型标签、无代理
  标签作为真值、仅本地存储）；模型/代理/LLM 标签被拒绝作为人工/手工标签。
- 所有无声明 / 无运行时变更标志保持 false；诊断标志
  （`aggregate_only_public_artifact`、`diagnostic_only`、`not_evidence`）保持
  true；夹具/控制 true 标志是唯一为 true 的控制标志。
- 未修改 runtime/retriever/pack/model/backend/default-policy 文件。
  `current-research-conclusions` **未**更新（D4e 是夹具/仅阻塞 artifact；结论
  无变化）。

## 2026-06-20 — D4f D4b Bundle 校验 / 门检查夹具（公开夹具 / 无校验产物）

### 目标

实现 D4f 为 **D4b 真值 bundle 校验 / 门检查夹具**公开 artifact。D4f 是真实
标签存在之前的最后一个有用夹具：D4e 证明已填充 packet 可以在本地转换为 D4b
bundle；D4f 证明 D4b bundle 可以在本地校验并检查门前提，而无需发布标签、精确
计数或指标。默认提交的 artifact 是**公开夹具 / 无校验产物**，不是真实的 D4b
bundle 校验运行，不是门通过，不是校准，不是一致性/置信区间计算，也不解锁 D5。
D4f 必须不默认读取私有 D4b bundle，不默认校验私有 bundle，不默认持久化私有
bundle，不接受包引用/任务/仓库 ID/路径/跨度/代码片段/内容哈希/查询/候选文本/
标注者 ID/模型输出/提供者 payload，不在任何提交产物中发出标签/原始标签行/
精确计数/桶计数/单元计数/一致性指标值/置信区间数值，不计算校准/标注者间一致
性/置信区间，不通过任何公开发布门，不解锁 D5，不声明真 E/S 校准，不执行模型/
LLM 标注，也不改变运行时行为、retriever、pack、model、backend、默认策略或
EvidenceCore 语义。

### 实现

- 新脚本 `eval/d4f_bundle_validation_gate.py`（纯 Python stdlib；无外部
  导入）。仅公开夹具 / 无校验 artifact；私有校验器是可选，仅写入 `/tmp` 输出
  （永不提交）。
  - 声明级别 `d4b_bundle_validation_gate_harness_only`；状态
    `blocked_no_private_bundle_available_or_no_validation_run`；模式
    `public_harness_no_private_bundle_no_validation`；阶段 `D4f`；
    D4b bundle schema 源 `d4b_true_label_bundle_v1`；D4e 转换器源
    `d4e_filled_packet_converter_harness.v1`；D4d runbook 协议
    `d4d_human_annotation_runbook.v1`。
  - CLI：`--self-test`、`--out`、`--allow-private-bundle`、
    `--input-bundle`、`--synthetic-harness-test`。未知或类似私有输入的参数
    会以通用 `invalid arguments` 消息拒绝，不回显私有路径或 basename
    （SafeArgumentParser 模式）。
  - 默认 false 标志（全为 false）：`private_bundle_read`、
    `private_bundle_validated`、`private_bundle_persisted`、
    `bundle_validation_run`、`labels_read`、`labels_persisted`、
    `raw_label_rows_emitted`、`exact_private_counts_emitted`、
    `bucket_counts_emitted`、`cell_counts_emitted`、
    `calibration_metrics_computed`、`inter_rater_agreement_computed`、
    `inter_rater_agreement_measured`、`agreement_metric_values_emitted`、
    `confidence_intervals_computed`、`confidence_interval_values_emitted`、
    `public_release_gate_passed`、`d5_unblocked`、
    `true_e_s_calibration_claimed`、`private_input_path_emitted`、
    `private_output_path_emitted`、`task_ids_emitted`、`repo_ids_emitted`、
    `paths_or_spans_emitted`、`snippets_emitted`、`content_sha_emitted`、
    `query_or_candidate_text_emitted`、`rater_ids_emitted`、
    `model_or_llm_labeling_performed`、`model_assisted_labels_allowed`。
  - 无声明 / 无运行时变更标志（全为 false）：
    `runtime_behavior_changed`、`retriever_changed`、`pack_builder_changed`、
    `model_calls_changed`、`backend_changed`、`default_policy_changed`、
    `evidencecore_semantics_changed`、`promotion_ready`、
    `default_should_change`、`downstream_agent_value_proven`、
    `runtime_clean_general_algorithm_claimed`、`ood_temporal_supported`、
    `quiver_systems_supported`。
  - 夹具/控制 true 标志（恰为十个，全为 true）：
    `bundle_validation_harness_available`、`private_cli_guard_validated`、
    `tmp_output_resolved_guard_validated`、`sanitized_error_guard_validated`、
    `d4b_bundle_schema_contract_defined`、`gate_check_contract_defined`、
    `min_n_gate_referenced`、`k_min_gate_referenced`、
    `agreement_availability_gate_referenced`、`ci_availability_gate_referenced`。
    默认提交产物中无读取/校验/标签/计数/指标/D5 声明标志为 true。
  - 公开契约：`d4b_bundle_schema_contract`（`schema`、`required_label_source`、
    `bundle_allowed_keys`、`label_object_allowed_keys`、
    `e_score_levels=[E0,E1,E2]`、`s_score_levels=[S0,S1,S2]`、
    `bucket_names=[primary_evidence,dependency_support,weak_candidates,
    abstained]`、`rejects_unknown_keys=true`、
    `rejects_packet_refs_paths_snippets_raters=true`）；
    `gate_check_contract`（`min_total_labels_gate_referenced=true`、
    `k_min_gate_referenced=true`、
    `agreement_availability_gate_referenced=true`、
    `ci_availability_gate_referenced=true`、
    `min_rater_count_gate_referenced=true`、`min_rater_count=2`、
    `min_total_labels_gate=50`、`k_min_cell_gate=5`、
    `gate_band_values=[met,not_met,not_evaluated]`、
    `small_cell_suppression_required=true`、
    `exact_counts_never_emitted=true`、`metrics_never_computed=true`、
    `validator_not_run_by_default=true`）；
    `d4d_runbook_contract`（`protocol`、`required_attestation_fields`、
    `attestation_must_be_all_true=true`、
    `no_llm_or_model_labels_required=true`、
    `no_proxy_labels_as_true_labels_required=true`、
    `local_only_storage_required=true`）；
    `d4e_converter_contract`（`converter_source`、`target_bundle_schema`、
    `private_only=true`、`output_location=tmp_only_local_private`、
    `committed=false`）；
    `validation_harness_info`（`available=true`、`opt_in_required=true`、
    `output_location=tmp_only_local_private`、`committed=false`、
    `validates_d4b_bundle_schema=true`、`runs_gate_checks_only=true`、
    `rejects_packet_refs_paths_snippets_raters=true`、
    `rejects_model_proxy_llm_labels=true`、`claims_calibration=false`、
    `computes_agreement_or_ci=false`）。
  - 私有 D4b bundle 输入契约：消费 D4e D4b bundle 输出形状。允许的 bundle 键：
    `schema`、`label_source`、`rater_count`、`agreement_available`、
    `confidence_intervals_available`、`synthetic_harness_test`、
    `local_private_conversion_executed`、`real_human_labels_converted`、
    `labels`。允许的标签对象键：`e_score`、`s_score`、`bucket`、
    `citation_valid`、`rater_pair_present`、`adjudicated`。拒绝包引用/任务/仓库
    ID/路径/跨度/代码片段/内容哈希/查询/候选文本/标注者 ID/姓名/提示/响应/模型
    输出/提供者 payload/API 密钥/原始一致性指标值/置信区间数值/逐行哈希/未知键。
    D4f 仅校验 schema 和门可用性，不计算指标。
  - 私有 D4f 门报告输出契约：`schema_version` 恰为
    `d4f_bundle_validation_gate_private_report.v1`，`private_validation_report=true`、
    `public_artifact=false`、`do_not_commit=true`、
    `small_cell_suppression_required=true`、门布尔（`schema_gate_passed`、
    `label_source_gate_passed`、`rater_count_gate_passed`、
    `agreement_availability_gate_passed`、`ci_availability_gate_passed`）、
    频段（`min_total_labels_gate_band`、`k_min_gate_band`，值为
    `met`/`not_met`/`not_evaluated`）、`exact_private_counts_emitted=false`、
    `bucket_counts_emitted=false`、`cell_counts_emitted=false`、
    `agreement_metric_values_emitted=false`、
    `confidence_interval_values_emitted=false`、
    `public_release_gate_passed=false`、`d5_unblocked=false`。对于
    `--synthetic-harness-test`：`synthetic_harness_test=true`、
    `synthetic_bundle_validated_for_harness_only=true`、
    `local_private_bundle_validation_run=false`、
    `real_human_bundle_validated=false`。对于真实本地私有运行（无 synthetic CLI
    标志、bundle 未标记为合成、label_source 为 human manual、D4e real-conversion
    标志为 true、schema 通过、/tmp 守卫通过）：
    `synthetic_harness_test=false`、
    `synthetic_bundle_validated_for_harness_only=false`、
    `local_private_bundle_validation_run=true`、
    `real_human_bundle_validated=true`。即使所有门本地通过，报告也始终保持
    `public_release_gate_passed=false` 和 `d5_unblocked=false`。
  - 严格公开扫描器（故障关闭，带精确契约字符串白名单）。契约容器
    （`d4b_bundle_schema_contract`、`gate_check_contract`、
    `d4d_runbook_contract`、`d4e_converter_contract`）仅允许经批准的
    schema/协议标识符、E/S 等级、桶名、标签槽位字段名、attestation 字段名、
    human-manual label source 标识符、D4e 转换器源标识符、私有报告 schema
    标识符、经批准的 D4b bundle 字段名 token、门频段值和经批准的类别字符串
    （如 `tmp_only_local_private`）。任意短字符串（如 `compute_loss` 或私有
    文本）即使在契约容器内**也会被拒绝**（无过宽容器豁免）；敏感字段名
    （`content_sha`、`query_text`、`packet_ref`、`source_packet_schema`、
    `d4d_runbook_attestation`、`packets`）即使在契约容器内也被拒绝。字段名在
    任何位置作为键、在契约外作为值，均被拒绝。拒绝禁止的 dict 键和值模式：任何
    URL（无 URL 白名单）、32/40/64 字符十六进制摘要、类密钥字符串、类路径字符
    串、多行字符串、原始 JSON 片段、原始行范围以及自测 sentinel。
  - 私有 D4b bundle 输入守卫（与公开扫描器不同）：校验 D4e D4b bundle 输出形
    状（schema 恰为 `d4b_true_label_bundle_v1`、label_source 恰为
    `human_manual_true_e_s`、rater_count >= 2、agreement/CI 可用性为 bool、
    合成/真实标志为 bool 且组合真实、标签对象键恰为六个槽位、E/S 值在 D3 枚举
    内、bucket 在 D3 枚举内、citation_valid/rater_pair_present/adjudicated 为
    bool）；拒绝包引用/路径/代码片段/content_sha/查询/候选文本/标注者 ID/提供者
    payload/API 密钥/模型输出/原始一致性/置信区间数值/逐行哈希。
  - 私有 D4f 门报告输出守卫（与公开扫描器和私有 bundle 输入守卫**均**不同）：
    允许门布尔/频段和 schema/类别名称；拒绝标签列表/标签行/精确计数/一致性/
    CI 数值/任务/仓库/路径/代码片段/哈希/查询/标注者字段/输入输出路径或
    basename；校验 schema_version 恰为
    `d4f_bundle_validation_gate_private_report.v1`、`private_validation_report=true`、
    `public_artifact=false`、`do_not_commit=true`、
    `small_cell_suppression_required=true`、`public_release_gate_passed=false`、
    `d5_unblocked=false`、`*_emitted=false` 标志、合成/真实标志为真（合成 =>
    harness-only 且无真实校验；真实 => 未标记为合成）。
  - 解析后的 `/tmp` 输出守卫（强，仅对输出文件系统）：父目录符号链接逃逸被拒
    绝；已存在输出符号链接被拒绝；解析后目标必须保持在 `/tmp` 下。在打开或
    stat 输入之前校验（validate-before-read）。
  - CLI 守卫矩阵（纯词法，无文件系统）：`--input-bundle` 不带
    `--allow-private-bundle` 退出码 2；`--allow-private-bundle` 不带
    `--input-bundle` 退出码 2；私有模式要求显式 `--out`；提交产物路径在读取前
    被拒绝；非 `/tmp` 输出在读取前被拒绝；`--synthetic-harness-test` 不带
    `--allow-private-bundle` 退出码 2；路径遍历（`/tmp/../etc/...`）被拒绝。
  - 仅清洗过的错误：任何私有加载/解析/schema/隐私失败返回固定的
    `error: failed to load private bundle (schema/privacy/parse error; details suppressed)`；
    永不暴露输入路径、basename、原始 JSON 或标签文本。未知/类似私有输入的参数
    以通用 `invalid arguments` 消息拒绝（不回显值）。
  - 门检查逻辑（min-N=50、k_min=5、min_rater_count=2）：min-N 门在内部计算
    精确 N，但仅发出频段（`met`/`not_met`/`not_evaluated`）；k_min 门在内部计
    算每桶计数，但仅发出频段；永不发出精确 N 或单元计数。
  - 生成在自测失败或扫描器发现泄漏时拒绝成功（故障关闭 `_enforce_no_forbidden`
    + `_refuse_on_self_test_failure` 在写 JSON 之前立即执行）。

### 验证结果

```text
python3 -m py_compile eval/d4f_bundle_validation_gate.py    => PASS
python3 eval/d4f_bundle_validation_gate.py --self-test      => PASS (352/352 checks)
python3 eval/d4f_bundle_validation_gate.py \
  --out artifacts/d4f_bundle_validation_gate/\
d4f_bundle_validation_gate_report.json                     => PASS
  (status: blocked_no_private_bundle_available_or_no_validation_run,
   forbidden_scan: pass, self_test_passed: true,
   private_bundle_read: false,
   bundle_validation_run: false,
   d5_unblocked: false,
   public_release_gate_passed: false,
   bundle_validation_harness_available: true,
   private_cli_guard_validated: true,
   tmp_output_resolved_guard_validated: true,
   sanitized_error_guard_validated: true,
   d4b_bundle_schema_contract_defined: true,
   gate_check_contract_defined: true,
   min_n_gate_referenced: true,
   k_min_gate_referenced: true,
   agreement_availability_gate_referenced: true,
   ci_availability_gate_referenced: true,
   mode: public_harness_no_private_bundle_no_validation, phase: D4f,
   d4b_bundle_schema_source: d4b_true_label_bundle_v1,
   d4e_converter_source: d4e_filled_packet_converter_harness.v1,
   d4d_runbook_protocol: d4d_human_annotation_runbook.v1)
# 私有 /tmp 合成 smoke（不提交）：
python3 eval/d4f_bundle_validation_gate.py \
  --allow-private-bundle --synthetic-harness-test \
  --input-bundle /tmp/synthetic_d4b_bundle.json \
  --out /tmp/d4f_synthetic_validation.json                      => PASS
  (synthetic_harness_test=true,
   synthetic_bundle_validated_for_harness_only=true,
   local_private_bundle_validation_run=false,
   real_human_bundle_validated=false,
   schema_gate_passed=true, public_release_gate_passed=false,
   d5_unblocked=false)
# 私有 /tmp real-mode flag-path smoke（不提交；在合成夹具上，D4e real-conversion
# 标志设为 true）：
python3 eval/d4f_bundle_validation_gate.py \
  --allow-private-bundle \
  --input-bundle /tmp/real_flagpath_d4b_bundle.json \
  --out /tmp/d4f_real_flagpath_validation.json                  => PASS
  (synthetic_harness_test=false,
   local_private_bundle_validation_run=true,
   real_human_bundle_validated=true,
   public_release_gate_passed=false,
   d5_unblocked=false)
python3 scripts/validate_docs_i18n.py                           => PASS
git diff --check                                               => PASS
```

D4f 是真实标签存在之前的最后一个有用夹具：D4e 证明已填充 packet 可以在本地
转换为 D4b bundle；D4f 证明 D4b bundle 可以在本地校验并检查门前提，而无需发
布标签、精确计数或指标。D4f 实现了一个带 SafeArgumentParser CLI 的私有校验
器夹具（未知/类似私有输入参数不回显值）、一个严格故障关闭的公开扫描器带精确
契约字符串白名单（无过宽容器豁免——未批准字符串和敏感字段名即使在契约容器内
也被拒绝）、一个与公开扫描器和私有 bundle 输入守卫**均**不同的私有 D4f 门报
告输出守卫（允许门布尔/频段和 schema/类别名称；拒绝标签列表/标签行/精确计
数/一致性/CI 数值/任务/仓库/路径/代码片段/哈希/查询/标注者字段/输入输出路
径；校验 schema_version、`*_emitted=false` 标志和合成/真实标志为真）、一个解
析后的 `/tmp` 输出守卫（父目录符号链接逃逸、已存在输出符号链接和解析后目标逃
逸均被拒绝）、validate-before-read 顺序、以及故障关闭的生成在扫描器泄漏或自
测失败时拒绝成功。门检查逻辑（min-N=50、k_min=5、min_rater_count=2）在内部
计算精确 N 和每桶计数，但仅发出频段（`met`/`not_met`/`not_evaluated`）；永不
发出精确 N 或单元计数。默认提交 artifact 是夹具 / 无校验 artifact：它不读取任
何私有 D4b bundle，不运行任何校验，不持久化任何私有 bundle，不读取任何标签，
不计算任何校准/一致性/CI，不执行任何模型/LLM 标注，也不通过任何公开发布门。
D5 保持锁定。在合成夹具上的 real-mode flag-path 测试（在本地设置
`local_private_bundle_validation_run=true` 和
`real_human_bundle_validated=true`）仅是 flag-path 测试，**不**是真实标签
存在的证据。

### 注意事项

- D4f 仅是 D4b bundle 校验 / 门检查夹具公开 artifact。它是
  eval/诊断专用。它**不**改变运行时、retriever、pack、model、backend 或默认策
  略；也**不**改变 EvidenceCore 语义。它不是基准测试结果，不是下游 agent 价值
  声明，不是 runtime-clean 通用算法声明，不是 OOD 时间性声明，也不是 QuIVer
  系统声明。
- D4f 默认是带阻塞公开产物的夹具。默认提交产物**不**读取任何私有 D4b
  bundle，**不**运行任何校验，**不**持久化任何私有 bundle，**不**读取任何
  标签，**不**计算任何校准/一致性/置信区间，**不**执行任何模型/LLM
  标注，也**不**通过任何公开发布门。D5 保持锁定。夹具/控制 true 标志仅对已
  校验的夹具/控制为 true，而非任何真实 bundle 校验或门通过声明。
- D4f **不是**提交输出中的真实 bundle 校验，**不是**门通过，**不是**校准，
  **不是**一致性/置信区间计算，也**不**解锁 D5。它是真实标签存在之前的最后
  一个有用夹具。
- D4f 有私有校验器模式（可选，不提交）。私有输出仅写入 `/tmp` 且永不提交。
  私有报告仅含门布尔和频段（无标签、无精确计数、无指标）。在合成夹具上的
  real-mode flag-path 测试（在本地设置
  `local_private_bundle_validation_run=true` 和
  `real_human_bundle_validated=true`）仅是 flag-path 测试，**不**是真实标签
  存在的证据。真实人工标签尚未采集；D5 保持锁定。
- 校验器仅消费 D4e D4b bundle 输出形状；它拒绝包引用/路径/代码片段/
  content_sha/查询文本/候选文本/标注者 ID/提供者 payload/API 密钥/模型输出/
  原始一致性/置信区间数值/逐行哈希/未知键。D4f 仅校验 schema 和门可用性，
  不计算指标。
- min-N 和 k-min 门在内部计算（精确 N 和每桶计数），但报告仅发出频段
  （`met`/`not_met`/`not_evaluated`）；永不发出精确 N 或单元计数。
- 所有无声明 / 无运行时变更标志保持 false；诊断标志
  （`aggregate_only_public_artifact`、`diagnostic_only`、`not_evidence`）保持
  true；夹具/控制 true 标志是唯一为 true 的控制标志。
- 未修改 runtime/retriever/pack/model/backend/default-policy 文件。
  `current-research-conclusions` **未**更新（D4f 是夹具/仅阻塞 artifact；结论
  无变化）。

---

## 2026-06-20 — D4 系列 Harness 汇总 / D5 阻塞状态（公开纯汇总 artifact）

### 目标

实现一个**D4 系列 harness 汇总 / D5 阻塞状态**公开 artifact。这是**纯汇
总**，**不是**新的研究阶段。它仅汇总已提交的 D4a-D4f 公开状态/声明级别以
及 D5 阻塞项。它不执行任何私有读取、不进行任何探针、不产生任何 `/tmp` 输
出、不采集标签、不计算指标、也不进行 D5 校准。汇总不得读取私有记录/数据
包/标签/bundle，不得在任何提交产物中发出标签/原始标签行/精确计数/一致性/
置信区间数值，不得接受包引用/任务 ID/仓库 ID/路径/跨度/代码片段/内容哈希/
查询/候选文本/标注者 ID/模型输出/提供者 payload，不得计算校准/标注者间一
致性/置信区间，不得通过任何公开发布门，不得解锁 D5，不得声明真 E/S 校准，
不得执行模型/LLM 标注，且不得改变运行时行为、retriever、pack、model、
backend、默认策略或 EvidenceCore 语义。

### 实现

- 新脚本 `eval/d4_series_rollup.py`（纯 Python 标准库；无外部依赖）。仅公
  开纯汇总 artifact；无私有模式，无 `/tmp` 输出，无私有输入 CLI 守卫。
  - Schema 版本 `d4_series_rollup.v1`；声明级别
    `d4_series_harness_rollup_only`；状态
    `d5_blocked_no_real_human_manual_labels`；模式
    `public_rollup_no_private_reads`；阶段 `D4-rollup`。
  - CLI：`--self-test`、`--out`。未知/类似私有的参数以通用的 `invalid
    arguments` 消息拒绝，不回显私有路径或基名（SafeArgumentParser 模式）。
    汇总没有 `--allow-private-*`、没有 `--input-*`、也没有
    `--synthetic-*` 标志：它是纯汇总，不读取任何私有输入。
  - `d4_phases`：恰好六个条目（D4a-D4f），每个恰好一次，每个恰好有四个键
    `phase`、`commit`、`artifact_status`、`claim_level`。短 commit ID：
    `d62c13b`（D4a）、`6dd4024`（D4b）、`3458716`（D4c）、`55c9850`
    （D4d）、`280d8bb`（D4e）、`fea76d3`（D4f）。各阶段 `artifact_status`：
    `execution_gate_ready_no_labels_collected`（D4a）、
    `blocked_no_true_label_bundle_available`（D4b）、
    `blocked_no_annotation_packets_created`（D4c）、
    `protocol_ready_no_raters_no_labels_no_packets`（D4d）、
    `blocked_no_filled_packets_available_or_no_conversion_run`（D4e）、
    `blocked_no_private_bundle_available_or_no_validation_run`（D4f）。
    各阶段 `claim_level`：
    `dual_rubric_execution_gate_dry_run_only`（D4a）、
    `true_label_bundle_execution_harness_only`（D4b）、
    `annotation_packet_builder_harness_only`（D4c）、
    `human_annotation_runbook_protocol_only`（D4d）、
    `filled_packet_to_d4b_bundle_converter_harness_only`（D4e）、
    `d4b_bundle_validation_gate_harness_only`（D4f）。
  - 安全 true 标志（恰好十个，全部为 true）：
    `control_plane_chain_complete`、`d4a_execution_gate_complete`、
    `d4b_true_label_bundle_harness_complete`、
    `d4c_annotation_packet_builder_harness_complete`、
    `d4d_human_annotation_runbook_complete`、
    `d4e_converter_harness_complete`、
    `d4f_bundle_validation_gate_harness_complete`、
    `aggregate_only_public_artifact`、`diagnostic_only`、
    `not_evidence`。默认提交 artifact 中无任何读取/标签/计数/指标/D5 声明
    标志为 true。
  - D5 前提条件标志（全部为 false）：
    `real_human_manual_labels_available`、
    `d4e_real_local_conversion_over_real_labels_run`、
    `d4f_real_local_validation_over_real_labels_run`、
    `min_n_gate_passed_for_real_labels`、
    `k_min_gate_passed_for_real_labels`、
    `agreement_gate_passed_for_real_labels`、
    `ci_gate_passed_for_real_labels`、
    `d5_public_aggregate_candidate_allowed`。相同值也在 `d5_prerequisites`
    对象下分组，以便阅读；自测断言 flat 与 nested 表示完全一致。
  - 无读取/无声明/无运行时变更标志（全部为 false）：
    `private_records_read`、`private_packets_read`、
    `private_labels_read`、`private_bundles_read`、`labels_collected`、
    `calibration_metrics_computed`、`agreement_metrics_computed`、
    `confidence_intervals_computed`、
    `true_e_s_calibration_claimed`、`promotion_ready`、
    `default_should_change`、`downstream_agent_value_proven`、
    `runtime_behavior_changed`、`retriever_changed`、
    `pack_builder_changed`、`model_calls_changed`、`backend_changed`、
    `default_policy_changed`、`evidencecore_semantics_changed`、
    `runtime_clean_general_algorithm_claimed`、
    `ood_temporal_supported`、`quiver_systems_supported`。
  - 严格公开扫描器（故障关闭，带精确契约字符串白名单）。`d4_phases` 列表是
    一个精确契约容器：其中的字符串**值**必须在
    `APPROVED_CONTRACT_STRINGS` 中（阶段 ID `D4a`-`D4f` + `D4-rollup`；
    六个短 commit ID；六个阶段级 `artifact_status` 字符串；六个阶段级
    `claim_level` 字符串）。任意短字符串（如 `compute_loss` 或私有文本）
    即使在契约容器内也被拒绝（无过宽容器豁免）；敏感字段名
    （`content_sha`、`query_text`、`packet_ref`、
    `source_packet_schema`、`d4d_runbook_attestation`、`packets`）即使在
    契约容器内也被拒绝，且作为键在任何位置也被拒绝。拒绝禁止的字典键出现在
    任何位置，并拒绝值模式：任何 URL（无 URL 白名单）、32/40/64 字符十六进
    制摘要、类似密钥的字符串、路径形式字符串、多行字符串、原始 JSON 片段、
    原始行范围以及自测哨兵。
  - 生成在自测失败或扫描器发现泄漏时拒绝成功（故障关闭的
    `_enforce_no_forbidden` + `_refuse_on_self_test_failure`，在写入 JSON
    前立即执行）。

### 验证结果

```text
python3 -m py_compile eval/d4_series_rollup.py    => PASS
python3 eval/d4_series_rollup.py --self-test      => PASS (147/147 checks)
python3 eval/d4_series_rollup.py \
  --out artifacts/d4_series_rollup/d4_series_rollup_report.json  => PASS
  (status: d5_blocked_no_real_human_manual_labels,
   forbidden_scan: pass, self_test_passed: true,
   control_plane_chain_complete: true,
   d5_public_aggregate_candidate_allowed: false,
   real_human_manual_labels_available: false,
   mode: public_rollup_no_private_reads, phase: D4-rollup,
   d4_phases: [D4a d62c13b, D4b 6dd4024, D4c 3458716,
               D4d 55c9850, D4e 280d8bb, D4f fea76d3])
python3 scripts/validate_docs_i18n.py             => PASS
git diff --check                                 => PASS
```

D4 系列汇总是一个带 SafeArgumentParser CLI（未知/类似私有参数不回显值）、
严格故障关闭公开扫描器带精确契约字符串白名单（无过宽容器豁免——未批准字符
串和敏感字段名即使在 `d4_phases` 契约容器内也被拒绝）、以及故障关闭生成在
扫描器泄漏或自测失败时拒绝成功的公开纯汇总 artifact。汇总恰好列出六个 D4
阶段（D4a-D4f），每个恰好一次，附带其已提交的短 commit ID、各阶段
`artifact_status` 与各阶段 `claim_level`。默认提交 artifact 不读取任何私
有记录/数据包/标签/bundle，不采集任何标签，不计算任何校准/一致性/置信区
间，不执行任何模型/LLM 标注，也不通过任何公开发布门。D5 保持阻塞，因为真
实人工手动标签尚未采集。

### 注意事项

- D4 系列汇总是公开纯汇总 artifact。它是 eval/诊断专用。它**不**改变运行
  时、retriever、pack、model、backend 或默认策略；也**不**改变
  EvidenceCore 语义。它不是基准测试结果，不是下游 agent 价值声明，不是
  runtime-clean 通用算法声明，不是 OOD 时间性声明，也不是 QuIVer 系统声
  明。
- 汇总仅聚合已提交的 D4a-D4f 公开状态/声明级别。它**不**重新运行任何 D4
  夹具，**不**采集标签，**不**计算校准/一致性/置信区间，**不**校验任何
  bundle，也**不**解锁 D5。D5 保持阻塞，因为真实人工手动标签尚未采集。
- `d4_phases` 中的 `artifact_status` 字符串是 D4 系列汇总契约指定的汇总摘
  要形式。D4c 汇总摘要状态为
  `blocked_no_annotation_packets_created`；位于
  `artifacts/d4c_annotation_packet_builder/` 的底层已提交 D4c artifact 报告
  了更完整的状态
  `blocked_no_private_source_records_available_or_no_packets_built`
  （相同的阻塞语义，更完整的措辞）。D4a、D4b、D4d、D4e 和 D4f 的汇总状态
  与底层已提交 artifact 逐字匹配。全部六个 `claim_level` 值与全部六个短
  commit ID 与底层已提交 artifact 逐字匹配。
- 安全 true 标志仅表达控制面链与各 D4 夹具 artifact 已存在且已提交。它们
  **不**是真实标签采集、真实转换、真实校验、门通过、校准、一致性、置信区
  间或 D5 解锁的声明。
- 所有无声明/无运行时变更标志保持 false；诊断标志
  （`aggregate_only_public_artifact`、`diagnostic_only`、
  `not_evidence`）保持 true；安全 true 标志是唯一为 true 的标志。
- 未修改 runtime/retriever/pack/model/backend/default-policy 文件。
  `current-research-conclusions` **未**更新（汇总为纯汇总/D5 阻塞
  artifact；结论无变化）。

---

## 2026-06-20 — D5-A0 自动 E/S 校准 Smoke

### 目标

通过从已提交 r14 sanity span 标签（gold spans + hard negatives）在真实
OpenLocus retrieval 输出（regex、bm25、symbol、rrf）上派生自动 E 标签与确定性
S-proxy 标签，产出 Step 6 dual-rubric 流水线在控制面之后的首个实证 smoke。停
止“仅控制面”阶段；在不采集新人工/手动标签的前提下产出实证结果。

### 假设

已提交的 span 标签（gold + hard negatives）足以在真实 retrieval 输出上派生
smoke-only 的自动 E/S 校准信号，而无需被新人工/手动 true E/S 标签阻塞，也无需
声明 true E/S 校准。

### 实现说明

- **D5-A0 artifact**（`eval/d5a_automated_es_calibration.py`）：公开仅聚合
  smoke。使用已提交 r14 sanity 固定数据
  （`fixtures/r14/tasks/sanity.jsonl` + `fixtures/r14/labels/sanity.jsonl`）；
  按方法调用 `eval/run_retrieval.py`，将输出写入临时
  `/tmp/d5a_retrieval_*` 目录；读取这些临时输出（绝不提交）；计算自动 E 标签
  与确定性 S-proxy 标签；仅将聚合 counts/rates 写入已提交 artifact。
- **自动 E 标签流程**（确定性；从已提交 span 标签派生；绝不作为真实人工
  E/S）：无效/源缺失 -> `e_uncertain`；同时重叠 hard-negative 与 gold ->
  `conflict_uncertain`；仅重叠 hard-negative -> `e_hard_negative`；重叠
  gold -> `e_positive`；同 gold 文件但无 gold 重叠 ->
  `e_wrong_span_gold_file`；非 gold 文件且 span 有效 ->
  `e_negative_non_gold_file`；缺失标签绝不作为负样本。
- **S-proxy 标签流程**（确定性 support-shape 信号，**不是**真实人工
  S-score）：E-positive -> `s_proxy_not_evaluated_for_e_positive`（避免混
  淆）；`e_hard_negative`/`conflict_uncertain`/`e_uncertain` ->
  `s_proxy_none`；`e_wrong_span_gold_file` -> `s_proxy_positive`；同 gold
  文件上 gold span 邻接（+/-5 行，无重叠）-> `s_proxy_positive`；其他 ->
  `s_proxy_none`。
- **Artifact 身份**：`schema_version=d5a_automated_es_calibration.v1`、
  `claim_level=automated_e_s_calibration_smoke_only`、
  `status=automated_es_calibration_smoke_pass`（成功时）、
  `mode=public_aggregate_r14_retrieval_smoke`、`phase=D5-A0`。
- **无声明 / 无运行时变更标志**（全部为 false）：
  `automated_e_s_calibration_claimed`、
  `human_e_s_calibration_claimed`、`new_human_labels_collected`、
  `human_reference_audit_claimed`、`promotion_ready`、
  `default_should_change`、`evidencecore_semantics_changed`、
  `runtime_clean_general_algorithm_claimed`、
  `downstream_agent_value_proven`、
  `external_benchmark_performance_claimed`、
  `runtime_behavior_changed`、`retriever_changed`、
  `pack_builder_changed`、`model_calls_changed`、`backend_changed`、
  `default_policy_changed`、`true_e_s_calibration_claimed`、
  `raw_predictions_committed`、`raw_retrieval_outputs_committed`、
  `per_candidate_rows_emitted`、`public_release_gate_passed`、
  `d5_human_reference_calibration_unblocked`、`ood_temporal_supported`、
  `quiver_systems_supported`。
- **安全 true 标志**（恰好这些，全部为 true）：
  `aggregate_only_public_artifact`、`diagnostic_only`、`not_evidence`、
  `automated_e_s_calibration_smoke_claimed`、`automated_d5a_path_active`、
  `uses_existing_committed_labels`、`self_test_executed`、
  `transient_retrieval_outputs_only`。
- **严格公开扫描器**（故障关闭，带精确契约字符串白名单）。契约容器
  `methods_evaluated`、`methods_attempted`、`methods_succeeded`、
  `e_label_categories`、`s_proxy_label_categories` 是精确白名单：仅允许
  已批准 short token（方法名、fixture 类别、E/S 标签类别 token、retrieval
  类别 token）在其中出现。任意短字符串（如 `compute_loss` 或私有文本）即使
  在契约容器内也被拒绝（无过宽容器豁免）；敏感字段名
  （`content_sha`、`query_text`、`candidate`、`gold`、`hard_negative`、
  `evidence`、`predictions`、`retrieval_output` 等）即使在契约容器内也被拒
  绝，且作为键在任何位置也被拒绝。拒绝禁止的字典键出现在任何位置，并拒绝值
  模式：任何 URL（无 URL 白名单）、32/40/64 字符十六进制摘要、类似密钥的字
  符串、路径形式字符串、多行字符串、原始 JSON 片段、原始行范围，以及自测
  sentinel。Scanner 仅对最终公开聚合 artifact 执行（不对内存中的
  predictions/labels 扫描，因为后者包含 path/start_line 等）。
- **生成在自测失败或扫描器发现泄漏时拒绝成功**（故障关闭的
  `_enforce_no_forbidden` + `_refuse_on_self_test_failure`，在写入 JSON 前
  立即执行）。
- **Label-source 聚合键是显式白名单**：批准的 committed fixture 类别
  （`human_reviewed`、`mined`、`mined_high_confidence`、`unknown`）按原样计数；
  任何未批准的逐行来源类别折叠为 `other_unapproved_label_source_category`，
  scanner 拒绝 `label_source_category_counts` 下未批准的动态键。

### 验证结果

```text
python3 -m py_compile eval/d5a_automated_es_calibration.py    => PASS
python3 eval/d5a_automated_es_calibration.py --self-test      => PASS (157/157 checks)
python3 eval/d5a_automated_es_calibration.py \
  --out artifacts/d5a_automated_es_calibration/\
d5a_automated_es_calibration_report.json                     => PASS
  (status: automated_es_calibration_smoke_pass,
   forbidden_scan: pass, self_test_passed: true,
   mode: public_aggregate_r14_retrieval_smoke, phase: D5-A0,
   methods_succeeded: [regex, bm25, symbol, rrf],
   candidate_count_total: 3152,
   uses_existing_committed_labels: true,
   automated_d5a_path_active: true,
   new_human_labels_collected: false,
   human_e_s_calibration_claimed: false,
   automated_e_s_calibration_claimed: false,
   raw_retrieval_outputs_committed: false,
   per_candidate_rows_emitted: false,
   promotion_ready: false,
   default_should_change: false,
   retriever_changed: false,
   pack_builder_changed: false,
   model_calls_changed: false,
   backend_changed: false,
   default_policy_changed: false,
   evidencecore_semantics_changed: false,
   runtime_behavior_changed: false,
   runtime_clean_general_algorithm_claimed: false,
   downstream_agent_value_proven: false,
   external_benchmark_performance_claimed: false,
   d5_human_reference_calibration_unblocked: false,
   public_release_gate_passed: false)
python3 scripts/validate_docs_i18n.py                           => PASS
git diff --check                                               => PASS
```

D5-A0 smoke 是 D4 系列控制面 harness 因缺少真实人工/手动 true E/S 标签而被
阻塞后的首个实证 artifact。D5-H / 人工参考 / 人工校准审计在真实人工/手动
true E/S 标签采集前仍属 out of scope/不可用；D5-A 自动/程序化实证路径已激活。
D5-A0 从已提交 r14 sanity span 标签在真实 OpenLocus retrieval 输出（regex、
bm25、symbol、rrf 全部成功；共标记 3152 个 candidate）上派生自动 E/S 标签。
它是 smoke-only：**不**声明 true E/S 校准，**不**采集新人工标签，**不**审计
人工参考标签，**不**通过任何公开发布门，**不**提升任何 candidate，也**不**
解锁 D5-H / 人工参考 / 人工校准声明或 default/policy/公开发布声明。详见
[D5-A0 详细报告](d5a-automated-es-calibration.md)。

### 注意事项

- D5-A0 是公开仅聚合 smoke artifact。它是 eval/诊断专用。它**不**改变运行
  时、retriever、pack、model、backend 或默认策略；也**不**改变 EvidenceCore
  语义。它不是基准测试结果，不是下游 agent 价值声明，不是 runtime-clean 通
  用算法声明，不是 OOD 时间性声明，也不是 QuIVer 系统声明。
- D5-A0 使用已提交 r14 sanity 标签（gold spans + hard negatives）派生自动
  E 标签与确定性 S-proxy 标签。这些**不是**真实人工/手动 E/S 分数，也**不
  是** D3 dual-rubric E/S 分数。它们是从已提交 span 标签派生的 smoke-only
  聚合信号。
- D5-A0 **不**采集新人工/手动标签，**不**审计人工参考标签，**不**声明
  true E/S 校准，**不**通过任何公开发布门，也**不**解锁 D5-H / 人工参考 /
  人工校准声明或 default/policy/公开发布声明。D5-H / 人工参考 / 人工校准
  审计在真实人工/手动 true E/S 标签采集前仍属 out of scope/不可用；D5-A
  自动实证路径已激活并继续。
- D5-A0 按方法调用 `eval/run_retrieval.py`，输出写入临时
  `/tmp/d5a_retrieval_*` 目录并读取这些临时输出（绝不提交）。已提交
  artifact 仅包含聚合 counts/rates；无 per-candidate 行、无 path、无
  span、无 snippet、无 content_sha、无 query、无 gold 标签、无
  hard-negative 标签、无 task/repo ID、无行级数据。
- 聚合指标是 smoke-only，取决于已提交 r14 sanity 固定数据形状、四种固定
  retrieval 方法以及上述确定性 E/S 标签流程。它们**不**可跨不同
  fixture、标签集、方法或流程比较，也**不**是基准测试性能声明。
- 所有无声明 / 无运行时变更标志保持 false；诊断标志
  （`aggregate_only_public_artifact`、`diagnostic_only`、
  `not_evidence`）保持 true；smoke-claimed / 使用已提交标签 / D5-A 路径已
  激活标志（`automated_e_s_calibration_smoke_claimed`、
  `automated_d5a_path_active`、`uses_existing_committed_labels`、
  `self_test_executed`、`transient_retrieval_outputs_only`）是仅有的额
  外 true 标志。
- 未修改 runtime/retriever/pack/model/backend/default-policy 文件。
  `current-research-conclusions` 已更新以澄清：D5-H / 人工参考 / 人工校
  准在人工标签到位前仍属 out of scope，而 D5-A 自动实证路径已激活；不
  改变任何 promotion/default/runtime 声明。

---

## 2026-06-20 — B16-A 最小 Mock 下游 Paired Run

### 目标

产出首个**非仅控制面**的 B16 风格下游 agent 实证 run，无需等待 live
LLM agent 或 provider 凭据。在 `/tmp` 下生成隔离的合成公开 micro bug 工
作区，运行 paired control/treatment arms，执行行为依赖于所提供 context
pack 的确定性 mock agent，执行真实文件编辑，运行真实子进程测试，并仅输
出公开聚合行为指标。

### 假设

行为依赖 context pack 的确定性 mock agent 能在合成公开 micro 任务上执行
完整 B16 下游 agent edit/test 循环，并产出行为指标（solve_rate、
tests_pass_rate、correct_file_before_first_edit_rate、
wrong_file_edits_mean、tool_calls_before_first_edit_mean、
context_tokens_mean、latency_ms_mean、cost_proxy_mean），无需 live LLM
且不声明下游 agent 价值。

### 实现说明

- **B16-A artifact**
  （`eval/b16a_minimal_mock_agent_paired_run.py`）：公开仅聚合
  smoke。在代码中生成确定性合成公开 micro bug 任务（默认 24；
  `--task-count` 范围 4-32）；为每个 task+arm 创建全新 `/tmp` 工作区，
  含真实微型 Python 模块 + stdlib 测试；运行确定性 mock agent（真实文
  件编辑 + 真实子进程测试）；计算聚合行为指标；仅写入聚合
  counts/rates/means 到提交的 artifact。
- **Paired arm 设计**：预算/工具约束相同；仅 context pack 不同。
  **control** pack 为 bare/wrong-cue（偶数索引任务携带指向 distractor
  的 wrong-cue file；奇数索引任务无文件 cue）。**treatment** pack 为更
  丰富的 evidence pack，含 target file/symbol/operation hint cue。
  treatment pack 对设计子集因果地改变确定性 mock agent 的行为。
- **确定性 mock agent**：依赖 pack。若 pack 含 `target_file` cue -> 用
  正确修复编辑该文件（测试通过）。若 pack 含 `wrong_cue_file` cue ->
  编辑错误文件（测试仍失败；wrong_file_edits=1）。否则 -> 什么都不做
  （测试失败；无编辑）。编辑/no-op 后，运行真实子进程测试命令
  （`python3 <workspace>/test_target.py`）。
- **Artifact 身份**：
  `schema_version=b16a_minimal_mock_agent_paired_run.v1`、
  `claim_level=deterministic_mock_downstream_paired_smoke_only`、
  `status=mock_downstream_paired_smoke_pass`（成功时）、
  `mode=public_aggregate_synthetic_micro_tasks`、`phase=B16-A`。
- **Safe true flags**（仅这些，全为 true）：
  `downstream_agent_runs_performed`、`deterministic_mock_agent`、
  `synthetic_micro_tasks_used`、`paired_arms_evaluated`、
  `real_file_edits_performed`、`real_test_commands_executed`、
  `agent_behavior_metrics_evaluated`、`aggregate_only_public_artifact`、
  `diagnostic_only`。
- **No-claim / no-runtime-change flags**（全为 false）：
  `live_llm_agent`、`provider_calls_made`、`remote_calls_made`、
  `downstream_agent_value_proven`、`promotion_ready`、
  `default_should_change`、`runtime_behavior_changed`、
  `retriever_changed`、`pack_builder_changed`、`backend_changed`、
  `default_policy_changed`、`evidencecore_semantics_changed`、
  `external_benchmark_performance_claimed`、
  `live_agent_generalization_claimed`、`real_user_task_claimed`。
- **严格公开 scanner**（fail-closed）。拒绝 forbidden dict key 在任何位
  置出现（`task_id`、`workspace_path`、`file`、`target_file`、
  `wrong_cue_file`、`path`、`span`、`content_sha`、`snippet`、`code`、
  `patch`、`diff`、`test_output`、`stdout`、`stderr`、`event_log`、
  `stack_trace`、`api_key`、`base_url`、`provider_key`、`secret`、
  `token`、`credential`、`rows`、`per_run`、`predictions` 等）及 value
  模式：任意 URL（无 URL 允许列表）、32+ 字符 hex digest、secret-like
  字符串、带文件扩展名的 path-like 字符串、`/tmp/` 工作区路径 value、
  `task_N` 任务标识 value、patch/diff 标记（`---`、`+++`、`@@`）、堆栈跟
  踪（`Traceback (most recent call last)`）、多行字符串、raw JSON 片段、
  raw 行范围及 self-test sentinel。scanner 仅对最终公开聚合 artifact 运
  行（不对含路径/patch/测试输出的内存 per-run event log 运行）。
- **生成在 self-test 失败或 scanner 发现泄漏时拒绝成功**（fail-closed
  `_enforce_no_forbidden` + `_refuse_on_self_test_failure` 在写入 JSON
  前立即运行）。
- **per-run event log/patch/测试输出仅留在 `/tmp`**，绝不提交或上传。提
  交的 artifact 仅含聚合 counts/rates/means。

### 验证结果

```text
python3 -m py_compile eval/b16a_minimal_mock_agent_paired_run.py    => PASS
python3 eval/b16a_minimal_mock_agent_paired_run.py --self-test      => PASS (105/105 checks)
python3 eval/b16a_minimal_mock_agent_paired_run.py \
  --out artifacts/b16a_minimal_mock_agent_paired_run/\
b16a_minimal_mock_agent_paired_run_report.json                     => PASS
  (status: mock_downstream_paired_smoke_pass,
   forbidden_scan: pass, self_test_passed: true,
   mode: public_aggregate_synthetic_micro_tasks, phase: B16-A,
   synthetic_task_count: 24, total_runs: 48,
   control: solve_rate=0.0, tests_pass_rate=0.0,
     correct_file_before_first_edit_rate=0.0, wrong_file_edits_mean=0.5,
   treatment: solve_rate=1.0, tests_pass_rate=1.0,
     correct_file_before_first_edit_rate=1.0, wrong_file_edits_mean=0.0,
   deltas_treatment_minus_control: solve_rate=+1.0,
     wrong_file_edits_mean=-0.5,
   live_llm_agent: false, provider_calls_made: false,
   remote_calls_made: false, downstream_agent_value_proven: false,
   promotion_ready: false, default_should_change: false,
   retriever_changed: false, pack_builder_changed: false,
   backend_changed: false, default_policy_changed: false,
   evidencecore_semantics_changed: false, runtime_behavior_changed: false,
   external_benchmark_performance_claimed: false,
   live_agent_generalization_claimed: false, real_user_task_claimed: false)
python3 scripts/validate_docs_i18n.py                           => PASS
git diff --check                                               => PASS
```

B16-A smoke 是首个非仅控制面的 B16 风格下游 agent 实证 run。它在合成公开
micro 任务上用确定性 mock agent（无 live LLM、无 provider 调用、无远程
调用）执行真实 edit/test 循环。treatment pack 因果地改变 mock agent 的
行为（treatment solve_rate=1.0 vs control solve_rate=0.0），展示 pack 效
果 smoke。它明确**不是** live 下游 agent 价值声明，**不是** live agent
泛化声明，**不是**外部基准测试性能声明，也**不是**真实用户任务声明。
完整 B16 下游 coding-agent 评估阶段仍是需要真实 provider 调用的 live
paired agent run 的有界规划/可行性阶段。详见
[B16-A 详细报告](b16a-minimal-mock-agent-paired-run.md)。

### 注意事项

- B16-A 是公开仅聚合最小 mock 下游 paired smoke artifact。它是
  eval/诊断专用。它**不**改变 runtime、retriever、pack、backend 或
  default policy；它**不**改变 EvidenceCore 语义。它**不是**基准测试
  结果，**不是** live 下游 agent 价值声明，**不是** runtime-clean 通用
  算法声明，**不是** OOD 时间性声明，也**不是** QuIVer 系统声明。
- B16-A 使用**确定性 mock agent**（无 live LLM、无 provider 调用、无远
  程调用）。mock agent 的行为按设计依赖 pack：treatment pack 含 target
  file/symbol/operation cue，而 control pack 缺少 target cue 或携带
  wrong-cue file。这是因果 pack 效果 smoke，**不是** live agent 价值
  声明。
- B16-A 在代码中生成**确定性合成公开 micro bug 任务**。这些**不是**真
  实用户任务，也**不是**外部基准测试任务。因为是合成公开任务，确切的
  任务/run 计数可接受。
- B16-A 在每个 task+arm 的全新 `/tmp` 工作区中执行**真实文件编辑**和
  **真实子进程测试**（stdlib Python）。per-run event log、patch 和测试
  输出仅留在 `/tmp`，**绝不**提交或上传。提交的 artifact 仅含聚合
  counts/rates/means。
- B16-A **不**证明下游 agent 价值。treatment-vs-control delta 是设计
  pack cue 的确定性 mock 产物，**不是** treatment pack 改善 live 下游
  agent 的证据。`downstream_agent_value_proven=false`。
- B16-A **不**声明 live agent 泛化。确定性 mock agent 按构造平凡地泛化
  到合成任务族；这**不是** live agent 泛化声明。
  `live_agent_generalization_claimed=false`。
- 所有无声明 / 无运行时变更标志保持 false；诊断标志
  （`aggregate_only_public_artifact`、`diagnostic_only`）保持 true；
  确定性 mock run 标志是仅有的额外 true 标志。未修改任何
  runtime/retriever/pack/model/backend/default-policy 文件；无
  promotion/default/runtime 声明变更。

---

## 2026-06-21 — B16-B Less-Separable Mock 下游 Paired-Agent 压力测试

> 中文译本待补充。以下为英文原文，避免内容丢失。

### English source / 英文原文

### Objective

Extend B16-A from deliberately separable synthetic micro bugs to a
harder deterministic/mock downstream paired-agent **stress** run. This
remains empirical: real temporary workspaces, real file edits, real
subprocess tests, aggregate
solve/correct-file/wrong-file/tool-call/context/latency/cost-proxy
metrics. The new work reduces the artificial separability of B16-A
without jumping yet to live-provider agent execution.

### Hypothesis

A deterministic mock agent whose action depends on a **multi-cue**
context pack (target_file + target_symbol + operation_hint +
support_relation) can exercise the full B16 downstream-agent edit/test
loop on harder less-separable synthetic tasks (within-file symbol
ambiguity + cross-file symbol ambiguity + support offset) and produce
behavior metrics over paired control/treatment arms, without a live
LLM and without claiming downstream agent value. The treatment pack
causally alters the mock agent's behavior; treatment is perfect by
construction and docs describe this as a harness/stress result, NOT a
live agent result.

### Implementation notes

- **B16-B artifact** (`eval/b16b_less_separable_mock_paired_run.py`):
  public aggregate-only stress. Generates deterministic synthetic
  public less-separable stress tasks in code (default 24;
  `--task-count` range 4-32); creates a fresh `/tmp` workspace per
  task+arm with real multi-file Python modules (target.py with decoy
  symbol, distractor.py with same symbol, support.py with offset
  constant, test_target.py) + stdlib tests; runs a deterministic mock
  agent (real file edits + real subprocess tests); computes aggregate
  behavior metrics; writes ONLY aggregate counts/rates/means to the
  committed artifact.
- **Less-separable task family**: each task requires combining four
  cues to solve: `target_file` (to pick target.py, not distractor.py),
  `target_symbol` (to pick the right symbol in target.py, not the
  decoy), `operation_hint` (to apply replace-return-value), and
  `support_relation` (to apply the support offset). Missing any cue
  causes a deterministic wrong action.
- **Paired arm design**: same budget/tool constraints; only the context
  pack differs. **control_sparse** pack has `target_symbol` +
  `operation_hint` but NO `target_file` and NO `support_relation`
  (cross-file ambiguity + missing offset). **treatment_multi_cue** pack
  has all four cues (full multi-cue). The treatment pack causally
  alters the deterministic mock agent's behavior.
- **Deterministic mock agent**: multi-cue-dependent. Without
  `target_file` cue, performs a deterministic lexicographic symbol
  search; `distractor.py` sorts before `target.py`, so the agent picks
  the distractor (wrong file). Without `support_relation`, applies
  `correct_value` without offset (wrong value, tests fail). With all
  four cues, edits the correct file/symbol with the correct value
  (tests pass). After the edit/no-op, runs the real subprocess test
  command.
- **Artifact identity**:
  `schema_version=b16b_less_separable_mock_paired_run.v1`,
  `claim_level=deterministic_mock_downstream_paired_stress_only`,
  `status=mock_downstream_paired_stress_pass` (on success),
  `mode=public_aggregate_synthetic_stress_tasks`, `phase=B16-B`.
- **Safe true flags** (exactly these, all true):
  `downstream_agent_runs_performed`, `deterministic_mock_agent`,
  `paired_run_executed`, `real_file_edits_performed`,
  `subprocess_tests_executed`, `less_separable_stress_tasks`,
  `aggregate_only_public_artifact`, `diagnostic_only`.
- **No-claim / no-runtime-change flags** (all false):
  `live_llm_agent`, `provider_calls_made`,
  `remote_provider_calls_made`, `downstream_agent_value_proven`,
  `live_agent_generalization_claimed`, `promotion_ready`,
  `default_should_change`, `runtime_behavior_changed`,
  `retriever_changed`, `pack_builder_changed`, `backend_changed`,
  `default_policy_changed`, `evidencecore_semantics_changed`,
  `external_benchmark_performance_claimed`.
- **No recommendation fields**: B16-B emits NO `winner`, `best_arm`,
  `recommended_default`, `preferred_policy`, or `promotion` field
  anywhere.
- **Strict public scanner** (fail-closed). Rejects forbidden dict keys
  and value patterns: ANY URL, 32+ char hex digests, secret-like
  strings, path-like strings with file extensions, `/tmp/` workspace
  path values, `task_N` task-identifier values, patch/diff markers,
  stack traces, multiline strings, raw JSON fragments, raw line
  ranges, model-name-like strings, provider-env-like strings, and the
  self-test sentinel.
- **Generation refuses success if self-test fails or the scanner finds
  leakage** (fail-closed).
- **Per-run event logs/patches/test output stay under `/tmp` only** and
  are NEVER committed or uploaded.
- **Public schema is records-shaped**: `arm_results` contains fixed arm
  records and `paired_deltas` contains one metric per fixed-shape record;
  top-level dynamic-arm dict mirrors (`arm_metrics`, top-level
  `outcome_category_counts`) and the legacy
  `deltas_treatment_minus_control` field are intentionally absent.

### Validation results

```text
python3 -m py_compile eval/b16b_less_separable_mock_paired_run.py    => PASS
python3 eval/b16b_less_separable_mock_paired_run.py --self-test      => PASS (147/147 checks)
python3 eval/b16b_less_separable_mock_paired_run.py \
  --out artifacts/b16b_less_separable_mock_paired_run/\
b16b_less_separable_mock_paired_run_report.json                     => PASS
  (status: mock_downstream_paired_stress_pass,
    forbidden_scan: pass, self_test_passed: true,
    mode: public_aggregate_synthetic_stress_tasks, phase: B16-B,
    synthetic_task_count: 24, total_runs: 48,
    control_sparse: solve_rate=0.0, tests_pass_rate=0.0,
      correct_file_before_first_edit_rate=0.0, wrong_file_edits_mean=1.0,
    treatment_multi_cue: solve_rate=1.0, tests_pass_rate=1.0,
      correct_file_before_first_edit_rate=1.0, wrong_file_edits_mean=0.0,
    paired_deltas records: solve_rate=+1.0, wrong_file_edits_mean=-1.0,
    live_llm_agent: false, provider_calls_made: false,
    remote_provider_calls_made: false,
    downstream_agent_value_proven: false,
    promotion_ready: false, default_should_change: false,
    retriever_changed: false, pack_builder_changed: false,
    backend_changed: false, default_policy_changed: false,
    evidencecore_semantics_changed: false, runtime_behavior_changed: false,
    external_benchmark_performance_claimed: false,
    live_agent_generalization_claimed: false)
python3 scripts/validate_docs_i18n.py                           => PASS
git diff --check                                               => PASS
```

The B16-B stress extends B16-A from deliberately separable micro bugs
to a harder less-separable multi-cue task family. It executes a real
edit/test loop on synthetic public less-separable stress tasks with a
deterministic mock agent (no live LLM, no provider calls, no remote
calls). The treatment multi-cue pack causally alters the mock agent's
behavior (treatment solve_rate=1.0 vs control solve_rate=0.0),
demonstrating a pack-effect stress. Treatment is perfect by
construction; docs describe this as a harness/stress result, NOT a
live agent result. See
[B16-B detailed report](b16b-less-separable-mock-paired-run.md).

### Caveats

- B16-B is the public aggregate-only less-separable mock downstream
  paired stress artifact. It is eval/diagnostic only. It does NOT
  change runtime, retriever, pack, backend, or default policy; it
  does NOT change EvidenceCore semantics.
- B16-B uses a **deterministic mock agent** (no live LLM, no provider
  calls, no remote calls). The mock agent's behavior is multi-cue
  pack-dependent by design. Treatment is perfect by construction; docs
  describe this as a harness/stress result, NOT a live agent result.
- B16-B generates **deterministic synthetic public less-separable
  stress tasks** in code. These are NOT real user tasks and are NOT
  external benchmark tasks.
- B16-B performs **real file edits** and **real subprocess tests**
  (stdlib Python) in fresh `/tmp` workspaces per task+arm.
- B16-B does NOT prove downstream agent value.
  `downstream_agent_value_proven=false`.
- B16-B does NOT claim live agent generalization.
  `live_agent_generalization_claimed=false`.
- B16-B emits NO `winner`, `best_arm`, `recommended_default`,
  `preferred_policy`, or `promotion` recommendation field.
- All no-claim / no-runtime-change flags remain false; diagnostic
  flags remain true; the deterministic-mock-stress-run flags are the
  only additional true flags. No runtime/retriever/pack/model/
  backend/default-policy files were modified; no promotion/default/
  runtime claims change.

---

## 2026-06-21 — C5-A ContextBench Verified 检索性能 Smoke

### 目标

产出第一个外部-benchmark-形态的检索性能 smoke，基于 ContextBench verified
subset，将 C4 ContextBench 就绪/row-mapping smoke 转化为真实的检索性能
smoke。从 HuggingFace datasets-server 读取有界的 ContextBench verified
subset，在临时 `/tmp` 工作区中检出引用仓库到 `base_commit`，运行 OpenLocus
检索（初始 `bm25`，无 provider/model 调用），通过现有 `eval/score.py`
逻辑对 ContextBench `gold_context` spans 打分，并仅提交 aggregate 公共
报告。

### 假设

有界 ContextBench verified subset 可在临时 `/tmp` 工作区下通过真实
OpenLocus 检索 + 打分管线运行，产出 aggregate 检索 metrics（file recall、
MRR、span/line metrics、zero-overlap、structural/citation validity），
而无需持久化任何行级数据、repo URL/commit、gold paths/spans、生成的
JSONL、evidence 行、克隆仓库或 stdout/stderr。提交的 artifact 是
aggregate-only，且当检索 + 打分成功时 smoke 为 `pass`；当网络/HF/GitHub
失败时为真实的 `unavailable_with_reason`（无 stale/fake pass）。

### 阶段门

- C5-A 通过当 self-test 通过（113 个检查）、真实网络 smoke 完成（行已
  抓取、仓库已克隆、检索已执行、score.py metrics 已计算）、forbidden
  scan 干净，且提交的 artifact 仅记录 aggregate 计数/比率/均值，所有
  无声明标志为 false。
- C5-A 为 `unavailable_with_reason` 当网络/HF/GitHub/clone/检索/打分
  失败；artifact 记录真实的失败类别，无行级值。

### 实现说明

- **C5-A artifact**（`eval/c5_contextbench_verified_performance_smoke.py`）：
  公共 aggregate-only smoke。从 HF datasets-server `/rows` 端点抓取有界
  ContextBench verified 行（分页；仅 stdlib `urllib`；有界超时）；在内存
  中按 `language_filter`（仅为类别桶）过滤；对每一行，将 `gold_context`
  JSON 解析为临时 `gold_paths`/`gold_lines`（`content` 字段**绝不**读取或
  持久化）；将 `problem_statement` sanitizer 为检索 query（仅内存中；
  first paragraph / first sentence / raw；剥离 HTML 注释、HTML 标签、
  markdown header、code fence；限制长度）；在每行 `TemporaryDirectory`
  下通过 `git clone --filter=blob:none --no-checkout` 然后 `git checkout`
  克隆 `repo_url` 到 `base_commit`（有界超时）；在 `TemporaryDirectory`
  下生成临时 task/label JSONL；通过 `eval/run_retrieval.py`
  （`--method bm25 --cwd <repo_root>`）运行 OpenLocus 检索；运行
  `eval/score.py` 并解析 aggregate metrics；在成功行上聚合 metrics（每个
  allowlisted 数值 metric 的均值）；仅写入 aggregate 计数/比率/均值到
  提交的 artifact。
- **OpenLocus 二进制解析**：将 `--openlocus`（或默认
  `target/release/openlocus`，然后 `target/debug/openlocus` 回退）解析为
  **绝对**路径，因为 `run_retrieval.py` 使用 `--cwd <repo_root>` 运行，
  相对二进制路径无法解析。
- **Artifact 身份**：`schema_version=c5_contextbench_verified_performance_smoke.v1`、
  `claim_level=external_benchmark_retrieval_performance_smoke_only`、
  `status=pass|partial|unavailable_with_reason|fail_schema_contract|fail_forbidden_scan`、
  `mode=contextbench_verified_retrieval_performance_smoke`、`phase=C5-A`。
- **Safe true 标志**（仅当实际为真时为 true）：
  `external_benchmark_rows_read`、`repositories_materialized_transiently`、
  `openlocus_retrieval_executed`、`score_py_metrics_computed`、
  `performance_smoke`、`aggregate_only_public_artifact`、`diagnostic_only`。
- **无声明 / 无运行时变更标志**（全为 false）：
  `external_benchmark_performance_claimed`、`downstream_agent_value_proven`、
  `promotion_ready`、`default_should_change`、`runtime_behavior_changed`、
  `retriever_changed`、`pack_builder_changed`、`backend_changed`、
  `default_policy_changed`、`evidencecore_semantics_changed`、
  `provider_calls_made`、`remote_provider_calls_made`。
- **License 字段**（固定）：
  `dataset_license_status=unknown_dataset_license`、
  `row_level_redistribution_allowed=false`、
  `derived_row_level_publication_allowed=false`、
  `aggregate_metrics_publication=aggregate_only_smoke`。
- **严格公共 scanner**（fail-closed）。以 B16-A 为模型：无带字段名 token
  的合约容器；无过宽容器豁免。拒绝 forbidden dict key（`path`、`span`、
  `file`、`repo`、`repo_url`、`base_commit`、`instance_id`、
  `problem_statement`、`gold_context`、`gold_paths`、`gold_lines`、
  `query`、`content_sha`、`snippet`、`patch`、`diff`、`stdout`、`stderr`、
  `event_log`、`stack_trace`、`api_key`、`base_url`、`provider_key`、
  `secret`、`token`、`credential`、`rows`、`per_run`、`predictions`、
  `candidates`、`evidence` 等）出现在任意位置，并拒绝值模式：任意 URL（无
  URL allowlist —— repo URL **绝不**泄露）、32+ 字符 hex digest、40 字符
  commit SHA、形如 `astropy/astropy` 的 repo slug、secret-like 字符串、
  带文件扩展名的 path-like 字符串、`/tmp/` 工作区路径值、`task_N`
  任务标识符值、patch/diff 标记（`---`、`+++`、`@@`）、stack trace、
  多行字符串、原始 JSON 片段、原始行范围 `12-34`，以及 self-test sentinel。
  `failure_category_counts` 与 `metrics` 容器是 schema-key 容器，其
  CHILD KEY 是固定类别标签或 allowlisted metric 名称（**非**行级值）；
  forbidden_key 检查对这些子键放宽，但其下的值仍会被扫描。
- **生成在 self-test 失败或 scanner 发现泄露时拒绝成功**
  （fail-closed `_enforce_no_forbidden` +
  `_refuse_on_self_test_failure`，在写入 JSON 前立即执行）。
- **临时 /tmp clone + 检索 + 打分**：每行 `TemporaryDirectory` 用于克隆
  仓库；`TemporaryDirectory` 用于生成的 task/label/run JSONL。所有原始
  ContextBench 行、queries、repo URL/名称、base commit、gold paths/spans/
  contents、生成的 JSONL、evidence 行、克隆仓库与 stdout/stderr 仅保留在
  `/tmp` 下，**绝不**提交或上传。提交的 artifact 仅包含 aggregate
  计数/比率/均值。
- **不可用模式**：如果网络 smoke 无法完成（网络/HF/GitHub 失败、克隆
  超时、检索失败、打分失败），artifact 记录真实的
  `unavailable_with_reason`，带有真实的 `failure_reason_category` 与
  对应的 `failure_category_counts` 计数。绝不写入 stale/fake pass。在
  不可用模式下，`metrics={}`、`performance_smoke=false`、
  `openlocus_retrieval_executed=false`、`score_py_metrics_computed=false`、
  `repositories_materialized_transiently=false`；
  `external_benchmark_rows_read=true` 仅当失败前实际抓取了行。

### CI workflow

- `.github/workflows/c5-contextbench-verified-performance-smoke.yml`：
  手动 opt-in `workflow_dispatch`，带有布尔
  `enable_external_benchmark_network` 默认 false，以及 `row_limit`、
  `method`、`query_mode` 输入。未启用时，no-op 并显示明确消息。无
  `secrets.`、无 `vars.`、无 `OPENLOCUS` provider env。构建 OpenLocus
  CLI（release），运行 self-test，仅在启用时运行网络 smoke，校验标志
  （必须为 true：`aggregate_only_public_artifact`、`diagnostic_only`；
  必须为 false：所有无声明 / 无运行时变更标志），校验 docs i18n，检查
  工作树，仅上传 aggregate 报告（7 天保留）。

### 验证结果

```text
python3 -m py_compile eval/c5_contextbench_verified_performance_smoke.py  => PASS
python3 eval/c5_contextbench_verified_performance_smoke.py --self-test  => PASS (113/113 checks)
python3 eval/c5_contextbench_verified_performance_smoke.py \
  --row-limit 5 --method bm25 --query-mode first_paragraph \
  --language-filter python \
  --out artifacts/c5_contextbench_verified_performance_smoke/\
c5_contextbench_verified_performance_smoke_report.json  => PASS
  (status: pass, forbidden_scan: pass, self_test_passed: true,
   mode: contextbench_verified_retrieval_performance_smoke, phase: C5-A,
   method: bm25, query_mode: first_paragraph, language_filter: python,
   rows_fetched: 5, rows_evaluated: 5, rows_successful: 5, rows_failed: 0,
   network_calls: 1, provider_calls: 0,
   external_benchmark_rows_read: true,
   repositories_materialized_transiently: true,
   openlocus_retrieval_executed: true,
   score_py_metrics_computed: true,
   performance_smoke: true,
   aggregate_only_public_artifact: true,
   diagnostic_only: true,
   external_benchmark_performance_claimed: false,
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

C5-A smoke 是 OpenLocus 研究轨中第一个外部-benchmark-形态的检索性能
smoke。它执行从 HF datasets-server 的真实网络抓取、在临时 `/tmp` 目录下
对引用仓库到其 `base_commit` 的真实 `git clone` + `git checkout`、对
每个仓库的真实 OpenLocus `bm25` 检索，以及真实的 `eval/score.py` 打分，
产出有界 ContextBench verified subset 上的 aggregate 检索 metrics。它
明确**不是**严格的 benchmark 结果、**不是**leaderboard 条目、**不是**
性能声称、**不是**promotion、**不是**默认/策略变更、**不是**
runtime/retriever/pack/backend/EvidenceCore 语义变更，也**不是**下游
agent 价值声称。完整的 C5 外部-benchmark-评估阶段仍然是一个有界的规划/
可行性阶段，需要严格的 benchmark 设计、更大的样本量、多种方法与统计
分析。见 [C5-A 详细报告](c5-contextbench-verified-performance-smoke.md)。

### 注意事项

- C5-A 是公共 aggregate-only 外部 benchmark 检索性能 smoke artifact。
  它是 eval/diagnostic only。它**不**改变 runtime、retriever、pack、
  backend 或默认策略；它**不**改变 EvidenceCore 语义。它**不是**
  benchmark 结果、**不是**leaderboard 条目、**不是**性能声称、**不是**
  promotion、**不是**默认变更、**不是**runtime-clean 通用算法声称、
  **不是**OOD 时间泛化声称、**不是**QuIVer systems 声称，也**不是**下游
  agent 价值声称。
- C5-A **不**运行 provider 调用，**不**运行远程 provider 调用。唯一的
  网络调用是对公共 HF datasets-server（抓取有界 ContextBench verified
  行）与对公共 GitHub（在临时 `/tmp` 目录下克隆引用仓库到其
  `base_commit`）。`provider_calls=0`、`provider_calls_made=false`、
  `remote_provider_calls_made=false`。
- C5-A 使用**有界 ContextBench verified subset**（默认 5 行；硬上限 20
  行）。这是 smoke，**不是**严格的 benchmark 评估。Aggregate metrics
  是小样本上的点估计，**不应**被解读为 benchmark 结果、leaderboard 条目
  或性能声称。
- C5-A 在临时 `/tmp` 目录下检出引用仓库到其 `base_commit`。克隆的仓库、
  生成的 task/label/run JSONL、evidence 行与 stdout/stderr 仅保留在
  `/tmp` 下，**绝不**提交或上传。提交的 artifact 仅包含 aggregate
  计数/比率/均值。
- C5-A **不**声称外部 benchmark 性能。Aggregate metrics 是 smoke 级别
  的诊断，**不是**benchmark 结果。
  `external_benchmark_performance_claimed=false`。
- C5-A **不**证明下游 agent 价值。检索 smoke 不演练任何下游 agent。
  `downstream_agent_value_proven=false`。
- ContextBench 数据集 license 未知
  （`unknown_dataset_license`）；行级再分发被禁用
  （`row_level_redistribution_allowed=false`），派生行级发布被禁用
  （`derived_row_level_publication_allowed=false`）。Aggregate metrics
  发布允许作为 aggregate-only smoke
  （`aggregate_metrics_publication=aggregate_only_smoke`）。
- 所有无声明 / 无运行时变更标志保持 false；诊断标志
  （`aggregate_only_public_artifact`、`diagnostic_only`）保持 true。
  未修改任何 runtime/retriever/pack/model/backend/default-policy 文件；
  无 promotion/default/runtime 声明变更。

## 2026-06-21 — F1 反事实证据效用 Smoke

### 目标

产出首个反事实证据效用 smoke，检验深层研究设想：E/S 应当被度量为一
个 coding-agent 轨迹的**边际因果效用**，而不仅是主观相关性。F1 在
**六个反事实 context variant** 下对合成公开 micro bug 任务运行确
定性/mock agent，按 variant 度量 B16 风格下游指标，并从聚合 variant
指标计算**五个边际效用 delta**。这是实证且因果形态的，但仍是确
定性/mock smoke，不是 live-agent 价值，也不是真实 E/S 校准。

### 假设

确定性 mock agent 在合成公开 micro bug 任务上，可在临时 `/tmp` 工作
区下跨反事实 context variant（primary vs base；support vs base；
distractor vs base；support 加到 primary；distractor 加到 primary）
产出因果形态的边际效用 delta，同时执行真实文件编辑和真实子进程测
试，且无需持久化任何 task ID、工作区路径、文件路径、源码片段、
patch/diff、测试输出、raw event log、per-run 行、context pack 内容
或 content hash。提交的 artifact 是 aggregate-only，且当全部六个
variant 都执行、primary 解题、support-only/distractor-only/base 不
解题、distractor-only 的 wrong_file_edits > base，且全部五个边际
delta 从聚合指标计算时，smoke 为 `pass`。

### 阶段门

- F1 通过当 self-test 通过（162 个检查）、全部六个 variant 都以
  run_count > 0 运行、primary_only solve_rate = 1.0、base_no_context /
  support_only / distractor_only solve_rate = 0.0、distractor_only
  wrong_file_edits_mean > base_no_context wrong_file_edits_mean、全
  部五个边际 effect 从聚合 variant 指标计算、forbidden scan 干净，
  且提交的 artifact 仅记录 aggregate 计数/比率/均值，所有无声明标志
  为 false。

### 实现说明

- **F1 artifact**
  （`eval/f1_counterfactual_evidence_utility_smoke.py`）：公开
  aggregate-only smoke。在代码中生成确定性合成公开 micro bug 任务
  规格（默认 24 个；CLI 硬上限 100；不提交 fixture 文件）。对每个
  任务和六个 variant 之一，创建一个全新 `TemporaryDirectory` 工作区，
  含 `target.py`（buggy）、`support.py`（helper，非 target symbol）、
  `distractor.py`（错误文件）和 `test_target.py`（stdlib 测试）。
  这些路径/文件**绝不**出现在公开 artifact 中。
- **六个反事实 context variant**（固定 allowlist；pack cue 仅内存中，
  绝不发出）：
  `base_no_context`（无 cue -> no-op -> 测试失败）；
  `primary_only`（primary target/symbol/operation cue -> 正确编辑
  target -> 测试通过）；
  `support_only`（support cue -> 编辑 support.py 错误文件 -> 测试失
  败）；
  `primary_plus_support`（primary + support -> inspect support，正确
  编辑 target -> 测试通过；比 primary 更丰富的 tool/context）；
  `distractor_only`（wrong cue -> 编辑 distractor -> 测试失败；
  wrong_file_edits 增加）；
  `primary_plus_distractor`（primary + distractor -> inspect
  distractor，正确编辑 target，再在正确首次编辑之后编辑 distractor
  -> 测试通过；wrong_file_edits/tool/context 比 primary 差）。
- **Mock agent policy**（确定性，依赖 pack；per-run event log 仅内存，
  绝不提交）：
  若 primary_target cue 存在 -> 若同时存在 support/distractor 则
  先 inspect，再正确编辑 target，再（若也存在 distractor）在正确首
  次编辑之后编辑 distractor；
  若 support cue 存在（无 primary）-> 编辑 support（错误文件）；
  若 wrong cue 存在（无 primary）-> 编辑 distractor（错误文件）；
  否则 -> no-op。运行真实子进程测试，记录通过/失败。
- **边际效用 delta**（固定 effect 名称；效用专属；刻意**不**用
  `E_primary` / `S_support`）：
  `primary_context_vs_base` = `primary_only` - `base_no_context`；
  `support_context_vs_base` = `support_only` - `base_no_context`；
  `distractor_context_vs_base` = `distractor_only` - `base_no_context`；
  `support_added_to_primary` = `primary_plus_support` - `primary_only`；
  `distractor_added_to_primary` = `primary_plus_distractor` -
  `primary_only`。每个 effect 为所有 rate/mean 指标输出 delta（不含
  `run_count`）。
- **Theory mapping**：记录 `primary_context_vs_base` 对应
  `e_utility_smoke_proxy`，`support_added_to_primary` 对应
  `s_conditional_utility_smoke_proxy`，`distractor_added_to_primary`
  对应 `s_conditional_distractor_utility_smoke_proxy`，但
  `true_e_s_calibration_claimed=false`、
  `automated_e_s_full_calibration_claimed=false`、
  `human_e_s_calibration_claimed=false`。mapping 仅为命名/解释辅助；
  delta 是从合成任务上的确定性 mock 聚合指标计算的，**不是**从真实
  人工/手动 E/S 标签计算的。
- **Artifact 身份**：
  `schema_version=f1_counterfactual_evidence_utility_smoke.v1`、
  `claim_level=counterfactual_evidence_utility_smoke_only`、
  `status=counterfactual_evidence_utility_smoke_pass`、
  `mode=public_aggregate_synthetic_micro_tasks`、`phase=F1`。
- **Safe true 标志**（仅这些，全为 true）：
  `counterfactual_context_variants_executed`、`deterministic_mock_agent`、
  `real_file_edits_performed`、`subprocess_tests_executed`、
  `marginal_utility_metrics_computed`、
  `aggregate_only_public_artifact`、`diagnostic_only`。
- **无声明 / 无运行时变更标志**（全为 false）：
  `live_llm_agent`、`provider_calls_made`、
  `remote_provider_calls_made`、`downstream_agent_value_proven`、
  `live_agent_generalization_claimed`、`real_user_task_claimed`、
  `true_e_s_calibration_claimed`、
  `automated_e_s_full_calibration_claimed`、
  `human_e_s_calibration_claimed`、
  `external_benchmark_performance_claimed`、`promotion_ready`、
  `default_should_change`、`runtime_behavior_changed`、
  `retriever_changed`、`pack_builder_changed`、`backend_changed`、
  `default_policy_changed`、`evidencecore_semantics_changed`。
- **严格公共 scanner**（fail-closed）。以 B16-A 为模型：无带字段名 token
  的合约容器；无过宽容器豁免。拒绝 forbidden dict key（`task_id`、
  `workspace_path`、`file`、`target_file`、`wrong_cue_file`、
  `support_file`、`target_module`、`support_module`、
  `distractor_module`、`test_module`、`path`、`span`、`content_sha`、
  `snippet`、`code`、`patch`、`diff`、`test_output`、`stdout`、
  `stderr`、`event_log`、`stack_trace`、`api_key`、`base_url`、
  `provider_key`、`secret`、`token`、`credential`、`rows`、`per_run`、
  `predictions`、`candidates`、`content`、`source`、`text`、`body`
  等）出现在任意位置，并拒绝值模式：任意 URL（无 URL allowlist）、
  32+ 字符 hex digest、secret-like 字符串、带文件扩展名的 path-like
  字符串（拒绝 `target.py`、`support.py`、`distractor.py`、
  `test_target.py` 作为值）、`/tmp/` 工作区路径值、`task_N` 任务标识
  值、patch/diff 标记（`---`、`+++`、`@@`）、堆栈跟踪、多行字符串、
  raw JSON 片段、raw 行范围 `12-34`，以及 self-test sentinel。
- **生成在 self-test 失败或 scanner 发现泄露时拒绝成功**
  （fail-closed `_enforce_no_forbidden` +
  `_refuse_on_self_test_failure`，在写入 JSON 前立即执行）。

### CI workflow

- `.github/workflows/empirical-research.yml`：在
  `b16a-minimal-mock-agent-paired-run` 之后新增一个
  `f1-counterfactual-evidence-utility-smoke` job。无 `secrets.`、无
  `vars.`、无 `OPENLOCUS` provider env、无网络。运行 `python3 -m
  py_compile`、`--self-test`、默认 run（写入 `$RUNNER_TEMP`），校验
  flag 不变量（必须为 true：`counterfactual_context_variants_executed`、
  `deterministic_mock_agent`、`real_file_edits_performed`、
  `subprocess_tests_executed`、`marginal_utility_metrics_computed`、
  `aggregate_only_public_artifact`、`diagnostic_only`；必须为 false：
  全部 18 个无声明 / 无运行时变更标志），校验 docs i18n，检查工作
  树，仅上传 aggregate temp report（7 天保留）。

### 验证结果

```text
python3 -m py_compile eval/f1_counterfactual_evidence_utility_smoke.py  => PASS
python3 eval/f1_counterfactual_evidence_utility_smoke.py --self-test  => PASS (162/162 checks)
python3 eval/f1_counterfactual_evidence_utility_smoke.py \
  --out artifacts/f1_counterfactual_evidence_utility/\
f1_counterfactual_evidence_utility_report.json  => PASS
  (status: counterfactual_evidence_utility_smoke_pass,
   forbidden_scan: pass, self_test_passed: true,
   mode: public_aggregate_synthetic_micro_tasks, phase: F1,
   variant_count: 6, effect_count: 5,
   synthetic_task_count: 24, total_runs: 144,
   base_no_context: solve_rate=0.0, tests_pass_rate=0.0,
     wrong_file_edits_mean=0.0, tool_calls_before_first_edit_mean=0.0,
     context_tokens_mean=8.0,
   primary_only: solve_rate=1.0, tests_pass_rate=1.0,
     wrong_file_edits_mean=0.0, tool_calls_before_first_edit_mean=1.0,
     context_tokens_mean=24.0,
   support_only: solve_rate=0.0, tests_pass_rate=0.0,
     wrong_file_edits_mean=1.0, tool_calls_before_first_edit_mean=1.0,
     context_tokens_mean=20.0,
   primary_plus_support: solve_rate=1.0, tests_pass_rate=1.0,
     wrong_file_edits_mean=0.0, tool_calls_before_first_edit_mean=2.0,
     context_tokens_mean=40.0,
   distractor_only: solve_rate=0.0, tests_pass_rate=0.0,
     wrong_file_edits_mean=1.0, tool_calls_before_first_edit_mean=1.0,
     context_tokens_mean=16.0,
   primary_plus_distractor: solve_rate=1.0, tests_pass_rate=1.0,
     wrong_file_edits_mean=1.0, tool_calls_before_first_edit_mean=2.0,
     context_tokens_mean=32.0,
   marginal_effects:
     primary_context_vs_base: solve_rate_delta=+1.0,
       wrong_file_edits_mean_delta=+0.0,
       tool_calls_before_first_edit_mean_delta=+1.0,
       context_tokens_mean_delta=+16.0,
     support_context_vs_base: solve_rate_delta=+0.0,
       wrong_file_edits_mean_delta=+1.0,
       tool_calls_before_first_edit_mean_delta=+1.0,
       context_tokens_mean_delta=+12.0,
     distractor_context_vs_base: solve_rate_delta=+0.0,
       wrong_file_edits_mean_delta=+1.0,
       tool_calls_before_first_edit_mean_delta=+1.0,
       context_tokens_mean_delta=+8.0,
     support_added_to_primary: solve_rate_delta=+0.0,
       wrong_file_edits_mean_delta=+0.0,
       tool_calls_before_first_edit_mean_delta=+1.0,
       context_tokens_mean_delta=+16.0,
     distractor_added_to_primary: solve_rate_delta=+0.0,
       wrong_file_edits_mean_delta=+1.0,
       tool_calls_before_first_edit_mean_delta=+1.0,
       context_tokens_mean_delta=+8.0,
   live_llm_agent: false, provider_calls_made: false,
   remote_provider_calls_made: false,
   downstream_agent_value_proven: false,
   true_e_s_calibration_claimed: false,
   automated_e_s_full_calibration_claimed: false,
   human_e_s_calibration_claimed: false,
   promotion_ready: false, default_should_change: false,
   runtime_behavior_changed: false, retriever_changed: false,
   pack_builder_changed: false, backend_changed: false,
   default_policy_changed: false, evidencecore_semantics_changed: false,
   external_benchmark_performance_claimed: false,
   live_agent_generalization_claimed: false,
   real_user_task_claimed: false)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

F1 smoke 是 OpenLocus 研究轨中首个反事实证据效用 smoke。它在六个反
事实 context variant 下真实执行 edit/test 循环，按 variant 计算聚合
行为指标，并从这些聚合指标计算五个边际效用 delta。它明确**不是**
benchmark 结果、**不是** live 下游 agent 价值声称、**不是**真实 E/S
校准声称、**不是**promotion、**不是**默认/策略变更、**不是**
runtime/retriever/pack/backend/EvidenceCore 语义变更，也**不是**真实
用户任务声称。详见 [F1 详细报告](f1-counterfactual-evidence-utility.md)。

### 注意事项

- F1 是公开 aggregate-only 反事实证据效用 smoke artifact。它是
  eval/diagnostic only。它**不**改变 runtime、retriever、pack、
  backend 或默认策略；它**不**改变 EvidenceCore 语义。它**不是**
  benchmark 结果、**不是** live 下游 agent 价值声称、**不是**真实
  E/S 校准声称、**不是**runtime-clean 通用算法声称、**不是**OOD 时
  间性声称、**不是**QuIVer systems 声称，也**不是**下游 agent 价值
  声称。
- F1 使用**确定性 mock agent**（无 live LLM、无 provider 调用、无远
  程调用）。mock agent 的行为按设计依赖 pack。这是因果 pack 效果
  smoke，**不是** live agent 价值声称。
- F1 在代码中生成**确定性合成公开 micro bug 任务**。这些**不是**真
  实用户任务，也**不是**外部 benchmark 任务。因为是合成公开任务，确
  切的任务/run 计数可接受。
- F1 在每个 task+variant 的全新 `/tmp` 工作区中执行**真实文件编辑**
  和**真实子进程测试**（stdlib Python）。per-run event log、patch 和
  测试输出仅留在 `/tmp`，**绝不**提交或上传。提交的 artifact 仅含
  聚合计数/比率/均值和聚合边际 effect delta。
- F1 **不**证明下游 agent 价值。边际 effect delta 是设计 pack cue
  的确定性 mock 产物，**不是**任何 context variant 改善 live 下游
  agent 的证据。`downstream_agent_value_proven=false`。
- F1 **不**声明 live agent 泛化。确定性 mock agent 按构造平凡地泛化
  到合成任务族；这**不是** live agent 泛化声称。
  `live_agent_generalization_claimed=false`。
- F1 **不是**真实 E/S 校准。theory mapping 标签仅为命名/解释辅助；
  delta 是从合成任务上的确定性 mock 聚合指标计算的，**不是**从真实
  人工/手动 E/S 标签计算的。
  `true_e_s_calibration_claimed=false`、
  `automated_e_s_full_calibration_claimed=false`、
  `human_e_s_calibration_claimed=false`。
- 所有无声明 / 无运行时变更标志保持 false；诊断标志
  （`aggregate_only_public_artifact`、`diagnostic_only`）保持 true。
  未修改任何 runtime/retriever/pack/model/backend/default-policy 文
  件；无 promotion/default/runtime 声明变更。

## 2026-06-21 — C5-B ContextBench Verified 检索方法矩阵 Smoke

### 目标

产出 C5-A 外部-benchmark-形态检索性能 smoke 的有界多方法矩阵扩展。从
HuggingFace datasets-server `/rows` 读取有界 ContextBench verified subset
**一次**（跨所有方法共享），在临时 `/tmp` 工作区中检出引用仓库到
`base_commit`，跨请求的方法矩阵（默认 `bm25,regex,symbol`；允许
`bm25,regex,text,symbol`；固定 `baseline_method=bm25`；无 provider/model
调用）运行 OpenLocus 检索，通过现有 `eval/score.py` 逻辑对每种方法针对
ContextBench `gold_context` spans 打分，并仅提交一个 aggregate 公共报告，
其中包含每方法记录和仅 aggregate 的、与固定 `bm25` baseline 的 delta。C5-B
**不**输出 `winner`、`best_method`、`recommended_default` 或任何暗示策略/默认
决策的字段。

### 假设

有界 ContextBench verified subset 可在临时 `/tmp` 工作区下通过真实 OpenLocus
检索 + 打分管线跨有界方法矩阵运行，产出每方法 aggregate 检索 metrics
（file recall@10、MRR、span F0.5@10、success_rate）和仅 aggregate 的、与固定
`bm25` baseline 的 delta，而无需持久化任何行级数据、repo URL/commit、gold
paths/spans、生成的 JSONL、evidence 行、克隆仓库、每行 metrics、行级 hash、
stdout/stderr，或任何 winner/recommendation 字段。提交的 artifact 是
aggregate-only，且当所有请求方法都完成检索+打分且每方法至少一个成功行、
scanner 通过、artifact 形态为记录列表（**非**以方法名为 key 的 dict）时，smoke
为 `pass`；当至少一个方法成功且至少一个失败时为 `partial`；当无方法完成
检索+打分时为真实的 `unavailable_with_reason`（无 stale/fake pass）。

### 阶段门

- C5-B 通过当 self-test 通过（154 个检查）、真实网络矩阵 smoke 完成（行抓取
  **一次**跨方法共享、仓库每方法克隆、每方法检索执行、每方法 score.py
  metrics 计算）、C5-B forbidden scan 干净、artifact 形态为记录列表（**非**
  以方法名为 key 的 dict），且提交的 artifact 仅记录 aggregate 计数/比率/均值
  与仅 aggregate 的 delta，所有无声明标志为 false，且无 recommendation 字段。
- C5-B 为 `partial` 当至少一个方法成功且至少一个方法失败/不可用。
- C5-B 为 `unavailable_with_reason` 当所有方法的网络/HF/GitHub/clone/检索/
  打分失败；artifact 记录真实的失败类别，无行级值。
- C5-B 为 `fail_schema_contract` 当方法配置无效、意外 metric key 或不安全
  artifact 结构（如 `method_results` 为以方法名为 key 的 dict）。
- C5-B 为 `fail_forbidden_scan` 当 scanner 失败。

### 实现说明

- **C5-B artifact**
  （`eval/c5b_contextbench_verified_method_matrix_smoke.py`）：公共
  aggregate-only 方法矩阵 smoke。复用 C5-A helper
  （`import c5_contextbench_verified_performance_smoke as c5a`）：
  行抓取（`c5a._fetch_contextbench_rows`）、query sanitizer
  （`c5a._sanitize_query`）、gold context 解析（`c5a._parse_gold_context`）、
  克隆 + 检出（`c5a._clone_and_checkout`）、临时 JSONL 写入
  （`c5a._write_transient_jsonl`）、检索 + 打分 runner
  （`c5a._run_retrieval_and_score`）、OpenLocus 二进制解析
  （`c5a._resolve_openlocus_binary`）、失败类别
  （`c5a.FAILURE_CATEGORIES`）、score metric allowlist
  （`c5a.SCORE_METRIC_ALLOWLIST` —— C5-B 的 `METHOD_METRIC_ALLOWLIST` 是
  严格子集）、scanner 原语（`c5a._scan_forbidden`、
  `c5a._refuse_on_self_test_failure`、`c5a._now_iso`、`c5a._write_json`、
  `c5a._check`）、query 模式 / 语言过滤器（`c5a.ALLOWED_QUERY_MODES`
  等）与 license 字段（`c5a.LICENSE_FIELDS`）。C5-B 拥有自己的 schema、claim
  字段、方法矩阵聚合、方法 allowlist 校验与矩阵 self-test。
- **方法 parser**（`parse_methods`）：空/None -> 默认
  `["bm25", "regex", "symbol"]`；每个 token 必须在 `ALLOWED_METHODS`
  （`bm25,regex,text,symbol`）中；重复方法被确定性去重（保留首次出现顺序）；
  空 token 被跳过；无效配置时，产出 `fail_schema_contract` 报告。
- **跨方法共享行抓取**：从 HF datasets-server `/rows` 端点抓取有界
  ContextBench verified 行**一次**（分页；仅 stdlib `urllib`；有界超时）；在
  内存中按 `language_filter`（仅为类别桶）过滤。同一行列表对每种方法复用
  （无重复网络抓取）。
- **每方法检索 + 打分**：对请求矩阵中的每种方法，遍历共享行；每行，将
  `gold_context` JSON 解析为临时 `gold_paths`/`gold_lines`（`content` 字段
  **绝不**读取或持久化）；将 `problem_statement` sanitizer 为检索 query
  （仅内存中）；在每行 `TemporaryDirectory` 下克隆 `repo_url` 到
  `base_commit`；在 `TemporaryDirectory` 下生成临时 task/label JSONL；通过
  `eval/run_retrieval.py`（`--method <method> --cwd <repo_root>`）运行
  OpenLocus 检索；运行 `eval/score.py` 并解析 aggregate metrics；在该方法的
  成功行上聚合 metrics（每个 allowlisted 数值 metric 的均值；`success_rate`
  由 `rows_successful / rows_evaluated` 重新计算）。
- **方法结果记录**（`method_results`）：记录列表（**非**以方法名为 key 的
  dict）——
  `{"method": <m>, "status": <s>, "rows_evaluated": <n>,
  "rows_successful": <n>, "rows_failed": <n>, "metrics": {...},
  "failure_category_counts": {...}}`。每个 `method` 值必须在
  `ALLOWED_METHODS` 中。
- **与 baseline 的 delta**（`smoke_metric_deltas_vs_baseline`）：记录列表
  （仅固定 `baseline_method=bm25` 以外的方法），每条记录对应一个 metric。
  每条记录含 `baseline_method`、`method`、`metric` 与数值 `delta`
  （`method_metric - baseline_metric`）。仅输出 `DELTA_METRIC_ALLOWLIST`
  metric（`file_recall@10`、`mrr`、`span_f0.5@10`、`success_rate`）。如果
  baseline 方法缺失或没有 metrics，则不输出 delta（空列表，**非** fake zero）。
- **无 recommendation 字段**：C5-B **不**在任何位置输出 `winner`、
  `best_method`、`recommended_default`、`recommended_method`、
  `preferred_method`、`default_method`、`policy_decision`、`decision`、
  `ranking` 或 `rank`。`baseline_method` 固定为 `bm25`、
  `baseline_is_policy_candidate=false`、`default_should_change=false`。
- **OpenLocus 二进制解析**：将 `--openlocus`（或默认
  `target/release/openlocus`，然后 `target/debug/openlocus` 回退）解析为
  **绝对**路径，因为 `run_retrieval.py` 使用 `--cwd <repo_root>` 运行，
  相对二进制路径无法解析。
- **Artifact 身份**：`schema_version=c5b_contextbench_verified_method_matrix_smoke.v1`、
  `claim_level=external_benchmark_retrieval_method_matrix_smoke_only`、
  `status=pass|partial|unavailable_with_reason|fail_schema_contract|fail_forbidden_scan`、
  `mode=contextbench_verified_retrieval_method_matrix_smoke`、阶段 `C5-B`。
- **Safe true 标志**（仅当实际为真时为 true）：
  `external_benchmark_rows_read`、`repositories_materialized_transiently`、
  `openlocus_retrieval_executed`、`score_py_metrics_computed`、
  `method_matrix_smoke`、`aggregate_only_public_artifact`、`diagnostic_only`。
- **无声明 / 无运行时变更标志**（全为 false）：
  `external_benchmark_performance_claimed`、`leaderboard_entry_claimed`、
  `downstream_agent_value_proven`、`promotion_ready`、
  `default_should_change`、`baseline_is_policy_candidate`、
  `runtime_behavior_changed`、`retriever_changed`、`pack_builder_changed`、
  `backend_changed`、`default_policy_changed`、
  `evidencecore_semantics_changed`、`provider_calls_made`、
  `remote_provider_calls_made`。
- **License 字段**（固定）：
  `dataset_license_status=unknown_dataset_license`、
  `row_level_redistribution_allowed=false`、
  `derived_row_level_publication_allowed=false`、
  `aggregate_metrics_publication=aggregate_only_smoke`。
- **严格 C5-B 公共 scanner**（fail-closed）。复用 C5-A forbidden scanner 原语
  进行原始 key/value 泄露检测（URL、hex digest、repo slug、/tmp 路径、patch
  marker、stack trace、secret 等），并**新增** C5-B 特定检查：
  - 如果 `method_results` 是以方法名为 key 的 dict，则拒绝（C5-B 要求记录
    列表，**非** dict）；
  - 拒绝每个 `method` 值不在 `ALLOWED_METHODS` 中的方法结果记录；
  - 拒绝任何位置的 `FORBIDDEN_RECOMMENDATION_FIELDS` key（`winner`、
    `best_method`、`recommended_default`、`recommended_method`、
    `preferred_method`、`default_method`、`policy_decision`、`decision`、
    `ranking`、`rank`）；
  - 拒绝任何位置的 C5-B 特定额外 forbidden key：`row`、`rows_data`、
    `raw_row`、`raw_rows`、`repo_name`、`repo_slug`、`query_text`、`gold`、
    `gold_path`、`gold_span`、`gold_snippet`、`snippet`、`snippets`、
    `content_sha`、`stdout`、`stderr`、`stdout_text`、`stderr_text`、
    `evidence_row`、`evidence_rows`、`retrieved_path`、`retrieved_paths`、
    `retrieved_snippet`、`cloned_repo_path`、`cloned_repo`、
    `per_row_metrics`、`row_metrics`。
  - 过滤掉一个 C5-A false positive：方法名字符串 `"text"` 作为值出现在
    `methods_allowed`/`methods_requested` 下时，会被 C5-A 标记为
    `forbidden_field_name_value`（因为 `text` 是 C5-A 合约中的 forbidden
    CONTENT/KEY 名）。在 C5-B 中，`text` 也是一个合法的 OpenLocus 检索方法
    名，因此它可以作为值出现在 `methods_allowed`/`methods_requested` 下。C5-B
    scanner 过滤掉该单点 false positive（仅针对 C5-B 特定安全值路径上的
    `forbidden_field_name_value` 违规）；所有其他 C5-A 违规保留。
- **生成在 self-test 失败或 scanner 发现泄露时拒绝成功**
  （fail-closed `_enforce_c5b_no_forbidden` +
  `c5a._refuse_on_self_test_failure`，在写入 JSON 前立即执行）。
- **临时 /tmp clone + 检索 + 打分**：每方法每行 `TemporaryDirectory` 用于
  克隆仓库；`TemporaryDirectory` 用于生成的 task/label/run JSONL。所有原始
  ContextBench 行、queries、repo URL/名称、base commit、gold paths/spans/
  contents、生成的 JSONL、evidence 行、克隆仓库、每行 metrics、行级 hash 与
  stdout/stderr 仅保留在 `/tmp` 下，**绝不**提交或上传。提交的 artifact 仅
  包含 aggregate 计数/比率/均值与仅 aggregate 的 delta。
- **不可用模式**：如果所有方法的网络 smoke 无法完成（网络/HF/GitHub 失败、
  克隆超时、检索失败、打分失败），artifact 记录真实的
  `unavailable_with_reason`，带真实的 `failure_reason_category` 与对应的
  `failure_category_counts` 计数。绝不写入 stale/fake pass。在不可用模式下，
  `method_results` 是记录列表，每请求方法一条，每条
  `status=unavailable_with_reason` 且 `metrics={}` 为空；
  `smoke_metric_deltas_vs_baseline=[]`；`method_matrix_smoke=false`；
  `openlocus_retrieval_executed=false`；`score_py_metrics_computed=false`；
  `repositories_materialized_transiently=false`；
  `external_benchmark_rows_read=true` 仅当失败前实际抓取了行。
- **Schema 合约失败模式**：在无效方法配置（未知方法、空方法等）、意外 metric
  key 或不安全 artifact 结构（如 `method_results` 为 dict）时，artifact 记录
  `fail_schema_contract`，`failure_reason_category` 设为 schema 违规类型。

### CI workflow

- `.github/workflows/c5-contextbench-method-matrix-smoke.yml`：手动 opt-in
  `workflow_dispatch`，带布尔 `enable_external_benchmark_network` 默认
  false，以及 `row_limit`、`methods`、`query_mode` 输入。未启用时，no-op
  并显示明确消息。无 `secrets.`、无 `vars.`、无 `OPENLOCUS_LLM`/
  `OPENLOCUS_EMBEDDING` provider env。构建 OpenLocus CLI（release），运行
  self-test，仅在启用时运行矩阵 smoke，校验标志（必须为 true：
  `aggregate_only_public_artifact`、`diagnostic_only`；必须为 false：所有
  无声明 / 无运行时变更标志，含 `baseline_is_policy_candidate`、
  `default_should_change`、`leaderboard_entry_claimed`；license 字段固定；
  `baseline_method=bm25`；任何位置无 `winner`/`best_method`/
  `recommended_default` 字段；`method_results` 是带 allowlisted `method` 值的
  记录列表），校验 docs i18n，检查工作树，仅上传 aggregate 报告（7 天保留）。

### 验证结果

```text
python3 -m py_compile eval/c5b_contextbench_verified_method_matrix_smoke.py  => PASS
python3 eval/c5b_contextbench_verified_method_matrix_smoke.py --self-test  => PASS (161/161 checks)
cargo build --locked --release -p openlocus-cli  => PASS
python3 eval/c5b_contextbench_verified_method_matrix_smoke.py \
  --row-limit 5 --methods bm25,regex,symbol \
  --query-mode first_paragraph --language-filter python \
  --openlocus target/release/openlocus \
  --out artifacts/c5b_contextbench_verified_method_matrix/\
c5b_contextbench_verified_method_matrix_report.json  => PASS
  (status: pass, forbidden_scan: pass, self_test_passed: true,
   mode: contextbench_verified_retrieval_method_matrix_smoke, phase: C5-B,
   methods: [bm25, regex, symbol], methods_attempted: 3,
   methods_successful: 3, methods_succeeded: 3, methods_failed: 0,
   rows_fetched: 5, network_calls: 1, provider_calls: 0,
   baseline_method: bm25, baseline_is_policy_candidate: false,
   default_should_change: false,
   external_benchmark_rows_read: true,
   repositories_materialized_transiently: true,
   openlocus_retrieval_executed: true,
   score_py_metrics_computed: true,
   method_matrix_smoke: true,
   aggregate_only_public_artifact: true,
   diagnostic_only: true,
   external_benchmark_performance_claimed: false,
   leaderboard_entry_claimed: false,
   downstream_agent_value_proven: false, promotion_ready: false,
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

C5-B smoke 是 OpenLocus 研究轨中第一个外部-benchmark-形态的检索方法矩阵
smoke。它执行从 HF datasets-server 的真实网络抓取**一次**（跨方法共享）、对
引用仓库到其 `base_commit` 的每方法每行真实 `git clone` + `git checkout`（在
临时 `/tmp` 目录下）、跨请求方法矩阵（`bm25`、`regex`、`symbol`）对每个
仓库的真实 OpenLocus 检索，以及每方法真实的 `eval/score.py` 打分，产出有界
ContextBench verified subset 上每方法的 aggregate 检索 metrics，以及与固定
`bm25` baseline 的仅 aggregate delta。它明确**不是**严格的 benchmark 结果、
**不是**leaderboard 条目、**不是**性能声称、**不是**promotion、**不是**默认/
策略变更、**不是**runtime/retriever/pack/backend/EvidenceCore 语义变更、
**不是**下游 agent 价值声称，且**不**输出任何
`winner`/`best_method`/`recommended_default` 字段。完整的 C5 外部-benchmark-
评估阶段仍然是一个有界的规划/可行性阶段，需要严格的 benchmark 设计、更大的
样本量、多种方法与统计分析。见
[C5-B 详细报告](c5b-contextbench-verified-method-matrix-smoke.md)。

### 注意事项

- C5-B 是公共 aggregate-only 外部 benchmark 检索方法矩阵 smoke artifact。
  它是 eval/diagnostic only。它**不**改变 runtime、retriever、pack、
  backend 或默认策略；它**不**改变 EvidenceCore 语义。它**不是**
  benchmark 结果、**不是**leaderboard 条目、**不是**性能声称、**不是**
  promotion、**不是**默认变更、**不是**runtime-clean 通用算法声称、
  **不是**OOD 时间泛化声称、**不是**QuIVer systems 声称，也**不是**下游
  agent 价值声称。
- C5-B **不**输出 `winner`、`best_method`、`recommended_default` 或任何
  暗示策略/默认决策的字段。固定 `baseline_method` 为 `bm25`、
  `baseline_is_policy_candidate=false`、`default_should_change=false`。
- C5-B **不**运行 provider 调用，**不**运行远程 provider 调用。唯一的
  网络调用是对公共 HF datasets-server（抓取有界 ContextBench verified 行
  **一次**，跨方法共享）与对公共 GitHub（在临时 `/tmp` 目录下每方法克隆
  引用仓库到其 `base_commit`）。`provider_calls=0`、
  `provider_calls_made=false`、`remote_provider_calls_made=false`。
- C5-B 使用**有界 ContextBench verified subset**（默认 5 行；硬上限 10 行；
  每方法）。这是 smoke，**不是**严格的 benchmark 评估。Aggregate metrics
  是小样本上的点估计，**不应**被解读为 benchmark 结果、leaderboard 条目、
  性能声称或方法推荐。
- C5-B 在临时 `/tmp` 目录下检出引用仓库到其 `base_commit`。克隆的仓库、
  生成的 task/label/run JSONL、evidence 行与 stdout/stderr 仅保留在
  `/tmp` 下，**绝不**提交或上传。提交的 artifact 仅包含 aggregate
  计数/比率/均值与仅 aggregate 的 delta。
- C5-B **不**声称外部 benchmark 性能。Aggregate metrics 是 smoke 级别的
  诊断，**不是**benchmark 结果。
  `external_benchmark_performance_claimed=false`。
- C5-B **不**证明下游 agent 价值。检索矩阵 smoke 不演练任何下游 agent。
  `downstream_agent_value_proven=false`。
- ContextBench 数据集 license 未知
  （`unknown_dataset_license`）；行级再分发被禁用
  （`row_level_redistribution_allowed=false`），派生行级发布被禁用
  （`derived_row_level_publication_allowed=false`）。Aggregate metrics
  发布允许作为 aggregate-only smoke
  （`aggregate_metrics_publication=aggregate_only_smoke`）。
- 所有无声明 / 无运行时变更标志保持 false；诊断标志
  （`aggregate_only_public_artifact`、`diagnostic_only`）保持 true。
  未修改任何 runtime/retriever/pack/model/backend/default-policy 文件；
  无 promotion/default/runtime 声明变更。

---

## 2026-06-21 — B16-C Live-Provider 下游 Paired Smoke

### 目标

将 B16 从确定性/mock 下游 edit-test 实验推进到首个 **live-provider
下游 paired smoke**。在合成公开 micro bug 任务上运行微型 paired live
LLM agent，本地应用模型的结构化 edit action，执行真实测试，并仅发布
聚合行为指标。

### 假设

live LLM provider（OpenAI 兼容）能在合成公开 micro 任务上执行完整
B16 下游 agent edit/test 循环，并在 paired
control_sparse / treatment_context_pack arms 下产出行为指标
（solve_rate、tests_pass_rate、correct_file_before_first_edit_rate、
wrong_file_edits_mean、tool_calls_before_first_edit_mean、
context_tokens_mean、latency_ms_mean、cost_proxy_mean），且不声明下游
agent 价值或 live agent 泛化。

### 实现说明

- **B16-C artifact**（`eval/b16c_live_provider_paired_smoke.py`）：
  公开仅聚合 smoke。在代码中生成确定性合成公开 micro bug 任务（默认
  2；`--task-count` 范围 2-8，硬上限 8）；为每个 task+arm 创建全新
  `/tmp` 工作区，含真实微型 Python 模块 + stdlib 测试；仅当
  `--allow-remote` + `OPENLOCUS_ALLOW_REMOTE=1` + provider env 全部设
  置时运行 **live LLM agent**（OpenAI 兼容）；本地应用模型的结构化
  edit action（仅白名单 `target.py`；action 仅
  `replace_return_value` / `no_op`；无任意路径，无 shell）；运行真实
  子进程测试；计算聚合行为指标；仅写入聚合 counts/rates/means 到提交
  artifact。
- **Provider client helper**（`eval/provider_client.py`）：最小共享
  OpenAI 兼容 chat helper。返回安全的 `ProviderCallResult`，含聚合计数
  （calls attempted / succeeded / failed、invalid_json、timeout、
  latency、若 provider 返回 `usage` 的数值 usage、固定 failure-category
  枚举 token、HTTP status）。raw prompt / message / response / base
  URL / API key / provider payload **绝不**在公开诊断中返回。安全失败
  类别是固定枚举；raw 异常文本被抑制。
- **Paired arm 设计**：`control_sparse`（最小描述；无 target file
  cue；小 token 预算）vs `treatment_context_pack`（target file cue、
  symbol cue、紧凑文件摘要；较大 token 预算）。预算/工具约束相同；
  仅 context pack 不同。
- **Live LLM provider 约束**：仅当 `--allow-remote` AND
  `OPENLOCUS_ALLOW_REMOTE=1` AND（当 `--require-workflow-dispatch` 时）
  `OPENLOCUS_LLM_WORKFLOW_DISPATCH=1` AND
  `OPENLOCUS_LLM_BASE_URL` / `OPENLOCUS_LLM_API_KEY` /
  `OPENLOCUS_LLM_MODEL` 全部设置时才进行远程调用。prompt/response 绝
  不持久化。
- **Artifact 身份**：
  `schema_version=b16c_live_provider_paired_smoke.v1`、
  `claim_level=live_provider_downstream_paired_smoke_only`、
  `mode=public_aggregate_synthetic_micro_tasks`、`phase=B16-C`。状态枚
  举：`live_provider_paired_smoke_pass`、
  `unavailable_no_local_provider_env`、`blocked_remote_not_enabled`、
  `provider_call_failed`、`structured_action_parse_failed`、
  `paired_run_failed`、`fail_forbidden_scan`。
- **Safe true flags**（仅 live run 时）：
  `downstream_agent_runs_performed`、`live_llm_agent`、
  `provider_calls_made`、`remote_provider_calls_made`、
  `paired_run_executed`、`synthetic_micro_tasks_used`、
  `real_file_edits_performed`、`real_test_commands_executed`、
  `agent_behavior_metrics_evaluated`、
  `aggregate_only_public_artifact`、`diagnostic_only`。unavailable/
  blocked 状态下，live-run 标志为 false（除
  `aggregate_only_public_artifact=true` 和 `diagnostic_only=true`）。
- **Always-false no-claim flags**：
  `downstream_agent_value_proven`、
  `live_agent_generalization_claimed`、`promotion_ready`、
  `default_should_change`、
  `external_benchmark_performance_claimed`、`real_user_task_claimed`、
  `runtime_behavior_changed`、`retriever_changed`、
  `pack_builder_changed`、`backend_changed`、
  `default_policy_changed`、`evidencecore_semantics_changed`。
- **严格公开 scanner**（fail-closed）。拒绝 forbidden dict key 在任何
  位置出现（`prompt`、`messages`、`response`、`provider_payload`、
  `url`、`base_url`、`api_key`、`secret`、`workspace`、`path`、`file`、
  `target_file`、`snippet`、`code`、`patch`、`diff`、`test_output`、
  `stdout`、`stderr`、`event_log`、`stack_trace`、`content_sha`、
  `task_id`、`per_run`、`model_id_raw`、`model_id` 等）及 value 模式：任
  意 URL、32+ 字符 hex digest、secret-like 字符串、path-like 字符串、
  `/tmp/` 工作区路径 value、`task_N` 标识、patch/diff 标记、堆栈跟踪、
  多行字符串、raw JSON 片段、raw 行范围、raw model routing prefix 及
  self-test sentinel。
- **生成在 self-test 失败或 scanner 发现泄漏时拒绝成功**（fail-closed
  `_enforce_no_forbidden` + `_refuse_on_self_test_failure` 在写入
  JSON 前立即运行）。
- **per-run event log/prompt/response/测试输出仅留在 `/tmp`**，绝不提
  交或上传。

### 验证结果

```text
python3 -m py_compile eval/provider_client.py eval/b16c_live_provider_paired_smoke.py  => PASS
python3 eval/provider_client.py --self-test                            => PASS (33/33 checks)
python3 eval/b16c_live_provider_paired_smoke.py --self-test            => PASS (119/119 checks)
python3 eval/b16c_live_provider_paired_smoke.py \
  --out artifacts/b16c_live_provider_paired_smoke/\
b16c_live_provider_paired_smoke_report.json                           => PASS
  (status: blocked_remote_not_enabled,
   forbidden_scan: pass, self_test_passed: true,
   mode: public_aggregate_synthetic_micro_tasks, phase: B16-C,
   model_display_category: unavailable,
   live_llm_agent: false, provider_calls_made: false,
   remote_provider_calls_made: false, paired_run_executed: false,
   downstream_agent_value_proven: false, promotion_ready: false,
   default_should_change: false, retriever_changed: false,
   pack_builder_changed: false, backend_changed: false,
   default_policy_changed: false, evidencecore_semantics_changed: false,
   runtime_behavior_changed: false,
   external_benchmark_performance_claimed: false,
   live_agent_generalization_claimed: false, real_user_task_claimed: false)
python3 scripts/validate_docs_i18n.py                                  => PASS
git diff --check                                                       => PASS
```

手动 CI run `27900913599`（`real-provider-benchmark`，
`stage=b16c_live_provider_paired_smoke`，`enable_remote_models=true`）完成
`status=live_provider_paired_smoke_pass`；已提交 artifact 现在镜像该
sanitized aggregate CI report。该 run 执行 2 个合成任务 / 4 次 live provider
call，4/4 calls 成功，invalid_json_count=0，并通过 workflow privacy
validator。两个 arm 都解出两个平凡 micro 任务（`control_sparse`
solve_rate=1.0；`treatment_context_pack` solve_rate=1.0），因此
treatment-minus-control solve-rate delta 为 0.0。B16-C upload surface
仅包含 sanitized aggregate report；`plan.json` 等通用 `real-provider` artifacts
已从 B16-C artifact upload 中排除。默认本地 no-env 路径在未开启 remote
opt-in / provider env 不可用时仍真实输出 `blocked_remote_not_enabled` /
`unavailable_no_local_provider_env`。详见 [B16-C 详细报告](b16c-live-provider-paired-smoke.md)。

### 注意事项

- B16-C 是公开仅聚合 live-provider 下游 paired smoke artifact。它是
  eval/诊断专用。它**不**改变 runtime、retriever、pack、backend 或
  default policy；它**不**改变 EvidenceCore 语义。它**不是**基准测试
  结果，**不是**下游 agent 价值声明，**不是** runtime-clean 通用算法
  声明，**不是** OOD 时间性声明，也**不是** QuIVer 系统声明。
- B16-C 仅在 `--allow-remote` + `OPENLOCUS_ALLOW_REMOTE=1` + provider
  env 全部设置时使用 **live LLM provider**（OpenAI 兼容）。默认本地
  no-env 路径仍真实输出 `blocked_remote_not_enabled` /
  `unavailable_no_local_provider_env`；已提交 artifact 镜像手动 CI
  live-provider run `27900913599` 的 sanitized 成功结果。它**不是** fake pass。
- B16-C **不**证明下游 agent 价值。
  `downstream_agent_value_proven=false`。
- 成功的 live CI run 是 provider/plumbing 与 live execution smoke。由于两个
  arm 都解出了微型合成任务，它**没有**显示正向 treatment effect
  （`solve_rate` delta = 0.0）。
- B16-C **不**声明 live agent 泛化。
  `live_agent_generalization_claimed=false`。
- B16-C **不**发布 prompt、response、provider payload、base URL、
  API key、raw model 路由前缀、工作区路径、文件路径、源码片段、
  patch/diff、测试输出、raw event log 或 per-run 行。per-run 数据仅
  留在 `/tmp`。
- 所有无声明 / 无运行时变更标志保持 false；诊断标志保持 true；
  live-run 标志**仅**在 live run 实际执行时为 true。未修改任何
  runtime/retriever/pack/model/backend/default-policy 文件；无
  promotion/default/runtime 声明变更。

---

## 2026-06-21 — B16-D Less-Trivial Live-Provider 下游 Paired Smoke

### 目标

继 B16-C 之后，用更难的 live-provider paired smoke 直接测试 context
pack 是否能在更不平凡的合成公开任务上影响 live LLM edit/test 行为。
B16-C 证明了 live-provider 管道和隐私门，但两 arm 饱和
（`solve_rate=1.0`，treatment delta `0.0`）。B16-D 保持相同的仅聚合安
全模型，同时让任务族更不平凡。

### 假设

在 live LLM provider 下的 less-trivial 多文件任务族（同符号
distractor + 需要 support relation）能执行完整 B16 下游 agent edit/test
循环，并产出行为指标 + honest signal 字段
（`context_pack_signal_observed`、`treatment_solve_rate_delta`、
`treatment_wrong_file_edits_delta`），且不声明下游 agent 价值、live
agent 泛化或 promotion/default 变更。

### 实现说明

- **B16-D artifact**
  （`eval/b16d_less_trivial_live_provider_paired_smoke.py`）：公开仅
  聚合 smoke。复用 B16-C 的 `eval/provider_client.py`（不变）。在代码
  中生成确定性 less-trivial 合成公开 micro bug 任务（默认 4；
  `--task-count` 范围 2-8，硬上限 8）；每个任务多文件：`target.py`
  （buggy 函数，与 distractor 同符号）、`distractor.py`（同名
  decoy）、`support.py`（helper constant；support relation）、
  `test_target.py`（导入 target AND support；断言正确关系）。每个
  task+arm 全新 `/tmp` 工作区。仅当 `--allow-remote` +
  `OPENLOCUS_ALLOW_REMOTE=1` + provider env 时使用 live LLM agent。
  结构化 edit action 白名单：仅 `target.py`；action
  `replace_return_value` / `choose_helper_constant` / `no_op`；无任
  意路径，无 shell；distractor/support 不可编辑。真实文件编辑 + 真
  实子进程测试。
- **确定性正确值公式**：
  `helper_constant = 10 + task_index * 7`；
  `correct_value = helper_constant * 2 + task_index`。
- **Paired arm 设计**：`control_sparse`（无 target file cue；无
  support-relation cue；小 token 预算）vs `treatment_context_pack`
  （target file cue、target symbol cue、support-relation cue、
  exact edit constraint；较大 token 预算）。预算/工具约束相同；仅
  context pack 不同。
- **Artifact 身份**：
  `schema_version=b16d_less_trivial_live_provider_paired_smoke.v1`、
  `claim_level=less_trivial_live_provider_downstream_paired_smoke_only`、
  `mode=public_aggregate_synthetic_less_trivial_tasks`、`phase=B16-D`。
  状态枚举：`live_provider_less_trivial_paired_smoke_pass`、
  `blocked_remote_not_enabled`、
  `unavailable_no_local_provider_env`、`provider_call_failed`、
  `structured_action_parse_failed`、`paired_run_failed`、
  `fail_forbidden_scan`。
- **Safe true flags**（仅 live run 时）：与 B16-C 相同的 11 个
  （`downstream_agent_runs_performed`、`live_llm_agent`、
  `provider_calls_made`、`remote_provider_calls_made`、
  `paired_run_executed`、`synthetic_micro_tasks_used`、
  `real_file_edits_performed`、`real_test_commands_executed`、
  `agent_behavior_metrics_evaluated`、
  `aggregate_only_public_artifact`、`diagnostic_only`）。
- **Always-false no-claim flags**（全 12 个）：与 B16-C 相同。
- **Honest signal 字段**（诊断 smoke 结果，**绝不**是
  promotion/default/value 声明）：
  `context_pack_signal_observed`（bool）、`treatment_solve_rate_delta`
  （number）、`treatment_wrong_file_edits_delta`（number）。零/负
  treatment delta 是有效的实证结果。
- **CI 通过标准**：live run completed + privacy scan passed +
  artifact is honest。CI 通过**不**要求 treatment 改善。
- **严格公开 scanner**（fail-closed）：与 B16-C 相同形状；拒绝
  forbidden key 在任何位置出现及 value 模式（URL、hex digest、
  secret-like、path-like、`/tmp/`、任务标识、patch 标记、堆栈跟踪、
  多行、raw JSON、行范围、raw model routing prefix、sentinel）。scanner
  仅对最终公开聚合 artifact 运行。
- **per-run event log/prompt/response/测试输出仅留在 `/tmp`**，绝不提
  交或上传。

### 验证结果

```text
python3 -m py_compile eval/b16d_less_trivial_live_provider_paired_smoke.py  => PASS
python3 eval/b16d_less_trivial_live_provider_paired_smoke.py --self-test  => PASS (138/138 checks)
python3 eval/b16d_less_trivial_live_provider_paired_smoke.py \
  --out artifacts/b16d_less_trivial_live_provider_paired_smoke/\
b16d_less_trivial_live_provider_paired_smoke_report.json               => PASS
  (status: blocked_remote_not_enabled,
   forbidden_scan: pass, self_test_passed: true,
   mode: public_aggregate_synthetic_less_trivial_tasks, phase: B16-D,
   model_display_category: unavailable,
   live_llm_agent: false, provider_calls_made: false,
   remote_provider_calls_made: false, paired_run_executed: false,
   downstream_agent_value_proven: false, promotion_ready: false,
   default_should_change: false, retriever_changed: false,
   pack_builder_changed: false, backend_changed: false,
   default_policy_changed: false, evidencecore_semantics_changed: false,
   runtime_behavior_changed: false,
   external_benchmark_performance_claimed: false,
   live_agent_generalization_claimed: false, real_user_task_claimed: false)
python3 scripts/validate_docs_i18n.py                                  => PASS
git diff --check                                                       => PASS
```

手动 CI run `27901644438`（`real-provider-benchmark`，
`stage=b16d_less_trivial_live_provider_paired_smoke`，
`enable_remote_models=true`）完成
`live_provider_less_trivial_paired_smoke_pass` 并通过 privacy validation。已提交
artifact 现在镜像该 sanitized aggregate CI report：

```text
synthetic_task_count: 4
total_runs: 8
provider calls: 8 attempted / 8 succeeded / 0 failed
invalid_json_count: 0
forbidden_scan: pass
model_display_category: Kimi-K2.7-Code
control_sparse: solve_rate=0.5, tests_pass_rate=0.5, wrong_file_edits_mean=0.0
treatment_context_pack: solve_rate=1.0, tests_pass_rate=1.0, wrong_file_edits_mean=0.0
treatment-minus-control solve_rate delta: +0.5
treatment-minus-control tests_pass_rate delta: +0.5
context_pack_signal_observed: true
```

默认本地 no-provider-env 路径仍真实输出 `blocked_remote_not_enabled` 且 live-run
标志为 false。正向 treatment delta 是微型合成 smoke 信号，不是下游价值或泛化证明。
详见 [B16-D 详细报告](b16d-less-trivial-live-provider-paired-smoke.md)。

### 注意事项

- B16-D 是公开仅聚合 less-trivial live-provider 下游 paired smoke
  artifact。它是 eval/诊断专用。它**不**改变 runtime、retriever、
  pack、backend 或 default policy；它**不**改变 EvidenceCore 语义。
  它**不是**基准测试结果，**不是**下游 agent 价值声明，**不是**
  runtime-clean 通用算法声明，**不是** OOD 时间性声明，也**不是**
  QuIVer 系统声明。
- B16-D 仅在 `--allow-remote` + `OPENLOCUS_ALLOW_REMOTE=1` + provider
  env 全部设置时使用 **live LLM provider**（OpenAI 兼容）。默认本地 no-env
  路径仍真实；已提交 artifact 镜像手动 CI run `27901644438` 的 sanitized
  成功结果。它**不是** fake pass。
- B16-D **不**证明下游 agent 价值。
  `downstream_agent_value_proven=false`。
- B16-D **不**声明 live agent 泛化。
  `live_agent_generalization_claimed=false`。
- B16-D **不**发布 prompt、response、provider payload、base URL、
  API key、raw model 路由前缀、工作区路径、文件路径、源码片段、
  patch/diff、测试输出、raw event log 或 per-run 行。per-run 数据仅
  留在 `/tmp`。
- `honest_signals` 是诊断 smoke 结果，**绝不**是
  promotion/default/value 声明。零/负 treatment delta 是有效的实证
  结果。
- 所有无声明 / 无运行时变更标志保持 false；诊断标志保持 true；
  live-run 标志**仅**在 live run 实际执行时为 true。未修改任何
  runtime/retriever/pack/model/backend/default-policy 文件；无
  promotion/default/runtime 声明变更。

---

## 2026-06-21 — B16-E Broader Live-Provider 下游 Paired Smoke

### 目标

将 B16-D 从单一 less-trivial 合成 live-provider 任务族扩展为小型异构合
成任务族矩阵。测试 context-pack treatment 信号是否能超越 B16-D 模板，
同时保持阶段有界、仅聚合、手动 provider gating。

### 假设

在 live LLM provider 下的异构合成任务族矩阵（四族，各有不同决定性 cue）
能执行完整 B16 下游 agent edit/test 循环，并产出行为指标 + 族级 honest
signal 字段，且不声明下游 agent 价值、live agent 泛化或
promotion/default 变更。

### 实现说明

- **B16-E artifact**
  （`eval/b16e_broader_live_provider_paired_smoke.py`）：公开仅聚合
  smoke。复用 B16-C/D 的 `eval/provider_client.py`（不变）。在四个固定
  白名单任务族中生成确定性异构合成公开 micro bug 任务（默认 8；
  `--task-count` 范围 4-12，硬上限 12；默认 16 live 调用；最多 24）。
  每个任务多文件：`target.py`（buggy 函数，与 distractor 同符号）、
  `distractor.py`（同名 decoy）、`support.py`（helper constant）、
  `test_target.py`（导入 target AND support；断言正确族特定关系）。每
  个 task+arm 全新 `/tmp` 工作区。仅当 `--allow-remote` +
  `OPENLOCUS_ALLOW_REMOTE=1` + provider env 时使用 live LLM agent。
  结构化 edit action 白名单：仅 `target.py`；action
  `replace_return_value` / `choose_helper_constant` / `no_op`；无任
  意路径，无 shell；distractor/support 不可编辑。真实文件编辑 + 真实
  子进程测试。
- **四任务族**（各有不同决定性 cue）：
  1. `same_symbol_support_relation` — 正确值 =
     `helper_constant * 2 + task_index`。
  2. `operation_ambiguity` — 正确值 = `base_value * 2`。
  3. `boundary_condition` — 正确值 = `limit_value - 1`。
  4. `helper_dependency_choice` — 正确值 = `helper_b * 3`。
- **Paired arm 设计**：`control_sparse`（无 target file cue；无决定性
  cue；小 token 预算）vs `treatment_context_pack`（target file cue、
  target symbol cue、族特定决定性 cue、exact edit constraint；较大
  token 预算）。
- **Artifact 身份**：
  `schema_version=b16e_broader_live_provider_paired_smoke.v1`、
  `claim_level=broader_live_provider_downstream_paired_smoke_only`、
  `mode=public_aggregate_synthetic_task_family_matrix`、`phase=B16-E`。
  状态枚举：`broader_live_provider_paired_smoke_pass`、
  `blocked_remote_not_enabled`、
  `unavailable_no_local_provider_env`、`provider_call_failed`、
  `structured_action_parse_failed`、`paired_run_failed`、
  `fail_forbidden_scan`。
- **Safe true flags**（仅 live run 时）：11 个，含
  `synthetic_task_family_matrix_used`。
- **Always-false no-claim flags**（全 12 个）：与 B16-C/D 相同。
- **Records-shaped 容器**：`arm_results`、`paired_deltas`、
  `task_family_results`（固定记录，白名单族名；无 task ID）、
  `family_signal_summary`（仅聚合计数）、`honest_signals`（诊断
  smoke 结果）。
- **env preservation self-test**：回归守卫，无网络 self-test probe 不
  清除 live provider env。
- **CI 通过标准**：live run completed + privacy scan passed +
  artifact is honest。CI 通过**不**要求 treatment 改善。零/负 delta
  有效。

### 验证结果

```text
python3 -m py_compile eval/b16e_broader_live_provider_paired_smoke.py  => PASS
python3 eval/b16e_broader_live_provider_paired_smoke.py --self-test  => PASS (188/188 checks)
python3 eval/b16e_broader_live_provider_paired_smoke.py \
  --out artifacts/b16e_broader_live_provider_paired_smoke/\
b16e_broader_live_provider_paired_smoke_report.json               => PASS
  (status: blocked_remote_not_enabled,
   forbidden_scan: pass, self_test_passed: true,
   mode: public_aggregate_synthetic_task_family_matrix, phase: B16-E,
   model_display_category: unavailable,
   live_llm_agent: false, provider_calls_made: false,
   remote_provider_calls_made: false, paired_run_executed: false,
   synthetic_task_family_matrix_used: false,
   downstream_agent_value_proven: false, promotion_ready: false,
   default_should_change: false, retriever_changed: false,
   pack_builder_changed: false, backend_changed: false,
   default_policy_changed: false, evidencecore_semantics_changed: false,
   runtime_behavior_changed: false,
   external_benchmark_performance_claimed: false,
   live_agent_generalization_claimed: false, real_user_task_claimed: false)
python3 scripts/validate_docs_i18n.py                                  => PASS
git diff --check                                                       => PASS
```

手动 CI run `27902925812`（`real-provider-benchmark`，
`stage=b16e_broader_live_provider_paired_smoke`，
`enable_remote_models=true`）完成
`broader_live_provider_paired_smoke_pass` 并通过 privacy validation。已提交
artifact 现在镜像该 sanitized aggregate CI report：

```text
synthetic_task_count: 8
total_runs: 16
provider calls: 16 attempted / 16 succeeded / 0 failed
invalid_json_count: 0
forbidden_scan: pass
model_display_category: Kimi-K2.7-Code
control_sparse: solve_rate=0.125, tests_pass_rate=0.125, wrong_file_edits_mean=0.0
treatment_context_pack: solve_rate=1.0, tests_pass_rate=1.0, wrong_file_edits_mean=0.0
treatment-minus-control solve_rate delta: +0.875
treatment-minus-control tests_pass_rate delta: +0.875
families_with_positive_solve_delta: 4/4
context_pack_signal_observed: true
```

默认本地 no-provider-env 路径仍真实输出 `blocked_remote_not_enabled` 且
live-run 标志为 false。正向 treatment delta 是更广但仍微型的合成 smoke 信号，
不是下游价值或泛化证明。详见 [B16-E 详细报告](b16e-broader-live-provider-paired-smoke.md)。

### 注意事项

- B16-E 是公开仅聚合 broader live-provider 下游 paired smoke
  artifact。它是 eval/诊断专用。它**不**改变 runtime、retriever、
  pack、backend 或 default policy；它**不**改变 EvidenceCore 语义。
  它**不是**基准测试结果，**不是**下游 agent 价值声明，**不是**
  runtime-clean 通用算法声明，**不是** OOD 时间性声明，也**不是**
  QuIVer 系统声明。
- B16-E 仅在 `--allow-remote` + `OPENLOCUS_ALLOW_REMOTE=1` + provider
  env 全部设置时使用 **live LLM provider**（OpenAI 兼容）。默认本地 no-env
  路径仍真实；已提交 artifact 镜像手动 CI run `27902925812` 的 sanitized
  成功结果。它**不是** fake pass。
- B16-E **不**证明下游 agent 价值。
  `downstream_agent_value_proven=false`。
- B16-E **不**声明 live agent 泛化。
  `live_agent_generalization_claimed=false`。
- B16-E **不**发布 prompt、response、provider payload、base URL、
  API key、raw model 路由前缀、工作区路径、文件路径、源码片段、
  patch/diff、测试输出、raw event log 或 per-run 行。per-run 数据仅
  留在 `/tmp`。
- `honest_signals` 和 `family_signal_summary` 是诊断 smoke 结果，
  **绝不**是 promotion/default/value 声明。零/负 treatment delta
  是有效的实证结果。
- 所有无声明 / 无运行时变更标志保持 false；诊断标志保持 true；
  live-run 标志**仅**在 live run 实际执行时为 true。未修改任何
  runtime/retriever/pack/model/backend/default-policy 文件；无
  promotion/default/runtime 声明变更。

---

## 2026-06-21 — F1-B Retrieval-Derived Counterfactual Utility Smoke

### 目标

将 F1 从纯合成 context variants 推进到 **retrieval-derived**
counterfactual utility：使用真实 ContextBench verified rows、临时公开
repo clones、真实 OpenLocus retrieval 输出及 `eval/score.py` 指标，估计
candidate-set variants 的聚合边际效用。

### 假设

真实 ContextBench verified rows + 真实 OpenLocus retrieval + 真实
`eval/score.py` 指标能产出聚合 counterfactual candidate-set 效用 delta
（bm25 vs empty、regex vs empty、symbol vs empty、symbol added to
bm25），且不进行 provider 调用，不声明下游效用、true E/S 校准或外部
基准测试性能。

### 实现说明

- **F1-B artifact**
  （`eval/f1b_retrieval_derived_counterfactual_utility_smoke.py`）：
  公开仅聚合 smoke。向后兼容导入 C5-A helpers
  （`c5_contextbench_verified_performance_smoke`，C5-A **不**被修改）。
  获取有界 ContextBench verified rows（默认 5；`--row-limit` 硬上限
  10）；在 `/tmp` 下临时 clone repos；按方法（bm25,regex,symbol）运行
  真实 OpenLocus retrieval；运行 `eval/score.py`；派生五个
  candidate-set variants（`baseline_empty_candidate_set`、`bm25_topk`、
  `regex_topk`、`symbol_topk`、`bm25_plus_symbol_topk`）和四个
  counterfactual effects（`bm25_candidates_vs_empty`、
  `regex_candidates_vs_empty`、`symbol_candidates_vs_empty`、
  `symbol_added_to_bm25`）。指标：`file_recall@10`、`mrr`、
  `span_f0.5@10`、`success_rate`。Records-shaped
  `variant_results`、`counterfactual_effects`、`method_inputs`。无动态
  dict 镜像。严格 fail-closed scanner。无 provider 调用。
- **已延迟**：`bm25_plus_distractor_topk` variant 和
  `distractor_added_to_bm25` effect 已延迟（安全实现需要
  per-candidate 身份跟踪，有泄露风险）。
- **Artifact 身份**：
  `schema_version=f1b_retrieval_derived_counterfactual_utility_smoke.v1`、
  `claim_level=retrieval_derived_counterfactual_utility_smoke_only`、
  `mode=public_aggregate_contextbench_retrieval_counterfactual`、
  `phase=F1-B`。
- **Safe true flags**（仅当实际为 true 时）：
  `retrieval_derived_counterfactual_utility_smoke`、
  `external_benchmark_rows_read`、`openlocus_retrieval_executed`、
  `score_py_metrics_computed`、`aggregate_only_public_artifact`、
  `diagnostic_only`。
- **Always-false no-claim flags**：
  `true_e_s_calibration_claimed`、
  `automated_e_s_full_calibration_claimed`、
  `human_e_s_calibration_claimed`、
  `downstream_agent_value_proven`、`live_llm_agent`、
  `provider_calls_made`、`remote_provider_calls_made`、
  `external_benchmark_performance_claimed`、
  `leaderboard_entry_claimed`、`promotion_ready`、
  `default_should_change`、`runtime_behavior_changed`、
  `retriever_changed`、`pack_builder_changed`、`backend_changed`、
  `default_policy_changed`、`evidencecore_semantics_changed`。
- **无 winner/best/recommended-default 字段**。**无 E/S 校准记法**
  （`E_primary` / `S_support`）。

### 验证结果

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

手动 CI run `27903995230` 在 workflow-only upload env 修复（`4fe5708`）后通过。
CI artifact 已下载并结构化检查：

```text
status: retrieval_derived_counterfactual_utility_smoke_pass
rows_fetched: 5
rows_successful: 5
forbidden_scan: pass
bm25_topk: file_recall@10=0.4, mrr=0.225, span_f0.5@10=0.015905, success_rate=1.0
regex_topk: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0
symbol_topk: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0
bm25_plus_symbol_topk: file_recall@10=0.4, mrr=0.225, span_f0.5@10=0.015905, success_rate=1.0
bm25_candidates_vs_empty: file_recall@10 delta=+0.4, mrr delta=+0.225
symbol_added_to_bm25: file_recall@10 delta=0.0, mrr delta=0.0
```

CI artifact 不含 repo URLs、base commits、queries/problem statements、gold
contexts、content hashes、stdout/stderr、`/tmp` paths、provider fields、
winner/best/default 字段或 E/S notation。

F1-B 是首个 retrieval-derived counterfactual utility smoke。它使用
真实 ContextBench verified rows、真实 OpenLocus retrieval 和真实
`eval/score.py` 指标计算聚合 candidate-set 效用 delta。它是
smoke-only：它**不**声明下游效用、true E/S 校准、外部基准测试性能、
leaderboard 条目、promotion 或 default/policy/runtime/retriever/
pack/backend/EvidenceCore 语义变更。详见
[F1-B 详细报告](f1b-retrieval-derived-counterfactual-utility.md)。

### 注意事项

- F1-B 是公开仅聚合 retrieval-derived counterfactual utility smoke
  artifact。它是 eval/诊断专用。它**不**改变 runtime、retriever、
  pack、backend 或 default policy；它**不**改变 EvidenceCore 语义。
  它**不是**基准测试结果，**不是**下游效用，**不是** true E/S 校
  准，**不是**外部基准测试性能声明，**不是** leaderboard 条目，也
  **不是** promotion。
- F1-B **不**进行任何 provider 调用，**不**进行任何远程 provider
  调用。所有临时数据仅保留在内存或 `/tmp`。
- F1-B **不**证明下游 agent 价值。
  `downstream_agent_value_proven=false`。
- F1-B **不**声明 true E/S 校准。
  `true_e_s_calibration_claimed=false`。
- F1-B **不**声明外部基准测试性能。
  `external_benchmark_performance_claimed=false`。
- `bm25_plus_distractor_topk` variant 和 `distractor_added_to_bm25`
  effect 已延迟（安全实现需要 per-candidate 身份跟踪，有泄露风险）。
- `bm25_plus_symbol_topk` 使用近似聚合（per-method 指标 max），**不
  是**真正的 union candidate set。
- 所有无声明 / 无运行时变更标志保持 false；诊断标志保持 true；
  smoke-claimed 标志**仅**在真实网络 run 实际执行时为 true。未修改
  任何 runtime/retriever/pack/model/backend/default-policy 文件；无
  promotion/default/runtime 声明变更。

---

## 2026-06-21 — C5-C ContextBench Verified 检索方法矩阵 Scale Smoke

### 目标

将 C5-B/F1-B 从 5 行 ContextBench verified 检索 smoke 扩展为有界 20 行
外部-benchmark 方法矩阵 scale smoke。从 HF datasets-server **一次性**读取
有界 20 行 ContextBench verified subset（跨所有方法共享），在临时 `/tmp`
目录下检出引用仓库到 `base_commit`（每方法+每行一次），跨请求方法矩阵运行
OpenLocus 检索（默认 `bm25,regex,symbol`；C5-C 仅允许 `bm25,regex,symbol`；
不允许 `text`；无 provider/model 调用），通过现有 `eval/score.py` 逻辑对
每种方法针对 benchmark label spans 打分，并仅提交 aggregate
公共报告。

### 假设

有界 20 行 ContextBench verified subset 可在临时 `/tmp` 工作区下（每方法+
每行一次）通过真实 OpenLocus 检索 + 打分管线跨 `bm25,regex,symbol` 方法矩阵
运行，产出每方法 aggregate 检索 metrics（file_recall@10、mrr、span_f0.5@10、
success_rate）与仅 aggregate 的、与固定 `bm25` baseline 的 delta，而无需
持久化任何行级数据、repo URL/commit、gold paths/spans、生成的 JSONL、
evidence 行、克隆仓库或 stdout/stderr。

### 阶段门

- C5-C 通过当 self-test 通过（179 个检查）、真实网络 smoke 完成（行已抓取、
  仓库已克隆、全部 3 个方法的检索已执行、score.py metrics 已计算）、
  forbidden scan 干净，且提交的 artifact 仅记录 aggregate 计数/比率/均值，
  所有无声明标志为 false，无 `winner`/`best_method`/`recommended_default`。
- C5-C 为 `unavailable_with_reason` 当网络/HF/GitHub/clone/检索/打分失败；
  artifact 记录真实的失败类别，无行级值。

### 实现说明

- **C5-C artifact**
  （`eval/c5c_contextbench_verified_method_matrix_scale_smoke.py`）：
  公共 aggregate-only scale smoke。复用 C5-A 原语（row fetch、query
  sanitizer、clone/retrieval/score runner、score metric allowlist、failure
  categories、scanner 原语），但**不**导入或修改 C5-B。从 HF
  datasets-server `/rows` 端点**一次性**抓取有界 20 行 ContextBench
  verified 行（跨方法共享；分页；仅 stdlib `urllib`；有界超时）；在内存中
  按 `language_filter`（仅为类别桶）过滤；对每种方法（仅
  `bm25,regex,symbol`），对每一行，将 benchmark label context JSON 解析为临时
  `gold_paths`/`gold_lines`（`content` 字段**绝不**读取或持久化）；将
  `problem_statement` sanitizer 为检索 query（仅内存中）；在每行
  `TemporaryDirectory` 下通过 `git clone --filter=blob:none --no-checkout`
  然后 `git checkout` 克隆 `repo_url` 到 `base_commit`（有界超时）；在
  `TemporaryDirectory` 下生成临时 task/label JSONL；通过
  `eval/run_retrieval.py` 运行 OpenLocus 检索（`--method <method> --cwd
  <repo_root>`）；运行 `eval/score.py` 并解析 aggregate metrics；在成功行上
  聚合 metrics（每个 allowlisted 数值 metric 的均值）；记录每方法的
  `aggregate_runtime_seconds`；计算与固定 `bm25` baseline 的 aggregate
  delta；仅写入 aggregate 计数/比率/均值到提交的 artifact。
- **Artifact 身份**：
  `schema_version=c5c_contextbench_verified_method_matrix_scale_smoke.v1`、
  `claim_level=external_benchmark_retrieval_method_matrix_scale_smoke_only`、
  `status=contextbench_method_matrix_scale_smoke_pass|partial|unavailable_with_reason|fail_forbidden_scan`、
  `mode=contextbench_verified_bounded_scale_method_matrix`、`phase=C5-C`。
- **Safe true 标志**（仅当实际为真时为 true）：
  `retrieval_scale_smoke_performed`、`openlocus_retrieval_executed`、
  `score_py_metrics_computed`、`aggregate_only_public_artifact`、
  `diagnostic_only`。（C5-C **不**使用 C5-B 的 `method_matrix_smoke` 标志
  或 C5-A 的 `external_benchmark_rows_read`/
  `repositories_materialized_transiently`/`performance_smoke` 标志。）
- **无声明 / 无运行时变更标志**（全为 false）：
  `external_benchmark_performance_claimed`、
  `leaderboard_entry_claimed`、`downstream_agent_value_proven`、
  `promotion_ready`、`default_should_change`、
  `baseline_is_policy_candidate`、`runtime_behavior_changed`、
  `retriever_changed`、`pack_builder_changed`、`backend_changed`、
  `default_policy_changed`、`evidencecore_semantics_changed`、
  `provider_calls_made`、`remote_provider_calls_made`。
- **License 字段**（固定）：
  `dataset_license_status=unknown_dataset_license`、
  `row_level_redistribution_allowed=false`、
  `derived_row_level_publication_allowed=false`、
  `aggregate_metrics_publication=aggregate_only_smoke`。
- **方法矩阵**：`ALLOWED_METHODS = (bm25, regex, symbol)` 仅。C5-C **不**
  允许 `text`（不同于 C5-B）。`BASELINE_METHOD=bm25`，
  `baseline_is_policy_candidate=false`。
- **严格公共 scanner**（fail-closed）。复用 C5-A forbidden scanner 原语 +
  C5-C 专属检查：拒绝 `method_results` 为以方法名为 key 的 dict；拒绝推荐/
  策略字段（`winner`、`best_method`、`recommended_default` 等）出现在任意
  位置；拒绝额外的 row/repo/query/gold/path/span/snippet/content_sha/
  stdout/stderr key 出现在任意位置；拒绝 `text` 作为 `method_results` 中的
  方法。
- **生成在 self-test 失败或 scanner 发现泄露时拒绝成功**
  （fail-closed `_enforce_c5c_no_forbidden` +
  `_refuse_on_self_test_failure`，在写入 JSON 前立即执行）。
- **临时 /tmp clone + 检索 + 打分**：每方法+每行 `TemporaryDirectory` 用于
  克隆仓库；`TemporaryDirectory` 用于生成的 task/label/run JSONL。所有原始
  ContextBench 行、queries、repo URL/名称、base commit、gold paths/spans/
  contents、生成的 JSONL、evidence 行、克隆仓库与 stdout/stderr 仅保留在
  `/tmp` 下，**绝不**提交或上传。
- **不可用模式**：如果网络 smoke 无法完成，artifact 记录真实的
  `unavailable_with_reason`，带有真实的 `failure_reason_category`（无
  stale/fake pass）。在不可用模式下，`method_results` 是每方法记录的列表，
  每个带 `status=unavailable_with_reason`、`metrics={}`、零行计数；
  `smoke_metric_deltas_vs_baseline=[]`；
  `retrieval_scale_smoke_performed=false`；
  `aggregate_only_public_artifact=true` 与 `diagnostic_only=true` 保持为
  true。

### CI workflow

- `.github/workflows/c5-contextbench-method-matrix-scale-smoke.yml`：
  手动 opt-in `workflow_dispatch`，带布尔
  `enable_external_benchmark_network` 默认 false，`row_limit`（默认 20，硬上限
  20），`methods`（默认 `bm25,regex,symbol`；仅允许 `bm25,regex,symbol`），
  `query_mode` 输入。未启用时，no-op 并显示明确消息。无 `secrets.`、无
  `vars.`、无 `OPENLOCUS_LLM`/`OPENLOCUS_EMBEDDING` env。构建 OpenLocus CLI
  （release），运行 self-test，仅在启用时运行网络 smoke，校验标志，校验 docs
  i18n，检查工作树，仅上传 aggregate 报告（7 天保留）。

### 验证结果

```text
python3 -m py_compile eval/c5c_contextbench_verified_method_matrix_scale_smoke.py  => PASS
python3 eval/c5c_contextbench_verified_method_matrix_scale_smoke.py --self-test  => PASS (174/174 checks)
python3 eval/c5c_contextbench_verified_method_matrix_scale_smoke.py \
  --row-limit 20 --methods bm25,regex,symbol \
  --query-mode first_paragraph --language-filter python \
  --out artifacts/c5c_contextbench_verified_method_matrix_scale/\
c5c_contextbench_verified_method_matrix_scale_report.json  => PASS
  (status: contextbench_method_matrix_scale_smoke_pass,
   forbidden_scan: pass, self_test_passed: true,
   mode: contextbench_verified_bounded_scale_method_matrix, phase: C5-C,
   methods: [bm25, regex, symbol], methods_successful: 3, methods_failed: 0,
   rows_fetched: 20, rows_evaluated: 20, rows_successful: 20, rows_failed: 0,
   network_calls: 1, provider_calls: 0,
   retrieval_scale_smoke_performed: true,
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

手动 CI run `27905621090`（`c5-contextbench-method-matrix-scale-smoke`，
`enable_external_benchmark_network=true`，`row_limit=20`，
`methods=bm25,regex,symbol`）在 workflow 对 network-enabled run 改为 fail-closed
后通过。CI artifact 检查：

```text
status: contextbench_method_matrix_scale_smoke_pass
rows_fetched: 20
methods_successful: 3
methods_failed: 0
forbidden_scan: pass
bm25: file_recall@10=0.35, mrr=0.143107, span_f0.5@10=0.020838, success_rate=1.0
regex: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0
symbol: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0
regex-minus-bm25 file_recall@10 delta: -0.35
symbol-minus-bm25 file_recall@10 delta: -0.35
```

较早的 run `27905321437` 上传了绿色 `unavailable_with_reason` 报告，被视为
fail-open bug 而不是经验性成功；network-enabled C5-C CI 现在要求 pass/partial、
`rows_fetched > 0` 且至少一个方法成功。

C5-C smoke 是第一个外部-benchmark-形态的检索方法矩阵 scale smoke。它执行
从 HF datasets-server 的真实网络抓取（**一次性**，跨全部 3 个方法共享），
在临时 `/tmp` 目录下对引用仓库到其 `base_commit` 的真实 `git clone` +
`git checkout`（每方法+每行一次），对每个仓库运行每种方法（`bm25`、
`regex`、`symbol`）的真实 OpenLocus 检索，以及真实的 `eval/score.py` 打分，
产出有界 20 行 ContextBench verified subset 上的每方法 aggregate 检索
metrics。它明确**不是**严格的 benchmark 结果、**不是** leaderboard 条目、
**不是**性能声称、**不是**promotion、**不是**默认/策略变更、**不是**
runtime/retriever/pack/backend/EvidenceCore 语义变更，也**不是**下游 agent
价值声称。完整的 C5 外部-benchmark-评估阶段仍然是一个有界的规划/可行性
阶段。见 [C5-C 详细报告](c5c-contextbench-method-matrix-scale-smoke.md)。

### 注意事项

- C5-C 是公共 aggregate-only 外部 benchmark 检索方法矩阵 scale smoke
  artifact。它是 eval/diagnostic only。它**不**改变 runtime、retriever、
  pack、backend 或默认策略；它**不**改变 EvidenceCore 语义。它**不是**
  benchmark 结果、**不是**leaderboard 条目、**不是**性能声称、**不是**
  promotion、**不是**默认变更、**不是**runtime-clean 通用算法声称、
  **不是**OOD 时间泛化声称、**不是**QuIVer systems 声称，也**不是**下游
  agent 价值声称。
- C5-C **不**输出 `winner`、`best_method`、`recommended_default` 或任何
  暗示策略/默认决策的字段。固定 `baseline_method` 为 `bm25`，
  `baseline_is_policy_candidate=false`，`default_should_change=false`。
- C5-C **不**运行 provider 调用，**不**运行远程 provider 调用。唯一的网络
  调用是对公共 HF datasets-server（**一次性**抓取有界 ContextBench verified
  行，跨所有方法共享）与对公共 GitHub（在临时 `/tmp` 目录下克隆引用仓库到
  其 `base_commit`，每方法+每行一次）。`provider_calls=0`、
  `provider_calls_made=false`、`remote_provider_calls_made=false`。
- C5-C 使用**有界 20 行 ContextBench verified subset**（每方法默认 20 行；
  硬上限 20）。这是 scale smoke，**不是**严格的 benchmark 评估。Aggregate
  metrics 是有界样本上的点估计，**不应**被解读为 benchmark 结果、
  leaderboard 条目或性能声称。
- C5-C 在临时 `/tmp` 目录下检出引用仓库到其 `base_commit`，每方法+每行
  一次（因为每种方法针对相同的行运行但在隔离工作区中）。克隆的仓库、生成的
  task/label/run JSONL、evidence 行与 stdout/stderr 仅保留在 `/tmp` 下，
  **绝不**提交或上传。提交的 artifact 仅包含 aggregate 计数/比率/均值与
  可选的每方法 aggregate runtime 秒数。
- C5-C **不**声称外部 benchmark 性能。Aggregate metrics 是 smoke 级别
  的诊断，**不是**benchmark 结果。
  `external_benchmark_performance_claimed=false`。
- C5-C **不**证明下游 agent 价值。检索 smoke 不演练任何下游 agent。
  `downstream_agent_value_proven=false`。
- ContextBench 数据集 license 未知
  （`unknown_dataset_license`）；行级再分发被禁用
  （`row_level_redistribution_allowed=false`），派生行级发布被禁用
  （`derived_row_level_publication_allowed=false`）。Aggregate metrics
  发布允许作为 aggregate-only smoke
  （`aggregate_metrics_publication=aggregate_only_smoke`）。
- 所有 no-claim / no-runtime-change 标志保持 false；诊断标志
  （`aggregate_only_public_artifact`、`diagnostic_only`）保持 true。
  未修改任何 runtime/retriever/pack/model/backend/default-policy 文件；
  无 promotion/default/runtime 声明变更。

---

## 2026-06-21 — C5-D RepoQA BM25 检索性能 Smoke

### 目标

运行第一个真实 RepoQA 检索性能 smoke，而不创建另一个仅就绪阶段。使用已知
的 EvalPlus RepoQA release asset `repoqa-2024-06-23.json.gz`，在内存中解析
一个小的有界 Python needle 集，临时克隆引用仓库，运行 OpenLocus `bm25`，
用 `eval/score.py` 对 needle path/line ranges 打分，并仅发布 aggregate
metrics。

### 为何 RepoQA，而非 SWE-Explore

- SWE-Explore C4.3 row-map smoke 在预览行中未找到可用的 line-budget/检索
  label 形状。
- RepoQA 有已知的 release asset 和自然的检索结构：
  `needle.description` 是 query，`needle.path` + start/end lines 是 gold
  target。

### 假设

有界 RepoQA Python needle subset 可在临时 `/tmp` 工作区下通过真实
OpenLocus 检索 + 打分管线运行，产出 aggregate 检索 metrics，而无需持久化
release asset、repo 记录、commit SHA、needle 字段、生成的 JSONL、evidence
行、克隆仓库或 stdout/stderr。

### 阶段门

- C5-D 通过当 self-test 通过（219 个检查）、真实网络 smoke 完成（asset 已
  下载、needle 已解析、仓库已克隆、检索已执行、score.py metrics 已计算）、
  forbidden scan 干净，且提交的 artifact 仅记录 aggregate 计数/比率/均值，
  所有无声明标志为 false，无 `winner`/`best_method`/`recommended_default`。
- C5-D 为 `unavailable_*` 当 asset 下载/解析失败、无 Python needle、或
  repo 克隆/检索/打分失败。

### 实现说明

- **C5-D artifact**（`eval/c5d_repoqa_bm25_retrieval_smoke.py`）：公共
  aggregate-only smoke。下载 `repoqa-2024-06-23.json.gz` 到内存字节（临时；
  **绝不**写入工作区）；在内存中解压；解析按 `language_filter=python`
  过滤的 RepoQA needle（**无**静默全语言回退）；对每个 needle，将
  `needle_description` sanitizer 为检索 query（提取 `Purpose` 部分的第一句；
  仅内存中）；在每 needle `TemporaryDirectory` 下克隆 `repo_url` 到
  `commit_sha`；生成临时 task/label JSONL；通过 `eval/run_retrieval.py`
  运行 OpenLocus 检索（`--method bm25 --cwd <repo_root>`）；运行
  `eval/score.py`；在成功 needle 上聚合 metrics；仅写入 aggregate 计数/比率/
  均值到提交的 artifact。
- **Artifact 身份**：
  `schema_version=c5d_repoqa_retrieval_performance_smoke.v1`、
  `claim_level=repoqa_retrieval_performance_smoke_only`、
  `status=repoqa_retrieval_smoke_pass|partial|unavailable_asset_download_failed|unavailable_no_python_needles|unavailable_repo_clone_failed|fail_forbidden_scan|fail_schema_contract`、
  `mode=repoqa_bounded_bm25_retrieval_smoke`、`phase=C5-D`。
- **Safe true 标志**（仅当实际为真时为 true）：
  `repoqa_retrieval_smoke_performed`、`asset_downloaded_transiently`、
  `repoqa_needles_parsed_in_memory`、
  `repositories_materialized_transiently`、
  `openlocus_retrieval_executed`、`score_py_metrics_computed`、
  `aggregate_only_public_artifact`、`diagnostic_only`。
- **无声明 / 无运行时变更标志**（全为 false）：
  `external_benchmark_performance_claimed`、
  `leaderboard_entry_claimed`、`downstream_agent_value_proven`、
  `promotion_ready`、`default_should_change`、
  `runtime_behavior_changed`、`retriever_changed`、
  `pack_builder_changed`、`backend_changed`、
  `default_policy_changed`、`evidencecore_semantics_changed`、
  `provider_calls_made`、`remote_provider_calls_made`。
- **License 字段**（固定）：
  `dataset_license_status=unknown_dataset_license`、
  `row_level_redistribution_allowed=false`、
  `derived_row_level_publication_allowed=false`、
  `aggregate_metrics_publication=aggregate_only_smoke`。
- **方法矩阵**：`ALLOWED_METHODS = (bm25,)` 仅。
- **语言过滤**：`ALLOWED_LANGUAGE_FILTERS = (python,)` 仅；**无**静默全语言
  回退。
- **严格公共 scanner**（fail-closed）。复用 C5-A forbidden scanner 原语 +
  C5-D 专属检查：拒绝 RepoQA 专属 forbidden key（repo、commit_sha、
  entrypoint_path、topic、content、dependency、needles、needle、needle_name、
  needle_path、needle_description、start_line、end_line、start_byte、
  end_byte、global_*、code_ratio、path、description 等）；拒绝推荐/策略字段
  （`winner`、`best_method`、`recommended_default` 等）出现在任意位置。
- **生成在 self-test 失败或 scanner 发现泄露时拒绝成功**
  （fail-closed `_enforce_c5d_no_forbidden` +
  `_refuse_on_self_test_failure`，在写入 JSON 前立即执行）。
- **临时 /tmp asset + clone + 检索 + 打分**：asset 下载到内存字节（**绝不**
  写入工作区）；每 needle `TemporaryDirectory` 用于克隆仓库；
  `TemporaryDirectory` 用于生成的 task/label/run JSONL。所有原始 repo 记录、
  repo 名称/URL、commit SHA、entrypoint 路径、topics、content、dependency、
  needle 名称/描述/路径/start/end lines、生成的 JSONL、evidence 行、克隆
  仓库与 stdout/stderr 仅保留在 `/tmp` 下，**绝不**提交或上传。
- **不可用状态**：如果网络 smoke 无法完成，artifact 记录真实的
  `unavailable_*`，带有真实的 `failure_reason_category`（无 stale/fake pass）。

### CI workflow

- `.github/workflows/c5-repoqa-bm25-retrieval-smoke.yml`：手动 opt-in
  `workflow_dispatch`，带布尔 `enable_external_benchmark_network` 默认 false，
  `needle_limit`（默认 5，硬上限 10），`language_filter`（仅 python），
  `method`（仅 bm25）输入。未启用时，no-op 并显示明确消息。无 `secrets.`、
  无 `vars.`、无 `OPENLOCUS_LLM`/`OPENLOCUS_EMBEDDING` env。构建 OpenLocus
  CLI（release），运行 self-test，仅在启用时运行网络 smoke，校验标志
  （fail-closed 如 C5-C：network-enabled CI 不可在 unavailable/无 needle 时
  通过；要求 status 在（`repoqa_retrieval_smoke_pass`，`partial`）、
  `needles_seen > 0`、`needles_successful > 0`、`forbidden_scan.status=pass`），
  校验 docs i18n，检查工作树，仅上传 aggregate 报告（7 天保留）。

### 验证结果

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

手动 CI run `27906775008` 已通过，并且只上传 aggregate C5-D report。已提交
artifact 现在镜像该 sanitized CI report：needles_seen=5、needles_successful=5、
needles_failed=0、file_recall@10=0.6、mrr=0.46、span_f0.5@10=0.041634、
success_rate=1.0、aggregate_runtime_seconds=4.025、forbidden_scan=pass、
provider_calls=0。

C5-D smoke 是第一个 RepoQA 形态的检索性能 smoke。它下载
`repoqa-2024-06-23.json.gz` release asset 到内存字节（临时），在内存中解析
5 个 RepoQA Python needle，在临时 `/tmp` 目录下克隆引用仓库到其
`commit_sha`，对每个仓库运行 OpenLocus `bm25` 检索，并运行 `eval/score.py`
产出 aggregate 检索 metrics。它明确**不是**严格的 benchmark 结果、**不是**
leaderboard 条目、**不是**性能声称、**不是**promotion、**不是**默认/策略
变更、**不是**runtime/retriever/pack/backend/EvidenceCore 语义变更，也**不是**
下游 agent 价值声称。完整的 C5 外部-benchmark-评估阶段仍然是一个有界的
规划/可行性阶段。见 [C5-D 详细报告](c5d-repoqa-bm25-retrieval-smoke.md)。

### 注意事项

- C5-D 是公共 aggregate-only RepoQA BM25 检索性能 smoke artifact。它是
  eval/diagnostic only。它**不**改变 runtime、retriever、pack、backend 或
  默认策略；它**不**改变 EvidenceCore 语义。它**不是** benchmark 结果、
  **不是**leaderboard 条目、**不是**性能声称、**不是**promotion、**不是**
  默认变更、**不是**runtime-clean 通用算法声称、**不是**OOD 时间泛化声称、
  **不是**QuIVer systems 声称，也**不是**下游 agent 价值声称。
- C5-D **不**输出 `winner`、`best_method`、`recommended_default` 或任何
  暗示策略/默认决策的字段。
- C5-D **不**运行 provider 调用，**不**运行远程 provider 调用。唯一的网络
  调用是对公共 GitHub（asset 下载 + repo 克隆）。`provider_calls=0`、
  `provider_calls_made=false`、`remote_provider_calls_made=false`。
- C5-D 使用**有界 RepoQA Python needle subset**（默认 5 needle；硬上限
  10）。这是 smoke，**不是**严格的 benchmark 评估。
- C5-D 下载 `repoqa-2024-06-23.json.gz` release asset 到内存字节（临时；
  **绝不**写入工作区）并在内存中解压。克隆的仓库、生成的 task/label/run
  JSONL、evidence 行与 stdout/stderr 仅保留在 `/tmp` 下，**绝不**提交或
  上传。
- C5-D **不**静默从 Python 回退到所有语言。若
  `language_filter=python` 且零 Python needle 找到，artifact 为真实的
  `unavailable_no_python_needles`。
- C5-D **不**声称外部 benchmark 性能。
  `external_benchmark_performance_claimed=false`。
- C5-D **不**证明下游 agent 价值。
  `downstream_agent_value_proven=false`。
- RepoQA 数据集 license 未知
  （`unknown_dataset_license`）；行级再分发被禁用，派生行级发布被禁用。
  Aggregate metrics 发布允许作为 aggregate-only smoke。
- 所有 no-claim / no-runtime-change 标志保持 false；诊断标志
  （`aggregate_only_public_artifact`、`diagnostic_only`）保持 true。
  未修改任何 runtime/retriever/pack/model/backend/default-policy 文件；
  无 promotion/default/runtime 声明变更。

---

## 2026-06-21 — C5-E RepoQA 方法矩阵检索 Smoke

### 目标

将 C5-D 从单方法 RepoQA `bm25` 扩展为 `bm25,regex,symbol` 有界方法矩阵。
临时下载 EvalPlus RepoQA release asset，在内存中解析 Python needle，临时
克隆引用仓库，按方法运行 OpenLocus 检索，用 `eval/score.py` 打分，并仅
发布 aggregate metrics。

### 假设

有界 RepoQA Python needle subset 可在临时 `/tmp` 工作区下通过真实
OpenLocus 检索 + 打分管线跨 `bm25,regex,symbol` 方法矩阵运行，产出每方法
aggregate 检索 metrics 与仅 aggregate 的、与固定 `bm25` baseline 的 delta，
而无需持久化 release asset、repo 记录、commit SHA、needle 字段、生成的
JSONL、evidence 行、克隆仓库或 stdout/stderr。

### 阶段门

- C5-E 通过当 self-test 通过（228 个检查）、真实网络 smoke 完成（asset 已
  下载、needle 已解析、仓库已克隆、全部 3 个方法的检索已执行、score.py
  metrics 已计算）、forbidden scan 干净，且提交的 artifact 仅记录 aggregate
  计数/比率/均值，所有无声明标志为 false，无
  `winner`/`best_method`/`recommended_default`。
- C5-E 为 `unavailable_with_reason` 当 asset 下载/解析失败、无 Python
  needle、或 repo 克隆/检索/打分失败。

### 实现说明

- **C5-E artifact**（`eval/c5e_repoqa_method_matrix_smoke.py`）：公共
  aggregate-only smoke。复用 C5-D 原语（asset 下载、gzip 解析、needle 提取、
  临时 repo clone/checkout、score task/label/run 生成、scanner/failure
  categories）与 C5-B/C5-C 模式（records 形状方法结果、与 baseline 的
  delta）。**不**导入或修改 C5-C。抓取有界 RepoQA Python needle subset
  （跨方法共享）；每方法+每 needle 临时 `/tmp` clone+retrieval+score；每方法
  `aggregate_runtime_seconds`；`method_results` 为记录列表（**非**以方法名为
  key 的 dict）；`smoke_metric_deltas_vs_baseline` 为固定记录，带
  `baseline_method=bm25`。
- **Artifact 身份**：
  `schema_version=c5e_repoqa_method_matrix_smoke.v1`、
  `claim_level=repoqa_retrieval_method_matrix_smoke_only`、
  `status=repoqa_method_matrix_smoke_pass|partial|unavailable_with_reason|fail_forbidden_scan|fail_schema_contract`、
  `mode=repoqa_bounded_method_matrix_smoke`、`phase=C5-E`。
- **Safe true 标志**（仅当实际为真时为 true）：
  `repoqa_method_matrix_smoke_performed`、`asset_downloaded_transiently`、
  `repoqa_needles_parsed_in_memory`、
  `repositories_materialized_transiently`、
  `openlocus_retrieval_executed`、`score_py_metrics_computed`、
  `aggregate_only_public_artifact`、`diagnostic_only`。（C5-E **不**使用
  C5-D 的 `repoqa_retrieval_smoke_performed` 标志。）
- **无声明 / 无运行时变更标志**（全为 false）：
  `external_benchmark_performance_claimed`、
  `leaderboard_entry_claimed`、`downstream_agent_value_proven`、
  `promotion_ready`、`default_should_change`、
  `baseline_is_policy_candidate`、`runtime_behavior_changed`、
  `retriever_changed`、`pack_builder_changed`、`backend_changed`、
  `default_policy_changed`、`evidencecore_semantics_changed`、
  `provider_calls_made`、`remote_provider_calls_made`。
- **方法矩阵**：`ALLOWED_METHODS = (bm25, regex, symbol)` 仅。`text`
  **不**允许。`BASELINE_METHOD=bm25`，
  `baseline_is_policy_candidate=false`。
- **严格公共 scanner**（fail-closed）。复用 C5-D forbidden scanner 原语 +
  C5-E 专属检查：拒绝 `method_results` 为以方法名为 key 的 dict；拒绝推荐/
  策略字段出现在任意位置；拒绝 RepoQA 专属 forbidden key 出现在任意位置。
- **生成在 self-test 失败或 scanner 发现泄露时拒绝成功**
  （fail-closed `_enforce_c5e_no_forbidden` +
  `_refuse_on_self_test_failure`，在写入 JSON 前立即执行）。
- **临时 /tmp asset + clone + 检索 + 打分**：asset 下载到内存字节（**绝不**
  写入工作区）；每方法+每 needle `TemporaryDirectory` 用于克隆仓库；
  `TemporaryDirectory` 用于生成的 task/label/run JSONL。所有原始 repo 记录、
  repo 名称/URL、commit SHA、entrypoint 路径、topics、content、dependency、
  needle 名称/描述/路径/start/end lines、生成的 JSONL、evidence 行、克隆
  仓库与 stdout/stderr 仅保留在 `/tmp` 或内存中，**绝不**提交或上传。
- **不可用模式**：如果网络 smoke 无法完成，artifact 记录真实的
  `unavailable_with_reason`，带真实的 `failure_reason_category`（无
  stale/fake pass）。`method_results` 是每方法记录的列表，每个带
  `status=unavailable_with_reason`、`metrics={}`、零 needle 计数；
  `smoke_metric_deltas_vs_baseline=[]`。

### CI workflow

- `.github/workflows/c5-repoqa-method-matrix-smoke.yml`：手动 opt-in
  `workflow_dispatch`，带布尔 `enable_external_benchmark_network` 默认
  false，`needle_limit`（默认 5，硬上限 10），`methods`（默认
  `bm25,regex,symbol`；仅允许 bm25/regex/symbol），`language_filter`
  （仅 python）输入。未启用时，no-op 并显示明确消息。无 `secrets.`、无
  `vars.`、无 provider model env。构建 OpenLocus
  CLI（release），运行 self-test，仅在启用时运行网络 smoke，校验标志
  （fail-closed 如 C5-C：network-enabled CI 不可在 unavailable/无 needle 时
  通过；要求 status 在（`repoqa_method_matrix_smoke_pass`，`partial`）、
  `needles_seen > 0`、`methods_successful > 0`、
  `forbidden_scan.status=pass`），校验 docs i18n，检查工作树，仅上传
  aggregate 报告（7 天保留）。

### 验证结果

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

手动 CI run `27907731742` 已通过，并且只上传 aggregate C5-E report。已提交
artifact 现在镜像该 sanitized CI report：needles_seen=5、methods_successful=3、
methods_failed=0、bm25 file_recall@10=0.6/mrr=0.46/span_f0.5@10=0.041634/
success_rate=1.0，regex 与 symbol file_recall@10=0.0，aggregate_runtime_seconds
bm25=9.416 / regex=6.969 / symbol=11.436，forbidden_scan=pass，provider_calls=0。

C5-E smoke 是第一个 RepoQA 形态的检索方法矩阵 smoke。它下载
`repoqa-2024-06-23.json.gz` release asset 到内存字节（临时），在内存中解析
5 个 RepoQA Python needle，在临时 `/tmp` 目录下克隆引用仓库到其
`commit_sha`（每方法+每 needle 一次），对每个仓库运行每种方法（`bm25`、
`regex`、`symbol`）的 OpenLocus 检索，并运行 `eval/score.py` 产出每方法
aggregate 检索 metrics。它明确**不是**严格的 benchmark 结果、**不是**
leaderboard 条目、**不是**性能声称、**不是**promotion、**不是**默认/策略
变更、**不是**runtime/retriever/pack/backend/EvidenceCore 语义变更，也**不是**
下游 agent 价值声称。完整的 C5 外部-benchmark-评估阶段仍然是一个有界的
规划/可行性阶段。见 [C5-E 详细报告](c5e-repoqa-method-matrix-smoke.md)。

### 注意事项

- C5-E 是公共 aggregate-only RepoQA 检索方法矩阵 smoke artifact。它是
  eval/diagnostic only。它**不**改变 runtime、retriever、pack、backend 或
  默认策略；它**不**改变 EvidenceCore 语义。它**不是** benchmark 结果、
  **不是**leaderboard 条目、**不是**性能声称、**不是**promotion、**不是**
  默认变更、**不是**runtime-clean 通用算法声称、**不是**OOD 时间泛化声称、
  **不是**QuIVer systems 声称，也**不是**下游 agent 价值声称。
- C5-E **不**输出 `winner`、`best_method`、`recommended_default` 或任何
  暗示策略/默认决策的字段。固定 `baseline_method` 为 `bm25`，
  `baseline_is_policy_candidate=false`，`default_should_change=false`。
- C5-E **不**运行 provider 调用，**不**运行远程 provider 调用。唯一的网络
  调用是对公共 GitHub（asset 下载 + repo 克隆）。`provider_calls=0`、
  `provider_calls_made=false`、`remote_provider_calls_made=false`。
- C5-E 使用**有界 RepoQA Python needle subset**（每方法默认 5 needle；硬
  上限 10）。这是 smoke，**不是**严格的 benchmark 评估。
- C5-E 在临时 `/tmp` 目录下检出引用仓库到其 `commit_sha`，每方法+每 needle
  一次（因为每种方法针对相同的 needle 运行但在隔离工作区中）。
- C5-E **不**静默从 Python 回退到所有语言。
- C5-E **不**声称外部 benchmark 性能。
  `external_benchmark_performance_claimed=false`。
- C5-E **不**证明下游 agent 价值。
  `downstream_agent_value_proven=false`。
- RepoQA 数据集 license 未知；行级再分发被禁用，派生行级发布被禁用。
  Aggregate metrics 发布允许作为 aggregate-only smoke。
- 所有 no-claim / no-runtime-change 标志保持 false；诊断标志保持 true。
  未修改任何 runtime/retriever/pack/model/backend/default-policy 文件；
  无 promotion/default/runtime 声明变更。

## 2026-06-21 — C5-F RepoQA 10-Needle 方法矩阵 Scale Smoke

### 变更内容

C5-F 将 C5-E 从每方法 5 个 RepoQA Python needle 扩展到每方法 10 个 needle，同时保持 C5-E 是已完成 checkpoint。C5-F 是独立 artifact/workflow/docs phase：

- evaluator：`eval/c5f_repoqa_method_matrix_scale_smoke.py`
- artifact：`artifacts/c5f_repoqa_method_matrix_scale/c5f_repoqa_method_matrix_scale_report.json`
- workflow：`.github/workflows/c5-repoqa-method-matrix-scale-smoke.yml`
- 详细报告：[C5-F 详细报告](c5f-repoqa-method-matrix-scale-smoke.md)

C5-F 复用 C5-E 的 RepoQA asset/needle/clone/retrieval/score 管线，但替换为 C5-F identity（`schema_version=c5f_repoqa_method_matrix_scale_smoke.v1`、`claim_level=repoqa_retrieval_method_matrix_scale_smoke_only`、`mode=repoqa_bounded_10_needle_method_matrix_scale_smoke`、`phase=C5-F`）以及默认/硬上限 needle limit 10。

### 真实 smoke

```text
python3 -m py_compile eval/c5f_repoqa_method_matrix_scale_smoke.py => PASS
python3 eval/c5f_repoqa_method_matrix_scale_smoke.py --self-test => PASS (191/191 checks)
python3 eval/c5f_repoqa_method_matrix_scale_smoke.py --needle-limit 10 --language-filter python --methods bm25,regex,symbol --out artifacts/c5f_repoqa_method_matrix_scale/c5f_repoqa_method_matrix_scale_report.json => PASS
```

手动 CI run `27909885489` 已成功完成，已提交 artifact 现在镜像该 sanitized aggregate report。

Aggregate result：

```text
status: repoqa_method_matrix_scale_smoke_pass
needles_seen: 10
methods_successful: 3
methods_failed: 0
forbidden_scan: pass
provider_calls: 0
bm25: file_recall@10=0.5, mrr=0.369216, span_f0.5@10=0.020817, success_rate=1.0
regex: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0
symbol: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0
aggregate_runtime_seconds: bm25=19.018, regex=18.181, symbol=28.251
regex-minus-bm25 file_recall@10 delta: -0.5
symbol-minus-bm25 file_recall@10 delta: -0.5
```

### 边界

C5-F 是 smoke-only。它不声明外部 benchmark 结果、leaderboard 条目、性能、promotion、默认变更、方法 winner、runtime/retriever/pack/backend/EvidenceCore 语义变更或下游 agent 价值。它不输出 `winner`、`best_method`、`recommended_default` 或 policy/default recommendation 字段。Raw RepoQA repo 值、commit、description、path、line range、source、生成的 JSONL、retrieval evidence rows、stdout/stderr、clone path、row ID、hash 与 provider fields 均保持临时，绝不提交或上传。手动 workflow 仅 `workflow_dispatch`，不使用 provider credential/model environment，只上传 aggregate report，并对 network-enabled run fail-closed。

---

## 2026-06-21 — F1-C Cross-Benchmark Retrieval-Derived Utility Smoke

### 目标

在两个有界外部-benchmark-形态的检索样本上产出新的实证 counterfactual
utility 实验。F1-C 必须重新运行真实数据，而非组合现有 C5 aggregate
artifact。F1-C 重新运行 ContextBench verified（20 行，python，
`first_paragraph`，`bm25,regex,symbol`）和 RepoQA（10 个 Python
needle，`bm25,regex,symbol`），并按 benchmark/method 计算固定
retrieval-derived utility proxy、跨基准加权均值与 counterfactual
effects。

### 假设

真实 ContextBench verified 20 行 + 真实 RepoQA 10 needle 重新运行，
结合固定诊断 utility proxy
（`utility = file_recall@10 + 0.25*mrr + 0.5*span_f0.5@10 -
miss_penalty`，其中 `miss_penalty=0.25 if file_recall@10 == 0 else
0`）与合成 `empty_retrieval` 零基线，可产出聚合跨基准 counterfactual
utility delta（`bm25_vs_empty`、`regex_vs_empty`、`symbol_vs_empty`、
`regex_vs_bm25`、`symbol_vs_bm25`），无需 provider 调用，且不声明下游
效用、true E/S 校准、方法 winner 或外部基准性能。

### 实现说明

- **F1-C artifact**
  （`eval/f1c_cross_benchmark_retrieval_utility.py`）：公开仅聚合跨基准
  smoke。向后兼容导入 C5-C、C5-E、C5-A、C5-D helpers（均未修改）。
  ContextBench 复用 C5-C matrix 执行（`c5c._run_single_method`、
  `c5c._public_failure_counts`、`c5c.PUBLIC_FAILURE_CATEGORIES`）；
  RepoQA 复用 C5-E matrix 执行（`c5e._run_single_method`）。重新运行
  真实有界外部数据：ContextBench verified 20 行（HF datasets-server
  `/rows`；仅 stdlib `urllib`；分页；跨方法共享）；RepoQA 10 个 Python
  needle（EvalPlus release asset `repoqa-2024-06-23.json.gz` 下载到内
  存字节；内存解压；内存解析 needle；**不**静默回退到 all-language）。
  复用 C5-A 原语（`_fetch_contextbench_rows`、
  `_resolve_openlocus_binary`、`_clone_and_checkout`、
  `_run_retrieval_and_score`、`_filter_score_metrics`）与 C5-D 原语
  （`_download_asset_to_bytes`、`_decompress_asset`、
  `_parse_repoqa_needles`、`_sanitize_needle_description`）。
- **效用公式（固定诊断 proxy；**不是**下游 solve rate，**不是** E/S
  校准）**：
  `utility = file_recall@10 + 0.25*mrr + 0.5*span_f0.5@10 -
  miss_penalty`，其中 `miss_penalty=0.25 if file_recall@10 == 0
  else 0`。
- **Counterfactual effects（固定白名单；仅 records-shaped）**：
  `bm25_vs_empty`（bm25 - empty_retrieval）、`regex_vs_empty`
  （regex - empty_retrieval）、`symbol_vs_empty`（symbol -
  empty_retrieval）、`regex_vs_bm25`（regex - bm25）、`symbol_vs_bm25`
  （symbol - bm25）。针对每个聚合指标（`file_recall@10`、`mrr`、
  `span_f0.5@10`、`success_rate`、`retrieval_utility`）的跨基准加权
  均值计算。
- **跨基准加权均值**：按样本计数（ContextBench 行计数、RepoQA needle
  计数）。`empty_retrieval` 在两个基准上 sample_count=0；其加权均值按
  构造为 0。
- **Artifact identity**：
  `schema_version=f1c_cross_benchmark_retrieval_utility.v1`、
  `claim_level=cross_benchmark_retrieval_derived_utility_smoke_only`、
  `mode=bounded_contextbench_repoqa_retrieval_utility`、阶段 `F1-C`。
  状态枚举：`cross_benchmark_retrieval_utility_pass`（两基准都 pass
  且 bm25 在两基准上都成功）、`partial_with_exclusions`（至少一个基
  准 pass 且 bm25 至少在一个基准上成功）、`unavailable_with_reason`
  （无/阻塞/网络不可用）、`fail_forbidden_scan`、
  `fail_schema_contract`。
- **Safe true flags**（仅当实际为 true 时）：
  `retrieval_derived_counterfactual_utility_smoke`、
  `contextbench_rows_read`、`repoqa_needles_read`、
  `openlocus_retrieval_executed`、`score_py_metrics_computed`、
  `aggregate_only_public_artifact`、`diagnostic_only`。
- **Always-false no-claim flags**：`true_e_s_calibration_claimed`、
  `automated_e_s_full_calibration_claimed`、
  `human_e_s_calibration_claimed`、
  `external_benchmark_performance_claimed`、
  `leaderboard_entry_claimed`、`method_winner_claimed`、
  `baseline_is_policy_candidate`、`downstream_agent_value_proven`、
  `promotion_ready`、`default_should_change`、
  `runtime_behavior_changed`、`retriever_changed`、
  `pack_builder_changed`、`backend_changed`、
  `default_policy_changed`、`evidencecore_semantics_changed`、
  `provider_calls_made`、`remote_provider_calls_made`。
- **无 winner/best/recommended-default 字段**。**无 E/S 校准记法**
  （`E_primary` / `S_support`）。**无 raw model/routing 前缀**。
- **失败类别保持分离**：ContextBench 失败类别（C5-C public 枚举，含
  `label_context_parse_failed` 重命名）位于
  `contextbench_failure_category_counts`；RepoQA 失败类别
  （C5-D/C5-E 枚举，含 `asset_download_failed`、
  `needle_parse_failed` 等）位于 `repoqa_failure_category_counts`。
  不兼容枚举**不**合并。
- **Forbidden scanner（公开，fail-closed）**：组合 C5-A/C5-C/C5-E
  scanner 并添加 F1-C 特定检查：拒绝任意位置出现 recommendation /
  ES-notation key；拒绝 `benchmark_results` /
  `cross_benchmark_method_results` / `counterfactual_effects` 的
  dict-keyed 镜像；拒绝 raw model 路由前缀（`[mk]`）。

### 验证结果

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
   contextbench_rows_read: true, repoqa_needles_read: true,
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

本地真实网络 run 与手动 CI run `27911651758` 产出以下聚合指标：

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

已提交 artifact 不含 repo URL、commit、problem statement、query、
needle description、gold label、label path/span/line range、source
snippet、生成 JSONL、retrieval evidence row、candidate path/span/
content hash、stdout/stderr、clone path、raw asset row、row hash、
provider field、raw model/routing 前缀或 winner/best/default/
recommended 字段。

F1-C 是首个跨基准 retrieval-derived utility smoke。它重新运行真实
ContextBench verified 20 行 + RepoQA 10 needle Python 外部数据、真实
OpenLocus retrieval 与真实 `eval/score.py` 指标，以计算固定
retrieval-derived utility proxy 与聚合 counterfactual delta。它是
smoke-only：它**不**声明下游效用、true E/S 校准、方法 winner、外部
基准性能、leaderboard 条目、promotion 或
default/policy/runtime/retriever/pack/backend/EvidenceCore 语义变更。
详见 [F1-C 详细报告](f1c-cross-benchmark-retrieval-utility.md)。

### 注意事项

- F1-C 是公开仅聚合跨基准 retrieval-derived utility smoke artifact。
  它是 eval/诊断专用。它**不**改变 runtime、retriever、pack、backend
  或 default policy；它**不**改变 EvidenceCore 语义。它**不是**基准
  测试结果，**不是**下游效用，**不是** true E/S 校准，**不是**外部
  基准测试性能声明，**不是** leaderboard 条目，**不是**方法 winner，
  也**不是** promotion。
- F1-C 重新运行真实有界外部数据（ContextBench verified 20 行 + RepoQA
  10 needle Python）。它**不**组合现有 C5-C 或 C5-E aggregate
  artifact；它重新执行真实 retrieval+score 管线。
- F1-C **不**进行任何 provider 调用，**不**进行任何远程 provider 调
  用。所有临时数据仅保留在内存或 `/tmp`。
- F1-C **不**证明下游 agent 价值。
  `downstream_agent_value_proven=false`。
- F1-C **不**声明 true E/S 校准。
  `true_e_s_calibration_claimed=false`。
- F1-C **不**声明外部基准测试性能。
  `external_benchmark_performance_claimed=false`。
- F1-C **不**声明方法 winner。
  `method_winner_claimed=false`。
- 效用公式是固定诊断 proxy。它**不是**下游 solve rate，**不是**已校准
  agent utility，**不是** promotion 指标。miss_penalty（当
  file_recall@10 == 0 时为 0.25）可能产生负效用值；这是有意的。
- `empty_retrieval` 是合成零上下文基线。不对其执行 retrieval run；
  所有指标与效用按构造为 0。
- 跨基准加权均值使用样本计数作为权重。这是 smoke 级聚合，**不是**正
  式 meta-analysis。
- ContextBench 与 RepoQA 失败类别在公开 artifact 中保持分离；其不兼
  容枚举**不**合并。
- 所有无声明 / 无运行时变更标志保持 false；诊断标志保持 true；
  smoke-claimed 标志**仅**在真实网络 run 实际执行时为 true。未修改任
  何 runtime/retriever/pack/model/backend/default-policy 文件；无
  promotion/default/runtime 声明变更。

## 2026-06-21 — F1-D 跨基准检索 Utility 稳健性 Smoke

### 目标

将 F1-C 从点估计扩展到诊断性 paired-bootstrap 置信/符号稳定性估计。
F1-D 必须重新运行真实有界外部数据（不组合现有 C5 或 F1-C aggregate
artifact），在聚合前拦截 per-unit score 指标（仅在内存或 `/tmp` 中），
按 benchmark/method 计算固定 retrieval-derived utility proxy、跨基准加
权均值，以及五个固定 effect 跨五个 metric 的 paired bootstrap 置信/符
号稳定性统计。

### 假设

对 ContextBench verified 20 行 + RepoQA 10 needle 的真实重新运行，结
合聚合前的 per-unit 指标拦截、固定诊断 utility proxy（与 F1-C 不变：
`utility = file_recall@10 + 0.25*mrr + 0.5*span_f0.5@10 - miss_penalty`，
其中 `miss_penalty=0.25 if file_recall@10 == 0 else 0`）、合成
`empty_retrieval` 零基线，以及保持基准样本计数的 paired 跨基准
bootstrap 重采样，可以在不进行 provider 调用、不声明下游效用、true E/S
校准、方法 winner、外部基准性能或正式置信区间的前提下，产出 effect
`bm25_vs_empty`、`regex_vs_empty`、`symbol_vs_empty`、
`regex_vs_bm25`、`symbol_vs_bm25` 在 metric `retrieval_utility`、
`file_recall@10`、`mrr`、`span_f0.5@10`、`success_rate` 上的聚合
bootstrap 置信区间（p05/p50/p95）与符号稳定性分数。

### 实现备注

- **F1-D artifact**
  （`eval/f1d_cross_benchmark_retrieval_robustness.py`）：公开仅聚合跨
  基准稳健性 smoke。导入 F1-C、C5-C、C5-E、C5-A、C5-D helper 向后兼容
  （均未修改）。本地镜像 C5-C `_run_single_method` 循环与 C5-E
  `_run_single_method` 循环，但在聚合前将 per-unit 指标捕获为
  `dict[int, dict[str, float]]`（unit index -> 指标），仅存在于内存。
  **不**调用会内部折叠 per-unit 数据的 `c5c._run_single_method` 或
  `c5e._run_single_method`。复用 C5-A 原语
  （`_fetch_contextbench_rows`、`_resolve_openlocus_binary`、
  `_clone_and_checkout`、`_run_retrieval_and_score`、
  `_parse_gold_context`、`_sanitize_query`、`_write_transient_jsonl`）
  与 C5-D 原语（`_download_asset_to_bytes`、`_decompress_asset`、
  `_parse_repoqa_needles`、`_sanitize_needle_description`、
  `_clone_and_checkout`、`_write_transient_jsonl`、
  `_run_retrieval_and_score`）。复用 F1-C utility 公式
  （`f1c._compute_utility`、`f1c._extract_method_metrics`）以保证公式同
  一性。复用 F1-C scanner（`f1c._scan_f1c`）并添加 F1-D 特定 forbidden
  key 与 record-shape 检查。
- **Utility 公式（固定诊断 proxy；与 F1-C 不变）**：
  `utility = file_recall@10 + 0.25*mrr + 0.5*span_f0.5@10 - miss_penalty`，
  其中 `miss_penalty=0.25 if file_recall@10 == 0 else 0`。
- **Per-unit 指标拦截**：F1-D 为每个成功 unit（row/needle）捕获 per-unit
  score.py 指标（file_recall@10、mrr、span_f0.5@10、success_rate），计
  算 per-unit retrieval_utility，并作为
  `dict[int, dict[str, float]]` 仅存储在内存中。Per-unit 数据**绝不**写
  入磁盘或提交。公开 artifact 仅输出聚合均值与 bootstrap 统计。
- **聚合 retrieval_utility**：从聚合 metric 均值计算（mean 的 utility），
  与 F1-C 的聚合语义一致。这**不是** per-unit utility 的均值（
  miss_penalty 非线性使两者不同）。
- **Bootstrap effects（固定 allowlist；仅 records 形态）**：
  `bm25_vs_empty`（bm25 - empty_retrieval）、`regex_vs_empty`
  （regex - empty_retrieval）、`symbol_vs_empty`（symbol -
  empty_retrieval）、`regex_vs_bm25`（regex - bm25）、`symbol_vs_bm25`
  （symbol - bm25）。计算用于每个聚合 metric（`file_recall@10`、`mrr`、
  `span_f0.5@10`、`success_rate`、`retrieval_utility`）的跨基准加权均
  值。5 个 effect x 5 个 metric = 25 条 bootstrap effect 记录。
- **跨基准重采样（保持样本计数）**：在每个 bootstrap replicate 内，
  ContextBench paired unit 按 ContextBench 样本计数（20）有放回重采样，
  RepoQA paired unit 按 RepoQA needle 计数（10）有放回重采样，跨基准加
  权均值使用原始样本计数作为权重计算。对于 paired effect
  （`regex_vs_bm25`、`symbol_vs_bm25`），重采样保持 treatment-baseline
  配对（paired complete-case 分析）。对于 `retrieval_utility`，
  bootstrap 从重采样的聚合 metric 均值重新计算 utility（mean 的
  utility）。对于 `empty_retrieval` baseline，baseline utility 按构造
  为 0.0（**不是** utility(0,0,0) 即 -0.25）。
- **公开 effect 记录字段**：`effect_name`、`metric`、`point_estimate`、
  `bootstrap_mean`、`ci_p05`、`ci_p50`、`ci_p95`、
  `sign_positive_fraction`、`sign_negative_fraction`、
  `sign_zero_fraction`、`sample_units`、`bootstrap_replicates`、
  `bootstrap_seed`。
- **Artifact 身份**：
  `schema_version=f1d_cross_benchmark_retrieval_robustness.v1`、
  `claim_level=cross_benchmark_retrieval_utility_robustness_smoke_only`、
  `mode=bounded_contextbench_repoqa_retrieval_robustness`、阶段
  `F1-D`。状态枚举：
  `cross_benchmark_retrieval_robustness_pass`（两个基准均通过且 bm25 在
  两者上均成功）、`partial`（至少一个基准通过且 bm25 至少在一个上成
  功）、`unavailable_with_reason`（无/阻塞/网络不可用）、
  `fail_forbidden_scan`、`fail_schema_contract`。
- **安全 true flag**（仅当实际为 true 时）：
  `retrieval_utility_robustness_smoke`、`contextbench_rows_read`、
  `repoqa_needles_read`、`openlocus_retrieval_executed`、
  `score_py_metrics_computed`、`bootstrap_computed`、
  `aggregate_only_public_artifact`、`diagnostic_only`。
- **始终为 false 的 no-claim flag**：`true_e_s_calibration_claimed`、
  `automated_e_s_full_calibration_claimed`、
  `human_e_s_calibration_claimed`、
  `external_benchmark_performance_claimed`、
  `leaderboard_entry_claimed`、`method_winner_claimed`、
  `baseline_is_policy_candidate`、`downstream_agent_value_proven`、
  `promotion_ready`、`default_should_change`、
  `runtime_behavior_changed`、`retriever_changed`、
  `pack_builder_changed`、`backend_changed`、
  `default_policy_changed`、`evidencecore_semantics_changed`、
  `provider_calls_made`、`remote_provider_calls_made`。
- **无 winner/best/recommended-default 字段**。**无 E/S 校准记法**
  （`E_primary` / `S_support`）。**无 raw model/routing prefix**。
  **无 per-unit metric 数组、row hash 或 F1-C 容器名**
  （`benchmark_results`、`cross_benchmark_method_results`、
  `counterfactual_effects`）。
- **失败类别保持分离**：ContextBench 失败类别在
  `contextbench_failure_category_counts` 下；RepoQA 失败类别在
  `repoqa_failure_category_counts` 下。不兼容枚举**不**合并。
- **Forbidden scanner（公开，fail-closed）**：组合 F1-C scanner（本身
  组合 C5-A/C5-C/C5-E scanner 与 F1-C 特定检查）并添加 F1-D 特定检查：
  拒绝任意位置出现 F1-C record 容器名与 per-unit metric 数组 key；拒绝
  `benchmark_method_means` / `cross_benchmark_method_means` /
  `bootstrap_effect_records` 的 dict-keyed mirror；拒绝 raw model routing
  prefix。

### 验证结果

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
   bootstrap_computed: true,
   contextbench_rows_read: true, repoqa_needles_read: true,
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

本地真实网络 run 与手动 CI run `27913035117` 产生以下聚合指标与 bootstrap 统计：

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

点估计与 F1-C 的跨基准加权均值 delta 一致（`bm25_vs_empty`
retrieval_utility = +0.465035，`regex_vs_bm25` = -0.715035），确认
utility 公式与聚合与 F1-C 不变。bootstrap CI 与符号稳定性分数在这些
点估计之上扩展了诊断性稳健性信息。

已提交 artifact 不包含 repo URL、commit、problem statement、query、
needle description、gold label、label path/span/line range、source
snippet、generated JSONL、retrieval evidence row、candidate path/span/
content hash、stdout/stderr、clone path、raw asset row、per-row/
per-needle metric 数组、row hash、provider 字段、raw model/routing
prefix、F1-C 容器名或 winner/best/default/recommended 字段。

F1-D 是首个跨基准检索 utility 稳健性 smoke。它重新运行真实
ContextBench verified 20 行 + RepoQA 10 needle Python 外部数据，在聚
合前拦截 per-unit score 指标，并计算 paired bootstrap 置信/符号稳定
性统计。它是 smoke-only：它**不**声明下游效用、true E/S 校准、方法
winner、外部基准性能、正式置信区间、leaderboard 条目、promotion 或
default/policy/runtime/retriever/pack/backend/EvidenceCore 语义变更。详见
[F1-D 详细报告](f1d-cross-benchmark-retrieval-robustness.md)。

### 注意事项

- F1-D 是公开仅聚合跨基准检索 utility 稳健性 smoke artifact。它是
  eval/诊断专用。它**不**改变 runtime、retriever、pack、backend 或
  default policy；它**不**改变 EvidenceCore 语义。它**不是**基准测试
  结果，**不是**下游效用，**不是** true E/S 校准，**不是**外部基准测
  试性能声明，**不是** leaderboard 条目，**不是**方法 winner，**不
  是**正式置信区间，也**不是** promotion。
- F1-D 重新运行真实有界外部数据（ContextBench verified 20 行 + RepoQA
  10 needle Python）。它**不**组合现有 C5-C、C5-E 或 F1-C aggregate
  artifact；它重新执行真实 retrieval+score 管线，并在聚合前在内存中拦
  截 per-unit 指标。
- F1-D **不**进行任何 provider 调用，**不**进行任何远程 provider 调
  用。所有临时数据仅保留在内存或 `/tmp`。Per-unit 指标仅存在于内存或
  `/tmp`；公开 artifact 仅输出聚合均值与 bootstrap 统计。
- bootstrap 统计是诊断性稳健性估计，**不是**正式外部基准置信区间。它
  们反映有界 smoke 样本的变异性，而非完整基准评估的总体级不确定性。
- `success_rate` metric 是退化的（对成功完成检索的 real method 始终
  为 1.0）。bootstrap 正确反映这一点。
- 跨基准重采样保持基准样本计数。这是 smoke 级诊断，**不是**正式
  meta-analysis。
- 所有无声明 / 无运行时变更标志保持 false；诊断标志保持 true；
  smoke-claimed 标志**仅**在真实网络 run 实际执行时为 true。未修改任
  何 runtime/retriever/pack/model/backend/default-policy 文件；无
  promotion/default/runtime 声明变更。

## 2026-06-21 — D5-A1 自动化校准特征表

### 目标

从实证 smoke 推进到校准就绪弱监督特征，通过机器读取已提交的聚合
artifact 并计算确定性特征记录。D5-A1 是对真实先前 run 的经验特征提
取，不是研究日志摘要，也不是校准。

### 假设

机器读取 F1-D、F1-C、C5-C、C5-F、B16-E（可选 D5-A0、B16-D）的已提交
聚合 artifact，验证其 schema 与声明 flag，并提取数值聚合信号，可以
在不进行 provider 调用、不进行校准、不声明下游 utility、true E/S 校
准、方法 winner、外部基准性能、policy/default 或已校准模型的前提下，
产出确定性校准特征/bucket 记录与测量推荐。

### 实现备注

- **D5-A1 artifact**
  （`eval/d5a1_automated_calibration_feature_table.py`）：公开仅聚合特
  征表。导入 F1-D scanner 原语向后兼容（均未修改）。机器读取已提交聚
  合 artifact（**不是**研究日志或自由文档）。
- **必需输入**（缺失/schema 不匹配/status 不匹配/不安全声明 flag 时
  fail-closed）：F1-D、F1-C、C5-C、C5-F、B16-E。
- **可选输入**（仅在存在且 claim-safe 时包含；否则记录为
  `skipped_optional`，仅带聚合原因类别）：D5-A0、B16-D。
- **提取的信号**：检索稳健性（F1-D bm25_vs_empty、regex_vs_bm25、
  symbol_vs_bm25 retrieval_utility point/CI/sign stability）；外部基
  准一致/分歧（C5-C+C5-F bm25_positive_on_both、
  regex_symbol_negative_on_both、方法一致计数）；live provider delta
  （B16-E context_pack_signal_observed、solve_rate_delta、families
  positive/zero/negative）；可选 D5-A0 anchor 与 B16-D 次要 live 信号。
- **校准特征**（弱监督，**不是**已校准标签）：量级 bucket、符号稳定
  性 bucket、live provider delta bucket、family 分布 bucket、跨信号对
  齐标签。
- **跨信号对齐标签**（固定 allowlist）：
  `retrieval_robust_positive_plus_live_positive`、
  `retrieval_negative_methods_plus_live_not_supported`、
  `retrieval_only_insufficient`、`conflicting_signals`。
- **就绪 bucket**（固定 allowlist）：
  `ready_for_manual_review`、`needs_more_live_downstream`、
  `retrieval_only_insufficient`、`conflicting_signals`、
  `insufficient_signal`。
- **推荐的下一步测量**（仅测量，**不是** policy/default/method
  winner）：`manual_reference_audit`、`heldout_benchmark_scale`、
  `live_downstream_scale`。
- **Artifact 身份**：
  `schema_version=d5a1_automated_calibration_feature_table.v1`、
  `claim_level=automated_calibration_feature_extraction_only`、
  `mode=committed_aggregate_feature_extraction`、阶段 `D5-A1`。状态枚
  举：`automated_calibration_feature_table_pass`、
  `fail_input_contract`、`fail_forbidden_scan`。
- **安全 true flag**（仅当实际为 true 时）：
  `automated_calibration_feature_extraction_performed`、
  `aggregate_only_public_artifact`、`diagnostic_only`。
- **始终为 false 的 no-claim flag**：`true_e_s_calibration_claimed`、
  `automated_e_s_full_calibration_claimed`、
  `human_e_s_calibration_claimed`、`calibrated_model_claimed`、
  `policy_recommendation_claimed`、`method_winner_claimed`、
  `external_benchmark_performance_claimed`、
  `downstream_agent_value_proven`、`promotion_ready`、
  `default_should_change`、所有 runtime/retriever/pack/backend/
  default-policy/EvidenceCore 变更 flag、`provider_calls_made`、
  `remote_provider_calls_made`。
- **无 winner/best/recommended-default/calibrated-model/policy-
  recommendation 字段**。**无 E/S 校准记法**。**无 raw model/routing
  prefix**。**无 per-unit metric 数组、原始输入 artifact 路径/内容或
  B16 任务文本**。
- **Forbidden scanner（公开，fail-closed）**：组合 F1-D scanner（本身
  组合 F1-C/C5-A/C5-C/C5-E scanner 与 F1-D 特定检查）并添加 D5-A1 特定
  forbidden key（原始输入 artifact 路径/内容、校准声明 key、policy/
  default 推荐 key、原始 B16 任务文本/provider payload、per-unit metric
  数组 key）与 D5-A1 record-shape 检查（`input_artifact_records`、
  `signal_records`、`calibration_feature_records`、
  `readiness_bucket_records`、
  `recommended_next_measurement_records`）。

### 验证结果

```text
python3 -m py_compile eval/d5a1_automated_calibration_feature_table.py  => PASS
python3 eval/d5a1_automated_calibration_feature_table.py --self-test  => PASS (126/126 checks)
python3 eval/d5a1_automated_calibration_feature_table.py \
  --out artifacts/d5a1_automated_calibration_feature_table/\
d5a1_automated_calibration_feature_table_report.json  => PASS
  (status: automated_calibration_feature_table_pass,
   forbidden_scan: pass, self_test_passed: true,
   cross_signal_alignment: retrieval_robust_positive_plus_live_positive,
   readiness_bucket: ready_for_manual_review,
   signals: 9, features: 7, bucket_records: 5, measurements: 2,
   automated_calibration_feature_extraction_performed: true,
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
   evidencecore_semantics_changed: false,
   calibrated_model_claimed: false,
   policy_recommendation_claimed: false)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

本地特征提取 run 产生以下聚合记录：

```text
status: automated_calibration_feature_table_pass
forbidden_scan: pass
cross_signal_alignment: retrieval_robust_positive_plus_live_positive
readiness_bucket: ready_for_manual_review
input_artifact_records:
  F1-D: required=true, loaded=true, claim_safe=true, unit_count=30
  F1-C: required=true, loaded=true, claim_safe=true, unit_count=30
  C5-C: required=true, loaded=true, claim_safe=true, unit_count=20
  C5-F: required=true, loaded=true, claim_safe=true, unit_count=10
  B16-E: required=true, loaded=true, claim_safe=true, unit_count=16
  D5-A0: required=false, loaded=true, claim_safe=true, unit_count=4
  B16-D: required=false, loaded=true, claim_safe=true, unit_count=8
signal_records:
  bm25_vs_empty_retrieval_utility (F1-D): point=+0.465035, ci=[+0.298938, +0.464512, +0.624026], sign+=1.0, units=30
  regex_vs_bm25_retrieval_utility (F1-D): sign-=1.0, units=30
  symbol_vs_bm25_retrieval_utility (F1-D): sign-=1.0, units=30
  bm25_positive_on_both_benchmarks (C5-C+C5-F): bm25_positive_on_both=true
  regex_symbol_negative_on_both_benchmarks (C5-C+C5-F): regex_negative=true, symbol_negative=true
  benchmark_method_agreement (C5-C+C5-F): agree=3, disagree=0
  b16e_context_pack_signal (B16-E): solve_rate_delta=+0.875, families_positive=4
  d5a0_automated_calibration_smoke_anchor (D5-A0)
  b16d_secondary_live_signal (B16-D)
calibration_feature_records:
  bm25_vs_empty_retrieval_utility_magnitude: bucket=weak_positive, value=0.465035
  bm25_vs_empty_sign_stability: bucket=stable_positive, value=1.0
  regex_vs_bm25_sign_stability: bucket=stable_negative, value=1.0
  symbol_vs_bm25_sign_stability: bucket=stable_negative, value=1.0
  live_provider_solve_rate_delta: bucket=strong_positive, value=0.875
  live_provider_family_distribution: bucket=all_families_positive, value=4
  cross_signal_alignment: bucket=retrieval_robust_positive_plus_live_positive
readiness_bucket_records:
  ready_for_manual_review: count=1
  needs_more_live_downstream: count=0
  retrieval_only_insufficient: count=0
  conflicting_signals: count=0
  insufficient_signal: count=0
recommended_next_measurement_records:
  manual_reference_audit
  heldout_benchmark_scale
```

已提交 artifact 不包含原始 task/row/needle ID、repo URL、commit、
path/span/line range、source/snippet、prompt/response、provider
payload、per-unit metric 数组、B16 任务文本、私有标签、content hash、
candidate/evidence 行或 winner/best/default/calibrated-model/policy-
recommendation 字段。

D5-A1 是首个自动化校准特征表。它机器读取已提交聚合 artifact，提取
数值信号，并计算确定性校准特征/bucket 记录用于未来校准/人工审查。它
仅特征提取：它**不**声明校准、下游 utility、true E/S 校准、方法
winner、外部基准性能、正式置信区间、policy/default 推荐、
leaderboard 条目、promotion 或 default/policy/runtime/retriever/pack/
backend/EvidenceCore 语义变更。详见
[D5-A1 详细报告](d5a1-automated-calibration-feature-table.md)。

### 注意事项

- D5-A1 是公开仅聚合自动化校准特征表 artifact。它是 eval/diagnostic
  only。它**不**改变 runtime、retriever、pack、backend 或 default
  policy；它**不**改变 EvidenceCore 语义。它**不是**校准、**不是**已
  校准模型声明、**不是** policy/default 推荐、**不是** benchmark 结果、
  **不是**下游 utility、**不是** true E/S 校准、**不是**外部基准测试
  性能声明、**不是** leaderboard 条目、**不是**方法 winner、**也不
  是** promotion。
- D5-A1 机器读取已提交聚合 artifact。它**不**摘要研究日志或自由文档。
  它**不**重新运行任何检索或评分管线。
- D5-A1 **不**进行任何 provider 调用，**不**进行任何远程 provider 调
  用。所有输入数据从已提交聚合 artifact 读取（仅聚合计数与指标）。
- 特征是面向未来校准/人工审查的弱监督特征，**不是**已校准标签。就绪
  bucket 是诊断 bucket，**不是** promotion/default 门槛。
- 推荐的下一步测量仅测量。它们**不是** policy/default/method winner
  推荐。
- 所有无声明 / 无运行时变更标志保持 false；诊断标志保持 true；
  `automated_calibration_feature_extraction_performed=true` 仅在特征提
  取实际执行时。未修改任何 runtime/retriever/pack/model/backend/
  default-policy 文件；无 promotion/default/runtime 声明变更。

## 2026-06-21 — D5-A2 Heldout 特征验证 Smoke

### 目标

验证 D5-A1 的 retrieval-derived 特征 bucket 是否在新鲜的 heldout
外部检索样本上复现。D5-A2 必须运行新的 heldout 测量（ContextBench
行 21-40 + RepoQA needle 11-20），不重读现有 C5/F1 artifact。

### 实现备注

- **D5-A2 artifact**（`eval/d5a2_heldout_feature_validation.py`）：
  公开仅聚合 heldout 特征验证 smoke。加载 D5-A1 已提交 artifact 作为
  预注册特征源（缺失/schema 不匹配/不安全声明 flag 时 fail-closed）。
  运行新鲜 heldout ContextBench verified Python 行 21-40（抓取 40，
  评估切片 [20,40)）与 RepoQA Python needle 11-20（解析 20，评估切片
  [10,20)），方法 bm25/regex/symbol。向后兼容复用 C5-A/C5-C/C5-D/C5-E
  原语（均未修改）。计算相同固定 retrieval-derived utility proxy
  （与 F1-C/F1-D 不变）。
- **验证记录**（4 项检查）：bm25_vs_empty retrieval_utility 量级
  （正）；bm25_vs_empty 符号稳定性（两个基准 file_recall > 0）；
  regex_vs_bm25 符号稳定性（负）；symbol_vs_bm25 符号稳定性（负）。
- **验证结果**（固定 allowlist）：
  `retrieval_feature_validation_supported`、
  `retrieval_feature_validation_mixed`、
  `retrieval_feature_validation_not_supported`、
  `unavailable_with_reason`。
- **Artifact 身份**：
  `schema_version=d5a2_heldout_feature_validation.v1`、
  `claim_level=heldout_retrieval_feature_validation_smoke_only`、
  `mode=heldout_contextbench_repoqa_feature_validation`、阶段
  `D5-A2`。

### 验证结果

```text
python3 -m py_compile eval/d5a2_heldout_feature_validation.py  => PASS
python3 eval/d5a2_heldout_feature_validation.py --self-test  => PASS (811/118 checks)
python3 eval/d5a2_heldout_feature_validation.py \
  --contextbench-row-offset 20 --contextbench-row-limit 20 \
  --repoqa-needle-offset 10 --repoqa-needle-limit 10 \
  --methods bm25,regex,symbol \
  --out artifacts/d5a2_heldout_feature_validation/\
d5a2_heldout_feature_validation_report.json  => PASS
  (status: heldout_feature_validation_pass,
   forbidden_scan: pass, self_test_passed: true,
   validation_outcome: retrieval_feature_validation_supported,
   contextbench_rows_fetched: 20, repoqa_needles_seen: 10,
   network_calls: 2, provider_calls: 0,
   heldout_feature_validation_executed: true)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

手动 CI run `27915252367` 已通过，并上传 sanitized aggregate D5-A2 report。所有 4 个 D5-A1 检索特征在 heldout 数据上复现：
bm25_vs_empty_retrieval_utility_magnitude（heldout +0.727961，正，
supported）；bm25_vs_empty_sign_stability（heldout file_recall
+0.6，正，supported）；regex_vs_bm25_sign_stability（heldout
-0.977961，负，supported）；symbol_vs_bm25_sign_stability（heldout
-0.977961，负，supported）。heldout ContextBench bm25
file_recall@10=0.7（对比原始 D5-A1 行 1-20 的 0.35）支持 bm25 正向
检索特征在此 heldout 切片上成立。

详见 [D5-A2 详细报告](d5a2-heldout-feature-validation.md)。

### 注意事项

- D5-A2 是 heldout 仅聚合特征验证 smoke，**不是**校准，**不是**
  policy/default，**不是**方法 winner，**不是** benchmark 性能，**不
  是**下游价值，**不是** runtime/retriever/pack/backend/default-policy/
  EvidenceCore 变更。
- D5-A2 仅验证 D5-A1 的检索特征稳定性；它 **不**验证 live-provider/
  下游对齐。
- D5-A2 运行新鲜 heldout 检索；它 **不**重读 C5/F1 artifact。无
  provider 调用。所有临时数据在内存或 /tmp。

## 2026-06-21 — BEA-0 Budgeted Evidence Acquisition v0

### 目标

从 readiness/control-plane/aggregate-validation 工作转向一个真正的算法级
检索/采集实验，并保留私有 per-record SCORE 轨迹。BEA-0 实现并运行一个
确定性 budgeted 采集策略，对全新 external benchmark 数据重新运行，将私有
per-record SCORE JSONL 保留在 `/tmp`（绝不提交、绝不上传），仅公开聚合的
baseline-vs-treatment delta。

### 设计（specialist 审查）

- @explorer 映射 BEA/retrieval/logging 入口：
  `eval/run_retrieval.py:run_query()`（真实 per-row 检索原语，覆盖
  `regex`/`text`/`bm25`/`symbol`/`rrf`，通过 OpenLocus CLI），
  `eval/score.py`（per-row 评分函数，可作为模块导入），
  `eval/c5_contextbench_verified_performance_smoke.py` 和
  `eval/c5d_repoqa_bm25_retrieval_smoke.py`（真实 fetch/clone/retrieve/score
  harness，含 forbidden 扫描器和 license 字段），以及
  `eval/c3_budgeted_evidence_acquisition.py`（仅 replay；从预计算 P21
  outcomes 中选择，不采集新证据；不充分）。
- @oracle 批准 BEA-0 仅当它是一个真正算法级检索/采集实验且含私有 SCORE
  轨迹时，而非 aggregate validation wrapper。

### 范围

- Phase：`BEA-0`。
- 数据：全新 ContextBench verified Python 行（默认 10；硬上限 20）和
  RepoQA Python needle（默认 5；硬上限 10）。
- 方法：`bm25`、`regex`、`symbol`；可选 `rrf`（如便宜）。
- Baseline：`bm25_top10`；启用 rrf 时为 `rrf_bm25_regex_symbol_top10`。
- Treatment：`bea_v0_budgeted` 确定性策略，在证据预算下（默认 10；硬上限
  20）。
- 无 provider 调用。无 runtime/retriever/default 变更。

### BEA v0 策略（runtime-clean，确定性）

Treatment 策略 `bea_v0_budgeted` 只消费在评分前可用的 runtime-clean 候选
特征：method source、候选在 method 内的 rank、score 或 normalized
score（如可用）、跨 method 的 rank agreement（多少个不同 method 返回同一
`(path, start_line, end_line)` span）、重复 path/span overlap、候选总数、
已接受 file/path 覆盖、剩余预算，以及廉价 path kind/file extension 元数据。
不得使用 gold files/lines/labels、row IDs、benchmark 专属 answer hints、
同一记录的 previous outcome、provider/model 名、或私有 route buckets。

算法：(1) 计算每 span 的 agreement；(2) 对去重 span 按
（agreement DESC, min_rank ASC, max_norm_score DESC）排序；(3) 在预算下
迭代，emit `accept_candidate` / `skip_low_support` / `rerank_by_agreement`
/ `stop_budget_exhausted` action；(4) 可选 `expand_same_file` 处理 deferred
rerank 池（预算剩余时）。

### 私有 SCORE JSONL

每条 evaluated record 必需。仅写入 `/tmp`（或显式忽略的私有路径，位于被
gitignore 的 `runs/` 目录下）。绝不提交，绝不上传。私有 SCORE 路径绝不
序列化到公开 artifact、docs 或 CI artifact。

私有行内容：`phase_run_id`、`benchmark`、`private_record_id`、
`runtime_query_feature_summary`（仅 runtime-clean 特征）、`candidate_list`
（每候选：method、rank、score、normalized_score、path、start_line、
end_line、content_sha、extension、agreement）、`action_trace`（step、
action、candidate_method、candidate_rank、agreement、max_norm_score）、
`budget_states`（step、budget_remaining、accepted_so_far、candidate_count）、
`accepted_candidates`、`final_candidates`、
`baseline_bm25_top10_evidence`、`baseline_rrf_top10_evidence`、
`score_outcome`（per-arm 指标）、`latency_ms`、`cost_usd=0.0`、`tokens=0`、
`provider_calls=0`、`failure_reason`、`method_latencies_ms`、
`rrf_latency_ms`、`method_errors`、`rrf_error`。

### 公开 artifact

目标路径：
`artifacts/bea0_budgeted_evidence_acquisition/bea0_budgeted_evidence_acquisition_report.json`。

仅聚合计：`schema_version`、`generated_by`、`generated_at`、
`claim_level`、`status`、`mode`、`phase`、`methods`、`budget`、
`enable_rrf_baseline`、`baseline_arms`、`treatment_arm`、`network_mode`、
`openlocus_binary_source`、`contextbench_row_limit_requested`、
`repoqa_needle_limit_requested`、`records_evaluated`、`records_successful`、
`records_failed`、`network_calls`、`provider_calls=0`、`arm_metrics`（per-arm
allowlisted 指标）、`deltas`（per-arm baseline-vs-treatment allowlisted
delta）、私有 SCORE manifest aggregate-only 字段
（`private_score_records_written`、`private_score_record_count`、
`private_score_schema_version`、`private_score_manifest_hash`、
`private_score_storage_class`、`private_score_path_publicly_serialized=false`）、
`aggregate_runtime_seconds`、`failure_category_counts`、safe true flag、
no-claim / no-runtime-change false flag、license 字段、`self_test_passed`、
`framing`、`forbidden_scan` 摘要。

禁止公开值：repo URL/name、commit、row/needle ID、query/description、
path/span/line range、source/snippet、candidate list、evidence row、
content hash、私有 SCORE 路径、provider payload、stdout/stderr、clone 路径、
gold label、action trace、budget state、accepted candidate、final
candidate、score outcome。

### Claim 边界

允许的 claim：BEA-0 度量确定性 budgeted 采集策略在有界 real
ContextBench/RepoQA 样本上的聚合检索/采集质量与预算 delta。

不允许：benchmark 性能、leaderboard、downstream-agent 价值、calibration、
method winner、default/promotion、runtime/retriever/backend 变更、
EvidenceCore 语义变更。Candidate 仍非事实；EvidenceCore 语义不变。

### 指标

Per arm 聚合：`file_recall@10`、`mrr`、`span_f0.5@10`、`success_rate`、
`candidate_count_read`、`evidence_budget_used`、`action_steps`、
`latency_seconds`、`quality_per_candidate`。聚合 delta vs `bm25_top10`
（启用 rrf 时还包括 vs `rrf_bm25_regex_symbol_top10`）。

有效结果可为 improvement、相同质量但更少预算、no-delta、或质量损失但含
causal action-trace 失败模式。

### 验证结果

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
   private_score_storage_class: tmp_private,
   private_score_path_publicly_serialized: false)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

### 真实有界手动 CI run `27934507148`结果（2026-06-21）

有界手动 CI run `27934507148`（ContextBench 2 行 + RepoQA 1 needle，budget=5，方法
bm25/regex/symbol，必需并启用 rrf baseline）成功完成：

- `arm_metric_records` arm=`bm25_top10`: file_recall@10=0.666667, mrr=0.666667,
  span_f0.5@10=0.059187, success_rate=0.666667,
  candidate_count_read=13.333333, evidence_budget_used=6.666667,
  action_steps=6.666667, latency_seconds=0.444333,
  quality_per_candidate=0.002959。
- `arm_metric_records` arm=`rrf_bm25_regex_symbol_top10`: file_recall@10=0.666667,
  mrr=0.666667, span_f0.5@10=0.059187, success_rate=0.666667,
  candidate_count_read=13.333333, evidence_budget_used=6.666667,
  action_steps=6.666667, latency_seconds=1.314,
  quality_per_candidate=0.002959。
- `arm_metric_records` arm=`bea_v0_budgeted`: file_recall@10=0.666667, mrr=0.666667,
  span_f0.5@10=0.086849, success_rate=0.666667,
  candidate_count_read=13.333333, evidence_budget_used=3.333333,
  action_steps=4.0, latency_seconds=4.253045,
  quality_per_candidate=0.004343。
- `delta_records` treatment_arm=`bea_v0_budgeted`（vs `bm25_top10`）: file_recall@10=0.0,
  mrr=0.0, span_f0.5@10=+0.027662, success_rate=0.0,
  evidence_budget_used=-3.333334, action_steps=-2.666667,
  quality_per_candidate=+0.001384, latency_seconds=+3.808712,
  candidate_count_read=0.0。
- `aggregate_runtime_seconds`: 25.65。

Treatment 在使用约一半 evidence budget（`evidence_budget_used=3.33` vs
`6.67`）的情况下，与两条 baseline 保持 file_recall@10 / mrr /
success_rate 持平，并将 `span_f0.5@10` 提升 `+0.028`、
`quality_per_candidate` 提升 `+0.0014`。3 行私有 per-record SCORE JSONL
写入 `/tmp/bea0_private_score_<pid>_<ts>/bea0.private.jsonl`（transient；
绝不提交或上传）。

### Caveats

- BEA-0 是公开 aggregate-only budgeted evidence acquisition v0 smoke
  artifact。它是 eval/diagnostic only。它不更改 runtime、retriever、
  pack、backend 或 default policy；它不更改 EvidenceCore 语义。它不是
  benchmark 结果、不是 leaderboard 条目、不是性能声明、不是
  method-winner 声明、不是 calibration 声明、不是 promotion、不是
  default 变更、不是 runtime-clean general algorithm 声明、且不是
  downstream agent 价值声明。
- BEA-0 不输出 `winner`、`best_method`、`recommended_default`、
  `method_winner`、`calibration`，或任何暗示 policy/default 决策的字段。
- BEA-0 不运行 provider 调用，也不运行 remote provider 调用。
  `provider_calls=0`、`provider_calls_made=false`、
  `remote_provider_calls_made=false`。
- BEA-0 使用有界 ContextBench verified Python 行（默认 10；硬上限 20）和
  有界 RepoQA Python needle（默认 5；硬上限 10）。这是 smoke，不是严格
  benchmark 评估。聚合指标为有界样本上的点估计。
- BEA-0 仅在 `/tmp`（或显式忽略的私有路径，位于被 gitignore 的 `runs/`
  目录下）写入私有 per-record SCORE JSONL。私有 SCORE 路径绝不序列化到
  公开 artifact、docs 或 CI artifact。
- BEA-0 不会从 Python 静默回退到所有语言。
- BEA-0 不声明 external benchmark 性能、method-winner 或 calibration。
  聚合指标为 smoke 级 diagnostic。
- BEA-0 不证明 downstream agent 价值。采集 smoke 不演练任何 downstream
  agent。
- 所有 no-claim / no-runtime-change flag 保持 false；diagnostic flag
  （`aggregate_only_public_artifact`、`diagnostic_only`）保持 true。
  未修改任何 runtime/retriever/pack/model/backend/default-policy 文件；
  无 promotion/default/runtime claim 变更。EvidenceCore 语义不变。

## 2026-06-21 — BEA-1 Mechanism Ablation Smoke

### 目标

将 BEA-0 转为一个小型真实机制消融。对全新有界 external ContextBench +
RepoQA 检索，保留私有 per-record SCORE JSONL 于 `/tmp`，并在同一组记录上
将 BEA v0 与机制特定控制进行对比。公开输出仍为 records 形态的仅聚合。

### 设计（specialist 审查）

- @oracle plan 审查 No-Go（初始 BEA-1 草稿）；计划收紧为确切的
  same-budget `K`、arm 算法、paired denominator 规则、对比 record 形态、
  私有 SCORE manifest 形态，以及更严格的 CI gate。
- BEA-1 通过直接模块导入复用 BEA-0 原语（候选规范化、BEA v0 策略、扫描器、
  私有 SCORE writer、arm 指标）。无新 runtime/retriever/default 变更。

### 范围

- Phase：`BEA-1`。
- Fresh external run；不 bootstrap BEA-0 聚合 artifact。
- 默认有界样本：ContextBench 5 行 + RepoQA 3 needle。
- 硬上限：ContextBench 20 行，RepoQA 10 needle。
- 方法：`bm25,regex,symbol`；可选 RRF baseline。
- 证据预算默认：5；硬上限 20。
- 无 provider 调用。
- 仅手动 external-network CI。

### Arm（固定；无动态 arm 名）

- `bm25_top10`：正常 BM25 top-10 baseline。
- `rrf_bm25_regex_symbol_top10`：启用时的多方法 RRF baseline。
- `bea_v0_budgeted`：BEA-0 确定性策略，仅 runtime-clean 特征；仅将私有
  action trace 记录到 SCORE。
- `same_budget_bm25_prefix`：去重后前 `K` 个 BM25 候选；无 agreement
  reranking，无 BEA 序贯 coverage/defer/expand 规则。
- `agreement_only_same_budget`：与 BEA 相同的去重候选宇宙；按 agreement
  desc、min_rank asc、max_normalized_score desc、稳定候选顺序排序；取前
  `K`；无 BEA 序贯 coverage/defer/expand 规则。
- `seeded_random_same_budget`：确定性 PRNG，固定公开种子 `20240621`；从
  稳定排序后相同的去重候选宇宙中采样 `K`；种子或排序中无
  gold/labels/row IDs/provider/model 字段。

这些 arm 回答 BEA-0 的增益是否来自多源 agreement / 序贯预算采集，而非
仅仅是读取更少候选。

### 同预算定义

```text
K = len(bea_v0_budgeted.accepted_candidates)
K = min(K, available_deduped_candidate_count)
```

若 BEA 对某条记录接受零候选，同预算控制也选择零，且该记录在机制对比中
标记为不可用，除非所有固定 arm 均有有效的零候选指标。公开产物绝不序列化
accepted candidates 或 candidate lists；仅聚合 arm/对比 records 公开。

### Paired denominator 规则

机制对比是 paired 的。一条对比仅包含 baseline 和 treatment arm 在同一
记录上均有有效指标的记录。若任一固定机制 arm 对某条记录失败，则从每条
机制对比中排除该记录，并增加 `paired_exclusion_count`（以及
`record_excluded_from_paired_denominator` failure category），或若排除
导致低于最小 paired 计数，则将运行标记为 `partial`。每条公开
`mechanism_contrast_records` 行必须包含 `record_count`，以便 delta 可
解释。

### Claim 边界

BEA-1 是机制消融 smoke。不声明 benchmark 性能、leaderboard、method
winner/default 推荐、calibration、downstream-agent 价值证明、promotion、
runtime/retriever/pack/backend/default-policy 变更，或 EvidenceCore 语义
变更。

必需 false flag：`external_benchmark_performance_claimed`、
`leaderboard_entry_claimed`、`method_winner_claimed`、
`calibration_claimed`、`downstream_agent_value_proven`、
`promotion_ready`、`default_should_change`，所有
runtime/retriever/pack/backend/default/EvidenceCore 变更 flag，以及
provider 调用 flag。

允许 true flag（若确实为 true）：`mechanism_ablation_performed`、
`bea_v0_acquisition_performed`、`private_score_records_written`、
`external_benchmark_rows_read`、`openlocus_retrieval_executed`、
`score_py_metrics_computed`、`aggregate_only_public_artifact`、
`diagnostic_only`。

### Artifact 身份

- `schema_version`：`bea1_mechanism_ablation.v1`
- `claim_level`：`bea_v0_mechanism_ablation_smoke_only`
- `status`：`bea1_mechanism_ablation_pass` | `partial` |
  `unavailable_with_reason` | `fail_forbidden_scan` | `fail_schema_contract`
- `mode`：`bounded_external_retrieval_mechanism_ablation`
- `phase`：`BEA-1`

### 公开 artifact 形态（仅 records）

- `arm_metric_records`：每 arm/metric 一条 `{arm, metric, value}` record。
- `delta_records`：每 treatment/metric 一条
  `{baseline_arm, treatment_arm, metric, delta}`（每条 treatment arm vs 固定
  `bm25_top10` baseline）。
- `mechanism_contrast_records`：固定形态
  `{contrast, baseline_arm, treatment_arm, metric, delta, record_count}`，
  对 `bea_vs_same_budget_bm25`、`bea_vs_agreement_only`、
  `bea_vs_seeded_random`（BEA v0 vs 每个同预算控制，在 paired denominator
  上）。
- `private_score_manifest`：aggregate-only manifest 块，含
  `records_written`、`record_count`、`schema_version`、`manifest_hash`、
  `storage_class`、`path_publicly_serialized=false`。

允许的指标：`file_recall@10`、`mrr`、`span_f0.5@10`、`success_rate`、
`candidate_count_read`、`evidence_budget_used`、`action_steps`、
`latency_seconds`、`quality_per_candidate`。

禁止公开：queries、repo URL/name、commit、path、span、content、candidate
list、action trace、accepted candidate、budget state、per-record 指标、
SCORE 行、私有 SCORE 路径、row/needle ID、content hash、provider 字段、
winner/best/default label、calibration label。

### 验证结果

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
   private_score_manifest.path_publicly_serialized: false)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

## 2026-06-21 — BEA-2 Policy v0.2 Diversity/Risk 机制消融 Smoke

### 目标

实现并测试真正的 BEA v0.2 算法变更。BEA-1 表明 BEA v0 与同预算
BM25/agreement-only 持平，仅胜过 seeded random。BEA-2 测试确定性
gold-free diversity/risk-aware 采集策略能否在全新 heldout external 记录上
超越 v0 和同预算控制。

### 全新 heldout 切片

- ContextBench verified Python 行 offset 40、limit 20。
- RepoQA Python needle offset 20、limit 10。

### BEA v0.2 策略（runtime-clean，确定性）

优先级分数 = WEIGHT_AGREEMENT(0.30) × agreement_norm +
WEIGHT_BM25_NORM(0.20) × bm25_norm + WEIGHT_DIVERSITY(0.20) × diversity +
WEIGHT_QUERY_PATH_OVERLAP(0.15) × query_path_overlap +
WEIGHT_RISK_PENALTY(-0.25) × risk_penalty +
WEIGHT_DUPLICATION_PENALTY(-0.30) × duplication_penalty。

冻结权重（不从 outcomes 调优）。按优先级降序在预算下贪心选择，每次选择
后重新计算优先级。

### 固定策略 arm

- `bm25_prefix_same_budget`、`agreement_only_same_budget`、`bea_v0`、
  `bea_v0_2_diversity_risk`、`seeded_random_same_budget`；可选
  `rrf_same_budget`。

### 验证结果

```text
python3 -m py_compile eval/bea2_policy_v02.py  => PASS
python3 eval/bea2_policy_v02.py --self-test  => PASS (321/321 checks)
python3 eval/bea2_policy_v02.py \
  --enable-external-benchmark-network \
  --contextbench-row-offset 40 --contextbench-row-limit 3 \
  --repoqa-needle-offset 20 --repoqa-needle-limit 2 \
  --budget 5 --methods bm25,regex,symbol --enable-rrf-baseline \
  --out artifacts/bea2_policy_v02/bea2_policy_v02_report.json  => PASS
  (status: bea2_policy_v02_pass, 5 records successful,
   private_score_manifest.record_count=30 (5×6 arms),
   private_score_storage_class=tmp_private,
   private_score_path_publicly_serialized=false,
   provider_calls=0, forbidden_scan=pass)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

### 手动 CI 结果（2026-06-21）

手动 CI run `27938484585`（2026-06-21）已通过：ContextBench offset 40 limit 20 + RepoQA offset 20 limit 10，budget=5，方法 bm25/regex/symbol，启用 RRF baseline。30 条记录成功；`paired_exclusion_count=0`；forbidden scan pass；`provider_calls=0`；`private_score_manifest.record_count=180`（30 条记录 × 6 arm）；`private_score_manifest.storage_class=tmp_private`；`private_score_manifest.path_publicly_serialized=false`；`aggregate_runtime_seconds=386.3`。BEA v0.2 相对 BEA v0 / same-budget BM25 / agreement-only / RRF：`file_recall@10` delta=+0.033334，`mrr` delta=+0.081667，`span_f0.5@10` delta=-0.012947，`success_rate` delta=+0.033334，`latency_seconds` delta=+8.188547，`evidence_budget_used` delta=0.0。Win/tie/loss（v0.2 vs v0，n=30）：file_recall@10 win=3 tie=25 loss=2；mrr win=7 tie=21 loss=2；span_f0.5@10 win=0 tie=28 loss=2；success_rate win=3 tie=25 loss=2。相对 seeded random，v0.2 的正向 delta 更强（`file_recall@10` +0.233334，`mrr` +0.326667，`span_f0.5@10` +0.019687，`success_rate` +0.233334）。这是 mixed smoke-level 机制结果，不是 method-winner/default/performance/calibration 声明。

### Caveats

- BEA-2 是 eval/diagnostic only。不是 benchmark/leaderboard/performance/
  method-winner/calibration/promotion/default/runtime/EvidenceCore/
  downstream-value 声明。
- v0.2 优先级权重为冻结常量，不从 outcomes 调优。
- 有界 CI 样本（30 条记录）。smoke，非严格评估。
- 所有 no-claim / no-runtime-change flag 为 false；EvidenceCore 语义不变。

## 2026-06-21 — BEA-3 Anchor/Span/Latency-Aware 策略 Smoke

### 目标

测试冻结 BEA v0.3 算法策略，针对 BEA-2 的混合结果：保持 file/MRR/success
增益的同时减少 span_f0.5 和 latency 回归。

### v0.3 冻结策略

`bea_v0_3_anchor_span_latency`：为 BM25/agreement anchor 预留
`anchor_count=min(2,budget)` slot；对剩余预算应用 diversity/risk 评分；
添加 span/latency 代理（更紧 line-span bonus、same-file-as-anchor 支持
bonus、风险惩罚、weak-support 惩罚、边际优先级 early stop）。冻结权重：
anchor=0.35、span_tight=0.15、anchor_file_support=0.10、
weak_support_penalty=-0.20、early_stop_margin=0.05。不从 outcomes 调优。

消融：`v0_3_no_anchor`、`v0_3_no_early_stop`。

### 全新 primary 切片

ContextBench offset 60、limit 20。RepoQA offset 30、limit 10。

### 必需 arm

v0.3、v0.3_no_anchor、v0.3_no_early_stop、v0.2、v0、bm25_prefix、
agreement_only、seeded_random、rrf_same_budget（可用时）。

### 验证结果

```text
python3 -m py_compile eval/bea3_anchor_span_latency.py  => PASS
python3 eval/bea3_anchor_span_latency.py --self-test  => PASS (225/225 checks)
python3 eval/bea3_anchor_span_latency.py \
  --enable-external-benchmark-network \
  --contextbench-row-offset 60 --contextbench-row-limit 3 \
  --repoqa-needle-offset 30 --repoqa-needle-limit 2 \
  --budget 5 --methods bm25,regex,symbol --enable-rrf-baseline \
  --out artifacts/bea3_anchor_span_latency/bea3_anchor_span_latency_report.json  => PASS
  (status: bea3_anchor_span_latency_pass, 5 records successful,
   private_score_manifest.record_count=45 (5×9 arms),
   private_score_storage_class=tmp_private,
   private_score_path_publicly_serialized=false,
   provider_calls=0, forbidden_scan=pass)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

### 手动 CI 结果（run `27942492278`，2026-06-21）

fixed CI run `27942492278` 已通过；它是在补上必需的 v0.3-vs-v0.2
`delta_records` 验证后得到的结果。较早 green run `27941717490` 因公开 delta
surface 不完整，不作为结果 artifact。

30 条记录成功（ContextBench 20 + RepoQA 10）。270 行私有 SCORE
（30 × 9 arm）。`forbidden_scan=pass`、`provider_calls=0`、
`private_score_manifest.record_count=270`、`path_publicly_serialized=false`、
`aggregate_runtime_seconds=398.532`。

在 30-record CI slice 上，BEA v0.3 相对 BEA v0.2：

```text
file_recall@10 delta: 0.0        (win=0, tie=30, loss=0)
mrr delta: 0.0                   (win=0, tie=30, loss=0)
span_f0.5@10 delta: +0.00217     (win=1, tie=29, loss=0)
success_rate delta: 0.0          (win=0, tie=30, loss=0)
latency_seconds delta: +0.001098
evidence_budget_used delta: 0.0
quality_per_latency delta: +0.000292
```

同一切片上，BEA v0.3 相对 BEA v0 / same-budget BM25 / agreement-only / RRF：
file_recall@10 +0.066667、mrr +0.130556、success_rate +0.066667、
span_f0.5@10 -0.010068。相对 seeded random：file_recall@10 +0.2、mrr
+0.231667、span_f0.5@10 +0.015826、success_rate +0.2。

机制摘要：anchor_used_rate=1.0、early_stop_rate=0.0、
mean_budget_used=4.333333、mean_latency_seconds=8.7516、
mean_span_extent=4.246667。

解释：v0.3 在该切片上并没有相对 v0.2 实质改善 file/MRR/success；它只给出
极小的 span/quality-per-latency 正向信号，latency 基本相同。这是 weak/mixed
smoke 结果，不是 method winner 或 default-policy 声明。

### Caveats

- BEA-3 是 eval/diagnostic only。不是 benchmark/leaderboard/performance/
  method-winner/calibration/promotion/default/runtime/EvidenceCore/
  downstream-value 声明。
- v0.3 权重为冻结常量，不从 outcomes 调优。
- 有界 CI 样本（30 条记录）。smoke，非严格评估。
- v0.3 在 file/MRR/success 上与 v0.2 基本持平，只出现极小的
  span/quality-per-latency 正向信号。
- BEA-0/BEA-1/BEA-2 语义未修改。

## 2026-06-21 — B16-F BEA-Derived Context Pack Live-Provider Paired Smoke

### 目标

运行第一个下游 live-provider paired smoke，将 BEA v0.3-derived
context pack 与 same-budget BM25 context-pack 对照（以及 sparse 对照）
在有界合成 coding 任务上进行比较。这直接回应 deep-research 指令的缺口：
BEA 检索侧指标不够；BEA 必须在 live coding-agent 行为上测试。主对比为
BEA v0.3 context pack vs same-budget BM25 context pack，而非仅仅 BEA vs
sparse。

### 范围

- 阶段：`B16-F`。
- Evaluator：`eval/b16f_bea_derived_context_pack_paired_smoke.py`。
- Artifact：
  `artifacts/b16f_bea_derived_context_pack_paired_smoke/b16f_bea_derived_context_pack_paired_smoke_report.json`。
- 文档：
  `docs/en/b16f-bea-derived-context-pack-paired-smoke.md` 和 zh 镜像。
- `.github/workflows/real-provider-benchmark.yml` 中的 workflow stage：
  `b16f_bea_derived_context_pack_paired_smoke`。
- 仅手动 real-provider workflow；本地/no-env 模式真实阻断。
- 默认：8 合成任务 x 3 arms = 24 次 live provider 调用。

### Arms

1. `control_sparse`：仅任务 issue，最小 context。
2. `bm25_same_budget_context_pack`：same-budget BM25 prefix pack。
3. `bea_v03_context_pack`：冻结 BEA v0.3 anchor/span/latency 选中 pack。

主公开 paired delta：BEA 减 same-budget BM25。次 delta：BEA 减 sparse
与 BM25 减 sparse。

### 任务族

八个固定公开族标签：`same_symbol_support_relation`、
`operation_ambiguity`、`boundary_condition`、
`helper_dependency_choice`、`config_or_test_mismatch`、
`distractor_file`、`nearby_wrong_function`、`cross_file_symbol`。公开
artifact 仅包含族聚合计数，绝不包含 raw task text。

### Context-pack 生成

对于每个合成工作区，B16-F 构造 runtime-clean 候选特征（method source、
rank、score/normalized score、agreement count、span extent、path）。BM25
选择 same-budget BM25 prefix；BEA 应用冻结 v0.3，仅使用 runtime 可用特征。
BEA selector **绝不**读取 gold paths/lines/labels、`correct_value`、
task_family decisive cue 或任何私有答案。候选路径、片段、BEA/BM25 action
trace、budget trace、pack composition、prompt、response、patch 和测试输出
仅在 `/tmp` 下私有。

### 私有 artifact

对于每个 task x arm，B16-F 写入私有 SCORE JSONL（候选特征、BEA action/
budget trace、选中候选、score outcome）和私有 event JSONL（prompt、
response、parsed action、patch、test stdout/stderr、provider metadata），
仅 `/tmp` 下。公开 artifact 仅包含 `private_score_manifest` 和
`private_event_manifest`，含 record count、schema 版本、
`storage_class=tmp_private`、`path_publicly_serialized=false` 和 manifest
hash。

### 公开 artifact 形状

仅聚合 record 的公开 artifact：`schema_version`、`generated_by`、
`generated_at`、`claim_level`、`status`、`mode`、`phase`、
`model_display_category`、`input_summary`、`arm_results`（per-arm 聚合
metrics）、`paired_deltas`（3 对比：BEA-vs-BM25 主、BEA-vs-sparse、
BM25-vs-sparse）、`task_family_results`、`family_signal_summary`、
`honest_signals`、`private_score_manifest`、`private_event_manifest`、
`forbidden_scan`、no-claim/no-runtime-change flag、`self_test_checks_total`、
`self_test_checks_passed` 与 `self_test_passed`。无 raw task text、prompt、response、
patch、path、片段、候选特征、BEA action trace、pack composition、provider
payload、私有 path 或 per-task 结果。

### 声明边界

B16-F 仅为 live-provider 下游 paired smoke。它不是下游 agent 价值证明、
method winner、基准性能、default/promotion/runtime/EvidenceCore 改动或
calibration。文档标明仅为 smoke；负/平结果可接受。

### 验证结果

```text
python3 -m py_compile eval/b16f_bea_derived_context_pack_paired_smoke.py  => PASS
python3 eval/b16f_bea_derived_context_pack_paired_smoke.py --self-test  => PASS (352/352 checks)
python3 eval/b16f_bea_derived_context_pack_paired_smoke.py \
  --out artifacts/b16f_bea_derived_context_pack_paired_smoke/\
b16f_bea_derived_context_pack_paired_smoke_report.json  => PASS
  (status: blocked_remote_not_enabled,
   forbidden_scan: pass, self_test_passed: true,
   mode: public_aggregate_synthetic_task_family_matrix, phase: B16-F,
   model_display_category: unavailable,
   live_llm_agent: false, provider_calls_made: false,
   paired_run_executed: false,
   bea_v03_context_pack_executed: false,
   bm25_same_budget_context_pack_executed: false,
   private_score_records_written: false,
   private_event_records_written: false,
   downstream_agent_value_proven: false, promotion_ready: false,
   method_winner_claimed: false, calibration_claimed: false)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

本地 no-env 验证路径真实且 blocked/unavailable。

### 手动 CI 结果

手动 real-provider CI run `27945253824` 已通过。已提交 artifact 现在镜像该 run 的 sanitized aggregate report：8 个合成任务 x 3 arms = 24 次 live provider calls，`model_display_category=Kimi-K2.7-Code`，forbidden scan pass，352/352 self-test checks，`private_score_manifest.record_count=24`、`private_event_manifest.record_count=24`，两个 manifest 均为 `storage_class=tmp_private` 且 `path_publicly_serialized=false`。Sparse control 解出 2/8（`solve_rate=0.25`、`tests_pass_rate=0.25`、`latency_seconds_mean=13.4355`）；same-budget BM25 context pack 解出 11/11（`solve_rate=1.0`、`tests_pass_rate=1.0`、`latency_seconds_mean=1.1885`）；BEA v0.3 context pack 也解出 11/11（`solve_rate=1.0`、`tests_pass_rate=1.0`、`latency_seconds_mean=1.579`）。主对比 BEA-vs-BM25：solve/test/wrong-file/edit-validity delta 均为 0.0，`latency_seconds_mean` delta +0.3905，prompt tokens +161，completion tokens +47。相对 sparse 的次级 delta：两个 context arms 的 solve/test 均为 +0.75。解释：B16-F 在此有界合成 live-provider 切片上显示 context pack 相对 sparse 有收益，但 BEA v0.3 未优于 same-budget BM25；primary contrast 的 `context_pack_signal_observed=false`。这是下游 live-provider smoke 结果，不是下游价值证明、不是 method-winner/default/performance/calibration 声明。

### Caveats

- B16-F 是 eval/diagnostic only。不是 benchmark/leaderboard/performance/
  method-winner/calibration/promotion/default/runtime/EvidenceCore/
  downstream-value 声明。
- BEA v0.3 冻结策略权重为常量，不从 outcomes 调优。
- BEA selector 仅使用 runtime-clean 候选特征；通过 self-test 中的
  gold-tainting 不变量验证。
- 有界合成样本（默认 8 任务 x 3 arms）。smoke，非严格评估。
- 所有 no-claim / no-runtime-change flag 为 false；EvidenceCore 语义未改。
- BEA-0/BEA-1/BEA-2/BEA-3 语义未修改。

## 2026-06-21 — B16-G Context-Pack Atom Ablation Live-Provider Smoke

### 目标

解释 B16-F 的下游 tie：context pack 优于 sparse，但 BEA v0.3 并未优于
same-budget BM25。B16-G 运行 live-provider atom ablation，以识别
target-file cue、decisive support cue、distractor cue 或其组合是否驱动
解决。

### 前序结果

B16-F 结果 checkpoint `f58ce0f`，手动 CI run `27945253824`：8 合成任务 x
3 arms = 24 live 调用。Sparse solve/test=0.25，same-budget BM25 context
solve/test=1.0，BEA v0.3 context solve/test=1.0。BEA-vs-BM25 主 delta 在
solve/test/wrong-file/edit-validity 上为 0.0；BEA latency +0.3905s 且
额外 token。解释：context pack 优于 sparse，但 BEA 未优于 same-budget
BM25。

### 范围

- 阶段：`B16-G`。
- Evaluator：`eval/b16g_context_pack_atom_ablation.py`。
- Artifact：
  `artifacts/b16g_context_pack_atom_ablation/b16g_context_pack_atom_ablation_report.json`。
- 文档：`docs/en/b16g-context-pack-atom-ablation.md` 和 zh 镜像。
- `.github/workflows/real-provider-benchmark.yml` 中的 workflow stage：
  `b16g_context_pack_atom_ablation`。
- 仅手动 real-provider workflow；本地/no-env 模式真实阻断。
- 默认：8 合成任务 x 5 arms = 40 次 live provider 调用。

### Arms

1. `control_sparse`：仅任务 issue，最小 context；无 atom。
2. `target_only`：target file cue + target symbol cue；无 support，无
   decisive cue。
3. `support_only`：support module cue + decisive cue；无 target file/
   symbol cue。
4. `distractor_plus_support`：distractor file cue + support module cue
   + decisive cue；无 target file；wrong-file cue。
5. `target_plus_support`：target file cue + target symbol cue + support
   module cue + decisive cue（full pack）。

主对比：`target_plus_support` vs `distractor_plus_support`；
`target_plus_support` vs `support_only`；`target_only` vs
`support_only`。次对比：每个 context arm vs `control_sparse`。

### 机制摘要 record

仅聚合 record 字段：`support_atom_sufficient_count`、
`target_atom_required_count`、`distractor_hurts_count`、
`all_arms_solved_count`、`sparse_solved_count`。

### 私有 artifact

对于每个 task x arm，B16-G 写入私有 SCORE JSONL（atom composition、score
outcome）和私有 event JSONL（prompt、response、parsed action、patch、
test stdout/stderr、provider metadata），仅 `/tmp` 下。公开 artifact 仅
包含聚合 manifest，含 record count、schema 版本、
`storage_class=tmp_private`、`path_publicly_serialized=false` 和 manifest
hash。

### 公开 artifact 形状

仅聚合 record 的公开 artifact：`schema_version`、`generated_by`、
`generated_at`、`claim_level`、`status`、`mode`、`phase`、
`model_display_category`、`input_summary`、`arm_results`（per-arm 聚合
metrics）、`paired_deltas`（7 对比：3 主 + 4 次）、
`task_family_results`、`mechanism_summary_records`、`honest_signals`、
`private_score_manifest`、`private_event_manifest`、`forbidden_scan`、
no-claim flag（包括 `bea_superiority_claimed`）、
`self_test_checks_total`、`self_test_checks_passed` 和 `self_test_passed`。
无 raw task text、prompt、
response、patch、path、片段、atom composition、候选 trace、provider
payload、私有 path 或 per-task 结果。

### 声明边界

B16-G 仅为 live-provider atom-ablation 下游 smoke。它不是下游 agent 价值
证明、BEA 优越性声明、method winner、基准性能、default/promotion/
runtime/EvidenceCore 改动或 calibration。文档标明仅为 smoke；负/平结果
可接受。

### 验证结果

```text
python3 -m py_compile eval/b16g_context_pack_atom_ablation.py  => PASS
python3 eval/b16g_context_pack_atom_ablation.py --self-test  => PASS (221/221 checks)
python3 eval/b16g_context_pack_atom_ablation.py \
  --out artifacts/b16g_context_pack_atom_ablation/\
b16g_context_pack_atom_ablation_report.json  => PASS
  (status: blocked_remote_not_enabled,
   forbidden_scan: pass, self_test_passed: true,
   mode: public_aggregate_synthetic_task_family_matrix, phase: B16-G,
   model_display_category: unavailable,
   live_llm_agent: false, provider_calls_made: false,
   paired_run_executed: false,
   atom_ablation_executed: false,
   private_score_records_written: false,
   private_event_records_written: false,
   downstream_agent_value_proven: false, promotion_ready: false,
   method_winner_claimed: false, calibration_claimed: false,
   bea_superiority_claimed: false)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

本地 no-env 验证路径真实且 blocked/unavailable。手动 real-provider CI run
`27947247773` 已通过，已提交 artifact 现在镜像该 sanitized aggregate report：8
任务 x 5 arms = 40 次 live provider calls，forbidden scan pass，
`model_display_category=Kimi-K2.7-Code`，221/221 self-test checks，
`private_score_manifest.record_count=40`、`private_event_manifest.record_count=40`，
两个 manifest 均为 `storage_class=tmp_private` 且
`path_publicly_serialized=false`。

Live result：`control_sparse` solve/test=0.0；`target_only` solve/test=0.0；
`support_only` solve/test=1.0；`distractor_plus_support` solve/test=1.0；
`target_plus_support` solve/test=1.0。主对比：target+support vs
distractor+support solve/test delta=0.0；target+support vs support-only
solve/test delta=0.0；target-only vs support-only solve/test delta=-1.0。
机制 summary：`support_atom_sufficient_count=8`、
`target_atom_required_count=0`、`distractor_hurts_count=0`、
`all_arms_solved_count=0`、`sparse_solved_count=0`。解释：在该有界合成
live-provider 切片上，decisive support 足以驱动解题；target-only context 不足；
当 decisive support 存在时 distractor 未造成伤害。该结果解释 B16-F 的 tie，
但不声明 BEA 优越性或下游价值证明。

### Caveats

- B16-G 是 eval/diagnostic only。不是 benchmark/leaderboard/performance/
  method-winner/calibration/promotion/default/runtime/EvidenceCore/
  downstream-value/BEA-优越性 声明。
- Atom composition per arm 为确定性；不从 outcomes 调优。
- 有界合成样本（默认 8 任务 x 5 arms）。smoke，非严格评估。
- 所有 no-claim / no-runtime-change flag 为 false；EvidenceCore 语义未改。
- B16-F 语义未修改；B16-G 是独立 atom-ablation phase。

## 2026-06-21 — B16-H File-Choice Atom Ablation Live-Provider Smoke

### 目标

运行 live-provider file-choice atom ablation，解决 B16-G 的主要
confound：B16-G 的结构化 action schema 和 prompt 强制编辑 target.py，
因此 support_only 解决 11/11 并不能证明 support atom 单独能引导文件选择。
B16-H 在保持安全结构化 action 和私有 trace 的同时移除了该 confound。

### 前序结果

- B16-G 结果 checkpoint：`b407622`，CI run `27947247773`。
  `support_only`、`distractor_plus_support` 和
  `target_plus_support` 解决 11/11；`target_only` 和 sparse 解决 0/8。这
  受限于 target-file 强制 harness。

### 范围

- 阶段：`B16-H`。
- Evaluator：`eval/b16h_file_choice_atom_ablation.py`。
- Artifact：
  `artifacts/b16h_file_choice_atom_ablation/b16h_file_choice_atom_ablation_report.json`。
- 文档：`docs/en/b16h-file-choice-atom-ablation.md` 和 zh 镜像。
- `.github/workflows/real-provider-benchmark.yml` 中的 workflow stage：
  `b16h_file_choice_atom_ablation`。
- 仅手动 real-provider workflow；本地/no-env 模式真实阻断。
- 默认：8 合成任务 x 5 arms = 40 次 live provider 调用。

### Arms

1. `control_sparse`：仅任务 issue，最小 context；无 atom。
2. `file_choice_target_only`：target file cue + target symbol cue；无
   support，无 decisive cue。
3. `file_choice_support_only`：support module cue + decisive cue；无
   target file/symbol cue。
4. `file_choice_distractor_plus_support`：distractor file cue + support
   module cue + decisive cue；无 target file；wrong-file cue。
5. `file_choice_target_plus_support`：target file cue + target symbol
   cue + support module cue + decisive cue（full pack）。

主对比：`file_choice_target_plus_support` vs
`file_choice_support_only`；`file_choice_target_plus_support` vs
`file_choice_distractor_plus_support`；`file_choice_target_only` vs
`file_choice_support_only`。次对比：每个 context arm vs
`control_sparse`。

### Harness 改动（文件选择 confound 移除）

- prompt 不再说 only use target.py。
- 无全局 `ALLOWED_EDIT_FILES = {target.py}` 集合。
- 仅接受 per-task 安全文件集：target module、distractor module 和
  support/config/cross-file module（若存在）。
- 绝不接受任意路径。
- chosen file 仅记录在私有 event/SCORE trace 中。
- 公开仅暴露聚合文件选择率（selected_target_file_rate、
  selected_distractor_file_rate、selected_support_file_rate）。

### 机制摘要 record

仅聚合 record 字段：
`support_only_sufficient_with_file_choice_count`、
`target_atom_required_with_file_choice_count`、
`distractor_hurts_with_file_choice_count`、
`wrong_file_selection_count`、
`all_arms_solved_count`、
`sparse_solved_count`。

### 私有 artifact

对于每个 task x arm，B16-H 写入私有 SCORE JSONL（atom composition、
chosen_file、score outcome）和私有 event JSONL（prompt、response、
parsed action、chosen_file、patch/diff、test stdout/stderr、provider
metadata、tokens/cost/latency、failure reason），仅 `/tmp` 下。公开
artifact 仅包含聚合 manifest，含 record count、schema 版本、
`storage_class=tmp_private`、`path_publicly_serialized=false` 和
manifest hash。

### 公开 artifact 形状

仅聚合 record 的公开 artifact：`schema_version`、`generated_by`、
`generated_at`、`claim_level`、`status`、`mode`、`phase`、
`model_display_category`、`input_summary`（含
`file_choice_confound_removed=true`）、`arm_results`（per-arm 聚合
metrics，含文件选择率）、`paired_deltas`（7 对比：3 主 + 4 次）、
`task_family_results`、`mechanism_summary_records`、`honest_signals`、
`private_score_manifest`、`private_event_manifest`、`forbidden_scan`、
no-claim flag（包括 `bea_superiority_claimed`）、
`self_test_checks_total`/`self_test_checks_passed`。无 raw task text、prompt、
response、patch、path、片段、atom composition、chosen file 名、候选
trace、provider payload、私有 path 或 per-task 结果。

### 声明边界

B16-H 是有界合成 live-provider file-choice atom-ablation smoke。它不是
下游价值证明、BEA 优越性、method winner/default、基准性能、真实用户
证据、calibration、promotion 或 runtime/retriever/pack/backend/
default-policy/EvidenceCore 改动。文档对任何 sufficiency 发现标明
"在此有界合成 file-choice 切片上"。

### 验证结果

```text
python3 -m py_compile eval/b16h_file_choice_atom_ablation.py  => PASS
python3 eval/b16h_file_choice_atom_ablation.py --self-test  => PASS (266/266 checks)
python3 eval/b16h_file_choice_atom_ablation.py \
  --out artifacts/b16h_file_choice_atom_ablation/\
b16h_file_choice_atom_ablation_report.json  => PASS
  (status: blocked_remote_not_enabled,
   forbidden_scan: pass, self_test_passed: true,
   mode: public_aggregate_synthetic_task_family_matrix, phase: B16-H,
   model_display_category: unavailable,
   live_llm_agent: false, provider_calls_made: false,
   paired_run_executed: false,
   file_choice_atom_ablation_executed: false,
   private_score_records_written: false,
   private_event_records_written: false,
   downstream_agent_value_proven: false, promotion_ready: false,
   method_winner_claimed: false, calibration_claimed: false,
   bea_superiority_claimed: false)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

本地 no-env 验证路径真实且 blocked/unavailable。手动 real-provider CI run `27949115076` 已通过：8 任务 x 5 arms = 40 次 live provider calls；forbidden scan pass；私有 SCORE/event manifest 各 `record_count=40` 且 `path_publicly_serialized=false`；266/266 self-test。结果：`control_sparse` solve/test=0.0；`file_choice_target_only` solve/test=0.0 但 selected target file rate=1.0；`file_choice_support_only` solve/test=1.0 且 selected target file rate=1.0；`file_choice_distractor_plus_support` solve/test=1.0 且 selected target file rate=1.0；`file_choice_target_plus_support` solve/test=1.0 且 selected target file rate=1.0。机制 summary：`support_only_sufficient_with_file_choice_count=8`、`target_atom_required_with_file_choice_count=0`、`distractor_hurts_with_file_choice_count=0`、`wrong_file_selection_count=0`、`all_arms_solved_count=0`、`sparse_solved_count=0`。解释：在此有界合成 file-choice 切片上，decisive support cue 仍足以引导文件选择；target-only context 不足；当 decisive support 存在时 distractor 未造成伤害。这不是下游价值证明、BEA 优越性声明、method-winner/default 声明、benchmark/performance 声明或 calibration 声明。

### Caveats

- B16-H 是 eval/diagnostic only。不是 benchmark/leaderboard/performance/
  method-winner/calibration/promotion/default/runtime/EvidenceCore/
  downstream-value/BEA-优越性 声明。
- 文件选择 confound 已移除；chosen file 仅记录在私有 trace 中；公开
  artifact 仅聚合文件选择率。
- 有界合成样本（默认 8 任务 x 5 arms）。smoke，非严格评估。sufficiency
  措辞限于 "在此有界合成 file-choice 切片上"。
- 所有 no-claim / no-runtime-change flag 为 false；EvidenceCore 语义
  未改。
- B16-F/B16-G 语义未修改；B16-H 是独立 file-choice atom-ablation phase。

## 2026-06-21 — B16-I Non-Decisive Support / Target-Support Conjunction Live-Provider Smoke

### 目标

B16-I 测试 B16-H 暴露的机制。B16-H 移除了文件选择 confound，但
support-only 仍然解决了所有任务，因为 support cue 过于 decisive。B16-I
重新设计 live-provider 合成任务，用来测试 support 单独是否可变为非
decisive：预期 target binding 和 support rule 需要同时存在。Run
`27950908481` 未支持该假设；support-only 仍然足够。

### 前序结果

B16-H 结果 checkpoint `8eb150c`，手动 CI run `27949115076`：8 任务 x 5
arms = 40 live 调用。`control_sparse` solve/test = 0.0。
`file_choice_target_only` solve/test = 0.0 但
selected_target_file_rate=1.0。`file_choice_support_only`、
`file_choice_distractor_plus_support` 和
`file_choice_target_plus_support` solve/test = 1.0。
`support_only_sufficient_with_file_choice_count=8`、
`target_atom_required_with_file_choice_count=0`、
`wrong_file_selection_count=0`。结论：decisive support cue 在该有界切片
上足够；target-only 不足。暂不从该结果调优 BEA。

### 范围

- 阶段：`B16-I`。
- Evaluator：`eval/b16i_target_support_conjunction.py`。
- Artifact：
  `artifacts/b16i_target_support_conjunction/b16i_target_support_conjunction_report.json`。
- 文档：`docs/en/b16i-target-support-conjunction.md` 和 zh 镜像。
- Workflow stage：`b16i_target_support_conjunction`。
- 仅手动 real-provider workflow；本地/no-env 模式真实阻断。
- 默认：8 合成任务 x 5 arms = 40 次 live provider 调用。

### Arms

1. `control_sparse`：仅任务 issue，最小 context；无 atom。
2. `file_choice_target_only`：target file cue + target symbol cue；无
   support module，无 support rule。
3. `file_choice_nondecisive_support_only`：support module cue + 非决定性
   support rule；无 target file cue，无 symbol cue。support atom **不**
   包含确切最终答案、确切 target-file 指令或 target-symbol edit 指令。
4. `file_choice_distractor_plus_nondecisive_support`：distractor file
   cue + support module cue + 非决定性 support rule；无 target file；
   wrong-file binding。
5. `file_choice_target_plus_support`：target file cue + target symbol
   cue + support module cue + 非决定性 support rule（conjunction arm）。

主对比：`file_choice_target_plus_support` vs
`file_choice_target_only`；vs
`file_choice_nondecisive_support_only`；vs
`file_choice_distractor_plus_nondecisive_support`。次对比：
`file_choice_target_only` vs
`file_choice_nondecisive_support_only`；每个 context arm vs
`control_sparse`。

### 预期非决定性 support cue 设计

support atom 给出 formula/invariant/dependency/config relation，仍需要
TARGET BINDING 才能应用。它**不**包含确切最终答案、确切 target-file
指令或 target-symbol edit 指令。`file_choice_target_plus_support` arm
额外给出 target binding，使完整 cue 成为决定性的。

### 机制摘要 record

`target_support_conjunction_required_count`、
`support_only_sufficient_count`、`target_only_sufficient_count`、
`distractor_hurts_count`、`wrong_file_selection_count`、
`all_arms_solved_count`、`sparse_solved_count`。

### 验证结果

```text
python3 -m py_compile eval/b16i_target_support_conjunction.py  => PASS
python3 eval/b16i_target_support_conjunction.py --self-test  => PASS (306/306 checks)
python3 eval/b16i_target_support_conjunction.py \
  --out artifacts/b16i_target_support_conjunction/\
b16i_target_support_conjunction_report.json  => PASS
  (status: blocked_remote_not_enabled,
   forbidden_scan: pass, self_test_passed: true,
   mode: public_aggregate_synthetic_task_family_matrix, phase: B16-I,
   model_display_category: unavailable,
   live_llm_agent: false, provider_calls_made: false,
   paired_run_executed: false,
   target_support_conjunction_executed: false,
   private_score_records_written: false,
   private_event_records_written: false,
   downstream_agent_value_proven: false, promotion_ready: false,
   method_winner_claimed: false, calibration_claimed: false,
   bea_superiority_claimed: false)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

本地 no-env 验证路径真实且 blocked/unavailable。手动 real-provider CI
run 待执行。

### Caveats

- B16-I 是 eval/diagnostic only。不是 benchmark/leaderboard/performance/
  method-winner/calibration/promotion/default/runtime/EvidenceCore/
  downstream-value/BEA-优越性 声明。
- support cue 按设计预期非决定性，但 run `27950908481` 未观察到 target-support conjunction requirement；support-only 仍然足够。
- 有界合成样本（默认 8 任务 x 5 arms）。smoke，非严格评估。sufficiency
  措辞限于 "在此有界合成 file-choice 切片上"。
- 所有 no-claim / no-runtime-change flag 为 false；EvidenceCore 语义
  未改。
- B16-F/B16-G/B16-H 语义未修改；B16-I 是独立 target-support conjunction
  phase。

## 2026-06-21 — B16-J Ambiguous-Support Conjunction Live-Provider Smoke

### 目标

B16-J 是最后一个 B16 atom-redesign 尝试。它通过 role-neutral candidate filenames 与完整 prompt 泄漏自测修复 B16-I 失败，然后测试 target binding + ambiguous support 是否是 live-provider 解题所需组合。

### 前序结果

B16-I 结果 checkpoint `f5ad8de`，CI run `27950908481`：support-only 解决 11/11；target-support conjunction 未观察到（`target_support_conjunction_required_count=0`、`support_only_sufficient_count=8`）。

### 范围

- 阶段：`B16-J`。Evaluator：`eval/b16j_ambiguous_support_conjunction.py`。
- Artifact：`artifacts/b16j_ambiguous_support_conjunction/b16j_ambiguous_support_conjunction_report.json`。
- 文档：`docs/en/b16j-ambiguous-support-conjunction.md` 和 zh 镜像。
- Workflow stage：`b16j_ambiguous_support_conjunction`。
- 默认：8 任务 x 5 arms = 40 次 live provider 调用。

### Arms

1. `control_sparse`；2. `ambiguous_target_only`；3. `ambiguous_support_only`；4. `ambiguous_distractor_plus_support`；5. `ambiguous_target_plus_support`。

support-only 完整 prompt 自测避免 target-role lexical cues、target filename、target symbol、unique noun、exact answer、edit instruction 或 test path/name。candidate filenames 是 role-neutral；target/distractor 角色只留在私有 evaluator 结构中。

### 验证结果

```text
python3 -m py_compile eval/b16j_ambiguous_support_conjunction.py  => PASS
python3 eval/b16j_ambiguous_support_conjunction.py --self-test  => PASS (329/329 checks)
python3 eval/b16j_ambiguous_support_conjunction.py --out ...  => PASS
  (status: blocked_remote_not_enabled, forbidden_scan: pass,
   self_test_passed: true, phase: B16-J,
   bea_superiority_claimed: false, support_cue_ambiguous: true)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

手动 real-provider CI run `27953321504` 已通过：8 任务 x 5 arms = 40 次 live provider calls；forbidden scan pass；私有 SCORE/event manifest 各 `record_count=40` 且 `path_publicly_serialized=false`；329/329 self-test。结果：`control_sparse` solve/test=0.0、selected_target_file_rate=0.125、wrong_file_edit_rate=0.875；`ambiguous_target_only` solve/test=0.0、selected_target_file_rate=1.0；`ambiguous_support_only` solve/test=0.25、selected_target_file_rate=0.25、selected_distractor_file_rate=0.625、wrong_file_edit_rate=0.75；`ambiguous_distractor_plus_support` solve/test=0.625、selected_target_file_rate=0.625、selected_distractor_file_rate=0.375；`ambiguous_target_plus_support` solve/test=1.0、selected_target_file_rate=1.0、wrong_file_edit_rate=0.0。`ambiguous_target_plus_support` 的主 delta：vs `ambiguous_support_only` solve/test delta=+0.75、wrong_file_edit_rate delta=-0.75、selected_target_file_rate delta=+0.75；vs `ambiguous_target_only` solve/test delta=+1.0；vs `ambiguous_distractor_plus_support` solve/test delta=+0.375、wrong_file_edit_rate delta=-0.375。机制 summary：`target_support_conjunction_required_count=6`、`support_only_sufficient_count=2`、`target_only_sufficient_count=0`、`distractor_hurts_count=3`、`ambiguous_support_wrong_binding_count=6`、`wrong_file_selection_count=6`、`all_arms_solved_count=0`、`sparse_solved_count=0`。解释：在 role-neutral 文件名和完整 prompt 泄漏自测之后，B16-J 终于在该有界合成切片上隔离出 target+support conjunction 信号；support-only 多数任务不再足够（2/8），target-only 0/8，而 ambiguous support 加 target binding 后 11/11。该结果仍只是 smoke-level 合成 live-provider 机制结果，不是下游价值证明、BEA 优越性、method-winner/default、benchmark/performance、calibration、promotion 或 runtime/EvidenceCore 改动。

### Caveats

- B16-J 是 eval/diagnostic only。不是下游价值/BEA 优越性/method winner/default/benchmark/calibration/promotion/runtime/EvidenceCore 声明。
- 这是有界合成 live-provider 机制 smoke，不是真实用户任务证据。
- B16-J 已满足 stop rule：它隔离出 conjunction 信号；不要运行 B16-K，下一步转向外部 BEA scale / 更广真实 benchmark 工作。

## 2026-06-21 — BEA-4 External Scale Smoke

### 目标

为冻结 BEA v0.3 策略运行更大的 external benchmark scale smoke。本阶段度量
scale 行为；不更改 BEA v0.3、不调优策略权重、不声明 method winner/default。

### 冻结策略

`bea_v0_3_anchor_span_latency` 与 BEA-3 完全相同（冻结权重：anchor=0.35、
span_tight=0.15、anchor_file_support=0.10、weak_support_penalty=-0.20、
early_stop_margin=0.05）。BEA-4 期间无算法/权重变更
（`algorithm_changed_during_bea4=false`、
`weights_tuned_during_bea4=false`——绑定）。

### 必需 arm（无消融）

`bm25_prefix_same_budget`、`agreement_only_same_budget`、`rrf_same_budget`
（启用时）、`bea_v0`、`bea_v0_2_diversity_risk`、
`bea_v0_3_anchor_span_latency`、`seeded_random_same_budget`。

### 全新 primary 切片

ContextBench verified Python 行 offset 80、limit 80（硬上限 80）。
RepoQA Python needle offset 40、limit 40（硬上限 40）。

### 公开 artifact 形态

仅 records：`benchmark_arm_metric_records`、`delta_records`（v0.3 vs
bm25/agreement/rrf/v0.2/v0/random）、`win_tie_loss_records`、
`worst_slice_records`（7 个固定 bucket 标签；每 benchmark × arm 取最差
N=5）、`mechanism_summary_records`、aggregate-only `private_score_manifest`。

### Worst-slice bucket 标签（固定公开聚合）

`benchmark`、`query_length_bucket`、`candidate_pool_size_bucket`、
`budget_exhaustion_bucket`、`file_kind_mix_bucket`、`method_agreement_bucket`、
`rank_gap_bucket`。无 row IDs、repos、paths、commits、queries、labels、
candidate lists 或 gold/source snippets。

### 验证结果

```text
python3 -m py_compile eval/bea4_external_scale_smoke.py  => PASS
python3 eval/bea4_external_scale_smoke.py --self-test  => PASS (238/238 checks)
python3 eval/bea4_external_scale_smoke.py \
  --enable-external-benchmark-network \
  --contextbench-row-offset 80 --contextbench-row-limit 3 \
  --repoqa-needle-offset 40 --repoqa-needle-limit 2 \
  --budget 5 --methods bm25,regex,symbol --enable-rrf-baseline \
  --out artifacts/bea4_external_scale_smoke/bea4_external_scale_smoke_report.json  => PASS
  (status: bea4_external_scale_smoke_pass, 5 records successful,
   private_score_manifest.record_count=35 (5×7 arms),
   private_score_storage_class=tmp_private,
   private_score_path_publicly_serialized=false,
   provider_calls=0, forbidden_scan=pass,
   algorithm_changed_during_bea4=false, weights_tuned_during_bea4=false)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

### 手动 CI scale 结果（run `27957586271`）

手动 CI run `27957586271` 在完整 BEA-4 scale 切片上通过：120 条记录成功
（ContextBench 80 + RepoQA 40），`network_calls=3`，`provider_calls=0`，
forbidden scan pass，`private_score_manifest.record_count=840`（120×7 arm），
`path_publicly_serialized=false`。

BEA v0.3 benchmark 指标：ContextBench file_recall@10=0.225、mrr=0.151875、
span_f0.5@10=0.013607、success_rate=0.225；RepoQA file_recall@10=0.575、
mrr=0.402917、span_f0.5@10=0.044761、success_rate=0.575。

Delta：v0.3 与 BEA v0.2 在 file_recall/MRR/success 上持平，span 略低
（-0.000075），latency 微增（+0.000831s）。v0.3 相对 BEA v0 / same-budget
BM25 / agreement-only / RRF：file_recall +0.108334，MRR +0.076945，span
+0.001333，success +0.108334；相对 seeded random：file_recall +0.175，MRR
+0.139028，span +0.020195，success +0.175。Latency 与 quality-per-latency 是
mixed，尤其 vs RRF 的 quality_per_latency delta=-0.05038。

Worst-slice records：70 条固定公开 bucket label 的聚合记录。该结果是 scale
smoke evidence，不是 method-winner/default/performance/calibration/downstream-value
声明。

### Caveats

- BEA-4 是 eval/diagnostic only。不是 benchmark/leaderboard/performance/
  method-winner/calibration/promotion/default/runtime/EvidenceCore/
  downstream-value 声明。
- v0.3 算法/权重与 BEA-3 完全一致（冻结）。
  `algorithm_changed_during_bea4=false`、
  `weights_tuned_during_bea4=false`（绑定）。
- 已提交 artifact 镜像手动 CI run `27957586271` 的完整 ContextBench 80 +
  RepoQA 40 scale 切片。3+2 命令仅作为本地验证保留，不作为结果证据。
- BEA-0/BEA-1/BEA-2/BEA-3 语义未修改。

## 2026-06-21 — BEA-5 Frozen-Policy Robustness Smoke

### 目标

运行全新 disjoint 更大/跨切片 external 稳健性 smoke，BEA v0.3 与 BEA-4
完全一致（冻结）。测试 BEA-4 结论在任何 BEA v0.4 调优前是否稳定。

### 冻结策略

`bea_v0_3_anchor_span_latency` 与 BEA-3/BEA-4 完全相同（冻结权重：
anchor=0.35、span_tight=0.15、anchor_file_support=0.10、
weak_support_penalty=-0.20、early_stop_margin=0.05）。BEA-5 期间无算法/权重
变更（`algorithm_changed_during_bea5=false`、
`weights_tuned_during_bea5=false`——绑定）。

### 必需 arm（7 个；RRF 必需，从不可选）

`bea_v0_3_anchor_span_latency`、`bea_v0_2_diversity_risk`、`bea_v0`、
`bm25_prefix_same_budget`、`agreement_only_same_budget`、`rrf_same_budget`、
`seeded_random_same_budget`。无消融。

### 固定协议与最终 run

最初 fixed-tail 协议无法提供足够 evaluable records。最终协议改为在全可用
Python frame 上做 success-quota sampling，排除 BEA-2/3/4 窗口，raw caps 为
ContextBench 480 与 RepoQA 240，budget 5，固定 methods `bm25,regex,symbol`，
RRF 必需。

最终 CI run `28003522632` 以 119/120 successful records fail-closed。本地
exact-protocol rerun 复现了同一 aggregate artifact。

### 公开 artifact 形态

仅 records：`benchmark_arm_metric_records`、`delta_records`（v0.3 vs
bm25/agreement/rrf/v0.2/v0/random）、`win_tie_loss_records`、
`worst_slice_records`（7 个固定 bucket 标签；每 benchmark × arm 取最差
N=5）、`mechanism_summary_records`、`robustness_summary_records`（cross_slice
delta、sign stability、quality_per_latency 聚合、worst-slice cluster 计数）、
`benchmark_attempt_records`、aggregate-only `private_score_manifest`、
aggregate-only `private_attempt_manifest`。

### Natural-key 唯一性

每个公开 record 表按其 natural key 唯一。self-test 和 CI validator 检查
全部 6 个 record 表的唯一性。

### Counts-only self-test 摘要

公开 artifact 仅记录 `self_test_passed`（bool）、
`self_test_checks_total`（int, 435）、`self_test_checks_passed`（int）。
无 self_test 详情列表。禁止字段：`self_test_checks`、
`self_test_details`、`self_test_list`、`checks`、`check_list`。

### 验证结果

```text
python3 -m py_compile eval/bea5_frozen_policy_robustness.py  => PASS
python3 eval/bea5_frozen_policy_robustness.py --self-test  => PASS (435/435 checks)
python3 eval/bea5_frozen_policy_robustness.py \
  --enable-external-benchmark-network \
  --contextbench-row-offset 0 --contextbench-row-limit 480 \
  --repoqa-needle-offset 0 --repoqa-needle-limit 240 \
  --budget 5 --methods bm25,regex,symbol \
  --out artifacts/bea5_frozen_policy_robustness/bea5_frozen_policy_robustness_report.json  => PASS
  (status: partial, records_successful=119, records_attempted_total=186,
   records_excluded=67, quota_reached=false,
   contextbench_successful=82, repoqa_successful=37,
   private_score_manifest.record_count=833 (119×7 arms),
   private_attempt_manifest.record_count=186,
   provider_calls=0, forbidden_scan=pass,
   algorithm_changed_during_bea5=false, weights_tuned_during_bea5=false,
   self_test_checks_total=435, self_test_checks_passed=435)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

### 固定协议 near-miss 结果（2026-06-22）

CI run `28003522632` 以 `records_successful=119` fail-closed，比严格
`target_successful_records=120` 少 1 条。本地 exact-protocol rerun 复现
artifact：`records_attempted_total=186`、`records_excluded=67`、
`contextbench_successful=82`、`repoqa_successful=37`、
`failure_category_counts.retrieval_failed=67`、
`failure_category_counts.rrf_required_but_missing=0`。

119 条成功记录上的 selected deltas：v0.3 与 v0.2 在 file_recall@10、MRR、
success_rate 上打平；v0.3 vs v0.2 有 `span_f0.5@10 +0.004953`、
`quality_per_latency +0.002853`。v0.3 相对 BM25/agreement/RRF 在
file_recall@10/MRR/success_rate 上为 +0.184874/+0.164566/+0.184874，但保留
latency trade-off，且因为 quota 未达成不能记录为 BEA-5 pass。

### Caveats

- BEA-5 是 eval/diagnostic only。不是 benchmark/leaderboard/performance/
  method-winner/calibration/promotion/default/runtime/EvidenceCore/
  downstream-value 声明。
- v0.3 算法/权重与 BEA-3/BEA-4 完全一致（冻结）。
  `algorithm_changed_during_bea5=false`、
  `weights_tuned_during_bea5=false`（绑定）。
- 最终固定协议少 1 条成功记录（119/120），这是 No-Go / near-miss 结果，
  作为 failure decomposition 输入。
- RRF arm 必需；CI 在 RRF 禁用/缺失时失败。
- BEA-0/BEA-1/BEA-2/BEA-3/BEA-4 语义未修改。

## 2026-06-22 — BEA-FD1: BEA-4/5 冻结重放失败分解

### 目标

BEA-5 近似未达（`records_successful=119`，`status=partial`，CI
`28003522632`）后，在 BEA v0.4 前运行 per-record 失败分解。重放冻结
BEA-4/5 协议以在 `/tmp` 下重新生成 per-record 私有分解行，将 v0.3 treatment
结果分类到固定类别 enum，并发布 records-only 聚合分解表。不更改 BEA v0.3、
采样、gate、arm 或权重。不实现 v0.4。

### 固定类别 enum

`gold_file_absent`、`gold_span_absent`、`correct_file_wrong_span`、
`redundant_same_file_candidates`、`too_many_anchor_slots`、
`missing_support_candidate`、`support_selected_without_target`、
`target_selected_without_support`、`risk_penalty_removed_gold`、
`early_stop_too_early`、`budget_spent_on_low_marginal_gain`、
`latency_without_quality_gain`。

### 验证

```text
python3 -m py_compile eval/bea_fd1_failure_decomposition.py  => PASS
python3 eval/bea_fd1_failure_decomposition.py --self-test  => PASS (174/174 checks)
python3 eval/bea_fd1_failure_decomposition.py \
  --out artifacts/bea_fd1_failure_decomposition/bea_fd1_failure_decomposition_report.json  => PASS
  (status: unavailable_with_reason, no-network artifact,
   provider_calls=0, forbidden_scan=pass,
   algorithm_changed_during_bea_fd1=false, weights_tuned_during_bea_fd1=false,
   self_test_checks_total=174, self_test_checks_passed=174)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

### Caveats

- BEA-FD1 是 eval/diagnostic only。不是 benchmark/leaderboard/performance/
  method-winner/calibration/promotion/default/runtime/EvidenceCore/
  downstream-value 声明。
- v0.3 算法/权重冻结；`algorithm_changed_during_bea_fd1=false`、
  `weights_tuned_during_bea_fd1=false`（绑定）。
- 首次实现计算类别子集；trace-missing 类别标记为
  `unavailable_missing_trace`。
- Manual BEA-FD1 CI run `28011901294` 通过：status `bea_fd1_decomposition_pass`，records_decomposed=239，private decomposition rows=86040，forbidden_scan=pass。
- 结果解释：主导的 available 类别是 low marginal gain / latency cost、gold-file absence、correct-file/wrong-span；support-target 类别在私有 SCORE 尚无 role labels 前仍为 unavailable。

## 2026-06-23 — BEA-v0.4-P1：集合角色代理冒烟

### 目标

在 BEA-FD1 失败分解之后，为集合/互补感知 BEA 策略产生最小真实算法证据，
不声称 v0.4 已被证明。问题：确定性角色代理集合选择能否改变 BEA v0.3 行为，
并在不发生灾难性质量损失的前提下减少 FD1 失败家族？

### 范围（绑定）

- 仅评估本地。不更改 runtime/default/EvidenceCore。
- 不运行 B16-K，不调优 v0.31/v0.32 权重，不扩展 dense/graph/QuIVer/provider
  范围。
- 预算固定为 5。方法固定为 `bm25,regex,symbol`。
- 角色代理为确定性运行时清洁，无 gold/私有标签：
  固定枚举 `target_proxy`、`support_proxy`、`unknown`。

### 必需臂（6 个；RRF 廉价且稳定）

`bm25_prefix_same_budget`、`bea_v0_3_anchor_span_latency`、
`role_proxy_only_same_budget`、`setwise_complementarity_v0_4_p1`、
`seeded_random_same_budget`、`rrf_same_budget`。处理臂：
`setwise_complementarity_v0_4_p1`。质量基线：v0.3。

### v0.4 P1 集合选择规则（冻结、无事后调优）

- 如果可用，至少选择一个 `target_proxy`（预留目标槽位）。
- 优先选择来自不同文件/符号家族的 `support_proxy`。
- 惩罚重复同文件选择（强惩罚 -0.35）。
- 奖励新颖性/来源多样性/span 紧致度。
- 冻结权重：target=0.40、support_cross_file=0.20、
  source_diversity=0.15、span_tight=0.10、novelty=0.10、
  weak_support_penalty=-0.15。

### 数据集 / 协议

新鲜小规模外部冒烟（成功配额），失败即关闭：
records_successful>=30、contextbench_successful>=20、repoqa_successful>=10。
原始尝试上限 ContextBench 480 / RepoQA 240。强制排除窗口：BEA-2/3/4
（ContextBench [40,160)、RepoQA [20,80)）。BEA-5 重叠已披露但不排除
（BEA-5 在同一完整帧上使用成功配额且未消耗全部帧）。这是 P1 冒烟证据，
不是新鲜不相交验证。

### 硬门控

角色代理可行性：assignment_rate>=0.70、target_available>=0.50、
support_available>=0.30、unknown_only<=0.30。行为：
setwise_diff_vs_v03>=0.25、dup_file_v04<=dup_file_v03、
source_diversity_v04>=source_diversity_v03。质量安全：
file_recall@10/mrr 在 0.05 内、span 在 0.02 内、延迟在 1.25x 内。
至少一个方向性改进。

### 公开产物形态

仅记录：`source_run_records`、`arm_metric_records`、`arm_delta_records`、
`role_proxy_summary_records`、`setwise_behavior_records`、
`failure_family_records`、`win_tie_loss_records`、`availability_records`、
`benchmark_attempt_records`，仅聚合
`private_score_manifest`/`private_decision_manifest`/
`private_role_proxy_manifest`、`hard_gate_records`、`failure_category_count_records`、`forbidden_scan`。无公开
记录 ID、仓库 URL、提交、路径、查询、gold 标签、span、片段、候选文件、
决策顺序、分数组件或每条记录角色标签。

### 验证结果

```text
python3 -m py_compile eval/bea_v04_p1_setwise_role_proxy_smoke.py  => PASS
python3 eval/bea_v04_p1_setwise_role_proxy_smoke.py --self-test  => PASS (269/269 checks)
python3 eval/bea_v04_p1_setwise_role_proxy_smoke.py \
  --out artifacts/bea_v04_p1_setwise_role_proxy/bea_v04_p1_setwise_role_proxy_smoke_report.json  => PASS
  (status: unavailable_with_reason, no-network artifact,
   provider_calls=0, forbidden_scan=pass,
   algorithm_changed_during_bea_v04_p1=false, weights_tuned_during_bea_v04_p1=false,
   v04_full_matrix_claimed=false,
   self_test_checks_total=269, self_test_checks_passed=269)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

### Manual CI 结果

Manual CI run `28017063082` 通过 fail-closed workflow，并产生有效 P1 No-Go / 弱负向结果：status `no_go_proxy_unavailable`，records_successful=38（ContextBench 20、RepoQA 18），attempted=46，excluded=8，private SCORE rows=228，decision rows=190，role-proxy rows=760。当前 role proxies 给所有 candidate 分配了角色，但 target_proxy_available_rate=0.0，setwise_selection_diff_rate_vs_v03=0.105263（低于 0.25）。相对 v0.3 没有灾难性质量退化，但也没有改进：file_recall@10 和 MRR delta 为 0.0，span_f0.5@10 delta=-0.003036，latency delta=+0.001686s，quality_per_latency delta=-0.000809。

### 注意事项

- BEA-v0.4-P1 仅为评估/诊断。不是 benchmark/leaderboard/
  performance/method-winner/calibration/promotion/default/runtime/
  EvidenceCore/downstream-value 声明。不是 v0.4 证明。不是完整 v0.4 矩阵。
- v0.3 算法/权重冻结；`algorithm_changed_during_bea_v04_p1=false`。
- 角色代理为确定性运行时清洁，无 gold/私有标签。
- 新鲜冒烟协议披露 BEA-5 重叠（不是新鲜不相交验证）。CI run `28017063082`
  是真实 P1 冒烟结果；默认无网络 artifact 已被 supersede。
- 私有 score/decision/role-proxy JSONL 文件仅写入 `/tmp` 且永不上传。
- 离线 BEA-4/5 反事实重放是未来扩展（私有轨迹缺少完整候选列表，
  因此无法在同一候选上重新运行 v0.4 P1 选择）。

## 2026-06-23 — BEA-v0.4-P2：目标角色代理修复冒烟

### 目标

修复 P1 的具体 target-role proxy 失败（`target_proxy_available_rate=0.0`），但不进入完整 v0.4 矩阵。问题是运行时清洁的 target-role proxy 特征能否产生非零 target availability，并相对 v0.3 与冻结 P1 实质改变 setwise selection。

### 实现 / 验证

- Local checkpoint `d59492f` 新增 standalone evaluator `eval/bea_v04_p2_target_role_proxy_repair_smoke.py`、docs、artifact 与 manual CI workflow。
- P2 保持 v0.3 冻结，复用 P1 frame，排除 BEA-2/3/4 windows，披露 BEA-5/P1 overlap，并仅在 `/tmp` 写入私有 score/decision/role-proxy/target-feature JSONL。
- Self-test 335/335；public artifact 保持 records-only；local checkpoint 前已移除 top-level manifest dict mirrors。

### Manual CI 结果

Manual CI run `28020331024` 通过 fail-closed，并产生有效 P2 No-Go：status `no_go_target_proxy_still_unavailable`，records_successful=38（ContextBench 20、RepoQA 18），attempted=46，excluded=8，private SCORE rows=228，decision rows=190，role-proxy rows=760，target-feature rows=760，forbidden_scan=pass。

P2 修复了 target availability 问题：target_proxy_available_rate 从 0.0 升至 1.0，target_proxy_selected_rate_p2=1.0。但 support_proxy_available_rate_p2=0.0，selection_diff_rate_p2_vs_p1=0.0，selection_diff_rate_p2_vs_v03=0.105263（低于 0.25）。相对 v0.3 的质量安全通过（file_recall@10 与 MRR delta 为 0.0，span_f0.5@10 delta=-0.003036，latency +0.001789s），但没有算法推进。

### 决定

不能从 P2 进入完整 v0.4 矩阵。下一步必须修复 support/complementarity proxy 行为或停止当前 role-proxy 设计；不做 v0.31/v0.32 权重微调，也不跑 B16-K。


## 2026-06-23 — BEA-v0.4-P3：支持/互补代理修复冒烟

### 目标

在 P2 之后只运行一次最终有界修复：以修复后的 P2 目标锚点为条件构造 support/complementarity proxy，检验支持可用性是否非退化、P3 是否相对 v0.3/P2/P1 实质改变选择、以及质量是否安全。这不是完整 v0.4 矩阵，也不是 v0.4 证明。

### 实现 / 验证

- Local checkpoint `7f58f66` 新增 standalone evaluator `eval/bea_v04_p3_support_complementarity_repair_smoke.py`、docs、aggregate artifact 与 manual CI workflow。
- P3 使用同一 P1/P2 frame，保持 v0.3/P1/P2 冻结，仅使用 7 个臂，私有 score/decision/role-proxy/support-feature/pair-feature JSONL 仅写入 `/tmp`，公开 records-only 聚合表。
- Self-test 400/400；public artifact 没有 top-level manifest dict mirrors，也没有动态 `hard_gates`/`failure_category_counts` dict。

### Manual CI 结果

Manual CI run `28022595796` 通过 fail-closed，并产生有效 P3 No-Go：status `no_go_support_proxy_degenerate`，records_successful=38（ContextBench 20、RepoQA 18），attempted=46，excluded=8，private SCORE rows=266，decision rows=190，role-proxy rows=760，support-feature rows=760，pair-feature rows=38，forbidden_scan=pass。

P3 对 support collapse 修复过度：target proxy available/selected rate 都为 1.0，support proxy available/selected rate 都为 1.0，target-support pair available/selected rate 都为 1.0，但 `support_proxy_available_rate_p3=1.0` 超过 <=0.90 gate，且 `mean_support_candidates_per_record_p3=18.289474` 超过 <=8.0 非退化 gate。P3 改变了选择（相对 v0.3=0.5、相对 P2=0.394737、相对 P1=0.394737），但质量相对 v0.3 退化：file_recall@10 delta -0.052632，MRR delta -0.155263，span_f0.5@10 delta -0.003531，latency +0.001730s，quality_per_latency 0.015992 vs 0.016856。

### 决定

停止 role-proxy repair 线。不要运行 legacy role-proxy P4/P5。不要从当前 role-proxy 设计进入完整 v0.4 矩阵。不要调 v0.31/v0.32 权重。下一步算法工作必须转向直接 FD1-objective setwise acquisition，直接使用 decomposition losses，而不是继续修 target/support proxy。

## 2026-06-23 — BEA-FD2-A：直接 FD1 目标 Setwise 采集冒烟

### 目标

P1/P2/P3 关闭 role-proxy 线后，测试一个直接替代方案：把 FD1 聚合 failure-decomposition losses 作为冻结 setwise objective。这个 treatment 不是 role proxy，不是 legacy role-proxy P4/P5，不是完整 v0.4 矩阵，也不是 v0.31/v0.32 权重微调。它使用与 P1/P2/P3 相同的 38 条 bounded frame，回答直接 FD1-weighted objective 是否值得进入 heldout FD2-B。

### 实现 / 验证

- Local checkpoint `709b0cb` 新增 standalone evaluator `eval/bea_fd2a_direct_fd1_objective_setwise_smoke.py`、docs、aggregate artifact 与 manual CI workflow。
- FD2-A 使用 5 个臂：same-budget BM25、same-budget RRF、frozen v0.3、coverage-only setwise、FD1-weighted setwise。
- 私有 score/decision/FD1-objective feature/post-hoc decomposition/objective-config JSONL 仅写入 `/tmp`；公开 artifact 只包含 aggregate-only records tables。
- Self-test 373/373；role proxy 被明确禁用。

### Manual CI 结果

Manual CI run `28025382422` 通过 fail-closed，并产生有效 bounded No-Go：status `no_go_no_fd1_loss_reduction`，records_successful=38（ContextBench 20，RepoQA 18），attempted=46，excluded=8，private SCORE rows=190，decision rows=190，FD1-objective feature rows=190，post-hoc decomposition rows=950，objective config rows=1，forbidden_scan=pass。

FD1-weighted treatment 实质改变了选择（相对 v0.3 diff=0.710526，相对 coverage-only diff=0.684211），但 objective 变差：composite FD1 loss 为 0.756181，而 v0.3 为 0.397802、coverage-only 为 0.748783。质量也退化：file_recall@10 为 0.684211（v0.3 为 0.763158），MRR 为 0.516228（v0.3 为 0.569737）。Span_f0.5@10 与 latency gate 通过，但 FD1-loss 与 quality gate 失败。

### 决定

不要从这个 objective 进入 FD2-B。不要调 v0.31/v0.32 权重。不要复活 role proxy。直接 FD1-weighted objective 在这个 bounded frame 上应视为失败算法假设；下一步算法工作必须先解释为什么优化聚合 FD1 losses 会选出更差 evidence set，再提出新 objective。

## 2026-06-23 — BEA-FD2-A1：直接 FD1 目标失败归因重放

### 目标

解释 BEA-FD2-A 直接 aggregate-FD1-loss weighting 为什么选出更差 evidence set。本阶段是 replay-only 机制归因，不是新 selector，不是 FD2-B，不是 legacy role-proxy P4/P5，也不是 v0.31/v0.32 调参。

### 实现 / 验证

- Local checkpoint `67a6d61` 新增 standalone evaluator `eval/bea_fd2a1_failure_attribution_replay.py`、manual workflow、aggregate artifact 与 en/zh docs。
- Evaluator 在 `/tmp` 下原样重跑 FD2-A，解析私有 score/decision/FD1-objective feature/post-hoc decomposition/objective-config traces，并只发布 aggregate records-only 机制表。
- Self-test 404/404；默认无网络 artifact 如实为 `unavailable_with_reason`。

### Manual CI 结果

Manual CI run `28027342996` 10m42s 绿色完成。Replay 匹配 FD2-A：records_attributed=38，records_regressed=38，private trace counts 190/190/190/950/1，forbidden_scan=pass，status `bea_fd2a1_attribution_replay_pass`。

主导机制非常明确：`latency_category_non_actionable_or_dominating` 在 38/38 条退化记录上触发。次级机制为 redundancy_overcorrection 4/38、gold_file_displacement 3/38、aggregate_weight_category_collision 3/38。候选可用性不是 blocker：`candidate_availability_limit=0/38`，且 38/38 记录在 budget 与 2×budget 以上的池中都有更好候选。

### 决定

FD2-A 失败是因为 aggregate FD1-loss objective 对 candidate-level proxy 无法操作的 latency-loss 类别施加了决定性压力。下一步 objective 设计应去掉或解耦不可操作的 latency 压力，并保护 file-recall/gold-file utility。不要从 FD2-A 运行 FD2-B，不要复活 role proxy，不要调 v0.31/v0.32 权重。

## 2026-06-24 — BEA-v1-P1：可行动性审计与 Oracle 上限检查

### 目标

正式以 hierarchical/actionability-aware 研究线启动 BEA v1，而不是继续修 BEA v0.4。将 FD1 failure categories 映射到真正能因果影响它们的 action layers，并从 FD1 evidence 计算诚实 oracle ceilings。不运行 selector，不调权重，不复活 role proxy，也不从聚合 latency 推断上限。

### 实现 / 验证

- Local checkpoint `6e661f1` 新增 `eval/bea_v1_p1_actionability_audit.py`、manual workflow、aggregate artifact 与 en/zh docs。
- CI 修复 `b63db2a` 将 FD1 private replay 输出从 `$RUNNER_TEMP` 改到 `/tmp/...`，以满足已有 private-dir safety rule。
- CI 修复 `9c72ae2` 将 FD1 private decomposition 分组从单独 `private_record_id` 改为 `(source_phase, private_record_id)`，避免 BEA-4/BEA-5 ID 碰撞（错误 192 组 -> 正确 239 组）。
- Self-test 596/596；默认无私有 artifact 如实为 `no_go_ceiling_unavailable`。

### Manual CI 结果

Manual CI run `28076434237` 绿色完成。Workflow 在 `/tmp/bea_v1_p1_fd1_private_28076434237` 重新生成 FD1 private decomposition，验证 FD1 replay artifact（`bea_fd1_decomposition_pass`），解析 86040 条 private decomposition rows，恢复 239 个 composite record groups，并发布 aggregate-only public artifact。

Status 为 `no_go_retrieval_availability_limit`。Actionability matrix 覆盖全部 12 个 FD1 categories × 6 个 action layers。File-selector ceiling 计算为 private lower bound + public upper bound：`gold_file_absent` denominator=119，recoverable lower-bound count=1，lower-bound rate=0.004184，upper-bound count=119，upper-bound rate=0.497908，unrecoverable candidate-unavailable lower-bound count=118，retrieval-availability rate=0.991597。

### 决定

不要基于这份 evidence 启动 BEA-v1-A coverage-preserving selector。Selector-only optimization 在 FD1 frame 上缺少足够 lower-bound upside；主导问题是 candidate availability / retrieval reach，而 span/refiner 与 stopping ceilings 仍诚实不可用，因为 FD1 缺少必要 trace 字段。

## 2026-06-24 — BEA-v1-P2：候选可用性 / 检索可达性冒烟

### 目标

回应 BEA-v1-P1 的 retrieval-availability No-Go：测试 runtime-clean retrieval expansion 是否能让 119 条 `gold_file_absent` 分母中的文件变得可达。这不是 selector，不是 FD2-B，不是 v0.4 repair，不是 provider/model 实验，也不是 latency-weighted candidate score。

### 实现 / 验证

- Local checkpoint `2940750` 增加 `eval/bea_v1_p2_candidate_availability_reach_smoke.py`、manual workflow、aggregate artifact 与 en/zh docs。
- CI 修复 `d0daee7` 更正 RRF retrieval flag（`openlocus retrieve --max-results`，不是 `--limit`）。
- CI 修复 `d4de762` 强化 runtime-safe queries：regex 使用 literal-escaped public task text，symbol 使用安全 identifier token，RRF 从 bm25/regex/symbol ranks 派生，而不是把原始 issue text 传给 `openlocus retrieve`。
- Self-test 278/278；默认无网络 artifact 仍诚实为 `unavailable_with_reason`。

### Manual CI 结果

Manual CI run `28093864524` 完成 green。workflow 在 `/tmp` 下重建 FD1 private decomposition，验证 replay，在 119 条 `gold_file_absent` 分母上运行 4 个 retrieval-reach arms，写出 476 条私有 reach 行，并只上传 aggregate public artifact。

状态为 `no_go_retrieval_reach_latency_or_pool_cost`。Baseline current pool 达到 32/119 文件。Depth-only expansion 达到 59/119（新增 27；availability lift 0.226891；pool 3.41×；latency 1.18×）。Query-anchor variants 达到 60/119（新增 28）但违反 pool/latency safety。Combined depth+query 达到 81/119（新增 49；lift 0.411765），但 pool 10.13×、latency 3.89×，违反 safety gate。

### 决策

Candidate availability 可被实证改善，但 naive broad expansion 成本过高。不要从 combined arm 启动 BEA-v1-A selector。下一步 BEA v1 应是 constrained retrieval policy：保留 depth-only 增益，同时约束 pool size 和 latency。Latency 继续不进入 candidate relevance scoring；它属于 retrieval/action scheduling safety，而不是 candidate scoring。

## 2026-06-24 — BEA-v1-P3：受约束检索策略冒烟

### 目标

测试 P2 之后第一个真正的 BEA v1 retrieval-action policy：保留大部分 P2 depth-only candidate-availability 增益，同时约束 pool/latency。这不是 selector，不是 default/promotion，不是 FD2-B/v0.4 repair，latency 也不作为 candidate relevance。

### 实现 / 验证

Local checkpoint `6801e2b` 增加 `eval/bea_v1_p3_constrained_retrieval_policy_smoke.py`、manual CI workflow、默认诚实 no-network artifact 与 en/zh docs。@oracle 在第一次本地 review 中阻塞，因为 `no_go_p3_replay_mismatch` 仍被列为 CI-valid；修复后它已从 real-run statuses 移除，self-test 更新为 365/365，并被文档定义为 default/replay failure only。

### Manual CI 结果

Manual CI run `28102428194` 以 1h22m03s 完成 green。它在 `/tmp` 下重建 FD1 private decomposition，验证 replay，在 119 条 `gold_file_absent` 分母上运行 3 个 P3 arms，写出 357 条私有 policy 行，并只上传 aggregate public artifact。

状态是 `no_go_p3_cost_exceeded`。Baseline 达到 32/119（mean pool 19.98，latency 1.677s）。P2 depth reference 达到 59/119（新增 27，pool 68.18 / 3.41×，latency 1.991s / 1.19×）。P3 constrained policy 达到 58/119（新增 26，availability lift 0.218487），mean pool 41.50（2.08×），latency 3.645s（2.17×）。Pool safety 通过；latency safety 失败。P3 efficiency 很强（1.208122），并保留 selector relevance（mean first-gold rank 25.69；50 条记录超过 budget）。

### 决策

Constrained retrieval-action scheduling 在 reach 与 pool efficiency 上有希望，但这个具体 sequential scheduler 失败于 latency safety。不要将其推进为 v1-A 输入。下一步应隔离为何候选更少仍耗时更高，并在 retrieval-action 层测试 latency-aware action scheduler，同时不把 latency 放入 candidate relevance scoring。

## 2026-06-24 — BEA-v1-P4：延迟感知检索动作调度器冒烟

BEA-v1-P4 在 P3 证明 constrained-retrieval 机制真实但 latency safety 失败之后
运行。该阶段保留 119 条 FD1 `gold_file_absent` 分母，并比较四个固定 arms：
current pool、P2 depth-only reference、P3 constrained reference，以及 P4
runtime-clean latency-aware action scheduler。Latency 仅用于 retrieval-action
scheduling / stop 和 cost gates，绝不进入 candidate relevance scoring。

Local checkpoint `87a266a` 添加 evaluator/workflow/docs。Commit `3ffeb23`
在一次 fail-closed run 证明需要保留 aggregate report 后，加入 diagnostic
prevalidation upload。Manual CI run `28118888584` 以 1h23m50s 完成 green，
在 `/tmp` 下重建 FD1 private decomposition，验证 239 / 86040 replay rows，
运行 P4 scheduler smoke，在 `/tmp` 下写出 476 条私有 scheduler rows，并仅
发布 aggregate records。

结果 status：`bea_v1_p4_latency_aware_retrieval_scheduler_pass`。

观测 reach/cost：

- Baseline：32/119 reachable，pool 19.983193，latency 1.799924s。
- P2 depth-only reference：59/119 reachable（新增 27），pool 68.184874
  （3.412111×），latency 2.124798s（1.180493×）。
- P3 constrained reference：58/119 reachable（新增 26），pool 41.512605
  （2.077376×），latency 3.906403s（2.170315×），复现 P3 failure。
- P4 scheduler：56/119 reachable（新增 24），availability lift 0.201681，
  pool 41.092437（2.056350×），latency 3.149319s（1.749695×），hard-cap
  violations 0。

解释：P4 保留了 P2 depth-only reach gain 的至少 75%，同时修复了 P3 的
latency failure（相比 P3 latency 降低 19.3806%，且低于 2.0× baseline）。
这验证 retrieval-action scheduling 是 runtime-clean candidate-availability lever。
它仍不是 method-winner/default/runtime-promotion 声明，也没有解决 selector
relevance：mean first reachable gold rank 仍为 25.625，48 条记录仍超出 budget。

## 2026-06-24 — BEA-v1-P4H：不相交调度器验证

### 目标

在不相交 raw external heldout file-miss 分母上验证冻结 P4 latency-aware
retrieval-action scheduler。这不是 selector/reranker 阶段，不是 P5，也不是 default/
promotion 声明。Latency 仍只作为 retrieval-action scheduling/cost 信号，绝不作为
candidate relevance。

### 实现 / 验证

Local checkpoint `dee1ce1` 新增 `eval/bea_v1_p4h_disjoint_scheduler_validation.py`、
manual workflow、aggregate artifact 与 en/zh docs。第一次 fixed-tail CI 尝试失败，
原因是 ContextBench offset 480 与 RepoQA offset 240 都取不到 raw rows。Commit
`0dfeb27` 将其改为 full-frame disjoint success-quota scan：从可用 raw rows 开始，
排除 FD1 private replay 中 BEA-4/5 的精确 prior raw keys，在 treatment arms 之前构造
baseline file-miss denominator，并在不足 80 条 heldout file-miss 时 fail closed。

### Manual CI 结果

Manual CI run `28132121958` 绿色完成，并产出有效 aggregate No-Go artifact。Status 为
`no_go_p4h_insufficient_denominator`，不是 scheduler pass。

Workflow 在 `/tmp` 下重建 FD1 private decomposition，验证 239 / 86040 replay，并运行
full-frame raw external 不相交扫描。精确 prior-key 排除移除了 239 条 BEA-4/5 raw
records。扫描取到 266 条 ContextBench rows 与 100 条 RepoQA rows，排除 162 条
ContextBench + 77 条 RepoQA exact prior records，尝试 104 条 ContextBench + 23 条
RepoQA rows，最终只找到 73 条 baseline file-miss heldout denominator records：
ContextBench 61，RepoQA 12。

P4H 硬性分母 gate 保持 80，因此 evaluator 未运行 P2/P3/P4 scheduler arms：
`retrieval_policy_executed=false`，`private_scheduler_rows=0`，
`expected_private_scheduler_rows=0`。`forbidden_scan.status=pass`，self-test 为 69/69，
且没有 provider calls。

### 决策

P4H 没有在不相交 heldout 分母上验证 P4。它也不推翻 P4 的 119-record same-frame pass：
本次 No-Go 的具体含义是，在精确排除 prior 后，可用的不相交 ContextBench/RepoQA frame
只产出 73/80 条 baseline file-miss heldout records。不要从 P4H 进入 P5 selector/
reranker、BEA-v1-A、runtime promotion、method-winner 声明或 broad retrieval expansion。

## 2026-06-24 — BEA-v1-P4I：不相交分母蓄水池审计

### 目标

审计 P4H denominator blocker 是 sampling artifact，还是当前受支持 ContextBench/RepoQA
Python frame 中真实的 source/reservoir limitation。P4I 仅是 denominator/source audit。
它不运行 scheduler arms、selector/reranker 逻辑、retrieval expansion、provider calls 或
P5/v1-A。

### 实现 / 验证

Local checkpoint `a834733` 新增 `eval/bea_v1_p4i_disjoint_denominator_reservoir_audit.py`、
manual CI workflow、aggregate artifact 与双语 docs。Local review 期间，审计被收紧：
network-enabled run 必须使用 FD1 中的 exact BEA-4/5 prior exclusion；P4H exact-key
overlap 被显式标为 unresolved（`p4h_overlap_resolved=false`）；除非 reservoir 被证明为
qualified all-prior-disjoint，否则 reservoir upper bound 不能授权 frozen P4H rerun。
Self-test count 为 811/118。

### Manual CI 结果

Manual CI run `28137455572` 绿色完成，用时 1h09m47s。公开 artifact 是有效 aggregate
No-Go，`status=no_go_disjoint_denominator_reservoir_insufficient`。

Workflow 在 `/tmp` 下重新生成 FD1 private decomposition，验证 239 / 86040 replay，并运行
P4I full-frame reservoir audit。它取到 366 条 raw rows，从 FD1 精确排除 239 条 BEA-4/5
prior raw keys，尝试 127 条非 prior candidate rows，观察到 54 条 baseline-reached rows，
只找到 73 条 FD1-excluded file-miss reservoir records。FD1-excluded upper bound 为
73/80；`qualified_denominator_reservoir_count=0`，因为 P4H 的 73 条 exact selected keys
没有提交，overlap 仍未解决。`forbidden_scan.status=pass`。

### 决策

P4I 确认 P4H denominator blocker 不只是 fixed-tail sampling。当前受支持
ContextBench/RepoQA Python frame 在 exact prior exclusion 后仍只产出 73/80 条
FD1-excluded file-miss reservoir records。不要从 P4I 运行 frozen P4H rerun、P5
selector/reranker、BEA-v1-A、runtime promotion、method-winner 声明或 broad retrieval expansion。

## 2026-06-24 — BEA-v1-P4J：Cross-Source File-Miss Reservoir Unlock Audit

### 目标

审计 P4H/P4I denominator blocker 是否只属于当前受支持 ContextBench/RepoQA Python
frame，还是 already-supported cross-source frames 能解锁更大的 file-miss reservoir。
P4J 仅是 source/denominator audit；不运行 scheduler arms、selector/reranker、
retrieval expansion、provider calls、frozen P4 rerun、P5 或 BEA-v1-A。

### 实现 / 验证

Local checkpoint `18671d8` 新增
`eval/bea_v1_p4j_cross_source_reservoir_unlock_audit.py`、manual workflow、聚合
artifact 与双语 docs。审计只使用两个 already-supported source frames：ContextBench
`contextbench_verified/train` + `language_filter=all`，以及 RepoQA non-Python asset
languages（直接解析，因为 c5d CLI 只允许 Python）。

第一次 network run `28141276171` fail-closed，因为 evaluator 把内部 scan exception
吞成 `unexpected_exception`，缺少可行动聚合诊断。Commit `18126f4` 加入 safe scan
diagnostic records 和 row/frame fail-closed handling，但不降低 validator：network-enabled
有效状态仍不包括 `fail_schema_contract` 或 `unavailable_with_reason`。

### Manual CI 结果

Manual network-enabled CI run `28146407493` 绿色完成（1h46m38s）。公开 artifact 是
有效 aggregate No-Go，`status=no_go_cross_source_reservoir_unqualified`。

P4J 找到了较大的 FD1-excluded upper-bound file-miss reservoir：取到 780 rows，尝试
618 rows，排除 162 条 FD1 BEA-4/5 exact prior raw keys，观察到 285 条 baseline-reached
rows，并选出 333 条 file-miss rows。Upper-bound reservoir 包含 197 条 ContextBench
all-language records 和 136 条 RepoQA non-Python records（`cross_source_non_python_reservoir_count=272`，
`cross_source_python_reservoir_count=61`）。Private reservoir scan rows 只写在 `/tmp`
（`record_count=618`）；公开 artifact 保持 aggregate-only，`forbidden_scan.status=pass`。

### 决策

P4J 证明 source story 不止当前 Python frame：存在 333-record cross-source upper-bound
reservoir。但它不具备 locked P4 validation 资格，因为 P4H/P4I exact selected keys
仍不可用/仅 aggregate-only（`p4h_p4i_overlap_resolved=false`，
`qualified_cross_source_reservoir_count=0`）。因此 P4J 不授权 locked-P4 scheduler
validation、frozen P4 rerun、P5 selector/reranker、BEA-v1-A、runtime promotion、
method-winner 声明或 broad retrieval expansion。

## 2026-06-25 — BEA-v1-P4K：Exact Overlap Resolution & Locked Reservoir Audit

### 目标

通过从相同确定性协议和 FD1 private replay 重建 P4H、P4I、P4J 的 exact selected
raw-key sets，解决 P4J 的唯一 blocker：P4H/P4I exact-overlap uncertainty。P4K 仅是
overlap/locked-reservoir audit；不运行 scheduler arms、selector/reranker、retrieval
expansion、provider calls、frozen P4 rerun、P5 或 BEA-v1-A。

### 实现 / 验证

Local checkpoint `c6b7fc9` 新增
`eval/bea_v1_p4k_exact_overlap_resolution_locked_reservoir_audit.py`、manual CI
workflow、聚合 artifact 与双语 docs。Local review 移除了 hardcoded locked-count
expectation，要求 P4J reconstruction 匹配 committed 333 total 与 61 Python / 272
non-Python split，将 raw parse / clone / retrieval / unexpected failures 设为 blocking
fail-closed，并稳定 ready status/authorization fields。Self-tests 为 106/106。

### Manual CI 结果

Manual network-enabled CI run `28151914531` 绿色完成（1h50m01s）。公开 artifact
status 为 `cross_source_locked_reservoir_ready_for_locked_p4_validation_design`。

P4K 重建 P4H `73/73`、P4I `73/73`、P4J `333/333`，split 为 61 Python + 272
non-Python。Exact overlap 发现 P4J 的 61 条 Python rows 全部与 P4H/P4I Python-frame
reservoir 重叠，留下 post-overlap locked cross-source reservoir `272/80`，全部来自
non-Python。Artifact `forbidden_scan.status=pass`，exact keys/private reconstruction
rows 只保存在 `/tmp`。

### 决策

P4K 解决了 P4J 的 unqualified-reservoir blocker，并且只授权设计后续
locked-denominator P4 validation phase。它没有执行该 validation：
`scheduler_validation_authorized=false`，`locked_p4_validation_executed=false`，
`frozen_p4_rerun_authorized=false`，`p5_authorized=false`，`v1_a_authorized=false`。
不要从 P4K 进入 P5、BEA-v1-A、runtime promotion、method-winner 声明或 broad
retrieval expansion。

## 2026-06-25 — BEA-v1-P4L：Locked Non-Python P4 Scheduler Validation

### 目标

验证 frozen BEA-v1-P4 retrieval-action scheduler 是否能泛化到 P4K 锁定的 non-Python
cross-source denominator。P4L 仅是 scheduler validation：不做 selector/reranker、P5、
BEA-v1-A、provider calls、参数调优、阈值搜索、新 arms、broad retrieval expansion，
也不做 runtime/default promotion。

### 实现 / 验证

Local checkpoint `5922826` 新增
`eval/bea_v1_p4l_locked_non_python_scheduler_validation.py`、manual workflow、聚合默认
artifact 与双语 docs。Follow-up checkpoint `251ae2b` 将 live denominator drift 分类为
有效 No-Go `no_go_p4l_locked_denominator_unavailable`。Checkpoint `6034b3d` 修正
P4-treatment hard-cap gate：P4L 会报告 reference-arm hard-cap violations，但 frozen P4
gate 只约束 P4 treatment arm。Checkpoint `e98839b` 在一次长 evaluator step 没有 artifact/
output 后加入 CI heartbeat wrapper。Self-tests 为 122/122。

### Manual CI 结果

Manual network-enabled CI run `28184096209` 绿色完成（2h33m08s），status 为
`bea_v1_p4l_locked_non_python_scheduler_validation_pass`。

P4L 精确重建 P4J/P4K（`333/61/272`），并将 non-Python denominator 锁定为 272。它执行
四个 frozen arms，并只在 `/tmp` 写出 1088 条 private arm-outcome rows。公开聚合 arm
metrics：

| Arm | Reach | Mean pool | Mean latency | Hard-cap violations |
|---|---:|---:|---:|---:|
| baseline current pool | 0/272 | 13.871324 | 2.059338s | 0 |
| P2 depth-only reference | 55/272 | 53.084559 | 1.863294s | 3 |
| P3 constrained reference | 55/272 | 31.058824 | 3.626279s | 0 |
| frozen P4 latency-aware scheduler | 52/272 | 30.194853 | 2.381607s | 0 |

Frozen P4 scheduler 保留 P2 depth-only reach gain 的 `0.945455`，相对 P3 降低 latency
（`p4_vs_p3_latency_ratio=0.656763`，`p4_latency_reduction_vs_p3=0.343237`），保持在
pool gate 内（`p4_pool_growth_ratio=2.176782`），并且 P4-treatment hard-cap violations
为 0。P2 的 3 次 hard-cap violations 只是 reference diagnostics。
`forbidden_scan.status=pass`。

### 决策

P4L 验证 frozen P4 retrieval-action scheduler 在 locked non-Python denominator 上成立。
它仍不授权 P5 selector/reranker、BEA-v1-A、runtime/default promotion、method-winner
声明、frozen P4 rerun 或 broad retrieval expansion。

## 2026-06-26 — BEA-v1-N1：Frozen P4 + Span-Refiner Smoke

### 目标

执行 Report 4 的第一个 span 阶段，同时不改变 frozen P4 scheduler：重放 FD1，重建
P4L/P4K locked non-Python denominator，验证 D0 scheduler preservation，形成私有
rank-aware wrong-span denominator，并测试 file-preserving post-P4 span refiner。N1
不是 selector/reranker、P5、BEA-v1-A、downstream-agent evaluation、runtime promotion
或 method-winner 声明。

### 实现 / 验证

Local checkpoint `c77f8d1` 新增
`eval/bea_v1_n1_frozen_p4_span_refiner_smoke.py`、manual workflow、聚合默认 artifact
与双语 docs。后续 checkpoint 依次加入 safe failure diagnostics（`9c6cd41`）、绝对
openlocus binary 解析（`c51d20b`）、全文件同文件 line-window refiner（`e04b2fa`）、
rank-aware D1 total/top-10/rank-blocked accounting（`6b152d2`），以及 auxiliary
line-label lookup 分类修复（`0ddc2e8`）。Self-tests 为 52/52。

### Manual CI 结果

Manual network-enabled CI run `28245155237` 绿色完成（2h33m52s），status 为
`no_go_n1_inadequate_top10_actionable_denominator`。

D0 replay 在 locked 272-record non-Python denominator 上复现 P4L scheduler 结果：
baseline `0`，P2 `55`，P3 `55`，P4 `52`，P4 treatment hard-cap violations `0`。
D1 total / pool span-opportunity 充分，为 `40`，但 D1 top-10 actionable 为 `0`，D1
rank-blocked 为 `40`。全文件同文件 refiner 在局部 gold-file span 上改善 8/40，退化
0/40，但 40 条全部在 top-10 之外。公开 sanitized rows 仅匿名/桶化；
`forbidden_scan.status=pass`。

### 决策

N1 是 span-only repair 的有效 No-Go，不是 refiner pass。瓶颈已经从同文件 line
refinement 转移到 rank/pack actionability：必须先把 gold-file evidence 移入 actionable
top-10 pack，canonical `SpanF0.5@10` 才能给 file-preserving span refiner 记功。不要从
N1 跳到 P5 selector/reranker、BEA-v1-A、runtime/default promotion、method-winner 声明
或 broad retrieval expansion。

## 2026-06-27 — BEA-v1-N2：Rank/Pack Actionability Decomposition

### 目标

在不实现 selector/reranker、不改变 frozen P4 的前提下，分解 N1 的 40 条 rank-blocked
records。N2 绑定 closed N1 的 D0 scheduler-preservation artifact，在 `/tmp` 下重新生成
FD1 private traces，重建 locked denominator，并只重放 D2 所需的 ordered frozen-P4 candidate
路径。

### 实现 / 验证

Local checkpoints：`e4c4d54`（N2 实现）、`e1406a5`（CI 磁盘稳定性修复：绑定 N1 D0，
避免重复完整 P4L 四臂验证）、`7c90213`（当 D2=40 完整时，candidate-order-unavailable
作为诊断而非阻断）、`a5b519b`（从 N1 artifact 继承非 gating D0 latency 展示字段）。
Self-tests 为 28/28。

### Manual CI 结果与修正 provenance

Manual CI run `28272769423` 在 checkpoint `7c90213` 上生成有效 empirical N2 artifact。
写回前发现一个公开 D0 展示 bug：`p4_p3_latency_ratio_observed` 被打印为 `0.0`，而
closed N1 artifact 记录为 `0.662177`。已提交 artifact 只做这一项 records-only、非 gating
修正；D2 counts、sanitized rows、design scope、failure categories、manifests 均未改变。代码
checkpoint `a5b519b` 修复了该 bug。Rerun `28275921872` 与 `28277110197` 在有效 N2
结果生成前分别因 transient locked-denominator reconstruction / FD1 前置失败而失败，因此不构成
对 CI `28272769423` 的反证。

### 结果

Status：`n2_rank_pack_actionability_decomposition_pass`。D2 精确重建（`40/40`），且所有
rows 已分类。First gold-file rank bucket 为 `rank_21_50=40/40`。Top-20 recovery 为
`0/40`；top-50 与 top-100 recovery 均为 `40/40`；unique-file top-10 recovery 为
`0/40`；evidence materializable 为 `40/40`；hard-cap violations 为 `0`；scanner status
为 `pass`。

Primary blocker：`extra_depth_append_blocked=40/40`。

### 决策

N2 只授权 extra-depth merge-order design。它不授权 implementation、P5 selector/reranker、
BEA-v1-A、selector/reranker execution、runtime/default promotion、method-winner 声明、
broad retrieval expansion、downstream-value 声明或 frozen P4 rerun。

## 2026-06-27 — BEA-v1-N3：Extra-Depth Merge-Order Design Simulation

### 目标

测试 N2 授权的 design-only follow-up：简单 frozen、deterministic extra-depth merge-order
simulations 能否在不改变 candidate pool、不运行新 retrieval、selector、reranker、P5、
BEA-v1-A、provider calls、learned weights 或 gold-based policy 的前提下，把 40 条 D2
records 从 rank 21-50 移入 top-10。

### Manual CI 结果

Local checkpoint `76ebd32` 新增 evaluator/workflow/default artifact/docs。Manual CI
`28278662782` 绿色完成，public status 为 `n3_merge_order_design_inconclusive`。

Validated artifact 精确重建 D3（`40/40`），private manifests 只写在 `/tmp`，public scan
通过。Simulation outcomes：

- frozen P4 order：`0/40` recovered into top-10；
- fixed interleave 2-primary/1-extra after 4：`8/40`；
- early extra-depth quota 3：`10/40`；
- bounded promotion after primary prefix 4/3：`10/40`。

最佳 recovery rate 为 `0.25`，低于 `0.50` pass gate。两个最强 arms 的 retention 为
`0.975`，recovered materialization rate 为 `1.0`，hard-cap violations 为 `0`，所以
cost/retention 不是 blocker；recovery 本身太低。

### 决策

N3 不是 pass，不授权 implementation、P5、BEA-v1-A、selector/reranker execution、
runtime/default promotion、method-winner 声明、broad retrieval expansion、downstream-value
声明或 frozen P4 rerun。N3 测试的简单 bounded merge-order designs 对 N2 rank/pack
blocker 不足。

---

## 2026-06-27 — BEA-v1-P0-1：Trace Gap Audit

### 目标

将 N3 之后的状态转换为后续研究 agent 可直接复盘的 trace-surface audit。本阶段只读取已提交的
FD1、P1、FD2-A1、P4L、N2 与 N3 public artifacts，并发布经过 scanner 验证的 sanitized
per-gap rows。它不运行 retrieval、provider、selector、reranker、P5、BEA-v1-A、runtime
promotion、broad retrieval expansion 或 downstream-value evaluation。

### 结果

`eval/bea_v1_trace_gap_audit.py` 生成
`artifacts/bea_v1_trace_gap_audit/bea_v1_trace_gap_audit_report.json`，status 为
`trace_gap_audit_pass`。Self-test 通过 `5/5`，forbidden scan 通过，并覆盖全部 12 个
FD1 categories。

Trace availability summary：

- `sanitized_available`：3；
- `private_only_needs_public_export`：3；
- `missing_label`：3；
- `missing_trace`：2；
- `aggregate_only_insufficient_for_deep_research`：1。

### 解释

N2/N3 已为 rank/pack 与 merge-order 复盘提供 sanitized rows，但更完整的 BEA-v1 机制面仍然
trace 不完整。当前直接数据面缺口是 action-cost scheduler export、support-link labels、same-file
redundancy trace、risk-penalty trace 与 ordered-prefix stop trace。

### 决策

P0-1 只授权 trace/data-surface 工作：actionability-matrix refresh、sanitized P4/P4L scheduler
dataset export、support-link labeling inputs，以及 redundancy、risk-penalty、ordered-prefix stop
traces 的保留/导出。它不授权 implementation、P5、BEA-v1-A、selector/reranker execution、
runtime/default promotion、method-winner 声明、broad retrieval expansion、downstream-value 声明
或 frozen P4 rerun。

---

## 2026-06-27 — BEA-v1-P0-2：Actionability Matrix Refresh

### 目标

用 P0-1 trace-readiness evidence 刷新 P1 的 12-category × 6-action-layer actionability
matrix，同时保持 P1 是 causal matrix 来源。本阶段只是 artifact join：不运行 retrieval、provider
calls、selector/reranker execution、FD1 replay、runtime change 或 policy implementation。

### 结果

`eval/bea_v1_p0_2_actionability_matrix_refresh.py` 生成
`artifacts/bea_v1_p0_2_actionability_matrix_refresh/bea_v1_p0_2_actionability_matrix_refresh_report.json`，
status 为 `actionability_matrix_refresh_pass`。Self-test 通过 `22/22`，forbidden scan 通过，
全部 72 个 matrix cells 已刷新，且 P1 causal cell classes 未被修改。

Cell readiness summary：

- `ready_sanitized_trace`：10；
- `blocked_private_export`：11；
- `blocked_missing_label`：18；
- `blocked_missing_trace`：12；
- `blocked_aggregate_only`：3；
- `not_applicable_by_layer`：18。

### 决策

P0-2 确认下一步 BEA-v1 工作是 trace/data-surface work，而不是 policy implementation。授权的
follow-ups 是 sanitized scheduler dataset export、support-link input design，以及 redundancy/risk/
ordered-prefix stop trace preservation。P0-2 不授权 P5、BEA-v1-A、selector/reranker execution、
runtime/default promotion、method-winner 声明、broad retrieval expansion、downstream-value 声明或
frozen P4 rerun。

---

## 2026-06-27 — BEA-v1-P0-3：Scheduler Dataset Export

### 目标

导出 P0-1/P0-2 要求的 scheduler/action-cost data surface。本阶段 join 已提交的 P4L 与 P0-2 artifacts，并可选接受项目内 ignored directory 中匹配的 private P4L arm rows。它不运行 retrieval、provider calls、selector、reranker、threshold tuning、runtime changes 或 policy implementation。

### 结果

`eval/bea_v1_p0_3_scheduler_dataset_export.py` 生成 `artifacts/bea_v1_p0_3_scheduler_dataset_export/bea_v1_p0_3_scheduler_dataset_export_report.json`，status 为 `scheduler_dataset_export_contract_pass`。Self-test 通过 `11/11`，forbidden scan 通过，artifact 包含 4 条 sanitized aggregate scheduler arm rows、12 条 sanitized subgroup denominator rows，以及 P0-2 action-cost join rows。

Full private arm-row export 仍为 optional，本轮没有满足，因为历史 P4L private JSONL 是在之前环境生成的。后续 private rows 应在 `.openlocus/research-private/` 下生成或恢复，并通过 `--private-arm-outcomes-jsonl` 提供。

### 决策

P0-3 补齐了 aggregate scheduler/action-cost contract。剩余实践分叉是：在项目内 private directory 恢复/重跑 P4L private arm rows，或转向 18 个 `blocked_missing_label` cells 的 support-link input design。P0-3 不授权 P5、BEA-v1-A、selector/reranker execution、runtime/default promotion、method-winner 声明、broad retrieval expansion、downstream-value 声明或作为质量声明的 frozen P4 rerun。

---

## 2026-06-27 — BEA-v1-P0-4：Support-Link Input Design

### 目标

将 P0-1/P0-2 的 support-link missing-label 缺口转换为 scanner-validated labeling input contract。本阶段 join P0-1 的 `support_link_trace` gaps 与 P0-2 的 `blocked_missing_label` cells。它不标注 private rows，不运行 retrieval，不调用 provider，不执行 counterfactual，不运行 selector/reranker，也不实现 policy。

### 结果

`eval/bea_v1_p0_4_support_link_input_design.py` 生成 `artifacts/bea_v1_p0_4_support_link_input_design/bea_v1_p0_4_support_link_input_design_report.json`，status 为 `support_link_input_design_pass`。Self-test 通过 `11/11`，forbidden scan 通过，artifact 包含 18 条 sanitized support-link design records 与 6 个 labeling contract fields。

所有 target/support hit states 仍为 `unknown_not_labeled`；该 artifact 是 input contract，不是 labeled dataset，也不是 support marginal-utility result。

### 决策

P0-4 只授权 support-link labeling input work。后续 phase 可以使用该 contract 标注 private rows，然后再判断是否执行 support counterfactual。P0-4 不授权 P5、BEA-v1-A、selector/reranker execution、runtime/default promotion、method-winner 声明、broad retrieval expansion、downstream-value 声明或 support counterfactual execution。

---

## 2026-06-27 — BEA-v1-P0-5：Support-Link Labeling Harness

### 目标

将 P0-4 的 support-link input contract 转换为 private labeling harness。该 harness 可以生成未标注的项目内 private JSONL template，也可以验证已完成的 private label JSONL，同时不把 private paths、raw rows、snippets、candidates、ranks、scores 或 source-linkable data 序列化进 public artifact。

### 结果

`eval/bea_v1_p0_5_support_link_labeling_harness.py` 生成 `artifacts/bea_v1_p0_5_support_link_labeling_harness/bea_v1_p0_5_support_link_labeling_harness_report.json`，status 为 `support_link_labeling_harness_contract_pass`。Self-test 通过 `21/21`，forbidden scan 通过，public artifact 包含 18 条 sanitized harness records 与 private-template manifest。Private template 已生成到 `.openlocus/research-private/`，该目录被 git ignore。

本轮未提供 private labels，因此 optional full private-label validation gate 仍为 false。

### 决策

P0-5 只授权 private support labeling 或 private label validation。它不授权 support counterfactual execution、support marginal-utility 声明、P5、BEA-v1-A、selector/reranker execution、runtime/default promotion、method-winner 声明、broad retrieval expansion 或 downstream-value 声明。

---

## 2026-06-27 — BEA-v1-P0-6/7/8：Parallel Trace Surfaces

### 目标

并行关闭剩余 P0 trace-surface contracts：same-file redundancy、risk-penalty removal 与 ordered-prefix stop decisions。本阶段读取 P0-1/P0-2 artifacts，输出 scanner-validated contract rows，并保持 private trace rows 为 optional 且本轮 absent。

### 结果

`eval/bea_v1_p0_6_7_8_parallel_trace_surfaces.py` 生成三个 reports：P0-6 status 为 `same_file_redundancy_trace_surface_contract_pass`，P0-7 status 为 `risk_penalty_trace_surface_contract_pass`，P0-8 status 为 `ordered_prefix_stop_trace_surface_contract_pass`。Self-test 通过 `5/5`，三个 reports scanner 均通过，每个 trace surface 包含 6 条 contract records。

这些 reports 定义 private schemas 与 public-safe bucket fields，但不填充 private trace rows。

### 决策

P0-6/7/8 只授权 trace-surface review 或 private trace validation。它们不授权 policy tuning、counterfactual execution、P5、BEA-v1-A、selector/reranker execution、runtime/default promotion、method-winner 声明、broad retrieval expansion 或 downstream-value 声明。

---

## 2026-06-27 — BEA-v1-P0-9：Readiness Consolidation

### 目标

将 P0-1 到 P0-8 汇总为单一 next-experiment gate，并防止 contract-pass artifacts 被误认为已填充的 mechanism evidence。

### 结果

`eval/bea_v1_p0_9_readiness_consolidation.py` 生成 `artifacts/bea_v1_p0_9_readiness_consolidation/bea_v1_p0_9_readiness_consolidation_report.json`，status 为 `readiness_consolidation_pass_labeling_authorized_only`。Self-test 通过 `5/5`，forbidden scan 通过，检查 8 个 P0 inputs。

所有 P0 inputs 都可以加载、status 符合预期，并通过 scanner。但是后段 P0 surfaces 仍为 contract-only：scheduler private arm rows、support labels、same-file redundancy traces、risk-penalty traces 与 ordered-prefix stop traces 尚未填充为 private rows。

### 决策

P0-9 只授权 private labeling 或 private trace validation。它不授权 support counterfactual execution、trace counterfactuals、policy tuning、P5、BEA-v1-A、selector/reranker execution、runtime/default promotion、broad retrieval expansion、method-winner 声明或 downstream-value 声明。

---

## 2026-06-27 — BEA-v1-P1-0：Support-Label Validator Dry Run

### 目标

在任何真实 private support labeling 或 support counterfactual work 前，用 synthetic private fixture 端到端验证 P0-5 private support-label harness。

### 结果

`eval/bea_v1_p1_0_support_label_validator_dry_run.py` 生成 `artifacts/bea_v1_p1_0_support_label_validator_dry_run/bea_v1_p1_0_support_label_validator_dry_run_report.json`，status 为 `support_label_validator_dry_run_pass`。Self-test 通过 `22/22`，forbidden scan 通过，18 条 synthetic private labels 通过 harness 验证。Synthetic fixture 写入 `.openlocus/research-private/`，并明确不是真实 label data。

### 决策

P1-0 授权使用已验证 schema 与 harness 进行真实 private support labeling。Support counterfactual execution 仍被阻断，直到真实 private labels 完整且 scanner-validated。P1-0 不授权 P5、BEA-v1-A、selector/reranker execution、runtime/default promotion、broad retrieval expansion、method-winner 声明、downstream-value 声明、support counterfactual execution 或 support marginal-utility 声明。

---

## 2026-06-28 — BEA-v1-P1-1：Private Labeling Queue Preparation

### 目标

基于 P0-4 design records 与 P1-0 已验证的 harness path，准备真实 project-private support-labeling queue，同时只发布 scanner-safe queue manifests 与 buckets。

### 结果

`eval/bea_v1_p1_1_private_labeling_queue_preparation.py` 生成 `artifacts/bea_v1_p1_1_private_labeling_queue_preparation/bea_v1_p1_1_private_labeling_queue_preparation_report.json`，status 为 `private_labeling_queue_preparation_pass`。Self-test 通过 `22/22`，forbidden scan 通过，并在 `.openlocus/research-private/` 下写入 18 条 queue records。

### 决策

P1-1 授权基于生成 queue 进行真实 private support labeling。它不授权 support counterfactual execution、support marginal-utility 声明、P5、BEA-v1-A、selector/reranker execution、runtime/default promotion、broad retrieval expansion、method-winner 声明或 downstream-value 声明。

---

## 2026-06-28 — BEA-v1-P1-2：Private Label Intake Validator

### 目标

为 P1-1 project-private queue 增加 fail-closed 的真实 private support labels intake validator，同时不伪造 labels，也不执行任何 support counterfactual。

### 结果

`eval/bea_v1_p1_2_private_label_intake_validator.py` 生成 `artifacts/bea_v1_p1_2_private_label_intake_validator/bea_v1_p1_2_private_label_intake_validator_report.json`，status 为 `private_label_intake_validator_contract_pass`。Self-test 通过 `11/11`，forbidden scan 通过，并从 `.openlocus/research-private/` 验证了 18 条 private queue records。

本轮未提供真实 private labels，因此有效真实 labels 仍为 `0/18`，counterfactual gate 仍保持 blocked。

### 决策

P1-2 只授权 private support-label intake validation。它不授权 support counterfactual execution、support marginal-utility 声明、P5、BEA-v1-A、selector/reranker execution、runtime/default promotion、broad retrieval expansion、method-winner 声明或 downstream-value 声明。

---

## 2026-06-28 至 2026-06-30 — BEA-v1 N-series roll-up：P1-2 到 N10ES

### 目标

把叙事日志补到当前研究状态。P1-2 之后项目进入大量细粒度 per-phase docs；详细事实以 per-phase docs 和 [`current-research-conclusions.md`](current-research-conclusions.md) 为准。本节只记录主线，不逐字复制所有 N10 子阶段。

### 结果

P1-2 之后的主线从 support-label intake 转到 N-series 实证研究：

- **恢复前置链路**：本地重建 FD1、P4L、N1、N2 private/replay inputs，把“缺输入”的阻塞变成可运行 fixed-pool 实验。
- **Support-label 与 trace-surface 后续分支**：P1-3 生成 automated support labels，但 P1-4/P1-5R 证明这些 labels 不够 informative，且 private context 不可重建。P2/P3 将 late trace gaps 收敛到 frozen trace-logger designs/proxy fixture audits，最终因为没有 existing empirical event source 而关闭 proxy 路线。
- **P4 locked-reservoir 线**：P4H/P4I/P4J/P4K 将 disjoint denominator/reservoir 问题收敛为 locked non-Python reservoir；P4L 在 272-record denominator 上验证 frozen P4 scheduler，但不授权 P5/runtime promotion。
- **N6XFR-E 到 N9**：修正 extra-depth 语义为真实 `rank>20` 规则，fixed-pool 最佳 arm 达到 top10 `25/40`。N7 审计，N8 独立复算，N9 公开打包。
- **N10 exact-denominator 分支**：N10/N10R 证明更大的 exact N2-equivalent rank-pack rows 在定义上已经耗尽，不能硬扩。
- **N10T span-surface proxy 分支**：改用 N1 span-surface proxy。file-level reach 有提升，但 N10X/N10Y/N10Z 证明 span utility gap 来自 same-file span-window misalignment。
- **Span-window repair 分支**：固定窗口和非对称窗口提升 span overlap；后续探索找到更强的 observable window rules。local-window 线最高到 `30/36` 后饱和，瓶颈转向 file reach。
- **Rank/file-reach 分支**：测试 distinct-file packing、deep-rank promotion、suffix-safe path matching。Deep-rank promotion 仍有害；oracle candidate ceiling 显示如果能补进缺失文件，上限很高。
- **Normalized-BM25 candidate-source 分支**：identifier-normalized BM25 找到旧池没有的新文件。novel-first depth-to-head repacking 产生同源正结果，fixed difference-aware rule 在 N10DZ/N10EB sample 上达到 `13/60`。
- **Public CI transfer 检查**：N10EN 在 GitHub Actions 上测试该 winner，结果为有效负结果：baseline top10 `39/40`，diffaware `37/40`，lost baseline top10 `2`。
- **Failure/safety-probe 链**：N10EO 诊断 N10EN regression 是 novel-first 推掉强 baseline hits；N10EP/N10EQ 设计 public safety probe；N10ER 在 held-out public CI sample 上运行后发现该 safety signal **没有复现**；N10ES 将其打包为 public-only audit。

最新相关提交：

```text
c8fd353 feat(eval): record N10ER CI safety probe result
8c04a0a docs(eval): package N10ER safety probe audit
```

### 决策

当前最新状态是 N10ES：

- N10ER CI run `28457213423` 在 `canary_small_heldout` 上成功。
- 状态：`n10er_safety_probe_complete_no_signal_reproduced_n10es_authorized`。
- 样本：`80` public tasks，`60` scored，`40` with gold，citation validity `7772/7772`，heldout overlap `0`。
- Arms：baseline `37/39/40/40`，full `36/39/40/40`，guard `38/39/40/40`，diffaware `37/39/40/40`。
- risk bucket 足够大（`26` tasks），但 low-novelty strong-baseline displacement signal 没复现：bucket 内 full/guard/diffaware losses 为 `0/0/0`。

N10ES 将其锁定为**有效 bounded public-CI research negative**，不是基础设施失败，也不是 promotion 证据。它只授权 **N10ET public design/decision**。不授权 N10ER rerun、threshold tuning、新 policy experiments、guard/full/diffaware promotion、runtime/default changes、method-winner claims、downstream/scaled retrieval、provider/model network 或 raw diagnostic publication。

详细当前状态见：[`current-research-conclusions.md`](current-research-conclusions.md)、[`bea-v1-n10er-bounded-public-ci-score-guard-safety-probe.md`](bea-v1-n10er-bounded-public-ci-score-guard-safety-probe.md)、[`bea-v1-n10es-public-safety-probe-audit-package.md`](bea-v1-n10es-public-safety-probe-audit-package.md)。


---

## 2026-06-30 — BEA-v1-N10ET：Public Safety Probe Design/Decision

### 目标

以 public-only design/decision 阶段收尾 BEA-v1-N10E safety-probe 分支，锁定 N10ES/N10ER public facts，记录收尾决策，并只授权下一 route。

### 结果

`eval/bea_v1_n10et_public_safety_probe_design_decision.py` 生成 `artifacts/bea_v1_n10et_public_safety_probe_design_decision/bea_v1_n10et_public_safety_probe_design_decision_report.json`，状态为 `n10et_public_safety_probe_design_decision_complete_haae_r0_authorized`。Self-test 通过 `74/74`，forbidden scan 通过，private input reads `0`，retrieval executions `0`，recomputes `0`，CI reruns `0`，candidate generations `0`。N10ES/N10ER source 已锁定：N10ES checkpoint `8c04a0a`，N10ER checkpoint `c8fd353`，CI run `28457213423`（head `2e7894e`），status `n10er_safety_probe_complete_no_signal_reproduced_n10es_authorized` 与 `n10es_public_safety_probe_audit_package_complete_n10et_authorized`，sample `80/60/40`，`overlap_zero`，citation `7772/7772`，baseline `37/39/40/40`，full `36/39/40/40` lost `1`，guard `38/39/40/40` lost `0`，diffaware `37/39/40/40` lost `1`，risk bucket `task_count=26`，losses `0/0/0`，`guard_would_preserve_full_loss_count=0` 均匹配。该阶段只读取 public artifacts/docs/current conclusions/research logs/README 与 git metadata；不进行任何 execution、private reads、CI rerun、retrieval/recompute 或 candidate generation。

记录三条收尾决策：BEA-v1-N10E/difference-aware 仍是 local same-source hypothesis；N10ER/N10ES 是有效 public held-out negative（有效 research negative，不是 CI failure）；不推广 guard/full/diffaware，不调阈值，不 rerun N10ER，不执行 CI variant，不执行 selector/reranker，不做新 policy experiment，不改 runtime/default，不 claim method-winner，不做 downstream/scaled retrieval，不发布 raw diagnostic。该阶段设计并只授权下一 route：**BEA-v1-HAAE-R0 —— Hierarchical Actionable Evidence Acquisition Route Design / Schema Preflight**，一个 public-only、design-only 的 schema preflight，明确 **不是** BEA-v1-A、不是 selector-only、不是 selector/reranker execution、不是 P5、不是 runtime/default promotion。

### 决策

N10ET 只授权 BEA-v1-HAAE-R0 Hierarchical Actionable Evidence Acquisition Route Design / Schema Preflight（public-only，design-only，不执行）。它不授权 N10ET/N10ES re-run、N10ER re-run/execution、任何 execution、rerun、retrieval、recompute、candidate generation、threshold tuning、新 policy experiments、frozen-rule changes、guard/full/diffaware promotion、runtime/default changes、method-winner claims、downstream/scaled retrieval、raw diagnostic publication、CI variant execution、selector/reranker execution、BEA-v1-A、P5、provider/model network 或 network runs。所有这类 stop/go 字段均为 `false`。HAAE-R0 non-identity booleans（`haae_r0_not_bea_v1_a_bool`、`haae_r0_not_selector_only_bool`、`haae_r0_not_selector_reranker_execution_bool`、`haae_r0_not_p5_bool`、`haae_r0_not_runtime_default_promotion_bool`）全部为 `true`。已关闭 N10E 分支的详细事实来源是 `current-research-conclusions.md` 与 per-phase N10EO/N10EP/N10EQ/N10ER/N10ES/N10ET docs。参见 `docs/zh/bea-v1-n10et-public-safety-probe-design-decision.md`。


---

## 2026-06-30 — BEA-v1-HAAE-R0：Hierarchical Actionable Evidence Acquisition Route Design / Schema Preflight

### 目标

以 public-only、design-only schema preflight（HAAE-R0）开启下一 acquisition route，锁定 N10ET 收尾事实，并在任何未来 execution-authorized 阶段开启之前，设计一个 machine-readable、非空的 control-plane（route architecture、unified private trace schema、public aggregation contract、arm specs、metric specs、held-out protocol、stop rules、synthetic validator、HAAE-R1 contract）。HAAE-R0 明确不是 BEA-v1-A、不是 selector-only、不是 selector/reranker execution、不是 P5、不是 runtime/default promotion。

### 结果

`eval/bea_v1_haae_r0_hierarchical_actionable_evidence_acquisition_design_schema_preflight.py` 生成 `artifacts/bea_v1_haae_r0_hierarchical_actionable_evidence_acquisition_design_schema_preflight/bea_v1_haae_r0_hierarchical_actionable_evidence_acquisition_design_schema_preflight_report.json`，状态为 `haae_r0_design_schema_preflight_complete_haae_r1_authorized`。Self-test 通过 `132/132`，forbidden scan 通过，private input reads `0`，retrieval executions `0`，recomputes `0`，CI reruns `0`，candidate generations `0`，arm scorings `0`，OpenLocus executions `0`。N10ET source 已锁定：checkpoint `26d817e`，status `n10et_public_safety_probe_design_decision_complete_haae_r0_authorized`，HAAE-R0 authorized true（`haae_r0_design_only_schema_preflight_authorized_bool`），HAAE-R0 execution false，BEA-v1-A false，P5 false，selector/reranker false，runtime/default false，且 N10ET HAAE-R0 non-identity booleans 全部匹配。该阶段只读取 N10ET public aggregate report 与 public docs/current-conclusions/research-log/summary/README + git metadata；不进行任何 execution、private reads、CI rerun、retrieval/recompute、candidate generation、arm scoring 或 OpenLocus execution。

该 artifact 带有 concrete machine-readable control-plane：`route_architecture_records`（4 个 layers —— source_acquisition、rank_pack_depth_to_head、span_projection、scheduler_operating_point，每个保留 EvidenceCore 并在 current-source evidence 不可用时 abstain）；`unified_private_schema_spec_records`（10 个 private-root-only、aggregate-bucket-only groups）；`public_aggregation_contract_records`（4 个 aggregations）；`arm_spec_records`（BM25_same_budget、RRF_same_budget、BEA_v0.3_frozen、V1_sched_span、V1_sched_span_rank —— same budget、不执行、不 scoring、不 tuning）；`metric_spec_records`（6 个 aggregate metrics）；`heldout_protocol_records`（overlap_zero、no gold-for-policy、不 materialize split）；`stop_rule_records`（4 个 abstain rules）；`synthetic_validator_records`（一个带有 4-task embedded synthetic fixture 的 validator，在进程内验证所有 contracts —— 不是 real data、不是 replay、不是 retrieval、不是 candidate generation）；以及 `haae_r1_contract_records`（HAAE-R1 contract）。记录六个 risk controls（HAAE-R0 drift into selector/P5/runtime、HAAE-R0 drift into execution、HAAE-R0 empty control-plane、HAAE-R1 scope creep beyond feasibility inventory、private diagnostic leakage、runtime/default creep）—— 全部已控制。

### 决策

HAAE-R0 只授权 BEA-v1-HAAE-R1 Unified Private Trace Schema Feasibility Inventory 交接（public-only、design-only、explicit private roots only、aggregate buckets only、no replay/scoring/retrieval/candidate generation）：`haae_r1_unified_private_trace_schema_feasibility_inventory_authorized_bool=true`、`haae_r1_execution_authorized_bool=false`、`haae_r1_replay_authorized_bool=false`、`haae_r1_scoring_authorized_bool=false`、`haae_r1_retrieval_authorized_bool=false`、`haae_r1_candidate_generation_authorized_bool=false`。它不授权 N10ET/N10ES re-run、N10ER re-run/execution、任何 HAAE-R0 execution、任何 execution、rerun、retrieval、recompute、candidate generation、arm scoring、OpenLocus execution、threshold tuning、新 policy experiments、frozen-rule changes、guard/full/diffaware promotion、runtime/default changes、method-winner claims、downstream/scaled retrieval、raw diagnostic publication、CI variant execution、selector/reranker execution、BEA-v1-A、P5、provider/model network 或 network runs。所有这类 stop/go 字段均为 `false`。HAAE-R0 non-identity booleans（`haae_r0_not_bea_v1_a_bool`、`haae_r0_not_selector_only_bool`、`haae_r0_not_selector_reranker_execution_bool`、`haae_r0_not_p5_bool`、`haae_r0_not_runtime_default_promotion_bool`）全部为 `true`。参见 `docs/zh/bea-v1-haae-r0-hierarchical-actionable-evidence-acquisition-design-schema-preflight.md`。

---

## 2026-06-30 — BEA-v1-HAAE-R1：Unified Private Trace Schema Feasibility Inventory

### 目标

对 10 个 HAAE-R0 unified private trace schema groups 是否能从显式提供的 project-private root buckets 中填充进行盘点，只输出 aggregate buckets。HAAE-R1 是 feasibility inventory，不是 replay/scoring/retrieval/candidate generation。默认 / no-private 模式不读取 private roots。

### 结果

`eval/bea_v1_haae_r1_unified_private_trace_schema_feasibility_inventory.py` 生成 `artifacts/bea_v1_haae_r1_unified_private_trace_schema_feasibility_inventory/bea_v1_haae_r1_unified_private_trace_schema_feasibility_inventory_report.json`，状态为 `haae_r1_feasibility_inventory_unavailable_no_explicit_private_roots`（默认 / no-private 模式）。Self-test 通过 `121/121`，forbidden scan 通过，private read count bucket `count_0`，retrieval executions `0`，recomputes `0`，CI reruns `0`，candidate generations `0`，arm scorings `0`，OpenLocus executions `0`，replays `0`，HAAE-layer executions `0`。HAAE-R0 source 已锁定：checkpoint `854fc2e`，status `haae_r0_design_schema_preflight_complete_haae_r1_authorized`，HAAE-R1 authorized true，HAAE-R1 execution/replay/scoring/retrieval/candidate-generation 均为 false。

该阶段在默认模式下只读取 HAAE-R0 public aggregate report 与 public docs/current-conclusions/research-log/summary/README + git metadata。Real inventory 模式（`--allow-private-inventory --private-root <path>`）枚举显式提供的 private roots，按 extension/type/schema bucket 识别候选文件，解析 schemas/JSON keys，流式输出 row-count buckets、column presence buckets、type compatibility buckets、missingness buckets 与 anonymous join-shape availability buckets。它绝不发布 paths、filenames、basenames、repo names、task ids、queries、candidates、spans、snippets、hashes、exact ranks/scores、labels 或 row values。全部 10 个 HAAE-R0 schema groups 已覆盖；5 个 critical groups 是 `task_identity`、`candidate_pool`、`evidence_core`、`arm_assignment`、`outcome_metric`。记录六个 risk controls（private diagnostic leakage、HAAE-R1 scope creep beyond feasibility inventory、default mode reads private roots、HAAE-R0 drift into selector/P5/runtime、runtime/default creep、overinterpretation from insufficient coverage）——全部已控制。

### 决策

HAAE-R1 只是 feasibility inventory。Handoff：pass（全部 10 个 groups 至少 partial 且 critical groups full 或 sufficient）→ **只** 授权 **BEA-v1-HAAE-R2 Feasibility-Gated Offline Trace Join Design**（design-only，不 execution/replay/scoring/retrieval/candidate generation）；controlled no-go（有效但不足）→ **只** 授权 **BEA-v1-HAAE-R1A Private Trace Coverage Gap Design**（design-only，不 execution）。它不授权任何 execution、rerun、retrieval、recompute、candidate generation、arm scoring、OpenLocus execution、replay、HAAE-layer execution、threshold tuning、新 policy experiments、frozen-rule changes、guard/full/diffaware promotion、runtime/default changes、method-winner claims、downstream/scaled retrieval、raw diagnostic publication、CI variant execution、selector/reranker、BEA-v1-A、P5、provider/model network 或 network runs。所有这类 stop/go 字段均为 `false`。HAAE-R1 明确 **不是** BEA-v1-A、不是 selector-only、不是 selector/reranker execution、不是 P5、不是 runtime/default promotion。参见 `docs/zh/bea-v1-haae-r1-unified-private-trace-schema-feasibility-inventory.md`。

---

## 2026-06-30 — BEA-v1-HAAE-R1A：Private Trace Coverage Gap Design

### 目标

在 HAAE-R1 确认全部 10 个 groups `not_present`（无 explicit private roots）后，为 10 个 HAAE-R0 schema groups 设计 root source options、bounded regeneration design 与 root manifest schema。HAAE-R1A 是 public-only design；不读取 private，不 root regeneration。

### 结果

`eval/bea_v1_haae_r1a_private_trace_coverage_gap_design.py` 生成 `artifacts/bea_v1_haae_r1a_private_trace_coverage_gap_design/bea_v1_haae_r1a_private_trace_coverage_gap_design_report.json`，状态为 `haae_r1a_private_trace_coverage_gap_design_complete_r1b_preflight_authorized`。Self-test 通过 `112/112`，forbidden scan 通过，private input reads `0`，root regenerations `0`，replays `0`，HAAE-layer executions `0`，network runs `0`，clone/build/search `false`。HAAE-R1 source 已锁定：checkpoint `2ea77da`，status `haae_r1_feasibility_inventory_unavailable_no_explicit_private_roots`，HAAE-R2 false，全部 10 个 groups `not_present` 已确认。

该阶段只读取 HAAE-R1/R0/N10ET public artifacts/docs/evaluators 用于 constants，以及 FD1、P4L、N1、N2、N10-series / mechanism synthesis 的 public artifacts/docs 用于分类 source option buckets。它记录全部 10 个 groups 的 coverage gap records，为每个 group 分类一个 root source option（9 个 `public_evidence_strong`，1 个 `public_evidence_partial`），设计 5 个 bounded regeneration designs（explicit opt-in、FD1 private decomposition、P4L private arm-outcome、N10EO private diagnostic rerun、N10ER public CI replay），并设计一个 6 字段 root manifest schema。记录六个 risk controls ——全部已控制。

### 决策

HAAE-R1A 只授权 BEA-v1-HAAE-R1B Bounded Private Trace Root Regeneration Preflight Package（design-only，不 execution/private read/replay/scoring/retrieval/candidate generation）：`haae_r1b_bounded_private_trace_root_regeneration_preflight_authorized_bool=true`，`haae_r1b_design_only_bool=true`，`haae_r1b_execution_authorized_bool=false`。它不授权任何 execution、rerun、retrieval、recompute、candidate generation、arm scoring、OpenLocus execution、replay、HAAE-layer execution、root regeneration、threshold tuning、新 policy experiments、frozen-rule changes、guard/full/diffaware promotion、runtime/default changes、method-winner claims、downstream/scaled retrieval、raw diagnostic publication、CI variant execution、selector/reranker、BEA-v1-A、P5、provider/model network 或 network runs。所有这类 stop/go 字段均为 `false`。HAAE-R1A 明确 **不是** BEA-v1-A、不是 selector-only、不是 selector/reranker execution、不是 P5、不是 runtime/default promotion。参见 `docs/zh/bea-v1-haae-r1a-private-trace-coverage-gap-design.md`。

---

## 2026-06-30 — BEA-v1-HAAE-R1B：Bounded Private Trace Root Regeneration Preflight Package

### 目标

在 HAAE-R1A 授权 R1B 后，打包一个 public-only、design-only 的 bounded private trace root regeneration preflight。R1B 不执行任何操作；它打包 recipe catalog、operator checklist、private output contract、public manifest schema 与 R1C bounded contract。

### 结果

`eval/bea_v1_haae_r1b_bounded_private_trace_root_regeneration_preflight_package.py` 生成 `artifacts/bea_v1_haae_r1b_bounded_private_trace_root_regeneration_preflight_package/bea_v1_haae_r1b_bounded_private_trace_root_regeneration_preflight_package_report.json`，状态为 `haae_r1b_bounded_private_trace_root_regeneration_preflight_package_complete_r1c_smoke_authorized`。Self-test 通过 `108/108`，forbidden scan 通过，private input reads `0`，root regenerations `0`，replays `0`，HAAE-layer executions `0`，network runs `0`。HAAE-R1A source 已锁定：checkpoint `e54d1b4`，R1B authorized/design-only，所有 execution 为 false。

该阶段打包了一个 machine-readable control-plane：12 条 public input records、10 条 recipe catalog records（覆盖全部 10 个 HAAE-R0 schema groups）、5 条 operator checklist records、3 条 private output contract records、5 条 public manifest schema records，以及一个 R1C bounded contract。记录六个 risk controls ——全部已控制。

### 决策

HAAE-R1B 只授权 BEA-v1-HAAE-R1C Bounded Private Trace Root Regeneration Smoke（design-only，单独实现/审查）：`haae_r1c_bounded_private_trace_root_regeneration_smoke_authorized_bool=true`，`haae_r1c_design_only_bool=true`，`haae_r1c_execution_authorized_bool=false`，`haae_r1c_bounded_recipe_only_bool=true`。R1C boundary 要求显式 opt-in、private output only、public manifest only、bounded recipe only；unbounded replay/retrieval/candidate generation/scoring/selector/BEA-v1-A/P5/runtime 全部为 false。R1B 不授权任何 execution、private reads、root regeneration 或其他阶段。参见 `docs/zh/bea-v1-haae-r1b-bounded-private-trace-root-regeneration-preflight-package.md`。

---

## 2026-06-30 — BEA-v1-HAAE-R1C：Bounded Private Trace Root Regeneration Smoke

### 目标

在 HAAE-R1B 授权 R1C 后，执行 private trace root regeneration pipeline 的第一个 bounded smoke。R1C 是第一个允许 explicit-opt-in 创建 private HAAE trace-root artifact 的阶段，但仅作为 bounded smoke。它不得运行 FD1/P4L/N10EO/N10ER replay。

### 结果

`eval/bea_v1_haae_r1c_bounded_private_trace_root_regeneration_smoke.py` 生成 `artifacts/bea_v1_haae_r1c_bounded_private_trace_root_regeneration_smoke/bea_v1_haae_r1c_bounded_private_trace_root_regeneration_smoke_report.json`，状态为 `haae_r1c_bounded_private_manifest_root_smoke_complete_r1d_inventory_authorized`（explicit bootstrap smoke 模式）。Self-test 通过 `105/105`，forbidden scan 通过，private input reads `0`，private writes `1`，replays `0`，FD1/P4L/N10EO/N10ER replays `0`，HAAE-layer executions `0`。HAAE-R1B source 已锁定：checkpoint `8830492`，R1C 被 R1B authorized/design-only，bounded recipe only，所有 replay/scoring/retrieval/candidate-generation 为 false。

默认模式不进行任何 private reads 或 writes。Explicit opt-in 要求 `--allow-private-root-regeneration-smoke --recipe <allowed> --private-output-root <path> --confirm-private-output-only`。Bootstrap recipe 创建显式 private output root，只写 manifest/control 文件与 empty/schema-category placeholders，零 raw rows，只发布 bucketized manifest。4 个 deferred recipes（FD1/P4L/N10EO/N10ER replay）标记为 deferred。10 条 schema group manifest records（全部 `raw_row_count=0`）。6 个 risk controls ——全部已控制。

### 决策

成功的 R1C bootstrap smoke 只授权 **BEA-v1-HAAE-R1D Explicit Private Root Schema Inventory Smoke**。R1C 不得运行 FD1/P4L/N10EO/N10ER replay、retrieval、scoring、candidate generation、selector、BEA-v1-A/P5/runtime/default。所有这类 stop/go 字段均为 `false`。参见 `docs/zh/bea-v1-haae-r1c-bounded-private-trace-root-regeneration-smoke.md`。

## 2026-06-30 — BEA-v1-HAAE-R1D：Explicit Private Root Schema Inventory Smoke

`eval/bea_v1_haae_r1d_explicit_private_root_schema_inventory_smoke.py` 生成 `artifacts/bea_v1_haae_r1d_explicit_private_root_schema_inventory_smoke/bea_v1_haae_r1d_explicit_private_root_schema_inventory_smoke_report.json`，状态为 `haae_r1d_schema_inventory_complete_no_go_bootstrap_placeholders_only`。Self-test 通过 `92/92`，forbidden scan 通过，HAAE-R1C checkpoint `bc1e7a2` 已锁定，使用 explicit private-root mode，private read bucket 为 `count_1_to_10`，private write bucket 为 `count_0`，row values read 为 `false`，raw publication 为 `false`。

Inventory accounted for 全部 10 个 HAAE schema groups，但 R1C bootstrap root 是 placeholder-only：placeholder groups `count_1_to_10`，meaningful groups `count_0`。这证明 root/output/manifest pipeline 可工作，但 root 没有可用于 hydration 的 meaningful schema coverage。

### Decision

R1D 是 hydration execution 与 HAAE-R2 的 controlled No-Go。它不授权 replay、scoring、retrieval、candidate generation、HAAE-layer execution、selector/reranker、BEA-v1-A/P5、runtime/default change 或 raw publication。后续进展需要单独的 bounded hydration preflight 或 operator-supplied meaningful root。参见 `docs/zh/bea-v1-haae-r1d-explicit-private-root-schema-inventory-smoke.md`。

## 2026-07-01 — BEA-v1-HAAE-R1E：Bounded Private Experiment Material Generation

`eval/bea_v1_haae_r1e_bounded_private_experiment_material_generation.py` 生成 `artifacts/bea_v1_haae_r1e_bounded_private_experiment_material_generation/bea_v1_haae_r1e_bounded_private_experiment_material_generation_report.json`，状态为 `haae_r1e_bounded_private_material_generation_complete_r2_small_experiment_authorized`。Self-test 通过 `21/21`，forbidden scan 通过，HAAE-R1D source checkpoint `9299b0a` 已锁定，默认 no-opt-in 状态为 `haae_r1e_unavailable_no_explicit_material_generation_opt_in`。

Explicit run 只允许 local/manual，并且只在显式 temp/ignored private root 下写入 raw private material rows。它使用公开 R14 sanity tasks，只在 explicit private mode 读取 labels，扫描 bounded committed Rust corpus，并生成 deterministic BM25-like、symbol-overlap trace 与 RRF-like merge order。公开 artifact 只包含 aggregate buckets，不包含 private paths、task ids、queries、candidate names、labels、spans、scores、hashes、snippets、rows 或 diagnostics。

### Decision

R1E 只授权 small local HAAE-R2 experiment。它不授权 CI、network、clone、provider/model calls、broad replay、selector/reranker execution、BEA-v1-A/P5、runtime/default changes、scoring claims、method-winner claims 或 raw publication。参见 `docs/zh/bea-v1-haae-r1e-bounded-private-experiment-material-generation.md`。

## 2026-07-01 — BEA-v1-HAAE-R2：Small Local Lexical Material Experiment

`eval/bea_v1_haae_r2_small_local_lexical_material_experiment.py` 生成 `artifacts/bea_v1_haae_r2_small_local_lexical_material_experiment/bea_v1_haae_r2_small_local_lexical_material_experiment_report.json`，状态为 `haae_r2_small_local_lexical_material_experiment_complete_r2a_public_audit_authorized`。Self-test 通过 `21/21`，forbidden scan 通过，HAAE-R1E source checkpoint `0135e1f` 已锁定，默认 no-root 状态为 `haae_r2_unavailable_no_explicit_r1e_private_material_root`。

Explicit run 只读取调用者提供的 private-material root 中已有的 R1E private material groups，不写入 private。它只在内存中 join 预计算的 `rank_pack` rows 与 `outcome_metric` rows，并为 `bm25_like`、`symbol_overlap`、`rrf_like` 计算 aggregate metrics。公开 artifact 只包含 buckets 与 booleans：group reads、rank-source metrics、agreement、summary、boundaries、gates、readback、stop/go 和 forbidden scan。它不发布 private root path 或 basename、task ids、queries、candidate paths、snippets、labels、raw ranks、scores、hashes、filenames 或 raw rows。

### Decision

R2 只授权 BEA-v1-HAAE-R2A Public Audit Package。它不授权 R3 scale preflight、new candidate generation、rematerialization、source-corpus scan、broad retrieval、OpenLocus runtime、scheduler/HAAE-layer execution、selector/reranker、CI/network/clone/provider、BEA-v1-A/P5、runtime/default changes、raw publication 或 method-winner claims。参见 `docs/zh/bea-v1-haae-r2-small-local-lexical-material-experiment.md`。

## 2026-07-01 — BEA-v1-HAAE-R2A Small Local Experiment Public Audit Package

`eval/bea_v1_haae_r2a_public_audit_package.py` 生成 `artifacts/bea_v1_haae_r2a_small_local_experiment_public_audit_package/bea_v1_haae_r2a_small_local_experiment_public_audit_package_report.json`，状态为 `haae_r2a_public_audit_package_complete_r2b_scale_preflight_design_authorized`。Self-test 通过 `22/22`，forbidden scan 通过，HAAE-R2 source checkpoint `0784be0` 已锁定，R2 source status 为 `haae_r2_small_local_lexical_material_experiment_complete_r2a_public_audit_authorized`。

R2A 是 public-only。它不读取 private material，不 recompute，也不运行 candidate generation、retrieval、scheduler/HAAE execution、selector/reranker、runtime/default change 或 BEA-v1-A/P5 action。Audit 确认 R2 tiny-N aggregate readback：`bm25_like`、`symbol_overlap`、`rrf_like` 的 hit-rate bucket 均为 `rate_1`；pairwise same-top agreement bucket 为 `rate_1`；sample bucket 为 `count_2_to_5`。

### Decision

这是 tiny-N audit，不是 no method-winner claim，也不是 runtime/default decision。R2A 只授权 BEA-v1-HAAE-R2B Scale Preflight Design，用于设计如何把 material generation 扩展到超过三个 tasks。它不授权 scale execution 或 CI。参见 `docs/zh/bea-v1-haae-r2a-small-local-experiment-public-audit-package.md`。

## 2026-07-01 — BEA-v1-HAAE-R2B Scale Preflight Design

`eval/bea_v1_haae_r2b_scale_preflight_design.py` 生成 `artifacts/bea_v1_haae_r2b_scale_preflight_design/bea_v1_haae_r2b_scale_preflight_design_report.json`，状态为 `haae_r2b_scale_preflight_design_complete_r2c_local_medium_material_smoke_preflight_authorized`。Self-test 通过 `22/22`，forbidden scan 通过，HAAE-R2A checkpoint `2ca1ac4` 已锁定。

R2B 是 public-only design/preflight。它只检查已提交的公开 R14 fixture metadata，并选择 `r14_medium_local_material_smoke`，source fixture task-count 为 `count_21_to_50`，target task-count 为 `count_10_to_20`，selected subset policy 为 `deterministic_public_manifest_prefix_cap_10_to_20`，candidate-depth 为 `count_20`，private-row cap 为 `count_le_5000`。Boundary：no private/material gen/execution/CI/network/BEA-v1-A/P5/method-winner。它不执行 private reads/writes、material generation、experiment、recompute、candidate generation、retrieval、source-corpus scan、OpenLocus execution、scheduler/HAAE execution、selector/reranker、CI/network/clone、runtime/default change、BEA-v1-A/P5 或 method-winner/scaling claim。

### Decision

R2B 只授权 BEA-v1-HAAE-R2C Local Medium Material Smoke Preflight。R2C 仍是 preflight/package phase：execution、private read/write、CI execution 与 material generation 均为 false。参见 `docs/zh/bea-v1-haae-r2b-scale-preflight-design.md`。

## 2026-07-01 — BEA-v1-HAAE-R2C Local Medium Material Smoke Preflight

`eval/bea_v1_haae_r2c_local_medium_material_smoke_preflight.py` 生成 `artifacts/bea_v1_haae_r2c_local_medium_material_smoke_preflight/bea_v1_haae_r2c_local_medium_material_smoke_preflight_report.json`，状态为 `haae_r2c_local_medium_material_smoke_preflight_complete_r2d_generation_smoke_authorized`。Self-test 通过 `21/21`，forbidden scan 通过，HAAE-R2B checkpoint `dea8a2f` 已锁定。

R2C 是 public-only preflight/package。它锁定 `r14_medium_local_material_smoke`、source fixture bucket `count_21_to_50`、subset policy `deterministic_public_manifest_prefix_cap_10_to_20`、target task bucket `count_10_to_20`、candidate depth `count_20` 与 private row cap `count_le_5000`。Boundary：`no_private_material_gen_execution_ci_network_bea_v1_a_p5_method_winner`。它不创建 private root，不写 private rows，不生成 material，不运行 experiment、recompute、retrieval、超过 fixture count 的 source scan、OpenLocus/runtime、network/clone/CI、scheduler/HAAE、selector/reranker、runtime/default、BEA-v1-A/P5 或 method/scaling claim。

### Decision

R2C 只授权 BEA-v1-HAAE-R2D Explicit Local Medium Material Generation Smoke，要求 explicit local/manual opt-in，在 explicit private root 下写 private rows，public output 只能 aggregate-only。CI/network/provider、experiment comparison、R2 recompute、retrieval runtime、scheduler/HAAE、selector/reranker、runtime/default、BEA-v1-A/P5、method claim 与 scaling claim 均保持 false。参见 `docs/zh/bea-v1-haae-r2c-local-medium-material-smoke-preflight.md`。

## 2026-07-01 — BEA-v1-HAAE-R2D Explicit Local Medium Material Generation Smoke

`eval/bea_v1_haae_r2d_explicit_local_medium_material_generation_smoke.py` 生成 `artifacts/bea_v1_haae_r2d_explicit_local_medium_material_generation_smoke/bea_v1_haae_r2d_explicit_local_medium_material_generation_smoke_report.json`。默认模式状态为 `haae_r2d_unavailable_no_explicit_medium_material_generation_opt_in`；explicit pass 状态为 `haae_r2d_explicit_local_medium_material_generation_smoke_complete_r2e_material_audit_authorized`。Self-test 通过 `19/19`，HAAE-R2C checkpoint `68000b2` 已锁定。

R2D 要求 explicit opt-in。它使用 subset policy `deterministic_public_manifest_prefix_cap_10_to_20`、public fixture bucket `count_21_to_50`、target bucket `count_10_to_20`、candidate depth `count_20` 与 private row cap `count_le_5000`。Explicit mode 只在提供的 private root 下写 private rows；public artifact 记录 private write bucket `count_le_5000`、private read validation bucket `count_1_to_10`、public aggregate-only 与 no raw publication。

### Decision

R2D 只授权 BEA-v1-HAAE-R2E Local Medium Material Audit Package。它不授权 no experiment comparison、no R2 recompute、no runtime/retrieval/source scan beyond fixture、no CI/network/provider、no scheduler/HAAE/selector、no BEA-v1-A/P5/runtime/default 或 no method/scaling claim。参见 `docs/zh/bea-v1-haae-r2d-explicit-local-medium-material-generation-smoke.md`。

## 2026-07-01 — BEA-v1-HAAE-R2E Local Medium Material Audit Package

`eval/bea_v1_haae_r2e_local_medium_material_audit_package.py` 生成 `artifacts/bea_v1_haae_r2e_local_medium_material_audit_package/bea_v1_haae_r2e_local_medium_material_audit_package_report.json`。状态为 `haae_r2e_local_medium_material_audit_package_complete_r2f_medium_experiment_authorized`，self-test `18/18`，R2D checkpoint `c4e454a`，R2D status `haae_r2d_explicit_local_medium_material_generation_smoke_complete_r2e_material_audit_authorized`。

R2E 是 public-only audit，no private root read。它确认 task bucket `count_10_to_20`、source fixture bucket `count_21_to_50`、subset policy `deterministic_public_manifest_prefix_cap_10_to_20`、candidate depth `count_20`、private row cap `count_le_5000`、total private row bucket `count_le_5000`，以及 rank sources `bm25_like/symbol_overlap/rrf_like`。

### Decision

R2E 只授权 R2F local medium material experiment，要求 operator-supplied explicit private root，只读取 existing R2D private material，并计算 aggregate metrics。没有 no new material/candidate generation/retrieval/runtime/source scan/CI/network/scheduler/HAAE/selector/BEA-v1-A/P5/default/method/scaling claim。参见 `docs/zh/bea-v1-haae-r2e-local-medium-material-audit-package.md`。

## 2026-07-01 — BEA-v1-HAAE-R2F Local Medium Material Experiment

`eval/bea_v1_haae_r2f_local_medium_material_experiment.py` 以 explicit mode 读取 existing R2D private material，生成 `artifacts/bea_v1_haae_r2f_local_medium_material_experiment/bea_v1_haae_r2f_local_medium_material_experiment_report.json`。默认状态仍为 `haae_r2f_unavailable_no_explicit_r2d_private_material_root`；explicit pass status 为 `haae_r2f_local_medium_material_experiment_complete_r2g_public_audit_authorized`。Self-test 通过 `22/22`，R2E checkpoint 为 `b166d79`，R2E status 为 `haae_r2e_local_medium_material_audit_package_complete_r2f_medium_experiment_authorized`。

R2F 要求 explicit private material root，并只读取 existing R2D private material only。它为 `bm25_like/symbol_overlap/rrf_like` 计算 aggregate-only metrics，不发布 path、basename、filename、task id、query、candidate、label、score、hash、snippet 或 exact per-task value。三个 rank sources 的 gold-file hit-rate bucket `rate_1`、same-top candidate rate bucket `rate_1`、top1/top5/top10 buckets `count_10_to_20`。

### Decision

R2F 只授权 BEA-v1-HAAE-R2G Public Audit Package。Boundary: no new candidates/retrieval/source scan/OpenLocus/runtime/scheduler/selector/CI/network/provider/default/BEA-v1-A/P5/method/scaling claim。参见 `docs/zh/bea-v1-haae-r2f-local-medium-material-experiment.md`。

## 2026-07-01 — BEA-v1-HAAE-R2G Public Audit Package

`eval/bea_v1_haae_r2g_public_audit_package.py` 生成 `artifacts/bea_v1_haae_r2g_public_audit_package/bea_v1_haae_r2g_public_audit_package_report.json`。状态为 `haae_r2g_public_audit_package_complete_r2h_next_step_design_authorized`，self-test `9/9`，HAAE-R2F checkpoint `1e0c718`，R2F status `haae_r2f_local_medium_material_experiment_complete_r2g_public_audit_authorized`。

R2G 是 public-only，只读取 public R2F artifact/docs。它确认 rank-source hit-rate bucket `rate_1`、same-top candidate rate bucket `rate_1`、top1/top5/top10 buckets `count_10_to_20`，scope 为 medium material experiment only。

### Decision

R2G 只授权 BEA-v1-HAAE-R2H Next-Step Design Decision。Boundary: no method-winner/default/scaling claim。它不授权 execution、CI、scale material generation、runtime/default changes、BEA-v1-A/P5、method-winner claims、scaling claims 或 raw publication。参见 `docs/zh/bea-v1-haae-r2g-public-audit-package.md`。

## 2026-07-01 — BEA-v1-HAAE-R2H Next-Step Design Decision

`eval/bea_v1_haae_r2h_next_step_design_decision.py` 生成 `artifacts/bea_v1_haae_r2h_next_step_design_decision/bea_v1_haae_r2h_next_step_design_decision_report.json`。状态为 `haae_r2h_next_step_design_decision_complete_r2i_harder_diversified_material_generation_authorized`，self-test `11/11`，HAAE-R2G checkpoint `cd583d6`，R2G status `haae_r2g_public_audit_package_complete_r2h_next_step_design_authorized`。

R2H diagnosis 为 `arms_not_separating`。Decision 是 reject/defer scaling the same R14 medium recipe，并选择 harder/diversified local material generation。R2I boundary 为 target 20 tasks、candidate depth 40、private row cap 10000、explicit opt-in local private root、public aggregate-only manifest、rank sources `bm25_like/symbol_overlap/path_prior/structure_token_overlap/rrf_like/control_baseline`，并且 no experiment metrics in R2I。

### Decision

R2H 只授权 BEA-v1-HAAE-R2I Harder/Diversified Local Material Generation Smoke。Boundary 仍为 no method/default/scaling claim、no private read、no material generation in R2H、no execution、no recompute、no retrieval/source scan/OpenLocus/runtime、no CI/network/provider/clone、no scheduler/HAAE/selector。参见 `docs/zh/bea-v1-haae-r2h-next-step-design-decision.md`。

## 2026-07-01 — BEA-v1-HAAE-R2I Harder/Diversified Local Material Generation Smoke

`eval/bea_v1_haae_r2i_harder_diversified_local_material_generation_smoke.py` 以默认模式生成 `artifacts/bea_v1_haae_r2i_harder_diversified_local_material_generation_smoke/bea_v1_haae_r2i_harder_diversified_local_material_generation_smoke_report.json`。默认状态为 `haae_r2i_unavailable_no_explicit_harder_diversified_material_generation_opt_in`；explicit pass status 为 `haae_r2i_harder_diversified_local_material_generation_complete_r2j_experiment_authorized`。Self-test 通过 `21/21`，HAAE-R2H checkpoint 为 `3db7366`，R2H status 为 `haae_r2h_next_step_design_decision_complete_r2i_harder_diversified_material_generation_authorized`。

R2I 要求 explicit opt-in。Locked boundary 为 target 20 tasks、candidate depth 40、private row cap 10000，rank sources 为 `bm25_like/symbol_overlap/path_prior/structure_token_overlap/rrf_like/control_baseline`。它只在 explicit operator root 下写 private rows，发布 aggregate public manifest，并且 no experiment metrics in R2I。

### Decision

R2I 只授权 BEA-v1-HAAE-R2J Harder/Diversified Material Experiment。它不读取 old private roots，不运行 retrieval/runtime/OpenLocus/source scan outside fixture，不使用 CI/network/provider/clone，不执行 scheduler/HAAE/selector，不改变 BEA-v1-A/P5/defaults，也不提出 method/scaling claims。参见 `docs/zh/bea-v1-haae-r2i-harder-diversified-local-material-generation-smoke.md`。

## 2026-07-01 — BEA-v1-HAAE-R2J Harder/Diversified Material Experiment

`eval/bea_v1_haae_r2j_harder_diversified_material_experiment.py` 以 explicit mode 读取 existing R2I private material，生成 `artifacts/bea_v1_haae_r2j_harder_diversified_material_experiment/bea_v1_haae_r2j_harder_diversified_material_experiment_report.json`。默认状态为 `haae_r2j_unavailable_no_explicit_r2i_private_material_root`；pass status 为 `haae_r2j_harder_diversified_material_experiment_complete_r2k_public_audit_authorized`；non-separating status 为 `haae_r2j_harder_diversified_material_experiment_complete_no_go_non_separating`。Self-test 通过 `21/21`，HAAE-R2I checkpoint 为 `16d1349`，R2I status 为 `haae_r2i_harder_diversified_local_material_generation_complete_r2j_experiment_authorized`。

R2J 要求 explicit private material root，并且 input 是 existing R2I material only。它为 `bm25_like/symbol_overlap/path_prior/structure_token_overlap/rrf_like/control_baseline` 计算 aggregate-only metrics，并计算 separation diagnostics，且保持 `method_winner_bool=false`。显式结果为 `separation_signal_bool=true`、`rank_spread_bucket=spread_medium`、`control_baseline_separation_bucket=non_control_better`；`path_prior` 的 top1/top5/top10/top20 buckets 都是 `count_10_to_20` 且 `mrr_high`，而 `control_baseline` 的 top1 bucket 是 `count_0` 且 `mrr_low`。

### Decision

R2J 在 separation passes 时只授权 BEA-v1-HAAE-R2K Public Audit Package。Boundary 仍为 no method winner/default/scaling claim、no root discovery、no private writes、no candidate/material generation、no retrieval/runtime/OpenLocus/source scan/CI/network/provider/scheduler/selector，且 no exact per-task/private publication。参见 `docs/zh/bea-v1-haae-r2j-harder-diversified-material-experiment.md`。
