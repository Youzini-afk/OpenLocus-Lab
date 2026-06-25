# BEA-v1-P4K：精确重叠解析与锁定蓄水池审计

日期：2026-06-25。BEA-v1-P4K 是在 BEA-v1-P4J No-Go（CI `28146407493`，
`no_go_cross_source_reservoir_unqualified`，上界蓄水池 333 但因 P4H/P4I 重叠未
解决导致合格计数为 0）之后进行的有限**分母/来源审计**。它**不**运行
P2/P3/P4 调度器臂，**不**验证调度器，**不**扩大检索，**不**执行
selector/reranker，**不**调用任何 provider，**不**运行 runtime/default 提升或
method-winner 逻辑，也**不**授权 P5、BEA-v1-A、frozen P4 验证或 frozen P4
重跑。唯一的诊断臂是 `current_bea_candidate_pool_replay`。

> `claim_level = bea_v1_p4k_exact_overlap_resolution_locked_reservoir_audit_only`。
> `provider_calls_made=false`、
> `gold_labels_used_for_query_construction=false`、
> `gold_labels_used_for_policy=false`、`latency_in_candidate_relevance=false`、
> `query_anchors_used_in_p4_arm=false`、`selector_or_reranker_changed=false`、
> `selector_or_reranker_executed=false`、
> `p2_depth_only_reference_executed=false`、
> `p3_constrained_depth_policy_reference_executed=false`、
> `p4_latency_aware_action_scheduler_executed=false`、
> `v1_a_selector_executed=false`、`p5_authorized=false`、
> `v1_a_authorized=false`、`frozen_p4_rerun_authorized=false`、
> `frozen_p4_validation_executed=false`、`locked_p4_validation_executed=false`
> 以及 `locked_p4_validation_design_authorized=false`（默认）均为 binding。

## 动机（P4H/P4I/P4J No-Go）

- P4H（CI `28132121958`）：`no_go_p4h_insufficient_denominator`，在受支持的
  Python frame 中 73/80 不相交文件缺失 heldout 记录；精确选定 key 为 private
  且未提交。
- P4I（CI `28137455572`）：`no_go_disjoint_denominator_reservoir_insufficient`，
  相同的 73 FD1 排除 Python-frame 蓄水池；精确选定 key 为 private/不可用。
- P4J（CI `28146407493`）：`no_go_cross_source_reservoir_unqualified`，在
  ContextBench all-language + RepoQA 非 Python 中找到上界蓄水池 333，但因
  P4H/P4I 重叠未解决导致合格计数为 0。

P4K 回答 P4J 留下的开放问题：能否在 `/tmp` 下使用确定性来源排序和相同的
baseline/当前候选池 replay 分类器，经验性地重建 P4H（73）、P4I（73）和
P4J（333）的精确选定 raw key，如果能，从 P4J 中移除 P4H 和 P4I 重叠后的
排除后锁定跨来源蓄水池计数是多少？

## 范围（binding）

- P4K 是**仅精确重叠解析与锁定蓄水池审计**。它不是 P5、不是 BEA-v1-A、不是
  调度器验证、不是检索扩展、不是 selector/reranker、不是 broad retrieval、
  不是 method-winner 逻辑、不是 runtime/default 提升、不是 frozen P4 验证、
  不是 frozen P4 重跑。
- 它重新运行 P4H/P4I/P4J 使用的相同确定性扫描，使用现有的
  `current_bea_candidate_pool_replay` 诊断臂，并将选定 raw key **私有记录于
  `/tmp`**（从不上传，从不公开序列化）。
- P4H/P4I 重建：ContextBench Python（offset 0，limit 480）+ RepoQA Python
  （offset 0，limit 240），FD1 BEA-4/5 精确 key 排除，baseline 文件缺失选择。
  P4H 目标 80（找到 73），P4I 扫描完整 frame（找到 73）。两者使用相同的
  Python frame 和分类器，因此其重建 key 集相同（各预期 73）。
- P4J 重建：ContextBench all-languages（limit 480）+ RepoQA 非 Python（每语言
  limit 60），FD1 BEA-4/5 精确 key 排除（Python 经 python-ordinal；非 Python
  按构造不相交），baseline 文件缺失选择（预期总数 333，其中 committed P4J split
  为 61 Python 与 272 non-Python）。

## 规范重叠 key

- Python 行：`("python", benchmark, python_ordinal)` — 跨 P4H/P4I/P4J Python
  扫描匹配，因为任何抓取中第 N 个 Python 行是相同的数据集行。
- 非 Python 行：`("non_python", source_frame, language, raw_idx)` — P4J 独有，
  按构造与 P4H/P4I（仅 Python）不相交。

所有 key 集为 private（仅内存或 `/tmp`）。不公开序列化任何规范 key、raw key、
row ID 或私有 hash。

## 重建与重叠计算

- 重建需要网络访问 + OpenLocus 二进制 + FD1 private decomposition。若任何前置
  条件失败，状态为 `fail_schema_contract`（fail-closed）或
  `unavailable_with_reason`（无网络）。
- 若重建计数无法精确匹配预期聚合（73/73/333），状态为
  `no_go_exact_overlap_resolution_unavailable`（保守，从不伪造 key 或使用
  公开 aggregate 近似）。
- 重叠：`p4j_overlap_with_p4h_count` = |P4J keys ∩ P4H keys|；
  `p4j_overlap_with_p4i_count` = |P4J keys ∩ P4I keys|。
- 锁定蓄水池 = P4J keys − FD1 prior − P4H keys − P4I keys。由于 P4H 和 P4I 使用
  相同 Python frame，减去两者会移除同一组 Python key 一次。非 Python P4J rows
  按构造与 P4H/P4I 不相交；任何 Python contribution 都由 exact overlap 决定，而
  不是由公开 aggregate 预设。

## 硬有效性门

- `p4h_exact_keys_reconstructed=true` 且 `p4i_exact_keys_reconstructed=true`
  且 `p4j_exact_keys_reconstructed=true` 才能进行重叠解析。
- `locked_cross_source_reservoir_count >= 80` 作为蓄水池可用性证据。
- FD1 精确 prior 排除已使用；不序列化私有 raw key/id/规范 key。
- `exact_keys_publicly_serialized=false`；
  `private_key_hashes_publicly_serialized=false`。
- Aggregate-only、records-only 公开 artifact：公开指标无动态 dict。
- `forbidden_scan.status=pass`。
- 无 provider 调用。无 P2/P3/P4 调度器臂。无 selector/reranker。无
  method-winner 逻辑。无 runtime/default 提升。
- 阻塞性失败（扫描失败、扫描未尝试、clone 失败、asset 下载/解压失败、意外
  异常、FD1 replay/schema 不匹配）不能作为 overlap-resolution-unavailable
  报告；它们产生 `fail_schema_contract`（fail-closed）。

## 状态

- `cross_source_locked_reservoir_ready_for_locked_p4_validation_design` — 仅当 P4H 计数
  =73、P4I 计数=73、P4J 计数=333、FD1 prior 排除已使用、精确 P4H/P4I/P4J
  重建成功、`locked_cross_source_reservoir_count >= 80`、公开 artifact
  aggregate-only、`forbidden_scan.status=pass` 时。这**仅**授权设计后续的
  locked-denominator 验证阶段。它**不**运行调度器，**不**执行 P4 验证，
  **不**授权 P5、BEA-v1-A、runtime 提升、method-winner 主张、broad retrieval
  扩展、selector/reranker 执行、frozen P4 重跑或 frozen P4 验证。
  `locked_p4_validation_design_authorized=true` 和 `scheduler_validation_authorized=false` 仅在 `stop_go_records` 内表达；
  顶层 guard `locked_p4_validation_executed` 保持 false。
- `no_go_locked_cross_source_reservoir_insufficient` — 精确重叠已解析，但
  `locked_cross_source_reservoir_count < 80`。
- `no_go_exact_overlap_resolution_unavailable` — 任何精确 key 重建无法确定性
  复现或无法匹配预期计数（73/73/333）。不伪造 key；不匹配原因仅以 aggregate
  披露。
- `unavailable_with_reason` — 默认无网络 artifact（诚实，非 pass）。
- `fail_schema_contract` / `fail_forbidden_scan` — 隐私/schema/provenance 失败。
  任何 `fail_*` 状态对网络-enabled 的真实运行都不是 CI-valid。

## 停止规则（精确）

1. 若重建未尝试（网络禁用、前置条件缺失），默认 artifact 为
   `unavailable_with_reason`（仅无网络路径）。
2. 若重建期间发生阻塞性失败（raw 抓取失败、clone 失败、asset 下载/解压失败、
   意外异常、FD1 replay/schema 不匹配），状态为 `fail_schema_contract`
   （fail-closed）。
3. 若重建完成但任何计数无法精确匹配预期（P4H≠73、P4I≠73 或 P4J≠333），状态
   为 `no_go_exact_overlap_resolution_unavailable`。
4. 若重建完成且所有计数匹配但 `locked_cross_source_reservoir_count < 80`，
   状态为 `no_go_locked_cross_source_reservoir_insufficient`。
5. 若重建完成且所有计数匹配且 `locked_cross_source_reservoir_count >= 80`，
   状态为 `cross_source_locked_reservoir_ready_for_locked_p4_validation_design`。这仅
   授权设计后续 locked-denominator 验证阶段；它不运行任何调度器或验证。

## 公开 artifact 契约

必需的 aggregate-only 记录表（records-only；无动态 dict）：

- `source_run_records`
- `reconstruction_records`
- `overlap_records`
- `stop_go_records`
- `gate_records`
- `private_manifest_records`
- `failure_category_count_records`
- `framing`
- `forbidden_scan`

不序列化任何规范 key、raw key、row ID、仓库 URL、路径、query、gold 文件、候选
列表、snippet、私有精确 key hash 或私有路径 hash。`private_manifest_records`
中的 `manifest_hash` 是仅作 provenance 的文件级完整性 hash。
`exact_keys_publicly_serialized=false`。

## Workflow

手动 workflow
`bea-v1-p4k-exact-overlap-resolution-locked-reservoir-audit.yml` 仅通过
`workflow_dispatch` 运行，接受 `enable_external_benchmark_network`。它构建
OpenLocus release CLI，运行 self-test，在 `/tmp` 下重新生成 FD1 private
decomposition，验证 239/86040 replay，运行 P4K 精确重叠解析重建，fail-closed
验证报告，并上传 aggregate 报告。私有重建 JSONL/key manifest 仅写入 `/tmp`，
从不上传。workflow 不使用 model/provider secret。私有目录使用 `/tmp`，不使用
`$RUNNER_TEMP`；只有最终公开报告暂存于 `$RUNNER_TEMP` 供上传。失败时上传
prevalidation artifact 供诊断。

## 本地验证

```text
python3 -m py_compile eval/bea_v1_p4k_exact_overlap_resolution_locked_reservoir_audit.py  => PASS
python3 eval/bea_v1_p4k_exact_overlap_resolution_locked_reservoir_audit.py --self-test  => PASS (106/106 checks)
python3 eval/bea_v1_p4k_exact_overlap_resolution_locked_reservoir_audit.py \
  --out artifacts/bea_v1_p4k_exact_overlap_resolution_locked_reservoir_audit/bea_v1_p4k_exact_overlap_resolution_locked_reservoir_audit_report.json  => PASS
  (默认无网络 status: unavailable_with_reason,
   forbidden_scan=pass, locked_cross_source_reservoir_count=0,
   exact_overlap_resolution_attempted=false,
   self_test_checks_total=106, self_test_checks_passed=106)
```

## CI 结果

Manual network-enabled CI run `28151914531` 绿色完成（1h50m01s）。公开 artifact
status 为 `cross_source_locked_reservoir_ready_for_locked_p4_validation_design`。

P4K 使用 `/tmp` 下的 FD1 private replay 成功重建 P4H、P4I、P4J 的 exact selected
raw-key sets：P4H `73/73`，P4I `73/73`，P4J `333/333`，并复现 committed split
`61` Python + `272` non-Python。Exact overlap 显示 P4J 的 61 条 Python rows 全部与
P4H/P4I Python-frame reservoir 重叠；扣除 overlap 后，locked cross-source reservoir
为 `272/80`，全部来自 non-Python cross-source frame。

聚合 CI 指标：

- `status=cross_source_locked_reservoir_ready_for_locked_p4_validation_design`
- `locked_cross_source_reservoir_count=272`
- `non_python_locked_reservoir_count=272`
- `python_locked_reservoir_count=0`
- `p4h_reconstructed_denominator_count=73`
- `p4i_reconstructed_reservoir_count=73`
- `p4j_reconstructed_upper_bound_count=333`
- `p4j_reconstructed_python_count=61`
- `p4j_reconstructed_non_python_count=272`
- `p4j_overlap_with_p4h_count=61`
- `p4j_overlap_with_p4i_count=61`
- `locked_p4_validation_design_authorized=true` 仅在 `stop_go_records` 内表达
- `scheduler_validation_authorized=false`，`locked_p4_validation_executed=false`，
  `frozen_p4_rerun_authorized=false`，`p5_authorized=false`，`v1_a_authorized=false`
- `self_test_checks_total=106`，`self_test_checks_passed=106`
- `forbidden_scan.status=pass`

这解决了 P4J 的 unqualified-reservoir blocker，并且只授权设计后续
locked-denominator P4 validation phase。P4K 本身没有运行 scheduler arms，也不授权
P5、BEA-v1-A、runtime promotion、method-winner 声明、frozen P4 rerun 或 broad
retrieval expansion。

## 注意事项

- P4K 是分母/来源审计。它不是 benchmark/leaderboard、default-policy、
  method-winner、runtime-promotion、downstream-value、P5、BEA-v1-A、调度器验证、
  检索扩展、selector/reranker、frozen-P4-validation、frozen-P4-rerun 或
  runtime/default 提升授权主张。
- `cross_source_locked_reservoir_ready_for_locked_p4_validation_design` **不**授权
  frozen P4 重跑（`frozen_p4_rerun_authorized=false`），也没有执行 frozen/locked P4
  验证（`frozen_p4_validation_executed=false`，`locked_p4_validation_executed=false`）；
  它仅授权设计后续的 locked-denominator 验证阶段。
- 重建重新运行相同的确定性扫描。若原始 P4H/P4I/P4J 运行与 P4K 重建之间的来源
  排序或 baseline 结果漂移，计数可能不匹配，产生
  `no_go_exact_overlap_resolution_unavailable`。
- P4H 和 P4I 重建共享相同的 Python-frame 扫描（相同 key 集），因为两者扫描了
  相同的 Python frame 和分类器。
- Gold/private label 仅用于评估/scoring 文件缺失。
- 延迟完全不测量或使用（分母审计，非调度器）。
