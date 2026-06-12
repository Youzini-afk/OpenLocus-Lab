# R20 Auto-Wide Retrieval Failure-Surface Benchmark

## Overview

R20 is a **generated/mined/weak failure-surface dataset** for retrieval failure
discovery. It is **NOT promotion evidence**. No runner/scorer matrix exists yet;
R21 will use this dataset.

**R20 labels are failure-surface oracle/probe labels, not EvidenceCore.**

## Key Constraints

- **Public tasks** contain ONLY: `task_id`, `repo_id`, `query`, `public_version`,
  `source_tier`. No gold/expected/oracle/risk/judgement fields leak.
- **Private labels** carry all judgement fields: `query_category`, `intent_guess`,
  `risk_tags`, `oracle_type`, `expected_behavior`, `label_quality`, `gold_spans`,
  `hard_distractors`, `must_not_primary`, `why_this_is_hard`,
  `which_strategy_it_targets`, `caveat`.
- **expected_behavior** enum: `primary_evidence` | `supporting_only` |
  `weak_candidates` | `abstain` | `no_primary`
- **oracle_type** enum: `deterministic` | `mined` | `differential` |
  `metamorphic` | `stress`
- **label_quality**: `mined_high_confidence` | `mined` | `weak` (NO `human_reviewed`)
- **not_promotion_evidence** = true, **core_changes** = false,
  **remote_calls** = 0, **dense_or_llm_claims** = false

## Scale

| Metric | Count |
|--------|-------|
| Repos | 9 |
| Tasks | 741 |
| Labels | 741 |
| Categories | 25 |

## Category Coverage

| Category | Tasks |
|----------|-------|
| positive_exact_symbol | 180 |
| positive_regex_anchor | 90 |
| positive_natural_language | 9 |
| positive_issue_style | 9 |
| negative_nonexistent_symbol | 45 |
| negative_nonexistent_feature | 45 |
| ambiguous_query | 45 |
| vague_query | 45 |
| hard_distractor | 39 |
| same_name_symbol | 39 |
| frontend_backend_confusion | 5 |
| test_source_confusion | 5 |
| docs_source_confusion | 9 |
| generated_vendor_trap | 9 |
| config_key_trap | 45 |
| route_handler_trap | 31 |
| stacktrace_style | 9 |
| dirty_overlay | 9 |
| deleted_file | 9 |
| renamed_file | 9 |
| branch_switch_like | 9 |
| stale_index_candidate | 9 |
| graph_neighbor_trap | 9 |
| dense_semantic_trap | 9 |
| proper_name_api_config_regression | 19 |

## Repo Coverage

| Repo | Tasks |
|------|-------|
| codex2api | 84 |
| fast-context-mcp | 81 |
| gemini-web2api | 72 |
| grok2api | 85 |
| infinite-canvas | 83 |
| kiro2 | 83 |
| smartsearch | 85 |
| triviumdb | 85 |
| windsurf2api | 83 |

## Language Coverage

| Language | Tasks |
|----------|-------|
| go | 132 |
| javascript | 167 |
| python | 239 |
| rust | 141 |
| typescript | 62 |

## Files

```
fixtures/r20_auto_wide/
  README.md                    This file
  dataset_manifest.json        Dataset metadata, tier info, generation info
  repos.lock.jsonl             Locked repo entries with content manifest SHA
  tasks/
    auto_wide.jsonl            R20 public tasks (no gold/expected/oracle fields)
  labels/
    auto_wide.jsonl            R20 private labels (failure-surface oracle/probe)
  safety_checks.json           Safety check results (populated by static validator)
  coverage_report.json         Coverage by category/repo/language/oracle/expected/risk
```

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
