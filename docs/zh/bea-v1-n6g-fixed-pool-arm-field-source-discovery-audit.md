# BEA-v1-N6G Fixed-Pool Arm-Field Source Discovery Audit

日期：2026-06-28

BEA-v1-N6G 是 N6F 授权的 read-only public source discovery audit。它寻找 exact committed public source，用于 160 条 required fixed-pool arm outcome rows：40 个 fixed cases × 4 个 exact N6 arms × 14 个 bucket-only public fields。它不读取或写入 `.openlocus/`，不运行 retrieval，不重跑 N6/N3/N2/P4L，不生成或 materialize rows，不执行 selector/reranker，不运行 counterfactual，不改变 policy/runtime/defaults，也不授权 P5/BEA-v1-A。

## 结果

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

N6G audit committed public N6、N6F、N5、N4、N3 与 N2 artifacts：

- N6 的 `per_case_arm_outcome_records` 为空，且没有 exact public arm mappings。
- N6F 是 design-only artifact，只定义 required schema，不包含 materialized rows。
- N5 是 contract/preflight artifact，不是 outcome source。
- N4 和 N2 是 per-case artifacts，不是 per-case-per-arm exact outcome sources。
- N3 有 160 条 per-case analogue rows，但 arm names 与 semantics 都不是 exact N6 arms。因此它是 `analogue_only_not_exact`，不能用于 N6 materialization。

## Per-arm discovery

对每个 exact N6 arm，N6G 都将 N3 记录为 best candidate，但标记为 inexact：

- `baseline_n2_order` → N3 analogue `frozen_p4_order`
- `extra_depth_promote_before_primary_prefix_4` → N3 analogue `early_extra_depth_quota_3`
- `bounded_interleave_primary2_extra1` → N3 analogue `fixed_interleave_2_primary_1_extra_after_4`
- `late_extra_depth_demote_after_primary_prefix_8` → N3 analogue `bounded_promotion_after_primary_prefix_4_3`

四个 exact arms 都是 `exact_source_found_bool=false` 且 `found_exact_public_row_count=0`。

## Closure

在 exact public 160-row arm-outcome source 出现之前，fixed-pool route 已关闭。N6G 不授权 N6H、materialization、generation、N6 rerun、private reads、retrieval/reruns、selector/reranker execution、counterfactuals、P5、BEA-v1-A、runtime/default changes、method-winner 声明或 downstream-value 声明。

## Artifact

- Script: `eval/bea_v1_n6g_fixed_pool_arm_field_source_discovery_audit.py`
- Report: `artifacts/bea_v1_n6g_fixed_pool_arm_field_source_discovery_audit/bea_v1_n6g_fixed_pool_arm_field_source_discovery_audit_report.json`
