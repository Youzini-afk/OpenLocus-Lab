# BEA-v1-P2-1 Ordered-Prefix Stop Evidence Surface

日期：2026-06-28

BEA-v1-P2-1 将已提交的 ordered-prefix / early-stop evidence 汇总为 scanner-safe public rows。它区分 aggregate-only evidence 与 private-trace readiness，不运行 policy changes、policy tuning、selector/reranker changes、implementation、runtime promotion 或 counterfactuals。

## 结果

```text
status: no_go_p2_1_ordered_prefix_only_aggregate
self-test: 8 / 8
forbidden scan: pass
sanitized stop evidence rows: populated
source artifact coverage: >= 2
early-stop failure-category rows: > 0
private trace rows: unavailable locally
private-trace readiness: false
```

该 surface 从 P0-8、FD1、BEA-3/4/5 以及 v0.4 P1/P2/P3 artifacts 提取 aggregate rows。这些 rows 可作为已提交证据，说明 early-stop / ordered-prefix behavior 存在；但大多数字段仍是 aggregate proxies。可选的 project-private ordered-prefix trace JSONL 本地不存在，因此 row-level prefix position、cost、budget、marginal gain 与 continue-counterfactual readiness 未通过。

所有 public per-row identifiers 都会在合并后重新生成匿名本地 id，因此 artifact 内唯一，且不暴露 source ids。

## 决策

P2-1 只是 data-surface extraction。它不授权 ordered-prefix stop-policy changes、trace counterfactual execution、support counterfactual execution、policy tuning、implementation、selector/reranker execution、P5、BEA-v1-A、runtime/default promotion、broad retrieval expansion、method-winner claims 或 downstream-value claims。

## Artifact

- Script：`eval/bea_v1_p2_1_ordered_prefix_stop_evidence_surface.py`
- Report：`artifacts/bea_v1_p2_1_ordered_prefix_stop_evidence_surface/bea_v1_p2_1_ordered_prefix_stop_evidence_surface_report.json`
