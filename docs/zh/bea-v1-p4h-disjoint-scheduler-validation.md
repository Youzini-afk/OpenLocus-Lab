# BEA-v1-P4H：不相交调度器验证

日期：2026-06-24。BEA-v1-P4H 在不相交 raw external heldout 文件缺失分母上，
验证 checkpoint `f0e99ca` 中冻结的 BEA-v1-P4 延迟感知检索动作调度器。它是
经验验证和 rank-budget audit，不是控制面变更。

> `claim_level = bea_v1_p4h_disjoint_scheduler_validation_only`。
> `provider_calls_made=false`、`gold_labels_used_for_query_construction=false`、
> `gold_labels_used_for_policy=false`、`latency_in_candidate_relevance=false`、
> `query_anchors_used_in_p4_arm=false`、`selector_or_reranker_changed=false`
> 均为 binding。

## 绑定上下文

- BEA-v1-P4 checkpoint：`f0e99ca`；status 为
  `bea_v1_p4_latency_aware_retrieval_scheduler_pass`。
- P4 观测结果：baseline 32/119，P2 depth-only 59/119，P3 reference 58/119，
  P4 frozen scheduler 56/119；P4 pool 为 baseline 的 2.056350×，latency 为
  1.749695×，相对 P3 latency 降低 19.3806%，hard-cap violations 为 0。
- P4 的 selector relevance 仍未解决：mean first reachable gold rank 为
  25.625，48 条记录超出 budget。
- P4H 复用同一个冻结 P4 检索动作调度器。它不调阈值、不添加 query anchor、
  不扩大检索、不修改 selector/reranker，也不把 latency 用于 candidate relevance
  scoring。

## 分母构造

- P4H 分母**不是** FD1 `gold_file_absent` 的尾部。已提交的 FD1 artifact 中
  `gold_file_absent` 正好只有 119 条记录，因此取前 119 条之后的记录会得到空
  heldout 分母。
- P4H 改为执行 raw external 不相交扫描，窗口明确位于既有 BEA-4 / BEA-5 /
  P1-P4 caps 之后：
  - ContextBench：`offset=480`，`limit=240`。
  - RepoQA：`offset=240`，`limit=120`。
- 扫描按稳定 raw 顺序进行。对每条 raw row，P4H clone repository，只运行
  `current_bea_candidate_pool_replay`，并且仅当 baseline/current candidate pool
  未触达 gold file（`gold_file_available=false`）时才纳入分母。
- 分母在运行 P2/P3/P4 treatment arm 之前构造。扫描得到的 baseline 结果会缓存，
  并作为已选分母记录的第 1 个 arm 复用。
- 如果可能，扫描在达到 80 条目标/最小分母记录后停止；80 条 gate 不降低。如果
  raw 窗口扫描完成后仍不足 80 条，P4H fail closed，status 为
  `no_go_p4h_insufficient_denominator`。
- 公开 artifact 只发布按 source、benchmark、raw window 聚合的 attempt/yield/
  exclusion 计数。私有 per-record key、row index、query、repository URL、gold
  path、candidate path、manifest 和 trace 只写入 `/tmp`。

## 检索调度器 arm（4 个，固定）

1. `current_bea_candidate_pool_replay` —— baseline 当前 BEA candidate pool。
2. `p2_depth_only_reference` —— P2 depth-only reference。
3. `p3_constrained_depth_policy_reference` —— P3 constrained policy reference。
4. `p4_latency_aware_action_scheduler_frozen` —— 冻结 P4 treatment scheduler。

treatment 名称刻意区别于 P4，用于明确这是 heldout 上的冻结复制验证。

## 硬性有效性 gate

- FD1/private replay 验证与 P4 相同的 239 / 86040 基础行为，用于 provenance；
  但 FD1 记录不复用为 P4H 分母。
- Raw external 分母扫描已执行，既有 raw windows 已排除，heldout 分母至少包含
  80 条 file-miss 记录。
- 私有 scheduler rows 等于 `denominator_count × 4`。
- `forbidden_scan.status=pass`。
- 无 provider call。
- gold/private label 不用于 query 构造、scheduler policy 或 candidate ranking。
- `latency_in_candidate_relevance=false`。
- 公开 artifact 仅聚合、仅 records：无 per-record ID、路径、query、snippet、
  candidate list、gold file、私有 trace path 或私有 row payload。

## 复制 gate

P4H 只有在冻结 P4 scheduler 在 heldout 分母上满足所有 gate 时才通过：

1. **Reach preservation**：P4H newly reachable 至少为 P2 depth-only newly
   reachable 的 75%，或达到按分母缩放的绝对下限；并且至少为 P3 reference
   newly reachable 的 90%（除非 P3 本身漂移/失败）。
2. **Latency**：P4H latency multiplier ≤ 2.0× baseline，且比 P3 reference
   latency 至少低 10%。
3. **Pool/cap**：P4H pool multiplier ≤ 4.0× baseline，hard-cap violations 为 0。
4. **Action reduction**：P4H 相比 P3 有实质更少的检索动作（mean extra-depth
   actions 至少少 25%，或按分母缩放后至少 20 条记录 action 更少）。
5. **Subgroup guard**：任何 `n >= 20` 的 source/benchmark subgroup，P4H 至少
   保留 P2 depth gain 的 50%，且仍满足 latency/pool gate。

## Rank-budget audit

P4H 还输出 `rank_budget_audit_records`，包含：

- `rank_budget_bottleneck_confirmed`
- `selector_phase_justified`

如果 mean first reachable gold rank > 5，或按分母缩放后至少 25 条记录仍超出
budget，则确认 bottleneck。该 audit 本身不会使 scheduler 失败；它只在 P4H
通过时为可能的后续 selector 阶段提供依据。

## 状态

- `bea_v1_p4h_disjoint_scheduler_validation_pass`
- `no_go_p4h_insufficient_denominator`
- `no_go_p4h_replay_mismatch`
- `no_go_p4h_reach_not_replicated`
- `no_go_p4h_latency_not_fixed`
- `no_go_p4h_cost_exceeded`
- `no_go_p4h_policy_degenerate`
- `unavailable_with_reason`
- `fail_forbidden_scan` / `fail_schema_contract`

`fail_*` 是 schema/privacy 失败。在启用网络的真实运行中，
`no_go_p4h_replay_mismatch` 不是 CI-valid 结果，因为它表示 replay/schema 或前置
条件不匹配。

## 公开 artifact 契约

必需的仅聚合 record 表：

- `source_run_records`
- `denominator_records`
- `denominator_scan_records`
- `arm_reach_records`
- `arm_delta_records`
- `arm_cost_records`
- `arm_action_records`
- `channel_action_records`
- `scheduler_stop_reason_records`
- `latency_decomposition_records`
- `efficiency_records`
- `reach_bucket_records`
- `rank_band_records`
- `cost_safety_records`
- `subgroup_safety_records`
- `rank_budget_audit_records`
- `stop_go_records`
- `gate_records`
- `private_manifest_records`
- `failure_category_count_records`
- `framing`
- `forbidden_scan`

不序列化动态 per-record detail、公开私有 hash 或私有路径。

## Workflow

手动 workflow `bea-v1-p4h-disjoint-scheduler-validation.yml` 仅通过
`workflow_dispatch` 运行，并接受 `enable_external_benchmark_network`。它构建
OpenLocus release CLI、运行 self-test、在 `/tmp` 下重新生成 FD1 private
decomposition、验证 FD1 replay、运行 P4H raw external 不相交扫描和 scheduler
validation、fail-closed 验证报告，如存在则上传 prevalidation 聚合报告，并上传
最终聚合报告。私有 JSONL/JSON trace 不上传。

## 本地验证

```text
python3 -m py_compile eval/bea_v1_p4h_disjoint_scheduler_validation.py  => PASS
python3 eval/bea_v1_p4h_disjoint_scheduler_validation.py --self-test  => PASS (58/58 checks)
python3 eval/bea_v1_p4h_disjoint_scheduler_validation.py \
  --out artifacts/bea_v1_p4h_disjoint_scheduler_validation/bea_v1_p4h_disjoint_scheduler_validation_report.json  => PASS
  (默认无网络 status: unavailable_with_reason,
   stop_go_decision: no_go_p4h_replay_mismatch,
   forbidden_scan=pass, denominator_count=0,
   raw_denominator_scan_attempted=false,
   self_test_checks_total=58, self_test_checks_passed=58)
```

CI 结果在手动网络 workflow 运行前保持 pending。

## 限制

- P4H 仅为 validation/audit。它不是 benchmark/leaderboard、default-policy、
  method-winner、runtime-promotion、downstream-value 或 v1-A 授权声明。
- 它不实现 selector/reranker 变更。
- gold/private label 仅用于评估/评分 reach。
- latency 只作为 scheduling/cost 信号，绝不用于 candidate relevance。
