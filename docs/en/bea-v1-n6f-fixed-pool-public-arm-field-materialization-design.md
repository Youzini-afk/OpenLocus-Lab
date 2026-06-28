# BEA-v1-N6F Fixed-Pool Public Arm-Field Materialization Design

Date: 2026-06-28

BEA-v1-N6F is a final design/closure phase after N6 stopped with `no_go_n6_public_fixed_pool_arm_fields_insufficient`. It defines the scanner-safe public row schema required before any future N6 rerun/materialization can be considered. It performs no materialization, no generation, no retrieval, no rerun, no selector/reranker execution, no counterfactual, no policy/runtime change, and no private read.

## Result

```text
status: fixed_pool_public_arm_field_materialization_design_pass
self-test: 16 / 16
forbidden scan: pass
required public rows: 160
case count: 40
arm count: 4
private reads / execution: 0
N6G source discovery audit authorized: true
```

## Required public arm outcome row

Future materialization must publish one scanner-safe public row for every `anonymous_case_id × arm_bucket` pair: 40 fixed N5/N4 cases times four exact N6 arms, for 160 rows.

Each row must contain exactly bucket-only public fields:

- `anonymous_public_arm_outcome_id`
- `anonymous_case_bucket`
- `arm_bucket`
- `fixed_pool_case_set_bucket`
- `arm_semantics_exact_match_bool`
- `candidate_pool_changed_bool=false`
- `new_retrieval_used_bool=false`
- `selector_or_reranker_used_bool=false`
- `top10_recovery_bucket`
- `top20_recovery_bucket`
- `rank_shift_bucket`
- `case_regression_bucket`
- `hard_cap_bucket`
- `outcome_materialized_bool`

The schema forbids raw ranks, candidate paths/lists, raw order, task/repo identifiers, snippets, hashes, scores, provider payloads, raw diffs, and source-linkable values.

## Why this design is needed

N6 verified that the 40-case set is consistent and that N5 authorized four fixed-pool arms, but exact public per-case arm outcomes do not exist for those arms. N3 has analogue arms, but their names and semantics differ from N5/N6 arms, so they cannot be reused as N6 results.

## Decision

N6F authorizes only **BEA-v1-N6G Fixed-Pool Arm-Field Source Discovery Audit** for read-only public source discovery. It does not authorize N6 rerun, field generation/materialization, private reads, retrieval/reruns, selector/reranker execution, counterfactuals, policy/runtime changes, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n6f_fixed_pool_public_arm_field_materialization_design.py`
- Report: `artifacts/bea_v1_n6f_fixed_pool_public_arm_field_materialization_design/bea_v1_n6f_fixed_pool_public_arm_field_materialization_design_report.json`
