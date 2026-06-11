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
- **Eval**: Updated `run_retrieval.py` to accept `--method regex|text|bm25|symbol|rrf`, `--channels` for RRF. Updated `score.py` with structural_validity + citation_validity (true file I/O validation), FileRecall@1/5/10, FilePrecision@5/10, MRR, LinePrecision@10, LineRecall@10, SpanF0.5@10, token_waste_ratio@10, wrong_span_rate@10 (gold-file-only), zero_overlap_evidence_rate@10 (all evidence). Added `fixtures/r2.jsonl` with 28 tasks, gold spans refreshed to current codebase.

### R2 eval results (after oracle review fixes)

| Metric | regex | bm25 | symbol | rrf |
|---|---|---|---|---|
| file_recall@1 | 0.21 | **0.46** | 0.39 | **0.46** |
| file_recall@5 | 0.50 | **0.86** | 0.39 | **0.86** |
| file_recall@10 | 0.57 | **0.93** | 0.39 | **0.93** |
| mrr | 0.33 | 0.64 | 0.39 | **0.64** |
| line_precision@10 | 0.07 | 0.06 | **0.39** | 0.08 |
| line_recall@10 | 0.02 | 0.06 | 0.01 | 0.05 |
| span_f0.5@10 | 0.04 | 0.06 | 0.06 | **0.07** |
| structural_validity | **1.0** | **1.0** | **1.0** | **1.0** |
| citation_validity | **1.0** | **1.0** | **1.0** | **1.0** |
| wrong_span_rate@10 | 0.79 | 0.77 | **0.0** | 0.78 |
| zero_overlap@10 | 0.90 | 0.92 | **0.0** | 0.92 |
| avg_latency_ms† | 12 | 131 | 168 | 274 |

† CLI end-to-end latency including index build (BM25/RRF) or file scan (symbol). Not a warm-index benchmark.

### Key findings

1. BM25 substantially improves file-level recall on the current self-referential fixture (0.46 vs 0.21 at k=1, 0.86 vs 0.50 at k=5). This is an early local-only bakeoff result, not a general benchmark claim.
2. Symbol search has the highest line precision (0.39) and zero wrong spans when it fires, but only activates for definition-style queries on known languages.
3. RRF fusion recovers BM25-level file recall (0.86 at k=5) while incorporating symbol precision, achieving the best SpanF0.5@10 (0.07) in this fixture.
4. All methods produce citation-valid evidence (1.0 structural + true citation validity).
5. Token waste ratio remains high (~0.92) — evidence spans are narrow but often miss gold lines. Query-token line scoring fixed chunk-center anchoring, but chunking/query expansion/gold-span calibration need further refinement.
6. BM25 stale check and no-overlap skip are effective: no stale or center-only hits appear in the output.
7. Symbol boundary delimiters prevent partial matches (verified: "User" does not match "UserProfile").

### Oracle review fixes applied

- **BM25 span selection**: Replaced chunk-center anchoring with line-level query token overlap scoring. Hits with no token overlap are skipped (precision-biased).
- **BM25 stale check**: Index-time content_sha compared to current file hash. Mismatch → skip. Strict line range guard added.
- **BM25 query fallback**: Removed `*` all-doc fallback; parse failures now degrade to sanitized query or empty results.
- **Symbol boundary**: Added `(?:[^a-zA-Z0-9_]|$)` delimiter after symbol name in all patterns. Prevents partial matches.
- **RRF overlap dedup**: Wider span's why/channels/score are now merged into the narrower survivor. Deterministic tie-break: score desc, path asc, start_line asc, end_line asc.
- **Eval citation validity**: Split into `structural_validity` (no I/O) and `citation_validity` (verifies path exists and range/hash match current file). Added `--repo-root`.
- **Eval metrics**: Added `zero_overlap_evidence_rate@10` (all evidence, not just gold-file). `wrong_span_rate@10` now only counts evidence on gold files. Added `--channels` to `run_retrieval.py`.
- **Fixtures**: Refreshed gold spans to current codebase actual line numbers.

### Caveats carried forward

- BM25 builds a fresh Tantivy index per query; not suitable for large repos without persistent indexing.
- Symbol search is heuristic-only; real TreeSitter or SCIP would improve recall.
- Line-level metrics are low because gold spans target specific code regions; the eval is more meaningful for file-level metrics at this stage.
- BM25 CLI end-to-end latency includes index build; a persistent index would reduce this significantly.
- The Rust `regex` crate does not support lookahead; symbol boundary uses consuming match `(?:[^a-zA-Z0-9_]|$)` instead.
