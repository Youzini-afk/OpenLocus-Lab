# C5-F RepoQA 方法矩阵 Scale Smoke

日期：2026-06-21

C5-F 是 RepoQA 方法矩阵检索 smoke 的单独 10-needle scale checkpoint。它复用
C5-E 的 RepoQA asset/needle/clone/retrieval/score 管线，但保持 C5-E 不变，并写入
独立的 C5-F artifact。

## Claim 边界

C5-F 是 `repoqa_retrieval_method_matrix_scale_smoke_only`：diagnostic、aggregate-only
的外部-benchmark-形态检索 smoke。它不是外部 benchmark 性能声明、leaderboard
条目、方法 winner、default-policy 建议、下游 agent 价值证明、runtime/retriever/
pack/backend 变更或 EvidenceCore 语义变更。

所有 no-claim 标志保持 false：`external_benchmark_performance_claimed`、
`leaderboard_entry_claimed`、`downstream_agent_value_proven`、`promotion_ready`、
`default_should_change`、`baseline_is_policy_candidate`、runtime/retriever/pack/
backend/default-policy/EvidenceCore 变更标志、`provider_calls_made` 和
`remote_provider_calls_made`。

## Evaluator 与 artifact

- Evaluator：`eval/c5f_repoqa_method_matrix_scale_smoke.py`
- Artifact：
  `artifacts/c5f_repoqa_method_matrix_scale/c5f_repoqa_method_matrix_scale_report.json`
- Schema：`c5f_repoqa_method_matrix_scale_smoke.v1`
- Status：`repoqa_method_matrix_scale_smoke_pass`
- Phase：`C5-F`
- Needle limit：默认 10，硬上限 10
- Methods：`bm25,regex,symbol`
- Delta baseline：`bm25`
- Query/gold config labels：`needle_description`、`needle_path_line_range`

Raw RepoQA repo 值、commit、description、path、line range、source、生成的 JSONL、
retrieval evidence rows、stdout/stderr、clone path、row ID、hash 与 provider fields
都只临时存在，绝不提交或上传。

## 本地真实 smoke 结果

```text
python3 -m py_compile eval/c5f_repoqa_method_matrix_scale_smoke.py => PASS
python3 eval/c5f_repoqa_method_matrix_scale_smoke.py --self-test => PASS (191/191 checks)
python3 eval/c5f_repoqa_method_matrix_scale_smoke.py \
  --needle-limit 10 --language-filter python --methods bm25,regex,symbol \
  --out artifacts/c5f_repoqa_method_matrix_scale/c5f_repoqa_method_matrix_scale_report.json => PASS
```

Aggregate 本地结果：

```text
status: repoqa_method_matrix_scale_smoke_pass
needles_seen: 10
methods_successful: 3
methods_failed: 0
forbidden_scan: pass
provider_calls: 0
bm25: file_recall@10=0.5, mrr=0.369216, span_f0.5@10=0.020817, success_rate=1.0
regex: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0
symbol: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0
regex-minus-bm25 file_recall@10 delta: -0.5
symbol-minus-bm25 file_recall@10 delta: -0.5
```

这些只是 smoke diagnostics，不是性能或 default-policy 声明。

## 手动 CI

Workflow：`.github/workflows/c5-repoqa-method-matrix-scale-smoke.yml`。

手动输入：

```text
enable_external_benchmark_network=true
needle_limit=10
language_filter=python
methods=bm25,regex,symbol
```

该 workflow 仅 `workflow_dispatch`，不使用 provider credential/model environment，且只上传
aggregate C5-F report。它 fail-closed：network-enabled CI 必须产出 pass/partial
status、`needles_seen > 0`、`methods_successful > 0` 和
`forbidden_scan.status=pass`。
