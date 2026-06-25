# BEA-v1-P4K: Exact Overlap Resolution & Locked Reservoir Audit

Date: 2026-06-25. BEA-v1-P4K is a bounded **denominator/source audit**
performed after the BEA-v1-P4J No-Go (CI `28146407493`,
`no_go_cross_source_reservoir_unqualified`, upper-bound reservoir 333 but
qualified count 0 because P4H/P4I overlap was unresolved). It does **not** run
P2/P3/P4 scheduler arms, does **not** validate a scheduler, does **not** expand
retrieval, does **not** execute a selector/reranker, does **not** call any
provider, does **not** run runtime/default promotion or method-winner logic,
and does **not** authorize P5, BEA-v1-A, frozen P4 validation, or frozen P4
rerun. The only diagnostic arm is `current_bea_candidate_pool_replay`.

> `claim_level = bea_v1_p4k_exact_overlap_resolution_locked_reservoir_audit_only`.
> `provider_calls_made=false`, `gold_labels_used_for_query_construction=false`,
> `gold_labels_used_for_policy=false`, `latency_in_candidate_relevance=false`,
> `query_anchors_used_in_p4_arm=false`, `selector_or_reranker_changed=false`,
> `selector_or_reranker_executed=false`,
> `p2_depth_only_reference_executed=false`,
> `p3_constrained_depth_policy_reference_executed=false`,
> `p4_latency_aware_action_scheduler_executed=false`,
> `v1_a_selector_executed=false`, `p5_authorized=false`,
> `v1_a_authorized=false`, `frozen_p4_rerun_authorized=false`,
> `frozen_p4_validation_executed=false`, `locked_p4_validation_executed=false`,
> and `locked_p4_validation_design_authorized=false` (default) are binding.

## Motivation (P4H/P4I/P4J No-Go)

- P4H (CI `28132121958`): `no_go_p4h_insufficient_denominator`, 73/80 disjoint
  file-miss heldout records in the supported Python frame; exact selected keys
  were private and not committed.
- P4I (CI `28137455572`): `no_go_disjoint_denominator_reservoir_insufficient`,
  same 73 FD1-excluded Python-frame reservoir; exact selected keys
  private/unavailable.
- P4J (CI `28146407493`): `no_go_cross_source_reservoir_unqualified`, found
  upper-bound reservoir 333 across ContextBench all-language + RepoQA non-Python,
  but qualified count 0 because P4H/P4I overlap was unresolved.

P4K answers the open question left by P4J: can exact selected raw keys for
P4H (73), P4I (73), and P4J (333) be empirically reconstructed under `/tmp`
using deterministic source ordering and the same baseline/current
candidate-pool replay classifier, and if so, what is the post-exclusion locked
cross-source reservoir count after removing P4H and P4I overlap from P4J?

## Scope (binding)

- P4K is an **exact overlap resolution & locked reservoir audit only**. It is
  NOT P5, NOT BEA-v1-A, NOT scheduler validation, NOT retrieval expansion, NOT
  selector/reranker, NOT broad retrieval, NOT method-winner logic, NOT
  runtime/default promotion, NOT frozen P4 validation, NOT frozen P4 rerun.
- It re-runs the same deterministic scans used by P4H/P4I/P4J, using the
  existing `current_bea_candidate_pool_replay` diagnostic arm, and records
  selected raw keys **privately under `/tmp`** (never uploaded, never publicly
  serialized).
- P4H/P4I reconstruction: ContextBench Python (offset 0, limit 480) + RepoQA
  Python (offset 0, limit 240), FD1 BEA-4/5 exact-key exclusion, baseline
  file-miss selection. P4H had target 80 (found 73), P4I scanned full frame
  (found 73). Both use the same Python frame and classifier, so their
  reconstructed key sets are identical (expected 73 each).
- P4J reconstruction: ContextBench all-languages (limit 480) + RepoQA non-Python
  (per-language limit 60), FD1 BEA-4/5 exact-key exclusion (Python via
  python-ordinal; non-Python by-construction disjoint), baseline file-miss
  selection (expected 333 total, with the committed P4J split 61 Python and
  272 non-Python).

## Canonical overlap keys

- Python rows: `("python", benchmark, python_ordinal)` — matches across
  P4H/P4I/P4J Python scans because the Nth Python row in any fetch is the same
  dataset row.
- Non-Python rows: `("non_python", source_frame, language, raw_idx)` — unique
  to P4J, by-construction disjoint from P4H/P4I (Python-only).

All key sets are private (in-memory or `/tmp` only). No canonical keys, raw
keys, row IDs, or private hashes are publicly serialized.

## Reconstruction & overlap computation

- The reconstruction requires network access + the OpenLocus binary + FD1
  private decomposition. If any prerequisite fails, the status is
  `fail_schema_contract` (fail-closed) or `unavailable_with_reason` (no
  network).
- If reconstruction counts cannot exactly match expected aggregates (73/73/333),
  the status is `no_go_exact_overlap_resolution_unavailable` (conservative,
  never invents keys or uses public aggregate approximations).
- Overlap: `p4j_overlap_with_p4h_count` = |P4J keys ∩ P4H keys|;
  `p4j_overlap_with_p4i_count` = |P4J keys ∩ P4I keys|.
- Locked reservoir = P4J keys − FD1 prior − P4H keys − P4I keys. Since P4H and
  P4I use the same Python frame, subtracting both removes the same Python key
  set once. Non-Python P4J rows are by-construction disjoint from P4H/P4I;
  any Python contribution is determined by exact overlap, not by a public
  aggregate assumption.

## Hard validity gates

- `p4h_exact_keys_reconstructed=true` AND `p4i_exact_keys_reconstructed=true`
  AND `p4j_exact_keys_reconstructed=true` for overlap resolution.
- `locked_cross_source_reservoir_count >= 80` for reservoir availability.
- FD1 exact prior exclusion used; no private raw keys/ids/canonical keys
  serialized.
- `exact_keys_publicly_serialized=false`;
  `private_key_hashes_publicly_serialized=false`.
- Aggregate-only, records-only public artifact: no dynamic dicts for public
  metrics.
- `forbidden_scan.status=pass`.
- No provider calls. No P2/P3/P4 scheduler arms. No selector/reranker. No
  method-winner logic. No runtime/default promotion.
- Blocking failures (scan failed, scan not attempted, clone failed, asset
  download/decompress failed, unexpected exception, FD1 replay/schema
  mismatch) cannot be reported as overlap-resolution-unavailable; they yield
  `fail_schema_contract` (fail-closed).

## Statuses

- `cross_source_locked_reservoir_ready_for_locked_p4_validation_design` — ONLY if P4H
  count=73, P4I count=73, P4J count=333, FD1 prior exclusion used, exact
  P4H/P4I/P4J reconstruction succeeded, `locked_cross_source_reservoir_count
  >= 80`, public artifact aggregate-only, `forbidden_scan.status=pass`. This
  authorizes **only** designing a later locked-denominator validation phase.
  It does **not** run a scheduler, does **not** execute P4 validation, does
  **not** authorize P5, BEA-v1-A, runtime promotion, method-winner claims,
  broad retrieval expansion, selector/reranker execution, frozen P4 rerun, or
  frozen P4 validation. `locked_p4_validation_design_authorized=true` and `scheduler_validation_authorized=false` are
  expressed only inside `stop_go_records`; the top-level guard
  `locked_p4_validation_executed` remains false.
- `no_go_locked_cross_source_reservoir_insufficient` — exact overlap resolved,
  but `locked_cross_source_reservoir_count < 80`.
- `no_go_exact_overlap_resolution_unavailable` — any exact key reconstruction
  cannot be reproduced deterministically or cannot match expected counts
  (73/73/333). No keys are invented; the mismatch reason is disclosed in
  aggregate only.
- `unavailable_with_reason` — default no-network artifact (honest, not a
  pass).
- `fail_schema_contract` / `fail_forbidden_scan` — privacy/schema/provenance
  failures. No `fail_*` status is CI-valid for a network-enabled real run.

## Stop rules (exact)

1. If the reconstruction was not attempted (network disabled, prerequisites
   missing), the default artifact is `unavailable_with_reason` (no-network
   path only).
2. If a blocking failure occurs during the reconstruction (raw fetch failed,
   clone failed, asset download/decompress failed, unexpected exception, FD1
   replay/schema mismatch), the status is `fail_schema_contract`
   (fail-closed).
3. If the reconstruction completes but any count cannot exactly match expected
   (P4H≠73, P4I≠73, or P4J≠333), the status is
   `no_go_exact_overlap_resolution_unavailable`.
4. If the reconstruction completes with all counts matching but
   `locked_cross_source_reservoir_count < 80`, the status is
   `no_go_locked_cross_source_reservoir_insufficient`.
5. If the reconstruction completes with all counts matching and
   `locked_cross_source_reservoir_count >= 80`, the status is
   `cross_source_locked_reservoir_ready_for_locked_p4_validation_design`. This
   authorizes only designing a later locked-denominator validation phase; it
   does not run any scheduler or validation.

## Public artifact contract

Required aggregate-only record tables (records-only; no dynamic dicts):

- `source_run_records`
- `reconstruction_records`
- `overlap_records`
- `stop_go_records`
- `gate_records`
- `private_manifest_records`
- `failure_category_count_records`
- `framing`
- `forbidden_scan`

No canonical keys, raw keys, row IDs, repo URLs, paths, queries, gold files,
candidate lists, snippets, private exact-key hashes, or private path hashes
are serialized. The `manifest_hash` in `private_manifest_records` is a
provenance-only file-level integrity hash. `exact_keys_publicly_serialized=false`.

## Workflow

The manual workflow
`bea-v1-p4k-exact-overlap-resolution-locked-reservoir-audit.yml` runs only via
`workflow_dispatch` and accepts `enable_external_benchmark_network`. It builds
the OpenLocus release CLI, runs self-tests, regenerates FD1 private
decomposition under `/tmp`, validates the 239/86040 replay, runs the P4K
exact overlap resolution reconstruction, validates the report fail-closed,
and uploads the aggregate report. Private reconstruction JSONL/key manifests
are written under `/tmp` only and are never uploaded. The workflow uses no
model/provider secrets. Private directories use `/tmp`, not `$RUNNER_TEMP`;
only the final public report is staged at `$RUNNER_TEMP` for upload. A
prevalidation artifact is uploaded on failure for diagnostics.

## Local validation

```text
python3 -m py_compile eval/bea_v1_p4k_exact_overlap_resolution_locked_reservoir_audit.py  => PASS
python3 eval/bea_v1_p4k_exact_overlap_resolution_locked_reservoir_audit.py --self-test  => PASS (106/106 checks)
python3 eval/bea_v1_p4k_exact_overlap_resolution_locked_reservoir_audit.py \
  --out artifacts/bea_v1_p4k_exact_overlap_resolution_locked_reservoir_audit/bea_v1_p4k_exact_overlap_resolution_locked_reservoir_audit_report.json  => PASS
  (default no-network status: unavailable_with_reason,
   forbidden_scan=pass, locked_cross_source_reservoir_count=0,
   exact_overlap_resolution_attempted=false,
   self_test_checks_total=106, self_test_checks_passed=106)
```

## CI result

Manual network-enabled CI run `28151914531` completed green in 1h50m01s.
The public artifact status is
`cross_source_locked_reservoir_ready_for_locked_p4_validation_design`.

P4K successfully reconstructed the exact selected raw-key sets for P4H, P4I,
and P4J using FD1 private replay under `/tmp`: P4H `73/73`, P4I `73/73`, and
P4J `333/333` with the committed split `61` Python + `272` non-Python. Exact
overlap showed that all 61 P4J Python rows overlapped the P4H/P4I Python-frame
reservoir; after subtracting overlap, the locked cross-source reservoir is
`272/80`, entirely from the non-Python cross-source frame.

Aggregate CI metrics:

- `status=cross_source_locked_reservoir_ready_for_locked_p4_validation_design`
- `locked_cross_source_reservoir_count=272`
- `non_python_locked_reservoir_count=272`
- `python_locked_reservoir_count=0`
- `p4h_reconstructed_denominator_count=73`
- `p4i_reconstructed_reservoir_count=73`
- `p4j_reconstructed_upper_bound_count=333`
- `p4j_reconstructed_python_count=61`
- `p4j_reconstructed_non_python_count=272`
- `p4j_overlap_with_p4h_count=61`
- `p4j_overlap_with_p4i_count=61`
- `locked_p4_validation_design_authorized=true` only inside
  `stop_go_records`
- `scheduler_validation_authorized=false`, `locked_p4_validation_executed=false`,
  `frozen_p4_rerun_authorized=false`, `p5_authorized=false`, and
  `v1_a_authorized=false`
- `self_test_checks_total=106`, `self_test_checks_passed=106`
- `forbidden_scan.status=pass`

This resolves the P4J unqualified-reservoir blocker and authorizes only the
design of a subsequent locked-denominator P4 validation phase. P4K itself did
not run scheduler arms and does not authorize P5, BEA-v1-A, runtime promotion,
method-winner claims, frozen P4 rerun, or broad retrieval expansion.

## Caveats

- P4K is a denominator/source audit only. It is not a benchmark/leaderboard,
  default-policy, method-winner, runtime-promotion, downstream-value, P5,
  BEA-v1-A, scheduler-validation, retrieval-expansion, selector/reranker,
  frozen-P4-validation, frozen-P4-rerun, or runtime/default-promotion
  authorization claim.
- `cross_source_locked_reservoir_ready_for_locked_p4_validation_design` does NOT
  authorize frozen P4 rerun (`frozen_p4_rerun_authorized=false`) or execute
  frozen/locked P4 validation (`frozen_p4_validation_executed=false`,
  `locked_p4_validation_executed=false`); it authorizes only designing a later
  locked-denominator validation phase.
- The reconstruction re-runs the same deterministic scans. If source ordering
  or baseline results drift between the original P4H/P4I/P4J runs and the P4K
  reconstruction, counts may not match, yielding
  `no_go_exact_overlap_resolution_unavailable`.
- P4H and P4I reconstruction share the same Python-frame scan (same key set)
  because both scanned the same Python frame with the same classifier.
- Gold/private labels are used only for evaluation/scoring file-miss.
- Latency is not measured or used at all (denominator audit, not a scheduler).
