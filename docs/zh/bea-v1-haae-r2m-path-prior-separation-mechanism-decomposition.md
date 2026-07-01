# BEA-v1-HAAE-R2M Path-Prior Separation Mechanism Decomposition

日期：2026-07-01

BEA-v1-HAAE-R2M Path-Prior Separation Mechanism Decomposition 只在 operator 显式
opt in 时读取 explicit existing R2I private material root。默认模式不读取 private，并输出
`haae_r2m_unavailable_no_explicit_r2i_private_material_root`。

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

R2M 不写 private rows，不生成 material 或 candidates，不运行 retrieval、runtime、source
scan、CI、network、provider、scheduler 或 selector，并且不发布 raw paths、tokens、
extensions、filenames、directories、task ids、queries、snippets、labels、exact ranks、
scores、hashes、line ranges 或 per-task values。

结果：public buckets 指向 `path_structure_prior`，不是笼统的 method victory。这个信号由 extension/language alignment、directory-depth alignment、same-module/path-token overlap、fixture path cues，以及一个 deliberately weak control baseline 支撑。所以下一步应先 audit mechanism 并测试 robustness，而不是提升成默认规则。
