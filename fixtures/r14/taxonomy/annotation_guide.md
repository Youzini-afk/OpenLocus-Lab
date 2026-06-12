# R14 Annotation Guide

## How to Annotate Gold Spans

### Step 1: Identify the Target
For each task, determine what the correct answer should be:
- `exact_symbol`: The exact definition location of the symbol
- `implementation_search`: The primary implementation body
- `config_policy`: The configuration/policy definition code
- `test_selection`: The test function(s)
- `negative`: No gold spans (empty)
- `stress`: Multiple relevant spans
- `cross_repo`: Spans from different repos

### Step 2: Locate in Codebase
1. Use `openlocus search symbol <name>` to find candidate definitions
2. Use `openlocus read <path:start-end>` to verify the span
3. Record the relative path (from repo root) and 1-indexed inclusive line range

### Step 3: Record Gold Span
```json
{
  "path": "src/example/module.rs",
  "start_line": 42,
  "end_line": 55,
  "rationale": "Definition of ExampleStruct with all fields"
}
```

### Step 4: Identify Hard Negatives
For each task, think about what a retrieval method might incorrectly return:
1. **Similar names**: `ExampleMeta` is a hard negative for `ExampleCore`
2. **References/usages**: Code that uses the target but doesn't define it
3. **Re-exports**: `pub use` statements that reference the target
4. **Test code**: Tests that exercise the target functionality
5. **Related but different**: Adjacent functionality in the same module

Record as:
```json
{
  "path": "src/example/other.rs",
  "start_line": 10,
  "end_line": 25,
  "rationale": "ExampleMeta is a different struct that could be confused with ExampleCore"
}
```

### Step 5: Assign Label Quality
- `human_reviewed`: You have manually verified the span is correct
- `mined_high_confidence`: Automated extraction with structural verification
  (e.g., symbol definition found by Tree-sitter or exact regex match)
- `mined`: Automated extraction with heuristic verification
- `weak`: Coarse file-level match or approximate line range

## Critical Rules

1. **Never copy gold information into task files.** Tasks contain only the query
   and task metadata. Labels are private.
2. **Hard negatives must not be in the gold set.** A path/span cannot be both
   gold and a hard negative for the same task.
3. **Gold spans must exist in the repo lock.** The `repos.lock.jsonl` must
   reference a repo that contains the gold span's file.
4. **Line ranges must be valid.** `start_line >= 1`, `end_line >= start_line`,
   and the line range must not exceed the file's total line count.
5. **Stale labels must be flagged.** If the codebase changes after annotation,
   labels may become stale. The `label_quality` field should be downgraded.
