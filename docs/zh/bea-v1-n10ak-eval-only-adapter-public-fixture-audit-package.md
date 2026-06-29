# BEA-v1-N10AK Eval-Only Adapter Public Fixture Integration Audit Package

日期：2026-06-29

BEA-v1-N10AK 是 N10AJ default-off eval-only adapter patch 的 public/synthetic-only audit package。它只读取 public N10AJ/N10AI/N10AH artifacts，并执行 static adapter/helper source checks。它不读取 private rows，也不 recompute empirical N10AB/N10AF metrics。

## 结果

```text
status: eval_only_adapter_public_fixture_audit_package_complete_n10al_authorized
self-test: 13 / 13
forbidden scan: pass
N10AJ adapter status: pass
N10AI target: future_eval_only_span_projection_adapter
N10AH helper status: pass
synthetic projection checks: 8 / 8
private reads: 0
empirical recomputes: 0
```

## Audit findings

- N10AJ status 与 forbidden scan 通过。
- N10AI 选择了 future eval-only span projection adapter target。
- N10AH helper artifact 有效，且 helper source 存在。
- Adapter source 存在、导入 helper，并且没有 forbidden IO imports/calls。
- N10AJ synthetic projections 通过，count/order preservation 通过，no-IO/private boundary 通过，没有 existing evaluator hook-in，runtime/default configuration 未改变。

## Claim boundary

Allowed claim：default-off eval-only adapter exists and is synthetically validated。Forbidden claims 仍包括 runtime/default promotion、existing evaluator hook-in、private read by default、retrieval/rerun、candidate generation、selector/reranker、P5/BEA-v1-A、method-winner 与 downstream-value claims。

## 决策

N10AK 只授权 `BEA-v1-N10AL Scoped Eval-Only Adapter Integration Smoke`。N10AK 本身不授权 existing evaluator hook-in、runtime/default enablement、private reads by default、retrieval/rerun、candidate generation、selector/reranker execution、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10ak_eval_only_adapter_public_fixture_audit_package.py`
- Report: `artifacts/bea_v1_n10ak_eval_only_adapter_public_fixture_audit_package/bea_v1_n10ak_eval_only_adapter_public_fixture_audit_package_report.json`
