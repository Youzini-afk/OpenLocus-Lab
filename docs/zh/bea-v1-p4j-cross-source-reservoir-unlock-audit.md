# BEA-v1-P4J：跨来源文件缺失蓄水池解锁审计

日期：2026-06-25。BEA-v1-P4J 是在 BEA-v1-P4I No-Go（checkpoint
`cc19f5b`，CI 运行 `28137455572`，`no_go_disjoint_denominator_reservoir_insufficient`，73/80
不相交文件缺失记录）之后进行的有限**跨来源分母/来源审计**。它**不**运行
P2/P3/P4 调度器臂，**不**验证调度器，**不**扩大检索，**不**执行
selector/reranker，**不**调用任何 provider，**不**运行 runtime/default 提升
或 method-winner 逻辑，也**不**授权 P5、BEA-v1-A 或 frozen P4 重跑。唯一的
诊断臂是 `current_bea_candidate_pool_replay`。

> `claim_level = bea_v1_p4j_cross_source_reservoir_unlock_audit_only`。
> `provider_calls_made=false`、
> `gold_labels_used_for_query_construction=false`、
> `gold_labels_used_for_policy=false`、`latency_in_candidate_relevance=false`、
> `query_anchors_used_in_p4_arm=false`、`selector_or_reranker_changed=false`、
> `selector_or_reranker_executed=false`、
> `p2_depth_only_reference_executed=false`、
> `p3_constrained_depth_policy_reference_executed=false`、
> `p4_latency_aware_action_scheduler_executed=false`、
> `v1_a_selector_executed=false`、`p5_authorized=false`、
> `v1_a_authorized=false`、`frozen_p4_rerun_authorized=false` 以及
> `locked_p4_validation_executed=false` 均为 binding。

## 动机（P4H/P4I No-Go）

- P4H 结果 checkpoint `9305701`；CI 运行 `28132121958`；状态
  `no_go_p4h_insufficient_denominator`：full-frame 不相交扫描只找到
  **73/80** 条 heldout baseline 文件缺失记录。
- P4I 结果 checkpoint `cc19f5b`；CI 运行 `28137455572`；状态
  `no_go_disjoint_denominator_reservoir_insufficient`：在受支持的
  ContextBench/RepoQA **Python** frame 上进行的 full-frame 不相交蓄水池扫描
  只找到 **73/80** 条 FD1 排除后的文件缺失蓄水池记录（61 ContextBench，12
  RepoQA）。P4H 重叠仍未解决（P4H 精确选定 key 为 private/aggregate-only）。

P4J 回答 P4H/P4I 留下的开放问题：73/80 的阻塞究竟是当前受支持的
ContextBench/RepoQA **Python** frame 特有，还是其他已受支持的**跨来源 frame**
能解锁至少 80 条 baseline 文件缺失分母记录？

## 范围（binding）

- P4J 是**仅跨来源分母/来源审计**。它不是 P5、不是 BEA-v1-A、不是调度器
  验证、不是检索扩展、不是 selector/reranker、不是 broad retrieval、不是
  method-winner 逻辑、不是 runtime/default 提升、不是 frozen P4 重跑。
- 它只扫描已受支持的跨来源 frame，用现有 `current_bea_candidate_pool_replay`
  诊断臂评估：
  1. ContextBench `contextbench_verified/train`，`language_filter="all"`，通过
     `c5a._fetch_contextbench_rows(limit, "all")`。**不**使用 `default` config
     （那属于新数据集集成）。
  2. RepoQA 非 Python 顶层 asset 语言，通过
     `c5d._download_asset_to_bytes` + `c5d._decompress_asset` +
     `c5d._parse_repoqa_needles(parsed, lang, limit)`。绕过 c5d CLI，因其
     argparse 当前只允许 Python。
- 候选分母记录是 baseline/当前候选池对 gold 文件的**缺失**
  （`gold_file_available=false`）。唯一诊断臂是
  `current_bea_candidate_pool_replay`。不运行 P2/P3/P4 调度器臂。
- 扫描**不**在 80 条目标处停止；它统计完整的累计跨来源文件缺失蓄水池上界，
  并单独报告该蓄水池是否具备 all-prior-disjoint 资格。

## 排除的来源 frame（已说明）

- SWE-Explore：仅 schema/row-map，无 `repo_url` / `base_commit` clone 路径。
- CORE-Bench：仅 readiness probe，无 row-to-retrieval adapter。
- SWE-bench original：仓库中无 adapter。
- ContextBench `default` config：尚未集成；使用它属于新数据集集成，超出 P4J
  范围。

这些记录在 `excluded_source_frame_records` 中披露。

## 分母构造

- P4J 蓄水池**不是** FD1 `gold_file_absent` 的尾部，也不复用 prior
  P1/P2/P3/P4 的 FD1 分母。
- P4J 执行跨来源文件缺失蓄水池解锁配额扫描：
  - ContextBench `all`：`offset=0`，`limit=480`，`language_filter="all"`。
  - RepoQA 非 Python：每语言 `limit=60`；语言从下载的 RepoQA release asset
    动态发现（绕过 c5d CLI）。
- 精确 prior raw-key 排除在**适用时**使用。从 FD1 private decomposition 中，
  只有 **BEA-4 与 BEA-5** 的精确 raw key 可用
  （`exact_prior_exclusion_scope =
  fd1_private_exact_bea4_bea5_raw_keys_where_applicable_by_construction_disjoint_for_non_python_frames`）。
  这些位于 Python-ordinal 空间，应用于 ContextBench Python 行（通过运行中的
  python-ordinal 映射）。对其他 prior 阶段不伪造精确 key。
- 对非 Python frame（ContextBench 非 Python 行 + RepoQA 非 Python needle），
  披露**按构造不相交**依据：BEA-4/5 只在 Python frame 上运行，因此非 Python
  行没有 FD1 prior key（`by_construction_disjoint_non_python_frames=true`）。
  这是披露，不是伪造。
- 对 P1/P2/P3/P4，FD1 BEA-4/BEA-5 精确超集已覆盖其共享的 119 条 Python 分母，
  因此只发出 aggregate 披露。
- 对 P4H/P4I，精确选定 key 为 private（仅 `/tmp`，从不提交，不在 FD1 中），
  因此只发出 aggregate 披露且不伪造精确 key。蓄水池因此作为 FD1 排除后的
  上界文件缺失池报告，可能与 P4H/P4I 的 heldout 选择重叠。非 Python 子集
  （`cross_source_non_python_reservoir_count`）按构造与 P4H/P4I（仅 Python）
  不相交，但**不**被视为具备 all-prior-disjoint 资格的蓄水池，除非 P4H/P4I
  重叠被解决（见下文）。
- 扫描在排除后使用稳定的 raw 顺序。对每条 raw 行，P4J clone 仓库，只运行
  `current_bea_candidate_pool_replay`，并仅当 baseline/当前候选池缺失 gold 文件
  时将该行选入蓄水池。
- 蓄水池在任何未来调度器结果之前构造。没有 treatment arm。
- 公开 artifact 只发布按来源、frame、benchmark 和语言桶分组的 aggregate
  尝试/产出/排除计数，加上子组计数和累计蓄水池计数。私有 per-record key、
  row index、query、仓库 URL、gold 路径、候选路径、manifest 和 trace 仅写入
  `/tmp`。

## 硬有效性门

- `reservoir_upper_bound_count >= 80` 作为蓄水池可用性证据。
- `qualified_cross_source_reservoir_count >= 80` 且
  `p4h_p4i_overlap_resolved=true` 才能达到
  `cross_source_reservoir_ready_for_locked_p4_validation_design`。
- 精确 prior 排除在适用时使用；不序列化私有 raw key/id。
- 分母/蓄水池在任何未来调度器结果之前构造（没有 treatment arm）。
- Aggregate-only、records-only 公开 artifact：公开指标无动态 dict（只有
  `framing` 与 `forbidden_scan` 是固定 schema dict；
  `forbidden_scan.violation_categories` 为 list）。
- `forbidden_scan.status=pass`。
- 无 provider 调用。
- 无检索策略变更、无 selector/reranker 执行、无 latency-in-relevance、无
  P2/P3/P4 调度器臂、无 method-winner 逻辑、无 runtime/default 提升。
- 阻塞性失败（扫描失败、扫描未尝试、clone 失败、asset 下载/解压失败、意外
  异常、FD1 replay/schema 不匹配）不能作为分母不足报告；它们产生
  `fail_schema_contract`（fail-closed）。

## 状态

- `cross_source_reservoir_ready_for_locked_p4_validation_design` — 具备
  all-prior-disjoint 资格的跨来源蓄水池在 P4H/P4I 重叠已解决时达到 `>= 80`。
  这**仅**授权设计一个在锁定分母上的独立 frozen P4 验证。它**不**运行调度器，
  **不**授权 P5、BEA-v1-A、runtime 提升、method-winner 主张、broad retrieval
  扩展、selector/reranker 执行、frozen P4 重跑或 runtime/default 提升。
  `locked_p4_validation_design_authorized=true` 仅在 `stop_go_records` 内表达；
  顶层 guard `locked_p4_validation_executed` 保持 false。
  `frozen_p4_rerun_authorized=false`。
- `no_go_cross_source_file_miss_reservoir_insufficient` — 扫描受支持的跨来源
  frame 后仍 `< 80`。确认 FD1 排除后的文件缺失分母稀缺对当前受支持的跨来源
  frame 是结构性的。
- `no_go_cross_source_reservoir_unqualified` — FD1 排除后的上界蓄水池达到
  `>=80`，但 P4H/P4I 重叠未解决（精确选定 key 不可用）。这只是来源解锁证据；
  不授权任何调度器重跑或 locked P4 验证设计。
- `unavailable_with_reason` — 默认无网络 artifact（诚实，非 pass）。
- `fail_schema_contract` / `fail_forbidden_scan` — 隐私/schema/provenance 失败。
  任何 `fail_*` 状态对网络-enabled 的真实运行都不是 CI-valid。

网络 workflow 验证器对隐私/schema 失败 fail-closed，只接受
`cross_source_reservoir_ready_for_locked_p4_validation_design`、
`no_go_cross_source_file_miss_reservoir_insufficient` 或
`no_go_cross_source_reservoir_unqualified` 作为有效研究结果（仅在无网络
默认路径下接受 `unavailable_with_reason`）。

## 停止规则（精确）

1. 若蓄水池扫描未尝试（网络禁用、前置条件缺失），默认 artifact 为
   `unavailable_with_reason`（仅无网络路径）。扫描从不伪造。
2. 若扫描期间发生阻塞性失败（raw 抓取失败、clone 失败、asset 下载/解压失败、
   意外异常、FD1 replay/schema 不匹配、精确 prior 排除不可用），状态为
   `fail_schema_contract`（fail-closed）。阻塞性失败从不作为
   `no_go_cross_source_file_miss_reservoir_insufficient` 报告。
3. 若扫描完成且累计上界文件缺失蓄水池 `< 80`，状态为
   `no_go_cross_source_file_miss_reservoir_insufficient`。80 的硬门不下调。
4. 若扫描完成且累计上界文件缺失蓄水池 `>= 80` 但 P4H/P4I 重叠未解决，状态为
   `no_go_cross_source_reservoir_unqualified`。这不授权任何调度器重跑或
   locked P4 验证设计。
5. 若扫描完成且具备 all-prior-disjoint 资格的跨来源蓄水池 `>= 80` 且重叠已
   解决，状态为
   `cross_source_reservoir_ready_for_locked_p4_validation_design`。这仅授权在
   锁定分母上设计独立的 frozen P4 验证；它不运行调度器、不选择 method、不变更
   任何 default、不授权 P5 / BEA-v1-A / runtime 提升 / method winner /
   broad retrieval 扩展 / frozen P4 重跑。
6. `cross_source_reservoir_ready_for_locked_p4_validation_design` 本身不运行
   调度器、不选择 method、不变更任何 default。后续 frozen P4 验证是一个独立的、
   显式授权的步骤，必须在验证时锁定分母并用精确 key 解决任何 P4H/P4I 重叠。

## 公开 artifact 契约

必需的 aggregate-only 记录表（records-only；无动态 dict）：

- `source_run_records`
- `denominator_reservoir_records`
- `denominator_scan_records`
- `cross_source_frame_records`
- `excluded_source_frame_records`
- `prior_raw_exclusion_records`
- `subgroup_reservoir_records`
- `stop_go_records`
- `gate_records`
- `private_manifest_records`
- `failure_category_count_records`
- `framing`
- `forbidden_scan`

不序列化任何动态 per-record 详情、私有 raw key/id/path、仓库 URL、query、
gold 路径、候选路径、snippet、prompt/response、provider payload、私有 hash、
或私有 trace 路径。`private_manifest_records` 中的 `manifest_hash` 是仅作
provenance 的文件级完整性 hash，不暴露 row id、raw key、路径、query、候选列表
或 trace 位置。不序列化任何 row/key/path hash。

## Workflow

手动 workflow
`bea-v1-p4j-cross-source-reservoir-unlock-audit.yml` 仅通过
`workflow_dispatch` 运行，接受 `enable_external_benchmark_network`。它构建
OpenLocus release CLI，运行 self-test，在 `/tmp` 下重新生成 FD1 private
decomposition，验证 239-record / 86040-row 的 FD1 replay，运行 P4J 跨来源文件
缺失蓄水池扫描，fail-closed 验证报告，并上传 aggregate 报告。私有
JSONL/JSON trace 仅写入 `/tmp`，从不上传。workflow 不使用 model/provider
secret。私有目录使用 `/tmp`，不使用 `$RUNNER_TEMP`；只有最终公开报告暂存于
`$RUNNER_TEMP` 供上传。

## 本地验证

```text
python3 -m py_compile eval/bea_v1_p4j_cross_source_reservoir_unlock_audit.py  => PASS
python3 eval/bea_v1_p4j_cross_source_reservoir_unlock_audit.py --self-test  => PASS (118/118 checks)
python3 eval/bea_v1_p4j_cross_source_reservoir_unlock_audit.py \
  --out artifacts/bea_v1_p4j_cross_source_reservoir_unlock_audit/bea_v1_p4j_cross_source_reservoir_unlock_audit_report.json  => PASS
  (默认无网络 status: unavailable_with_reason,
   forbidden_scan=pass, denominator_count=0,
   cross_source_reservoir_scan_attempted=false,
   self_test_checks_total=118, self_test_checks_passed=118)
```

## CI 结果

Manual network-enabled CI run `28146407493` 在 diagnostic/fail-closed patch
`18126f4` 后绿色完成。它产出了有效 aggregate-only 研究结果，status 为
`no_go_cross_source_reservoir_unqualified`。

P4J 成功显示：alternative already-supported cross-source frames 中存在较大的
FD1-excluded file-miss reservoir upper bound；但该 reservoir 还不具备 locked P4
validation 资格，因为 P4H/P4I exact selected keys 不可用，overlap 未解决。

聚合 CI 指标：

- `status=no_go_cross_source_reservoir_unqualified`
- `denominator_count=333`，`reservoir_upper_bound_count=333`
- `qualified_cross_source_reservoir_count=0`
- `cross_source_non_python_reservoir_count=272`
- `cross_source_python_reservoir_count=61`
- `raw_scan_fetched_records=780`
- `raw_scan_attempted_records=618`
- `raw_scan_prior_exact_excluded_records=162`
- `raw_scan_by_construction_disjoint_records=514`
- `raw_scan_yield_file_miss_records=333`
- `raw_scan_baseline_reached_records=285`
- `raw_scan_baseline_error_records=0`
- `exact_prior_exclusion_used=true`
- `p4h_p4i_overlap_resolved=false`
- `private_manifest_records`：FD1 replay 86040 rows，P4J private reservoir scan 618 rows
- `scan_diagnostic_records=[]`
- `self_test_checks_total=118`，`self_test_checks_passed=118`
- `forbidden_scan.status=pass`

Frame-level result：

- ContextBench all-language frame：取到 480 rows，排除 162 条 FD1 BEA-4/5 exact
  prior rows，尝试 318 rows，选出 197 条 file-miss records。
- RepoQA non-Python frame：在 cpp/go/java/rust/typescript 上取到并尝试 300 rows，
  选出 136 条 file-miss records。

这不是 `cross_source_reservoir_ready_for_locked_p4_validation_design`。P4J 不授权
locked-P4 scheduler validation、frozen P4 rerun、P5 selector/reranker、BEA-v1-A、
runtime promotion、method-winner 声明或 broad retrieval expansion。

## 注意事项

- P4J 是仅跨来源分母/来源审计。它不是 benchmark/leaderboard、default-policy、
  method-winner、runtime-promotion、downstream-value、P5、BEA-v1-A、调度器验证、
  检索扩展、selector/reranker、frozen-P4-rerun 或 runtime/default 提升授权主张。
- 精确排除范围仅 BEA-4/BEA-5（来自 FD1），在适用处应用（ContextBench Python
  行经 python-ordinal）。P4H/P4I 精确选定 key 为 private（仅 `/tmp`）且不排除；
  蓄水池是 FD1 排除后的上界，可能与 P4H/P4I 的 heldout 选择重叠。若该上界达到
  80 而 P4H/P4I 重叠仍未解决，P4J 报告
  `no_go_cross_source_reservoir_unqualified`，而非 ready。
- 非 Python 子集（`cross_source_non_python_reservoir_count`）按构造与 P4H/P4I
  （仅 Python）不相交，但**不**被视为具备 all-prior-disjoint 资格的蓄水池，除非
  通过在 `/tmp` 下重新生成 P4H/P4I 精确选定 key 来解决重叠。
- `cross_source_reservoir_ready_for_locked_p4_validation_design` **不**授权
  frozen P4 重跑（`frozen_p4_rerun_authorized=false`）；它仅授权在锁定分母上
  设计独立的 locked-P4 验证。
- Gold/private label 仅用于评估/scoring 文件缺失。
- 延迟完全不测量或使用（分母审计，非调度器）。
- ContextBench `default` config 被有意排除（新数据集集成超出范围）；只使用
  `contextbench_verified/train` 与 `language_filter="all"`。
- RepoQA c5d CLI 被绕过，因其 argparse 只允许 Python；非 Python asset 语言直接
  通过 `c5d._parse_repoqa_needles(parsed, lang, limit)` 解析。
