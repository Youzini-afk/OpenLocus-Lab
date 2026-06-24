# BEA-v1-P4I：不相交分母蓄水池审计

日期：2026-06-24。BEA-v1-P4I 是在 BEA-v1-P4H No-Go 之后进行的有限
**分母/来源审计**。它**不**运行 P2/P3/P4 调度器臂，**不**验证调度器，
**不**扩大检索，**不**执行 selector/reranker，也**不**授权 P5 或
BEA-v1-A。唯一的诊断臂是 `current_bea_candidate_pool_replay`。

> `claim_level = bea_v1_p4i_disjoint_denominator_reservoir_audit_only`。
> `provider_calls_made=false`、
> `gold_labels_used_for_query_construction=false`、
> `gold_labels_used_for_policy=false`、`latency_in_candidate_relevance=false`、
> `query_anchors_used_in_p4_arm=false`、`selector_or_reranker_changed=false`、
> `selector_or_reranker_executed=false`、
> `p2_depth_only_reference_executed=false`、
> `p3_constrained_depth_policy_reference_executed=false`、
> `p4_latency_aware_action_scheduler_executed=false`、`p5_authorized=false`、
> `v1_a_authorized=false` 以及 `frozen_p4h_rerun_authorized=false`（默认）
> 均为 binding。

## 动机（P4H No-Go）

- P4H 结果 checkpoint `9305701`；CI 运行 `28132121958`（green，但是有效的
  No-Go）；full-frame 扫描修复 `0dfeb27`；本地 checkpoint `dee1ce1`。
- P4H 状态 `no_go_p4h_insufficient_denominator`：full-frame 不相交扫描只找到
  **73/80** 条 heldout baseline 文件缺失记录（61 ContextBench，12 RepoQA）。
  由于 80 的硬分母门未被下调，P2/P3/P4 调度器臂未执行。
- P4H 耗尽了可用受支持 Python frame：抓取 266 条 ContextBench 行（limit
  480）和 100 条 RepoQA 行（limit 240），排除 239 条 prior exact raw key
  （162 ContextBench + 77 RepoQA）。
- P4H **不**授权 P5 / BEA-v1-A。

P4I 回答 P4H 留下的开放问题：73/80 的阻塞究竟是当前 ContextBench/RepoQA
Python-frame 分母被耗尽，还是不相交文件缺失分母稀缺是结构性的？

## 范围（binding）

- P4I 是**仅分母/来源审计**。它不是 P5、不是 BEA-v1-A、不是调度器验证、
  不是检索扩展、不是 selector/reranker、不是 broad retrieval。
- 它只扫描已受支持、能用现有 `current_bea_candidate_pool_replay` 诊断臂评估
  的外部 benchmark raw frame/adapter：ContextBench（`offset=0`，`limit=480`）
  与 RepoQA（`offset=0`，`limit=240`）。
- 候选分母记录是 baseline/当前候选池对 gold 文件的**缺失**
  （`gold_file_available=false`）。唯一诊断臂是
  `current_bea_candidate_pool_replay`。不运行 P2/P3/P4 调度器臂。
- 扫描**不**在 80 条目标处停止；它统计完整的累计不相交文件缺失蓄水池。

## 分母构造

- P4I 蓄水池**不是** FD1 `gold_file_absent` 的尾部，也不复用 prior
  P1/P2/P3/P4 的 FD1 分母。
- P4I 在受支持 Python frame 上执行 full-frame raw external 不相交文件缺失
  蓄水池配额扫描：
  - ContextBench：`offset=0`，`limit=480`。
  - RepoQA：`offset=0`，`limit=240`。
- 精确 prior raw-key 排除在**可用时**使用。从 FD1 private decomposition 中，
  只有 **BEA-4 与 BEA-5** 的精确 raw key 可用
  （`exact_prior_exclusion_scope =
  fd1_private_exact_bea4_bea5_raw_keys_only`）。此即精确排除范围；对其他
  prior 阶段不伪造精确 key。
- 对 P1/P2/P3/P4，FD1 BEA-4/BEA-5 精确超集已覆盖其共享的 119 条分母，因此只
  发布聚合披露（`covered_by_fd1_bea4_bea5_exact_superset`）。
- 对 P4H，其精确 73 条已选 raw key 是私有的（仅 `/tmp`，从不提交，不在 FD1
  中），因此只发布聚合披露
  （`p4h_exact_keys_private_tmp_only_aggregate_disclosure`），不伪造精确 key。
  因此蓄水池报告为可能与 P4H heldout 选择重叠的累计不相交文件缺失池。
- 排除之后扫描按稳定 raw 顺序进行。对每条 raw row，P4I clone repository，只运
  行 `current_bea_candidate_pool_replay`，仅当 baseline/当前候选池缺失 gold
  文件时才将该行选入蓄水池。
- 蓄水池在任何未来调度器结果之前构造。没有 treatment 臂。
- 公开 artifact 只发布按来源/benchmark/raw window 的聚合 attempt/yield/exclusion
  计数，加上 subgroup 计数和累计蓄水池计数。私有 per-record key、row index、
  query、repository URL、gold path、candidate path、manifest 与 trace 仅写入
  `/tmp`。

## 硬有效性门

- `reservoir_upper_bound_count >= 80` 才提供 reservoir availability evidence。
- `qualified_denominator_reservoir_count >= 80` 且 `p4h_overlap_resolved=true`
  才能 `reservoir_ready_for_frozen_p4h_rerun`。
- 精确 prior 排除在可用时使用；不序列化私有 raw key/id。
- 分母/蓄水池在任何未来调度器结果之前构造（没有 treatment 臂）。
- 仅聚合、仅记录的公开 artifact：公开指标不含动态 dict（只有 `framing` 和
  `forbidden_scan` 是固定 schema 的 dict；`forbidden_scan.violation_categories`
  是 list）。
- `forbidden_scan.status=pass`。
- 无 provider 调用。
- 无检索策略变更、无 selector/reranker 执行、无 latency-in-relevance、无
  P2/P3/P4 调度器臂。
- 阻塞性失败（扫描失败、扫描未尝试、clone 失败、意外异常）不能被报告为分母不
  足；它们产生 `fail_schema_contract`（fail-closed）。

## 状态

- `reservoir_ready_for_frozen_p4h_rerun` —— 合格的不相交文件缺失蓄水池达到
  `>= 80`。此状态**仅**授权在锁定分母上对冻结 P4H 调度器验证进行 rerun。它
  **不**授权 P5、BEA-v1-A、运行时晋升、method-winner 主张、broad retrieval
  扩展或 selector/reranker 执行。`frozen_p4h_rerun_authorized=true` 只在
  `stop_go_records` 中表达；顶层 guard 字段保持 false。`p5_authorized=false`、
  `v1_a_authorized=false` 等。
- `no_go_disjoint_denominator_reservoir_insufficient` —— 在扫描受支持 frame 后
  仍 `< 80`。这确认对当前受支持 frame 而言，FD1-excluded 文件缺失分母稀缺是结构性的。
- `no_go_disjoint_denominator_reservoir_unqualified` —— FD1-excluded upper-bound
  reservoir 达到 `>=80`，但 P4H exact raw keys 不可用，因此和 P4H 73 条 heldout
  records 的 overlap 未解决。它不授权 frozen P4H rerun。
- `unavailable_with_reason` —— 默认无网络 artifact（诚实，不是 pass）。
- `fail_schema_contract` / `fail_forbidden_scan` —— 隐私/schema/provenance
  失败。任何 `fail_*` 状态对网络启用的真实运行都不是 CI-valid 的。

网络 workflow validator 对隐私/schema 失败 fail-closed，并且只接受
`reservoir_ready_for_frozen_p4h_rerun`、
`no_go_disjoint_denominator_reservoir_insufficient` 或
`no_go_disjoint_denominator_reservoir_unqualified` 作为有效研究结果（加上
`unavailable_with_reason` 仅在无网络默认路径中）。

## 停止规则（精确）

1. 如果蓄水池扫描未尝试（网络禁用、前置条件缺失），默认 artifact 为
   `unavailable_with_reason`（仅无网络路径）。从不伪造扫描。
2. 如果扫描期间发生阻塞性失败（raw 抓取失败、clone 失败、意外异常、FD1
   replay/schema 不匹配），状态为 `fail_schema_contract`（fail-closed）。
   阻塞性失败从不被报告为 `no_go_disjoint_denominator_reservoir_insufficient`。
3. 如果扫描完成且累计 upper-bound 文件缺失蓄水池 `< 80`，状态为
   `no_go_disjoint_denominator_reservoir_insufficient`。80 的硬门不下调。
4. 如果扫描完成且累计 upper-bound 文件缺失蓄水池 `>= 80`，但 P4H exact-key overlap
   未解决，状态为 `no_go_disjoint_denominator_reservoir_unqualified`。它不授权任何
   scheduler rerun。
5. 如果扫描完成且合格的全 prior 不相交文件缺失蓄水池 `>= 80`，状态为
   `reservoir_ready_for_frozen_p4h_rerun`。此状态仅授权在锁定分母上对冻结 P4H
   调度器验证进行 rerun；它不授权 P5 / BEA-v1-A / 运行时晋升 / method winner
   / broad retrieval 扩展。
6. `reservoir_ready_for_frozen_p4h_rerun` 本身不运行调度器、不选择方法、不改变
   任何默认。随后的冻结 P4H rerun 是单独的、显式授权的步骤，必须在 rerun 时锁
   定分母并使用 P4H 精确 key 解决任何 P4H 重叠。

## 公开 artifact 契约

必需的仅聚合记录表（仅记录；无动态 dict）：

- `source_run_records`
- `denominator_reservoir_records`
- `denominator_scan_records`
- `prior_raw_exclusion_records`
- `subgroup_reservoir_records`
- `stop_go_records`
- `gate_records`
- `private_manifest_records`
- `failure_category_count_records`
- `framing`
- `forbidden_scan`

不序列化动态 per-record 细节、私有 raw key/id/path 以及私有 trace 路径。
`private_manifest_records` 中的 `manifest_hash` 是仅 provenance 的文件级完整性
哈希，不暴露 row id、raw key、path、query、candidate list 或 trace 位置。不序
列化任何 row/key/path 哈希。

## Workflow

手动 workflow
`bea-v1-p4i-disjoint-denominator-reservoir-audit.yml` 只通过
`workflow_dispatch` 运行，接受 `enable_external_benchmark_network`。它构建
OpenLocus release CLI，运行 self-test，在 `/tmp` 下重新生成 FD1 private
decomposition，验证 FD1 replay，运行 P4I raw external 不相交文件缺失蓄水池扫
描，fail-closed 验证报告，并上传聚合报告。不上传私有 JSONL/JSON trace。
workflow 不使用任何 model/provider secret。

## 本地验证

```text
python3 -m py_compile eval/bea_v1_p4i_disjoint_denominator_reservoir_audit.py  => PASS
python3 eval/bea_v1_p4i_disjoint_denominator_reservoir_audit.py --self-test  => PASS (88/88 checks)
python3 eval/bea_v1_p4i_disjoint_denominator_reservoir_audit.py \
  --out artifacts/bea_v1_p4i_disjoint_denominator_reservoir_audit/bea_v1_p4i_disjoint_denominator_reservoir_audit_report.json  => PASS
  (默认无网络状态：unavailable_with_reason，
   forbidden_scan=pass, denominator_count=0,
   raw_denominator_scan_attempted=false,
   self_test_checks_total=88, self_test_checks_passed=88)
```

## 注意事项

- P4I 仅是分母/来源审计。它不是 benchmark/leaderboard、default-policy、
  method-winner、运行时晋升、downstream-value、P5、BEA-v1-A、调度器验证、检索
  扩展或 selector/reranker 授权主张。
- 精确排除范围仅为 BEA-4/BEA-5（来自 FD1）。P4H 精确 73 条已选 key 是私有的
  （仅 `/tmp`）且未被排除；蓄水池是 FD1-excluded upper bound，可能与 P4H heldout
  重叠。如果该 upper bound 达到 80 但 P4H overlap 仍未解决，P4I 报告
  `no_go_disjoint_denominator_reservoir_unqualified`，不是 ready。
- 现实的经验结果是
  `no_go_disjoint_denominator_reservoir_insufficient`：受支持 Python frame 在
  80 门以下耗尽。若 FD1-excluded upper bound `>=80` 但 P4H overlap 未解决，则结果为
  `no_go_disjoint_denominator_reservoir_unqualified`。
- Gold/private label 仅用于评估/打分的文件缺失判定。
- Latency 完全不被测量或使用（分母审计，不是调度器）。
