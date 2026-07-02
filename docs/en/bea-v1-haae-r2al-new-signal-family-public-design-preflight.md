# BEA-v1-HAAE-R2AL New Signal Family Public Design Preflight

Date: 2026-07-03

BEA-v1-HAAE-R2AL New Signal Family Public Design Preflight is a public-only design/preflight after R2AK checkpoint `36fc4fa`, status `haae_r2ak_robustness_failure_decision_complete_r2al_new_signal_family_public_design_authorized_route_closed`. R2AK self-test 22/22, forbidden scan pass, route closed for `r2ac_r2ai_single_rank_content_path_signal`, and robustness failure `brittle_or_artifact` are source-locked.

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

R2AL selects `evidence_pair_support_complementarity`. It rejects public aggregate mechanism analysis as low value after route closure, rejects single-rank content/path tweak because it shares the failure mode where controls match signal, rejects lexical rank expansion because it is a single-rank variant and not a new signal family, and rejects provider semantic judgement because provider/network execution is not authorized.

R2AM may define evidence-pair/support material schema, public source allowlist, bounds/caps, and a private-output contract for later R2AN. R2AM must remain public-only preflight, not generation.
