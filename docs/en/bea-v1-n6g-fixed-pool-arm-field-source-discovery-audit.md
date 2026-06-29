# BEA-v1-N6G Fixed-Pool Arm-Field Source Discovery Audit

Date: 2026-06-28

BEA-v1-N6G is the read-only public source discovery audit authorized by N6F. It looks for an exact committed public source for the 160 required fixed-pool arm outcome rows: 40 fixed cases × four exact N6 arms × 14 bucket-only public fields. It does not read or write `.openlocus/`, run retrieval, rerun N6/N3/N2/P4L, generate or materialize rows, execute selectors/rerankers, run counterfactuals, change policy/runtime/defaults, or authorize P5/BEA-v1-A.

## Result

```text
status: no_go_n6g_candidate_sources_inexact_or_aggregate_only
self-test: 18 / 18
forbidden scan: pass
required public rows: 160
covered exact public rows: 0
covered exact arms: 0
exact public source found: false
fixed-pool route closed: true
```

## Candidate source inventory

N6G audits committed public N6, N6F, N5, N4, N3, and N2 artifacts:

- N6 has empty `per_case_arm_outcome_records` and no exact public arm mappings.
- N6F is design-only and defines the required schema, but contains no materialized rows.
- N5 is a contract/preflight artifact, not an outcome source.
- N4 and N2 are per-case artifacts, not per-case-per-arm exact outcome sources.
- N3 has 160 per-case analogue rows, but the arm names and semantics are not exact N6 arms. It is therefore `analogue_only_not_exact` and unusable for N6 materialization.

## Per-arm discovery

For each exact N6 arm, N6G records N3 as the best candidate but marks it inexact:

- `baseline_n2_order` → N3 analogue `frozen_p4_order`
- `extra_depth_promote_before_primary_prefix_4` → N3 analogue `early_extra_depth_quota_3`
- `bounded_interleave_primary2_extra1` → N3 analogue `fixed_interleave_2_primary_1_extra_after_4`
- `late_extra_depth_demote_after_primary_prefix_8` → N3 analogue `bounded_promotion_after_primary_prefix_4_3`

All four exact arms have `exact_source_found_bool=false` and `found_exact_public_row_count=0`.

## Closure

The fixed-pool route is closed until an exact public 160-row arm-outcome source exists. N6G does not authorize N6H, materialization, generation, N6 rerun, private reads, retrieval/reruns, selector/reranker execution, counterfactuals, P5, BEA-v1-A, runtime/default changes, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n6g_fixed_pool_arm_field_source_discovery_audit.py`
- Report: `artifacts/bea_v1_n6g_fixed_pool_arm_field_source_discovery_audit/bea_v1_n6g_fixed_pool_arm_field_source_discovery_audit_report.json`
