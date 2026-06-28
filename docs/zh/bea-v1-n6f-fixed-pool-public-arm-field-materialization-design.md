# BEA-v1-N6F Fixed-Pool Public Arm-Field Materialization Design

日期：2026-06-28

BEA-v1-N6F 是 N6 以 `no_go_n6_public_fixed_pool_arm_fields_insufficient` 停止后的 final design/closure phase。它定义未来 N6 rerun/materialization 之前所需的 scanner-safe public row schema。本阶段不做 materialization，不生成字段，不运行 retrieval，不 rerun，不执行 selector/reranker，不做 counterfactual，不改 policy/runtime，也不读取 private。

## 结果

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

未来 materialization 必须为每个 `anonymous_case_id × arm_bucket` 组合发布一条 scanner-safe public row：40 个固定 N5/N4 cases × 4 个 exact N6 arms，共 160 rows。

每行必须只包含 bucket-only public fields：

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

该 schema 禁止 raw ranks、candidate paths/lists、raw order、task/repo identifiers、snippets、hashes、scores、provider payloads、raw diffs 和任何 source-linkable values。

## 为什么需要该设计

N6 已确认 40-case set 一致，且 N5 授权了四个 fixed-pool arms，但这些 exact arms 的 exact public per-case arm outcomes 不存在。N3 有 analogue arms，但名称和语义不同于 N5/N6 arms，因此不能作为 N6 results 复用。

## 决策

N6F 只授权 **BEA-v1-N6G Fixed-Pool Arm-Field Source Discovery Audit**，且范围仅为 read-only public source discovery。它不授权 N6 rerun、field generation/materialization、private reads、retrieval/reruns、selector/reranker execution、counterfactuals、policy/runtime changes、P5、BEA-v1-A、method-winner 声明或 downstream-value 声明。

## Artifact

- Script: `eval/bea_v1_n6f_fixed_pool_public_arm_field_materialization_design.py`
- Report: `artifacts/bea_v1_n6f_fixed_pool_public_arm_field_materialization_design/bea_v1_n6f_fixed_pool_public_arm_field_materialization_design_report.json`
