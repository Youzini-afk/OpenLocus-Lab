# BEA-v1-HAAE-R2M Path-Prior Separation Mechanism Decomposition

Date: 2026-07-01

BEA-v1-HAAE-R2M Path-Prior Separation Mechanism Decomposition reads an explicit
existing R2I private material root only when the operator opts in. Default mode
does no private read and emits `haae_r2m_unavailable_no_explicit_r2i_private_material_root`.

```text
phase: BEA-v1-HAAE-R2M Path-Prior Separation Mechanism Decomposition
pass status: haae_r2m_path_prior_separation_mechanism_decomposition_complete_r2n_public_audit_authorized
self-test: 19/19
source lock: HAAE-R2L checkpoint 0dd357e
source status: haae_r2l_next_step_decision_mechanism_preflight_complete_r2m_mechanism_decomposition_authorized
input: explicit existing R2I private material root
output: aggregate-only mechanism buckets
mechanisms: extension/language prior; directory depth prior; same-module/path-token overlap; fixture artifact bias; control baseline weakness
summary: dominant_mechanism_bucket, confidence, actionability
dominant mechanism: path_structure_prior
confidence: medium_high
supporting buckets: extension_prior_supporting; directory_depth_prior_supporting; same_module_path_token_prior_supporting; fixture_pool_contains_path_cues; control_underfit
boundary: no method/default/scaling claim
next phase: BEA-v1-HAAE-R2N Public Audit Package
```

R2M writes no private rows, generates no material or candidates, runs no retrieval,
runtime, source scan, CI, network, provider, scheduler, or selector, and publishes
no raw paths, tokens, extensions, filenames, directories, task ids, queries,
snippets, labels, exact ranks, scores, hashes, line ranges, or per-task values.

Result: the public buckets point to `path_structure_prior`, not a generic method
victory. The signal is supported by extension/language alignment, directory-depth
alignment, same-module/path-token overlap, fixture path cues, and a deliberately
weak control baseline. This means the next step should audit the mechanism and
test robustness, not promote a default rule.
