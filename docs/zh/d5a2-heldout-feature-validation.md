# D5-A2 Heldout 特征验证 Smoke（公开仅聚合 Artifact）

## 范围与声明边界

D5-A2 验证 D5-A1 的 retrieval-derived 特征 bucket 是否在 **新鲜的
heldout 外部检索样本** 上复现。D5-A2 加载 D5-A1 已提交 artifact 作为预
注册特征源，对新的 heldout ContextBench verified Python 行 21-40 与
RepoQA Python needle 11-20 运行方法 bm25/regex/symbol，计算相同的
retrieval-derived utility proxy，并检查 heldout 指标是否支持 D5-A1 特
征 bucket。

D5-A2 明确 **不是**校准，**不是**已校准模型声明，**不是** policy/
default 推荐，**不是**方法 winner 声明，**不是**外部基准测试性能声
明，**不是**下游 agent 价值声明，**不是** leaderboard 条目，**也不
是** runtime/retriever/pack/backend/default-policy/EvidenceCore 语义
变更。它仅验证 D5-A1 的检索特征稳定性组件；它 **不**验证 live-
provider/下游对齐。它 **不**进行任何 provider 调用，**不**进行任何远
程 provider 调用。

- 声明级别：`heldout_retrieval_feature_validation_smoke_only`。
- 模式：`heldout_contextbench_repoqa_feature_validation`；阶段
  `D5-A2`。
- 状态枚举：`heldout_feature_validation_pass`（所有特征复现）；
  `partial`（混合或未支持但有数据）；`unavailable_with_reason`（无
  heldout 数据）；`fail_forbidden_scan`；`fail_schema_contract`。
- 验证结果标签（固定 allowlist）：
  `retrieval_feature_validation_supported`（全部复现）、
  `retrieval_feature_validation_mixed`（部分复现）、
  `retrieval_feature_validation_not_supported`（均未复现）、
  `unavailable_with_reason`。

## D5-A1 输入（预注册特征源）

D5-A2 加载 D5-A1 已提交 artifact 并提取：

- `readiness_bucket`（如 `ready_for_manual_review`）。
- `cross_signal_alignment`（如
  `retrieval_robust_positive_plus_live_positive`）。
- `calibration_feature_records`（预注册特征 bucket）。

Fail-closed：D5-A1 缺失、schema 不匹配、status 不匹配、不安全声明
flag 或 `forbidden_scan.status != pass` => status
`unavailable_with_reason` 且 CLI 非零退出。

## Heldout 测量

D5-A2 运行新鲜的 heldout 检索测量（**不**是重读现有 C5/F1 artifact）：

- **ContextBench verified Python 行 21-40**：从 HF datasets-server
  抓取 (offset+limit)=40 行，仅评估 heldout 切片 [20, 40)。
- **RepoQA Python needle 11-20**：从 RepoQA release asset 解析
  (offset+limit)=20 个 needle，仅评估 heldout 切片 [10, 20)。
- 方法：仅 `bm25,regex,symbol`。
- 无 provider 调用。

## Utility 公式（固定诊断 proxy；与 F1-C/F1-D 不变）

```text
utility = file_hit + 0.25*mrr + 0.5*span_f0.5 - miss_penalty
miss_penalty = 0.25 if file_recall@10 == 0 else 0
```

## 验证规则

D5-A2 检查四个检索特征验证（仅 records 形态）：

1. **`bm25_vs_empty_retrieval_utility_magnitude`**：预注册 bucket
   `weak_positive`/`strong_positive` => heldout bm25
   retrieval_utility > 0（empty 按构造为 0）。
2. **`bm25_vs_empty_sign_stability`**：预注册
   `stable_positive` => heldout bm25 file_recall@10 在两个基准上均
   > 0。
3. **`regex_vs_bm25_sign_stability`**：预注册
   `stable_negative` => heldout regex retrieval_utility < bm25
   retrieval_utility。
4. **`symbol_vs_bm25_sign_stability`**：预注册
   `stable_negative` => heldout symbol retrieval_utility < bm25
   retrieval_utility。

每条记录：`{feature_name, preregistered_bucket, heldout_metric,
heldout_direction, supported}`。

## 公开 artifact 形态

仅 records 形态列表（无动态 dict 镜像）：

- `d5a1_input_record`：单条记录（schema、status、就绪 bucket、跨
  信号对齐、claim-safe、特征/信号计数）。
- `heldout_benchmark_method_records`：固定 record 列表
  `{benchmark, method, sample_count, metrics}`。
- `validation_records`：固定 record 列表（字段如上）。
- `validation_summary_records`：固定 record 列表
  `{outcome, outcome_count}`（allowlist 中每个 outcome 一条）。

## CLI

```bash
python3 -m py_compile eval/d5a2_heldout_feature_validation.py
python3 eval/d5a2_heldout_feature_validation.py --self-test
python3 eval/d5a2_heldout_feature_validation.py \
    --contextbench-row-offset 20 --contextbench-row-limit 20 \
    --repoqa-needle-offset 10 --repoqa-needle-limit 10 \
    --methods bm25,regex,symbol \
    --out artifacts/d5a2_heldout_feature_validation/\
d5a2_heldout_feature_validation_report.json
```

## 验证

```text
python3 -m py_compile eval/d5a2_heldout_feature_validation.py  => PASS
python3 eval/d5a2_heldout_feature_validation.py --self-test  => PASS (88/88 checks)
python3 eval/d5a2_heldout_feature_validation.py \
  --contextbench-row-offset 20 --contextbench-row-limit 20 \
  --repoqa-needle-offset 10 --repoqa-needle-limit 10 \
  --methods bm25,regex,symbol \
  --out artifacts/d5a2_heldout_feature_validation/\
d5a2_heldout_feature_validation_report.json  => PASS
  (status: heldout_feature_validation_pass,
   forbidden_scan: pass, self_test_passed: true,
   validation_outcome: retrieval_feature_validation_supported,
   contextbench_rows_fetched: 20, repoqa_needles_seen: 10,
   network_calls: 2, provider_calls: 0,
   heldout_feature_validation_executed: true,
   downstream_agent_value_proven: false,
   true_e_s_calibration_claimed: false,
   calibrated_model_claimed: false,
   policy_recommendation_claimed: false,
   method_winner_claimed: false,
   external_benchmark_performance_claimed: false,
   promotion_ready: false,
   default_should_change: false)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

本地 heldout run 产生以下聚合记录（不提交 row/needle ID/repo URL/
commit/query/path/span/snippet/JSONL/evidence/per-unit metric/hash/
stdout/stderr/clone path/provider 字段/winner/default/calibration 声
明）：

```text
status: heldout_feature_validation_pass
validation_outcome: retrieval_feature_validation_supported
contextbench_rows_fetched: 20
repoqa_needles_seen: 10
network_calls: 2
forbidden_scan: pass
provider_calls: 0
d5a1_input_record:
  readiness_bucket: ready_for_manual_review
  cross_signal_alignment: retrieval_robust_positive_plus_live_positive
  feature_count: 7, signal_count: 9
heldout_benchmark_method_records:
  contextbench/bm25: sample_count=20, file_recall@10=0.7, retrieval_utility=0.815104
  contextbench/regex: sample_count=20, file_recall@10=0.0, retrieval_utility=-0.25
  contextbench/symbol: sample_count=20, file_recall@10=0.0, retrieval_utility=-0.25
  repoqa/bm25: sample_count=10, file_recall@10=0.5, retrieval_utility=0.553674
  repoqa/regex: sample_count=10, file_recall@10=0.0, retrieval_utility=-0.25
  repoqa/symbol: sample_count=10, file_recall@10=0.0, retrieval_utility=-0.25
validation_records:
  bm25_vs_empty_retrieval_utility_magnitude: prereg=weak_positive, heldout=+0.727961, dir=positive, supported=True
  bm25_vs_empty_sign_stability: prereg=stable_positive, heldout=+0.6, dir=positive, supported=True
  regex_vs_bm25_sign_stability: prereg=stable_negative, heldout=-0.977961, dir=negative, supported=True
  symbol_vs_bm25_sign_stability: prereg=stable_negative, heldout=-0.977961, dir=negative, supported=True
validation_summary_records:
  retrieval_feature_validation_supported: count=4
  retrieval_feature_validation_mixed: count=0
  retrieval_feature_validation_not_supported: count=0
  unavailable_with_reason: count=0
```

所有 4 个 D5-A1 检索特征在 heldout 数据上复现
（`retrieval_feature_validation_supported`，supported 计数=4/4）。

## 注意事项

- D5-A2 是公开仅聚合 heldout 特征验证 smoke artifact。它是
  eval/diagnostic only。它 **不是**校准、**不是**已校准模型声明、
  **不是** policy/default 推荐、**不是** benchmark 结果、**不是**下
  游 utility、**不是** true E/S 校准、**不是**外部基准测试性能声明、
  **不是** leaderboard 条目、**不是**方法 winner、**也不是**
  promotion。
- D5-A2 仅验证 D5-A1 的检索特征稳定性组件。它 **不**验证 live-
  provider/下游对齐。
- D5-A2 运行新鲜的 heldout 检索测量（行 21-40，needle 11-20）。它
  **不**重读现有 C5/F1 artifact。
- D5-A2 **不**进行任何 provider 调用，**不**进行任何远程 provider 调
  用。所有临时数据仅保留在内存或 `/tmp`。
- heldout run 发现 ContextBench heldout bm25 file_recall@10=0.7（对比
  原始 D5-A1 行 1-20 的 0.35），支持 bm25 正向检索特征在此 heldout
  切片上成立（且在该切片上更强）。
- 所有无声明 / 无运行时变更标志保持 false；诊断标志保持 true；
  `heldout_feature_validation_executed=true` 仅在真实 heldout run 实际
  执行时。
