# BEA-v1-HAAE-R2AF Real-File Signal Robustness Material Preflight

日期：2026-07-03

BEA-v1-HAAE-R2AF Real-File Signal Robustness Material Preflight 是 R2AE checkpoint `4be50bc` 之后的 public-only design/preflight package。它只读取 committed public R2AE artifact/docs。R2AF 本身 no private reads/writes，no execution，no source scan，no candidate/material generation。

```text
phase: BEA-v1-HAAE-R2AF Real-File Signal Robustness Material Preflight
status: haae_r2af_real_file_signal_robustness_material_preflight_complete_r2ag_material_generation_authorized
self-test: 26/26
source lock: HAAE-R2AE checkpoint 4be50bc
source status: haae_r2ae_real_file_signal_robustness_scale_decision_complete_r2af_robustness_material_preflight_authorized
R2AG design: target 20 existing R2AA task frame if available; depth 40; row cap 20000
R2AG variants: symbol/content ablation; query-token masking; shuffled content control; negative/control strengthening
R2AG boundary: explicit private root; bounded public corpus manifest; aggregate-only public artifact; no metrics in R2AG beyond material QA
authorization: authorize only R2AG material generation; no R2AH experiment; no CI/scale/default/method claim
R2AF boundary: no private reads/writes; no execution; no source scan; no candidate/material generation
```

## Decision

R2AF 打包进一步 real-file signal claim 之前所需的 robustness-material design。唯一授权的下一阶段是 **BEA-v1-HAAE-R2AG Explicit Local Bounded Robustness Material Generation**。R2AG 必须使用 explicit private root，优先使用 existing R2AA task frame（如果可用则 target 20），candidate depth 上限为 depth 40，private rows 上限为 row cap 20000，并且只发布带 bounded public corpus manifest 的 aggregate-only public artifact。

必需的 variant suite 用于在没有 path/gold leakage 的情况下测试 real-file signal robustness：symbol/content ablation、query-token masking、shuffled content control、negative/control strengthening。R2AG 只允许 material QA；no metrics in R2AG beyond material QA。R2AF 不授权 R2AH experiment、CI、scale、runtime/default change、method claim、source scan、execution，也不在 R2AF 中授权 candidate/material generation。

 R2AG local execution authorized; R2AG private write authorized; R2AG bounded source scan authorized; R2AG candidate/material generation authorized; broad source scan, CI, network/provider/clone, experiment metrics, default/method/scale claims remain forbidden.
