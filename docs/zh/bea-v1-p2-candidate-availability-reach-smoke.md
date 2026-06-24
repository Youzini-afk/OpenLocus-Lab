# BEA-v1-P2: 候选可用性 / 检索可达性冒烟

日期：2026-06-23（BEA-v1-P2 —— BEA v1 Hierarchical Actionable Evidence
Acquisition 的第二阶段。在 BEA-v1-P1 结果 checkpoint `d96e860` 之后
运行。P1 解析了已验证的 FD1 私有重放（86040 行 / 239 分组）并拒绝了
仅 selector 的 BEA-v1-A：`gold_file_absent` 分母=119，file-selector
下界可恢复计数=1，检索可用性 rate=0.991597。Selector 无法恢复缺失的
gold 文件。P2 测试候选可用性 / 检索可达性，而非选择。它不是 BEA v0.4
修复，不是 FD2-B / FD2-C，不是 P4 / P5，不是 v0.31 / v0.32 调参，不是
B16-K，不是 selector / acquisition 阶段，不是 dense/graph/QuIVer 质量
混合，也不是 P1 重放。）

> `claim_level = bea_v1_p2_candidate_availability_reach_smoke_only`。
> 所有 no-claim / no-runtime-change flag 为 false。`provider_calls_made=false`
> 是 binding。`role_proxy_used=false` 与
> `gold_labels_used_for_query_construction=false` 是 binding。

## 绑定上下文

- BEA-v1-P1 结果 checkpoint：`d96e860`；status
  `no_go_retrieval_availability_limit`。P1 解析了已验证的 FD1 私有重放
  （86040 行 / 239 分组），发现 `gold_file_absent` 分母=119，
  file-selector 下界可恢复计数=1，检索可用性 rate=0.991597。
- P2 在 FD1 `gold_file_absent` 分母（精确 119 个 record）上运行确定性、
  无 provider、网络启用的检索可达性冒烟。它比较当前 BEA candidate pool
  与小型 runtime-clean 扩展 arm，以确定 gold 文件是否在选择工作之前变得
  可用。

## 检索可达性 arm（4）

1. `current_bea_candidate_pool_replay` —— 当前 BEA runtime-clean 检索
   pool（bm25/regex/symbol + RRF/derived RRF）。锚定 v1-P1 baseline。
2. `expanded_pool_more_depth_same_methods` —— 相同方法，更大的 candidate
   生成深度（4x）。测试截断 vs 真实检索缺失。
3. `expanded_pool_query_anchor_variants` —— 仅从公开任务文本构建的
   runtime-clean query 变体（标识符 token、路径类 token、符号类 token、
   import/package token、camel/snake 拆分）。无 gold 路径、私有标签、
   role/support proxy 或事后调参。
4. `expanded_pool_depth_plus_query_anchor` —— 深度扩展 + query-anchor
   变体组合 arm。

## 指标（在 119 分母上）

- `gold_file_available_any_pool` —— gold 文件在任一 arm 的 pool 中找到。
- `gold_file_available_at_50/100/200` —— gold 文件在 rank 50/100/200 内
  找到。
- `first_gold_file_rank_mean/median` —— 首个 gold-file rank 的均值/中位数。
- `candidate_pool_size_mean` —— candidate pool 大小均值。
- `retrieval_latency_mean_seconds` —— 检索延迟均值。
- `duplicate_file_rate` —— 重复文件率。
- `newly_reachable_count` —— gold 在扩展 arm 中可用但在 baseline 中不可用
  的 record。
- `still_unavailable_count` —— gold 在任何 arm 中都未找到的 record。

## 回到 v1-A 的 stop / go

仅当以下全部满足时才重新开启 BEA-v1-A：

1. 119 分母上新可达的 gold 文件是 material 的：
   `newly_available_count >= 25` 或 `availability_lift >= 0.20`，其中
   `availability_lift = newly_reachable_count / 119`（不是除以很小的
   baseline-available count）。
2. 扩展不需要 pool/latency 爆炸：pool 大小 <= 4x baseline 且
   latency <= 2x baseline。
3. 至少一个 runtime-clean 机制主导（depth、query 或组合 arm 有
   `newly_reachable > 0`）。
4. 运行时无 gold/私有标签（binding flag
   `gold_labels_used_for_query_construction=false`）。
5. 扩展 pool 留下 selector/packer 问题：gold 可达但通常低于最终 budget
  （以 `first_gold_file_rank_mean > budget` 代理）。

否则 No-Go 并转向检索层设计或 span/stopping 上限的 trace 收集。

## 公开 artifact 契约

仅聚合、仅 records。无公开 record ID、路径、query、snippet、gold 文件、
candidate 列表、per-record rank、私有 trace 路径或私有 row payload。

必需公开表（仅 records，natural key）：

- `source_run_records`：`(source_phase, source_ci_run_id)` —— FD1 + P1
  binding context，含 replay-artifact 验证字段。
- `denominator_records`：`(source_phase, benchmark)` —— 每 (sp, bm) 分母
  计数。
- `arm_reach_records`：`(arm_name,)` —— 每 arm 聚合可达性指标。
- `arm_delta_records`：`(arm_name,)` —— 每 arm 相对 baseline 的 delta。
- `reach_bucket_records`：`(arm_name, reach_bucket)` —— 每 (arm, bucket) 计数。
- `rank_band_records`：`(arm_name, rank_band)` —— 每 (arm, band) 计数。
- `cost_safety_records`：`(cost_safety_axis,)` —— pool/latency 倍率安全检查。
- `stop_go_records`：`(stop_go_decision,)` —— v1-A 重开决策。
- `gate_records`：`(gate,)` —— fail-closed gate。
- `private_manifest_records`：`(manifest_name,)` —— FD1 private replay 和
  BEA-v1-P2 private reach trace manifest；路径绝不序列化。
- `failure_category_count_records`：`(failure_category,)`。
- `framing`、`forbidden_scan`。

## CI gate（fail-closed）

手动 CI workflow `bea-v1-p2-candidate-availability-reach.yml` 仅在
`workflow_dispatch` 且 `enable_external_benchmark_network=true` 时运行。
它重新生成 FD1 私有分解，验证 replay 报告，重放 P2 检索冒烟
（网络 + OpenLocus binary，无 provider secret），并仅上传聚合报告。私有
JSONL/JSON 文件绝不上传。

Fail-closed 验证：

- `status` 属于：`bea_v1_p2_retrieval_reach_pass` |
  `no_go_retrieval_reach_insufficient` |
  `no_go_retrieval_reach_latency_or_pool_cost` |
  `no_go_replay_mismatch`。
- FD1 replay 匹配 239 / 86040。
- 分母精确 119。
- real-run status 下 `fd1_private_decomposition_parsed=true` 且
  `replay_artifact_validated=true`。
- `provider_calls_made=false`。
- `gold_labels_used_for_query_construction=false`。
- `forbidden_scan.status=pass`。
- 仅 records 公开形状；natural-key 唯一性。
- 无 forbidden 顶层字段。

## 状态

- `bea_v1_p2_retrieval_reach_pass` —— 新可用 material，成本安全 ok，
  runtime-clean 机制主导，selector 问题仍存在。
- `no_go_retrieval_reach_insufficient` —— 新可用低于阈值或无 runtime-clean
  机制主导。
- `no_go_retrieval_reach_latency_or_pool_cost` —— pool 或 latency 倍率超限。
- `no_go_replay_mismatch` —— FD1 replay/分母不匹配或检索可达性未执行。
- `unavailable_with_reason` —— 默认无网络 artifact。
- `fail_forbidden_scan` / `fail_schema_contract` —— schema/leak 失败。

## 验证

```text
python3 -m py_compile eval/bea_v1_p2_candidate_availability_reach_smoke.py  => PASS
python3 eval/bea_v1_p2_candidate_availability_reach_smoke.py --self-test  => PASS (274/274 checks)
python3 eval/bea_v1_p2_candidate_availability_reach_smoke.py \
  --out artifacts/bea_v1_p2_candidate_availability_reach/bea_v1_p2_candidate_availability_reach_smoke_report.json  => PASS
  (默认无网络 status: unavailable_with_reason,
   stop_go_decision: no_go_replay_mismatch,
   forbidden_scan=pass, denominator_count=0,
   provider_calls_made=false,
   self_test_checks_total=274, self_test_checks_passed=274)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

## Manual CI 结果

CI 待定 —— 手动 CI workflow 必须以 `enable_external_benchmark_network=true`
触发，以重新生成 FD1 私有分解、验证 replay 报告并重放 P2 检索可达性冒烟。
在此之前，committed artifact 保持诚实的 `unavailable_with_reason` 默认。

## 限制

- BEA-v1-P2 仅 eval/diagnostic。不是 benchmark/leaderboard/
  performance/method-winner/calibration/promotion/default/runtime/
  EvidenceCore/downstream-value 声明。
- Gold/私有标签仅用于评估/评分可达性，绝不用于构造 query/candidate。
  `gold_labels_used_for_query_construction=false` 是 binding。
- P2 evaluator 在默认 artifact 生成期间不运行检索/provider call。CI workflow
  通过子进程重放检索冒烟；evaluator 读取结果。
- 私有 per-record trace（query 变体、candidate 列表、gold-file 匹配标签、
  reach bucket、latency/pool-size）仅位于 `/tmp` 且绝不上传。
- BEA-v1-P2 不是 BEA v0.4 修复、不是 FD2-B、不是 FD2-C、不是 P4、
  不是 P5、不是 v0.31/v0.32 调参、不是 B16-K、不是 dense/graph/QuIVer
  质量混合、不是 selector/packer runtime 变更。
