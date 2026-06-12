# R15 Expected Failures / Known Issues

## Methods Expected to Fail on Certain Task Types

### regex search
- Broad/vague stress queries (e.g., "error handling", "configuration setup")
  may return too many results or miss the relevant ones.
- Provider-ish queries may match unrelated code.
- Query noise words will return excessive results with poor precision.

### bm25 search
- Exact symbol queries may rank the correct file lower than files with
  frequent mentions of the symbol name.
- Multi-word queries may be split and match irrelevant combinations.

### symbol search
- Only works for definition-style queries in supported languages.
- Python `async def` may not be matched by some symbol patterns.
- Go methods (func with receiver) may not be found by simple name search.
- JS arrow functions and const declarations may be missed.

## Multi-Language Caveats

- OpenLocus CLI may only scan/index specific file types. If the CLI does not
  support `.mjs` or `.go` scanning, tasks targeting those file types will
  return empty results. This is a known limitation, not a bug.
- Python indentation-based end_line estimation is approximate.
- Go method receivers are included in the full function signature but the
  extracted name is just the method name.

## Repo-Specific Issues

### fast-context-mcp
- Only 5 source files (.mjs). Very limited symbol diversity.

### gemini-web2api
- Only 9 Python files. Limited task coverage.

### smartsearch
- Originally 2102 Python files but after excluding `node_modules`, `__pycache__`,
  `dist`, `build`, etc., only ~69 source files are indexed. The large majority
  are in excluded directories.

## Stress Task Limitations

- Stress tasks have weak labels with no gold spans. They measure recall
  behavior under ambiguity, not precision.
- Negative tasks are verified by construction (the query intentionally
  references non-existent functionality).

## Citation Validation

- The Rust citation validator expects evidence paths relative to the
  isolated root, not the original absolute path. The benchmark runner runs
  validation before isolated-root cleanup and records `citation_hash_checked`.
- Scoring compares label-relative paths against exact prediction paths or a
  single `repo_id/` prefix. It does not use arbitrary suffix matching.
