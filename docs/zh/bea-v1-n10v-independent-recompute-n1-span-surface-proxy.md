# BEA-v1-N10V Independent Recompute N1 Span-Surface Proxy

日期：2026-06-29

BEA-v1-N10V 使用 same scoped private span rows 与 same four proxy arms，独立 recompute N10T N1 span-surface proxy result。它直接实现 transform logic，不 import 或调用 N10T evaluator。Public output 只包含 aggregate counts、buckets、booleans 与 claim-boundary records。

## 结果

```text
status: independent_recompute_n1_span_surface_proxy_pass_n10w_authorized
self-test: 15 / 15
forbidden scan: pass
private span rows read: 213
other private files read: 0
eligible denominator: 213
reachable in pool: 52
baseline top10/top20: 0 / 0
best arm: span_extra_depth_promote_before_primary_prefix_4
best top10/top20: 34 / 44
best delta top10 vs baseline: 34
regressions: 0
threshold passed: true
comparison to N10T: match
```

## Independent recompute boundary

- 只读取 N10U 授权的 same scoped private N1 span rows。
- 不读取其他 private files 或 broad private storage。
- 不 import 或调用 N10T code / transform functions。
- 只在 ordering 后进行 file-level matching；ordering 不使用 gold signal。
- 保持 fixed candidate pool：不 add/remove/generate/materialize candidates。
- 不运行 retrieval，不 rerun P4L/N1/N2/N3，不执行 OpenLocus，不 search new arms，不运行 selector/reranker logic，不进行 support labeling，不进入 P5/BEA-v1-A，不运行 counterfactuals，也不改变 runtime/default policy。

## 决策

N10V 精确验证 N10T aggregate proxy result，并只授权 `BEA-v1-N10W N1 Span-Surface Proxy Replication Package`。它不授权 broad private reads、runtime/default promotion、method-winner 声明、downstream-value 声明、P5、BEA-v1-A、selector/reranker execution、retrieval、reruns、new-arm search、counterfactuals 或 policy changes。

## Artifact

- Script: `eval/bea_v1_n10v_independent_recompute_n1_span_surface_proxy.py`
- Report: `artifacts/bea_v1_n10v_independent_recompute_n1_span_surface_proxy/bea_v1_n10v_independent_recompute_n1_span_surface_proxy_report.json`
