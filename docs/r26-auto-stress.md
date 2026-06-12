# R26 Auto-Stress-1000 Retrieval Failure-Surface Benchmark

## Overview

R26 is a **weak/mined/deterministic stress dataset** for retrieval failure discovery. It is **NOT promotion evidence** and **NOT a retrieval strategy promotion mechanism**. It is designed to maximize failure discovery across 10 stress categories using the same external repo set as R20 and deriving some queries from existing R20 tasks/labels where useful.

**R26 labels are stress failure-surface labels, not EvidenceCore.**

## Key Constraints

- **Public tasks** contain ONLY: `test_id`, `repo_id`, `query`, `public_version`, `source`. No category/risk/gold/expected/oracle/risk_tags/intent_guess/why/strategy fields leak.
- **Private labels** carry ALL judgement fields: `test_id`, `repo_id`, `query`, `source_category`, `risk_public`, `intent_guess`, `risk_tags`, `oracle_type`, `expected_behavior`, `gold_spans`, `hard_distractors`, `must_not_primary`, `why_this_is_hard`, `which_strategy_it_targets`.
- **expected_behavior** enum: `primary_evidence` | `supporting_only` | `weak_candidates` | `abstain` | `no_primary`
- **oracle_type** enum: `deterministic` | `mined` | `differential` | `metamorphic` | `stress`
- **No canary tokens** anywhere in tasks or labels.
- **Deterministic seed**: 42.
- **not_promotion_evidence** = true, **core_changes** = false, **remote_calls** = 0, **dense_or_llm_claims** = false

## Scale

| Metric | Count |
|--------|-------|
| Repos | 9 |
| Tasks | 1100 |
| Labels | 1100 |
| Categories | 10 |

## Category Composition

| Category | Count | Target | Description |
|----------|-------|--------|-------------|
| negative_nonexistent | 150 | 150 | Fake symbols/features that don't exist; tests hallucination resistance |
| ambiguous_vague | 150 | 150 | Ambiguous or vague queries; tests disambiguation and noise guards |
| hard_distractor | 200 | 200 | Similar-name symbols that distract; tests precision under confusion |
| semantic_trap | 150 | 150 | ML/AI terminology unrelated to repo code; tests dense/semantic false positives |
| same_name_symbol | 100 | 100 | Same symbol name in multiple locations; tests context ranking |
| frontend_backend_confusion | 75 | 75 | Frontend/backend name overlap; tests layer disambiguation |
| test_source_confusion | 75 | 75 | Test vs source name overlap; tests path filtering |
| generated_vendor_trap | 50 | 50 | Vendor/generated patterns; tests non-project code exclusion |
| stale_index_like | 50 | 50 | Deleted/renamed/modified file references; tests stale index detection |
| dense_quiver_specific_trap | 100 | 100 | QuIVer/TDB/dense infrastructure terminology; tests naming confusion |

## Honest Caveats

### This is weak/mined/deterministic stress, NOT promotion evidence

1. **R26 is explicitly designed to maximize failure discovery**, not to demonstrate quality. High failure rates on R26 are expected and do not indicate a problem with retrieval strategies.
2. **Labels are mined/weak/deterministic, not human-verified.** `human_reviewed` is forbidden. Many labels are generated from templates with no manual inspection.
3. **Negative/abstain cases dominate** (590/1100 = 53.6% abstain + 70/1100 = 6.4% no_primary). This is intentional: stress testing focuses on failure modes, not success modes.
4. **Derivation from R20 is shallow.** R26 reuses R20 repo sources and some R20 label queries as seeds, but does NOT inherit R20 gold spans or oracle judgments. R26 labels are freshly generated with stress-specific logic.
5. **semantic_trap and dense_quiver_specific_trap categories contain queries about ML/AI/vector infrastructure that these repos do NOT implement.** These test false-positive resistance, not retrieval quality.
6. **stale_index_like cases are metamorphic probes.** They reference code that may not exist in the current snapshot. They test stale index detection, not current-code retrieval.
7. **No runner/scorer matrix exists for R26.** R26 is a static dataset with a static validator. No retrieval strategies have been run against it yet.
8. **R26 labels are stress failure-surface labels, not EvidenceCore.**

## Files

```
fixtures/r26_auto_stress/
  dataset_manifest.json        Dataset metadata, tier info, generation info, SHA256 checksums
  repos.lock.jsonl              Locked repo entries with content manifest SHA
  tasks/
    auto_stress.jsonl           R26 public tasks (query only; no category/risk/gold/expected/oracle fields)
  labels/
    auto_stress.jsonl           R26 private labels (stress failure-surface oracle/probe)
  safety_checks.json            Safety check results (populated by static validator)
  summary.json                  Summary counts and category distribution
```

## Validation

Run the fail-closed static validator:

```bash
python3 eval/r26_validate_auto_stress.py --workspace . --fixtures fixtures/r26_auto_stress
```

The validator checks 19 conditions including:
- Schema separation (no private category/risk/judgement fields in public tasks)
- Label-public task consistency
- Enum validity
- Category distribution (all 10 required, exact deterministic target counts)
- Total count >= 1000
- Per-repo count >= 50
- Repo content manifest SHA locks (source drift detection)
- No canary tokens
- Dataset manifest flags
- Deterministic SHA256 checksums
- Gold span / must_not_primary / hard_distractor overlap constraints
- Span path/range validity against locked source files

## Generation

```bash
python3 eval/r26_generate_auto_stress.py --workspace . --out fixtures/r26_auto_stress
```

Uses deterministic seed 42. Uses the same external repo set as R20 and derives some queries from existing R20 tasks/labels where useful.
