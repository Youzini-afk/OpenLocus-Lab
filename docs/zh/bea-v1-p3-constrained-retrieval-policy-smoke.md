# BEA-v1-P3: 受约束检索策略冒烟

日期：2026-06-24（BEA-v1-P3 —— BEA v1 Hierarchical Actionable Evidence
Acquisition 的第三阶段。在 BEA-v1-P2 结果 checkpoint `930dd48` 之后
运行。P2 在 FD1 `gold_file_absent` 分母（119 个 record）上运行候选
可用性 / 检索可达性冒烟，发现 runtime-clean retrieval expansion 能找回
额外 gold 文件，但 naive broad expansion 成本过高：baseline 达到
32/119；depth-only 达到 59/119（新增 27，pool 3.41×，latency
1.18×）；query-anchor 达到 60/119（新增 28）但成本越界；combined
depth+query 达到 81/119（新增 49），但违反 pool/latency safety
（pool 10.13×，latency 3.89×）。P2 status 为
`no_go_retrieval_reach_latency_or_pool_cost`。P3 是 BEA v1 中第一个真实
retrieval-action policy，不是 selector / default / promotion。它不是
BEA v0.4 修复，不是 FD2-B / FD2-C，不是 P4 / P5，不是 v0.31 / v0.32
调参，不是 B16-K，不是 selector / acquisition 阶段，不是
dense/graph/QuIVer 质量混合，不是 latency-in-relevance scoring，也不
是 P1 或 P2 重放。）

> `claim_level = bea_v1_p3_constrained_retrieval_policy_smoke_only`。
> 所有 no-claim / no-runtime-change flag 为 false。`provider_calls_made=false`
> 是 binding。`role_proxy_used=false`、
> `gold_labels_used_for_query_construction=false`、
> `gold_labels_used_for_policy=false`、
> `latency_in_candidate_relevance=false`、
> `query_anchors_used_in_p3_arm=false` 是 binding。

## 绑定上下文

- BEA-v1-P2 结果 checkpoint：`930dd48`；status
  `no_go_retrieval_reach_latency_or_pool_cost`。P2 显示 runtime-clean
  retrieval expansion 能额外找回 27–49 个 gold 文件，但 naive broad
  expansion 成本过高（combined arm pool 10.13×，latency 3.89×）。
- BEA-v1-P1 结果 checkpoint：`d96e860`；status
  `no_go_retrieval_availability_limit`。`gold_file_absent`
  分母=119，file-selector 下界可恢复计数=1，检索可用性 rate=0.991597。
- P3 在 FD1 `gold_file_absent` 分母（精确 119 个 record）上运行确定性、
  无 provider、网络启用的 constrained retrieval policy。它测试一个
  runtime-clean constrained retrieval scheduler 能否保留大部分 P2
  depth-only reach（59/119），同时约束 pool / latency。

## 检索策略 arm（3）

1. `current_bea_candidate_pool_replay` —— 当前 BEA runtime-clean 检索
   pool（bm25/regex/symbol + derived RRF），depth=1。锚定 v1-P1 / v1-P2
   baseline。预期 ~32/119。
2. `p2_depth_only_reference` —— 相同 P2 depth-only 扩展（depth=4，相同
   方法，无 query anchor）。仅作参考。预期 ~59/119。
3. `p3_constrained_depth_policy` —— 主 treatment。一个 runtime-clean
   constrained retrieval scheduler：从 baseline pool 出发，仅计算公开
   diagnostics，在 predeclared under-retrieval 条件下最多应用一轮额外
   depth，按 marginal new-file yield filter 合并，并在 hard candidate
   cap / unique-file cap / action budget 处停止。

## P3 策略机制（runtime-clean retrieval scheduler）

P3 arm 是 **retrieval-action policy**，不是 candidate relevance scoring。
latency 仅作为 stop / safety metric 度量，绝不作为 relevance 信号。

1. **Baseline round**：以 depth=1 收集 bm25 / literal-regex / symbol
   候选，从方法结果列表 derive RRF，去重。这是 baseline pool（复用 P2 的
   runtime-safe retrieval helpers）。
2. **Runtime-clean diagnostics**（仅公开信号；无 gold / 私有标签，无事后
   调参）：unique file count、duplicate-file rate、method agreement
   count、non-empty channels、normalized score mass / spread、query-token
   / path-token overlap。
3. **Under-retrieval 触发**：当任一 predeclared 条件成立时，应用一轮
   额外 depth（depth=4，无 query anchor —— query anchor 在 P3 主 arm
   中被禁用）：
   - unique file count < 15（低 unique file count），
   - duplicate-file rate > 0.50（高 duplicate-file rate），
   - non-empty channels ≤ 2（非空 channel 过少），
   - normalized score mass < 5.0（低 score mass）。
4. **Marginal new-file yield filter**：仅合并 extra round 中文件相对
   baseline pool 为 NEW 的候选。若 extra round 新 unique file 数 < 2，
   则跳过合并（degenerate extra round）。
5. **Stop 条件**：hard candidate cap（每 record 100，≤120）、unique-file
   cap（80）、action budget（≤1 轮额外 depth）、或 marginal new-file
   yield 低于阈值。
6. **Gold-file reach** 在最终合并 + 去重 + 截断后的 pool 上计算。Gold
   路径仅用于检查 reach，绝不用于构造 pool 或 policy。

## 指标（在 119 分母上）

- `gold_file_available_any_pool` —— gold 文件在任一 arm 的 pool 中找到。
- `gold_file_available_at_50/100/200` —— gold 文件在 rank 50/100/200 内
  找到。
- `first_gold_file_rank_mean/median` —— 首个 gold-file rank 的均值/中位数。
- `candidate_pool_size_mean` —— candidate pool 大小均值。
- `retrieval_latency_mean_seconds` —— 检索延迟均值。
- `duplicate_file_rate` —— 重复文件率。
- `newly_reachable_count` —— gold 在某 arm 中可用但在 baseline 中不可用
  的 record。
- `still_unavailable_count` —— gold 在任何 arm 中都未找到的 record。
- `pool_size_multiplier` / `latency_multiplier` —— 每 arm 相对 baseline
  的成本。
- `hard_cap_violation_count` —— P3 arm 中超过 hard candidate cap 的
  record 数。
- `newly_reachable_per_added_candidate` —— 策略效率。

## 研究成功 gate

P3 通过仅当以下全部成立：

1. **Reach preservation**：新可达 ≥ 20/119 或保留 ≥ 75% 的 P2 depth-only
   新可达（≥ 21 of +27）。
2. **Cost safety**：mean pool 倍率 ≤ 4.0× baseline；mean latency 倍率
   ≤ 2.0× baseline；hard cap violation count = 0。
3. **Policy efficiency**：`newly_reachable_per_added_candidate` 优于 P2
   combined（0.268638）且不显著差于 P2 depth-only（≥ 80% of 0.560077）。
4. **Selector relevance 仍存在**：足够多可达 gold 文件仍位于最终 budget
   之外（mean first-gold rank > 5 或 ≥ 25 个 record 的 first-gold rank
   > budget）。

## No-Go 状态

- `no_go_p3_reach_not_preserved` —— P3 未保留足够的 P2 depth-only reach。
- `no_go_p3_cost_exceeded` —— pool / latency / hard-cap safety 违反。
- `no_go_p3_policy_degenerate` —— 策略效率退化、无 runtime-clean 主导、
  或无 selector 问题残留。
- `no_go_p3_replay_mismatch` —— FD1 replay / 分母不匹配、reach drift、或
  检索策略未执行。

CI / schema / privacy 失败（`fail_forbidden_scan`、
`fail_schema_contract`）会 fail CI，不是有效研究 status。

## 硬性有效性 gate（fail-closed）

- FD1 replay 验证 239 / 86040。
- 分母精确 119。
- Baseline reach 在容差内复现（预期 32，±3）。
- P2 depth-only 参考 reach 在容差内复现（预期 59，±3）。
- P3 检索在 119 个 record 上执行。
- 私有 reach 行 = 分母 × arm = 119 × 3 = 357。
- `forbidden_scan.status=pass`。
- 无 provider call、无 gold / 私有标签用于 policy / query 构造、无
  selector / packer / default / runtime promotion、无 role proxy、
  latency 不进入 candidate relevance、P3 arm 不使用 query anchor。

## 公开 artifact 契约

仅聚合、仅 records。无公开 record ID、路径、query、snippet、gold 文件、
candidate 列表、per-record rank、私有 trace 路径或私有 row payload。

必需公开表（仅 records，natural key）：

- `source_run_records`：`(source_phase, source_ci_run_id)` —— FD1 + P1
  + P2 binding context，含 replay-artifact 验证字段与 P3 policy config
  hash。
- `denominator_records`：`(source_phase, benchmark)`。
- `arm_reach_records`：`(arm_name,)`。
- `arm_delta_records`：`(arm_name,)`。
- `arm_cost_records`：`(arm_name, cost_axis)` —— 每 arm pool / latency
  倍率 + hard-cap violation count。
- `policy_action_records`：`(policy_action,)`。
- `policy_stop_reason_records`：`(stop_reason,)`。
- `efficiency_records`：`(efficiency_axis,)` —— 每 arm
  newly_reachable_per_added_candidate vs P2 combined / depth。
- `reach_bucket_records`：`(arm_name, reach_bucket)`。
- `rank_band_records`：`(arm_name, rank_band)`。
- `cost_safety_records`：`(cost_safety_axis,)`。
- `stop_go_records`：`(stop_go_decision,)`。
- `gate_records`：`(gate,)`。
- `private_manifest_records`：`(manifest_name,)` —— FD1 private replay 与
  BEA-v1-P3 private policy trace manifest；路径绝不序列化。
- `failure_category_count_records`：`(failure_category,)`。
- `framing`、`forbidden_scan`。

## CI gate（fail-closed）

手动 CI workflow `bea-v1-p3-constrained-retrieval-policy.yml` 仅在
`workflow_dispatch` 且 `enable_external_benchmark_network=true` 时运行。
它在 `/tmp` 下（非 `$RUNNER_TEMP`）重建 FD1 私有分解，验证 replay
report，重放 P3 constrained retrieval policy 冒烟（网络 + OpenLocus
binary，无 provider secret），并仅上传聚合报告。私有 JSONL/JSON 文件
绝不上传。

Fail-closed 验证：

- `status` 属于：`bea_v1_p3_constrained_retrieval_policy_pass` |
  `no_go_p3_reach_not_preserved` | `no_go_p3_cost_exceeded` |
  `no_go_p3_policy_degenerate`。`no_go_p3_replay_mismatch` 是 replay/default
  failure status，不是 CI-valid real-run result。
- FD1 replay 匹配 239 / 86040。
- 分母精确 119。
- real-run status 下 `fd1_private_decomposition_parsed=true` 且
  `replay_artifact_validated=true`。
- `provider_calls_made=false`。
- `gold_labels_used_for_query_construction=false`。
- `gold_labels_used_for_policy=false`。
- `latency_in_candidate_relevance=false`。
- `query_anchors_used_in_p3_arm=false`。
- `forbidden_scan.status=pass`。
- 仅 records 公开形状；natural-key 唯一性。
- 无 forbidden 顶层字段。

## 状态

- `bea_v1_p3_constrained_retrieval_policy_pass` —— reach 保留、成本安全
  ok、策略效率优于 combined 且不显著差于 depth、runtime-clean 主导、
  selector 问题残留。
- `no_go_p3_reach_not_preserved` —— P3 reach 低于保留阈值。
- `no_go_p3_cost_exceeded` —— pool / latency / hard-cap safety 违反。
- `no_go_p3_policy_degenerate` —— 效率退化、无 runtime-clean 主导、或无
  selector 问题残留。
- `no_go_p3_replay_mismatch` —— FD1 replay / 分母不匹配、reach drift、
  或检索策略未执行；network enabled 时不是 CI-valid 结果。
- `unavailable_with_reason` —— 默认无网络 artifact。
- `fail_forbidden_scan` / `fail_schema_contract` —— schema/leak 失败。

## 验证

```text
python3 -m py_compile eval/bea_v1_p3_constrained_retrieval_policy_smoke.py  => PASS
python3 eval/bea_v1_p3_constrained_retrieval_policy_smoke.py --self-test  => PASS (365/365 checks)
python3 eval/bea_v1_p3_constrained_retrieval_policy_smoke.py \
  --out artifacts/bea_v1_p3_constrained_retrieval_policy/bea_v1_p3_constrained_retrieval_policy_smoke_report.json  => PASS
  (默认无网络 status: unavailable_with_reason,
   stop_go_decision: no_go_p3_replay_mismatch,
   forbidden_scan=pass, denominator_count=0,
   provider_calls_made=false,
   latency_in_candidate_relevance=false,
   query_anchors_used_in_p3_arm=false,
   self_test_checks_total=365, self_test_checks_passed=365)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

## 限制

- BEA-v1-P3 仅 eval/diagnostic。不是 benchmark/leaderboard/
  performance/method-winner/calibration/promotion/default/runtime/
  EvidenceCore/downstream-value 声明。
- Gold/私有标签仅用于评估/评分可达性，绝不用于构造 query/candidate/policy。
  `gold_labels_used_for_query_construction=false` 与
  `gold_labels_used_for_policy=false` 是 binding。
- latency 仅作为 stop / safety metric 度量，绝不作为 candidate relevance
  信号。`latency_in_candidate_relevance=false` 是 binding。
- Query anchor 在 P3 主 arm 中被禁用。
  `query_anchors_used_in_p3_arm=false` 是 binding。
- P3 evaluator 在默认 artifact 生成期间不运行检索/provider call。CI workflow
  通过子进程重放 constrained retrieval policy；evaluator 读取结果。
- 私有 per-record trace（policy diagnostics、执行的 action、stop reason、
  per-arm candidate 列表/rank、gold-file reach 标签、latency/pool-size、
  config hash）仅位于 `/tmp` 且绝不上传。
- BEA-v1-P3 不是 BEA v0.4 修复、不是 FD2-B、不是 FD2-C、不是 P4、
  不是 P5、不是 v0.31/v0.32 调参、不是 B16-K、不是 dense/graph/QuIVer
  质量混合、不是 selector/packer runtime 变更、不是 latency-in-relevance
  scoring。
