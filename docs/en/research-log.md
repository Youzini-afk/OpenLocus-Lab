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

### Caveats

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
| Path derivation: none | 227/741 (30.6%) |
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
- Produces `docs/r28-promotion-candidate-report.json` and `docs/r28-promotion-candidate-report.md`.
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

## 2026-06-18 — B10B Runtime-Shadow Replay (Ambiguous Branch Only)

### Objective

B10B is the next step after the B10 freeze of
`balanced_policy_v1_benchmark_routed`. It validates a predeclared
runtime-feature-only shadow predicate that approximates the ambiguous branch of
the frozen benchmark-routed spec on the same records via action-agreement
replay only. There are no new model runs, no new default policy, no policy
search, no tuning, and no promotion. The goal is to test whether runtime
`route_features` alone (`query_noise`, `candidate_support_exists`,
`local_anchor`, `rrf_backed_by_anchor`) can shadow the ambiguous branch that
the frozen spec currently drives off benchmark public labels
(`task_bucket`/`task_risk_tags`).

### Implementation notes

- Parallel reconnaissance: @explorer mapped the 16-key `route_features` space
  and identified 4 clean shadow features (`query_noise`,
  `candidate_support_exists`, `local_anchor`, `rrf_backed_by_anchor`);
  @librarian confirmed the methodology as "offline shadow-policy conformance
  replay" (not full OPE — no propensities, no counterfactual weighting);
  @oracle strategic review found 4 blockers in the original implementation.
- @fixer strengthened the evaluator (1163 → ~1820 lines): added
  `outcome_metrics` to the leakage mutation test, predeclared acceptance gates
  (10 gates), stratified agreement metrics (`target_weak_only_recall`,
  `target_use_p25_specificity`, `shadow_weak_only_precision`,
  `label_driven_ambiguous_recall_qn0`, `query_noise_only_recall_qn1`),
  silent-failure checks (`all_shadow_ambiguous`,
  `all_shadow_non_ambiguous`, `base_rate_only_suspected`,
  `no_silent_failure`), Cohen's kappa (direct implementation, no
  numpy/sklearn), outcome-equivalence audit on the disagreement subset (4
  partitions), verdict framework (`runtime_shadow_ambiguous_supported` +
  `support_claim` + `support_claim_reason`), `replay_source` parameter
  (`synthetic_fixture` vs `ci_ephemeral_records`), and a CLI `--records`
  option for CI integration.
- @oracle final review found 1 remaining concern: the denominator was treated
  as an escape clause (OR) instead of a hard gate (AND). @fixer fixed:
  `label_driven_ambiguous_min_denominator=10` is now a HARD gate; an
  insufficient denominator yields verdict `False` with
  `support_claim="empirical_replay_support_pending"` and
  `support_claim_reason="insufficient_label_driven_denominator"`.
- Final spec sha256:
  `c201eb709dc0112c2bb91db33917c6d20ea48582924821a2bda7950709e754ba`.
- All 10 self-test checks PASS.

### Findings

- B10B is now a mechanics-validated scaffold: the evaluator, leakage guard,
  verdict framework, and all 10 predeclared gates work correctly.
- Current verdict on the synthetic fixture:
  `runtime_shadow_ambiguous_supported=false`,
  `support_claim="mechanics_only_synthetic_fixture"`,
  `support_claim_reason="synthetic_fixture_only"`,
  `replay_source="synthetic_fixture"`.
- No real CI ephemeral records exist on disk (P21 ephemeral records are written
  to `$RUNNER_TEMP` and not committed; P21 public JSON is aggregate-only after
  the B2 privacy repair).
- Therefore B10B cannot make any empirical support claim yet. Empirical
  validation requires either CI integration (run `--records` against
  `$RUNNER_TEMP/p25-policy-records-ephemeral-v1/*.json` before cleanup) or B11
  prospective runs.

### Caveats

- B10B is ambiguous-branch runtime-shadow only; it does **not** prove a
  runtime-clean balanced policy.
- The default `use_p25_action` still delegates to the P25 benchmark-routed
  behavior.
- No live LLM calls (`runtime_calls_by_replay=0`, `model_calls_by_replay=0`).
- No default change, no promotion, no `EvidenceCore` semantic change.
- B11 should be framed as "exploratory prospective stress test", not
  "supported validation", until B10B runs on real CI records and passes the
  predeclared gates.
- The shadow predicate is FROZEN; no tuning during B11. Any predicate change
  should start a new frozen spec/version.

## 2026-06-18 — B10B Runtime-Shadow Replay CI Integration

### Objective

Integrate B10B into the CI workflow so it runs against real P21 ephemeral records, turning the mechanics-validated scaffold into an empirically-validated one on the next P21 CI run.

### Implementation notes

- Made `eval/b10b_runtime_shadow_replay.py --records` accept either a JSON array (legacy) or a P21 payload object (with `records` field). Format detected by top-level type.
- Added `_extract_outcome_metrics(record, target_action_value)` helper that resolves outcome_audit data from P21 per-strategy dicts: `weak_candidate_only` when target=weak_only, `candidate_baseline` when target=use_p25_action. Extracts only the four `OUTCOME_AUDIT_NUMERIC_FIELDS` (`added_gold_span`, `added_false_span`, `span_f0_5`, `primary_false_positive_rate`) into a new in-memory dict. Record is never mutated. Shadow predicate still never reads outcome_metrics (audit-only).
- Added `--out <path>` CLI option for CI output path.
- Added CI step in `.github/workflows/real-provider-benchmark.yml` (P21-G3L step, after P62, before `rm -f "$P25_RECORDS"` cleanup): `if [[ -f "$P25_RECORDS" ]]; then python3 eval/b10b_runtime_shadow_replay.py --records "$P25_RECORDS" --out artifacts/real_provider_ci/b10b_runtime_shadow_replay_report.json; fi`. Verdict=False is a valid result (not a CI failure); only file/parse errors fail.
- Spec hash unchanged: `c201eb709dc0112c2bb91db33917c6d20ea48582924821a2bda7950709e754ba` (no spec changes; outcome extraction is audit-only).
- Local P21 payload fixture test passed: `replay_source="ci_ephemeral_records"`, `outcome_audit_status="ok"` with 4 records across all 4 partitions, verdict=False with `insufficient_label_driven_denominator` (expected for small sample).
- Self-test still passes (10 checks).

### Findings

- B10B is now wired into CI. The next P21 CI run (triggered via workflow_dispatch with enable_remote_models=true) will produce real empirical B10B data.
- If B10B passes all 10 predeclared gates on real records, it upgrades from "mechanics-validated scaffold" to "empirically-supported".
- If B10B fails gates, B11 prospective validation still proceeds (B10B is ambiguous-branch shadow only; B11 tests the benchmark-routed policy).

### Caveats

- B10B CI integration is non-blocking initially (verdict=False is a valid result).
- Real empirical validation requires the next P21 CI run, which needs workflow_dispatch + enable_remote_models=true.
- No new live LLM calls from B10B itself (replay-only).

## 2026-06-18 — B11 Prospective Blind Validation Planning

### Objective

Draft the B11 preregistration plan: a prospective validation of the frozen balanced policy `balanced_policy_v1_benchmark_routed` on new repos/tasks generated after the 2026-06-18 policy freeze, with no retuning of policies, thresholds, or success criteria.

### Implementation notes

- Parallel reconnaissance: @explorer identified 8 repos already used in B6B/B6C/B6E/B6F/B8-lite (`py_flask`, `js_express`, `go_gin`, `rust_ripgrep`, `go_cobra`, `py_httpx`, `js_axios`, `rust_mdbook`) and mapped available new repos from `eval/ci_repos/openlocus-ci-repos-v1.yaml`. @librarian researched prospective validation methodology (preregistration, worst-group metrics, CVaR, leave-one-out, live LLM eval best practices). @oracle strategic plan returned empty (proceeded with own analysis).
- Selected 8 new repos for minimum viable B11: `py_fastapi`, `py_pytest`, `ts_vite`, `ts_hono`, `go_chi`, `go_prometheus`, `rust_deno`, `java_spring_petclinic` (5 languages: Python, TypeScript, Go, Rust, Java).
- Confirmed 4 model families from `eval/p21_model_profiles.json`: Kimi-K2.7-Code (tool_call, reference), Qwen3.6-27B (json_schema_strict, secondary), DeepSeek-V4-Flash (json_schema_strict, recall), DeepSeek-V4-Pro (json_schema_strict, conservative). GLM-5.2 excluded (noisy per B9A/B6D).
- Confirmed 4 policies: Local baseline (no LLM), P25 `bucket_routed_v0`, Balanced v1 `balanced_policy_v1_benchmark_routed`, Conservative `rmc_local_conservative_v0`.
- Predeclared success/failure/partial criteria with explicit thresholds (Δgold_span, ΔSpanF0.5, ΔPFP, Δfalse_spans, ΔLLM_calls; overall + worst-group).
- Defined RobustUtility = min_group(SpanF0.5 - λ*PFP - μ*normalized_cost - ν*normalized_latency) with λ=1.0, μ=0.1, ν=0.1.
- B10B integration: B10B --records runs in CI after each B11 run (already wired in commit 2cbdd0c), giving B10B first empirical validation.
- Wrote B11 preregistration plan at `docs/en/b11-prospective-blind-validation.md` (325 lines).

### Findings

- B11 plan is now frozen before any prospective live runs. No retuning of policies, thresholds, or success criteria after live runs begin.
- B11 is framed as "exploratory prospective stress test" (per @oracle B10B review): B10B hasn't run on real CI records yet, so the runtime-shadow predicate is not empirically supported. B11 tests the benchmark-routed balanced policy, not the runtime-shadow predicate.
- Minimum viable B11 (8 repos, ~120 tasks, 4 models) is feasible autonomously for infrastructure setup; live runs require workflow_dispatch + enable_remote_models=true.

### Caveats

- B11 plan is a preregistration; any post-hoc analysis must be labeled exploratory.
- Live LLM runs require user workflow_dispatch trigger.
- B11 does NOT prove promotion readiness; `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`.
- B11 evaluator skeleton (`eval/b11_prospective_validation.py`) and CI workflow stage are next steps (separate tasks).

## 2026-06-18 — B12 Mechanism Decomposition Planning

### Objective
Draft B12 preregistration plan: mechanism decomposition via 5 ablation variants (A-E) and 4 hypotheses (H1-H4) to understand WHY the balanced policy works.

### Implementation notes
- Defined 5 ablation variants: A (full balanced), B (deterministic LLM reduction), C (ambiguous weak_only only, ≡A), D (P25 default), E (random LLM reduction).
- Defined 4 hypotheses: H1 (ambiguous routing), H2 (LLM call reduction), H3 (P25 fallback sufficiency), H4 (model-specific).
- Methodology: replay-based (if P21 records available) OR live ablation runs.
- B12 evaluator skeleton at `eval/b12_mechanism_decomposition.py` (~900 lines, 10 self-test checks, spec sha256 stable).
- --input is a stub (verdict=not_implemented); full ablation computation deferred.

### Findings
- B12 plan is frozen before any ablation runs.
- B12 can be done as replay if P21 records available (from B11 live runs or CI ephemeral).
- A≡C (both are "ambiguous→weak_only, else P25") since the balanced policy only has one routing rule.

### Caveats
- B12 ablation runs (if needed) require workflow_dispatch + enable_remote_models=true.
- B12 does NOT prove promotion; `promotion_ready=false`, `default_should_change=false`.

## 2026-06-18 — B13 Distributionally Robust Policy Search Planning

### Objective
Draft B13 preregistration plan: distributionally robust policy search that optimizes worst-group utility (not average), using only runtime-observable features, validated via rotating leave-one-model-family-out.

### Implementation notes
- Rule grammar: 6-10 rules, each using only runtime route_features (query_noise, candidate_support_exists, local_anchor, rrf_backed_by_anchor, candidate_count, etc.). No benchmark-private labels, no score-private fields, no model names in algorithm_spec.
- Optimization objective: maximize worst-group utility OR CVaR_20%. RobustUtility = SpanF0.5 - λ*PFP - μ*normalized_cost - ν*normalized_latency (λ=1.0, μ=0.1, ν=0.1).
- Validation: rotating leave-one-model-family-out (Kimi+Qwen→DeepSeek, Kimi+DeepSeek→Qwen, Qwen+DeepSeek→Kimi). All 3 rotations must pass.
- B13 evaluator skeleton at `eval/b13_dro_policy_search.py` (~2300 lines, 9 read-only self-test checks, spec sha256 stable). `--self-test` is read-only (compares in-memory expected artifacts to on-disk artifacts, fails on drift, does not mutate checked-in artifacts); `--regenerate-artifacts` is the only path that mutates checked-in artifacts.
- --input is a stub (verdict=not_implemented); full search deferred.
- Special invariant: `algorithm_spec_has_no_model_names=true` (verify no model names in spec).
- Skeleton verdict framework emits only `insufficient_data` (synthetic fixture) or `not_implemented` (ci_ephemeral_records stub); `success` / `failure` / `partial` are reserved for a future empirical `policy_search_performed=true` path that is NOT present in this skeleton.
- Synthetic / stub reports emit only rotation *definitions* (`rotations_defined=true`, `rotation_count=3`, `rotations_evaluated=false`); they never emit per-rotation `passes=true` / `all_rotations_pass=true` / `test_worst_group_utility` / `delta_vs_b10_reference` as if empirical. Top-level `policy_found=false`, `rotations_evaluated=false`, `winner_declared=false` are always present.

### Findings
- B13 plan is frozen before any search runs.
- B13 requires P21 records from B11 live runs (4 model families × 8 repos).
- B13 is the policy-search stage (`stage_is_policy_search=true`), but the
  shipped skeleton performs NO empirical policy search
  (`empirical_policy_search_performed=false`); the synthetic / stub report
  sets `policy_search_performed=false`, `policy_found=false`,
  `rotations_evaluated=false`, `winner_declared=false` so the public
  artifact cannot be misread as an empirical B13 run. No empirical
  per-rotation passes / utilities / deltas are emitted. Results are NOT
  promoted (`promotion_ready=false`, `default_should_change=false`).
- B13 is the last "immediate priority" item in B10-B19 Breakthrough Sprint.

### Caveats
- B13 search requires P21 records (from B11 live runs or CI ephemeral).
- B13 does NOT prove promotion; results are research candidates only.
- After B13, remaining items (B14-B19) are second priority or parallel tracks.

## 2026-06-18 — B13 Public-Aggregate Feasibility / No-Go Screen

### Objective

Produce a bounded, public-aggregate **feasibility / no-go screen** (NOT real
B13 distributionally robust policy search) for B13 from the already-published
B11 aggregate and B12 public-aggregate screen, after the explorer/oracle
finding that real B13 cannot be performed from public aggregates alone.

### Implementation notes

- New screen script `eval/b13_public_aggregate_feasibility_screen.py` (pure
  Python; reuses `b6_lite_interpretable_policy_search._walk_forbidden` for the
  public-output forbidden-key scan; `--self-test` synthetic-fixture mode +
  input-validation block checks + insufficient-data branch check + forbidden
  scan check).
- New aggregate artifact
  `artifacts/b13_dro_policy_search/b13_public_aggregate_feasibility_report.json`
  (schema `b13-public-aggregate-feasibility-screen-v0`).
- The screen reads only `artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json`
  and `artifacts/b12_mechanism_decomposition/b12_public_aggregate_screen_report.json`
  (already-published public aggregates); no raw records, paths, prompts,
  responses, snippets, or private labels are read or emitted.
- Hardened B13 skeleton claim fields: `eval/b13_dro_policy_search.py` now
  distinguishes `stage_is_policy_search=true` (B13 stage IS policy search)
  from `empirical_policy_search_performed=false` (no empirical search
  performed by skeleton); the synthetic / stub report sets
  `policy_search_performed=false`, `policy_found=false`,
  `rotations_evaluated=false`, `winner_declared=false` so the public
  artifact cannot be misread as an empirical B13 search. Synthetic / stub
  reports emit only rotation *definitions* (`rotations_defined=true`,
  `rotation_count=3`, `rotations_evaluated=false`); they never emit
  per-rotation `passes=true` / `all_rotations_pass=true` /
  `test_worst_group_utility` / `delta_vs_b10_reference` as if empirical.
  The skeleton verdict framework emits only `insufficient_data` (synthetic
  fixture) or `not_implemented` (ci_ephemeral_records stub); `success` /
  `failure` / `partial` are reserved for a future empirical
  `policy_search_performed=true` path that is NOT present in this skeleton.
  `--self-test` is read-only (compares in-memory expected artifacts to
  on-disk artifacts, fails on drift, writes nothing);
  `--regenerate-artifacts` is the only mutating path.
  `verify_algorithm_spec`, `verify_report`, `_print_summary`, and
  `run_self_test` updated accordingly.

### Findings

- B13 verdict from the public aggregate screen: `no_go_public_aggregate_only`
  (B11 has 384 records; the public aggregate is sufficient to produce a
  feasibility read, but real B13 search is not possible from public
  aggregates alone).
- `empirical_policy_search_performed=false`, `policy_search_performed=false`,
  `policy_found=false`, `rotations_evaluated=false`,
  `full_b13_possible_from_public_artifacts=false`.
- Missing inputs that block real B13 from the public artifacts:
  `no_per_record_route_features_in_public_artifact`,
  `no_per_record_action_eligibility_in_public_artifact`,
  `no_per_strategy_outcomes_in_public_artifact`,
  `no_weak_candidate_only_public_outcomes_in_public_artifact`,
  `no_group_membership_for_train_test_rotations_in_public_artifact`,
  `no_held_out_family_evaluation_in_public_artifact`,
  `no_candidate_rule_coverage_in_public_artifact`.
- B11 mixed/partial verdict (`partial_with_failure`) and B12 public-aggregate
  screen statuses carried forward unchanged; they do NOT authorize
  promotion, default change, or a runtime-clean general algorithm.
- Descriptive overall-mean penalty index from already-published fixed strategies
  (P25 / balanced_v1) included under
  `descriptive_fixed_strategy_proxy_not_policy_search=true`; it is strictly
  descriptive, NOT the B13 RobustUtility, NOT worst-group/CVaR/rotation-
  validated, NOT valid for policy selection or strategy ranking; never
  selects a new rule, never declares a winner.

### Caveats

- The screen is NOT real B13 distributionally robust policy search. It does
  NOT claim empirical policy search, does NOT select a rule, does NOT
  declare a winner.
- No promotion, no default change, no runtime-clean general algorithm claim,
  no EvidenceCore semantics change (`promotion_ready=false`,
  `default_should_change=false`, `evidencecore_semantics_changed=false`,
  `policy_search_performed=false`, `quality_strategy_tuned=false`,
  `new_provider_calls=0`).
- Recommended next step: future ephemeral-record B13 replay (the only path
  that can perform empirical distributionally robust policy search), or
  first ephemeral-record B12 replay to causally decompose the balanced
  policy. The public aggregate alone is insufficient for either.

## 2026-06-18 — B11 Official Integrated Matrix Aggregate Report

### Objective

Produce a bounded, aggregate-only rollup of the finished B11 official integrated matrix from the already-downloaded public B11/B10B aggregate artifacts, without reading any raw records, paths, prompts, responses, snippets, or private labels.

### Implementation notes

- Inputs: 32 run directories under `/tmp/b11_official_integrated_artifacts`, each containing `artifacts/real_provider_ci/b11_prospective_validation_report.json` and `b10b_runtime_shadow_replay_report.json`. The matrix finished 32/32 after retrying two transient `provider_status` failures.
- New combiner script `eval/b11_matrix_combiner.py` (pure Python; reuses `b6_lite_interpretable_policy_search._walk_forbidden` for the public-output forbidden-key scan; `--self-test` synthetic-fixture mode + empty-input block check).
- New aggregate artifact `artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json` (schema `b11-prospective-matrix-aggregate-report-v0`).
- Combiner refuses any run directory name that is not a public B11 repo slice + public model display name + run-id triple; emits only sanitized counts, public repo slice IDs (`py_fastapi`, `py_pytest`, `ts_vite`, `ts_hono`, `go_chi`, `go_prometheus`, `rust_deno`, `java_spring_petclinic`), public model-family names (`kimi`, `qwen`, `deepseek_flash`, `deepseek_pro`), weighted means, deltas, and verdict counts. No run IDs are emitted.

### Findings

- 32 runs, 384 records. Verdict counts: success 8, partial 23, failure 1.
- Overall weighted means across 384 records (`local_baseline` / `p25` / `balanced_v1` / `conservative`): `gold_span 0.377604 / 0.247396 / 0.244792 / 0.125000`; `false_span 1.203125 / 0.236979 / 0.182292 / 0.236979`; `span_f0_5 0.062197 / 0.064538 / 0.062639 / 0.023611`; `PFP 0.083333 / 0.020833 / 0.0 / 0.0`; `model_calls 0.0 / 0.958333 / 0.604167 / 0.0`.
- Balanced v1 vs P25 deltas: `Δgold_span -0.002604`, `Δfalse_span -0.054688`, `ΔSpanF0.5 -0.001899`, `ΔPFP -0.020833`, `Δmodel_calls -0.354167`. Balanced v1 preserved near-parity SpanF0.5/gold vs P25 while reducing false spans, PFP, and model calls on average.
- Per model family (balanced_v1 vs P25, 96 records each): `deepseek_flash` partial 6 / success 2; `deepseek_pro` partial 5 / success 3; `kimi` partial 5 / success 2 / failure 1 (a `py_fastapi` slice exceeded `failure_spanf05_delta`); `qwen` partial 7 / success 1.
- B10B: 32/32 reports, `runtime_shadow_ambiguous_supported=false` on all, `support_claim="empirical_replay_support_pending"` (reason `insufficient_label_driven_denominator`; max `label_driven_ambiguous_denominator_qn0=3` vs the 10-record hard gate). B10B runtime-shadow predicate remains empirical-pending.

### Caveats

- B11 is mixed/partial. The result strengthens the algorithm-candidate signal but does NOT prove a runtime-clean general algorithm.
- No promotion, no default change, no EvidenceCore semantics change (`promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `policy_search_performed=false`, `quality_strategy_tuned=false`, `new_provider_calls=0`).
- The Kimi `py_fastapi` failure slice and the B10B denominator-pending predicate are open issues for B12 (mechanism decomposition).
- Aggregate-only; no raw records, paths, prompts, responses, snippets, or private labels were read by the combiner.

## 2026-06-18 — B12 Public Aggregate Mechanism Screen

### Objective

Produce a bounded, public-aggregate **mechanism screen** (NOT a full B12 per-record replay) for H1-H4 from the already-published B11 aggregate report, after the explorer/oracle found that full B12 replay is impossible from the current public artifacts.

### Implementation notes

- New screen script `eval/b12_public_aggregate_screen.py` (pure Python; reuses `b6_lite_interpretable_policy_search._walk_forbidden` for the public-output forbidden-key scan; `--self-test` synthetic-fixture mode + input-validation block checks + H3 parity-break check + H4 spread-supported branch check).
- New aggregate artifact `artifacts/b12_mechanism_decomposition/b12_public_aggregate_screen_report.json` (schema `b12-public-aggregate-mechanism-screen-v0`).
- The screen reads only `artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json` (the already-published B11 aggregate); no raw records, paths, prompts, responses, snippets, or private labels are read or emitted.
- The screen applies the SAME frozen numeric gates as full B12 (±0.02 approx-equality on `gold_span`/`span_f0_5`; 0.05 H4 model-family spread threshold) but to aggregate deltas only, since per-record ablation deltas are unavailable publicly.
- Emits **per-hypothesis screen statuses**, never a single global `supported` verdict; preserves all safety fields verbatim (`aggregate_only_public_artifact=true`, `candidate_not_fact=true`, `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `policy_search_performed=false`, `quality_strategy_tuned=false`, `new_provider_calls=0`).

### Findings

- H1 ambiguous routing: `inconclusive_unavailable_ablation_controls` — public aggregate lacks per-record route decisions, ambiguous subset, variants B/E; does NOT claim H1 support.
- H2 LLM call reduction: `reduced_calls_observed_causal_mechanism_inconclusive` — `Δmodel_calls -0.354167` so reduced calls are observed descriptively, but without variant E the causal mechanism cannot be attributed; does NOT claim H2 causal support.
- H3 P25 fallback sufficiency: `aggregate_primary_parity_supported_consistent_with_h3` — `Δgold_span -0.002604` and `ΔSpanF0.5 -0.001899` both within ±0.02; consistent with H3 at the aggregate primary-parity level, but NOT a full H3 supported verdict (per-record fallback sufficiency cannot be concluded from aggregate deltas alone).
- H4 model-specific: `family_gold_spread_not_supported_model_repo_interaction_inconclusive` — per-family gold_span delta spread `0.010417` (deepseek_flash 0.0, deepseek_pro 0.0, kimi -0.010417, qwen 0.0) at or below the 0.05 family-level threshold; NOT supported under the predeclared family-level gold-span spread criterion; NOT a full H4 refutation because the Kimi `py_fastapi` failure slice leaves model×repo interaction inconclusive without per-record data.

### Testability gaps (why full B12 is not possible from the public artifact)

- `no_per_record_route_decisions_in_public_artifact` — only policy-level route-decision counts are published; per-record ambiguous vs P25 decisions are absent.
- `no_ambiguous_subset_membership_in_public_artifact` — the public aggregate does not identify which records fell into the ambiguous subset, so variants B/C/E cannot be reconstructed by subset selection.
- `no_deterministic_call_reduction_variant_B_in_public_artifact` — variant B is not a published policy in the B11 matrix, so H1 A>B and H2 routing-vs-reduction comparisons cannot be made.
- `no_random_call_reduction_variant_E_in_public_artifact` — variant E is not published; without E the H2 A≈E criterion cannot be evaluated.
- `no_weak_candidate_only_outcomes_in_public_artifact` — `weak_candidate_only` per-strategy outcomes are not in the public aggregate, so the routing-rule contribution cannot be isolated.

### Caveats

- The screen is NOT a full B12 mechanism decomposition. It does NOT claim H1 support, does NOT claim H2 causal support, does NOT claim full H4 refutation (only the family-level gold-span spread criterion is not supported), and does NOT claim H3 fully supported (only aggregate primary parity).
- No promotion, no default change, no runtime-clean general algorithm claim, no EvidenceCore semantics change (`promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `policy_search_performed=false`, `quality_strategy_tuned=false`, `new_provider_calls=0`).
- Recommended next step: future ephemeral-record B12 replay (preferred), or B13 distributionally robust policy search with caution. B13 must not be treated as authorized by a B12 supported verdict.

## 2026-06-18 — B14 Uncertainty Calibration Planning + Public-Aggregate Feasibility / No-Go Screen

### Objective

Add the B14 uncertainty-calibration **preregistration + evaluator skeleton + public-aggregate feasibility / no-go screen**. This is a bounded planning / feasibility phase, NOT empirical calibration. Real B14 (model-independent uncertainty calibration using local candidate signals, model output structure, cross-model disagreement; metrics risk-coverage, selective risk, ECE, PFP at fixed coverage; worst-group reporting; rotating leave-one-model-family-out) requires per-record uncertainty scores + per-record outcomes + paired model outputs, which are unavailable in current public artifacts.

### Implementation notes

- New preregistration docs `docs/en/b14-uncertainty-calibration.md` and `docs/zh/b14-uncertainty-calibration.md` (frozen signal families, forbidden labels, required per-record inputs, split/calibration/test protocol, coverage levels, ECE target definition, worst-group reporting, privacy/publication gates, success/partial/failure criteria). Explicit that current public artifacts (B11 aggregate, B12 public screen, B13 public feasibility) are insufficient.
- New evaluator skeleton `eval/b14_uncertainty_calibration.py` (pure Python; mirrors B13 freeze style): frozen `build_algorithm_spec` + `build_report`; read-only `--self-test` (synthetic fixture mechanics only, compares in-memory expected artifacts to on-disk artifacts and fails on drift, does not mutate checked-in artifacts); `--regenerate-artifacts` is the explicit checked-in-artifact mutating path; `--input` stub requires explicit `--out`, refuses to write the checked-in B14 report, and returns `not_implemented` / `insufficient_data` (NOT empirical calibration). Safety fields preserved verbatim: `uncertainty_calibration_performed=false`, `calibrated_model_claim=false`, `per_record_inputs_available=false` for stub/synthetic; `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `policy_search_performed=false`, `quality_strategy_tuned=false`, `new_provider_calls=0`. The skeleton MUST NOT compute fake ECE / risk-coverage / selective-risk / PFP-at-coverage metrics from aggregate means; the synthetic fixture validates only metric NAMES and gates (`metrics_evaluated=false`, `no_fake_metrics_from_aggregate_means=true`).
- New aggregate artifacts `artifacts/b14_uncertainty_calibration/b14_uncertainty_calibration.algorithm.json` (schema `b14-uncertainty-calibration-spec-v0`) and `b14_uncertainty_calibration_report.json` (schema `b14-uncertainty-calibration-report-v0`), generated by `--regenerate-artifacts`.
- New bounded public-aggregate feasibility screen `eval/b14_public_aggregate_feasibility_screen.py` (pure Python; reuses `b6_lite_interpretable_policy_search._walk_forbidden` for the public-output forbidden-key scan; `--self-test` synthetic-fixture mode + input-validation block checks + insufficient-data branch check + forbidden scan check). It reads only `artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json`, `artifacts/b12_mechanism_decomposition/b12_public_aggregate_screen_report.json`, and `artifacts/b13_dro_policy_search/b13_public_aggregate_feasibility_report.json` (already-published public aggregates); no raw records, paths, prompts, responses, snippets, or private labels are read or emitted.
- New aggregate artifact `artifacts/b14_uncertainty_calibration/b14_public_aggregate_feasibility_report.json` (schema `b14-public-aggregate-feasibility-screen-v0`).

### Findings

- B14 verdict from the public aggregate screen: `no_go_public_aggregate_only` (B11 has 384 records; the public aggregate is sufficient to produce a feasibility read, but real B14 calibration is not possible from public aggregates alone).
- `uncertainty_calibration_performed=false`, `calibrated_model_claim=false`, `per_record_inputs_available=false`, `uncertainty_score_found=false`, `rotations_evaluated=false`, `metrics_evaluated=false`, `no_fake_metrics_from_aggregate_means=true`, `full_b14_possible_from_public_artifacts=false`.
- Missing inputs that block real B14 from the public artifacts: `no_per_record_uncertainty_scores_in_public_artifact`, `no_per_record_outcomes_in_public_artifact`, `no_paired_cross_model_outputs_in_public_artifact`, `no_schema_repair_per_call_rows_in_public_artifact`, `no_candidate_score_distributions_or_entropy_in_public_artifact`, `no_calibration_test_split_in_public_artifact`, `no_ece_bins_in_public_artifact`, `no_fixed_coverage_thresholds_applicable_in_public_artifact`.
- B11 mixed/partial verdict (`partial_with_failure`), B12 public-aggregate screen statuses, and B13 no-go carried forward unchanged; they do NOT authorize promotion, default change, calibrated-model claim, or a runtime-clean general algorithm.
- Skeleton self-test verdict `insufficient_data` (synthetic fixture; no per-record (uncertainty, outcome) pairs; no metric values computed); `--input` stub verdict `not_implemented`.

### Caveats

- The screen is NOT real B14 uncertainty calibration. It does NOT compute ECE / risk-coverage / selective risk / PFP-at-coverage, does NOT claim empirical calibration, does NOT select an uncertainty score, does NOT declare a winner.
- No promotion, no default change, no calibrated-model claim, no runtime-clean general algorithm claim, no EvidenceCore semantics change (`promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `uncertainty_calibration_performed=false`, `calibrated_model_claim=false`, `per_record_inputs_available=false`, `policy_search_performed=false`, `quality_strategy_tuned=false`, `new_provider_calls=0`).
- Recommended next step: future ephemeral-record B14 calibration (the only path that can perform empirical uncertainty calibration), or first ephemeral-record B13 replay to authorize a candidate policy. The public aggregate alone is insufficient for either.


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

Add the B18 OOD / temporal evaluation **preregistration + evaluator skeleton + bounded public-aggregate no-go screen**. This is a bounded preregistration / no-go phase, NOT a real OOD / temporal evaluation, NOT a policy search, NOT a quality strategy tuning, NOT a default change, NOT an EvidenceCore semantics change, NOT a promotion. Real B18 (frozen, preregistered OOD / temporal evaluation across five frozen split axes — `temporal_split`, `repo_split`, `language_split`, `model_family_split`, `adversarial_split` — under a no-retuning protocol with metrics ood_generalization_gap, temporal_holdout_delta, repo_holdout_metric, language_holdout_metric, model_family_holdout_metric, adversarial_robustness_score, worst_group_metric, cvar_tail_metric, per_cell_denominator, temporal_split_integrity, no_retuning_proof_metric, citation_validity, stale_evidencecore_rejection_rate; worst-group reporting; rotating fresh-validation split stratified by `(repo, language, model_family, time)`) requires per-record OOD / temporal inputs + per-record records + per-record time index + per-record commit chronology + per-record repo / language / model_family axes + per-record task category + per-record adversarial holdout membership + per-record temporal holdout membership + per-record outcome label + per-record citation validity + per-record stale rejection + per-record EvidenceCore rejection + per-record randomized run order proof + per-record no-retuning proof + a shared frozen evaluation protocol manifest, which are unavailable in any current public artifact. The existing B11 / R15 / R20 / R26 aggregates are aggregate-only / metadata-only carry-forward, not OOD / temporal proof and not promotion evidence; they do NOT contain per-record records, a time axis, commit chronology, per-repo-per-language cells, a model_family x repo matrix, adversarial holdout outcomes, or temporal holdout outcomes; the R15 / R20 / R26 repo locks are synthetic / static snapshots with no real commit chronology or time axis.

### Implementation notes

- New preregistration docs `docs/en/b18-ood-temporal-evaluation.md` and `docs/zh/b18-ood-temporal-evaluation.md` (frozen split axes, no-retuning protocol, metric registry, hard gates, experimental structure, success/partial/failure criteria). Explicit that the existing B11 / R15 / R20 / R26 aggregates are aggregate-only / metadata-only carry-forward — not promotion evidence, not OOD / temporal proof; they do NOT contain per-record records, a time axis, commit chronology, per-repo-per-language cells, a model_family x repo matrix, adversarial holdout outcomes, or temporal holdout outcomes.
- New evaluator skeleton `eval/b18_ood_temporal_evaluation.py` (pure Python; mirrors B13/B14/B15/B16/B17 freeze style): frozen `build_algorithm_spec` + `build_report`; read-only `--self-test` (synthetic fixture mechanics only, compares in-memory expected artifacts to on-disk artifacts and fails on drift, does not mutate checked-in artifacts); `--regenerate-artifacts` is the explicit checked-in-artifact mutating path (also writes the canonical public no-go screen report); `--public-screen --out <path>` runs the bounded public-aggregate no-go screen from the current public artifacts and writes to the explicit `--out` path (if `--out` absent, the canonical public screen artifact is written ONLY when invoked from `--regenerate-artifacts`; otherwise `--out` is required for non-self-test); `--input` stub requires explicit `--out`, refuses to write ANY path inside `artifacts/b18_ood_temporal_evaluation/`, and returns `not_implemented` / `insufficient_data` (NOT empirical OOD / temporal evaluation). Safety fields preserved verbatim: `stage_is_ood_temporal_evaluation=true`, `ood_temporal_evaluation_performed=false`, `metrics_evaluated=false`, `policy_search_performed=false`, `quality_strategy_tuned=false`, `real_ood_temporal_supported=false`, `retrieval_policy_changed=false` for stub/synthetic; `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `new_provider_calls=0`. The skeleton MUST NOT compute fake ood_generalization_gap / temporal_holdout_delta / repo_holdout_metric / language_holdout_metric / model_family_holdout_metric / adversarial_robustness_score / worst_group_metric / cvar_tail_metric / per_cell_denominator / temporal_split_integrity / no_retuning_proof_metric / citation_validity / stale_evidencecore_rejection_rate metrics from the B11 aggregate means or from the R15 / R20 / R26 repo locks; the synthetic fixture validates only metric NAMES and gates (`metrics_evaluated=false`, `no_fake_ood_metrics_from_aggregate_means=true`).
- New aggregate artifacts `artifacts/b18_ood_temporal_evaluation/b18_ood_temporal_evaluation.algorithm.json` (schema `b18-ood-temporal-evaluation-spec-v0`), `b18_ood_temporal_evaluation_report.json` (schema `b18-ood-temporal-evaluation-report-v0`), and `b18_public_ood_temporal_screen_report.json` (schema `b18-public-ood-temporal-screen-v0`), generated by `--regenerate-artifacts`.
- New bounded public-aggregate no-go screen integrated into `eval/b18_ood_temporal_evaluation.py` (`--public-screen` mode + `screen_public` function; reuses `b6_lite_interpretable_policy_search._walk_forbidden` for the shared public-output forbidden-key scan plus the B18 evaluator's own stricter `_recursive_key_scan`; `--self-test` includes `public_screen_no_go` and `public_screen_optional_artifacts_absent` checks). It reads only `artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json`, `fixtures/r15/repos.lock.jsonl`, `fixtures/r20_auto_wide/repos.lock.jsonl`, `fixtures/r26_auto_stress/repos.lock.jsonl`, `fixtures/r20_auto_wide/dataset_manifest.json`, and `fixtures/r26_auto_stress/dataset_manifest.json` (already-published public aggregates / metadata); each guard is optional and absent artifacts are reported as `not_present` rather than failing. No raw records, paths, prompts, responses, snippets, diffs, patches, test results, solve labels, agent event logs, per-record records, time indices, commit chronology, outcome labels, content SHAs, or private labels are read or emitted.

### Findings

- B18 verdict from the public-aggregate no-go screen: `no_go_public_aggregate_only` (every present public artifact is aggregate-only or a synthetic static snapshot; none contains per-record records, a time axis, commit chronology, per-repo-per-language cells, a model_family x repo matrix, adversarial holdout outcomes, or temporal holdout outcomes).
- `stage_is_ood_temporal_evaluation=true`, `ood_temporal_evaluation_performed=false`, `metrics_evaluated=false`, `policy_search_performed=false`, `quality_strategy_tuned=false`, `real_ood_temporal_supported=false`, `retrieval_policy_changed=false`, `no_fake_ood_metrics_from_aggregate_means=true`, `full_b18_ood_temporal_evaluation_possible_from_public_artifacts=false`, `new_provider_calls=0`.
- Missing inputs that block real B18 from the public aggregates: `no_per_record_records`, `no_time_axis`, `no_commit_chronology`, `no_per_repo_per_language_cells_in_public_b11`, `no_model_family_x_repo_matrix`, `no_adversarial_holdout_outcomes`, `no_temporal_holdout_outcomes`.
- B11 aggregate `promotion_ready=false`, `aggregate_only_public_artifact=true`; R15 / R20 / R26 repo locks are synthetic static snapshots (single static snapshot commit label, no chronological ordering) — all carried forward unchanged as pre-B18 signals only, NOT promotion, NOT OOD / temporal proof.
- Skeleton self-test verdict `insufficient_data` (synthetic fixture; no per-record OOD / temporal inputs; no metric values computed); `--input` stub verdict `not_implemented`.

### Caveats

- The screen is NOT real B18 OOD / temporal evaluation. It does NOT compute ood_generalization_gap / temporal_holdout_delta / repo_holdout_metric / language_holdout_metric / model_family_holdout_metric / adversarial_robustness_score / worst_group_metric / cvar_tail_metric / per_cell_denominator / temporal_split_integrity / no_retuning_proof_metric / citation_validity / stale_evidencecore_rejection_rate metrics, does NOT claim OOD / temporal evaluation, does NOT claim generalization, does NOT promote a retrieval variant, does NOT change retrieval policy, does NOT declare a winner.
- No promotion, no default change, no retrieval-policy change, no backend quality promotion, no OOD / temporal evaluation, no policy search, no quality strategy tuning, no EvidenceCore semantics change, no metrics evaluated (`promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `retrieval_policy_changed=false`, `backend_quality_promoted=false`, `stage_is_ood_temporal_evaluation=true`, `ood_temporal_evaluation_performed=false`, `metrics_evaluated=false`, `policy_search_performed=false`, `quality_strategy_tuned=false`, `real_ood_temporal_supported=false`, `new_provider_calls=0`).
- The existing B11 / R15 / R20 / R26 aggregates are aggregate-only / metadata-only carry-forward — they are NOT OOD / temporal proof and NOT promotion evidence; they do NOT contain per-record records, a time axis, commit chronology, per-repo-per-language cells, a model_family x repo matrix, adversarial holdout outcomes, or temporal holdout outcomes; the R15 / R20 / R26 repo locks are synthetic / static snapshots with no real commit chronology or time axis.
- Recommended next step: future prospective per-record data collection with a real time axis and commit chronology per repo, plus per-repo / per-language / per-model-family cells and adversarial and temporal holdout memberships under a frozen no-retuning protocol, then run a B18 OOD / temporal evaluation. The public aggregates alone are insufficient.

## 2026-06-19 — B19 Theoretical Synthesis (Model-Robust Selective Evidence Conversion)

### Objective

Write the **theoretical synthesis** of the B10-B18 Breakthrough Sprint as a paper-style algorithm report for the candidate algorithm concept **Model-Robust Selective Evidence Conversion**. This is synthesis-only: do NOT run providers, do NOT change retrieval / default / `EvidenceCore`, do NOT claim promotion. Synthesize B10 / B10B / B11 / B12 / B13 / B14 / B15 / B16 / B17 / B18; introduce NO new metrics and NO new claims beyond B10-B18.

### Implementation notes

- New synthesis docs `docs/en/b19-theoretical-synthesis.md` and `docs/zh/b19-theoretical-synthesis.md` (algorithm concept; inputs; outputs/actions; core principles; problem statement; algorithm sketch/pseudocode; evidence boundary; policy-learning loop; adapter boundary; evaluation protocol; synthesized evidence B10-B18; current empirical evidence; no-go gaps; promotion blockers; next research program; bottom line). Explicit that B19 is synthesis-only and that all no-promotion flags are false.
- New evaluator `eval/b19_theoretical_synthesis.py` (pure Python): frozen `build_report`; read-only `--self-test` (compares in-memory expected report to on-disk artifact, fails on drift, does NOT mutate checked-in artifacts); `--regenerate-artifacts` is the ONLY path that mutates checked-in artifacts (rewrites the canonical report and re-runs the self-test); `--input` is a `not_implemented` stub because B19 is synthesis-only (requires `--out`, refuses to write inside `artifacts/b19_theoretical_synthesis/`).
- New aggregate artifact `artifacts/b19_theoretical_synthesis/b19_theoretical_synthesis_report.json` (schema `b19-theoretical-synthesis-report-v0`, claim level `theoretical_synthesis_of_b10_through_b18`), generated by `--regenerate-artifacts`.
- The B19-specific forbidden scan reuses the shared `b6_lite_interpretable_policy_search.FORBIDDEN_PUBLIC_KEYS` set and a digest-like value check (`[A-Fa-f0-9]{32,}`), but does NOT apply the shared helper's `>256 chars = long_string` rule because the synthesis IS intentionally long prose. The report's own `report_content_sha256` drift-guard self-hash is whitelisted by key name.
- A drift guard (`report_content_sha256`) is embedded as a SHA-256 over the canonical sorted-keys JSON of the report content excluding `generated_at` and `report_content_sha256` itself. The self-test recomputes and asserts equality.

### Findings

- B19 verdict: synthesis-only; the B10-B18 evidence boundary is carried forward unchanged. The only empirical numbers carried forward verbatim are the B11 official integrated matrix deltas (balanced_v1 vs p25): `Δgold_span -0.002604`, `ΔSpanF0.5 -0.001899`, `Δfalse_span -0.054688`, `ΔPFP -0.020833`, `Δmodel_calls -0.354167`. The self-test asserts them byte-for-byte against `artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json`.
- All no-promotion flags false: `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `runtime_clean_policy_supported=false`, `downstream_agent_value_proven=false`, `ood_temporal_supported=false`, `quiver_systems_supported=false`, `is_new_experiment=false`, `ran_providers=false`, `changed_retrieval_default_evidencecore=false`.
- Safety invariants preserved: `aggregate_only_public_artifact=true`, `candidate_not_fact=true`, `not_evidence=true`, `llm_output_not_evidence=true`, `new_provider_calls=0`, `forbidden_public_scan_clean=true`, `report_drift_guarded=true`, `docs_links_exist=true`, `synthesized_source_artifacts_pinned=true`, `no_fake_metrics_beyond_b10_b18=true`.
- Self-test verifies: all 10 required formal sections present and non-empty; all no-promotion flags literal False; B11 deltas present and exact (cross-checked against source artifact); all 10 synthesized source artifacts present on disk; B19 docs links exist (en + zh); forbidden public scan clean; report content hash drift guard matched.

### Caveats

- B19 is NOT a new experiment, NOT promotion, NOT a default change, NOT an `EvidenceCore` semantics change, NOT a runtime-clean policy claim, NOT a downstream-agent value claim, NOT an OOD/temporal claim, NOT a QuIVer systems claim.
- The synthesis carries forward the B12 / B13 / B14 / B15 / B16 / B17 / B18 no-go / screen-only / prior-screen statuses UNCHANGED. B11 `partial_with_failure` is carried forward UNCHANGED. B10 `runtime_clean=false` and B10B `runtime_shadow_ambiguous_supported=false` are carried forward UNCHANGED.
- No raw records / paths / spans / snippets / prompts / responses / gold labels / `content_sha` / provider keys / api keys are present in the public artifact. The drift-guard self-hash is the only digest-like value and is whitelisted by key name.
- Recommended next step: the B19 next-research-program list (runtime-clean B10B predicate, per-record mechanism / DRO / calibration / pack-policy / downstream-agent / QuIVer / OOD-temporal data collection), then a separate promotion preregistration. The synthesis itself never authorizes promotion.

## 2026-06-19 — C2 B12 CI Canary with Private P21 Records

### Objective

Verify the new C1 private-record adapter and B12 real `--input` replay path against an actual GitHub CI run, rather than only synthetic fixtures. The goal is to prove that B12 can consume runner-temp private P21 records and emit an aggregate-only public report while preserving the public/private boundary.

### Implementation notes

- First tried a tiny `3`-task prefix canary (run `27816674482`); it failed the existing P21 privacy gate because the sample did not exercise remote LLM snippets. This was a canary coverage failure, not a B12 replay failure.
- Reran with `round_robin_public_buckets` and `max_tasks=12` (run `27816890557`), which exercised the provider path and passed the P21 privacy gate, B10B, B11, and B12 report upload flow.
- Added aggregate-only artifact `artifacts/c2_b12_canary/c2_b12_canary_report.json` summarizing only public counts, verdicts, deltas, and safety flags. No private records, task IDs, raw repo IDs, paths, spans, content hashes, prompts, responses, snippets, provider URLs, or provider keys are committed.

### Findings

- B12 report used `replay_source="ci_ephemeral_records"` and consumed real private P21 records through `eval/c1_private_records.py`.
- Counts: `total_records=12`, `complete_records=12`, `incomplete_record_count=0`, `missing_required_outcome_count=0`, `balanced_branch_count=4`, `p25_llm_eligible_count=10`, `actual_call_avoided_count=4`, `random_selected_count=4`.
- Canary verdict: `partial`. H1 `refuted`, H2 `refuted`, H3 `supported`, H4 `insufficient_data` (single model family; H4 does not block H1-H3 verdict by design).
- A vs D deltas on the canary: `gold_span 0.0`, `SpanF0.5 0.0`, `false_span 0.0`, `PFP 0.0`, `model_calls -0.333333`. A vs E false-span delta was `-0.083334`.

### Caveats

- This is a canary-level result only: one repo, one model family, 12 records. It does NOT prove the B12 mechanism globally and does NOT promote, default-change, or make balanced_v1 runtime-clean.
- The next step is a full B12 matrix over the B11 repo/model cells, then aggregate the B12 reports before making mechanism claims.

## 2026-06-19 — C2/B12 Official Matrix Aggregate Combiner

### Objective

Implement the C2/B12 official matrix aggregate combiner: a bounded derived
aggregate rollup that combines the per-run `b12-mechanism-decomposition-report-v0`
public aggregate reports from a finished C2/B12 official integrated matrix run
into a single aggregate-only public artifact. This is aggregate-only; it does
NOT run providers, does NOT run policy search, does NOT promote, does NOT change
defaults, and does NOT alter `EvidenceCore` semantics.

### Implementation notes

- New evaluator `eval/b12_matrix_combiner.py` (pure Python). CLI: `--self-test`
  (synthetic 3-cell + 1-exclusion fixture, validates schema/safety/weighted
  means/forbidden scan/verdict); `--artifacts-dir <path>` (recursively discover
  `b12_mechanism_decomposition_report.json` under it, parsing run_id from the
  `real-provider-p21_llm_rich-<run_id>` path component); optional `--manifest
  <path>` (enforces `included`/`excluded` counts and reconciles every discovered
  report run_id to a manifest included cell); `--out <path>` default
  `artifacts/b12_mechanism_decomposition/b12_matrix_aggregate_report.json`.
- Output schema: `b12-mechanism-matrix-aggregate-report-v0`. Aggregate-only
  public: NO run IDs, task IDs, raw repo IDs, paths/spans/content_sha/prompts/
  responses/snippets/provider URLs/keys. Public repo slice IDs and model-family
  names are re-published only as slice IDs from the manifest, never as run IDs.
- Per-input validation: schema version `b12-mechanism-decomposition-report-v0`,
  `aggregate_only_public_artifact=true`, `promotion_ready=false`,
  `default_should_change=false`, `evidencecore_semantics_changed=false`,
  `replay_source == ci_ephemeral_records`, no forbidden public keys/values
  (reuses `b6_lite_interpretable_policy_search._walk_forbidden`),
  `complete_records > 0` and `incomplete_record_count == 0` for included cells.
- Aggregates over the 28 analyzable cells: `cell_count_target=32`,
  `analyzable_cell_count=28`, `excluded_cell_count=4`; `record_count_total`;
  `coverage_exclusions` (by public repo slice + model family + reason, no run
  ids); `verdict_counts` over per-run B12 verdicts; `hypothesis_status_counts`
  for H1/H2/H3/H4; record-weighted mean deltas vs D/E/B for `gold_span`,
  `span_f0_5`, `false_span`, `primary_false_positive_rate`, `model_calls`
  (weighted by `complete_records`), plus a record-weighted mean robust utility
  of A; `replay_count_totals` for `balanced_branch_count`,
  `p25_llm_eligible_count`, `actual_call_avoided_count`,
  `random_selected_count`; conservative `mechanism_summary`.

### Findings — run reconciliation

- Target matrix: 32 cells (8 public repo slices × 4 public model families).
- Analyzable: 28 cells (all 4 model families on 7 of 8 repo slices —
  `py_fastapi`, `py_pytest`, `ts_hono`, `go_chi`, `go_prometheus`, `rust_deno`,
  `java_spring_petclinic`).
- Excluded: 4 cells, all `ts_vite` × {kimi, qwen, deepseek_flash,
  deepseek_pro}, with `status=coverage_insufficient_no_remote_llm_snippet`.
  These cells failed the old P21 privacy gate because they did not exercise
  remote LLM snippets even at `max_tasks=24`. They are treated as
  coverage-insufficient, NOT as B12 mechanism failures.
- Transient Cargo failures occurred during the matrix run and were retried
  successfully (two `ts_hono × deepseek_pro` and `java_spring_petclinic ×
  deepseek_flash` retries succeeded with `source=
  retry_success_replacing_transient_failure`). No promotion, default, or
  runtime-clean claim was made on the back of these retries.

### Findings — key metrics from the generated aggregate

- `record_count_total=336` (12 complete records per cell).
- `verdict_counts={"partial": 28}`.
- `hypothesis_status_counts`: H1 `supported: 3 / refuted: 25`; H2
  `supported: 8 / refuted: 20`; H3 `supported: 28`; H4 `insufficient_data: 28`
  (every cell is a single-model-family slice, so H4 needs multi-model
  aggregation across cells; H4 insufficient_data does NOT block the H1-H3
  verdict by design).
- Record-weighted A (full balanced) deltas vs D (P25 default): `Δgold_span 0.0`,
  `ΔSpanF0.5 0.0`, `Δfalse_span -0.029762`, `ΔPFP -0.014881`,
  `Δmodel_calls -0.333333`; vs E (random call reduction): `Δgold_span -0.044643`,
  `ΔSpanF0.5 0.001569`, `Δfalse_span -0.592262`, `ΔPFP -0.026786`,
  `Δmodel_calls 0.0`; vs B (deterministic call reduction): `Δgold_span 0.0`,
  `ΔSpanF0.5 0.0`, `Δfalse_span -0.130952`, `ΔPFP -0.035714`, `Δmodel_calls 0.0`.
- `weighted_mean_robust_utility_a = 0.054155`.
- `replay_count_totals`: `balanced_branch_count=112`,
  `p25_llm_eligible_count=324`, `actual_call_avoided_count=112`,
  `random_selected_count=112`.
- `aggregate_verdict = partial_with_coverage_exclusions`.

### Caveats

- This is an aggregate of per-cell B12 reports, NOT a promotion step, NOT a
  default change, NOT a runtime-clean general algorithm claim, NOT an
  `EvidenceCore` semantics change. `promotion_ready=false`,
  `default_should_change=false`, `evidencecore_semantics_changed=false`,
  `policy_search_performed=false`, `runtime_clean_policy_supported=false`,
  `new_provider_calls=0`, `candidate_not_fact=true`.
- The 4 `ts_vite` exclusions are coverage gaps (no remote LLM snippets), NOT
  B12 mechanism failures. Mechanism claims are scoped to the 28 analyzable
  cells only.
- A global `supported` verdict is never emitted by policy: with coverage
  exclusions present the verdict is `partial_with_coverage_exclusions`; even
  at 32/32 it would remain `partial` (do not overclaim H1/H2/H3).
- H2 causal attribution is limited by the single frozen E seed per cell
  (`e_random_seed=20260618`); seed-averaging is deferred.
- Recommended next step: B13 distributionally robust policy search WITH CAUTION
  (B13 must not be treated as authorized by a B12 supported verdict), or a
  future B12 matrix rerun that closes the `ts_vite` coverage gap.

## 2026-06-19 — C3 Budgeted Evidence Acquisition v0 (Replay Evaluator)

### Objective

Implement C3 Budgeted Evidence Acquisition v0 as a real replay policy
experiment over the C1 private-records adapter, not a skeleton. C3 replays a
frozen interpretable candidate policy set (each a function of a runtime-clean
`route_features` dict only) against P21 per-strategy outcomes, computes a
budgeted evidence utility, and compares candidate policies to the P25 and
balanced_v1 baselines under a common-complete denominator.

### Implementation

- New evaluator `eval/c3_budgeted_evidence_acquisition.py` (pure Python; uses
  `eval/c1_private_records.py`). Modes: `--self-test` (synthetic fixture
  only, no empirical claim), `--regenerate-artifacts` (canonical synthetic
  spec + self-test report), `--input <path>` (real aggregate-only replay
  report; `replay_source="ci_ephemeral_records"`).
- New frozen algorithm spec
  `artifacts/c3_budgeted_evidence_acquisition/c3_budgeted_evidence_acquisition.algorithm.json`
  (deterministic, stable sha256
  `9c1b0842e030c95d1e54cd2bfe97b0bdf39335560172de8e25d3677ff8e5e8d2`).
- New synthetic self-test report
  `artifacts/c3_budgeted_evidence_acquisition/c3_budgeted_evidence_acquisition_report.json`.
- New docs `docs/en/c3-budgeted-evidence-acquisition.md` and
  `docs/zh/c3-budgeted-evidence-acquisition.md`.
- CI workflow integration in `.github/workflows/real-provider-benchmark.yml`:
  after B12 consumes `$P25_RECORDS` and before `rm -f "$P25_RECORDS"`, C3
  runs `python3 eval/c3_budgeted_evidence_acquisition.py --input "$P25_RECORDS"
  --out artifacts/real_provider_ci/c3_budgeted_evidence_acquisition_report.json`.
  Per-cell C3 emits sufficient stats only and no winner.

### Frozen design (no outcome tuning)

- Allowed runtime features (frozen allowlist of 10): `query_noise`,
  `candidate_support_exists`, `local_anchor`, `rrf_backed_by_anchor`,
  `candidate_count`, `symbol_regex_agree_file`, `symbol_regex_agree_span`,
  `rrf_anchor_agree_file`, `rrf_anchor_agree_span`, `dense_support_present`.
  Absent features are treated as false / 0; only aggregate
  `feature_presence_counts` are emitted (the raw `route_features` dict is a
  forbidden public key).
- Allowed candidate actions (frozen): `candidate_baseline`,
  `weak_candidate_only`, `llm_span_narrow`, `llm_filter`,
  `llm_abstain_filter`. P25 and balanced_v1 are NOT candidate actions; they
  are baselines only and marked `runtime_clean_candidate_policy=false`,
  `benchmark_label_taint=true`.
- Frozen candidate policy set (6, interpretable, NOT outcome-derived):
  `local_only`, `weak_on_noise_else_local`,
  `span_narrow_on_anchor_else_local`,
  `filter_on_noise_else_span_narrow_on_anchor_else_local`,
  `abstain_filter_on_disagreement_else_span_narrow_on_anchor_else_local`,
  `weak_on_disagreement_span_on_anchor_else_local`.
- Objective constants: `lambda=1.0`, `mu=1.0`, `cost_weight=0.1`.
  `utility = span_f0_5 - lambda*added_false_span -
  mu*primary_false_positive_rate - cost_weight*model_calls`.
- Coverage: common-complete denominator across all candidate policies and
  baselines; a record is excluded if any selected action outcome is missing.
  `complete_records==0` => `status=coverage_insufficient`. Per-cell report
  declares NO winner: `winner_declared=false`,
  `cell_diagnostic_rank_only=true`,
  `candidate_selection_deferred_to_matrix_combiner=true`.

### Runtime-clean hard rule

Candidate policies receive ONLY a projected `route_features` dict, never a
`PrivateRecord`, and never read `task_bucket` / `task_risk_tags` / `has_gold`
/ `score_group` / `outcomes` / `task_id` / `repo_id` / `model_family` /
`language` / private hashes. The evaluator verifies routing invariance via a
real PrivateRecord-field scrub test (scrubbed copy with every non-
`route_features` field replaced with sentinel/permuted values guaranteed to
differ from the original) and surfaces
`selected_actions_invariant_under_private_field_permutation=true`
and `runtime_clean_policy_inputs_only=true`.

### Safety invariants

- `empirical_algorithm_experiment_performed=true` and
  `policy_search_or_enumeration_performed=true` only under `--input` on real
  records (synthetic self-test sets both false).
- `replay_only=true`, `remote_calls_by_c3=0`, `model_calls_by_replay=0`,
  `promotion_ready=false`, `default_should_change=false`,
  `evidencecore_semantics_changed=false`,
  `aggregate_only_public_artifact=true`.
- Forbidden public keys scan rejects `task_id` / `repo_id` / `run_id` /
  `private_record_hash` / `route_features` / `outcomes` / `p31_score_gold` /
  `p31_candidate_pools` / `p33b_anchor_subtypes` / `task_risk_tags` / `path`
  / `span` / `content_sha` / `query` / `raw_query` / `snippet` / `prompt`
  / `response` / `provider_key` / `api_key` / `base_url` / `score_group`
  / `has_gold` / `strategy_results` / `source_ordinal` / `candidate_id` /
  `record_hash` / `test_id` / `private_label` / `private_labels` / `label`
  / `labels` / `gold_spans` / `hash` / `digest` / `task_bucket`. The scan is
  exact-match on key names, so safe metric names like `added_false_span` /
  `primary_false_positive_rate` / `added_gold_span` remain allowed. Aggregate
  `model_family` / `language` counts are emitted; `task_bucket` counts are
  omitted for v0.

### Self-test

`python3 eval/c3_budgeted_evidence_acquisition.py --self-test` passes (11
checks: forbidden scan, spec hash stable, action/feature allowlists frozen,
objective constants frozen, runtime-clean invariance (real PrivateRecord-
field scrub test), P25/balanced not candidate policies, synthetic-fixture
mechanics, `--input` full mode on a synthetic C1 payload, missing-outcome =>
`coverage_insufficient`, no per-cell winner, on-disk artifacts match in-memory
build (drift detection), docs paths exist). The self-test is strictly
read-only and MUST NOT mutate checked-in artifacts; use
`--regenerate-artifacts` to update canonical artifacts.

### Caveats

- C3 is a budgeted replay policy experiment, NOT a promotion step, NOT a
  default change, NOT an `EvidenceCore` semantics change, NOT a
  runtime-clean general algorithm proof. `promotion_ready=false`,
  `default_should_change=false`, `evidencecore_semantics_changed=false`.
- Per-cell C3 declares NO winner; candidate selection is deferred to the
  matrix combiner. The diagnostic rank is ordering-only, not a claim.
- Synthetic self-test fixtures confer no empirical support; only `--input`
  on real P21 records sets `empirical_algorithm_experiment_performed=true`.
- The frozen candidate policy set is an enumeration, not a tuned search; no
  threshold or policy is tuned from outcomes.

## 2026-06-19 — C3 Budgeted Evidence Acquisition Matrix Combiner

### Objective

Build the committed aggregate-only combiner for the C3 official matrix,
mirroring `eval/b12_matrix_combiner.py` but scoped to C3 budgeted evidence
acquisition per-cell reports. Combine the 28 analyzable per-cell
`c3-budgeted-evidence-acquisition-report-v0` artifacts plus 4 `ts_vite`
coverage exclusions into a single derived aggregate with diagnostic-rank-only
output and no winner/selection/promotion/default claim.

### Implementation

- New combiner `eval/c3_matrix_combiner.py` (pure Python; imports
  `eval/b6_lite_interpretable_policy_search.py` for the shared
  `_walk_forbidden` public-output scan). Modes: `--self-test` (synthetic 2-cell
  + 1-exclusion fixture, no private records), and the real combine
  (`--artifacts-dir` + `--manifest` + `--out`).
- Inputs: per-run artifacts containing
  `c3_budgeted_evidence_acquisition_report.json` under
  `<run_id>/real-provider-p21_llm_rich-<run_id>/artifacts/real_provider_ci/`,
  and the flat-list manifest of the 32 planned cells (4 `ts_vite` cells are
  `status=planned_exclusion_coverage_insufficient` with `run_id=null` and are
  included as coverage exclusions; 28 cells have real run_ids).
- New artifact
  `artifacts/c3_budgeted_evidence_acquisition/c3_matrix_aggregate_report.json`
  (canonical C3 matrix aggregate; `generated_by=c3_matrix_combiner`,
  `schema_version=c3-budgeted-evidence-acquisition-matrix-report-v0`,
  `claim_level=budgeted_matrix_aggregate_public_v0`).
- Updated docs `docs/en/c3-budgeted-evidence-acquisition.md` and
  `docs/zh/c3-budgeted-evidence-acquisition.md` with a "Matrix combiner"
  section.

### Per-cell validation (enforced on every included report)

Every included C3 per-cell report is verified to satisfy:
`schema_version=c3-budgeted-evidence-acquisition-report-v0`,
`generated_by=c3_budgeted_evidence_acquisition`,
`replay_source=ci_ephemeral_records`,
`empirical_algorithm_experiment_performed=true`, `winner_declared=false`,
`cell_diagnostic_rank_only=true`,
`candidate_selection_deferred_to_matrix_combiner=true`,
`runtime_clean_policy_inputs_only=true`,
`selected_actions_invariant_under_private_field_permutation=true`,
`promotion_ready/default_should_change/evidencecore_semantics_changed=false`,
`remote_calls_by_c3=0`, `model_calls_by_replay=0`,
`aggregate_only_public_artifact=true`, the per-cell safety invariants
`forbidden_public_keys_scanned=true` and
`no_raw_path_digest_provider_strings=true`, `complete_records>0`,
`incomplete_record_count==0`, and byte-exact frozen
`candidate_policy_ids` / `action_set` matching the C3 spec. The shared
`_walk_forbidden` scan is re-run on every input. Any expected included run
missing a report hard-fails unless the manifest marks it
coverage-insufficient.

### Aggregate mechanics

- `planned_cells=32`, `included_cells=28`, `coverage_excluded_cells=4`,
  `total_records` / `complete_records` = 336 / 336 (sum across cells).
- `per_candidate_policy`: for each of the 6 frozen candidate policy ids,
  record-weighted mean (`complete_records` weight) of each safe metric
  (`span_f0_5`, `added_gold_span`, `added_false_span`,
  `primary_false_positive_rate`, `model_calls`, `utility`) plus sum totals.
- `baseline_aggregates` for `p25` and `balanced_v1` (same weighting).
- `deltas_vs_p25` and `deltas_vs_balanced_v1`: record-weighted mean of the
  per-cell per-policy deltas for each safe metric.
- `diagnostic_rank_only_global`: candidate policies sorted by descending
  aggregate mean `utility`; `winner_declared=false`,
  `candidate_selection_deferred_to_future_preregistered_matrix=true`,
  `candidate_selected=false` for every policy. Ordering only — no winner,
  no freeze, no selection.
- `runtime_feature_coverage`: sum of `feature_presence_counts` across cells.
- `coverage_exclusion_summary` / `coverage_exclusion_reason_counts`: counts
  by `(repo_slice_id, model_family, reason)`; no run IDs.
- `artifact_manifest_summary`: count-only (no sha256 digests, to avoid
  hash-shaped values under the public forbidden-value scan).

### Official matrix result (28 analyzable + 4 excluded)

- `status=matrix_aggregate_ok_with_exclusions`.
- `diagnostic_rank_only_global[0]=weak_on_disagreement_span_on_anchor_else_local`
  (mean `utility=-0.167791`, mean `model_calls=0.511905`); followed by
  `abstain_filter_on_disagreement_else_span_narrow_on_anchor_else_local`
  (`utility=-0.199933`), `span_narrow_on_anchor_else_local`
  (`utility=-0.268981`),
  `filter_on_noise_else_span_narrow_on_anchor_else_local`
  (`utility=-0.270171`), `weak_on_noise_else_local` (`utility=-1.578684`),
  `local_only` (`utility=-1.638208`). **No winner declared.**
- Baselines: `p25` mean `utility=-0.227093` (mean `model_calls=0.964286`);
  `balanced_v1` mean `utility=-0.146141` (mean `model_calls=0.630953`).
- Top diagnostic delta vs `p25`:
  `weak_on_disagreement_span_on_anchor_else_local`
  (`Δutility=+0.059303`, `Δmodel_calls=-0.452381`).
- `runtime_feature_coverage`: `local_anchor=280`,
  `rrf_backed_by_anchor=172`, `rrf_anchor_agree_file=172`,
  `rrf_anchor_agree_span=172`, `candidate_count=123`,
  `candidate_support_exists=123`, `dense_support_present=123`,
  `symbol_regex_agree_file=56`, `symbol_regex_agree_span=56`,
  `query_noise=28`.

### Safety invariants (matrix aggregate)

- `aggregate_only_public_artifact=true`, `promotion_ready=false`,
  `default_should_change=false`, `evidencecore_semantics_changed=false`,
  `runtime_clean_candidate_evaluated=true`, `winner_declared=false`,
  `candidate_selected=false` (all policies),
  `candidate_selection_deferred_to_future_preregistered_matrix=true`,
  `remote_calls_by_combiner=0`, `model_calls_by_combiner=0`,
  `no_run_ids_emitted=true`, `no_task_ids_in_artifact=true`,
  `no_paths_spans_hashes_snippets_prompts_responses=true`,
  `no_forbidden_public_keys=true`,
  `no_raw_path_digest_provider_strings=true`. The shared
  `_walk_forbidden` scan is run on the final output (`integrity.
  forbidden_public_key_scan_clean=true`).

### Self-test

`python3 eval/c3_matrix_combiner.py --self-test` passes (5 checks: happy
path with weighted-mean/delta/baseline rollups + diagnostic rank + coverage
exclusion counts + no-winner/no-selection; forbidden-key injection rejection;
missing-report hard-fail; no-manifest real-path fail-closed; empty-input
block). The self-test is strictly read-only and uses synthetic fixtures
only; it confers no empirical support.

### Caveats

- The C3 matrix aggregate is **diagnostic-rank-only**. It is NOT a promotion
  step, NOT a default change, NOT an `EvidenceCore` semantics change, NOT a
  runtime-clean general algorithm proof, and NOT a candidate selection.
- `diagnostic_rank_only_global` is ordering only; the top-ranked policy is
  NOT a selected policy. Selection is deferred to a future preregistered
  matrix.
- The 4 `ts_vite` coverage exclusions
  (`coverage_insufficient_no_remote_llm_snippet`) remain an open coverage
  gap; they are NOT C3 mechanism failures.
- Public repo slice IDs and model-family names are emitted as `repo_slice_id`
  / `model_family` (matching B11/B12), not as raw `repo_id`; coverage
  exclusions carry no run IDs.

## 2026-06-20 — C4 External Benchmark Adapters — Schema Readiness v1

### Objective

Implement a real (non-skeleton) external benchmark adapter / schema
readiness layer for ContextBench and SWE-Explore, producing an
aggregate-only public artifact that records adapter/schema readiness
without persisting any row-level benchmark contents. C4.1 is **not** an
external benchmark performance evaluation, **not** a benchmark result,
and **not** a promotion or default change.

### Implementation

- New evaluator `eval/c4_external_benchmark_adapters.py` with argparse CLI:
  `--self-test`, `--benchmark {contextbench,swe_explore,all}`,
  `--schema-smoke`, `--limit` (default 3, hard cap 10), `--out`. Default
  invocation generates the canonical aggregate report from built-in known
  source/schema metadata plus synthetic self-test status, with no network.
- Canonical aggregate-only artifact
  `artifacts/c4_external_benchmark_adapters/c4_external_benchmark_adapter_report.json`
  (schema `c4_external_benchmark_adapters.v1`,
  `claim_level=adapter_schema_readiness_only`).
- ContextBench spec: dataset_id `Contextbench/ContextBench`; configs
  `default/train` 1136, `contextbench_verified/train` 500; schema-only
  field names `instance_id`, `original_inst_id`, `repo`, `repo_url`,
  `language`, `base_commit`, `gold_context`, `patch`, `test_patch`,
  `problem_statement`, `f2p`, `p2p`, `source`; license
  `unknown_dataset_license`; row-level redistribution disabled.
- SWE-Explore spec: dataset_id `SWE-Explore-Bench/SWE-Explore-Bench`;
  config `default/train` 848; schema-only field names `instance_id`,
  `repo_path`, `repo_dir`, `ground_truth`, `read_step_info`, `meta`,
  `dataset`; private categories include `ground_truth.*`,
  `read_step_info.*`, repo paths, file maps, line ranges; license
  `cc-by-nc-nd-4.0`; row-level redistribution AND derived-label
  publication disabled.
- Synthetic in-memory row adapters (`adapt_contextbench_row`,
  `adapt_swe_explore_row`) separate `public_task` (aggregate-safe metadata:
  presence booleans, field counts, categorical bucket only) from
  `private_label` (row-level payload, never serialized). Neither is ever
  serialized into a public artifact with row-level values.
- Line range normalization (`normalize_line_range`) accepts
  list/tuple/dict/`"S-E"`/`"S:E"` forms; rejects `start > end`, `start < 1`,
  non-int, bool. Synthetic self-test / private in-memory validation only.
- Strict fail-closed forbidden-output scanner (`_scan_forbidden`) forbids
  sensitive key names anywhere as dict keys and forbids
  URL/hex-digest/secret-like/path-like/multiline/long-string values; allows
  schema-only field-name lists under explicit containers
  (`field_names_schema_only`, `private_field_categories_detected`);
  allowlists known-safe provenance value paths (`spec_hash`,
  `generated_by`, `dataset_id`, `schema_version`, `claim_level`). The
  artifact records only `forbidden_scan: {status: "pass"}` plus
  category/path counts — never leaked values.
- Bounded HF datasets-server schema smoke via stdlib `urllib` only (no new
  dependencies), explicit bounded timeout, `/splits` as source of truth
  for `/first-rows` attempts. For `/first-rows`, only features/schema and
  row count/truncation booleans are parsed; raw rows remain local only
  and are never returned or written. On network/HF failure, produces
  status `unavailable` or `partial` with sanitized reason
  category/status code — no raw response body.
- Deterministic `spec_hash` (SHA-256 of canonical spec JSON excluding
  timestamps/network/raw rows/local paths):
  `9de6609359aa8de4cfe7ca50b1388ebc51d9ee2f016bb3bc6c34e253da5ef153`.

### Findings

```text
python3 -m py_compile eval/c4_external_benchmark_adapters.py   => PASS
python3 eval/c4_external_benchmark_adapters.py --self-test     => PASS (9 groups)
python3 eval/c4_external_benchmark_adapters.py \
  --out artifacts/c4_external_benchmark_adapters/\
c4_external_benchmark_adapter_report.json                     => PASS (forbidden_scan: pass)
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

Self-test groups (9): ContextBench adapter separation, SWE-Explore adapter
separation, line range normalization, forbidden scan rejects injection,
no-claim flags exactly false, spec hash deterministic, aggregate-only report,
forbidden scan blocks leak at generation, schema smoke report shape.

### Caveats

- C4.1 is adapter/schema readiness only. It does NOT validate row-level
  semantics, labels, or downstream agent value. The schema smoke confirms
  only that public HF datasets-server schema endpoints are reachable and
  parse; it does NOT confirm benchmark quality, label correctness, or
  fitness for any downstream evaluation.
- ContextBench dataset license is unknown even though the code repo is
  Apache-2.0; row-level redistribution is disabled.
- SWE-Explore HF dataset license is `cc-by-nc-nd-4.0`; row-level
  redistribution AND derived-label publication are disabled.
- Synthetic self-test rows confer NO empirical support.
- All no-claim flags remain false: `promotion_ready=false`,
  `default_should_change=false`, `evidencecore_semantics_changed=false`,
  `runtime_clean_general_algorithm_claimed=false`,
  `downstream_agent_value_proven=false`, `ood_temporal_supported=false`,
  `quiver_systems_supported=false`. No promotion, no default change, no
  EvidenceCore semantics change, no runtime-clean general algorithm claim,
  no downstream agent value claim, no OOD temporal claim, and no QuIVer
  systems claim follows from C4.1.

## 2026-06-20 — C4.2 ContextBench Verified Subset Row-Mapping Smoke

### Objective

Add a bounded **real row-mapping smoke** for the ContextBench verified
subset (`contextbench_verified/train`) that reads real HF datasets-server
`/first-rows` preview rows, adapts each row in function scope via the
existing `adapt_contextbench_row` adapter, validates the
`public_task` / `private_label` separation in memory, and emits an
aggregate-only artifact. Real rows live ONLY in function scope / memory;
no raw rows, sample rows, row values, row-level hashes, paths, spans, line
ranges, snippets, problem statements, patches/tests, prompts/responses,
provider payloads, content_sha, or raw HF payloads are persisted. C4.2 is
adapter/row-mapping readiness only, NOT a benchmark performance/result.

### Implementation

- New CLI flags on `eval/c4_external_benchmark_adapters.py`:
  `--row-map-smoke` (mutually exclusive with `--self-test` and
  `--schema-smoke`), `--row-limit` (default 10, hard cap 20),
  `--config` (default `contextbench_verified`; only this config supported),
  `--split` (default `train`). `--out` defaults to the C4.2 artifact
  path when not set, so the C4.1 canonical report is never overwritten.
- `_extract_first_rows` parses the datasets-server `/first-rows` payload
  into (rows, field_names, truncated) in function scope. Raw rows are
  returned to the caller ONLY for immediate in-scope adaptation and
  discarding.
- `_build_row_map_summary` iterates bounded rows, calls
  `adapt_contextbench_row(row)` per row, asserts the public task has no
  private attrs, counts field presence (non-empty by field name),
  public-task presence booleans, private-field category presence, and
  fixed failure categories. No row-level values, hashes, paths, spans, or
  snippets are emitted.
- `_row_map_smoke_contextbench_verified` calls `_http_get_json()` for the
  real `/first-rows` endpoint, extracts rows, bounds to `row_limit`,
  adapts, discards raw rows + payload immediately, builds the aggregate
  summary, and runs a fail-closed forbidden scan. On network/HF failure,
  emits sanitized `unavailable` status with `endpoint_unavailable`
  failure category — no raw response body.
- Forbidden scanner extended with `SCHEMA_KEY_CONTAINER_KEYS` allowlist
  (`field_presence_counts`, `public_task_presence_counts`,
  `private_field_presence_counts`, `failure_category_counts`) so count
  containers may use schema-only field-name strings as count bucket keys.
  The scanner still forbids row-level values, paths, spans, hashes, URLs,
  and secrets anywhere.
- New no-network self-test `_self_test_row_map_smoke_aggregate_only`
  builds synthetic rows with sentinel private values
  (`SECRET_REPO_SENTINEL`, `SECRET_PATCH_SENTINEL`, etc.), runs the
  aggregator, and asserts NONE of the sentinels appear in the report JSON,
  forbidden scan passes, injected `"12-34"` line range is rejected. New
  `_self_test_row_map_smoke_no_rows_unavailable` verifies `unavailable`
  status with `no_rows_returned` failure category when zero rows returned.

### Findings

```text
python3 -m py_compile eval/c4_external_benchmark_adapters.py   => PASS
python3 eval/c4_external_benchmark_adapters.py --self-test     => PASS (12 groups)
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

All 13 schema field names were non-empty in all 10 rows; all 5 public-task
presence booleans were True in all 10 rows; all 12 private-field
categories were non-empty in all 10 rows. No row-level values, hashes,
paths, spans, snippets, problem statements, patches/tests,
prompts/responses, provider payloads, content_sha, or raw HF payloads
were persisted.

### Caveats

- C4.2 is adapter/row-mapping readiness only. It does NOT validate
  row-level semantics, labels, or downstream agent value. The row-map
  smoke confirms the adapter boundary holds (public task has no private
  attrs; private label has private values only in memory); it does NOT
  confirm benchmark quality, label correctness, or fitness for any
  downstream evaluation.
- ContextBench dataset license is unknown; row-level redistribution is
  disabled.
- All no-claim flags remain false: `promotion_ready=false`,
  `default_should_change=false`, `evidencecore_semantics_changed=false`,
  `runtime_clean_general_algorithm_claimed=false`,
  `downstream_agent_value_proven=false`, `ood_temporal_supported=false`,
  `quiver_systems_supported=false`. No promotion, no default change, no
  EvidenceCore semantics change, no runtime-clean general algorithm claim,
  no downstream agent value claim, no OOD temporal claim, and no QuIVer
  systems claim follows from C4.2.
