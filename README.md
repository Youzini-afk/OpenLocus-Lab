# OpenLocus

OpenLocus is a **local-first, evidence-gated code-fact retrieval kernel** for
coding agents. It is local-first, but not local-only: exact search, symbol,
BM25, graph, read, and citation validation stay local; model/provider layers may
be used only behind explicit policy and CI opt-in gates.

The project is currently a research prototype, not a production default engine.
Its core invariant is stable:

```text
EvidenceCore = path + line range + content_sha + score + why + channels
```

Every intelligent layer — BM25, AST chunks, dense candidates, graph expansion,
LLM-derived views, context packs, provider output, QuIVer/TDB experiments, and
policy routing — must bottom out in **current-source EvidenceCore** or explicitly
abstain / request more context. Candidate is not fact.

## Current research status

Status date: **2026-06-19**.

OpenLocus is now in the **Candidate-to-Evidence Conversion** phase. The current
question is no longer “which retrieval channel is globally strongest?”; it is:

> How do we convert high-reach, high-false-cost candidate pools into low-false-
> cost, citation-valid Evidence without weakening `EvidenceCore`?

The latest research sprint is **B10-B19: Prospective Model-Robust Evidence
Conversion**, culminating in the theoretical synthesis:

```text
Model-Robust Selective Evidence Conversion
```

High-level status after B10-B19:

```text
promotion_ready=false
default_should_change=false
evidencecore_semantics_changed=false
runtime_clean_policy_supported=false
downstream_agent_value_proven=false
ood_temporal_supported=false
quiver_systems_supported=false
```

See the current report index:

- [`docs/current-research-conclusions.md`](docs/current-research-conclusions.md)
- [`docs/en/current-research-conclusions.md`](docs/en/current-research-conclusions.md)
- [`docs/zh/current-research-conclusions.md`](docs/zh/current-research-conclusions.md)

## B10-B19 snapshot

### B10 / B10B: balanced policy is promising, but not runtime-clean yet

B10 froze the algorithm spec `balanced_policy_v1_benchmark_routed`. It is a
**benchmark-routed research spec**, not a runtime-clean default policy:

```text
runtime_clean=false
runtime_feature_only_mode_supported=false
```

B10B introduced the runtime-shadow replay scaffold for the ambiguous branch:

```text
runtime_shadow_ambiguous =
  query_noise OR (candidate_support_exists AND anchor_disagreement_proxy)

anchor_disagreement_proxy = local_anchor AND NOT rrf_backed_by_anchor
```

B10B is mechanics-validated and wired into CI, but empirical support is still
pending. The hard denominator gate is:

```text
label_driven_ambiguous_min_denominator = 10
```

Across the B11 matrix, the maximum observed label-driven denominator was `3`, so
B10B remains `empirical_replay_support_pending`.

### B11: official integrated prospective matrix

B11 ran the first integrated prospective matrix over:

```text
32/32 final cells
384 records
8 public repo slices
4 model families
```

Aggregate verdict:

```text
partial_with_failure
success 8 / partial 23 / failure 1
```

Balanced v1 vs P25 weighted deltas over 384 records:

```text
Δgold_span   = -0.002604
ΔSpanF0.5    = -0.001899
Δfalse_span  = -0.054688
ΔPFP         = -0.020833
Δmodel_calls = -0.354167
```

Interpretation: balanced v1 preserves near-parity gold / SpanF0.5 while reducing
false spans, primary false positives, and model calls on average. However, one
Kimi `py_fastapi` slice failed the frozen SpanF0.5 threshold, so the result is a
strengthened algorithm-candidate signal, **not** promotion and not a default
change.

### B12-B18: why most later phases are no-go screens today

The later phases intentionally do not overclaim from public aggregates:

- **B12** mechanism decomposition cannot be identified from the public B11
  aggregate; it needs per-record strategy/action outcomes.
- **B13** distributionally robust policy search cannot run from aggregate means;
  it needs per-record grouped action outcomes.
- **B14** uncertainty calibration needs per-record uncertainty/outcome pairs.
- **B15** context-pack policy needs per-record pack-atom flags and outcomes.
- **B16** downstream coding-agent value needs a fixed agent harness with patch,
  test, solve-rate, wrong-file-edit, token, latency, and cost outcomes.
- **B17** QuIVer systems work is systems-only; current artifacts report QuIVer
  graph/vector backend missing.
- **B18** OOD/temporal evaluation needs per-record records with a real time axis,
  commit chronology, repo/language/model-family cells, and adversarial/temporal
  holdout outcomes.

### B19: theoretical synthesis

B19 defines **Model-Robust Selective Evidence Conversion** as the synthesis of
B10-B18:

```text
inputs:
  query
  local_candidate_pool
  runtime_observable_uncertainty
  model_capability_profile
  latency_cost_budget

actions:
  local_only
  weak/supporting
  LLM span-narrow
  LLM filter
  abstain
  request-more-context
  EvidenceCore materialization
```

Core principles:

1. Recall and Evidence admission are decoupled.
2. LLMs are routed by role, not used as universal arbiters.
3. `algorithm_spec` is separated from `model_adapter`.
4. Runtime-clean policy may use only runtime-observable features.
5. Optimization should be worst-group / cross-model robust, not average-only.
6. Every candidate must materialize into current-source `EvidenceCore`.

Detailed synthesis:

- [`docs/en/b19-theoretical-synthesis.md`](docs/en/b19-theoretical-synthesis.md)
- [`docs/zh/b19-theoretical-synthesis.md`](docs/zh/b19-theoretical-synthesis.md)
- [`artifacts/b19_theoretical_synthesis/b19_theoretical_synthesis_report.json`](artifacts/b19_theoretical_synthesis/b19_theoretical_synthesis_report.json)

## What OpenLocus does **not** claim today

OpenLocus currently does **not** claim:

- a promoted retrieval policy,
- a default policy change,
- a runtime-clean balanced policy,
- downstream coding-agent solve-rate improvement,
- OOD/temporal generalization,
- QuIVer systems readiness,
- dense/graph/LLM-derived content as Evidence,
- or any change to `EvidenceCore` semantics.

All public research artifacts are aggregate-only unless explicitly marked
otherwise. Raw prompts, responses, snippets, gold labels, provider keys, API
keys, and private per-record records must not be committed.

## Quick start

Build / inspect the CLI:

```bash
cargo run -p openlocus-cli -- --help
```

Representative commands:

```bash
# Source-backed read.
cargo run -p openlocus-cli -- read README.md:1-40 --json

# Repository scan.
cargo run -p openlocus-cli -- scan --json

# Exact / lexical / symbol search.
cargo run -p openlocus-cli -- search regex "EvidenceCore" --json
cargo run -p openlocus-cli -- search bm25 "candidate evidence" --json
cargo run -p openlocus-cli -- search symbol EvidenceCore --json

# Multi-channel retrieval.
cargo run -p openlocus-cli -- retrieve "EvidenceCore materialization" --channels regex,bm25,symbol --json

# Citation validation: true source hash/range/excerpt validation.
cargo run -p openlocus-cli -- citations validate evidence.json --json

# Session-local current-context helper.
cargo run -p openlocus-cli -- context-lite --write-files --json

# Persistent index experiments.
cargo run -p openlocus-cli -- index build --chunk-strategy line --json
cargo run -p openlocus-cli -- index validate --json

# Provider / derived / dense scaffolds are experimental.
cargo run -p openlocus-cli -- provider status --json
cargo run -p openlocus-cli -- derived build --experimental --write-files --json
cargo run -p openlocus-cli -- dense build --experimental --json
```

Some subcommands are research scaffolds. Anything marked `--experimental` should
be treated as candidate/diagnostic infrastructure, not a stable product API.

## Research entry points

Important scripts and artifacts:

```text
eval/p21_llm_rich_candidate.py
  Live rich-candidate harness.

eval/p25_bucket_policy.py
  Deterministic P25 bucket-routed reference policy.

eval/b10_runtime_feature_audit.py
  B10 balanced-policy feature provenance audit.

eval/b10b_runtime_shadow_replay.py
  Runtime-shadow replay scaffold for the ambiguous branch.

eval/b11_prospective_validation.py
  B11 per-record evaluator for the prospective matrix.

eval/b11_matrix_combiner.py
  Aggregate-only combiner for the 32-cell B11 integrated matrix.

eval/b12_public_aggregate_screen.py
  B12 bounded mechanism screen over public aggregate data.

eval/b13_public_aggregate_feasibility_screen.py
  B13 public-aggregate feasibility / no-go screen.

eval/b14_public_aggregate_feasibility_screen.py
  B14 public-aggregate uncertainty-calibration no-go screen.

eval/b15_context_pack_policy.py
  B15 context-pack policy preregistration / scaffold.

eval/b16_downstream_agent_evaluation.py
  B16 downstream-agent evaluation preregistration / scaffold.

eval/b17_quiver_systems_track.py
eval/b17_public_systems_diagnostic_screen.py
  B17 QuIVer systems-track scaffold and public diagnostic screen.

eval/b18_ood_temporal_evaluation.py
  B18 OOD/temporal preregistration + public no-go screen.

eval/b19_theoretical_synthesis.py
  B19 Model-Robust Selective Evidence Conversion synthesis.
```

Key reports:

- [`artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json`](artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json)
- [`artifacts/b12_mechanism_decomposition/b12_public_aggregate_screen_report.json`](artifacts/b12_mechanism_decomposition/b12_public_aggregate_screen_report.json)
- [`artifacts/b19_theoretical_synthesis/b19_theoretical_synthesis_report.json`](artifacts/b19_theoretical_synthesis/b19_theoretical_synthesis_report.json)

Documentation mirror check:

```bash
python3 scripts/validate_docs_i18n.py
```

## Development checks

Common local checks:

```bash
cargo fmt --all --check
cargo test --workspace
python3 scripts/validate_docs_i18n.py
python3 eval/b19_theoretical_synthesis.py --self-test
```

For live provider experiments, use the GitHub workflow with explicit opt-in. Do
not run remote providers implicitly from local scripts.

## Repository notes

- Main design document: [`openlocus-research-design.md`](openlocus-research-design.md)
- Agent usage guide: [`docs/en/AGENTS.md`](docs/en/AGENTS.md)
- Current research conclusions: [`docs/current-research-conclusions.md`](docs/current-research-conclusions.md)
- License: [`LICENSE`](LICENSE) (AGPL-3.0-only)
