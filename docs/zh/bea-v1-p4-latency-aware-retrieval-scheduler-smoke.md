# BEA-v1-P4: 延迟感知检索动作调度器冒烟

日期：2026-06-24（BEA-v1-P4 —— BEA v1 Hierarchical Actionable Evidence
Acquisition 的第四阶段。在 BEA-v1-P3 结果 checkpoint `eda2087` 之后
运行。P3 在 FD1 `gold_file_absent` 分母（119 个 record）上运行受约束
检索策略冒烟，产生了很强的 retrieval-action 机制信号，但 latency safety
失败：baseline 达到 32/119；P2 depth-only 达到 59/119（新增 27）；P3
constrained 达到 58/119（新增 26），pool 41.50 / 2.08× baseline，latency
3.645s / 2.17× baseline > 2.0 gate，efficiency 1.208122。P3 status 为
`no_go_p3_cost_exceeded`。P4 隔离 P3 的 latency 失败是否来自可避免的
sequential / redundant retrieval actions，并测试一个 runtime-clean
scheduler 修复方案，在保留 P3 / P2 reach 的同时降低 latency。它不是
BEA v0.4 修复，不是 FD2-B / FD2-C，不是 legacy P4 / P5，不是
v0.31 / v0.32 调参，不是 B16-K，不是 selector / acquisition 阶段，不是
dense/graph/QuIVer 质量混合，不是 latency-in-relevance scoring，也
不是 P1、P2 或 P3 重放。）

> `claim_level = bea_v1_p4_latency_aware_retrieval_scheduler_smoke_only`。
> 所有 no-claim / no-runtime-change flag 为 false。`provider_calls_made=false`
> 是 binding。`role_proxy_used=false`、
> `gold_labels_used_for_query_construction=false`、
> `gold_labels_used_for_policy=false`、
> `latency_in_candidate_relevance=false`、
> `query_anchors_used_in_p4_arm=false` 是 binding。

## 绑定上下文

- BEA-v1-P3 结果 checkpoint：`eda2087`；status
  `no_go_p3_cost_exceeded`。P3 保留了 reach 和 pool efficiency 但
  latency safety 失败：baseline 32/119，P2 depth 59/119（新增 27），P3
  constrained 58/119（新增 26），pool 41.50 (2.08×)，latency 3.645s
  (2.17× > 2.0 gate)，efficiency 1.208122，selector relevance 残留
  （mean first-gold rank 25.69，50 条记录位于 budget 之后）。
- BEA-v1-P2 结果 checkpoint：`930dd48`；status
  `no_go_retrieval_reach_latency_or_pool_cost`。
- BEA-v1-P1 结果 checkpoint：`d96e860`；status
  `no_go_retrieval_availability_limit`。`gold_file_absent`
  分母=119，file-selector 下界可恢复计数=1，检索可用性 rate=0.991597。
- P4 在 FD1 `gold_file_absent` 分母（精确 119 个 record）上运行确定性、
  无 provider、网络启用的 latency-aware retrieval-action scheduler。
  它测试一个 runtime-clean scheduler（选择 extra-depth channel actions，
  而非 P3 的全 channel extra-depth round）能否在保留 P3 / P2 reach 的
  同时降低 latency。

## 检索调度器 arm（4，固定）

1. `current_bea_candidate_pool_replay` —— 当前 BEA runtime-clean 检索
   pool（bm25/regex/symbol + derived RRF），depth=1。锚定 v1-P1 / v1-P2 /
   v1-P3 baseline。预期 ~32/119。
2. `p2_depth_only_reference` —— 相同 P2 depth-only 扩展（depth=4，相同
   方法，无 query anchor）。仅作参考。预期 ~59/119。
3. `p3_constrained_depth_policy_reference` —— 精确 P3 策略，预期
   ~58/119，latency ~2.17×。失败参考。
4. `p4_latency_aware_action_scheduler` —— 主 treatment，相同检索方法，
   无 query anchor，仅 action scheduling。

## P4 调度器机制（runtime-clean retrieval-action scheduler）

P4 arm 是 **retrieval-action scheduler**，不是 candidate relevance
scoring。latency 仅用于决定 actions / stop 和 cost gates，绝不用于
rank 候选。

1. **Baseline round**：以 depth=1 收集 bm25 / literal-regex / symbol
   **per-channel**（带 timing 缓存）；从方法结果列表 derive RRF。这缓存
   baseline channel 输出，使 extra-depth 不重跑 baseline 工作（P3 在其
   extra round 中重跑 baseline 工作；P4 缓存它）。
2. **Runtime-clean per-channel diagnostics**（仅公开信号；无 gold / 私有
   标签，无事后调参）：非空 channel、unique file count、duplicate-file
   rate、method agreement、per-channel new-file yield from baseline、
   score mass / spread、query-token / path-token overlap、per-channel
   elapsed time from current run。
3. **Extra-depth channel gating**：不使用 P3 的全 channel extra-depth
   round，而是 per-channel 选择 extra-depth actions：
   - 仅为 baseline 结果 sparse 或 high-yield-looking 的 channel 运行
     extra depth。
   - 跳过 empty / failing、saturated、duplicate-heavy 或已被其他 channel
     overlapped 的 channel。
   - 在 unique-file cap / candidate cap / action budget 达到时停止。
   - 缓存 / 复用 baseline channel 输出，使 extra-depth 不重跑 baseline
     工作。
   - 保持一个简单 predeclared 策略，无 threshold search / matrix。
4. **无 query anchor** 在 P4 中。
5. **latency 仅用于决定 actions / stop 和 cost gates，不用于 rank 候选。**

### 具体 P4 调度器

- 收集 baseline per-channel 输出（带 timing）。
- 计算 per-channel unique file contribution 和 overlap。
- 符合条件的 extra-depth channel：
  - baseline channel 非空、未失败；
  - channel unique file count 低于 cap (60) 或 channel 贡献至少最小
    unique-file share (≥10%) vs baseline；
  - 跳过 duplicate rate 过高 (>0.70) 或与已选 channel overlap 高 (≥0.85)
    的 channel；
  - 可选优先选择 cheapest / high-yield channel（action ordering，不是
    按 latency rank 候选）。
- 最多执行 1-2 个 extra-depth channel action（predeclared）。
- 合并 baseline + 来自所选 extra-depth channel 的 new unique-file
  候选，cap 候选 ≤100，unique files ≤80。

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
- `hard_cap_violation_count` —— P4 arm 中超过 hard candidate cap 的
  record 数。
- `newly_reachable_per_added_candidate` —— 调度器效率。
- `p4_mean_extra_depth_actions` / `p3_mean_extra_depth_actions` ——
  per-record action count 对比。
- `p4_extra_depth_latency_share` —— P4 总 latency 中 extra-depth action
  占比。

## 研究成功 gate

P4 通过仅当以下全部成立：

1. **Reach preservation**：新可达 ≥ 20/119 或保留 ≥ 75% 的 P2 depth-only
   新可达（≥ 21 of +27）。
2. **Latency fix**：P4 latency 倍率 ≤ 2.0× baseline AND P4 latency 比
   P3 latency 降低至少 10%。
3. **Pool safety**：P4 pool 倍率 ≤ 4.0× baseline；hard candidate cap
   violations = 0。
4. **Efficiency / action improvement**：新可达 per added candidate ≥ P3 的
   80% 或优于 P2 combined；action count 低于 P3 的 material share
   （≥ 25% 更少 extra-depth channel action 或 ≥ 20 条记录更少 action）。
5. **Selector relevance 仍存在**：足够多可达 gold 文件仍位于最终 budget
   之外（mean first-gold rank > 5 或 ≥ 25 个 record 的 first-gold rank
   > budget）。

## No-Go 状态

- `no_go_p4_reach_not_preserved` —— P4 未保留足够 reach。
- `no_go_p4_latency_not_fixed` —— latency safety 仍违反。
- `no_go_p4_cost_exceeded` —— pool / hard-cap safety 违反。
- `no_go_p4_policy_degenerate` —— efficiency / action 退化、无
  runtime-clean 主导、或无 selector 问题残留。
- `no_go_p4_replay_mismatch` —— FD1 replay / 分母不匹配、reach drift、
  或检索调度器未执行。

CI / schema / privacy 失败（`fail_forbidden_scan`、
`fail_schema_contract`）会 fail CI，不是有效研究 status。

## 硬性有效性 gate（fail-closed）

- FD1 replay 验证 239 / 86040。
- 分母精确 119。
- Baseline reach 在容差内复现（预期 32，±3）。
- P2 depth-only 参考 reach 在容差内复现（预期 59，±3）。
- P3 参考 reach 在容差内复现（预期 58，±3）。
- P4 检索在 119 个 record 上执行。
- 私有 policy 行 = 分母 × arm = 119 × 4 = 476。
- `forbidden_scan.status=pass`。
- 无 provider call、无 gold / 私有标签用于 scheduler / query 构造、无
  selector / packer / default / runtime promotion、无 role proxy、
  latency 不进入 candidate relevance、P4 arm 不使用 query anchor。

## 公开 artifact 契约

仅聚合、仅 records。无公开 record ID、路径、query、snippet、gold 文件、
candidate 列表、per-record rank、私有 trace 路径或私有 row payload。

必需公开表（仅 records，natural key）：

- `source_run_records`：`(source_phase, source_ci_run_id)` —— FD1 + P1
  + P2 + P3 binding context，含 replay-artifact 验证字段与 P4 scheduler
  config hash。
- `denominator_records`：`(source_phase, benchmark)`。
- `arm_reach_records`：`(arm_name,)`。
- `arm_delta_records`：`(arm_name,)`。
- `arm_cost_records`：`(arm_name, cost_axis)` —— 每 arm pool / latency
  倍率 + hard-cap violation count。
- `arm_action_records`：`(arm_name, scheduler_action)` —— per-scheduler
  -action count。
- `channel_action_records`：`(channel_name, channel_action)` —— per-channel
  聚合 action count。
- `scheduler_stop_reason_records`：`(scheduler_stop_reason,)`。
- `latency_decomposition_records`：`(latency_axis,)` —— baseline vs
  extra-depth latency 分解。
- `efficiency_records`：`(efficiency_axis,)` —— 每 arm
  newly_reachable_per_added_candidate vs P3 / P2 combined / depth。
- `reach_bucket_records`：`(arm_name, reach_bucket)`。
- `rank_band_records`：`(arm_name, rank_band)`。
- `cost_safety_records`：`(cost_safety_axis,)` —— treatment arm 最大
  pool / latency 倍率（排除 P3 失败参考）。
- `stop_go_records`：`(stop_go_decision,)` —— P4 scheduler 决策。
- `gate_records`：`(gate,)` —— fail-closed gate。
- `private_manifest_records`：`(manifest_name,)` —— FD1 private replay
  与 BEA-v1-P4 private scheduler trace manifest；路径绝不序列化。
- `failure_category_count_records`：`(failure_category,)`。
- `framing`、`forbidden_scan`。

## CI gate（fail-closed）

手动 CI workflow `bea-v1-p4-latency-aware-retrieval-scheduler.yml` 仅在
`workflow_dispatch` 且 `enable_external_benchmark_network=true` 时运行。
它在 `/tmp` 下（非 `$RUNNER_TEMP`）重建 FD1 私有分解，验证 replay
report，重放 P4 latency-aware retrieval scheduler 冒烟（网络 + OpenLocus
binary，无 provider secret），并仅上传聚合报告。私有 JSONL/JSON 文件
绝不上传。

Fail-closed 验证：

- `status` 属于：`bea_v1_p4_latency_aware_retrieval_scheduler_pass` |
  `no_go_p4_reach_not_preserved` | `no_go_p4_latency_not_fixed` |
  `no_go_p4_cost_exceeded` | `no_go_p4_policy_degenerate`。
  `no_go_p4_replay_mismatch` 是 replay/default failure status，不是
  CI-valid real-run result。
- FD1 replay 匹配 239 / 86040。
- 分母精确 119。
- real-run status 下 `fd1_private_decomposition_parsed=true` 且
  `replay_artifact_validated=true`。
- `provider_calls_made=false`。
- `gold_labels_used_for_query_construction=false`。
- `gold_labels_used_for_policy=false`。
- `latency_in_candidate_relevance=false`。
- `query_anchors_used_in_p4_arm=false`。
- `forbidden_scan.status=pass`。
- 仅 records 公开形状；natural-key 唯一性。
- 无 forbidden 顶层字段。

## 状态

- `bea_v1_p4_latency_aware_retrieval_scheduler_pass` —— reach 保留、
  latency 修复、成本安全 ok、efficiency / action 改善、runtime-clean 主导、
  selector 问题残留。
- `no_go_p4_reach_not_preserved` —— P4 reach 低于保留阈值。
- `no_go_p4_latency_not_fixed` —— latency 倍率 > 2.0× 或 latency 未比
  P3 降低 ≥10%。
- `no_go_p4_cost_exceeded` —— pool / hard-cap safety 违反。
- `no_go_p4_policy_degenerate` —— efficiency / action 退化、无
  runtime-clean 主导、或无 selector 问题残留。
- `no_go_p4_replay_mismatch` —— FD1 replay / 分母不匹配、reach drift、
  或检索调度器未执行；network enabled 时不是 CI-valid 结果。
- `unavailable_with_reason` —— 默认无网络 artifact。
- `fail_forbidden_scan` / `fail_schema_contract` —— schema/leak 失败。

## Manual CI 结果

Manual CI run `28118888584` 以 1h23m50s 完成 green。它在 `/tmp`
下重新生成 FD1 private decomposition，验证 replay artifact（239 records /
86040 private rows），在 119 条 `gold_file_absent` 分母上运行 4 个固定
P4 arms，在 `/tmp` 下写出 476 条私有 scheduler rows，并只上传聚合公开
artifact。

最终公开 status：
`bea_v1_p4_latency_aware_retrieval_scheduler_pass`。

观测 arms：

- Baseline current pool：32/119 reachable，mean pool 19.983193，mean
  latency 1.799924s。
- P2 depth-only reference：59/119 reachable（新增 27），mean pool
  68.184874（3.412111×），mean latency 2.124798s（1.180493×）。
- P3 constrained reference：58/119 reachable（新增 26），mean pool
  41.512605（2.077376×），mean latency 3.906403s（2.170315×）。这复现了
  P3 latency failure reference。
- P4 latency-aware action scheduler：56/119 reachable（新增 24），
  availability lift 0.201681，mean pool 41.092437（2.056350×），mean
  latency 3.149319s（1.749695×），hard-cap violations 为 0。

P4 通过预注册 gate：它保留了 P2 depth-only 增益的 >=75%，latency 低于
2.0× baseline，相比 P3 latency 降低 19.3806%，pool 低于 4.0× baseline，
在 119/119 条记录上减少 action，并且 selector relevance 仍未解决（mean
first-gold rank 25.625；48 条记录超出 budget）。这是 retrieval-action
scheduler smoke pass，不是 default-policy、benchmark-performance、
method-winner 或 runtime promotion 声明。

早先诊断尝试已被 supersede：run `28110294227` 在最终 schema 收敛前
fail-closed，run `28116719071` 在 FD1 replay 前置步骤只得到 201/239
records 而失败。固定后的 green run 是 `28118888584`。

## 验证

```text
python3 -m py_compile eval/bea_v1_p4_latency_aware_retrieval_scheduler_smoke.py  => PASS
python3 eval/bea_v1_p4_latency_aware_retrieval_scheduler_smoke.py --self-test  => PASS (378/378 checks)
python3 eval/bea_v1_p4_latency_aware_retrieval_scheduler_smoke.py \
  --out artifacts/bea_v1_p4_latency_aware_retrieval_scheduler/bea_v1_p4_latency_aware_retrieval_scheduler_smoke_report.json  => PASS
  (默认无网络 status: unavailable_with_reason,
   stop_go_decision: no_go_p4_replay_mismatch,
   forbidden_scan=pass, denominator_count=0,
   provider_calls_made=false,
   latency_in_candidate_relevance=false,
   query_anchors_used_in_p4_arm=false,
   self_test_checks_total=378, self_test_checks_passed=378)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

## 限制

- BEA-v1-P4 仅 eval/diagnostic。不是 benchmark/leaderboard/
  performance/method-winner/calibration/promotion/default/runtime/
  EvidenceCore/downstream-value 声明。
- Gold/私有标签仅用于评估/评分可达性，绝不用于构造 query/candidate/
  scheduler。`gold_labels_used_for_query_construction=false` 与
  `gold_labels_used_for_policy=false` 是 binding。
- latency 仅用于决定 actions / stop 和 cost gates，绝不作为 candidate
  relevance 信号。`latency_in_candidate_relevance=false` 是 binding。
- Query anchor 在 P4 arm 中被禁用。
  `query_anchors_used_in_p4_arm=false` 是 binding。
- P4 evaluator 在默认 artifact 生成期间不运行检索/provider call。CI workflow
  通过子进程重放 latency-aware retrieval scheduler；evaluator 读取结果。
- 私有 per-record trace（scheduler diagnostics、per-channel action/timing、
  stop reason、per-arm candidate 列表/rank、gold-file reach 标签、
  latency/pool-size、config hash）仅位于 `/tmp` 且绝不上传。
- BEA-v1-P4 不是 BEA v0.4 修复、不是 FD2-B、不是 FD2-C、不是 legacy P4、
  不是 P5、不是 v0.31/v0.32 调参、不是 B16-K、不是 dense/graph/QuIVer
  质量混合、不是 selector/packer runtime 变更、不是 latency-in-relevance
  scoring。
