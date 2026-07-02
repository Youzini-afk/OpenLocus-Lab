# BEA-v1-HAAE-R2AU Evidence-Pair Support Mechanism Decomposition Public Audit Package

日期：2026-07-03

BEA-v1-HAAE-R2AU Evidence-Pair Support Mechanism Decomposition Public Audit Package 是 public-only audit，只读取 R2AT public artifact only。不读取 private roots、private diagnostics、`/tmp` material 或 R2AN private material。

```text
phase: BEA-v1-HAAE-R2AU Evidence-Pair Support Mechanism Decomposition Public Audit Package
status: haae_r2au_evidence_pair_support_mechanism_decomposition_public_audit_package_complete_r2av_next_step_decision_authorized_pair_complementarity_supported
self-test: 44/44
self-test count 35/35: verified from R2AT
R2AT checkpoint: 0c9c108
R2AT status: haae_r2at_explicit_private_mechanism_decomposition_complete_r2au_public_audit_authorized_pair_complementarity_supported
R2AT public artifact only: true
public-only: true
audited buckets: pair_complementarity_supported; pair_complementarity_lift_high; support_vs_contrast_separation_medium; hard_negative_rejection_medium; path_confound_risk_low; gold_isolation_pass
privacy: no exact metric/raw private public fields; no private roots; no private diagnostics
boundary: no mechanism recomputation; no source/candidate/corpus scan; no material regeneration; no method/default/scale/raw claim
next: BEA-v1-HAAE-R2AV Evidence-Pair Support Next-Step Decision Package
next boundary: public decision/design only
```

R2AU 不从 private rows recompute mechanism metrics，不 regenerate material，不 scan source/candidate/corpus，也不运行 retrieval/OpenLocus/runtime/CI/network/provider/clone。Stop/go 只授权 BEA-v1-HAAE-R2AV Evidence-Pair Support Next-Step Decision Package，且为 public decision/design only。
