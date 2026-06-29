# BEA-v1-N10AI Default-Off Span Window Helper Integration Preflight

日期：2026-06-29

BEA-v1-N10AI 仅为 static integration preflight。它识别 N10AH helper 的 safe eval-only integration target，不 patch 任何 hook、runtime path、existing evaluator、retrieval code、selector/reranker code 或 configuration。

## 结果

```text
status: default_off_span_window_helper_integration_preflight_pass_n10aj_authorized
self-test: 15 / 15
forbidden scan: pass
recommended hook target: future_eval_only_span_projection_adapter
existing runtime path: false
default-off interface defined: true
behavior risk: low
```

## Candidate hook points

- `n10ab_smoke_evaluator_expansion_loop`：eval-only，但不推荐，因为 patch existing smoke evaluator 存在 behavior-preservation risk。
- `n10x_span_overlap_evaluation_loop`：eval-only，但不推荐，因为 patch existing validation evaluator 存在 behavior-preservation risk。
- `future_eval_only_span_projection_adapter`：推荐目标。它是新的 eval-only adapter target，不是 existing runtime path，也不是 existing evaluator hook-in。

## Default-off interface

N10AJ target 必须保持 default-off 与 eval-only。它只能在 explicit evaluation call/flag 下暴露 fixed-window projection adapter；默认不进行 private read，不启用 runtime/default，不 retrieval/rerun，不 candidate generation，不 selector/reranker behavior，不进入 P5/BEA-v1-A，也不提出 method/downstream claim。

## 决策

N10AI 只授权 `BEA-v1-N10AJ Default-Off Eval-Only Span Projection Adapter Patch`。N10AI 不授权 existing evaluator hook-in、runtime/default enablement、private reads by default、retrieval/rerun、candidate generation、selector/reranker execution、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10ai_default_off_span_window_helper_integration_preflight.py`
- Report: `artifacts/bea_v1_n10ai_default_off_span_window_helper_integration_preflight/bea_v1_n10ai_default_off_span_window_helper_integration_preflight_report.json`
