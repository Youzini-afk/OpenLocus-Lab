# BEA-v1-P1-3 Agent-Generated Support Label Fill

日期：2026-06-28

BEA-v1-P1-3 使用确定性的 agent-generated proxy labels 填充 P1-1 project-private support-label queue。该填充只使用已有 queue/design 字段，不读取 raw source，不调用 provider，也不执行 support counterfactual。

## 结果

```text
status: agent_generated_support_label_fill_pass
self-test: 10 / 10
forbidden scan: pass
private queue rows read: 18
agent-generated private labels written: 18
P0-5-compatible labels: 18
P1-2 intake-valid labels: 18
label errors: 0
```

生成的 private JSONL 保留在 `.openlocus/research-private/` 下。Public artifact 只发布 scanner-validated manifests、anonymous local label rows、bucket summaries、gates 和 stop/go records。它不发布 design ids、queue item ids、private paths、source paths、spans、snippets、candidates、ranks、scores、prompts、responses 或 provider payloads。

## Label policy

由于没有使用 raw source，P1-3 将 target/support hit buckets 保持为 `unknown_not_labeled`，派生 `conjunction_bucket=ambiguous_unlabeled`，只复制 queue/design 中的 support-relation bucket，并根据 queue guidance 与 relation 使用保守的确定性 role/risk buckets。Private rows 包含 `label_origin=agent_generated`、`label_method_bucket=deterministic_queue_field_heuristic` 和 `human_calibrated=false`。

## 决策

P1-3 只是 automated private support-label fill。它不是 human labeling，不是 human-calibrated E/S evidence，不是 support utility evidence，也不是 mechanism evidence。它不授权 support counterfactual execution、support marginal-utility 声明、P5、BEA-v1-A、selector/reranker execution、implementation、runtime/default promotion、broad retrieval expansion、method-winner 声明或 downstream-value 声明。

## Artifact

- Script：`eval/bea_v1_p1_3_agent_generated_support_label_fill.py`
- Report：`artifacts/bea_v1_p1_3_agent_generated_support_label_fill/bea_v1_p1_3_agent_generated_support_label_fill_report.json`
- Private labels：`.openlocus/research-private/` 下的 project-ignored JSONL
