# R20 Auto-Wide Retrieval Failure-Surface Benchmark

> 中文译本待补充。The full Chinese translation is pending.
> 这是同名文件的占位符：保留英文原文，方便未来翻译对照。

## English source / 英文原文

# R20 Auto-Wide Retrieval Failure-Surface Benchmark

## Overview

R20 is a **generated/mined/weak failure-surface dataset** for retrieval failure
discovery. It is **NOT promotion evidence**. No runner/scorer matrix exists yet;
R21 will use this dataset.

**R20 labels are failure-surface oracle/probe labels, not EvidenceCore.**

## Design Principles

1. **Candidate is not fact.** R20 labels are failure-surface oracle/probe labels
   that describe what a retrieval system *should* or *should not* return. They
   are not EvidenceCore and cannot be used as promotion evidence.

2. **Public/private separation.** Public tasks contain only `task_id`, `repo_id`,
   `query`, `public_version`, and `source_tier`. All judgement fields (gold_spans,
   expected_behavior, oracle_type, risk_tags, etc.) are in private labels.

3. **Failure discovery, not quality scoring.** R20 is designed to surface
   retrieval failure modes — negative queries, ambiguous queries, traps, and
   stress cases. It is not a general retrieval quality benchmark.

4. **Static validation only.** No runner or scorer is included. The static
   validator (`eval/r20_static_validate.py`) enforces schema, enum, coverage,
   and anti-leakage constraints.

5. **No Rust core changes.** R20 is dataset-only. No modifications to the
   OpenLocus Rust codebase were made.

## Schema

### Public Task Fields (minimal, no leakage)

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | Unique identifier (e.g., `r20aw-0001`) |
| `repo_id` | string | Repository identifier from repos.lock |
| `query` | string | Search query text |
| `public_version` | string | Schema version (always `"0"`) |
| `source_tier` | string | Source tier (always `"r20_auto_wide"`) |

### Private Label Fields

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | Matches public task |
| `repo_id` | string | Repository identifier |
| `query_category` | enum | One of 25 required categories |
| `intent_guess` | string | Guessed retrieval intent |
| `risk_tags` | string[] | Risk categories for this task |
| `oracle_type` | enum | `deterministic`, `mined`, `differential`, `metamorphic`, `stress` |
| `expected_behavior` | enum | `primary_evidence`, `supporting_only`, `weak_candidates`, `abstain`, `no_primary` |
| `label_quality` | enum | `mined_high_confidence`, `mined`, `weak` (NO `human_reviewed`) |
| `gold_spans` | object[] | Expected result spans (may be empty for negative/ambiguous) |
| `hard_distractors` | object[] | Plausible but incorrect spans |
| `must_not_primary` | object[] | Spans that must NOT be returned as primary evidence |
| `why_this_is_hard` | string | Explanation of failure mode |
| `which_strategy_it_targets` | string | Retrieval strategy this task targets |
| `caveat` | string | Additional caveats |

## Required Categories

All 25 categories must have at least 5 tasks:

| Category | Description | expected_behavior | oracle_type |
|----------|-------------|-------------------|-------------|
| `positive_exact_symbol` | Exact symbol name queries | `primary_evidence` | `deterministic` |
| `positive_regex_anchor` | Partial/regex-style queries | `primary_evidence` | `deterministic` |
| `positive_natural_language` | Natural language queries | `weak_candidates` | `mined` |
| `positive_issue_style` | Issue-style queries | `weak_candidates` | `mined` |
| `negative_nonexistent_symbol` | Fake symbol names | `abstain` | `deterministic` |
| `negative_nonexistent_feature` | Fake feature descriptions | `no_primary` | `deterministic` |
| `ambiguous_query` | Ambiguous single-word queries | `weak_candidates` | `mined` |
| `vague_query` | Vague/noise queries | `abstain` | `stress` |
| `hard_distractor` | Same-name disambiguation | `primary_evidence` | `deterministic`/`mined` |
| `same_name_symbol` | Same name in multiple locations | `primary_evidence` | `deterministic` |
| `frontend_backend_confusion` | Frontend/backend name overlap | `primary_evidence` | `mined` |
| `test_source_confusion` | Test vs source disambiguation | `primary_evidence` | `mined` |
| `docs_source_confusion` | Docs vs source disambiguation | `primary_evidence`/`weak_candidates` | `mined`/`weak` |
| `generated_vendor_trap` | Vendor/generated code traps | `abstain` | `mined`/`stress` |
| `config_key_trap` | Config key vs source identifier | `supporting_only` | `mined`/`stress` |
| `route_handler_trap` | Route string vs code matching | `supporting_only`/`abstain` | `mined`/`stress` |
| `stacktrace_style` | Stacktrace-format queries | `weak_candidates` | `mined` |
| `dirty_overlay` | Modified-state queries | `weak_candidates` | `metamorphic` |
| `deleted_file` | Deleted file references | `abstain` | `metamorphic` |
| `renamed_file` | Renamed file references | `abstain` | `metamorphic` |
| `branch_switch_like` | Branch-only code references | `abstain` | `metamorphic` |
| `stale_index_candidate` | Stale index detection | `primary_evidence` | `differential` |
| `graph_neighbor_trap` | Graph neighbor vs definition | `primary_evidence` | `mined` |
| `dense_semantic_trap` | Semantic false positive traps | `abstain` | `stress` |
| `proper_name_api_config_regression` | Proper name/API/config traps | `abstain` | `stress` |

## Scale Requirements

- Total tasks: >= 300
- Repos: >= 9
- Per repo: >= 15 tasks
- Per category: >= 5 tasks
- Every R15 language covered (Rust, Python, Go, JavaScript, TypeScript)

## Static Validator

`eval/r20_static_validate.py` is **fail-closed**: any violation is an ERROR that
causes exit code 1, not a warning. Source paths must be accessible; manifest SHA
must be verifiable; public task fields are strictly limited; label schema is
hard-validated.

Enforced rules:

1. **No fields outside `PUBLIC_TASK_FIELDS` in public tasks** (ERROR, not warning)
2. Task/label ID bijection, no duplicates, no unknown repo_ids
3. Enum validity (expected_behavior, oracle_type, label_quality)
4. **Label required-field schema hard validation**: all 14 required fields must
   be present with correct types (str/list); non-caveat string fields must be
   non-empty
5. `primary_evidence` must have gold_spans; `abstain`/`no_primary` must not
6. `must_not_primary` must not overlap `gold_spans`
7. `hard_distractors` must not overlap `gold_spans`
8. **Path/range in gold_spans, hard_distractors, AND must_not_primary** must
   exist in locked source and be in bounds
9. Repo lock content_manifest_sha must match recomputed SHA
   (**source path inaccessible is ERROR**, not warning)
10. `label_quality` must not be `human_reviewed`
11. All 25 categories present with >= 5 tasks each
12. >= 9 repos, >= 300 total tasks, **every repo in repo_lock** >= 15 tasks
    (not just repos with tasks)
13. `dataset_manifest` flags: `not_promotion_evidence=true`, `core_changes=false`,
    `remote_calls=0`, `dense_or_llm_claims=false`

## Important Caveats

1. **R20 is a failure-surface dataset, NOT promotion evidence.**
2. **No runner/scorer matrix exists yet.** R21 will use this data.
3. **Labels are mined/weak, not human-verified.** `human_reviewed` is forbidden.
4. **Metamorphic/stress categories** (dirty_overlay, deleted_file, renamed_file,
   branch_switch_like) encode expected behavior for R21/R26 but do NOT mutate
   source in R20.
5. **generated_vendor_trap** may be synthetic if repos lack vendor/generated files.
6. **dense_semantic_trap / proper_name_api_config_regression** target semantic
   false positives around provider/api/config names.
7. **R20 labels are failure-surface oracle/probe labels, not EvidenceCore.**

