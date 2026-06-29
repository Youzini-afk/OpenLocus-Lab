# BEA-v1-N10AP Adapter-Enabled Variant Evaluator Result Audit Package

日期：2026-06-29

BEA-v1-N10AP 是 N10AO adapter-enabled variant evaluator 的 public-only audit package。它只读取 public N10AO/N10AN/N10AM/N10AL/N10AJ artifacts。它不读取 private rows，不 recompute metrics，不修改代码，不 hook existing evaluators，也不改变 runtime/default behavior。

## 结果

```text
status: adapter_enabled_variant_evaluator_result_audit_package_complete_n10aq_authorized
self-test: 14 / 14
forbidden scan: pass
explicit enablement used in N10AO: true
default enabled: false
private read by default: false
private reads in N10AP: 0
empirical recomputes in N10AP: 0
private span rows audited from N10AO: 213
baseline top10/top20 span overlap: 9 / 10
pm50 top10/top20 span overlap: 19 / 23
delta top10 vs baseline: 10
original span-hit lost: 0
candidate pool changed: false
order changed: false
```

## Audit findings

- N10AO status 与 forbidden scan 通过。
- N10AO 使用 explicit scoped enablement，同时保持 default mode disabled 与 private-read-by-default false。
- N10AO aggregate result 匹配 N10AL/N10AB/N10AD chain：213 rows、baseline 9/10、pm50 19/23、delta +10、0 original span-hit losses。
- Candidate pool 与 order 保持不变。
- N10AN strategy 为 `new_adapter_enabled_variant_evaluator`，并且不修改 existing validated evaluators。
- N10AM/N10AL/N10AJ public statuses 通过。
- N10AP 不进行 private read，也不进行 empirical recompute。

## Claim boundary

Allowed claim：new eval-only variant evaluator reproduces the scoped N1 pm50 aggregate under explicit enablement。Forbidden claims 仍包括 runtime/default promotion、existing evaluator hook-in、modification of existing validators、retrieval/rerun、candidate generation、new window tuning、selector/reranker、P5/BEA-v1-A、method-winner 与 downstream-value claims。

## 决策

N10AP 只授权 `BEA-v1-N10AQ Heldout External Validation Source-Discovery Preflight`，即用于 heldout 或 external validation 的 public/source-discovery preflight。它不授权 direct experiment execution、private reads、runtime/default enablement、retrieval/rerun、candidate generation、new arms/window tuning、selector/reranker execution、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10ap_adapter_enabled_variant_evaluator_result_audit_package.py`
- Report: `artifacts/bea_v1_n10ap_adapter_enabled_variant_evaluator_result_audit_package/bea_v1_n10ap_adapter_enabled_variant_evaluator_result_audit_package_report.json`
