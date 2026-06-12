# R14 Scaled Evidence Benchmark

## Overview

R14 establishes a **scaled benchmark program** for evaluating OpenLocus retrieval
quality across repository groups and task types. The program is structured as
S/M/L/X tiers with increasing scale and label quality requirements. The current
S/M data uses logical repo groups from one OpenLocus workspace snapshot; later
tiers are intended to add independent external repositories.

**This is a benchmark *foundation*, not a quality conclusion.** The current R14-S
tier provides a locally-runnable baseline. M/L/X tiers define target structures
and scaling goals; their data may be partially populated with mined labels of
varying confidence.

## Tier Scale Targets

| Tier | Repos | Tasks | Labels | Hard Negatives | Label Quality | Run Time |
|------|-------|-------|--------|----------------|---------------|----------|
| R14-S | 4+ | 40+ | 40+ | 8+ | human_reviewed + mined_high_confidence | <5 min local |
| R14-M | 8+ | 120+ | 120+ | 24+ | mined_high_confidence + weak | <30 min local |
| R14-L | 16+ | 400+ | 400+ | 80+ | mostly mined / weak | <2 hr |
| R14-X | 32+ | 1000+ | 1000+ | 200+ | mostly weak / auto-mined | multi-run |

## Label Quality Definitions

- **human_reviewed**: Gold spans verified by human review. Highest confidence.
- **mined_high_confidence**: Gold spans extracted by automated analysis (symbol
  lookup, exact match) with high structural confidence. Not human-verified but
  structurally sound (correct file, plausible line range).
- **mined**: Gold spans from automated heuristics. May have imprecise line ranges.
- **weak**: Gold spans from coarse heuristics (keyword match, file-level only).
  Line ranges may be approximate or missing.

## Anti-Leakage Design

1. **Public tasks** (`tasks/*.jsonl`) contain `task_id`, `query`, `task_type`,
   `method_hint`, and `repo_id`. They do **NOT** contain gold paths, lines, or
   hard negatives.
2. **Private labels** (`labels/*.jsonl`) contain `task_id`, `gold_spans`,
   `hard_negatives`, and `label_quality`. Labels are separate from tasks and
   must not be accessible to the runner.
3. **Leakage check** (`eval/r14_leakage_check.py`) verifies no gold information
   leaks into public task files, indexed repo roots, or benchmark artifacts.
   Runtime canary retrieval is enforced by `eval/r14_benchmark.py` inside
   isolated roots.

## Task Types

| Type | Description | Example Query |
|------|-------------|---------------|
| `exact_symbol` | Find definition of a specific symbol | `EvidenceCore` |
| `implementation_search` | Find implementation of named functionality | `bm25_search` |
| `config_policy` | Find configuration/policy-related code | `Policy exclude patterns` |
| `test_selection` | Find tests for a specific module | `tests for evidence module` |
| `negative` | Query with no good match in repo | `quantum_entanglement_solver` |
| `stress` | Broad/vague query testing recall under ambiguity | `error handling` |
| `cross_repo` | Query that should match across repos | `main entry point` |

## Benchmark Policy

The benchmark runner physically copies declared sources into isolated temp roots
and writes `.openlocus/policy.toml` from the repo lock. The effective isolated
policy excludes (glob-style patterns):
- `fixtures/**` (prevents memorization of gold data)
- `eval/**` (prevents access to scoring logic)
- `docs/**` (prevents matching against documentation of the benchmark itself)
- `runs/**` (prevents matching against previous output)
- `.openlocus/**` (prevents matching against cached state)
- `target/**` (prevents Rust build artifacts)
- `__pycache__/**`, `*.tmp`, `*.log`, `.git/**`, `node_modules/**`, `dist/**`

Predictions referencing any forbidden prefix are a CRITICAL failure (fail-closed).

## Files

```
fixtures/r14/
  README.md                    This file
  taxonomy/
    task_types.md              Task type definitions and annotation guide
    annotation_guide.md        How to annotate gold spans and hard negatives
  dataset_manifest.json        Dataset metadata, tier info, generation info
  repos.lock.jsonl             Locked repo entries with content manifest SHA
  tasks/
    sanity.jsonl               R14-S sanity tasks (quick validation)
    medium.jsonl               R14-M tasks
    large.jsonl                R14-L tasks
    stress.jsonl               Stress/negative tasks
  labels/
    sanity.jsonl               R14-S labels (private, not for runner)
    medium.jsonl               R14-M labels
    large.jsonl               R14-L labels
    stress.jsonl               Stress labels
  expected_failures/
    known_issues.md            Documented cases where methods are expected to fail
```

## Current Data Status

- R14-S: **Populated** with 4 logical repo groups from one OpenLocus workspace snapshot, 48 tasks, 48 labels (8 human_reviewed, 37 mined_high_confidence, 3 mined). Populated=True.
- R14-M: **Partially populated** with the same 4 logical repo groups, 36 tasks, 36 labels. Full M requires 8+ independent repo groups/repositories. Partial=True.
- R14-L: **Placeholder** — structure defined, 10 weak-label tasks. Not populated (repos=0). Requires additional repos.
- R14-X: **Not populated** — structure defined only. Requires external repo sources.

**Do not混淆 target scale with current populated data.** Target scale is the aspiration; current populated reflects what actually exists.

## Important Caveats

1. **R14-S is a foundation validation, not a quality conclusion.** It validates
   that the benchmark pipeline works end-to-end with real tasks and correct scoring.
2. **Current S/M is not yet independent multi-repo coverage.** It uses 4 logical
   OpenLocus crate groups from one workspace snapshot. Independent external
   repository coverage is a follow-up expansion.
3. **Mined labels are not human-verified.** `mined_high_confidence` labels are
   structurally sound but may have imprecise line ranges.
4. **Hard negatives are first-class data.** They represent plausible but incorrect
   retrieval targets and are essential for measuring precision under ambiguity.
5. **Citation validity is a safety gate, not a quality metric.** A method that
   produces 100% citation-valid but completely irrelevant evidence is not "good."
6. **No dense/LLM/graph quality claims.** R14 measures lexical/symbol/RRF baselines.
   Dense, LLM, and graph methods are future feature tracks.
