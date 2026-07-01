# BEA-v1-HAAE-R2AL New Signal Family Public Design Preflight

日期：2026-07-01

BEA-v1-HAAE-R2AL New Signal Family Public Design Preflight 是 R2AK checkpoint `36fc4fa`、status `haae_r2ak_robustness_failure_decision_complete_r2al_new_signal_family_public_design_authorized_route_closed` 之后的 public-only design/preflight。Source lock 包含 R2AK self-test 22/22、forbidden scan pass、route closed for `r2ac_r2ai_single_rank_content_path_signal`、robustness failure `brittle_or_artifact`。

```text
phase: BEA-v1-HAAE-R2AL New Signal Family Public Design Preflight
status: haae_r2al_new_signal_family_public_design_preflight_complete_r2am_material_generation_preflight_authorized
self-test: 28/28
source checkpoint: 36fc4fa
source status: haae_r2ak_robustness_failure_decision_complete_r2al_new_signal_family_public_design_authorized_route_closed
selected signal family: evidence_pair_support_complementarity
route closed: r2ac_r2ai_single_rank_content_path_signal
failure: brittle_or_artifact
rationale: move from isolated single-candidate rank to multi-evidence consistency/support/contrast
rejected: public aggregate mechanism analysis rejected; single-rank content/path tweak rejected; lexical rank expansion rejected; provider semantic judgement rejected
next: BEA-v1-HAAE-R2AM Evidence-Pair Support Material Generation Preflight
R2AM scope: R2AM public-only preflight
R2AN: R2AN generation requires separate authorization
claims: no method/default/scale/winner/validated-signal claims
```

R2AL 选择 `evidence_pair_support_complementarity`。它拒绝 public aggregate mechanism analysis，因为 route closure 后价值较低；拒绝 single-rank content/path tweak，因为它共享 controls match signal 的 failure mode；拒绝 lexical rank expansion，因为它是 single-rank variant 而不是 new signal family；拒绝 provider semantic judgement，因为 provider/network execution 未授权。

R2AM 可以定义 evidence-pair/support material schema、public source allowlist、bounds/caps，以及 later R2AN 的 private-output contract。R2AM 必须保持 public-only preflight，不是 generation。
