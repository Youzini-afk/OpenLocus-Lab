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

Status date: **2026-06-28**.

OpenLocus is now in the **BEA v1 actionability / retrieval-action scheduling**
line. The current question is no longer “which retrieval channel is globally
strongest?”; it is:

> How do we convert high-reach, high-false-cost candidate pools into low-false-
> cost, citation-valid Evidence without weakening `EvidenceCore`?

The latest closed phase is **BEA-v1-P1-4: Automated-Label Reliability Audit**:

```text
status: no_go_p1_4_low_evidence_labels
self-test: 10 / 10
forbidden scan: pass
private label rows: 18
P1-2 intake-valid rows: 18
label errors: 0
informative labels: 0 / 18
known conjunction labels: 0 / 18
unknown-both-hit labels: 18 / 18
```

N1 first showed that span-only repair was rank-blocked: D1 total / pool
span-opportunity was 40, but D1 top-10 actionable was 0. N2 decomposed those 40
rank-blocked records and localized the blocker to extra-depth append/merge-order.
N3 then tested three frozen, deterministic merge-order designs without new
retrieval, selectors, rerankers, P5, or BEA-v1-A:

```text
D3 design denominator: 40

frozen P4 order:                            0 / 40
fixed interleave 2-primary/1-extra after 4: 8 / 40
early extra-depth quota 3:                 10 / 40
bounded promotion after prefix 4/3:        10 / 40

best recovery rate: 0.25 < 0.50 pass gate
```

N3 is an inconclusive/negative design result: the simple bounded merge-order
designs do not solve the N2 blocker. It does **not** authorize implementation,
P5, BEA-v1-A, selector/reranker execution, runtime/default promotion,
method-winner claims, broad retrieval expansion, downstream-value claims, or a
frozen P4 rerun.

The follow-up trace-gap audit converted the post-N3 state into explicit trace
requirements for deep research agents. Rank/pack and merge-order review already
have sanitized rows from N2/N3, but the BEA-v1 mechanism surface still needs
sanitized public exports or new labels for action-cost, support-link, same-file
redundancy, risk-penalty, and ordered-prefix stop traces before new policy
experiments.

P0-2 then refreshed the P1 actionability matrix with P0-1 trace readiness without
mutating P1 causal cell classes. The result confirms the next work is data-surface
work: scheduler/action-cost export, support-link labeling input, same-file
redundancy trace, risk-penalty trace, and ordered-prefix stop trace.

P0-3 exported the scheduler/action-cost dataset contract from committed P4L and
P0-2 artifacts. Aggregate scheduler arms and subgroup denominator buckets are now
public as sanitized rows. Full per-arm private export remains optional because
the historical P4L private JSONL was generated in a previous environment; future
private rows should live under `.openlocus/research-private/` and be supplied via
`--private-arm-outcomes-jsonl`.

P0-4 converted the `support_link_trace` gap into a scanner-validated labeling
input contract. It publishes 18 sanitized support-link design rows and six label
fields, but keeps all target/support hit states unlabeled and does not execute a
support counterfactual.

P0-5 turned the P0-4 contract into a private labeling harness. It can emit an
unlabeled JSONL template under `.openlocus/research-private/` and validate a
completed private label JSONL, while public artifacts contain only sanitized
manifests, harness rows, and summaries.

P0-6/7/8 then closed the remaining parallel trace-surface contracts for
same-file redundancy, risk-penalty removal, and ordered-prefix stop decisions.
These are scanner-validated contract exports only; no private trace rows are
populated yet.

P0-9 consolidated P0-1 through P0-8 into a single next-experiment gate. All P0
artifacts load and pass scanners, but most late surfaces are still contract-only;
the only newly allowed next action is private labeling or private trace
validation.

P1-0 validated the P0-5 private support-label harness end to end with a synthetic
private fixture under `.openlocus/research-private/`. This proves the label
validator path works, but does not create real labels and does not authorize a
support counterfactual.

P1-1 prepared the real private support-labeling queue under
`.openlocus/research-private/`. The public artifact exposes only sanitized queue
buckets and confirms the queue is ready for private labeling.

P1-2 adds a private label intake validator over the P1-1 queue. In the current
run it validates the queue contract and public/private shape join, but no real
private labels were supplied, so support counterfactual execution remains
blocked.

P1-3 fills that queue with deterministic agent-generated private proxy labels
under `.openlocus/research-private/` and validates them through P0-5/P1-2. The
labels are explicitly not human labels, not human-calibrated E/S, not support
utility evidence, and not mechanism evidence; support counterfactual execution
remains blocked.

P1-4 audits those automated labels through direct P1-2 intake and verifies their
origin metadata, but returns `no_go_p1_4_low_evidence_labels`: all 18 labels keep
target/support hit buckets unknown and conjunction ambiguous. P1-5 denominator
audit and support counterfactual execution remain unauthorized.

Provenance note: N2 remains the source decomposition (`28272769423`, result
checkpoint `ce47caf`); N3 is the downstream design simulation over that closed N2
D2 denominator.

High-level guardrail status:

```text
promotion_ready=false
default_should_change=false
evidencecore_semantics_changed=false
runtime_clean_general_algorithm_claimed=false
downstream_agent_value_proven=false
method_winner_claimed=false
benchmark_performance_claimed=false
bea_v1_a_authorized=false
p5_selector_reranker_authorized=false
broad_retrieval_expansion_authorized=false
ood_temporal_supported=false
quiver_systems_supported=false
```

See the current report index:

- [`docs/current-research-conclusions.md`](docs/current-research-conclusions.md)
- [`docs/en/current-research-conclusions.md`](docs/en/current-research-conclusions.md)
- [`docs/zh/current-research-conclusions.md`](docs/zh/current-research-conclusions.md)

## BEA v1 snapshot

### What is established

- **BEA v0.3 remains mixed, not a winner.** BEA-4 scaled frozen v0.3 to
  120 successful records, and BEA-5 ended as a strict fixed-protocol No-Go /
  near-miss at 119/120.
- **Failure decomposition changed the direction.** BEA-FD1 decomposed BEA-4/5
  failures; FD2-A and FD2-A1 showed that directly weighting aggregate FD1 loss
  let non-actionable latency dominate candidate selection.
- **Selector-only BEA-v1-A is under-justified.** BEA-v1-P1 found the
  file-selector lower-bound recoverability for `gold_file_absent` was only
  1/119.
- **Retrieval-action scheduling is the viable BEA v1 lever so far.** P2/P3/P4
  showed candidate availability can improve when retrieval expansion is
  constrained and latency is handled at the action-scheduler layer, not inside
  candidate relevance scoring.
- **The disjoint denominator is now locked; N1 is rank-blocked; N2 localizes the blocker; N3 simple designs are insufficient.** P4H/P4I showed the supported
  Python frame only had 73/80 file-miss records; P4J found a 333-record
  cross-source upper-bound reservoir; P4K resolved exact overlap and locked a
  272-record non-Python denominator; P4L validated the frozen P4 scheduler on
  that locked denominator; N1 then found D1_total=40 but D1_top10_actionable=0,
  N2 classified all 40 as extra-depth append/merge-order blocked, and N3 tested
  three bounded merge-order designs but only recovered 8/40 or 10/40.

### What remains unresolved

- N3 did not find a passing merge-order design, and P0-1/P0-2 now show the next
  empirical question must first expose the missing trace surface: sanitized
  scheduler/action-cost rows, support-link labels, same-file redundancy trace,
  risk-penalty trace, and ordered-prefix stop trace.
- P0-3 has closed the aggregate scheduler/action-cost export contract, but not a
  full private arm-row export. The remaining practical fork is either to recover
  or rerun P4L private arm rows under `.openlocus/research-private/`, or move to
  support-link input design for the `blocked_missing_label` cells.
- P0-4 has closed the support-link input-design contract. The next support phase
  must either create scanner-validated private labels under this contract or stay
  at design level; it still cannot claim support marginal utility.
- P0-5 has closed the private labeling harness contract, and P1-3 now supplies
  scanner-validated agent-generated private proxy labels. These are not human
  labels or mechanism evidence, so support counterfactual execution remains
  unauthorized.
- P0-6/7/8 have closed the remaining trace-surface contracts, but they are not
  populated private trace exports. Policy tuning and counterfactual execution
  remain unauthorized until project-local private rows validate cleanly.
- P0-9 prevents contract-pass artifacts from being read as populated mechanism
  evidence. Support counterfactuals, trace counterfactuals, policy tuning, P5,
  and BEA-v1-A all remain blocked.
- P1-0 authorizes private support labeling using the validated schema and
  harness. P1-3 completed an automated/agent-generated fill, but support
  counterfactual execution remains blocked because these are queue/design-field
  proxy labels with unknown target/support hit buckets. P1-4 confirms they are
  intake-valid but too low-evidence for a P1-5 denominator audit. No
  human-calibrated claim is made or required.
- P1-1 authorizes labeling against the generated project-private queue. It still
  does not authorize support counterfactual execution or support marginal-utility
  claims.
- P1-3 authorizes only automated private support-label fill and P1-2 intake
  validation. It does not authorize support counterfactual execution, support
  marginal-utility claims, mechanism evidence claims, P5, or BEA-v1-A.
- P1-4 authorizes only automated-label reliability auditing. It does not
  authorize P1-5, support counterfactual execution, support marginal-utility
  claims, mechanism evidence claims, P5, or BEA-v1-A.
- The repo does **not** currently contain a real non-Python downstream solve/test
  harness for the locked denominator. Existing B16 downstream harnesses are
  synthetic Python-only; ContextBench/RepoQA locked-denominator records currently
  provide retrieval-reach / gold-path signals, not downstream task success.
- Therefore P4L/N1/N2/N3 are not downstream-value evidence. The next bounded step
  must not be a mislabeled downstream smoke or an immediate P5/v1-A selector.

## What OpenLocus does **not** claim today

OpenLocus currently does **not** claim:

- a promoted retrieval policy,
- a default policy change,
- a method winner,
- BEA-v1-A selector readiness,
- P5 selector/reranker authorization,
- broad retrieval expansion readiness,
- downstream coding-agent solve-rate improvement,
- OOD/temporal generalization,
- QuIVer systems readiness,
- dense/graph/LLM-derived content as Evidence,
- or any change to `EvidenceCore` semantics.

Research artifacts are no longer assumed to be aggregate-only. New mechanism
and actionability phases should publish **scanner-validated, deep-research-agent
readable per-record analysis artifacts** whenever the data license and safety
boundary allow it. These artifacts should expose enough structure for follow-up
research agents to audit mechanisms: anonymous record ids, benchmark/language/
source buckets, arm names, action/state features, hit/miss booleans, rank or
rank-bucket fields, latency/pool/action-cost buckets, disagreement categories,
risk classes, and sanitized trace-gap/actionability fields. Aggregate-only output
is still appropriate for external datasets or provider runs whose redistribution
rules forbid row-level release. Raw prompts, responses, snippets, provider
payloads, secrets, provider keys, API keys, unsanitized private rows, and any
source-linkable private data must not be committed.

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

eval/bea_v1_p4l_locked_non_python_scheduler_validation.py
  Locked non-Python frozen-P4 scheduler validation over the 272-record P4K
  denominator.

eval/bea_v1_n1_frozen_p4_span_refiner_smoke.py
  Frozen-P4 span-refiner smoke with D0 scheduler preservation and rank-aware D1
  total/top-10/rank-blocked denominators.

eval/bea_v1_n2_rank_pack_actionability_decomposition.py
  Rank/pack decomposition for N1's 40 rank-blocked records; authorizes only
  extra-depth merge-order design.
```

Key reports:

- [`artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json`](artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json)
- [`artifacts/b12_mechanism_decomposition/b12_public_aggregate_screen_report.json`](artifacts/b12_mechanism_decomposition/b12_public_aggregate_screen_report.json)
- [`artifacts/b19_theoretical_synthesis/b19_theoretical_synthesis_report.json`](artifacts/b19_theoretical_synthesis/b19_theoretical_synthesis_report.json)
- [`artifacts/bea_v1_p4l_locked_non_python_scheduler_validation/bea_v1_p4l_locked_non_python_scheduler_validation_report.json`](artifacts/bea_v1_p4l_locked_non_python_scheduler_validation/bea_v1_p4l_locked_non_python_scheduler_validation_report.json)
- [`artifacts/bea_v1_n1_frozen_p4_span_refiner_smoke/bea_v1_n1_frozen_p4_span_refiner_smoke_report.json`](artifacts/bea_v1_n1_frozen_p4_span_refiner_smoke/bea_v1_n1_frozen_p4_span_refiner_smoke_report.json)
- [`artifacts/bea_v1_n2_rank_pack_actionability_decomposition/bea_v1_n2_rank_pack_actionability_decomposition_report.json`](artifacts/bea_v1_n2_rank_pack_actionability_decomposition/bea_v1_n2_rank_pack_actionability_decomposition_report.json)

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
