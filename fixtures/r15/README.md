# R15 External Multi-Repo Evidence Benchmark

## Overview

R15 extends the R14 benchmark foundation with real local multi-repo benchmark
data from independent external git repositories under `/workspace`. It covers
Rust, Python, Go, TypeScript, and JavaScript source code across 9 independent
repos, generating Medium/Large/Stress tier data with multi-language symbol
extraction.

**This is a mined benchmark expansion, not a final quality conclusion.** The
current R15 data uses automated symbol/definition extraction across external
local repos. Labels are mined with varying confidence levels. External local
repos are workspace snapshots and are not modified.

## External Repositories

| repo_id | Path | Languages | Description |
|---------|------|-----------|-------------|
| fast-context-mcp | /workspace/fast-context-mcp/fast-context-mcp | JS (.mjs) | MCP server for fast-context |
| grok2api | /workspace/grok2api/grok2api | Python, JS | Grok2API web service |
| infinite-canvas | /workspace/infinite-canvas/infinite-canvas | Go, TS, TSX | Go handler/service + TS/TSX web |
| gemini-web2api | /workspace/gemini-web2api/gemini-web2api | Python | Gemini web2api service |
| windsurf2api | /workspace/windsurf2api/WindsurfAPI | JS | WindsurfAPI service |
| kiro2 | /workspace/kiro2/kiro.rs | Rust, TS, TSX | Rust kiro2 + TS/TSX front-end |
| triviumdb | /workspace/TDB/TriviumDB | Rust | TriviumDB vector database |
| smartsearch | /workspace/smartsearch/smartsearch | Python, JS | Smartsearch application |
| codex2api | /workspace/codex2api/codex2api | Go, TS, TSX | Go codex2api + TS/TSX components |

## Tier Scale

| Tier | Repos | Tasks | Labels | Hard Negatives | Label Quality | Run Time |
|------|-------|-------|--------|----------------|---------------|----------|
| R15-M | 9 | 166 | 166 | 270 | mined_high_confidence + mined + human_reviewed + weak | <30 min |
| R15-L | 9 | 294 | 294 | 270 | mined + weak | <1 hr |
| R15-stress | 9 | 19 | 19 | 0 | human_reviewed + weak | <10 min |

## Supported Source Extensions

`.rs`, `.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.go`, `.mjs`

## Ignored Directories

`node_modules`, `target`, `.git`, `dist`, `build`, `.venv`, `__pycache__`,
`.next`, `.nuxt`, `runs`, `fixtures`, `eval`, `docs`, `.openlocus`,
`coverage`, `.cache`, `.mypy_cache`, `.pytest_cache`, `.tox`, `venv`, `env`

## Label Quality Definitions

Same as R14:
- **human_reviewed**: Gold spans verified by human review. Highest confidence.
- **mined_high_confidence**: Gold spans from automated symbol extraction with
  high structural confidence. Not human-verified but structurally sound.
- **mined**: Gold spans from automated heuristics. May have imprecise line ranges.
- **weak**: Gold spans from coarse heuristics (keyword match, file-level only).

## Anti-Leakage Design

Same fail-closed design as R14, extended for external repos:

1. **Public tasks** contain `task_id`, `query`, `task_type`, `method_hint`, `repo_id`.
   No gold paths/lines/hard_negatives/label_quality.
2. **Private labels** are separate files with gold_spans, hard_negatives,
   label_quality, and source_repo_kind.
3. **Isolated roots**: Runner allowlist-copies only manifest/source files into
   temp roots under repo_id-specific folders. It never copies labels, whole repo
   artifacts, or symlinks.
4. **Runtime artifact cleanup**: OpenLocus CLI traces under `.openlocus/traces`
   are removed after each query/citation validation and audited as hard-gate
   artifacts before/after every method.
5. **local_absolute_path source**: Repo lock uses absolute paths for source,
   but isolated root preserves relative paths for retrieval verification.
6. **Unknown repo_id fail-closed**: No fallback to full workspace.
7. **Citation validator**: Rust hash-checks evidence in isolated root before cleanup.
8. **Canary tokens**: Runtime canary retrieval must return zero hits.
9. **Scoring path match**: Exact path or single `repo_id/` prefix only; no
   arbitrary suffix matching.

## Task Types

| Type | Description | Example Query |
|------|-------------|---------------|
| `exact_symbol` | Find definition of a specific symbol | `GrokClient` |
| `implementation_search` | Find implementation of named functionality | `handle_request` |
| `config_import` | Find configuration/import-related code | `configuration settings` |
| `negative` | Query with no good match in repo | `quantum_entanglement_solver` |
| `stress` | Broad/vague query testing recall | `error handling` |
| `mutation_negative` | Fake/mutated identifier that doesn't exist | `FIXME_bogus_method_xyz123` |
| `provider_ish` | Query referencing provider/embedding concepts | `embedding provider mock` |
| `query_noise` | Very common word likely to match everything | `function` |

## Files

```
fixtures/r15/
  README.md                    This file
  dataset_manifest.json        Dataset metadata, tier info, generation info
  repos.lock.jsonl             Locked repo entries with content manifest SHA
  tasks/
    medium.jsonl               R15-M tasks
    large.jsonl                R15-L tasks
    stress.jsonl               R15-stress tasks
  labels/
    medium.jsonl               R15-M labels (private, not for runner)
    large.jsonl                R15-L labels
    stress.jsonl               R15-stress labels
  taxonomy/
    annotation_guide.md        How to annotate (references R14 taxonomy)
  expected_failures/
    known_issues.md            Documented cases where methods are expected to fail
  safety_checks.json           Safety check results (populated by leakage check)
```

## Important Caveats

1. **R15 is a mined benchmark expansion, not a quality conclusion.** Labels are
   mined with varying confidence; not human-verified.
2. **External local repos are workspace snapshots.** They are read-only copies;
   no modifications are made to external repos.
3. **Multi-language support is best-effort.** OpenLocus CLI may only index
   specific file types. Task generation covers all declared extensions, but
   actual retrieval depends on CLI scan/search capabilities.
4. **Symbol extraction is heuristic.** Regex-based extraction may miss or
   misidentify symbols, especially in unfamiliar patterns.
5. **Hard negatives are mined, not curated.** They are structurally plausible
   but may not always be the best distractors.
6. **Citation validity is a safety gate, not a quality metric.**
   R15 benchmark reports `citation_hash_checked=true` only when the Rust
   validator checked actual evidence before isolated-root cleanup.
7. **No dense/LLM/graph quality claims.** R15 measures lexical/symbol/bm25 baselines.
