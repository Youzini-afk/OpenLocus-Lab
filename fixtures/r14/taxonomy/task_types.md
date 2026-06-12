# R14 Task Type Taxonomy

## Task Types

### exact_symbol
Find the definition of a specific named symbol (struct, enum, fn, trait, const, type alias).

- Query format: symbol name only (e.g., `EvidenceCore`, `scan_repo`, `Channel`)
- Expected: single narrow span at the symbol's definition site
- Gold: precise line range covering the definition signature/header
- Hard negative: other symbols with similar names, usages/references of the symbol

### implementation_search
Find the implementation of named functionality or module.

- Query format: function/method name or descriptive phrase (e.g., `bm25_search`, `build_index`, `materialize evidence`)
- Expected: the primary implementation span
- Gold: the function/method body or key implementation section
- Hard negative: test code that calls the function, re-exports, type signatures without bodies

### config_policy
Find configuration, policy, or settings-related code.

- Query format: descriptive phrase (e.g., `Policy exclude patterns`, `default ignores`, `content hashing`)
- Expected: the configuration/policy definition or default-setting code
- Gold: the struct definition, default impl, or configuration loading code
- Hard negative: code that uses the config/policy, unrelated config structures

### test_selection
Find test code for a specific module or functionality.

- Query format: test-related query (e.g., `tests for evidence module`, `bm25 test`)
- Expected: test function(s) targeting the specified module
- Gold: test function definition spans
- Hard negative: the module's implementation code itself, unrelated test code

### negative
Query with no good match in the indexed repos.

- Query format: topic not present in any indexed repo
- Expected: zero or low-quality results; methods should NOT produce confident hits
- Gold: empty (no gold spans)
- Purpose: measures false positive rate; runner should not be rewarded for returning results

### stress
Broad or ambiguous query testing recall and precision under uncertainty.

- Query format: vague/broad query (e.g., `error handling`, `search implementation`, `data storage`)
- Expected: multiple relevant spans across files; methods may legitimately differ on what's "best"
- Gold: multiple spans covering the broad topic; precision is hard to define
- Hard negative: tangentially related but not directly answering code

### cross_repo
Query that should match across multiple repositories.

- Query format: common programming concept (e.g., `main entry point`, `configuration loading`)
- Expected: results from multiple repos
- Gold: spans from different repos
- Purpose: tests retrieval across logical repo groups; independent multi-repo coverage is a future expansion

## Annotation Rules

1. **Gold spans must be verifiable**: The span must exist in the current codebase
   at the specified path and line range. If the codebase changes, labels become stale.
2. **Gold spans should be minimal**: Cover the definition/implementation, not
   the entire file or surrounding context. For functions, include the signature
   and key body lines. For structs, include the struct definition and field list.
3. **Hard negatives must be plausible but wrong**: A hard negative is a result
   that a reasonable retrieval method might return but is incorrect for this task.
   Examples: a usage of a symbol when the definition is sought; a test that
   exercises functionality when the implementation is sought; a similarly-named
   but different symbol.
4. **Line ranges are 1-indexed and inclusive**: `[start_line, end_line]` where
   both are inclusive and 1-indexed.
5. **Multiple gold spans per task are allowed**: When the answer spans multiple
   files or multiple locations in one file.
