# BEA-v1-N6XR Explicit Bounded Candidate-Pool Recapture Smoke

Date: 2026-06-28

BEA-v1-N6XR is an explicitly bounded candidate-pool recapture smoke after N6G closed the public-source route. It is a fail-closed preflight: it checks whether the 40 fixed N4/N5 cases can be recaptured locally without private reads, retrieval, network access, full P4L reconstruction, selector/reranker execution, counterfactuals, policy/runtime changes, or candidate-pool generation/materialization.

## Result

```text
status: no_go_n6xr_requires_full_rerun_or_unavailable_mapping
self-test: 19 / 19
forbidden scan: pass
N4 case count: 40
N5 arm count: 4
bounded replay command identified: false
public arm outcome rows written: 0
N7 authorized: false
```

## Why the smoke stops before execution

N6XR does not find a bounded local recapture path. The public N4 case identifiers are positional over N2 sanitized rows; no raw-record join key is present. Public artifacts do not contain candidate pools, raw ranks, or raw order fields. The required N2-to-raw mapping and P4L private reconstruction are unavailable locally under the authorized public-only boundary.

The smallest replay route would require full P4L reconstruction over the locked 272-record denominator, including network access, repository clones, OpenLocus baseline retrieval, and full rerun scope. That is outside the N6XR bounded 40-case smoke authorization.

## Records emitted

The artifact records:

- input artifacts N4/N5/N6/N6F/N6G with expected statuses;
- bounded replay preflight over 40 cases and four arms;
- mapping unavailability for positional case ids and missing raw join keys;
- a private inventory summary that does not read or list private files;
- replay cost boundary showing full P4L reconstruction would be required;
- canary recapture not executed;
- zero private/public/candidate-pool rows written;
- empty `public_arm_outcome_records`;
- four arms marked `not_evaluated_no_candidate_pools`.

## Decision

N6XR closes before execution. It does not say the method failed; it says the data surface cannot be reconstructed within the bounded authorization. The next allowed phase is `none_until_bounded_replay_path_or_exact_public_160_row_source_exists`. N6XR does not authorize N7, N6 rerun, full rerun, retrieval, private reads, candidate-pool generation/materialization, selector/reranker execution, counterfactuals, P5, BEA-v1-A, runtime/default changes, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n6xr_explicit_bounded_candidate_pool_recapture_smoke.py`
- Report: `artifacts/bea_v1_n6xr_explicit_bounded_candidate_pool_recapture_smoke/bea_v1_n6xr_explicit_bounded_candidate_pool_recapture_smoke_report.json`
