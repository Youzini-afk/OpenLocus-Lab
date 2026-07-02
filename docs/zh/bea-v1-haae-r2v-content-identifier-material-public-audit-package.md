# BEA-v1-HAAE-R2V Content-Identifier Material Public Audit Package

日期：2026-07-03

BEA-v1-HAAE-R2V Content-Identifier Material Public Audit Package 是对 committed R2U
aggregate artifact 的 public-only audit。它不读取 private root 或 private material，
也不 recompute、不生成 material、不计算 experiment metrics、不 retrieval、不运行
runtime/source scan、不使用 CI/network/provider，也不运行 scheduler/selector logic。

```text
phase: BEA-v1-HAAE-R2V Content-Identifier Material Public Audit Package
status: haae_r2v_content_identifier_material_public_audit_package_complete_r2w_material_experiment_authorized
self-test: 14/14
source lock: HAAE-R2U checkpoint bb95f80
source status: haae_r2u_content_identifier_material_generation_complete_r2v_public_audit_authorized
audit: target 20; depth 40; row cap 20000; seven rank sources
policy: no path tokens; no gold ranking; no metrics; public aggregate-only
next phase: BEA-v1-HAAE-R2W Content-Identifier Material Experiment
boundary: no new material generation/retrieval/runtime/source scan/CI/network/provider/scheduler/selector/BEA-v1-A/P5/default/method/scaling/raw publication
```

R2V 只授权 R2W 使用 explicit private root 读取 existing R2U private material。它不授权
new material generation、CI、retrieval、runtime/default changes、method winner claims、
scaling claims 或 raw publication。
