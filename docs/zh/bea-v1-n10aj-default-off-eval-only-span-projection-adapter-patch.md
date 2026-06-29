# BEA-v1-N10AJ Default-Off Eval-Only Span Projection Adapter Patch

日期：2026-06-29

BEA-v1-N10AJ 添加新的 eval-only span projection adapter，并仅用 synthetic/public-fixture checks 验证。它不修改 N10T、N10X、N10AB、N1/N2/N3/P4L evaluators、runtime/retrieval/selector/reranker/config files，也不修改 helper module。

## 结果

```text
status: default_off_eval_only_span_projection_adapter_patch_pass_n10ak_authorized
self-test: 16 / 16
forbidden scan: pass
adapter functions: 2
synthetic projections: 8
private reads: 0
filesystem IO: 0
existing evaluator hook-in: false
runtime/default config changed: false
```

## Adapter API

- `project_evidence_span_record(record, *, expansion_each_side, enabled=False)` 返回单条 evidence span record 的 non-mutating copy。`enabled=False` 时 copy 不变；`enabled=True` 时只通过 N10AH helper 扩展 `start_line` 与 `end_line`。
- `project_evidence_spans(records, *, expansion_each_side, enabled=False)` 投影一个 sequence，并保持 count 与 order。

该 adapter 从 pure N10AH helper 导入 `expand_evidence_span_record`。它不需要 path、content、gold、private storage、filesystem IO、retrieval、runtime configuration、adaptive tuning 或 selector/reranker behavior。Expansion 是 fixed，且由 caller 提供。

## Synthetic checks

N10AJ 验证 disabled unchanged/non-mutating behavior、enabled pm20/pm50 expansion、min-line clamp、order/count preservation、no path/content/gold requirement、invalid-input propagation、adapter no-IO static safety，以及 changed-file allowlist compliance。

## 决策

N10AJ 只授权 `BEA-v1-N10AK Eval-Only Adapter Public Fixture Integration Audit Package`。它不授权 existing evaluator hook-in、runtime/default enablement、private reads by default、retrieval/rerun、candidate generation、selector/reranker execution、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Artifact

- Adapter: `eval/bea_v1_span_window_projection_adapter.py`
- Script: `eval/bea_v1_n10aj_default_off_eval_only_span_projection_adapter_patch.py`
- Report: `artifacts/bea_v1_n10aj_default_off_eval_only_span_projection_adapter_patch/bea_v1_n10aj_default_off_eval_only_span_projection_adapter_patch_report.json`
