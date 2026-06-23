# BEA-v1-P1: FD1 可行动性与 Oracle 上限审计

日期：2026-06-23（BEA-v1-P1 —— BEA v1 Hierarchical Actionable Evidence
Acquisition 的第一阶段。它是在完整 FD1 239-record 帧上的经验性
可行动性审计，并在 committed FD1 公开聚合**以及**重新生成的 FD1
私有分解允许的范围内诚实计算 oracle 上限。它不是 BEA v0.4 修复，
不是 FD2-B / FD2-C，不是 P4 / P5，不是 v0.31 / v0.32 调参，不是
B16-K，不是 selector / acquisition 阶段，也不是 FD2-A1 重放。）

> `claim_level = bea_v1_p1_actionability_audit_only`。所有 no-claim /
> no-runtime-change flag 为 false。`role_proxy_used=false` 与
> `target_support_proxy_used=false` 继承自 FD1 scanner 纪律。
> `provider_calls_made=false` 是 binding。

## @oracle 第二次 No-Go 修复（binding）

在第一次 No-Go 修复（要求 FD1 私有重放以计算真实 file-selector 下界）后，
@oracle 标记了两个剩余 blocker：

1. **FD1 私有重放 fail-closed 不足。** workflow 仅验证私有 JSONL 存在且有
   86040 行。这不够：stale / mismatched / partial 重放仍可能授权 v1-A。
   修复后的 workflow 现在在信任 JSONL 前验证 FD1 replay 报告
   （`fd1_replay_report.json`）：schema_version、status、records_decomposed、
   private_decomposition_manifest（schema/record_count/records_written/
   path_publicly_serialized）、manifest_hash 与 committed FD1 artifact 的
   manifest_hash 匹配、forbidden_scan.status。审计 evaluator 通过
   `--fd1-replay-artifact` 重新验证 replay 报告，若 replay artifact 缺失/
   无效/不匹配则 No-Go 至 `no_go_ceiling_unavailable`（即使私有 JSONL 已
   提供）。

2. **stale/ambiguous no-replay 声明。** 之前的
   `bea_v1_p1_no_replay_executed=true` flag 有误导性，因为 CI workflow
   重新生成 FD1 私有分解。重命名为
   `bea_v1_p1_audit_evaluator_no_replay_executed=true`（v1 审计 *evaluator*
   自身不运行 retrieval/selector/replay）。添加显式 provenance flag：
   `fd1_private_decomposition_replay_supplied`、
   `fd1_private_decomposition_replay_validated`、
   `fd1_private_decomposition_replay_executed_by_workflow`。对本地默认/
   无私有 artifact 这些均为 false（supplied 为 false）。对真实 workflow 报告，
   supplied/validated 为 true，workflow-executed 为 true（当存在已验证的
   replay artifact 时）。

审计 evaluator 不重放 FD1；手动 CI workflow 在临时存储下重新生成 FD1
私有分解以计算下界。公开 artifact 仍为仅聚合、仅 records —— 不序列化私有
JSONL 路径或内容 hash。`replay_artifact_manifest_hash` 是 FD1 私有分解的
*schema manifest hash*（schema-content hash），不是私有 JSONL 内容 hash，
且必须与 committed FD1 artifact 的 manifest hash 匹配。

## 绑定上下文

- FD2-A1 结果 checkpoint：`b2aabf5`（status
  `bea_fd2a1_attribution_replay_pass`）。FD2-A1 表明 FD2-A 失败是因为
  `latency_category_non_actionable_or_dominating` bucket 主导了 38/38
  个回归 record，而 candidate availability 并非限制因素。用户显式将
  mainline 切换到 BEA v1 Hierarchical Actionable Evidence Acquisition。
- BEA-v1-P1 审计**完整 FD1 239-record 帧**（BEA-4 120 + BEA-5 119），
  而非 FD2-A1 38-record 帧。主要分母：`records_decomposed = 239`，
  `private_decomposition_manifest.record_count = 86040`。
- BEA-v1-P1 audit evaluator 读取 committed FD1 公开聚合（只读）、
  committed FD2-A1 公开 artifact（只读 binding context），以及 manual CI
  workflow 在临时目录生成的可选 FD1 private decomposition JSONL。审计
  evaluator 本身不重放 FD1、不重放 FD2-A1、不执行任何 selector / retrieval /
  provider call，也不修改任何 committed artifact。

## 行动层（6）

每个 FD1 failure category 映射到 6 个 BEA v1 行动层之一（这些层可
因果地影响该类别）：

1. `candidate_availability_retrieval`
2. `file_selector`
3. `span_refiner`
4. `setwise_packer_redundancy`
5. `stopping_scheduler`
6. `non_actionable_accounting`

## 单元格类别（5）

每个 `(failure_category, action_layer)` 单元格恰为以下之一：

- `direct_actionable` —— 该层是该类别的主要修复点
- `indirect_actionable` —— 该层能部分修复该类别
- `not_actionable_by_layer` —— 该层无法因果地影响该类别
- `candidate_unavailable` —— FD1 将该类别标记为
  `unavailable_no_support_label`（私有 SCORE schema 无 support/target
  标签）；candidate 级别可行动性无法评估；上限无法计算
- `ceiling_unavailable_insufficient_trace` —— FD1 将该类别标记为
  `unavailable_missing_trace`（公开聚合中 per-record trace 不足）；
  上限无法计算

## 可行动性矩阵（12 × 6 = 72 单元格）

公开表 `actionability_matrix_records`（natural key
`(failure_category, action_layer)`）发布全部 72 个单元格。要点
（在 7 个 available 的 FD1 类别中）：

- `gold_file_absent` → `file_selector` 是 `direct_actionable`
  （完美 selector 在 gold 位于 candidate pool 时总能选到它，可能恢复
  该类别）；`candidate_availability_retrieval` 是
  `candidate_unavailable`（gold 缺失意味着 retrieval 层无法恢复）。
- `correct_file_wrong_span` 和 `gold_span_absent` → `span_refiner`
  是 `direct_actionable`。
- `too_many_anchor_slots` → `span_refiner` 是 `direct_actionable`
  （anchor 选择位于 span 层）。
- `early_stop_too_early` → `stopping_scheduler` 是 `direct_actionable`。
- `budget_spent_on_low_marginal_gain` → `setwise_packer_redundancy`
  是 `direct_actionable`（边际效用 packing 控制 budget）。
- `latency_without_quality_gain` → `non_actionable_accounting` 是
  `direct_actionable`（latency 类别在 selection 期间无法由 candidate
  级别 proxy 行动 —— 它必须单独记账，不能折入 selection loss）。
  这是 FD2-A1 No-Go bucket。

3 个 `unavailable_no_support_label` 类别（`missing_support_candidate`、
`support_selected_without_target`、`target_selected_without_support`）
在所有 6 层上均为 `candidate_unavailable`。2 个
`unavailable_missing_trace` 类别（`redundant_same_file_candidates`、
`risk_penalty_removed_gold`）在所有 6 层上均为
`ceiling_unavailable_insufficient_trace`。

## Oracle 上限（诚实，绝不从聚合 latency 推断）

### file_selector 上限（必需，需要 FD1 私有重放）

从 FD1 公开聚合 + 重新生成的 FD1 私有分解 JSONL 计算**上界与下界**：

- 分母 = `gold_file_absent` 跨所有 source_phase/benchmark bucket 的
  affected 计数 = 119（BEA-4 62 + BEA-4 repoqa 17 + BEA-5 24 + BEA-5
  repoqa 16）。
- 可恢复上界 = 分母 = 119（完美 selector 在 gold 位于 candidate pool
  时最多可恢复这么多 record）。
- 可恢复 rate 上界 = 119 / 239 = 0.498。
- 可恢复下界 = 分母 record 中任一 baseline arm（v0.2 / v0 /
  bm25_prefix / agreement_only / rrf）对 `file_recall@10` 的
  `baseline_value` > 0.0 的计数（另一个同 pool / 同帧 arm 选中了
  正确文件 → gold 在 candidate pool 中）。这是可恢复性的**下界** ——
  它不证明每个分母 record 的 gold 都在 pool 中。
- unrecoverable_candidate_unavailable_count = 分母 − 下界（gold 未被
  任何 baseline arm 在同 pool/帧上选中的 record）。
- retrieval_availability_rate = unrecoverable / 分母（若分母 > 0）。
- ceiling_class = `computed_private_lower_bound_and_public_upper_bound`；
- ceiling_basis = `fd1_private_decomposition_replay`。

若未提供私有 JSONL（或无法解析，或行数 ≠ 86040，或分组 record 数 ≠ 239），
则从 `oracle_ceiling_records` 中省略 file_selector 行，在
`unavailable_ceiling_records` 中发布显式 `unavailable` 行，审计 No-Go 至
`no_go_ceiling_unavailable`，`stop_go_decision = needs_fd1_private_replay_before_v1_a`。

### span_refiner 上限（不可用）

FD1 有聚合 `correct_file_wrong_span` 计数，但无 per-record
candidate/gold span overlap。公开聚合不足以约束 span-refiner 上限。
作为显式 `unavailable_ceiling_records` 行发布，原因
`candidate_or_gold_span_overlap_fields_absent_in_fd1_public_aggregate`。

### setwise_packer_redundancy 上限（不可用）

FD1 将 `redundant_same_file_candidates` 标记为
`unavailable_missing_trace`（duplicate / file-grouping 字段不在公开
聚合中）。作为显式 `unavailable_ceiling_records` 行发布，原因
`redundant_same_file_candidates_marked_unavailable_missing_trace_in_fd1`。

### stopping_scheduler 上限（不可用）

FD1 有每类别聚合 `latency_loss`，但无 ordered-prefix utility/latency。
计划禁止从聚合 latency loss 推断 stopping 上限。作为显式
`unavailable_ceiling_records` 行发布，原因
`ordered_prefix_quality_or_latency_absent_in_fd1_public_aggregate`。

## v1-A coverage-preserving selector 的 stop / go 规则

仅当以下全部满足时，才进入 BEA-v1-A（runtime-clean coverage-preserving
file selector）：

1. FD1 私有分解重放已解析（86040 行，239 分组 record，零解析失败）。
   审计要求此项 —— 否则 No-Go 至 `no_go_ceiling_unavailable`，
   stop_go 为 `needs_fd1_private_replay_before_v1_a`。
2. file-selector oracle 上限已计算且分母非零且下界非 null
   （`file_selector_ceiling_computed == true`）。
3. file-selector 下界 rate 是 material 的
   （`file_selector_lower_bound_rate >= 0.05`）。下界 rate
   （非上界 rate）驱动 materiality 测试。
4. retrieval availability 不主导
   （`retrieval_availability_rate <= 0.50` 分母 record）。
5. span / stopping 问题不主导可恢复上限
   （`span_or_stopping_dominates == false`，计算为
   span_or_stopping dominance rate < file-selector 下界 rate 且
   < 0.50 阈值）。
6. runtime-clean coverage-preserving selector 合理
   （BEA-v1-P1 不执行任何 selector；这是基于可行动性矩阵的结构性判断
   —— `file_selector` 是 `gold_file_absent` 的 direct_actionable 层，
   且 FD1 帧已冻结）。

仅当所有条件满足时，审计 `stop_go_decision = go_v1_a_coverage_preserving_selector`。

若任一条件失败，BEA-v1-P1 停止并建议：若条件 1 失败则重放 FD1 私有分解；
若后续条件失败则移动到具有最高诚实上限的层。

## 公开 artifact 契约

仅聚合、仅 records。无公开 record ID、路径、query、snippet、span、
candidate key、selected order、私有 trace 路径或私有 row payload。
仅 count、rate、hash、schema name 与聚合 metric。

必需公开表（仅 records，natural key）：

- `source_run_records`：`(source_phase, source_ci_run_id)` —— FD1 审计
  源（committed FD1 artifact），含验证字段（预期 vs 审计计数、FD1
  schema/hash/status、FD2-A1 binding-context schema/hash/status/checkpoint），
  以及 FD1 私有分解重放状态（`fd1_private_decomposition_supplied`、
  `fd1_private_decomposition_parsed`、
  `fd1_private_decomposition_row_count` 须为 86040、
  `fd1_private_decomposition_group_count` 须为 239、
  `fd1_private_decomposition_denominator`、
  `fd1_private_decomposition_lower_bound`）。
- `failure_category_records`：`(failure_category,)` —— 12 行；每类别
  affected 计数（跨 source_phase/benchmark bucket 求和）与 FD1 可用性
  类别。
- `actionability_matrix_records`：`(failure_category, action_layer)`
  —— 72 行（12 类别 × 6 层）；单元格类别加 boolean
  is_direct_actionable / is_indirect_actionable /
  is_candidate_unavailable / is_ceiling_unavailable flag。
- `oracle_ceiling_records`：`(ceiling_name,)` —— 已计算的上限
  （仅 file_selector）。`oracle_ceiling_records` 仅用于实际计算过的上限；
  不可用上限发布于 `unavailable_ceiling_records`。
- `candidate_availability_records`：
  `(source_phase, benchmark, failure_category)` —— 每 (sp, bm, cat) 的
  evaluable record 计数（仅 7 个 ceiling-relevant available 类别；
  排除不可用类别）。
- `unavailable_ceiling_records`：`(ceiling_name,)` —— 3 行
  （span_refiner、setwise_packer_redundancy、stopping_scheduler），
  含显式 reason 字符串。
- `redundancy_tradeoff_records`：`(tradeoff_axis,)` —— 2 行
  （marginal_utility_per_added_candidate、
  duplicate_same_file_suppression_cost），均为 `unavailable`，
  含 reason。
- `stop_go_records`：`(stop_go_decision,)` —— 1 行；v1-A stop/go
  决策与 reason，记录所有阈值输入。
- `gate_records`：`(gate,)` —— 11 个 fail-closed gate。
- `private_manifest_records`：`(manifest_name,)` —— 1 行回显 FD1
  private_decomposition_manifest（只读；仅 count/hash/storage；
  路径绝不序列化）。
- `failure_category_count_records`：`(failure_category,)` —— 审计级别
  failure category 计数（如 `fd1_artifact_missing`、
  `fd1_records_decomposed_mismatch` 等）。
- `framing`、`forbidden_scan`。

## CI gate（fail-closed）

手动 CI workflow `bea-v1-p1-actionability-audit.yml` 仅在
`workflow_dispatch` 上运行。CI workflow 在 `$RUNNER_TEMP/fd1_private`
下重新生成 FD1 私有分解（通过
`bea_fd1_failure_decomposition --enable-external-benchmark-network
--private-decomposition-dir` 的确定性重放），并通过
`--fd1-private-decomposition-jsonl` 将 JSONL 路径传给审计。私有 JSONL
绝不上传。无 provider secret/var/model env；FD1 重放使用冻结 BEA-4/5
协议，无 provider call。

Fail-closed 验证：

- `status` 属于允许的 real-run 审计结果之一：
  `bea_v1_p1_actionability_audit_pass` |
  `no_go_no_file_selector_ceiling` |
  `no_go_retrieval_availability_limit` |
  `no_go_span_or_stopping_dominates` |
  `no_go_ceiling_unavailable`。
- FD1 计数匹配：`records_decomposed == 239` 且
  `private_manifest_record_count == 86040`。
- 全部 12 个 FD1 类别出现在 `actionability_matrix_records` 中
  （72 行 = 12 × 6）。
- 当 FD1 私有重放运行（网络启用）时：
  - 任何 pass/go status 下 `fd1_private_decomposition_parsed == true`。
  - `fd1_private_decomposition_replay_supplied == true`、
    `fd1_private_decomposition_replay_validated == true`、
    `fd1_private_decomposition_replay_executed_by_workflow == true`。
  - `fd1_private_decomposition_row_count == 86040` 且
    `fd1_private_decomposition_group_count == 239`。
  - `replay_artifact_validated == true`、
    `replay_artifact_manifest_hash_match == true`、
    `replay_artifact_forbidden_scan_pass == true`、
    `replay_artifact_manifest_records_written == true`、
    `replay_artifact_manifest_path_publicly_serialized == false`、
    `replay_artifact_failure_category == ""`（在 source_run_records 中）。
  - status 为 pass 时，`oracle_ceiling_records` 含 `file_selector` 行，
    `ceiling_class = computed_private_lower_bound_and_public_upper_bound`，
    `ceiling_basis = fd1_private_decomposition_replay`。
  - status 为 pass 时 `recoverable_count_lower_bound` 非 null。
  - `file_selector_lower_bound` 为 null 时 `stop_go_decision` 不得为
    `go_v1_a_coverage_preserving_selector`。
- 当网络未启用（默认无重放）时：
  - `status == no_go_ceiling_unavailable`。
  - `stop_go_decision == needs_fd1_private_replay_before_v1_a`。
- span / stopping 要么已计算，要么有显式不可用行
  （`unavailable_ceiling_records`）。
- `forbidden_scan.status == pass`。
- 仅 records 公开形状；每个公开 record 表的 natural-key 唯一性。
- 无 forbidden 顶层字段（private / per-record / claim /
  dynamic-dict / self-test detail / forbidden-scope flag 如
  `is_v04_repair`、`is_fd2_b`、`is_p4`、`is_b16k`）。
- `provider_calls_made == false`。

`unavailable_with_reason` 仅对默认无 FD1 artifact 情形有效
（诚实；非伪造 pass）。`fail_forbidden_scan` 与
`fail_schema_contract` 是失败状态，非 CI-valid 结果。

## 状态

- `bea_v1_p1_actionability_audit_pass` —— file-selector 上限已计算
  且 upside material；retrieval availability 不主导；span/stopping
  不主导；v1-A coverage-preserving selector 合理。
- `no_go_no_file_selector_ceiling` —— file-selector oracle 上限不可用
  或 upside 低于 material 阈值（0.05）。
- `no_go_retrieval_availability_limit` —— retrieval-availability rate
  超过可恢复上限的 0.50。
- `no_go_span_or_stopping_dominates` —— span-refiner 或
  stopping-scheduler 可行动 loss 主导（dominance rate > 0.50 且超过
  file-selector upside rate）。
- `no_go_ceiling_unavailable` —— file-selector 上限不可用且 audit_match
  为 True（罕见；保留）。
- `unavailable_with_reason` —— 默认无 FD1 artifact 或 audit-mismatch
  情形（诚实；非伪造 pass）。
- `fail_forbidden_scan` / `fail_schema_contract` —— schema/leak 失败；
  非 CI-valid 结果。

## 验证

```text
python3 -m py_compile eval/bea_v1_p1_actionability_audit.py  => PASS
python3 eval/bea_v1_p1_actionability_audit.py --self-test  => PASS (596/596 checks)
python3 eval/bea_v1_p1_actionability_audit.py \
  --out artifacts/bea_v1_p1_actionability_audit/bea_v1_p1_actionability_audit_report.json  => PASS
  (默认无私有 JSONL status: no_go_ceiling_unavailable,
   stop_go_decision: needs_fd1_private_replay_before_v1_a,
   forbidden_scan=pass, records_decomposed=239,
   private_manifest_record_count=86040,
   fd1_private_decomposition_parsed=false,
   fd1_private_decomposition_replay_supplied=false,
   fd1_private_decomposition_replay_validated=false,
   provider_calls_made=false,
   self_test_checks_total=596, self_test_checks_passed=596)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

要授权 v1-A，审计必须使用重新生成的 FD1 私有分解 JSONL **以及** FD1 replay
报告运行（CI workflow 在 `enable_external_benchmark_network=true` 时自动
完成两者）：

```text
python3 eval/bea_fd1_failure_decomposition.py \
  --enable-external-benchmark-network \
  --private-decomposition-dir /tmp/fd1_private \
  --openlocus target/release/openlocus \
  --out /tmp/fd1_replay_report.json
python3 eval/bea_v1_p1_actionability_audit.py \
  --fd1-private-decomposition-jsonl /tmp/fd1_private/bea_fd1.decomposition.jsonl \
  --fd1-replay-artifact /tmp/fd1_replay_report.json \
  --out artifacts/bea_v1_p1_actionability_audit/bea_v1_p1_actionability_audit_report.json
```

## Manual CI 结果

默认无私有 JSONL artifact 诚实为 `no_go_ceiling_unavailable`，
`stop_go_decision = needs_fd1_private_replay_before_v1_a` —— 这是未运行
FD1 私有分解重放时的真实状态。审计不从公开聚合上界单独伪造 pass。

当 CI workflow 以 `enable_external_benchmark_network=true` 运行时，它在
`$RUNNER_TEMP/fd1_private` 重新生成 FD1 私有分解（冻结 BEA-4/5 协议的
确定性重放，无 provider call），将 JSONL 路径传给审计，审计计算真实的
file-selector 下界。status 与 stop_go 决策随后取决于计算出的下界 rate
vs materiality 阈值（0.05）以及 retrieval availability rate vs
dominance 阈值（0.50）。

真实重放运行后此 Manual CI 结果将填入；在此之前，committed artifact
保持诚实的 `no_go_ceiling_unavailable` 默认。

## 限制

- BEA-v1-P1 仅 eval/diagnostic。不是 benchmark/leaderboard/
  performance/method-winner/calibration/promotion/default/runtime/
  EvidenceCore/downstream-value 声明。
- file-selector oracle 上限需要 FD1 私有分解重放（86040 行 / 239 分组
  record）**以及** FD1 replay 报告（已验证：schema/status/counts/
  manifest-hash/forbidden_scan）以计算真实下界。公开聚合上界单独不足以
  授权 v1-A —— 无私有重放且无已验证 replay artifact 时，审计诚实 No-Go
  至 `no_go_ceiling_unavailable`。
- 审计 *evaluator* 不重放 FD1、不运行 retrieval/selector/provider call。
  手动 CI workflow 在 `$RUNNER_TEMP` 重新生成 FD1 私有分解（冻结 BEA-4/5
  确定性重放，无 provider call）并写入 FD1 replay 报告；审计 evaluator
  读取两者。`bea_v1_p1_audit_evaluator_no_replay_executed=true` flag 跟踪
  evaluator 的 no-replay 不变量；`fd1_private_decomposition_replay_*`
  flag 跟踪 workflow 的重放 provenance。
- 可恢复下界**仅为下界**：它计数任一 baseline arm 选中正确文件的
  record。它不证明每个分母 record 的完整 candidate-pool 可用性。
- `replay_artifact_manifest_hash` 是 FD1 私有分解的 *schema manifest hash*
  （schema-content hash），不是私有 JSONL 内容 hash。公开 artifact 不
  序列化私有 JSONL 路径或内容 hash。
- span-refiner / setwise_packer_redundancy / stopping_scheduler 上限
  诚实不可用。计划禁止从聚合 latency loss 推断 stopping 上限。
- 审计继承 FD1 的不可用类别纪律：
  `redundant_same_file_candidates` 与 `risk_penalty_removed_gold` 为
  `unavailable_missing_trace`；`missing_support_candidate`、
  `support_selected_without_target`、
  `target_selected_without_support` 为 `unavailable_no_support_label`。
  BEA-v1-P1 不发明 support/target 标签或 per-record trace。
- BEA-v1-P1 不是 BEA v0.4 修复、不是 FD2-B、不是 FD2-C、不是 P4、
  不是 P5、不是 v0.31/v0.32 调参、不是 B16-K、不是 FD2-A1 重放。
  framing flag `is_v04_repair=false`、`is_fd2_b=false`、
  `is_fd2_c=false`、`is_p4=false`、`is_p5=false`、
  `is_v031_tuning=false`、`is_v032_tuning=false`、`is_b16k=false`
  是 binding。
