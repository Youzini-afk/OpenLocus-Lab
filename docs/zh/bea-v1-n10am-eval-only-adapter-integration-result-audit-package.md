# BEA-v1-N10AM Eval-Only Adapter Integration Result Audit Package

日期：2026-06-29

BEA-v1-N10AM 是 N10AL eval-only adapter integration smoke 的 public-only audit package。它只读取 public N10AL/N10AK/N10AJ/N10AB/N10AD artifacts。它不读取 private rows，不 recompute metrics，不 hook existing evaluators，也不修改 runtime/default behavior。

## 结果

```text
status: eval_only_adapter_integration_result_audit_package_complete_n10an_authorized
self-test: 12 / 12
forbidden scan: pass
eligible denominator: 213
baseline top10/top20 span overlap: 9 / 10
pm50 top10/top20 span overlap: 19 / 23
delta top10 vs baseline: 10
original span-hit lost: 0
candidate pool changed: false
order changed: false
private reads: 0
empirical recomputes: 0
```

## Audit findings

- N10AL status 与 forbidden scan 通过。
- N10AL aggregate result 匹配 N10AB 与 N10AD：213 rows、baseline 9/10、pm50 19/23、delta +10、0 original span-hit losses。
- Candidate pool 与 order 保持不变。
- N10AK 与 N10AJ public statuses 通过。
- N10AM 不进行 private read，也不进行 empirical recompute。

## Claim boundary

Allowed claim：eval-only adapter reproduces the scoped N1 pm50 aggregate。Forbidden claims 仍包括 runtime/default promotion、existing evaluator hook-in、retrieval/rerun、candidate generation、selector/reranker、P5/BEA-v1-A、method-winner 与 downstream-value claims。

## 决策

N10AM 只授权 `BEA-v1-N10AN Default-Off Existing-Evaluator Hook Feasibility Preflight`，这是 public/static preflight。N10AM 本身不授权 existing evaluator hook-in、runtime/default enablement、private reads、retrieval/rerun、candidate generation、selector/reranker execution、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10am_eval_only_adapter_integration_result_audit_package.py`
- Report: `artifacts/bea_v1_n10am_eval_only_adapter_integration_result_audit_package/bea_v1_n10am_eval_only_adapter_integration_result_audit_package_report.json`
