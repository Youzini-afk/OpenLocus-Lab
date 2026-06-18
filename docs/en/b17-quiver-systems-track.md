# B17 QuIVer Systems Track

Date: 2026-06-18

B17 is the **QuIVer systems track** phase. The goal is a **frozen,
preregistered backend bakeoff** that compares ANN backend candidates
on backend systems metrics (latency, memory, build time, update cost,
index size) **under a frozen candidate-quality policy** so backend
quality cannot be silently relaxed when comparing latency / memory /
build / update / index-size numbers.

B17 is a **bounded planning / diagnostic phase**, NOT QuIVer
production backend, NOT ANN quality promotion, NOT default change,
NOT EvidenceCore semantics change. The shipped skeleton performs NO
real ANN backend bakeoff, NO HNSW run, NO QuIVer/Vamana graph run,
NO candidate-set equivalence matrix across backends, NO update-cost /
build-time / index-size benchmark, NO stale/citation cross-backend
validation. The frozen preregistration
(`eval/b17_quiver_systems_track.py`) defines the backend set, the
candidate-set equivalence constraints, the metric registry, the hard
gates, and the experimental structure (no-backend-bakeoff feasibility
→ frozen candidate-quality policy → ANN backend bakeoff → candidate-
set equivalence validation); the bounded public-systems diagnostic
carry-forward / no-go screen
(`eval/b17_public_systems_diagnostic_screen.py`) reads the
already-published R33 readiness + R34/R36 anchor-proto + real-provider
P3/P4 quiver diagnostics + optional R24 QuIVer/TDB/dense probe and
emits a `no_go_quiver_graph_missing` (or
`diagnostic_carry_forward_only`) verdict.

> **Important claim boundary.** B17 IS the quiver-systems-track
> *stage* (`stage_is_quiver_systems_track=true`), but the shipped
> skeleton performs NO ANN backend bakeoff
> (`ann_backend_bakeoff_performed=false`), NO candidate-set
> equivalence validation
> (`candidate_set_equivalence_validated=false`), NO QuIVer/Vamana
> graph implementation (`quiver_graph_implemented=false`), and NO
> backend quality promotion (`backend_quality_promoted=false`). The
> synthetic-fixture / `--input` stub report sets
> `promotion_ready=false`, `default_should_change=false`,
> `evidencecore_semantics_changed=false`, `retrieval_policy_changed=false`,
> `metrics_evaluated=false`, `new_provider_calls=0` so the public
> artifact cannot be mistaken for an empirical B17 systems bakeoff
> result. This commit is strictly a skeleton / no-go commit: the
> current flags (`ann_backend_bakeoff_performed=false`,
> `candidate_set_equivalence_validated=false`,
> `quiver_graph_implemented=false`,
> `backend_quality_promoted=false`) remain false. Any future real
> B17 empirical path would require its own separate preregistration;
> the exact flag schema for that future path is future work and is
> NOT present in this skeleton. B17 results in this commit are
> research candidates only: this skeleton/no-go commit authorizes no
> default change, no retrieval-policy change, no backend quality
> promotion, no QuIVer graph implementation, no EvidenceCore
> modification, and no claim that any backend improves a downstream
> agent.

> **Important systems-vs-quality boundary.** The systems bakeoff is a
> **systems** comparison (latency / memory / build / update / index-
> size) under a **frozen candidate-quality policy**. A backend that
> wins on latency but violates candidate-set equivalence is rejected
> regardless of its systems numbers. The frozen candidate-quality
> policy is the precondition that makes the systems bakeoff
> meaningful: without it, backend latency comparisons would silently
> trade quality for speed.

> **CRITICAL anti-fabrication boundary.** The skeleton MUST NOT
> compute fake candidate_set_overlap_at_k / gold_retention_delta /
> span_f0_5_delta / primary_false_positive_delta / p50_latency /
> p95_latency / hot_memory / build_time / update_cost / index_size /
> recall_tolerance_violation_count metrics from the existing R33 /
> R34 / R36 / R24 diagnostics. Those diagnostics are BQ / flat_f32 /
> bq_topk_f32_rerank diagnostics only; they do NOT contain a
> QuIVer/Vamana graph implementation, an HNSW run, or a candidate-set
> equivalence matrix across backends, so any B17 systems metric
> computed from them would be a fabrication. The synthetic fixture
> validates only that the backend set, candidate-set equivalence
> constraints, metric names, and hard gates are wired correctly; it
> does NOT present synthetic metric values as empirical B17 systems
> results. The report surfaces `ann_backend_bakeoff_performed=false`,
> `candidate_set_equivalence_validated=false`,
> `quiver_graph_implemented=false`, `backend_quality_promoted=false`,
> `metrics_evaluated=false`, and
> `no_fake_ann_metrics_from_diagnostics=true` so a reader cannot
> mistake the skeleton for an empirical B17 systems bakeoff result.

## Preregistration declaration

The following artifacts, backend set, candidate-set equivalence
constraints, metric registry, hard gates, experimental structure,
and predeclared success/partial/failure criteria are **FROZEN**
before any B17 empirical systems bakeoff. No retuning of the backend
set, the candidate-set equivalence constraints, the metric registry,
the hard gates, or the success criteria is allowed after B17
empirical systems runs begin. Any post-hoc analysis must be labeled
exploratory and require a separate validation round.

### Frozen artifacts

- `r33_quiver_readiness` (R33 BQ readiness diagnostic) — referenced,
  not modified; **diagnostic-only carry-forward**, not promotion
  evidence, not quality proof
- `r34_r36_quiver_anchor_proto` (R34/R36 anchor-proto diagnostic) —
  referenced, not modified; **diagnostic-only carry-forward**, not
  promotion evidence, not quality proof
- B17 algorithm spec itself
  (`artifacts/b17_quiver_systems_track/b17_quiver_systems_track.algorithm.json`)
  — frozen before any systems bakeoff; stable sha256

## Systems-only objective (FROZEN)

Produce a **frozen, preregistered backend bakeoff** that compares ANN
backend candidates on backend systems metrics (latency, memory, build
time, update cost, index size) **under a frozen candidate-quality
policy** so backend quality cannot be silently relaxed. B17 does NOT
learn a backend, does NOT implement a QuIVer/Vamana graph in this
skeleton, does NOT change EvidenceCore, does NOT promote a default,
does NOT promote a backend, does NOT change retrieval policy, and does
NOT claim that any backend improves a downstream agent.

## Candidate backends (FROZEN)

The backend set is the closed set of ANN backend candidates a B17
systems bakeoff may compare under the frozen candidate-quality
policy:

- `flat_f32_reference` — the reference backend (ground-truth
  nearest-neighbor search; the candidate-set equivalence baseline)
- `hnsw_candidate` — an HNSW candidate backend (existing diagnostic-
  era candidate; no HNSW run exists in any current public artifact)
- `bq_topk_f32_rerank_candidate` — BQ top-k + f32 rerank candidate
  backend (existing diagnostic-era candidate)
- `quiver_vamana_prototype` — the QuIVer/Vamana graph backend (the
  B17 systems-track end goal; **unimplemented** —
  `quiver_vamana_implemented=false`)
- `tdb_vector_candidate` — OPTIONAL store/backend candidate only; NOT
  an Evidence source and EXCLUDED by default
  (`store_backend_candidate_only_never_evidence_source`)

Primary comparison backends (always present): `flat_f32_reference`
vs the candidate backends (`hnsw_candidate`,
`bq_topk_f32_rerank_candidate`, `quiver_vamana_prototype`).

## Candidate-set equivalence constraints (FROZEN)

A candidate backend is admissible to the systems bakeoff ONLY if it
preserves candidate quality within frozen tolerances versus the
reference backend (`flat_f32_reference`). The constraints are
FROZEN; a backend that fails any constraint is rejected regardless of
its latency / memory / build / update / index-size numbers.

- `candidate_set_overlap_at_k` — overlap@K vs reference must meet or
  exceed the frozen minimum overlap for every K in the frozen K set
  (`[10, 50, 100]`); minimum overlap `0.90`
- `gold_retention_delta_within_tolerance` —
  `gold_retention_delta` vs reference must be within the frozen
  tolerance (no quality regression beyond the frozen margin);
  tolerance `0.05`
- `primary_false_positive_delta_guard` —
  `primary_false_positive_delta` vs reference must not exceed the
  frozen guard (no PFP regression); guard `0.05`
- `span_f0_5_delta_within_tolerance` — `SpanF0.5_delta` vs reference
  must be within the frozen tolerance (no span-quality regression);
  tolerance `0.05`
- `citation_validity_required` — `citation_validity` must be `1.0`
  for every backend (fail-closed citation and range validation)
- `stale_evidencecore_rejection_required` — stale and EvidenceCore-
  rejected candidates must be rejected by every backend (no stale
  leakage)
- `no_default_expansion_required` — no candidate backend may expand
  the default retrieval policy without separate promotion

## Metric registry (FROZEN)

The metric NAMES B17 will compute when real per-backend systems
bakeoff inputs are available. The skeleton defines them and
validates the hard gates, but does NOT compute fake metric values
from the existing R33/R34/R36/R24 diagnostics.

- `candidate_set_overlap_at_k`
- `gold_retention_delta`
- `span_f0_5_delta`
- `primary_false_positive_delta`
- `p50_latency`
- `p95_latency`
- `hot_memory`
- `build_time`
- `update_cost`
- `index_size`
- `recall_tolerance_violation_count`

Every metric requires per-backend systems bakeoff inputs (index
build records, search latency records, hot memory records, index
size records, update cost records, candidate-set-at-K records, gold
retention records, span F0.5 records, PFP records, citation
validity records, stale rejection records, EvidenceCore rejection
records, recall tolerance violation records, randomized run order
proof, isolated index workspace proof, shared frozen candidate-
quality manifest); none can be computed from the existing R33/R34/
R36/R24 diagnostics.

## Hard gates (FROZEN)

The following hard gates are FROZEN before any B17 systems bakeoff.
A candidate backend that fails any gate is rejected, regardless of
its aggregate systems metrics.

- **quiver_graph_implementation_gate**: the B17 systems bakeoff cannot
  complete until a QuIVer or Vamana graph backend is implemented
  (`quiver_vamana_implemented=false` today). The skeleton does not
  evaluate this gate; it only defines it and reports the current
  status.
- **backend_parity_gate**: every backend must run under the same
  frozen candidate-quality policy, the same shared frozen candidate-
  quality manifest, the same randomized run order, and the same
  isolated index workspace; the only varied factor is the backend
  (`operational_parity_build_time_match_tolerance=0.20`,
  `operational_parity_update_cost_match_tolerance=0.20`). The
  skeleton does not evaluate this gate; it only defines it.
- **candidate_set_equivalence_gate**: every candidate backend must
  satisfy every candidate-set equivalence constraint versus the
  reference backend (overlap@K, gold_retention_delta,
  primary_false_positive_delta, SpanF0.5_delta, citation_validity,
  stale/EvidenceCore rejection, no default expansion). The skeleton
  does not evaluate this gate; it only defines it.
- **evidencecore_materialization_gate**: every backend's output
  must materialize through EvidenceCore with citation-valid
  evidence; no backend may bypass EvidenceCore. The skeleton does
  not evaluate this gate; it only defines it.
- **stale_citation_gate**: stale and EvidenceCore-rejected
  candidates must be rejected by every backend; citation validity
  must be `1.0` for every backend. The skeleton does not evaluate
  this gate; it only defines it.
- **privacy_gate**: `aggregate_only_public_artifact=true`; no raw
  records, task IDs, repo IDs, candidate IDs, paths, spans,
  snippets, prompts, responses, diffs, patches, test execution
  results, solve labels, agent event logs, backend event logs,
  index build records, search latency records, hot memory records,
  index size records, gold spans, private labels, provider keys,
  base URLs, API keys/secrets/tokens, content SHAs, digests, or
  line ranges in any public artifact; `new_provider_calls=0` in the
  skeleton.
- **promotion_false_gate**: `promotion_ready=false`,
  `default_should_change=false`,
  `evidencecore_semantics_changed=false`,
  `retrieval_policy_changed=false`,
  `backend_quality_promoted=false`,
  `quiver_graph_implemented=false`,
  `ann_backend_bakeoff_performed=false`,
  `candidate_set_equivalence_validated=false`,
  `metrics_evaluated=false` are always present, so a skeleton /
  stub / no-go report cannot be misread as a promoted backend or a
  QuIVer systems bakeoff result.

## Split protocol (FROZEN)

Real B17 splits per-backend inputs into a **task-screen split** and
a **fresh-validation split**, stratified by `(repo, model_family,
language)`. The split protocol is
`stratified_by_repo_model_family_language` with
`task_screen_fraction=0.50` and `fresh_validation_fraction=0.50`.
The fresh-validation split is held out and reported once
(`fresh_validation_split_reported_once=true`). No metric on the
fresh-validation split may feed back into the task screen or the
frozen candidate-quality policy.

## Worst-group reporting

B17 reports worst-group metrics over `{repo, model_family,
language}` groups, plus a `CVaR_20%` tail average (worst 20% of
group metrics). The CVaR tail fraction is `cvar_alpha=0.20`
(frozen).

## Privacy / publication gates

Public artifacts must be aggregate-only. The B17 evaluator enforces:

- **no** raw records, task IDs, repo IDs, candidate IDs, paths, spans,
  snippets, prompts, responses, diffs, patches, test execution
  results, solve labels, agent event logs, backend event logs, index
  build records, search latency records, hot memory records, index
  size records, gold spans, private labels, provider keys, base
  URLs, API keys/secrets/tokens, content SHAs, digests, or line
  ranges in any public artifact;
- **no** raw filesystem path strings, 64-char hex digests, http(s)
  URLs, or credential assignments as values;
- `aggregate_only_public_artifact=true`;
- `new_provider_calls=0` (skeleton; no live LLM calls and no live ANN
  backend bakeoff);
- `forbidden_public_key_scan_clean=true`.

## Predeclared success / partial / failure criteria

The criteria below are FROZEN before any B17 empirical systems
bakeoff (`PREDECLARED_CRITERIA`):

| Outcome | Criterion |
| --- | --- |
| **Success** | Every candidate backend satisfies every candidate-set equivalence constraint versus the reference backend on the fresh-validation split, the QuIVer/Vamana graph backend is implemented, every backend reports per-backend latency / memory / build / update / index-size within the operational-parity gates, AND cost/systems metrics reported per backend. |
| **Partial** | Some candidate backends satisfy candidate-set equivalence but not all; or one backend is within the operational-parity gates but another is not; or the QuIVer/Vamana graph backend is implemented but candidate-set equivalence validation has not completed. |
| **Failure** | No candidate backend satisfies candidate-set equivalence on the fresh-validation split, OR any hard gate fails (quiver graph implementation, backend parity, candidate-set equivalence, EvidenceCore materialization, stale/citation, privacy, promotion false). |

Frozen numeric gates:

- `candidate_set_overlap_at_k_minimum = 0.90`
- `gold_retention_delta_tolerance = 0.05`
- `primary_false_positive_delta_guard = 0.05`
- `span_f0_5_delta_tolerance = 0.05`
- `citation_validity_required = 1.0`
- `stale_evidencecore_rejection_required = true`
- `no_default_expansion_required = true`
- `equivalence_ks = [10, 50, 100]`
- `cvar_alpha = 0.20`
- `task_screen_fraction = 0.50`
- `fresh_validation_fraction = 0.50`
- `min_denominator_per_backend_repo_cell = 30`
- `operational_parity_build_time_match_tolerance = 0.20`
- `operational_parity_update_cost_match_tolerance = 0.20`
- `operational_parity_same_frozen_candidate_quality_policy = true`
- `operational_parity_no_default_expansion = true`
- `operational_parity_no_evidencecore_semantics_change = true`
- `systems_metrics_reported_per_backend = true`

The B17 verdict framework emits one of:

- `success` (every candidate backend satisfies candidate-set
  equivalence, QuIVer/Vamana graph implemented, all gates pass on
  the fresh-validation split)
- `failure` (no backend satisfies candidate-set equivalence, or any
  hard gate fails)
- `partial` (some backends satisfy, not all; or QuIVer/Vamana graph
  implemented but candidate-set equivalence incomplete)
- `insufficient_data` (synthetic fixture, or too few per-backend
  inputs)
- `not_implemented` (`--input` stub, real QuIVer systems bakeoff
  deferred)

The skeleton only emits `insufficient_data` (synthetic fixture) or
`not_implemented` (ci_ephemeral_records stub); `success` /
`failure` / `partial` are NOT emitted by this skeleton. Any future
real B17 empirical path that might emit them would require its own
separate preregistration, and its exact flag schema is future work
and is NOT present in this skeleton. This commit keeps
`ann_backend_bakeoff_performed=false`,
`candidate_set_equivalence_validated=false`,
`quiver_graph_implemented=false`, and
`backend_quality_promoted=false` strictly.

## Required per-backend inputs (real-B17 data contract)

Real B17 systems bakeoff requires ALL of the following per backend.
If any is missing, real B17 cannot run and the skeleton emits
`insufficient_data` / `not_implemented`.

- `per_backend_index_build_record`
- `per_backend_search_latency_record`
- `per_backend_hot_memory_record`
- `per_backend_index_size_record`
- `per_backend_update_cost_record`
- `per_backend_candidate_set_at_k_record`
- `per_backend_gold_retention_record`
- `per_backend_span_f0_5_record`
- `per_backend_primary_false_positive_record`
- `per_backend_citation_validity_record`
- `per_backend_stale_rejection_record`
- `per_backend_evidencecore_rejection_record`
- `per_backend_recall_tolerance_violation_record`
- `per_backend_randomized_run_order_proof`
- `per_backend_isolated_index_workspace_proof`
- `shared_frozen_candidate_quality_manifest`

## Existing R33/R34/R36 diagnostic carry-forward

The existing diagnostics are **diagnostic-only carry-forward**, not
quality proof and not promotion evidence:

- R33 readiness diagnostic (`artifacts/r33/quiver_readiness.json`):
  BQ2/sign-magnitude diagnostics only; `quiver_graph_implemented=
  false`; `quiver_quality_metrics_emitted=false`;
  `BQ_diagnostics_only=true`; `promotion_ready=false`
- R34/R36 anchor-proto diagnostic
  (`artifacts/r34_r36/quiver_anchor_proto.json`): flat f32, BQ top-k
  + f32 rerank, sharding layouts, anchor-seeded candidate-pool
  restriction; `quiver_mode=diagnostic_only`;
  `quiver_graph_implemented=false`;
  `quiver_default_allowed=false`;
  `quiver_supporting_channel_allowed=true`;
  `dense_or_quiver_role=candidate/supporting-only`;
  `promotion_ready=false`
- real-provider P3 quiver readiness
  (`artifacts/real_provider/p3_real_quiver_readiness.json`):
  diagnostic-only real-provider variant;
  `quiver_graph_implemented=false`;
  `quiver_quality_metrics_emitted=false`
- real-provider P4 quiver anchor proto
  (`artifacts/real_provider/p4_real_quiver_anchor_proto.json`):
  diagnostic-only real-provider variant;
  `quiver_mode=diagnostic_only`;
  `quiver_graph_implemented=false`
- R24 QuIVer/TDB/dense probe (`runs/r24-quiver-tdb-probe.json`):
  QuIVer unavailable/not-implemented; TDB feature-gated
  metadata/chunk store placeholder; dense mock candidate-channel
  safety/quality smoke (not semantic quality);
  `promotion_ready=false`

These diagnostics are pre-B17 signals only. They do NOT implement a
QuIVer/Vamana graph backend, do NOT contain an HNSW run, and do NOT
contain a candidate-set equivalence matrix across backends. They
are carried forward as **diagnostic-only**, not as quality proof.

## Safety invariants

```text
promotion_ready=false
default_should_change=false
evidencecore_semantics_changed=false
retrieval_policy_changed=false
backend_quality_promoted=false
stage_is_quiver_systems_track=true (B17 stage IS quiver systems track)
quiver_graph_implemented=false (skeleton performs no QuIVer or Vamana graph implementation)
ann_backend_bakeoff_performed=false (skeleton performs no ANN backend bakeoff)
candidate_set_equivalence_validated=false (skeleton validates no candidate-set equivalence)
metrics_evaluated=false (skeleton; no fake ANN metrics from diagnostics)
new_provider_calls=0 (skeleton; no live LLM calls)
no_fake_ann_metrics_from_diagnostics=true
aggregate_only_public_artifact=true
```

## What B17 does NOT prove

- B17 does **not** implement a QuIVer or Vamana graph backend.
- B17 does **not** run an HNSW backend.
- B17 does **not** perform an ANN backend bakeoff.
- B17 does **not** validate candidate-set equivalence across
  backends.
- B17 does **not** compute candidate_set_overlap_at_k /
  gold_retention_delta / span_f0_5_delta /
  primary_false_positive_delta / p50_latency / p95_latency /
  hot_memory / build_time / update_cost / index_size /
  recall_tolerance_violation_count metrics from the existing R33 /
  R34 / R36 / R24 diagnostics.
- B17 does **not** promote any backend.
- B17 does **not** change any defaults.
- B17 does **not** change retrieval policy.
- B17 does **not** change `EvidenceCore` semantics.
- B17 does **not** claim that any backend improves a downstream
  agent.
- B17 results are research candidates only; a B17-frozen backend
  candidate is NOT a promoted backend and is NOT the new default
  until separately promoted via the standard promotion process.
- B17's `--input` path is a stub (`verdict="not_implemented"`); full
  QuIVer systems bakeoff + candidate-set equivalence matrix is
  deferred to a later task.
- The existing R33/R34/R36/R24 diagnostics are **not** quality
  proof; they are diagnostic-only carry-forward.

## Self-test (read-only) and explicit artifact regeneration

```bash
python3 eval/b17_quiver_systems_track.py --self-test
python3 eval/b17_quiver_systems_track.py --regenerate-artifacts
python3 eval/b17_quiver_systems_track.py --self-test
python3 eval/b17_public_systems_diagnostic_screen.py --self-test
python3 eval/b17_public_systems_diagnostic_screen.py \
    --out artifacts/b17_quiver_systems_track/b17_public_systems_diagnostic_screen_report.json
```

The `eval/b17_quiver_systems_track.py --self-test` run is
**read-only**: it verifies the backend set, candidate-set equivalence
constraints, metric registry, hard gates, and experimental structure
against a synthetic fixture (definitions-only; no per-backend
systems bakeoff inputs, no computed metric values) and compares the
in-memory expected algorithm spec + report to the on-disk artifacts,
**failing on drift**. It does NOT mutate checked-in artifacts. It
emits `stage_is_quiver_systems_track=true`,
`quiver_graph_implemented=false`,
`ann_backend_bakeoff_performed=false`,
`candidate_set_equivalence_validated=false`,
`backend_quality_promoted=false`,
`metrics_evaluated=false`,
`new_provider_calls=0`,
`no_fake_ann_metrics_from_diagnostics=true`, so the synthetic-
fixture report is unambiguously NOT an empirical B17 systems bakeoff
result.

The read-only self-test runs these checks:

1. `forbidden_scan` — forbidden public keys/values scan
2. `spec_hash_stable` — algorithm spec sha256 stability
3. `backend_set_closed` — reference / candidate / optional-store
   backends are closed and mutually disjoint; QuIVer/Vamana graph
   backend is unimplemented; optional store backend excluded by
   default
4. `candidate_set_equivalence_constraints` — 7 frozen constraints
   with the required IDs present
5. `metric_registry` — 11 metric names defined; no aggregate-mean
   metrics
6. `hard_gates_defined` — quiver graph implementation / backend
   parity / candidate-set equivalence / EvidenceCore materialization
   / stale-citation / privacy / promotion-false gates defined
7. `experimental_structure_frozen` — 4 frozen stages; no feedback
8. `no_fake_ann_metrics_from_diagnostics` — synthetic fixture has no
   per-backend systems bakeoff inputs and no metric values
9. `input_stub_not_implemented` — `--input` stub returns
   `not_implemented`
10. `reference_diagnostics_pinned` — R33 readiness + R34/R36
    anchor-proto diagnostic-only carry-forward artifacts present on
    disk
11. `artifacts_match_in_memory` — read-only drift check: in-memory
    expected spec + report match the on-disk artifacts

`python3 eval/b17_quiver_systems_track.py --regenerate-artifacts`
is the ONLY path that mutates checked-in artifacts: it (re)writes
the on-disk algorithm spec + synthetic-fixture report from the
current build functions. After mutating, re-run `--self-test` to
confirm the on-disk artifacts now match the in-memory expected
objects (no drift).

The `--input` path is a non-canonical stub path: it requires an
explicit `--out` destination and refuses to write ANY path inside
`artifacts/b17_quiver_systems_track/` (canonical report, algorithm
spec, or public systems diagnostic screen report). It can write a
temporary stub report for development, but it does not mutate
checked-in B17 artifacts.

The `eval/b17_public_systems_diagnostic_screen.py --self-test` run
verifies the bounded public-systems diagnostic carry-forward / no-go
screen against a synthetic minimal R33 + R34/R36 + real-provider P3
+ P4 + R24 fixture. It emits `verdict=no_go_quiver_graph_missing`
(or `diagnostic_carry_forward_only`), with
`quiver_graph_implemented=false`,
`ann_backend_bakeoff_performed=false`,
`candidate_set_equivalence_validated=false`,
`backend_quality_promoted=false`,
`metrics_evaluated=false`,
`full_b17_systems_bakeoff_possible_from_public_artifacts=false`.

## Artifacts

- `artifacts/b17_quiver_systems_track/b17_quiver_systems_track.algorithm.json`
  (frozen spec; deterministic, stable sha256; regenerated only via
  `--regenerate-artifacts`)
- `artifacts/b17_quiver_systems_track/b17_quiver_systems_track_report.json`
  (synthetic-fixture self-test report, verdict `insufficient_data`;
  `quiver_graph_implemented=false`,
  `ann_backend_bakeoff_performed=false`,
  `candidate_set_equivalence_validated=false`,
  `backend_quality_promoted=false`,
  `stage_is_quiver_systems_track=true`,
  `no_fake_ann_metrics_from_diagnostics=true`;
  no empirical per-backend metric values)
- `artifacts/b17_quiver_systems_track/b17_public_systems_diagnostic_screen_report.json`
  (bounded public-systems diagnostic carry-forward / no-go screen
  report; `verdict=no_go_quiver_graph_missing` (or
  `diagnostic_carry_forward_only`);
  `full_b17_systems_bakeoff_possible_from_public_artifacts=false`;
  carries forward R33 `quiver_graph_implemented=false` and
  `quiver_quality_metrics_emitted=false`, R34/R36
  `quiver_mode=diagnostic_only`, real-provider P3/P4 diagnostic-only
  statuses, and R24 QuIVer/TDB/dense probe statuses; aggregate-only,
  no raw event traces, paths, diffs, prompts/responses, hidden
  tests, or task IDs)

## What's autonomous vs. needs user action

### Autonomous (can be done now)

- B17 plan document (this file)
- B17 evaluator skeleton (`eval/b17_quiver_systems_track.py`) +
  read-only `--self-test` (compares in-memory expected artifacts to
  on-disk artifacts, fails on drift) and explicit
  `--regenerate-artifacts` mutating path
- B17 frozen algorithm spec + synthetic-fixture report artifacts
- B17 bounded public-systems diagnostic carry-forward / no-go screen
  (`eval/b17_public_systems_diagnostic_screen.py`) + self-test +
  `artifacts/b17_quiver_systems_track/b17_public_systems_diagnostic_screen_report.json`
  (reads the published R33 + R34/R36 + real-provider P3/P4 quiver
  diagnostics + optional R24 probe; emits
  `no_go_quiver_graph_missing` /
  `diagnostic_carry_forward_only`; never claims QuIVer
  implementation, never computes an ANN metric from diagnostics,
  never promotes a backend, never declares a winner)

### Needs QuIVer/Vamana graph backend implementation

- B17 real systems bakeoff requires a QuIVer or Vamana graph backend
  implementation, an HNSW backend run, per-backend systems bakeoff
  inputs (index build records, search latency records, hot memory
  records, index size records, update cost records, candidate-set-
  at-K records, gold retention records, span F0.5 records, PFP
  records, citation validity records, stale rejection records,
  EvidenceCore rejection records, recall tolerance violation
  records, randomized run order proof, isolated index workspace
  proof), and a shared frozen candidate-quality manifest. If those
  records are not yet produced, B17 emits `insufficient_data` /
  `not_implemented`.

### Needs user review

- Results interpretation
- Decision to proceed to a real B17 empirical systems bakeoff path
  (separate preregistration required; must include a QuIVer or
  Vamana graph backend implementation)
- Decision to expand from the minimum viable backend set to a
  larger set (separate preregistration required)

## Next steps after B17

- **B17 success** (future real B17 path): every candidate backend
  satisfies candidate-set equivalence versus the reference backend,
  the QuIVer/Vamana graph backend is implemented, all hard gates
  pass. Proceed via the standard promotion process; B17 success
  does NOT auto-promote.
- **B17 failure** (future real B17 path): no candidate backend
  satisfies candidate-set equivalence. The current retrieval stack
  continues; no backend is promoted.
- **B17 partial** (future real B17 path): some backends satisfy,
  not all. Investigate backend-conditional candidate-quality
  policies; possibly expand the backend set in a separate B17B
  round (separate preregistration required).
- **B17 skeleton / no-go** (this commit): the bounded public-systems
  diagnostic carry-forward / no-go screen confirms real B17 cannot
  be performed from public diagnostics alone — the QuIVer/Vamana
  graph backend is missing. Real B17 requires QuIVer/Vamana graph
  backend implementation + per-backend systems bakeoff inputs.
