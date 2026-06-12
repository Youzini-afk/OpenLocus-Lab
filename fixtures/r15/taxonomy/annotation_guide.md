# R15 Annotation Guide

This guide references the R14 taxonomy and extends it for multi-language,
multi-repo benchmark annotation.

## Task Types

See `fixtures/r14/taxonomy/annotation_guide.md` for base definitions.

R15 adds the following task types:

### mutation_negative
Queries containing intentionally fake/mutated identifiers that do not exist
in the target repo. Used to test false positive resistance. Gold spans are
empty. Label quality: `human_reviewed`.

### provider_ish
Queries referencing provider/embedding/model concepts that may or may not
exist in the target repo. Used to test concept-level retrieval. Label
quality: `weak`.

### query_noise
Very common words (e.g., "the", "function", "return") that will match many
files. Used to test precision under high-recall conditions. Label quality:
`weak`.

## Multi-Language Symbol Extraction

R15 extracts symbols from multiple languages:

| Language | Patterns | Example |
|----------|----------|---------|
| Rust | `pub struct`, `pub enum`, `pub trait`, `pub fn`, `impl` | `Database`, `search` |
| Python | `class`, `def`, `async def` | `GrokClient`, `handle_request` |
| Go | `func`, `type struct`, `type interface` | `Handler`, `Serve` |
| JS/TS | `function`, `class`, `interface`, `type`, `const = () =>` | `createServer`, `Config` |

## Label Quality for R15

- **mined_high_confidence**: Symbol definitions extracted by regex from source
  files. The file and approximate line range are correct, but exact end_line
  may be imprecise.
- **mined**: Config/import/stress tasks with no precise gold spans.
- **human_reviewed**: Negative and mutation_negative tasks (empty gold spans,
  verified by construction).
- **weak**: Stress, query_noise, and provider_ish tasks with no gold spans.

## source_repo_kind Field

R15 labels include a `source_repo_kind` field:
- `external_local`: The repo is an independent external local repository
  (not part of the OpenLocus workspace).

## Hard Negatives

Hard negatives are mined from the same repo:
1. Same file, different symbol
2. Similar name in different file
3. Same kind in same language

Span-level hard negatives include `start_line` and `end_line`.
