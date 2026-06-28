# BEA-v1-P3-8I Explicit Proxy Fixture Logger Smoke Design

日期：2026-06-28

BEA-v1-P3-8I 是 future explicit proxy fixture logger smoke evaluator 的 design-only phase。它只使用 public P3-8H/P3-8G artifacts，不读也不写 private files。

## 结果

```text
status: explicit_proxy_fixture_logger_smoke_design_pass_p3_8j_authorized
self-test: 9 / 9
forbidden scan: pass
helper capture plans: 5
P3-8J evaluator implementation authorized: true
```

该设计保持 proxy mode 与 P3-8 empirical mode 分离。它要求 separate evaluator、default-disabled proxy mode、explicit proxy argument、P3-8G proxy fixtures、helper-only proxy fixture capture，以及 sanitized public projection only。

## 边界

P3-8I 不修改 P3-8、helper、target、runtime、retrieval、selector 或 reranker files。它不运行 capture、retrieval、P4L/N1/N2、support labeling、counterfactuals、policy tuning、P5、BEA-v1-A、runtime/default promotion 或 broad retrieval。它不读也不写 private files。

## Handoff

P3-8I 只授权 **BEA-v1-P3-8J Explicit Proxy Fixture Logger Smoke Evaluator Implementation**：separate evaluator only，no empirical capture。P3-8J 可以读取 P3-8G private proxy fixture files，import helper module，对 proxy fixtures 运行 helper build/validate/sanitize，并输出 sanitized public artifact。它不得修改 P3-8，不得写 private trace rows，不得 import/call target evaluators，不得运行 retrieval/P4L/N1/N2/support/counterfactual/policy/P5/BEA-v1-A，也不得声明 empirical trace capture。

## Artifact

- Script：`eval/bea_v1_p3_8i_explicit_proxy_fixture_logger_smoke_design.py`
- Report：`artifacts/bea_v1_p3_8i_explicit_proxy_fixture_logger_smoke_design/bea_v1_p3_8i_explicit_proxy_fixture_logger_smoke_design_report.json`
